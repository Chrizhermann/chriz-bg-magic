"""Small readers and writers for the Infinity Engine files the tests need: KEY/BIFF, TLK,
SPL V1 and 2DA. Used to build made-up test games and to read installed games (read-only).
"""
import struct
from pathlib import Path

TYPES = {"2DA": 0x3F4, "ARE": 0x3F2, "BCS": 0x3EF, "CRE": 0x3F1, "EFF": 0x3F8, "IDS": 0x3F0,
         "ITM": 0x3ED, "SPL": 0x3EE}

FX_FORMAT = "<HBBiiBBIBB8siiIii"  # one 48-byte SPL/ITM effect
FX_FIELDS = ("opcode", "target", "power", "p1", "p2", "timing", "dispel", "duration", "prob1",
             "prob2", "resource", "dice", "sides", "save", "bonus", "special")
FX_DEFAULTS = dict(opcode=0, target=2, power=0, p1=0, p2=0, timing=0, dispel=1, duration=0,
                   prob1=100, prob2=0, resource="", dice=0, sides=0, save=0, bonus=0, special=0)

SAVE_SPELL, SAVE_BREATH, BYPASS_MIRROR = 0x1, 0x2, 0x1000000


# --- effects and SPL -------------------------------------------------------------------

def pack_fx(**kw):
    v = {**FX_DEFAULTS, **kw}
    v["resource"] = v["resource"].encode("ascii")
    return struct.pack(FX_FORMAT, *(v[f] for f in FX_FIELDS))


def unpack_fx(data, off):
    vals = struct.unpack_from(FX_FORMAT, data, off)
    fx = dict(zip(FX_FIELDS, vals))
    fx["resource"] = fx["resource"].split(b"\0", 1)[0].decode("latin-1").upper()
    return fx


def make_spl(spell_type=1, level=1, abilities=(), casting=(), name=-1, desc=-1, school=0,
             sectype=0, flags=0, extra_fx_first=False):
    """SPL V1. abilities: list of dicts with target, range, min_level, projectile, effects
    (list of effect dicts). casting: effect dicts for the casting features. With
    extra_fx_first the casting features are stored after the ability effects."""
    head = bytearray(0x72)
    head[0:8] = b"SPL V1  "
    struct.pack_into("<i", head, 0x08, name)
    struct.pack_into("<i", head, 0x0C, -1)
    struct.pack_into("<I", head, 0x18, flags)
    struct.pack_into("<H", head, 0x1C, spell_type)
    head[0x25] = school
    head[0x27] = sectype
    struct.pack_into("<I", head, 0x34, level)
    struct.pack_into("<i", head, 0x50, desc)
    struct.pack_into("<i", head, 0x54, -1)
    ab_off = 0x72
    fx_off = ab_off + 0x28 * len(abilities)
    blocks, ab_bytes = bytearray(), bytearray()
    groups = [list(a.get("effects", [])) for a in abilities]
    order = (list(range(len(groups))) + ["cast"]) if extra_fx_first else (["cast"] + list(range(len(groups))))
    index, starts = 0, {}
    for g in order:
        effects = list(casting) if g == "cast" else groups[g]
        starts[g] = index
        for fx in effects:
            blocks += pack_fx(**fx)
        index += len(effects)
    for i, a in enumerate(abilities):
        ab = bytearray(0x28)
        ab[0] = a.get("form", 1)
        struct.pack_into("<H", ab, 0x02, 4)
        ab[0x0C] = a.get("target", 1)
        struct.pack_into("<H", ab, 0x0E, a.get("range", 30))
        struct.pack_into("<H", ab, 0x10, a.get("min_level", 1))
        struct.pack_into("<H", ab, 0x12, a.get("casting_time", 1))
        struct.pack_into("<H", ab, 0x1E, len(groups[i]))
        struct.pack_into("<H", ab, 0x20, starts[i])
        struct.pack_into("<H", ab, 0x26, a.get("projectile", 1))
        ab_bytes += ab
    struct.pack_into("<I", head, 0x64, ab_off)
    struct.pack_into("<H", head, 0x68, len(abilities))
    struct.pack_into("<I", head, 0x6A, fx_off)
    struct.pack_into("<H", head, 0x6E, starts["cast"])
    struct.pack_into("<H", head, 0x70, len(casting))
    return bytes(head + ab_bytes + blocks)


def parse_spl(data):
    """{'type', 'level', 'name', 'desc', 'abilities': [{'target', 'effects': [...]}], 'casting'}"""
    if data[:8] != b"SPL V1  ":
        raise ValueError("not SPL V1")
    ab_off, = struct.unpack_from("<I", data, 0x64)
    ab_cnt, = struct.unpack_from("<H", data, 0x68)
    fx_off, = struct.unpack_from("<I", data, 0x6A)
    c_first, c_cnt = struct.unpack_from("<HH", data, 0x6E)
    out = {"type": struct.unpack_from("<H", data, 0x1C)[0], "level": struct.unpack_from("<I", data, 0x34)[0],
           "name": struct.unpack_from("<i", data, 0x08)[0], "desc": struct.unpack_from("<i", data, 0x50)[0],
           "abilities": [],
           "casting": [unpack_fx(data, fx_off + (c_first + i) * 48) for i in range(c_cnt)]}
    for a in range(ab_cnt):
        o = ab_off + a * 0x28
        n, first = struct.unpack_from("<HH", data, o + 0x1E)
        out["abilities"].append({"target": data[o + 0x0C], "min_level": struct.unpack_from("<H", data, o + 0x10)[0],
                                 "effects": [unpack_fx(data, fx_off + (first + i) * 48) for i in range(n)]})
    return out


# --- ITM (only what the description tests need) -----------------------------------------

def make_itm(abilities=(), desc=-1, desc_unid=-1, item_type=11):
    """ITM V1 with magical abilities; abilities: lists of effect dicts."""
    head = bytearray(0x72)
    head[0:8] = b"ITM V1  "
    struct.pack_into("<i", head, 0x08, -1)
    struct.pack_into("<i", head, 0x0C, -1)
    struct.pack_into("<H", head, 0x1C, item_type)
    struct.pack_into("<i", head, 0x50, desc_unid)
    struct.pack_into("<i", head, 0x54, desc)
    ab_off = 0x72
    fx_off = ab_off + 0x38 * len(abilities)
    ab_bytes, blocks, index = bytearray(), bytearray(), 0
    for effects in abilities:
        ab = bytearray(0x38)
        ab[0] = 3
        struct.pack_into("<H", ab, 0x1E, len(effects))
        struct.pack_into("<H", ab, 0x20, index)
        for fx in effects:
            blocks += pack_fx(**fx)
        index += len(effects)
        ab_bytes += ab
    struct.pack_into("<I", head, 0x64, ab_off)
    struct.pack_into("<H", head, 0x68, len(abilities))
    struct.pack_into("<I", head, 0x6A, fx_off)
    struct.pack_into("<H", head, 0x6E, index)
    struct.pack_into("<H", head, 0x70, 0)
    return bytes(head + ab_bytes + blocks)


def itm_descs(data):
    return struct.unpack_from("<ii", data, 0x50)


# --- TLK ---------------------------------------------------------------------------------

def make_tlk(texts):
    head = 18 + 26 * len(texts)
    table, blob = bytearray(), bytearray()
    for text in texts:
        raw = text.encode("utf-8")
        table += struct.pack("<H8sIIII", 1 if raw else 0, b"", 0, 0, len(blob), len(raw))
        blob += raw
    return b"TLK V1  " + struct.pack("<HII", 0, len(texts), head) + table + blob


def tlk_text(data, strref):
    count, start = struct.unpack_from("<II", data, 10)
    if strref < 0 or strref >= count:
        return None
    off, ln = struct.unpack_from("<II", data, 18 + 26 * strref + 18)
    return data[start + off:start + off + ln].decode("utf-8", "replace")


# --- 2DA and IDS -------------------------------------------------------------------------

def make_2da(columns, rows, default="0xffff"):
    pad = lambda v: str(v).ljust(max(12, len(str(v)) + 1))  # noqa: E731
    out = ["2DA                 V1.0", default, " " * 12 + "".join(pad(c) for c in columns)]
    out += [pad(label) + "".join(pad(v) for v in values) for label, values in rows]
    return ("\r\n".join(out) + "\r\n").encode("ascii")


def make_ids(pairs, header="IDS V1.0"):
    return ("\r\n".join([header] + [f"{n} {s}" for n, s in pairs]) + "\r\n").encode("ascii")


# --- KEY/BIFF ----------------------------------------------------------------------------

def write_key_bif(root, resources):
    """resources: list of (resref, type, bytes). Writes data/fixture.bif and chitin.key."""
    name = b"data/fixture.bif\0"
    data_offset = 20 + 16 * len(resources)
    entries, contents = bytearray(), bytearray()
    for ordinal, (_, kind, data) in enumerate(resources):
        entries += struct.pack("<IIIHH", ordinal, data_offset + len(contents), len(data), kind, 0)
        contents += data
    bif = b"BIFFV1  " + struct.pack("<III", len(resources), 0, 20) + entries + contents
    key = bytearray(b"KEY V1  " + struct.pack("<IIII", 1, len(resources), 24, 36 + len(name)))
    key += struct.pack("<IIHH", len(bif), 36, len(name), 1) + name
    for ordinal, (resref, kind, _) in enumerate(resources):
        key += struct.pack("<8sHI", resref.encode("ascii"), kind, ordinal)
    (Path(root) / "data").mkdir(parents=True, exist_ok=True)
    (Path(root) / "data/fixture.bif").write_bytes(bif)
    (Path(root) / "chitin.key").write_bytes(key)


class Game:
    """Read-only view of an installed game: override first, then the BIFFs of chitin.key."""

    def __init__(self, root):
        self.root = Path(root)
        kb = (self.root / "chitin.key").read_bytes()
        if kb[:8] != b"KEY V1  ":
            raise ValueError("not a KEY V1 file")
        nbif, nres, boff, roff = struct.unpack_from("<IIII", kb, 8)
        bifs = []
        for i in range(nbif):
            _, fnoff, fnlen = struct.unpack_from("<IIH", kb, boff + i * 12)
            bifs.append(kb[fnoff:fnoff + fnlen].split(b"\0")[0].decode("latin-1").replace("\\", "/"))
        self.index = {}
        for i in range(nres):
            o = roff + i * 14
            name = kb[o:o + 8].split(b"\0")[0].decode("latin-1").upper()
            kind, loc = struct.unpack_from("<HI", kb, o + 8)
            self.index[(name, kind)] = (bifs[loc >> 20], loc & 0x3FFF)
        self._bif = {}
        self.override = {p.name.upper(): p for p in (self.root / "override").iterdir() if p.is_file()} \
            if (self.root / "override").is_dir() else {}

    def biff(self, resref, ext):
        key = (resref.upper(), TYPES[ext.upper()])
        if key not in self.index:
            return None
        bif, loc = self.index[key]
        path = self.root / bif
        if not path.exists():
            path = next((q for q in (self.root / "data").iterdir() if q.name.lower() == Path(bif).name.lower()), None)
            if path is None:
                return None
        if path not in self._bif:
            with open(path, "rb") as f:
                hdr = f.read(20)
                n, _, off = struct.unpack_from("<III", hdr, 8)
                f.seek(off)
                tab = f.read(n * 16)
            self._bif[path] = {struct.unpack_from("<I", tab, i * 16)[0] & 0x3FFF: struct.unpack_from("<II", tab, i * 16 + 4)
                               for i in range(n)}
        o, sz = self._bif[path][loc]
        with open(path, "rb") as f:
            f.seek(o)
            return f.read(sz)

    def get(self, resref, ext):
        p = self.override.get(f"{resref.upper()}.{ext.upper()}")
        return p.read_bytes() if p else self.biff(resref, ext)

    def tlk(self, strref, lang="en_us"):
        p = next((q for q in (self.root / "lang").iterdir() if q.name.lower() == lang), None)
        data = (p / "dialog.tlk").read_bytes()
        return tlk_text(data, strref)
