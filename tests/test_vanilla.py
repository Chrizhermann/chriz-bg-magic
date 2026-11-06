"""Tests for chriz-bg-magic/lib/cbmagic_vanilla.tpa in synthetic games."""

import struct

import fakegame as fg
import fixtures as fx
import ie
from harness import check, test

ie.TYPES.setdefault("PRO", 0x3FD)

# --- Synthetic descriptions matching vanilla English sentences ----------------------------

FIND_FAMILIAR_DESC = (
    "Find Familiar\n"
    "(Conjuration/Summoning)\n\n"
    "Level: 1\n"
    "Range: n/a\n"
    "Duration: Permanent"
)

BLINDNESS_DESC = (
    "Blindness\n"
    "(Illusion/Phantasm)\n\n"
    "Level: 1\n"
    "Range: Visual range of the caster\n"
    "Duration: 2 hours\n"
    "Casting Time: 2\n"
    "Area of Effect: 1 creature\n"
    "Saving Throw: Neg.\n\n"
    "This 1st-level spell temporarily blinds its target."
)

CLOUDKILL_DESC = (
    "Cloudkill\n"
    "(Evocation)\n\n"
    "Level: 5\n"
    "Range: 40 ft.\n"
    "Duration: 1 turn"
)

DEATH_FOG_DESC = (
    "Death Fog\n"
    "(Evocation)\n\n"
    "Level: 6\n"
    "Range: 30 ft.\n"
    "Duration: 1 turn"
)

WIZ_FOD_DESC = (
    "Finger of Death\n"
    "(Necromancy)\n\n"
    "Level: 7\n"
    "Saving Throw: Neg.\n\n"
    "Finger of Death snuffs out a victim's life force. If a Save vs. Spell is made with a -2 penalty, "
    "the victim instead takes 2d8+1 points of damage."
)

PRI_FOD_DESC = (
    "Finger of Death\n"
    "(Necromancy)\n\n"
    "Level: 7\n"
    "Sphere: Necromantic\n"
    "Saving Throw: Neg.\n\n"
    "The target dies instantly unless it saves vs. Spell with a -2 penalty."
)

ENTANGLE_DESC = (
    "Entangle\n"
    "(Alteration)\n\n"
    "Level: 1\n"
    "Sphere: Plant\n"
    "Saving Throw: Special\n\n"
    "A creature that rolls a successful save vs. Spell with a +3 bonus can move."
)

FLAME_BLADE_DESC = (
    "Flame Blade\n"
    "(Evocation)\n\n"
    "Level: 2\n"
    "Sphere: Elemental (Fire)\n\n"
    "With this spell, the caster causes a blazing ray of red-hot fire to spring forth from his hand. "
    "However, it is not a magical weapon in the normal sense of the term, so creatures struck only "
    "by magical weapons are not harmed by it."
)

WIZ_ELEM_DESC = (
    "Conjure Fire Elemental\n"
    "(Conjuration/Summoning)\n\n"
    "Level: 6\n\n"
    "There is a 60% chance that a 12-Hit-Dice elemental appears, a 35% chance that a 16-Hit-Dice "
    "elemental appears, and a 5% chance that a 24-Hit-Dice elemental appears."
)

PRI_FIRE_ELEM_DESC = (
    "Conjure Fire Elemental\n"
    "(Conjuration/Summoning)\n\n"
    "Level: 6\n"
    "Sphere: Elemental (Fire)\n\n"
    "There is a 60% chance that a 12-Hit-Dice elemental appears; a 35% chance that a 16-Hit-Dice "
    "elemental appears; and a 5% chance that a 24-Hit-Dice elemental appears."
)

PRI_EARTH_ELEM_DESC = (
    "Conjure Earth Elemental\n"
    "(Conjuration/Summoning)\n\n"
    "Level: 7\n"
    "Sphere: Elemental (Earth)\n\n"
    "There is a 60% chance that a 12-Hit-Dice elemental appears, a 35% chance that a 16-Hit-Dice "
    "elemental appears, and a 5% chance that a 24-Hit-Dice elemental appears."
)

GREASE_DESC = (
    "Grease\n"
    "(Conjuration)\n\n"
    "Level: 1\n\n"
    "Any creature entering the area or caught in it when the spell is cast must save vs. Spell at +2 or slip."
)

STINKING_CLOUD_VANILLA_DESC = (
    "Stinking Cloud\n"
    "(Evocation)\n\n"
    "Level: 2\n\n"
    "Any creature caught within the cloud must roll a successful Save vs. Poison at +2 or be rendered unconscious."
)

WEB_VANILLA_DESC = (
    "Web\n"
    "(Evocation)\n\n"
    "Level: 2\n\n"
    "Anyone caught within the webs must make a Save vs. Spell at -2 or be held fast."
)

INCENDIARY_CLOUD_VANILLA_DESC = (
    "Incendiary Cloud\n"
    "(Evocation)\n\n"
    "Level: 8\n\n"
    "Deals 1d4 fire damage per level (Save vs. Spell for half)."
)

PW_SLEEP_DESC = (
    "Power Word, Sleep\n"
    "(Conjuration/Summoning)\n\n"
    "Level: 2\n\n"
    "Puts a creature with 20 or fewer hit points to sleep."
)

MAGIC_RES_FULL_DESC = (
    "Magic Resistance\n"
    "(Abjuration)\n\n"
    "Level: 5\n"
    "Casting Time: 9\n"
    "Duration: 3 rounds + 1 round/level\n\n"
    "Upon casting this spell, the recipient receives a resistance to all magic of 2% per level of the priest "
    "(for example, 30% at 15th level) up to a maximum of 40% at 20th level. This resistance is set so that "
    "if the target already has more Magic Resistance than the priest would confer, it will actually lower it "
    "to the set value. This effect lasts for the duration of the spell or until dispelled."
)

STRENGTH_OF_ONE_DESC = (
    "Strength of One\n"
    "(Alteration)\n\n"
    "Level: 3\n\n"
    "When this spell is cast, the party receives a boon to their physical power, effectively setting "
    "everyone's Strength score to 18/75. If a party member has a Strength score higher than this "
    "(either naturally, or through a magical item), then <PRO_HISHER> Strength is lowered to 18/75."
)

MINOR_SEQ_DESC = "Minor Sequencer\n(Invocation/Evocation)\n\nLevel: 4\n"
CONTINGENCY_DESC = "Contingency\n(Evocation)\n\nLevel: 6\n"
SPELL_SEQ_DESC = "Spell Sequencer\n(Invocation/Evocation)\n\nLevel: 7\n"
SPELL_TRIG_DESC = "Spell Trigger\n(Invocation/Evocation)\n\nLevel: 8\n"
CHAIN_CONT_DESC = "Chain Contingency\n(Evocation)\n\nLevel: 9\n"


def _ct_desc(name, ct):
    return f"{name}\n\nLevel: 5\nCasting Time: {ct}\nDuration: 1 turn\n"


VANILLA_TEXTS = [
    *fx.TEXTS,
    FIND_FAMILIAR_DESC,
    BLINDNESS_DESC,
    CLOUDKILL_DESC,
    DEATH_FOG_DESC,
    WIZ_FOD_DESC,
    PRI_FOD_DESC,
    ENTANGLE_DESC,
    FLAME_BLADE_DESC,
    WIZ_ELEM_DESC,
    PRI_FIRE_ELEM_DESC,
    PRI_EARTH_ELEM_DESC,
    _ct_desc("Bless", 9),
    _ct_desc("Flame Strike", 8),
    _ct_desc("Heal", 9),
    _ct_desc("Blade Barrier", 9),
    _ct_desc("Bolt of Glory", 9),
    MAGIC_RES_FULL_DESC,
    _ct_desc("Righteous Magic", 9),
    _ct_desc("True Seeing", 8),
    _ct_desc("True Sight", 8),
    _ct_desc("Glyph of Warding", 9) + "\nA successful Saving Throw vs. Spell enables the creature to escape.",
    _ct_desc("Invisibility Purge", 8),
    _ct_desc("Strength", 9),
    _ct_desc("Fire Seeds", 9),
    GREASE_DESC,
    STINKING_CLOUD_VANILLA_DESC,
    WEB_VANILLA_DESC,
    INCENDIARY_CLOUD_VANILLA_DESC,
    PW_SLEEP_DESC,
    STRENGTH_OF_ONE_DESC,
    MINOR_SEQ_DESC,
    CONTINGENCY_DESC,
    SPELL_SEQ_DESC,
    SPELL_TRIG_DESC,
    CHAIN_CONT_DESC,
]
(
    FF_DESC,
    BLIND_DESC,
    CK_DESC,
    DF_DESC,
    WFOD_DESC,
    PFOD_DESC,
    ENT_DESC,
    FB_DESC,
    WELEM_DESC,
    PFELEM_DESC,
    PEELEM_DESC,
    BLESS_DESC,
    FSTRIKE_DESC,
    HEAL_DESC,
    BBARRIER_DESC,
    BGLORY_DESC,
    MR_DESC,
    RM_DESC,
    PTS_DESC,
    WTS_DESC,
    GLYPH_CT_DESC,
    IP_DESC,
    STR_DESC,
    FSEEDS_DESC,
    GR_DESC,
    SC_VAN_DESC,
    WEB_VAN_DESC,
    IC_VAN_DESC,
    PWS_DESC,
    SOO_DESC,
    MSEQ_DESC,
    CONT_DESC,
    SSEQ_DESC,
    STRIG_DESC,
    CCONT_DESC,
) = range(len(fx.TEXTS), len(VANILLA_TEXTS))

VANILLA_SPELL_SYMBOLS = [
    *fx.SPELL_SYMBOLS,
    (1101, "CLERIC_BLESS"),
    (1105, "CLERIC_ENTANGLE"),
    (1202, "CLERIC_BARKSKIN"),
    (1206, "CLERIC_FLAME_BLADE"),
    (1303, "CLERIC_DISPEL_MAGIC"),
    (1309, "CLERIC_INVISIBILITY_PURGE"),
    (1312, "CLERIC_STRENGTH_OF_ONE"),
    (1402, "CLERIC_ANIMAL_SUMMONING_1"),
    (1501, "CLERIC_ANIMAL_SUMMONING_2"),
    (1505, "CLERIC_TRUE_SIGHT"),
    (1509, "CLERIC_MAGIC_RESISTANCE"),
    (1513, "CLERIC_RIGHTEOUS_MAGIC"),
    (1602, "CLERIC_ANIMAL_SUMMONING_3"),
    (1603, "CLERIC_BLADE_BARRIER"),
    (1604, "CLERIC_CONJURE_ANIMALS"),
    (1605, "CLERIC_CONJURE_FIRE_ELEMENTAL"),
    (1606, "CLERIC_FIRE_SEEDS"),
    (1607, "CLERIC_HEAL"),
    (1612, "CLERIC_BOLT_OF_GLORY"),
    (1702, "CLERIC_CONJURE_EARTH_ELEMENTAL"),
    (1708, "CLERIC_FINGER_OF_DEATH"),
    (2101, "WIZARD_GREASE"),
    (2106, "WIZARD_BLINDNESS"),
    (2120, "WIZARD_REFLECTED_IMAGE"),
    (2123, "WIZARD_FIND_FAMILIAR"),
    (2125, "WIZARD_SPOOK"),
    (2205, "WIZARD_HORROR"),
    (2212, "WIZARD_MIRROR_IMAGE"),
    (2214, "WIZARD_STRENGTH"),
    (2220, "WIZARD_POWER_WORD_SLEEP"),
    (2298, "CONTINGENCY_MIRROR_IMAGE"),
    (2302, "WIZARD_REMOVE_MAGIC"),
    (2326, "WIZARD_TRUE_DISPEL_MAGIC"),
    (2420, "WIZARD_MINOR_SEQUENCER"),
    (2502, "WIZARD_CLOUDKILL"),
    (2609, "WIZARD_TRUE_SIGHT"),
    (2614, "WIZARD_DEATH_FOG"),
    (2616, "WIZARD_DISINTEGRATE"),
    (2617, "WIZARD_CONTINGENCY"),
    (2620, "WIZARD_CONJURE_FIRE_ELEMENTAL"),
    (2621, "WIZARD_CONJURE_AIR_ELEMENTAL"),
    (2622, "WIZARD_CONJURE_EARTH_ELEMENTAL"),
    (2710, "WIZARD_SPELL_SEQUENCER"),
    (2713, "WIZARD_FINGER_OF_DEATH"),
    (2809, "WIZARD_SPELL_TRIGGER"),
    (2908, "WIZARD_CHAIN_CONTINGENCY"),
    (2919, "WIZARD_WISH"),
    (4231, "INQUIS_DISPEL_MAGIC"),
]

VANILLA_RACES = [*fx.RACES, (144, "GOLEM"), (145, "ELEMENTAL"), (201, "SWORD")]


def _spl_with_hdr(
    *,
    spell_type=1,
    level=1,
    school=0,
    excl_1e=0,
    priest_20=0,
    desc=-1,
    abilities=(),
):
    raw = bytearray(ie.make_spl(spell_type=spell_type, level=level, school=school, desc=desc, abilities=abilities))
    struct.pack_into("<H", raw, 0x1E, excl_1e)
    struct.pack_into("<H", raw, 0x20, priest_20)
    return bytes(raw)


def _read_spl_ext(g: fg.FakeGame, resref: str):
    raw = g.file(f"override/{resref}.SPL")
    parsed = ie.parse_spl(raw)
    parsed["school"] = raw[0x25]
    parsed["excl_1e"] = struct.unpack_from("<H", raw, 0x1E)[0]
    parsed["priest_20"] = struct.unpack_from("<H", raw, 0x20)[0]
    ab_off = struct.unpack_from("<I", raw, 0x64)[0]
    for idx, ab in enumerate(parsed["abilities"]):
        ab["casting_time"] = struct.unpack_from("<H", raw, ab_off + idx * 0x28 + 0x12)[0]
    return parsed


def _make_elem_spl(*, min_levels, spell_type=1, level=6, desc=-1):
    abilities = []
    for ml in min_levels:
        effects = [
            dict(opcode=165, target=1, timing=0, duration=18, prob1=100, prob2=0),
            dict(opcode=177, target=1, timing=0, duration=60, prob1=60, prob2=0, resource="ELEM12A"),
            dict(opcode=177, target=1, timing=0, duration=60, prob1=60, prob2=0, resource="ELEM12B"),
            dict(opcode=177, target=1, timing=0, duration=60, prob1=95, prob2=61, resource="ELEM16A"),
            dict(opcode=177, target=1, timing=0, duration=60, prob1=100, prob2=96, resource="ELEM24A"),
        ]
        abilities.append(dict(min_level=ml, casting_time=9, effects=effects))
    return _spl_with_hdr(spell_type=spell_type, school=2, excl_1e=0x0100, level=level, desc=desc, abilities=abilities)


def _make_fblade_itm(*, flags=0x28, enchantment=0):
    raw = bytearray(ie.make_itm(abilities=[[]]))
    struct.pack_into("<I", raw, 0x18, flags)
    struct.pack_into("<I", raw, 0x60, enchantment)
    return bytes(raw)


def _make_pro(pro_type: int) -> bytes:
    buf = bytearray(0x200)
    buf[0:8] = b"PRO V1.0"
    struct.pack_into("<H", buf, 0x08, pro_type)
    return bytes(buf)


def _spl_with_pro(*, school=6, excl_1e=0x0040, level=1, pro=1, effects=()):
    raw = bytearray(_spl_with_hdr(school=school, excl_1e=excl_1e, level=level, abilities=[dict(min_level=1, effects=effects)]))
    ab_off = struct.unpack_from("<I", raw, 0x64)[0]
    struct.pack_into("<H", raw, ab_off + 0x26, pro)
    return bytes(raw)


def _itm_with_pro(*, pro=1, ab_flags_26=0, effects=()):
    raw = bytearray(ie.make_itm(abilities=[effects]))
    ab_off = struct.unpack_from("<I", raw, 0x64)[0]
    struct.pack_into("<H", raw, ab_off + 0x26, ab_flags_26)
    struct.pack_into("<H", raw, ab_off + 0x2A, pro)
    return bytes(raw)


def _vanilla_biff(**replace):
    files = {
        **fx.game(),
        "SPELL.IDS": ie.make_ids(VANILLA_SPELL_SYMBOLS),
        "RACE.IDS": ie.make_ids(VANILLA_RACES),
        "PROJECTL.IDS": ie.make_ids([(39, "AOETEST"), (40, "RAYTEST")]),
        "AOETEST.PRO": _make_pro(3),
        "RAYTEST.PRO": _make_pro(2),
        # 1. Find Familiar (SPWI123) + scroll
        "SPWI123.SPL": _spl_with_hdr(
            school=2,
            excl_1e=0x0100,
            level=1,
            desc=FF_DESC,
            abilities=[dict(min_level=1, effects=[dict(opcode=192, target=1)])],
        ),
        "SCRL6D.ITM": fx.scroll("SPWI123", FF_DESC),
        # 2. Blindness (SPWI106) + scroll
        "SPWI106.SPL": _spl_with_hdr(
            school=5,
            excl_1e=0x0400,
            level=1,
            desc=BLIND_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=2,
                    effects=[
                        dict(opcode=74, target=2, timing=0, duration=600, save=1),
                        dict(opcode=139, target=2, timing=1, duration=0, p1=14674, save=1),
                        dict(opcode=142, target=2, timing=0, duration=600, p2=8, save=1),
                    ],
                )
            ],
        ),
        "SCRL71.ITM": fx.scroll("SPWI106", BLIND_DESC),
        # 3. Cloudkill (SPWI502) + scroll
        "SPWI502.SPL": _spl_with_hdr(
            school=6,
            excl_1e=0x0040,
            level=5,
            desc=CK_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=5,
                    effects=[
                        dict(opcode=25, duration=60, save=4),
                        dict(opcode=12, p1=10, save=4),
                    ],
                )
            ],
        ),
        "SCRL2E.ITM": fx.scroll("SPWI502", CK_DESC),
        # 4. Death Fog (SPWI614) + scroll
        "SPWI614.SPL": _spl_with_hdr(
            school=6,
            excl_1e=0x0040,
            level=6,
            desc=DF_DESC,
            abilities=[dict(min_level=1, casting_time=6, effects=[dict(opcode=12, p1=8)])],
        ),
        "SCRL7T.ITM": fx.scroll("SPWI614", DF_DESC),
        # 5. Wizard Finger of Death (SPWI713) + scroll (SCRL8P so we don't collide with SCRL8N DBF)
        "SPWI713.SPL": _spl_with_hdr(
            school=7,
            excl_1e=0x0800,
            level=7,
            desc=WFOD_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=5,
                    effects=[
                        dict(opcode=55, target=2, timing=1, save=1, bonus=-2),
                        dict(opcode=215, target=2, timing=0, duration=2, save=1, bonus=-2, resource="SPFLAYER"),
                        dict(opcode=12, target=2, timing=1, dice=2, sides=8, p1=1, save=0, bonus=0),
                    ],
                )
            ],
        ),
        "SCRL8P.ITM": fx.scroll("SPWI713", WFOD_DESC),
        # 6. Priest Finger of Death (SPPR708)
        "SPPR708.SPL": _spl_with_hdr(
            spell_type=2,
            school=7,
            level=7,
            desc=PFOD_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=5,
                    effects=[
                        dict(opcode=55, target=2, timing=1, save=1, bonus=-2),
                        dict(opcode=215, target=2, timing=0, duration=2, save=1, bonus=-2, resource="SPFLAYER"),
                        dict(opcode=12, target=2, timing=1, dice=2, sides=8, p1=1, save=0, bonus=0),
                    ],
                )
            ],
        ),
        # 7. Disintegrate (SPWI616)
        "SPWI616.SPL": _spl_with_hdr(
            school=8,
            level=6,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=6,
                    effects=[
                        dict(opcode=215, target=2, timing=1, resource="SPHOLY"),
                        dict(opcode=238, target=2, timing=1, save=1, special=1),
                    ],
                )
            ],
        ),
        # 8. Wish (SPWI919)
        "SPWI919.SPL": _spl_with_hdr(
            school=2,
            excl_1e=0x0100,
            level=9,
            abilities=[dict(min_level=1, casting_time=9, effects=[dict(opcode=310, target=1)])],
        ),
        # 9. Entangle (SPPR105)
        "SPPR105.SPL": _spl_with_hdr(
            spell_type=2,
            school=8,
            level=1,
            desc=ENT_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=4,
                    effects=[
                        dict(opcode=154, target=2, duration=60, save=1, bonus=3),
                        dict(opcode=126, target=2, duration=60, save=1, bonus=3),
                        dict(opcode=142, target=2, duration=60, p2=144, save=1, bonus=3),
                    ],
                )
            ],
        ),
        # 10. Flame Blade (SPPR206 + FBLADE.ITM)
        "SPPR206.SPL": _spl_with_hdr(
            spell_type=2,
            school=6,
            priest_20=0,
            level=2,
            desc=FB_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=4,
                    effects=[dict(opcode=111, target=1, duration=24, resource="FBLADE")],
                )
            ],
        ),
        "FBLADE.ITM": _make_fblade_itm(flags=0x28, enchantment=0),
        # 11-13. Wizard Elemental Summoning (SPWI620, SPWI621, SPWI622) + scroll
        "SPWI620.SPL": _make_elem_spl(min_levels=list(range(12, 21)), spell_type=1, level=6, desc=WELEM_DESC),
        "SPWI621.SPL": _make_elem_spl(min_levels=list(range(12, 21)), spell_type=1, level=6, desc=WELEM_DESC),
        "SPWI622.SPL": _make_elem_spl(min_levels=list(range(12, 21)), spell_type=1, level=6, desc=WELEM_DESC),
        "SCRL7X.ITM": fx.scroll("SPWI620", WELEM_DESC),
        # 14-15. Priest Elemental Summoning (SPPR605, SPPR702)
        "SPPR605.SPL": _make_elem_spl(min_levels=list(range(11, 21)), spell_type=2, level=6, desc=PFELEM_DESC),
        "SPPR702.SPL": _make_elem_spl(min_levels=[1] + list(range(12, 21)), spell_type=2, level=7, desc=PEELEM_DESC),
        # 16-20. Druid-only priest spells
        "SPPR202.SPL": _spl_with_hdr(
            spell_type=2, level=2, abilities=[dict(min_level=1, casting_time=5, effects=[dict(opcode=0, target=1)])]
        ),
        "SPPR402.SPL": _spl_with_hdr(
            spell_type=2, level=4, abilities=[dict(min_level=1, casting_time=7, effects=[dict(opcode=177, target=1)])]
        ),
        "SPPR501.SPL": _spl_with_hdr(
            spell_type=2, level=5, abilities=[dict(min_level=1, casting_time=8, effects=[dict(opcode=177, target=1)])]
        ),
        "SPPR602.SPL": _spl_with_hdr(
            spell_type=2, level=6, abilities=[dict(min_level=1, casting_time=9, effects=[dict(opcode=177, target=1)])]
        ),
        "SPPR604.SPL": _spl_with_hdr(
            spell_type=2, level=6, abilities=[dict(min_level=1, casting_time=9, effects=[dict(opcode=177, target=1)])]
        ),
        # Row A. Grease (SPWI101) + scroll
        "SPWI101.SPL": _spl_with_hdr(
            school=2,
            excl_1e=0x0100,
            level=1,
            desc=GR_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=1,
                    effects=[
                        dict(opcode=158, target=2, duration=6, save=1, bonus=2),
                        dict(opcode=126, target=2, duration=6, save=1, bonus=2),
                        dict(opcode=142, target=2, duration=6, p2=145, save=1, bonus=2),
                    ],
                )
            ],
        ),
        "SCRL66.ITM": fx.scroll("SPWI101", GR_DESC),
        # Row B. Stinking Cloud (SPWI213) + scroll (with real school=6 so vanilla batch patches it)
        "SPWI213.SPL": _spl_with_hdr(
            school=6,
            excl_1e=0x0040,
            level=2,
            desc=SC_VAN_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=2,
                    effects=[
                        dict(opcode=39, target=2, power=2, p2=1, duration=12, save=4, bonus=2),
                        dict(opcode=142, target=2, power=2, p2=126, duration=12, save=4, bonus=2),
                    ],
                )
            ],
        ),
        "SCRL97.ITM": fx.scroll("SPWI213", SC_VAN_DESC),
        # Row C1. Web (SPWI215) + scroll (with real school=6)
        "SPWI215.SPL": _spl_with_hdr(
            school=6,
            excl_1e=0x0040,
            level=2,
            desc=WEB_VAN_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=2,
                    effects=[
                        dict(opcode=157, target=2, power=2, duration=6, save=1, bonus=-2),
                        dict(opcode=109, target=2, power=2, p2=2, duration=6, save=1, bonus=-2),
                    ],
                )
            ],
        ),
        "SCRL99.ITM": fx.scroll("SPWI215", WEB_VAN_DESC),
        # Row C2. Incendiary Cloud (SPWI810) + scroll (with real school=6)
        "SPWI810.SPL": _spl_with_hdr(
            school=6,
            excl_1e=0x0040,
            level=8,
            desc=IC_VAN_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=8,
                    effects=[fx.damage(fx.FIRE, 4)],
                )
            ],
        ),
        "SCRL9E.ITM": fx.scroll("SPWI810", IC_VAN_DESC),
        # Row D. Power Word, Sleep (SPWI220) (with real school=2)
        "SPWI220.SPL": _spl_with_hdr(
            school=2,
            excl_1e=0x0100,
            level=2,
            desc=PWS_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=1,
                    effects=[
                        dict(opcode=324, target=2, power=2, p1=20, p2=144, resource="SPWI220"),
                        dict(opcode=217, target=2, power=2, p2=1, duration=30),
                        dict(opcode=142, target=2, power=2, p2=14, duration=30),
                    ],
                )
            ],
        ),
        # Row E. Spook (SPWI125)
        "SPWI125.SPL": _spl_with_hdr(
            school=5,
            excl_1e=0x0400,
            level=1,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=1,
                    effects=[dict(opcode=24, target=2, power=1, duration=18, save=1)],
                )
            ],
        ),
        # Row F. Horror (SPWI205)
        "SPWI205.SPL": _spl_with_hdr(
            school=7,
            excl_1e=0x0800,
            level=2,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=2,
                    effects=[dict(opcode=24, target=2, power=2, duration=60, save=1)],
                )
            ],
        ),
        # Row G. Reflected Image (SPWI120), Mirror Image (SPWI212), Contingency Mirror Image (SPWI298)
        "SPWI120.SPL": _spl_with_hdr(
            school=5,
            excl_1e=0x0400,
            level=1,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=1,
                    effects=[dict(opcode=119, target=1, power=1, duration=24, resist_dispel=3)],
                )
            ],
        ),
        "SPWI212.SPL": _spl_with_hdr(
            school=5,
            excl_1e=0x0400,
            level=2,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=2,
                    effects=[dict(opcode=119, target=1, power=2, duration=36, resist_dispel=3)],
                ),
                dict(
                    min_level=6,
                    casting_time=2,
                    effects=[dict(opcode=119, target=1, power=2, duration=54, resist_dispel=3)],
                ),
            ],
        ),
        "SPWI298.SPL": _spl_with_hdr(
            school=5,
            excl_1e=0x0400,
            level=2,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=0,
                    effects=[dict(opcode=119, target=1, power=2, duration=120, resist_dispel=3)],
                )
            ],
        ),
        # Row H. AoE damage vs Mirror Image test fixtures (pro 40 = AOETEST, pro 41 = RAYTEST)
        "SPPR609.SPL": _spl_with_pro(
            pro=40,
            effects=[dict(opcode=12, target=2, dice=6, sides=6, save=0)],
        ),
        "SPPR411.SPL": _spl_with_pro(
            pro=41,
            effects=[dict(opcode=12, target=2, dice=4, sides=6, save=0)],
        ),
        "WAND05.ITM": _itm_with_pro(
            pro=40,
            effects=[dict(opcode=12, target=2, dice=6, sides=6, save=1)],
        ),
        "SW1H51.ITM": _itm_with_pro(
            pro=1,
            ab_flags_26=40,  # ability flags at 0x26 must not be mistaken for projectile index
            effects=[dict(opcode=12, target=2, dice=1, sides=10, save=0)],
        ),
        # Row I. Dispel Magic test fixtures (SPWI302, SPWI326, SPPR303, SPCL231)
        "SPWI302.SPL": _spl_with_hdr(
            school=1,
            level=3,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=3,
                    effects=[
                        dict(opcode=58, target=2, p1=0, p2=1),
                        dict(opcode=112, target=2),
                    ],
                )
            ],
        ),
        "SPWI326.SPL": _spl_with_hdr(
            school=1,
            level=3,
            abilities=[dict(min_level=1, casting_time=3, effects=[dict(opcode=58, target=2, p1=0, p2=0x20001)])],
        ),
        "SPPR303.SPL": _spl_with_hdr(
            spell_type=2,
            school=1,
            level=3,
            abilities=[dict(min_level=1, casting_time=3, effects=[dict(opcode=58, target=2, p1=0, p2=0x20001)])],
        ),
        "SPCL231.SPL": _spl_with_hdr(
            spell_type=4,
            school=1,
            level=3,
            abilities=[dict(min_level=1, casting_time=1, effects=[dict(opcode=58, target=2, p1=0, p2=0x20002)])],
        ),
        # Row K. Strength of One (SPPR312)
        "SPPR312.SPL": _spl_with_hdr(
            spell_type=2,
            school=8,
            level=3,
            desc=SOO_DESC,
            abilities=[
                dict(
                    min_level=1,
                    casting_time=3,
                    effects=[
                        dict(opcode=44, target=2, power=3, p1=18, p2=1, duration=72, resist_dispel=3),
                        dict(opcode=97, target=2, power=3, p1=75, p2=1, duration=72, resist_dispel=3),
                        dict(opcode=141, target=2, power=3, p2=16, timing=1, resist_dispel=3),
                        dict(opcode=142, target=2, power=3, p2=21, duration=72, resist_dispel=3),
                        dict(opcode=174, target=2, power=3, timing=4, duration=72, resist_dispel=3, resource="EFF_M08"),
                        dict(opcode=139, target=2, power=3, p1=14041, timing=1, resist_dispel=3),
                    ],
                )
            ],
        ),
        # Row L. Sequencers and Contingencies (SPWI420, SPWI617, SPWI710, SPWI809, SPWI908)
        "SPWI420.SPL": _spl_with_hdr(
            school=6, excl_1e=0x0040, level=4, desc=MSEQ_DESC, abilities=[dict(min_level=1, effects=[dict(opcode=256, target=1)])]
        ),
        "SPWI617.SPL": _spl_with_hdr(
            school=6, excl_1e=0x0040, level=6, desc=CONT_DESC, abilities=[dict(min_level=1, effects=[dict(opcode=232, target=1)])]
        ),
        "SPWI710.SPL": _spl_with_hdr(
            school=6, excl_1e=0x0040, level=7, desc=SSEQ_DESC, abilities=[dict(min_level=1, effects=[dict(opcode=256, target=1)])]
        ),
        "SPWI809.SPL": _spl_with_hdr(
            school=6, excl_1e=0x0040, level=8, desc=STRIG_DESC, abilities=[dict(min_level=1, effects=[dict(opcode=256, target=1)])]
        ),
        "SPWI908.SPL": _spl_with_hdr(
            school=6, excl_1e=0x0040, level=9, desc=CCONT_DESC, abilities=[dict(min_level=1, effects=[dict(opcode=232, target=1)])]
        ),
    }

    ct_fixtures = [
        ("SPPR503", 2, 5, 8, FSTRIKE_DESC, [fx.damage(fx.FIRE, 8)]),
        ("SPPR607", 2, 6, 9, HEAL_DESC, [dict(opcode=17, target=2)]),
        ("SPPR603", 2, 6, 9, BBARRIER_DESC, [dict(opcode=177, target=1)]),
        ("SPPR612", 2, 6, 9, BGLORY_DESC, [dict(opcode=12, target=2)]),
        ("SPPR509", 2, 5, 9, MR_DESC, [dict(opcode=166, target=2, p1=20, p2=1, duration=150)]),
        ("SPPR513", 2, 5, 9, RM_DESC, [dict(opcode=132, target=1)]),
        ("SPPR505", 2, 5, 8, PTS_DESC, [dict(opcode=193, target=1)]),
        ("SPWI609", 1, 6, 8, WTS_DESC, [dict(opcode=193, target=1)]),
        ("SPPR304", 2, 3, 9, GLYPH_CT_DESC, [fx.damage(fx.ELEC, 3)]),
        ("SPPR309", 2, 3, 8, IP_DESC, [dict(opcode=116, target=2)]),
        ("SPWI214", 1, 2, 9, STR_DESC, [dict(opcode=44, target=2)]),
        ("SPPR606", 2, 6, 9, FSEEDS_DESC, [dict(opcode=122, target=1)]),
    ]
    for res, stype, lvl, ct, dref, fxs in ct_fixtures:
        files[f"{res}.SPL"] = _spl_with_hdr(
            spell_type=stype,
            level=lvl,
            desc=dref,
            abilities=[
                dict(min_level=1, casting_time=ct, effects=fxs),
                dict(min_level=10, casting_time=ct, effects=fxs),
            ],
        )

    for k, v in replace.items():
        k = k.replace("_", ".")
        if v is None:
            files.pop(k, None)
        else:
            files[k] = v
    return files


def _fresh_vanilla(work, weidu, replace=None, **kw):
    return fg.FakeGame(
        work,
        weidu,
        tlk=kw.pop("tlk", ie.make_tlk(VANILLA_TEXTS)),
        biff=_vanilla_biff(**(replace or {})),
        **kw,
    )


@test
def vanilla_batch_on_vanilla_shaped_spells(work, weidu):
    """Every cbmagic_vanilla_* function applies its decided change, updates descriptions,
    and uninstalls cleanly."""
    g = _fresh_vanilla(work, weidu)
    before = g.tree()
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, f"install:\n{out}")

    # 1. Find Familiar (SPWI123): Universal school (0), exclusions 0, text updated
    s = _read_spl_ext(g, "SPWI123")
    check(s["school"] == 0 and s["excl_1e"] == 0, f"SPWI123 school/excl: {s}")
    check(s["desc"] != FF_DESC and "(Universal)" in g.tlk(s["desc"]), f"SPWI123 desc: {g.tlk(s['desc'])}")
    check(g.tlk(FF_DESC) == FIND_FAMILIAR_DESC, "shared FF_DESC strref must not be overwritten")
    _, scrl_id = g.itm_descs("SCRL6D")
    check("(Universal)" in g.tlk(scrl_id), f"SCRL6D desc: {g.tlk(scrl_id)}")

    # 2. Blindness (SPWI106): 4 abilities at 1/6/8/10 with durations 12/18/24/30s
    s = _read_spl_ext(g, "SPWI106")
    check([a["min_level"] for a in s["abilities"]] == [1, 6, 8, 10], f"SPWI106 min_levels: {s['abilities']}")
    for a, expected_dur in zip(s["abilities"], [12, 18, 24, 30]):
        durs = {f["opcode"]: f["duration"] for f in a["effects"]}
        check(durs[74] == expected_dur and durs[142] == expected_dur and durs[139] == 0, f"SPWI106 durs: {durs}")
    check(
        "Duration: 1 round/2 levels (2 to 5 rounds)" in g.tlk(s["desc"]),
        f"SPWI106 desc: {g.tlk(s['desc'])}",
    )
    _, scrl_id = g.itm_descs("SCRL71")
    check(
        "Duration: 1 round/2 levels (2 to 5 rounds)" in g.tlk(scrl_id),
        f"SCRL71 desc: {g.tlk(scrl_id)}",
    )

    # 3-4. Cloudkill (SPWI502) and Death Fog (SPWI614): school 2 (Conjuration), excl 0x0100 (Diviner)
    for res, scrl in [("SPWI502", "SCRL2E"), ("SPWI614", "SCRL7T")]:
        s = _read_spl_ext(g, res)
        check(s["school"] == 2 and s["excl_1e"] == 0x0100, f"{res} school/excl: {s}")
        check("(Conjuration/Summoning)" in g.tlk(s["desc"]), f"{res} desc: {g.tlk(s['desc'])}")
        _, scrl_id = g.itm_descs(scrl)
        check("(Conjuration/Summoning)" in g.tlk(scrl_id), f"{scrl} desc: {g.tlk(scrl_id)}")

    # 5-6. Wizard & Priest Finger of Death (SPWI713, SPPR708): save vs. Death (4) with bonus 0
    for res in ("SPWI713", "SPPR708"):
        s = _read_spl_ext(g, res)
        fx_by_op = {f["opcode"]: f for f in s["abilities"][0]["effects"]}
        check(fx_by_op[55]["save"] == 4 and fx_by_op[55]["bonus"] == 0, f"{res} op55: {fx_by_op[55]}")
        check(fx_by_op[215]["save"] == 4 and fx_by_op[215]["bonus"] == 0, f"{res} op215: {fx_by_op[215]}")
        check(fx_by_op[12]["save"] == 0 and fx_by_op[12]["bonus"] == 0, f"{res} op12: {fx_by_op[12]}")
        check("vs. Death" in g.tlk(s["desc"]), f"{res} desc: {g.tlk(s['desc'])}")
    _, scrl_id = g.itm_descs("SCRL8P")
    check("Save vs. Death is made" in g.tlk(scrl_id), f"SCRL8P desc: {g.tlk(scrl_id)}")

    # 7. Disintegrate (SPWI616): destroys Mordenkainen's Sword (RACE=201) via DESTSELF + op318 before op238
    s = _read_spl_ext(g, "SPWI616")
    effs = s["abilities"][0]["effects"]
    ops = [f["opcode"] for f in effs]
    check(ops.index(177) < ops.index(238) and ops.index(318) < ops.index(238), f"SPWI616 ops: {ops}")
    eff177 = [f for f in effs if f["opcode"] == 177][0]
    eff318 = [f for f in effs if f["opcode"] == 318][0]
    check(
        eff177["p1"] == 201 and eff177["p2"] == 4 and eff177["resource"] == "DESTSELF",
        f"SPWI616 op177: {eff177}",
    )
    check(eff177["save"] == 0 and eff177["bonus"] == 0, f"SPWI616 op177 save: {eff177}")
    check(
        eff318["p1"] == 201 and eff318["p2"] == 4 and eff318["resource"] == "SPWI616",
        f"SPWI616 op318: {eff318}",
    )

    # 8. Wish (SPWI919): school Universal (0), exclusions 0
    s = _read_spl_ext(g, "SPWI919")
    check(s["school"] == 0 and s["excl_1e"] == 0, f"SPWI919 school/excl: {s}")

    # 9. Entangle (SPPR105): save vs. Breath (2) with +3 bonus kept, plus 11 race immunities
    s = _read_spl_ext(g, "SPPR105")
    effs = s["abilities"][0]["effects"]
    ent_fxs = [f for f in effs if f["opcode"] in (154, 126, 142)]
    check(all(f["save"] == 2 and f["bonus"] == 3 for f in ent_fxs), f"SPPR105 saves: {ent_fxs}")
    imm_races = [f["p1"] for f in effs if f["opcode"] == 324 and f["p2"] == 4]
    expected_ent_races = [
        dict((sym, num) for num, sym in VANILLA_RACES)[r]
        for r in ("WYVERN", "BEHOLDER", "MEPHIT", "SPECTRE", "WRAITH", "SHADOW", "MIST", "ELEMENTAL", "GIANT", "ETTIN", "DRAGON")
    ]
    check(imm_races == list(reversed(expected_ent_races)), f"SPPR105 immunities: {imm_races} vs {expected_ent_races}")
    check("save vs. Breath with a +3 bonus" in g.tlk(s["desc"]), f"SPPR105 desc: {g.tlk(s['desc'])}")

    # 10. Flame Blade (SPPR206 + FBLADE.ITM): druid-only (0x4000 at 0x20) + magical +1 weapon
    s = _read_spl_ext(g, "SPPR206")
    check(s["priest_20"] == 0x4000, f"SPPR206 priest_20: {hex(s['priest_20'])}")
    check("treated as a magical weapon" in g.tlk(s["desc"]), f"SPPR206 desc: {g.tlk(s['desc'])}")
    fb_raw = g.file("override/FBLADE.ITM")
    fb_flags = struct.unpack_from("<I", fb_raw, 0x18)[0]
    fb_ench = struct.unpack_from("<I", fb_raw, 0x60)[0]
    check((fb_flags & 0x40) == 0x40 and fb_ench == 1, f"FBLADE flags={hex(fb_flags)} ench={fb_ench}")

    # 11-13. Wizard Elemental Summoning (SPWI620, SPWI621, SPWI622)
    expected_wiz = {
        12: [(0, 63), (64, 98), (99, 100)],
        16: [(0, 59), (60, 94), (95, 100)],
        20: [(0, 55), (56, 90), (91, 100)],
    }
    for res in ("SPWI620", "SPWI621", "SPWI622"):
        s = _read_spl_ext(g, res)
        by_ml = {a["min_level"]: a for a in s["abilities"]}
        for ml, windows in expected_wiz.items():
            effs = by_ml[ml]["effects"]
            check((effs[0]["prob2"], effs[0]["prob1"]) == (0, 100), f"{res} self-fx: {effs[0]}")
            tiers = [
                (effs[1]["prob2"], effs[1]["prob1"]),
                (effs[3]["prob2"], effs[3]["prob1"]),
                (effs[4]["prob2"], effs[4]["prob1"]),
            ]
            check(tiers == windows, f"{res} L{ml} tiers: {tiers}")
        check("56% / 35% / 9% at 20th level" in g.tlk(s["desc"]), f"{res} desc: {g.tlk(s['desc'])}")
    _, scrl_id = g.itm_descs("SCRL7X")
    check("56% / 35% / 9% at 20th level" in g.tlk(scrl_id), f"SCRL7X desc: {g.tlk(scrl_id)}")

    # 14-15. Priest Elemental Summoning (SPPR605, SPPR702)
    expected_pri = {
        0: [(0, 63), (64, 98), (99, 100)],  # L11: 64/35/1
        1: [(0, 60), (61, 97), (98, 100)],  # L12: 61/37/2
        4: [(0, 51), (52, 93), (94, 100)],  # L15: 52/42/6
        9: [(0, 36), (37, 87), (88, 100)],  # L20: 37/51/12
    }
    for res in ("SPPR605", "SPPR702"):
        s = _read_spl_ext(g, res)
        for idx, windows in expected_pri.items():
            effs = s["abilities"][idx]["effects"]
            tiers = [
                (effs[1]["prob2"], effs[1]["prob1"]),
                (effs[3]["prob2"], effs[3]["prob1"]),
                (effs[4]["prob2"], effs[4]["prob1"]),
            ]
            check(tiers == windows, f"{res} idx={idx} tiers: {tiers}")
        check("37% / 51% / 12% at 20th level" in g.tlk(s["desc"]), f"{res} desc: {g.tlk(s['desc'])}")

    # 16-20. Druid-only priest spells (SPPR202, SPPR402, SPPR501, SPPR602, SPPR604)
    for res in ("SPPR202", "SPPR402", "SPPR501", "SPPR602", "SPPR604"):
        s = _read_spl_ext(g, res)
        check(s["priest_20"] == 0x4000, f"{res} priest_20: {hex(s['priest_20'])}")

    # 21-33. Casting times and descriptions (including Invisibility Purge=3 and Fire Seeds=6)
    expected_cts = [
        ("SPPR503", 5),
        ("SPPR607", 6),
        ("SPPR603", 6),
        ("SPPR612", 6),
        ("SPPR509", 5),
        ("SPPR513", 5),
        ("SPPR505", 6),
        ("SPWI609", 6),
        ("SPPR304", 5),
        ("SPPR309", 3),
        ("SPWI214", 5),
        ("SPPR606", 6),
    ]
    for res, target_ct in expected_cts:
        s = _read_spl_ext(g, res)
        check([a["casting_time"] for a in s["abilities"]] == [target_ct, target_ct], f"{res} ct: {s['abilities']}")
        check(f"Casting Time: {target_ct}" in g.tlk(s["desc"]), f"{res} desc: {g.tlk(s['desc'])}")

    race_num = dict((sym, num) for num, sym in VANILLA_RACES)

    # Row A. Grease (SPWI101): save vs. Breath (2) with +2 bonus kept, 8 race immunities, text + scroll
    s = _read_spl_ext(g, "SPWI101")
    effs = s["abilities"][0]["effects"]
    gr_fxs = [f for f in effs if f["opcode"] in (158, 126, 142)]
    check(all(f["save"] == 2 and f["bonus"] == 2 for f in gr_fxs), f"SPWI101 saves: {gr_fxs}")
    imm_races = [f["p1"] for f in effs if f["opcode"] == 324 and f["p2"] == 4]
    expected_gr_races = [race_num[r] for r in ("WYVERN", "BEHOLDER", "MEPHIT", "SPECTRE", "WRAITH", "SHADOW", "MIST", "DRAGON")]
    check(imm_races == list(reversed(expected_gr_races)), f"SPWI101 immunities: {imm_races}")
    check("save vs. Breath at +2" in g.tlk(s["desc"]), f"SPWI101 desc: {g.tlk(s['desc'])}")
    _, scrl_id = g.itm_descs("SCRL66")
    check("save vs. Breath at +2" in g.tlk(scrl_id), f"SCRL66 desc: {g.tlk(scrl_id)}")

    # Row B. Stinking Cloud (SPWI213): school Conjuration (2, excl 0x0100), undead (row 1) + GOLEM/ELEMENTAL/SLIME immune, text + scroll
    s = _read_spl_ext(g, "SPWI213")
    check(s["school"] == 2 and s["excl_1e"] == 0x0100, f"SPWI213 school/excl: {s}")
    effs = s["abilities"][0]["effects"]
    check(any(f["opcode"] == 324 and f["p2"] == 1 and f["p1"] == 0 for f in effs), f"SPWI213 undead imm: {effs}")
    sc_races = {f["p1"] for f in effs if f["opcode"] == 324 and f["p2"] == 4}
    check({race_num["GOLEM"], race_num["ELEMENTAL"], race_num["SLIME"]}.issubset(sc_races), f"SPWI213 races: {sc_races}")
    check("(Conjuration/Summoning)" in g.tlk(s["desc"]), f"SPWI213 desc: {g.tlk(s['desc'])}")
    _, scrl_id = g.itm_descs("SCRL97")
    check("(Conjuration/Summoning)" in g.tlk(scrl_id), f"SCRL97 desc: {g.tlk(scrl_id)}")

    # Row C. Web (SPWI215) and Incendiary Cloud (SPWI810): school Conjuration (2, excl 0x0100), text + scroll
    for res, scrl in [("SPWI215", "SCRL99"), ("SPWI810", "SCRL9E")]:
        s = _read_spl_ext(g, res)
        check(s["school"] == 2 and s["excl_1e"] == 0x0100, f"{res} school/excl: {s}")
        check("(Conjuration/Summoning)" in g.tlk(s["desc"]), f"{res} desc: {g.tlk(s['desc'])}")
        _, scrl_id = g.itm_descs(scrl)
        check("(Conjuration/Summoning)" in g.tlk(scrl_id), f"{scrl} desc: {g.tlk(scrl_id)}")

    # Row D. Power Word, Sleep (SPWI220): school Enchantment (4, excl 0x0800), elf (row 15, 0-90),
    # half-elf (row 19, 0-30), undead (row 1), DRAGON, ELEMENTAL, 20 HP gate + wake-on-damage kept
    s = _read_spl_ext(g, "SPWI220")
    check(s["school"] == 4 and s["excl_1e"] == 0x0800, f"SPWI220 school/excl: {s}")
    effs = s["abilities"][0]["effects"]
    check(
        (effs[0]["opcode"], effs[0]["p2"], effs[0]["prob2"], effs[0]["prob1"]) == (324, 15, 0, 90),
        f"SPWI220 elf 90%: {effs[0]}",
    )
    check(
        (effs[1]["opcode"], effs[1]["p2"], effs[1]["prob2"], effs[1]["prob1"]) == (324, 19, 0, 30),
        f"SPWI220 half-elf 30%: {effs[1]}",
    )
    check(any(f["opcode"] == 324 and f["p2"] == 1 and f["p1"] == 0 for f in effs), f"SPWI220 undead: {effs}")
    pws_races = {f["p1"] for f in effs if f["opcode"] == 324 and f["p2"] == 4}
    check({race_num["DRAGON"], race_num["ELEMENTAL"]}.issubset(pws_races), f"SPWI220 races: {pws_races}")
    check(any(f["opcode"] == 324 and f["p1"] == 20 and f["p2"] == 144 for f in effs), "SPWI220 20 HP gate preserved")
    check(any(f["opcode"] == 217 and f["p2"] == 0 for f in effs), "SPWI220 wake-on-damage preserved")
    check("(Enchantment/Charm)" in g.tlk(s["desc"]), f"SPWI220 desc: {g.tlk(s['desc'])}")

    # Row E. Spook (SPWI125): undead (row 1) and True Seeing (stat 118 > 0) immune
    s = _read_spl_ext(g, "SPWI125")
    effs = s["abilities"][0]["effects"]
    spook_rows = {f["p2"] for f in effs if f["opcode"] == 324}
    check(1 in spook_rows and len(spook_rows) == 2, f"SPWI125 op324 rows: {spook_rows}")

    # Row F. Horror (SPWI205): undead (row 1) immune
    s = _read_spl_ext(g, "SPWI205")
    effs = s["abilities"][0]["effects"]
    check(any(f["opcode"] == 324 and f["p2"] == 1 and f["p1"] == 0 for f in effs), f"SPWI205 undead: {effs}")

    # Row G. Mirror Image (SPWI212, SPWI298) and Reflected Image (SPWI120) do not stack
    s_refl = _read_spl_ext(g, "SPWI120")
    refl_effs = s_refl["abilities"][0]["effects"]
    check(refl_effs[0]["opcode"] == 321 and refl_effs[0]["resource"] == "SPWI120", f"SPWI120 refresh: {refl_effs}")
    for res, expected_durs in [("SPWI212", [36, 54]), ("SPWI298", [120])]:
        s_mirr = _read_spl_ext(g, res)
        for ab, dur in zip(s_mirr["abilities"], expected_durs):
            ab_effs = ab["effects"]
            op321_res = {f["resource"] for f in ab_effs if f["opcode"] == 321}
            check(op321_res == {"SPWI212", "SPWI298", "SPWI120"}, f"{res} op321: {op321_res}")
            op206 = [f for f in ab_effs if f["opcode"] == 206]
            check(
                len(op206) == 1 and op206[0]["resource"] == "SPWI120" and op206[0]["duration"] == dur,
                f"{res} op206: {op206}",
            )

    # Row H. AoE damage bypasses Mirror Image (bit 24 = 0x1000000 on AoE SPL/ITM, untouched on ray SPL and melee ITM)
    s_aoe = _read_spl_ext(g, "SPPR609")
    check((s_aoe["abilities"][0]["effects"][0]["save"] & 0x1000000) == 0x1000000, f"SPPR609 save: {s_aoe}")
    check(g.file("override/SPPR411.SPL") is None, "single-target ray SPPR411 must not be touched")
    wand_raw = g.file("override/WAND05.ITM")
    wand_fx = ie.unpack_fx(wand_raw, struct.unpack_from("<I", wand_raw, 0x6A)[0])
    check((wand_fx["save"] & 0x1000000) == 0x1000000, f"WAND05 save: {wand_fx}")
    check(g.file("override/SW1H51.ITM") is None, "melee weapon SW1H51 with ab_flags=40 at 0x26 must not be touched")

    # Row I. Dispel Magic vs magically created weapons (high word at fx+0x0a set to 2, op112 deleted)
    s_disp = _read_spl_ext(g, "SPWI302")
    disp_effs = s_disp["abilities"][0]["effects"]
    check(len(disp_effs) == 1 and disp_effs[0]["opcode"] == 58 and disp_effs[0]["p2"] == 0x20001, f"SPWI302: {disp_effs}")

    # Row J. Magic Resistance (SPPR509): op166 p2=0 (add), self-refresh op321, description updated
    s_mr = _read_spl_ext(g, "SPPR509")
    for ab in s_mr["abilities"]:
        ab_effs = ab["effects"]
        check(ab_effs[0]["opcode"] == 321 and ab_effs[0]["resource"] == "SPPR509", f"SPPR509 op321: {ab_effs}")
        op166 = [f for f in ab_effs if f["opcode"] == 166][0]
        check(op166["p2"] == 0, f"SPPR509 op166 p2: {op166}")
    check("added to any Magic Resistance the target already has" in g.tlk(s_mr["desc"]), f"SPPR509 desc: {g.tlk(s_mr['desc'])}")

    # Row K. Strength of One (SPPR312 + SPPR312A): sub-spell payload + STR > 18 / STREXTRA >= 75 op318 guards
    s_soo = _read_spl_ext(g, "SPPR312")
    soo_effs = s_soo["abilities"][0]["effects"]
    soo_ops = [f["opcode"] for f in soo_effs]
    check(44 not in soo_ops and 97 not in soo_ops and 142 not in soo_ops, f"SPPR312 ops: {soo_ops}")
    check(141 in soo_ops and 174 in soo_ops and 139 in soo_ops, f"SPPR312 visuals kept: {soo_ops}")
    op318_soo = [f for f in soo_effs if f["opcode"] == 318 and f["resource"] == "SPPR312A"]
    check(len(op318_soo) == 2 and {f["p1"] for f in op318_soo} == {18, 75}, f"SPPR312 op318: {op318_soo}")
    op146_soo = [f for f in soo_effs if f["opcode"] == 146 and f["resource"] == "SPPR312A"]
    check(len(op146_soo) == 1 and op146_soo[0]["p2"] == 1, f"SPPR312 op146: {op146_soo}")
    s_sub = _read_spl_ext(g, "SPPR312A")
    sub_ops = [f["opcode"] for f in s_sub["abilities"][0]["effects"]]
    check(sub_ops == [44, 97, 142], f"SPPR312A ops: {sub_ops}")
    check("Strength is not lowered" in g.tlk(s_soo["desc"]), f"SPPR312 desc: {g.tlk(s_soo['desc'])}")

    # Row L. Sequencers and Contingencies (SPWI420, SPWI617, SPWI710, SPWI809, SPWI908): Universal school + text
    for res in ("SPWI420", "SPWI617", "SPWI710", "SPWI809", "SPWI908"):
        s = _read_spl_ext(g, res)
        check(s["school"] == 0 and s["excl_1e"] == 0, f"{res} school/excl: {s}")
        check("(Universal)" in g.tlk(s["desc"]), f"{res} desc: {g.tlk(s['desc'])}")

    # Uninstall restores the game tree
    out = g.uninstall()
    check("SUCCESSFULLY REMOVED" in out, f"uninstall:\n{out}")
    check(g.tree() == before, "uninstall must restore the game tree")


@test
def vanilla_batch_second_install_changes_nothing(work, weidu):
    """Running the component a second time on already-patched files makes no further edits."""
    g = _fresh_vanilla(work, weidu)
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, out)
    first_tree = g.tree()
    first_tlk = g.file("lang/en_US/dialog.tlk")

    out = g.run("--force-install-list")
    check("SUCCESSFULLY INSTALLED" in out, out)
    check(g.tree() == first_tree, "second install modified override files")
    check(g.file("lang/en_US/dialog.tlk") == first_tlk, "second install appended duplicate TLK strings")


@test
def vanilla_batch_alternate_layouts_and_preservation(work, weidu):
    """Compatibility policy check: non-vanilla layouts, extra effects, and existing mod edits are preserved."""
    replace = {
        # 1. Pre-expanded Blindness (10 abilities at min_level 1..10, plus a custom sound op174)
        "SPWI106.SPL": _spl_with_hdr(
            school=5,
            level=1,
            desc=BLIND_DESC,
            abilities=[
                dict(
                    min_level=ml,
                    casting_time=2,
                    effects=[
                        dict(opcode=74, target=2, timing=0, duration=120, save=1),
                        dict(opcode=174, target=2, timing=1, duration=0, resource="EFF_M01"),
                    ],
                )
                for ml in range(1, 11)
            ],
        ),
        # 2. Barkskin (SPPR202) with kit exclusion bits in 0x1e (0x0080) and alignment bits in 0x20 (0x0002),
        # plus existing cleric+druid flags (0x8002 -> should become 0x4002, keeping 0x0080 in 0x1e)
        "SPPR202.SPL": _spl_with_hdr(
            spell_type=2,
            excl_1e=0x0080,
            priest_20=0x8002,
            level=2,
            abilities=[dict(min_level=1, casting_time=5, effects=[dict(opcode=0, target=2)])],
        ),
        # 3. FBLADE.ITM already upgraded by another mod to +2 enchantment
        "FBLADE.ITM": _make_fblade_itm(flags=0x28, enchantment=2),
        # 4. Heal (SPPR607) already lowered to casting time 3 by another mod (should stay 3, not raised to 6)
        "SPPR607.SPL": _spl_with_hdr(
            spell_type=2,
            level=1,
            desc=BLESS_DESC,
            abilities=[dict(min_level=1, casting_time=3, effects=[dict(opcode=132, target=2)])],
        ),
    }
    g = _fresh_vanilla(work, weidu, replace=replace)
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, f"install:\n{out}")

    # Verify pre-expanded Blindness
    s = _read_spl_ext(g, "SPWI106")
    check(len(s["abilities"]) == 10, f"SPWI106 ability count: {len(s['abilities'])}")
    expected_durs = [12, 12, 12, 12, 12, 18, 18, 24, 24, 30]
    for a, exp in zip(s["abilities"], expected_durs):
        by_op = {f["opcode"]: f for f in a["effects"]}
        check(by_op[74]["duration"] == exp, f"SPWI106 op74 dur: {by_op[74]}")
        check(by_op[174]["duration"] == 0 and by_op[174]["resource"] == "EFF_M01", f"SPWI106 op174: {by_op[174]}")

    # Verify Barkskin preserved 0x1e and low alignment bits of 0x20
    s = _read_spl_ext(g, "SPPR202")
    check(s["excl_1e"] == 0x0080 and s["priest_20"] == 0x4002, f"SPPR202 excl: {s}")

    # Verify FBLADE.ITM kept enchantment 2 while gaining 0x40 magical flag
    fb_raw = g.file("override/FBLADE.ITM")
    check((struct.unpack_from("<I", fb_raw, 0x18)[0] & 0x40) == 0x40, "FBLADE magical flag")
    check(struct.unpack_from("<I", fb_raw, 0x60)[0] == 2, "FBLADE enchantment 2 preserved")

    # Verify Heal kept faster casting time 3 (and was not copied to override)
    check(g.file("override/SPPR607.SPL") is None, "SPPR607 with faster ct=3 should not be overwritten")


@test
def vanilla_batch_warnings_on_unexpected_inputs(work, weidu):
    """Missing weapon item or missing anchor opcodes are reported with warnings and left untouched."""
    replace = {
        "FBLADE.ITM": None,
        "SPWI616.SPL": _spl_with_hdr(
            school=8, level=6, abilities=[dict(min_level=1, effects=[dict(opcode=12, p1=10)])]
        ),
        "SPWI713.SPL": _spl_with_hdr(
            school=7, level=7, abilities=[dict(min_level=1, effects=[dict(opcode=12, p1=10)])]
        ),
    }
    g = _fresh_vanilla(work, weidu, replace=replace)
    out = g.install()
    check(fg.with_warnings(out), f"expected warnings:\n{out}")
    check("Flame Blade (SPPR206): weapon item FBLADE.itm is not in this game" in out, out)
    check("Disintegrate (SPWI616): no disintegrate effect (opcode 238)" in out, out)
    check("Finger of Death (SPWI713): no slay effect (opcode 55) with a save" in out, out)
