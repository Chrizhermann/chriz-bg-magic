"""Tests of the kept and adjusted Spell Revisions batch (cbmagic_sr.tpa) on made-up
spells shaped like the base game's, and on variations, idempotence, and invalid inputs."""
import struct

import fakegame as fg
import fixtures as fx
import ie
from harness import check, test

# Additional TLK strings for the SR batch tests (appended after fx.TEXTS).
BASE_STRREF = len(fx.TEXTS)
SR_TEXTS = [
    # +0: Invisibility
    "Invisibility\nDuration: Special\nThe creature remains invisible until 24 hours have passed.",
    # +1: Luck
    "Luck\nDuration: 3 rounds\nThe recipient is lucky for the next 3 rounds.",
    # +2: Clairvoyance (real BG2:EE 2.7.3.0 wording)
    "Clairvoyance\n(Divination)\n\nLevel: 3\nRange: Special\nDuration: Instant\nCasting Time: 3\n"
    "Area of Effect: Special\nSaving Throw: None\n\n"
    "The Clairvoyance spell empowers the wizard to see in <PRO_HISHER> mind the geographical features "
    "and buildings of the region <PRO_HESHE> is currently exploring. It extends to a great range, "
    "but cannot reveal creatures or their movements.",
    # +3: Invisibility, 10' Radius
    "Invisibility, 10' Radius\n(Illusion/Phantasm)\n\nLevel: 3\nRange: 0\nDuration: Special \n"
    "Casting Time: 9\nArea of Effect: 10-ft. radius\nSaving Throw: None \n\n"
    "This spell causes all friendly creatures within 10 ft. of the caster to vanish from sight "
    "and be undetectable by normal vision or even infravision. The spell remains in effect until "
    "it is magically broken or dispelled, until the wizard or recipient cancels it, until the "
    "recipient attacks any creature, or until 24 hours have passed.",
    # +4: Confusion
    "Confusion\nDuration: 5 rounds + 1 round/6 levels\n"
    "The spell lasts for 5 rounds plus 1 round every 6 levels of the caster.",
    # +5: Minor Sequencer
    "Minor Sequencer\n(Invocation/Evocation)\nLevel: 4",
    # +6: Teleport Field
    "Teleport Field\n(Alteration)\n\nLevel: 4\nRange: 40 ft.\nDuration: 1 turn\nCasting Time: 4\n"
    "Area of Effect: 15-ft. radius\nSaving Throw: None\n\n"
    "The wizard instigates a teleportation effect that randomly teleports all enemies in this area "
    "for the duration of the spell.",
    # +7: Oracle
    "Oracle\n(Divination)\n\nLevel: 5\nRange: 0\nDuration: Instant\nCasting Time: 5\n"
    "Area of Effect: 120-ft. radius\nSaving Throw: None\n\n"
    "When cast, this spell will cancel all Illusion/Phantasm spells of 5th level and lower within its "
    "area of effect. The spells affected are Reflected Image, Invisibility, Mirror Image, Non-Detection, "
    "Improved Invisibility, and Shadow Door.",
    # +8: Contingency
    "Contingency\n(Evocation)\nLevel: 6",
    # +9: Sphere of Chaos (real BG2:EE 2.7.3.0 wording)
    "Sphere of Chaos\n(Alteration)\n\nLevel: 7\nRange: 40 ft.\nDuration: 1 turn\nCasting Time: 7\n"
    "Area of Effect: 15-ft. radius\nSaving Throw: Special\n\n"
    "All enemies within the area of effect must make a Saving Throw vs. Spell every round that they "
    "remain in the sphere. If the Saving Throw is failed, one of the following random effects occurs:\n"
    " - target is polymorphed into a squirrel\n"
    " - target confused\n"
    " - target bursts into flames\n"
    " - target is paralyzed\n"
    " - target is disintegrated\n"
    " - target is healed 20 Hit Points\n"
    " - target is randomly teleported\n"
    " - target is rendered unconscious\n"
    " - target is hasted",
    # +10: Spell Sequencer
    "Spell Sequencer\n(Invocation/Evocation)\nLevel: 7",
    # +11: Spell Trigger
    "Spell Trigger\n(Invocation/Evocation)\nLevel: 8",
    # +12: Chain Contingency
    "Chain Contingency\n(Evocation)\nLevel: 9",
    # +13: Bless
    "Bless\nCasting Time: 9\nDuration: 6 rounds\nThis spell grants a +1 bonus to attack rolls and morale.",
    # +14: Doom (real BG2:EE 2.7.3.0 wording)
    "Doom\n(Alteration)\n\nLevel: 1\nSphere: Charm\nRange: 25 ft.\n"
    "Duration: 1 turn\nCasting Time: 9\nArea of Effect: 1 creature\nSaving Throw: None\n\n"
    "This spell causes a feeling of doom to overwhelm the target. For the duration of the spell, "
    "the target receives a -2 penalty to all <PRO_HISHER> rolls, including THAC0 and Saving Throws. "
    "There is no Saving Throw for this spell.",
    # +15: Silence 15' Radius
    "Silence 15' Radius\nSaving Throw: Neg.\n"
    "Upon casting this spell, complete silence prevails in the affected area. "
    "Each creature in the area must make a Saving Throw vs. Spell with a -5 penalty.",
    # +16: Free Action
    "Free Action\nDuration: 1 turn + 1 round/level\n"
    "While under the effects of this spell, the recipient becomes immune to anything that affects <PRO_HISHER> movement. "
    "This includes the effects of Web, Hold Person, Grease, and Entangle.",
    # +17: Neutralize Poison (real BG2:EE 2.7.3.0 wording)
    "Neutralize Poison\n(Necromancy)\n\nLevel: 4\nSphere: Healing \nRange: Touch \nDuration: Instant \n"
    "Casting Time: 1 \nArea of Effect: 1 creature \nSaving Throw: None \n\n"
    "This spell removes all toxins from the body, both natural and magical in nature. When this spell "
    "is cast upon a poisoned individual, it immediately neutralizes any poison and restores 10 lost Hit Points. "
    "This spell will also cure any diseases that the target might be suffering from, as well as blindness and deafness.",
    # +18: Holy Power
    "Holy Power\nCasting Time: 6\n"
    "Through this spell, the caster imbues himself with the strength and skill of a Fighter of the same level. "
    "The priest's Strength is set to 18/00, THAC0 becomes that of a Fighter of the same level, and the priest "
    "gains 1 temporary Hit Point per level.",
    # +19: Iron Skins name
    "Iron Skins",
    # +20: Iron Skins desc
    "Iron Skins\nCasting Time: 9\n"
    "When a druid casts this powerful spell, an outer skin of iron moves up from the ground to cover him.",
    # +21: Regenerate
    "Regenerate\nDuration: 1 round/2 levels\n"
    "This powerful spell enables the priest to imbue a creature with the ability to regenerate. "
    "Any creature touched by the priest will regenerate 3 Hit Points per second. "
    "The effect lasts for 1 round per 2 levels of the caster; for example, a 14th-level priest will "
    "regenerate 18 Hit Points per round for 7 rounds.",
    # +22: Aid
    "Aid\nDuration: 1 round + 1 round/level\n"
    "The recipient of this spell gains the benefits of a Bless spell (+1 to attack rolls and Saving Throws) "
    "and a special bonus of 1d8 additional Hit Points for the duration of the spell.",
    # +23: Holy Power name
    "Holy Power",
    # +24: Negative Plane Protection
    "Negative Plane Protection\nDuration: 5 rounds\n"
    "When this spell is cast, the recipient is protected from negative energy and level drain.",
    # +25: Greater Restoration
    "Greater Restoration\nCasting Time: 3\n"
    "When this spell is cast, the life energy level of the recipient is raised. "
    "It fully heals the target and cures any diseases or poisons.",
    # +26: Invisibility, 10' Radius name
    "Invisibility, 10' Radius",
]

INVIS_DESC = BASE_STRREF + 0
LUCK_DESC = BASE_STRREF + 1
CLAIR_DESC = BASE_STRREF + 2
INVIS10_DESC = BASE_STRREF + 3
CONF_DESC = BASE_STRREF + 4
MSEQ_DESC = BASE_STRREF + 5
TFIELD_DESC = BASE_STRREF + 6
ORACLE_DESC = BASE_STRREF + 7
CONT_DESC = BASE_STRREF + 8
CHAOS_DESC = BASE_STRREF + 9
SSEQ_DESC = BASE_STRREF + 10
STRIG_DESC = BASE_STRREF + 11
CCONT_DESC = BASE_STRREF + 12
BLESS_DESC = BASE_STRREF + 13
DOOM_DESC = BASE_STRREF + 14
SILENCE_DESC = BASE_STRREF + 15
FREEACT_DESC = BASE_STRREF + 16
NPOISON_DESC = BASE_STRREF + 17
HPOWER_DESC = BASE_STRREF + 18
IRONS_NAME = BASE_STRREF + 19
IRONS_DESC = BASE_STRREF + 20
REGEN_DESC = BASE_STRREF + 21
AID_DESC = BASE_STRREF + 22
HPOWER_NAME = BASE_STRREF + 23
NPP_DESC = BASE_STRREF + 24
GREST_DESC = BASE_STRREF + 25
INVIS10_NAME = BASE_STRREF + 26

ARCANE_SYMBOLS = [
    (2206, "WIZARD_INVISIBILITY"),
    (2209, "WIZARD_LUCK"),
    (2301, "WIZARD_CLAIRVOYANCE"),
    (2307, "WIZARD_INVISIBILITY_10_FOOT"),
    (2401, "WIZARD_CONFUSION"),
    (2420, "WIZARD_MINOR_SEQUENCER"),
    (2421, "WIZARD_TELEPORT_FIELD"),
    (2515, "WIZARD_ORACLE"),
    (2617, "WIZARD_CONTINGENCY"),
    (2710, "WIZARD_SPELL_SEQUENCER"),
    (2711, "WIZARD_SPHERE_OF_CHAOS"),
    (2809, "WIZARD_SPELL_TRIGGER"),
    (2908, "WIZARD_CHAIN_CONTINGENCY"),
]

DIVINE_SYMBOLS = [
    (1101, "CLERIC_BLESS"),
    (1110, "CLERIC_SHILLELAGH"),
    (1113, "CLERIC_DOOM"),
    (1201, "CLERIC_AID"),
    (1211, "CLERIC_SILENCE_15_FOOT"),
    (1403, "CLERIC_FREE_ACTION"),
    (1404, "CLERIC_NEUTRALIZE_POISON"),
    (1412, "CLERIC_HOLY_POWER"),
    (1413, "CLERIC_NEGATIVE_PLANE_PROTECTION"),
    (1506, "CLERIC_IRONSKIN"),
    (1711, "CLERIC_REGENERATE"),
    (1713, "CLERIC_RESTORATION"),
]


def make_spl_with_excl(excl=0, priest_excl=0, **kw):
    raw = bytearray(ie.make_spl(**kw))
    struct.pack_into("<H", raw, 0x1E, excl)
    struct.pack_into("<H", raw, 0x20, priest_excl)
    return bytes(raw)


def make_scroll_with_excl(spell, desc, u1=0x04, u3=0x80):
    raw = bytearray(ie.make_itm([[fx.fx(opcode=146, resource=spell), fx.fx(opcode=147, resource=spell)]], desc=desc))
    raw[0x2D] = u1
    raw[0x2F] = u3
    return bytes(raw)


def parse_spl_full(data):
    base = ie.parse_spl(data)
    base["flags"], = struct.unpack_from("<I", data, 0x18)
    base["excl"], = struct.unpack_from("<H", data, 0x1E)
    base["priest_excl"], = struct.unpack_from("<H", data, 0x20)
    base["school"] = data[0x25]
    base["sectype"] = data[0x27]
    base["icon"] = data[0x3A:0x42].rstrip(b"\x00").decode("latin-1")
    ab_off, = struct.unpack_from("<I", data, 0x64)
    for i, ab in enumerate(base["abilities"]):
        o = ab_off + i * 0x28
        ab["location"], = struct.unpack_from("<H", data, o + 0x02)
        ab["icon"] = data[o + 0x04:o + 0x0C].rstrip(b"\x00").decode("latin-1")
        ab["range"], ab["min_level"], ab["casting_time"] = struct.unpack_from("<HHH", data, o + 0x0E)
        ab["projectile"], = struct.unpack_from("<H", data, o + 0x26)
    return base


def sr_tlk():
    return ie.make_tlk(fx.TEXTS + SR_TEXTS)


def sr_biff(extra=None):
    base = fx.game()
    base["SPELL.IDS"] = ie.make_ids(fx.SPELL_SYMBOLS + ARCANE_SYMBOLS + DIVINE_SYMBOLS)
    base["PROJECTL.IDS"] = ie.make_ids([(158, "INAREA"), (159, "SPARBLPA"), (168, "SPARBLNP"), (189, "HOLD"), (337, "ohvrnp")])
    base["STATDESC.2DA"] = ie.make_2da(["DESCRIPTION", "BAM_FILE"], [("206", ["10554", "SPPR313D"])])
    # SPWI206 Invisibility
    base["SPWI206.SPL"] = ie.make_spl(1, 2, [{"target": 1, "effects": [
        fx.fx(opcode=20, power=2, timing=0, dispel=3, duration=7200),
        fx.fx(opcode=215, power=2, timing=1, dispel=3, resource="SPMAJINV"),
    ]}], desc=INVIS_DESC)
    base["SCRL90.ITM"] = fx.scroll("SPWI206", INVIS_DESC)
    # SPWI209 Luck
    base["SPWI209.SPL"] = ie.make_spl(1, 2, [{"target": 1, "effects": [
        fx.fx(opcode=133, power=2, p1=1, timing=0, dispel=3, duration=18),
        fx.fx(opcode=142, power=2, p2=32, timing=0, dispel=3, duration=18),
        fx.fx(opcode=174, power=2, timing=4, dispel=3, duration=18, resource="EFF_E04"),
    ]}], desc=LUCK_DESC)
    base["SCRL93.ITM"] = fx.scroll("SPWI209", LUCK_DESC)
    # SPWI301 Clairvoyance
    base["SPWI301.SPL"] = ie.make_spl(1, 3, [{"target": 5, "range": 0, "effects": [
        fx.fx(opcode=117, target=1, power=3, timing=0, duration=20),
        fx.fx(opcode=141, target=1, power=3, p2=24, timing=1),
        fx.fx(opcode=61, target=1, power=3, timing=0, duration=3),
    ]}], flags=0x2000, desc=CLAIR_DESC)
    base["SCRL1D.ITM"] = fx.scroll("SPWI301", CLAIR_DESC)
    # SPWI307 Invisibility 10' Radius
    base["SPWI307.SPL"] = ie.make_spl(1, 3, [{"target": 5, "casting_time": 9, "projectile": 159, "effects": [
        fx.fx(opcode=20, power=3, timing=0, dispel=3, duration=7200),
        fx.fx(opcode=174, power=3, timing=4, dispel=3, duration=7200, resource="EFF_E06"),
        fx.fx(opcode=141, power=3, p2=20, timing=1, dispel=3),
    ]}], name=INVIS10_NAME, desc=INVIS10_DESC)
    scrl1j = bytearray(fx.scroll("SPWI307", INVIS10_DESC))
    struct.pack_into("<ii", scrl1j, 0x08, INVIS10_NAME, INVIS10_NAME)
    base["SCRL1J.ITM"] = bytes(scrl1j)
    # SPWI401 Confusion (real BG2:EE has 4 abilities at min_level 1, 6, 12, 18)
    base["SPWI401.SPL"] = ie.make_spl(1, 4, [
        {"target": 4, "min_level": ml, "casting_time": 4, "effects": [
            fx.fx(opcode=128, power=4, timing=0, duration=dur, save=ie.SAVE_SPELL, bonus=-2),
            fx.fx(opcode=139, power=4, p1=14782, timing=1, duration=0, save=ie.SAVE_SPELL, bonus=-2),
            fx.fx(opcode=142, power=4, p2=3, timing=0, duration=dur, save=ie.SAVE_SPELL, bonus=-2),
            fx.fx(opcode=174, power=4, timing=4, duration=dur, save=ie.SAVE_SPELL, bonus=-2, resource="EFF_E05"),
        ]} for ml, dur in ((1, 30), (6, 36), (12, 42), (18, 48))
    ], desc=CONF_DESC)
    base["SCRL1U.ITM"] = fx.scroll("SPWI401", CONF_DESC)
    # Sequencers and Contingencies
    for res, desc, scrl in (
        ("SPWI420", MSEQ_DESC, "SCRL6D"),
        ("SPWI617", CONT_DESC, "SCRL7U"),
        ("SPWI710", SSEQ_DESC, "SCRL8L"),
        ("SPWI809", STRIG_DESC, "SCRL9D"),
        ("SPWI908", CCONT_DESC, "SCRL9Q"),
    ):
        base[f"{res}.SPL"] = make_spl_with_excl(
            excl=0x0800, spell_type=1, level=int(res[4]), school=6,
            abilities=[{"target": 5, "effects": [fx.fx(opcode=232, target=1, timing=0, duration=600)]}],
            desc=desc,
        )
        base[f"{scrl}.ITM"] = make_scroll_with_excl(res, desc, u1=0x04, u3=0x80)
    # SPWI421 Teleport Field (real BG2:EE has range 40)
    base["SPWI421.SPL"] = ie.make_spl(1, 4, [{"target": 4, "range": 40, "casting_time": 4, "effects": [
        fx.fx(opcode=222, power=4, p1=30, timing=1, dispel=1, save=0, bonus=0),
        fx.fx(opcode=215, power=4, p2=1, timing=0, dispel=1, duration=3, save=0, bonus=0, resource="SPDIMNDR"),
        fx.fx(opcode=174, power=4, timing=1, dispel=1, save=0, bonus=0, resource="EFF_M13"),
    ]}], desc=TFIELD_DESC)
    base["SCRL6E.ITM"] = fx.scroll("SPWI421", TFIELD_DESC)
    # SPWI515 Oracle
    base["SPWI515.SPL"] = ie.make_spl(1, 5, [{"target": 5, "range": 100, "casting_time": 3, "projectile": 159, "effects": [
        fx.fx(opcode=220, power=5, p1=5, p2=5, timing=1, dispel=3),
        fx.fx(opcode=221, power=5, p1=5, p2=3, timing=1, dispel=3),
        fx.fx(opcode=136, power=5, timing=1, dispel=3),
    ]}], desc=ORACLE_DESC)
    base["SCRL6W.ITM"] = fx.scroll("SPWI515", ORACLE_DESC)
    # SPWI711 Sphere of Chaos
    base["SPWI711.SPL"] = ie.make_spl(1, 7, [{"target": 5, "range": 40, "casting_time": 7, "projectile": 238, "effects": [
        fx.fx(opcode=141, power=7, p2=6, timing=1, dispel=1, prob1=100, prob2=0, save=ie.SAVE_SPELL, bonus=0),
        fx.fx(opcode=174, power=7, timing=1, dispel=1, prob1=100, prob2=0, save=ie.SAVE_SPELL, bonus=0, resource="EFF_M06C"),
        fx.fx(opcode=111, power=7, timing=0, dispel=1, duration=40, prob1=10, prob2=0, save=ie.SAVE_SPELL, bonus=0, resource="SQUIRP"),
        fx.fx(opcode=128, power=7, timing=0, dispel=1, duration=40, prob1=25, prob2=11, save=ie.SAVE_SPELL, bonus=0),
        fx.fx(opcode=13, power=7, p2=64, timing=1, dispel=1, prob1=60, prob2=51, save=ie.SAVE_SPELL, bonus=0),
        fx.fx(opcode=39, power=7, p2=1, timing=0, dispel=1, duration=40, prob1=90, prob2=81, save=ie.SAVE_SPELL, bonus=0),
        fx.fx(opcode=16, power=7, timing=0, dispel=1, duration=40, prob1=100, prob2=91, save=ie.SAVE_SPELL, bonus=0),
    ]}], desc=CHAOS_DESC)
    base["SCRL8M.ITM"] = fx.scroll("SPWI711", CHAOS_DESC)
    # SPPR101 Bless
    base["SPPR101.SPL"] = ie.make_spl(2, 1, [{"target": 4, "casting_time": 9, "effects": [
        fx.fx(opcode=130, power=1, p1=1, timing=0, dispel=3, duration=36),
        fx.fx(opcode=174, power=1, timing=4, dispel=3, duration=36, resource="EFF_E04"),
        fx.fx(opcode=215, power=1, p2=1, timing=0, dispel=3, duration=3, resource="ICBLESSI"),
    ]}], desc=BLESS_DESC)
    # SPPR110 Shillelagh
    base["SPPR110.SPL"] = make_spl_with_excl(
        priest_excl=0x0000, spell_type=2, level=1,
        abilities=[{"target": 5, "effects": [fx.fx(opcode=111, target=1, power=1, duration=24, resource="SHILLE")]}],
    )
    # SPPR113 Doom (real BG2:EE has leading op=321 effects before op=54)
    base["SPPR113.SPL"] = ie.make_spl(2, 1, [{"target": 1, "casting_time": 9, "effects": [
        fx.fx(opcode=321, power=1, timing=0, dispel=0, duration=0, save=0, bonus=0, resource="SPPR113"),
        fx.fx(opcode=321, power=1, timing=0, dispel=0, duration=0, save=0, bonus=0, resource="BALTH11"),
        fx.fx(opcode=321, power=1, timing=0, dispel=0, duration=0, save=0, bonus=0, resource="C2B1B"),
        fx.fx(opcode=54, power=1, p1=-2, timing=0, dispel=1, duration=60, save=0, bonus=0),
        fx.fx(opcode=33, power=1, p1=-2, timing=0, dispel=1, duration=60, save=0, bonus=0),
        fx.fx(opcode=34, power=1, p1=-2, timing=0, dispel=1, duration=60, save=0, bonus=0),
        fx.fx(opcode=35, power=1, p1=-2, timing=0, dispel=1, duration=60, save=0, bonus=0),
        fx.fx(opcode=36, power=1, p1=-2, timing=0, dispel=1, duration=60, save=0, bonus=0),
        fx.fx(opcode=37, power=1, p1=-2, timing=0, dispel=1, duration=60, save=0, bonus=0),
        fx.fx(opcode=142, power=1, p2=114, timing=0, dispel=1, duration=60, save=0, bonus=0),
    ]}], desc=DOOM_DESC)
    # SPPR201 Aid (20 abilities, min_level 1..20)
    base["SPPR201.SPL"] = make_spl_with_excl(
        priest_excl=0x8000, spell_type=2, level=2,
        abilities=[{"target": 1, "min_level": ml, "casting_time": 5, "effects": [
            fx.fx(opcode=129, power=2, p1=1, p2=0, timing=0, dispel=3, duration=6 + 6 * ml, dice=0 if ml == 1 else 1, sides=8),
            fx.fx(opcode=8, power=2, p1=-1120908544, p2=255, timing=0, dispel=3, duration=6 + 6 * ml),
            fx.fx(opcode=174, power=2, timing=4, dispel=3, duration=6 + 6 * ml, resource="EFF_E01"),
            fx.fx(opcode=215, power=2, p2=1, timing=0, dispel=3, duration=6, resource="SPHLYBLS"),
        ]} for ml in range(1, 21)],
        desc=AID_DESC,
    )
    # SPPR211 Silence 15' Radius
    base["SPPR211.SPL"] = ie.make_spl(2, 2, [{"target": 4, "casting_time": 5, "projectile": 149, "effects": [
        fx.fx(opcode=38, power=2, timing=0, dispel=1, duration=12, save=ie.SAVE_SPELL, bonus=-5),
    ]}], desc=SILENCE_DESC)
    # SPPR403 Free Action (cleric-only 0x8000, duration 60+6*lvl, blocks Haste op 101 p2=16 & op 206 SPWI305 & op 126 p1=100 p2=2)
    base["SPPR403.SPL"] = make_spl_with_excl(
        priest_excl=0x8000, spell_type=2, level=4,
        abilities=[{"target": 1, "min_level": ml, "casting_time": 5, "effects": [
            fx.fx(opcode=162, power=4, timing=1, dispel=3),
            fx.fx(opcode=126, power=4, p1=100, p2=2, timing=0, dispel=3, duration=60 + 6 * lvl),
            fx.fx(opcode=101, power=4, p2=16, timing=0, dispel=3, duration=60 + 6 * lvl),
            fx.fx(opcode=101, power=4, p2=109, timing=0, dispel=3, duration=60 + 6 * lvl),
            fx.fx(opcode=101, power=4, p2=154, timing=0, dispel=3, duration=60 + 6 * lvl),
            fx.fx(opcode=101, power=4, p2=157, timing=0, dispel=3, duration=60 + 6 * lvl),
            fx.fx(opcode=101, power=4, p2=175, timing=0, dispel=3, duration=60 + 6 * lvl),
            fx.fx(opcode=206, power=4, timing=0, dispel=3, duration=60 + 6 * lvl, resource="SPWI305"),
            fx.fx(opcode=169, power=4, p2=38, timing=0, dispel=3, duration=60 + 6 * lvl),
            fx.fx(opcode=240, power=4, p2=38, timing=1, dispel=3),
            fx.fx(opcode=267, power=4, p1=14023, timing=0, dispel=3, duration=60 + 6 * lvl),
            fx.fx(opcode=142, power=4, p2=19, timing=0, dispel=3, duration=60 + 6 * lvl),
        ]} for ml, lvl in ((1, 7), (8, 8), (20, 20))],
        desc=FREEACT_DESC,
    )
    # SPPR404 Neutralize Poison
    base["SPPR404.SPL"] = ie.make_spl(2, 4, [{"target": 1, "casting_time": 1, "effects": [
        fx.fx(opcode=321, power=4, timing=0, dispel=0, resource="SPPR419"),
        fx.fx(opcode=321, power=4, timing=0, dispel=0, resource="SPIN103"),
        fx.fx(opcode=11, power=4, timing=1, dispel=3),
        fx.fx(opcode=17, power=4, p1=10, timing=1, dispel=3),
        fx.fx(opcode=79, power=4, timing=1, dispel=3),
        fx.fx(opcode=75, power=4, timing=1, dispel=3),
        fx.fx(opcode=81, power=4, timing=1, dispel=3),
        fx.fx(opcode=240, power=4, p2=6, timing=1, dispel=3),
        fx.fx(opcode=240, power=4, p2=7, timing=1, dispel=3),
        fx.fx(opcode=240, power=4, p2=8, timing=1, dispel=3),
        fx.fx(opcode=240, power=4, p2=112, timing=1, dispel=3),
        fx.fx(opcode=61, power=4, timing=0, dispel=3, duration=3),
    ]}], desc=NPOISON_DESC)
    # SPPR412 Holy Power
    base["SPPR412.SPL"] = ie.make_spl(2, 4, [
        {"target": 5, "min_level": ml, "casting_time": 6, "effects": [
            fx.fx(opcode=44, target=1, power=4, p1=18, p2=1, timing=0, dispel=3, duration=6 * lvl),
            fx.fx(opcode=54, target=1, power=4, p1=21 - lvl, p2=1, timing=0, dispel=3, duration=6 * lvl),
            fx.fx(opcode=18, target=1, power=4, p1=lvl, p2=3, timing=0, dispel=3, duration=6 * lvl),
            fx.fx(opcode=142, target=1, power=4, p2=84, timing=0, dispel=3, duration=6 * lvl),
        ]} for ml, lvl in ((1, 7), (12, 12), (13, 13), (20, 20))
    ], name=HPOWER_NAME, desc=HPOWER_DESC)
    # SPPR413 Negative Plane Protection
    base["SPPR413.SPL"] = make_spl_with_excl(
        priest_excl=0x0000, spell_type=2, level=4,
        abilities=[{"target": 1, "min_level": 1, "casting_time": 7, "effects": [
            fx.fx(opcode=101, power=4, p2=216, timing=0, dispel=3, duration=30),
            fx.fx(opcode=142, power=4, p2=59, timing=0, dispel=3, duration=30),
            fx.fx(opcode=267, power=4, p1=41495, timing=0, dispel=3, duration=30),
            fx.fx(opcode=215, power=4, p2=1, timing=0, dispel=3, duration=3, resource="ICCSWOUI"),
            fx.fx(opcode=174, power=4, timing=4, dispel=3, duration=30, resource="EFF_E02"),
        ]}],
        desc=NPP_DESC,
    )
    # SPPR506 Iron Skins
    base["SPPR506.SPL"] = ie.make_spl(2, 5, [
        {"target": 5, "min_level": ml, "casting_time": 9, "effects": [
            fx.fx(opcode=218, target=1, power=5, p1=skins, timing=0, dispel=0, duration=7200),
            fx.fx(opcode=142, target=1, power=5, p2=80, timing=0, dispel=0, duration=7200),
        ]} for ml, skins in ((1, 4), (10, 5), (20, 10))
    ], name=IRONS_NAME, desc=IRONS_DESC)
    # SPPR711 Regenerate (usable by all priests 0x0000, 3 HP/s, 1 round/2 levels = 3*lvl)
    base["SPPR711.SPL"] = make_spl_with_excl(
        priest_excl=0x0000, spell_type=2, level=7,
        abilities=[{"target": 1, "min_level": ml, "casting_time": 7, "effects": [
            fx.fx(opcode=98, power=7, p1=3, p2=2, timing=0, dispel=3, duration=3 * lvl),
            fx.fx(opcode=142, power=7, p2=56, timing=0, dispel=3, duration=3 * lvl),
            fx.fx(opcode=174, power=7, timing=4, dispel=3, duration=3 * lvl, resource="EFF_E03"),
        ]} for ml, lvl in ((1, 14), (16, 16), (20, 20))],
        desc=REGEN_DESC,
    )
    # SPPR713 Greater Restoration
    base["SPPR713.SPL"] = ie.make_spl(2, 7, [{"target": 1, "min_level": 1, "casting_time": 3, "effects": [
        fx.fx(opcode=224, power=7, timing=1, dispel=2),
        fx.fx(opcode=17, power=7, p1=100, p2=2, timing=1, dispel=2),
        fx.fx(opcode=79, power=7, timing=1, dispel=2),
        fx.fx(opcode=11, power=7, timing=1, dispel=2),
        fx.fx(opcode=93, target=1, power=7, p1=7, timing=1, dispel=0),
    ]}], desc=GREST_DESC)
    if extra:
        base.update(extra)
    return base


@test
def kept_arcane_and_divine_spells_on_vanilla_shaped_inputs(work, weidu):
    """All 27 built arcane and divine spell changes patch the intended fields and effects,
    update spell and scroll descriptions, are idempotent on a second install, and restore
    cleanly on uninstall."""
    g = fg.FakeGame(work / "a", weidu, tlk=sr_tlk(), biff=sr_biff())
    before = g.tree()
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, f"install:\n{out}")

    # --- Arcane checks ---
    # 1. Invisibility
    s = parse_spl_full(g.file("override/SPWI206.SPL"))
    check([e["duration"] for e in s["abilities"][0]["effects"]] == [2400, 0], f"SPWI206: {s['abilities'][0]['effects']}")
    check("until 8 hours have passed" in g.tlk(s["desc"]), f"SPWI206 text: {g.tlk(s['desc'])}")
    check(g.itm_descs("SCRL90")[1] == s["desc"], "SCRL90 text")

    # 2. Luck
    s = parse_spl_full(g.file("override/SPWI209.SPL"))
    efx = s["abilities"][0]["effects"]
    check(efx[0]["opcode"] == 321 and efx[0]["resource"] == "SPWI209", f"SPWI209 refresh: {efx[0]}")
    check([e["duration"] for e in efx[1:]] == [90, 90, 90], f"SPWI209 durations: {efx[1:]}")
    check("Duration: 15 rounds" in g.tlk(s["desc"]) and "next 15 rounds" in g.tlk(s["desc"]), f"SPWI209 text: {g.tlk(s['desc'])}")

    # 3. Clairvoyance
    s = parse_spl_full(g.file("override/SPWI301.SPL"))
    check((s["flags"] & 0x2000) == 0 and s["sectype"] == 2, f"SPWI301 header: {s}")
    check([a["min_level"] for a in s["abilities"]] == [1, 7, 9, 11, 13, 15, 17, 19],
          f"SPWI301 min_levels: {[a['min_level'] for a in s['abilities']]}")
    for idx, ab in enumerate(s["abilities"]):
        dur = 18 + idx * 6
        ops = [e["opcode"] for e in ab["effects"]]
        check(ops == [321, 292, 142, 141, 61], f"SPWI301 ab {idx} ops: {ops}")
        check(ab["effects"][1]["p2"] == 1 and ab["effects"][1]["duration"] == dur and ab["effects"][1]["dispel"] == 3,
              f"SPWI301 ab {idx} op292: {ab['effects'][1]}")
    check("immune to backstab attacks" in g.tlk(s["desc"]) and "Range: Caster" in g.tlk(s["desc"]),
          f"SPWI301 text: {g.tlk(s['desc'])}")

    # 4. Invisibility Sphere (SPWI307)
    s = parse_spl_full(g.file("override/SPWI307.SPL"))
    check(g.tlk(s["name"]) == "Invisibility Sphere", f"SPWI307 name: {g.tlk(s['name'])}")
    check(s["abilities"][0]["casting_time"] == 1 and s["abilities"][0]["projectile"] > 337, f"SPWI307 ab: {s['abilities'][0]}")
    check([e["duration"] for e in s["abilities"][0]["effects"]] == [60, 60, 0], f"SPWI307 durations: {s['abilities'][0]['effects']}")
    inv10_pro = g.file("override/cbminv10.pro")
    check(inv10_pro is not None and struct.unpack_from("<HHHH", inv10_pro, 0x200) == (0xC0, 0, 110, 110), "cbminv10.pro ally-only radius 110")
    check(g.tlk(s["desc"]).startswith("Invisibility Sphere\n") and "Casting Time: 1" in g.tlk(s["desc"])
          and "until 1 turn has passed" in g.tlk(s["desc"]), f"SPWI307 text: {g.tlk(s['desc'])}")
    scrl1j_raw = g.file("override/SCRL1J.ITM")
    check(g.tlk(struct.unpack_from("<i", scrl1j_raw, 0x0C)[0]) == "Invisibility Sphere", "SCRL1J name")

    # 5. Confusion: preserves existing breakpoints (1, 6, 12, 18) and inserts 15 and 20 -> [1, 6, 12, 15, 18, 20].
    s = parse_spl_full(g.file("override/SPWI401.SPL"))
    check([a["min_level"] for a in s["abilities"]] == [1, 6, 12, 15, 18, 20],
          f"SPWI401 levels: {[a['min_level'] for a in s['abilities']]}")
    for ab, exp_dur in zip(s["abilities"], (24, 24, 24, 30, 30, 36)):
        check([e["duration"] for e in ab["effects"]] == [exp_dur, 0, exp_dur, exp_dur], f"SPWI401 ab: {ab['effects']}")
    check("Duration: 4 rounds (5 at 15th level, 6 at 20th level)" in g.tlk(s["desc"]), f"SPWI401 text: {g.tlk(s['desc'])}")

    # 6, 8, 10, 11, 12. Universal school sequencers & contingencies
    for res, scrl in (("SPWI420", "SCRL6D"), ("SPWI617", "SCRL7U"), ("SPWI710", "SCRL8L"),
                      ("SPWI809", "SCRL9D"), ("SPWI908", "SCRL9Q")):
        s = parse_spl_full(g.file(f"override/{res}.SPL"))
        check(s["school"] == 0 and (s["excl"] & 0x3FC0) == 0, f"{res} school/excl: {s}")
        check("(Universal)" in g.tlk(s["desc"]), f"{res} text: {g.tlk(s['desc'])}")
        itm = g.file(f"override/{scrl}.ITM")
        check((itm[0x2D] & 0x3F) == 0 and (itm[0x2F] & 0xC0) == 0, f"{scrl} usability: {itm[0x2D]:#x}, {itm[0x2F]:#x}")

    # 7. Teleport Field: range 30, Save vs. Spell at -4.
    s = parse_spl_full(g.file("override/SPWI421.SPL"))
    check(s["abilities"][0]["range"] == 30, f"SPWI421 range: {s['abilities'][0]['range']}")
    for e in s["abilities"][0]["effects"]:
        check(e["save"] == 1 and e["bonus"] == -4, f"SPWI421 fx: {e}")
    check("Range: 30 ft." in g.tlk(s["desc"]) and "Saving Throw: Neg." in g.tlk(s["desc"])
          and "Saving Throw vs. Spell with a -4 penalty" in g.tlk(s["desc"]), f"SPWI421 text: {g.tlk(s['desc'])}")

    # 9. Oracle: range 1, enemy-only radius-450 projectile cbmoracl.pro, level 9 illusion removal, full list in text.
    s = parse_spl_full(g.file("override/SPWI515.SPL"))
    ab = s["abilities"][0]
    check(ab["range"] == 1 and ab["projectile"] > 337, f"SPWI515 ab: {ab}")
    oracl_pro = g.file("override/cbmoracl.pro")
    check(oracl_pro is not None and struct.unpack_from("<HHHH", oracl_pro, 0x200) == (0x40, 0, 450, 450), "cbmoracl.pro enemy-only radius 450")
    check([e["p1"] for e in ab["effects"][:2]] == [9, 9], f"SPWI515 effects: {ab['effects']}")
    check("30-ft. radius" in g.tlk(s["desc"]) and "9th level and lower" in g.tlk(s["desc"])
          and "Shadow Door, Mislead, Project Image, and Mass Invisibility." in g.tlk(s["desc"]),
          f"SPWI515 text: {g.tlk(s['desc'])}")

    # 13. Sphere of Chaos
    s = parse_spl_full(g.file("override/SPWI711.SPL"))
    efx = s["abilities"][0]["effects"]
    check([e["opcode"] for e in efx[:2]] == [141, 174], f"SPWI711 hit visuals kept: {efx[:2]}")
    outcomes = [(e["opcode"], e["p2"], e["duration"], e["prob1"], e["prob2"], e["save"], e["bonus"])
                for e in efx if e["opcode"] in (76, 128, 24, 39, 175)]
    check(outcomes == [
        (76, 0, 6, 20, 0, 1, -4),
        (128, 0, 6, 40, 21, 1, -4),
        (24, 0, 6, 60, 41, 1, -4),
        (39, 0, 6, 80, 61, 1, -4),
        (175, 2, 6, 100, 81, 1, -4),
    ], f"SPWI711 outcomes: {outcomes}")
    check("save vs. Spell at -4 or suffer one of the following random effects for 1 round" in g.tlk(s["desc"]),
          f"SPWI711 text: {g.tlk(s['desc'])}")

    # --- Divine checks ---
    # 14. Bless: casting time 5, 20 abilities (levels 1..20), duration 30 + 6*lvl (36..150s), usable by clerics & druids.
    s = parse_spl_full(g.file("override/SPPR101.SPL"))
    check((s["priest_excl"] & 0xC000) == 0, f"SPPR101 priest_excl: {s['priest_excl']:#x}")
    check([a["min_level"] for a in s["abilities"]] == list(range(1, 21)), f"SPPR101 levels: {[a['min_level'] for a in s['abilities']]}")
    for idx, ab in enumerate(s["abilities"]):
        exp_dur = 30 + (idx + 1) * 6
        check(ab["casting_time"] == 5, f"SPPR101 ct: {ab['casting_time']}")
        check([e["duration"] for e in ab["effects"]] == [exp_dur, exp_dur, 3], f"SPPR101 ab {idx}: {ab['effects']}")
    check("Casting Time: 5" in g.tlk(s["desc"]) and "Duration: 5 rounds + 1 round/level (maximum 25 rounds)" in g.tlk(s["desc"]),
          f"SPPR101 text: {g.tlk(s['desc'])}")

    # 15. Shillelagh: druid-only (0x4000).
    s = parse_spl_full(g.file("override/SPPR110.SPL"))
    check(s["priest_excl"] == 0x4000, f"SPPR110 priest_excl: {s['priest_excl']:#x}")

    # 16. Doom: casting time 1, leading op=321s stay first with save=0, op=73 right after op=54, 5 abilities (1, 3, 5, 7, 9) with Save vs. Spell 0..-4.
    s = parse_spl_full(g.file("override/SPPR113.SPL"))
    check([a["min_level"] for a in s["abilities"]] == [1, 3, 5, 7, 9], f"SPPR113 levels: {[a['min_level'] for a in s['abilities']]}")
    for step, ab in enumerate(s["abilities"]):
        check(ab["casting_time"] == 1, f"SPPR113 ct: {ab['casting_time']}")
        ops = [e["opcode"] for e in ab["effects"]]
        check(ops[:5] == [321, 321, 321, 54, 73] and 0 not in ops, f"SPPR113 ops: {ops}")
        check(all(e["save"] == 0 and e["bonus"] == 0 for e in ab["effects"][:3]), f"SPPR113 321 saves: {ab['effects'][:3]}")
        check(all(e["save"] == 1 and e["bonus"] == -step for e in ab["effects"][3:]), f"SPPR113 ab {step} saves: {ab['effects'][3:]}")
    check("Saving Throw: Neg." in g.tlk(s["desc"]) and "THAC0, damage rolls, and Saving Throws" in g.tlk(s["desc"]),
          f"SPPR113 text: {g.tlk(s['desc'])}")

    # 17. Faerie Fire: added via ADD_SPELL with symbol CLERIC_CBMAGIC_FAERIE_FIRE, druid-only, hostile 0x0400, location 2, icons SPPR309C/SPPR309B, cbmffir.pro.
    ids_text = g.file("override/SPELL.IDS").decode("latin-1")
    check("CLERIC_CBMAGIC_FAERIE_FIRE" in ids_text, f"SPELL.IDS missing Faerie Fire:\n{ids_text}")
    ff_num = next(int(ln.split()[0]) for ln in ids_text.splitlines() if "CLERIC_CBMAGIC_FAERIE_FIRE" in ln)
    ff_res = f"SPPR{ff_num - 1000:03d}"
    ff_pro = g.file("override/cbmffir.pro")
    check(ff_pro is not None and struct.unpack_from("<HHHH", ff_pro, 0x200) == (0x40, 0, 75, 75), "cbmffir.pro enemy-only radius 75")
    s = parse_spl_full(g.file(f"override/{ff_res}.SPL"))
    check(s["priest_excl"] == 0x4000 and s["level"] == 1 and s["school"] == 6 and (s["flags"] & 0x0400) == 0x0400
          and s["icon"] == "SPPR309C", f"Faerie Fire header: {s}")
    ab = s["abilities"][0]
    check(ab["location"] == 2 and ab["icon"] == "SPPR309B" and ab["casting_time"] == 1
          and ab["range"] == 20 and ab["projectile"] > 337, f"Faerie Fire ab: {ab}")
    check(ab["effects"][0]["opcode"] == 136 and ab["effects"][0]["dispel"] == 2, f"Faerie Fire 136: {ab['effects'][0]}")
    check(ab["effects"][1]["opcode"] == 321 and ab["effects"][1]["resource"] == ff_res, f"Faerie Fire 321: {ab['effects'][1]}")
    check(any(e["opcode"] == 0 and e["p1"] == -2 and e["duration"] == 24 and e["save"] == 1 for e in ab["effects"]),
          f"Faerie Fire AC penalty: {ab['effects']}")
    check(any(e["opcode"] == 101 and e["p2"] == 20 and e["duration"] == 24 for e in ab["effects"]),
          f"Faerie Fire invisibility immunity: {ab['effects']}")
    check(g.tlk(s["name"]) == "Faerie Fire" and "pale violet glow" in g.tlk(s["desc"]), "Faerie Fire strings")

    # 18. Aid: op 129 replaced by op 18 (min(L,10) + 1d8 with L=max(ml,3)), duration 60*L, self-refresh op 321, STATDESC row 207 with SPPR150D.
    statdesc_text = g.file("override/STATDESC.2DA").decode("latin-1")
    check("207" in statdesc_text and "SPPR150D" in statdesc_text, f"STATDESC.2DA:\n{statdesc_text}")
    s = parse_spl_full(g.file("override/SPPR201.SPL"))
    check(len(s["abilities"]) == 20, f"SPPR201 abilities: {len(s['abilities'])}")
    for idx, ab in enumerate(s["abilities"]):
        ml = idx + 1
        eff_lvl = max(ml, 3)
        exp_hp = min(eff_lvl, 10)
        exp_dur = 60 * eff_lvl
        check(ab["effects"][0]["opcode"] == 321 and ab["effects"][0]["resource"] == "SPPR201", f"SPPR201 ab {idx} 321: {ab['effects'][0]}")
        check(not any(e["opcode"] == 129 for e in ab["effects"]), f"SPPR201 ab {idx} still has op129")
        hp_fx = [e for e in ab["effects"] if e["opcode"] == 18]
        check(len(hp_fx) == 1 and hp_fx[0]["p1"] == exp_hp and hp_fx[0]["p2"] == 0 and hp_fx[0]["duration"] == exp_dur
              and hp_fx[0]["dice"] == 1 and hp_fx[0]["sides"] == 8, f"SPPR201 ab {idx} op18: {hp_fx}")
        check(any(e["opcode"] == 142 and e["p2"] == 207 and e["duration"] == exp_dur for e in ab["effects"]),
              f"SPPR201 ab {idx} icon: {ab['effects']}")
        check(any(e["opcode"] == 215 and e["duration"] == 6 for e in ab["effects"]),
              f"SPPR201 ab {idx} SPHLYBLS duration kept: {ab['effects']}")
    check("Duration: 1 turn/level" in g.tlk(s["desc"])
          and "1d8 additional Hit Points +1 per level of the caster (up to a maximum of 1d8+10)" in g.tlk(s["desc"]),
          f"SPPR201 text: {g.tlk(s['desc'])}")

    # 19. Silence 15' Radius: projectile 169 (SPARBLNP+1).
    s = parse_spl_full(g.file("override/SPPR211.SPL"))
    check(s["abilities"][0]["projectile"] == 169, f"SPPR211 proj: {s['abilities'][0]}")
    check("Each enemy creature in the area" in g.tlk(s["desc"]), f"SPPR211 text: {g.tlk(s['desc'])}")

    # 20. Free Action: usable by druids & clerics (0x0000), 1 turn/level (420, 480, 1200), Stun immune, Haste allowed.
    s = parse_spl_full(g.file("override/SPPR403.SPL"))
    check(s["priest_excl"] == 0x0000, f"SPPR403 priest_excl: {s['priest_excl']:#x}")
    for ab, exp_dur in zip(s["abilities"], (420, 480, 1200)):
        p2s_101 = {e["p2"] for e in ab["effects"] if e["opcode"] == 101}
        check(16 not in p2s_101 and 45 in p2s_101 and 210 in p2s_101, f"SPPR403 101 p2s: {p2s_101}")
        check(not any(e["opcode"] == 206 and e["resource"] == "SPWI305" for e in ab["effects"]), "SPPR403 still blocks Haste")
        check(not any(e["opcode"] == 126 and e["p2"] == 2 for e in ab["effects"]), "SPPR403 still locks movement rate")
        check(all(e["duration"] in (0, exp_dur) for e in ab["effects"]), f"SPPR403 durations: {ab['effects']}")
    check("Duration: 1 turn/level" in g.tlk(s["desc"]) and "Slow, and Stun." in g.tlk(s["desc"]), f"SPPR403 text: {g.tlk(s['desc'])}")

    # 21. Neutralize Poison: 14 abilities (1, 8..20), cures poison (op 11) + poison immunity (op 101 p2=25) for 420..1200s, no heal/disease/blind/deaf.
    s = parse_spl_full(g.file("override/SPPR404.SPL"))
    check([a["min_level"] for a in s["abilities"]] == [1] + list(range(8, 21)),
          f"SPPR404 min_levels: {[a['min_level'] for a in s['abilities']]}")
    for idx, ab in enumerate(s["abilities"]):
        lvl = 7 + idx
        exp_dur = 60 * lvl
        ops = {e["opcode"] for e in ab["effects"]}
        check({321, 11, 101, 173, 169, 267, 142, 206}.issubset(ops), f"SPPR404 ops: {ops}")
        check(ops.isdisjoint({17, 79, 75, 81}), f"SPPR404 unwanted ops: {ops}")
        check(any(e["opcode"] == 101 and e["p2"] == 25 and e["duration"] == exp_dur for e in ab["effects"]),
              f"SPPR404 ab {idx}: {ab['effects']}")
    check("Duration: 1 turn/level" in g.tlk(s["desc"]) and "immune to poison for 1 turn per level" in g.tlk(s["desc"]),
          f"SPPR404 text: {g.tlk(s['desc'])}")

    # 22. Divine Power: renamed Divine Power in name and description, casting time 4, CBM412A/CBM412B EFFs created, op 177 added with dispel=3 for classes 3, 15, 14.
    s = parse_spl_full(g.file("override/SPPR412.SPL"))
    check(g.tlk(s["name"]) == "Divine Power", f"SPPR412 name: {g.tlk(s['name'])}")
    for ab, exp_res in zip(s["abilities"], ("CBM412A", "CBM412A", "CBM412B", "CBM412B")):
        check(ab["casting_time"] == 4, f"SPPR412 ct: {ab['casting_time']}")
        c_fx = [(e["p1"], e["p2"], e["dispel"], e["resource"]) for e in ab["effects"] if e["opcode"] == 177]
        check(c_fx == [(3, 5, 3, exp_res), (15, 5, 3, exp_res), (14, 5, 3, exp_res)], f"SPPR412 177: {c_fx}")
    eff_a = g.file("override/CBM412A.EFF")
    eff_b = g.file("override/CBM412B.EFF")
    check(eff_a is not None and struct.unpack_from("<ii", eff_a, 0x1C) == (6, 0), "CBM412A.EFF")
    check(eff_b is not None and struct.unpack_from("<ii", eff_b, 0x1C) == (1, 0), "CBM412B.EFF")
    check(g.tlk(s["desc"]).startswith("Divine Power\n") and "Casting Time: 4" in g.tlk(s["desc"])
          and "including base attacks per round at levels 7 and 13" in g.tlk(s["desc"]),
          f"SPPR412 text: {g.tlk(s['desc'])}")

    # 23. Negative Plane Protection: 14 abilities (1, 8..20), duration 60*lvl (420..1200s), usable by both clerics & druids.
    s = parse_spl_full(g.file("override/SPPR413.SPL"))
    check((s["priest_excl"] & 0xC000) == 0, f"SPPR413 priest_excl: {s['priest_excl']:#x}")
    check([a["min_level"] for a in s["abilities"]] == [1] + list(range(8, 21)),
          f"SPPR413 min_levels: {[a['min_level'] for a in s['abilities']]}")
    for idx, ab in enumerate(s["abilities"]):
        exp_dur = 60 * (7 + idx)
        check([e["duration"] for e in ab["effects"]] == [exp_dur, exp_dur, exp_dur, 3, exp_dur],
              f"SPPR413 ab {idx}: {ab['effects']}")
    check("Duration: 1 turn/level" in g.tlk(s["desc"]), f"SPPR413 text: {g.tlk(s['desc'])}")

    # 24. Iron Skins -> Stoneskin: renamed Stoneskin, casting time 1, skins & duration kept.
    s = parse_spl_full(g.file("override/SPPR506.SPL"))
    check(g.tlk(s["name"]) == "Stoneskin", f"SPPR506 name: {g.tlk(s['name'])}")
    check(all(a["casting_time"] == 1 for a in s["abilities"]), "SPPR506 casting time")
    check([a["effects"][0]["p1"] for a in s["abilities"]] == [4, 5, 10], "SPPR506 skins preserved")
    check("Stoneskin" in g.tlk(s["desc"]) and "Casting Time: 1" in g.tlk(s["desc"]) and "outer skin of stone" in g.tlk(s["desc"]),
          f"SPPR506 text: {g.tlk(s['desc'])}")

    # 25. Mass Regenerate: added via ADD_SPELL with symbol CLERIC_CBMAGIC_MASS_REGENERATE, sight-range party-only projectile cbmmreg.pro, location 2, icons SPPR711C/SPPR711B.
    check("CLERIC_CBMAGIC_MASS_REGENERATE" in ids_text, f"SPELL.IDS missing Mass Regenerate:\n{ids_text}")
    mr_num = next(int(ln.split()[0]) for ln in ids_text.splitlines() if "CLERIC_CBMAGIC_MASS_REGENERATE" in ln)
    mr_res = f"SPPR{mr_num - 1000:03d}"
    proj_ids_text = g.file("override/PROJECTL.IDS").decode("latin-1")
    check("cbmmreg" in proj_ids_text.lower(), f"PROJECTL.IDS missing cbmmreg:\n{proj_ids_text}")
    pro_raw = g.file("override/cbmmreg.pro")
    check(pro_raw is not None and len(pro_raw) == 0x300
          and struct.unpack_from("<H", pro_raw, 0x028) == (2,)
          and struct.unpack_from("<H", pro_raw, 0x100) == (0x80,)
          and pro_raw[0x11C:0x124].rstrip(b"\x00") == b"STTRAVL1"
          and struct.unpack_from("<H", pro_raw, 0x132) == (256,)
          and struct.unpack_from("<HHHH", pro_raw, 0x200) == (0xD0, 0, 452, 452)
          and struct.unpack_from("<BBBBH", pro_raw, 0x216) == (1, 255, 67, 0, 47),
          "cbmmreg.pro sight radius, ray count 0, palette offset, and party-only flags")
    s = parse_spl_full(g.file(f"override/{mr_res}.SPL"))
    check(s["priest_excl"] == 0x4000 and s["level"] == 5 and s["school"] == 8 and s["icon"] == "SPPR711C", f"Mass Regenerate header: {s}")
    check([a["min_level"] for a in s["abilities"]] == list(range(1, 11)), "Mass Regenerate min_levels")
    for idx, ab in enumerate(s["abilities"]):
        exp_dur = 72 + idx * 12
        check(ab["location"] == 2 and ab["icon"] == "SPPR711B" and ab["casting_time"] == 5 and ab["projectile"] > 337, f"Mass Regenerate ab: {ab}")
        check(ab["effects"][0]["opcode"] == 321 and ab["effects"][0]["resource"] == mr_res, f"Mass Regenerate 321: {ab['effects'][0]}")
        check(ab["effects"][1]["opcode"] == 98 and ab["effects"][1]["p1"] == 3 and ab["effects"][1]["p2"] == 3
              and ab["effects"][1]["duration"] == exp_dur, f"Mass Regenerate 98: {ab['effects'][1]}")
    check(g.tlk(s["name"]) == "Mass Regenerate" and "Area of Effect: Sight" in g.tlk(s["desc"])
          and "party members within sight" in g.tlk(s["desc"]), "Mass Regenerate strings")

    # 26. Regenerate: druid-only (0x4000), self-refresh first, 2 HP/s (p1=2), duration 6*lvl (84, 96, 120).
    s = parse_spl_full(g.file("override/SPPR711.SPL"))
    check(s["priest_excl"] == 0x4000, f"SPPR711 priest_excl: {s['priest_excl']:#x}")
    for ab, exp_dur in zip(s["abilities"], (84, 96, 120)):
        check(ab["effects"][0]["opcode"] == 321 and ab["effects"][0]["resource"] == "SPPR711", f"SPPR711 321: {ab['effects'][0]}")
        check(ab["effects"][1]["opcode"] == 98 and ab["effects"][1]["p1"] == 2 and ab["effects"][1]["duration"] == exp_dur,
              f"SPPR711 98: {ab['effects'][1]}")
        check([e["duration"] for e in ab["effects"][1:]] == [exp_dur, exp_dur, exp_dur], f"SPPR711 durs: {ab['effects']}")
    check("Duration: 1 round/level" in g.tlk(s["desc"]) and "2 Hit Points per second, and multiple castings do not stack." in g.tlk(s["desc"])
          and "12 Hit Points per round for 14 rounds" in g.tlk(s["desc"]), f"SPPR711 text: {g.tlk(s['desc'])}")

    # 27. Greater Restoration: keeps casting time 3 and fatigue op 93, adds cures with op 43 (Stone to Flesh) placed BEFORE op 17 (heal).
    s = parse_spl_full(g.file("override/SPPR713.SPL"))
    ab = s["abilities"][0]
    check(ab["casting_time"] == 3, f"SPPR713 ct: {ab['casting_time']}")
    ops_list = [e["opcode"] for e in ab["effects"]]
    ops = set(ops_list)
    check({224, 17, 79, 11, 93, 162, 46, 2, 43, 112, 321, 26, 75, 81, 240}.issubset(ops), f"SPPR713 ops: {ops}")
    check(ops_list.index(43) < ops_list.index(17), f"SPPR713 op 43 must precede op 17: {ops_list}")
    check(any(e["opcode"] == 112 and e["resource"] == "SQUIRP" for e in ab["effects"]), "SPPR713 SQUIRP removal")
    check(any(e["opcode"] == 321 and e["resource"] == "SPWI415" for e in ab["effects"]), "SPPR713 SPWI415 removal")
    check(any(e["opcode"] == 93 and e["target"] == 1 and e["p1"] == 7 for e in ab["effects"]), "SPPR713 fatigue kept")
    icons_240 = {e["p2"] for e in ab["effects"] if e["opcode"] == 240}
    check({13, 55, 14, 124, 35, 8, 112}.issubset(icons_240), f"SPPR713 op240 icons: {icons_240}")
    check("cures any diseases, poisons, blindness, deafness, curses, petrification, polymorph, hold, stun, or sleep." in g.tlk(s["desc"]),
          f"SPPR713 text: {g.tlk(s['desc'])}")

    # Second install writes nothing.
    done = {p.name.upper(): p.read_bytes() for p in (g.root / "override").iterdir()
            if p.is_file() and p.suffix.upper() in (".SPL", ".ITM", ".EFF", ".2DA", ".IDS")}
    tlk = (g.root / "lang" / g.lang / "dialog.tlk").read_bytes()
    h = fg.FakeGame(work / "b", weidu, tlk=tlk, biff=sr_biff(done))
    out2 = h.install()
    check("SUCCESSFULLY INSTALLED" in out2, f"second install:\n{out2}")
    written = sorted(p.name.upper() for p in (h.root / "override").iterdir() if p.suffix.upper() in (".SPL", ".ITM", ".EFF", ".PRO", ".2DA", ".IDS"))
    check(written == [], f"second install rewrote {written}")

    # Uninstall restores the first game.
    out_un = g.uninstall()
    check(g.tree() == before, f"uninstall left changes:\n{out_un}")


@test
def kept_spells_variations_and_broken_inputs(work, weidu):
    """Alternate layouts (casting effects after abilities, extra abilities and unrelated
    mod effects preserved, missing PROJECTL.IDS symbols falling back to default IDs) and
    corrupt/unrecognizable spells (warned and left untouched)."""
    # SPWI401 with extra_fx_first=True, casting effect op 139, an extra ability at min_level 10, and an unrelated timed mod effect (op 215 dur 12).
    conf_var = ie.make_spl(
        1, 4, [
            {"target": 4, "min_level": 1, "casting_time": 4, "effects": [
                fx.fx(opcode=128, power=4, timing=0, duration=36, save=ie.SAVE_SPELL, bonus=-2),
                fx.fx(opcode=215, power=4, timing=0, duration=12, resource="MODVIS"),
            ]},
            {"target": 4, "min_level": 10, "casting_time": 4, "effects": [
                fx.fx(opcode=128, power=4, timing=0, duration=42, save=ie.SAVE_SPELL, bonus=-2),
                fx.fx(opcode=215, power=4, timing=0, duration=12, resource="MODVIS"),
            ]},
        ],
        casting=[fx.fx(opcode=139, target=1, p1=999, timing=1)],
        extra_fx_first=True,
        desc=CONF_DESC,
    )
    # SPPR113 with an extra AC penalty op 0, an extra ability at min_level 6, and extra mod visual op 215.
    doom_var = ie.make_spl(2, 1, [
        {"target": 1, "min_level": 1, "casting_time": 9, "effects": [
            fx.fx(opcode=0, power=1, p1=-2, timing=0, duration=60),
            fx.fx(opcode=54, power=1, p1=-2, timing=0, duration=60),
            fx.fx(opcode=215, power=1, timing=1, duration=0, resource="MODDOOM"),
        ]},
        {"target": 1, "min_level": 6, "casting_time": 9, "effects": [
            fx.fx(opcode=0, power=1, p1=-2, timing=0, duration=60),
            fx.fx(opcode=54, power=1, p1=-2, timing=0, duration=60),
            fx.fx(opcode=215, power=1, timing=1, duration=0, resource="MODDOOM"),
        ]},
    ], desc=DOOM_DESC)
    # SPPR101 Bless with priest_excl=0x8000 and an unrelated timed mod effect (op 54 dur 36, same old_dur as op 130!).
    bless_var = make_spl_with_excl(
        priest_excl=0x8000, spell_type=2, level=1,
        abilities=[{"target": 4, "casting_time": 9, "effects": [
            fx.fx(opcode=130, power=1, p1=1, timing=0, dispel=3, duration=36),
            fx.fx(opcode=54, power=1, p1=2, timing=0, dispel=3, duration=36),
        ]}],
        desc=BLESS_DESC,
    )
    # SPWI711 Sphere of Chaos with an unrelated 100..0 mod effect (op 215 resource="MODCHAO").
    chaos_var = ie.make_spl(1, 7, [{"target": 5, "range": 40, "casting_time": 7, "projectile": 238, "effects": [
        fx.fx(opcode=141, power=7, p2=6, timing=1, dispel=1, prob1=100, prob2=0, save=ie.SAVE_SPELL, bonus=0),
        fx.fx(opcode=215, power=7, timing=1, dispel=1, prob1=100, prob2=0, save=0, bonus=0, resource="MODCHAO"),
        fx.fx(opcode=111, power=7, timing=0, dispel=1, duration=40, prob1=10, prob2=0, save=ie.SAVE_SPELL, bonus=0, resource="SQUIRP"),
    ]}], desc=CHAOS_DESC)
    # SPPR404 Neutralize Poison with an extra ability at min_level 5 and an unrelated mod effect (op 142 p2=99 dur 30).
    npoison_var = ie.make_spl(2, 4, [
        {"target": 1, "min_level": 1, "casting_time": 1, "effects": [
            fx.fx(opcode=11, power=4, timing=1, dispel=3),
            fx.fx(opcode=17, power=4, p1=10, timing=1, dispel=3),
            fx.fx(opcode=142, power=4, p2=99, timing=0, dispel=3, duration=30),
        ]},
        {"target": 1, "min_level": 5, "casting_time": 1, "effects": [
            fx.fx(opcode=11, power=4, timing=1, dispel=3),
            fx.fx(opcode=17, power=4, p1=10, timing=1, dispel=3),
            fx.fx(opcode=142, power=4, p2=99, timing=0, dispel=3, duration=30),
        ]},
    ], desc=NPOISON_DESC)
    # SPPR201 Aid with an extra mod visual op 215 and duplicate op 129.
    aid_var = make_spl_with_excl(
        priest_excl=0x8000, spell_type=2, level=2,
        abilities=[{"target": 1, "min_level": 1, "casting_time": 5, "effects": [
            fx.fx(opcode=129, power=2, p1=1, p2=0, timing=0, dispel=3, duration=12),
            fx.fx(opcode=129, power=2, p1=1, p2=0, timing=0, dispel=3, duration=12),
            fx.fx(opcode=215, power=2, timing=1, duration=0, resource="MODAID"),
        ]}],
        desc=AID_DESC,
    )
    # Broken SPWI206 (too short) and unrecognizable SPWI421 (no op 222).
    unrec_tfield = ie.make_spl(1, 4, [{"target": 4, "effects": [fx.fx(opcode=139, p1=1, timing=1)]}], desc=TFIELD_DESC)
    biff = sr_biff({
        "PROJECTL.IDS": ie.make_ids([]),
        "SPWI401.SPL": conf_var,
        "SPWI711.SPL": chaos_var,
        "SPPR101.SPL": bless_var,
        "SPPR113.SPL": doom_var,
        "SPPR201.SPL": aid_var,
        "SPPR404.SPL": npoison_var,
        "SPWI206.SPL": b"SPL V1  " + bytes(20),
        "SPWI421.SPL": unrec_tfield,
    })
    g = fg.FakeGame(work, weidu, tlk=sr_tlk(), biff=biff)
    out = g.install()
    check(fg.with_warnings(out), f"expected warnings:\n{out}")
    check("Invisibility (SPWI206) left as it is: shorter than an SPL header" in out, f"SPWI206 warning:\n{out}")
    check("Teleport Field (SPWI421) left as it is: no teleport field effect (opcode 222)" in out, f"SPWI421 warning:\n{out}")
    check(g.file("override/SPWI206.SPL") is None and g.file("override/SPWI421.SPL") is None, "corrupt/unrec must stay untouched")

    # Confusion variation kept casting effect, existing ability at min_level 10, and unrelated timed mod visual (dur 12).
    s = parse_spl_full(g.file("override/SPWI401.SPL"))
    check([e["opcode"] for e in s["casting"]] == [139], f"SPWI401 casting: {s['casting']}")
    check([a["min_level"] for a in s["abilities"]] == [1, 10, 15, 20], f"SPWI401 var levels: {[a['min_level'] for a in s['abilities']]}")
    for ab, exp_dur in zip(s["abilities"], (24, 24, 30, 36)):
        check([(e["opcode"], e["duration"], e["resource"]) for e in ab["effects"]] ==
              [(128, exp_dur, ""), (215, 12, "MODVIS")], f"SPWI401 var ab: {ab['effects']}")

    # Sphere of Chaos variation kept unrelated 100..0 MODCHAO effect.
    s = parse_spl_full(g.file("override/SPWI711.SPL"))
    check(any(e["opcode"] == 215 and e["resource"] == "MODCHAO" for e in s["abilities"][0]["effects"]),
          f"SPWI711 var MODCHAO kept: {s['abilities'][0]['effects']}")

    # Bless variation cleared priest_excl to 0 and preserved unrelated timed op 54 at duration 36 across all 20 abilities.
    s = parse_spl_full(g.file("override/SPPR101.SPL"))
    check(s["priest_excl"] == 0 and len(s["abilities"]) == 20, f"SPPR101 var: {s['priest_excl']}, {len(s['abilities'])}")
    check(any(e["opcode"] == 54 and e["duration"] == 36 for e in s["abilities"][19]["effects"]),
          f"SPPR101 var unrelated timed op 54 kept at 36s: {s['abilities'][19]['effects']}")

    # Neutralize Poison variation kept existing ability at min_level 5 and unrelated op 142 p2=99 dur 30.
    s = parse_spl_full(g.file("override/SPPR404.SPL"))
    check([a["min_level"] for a in s["abilities"]] == [1, 5] + list(range(8, 21)),
          f"SPPR404 var min_levels: {[a['min_level'] for a in s['abilities']]}")
    check(any(e["opcode"] == 142 and e["p2"] == 99 and e["duration"] == 30 for e in s["abilities"][1]["effects"]),
          f"SPPR404 var unrelated op 142 p2=99 kept: {s['abilities'][1]['effects']}")

    # Aid variation collapsed duplicate op 129 into single op 18 and kept MODAID.
    s = parse_spl_full(g.file("override/SPPR201.SPL"))
    ab0 = s["abilities"][0]
    check([e["opcode"] for e in ab0["effects"]] == [321, 18, 215, 142], f"SPPR201 var ops: {ab0['effects']}")
    check(ab0["effects"][2]["resource"] == "MODAID", f"SPPR201 var MODAID: {ab0['effects'][2]}")

    # Doom variation kept existing ability at min_level 6, stripped AC penalty (op 0), added damage penalty (op 73), and kept MODDOOM visual.
    s = parse_spl_full(g.file("override/SPPR113.SPL"))
    check([a["min_level"] for a in s["abilities"]] == [1, 3, 5, 6, 7, 9],
          f"SPPR113 var min_levels: {[a['min_level'] for a in s['abilities']]}")
    for ab, exp_bonus in zip(s["abilities"], (0, -1, -2, -2, -3, -4)):
        check([(e["opcode"], e["save"], e["bonus"], e["resource"]) for e in ab["effects"]] ==
              [(54, 1, exp_bonus, ""), (73, 1, exp_bonus, ""), (215, 1, exp_bonus, "MODDOOM")],
              f"SPPR113 var ab {ab['min_level']}: {ab['effects']}")

    # Fallback projectile IDs when PROJECTL.IDS is empty: Invisibility Sphere=159, Oracle=338, Silence=169, Faerie Fire=190, Mass Regenerate=337.
    check(parse_spl_full(g.file("override/SPWI307.SPL"))["abilities"][0]["projectile"] == 159, "Invisibility Sphere fallback proj")
    check(parse_spl_full(g.file("override/SPWI515.SPL"))["abilities"][0]["projectile"] == 338, "Oracle fallback proj")
    check(parse_spl_full(g.file("override/SPPR211.SPL"))["abilities"][0]["projectile"] == 169, "Silence fallback proj")
    ids_text = g.file("override/SPELL.IDS").decode("latin-1")
    ff_num = next(int(ln.split()[0]) for ln in ids_text.splitlines() if "CLERIC_CBMAGIC_FAERIE_FIRE" in ln)
    ff_res = f"SPPR{ff_num - 1000:03d}"
    check(parse_spl_full(g.file(f"override/{ff_res}.SPL"))["abilities"][0]["projectile"] == 190, "Faerie Fire fallback proj")
    mr_num = next(int(ln.split()[0]) for ln in ids_text.splitlines() if "CLERIC_CBMAGIC_MASS_REGENERATE" in ln)
    mr_res = f"SPPR{mr_num - 1000:03d}"
    check(parse_spl_full(g.file(f"override/{mr_res}.SPL"))["abilities"][0]["projectile"] == 337, "Mass Regenerate fallback proj")
