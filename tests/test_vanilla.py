"""Tests for chriz-bg-magic/lib/cbmagic_vanilla.tpa in synthetic games."""

import struct

import fakegame as fg
import fixtures as fx
import ie
from harness import check, test

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
    _ct_desc("Magic Resistance", 9),
    _ct_desc("Righteous Magic", 9),
    _ct_desc("True Seeing", 8),
    _ct_desc("True Sight", 8),
    _ct_desc("Glyph of Warding", 9) + "\nA successful Saving Throw vs. Spell enables the creature to escape.",
    _ct_desc("Invisibility Purge", 8),
    _ct_desc("Strength", 9),
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
) = range(len(fx.TEXTS), len(VANILLA_TEXTS))

VANILLA_SPELL_SYMBOLS = [
    *fx.SPELL_SYMBOLS,
    (1101, "CLERIC_BLESS"),
    (1105, "CLERIC_ENTANGLE"),
    (1202, "CLERIC_BARKSKIN"),
    (1206, "CLERIC_FLAME_BLADE"),
    (1309, "CLERIC_INVISIBILITY_PURGE"),
    (1402, "CLERIC_ANIMAL_SUMMONING_1"),
    (1501, "CLERIC_ANIMAL_SUMMONING_2"),
    (1505, "CLERIC_TRUE_SIGHT"),
    (1509, "CLERIC_MAGIC_RESISTANCE"),
    (1513, "CLERIC_RIGHTEOUS_MAGIC"),
    (1602, "CLERIC_ANIMAL_SUMMONING_3"),
    (1603, "CLERIC_BLADE_BARRIER"),
    (1604, "CLERIC_CONJURE_ANIMALS"),
    (1605, "CLERIC_CONJURE_FIRE_ELEMENTAL"),
    (1607, "CLERIC_HEAL"),
    (1612, "CLERIC_BOLT_OF_GLORY"),
    (1702, "CLERIC_CONJURE_EARTH_ELEMENTAL"),
    (1708, "CLERIC_FINGER_OF_DEATH"),
    (2106, "WIZARD_BLINDNESS"),
    (2123, "WIZARD_FIND_FAMILIAR"),
    (2214, "WIZARD_STRENGTH"),
    (2502, "WIZARD_CLOUDKILL"),
    (2609, "WIZARD_TRUE_SIGHT"),
    (2614, "WIZARD_DEATH_FOG"),
    (2616, "WIZARD_DISINTEGRATE"),
    (2620, "WIZARD_CONJURE_FIRE_ELEMENTAL"),
    (2621, "WIZARD_CONJURE_AIR_ELEMENTAL"),
    (2622, "WIZARD_CONJURE_EARTH_ELEMENTAL"),
    (2713, "WIZARD_FINGER_OF_DEATH"),
    (2919, "WIZARD_WISH"),
]

VANILLA_RACES = [*fx.RACES, (145, "ELEMENTAL"), (201, "SWORD")]


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


def _vanilla_biff(**replace):
    files = {
        **fx.game(),
        "SPELL.IDS": ie.make_ids(VANILLA_SPELL_SYMBOLS),
        "RACE.IDS": ie.make_ids(VANILLA_RACES),
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
    }

    ct_fixtures = [
        ("SPPR101", 2, 1, 9, BLESS_DESC, [dict(opcode=132, target=2)]),
        ("SPPR503", 2, 5, 8, FSTRIKE_DESC, [fx.damage(fx.FIRE, 8)]),
        ("SPPR607", 2, 6, 9, HEAL_DESC, [dict(opcode=17, target=2)]),
        ("SPPR603", 2, 6, 9, BBARRIER_DESC, [dict(opcode=177, target=1)]),
        ("SPPR612", 2, 6, 9, BGLORY_DESC, [dict(opcode=12, target=2)]),
        ("SPPR509", 2, 5, 9, MR_DESC, [dict(opcode=166, target=2)]),
        ("SPPR513", 2, 5, 9, RM_DESC, [dict(opcode=132, target=1)]),
        ("SPPR505", 2, 5, 8, PTS_DESC, [dict(opcode=193, target=1)]),
        ("SPWI609", 1, 6, 8, WTS_DESC, [dict(opcode=193, target=1)]),
        ("SPPR304", 2, 3, 9, GLYPH_CT_DESC, [fx.damage(fx.ELEC, 3)]),
        ("SPPR309", 2, 3, 8, IP_DESC, [dict(opcode=116, target=2)]),
        ("SPWI214", 1, 2, 9, STR_DESC, [dict(opcode=44, target=2)]),
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
        12: [(0, 64), (65, 99), (100, 100)],
        16: [(0, 60), (61, 95), (96, 100)],
        20: [(0, 56), (57, 91), (92, 100)],
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
        0: [(0, 64), (65, 99), (100, 100)],  # L11: 64/35/1
        1: [(0, 61), (62, 98), (99, 100)],   # L12: 61/37/2
        4: [(0, 52), (53, 94), (95, 100)],   # L15: 52/42/6
        9: [(0, 37), (38, 88), (89, 100)],   # L20: 37/51/12
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

    # 21-32. Casting times and descriptions
    expected_cts = [
        ("SPPR101", 5),
        ("SPPR503", 5),
        ("SPPR607", 6),
        ("SPPR603", 6),
        ("SPPR612", 6),
        ("SPPR509", 5),
        ("SPPR513", 5),
        ("SPPR505", 6),
        ("SPWI609", 6),
        ("SPPR304", 5),
        ("SPPR309", 4),
        ("SPWI214", 5),
    ]
    for res, target_ct in expected_cts:
        s = _read_spl_ext(g, res)
        check([a["casting_time"] for a in s["abilities"]] == [target_ct, target_ct], f"{res} ct: {s['abilities']}")
        check(f"Casting Time: {target_ct}" in g.tlk(s["desc"]), f"{res} desc: {g.tlk(s['desc'])}")

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
        # 4. Bless (SPPR101) already lowered to casting time 3 by another mod (should stay 3, not raised to 5)
        "SPPR101.SPL": _spl_with_hdr(
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

    # Verify Bless kept faster casting time 3 (and was not copied to override)
    check(g.file("override/SPPR101.SPL") is None, "SPPR101 with faster ct=3 should not be overwritten")


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
