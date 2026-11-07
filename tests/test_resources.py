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


def definitions():
    """{"sppr103.spl": what defs/ says}."""
    return {path.stem.lower(): json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(fx.DEFS.glob("*.json")) if path.name != "tables.json"}


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


def defined_bytes(g, numbers, name, defn, actual):
    """The resource as defs/ defines it in this game. A string's number is free: the check is that
    the number in the file leads to the defined text."""
    data, stamps = rf.build_resource(defn)
    check(data == (RES / name).read_bytes(), f"{name}: res/ is not what defs/ builds")
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
    for name, defn in definitions().items():
        if name in derived or (name in build_resources.NEEDS_EEEX and not eeex):
            continue
        actual = g.file(f"override/{installed_name(numbers, name)}")
        check(actual is not None, f"{name} is not in override")
        expected = defined_bytes(g, numbers, name, defn, actual)
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
    built = {p.name: p.read_bytes() for p in (work / "built/res").iterdir()}
    shipped = {p.name: p.read_bytes() for p in RES.iterdir()}
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


def effects_of(g, name):
    return [e for a in ie.parse_spl(ie.Game(g.root).get(name, "SPL"))["abilities"] for e in a["effects"]]


@test
def iwd_spells_are_patched_on_top_of_what_ships(work, weidu):
    """With IWDification's spells in the game the install patches them and leaves everything that
    ships as defined. Chant's private copies come from the game's Chant, so they are the game's."""
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
                        (1550, "CLERIC_CAUSE_CRITICAL_WOUNDS_IWD"), (1525, "CLERIC_RIGHTEOUS_WRATH_OF_THE_FAITHFUL")])
    hopelessness = ie.make_spl(1, 4, [{"target": 4, "effects": [fx.fx(opcode=39, target=2, power=4, p2=1, duration=54)]}])
    biff = fx.game(
        SPELL_IDS=ids, SPWI411_SPL=hopelessness,
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
    check_every_resource(g, derived=("cbb0.spl", "cbb1.spl", "cbmbonus.2da"))

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
    check(next(e for e in effects_of(g, "SPWI411") if e["opcode"] == 39)["p2"] == 0, "Hopelessness does not wake")
    chant = [e["resource"] for e in effects_of(g, "SPPR203") if e["opcode"] == 146]
    check(chant == ["CBB0", "CBB1"], f"Chant's copies: {chant}")
    check(any(e["opcode"] == 22 and e["resource"] == "CBTLUCK" for e in effects_of(g, "CBB0")), "Chant's luck has no type")
    installed = g.tree()
    install(g)
    check(g.tree() == installed, "a second install changed the game")
    check("SUCCESSFULLY REMOVED" in g.uninstall(), "uninstall")
    check(g.tree() == before, "the uninstall did not give back what stood there")
