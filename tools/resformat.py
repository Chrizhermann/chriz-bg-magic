"""SPL, ITM and EFF files as plain data, and back.

`defs/*.json` hold what each resource is. Field values are numbers, strings, or a symbol for what
only the install can know:

    {"text": "..."}             a string; the build adds it to resources.tra
    {"state": "NAME"}           a SPLSTATE.IDS value
    {"splprot": [stat, value, relation]}
    {"sectype": "name"}         a MSECTYPE.2DA row
    {"statdesc": N}             a row of `statdesc` in defs/tables.json
    {"projectile": "name"}      a projectile this mod adds
    {"spell": "SYMBOL"}         the resref of a spell whose slot is chosen at install
"""
import struct

HEADER_SPL = [
    (0x00, "8s", "signature"), (0x08, "i", "name"), (0x0C, "i", "name_identified"), (0x10, "res", "sound"),
    (0x18, "I", "flags"), (0x1C, "H", "type"), (0x1E, "I", "exclusion"), (0x22, "H", "animation"),
    (0x24, "B", "min_level"), (0x25, "B", "school"), (0x26, "B", "min_strength"), (0x27, "B", "sectype"),
    (0x28, "12s", "unused_28"), (0x34, "I", "level"), (0x38, "H", "stack"), (0x3A, "res", "icon"),
    (0x42, "H", "lore"), (0x44, "res", "ground_icon"), (0x4C, "I", "weight"), (0x50, "i", "description"),
    (0x54, "i", "description_identified"), (0x58, "res", "description_icon"), (0x60, "I", "enchantment"),
]
ABILITY_SPL = [
    (0x00, "B", "form"), (0x01, "B", "ability_flags"), (0x02, "H", "location"), (0x04, "res", "icon"),
    (0x0C, "B", "target"), (0x0D, "B", "target_count"), (0x0E, "H", "range"), (0x10, "H", "min_level"),
    (0x12, "H", "casting_time"), (0x14, "10s", "unused_14"), (0x22, "H", "charges"),
    (0x24, "H", "charge_depletion"), (0x26, "H", "projectile"),
]
HEADER_ITM = [
    (0x00, "8s", "signature"), (0x08, "i", "name"), (0x0C, "i", "name_identified"), (0x10, "64s", "raw_10"),
    (0x50, "i", "description"), (0x54, "i", "description_identified"), (0x58, "12s", "raw_58"),
]
ABILITY_ITM = [(0x00, "30s", "raw_00"), (0x22, "8s", "raw_22"), (0x2A, "H", "projectile"), (0x2C, "12s", "raw_2c")]
EFFECT = [
    (0x00, "H", "opcode"), (0x02, "B", "target"), (0x03, "B", "power"), (0x04, "i", "p1"), (0x08, "I", "p2"),
    (0x0C, "B", "timing"), (0x0D, "B", "dispel"), (0x0E, "I", "duration"), (0x12, "B", "prob1"), (0x13, "B", "prob2"),
    (0x14, "res", "resource"), (0x1C, "i", "dice"), (0x20, "i", "sides"), (0x24, "I", "save"), (0x28, "i", "bonus"),
    (0x2C, "i", "special"),
]
EFF_V2 = [
    (0x10, "I", "opcode"), (0x14, "I", "target"), (0x18, "I", "power"), (0x1C, "i", "p1"), (0x20, "I", "p2"),
    (0x24, "I", "timing"), (0x28, "I", "duration"), (0x2C, "H", "prob1"), (0x2E, "H", "prob2"),
    (0x30, "res", "resource"), (0x38, "i", "dice"), (0x3C, "i", "sides"), (0x40, "I", "save"), (0x44, "i", "bonus"),
    (0x48, "i", "special"),
]
SIZES = {"res": 8}


def size(kind):
    return SIZES[kind] if kind == "res" else struct.calcsize("<" + kind)


def read_fields(spec, data, base=0):
    out = {}
    for off, kind, name in spec:
        if kind == "res":
            raw = data[base + off:base + off + 8]
            out[name] = raw.split(b"\0", 1)[0].decode("latin-1")
        elif kind.endswith("s"):
            n = int(kind[:-1])
            raw = data[base + off:base + off + n]
            out[name] = raw.decode("latin-1") if name == "signature" else raw.hex()
        else:
            out[name] = struct.unpack_from("<" + kind, data, base + off)[0]
    return out


def write_fields(spec, values, buffer, base=0, stamps=None, where=""):
    for off, kind, name in spec:
        value = values[name]
        if isinstance(value, dict):
            stamps.append({"offset": base + off, "kind": kind, "value": value, "field": f"{where}{name}"})
            continue
        if kind == "res":
            buffer[base + off:base + off + 8] = value.encode("latin-1").ljust(8, b"\0")
        elif kind.endswith("s"):
            n = int(kind[:-1])
            raw = value.encode("latin-1") if name == "signature" else bytes.fromhex(value)
            buffer[base + off:base + off + n] = raw
        else:
            struct.pack_into("<" + kind, buffer, base + off, value)


def read_resource(name, data):
    ext = name.rsplit(".", 1)[-1].lower()
    if ext == "eff":
        out = {"format": "eff", "effect": read_fields(EFF_V2, data), "rest": data[:0x10].hex() + "|" + data[0x50:].hex()}
        return out
    header_spec, ability_spec, ability_size = ((HEADER_SPL, ABILITY_SPL, 0x28) if ext == "spl"
                                               else (HEADER_ITM, ABILITY_ITM, 0x38))
    out = {"format": ext, "header": read_fields(header_spec, data)}
    ab_off, ab_count, fx_off = struct.unpack_from("<IHI", data, 0x64)
    first_cast, cast_count = struct.unpack_from("<HH", data, 0x6E)

    def effects(first, count):
        return [read_fields(EFFECT, data, fx_off + (first + i) * 0x30) for i in range(count)]
    out["casting"] = effects(first_cast, cast_count)
    out["abilities"] = []
    for a in range(ab_count):
        base = ab_off + a * ability_size
        ability = read_fields(ability_spec, data, base)
        count, first = struct.unpack_from("<HH", data, base + 0x1E)
        ability["effects"] = effects(first, count)
        out["abilities"].append(ability)
    return out


def build_resource(defn):
    """The bytes of a resource, and the fields only the install can fill."""
    stamps = []
    if defn["format"] == "eff":
        head, tail = defn["rest"].split("|")
        buffer = bytearray(bytes.fromhex(head) + b"\0" * 0x40 + bytes.fromhex(tail))
        write_fields(EFF_V2, defn["effect"], buffer, 0, stamps, "effect.")
        return bytes(buffer), stamps
    ext = defn["format"]
    header_spec, ability_spec, ability_size = ((HEADER_SPL, ABILITY_SPL, 0x28) if ext == "spl"
                                               else (HEADER_ITM, ABILITY_ITM, 0x38))
    abilities = defn["abilities"]
    casting = defn["casting"]
    count = len(casting) + sum(len(a["effects"]) for a in abilities)
    ab_off = 0x72
    fx_off = ab_off + ability_size * len(abilities)
    buffer = bytearray(fx_off + 0x30 * count)
    write_fields(header_spec, defn["header"], buffer, 0, stamps, "header.")
    struct.pack_into("<IHI", buffer, 0x64, ab_off, len(abilities), fx_off)
    struct.pack_into("<HH", buffer, 0x6E, 0, len(casting))
    index = 0
    for i, effect in enumerate(casting):
        write_fields(EFFECT, effect, buffer, fx_off + index * 0x30, stamps, f"casting[{i}].")
        index += 1
    for a, ability in enumerate(abilities):
        base = ab_off + a * ability_size
        write_fields(ability_spec, {k: v for k, v in ability.items()}, buffer, base, stamps, f"ability[{a}].")
        struct.pack_into("<HH", buffer, base + 0x1E, len(ability["effects"]), index)
        for i, effect in enumerate(ability["effects"]):
            write_fields(EFFECT, effect, buffer, fx_off + index * 0x30, stamps, f"ability[{a}].effect[{i}].")
            index += 1
    return bytes(buffer), stamps
