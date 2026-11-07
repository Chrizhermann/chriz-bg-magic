"""Made-up game data for the tests of the real component: the tables it reads and writes, shaped
like the base game's (BG2:EE 2.7.3.0) and written from scratch here. Nothing is copied from game
files.
"""
import json
import re
from pathlib import Path

import ie

DEFS = Path(__file__).resolve().parents[1] / "defs"
SPELL_KINDS = {"SPPR": 1000, "SPWI": 2000, "SPIN": 3000, "SPCL": 4000}

# What the installer looks up by symbol, at its base-game number. Every other spell in defs/ gets a
# made-up symbol: a real SPELL.IDS names them too, which keeps ADD_SPELL out of their slots.
SPELL_SYMBOLS = [
    (1101, "CLERIC_BLESS"), (1113, "CLERIC_DOOM"), (1202, "CLERIC_BARKSKIN"), (1203, "CLERIC_CHANT"),
    (1314, "CLERIC_UNHOLY_BLIGHT"), (1406, "CLERIC_DEFENSIVE_HARMONY"), (1412, "CLERIC_HOLY_POWER"),
    (1507, "CLERIC_CHAMPIONS_STRENGTH"), (1513, "CLERIC_RIGHTEOUS_MAGIC"), (1711, "CLERIC_REGENERATE"),
    (1730, "CLERIC_AURA_OF_FLAMING_DEATH"), (2201, "WIZARD_BLUR"), (2209, "WIZARD_LUCK"), (2305, "WIZARD_HASTE"),
    (2411, "WIZARD_EMOTION_HOPELESSNESS"), (2414, "WIZARD_SPIRIT_ARMOR"), (2603, "WIZARD_TENSERS_TRANSFORMATION"),
    (2608, "WIZARD_PIERCE_MAGIC"), (2613, "WIZARD_IMPROVED_HASTE"),
]
SPLSTATES = [(0, "CHAOTIC_COMMANDS"), (1, "BARKSKIN"), (2, "DOOM"), (3, "HOPELESSNESS"), (4, "MANTLE")]
SPLPROT_ROWS = [("0_EA>=0", ["0x10a", "0", "4"]), ("1_GENERAL=UNDEAD", ["0x10b", "4", "1"]),
                ("2_UNUSED", ["*", "*", "*"]), ("3_RACE=ELF", ["0x10c", "2", "1"]),
                ("4_STAT", ["118", "0", "3"]), ("5_STAT", ["37", "75", "4"])]
SECTYPES = [("None", "4294967296"), ("SpellProtections", "27980"), ("SpecificProtections", "27981"),
            ("IllusionaryProtections", "27982"), ("MagicAttack", "27983"), ("DivinationAttack", "27984"),
            ("Conjuration", "27986"), ("CombatProtections", "34558"), ("Contingency", "34559"),
            ("Battleground", "34560"), ("OffensiveDamage", "34561"), ("Disabling", "34562"),
            ("Combination", "34564"), ("Non-combat", "34565")]
STATDESC_ROWS = 209  # rows 0 to 208, like the base game
PROJECTILES = [(1, "Arrow"), (2, "Axe"), (3, "Bolt"), (157, "INAREAPA"), (158, "INAREA")]
TEXTS = ["", "A spell of the base game.", "Another spell's text.", "Blinded", "Stunned", "Deafened"]


def fx(**kw):
    return kw


def defs_spell_numbers():
    """{number: resref} of every spell in defs/ that stands in a slot of its own."""
    added = {t["file"].split(".")[0].upper() for t in json.loads((DEFS / "tables.json").read_text("utf-8"))["spells"].values()}
    numbers = {}
    for path in DEFS.glob("*.spl.json"):
        resref = path.name.split(".")[0].upper()
        match = re.fullmatch(r"(SP[A-Z]{2})(\d{3})", resref)
        if match and match[1] in SPELL_KINDS and resref not in added:
            numbers[SPELL_KINDS[match[1]] + int(match[2])] = resref
    return numbers


def spell_ids(extra=()):
    named = dict(SPELL_SYMBOLS)
    for number, resref in defs_spell_numbers().items():
        named.setdefault(number, f"CBMTEST_{resref}")
    return ie.make_ids(sorted({**named, **dict(extra)}.items()))


def statdesc(extra_rows=0):
    rows = [(str(row), [str(10000 + row), "SPPR313D"]) for row in range(STATDESC_ROWS + extra_rows)]
    return ie.make_2da(["DESCRIPTION", "BAM_FILE"], rows, default="****")


def msectype(extra=()):
    return ie.make_2da(["RES_REF"], [(name, [text]) for name, text in [*SECTYPES, *extra]], default="4294967296")


def projectl(extra=()):
    return ie.make_ids([*PROJECTILES, *extra])


def missile(extra=()):
    return ie.make_ids([(number + 1, name) for number, name in [*PROJECTILES, *extra]])


def game(**replace):
    """BIFF contents of a game with what the real component needs; `replace` swaps files by name,
    SPWI411_SPL for SPWI411.SPL (None removes one)."""
    files = {
        "SPELL.IDS": spell_ids(),
        "SPLSTATE.IDS": ie.make_ids(SPLSTATES),
        "SPLPROT.2DA": ie.make_2da(["STAT", "VALUE", "RELATION"], SPLPROT_ROWS),
        "STATDESC.2DA": statdesc(),
        "MSECTYPE.2DA": msectype(),
        "PROJECTL.IDS": projectl(),
        "MISSILE.IDS": missile(),
    }
    for name, data in replace.items():
        name = name.replace("_", ".")
        if data is None:
            files.pop(name, None)
        else:
            files[name] = data
    return files


def tlk(extra=()):
    return ie.make_tlk([*TEXTS, *extra])
