"""What the mod ships whole: the build from defs/, reading and writing the files, and what an
install makes of them. The installs run the real component in made-up games; every file is checked
against defs/, with the install-time numbers read back from the game's own tables.
"""
import json
import struct
import sys

import fakegame as fg
import fixtures as fx
import ie
from harness import check, test

sys.path.insert(0, str(fg.REPO / "tools"))
import build_resources  # noqa: E402
import resformat as rf  # noqa: E402

RES = fg.MOD / "res"
TABLES = json.loads((fx.DEFS / "tables.json").read_text(encoding="utf-8"))
ADDED = {entry["file"]: symbol for symbol, entry in TABLES["spells"].items()}
SYMBOLS = ("text", "state", "splprot", "sectype", "statdesc", "projectile", "spell")
EEEX = {"M___EEex.lua": b"-- synthetic EEex bootstrap\n"}
RACE_ROW, NEW_ROW = ["118", "0", "3"], ["131", "1", "4"]  # one the fixture has, one it lacks


EFF = next(path.name.split(".")[0].upper() for path in sorted(fx.DEFS.glob("*.eff.json")))


def definitions(folder=None):
    """{"sppr103.spl": what defs/ says}; with `folder`, what defs/<folder>/ says."""
    root = fx.DEFS / folder if folder else fx.DEFS
    return {path.stem.lower(): json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(root.glob("*.json")) if path.name != "tables.json"}


ALT = build_resources.ALT.name


def is_symbol(value):
    return isinstance(value, dict) and next(iter(value), None) in SYMBOLS


def same_data(defined, read, where=""):
    """Differences between a definition and what was read back; symbols are the install's."""
    if is_symbol(defined):
        return []
    if isinstance(defined, dict):
        found = [] if defined.keys() == read.keys() else [f"{where}: keys {defined.keys() ^ read.keys()}"]
        return found + [d for key in defined.keys() & read.keys() for d in same_data(defined[key], read[key], f"{where}.{key}")]
    if isinstance(defined, list):
        found = [] if len(defined) == len(read) else [f"{where}: {len(defined)} defined, {len(read)} read"]
        return found + [d for i, pair in enumerate(zip(defined, read)) for d in same_data(*pair, f"{where}[{i}]")]
    return [] if defined == read else [f"{where}: {defined!r} defined, {read!r} read"]


class Numbers:
    """The numbers of this install, read back from the game's own tables after it."""

    def __init__(self, g):
        self.g = g
        game = ie.Game(g.root)
        self.states = self.ids(game.get("SPLSTATE", "IDS"))
        self.spells = self.ids(game.get("SPELL", "IDS"))
        self.projectiles = {k.lower(): v for k, v in self.ids(game.get("PROJECTL", "IDS")).items()}
        self.splprot = self.rows(game.get("SPLPROT", "2DA"))
        self.sectypes = [row[0] for row in self.rows(game.get("MSECTYPE", "2DA"))]
        self.statdesc = self.rows(game.get("STATDESC", "2DA"))

    @staticmethod
    def ids(data):
        out = {}
        for line in data.decode("latin-1").splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                out[parts[1]] = int(parts[0], 0)
        return out

    @staticmethod
    def rows(data):
        return [line.split() for line in data.decode("latin-1").splitlines()[3:] if line.strip()]

    def resref(self, symbol):
        number = self.spells[symbol]
        return f"{ {1: 'SPPR', 2: 'SPWI', 3: 'SPIN', 4: 'SPCL'}[number // 1000]}{number % 1000:03d}"

    def splprot_row(self, stat, value, relation):
        wanted = [int(str(v), 0) for v in (stat, value, relation)]
        for index, row in enumerate(self.splprot):
            if "*" not in row[1:4] and [int(v, 0) for v in row[1:4]] == wanted:
                return index
        raise AssertionError(f"no SPLPROT row for {wanted}")

    def statdesc_row(self, number):
        entry = TABLES["statdesc"][str(number)]
        found = [int(row[0]) for row in self.statdesc
                 if row[2].upper() == entry["bam"] and self.g.tlk(int(row[1])) == entry["text"]]
        check(len(found) == 1, f"statdesc {number}: rows {found}")
        return found[0]

    def value(self, symbol):
        kind, value = next(iter(symbol.items()))
        if kind == "state":
            return self.states[value]
        if kind == "splprot":
            return self.splprot_row(*value)
        if kind == "sectype":
            return self.sectypes.index(value)
        if kind == "statdesc":
            return self.statdesc_row(value)
        if kind == "projectile":
            return self.projectiles[value] + 1  # SPL and ITM headers count from PROJECTL.IDS + 1
        raise ValueError(symbol)


def defined_bytes(g, numbers, name, defn, actual, folder=""):
    """The resource as defs/ defines it in this game. A string's number is free: the check is that
    the number in the file leads to the defined text."""
    data, stamps = rf.build_resource(defn)
    check(data == (RES / folder / name).read_bytes(), f"{name}: res/ is not what defs/ builds")
    buffer = bytearray(data)
    for stamp in stamps:
        at, kind, symbol = stamp["offset"], stamp["kind"], stamp["value"]
        if "text" in symbol:
            ref = struct.unpack_from("<i", actual, at)[0]
            check(g.tlk(ref) == symbol["text"], f"{name}: {stamp['field']}: string {ref} is {g.tlk(ref)!r}")
            struct.pack_into("<i", buffer, at, ref)
        elif "spell" in symbol:
            buffer[at:at + 8] = numbers.resref(symbol["spell"]).encode("ascii").ljust(8, b"\0")
        else:
            struct.pack_into("<" + kind, buffer, at, numbers.value(symbol))
    return bytes(buffer)


def installed_name(numbers, name):
    return f"{numbers.resref(ADDED[name])}.spl" if name in ADDED else name


def differs(old, new):
    first = next((i for i, (a, b) in enumerate(zip(old, new)) if a != b), min(len(old), len(new)))
    return f"{len(old)} and {len(new)} bytes, first difference at {first:#x}"


def check_every_resource(g, derived=()):
    """Every file of defs/ and files/ is in override as defined, whatever stood there before.
    `derived`: files an install rightly builds from the spells of the game it finds."""
    numbers = Numbers(g)
    eeex = g.file("override/M___EEex.lua") is not None
    wrong = []
    alternatives = definitions(ALT)
    for name, defn in {**alternatives, **definitions()}.items():
        if name in derived or (name in build_resources.NEEDS_EEEX and not eeex):
            continue
        folder = ""
        if name in alternatives and not eeex:
            defn, folder = alternatives[name], ALT
        elif name not in definitions():
            continue  # only without EEex
        actual = g.file(f"override/{installed_name(numbers, name)}")
        check(actual is not None, f"{name} is not in override")
        expected = defined_bytes(g, numbers, name, defn, actual, folder)
        if actual != expected:
            wrong.append(f"{name}: {differs(expected, actual)}")
    check(not wrong, f"{len(wrong)} resources differ from defs/: {wrong[:12]}")
    for path in sorted((fg.MOD / "files").iterdir()):
        if path.name not in derived:
            check(g.file(f"override/{path.name}") == path.read_bytes(), f"{path.name} differs from files/")
    return numbers


def install(g):
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out and not fg.with_warnings(out), out)
    return out


def edited(name, change):
    """The shipped file with `change` applied to a copy of its bytes."""
    data = bytearray((RES / name).read_bytes())
    change(data)
    return bytes(data)


def first_stamp(kind, value=None):
    """The first file of defs/ with this symbol: its name, field offset and field size."""
    for name, defn in definitions().items():
        for stamp in rf.build_resource(defn)[1]:
            if kind in stamp["value"] and (value is None or stamp["value"][kind] == value):
                return name, stamp["offset"], "<" + stamp["kind"]
    raise AssertionError(f"no {kind} {value} in defs/")


def stamped(g, numbers, kind, value=None):
    name, offset, layout = first_stamp(kind, value)
    return struct.unpack_from(layout, g.file(f"override/{installed_name(numbers, name)}"), offset)[0]


@test
def the_build_is_in_sync_with_defs(work, weidu):
    """What is committed is what the generator makes of defs/."""
    build_resources.build(work / "built")
    built = {p.relative_to(work / "built/res").as_posix(): p.read_bytes()
             for p in (work / "built/res").rglob("*") if p.is_file()}
    shipped = {p.relative_to(RES).as_posix(): p.read_bytes() for p in RES.rglob("*") if p.is_file()}
    check(built.keys() == shipped.keys(), f"res/ differs in files: {sorted(built.keys() ^ shipped.keys())[:10]}")
    wrong = [name for name in built if built[name] != shipped[name]]
    check(not wrong, f"res/ is out of date: {wrong[:10]}")
    for rel in ("lib/cbmagic_resources.tpa", "languages/english/resources.tra"):
        check((work / "built" / rel).read_bytes() == (fg.MOD / rel).read_bytes(), f"{rel} is out of date")


@test
def reading_and_writing_round_trips(work, weidu):
    """Every definition survives being written and read back, field by field and byte by byte."""
    defs = definitions()
    check(sum(d["format"] in ("spl", "itm") for d in defs.values()) > 500, "defs/ is nearly empty")
    for name, defn in defs.items():
        data, stamps = rf.build_resource(defn)
        read = rf.read_resource(name, data)
        wrong = same_data(defn, read)
        check(not wrong, f"{name}: {wrong[:5]}")
        check(rf.build_resource(read)[0] == data, f"{name}: a second write differs")
        check(all(is_symbol(s["value"]) for s in stamps), f"{name}: unknown symbol")


@test
def decided_phase_one_spell_definitions(work, weidu):
    """The decided spells own their complete data, including new spell slots and class access."""
    defs = definitions()
    added = {
        "CLERIC_CBMAGIC_CONJURE_AIR_ELEMENTAL": {"file": "cbmair.spl", "type": 1, "level": 6},
        "CLERIC_CBMAGIC_ICELANCE": {"file": "cbmlance.spl", "type": 1, "level": 3},
    }
    for symbol, expected in added.items():
        check(TABLES["spells"].get(symbol) == expected, f"{symbol}: spell allocation")

    check(defs["sppr606.spl"]["header"]["name"] == 14253, "Fire Seeds keeps its own definition")
    check("sppr709.spl" not in ADDED, "priest Sphere of Chaos stands in Confusion's place, in no new slot")

    command = defs["sppr102.spl"]
    check((command["header"]["type"], command["header"]["level"], command["header"]["school"]) == (2, 1, 4),
          "Command header")
    check([ability["min_level"] for ability in command["abilities"]] == [1, 3, 5, 7, 9],
          "Command level breaks")
    for ability, penalty in zip(command["abilities"], (0, -1, -2, -3, -4)):
        check((ability["target"], ability["range"], ability["casting_time"], ability["projectile"]) == (1, 30, 1, 1),
              f"Command level {ability['min_level']}: delivery")
        payload = [(e["opcode"], e["target"], e["p1"], e["p2"], e["timing"], e["duration"],
                    e["save"], e["bonus"], e["resource"]) for e in ability["effects"]]
        check(payload == [(39, 2, 0, 0, 0, 6, 1, penalty, ""),
                          (174, 2, 0, 0, 4, 6, 1, penalty, "EFF_E05"),
                          (215, 1, 0, 0, 1, 0, 0, 0, "SPCOMSTT"),
                          (215, 2, 0, 0, 1, 0, 1, penalty, "SPCOMEND")],
              f"Command level {ability['min_level']}: payload")

    for name in ("spwi711.spl", "sppr709.spl"):
        sphere = defs[name]
        check(len(sphere["abilities"]) == 1, f"{name}: one field ability")
        ability = sphere["abilities"][0]
        check((ability["target"], ability["range"], ability["casting_time"], ability["projectile"]) == (4, 40, 7, 238),
              f"{name}: wizard field footprint")
        check({(e["prob2"], e["prob1"]) for e in ability["effects"]} ==
              {(0, 19), (20, 39), (40, 59), (60, 79), (80, 99)}, f"{name}: equal chaos windows")
    check(defs["spwi711.spl"]["abilities"] == defs["sppr709.spl"]["abilities"], "Sphere of Chaos payloads")
    check((defs["sppr709.spl"]["header"]["type"], defs["sppr709.spl"]["header"]["level"],
           defs["sppr709.spl"]["header"]["school"]) == (2, 7, 4), "priest Sphere of Chaos header")

    chaos = defs["spwi508.spl"]
    check([ability["min_level"] for ability in chaos["abilities"]] == [1, 15, 20], "Chaos level breaks")
    for ability, duration in zip(chaos["abilities"], (24, 30, 36)):
        check({e["duration"] for e in ability["effects"] if e["duration"]} == {duration},
              f"Chaos level {ability['min_level']}: duration")
        automatic = [e for e in ability["effects"] if e["dice"] == 4 and e["sides"] == 0]
        saved = [e for e in ability["effects"] if e["opcode"] in (61, 128, 139, 142, 174, 215)
                 and e["dice"] == 0 and e["sides"] == 5]
        check({e["opcode"] for e in automatic} == {61, 128, 139, 142, 174, 215} and
              all(e["save"] == 0 for e in automatic), f"Chaos level {ability['min_level']}: automatic branch")
        check({e["opcode"] for e in saved} == {61, 128, 139, 142, 174, 215} and
              all((e["save"], e["bonus"]) == (1, -4) for e in saved),
              f"Chaos level {ability['min_level']}: saving branch")

    air = defs["cbmair.spl"]
    check((air["header"]["type"], air["header"]["level"], air["header"]["school"], air["header"]["exclusion"]) ==
          (2, 6, 2, 1073741824), "Conjure Air Elemental header and druid access")
    air_rows = [(11, 64, 35, 1), (12, 61, 37, 2), (13, 58, 39, 3), (14, 55, 40, 5),
                (15, 52, 42, 6), (16, 49, 44, 7), (17, 46, 46, 8), (18, 43, 47, 10),
                (19, 40, 49, 11), (20, 37, 51, 12)]
    for ability, (level, low, middle, high) in zip(air["abilities"], air_rows):
        check((ability["min_level"], ability["target"], ability["range"], ability["casting_time"], ability["projectile"]) ==
              (level, 4, 35, 9, 1), f"Conjure Air Elemental level {level}: ability")
        upper_middle = low + middle - 1
        payload = [(e["opcode"], e["target"], e["p2"], e["timing"], e["dispel"], e["duration"],
                    e["prob2"], e["prob1"], e["resource"]) for e in ability["effects"]]
        check(payload == [(177, 1, 2, 0, 2, level * 60, 0, low - 1, "CBMAIR1"),
                          (177, 1, 2, 0, 2, level * 60, low, upper_middle, "CBMAIR2"),
                          (177, 1, 2, 0, 2, level * 60, upper_middle + 1, 99, "CBMAIR3")],
              f"Conjure Air Elemental level {level}: table")
    for tier in range(1, 4):
        effect = defs[f"cbmair{tier}.eff"]["effect"]
        check((effect["opcode"], effect["target"], effect["p1"], effect["p2"], effect["resource"]) ==
              (67, 1, 0, 0, f"CBMAIR{tier}"), f"air elemental tier {tier}: summon")
        creature = fg.MOD / "files" / f"cbmair{tier}.cre"
        check(creature.is_file(), f"air elemental tier {tier}: creature")
        data = creature.read_bytes()
        scripts = [data[offset:offset + 8].split(b"\0", 1)[0].decode("ascii")
                   for offset in range(0x248, 0x270, 8)]
        check(data[0x234] == (12, 16, 24)[tier - 1], f"air elemental tier {tier}: Hit Dice")
        check(scripts == ["None", "None", "None", "None", "BDSUM00"],
              f"air elemental tier {tier}: wizard control script")

    icelance = defs["cbmlance.spl"]
    check((icelance["header"]["type"], icelance["header"]["level"], icelance["header"]["school"],
           icelance["header"]["exclusion"]) == (2, 3, 6, 1073741824), "Icelance header and druid access")
    ability = icelance["abilities"]
    check(len(ability) == 1 and (ability[0]["target"], ability[0]["range"], ability[0]["casting_time"]) == (1, 100, 3),
          "Icelance delivery")
    payload = [(e["opcode"], e["target"], e["power"], e["p1"], e["p2"], e["timing"],
                e["duration"], e["save"], e["dice"], e["sides"]) for e in ability[0]["effects"]]
    check(payload == [(45, 2, 3, 0, 0, 0, 18, 1, 0, 0),
                      (12, 2, 3, 0, 131072, 1, 0, 0, 5, 6)], "Icelance stun and cold damage")
    check(all(e["opcode"] != 139 for e in ability[0]["effects"]), "Icelance has no independent stun message")
    check((defs["cbmlance.spl"]["header"]["school"], ability[0]["projectile"]) == (6, 233), "Icelance school and missile")

    for name in ("sppr102.spl", "spwi508.spl", "spwi711.spl", "sppr709.spl", "cbmair.spl", "cbmlance.spl"):
        check("text" in defs[name]["header"]["description"], f"{name}: complete English description")


@test
def definitions_lean_on_no_other_mod(work, weidu):
    """Nothing of EET or EE Fixpack is named: their files are not in every game this mod supports."""
    def resources(d):
        if isinstance(d, dict):
            if isinstance(d.get("resource"), str):
                yield d["resource"]
            for value in d.values():
                yield from resources(value)
        elif isinstance(d, list):
            for value in d:
                yield from resources(value)

    foreign = {f"{name}: {res}" for name, defn in definitions().items() for res in resources(defn)
               if res.upper().startswith(("#CURE", "K#FAM", "CDWSTYL", "CDINVEXP", "CDMK25", "DWFPDEVA", "SPINHUMW", "SPINHUMR"))}
    check(not foreign, f"{len(foreign)} named: {sorted(foreign)[:8]}")


@test
def celestials_are_what_was_decided(work, weidu):
    """Every spell that calls a celestial, the game's own effects, and the creatures they call."""
    defs = definitions()
    spells = {"sppr726.spl": ("SPDEVA", 7, 180, 1), "sppr727.spl": ("SPDEVA2", 7, 180, 1), "spcl923.spl": ("SPDEVA", 7, 180, 7),
              "spcl935.spl": ("SPDEVA2", 7, 180, 7), "spwi923.spl": ("SPPLAN", 9, 120, 1), "spwi924.spl": ("SPPLAN2", 9, 120, 1)}
    for name, (effect, power, duration, level) in spells.items():
        header, abilities = defs[name]["header"], defs[name]["abilities"]
        check((header["type"], header["level"], header["school"], len(abilities)) == (4, level, 2, 1), f"{name}: header")
        row = abilities[0]
        check((row["target"], row["range"], row["casting_time"], row["min_level"]) == (4, 30, 9, 1), f"{name}: delivery")
        check([(e["opcode"], e["target"], e["power"], e["p2"], e["duration"], e["resource"]) for e in row["effects"]] ==
              [(177, 1, power, 2, duration, effect)], f"{name}: summon")
        check("text" in header["description"] and "old" in header["description"], f"{name}: complete English description")
    creatures = {"spdeva.eff": ("CBMDEVAG", 7), "spdeva2.eff": ("CBMDEVAE", 7), "spplan.eff": ("CBMPLANG", 9),
                 "spplan2.eff": ("CBMPLANE", 9)}
    for name, (creature, power) in creatures.items():
        row = defs[name]["effect"]
        check((row["opcode"], row["target"], row["power"], row["p2"], row["resource"]) == (67, 1, power, 1, creature),
              f"{name}: calls the mod's creature")
    # What the files hold; the game adds CON 18's 36 Hit Points, the Armor Class of DEX, and so on.
    deva = dict(hp=100, ac=-1, thac0=10, attacks=1, levels=[14, 14, 1], attributes=[19, 0, 18, 18, 18, 18, 20])
    planetar = dict(hp=116, ac=-3, thac0=7, attacks=2, levels=[18, 18, 1], attributes=[19, 0, 18, 21, 19, 18, 22])
    for name, want, resist, spells, script, alignment, immune in (
            ("cbmdevag.cre", deva, [50, 100, 100, 0, 70, 50, 100, 10, 10, 10, 10], 29, "CBMDEVAC", 49, "IMMUNE2"),
            ("cbmdevae.cre", deva, [100, 0, 100, 50, 70, 100, 0, 10, 10, 10, 10], 29, "CBMDEVAC", 51, "IMMUNE2"),
            ("cbmplang.cre", planetar, [50, 100, 100, 0, 75, 50, 100, 20, 20, 20, 20], 38, "CBMPLANC", 49, "IMMUNE3"),
            ("cbmplane.cre", planetar, [100, 0, 100, 50, 75, 100, 0, 20, 20, 20, 20], 38, "CBMPLANC", 51, "IMMUNE3")):
        creature = defs[name]
        check({key: creature[key] for key in want} == want, f"{name}: values before the game's own bonuses")
        check(creature["resistances"] == resist and creature["saves"] == [3, 5, 4, 4, 6], f"{name}: resistances and saves")
        check((creature["gender"], creature["alignment"], creature["class"]) == (5, alignment, 8), f"{name}: not a SUMMONED gender")
        check(creature["scripts"] == [script, "None", "None", "None", "BDSUM00"], f"{name}: limit and default summon scripts")
        check(sum(sum(level.values()) for level in creature["spells"]) == spells, f"{name}: spells")
        check(creature["items"]["ring_left"] == immune, f"{name}: weapon immunity")
    for script, kind in (("cbmdevac.bcs", b"GLOBALCBMDEVASK"), ("cbmplanc.bcs", b"GLOBALCBMPLANASK")):
        data = (fg.MOD / "files" / script).read_bytes()
        check(b"LOCALSCBMARRIVE" in data and kind in data, f"{script}: asks for its own kind")


@test
def creature_files_hold_together(work, weidu):
    """Every table of every creature lies inside its file and agrees with the others."""
    files = [*sorted((fg.MOD / "files").glob("*.cre")), *sorted(RES.glob("*.cre"))]
    check(len(files) > 20, "creatures are missing")
    for path in files:
        data = path.read_bytes()
        known, known_n, info, info_n, spells, spells_n, slots, items, items_n, effects, effects_n = \
            struct.unpack_from("<IIIIIIIIIII", data, 0x2A0)
        size = 264 if data[0x33] else 48
        for what, at, count, width in (("known spells", known, known_n, 12), ("spell levels", info, info_n, 16),
                                       ("memorised spells", spells, spells_n, 12), ("items", items, items_n, 20),
                                       ("effects", effects, effects_n, size), ("slots", slots, 1, 80)):
            check(at + count * width <= len(data), f"{path.name}: {what} run past the end of the file")
        for row in range(info_n):
            first, count = struct.unpack_from("<II", data, info + 16 * row + 8)
            check(first + count <= spells_n, f"{path.name}: spell level {row} points past the memorised spells")
        held = struct.unpack_from("<38h", data, slots)
        check(all(i == -1 or 0 <= i < items_n for i in held), f"{path.name}: a slot points past the items")


@test
def find_familiar_keeps_the_game_s_summoning(work, weidu):
    """School and description are written; what calls the familiar stays each game's own."""
    summon = fx.fx(opcode=177, target=1, p2=2, timing=1, resource="K#FAMSUM")
    g = fg.FakeGame(work, weidu, tlk=fx.tlk(), biff=fx.game(
        SPWI123_SPL=ie.make_spl(1, 1, [{"target": 4, "effects": [summon]}], school=2)))
    install(g)
    spell = g.file("override/spwi123.spl")
    check(spell[0x25] == 0, f"Find Familiar school {spell[0x25]}")
    effects = ie.parse_spl(spell)["abilities"][0]["effects"]
    check([e["resource"] for e in effects] == ["K#FAMSUM"], f"summoning changed: {effects}")
    text = ie.tlk_text(g.file("lang/en_us/dialog.tlk"), struct.unpack_from("<i", spell, 0x50)[0])
    check("48 in Throne of Bhaal" in text and "9 in Baldur's Gate" in text, text[-300:])


@test
def overwrite_whatever_stood_there(work, weidu):
    """A hand edit, other text, other effect counts, garbage and nothing at all: each ends as
    defined, and the install runs through without a warning. Second install and uninstall too."""
    def heal_five_more(data):
        fx_off = struct.unpack_from("<I", data, 0x6A)[0]
        first = struct.unpack_from("<H", data, struct.unpack_from("<I", data, 0x64)[0] + 0x20)[0]
        at = fx_off + first * 0x30 + 4
        struct.pack_into("<i", data, at, struct.unpack_from("<i", data, at)[0] + 5)

    def other_text(data):
        struct.pack_into("<ii", data, 0x50, 2, 2)
        struct.pack_into("<i", data, 0x08, 1)

    other_counts = ie.make_spl(1, 4, [{"effects": [fx.fx(opcode=146, resource="SPWI414A")] * 7},
                                      {"min_level": 5, "effects": []}, {"min_level": 9, "effects": [fx.fx(opcode=37)]}],
                               casting=[fx.fx(opcode=139, p1=5)] * 3)
    garbage = bytes(range(256)) * 3
    override = {"SPPR103.SPL": edited("sppr103.spl", heal_five_more),      # Cure Light Wounds, by hand
                "SPWI201.SPL": edited("spwi201.spl", other_text),          # Blur, which the bonus types visit
                "SPPR101.SPL": garbage,                                    # Bless
                "SPWI608.SPL": b"SPL V1  ",                                # Pierce Magic, cut off
                "SCRL7L.ITM": garbage,                                     # the scroll of Pierce Magic
                f"{EFF}.EFF": garbage}
    biff = {"SPWI414.SPL": other_counts,                                   # Spirit Armor, another mod's
            "SPPR202.SPL": garbage,                                        # Barkskin, garbage in the BIFF
            "SPWI613.SPL": edited("spwi613.spl", other_text)}              # Improved Haste
    missing = "SPWI305.SPL"  # Haste: stands nowhere before the install
    g = fg.FakeGame(work, weidu, tlk=fx.tlk(), biff=fx.game(**{k.replace(".", "_"): v for k, v in biff.items()}),
                    override={**override, **EEEX})
    check(g.file(f"override/{missing}") is None, "the spell that is not there is there")
    before = g.tree()
    install(g)
    check_every_resource(g)
    installed = g.tree()
    # A second install gives the same game, and the uninstall gives back what stood there.
    install(g)
    check(g.tree() == installed, "a second install changed the game")
    check_every_resource(g)
    out = g.uninstall()
    check("SUCCESSFULLY REMOVED" in out, out)
    check(g.tree() == before, "the uninstall did not give back what stood there")
    for name, data in override.items():
        check(g.file(f"override/{name}") == data, f"{name} did not come back")
    check(g.file(f"override/{missing}") is None, "a file of ours stayed behind")


@test
def install_time_numbers_follow_the_game(work, weidu):
    """With other rows in the tables and other strings in the TLK, the numbers in the files follow."""
    def game(root, extra):
        states = fx.SPLSTATES if not extra else [(0, "CHAOTIC_COMMANDS"), (7, "OTHER_MOD"), (99, "BARKSKIN"), (100, "MANTLE")]
        prot = fx.SPLPROT_ROWS if not extra else [(f"{i}_OTHER", ["0x10a", str(i), "1"]) for i in range(10, 17)] + fx.SPLPROT_ROWS
        sectypes = [(f"OtherMod{i}", "1000") for i in range(extra)]
        projectiles = [(300 + i, f"OTHER{i}") for i in range(extra)]
        return fg.FakeGame(root, weidu, tlk=fx.tlk([f"Another mod's string {i}" for i in range(extra * 10)]), biff=fx.game(
            SPLSTATE_IDS=ie.make_ids(states), SPLPROT_2DA=ie.make_2da(["STAT", "VALUE", "RELATION"], prot),
            MSECTYPE_2DA=fx.msectype(sectypes), STATDESC_2DA=fx.statdesc(extra),
            PROJECTL_IDS=fx.projectl(projectiles), MISSILE_IDS=fx.missile(projectiles)))

    plain, other = game(work / "plain", 0), game(work / "other", 5)
    install(plain)
    install(other)
    a, b = check_every_resource(plain), check_every_resource(other)
    # Spell states: what the game has, and a free one for what it lacks.
    check((stamped(plain, a, "state", "BARKSKIN"), stamped(other, b, "state", "BARKSKIN")) == (1, 99), "state BARKSKIN")
    check((stamped(plain, a, "state", "MANTLE"), stamped(other, b, "state", "MANTLE")) == (4, 100), "state MANTLE")
    check(0 <= stamped(other, b, "state", "CBM_BONUS_TYPED") <= 255, "a state of ours")
    # SPLPROT: a row the game has, seven rows further down, and one it did not have.
    check((stamped(plain, a, "splprot", RACE_ROW), stamped(other, b, "splprot", RACE_ROW)) == (4, 11), "SPLPROT row")
    check(stamped(plain, a, "splprot", NEW_ROW) >= len(fx.SPLPROT_ROWS), "a new SPLPROT row goes behind the others")
    check(stamped(other, b, "splprot", NEW_ROW) == stamped(plain, a, "splprot", NEW_ROW) + 7, "a new SPLPROT row")
    # Sectype, projectile and record row: five rows further down.
    check(stamped(other, b, "sectype", "cbm_Haste") == stamped(plain, a, "sectype", "cbm_Haste") + 5, "sectype")
    check(stamped(plain, a, "statdesc", 209) == 209 and stamped(other, b, "statdesc", 209) == 214, "record row")
    check((stamped(plain, a, "projectile"), stamped(other, b, "projectile")) == (160, 306), "projectile")
    # Strings: new ones behind what the TLK holds.
    name, offset, layout = first_stamp("text")
    refs = [struct.unpack_from(layout, g.file(f"override/{installed_name(n, name)}"), offset)[0]
            for g, n in ((plain, a), (other, b))]
    check(refs[0] >= len(fx.TEXTS) and refs[1] == refs[0] + 50, f"string numbers {refs}")
    # A record row of the base game takes our text, whatever it said.
    for g, n in ((plain, a), (other, b)):
        rows = {int(row[0]): int(row[1]) for row in n.statdesc}
        for row, entry in TABLES["statdesc_changed"].items():
            check(g.tlk(rows[int(row)]) == entry["text"], f"record row {row}")


@test
def install_on_eet_and_with_eeex(work, weidu):
    """The result does not depend on the game or on EEex: what EEex adds comes on top."""
    g = fg.FakeGame(work / "eet", weidu, game="eet", tlk=fx.tlk(), biff=fx.game(), override=EEEX)
    install(g)
    check_every_resource(g)
    check(g.file("override/M_CBMREC.lua") is not None, "the record listener needs EEex and it is there")
    g = fg.FakeGame(work / "plain", weidu, tlk=fx.tlk(), biff=fx.game())
    out = install(g)
    check_every_resource(g)
    check(g.file("override/M_CBMREC.lua") is None and "EEex bootstrap absent" in out, "no listener without EEex")


@test
def other_languages_keep_their_descriptions(work, weidu):
    """English text in a German game would be no better: it keeps its own until a translation exists."""
    g = fg.FakeGame(work, weidu, tlk=fx.tlk(), biff=fx.game(), lang="de_DE")
    out = install(g)
    check("descriptions exist only in English so far" in out, out)
    definition = json.loads((fg.REPO / "defs/sppr103.spl.json").read_text(encoding="utf-8"))
    old_text = definition["header"]["description"]["old"]
    check(g.spl("SPPR103")["desc"] == old_text, "the description is not the game's own")


@test
def what_needs_eeex_stays_out_without_it(work, weidu):
    """Pierce Magic's new rule is an EEex callback, which does nothing without EEex. There the game's
    spell and scroll stay, so that the spell works and its text tells the truth; the log says so."""
    spell = ie.make_spl(1, 6, [{"effects": [fx.fx(opcode=166, p1=-15, duration=90)]}], desc=1)
    scroll = ie.make_itm([[fx.fx(opcode=147, target=1, timing=1, resource="SPWI608")]], desc=1)
    biff = fx.game(SPWI608_SPL=spell, SCRL7L_ITM=scroll)
    g = fg.FakeGame(work / "plain", weidu, tlk=fx.tlk(), biff=biff)
    out = install(g)
    check("spwi608.spl stays as it is: its new rule needs EEex" in out, out)
    check(g.file("override/SPWI608.SPL") is None and g.file("override/SCRL7L.ITM") is None, "the game's Pierce Magic is gone")
    check_every_resource(g)
    g = fg.FakeGame(work / "eeex", weidu, tlk=fx.tlk(), biff=biff, override=EEEX)
    install(g)
    check(any(e["opcode"] == 402 for e in g.spl("SPWI608")["abilities"][0]["effects"]), "EEex: ours")
    check_every_resource(g)


@test
def lesser_restoration_ends_drain_with_eeex(work, weidu):
    """Without EEex the game's Lesser Restoration stays. With it the spell calls CBMLRES, and Blood
    Rage keeps its own weakness in whatever slot this game gave it."""
    g = fg.FakeGame(work / "plain", weidu, tlk=fx.tlk(), biff=fx.game())
    out = install(g)
    check("sppr417.spl stays as it is: its new rule needs EEex" in out, out)
    check(g.file("override/SPPR417.SPL") is None, "Lesser Restoration was written without EEex")
    biff = fx.game(SPELL_IDS=fx.spell_ids([(1421, "CLERIC_BLOOD_RAGE")]), SPPR421_SPL=ie.make_spl(2, 4))
    g = fg.FakeGame(work / "eeex", weidu, tlk=fx.tlk(), biff=biff, override=EEEX)
    install(g)
    effects = g.spl("SPPR417")["abilities"][0]["effects"]
    check([e["opcode"] for e in effects] == [224, 402, 215, 61, 240, 93] and effects[1]["resource"] == "CBMLRES",
          f"Lesser Restoration: {[(e['opcode'], e['resource']) for e in effects]}")
    lua = g.file("override/M_CBMRST.lua").decode("utf-8")
    check('local SPARED = { ["SPPR421"] = true }' in lua and "%" not in lua, "Blood Rage is not spared")


@test
def simulacrum_keeps_the_abilities_of_its_level(work, weidu):
    """The clone helper calls CBMSIMU and the module is there; without EEex the game's text stays,
    which does not promise the filter."""
    g = fg.FakeGame(work / "plain", weidu, tlk=fx.tlk(), biff=fx.game())
    out = install(g)
    check("spwi804.spl stays as it is: its new rule needs EEex" in out, out)
    g = fg.FakeGame(work / "eeex", weidu, tlk=fx.tlk(), biff=fx.game(), override=EEEX)
    install(g)
    effects = g.spl("SIMULACR")["abilities"][0]["effects"]
    check(effects[-1]["opcode"] == 402 and effects[-1]["resource"] == "CBMSIMU", "the clone helper does not call CBMSIMU")
    check([e["p2"] for e in effects if e["opcode"] == 144] == [14, 9, 11, 12], "quick items blocked, abilities open")
    check(b"function CBMSIMU" in g.file("override/M_CBMSIM.lua"), "the module is missing")
    check_every_resource(g)


def effects_of(g, name):
    return [e for a in ie.parse_spl(ie.Game(g.root).get(name, "SPL"))["abilities"] for e in a["effects"]]


@test
def iwd_spells_are_patched_on_top_of_what_ships(work, weidu):
    """The IWD spells are rebuilt from the decision, so their order, omissions and even a corrupt
    predecessor never choose the result. Chant's private copies come from the game's Chant."""
    def damage(power, kind=0x400000):
        return fx.fx(opcode=12, target=2, power=power, p1=11, p2=kind, timing=1, dispel=1)

    def touch(level, item):
        return ie.make_spl(2, level, [{"target": 5, "casting_time": 7, "effects": [
            fx.fx(opcode=111, target=1, power=level, duration=15, resource=item)]}])

    def direct(level):
        return ie.make_spl(2, level, [{"target": 1, "casting_time": 5, "effects": [damage(level)]}])

    def timed(opcode, p1=1, **kw):
        return fx.fx(opcode=opcode, p1=p1, target=2, power=3, duration=60, dispel=3, **kw)

    ids = fx.spell_ids([(1215, "CLERIC_CURE_MODERATE_WOUNDS"), (1219, "CLERIC_CAUSE_MODERATE_WOUNDS"),
                        (1321, "CLERIC_CAUSE_MEDIUM_WOUNDS"), (1450, "CLERIC_CAUSE_SERIOUS_WOUNDS_IWD"),
                        (1550, "CLERIC_CAUSE_CRITICAL_WOUNDS_IWD"), (1525, "CLERIC_RIGHTEOUS_WRATH_OF_THE_FAITHFUL"),
                        (1734, "CLERIC_SYMBOL_HOPELESSNESS"), (2323, "WIZARD_ICELANCE"),
                        (2427, "WIZARD_EMOTION_HOPE"), (2516, "WIZARD_CONJURE_LESSER_FIRE_ELEMENTAL"),
                        (2520, "WIZARD_CONJURE_LESSER_AIR_ELEMENTAL"), (2521, "WIZARD_CONJURE_LESSER_EARTH_ELEMENTAL"),
                        (2526, "WIZARD_CONJURE_LESSER_WATER_ELEMENTAL"), (2620, "WIZARD_CONJURE_FIRE_ELEMENTAL"),
                        (2621, "WIZARD_CONJURE_AIR_ELEMENTAL"), (2622, "WIZARD_CONJURE_EARTH_ELEMENTAL"),
                        (2633, "WIZARD_CONJURE_WATER_ELEMENTAL")])
    lance = bytearray(ie.make_spl(1, 3, [{"target": 1, "projectile": 348}]))
    lance[0x3A:0x42] = b"SPWI323C"
    lance_ability = struct.unpack_from("<I", lance, 0x64)[0]
    lance[lance_ability + 4:lance_ability + 12] = b"SPWI323B"
    hopelessness = bytearray(ie.make_spl(1, 4, [{"target": 4, "projectile": 352, "effects": [
        fx.fx(opcode=39, target=2, power=4, p2=1, duration=54), fx.fx(opcode=45, target=2)]}]))
    water = bytearray(ie.make_spl(1, 6, [{"effects": []}], name=7))
    water[0x3A:0x42] = b"SPWI633C"
    water_ability = struct.unpack_from("<I", water, 0x64)[0]
    water[water_ability + 4:water_ability + 12] = b"SPWI633B"
    biff = fx.game(
        SPELL_IDS=ids, SPWI411_SPL=bytes(hopelessness), SPPR734_SPL=bytes(range(256)) * 3, SPWI427_SPL=ie.make_spl(),
        SPWI323_SPL=bytes(lance), SPWI526_SPL=ie.make_spl(), SPWI633_SPL=bytes(water),
        SPPR215_SPL=ie.make_spl(2, 2, [{"target": 1, "casting_time": 5, "effects": [fx.fx(opcode=17, target=2, p1=11, timing=1)]}]),
        SPPR219_SPL=direct(2), SPPR321_SPL=direct(3), SPPR450_SPL=touch(4, "IWDSER"), SPPR550_SPL=touch(5, "IWDCRI"),
        IWDSER_ITM=ie.make_itm([[damage(4)]], item_type=3), IWDCRI_ITM=ie.make_itm([[damage(5)]], item_type=3),
        SPPR525_SPL=ie.make_spl(2, 5, [{"target": 4, "effects": [fx.fx(opcode=146, p2=1, timing=1, resource="WRATHA")]}]),
        WRATHA_SPL=ie.make_spl(2, 5, [{"target": 4, "effects": [timed(54), timed(1), timed(206, resource="SPWI305", p2=16)]}]),
        SPPR203_SPL=ie.make_spl(2, 2, [{"target": 4, "effects": [
            fx.fx(opcode=146, p2=1, timing=1, resource="SPPR203E"), fx.fx(opcode=146, p2=1, timing=1, resource="SPPR203D")]}]),
        SPPR203E_SPL=ie.make_spl(2, 2, [{"target": 4, "effects": [timed(22), timed(33)]}]),
        SPPR203D_SPL=ie.make_spl(2, 2, [{"target": 4, "effects": [timed(22, -1), timed(33, -1)]}]))
    g = fg.FakeGame(work, weidu, tlk=fx.tlk(), biff=biff)
    before = g.tree()
    install(g)
    check_every_resource(g, derived=("cbb0.spl", "cbb1.spl", "cbmbonus.2da", "cbmlance.spl",
                                     "cbmiwhe.spl", "cbmiwhs.spl"))

    druid = g.file(f"override/{installed_name(Numbers(g), 'cbmlance.spl')}")
    ability = struct.unpack_from("<I", druid, 0x64)[0]
    check(druid[0x3A:0x42] == b"SPWI323C" and druid[ability + 4:ability + 12] == b"SPWI323B", "druid Icelance icons")
    check(struct.unpack_from("<H", druid, ability + 0x26)[0] == 348, "druid Icelance missile")

    roll = next(e for e in effects_of(g, "SPPR215") if e["opcode"] == 17)
    check((roll["p1"], roll["dice"], roll["sides"]) == (4, 2, 8), f"Cure Moderate: {roll}")
    for spell, payload_roll in (("SPPR219", (4, 2, 8)), ("SPPR321", (7, 2, 8))):
        guard, cast, block = effects_of(g, spell)[:3]
        check((guard["opcode"], cast["opcode"], block["opcode"]) == (318, 146, 324), f"{spell} undead split")
        heal = next(e for e in effects_of(g, cast["resource"]) if e["opcode"] == 17)
        check((heal["p1"], heal["dice"], heal["sides"]) == payload_roll, f"{spell} payload: {heal}")
    for item, payload_roll in (("IWDSER", (7, 3, 8)), ("IWDCRI", (12, 4, 8))):
        rows = ie.Game(g.root).get(item, "ITM")
        fx_off = struct.unpack_from("<I", rows, 0x6A)[0]
        cast = ie.unpack_fx(rows, fx_off + 0x30)
        check(cast["opcode"] == 146, f"{item}: no payload: {cast}")
        heal = next(e for e in effects_of(g, cast["resource"]) if e["opcode"] == 17)
        check((heal["p1"], heal["dice"], heal["sides"]) == payload_roll, f"{item} payload: {heal}")
    child = next(e for e in effects_of(g, "SPPR525") if e["opcode"] == 146)["resource"]
    check(child != "WRATHA", "Righteous Wrath's payload not isolated")
    check(not any(e["opcode"] == 206 for e in effects_of(g, child)), "Righteous Wrath still blocks Haste")
    check(any(e["opcode"] == 1 and e["resource"] == "CBTAPR" for e in effects_of(g, child)), "extra attack not tagged")
    emotion_file = g.file("override/spwi411.spl")
    ability = struct.unpack_from("<I", emotion_file, 0x64)[0]
    check(struct.unpack_from("<H", emotion_file, ability + 0x26)[0] == 352, "Emotion lost its own area")
    emotion = ie.parse_spl(emotion_file)["abilities"][0]
    rows = emotion["effects"]
    check([e["opcode"] for e in rows] == [39, 45, 232], f"Emotion rows: {rows}")
    check(rows[0]["p2"] == 0, "Hopelessness does not wake")
    check((rows[-1]["p2"], rows[-1]["resource"], rows[-1]["duration"], rows[-1]["save"], rows[-1]["special"]) ==
          (11, "CBMIWHE", 60, 1, 12), f"Emotion TookDamage condition: {rows[-1]}")
    check(effects_of(g, "CBMIWHE")[0]["resource"] == "SPWI411", "Emotion helper source")

    for spell, creatures in (("SPWI620", ("CBMWF1", "CBMWF2", "CBMWF3")), ("SPWI621", ("CBMWA1", "CBMWA2", "CBMWA3")),
                             ("SPWI622", ("CBMWE1", "CBMWE2", "CBMWE3")), ("SPWI633", ("CBMWW1", "CBMWW2", "CBMWW3"))):
        summoned = {e["resource"].upper() for e in effects_of(g, spell) if e["opcode"] == 177}
        check(summoned == set(creatures), f"{spell}: private contest creatures {summoned}")
        for name in creatures:
            eff = g.file(f"override/{name.lower()}.eff")
            check((struct.unpack_from("<I", eff, 0x10)[0], struct.unpack_from("<I", eff, 0x20)[0],
                   eff[0x30:0x38].split(b"\0", 1)[0]) == (67, 2, name.encode()), f"{name} EFF")
            check(g.file(f"override/{name.lower()}.cre")[0x248:0x250] == b"WIZELSU2", f"{name} script")
    for spell, name in (("SPWI516", "CBMWLF"), ("SPWI520", "CBMWLA"), ("SPWI521", "CBMWLE"), ("SPWI526", "CBMWLW")):
        parsed = ie.parse_spl(g.file(f"override/{spell.lower()}.spl"))
        check(len(parsed["abilities"]) == 12, f"{spell}: duration headers")
        check(all({e["resource"].upper() for e in a["effects"] if e["opcode"] == 177} == {name} and
                  {e["opcode"] for e in a["effects"]} == {165, 215, 177, 142} for a in parsed["abilities"]),
              f"{spell}: summon plus contest")
        check(g.file(f"override/{name.lower()}.cre")[0x248:0x250] == b"WIZELSUM", f"{name} script")
    taken = g.file("override/spwi633.spl")
    ability = struct.unpack_from("<I", taken, 0x64)[0]
    check(taken[0x3A:0x42] == b"SPWI633C" and taken[ability + 4:ability + 12] == b"SPWI633B", "Water keeps its icons")
    check(struct.unpack_from("<i", taken, 8)[0] == 7, "Water keeps its name")
    chant = [e["resource"] for e in effects_of(g, "SPPR203") if e["opcode"] == 146]
    check(chant == ["CBB0", "CBB1"], f"Chant's copies: {chant}")
    check(any(e["opcode"] == 22 and e["resource"] == "CBTLUCK" for e in effects_of(g, "CBB0")), "Chant's luck has no type")
    installed = g.tree()
    install(g)
    check(g.tree() == installed, "a second install changed the game")
    check("SUCCESSFULLY REMOVED" in g.uninstall(), "uninstall")
    check(g.tree() == before, "the uninstall did not give back what stood there")
