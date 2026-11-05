"""Made-up spells shaped like the base game's (BG2:EE 2.7.3.0) for the fix tests: the same
opcodes, parameters, saves and structure, written from scratch here. Nothing is copied
from game files.
"""
import ie

SPELL_SYMBOLS = [
    (1102, "CLERIC_COMMAND"), (1304, "CLERIC_GLYPH_OF_WARDING"), (1503, "CLERIC_FLAME_STRIKE"),
    (1512, "CLERIC_GREATER_COMMAND"), (1705, "CLERIC_FIRE_STORM"),
    (2105, "WIZARD_COLOR_SPRAY"), (2116, "WIZARD_SLEEP"), (2213, "WIZARD_STINKING_CLOUD"),
    (2215, "WIZARD_WEB"), (2220, "WIZARD_POWER_WORD_SLEEP"), (2304, "WIZARD_FIREBALL"),
    (2308, "WIZARD_LIGHTNING_BOLT"), (2313, "WIZARD_SKULL_TRAP"), (2318, "WIZARD_MINOR_SPELL_DEFLECTION"),
    (2411, "WIZARD_EMOTION_HOPELESSNESS"), (2414, "WIZARD_SPIRIT_ARMOR"), (2503, "WIZARD_CONE_OF_COLD"),
    (2523, "WIZARD_SUN_FIRE"),
    (2615, "WIZARD_CHAIN_LIGHTNING"), (2618, "WIZARD_SPELL_DEFLECTION"), (2712, "WIZARD_DELAYED_BLAST_FIREBALL"),
    (2810, "WIZARD_INCENDIARY_CLOUD"), (2911, "WIZARD_METEOR_SWARM"),
]
WEB_RACES = [(116, "SPIDER"), (118, "WYVERN"), (119, "SLIME"), (123, "BEHOLDER"), (132, "SHADOW"), (133, "SPECTRE"),
             (134, "WRAITH"), (136, "MIST"), (139, "MEPHIT"), (146, "DRAGON")]
RACES = [(1, "HUMAN"), (2, "ELF"), (142, "GIANT"), (199, "ETTIN"), *WEB_RACES]

FIRE, COLD, ELEC, MAGIC = 0x80000, 0x20000, 0x40000, 0x400000
SPELL_SAVE = ie.SAVE_SPELL | ie.BYPASS_MIRROR

# TLK: 0 empty, then the descriptions the fixes may touch.
TEXTS = [
    "",
    "Minor Spell Deflection\n\nThis spell affects a total of 4 spell levels. This spell will only affect up to "
    "7th-level spells, but if it tries to absorb a spell that goes over its limit, the spell will fail.",
    "Web\n\nAnyone in the area when the spell is cast must roll a Saving Throw vs. Spell with a -2 penalty. "
    "A failed Saving Throw means the creature is stuck (100% of the time, 'quoted' and \"double\").",
    "Delayed Blast Fireball\n\nVictims are allowed a Saving Throw vs. Spell for half damage.",
    "Fireball\n\nThose who roll successful Saving Throws manage to dodge, fall flat, or roll aside, each "
    "receiving half.",
    "Glyph of Warding\n\nA successful Saving Throw vs. Spell enables the creature to escape the effects of the glyph.",
    "Incendiary Cloud\n\n1d4 points of fire damage per level of the caster each round, with a Save vs. Spell for half.",
    "Spirit Armor\n\n+3 bonus to Save vs. Spell. Unless the creature makes a Saving Throw vs. Spell.",
    "Sleep\n\nCreatures must make a Saving Throw vs. Death with a -3 penalty or fall asleep. 100% sure.",
]
MSD_DESC, WEB_DESC, DBF_DESC, FIREBALL_DESC, GLYPH_DESC, ICLOUD_DESC, SPIRIT_DESC, SLEEP_DESC = range(1, 9)


def fx(**kw):
    return kw


def damage(kind, dice, save=SPELL_SAVE, half=True, level=3):
    return fx(opcode=12, target=2, power=level, p2=kind, timing=1, dice=dice, sides=6, save=save,
              special=0x100 if half else 0)


def by_level(levels, make):
    return [{"target": 4, "min_level": lvl, "effects": make(lvl)} for lvl in levels]


def spirit_armor():
    def effects(_):
        return [fx(opcode=0, power=4, p1=1, p2=16, duration=600, dispel=3),
                fx(opcode=142, power=4, p2=46, duration=600, dispel=3),
                fx(opcode=37, power=4, p1=3, duration=600, dispel=3),
                fx(opcode=148, power=4, p1=1, p2=1, timing=4, duration=600, resource="SPWI414A", dispel=3)]
    return ie.make_spl(1, 4, [{"target": 1, "effects": effects(1)}], desc=SPIRIT_DESC)


def minor_spell_deflection(levels=range(1, 8), resource_on=1, abilities=(1, 6, 7)):
    def effects(lvl):
        out = []
        for p2 in levels:
            out.append(fx(opcode=201, target=1, power=3, p1=4, p2=p2, duration=18 * lvl, dispel=2,
                          resource="SPWI318B" if p2 == resource_on else ""))
            if p2 == 1:
                out.append(fx(opcode=328, target=1, power=3, p2=66, duration=18 * lvl, dispel=2, special=1))
        out.append(fx(opcode=139, target=1, power=3, p1=10882, timing=1, dispel=2))
        return out
    return ie.make_spl(1, 3, [{"target": 5, "min_level": lvl, "effects": effects(lvl)} for lvl in abilities],
                       desc=MSD_DESC)


def save_spells():
    """The nine spells of the save rule, plus Sunfire's payload and the spells that keep
    their saves."""
    out = {
        "SPWI304.SPL": ie.make_spl(1, 3, by_level([1, 6, 10], lambda lvl: [damage(FIRE, min(lvl, 10))]),
                                   casting=[fx(opcode=265, target=1, p1=1, timing=1, resource="mgArea1")],
                                   desc=FIREBALL_DESC),
        "SPWI712.SPL": ie.make_spl(1, 7, by_level([1], lambda lvl: [damage(FIRE, 15, level=7)]), desc=DBF_DESC),
        "SPWI523.SPL": ie.make_spl(1, 5, [{"target": 5, "effects": [
            fx(opcode=148, target=1, p2=1, timing=1, resource="spwi523d"),
            fx(opcode=146, target=1, p2=1, timing=1, resource="SPWI900")]}]),
        "SPWI523D.SPL": ie.make_spl(1, 5, by_level([1, 15], lambda lvl: [
            fx(opcode=318, target=2, power=5, p2=43, resource="spwi523d"),
            damage(FIRE, min(lvl, 15), save=SPELL_SAVE | (0x2000000 if lvl == 15 else 0), level=5)])),
        "SPWI900.SPL": ie.make_spl(1, 5, by_level([1], lambda lvl: [damage(FIRE, 3, level=5)])),
        "SPWI503.SPL": ie.make_spl(1, 5, by_level([1, 20], lambda lvl: [damage(COLD, lvl, level=5)])),
        "SPPR503.SPL": ie.make_spl(2, 5, [{"target": 1, "effects": [damage(FIRE, 9, save=ie.SAVE_SPELL, level=5),
                                                                     fx(opcode=215, target=2, power=5, timing=1,
                                                                        resource="SPFLMSTR")]}]),
        "SPWI313.SPL": ie.make_spl(1, 3, by_level([1, 20], lambda lvl: [damage(MAGIC, lvl)])),
        "SPPR304.SPL": ie.make_spl(2, 3, by_level([1, 18], lambda lvl: [damage(ELEC, lvl, half=False)]), desc=GLYPH_DESC),
        "SPWI810.SPL": ie.make_spl(1, 8, by_level([1, 20], lambda lvl: [damage(FIRE, 16, level=8)]), desc=ICLOUD_DESC),
        "SPWI308.SPL": ie.make_spl(1, 3, [{"target": 1, "effects": [
            fx(opcode=318, target=1, timing=10, duration=2, resource="SPWI308"), damage(ELEC, 5)]}]),
        # Not part of the rule: Chain Lightning keeps Spell; Meteor Swarm and Fire Storm have no save.
        "SPWI615.SPL": ie.make_spl(1, 6, [{"target": 1, "effects": [damage(ELEC, 6, level=6)]}]),
        "SPWI911.SPL": ie.make_spl(1, 9, by_level([1], lambda lvl: [damage(FIRE, 4, save=ie.BYPASS_MIRROR, half=False,
                                                                           level=9)])),
        "SPPR705.SPL": ie.make_spl(2, 7, by_level([1], lambda lvl: [damage(FIRE, 2, save=ie.BYPASS_MIRROR, half=False,
                                                                           level=7)])),
    }
    return out


def sleep_spells():
    def sleep_effects(_):
        return [fx(opcode=324, power=1, p2=19, prob1=30, resource="spwi116", dispel=2),
                fx(opcode=39, power=1, p2=1, duration=30, dice=4, save=0x4, bonus=-3, special=14),
                fx(opcode=139, power=1, p1=14001, timing=1, dice=4, save=0x4, bonus=-3)]
    return {
        "SPWI116.SPL": ie.make_spl(1, 1, by_level([1, 2, 20], sleep_effects), desc=SLEEP_DESC),
        "SPWI105.SPL": ie.make_spl(1, 1, by_level([1], lambda lvl: [
            fx(opcode=39, power=1, p2=1, duration=30, dice=4, save=ie.SAVE_SPELL, special=14),
            fx(opcode=165, target=1, power=1, duration=1)])),
        "SPWI213.SPL": ie.make_spl(1, 2, by_level([1], lambda lvl: [
            fx(opcode=39, power=2, p2=1, duration=9, save=0x4, bonus=2, special=14),
            fx(opcode=142, power=2, p2=126, duration=9, save=0x4, bonus=2)])),
        "SPWI220.SPL": ie.make_spl(1, 2, [{"target": 1, "effects": [
            fx(opcode=324, power=2, p1=20, p2=144, resource="SPWI220"),
            fx(opcode=217, power=2, timing=1)]}]),
        # Command: one sleep without a save up to 5 Hit Dice, one with a save from 6 on.
        "SPPR102.SPL": ie.make_spl(2, 1, [{"target": 1, "effects": [
            fx(opcode=324, power=1, p2=19, prob1=30, resource="SPPR102"),
            fx(opcode=39, power=1, p2=1, duration=6, dice=5),
            fx(opcode=215, power=1, timing=1, resource="SPCOMSTT"),
            fx(opcode=39, power=1, p2=1, duration=6, sides=6, save=ie.SAVE_SPELL),
            fx(opcode=174, power=1, timing=4, duration=6, resource="EFF_E05")]}]),
        "SPPR512.SPL": ie.make_spl(2, 5, [{"target": 1, "min_level": lvl, "effects": [
            fx(opcode=324, power=5, p2=19, prob1=30, duration=1, resource="SPPR512"),
            fx(opcode=39, power=5, p2=1, duration=6 * lvl, save=ie.SAVE_SPELL),
            fx(opcode=174, power=5, timing=4, duration=6 * lvl, save=ie.SAVE_SPELL, resource="EFF_E07")]}
            for lvl in (1, 10, 20)]),
        "SPWI411.SPL": ie.make_spl(1, 4, by_level([1, 8, 20], lambda lvl: [
            fx(opcode=321, power=4, timing=1, resource="SPWI205"),
            fx(opcode=142, power=4, p2=37, duration=54),
            fx(opcode=39, power=4, p2=1, duration=54, save=ie.SAVE_SPELL),
            fx(opcode=101, power=4, p2=24, duration=54)])),
    }


def web():
    def effects(_):
        common = dict(power=2, save=ie.SAVE_SPELL, bonus=-2)
        return [fx(opcode=157, duration=7, **common), fx(opcode=109, p2=2, duration=7, **common),
                fx(opcode=142, p2=129, duration=7, **common), fx(opcode=139, p1=14102, timing=1, **common),
                # an effect with a save of its own (made up): it keeps its save vs. spell
                fx(opcode=12, power=2, p2=MAGIC, timing=1, dice=1, sides=4, save=ie.SAVE_SPELL, bonus=0)]
    return ie.make_spl(1, 2, by_level([1], effects), desc=WEB_DESC)


SPLPROT_ROWS = [("0_EA>=0", ["0x10a", "0", "4"]), ("1_GENERAL=UNDEAD", ["0x10b", "4", "1"]),
                ("2_UNUSED", ["*", "*", "*"]), ("3_RACE=ELF", ["0x10c", "2", "1"]),
                ("4_RACE=n", ["0x10c", "-1", "1"]), ("5_RACE!=n", ["0x10c", "-1", "5"])]


def scroll(spell, desc):
    return ie.make_itm([[fx(opcode=146, target=1, p2=1, timing=1, resource=spell)],
                        [fx(opcode=147, target=1, timing=1, resource=spell)]], desc=desc)


def game(splprot=SPLPROT_ROWS, **replace):
    """BIFF contents of a game with every spell the fixes touch; `replace` swaps files
    (None removes one)."""
    files = {
        "SPELL.IDS": ie.make_ids(SPELL_SYMBOLS),
        "RACE.IDS": ie.make_ids(RACES),
        "SPLPROT.2DA": ie.make_2da(["STAT", "VALUE", "RELATION"], splprot),
        "SPWI414.SPL": spirit_armor(),
        "SPWI318.SPL": minor_spell_deflection(),
        "SPWI215.SPL": web(),
        "SCRL6G.ITM": scroll("SPWI318", MSD_DESC),
        "SCRL99.ITM": scroll("SPWI215", WEB_DESC),
        "SCRL8N.ITM": scroll("SPWI712", DBF_DESC),
        "SCRL1G.ITM": scroll("SPWI304", FIREBALL_DESC),
        "SCRL5K.ITM": scroll("SPWI414", SPIRIT_DESC),
        "SWORD.ITM": ie.make_itm([[fx(opcode=146, resource="SPWI215")]], desc=WEB_DESC, item_type=20),
        **save_spells(),
        **sleep_spells(),
    }
    for k, v in replace.items():
        k = k.replace("_", ".")
        if v is None:
            files.pop(k, None)
        else:
            files[k] = v
    return files


def tlk():
    return ie.make_tlk(TEXTS)
