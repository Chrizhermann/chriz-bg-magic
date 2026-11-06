"""Tests for the SCS spell changes in chriz-bg-magic (cbmagic_scs.tpa)."""
import struct

from fakegame import FakeGame, installed_ok
from harness import test
from ie import SAVE_BREATH, SAVE_SPELL, make_2da, make_ids, make_itm, make_spl, make_tlk


def _spl_with_excl(data, excl=0, cast_gfx=0, priest_type=0, spell_type=None):
    b = bytearray(data)
    if spell_type is not None:
        struct.pack_into("<H", b, 0x1C, spell_type)
    struct.pack_into("<I", b, 0x1E, excl)
    if priest_type:
        struct.pack_into("<H", b, 0x20, priest_type)
    struct.pack_into("<H", b, 0x22, cast_gfx)
    return bytes(b)


def _itm_with_fields(data, usab=0, ench=0, kit3=0):
    b = bytearray(data)
    struct.pack_into("<I", b, 0x1E, usab)
    b[0x2D] = kit3
    struct.pack_into("<I", b, 0x60, ench)
    return bytes(b)


SPLPROT_BASE = [
    ("0_EA>=0", ["0x10a", "0", "4"]),
    ("1_GENERAL=UNDEAD", ["0x10b", "4", "1"]),
    ("49_ALLIES", ["0x113", "1", "1"]),
    ("76_SPLSTATE=n", ["0x112", "-1", "1"]),
    ("104_RACE=n", ["0x10c", "-1", "1"]),
    ("105_CLASS=n", ["0x10d", "-1", "1"]),
]


@test
def scs_batch1_arcane_spells(work, weidu):
    """Chromatic Orb, Melf's Minute Meteors, Skull Trap, Lower Resistance, Power Word Silence/Stun,
    Mantle, and Project Image match SCS behavior and are idempotent on re-install."""
    tlk = make_tlk([
        "placeholder",
        # 1: Chromatic Orb
        "Chromatic Orb\nEach orb will do damage to the target against which there is no save and an effect against which the target must save vs. Spell with a +6 bonus:\n 10th Level: 1d12 acid damage and turns the victim to stone.\n 12th Level: 2d8 acid damage and instantly kills the victim.",
        # 2: Skull Trap
        "Skull Trap\nThe damage inflicted is equal to 1d6 per level of the caster, or half with a successful Saving Throw vs. Spell.",
        # 3: Lower Resistance
        "Lower Resistance\nlower the Magic Resistance of this creature by 10% + 1% per level of the caster. 60% - 25% (initial casting) - 25% (current casting), which would leave the creature with 10% Magic Resistance.",
        # 4: Power Word, Silence
        "Power Word, Silence\n(Conjuration/Summoning)\nLevel: 6",
        # 5: Power Word, Stun
        "Power Word, Stun\n(Conjuration/Summoning)\nthe current number of Hit Points is used to determine this spell's effects.",
        # 6: Mantle
        "Mantle\nWhen the spell is cast, it confers complete invulnerability to all weapons of +2 or lower enchantment.",
    ])
    chrom_orb = make_spl(
        level=1, school=6, desc=1,
        abilities=[
            {"min_level": 1, "projectile": 24, "effects": [
                {"opcode": 12, "p2": 0x400000, "timing": 1, "dice": 1, "sides": 4},
                {"opcode": 74, "duration": 6, "save": SAVE_SPELL, "bonus": 6},
            ]},
            {"min_level": 10, "projectile": 24, "effects": [
                {"opcode": 134, "duration": 3600, "save": SAVE_SPELL, "bonus": 6},
            ]},
            {"min_level": 12, "projectile": 24, "effects": [
                {"opcode": 55, "p2": 2, "timing": 1, "save": SAVE_SPELL, "bonus": 6},
            ]},
        ],
    )
    meteors = make_spl(
        level=3, school=6,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 111, "target": 1, "p1": 5, "resource": "MELFMET"},
        ]}],
    )
    skull_trap = make_spl(
        level=3, school=7, desc=2,
        abilities=[
            {"min_level": lvl, "target": 4, "projectile": 96, "effects": [
                {"opcode": 12, "p2": 0x400000, "timing": 1, "dice": max(5, lvl), "sides": 6,
                 "save": SAVE_SPELL, "special": 0x100},
            ]}
            for lvl in [1, 6, 10, 12, 13, 15, 20]
        ],
    )
    lower_res = make_spl(
        level=5, school=1, desc=3,
        abilities=[
            {"min_level": lvl, "effects": [
                {"opcode": 166, "power": 5, "p1": -(10 + (9 if lvl == 1 else lvl)), "p2": 0,
                 "duration": 60, "dispel": 2},
                {"opcode": 139, "power": 5, "p1": 0, "timing": 1, "dispel": 2},
            ]}
            for lvl in [1, 10, 15, 20]
        ],
    )
    pw_silence = _spl_with_excl(
        make_spl(level=6, school=2, desc=4, abilities=[{"min_level": 1, "effects": [
            {"opcode": 38, "power": 6, "duration": 42, "dispel": 1},
        ]}]),
        excl=0x0100, cast_gfx=14,
    )
    pw_stun = _spl_with_excl(
        make_spl(level=7, school=2, desc=5, abilities=[{"min_level": 1, "effects": [
            {"opcode": 210, "power": 7, "timing": 1, "dispel": 1},
        ]}]),
        excl=0x0100, cast_gfx=14,
    )
    mantle = make_spl(
        level=7, school=1, desc=6,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 120, "target": 1, "power": 7, "p1": 0, "p2": 2, "duration": 24, "dispel": 3},
            {"opcode": 120, "target": 1, "power": 7, "p1": 1, "p2": 0, "duration": 24, "dispel": 3},
            {"opcode": 120, "target": 1, "power": 7, "p1": 2, "p2": 0, "duration": 24, "dispel": 3},
        ]}],
    )
    proj_img = make_spl(
        level=7, school=5,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 236, "target": 1, "power": 7, "p2": 2, "duration": 84, "dispel": 3},
        ]}],
    )
    projimag_payload = make_spl(
        level=9, school=0,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 144, "target": 1, "p2": 14, "timing": 9},
            {"opcode": 144, "target": 1, "p2": 7, "timing": 9},
            {"opcode": 144, "target": 1, "p2": 0, "timing": 9},
        ]}],
    )
    biff = {
        "SPELL.IDS": make_ids([
            (2118, "WIZARD_CHROMATIC_ORB"),
            (2325, "WIZARD_MELF_METEOR"),
            (2313, "WIZARD_SKULL_TRAP"),
            (2514, "WIZARD_LOWER_RESISTANCE"),
            (2612, "WIZARD_POWER_WORD_SILENCE"),
            (2715, "WIZARD_POWER_WORD_STUN"),
            (2708, "WIZARD_MANTLE"),
            (2703, "WIZARD_PROJECT_IMAGE"),
        ]),
        "SPLSTATE.IDS": make_ids([(29, "FREE_ACTION"), (67, "BUFF_PRO_EFFECTS")]),
        "STATS.IDS": make_ids([(88, "STONESKINS"), (125, "WIZARD_FIRE_SHIELD"), (131, "CLERIC_FREE_ACTION")]),
        "SPLPROT.2DA": make_2da(["STAT", "VALUE", "RELATION"], SPLPROT_BASE),
        "SPWI118.SPL": chrom_orb,
        "SPWI325.SPL": meteors,
        "SPWI313.SPL": skull_trap,
        "SPWI514.SPL": lower_res,
        "SPWI612.SPL": pw_silence,
        "SPWI715.SPL": pw_stun,
        "SPWI708.SPL": mantle,
        "SPWI703.SPL": proj_img,
        "MELFMET.ITM": _itm_with_fields(make_itm(item_type=24), ench=6),
        "PROJIMAG.SPL": projimag_payload,
        "SCRL7P.ITM": _itm_with_fields(
            make_itm([[
                {"opcode": 146, "resource": "SPWI612"},
                {"opcode": 147, "resource": "SPWI612"},
            ]], desc=4),
            usab=0x2f7f5e80,
            kit3=0x01,
        ),
    }
    fg = FakeGame(work, weidu, tlk=tlk, biff=biff)
    out = fg.install()
    assert installed_ok(out), out

    # 1. Chromatic Orb: 6 abilities (1, 2, 3, 4, 5, 7), range 50, no petrify/slay/INVOCH,
    # l3 has no save on 1d3 fire, l5 has Free Action op324 after 1d12 damage, l7 has 2d8 (no save) + hold 78s
    co_raw = fg.file("override/SPWI118.SPL")
    co_ab_off = struct.unpack_from("<I", co_raw, 0x64)[0]
    for a_idx in range(6):
        assert struct.unpack_from("<H", co_raw, co_ab_off + a_idx * 0x28 + 0x0E)[0] == 50
    co = fg.spl("SPWI118")
    assert [a["min_level"] for a in co["abilities"]] == [1, 2, 3, 4, 5, 7]
    for a in co["abilities"]:
        assert all(e["opcode"] not in (55, 134, 215) for e in a["effects"])
        assert any(e["opcode"] == 141 and e["p2"] == 25 for e in a["effects"])
    ab3_fx = co["abilities"][2]["effects"]
    assert [ (e["dice"], e["sides"], e["save"]) for e in ab3_fx if e["opcode"] == 12 ] == [(1, 8, 0), (1, 3, 0)]
    ab5_fx = co["abilities"][4]["effects"]
    assert [e["opcode"] for e in ab5_fx[:4]] == [12, 324, 324, 45]
    ab7_fx = co["abilities"][5]["effects"]
    assert any(e["opcode"] == 12 and e["dice"] == 2 and e["sides"] == 8 and e["save"] == 0 for e in ab7_fx)
    assert any(e["opcode"] == 175 and e["duration"] == 78 and e["save"] == SAVE_SPELL and e["bonus"] == 0 for e in ab7_fx)
    assert "paralyzes the target for 13 rounds" in fg.tlk(co["desc"])

    # 2. Melf's Minute Meteors: weapon enchantment 6 -> 2
    melf_raw = fg.file("override/MELFMET.ITM")
    assert struct.unpack_from("<I", melf_raw, 0x60)[0] == 2

    # 3. Skull Trap: abilities > 12 removed, max 12d6, save vs breath
    st = fg.spl("SPWI313")
    assert [a["min_level"] for a in st["abilities"]] == [1, 6, 10, 12]
    assert max(e["dice"] for a in st["abilities"] for e in a["effects"] if e["opcode"] == 12) == 12
    assert all(e["save"] == SAVE_BREATH for a in st["abilities"] for e in a["effects"] if e["opcode"] == 12)
    assert "maximum of 12d6" in fg.tlk(st["desc"])

    # 4. Lower Resistance: -39, -40, -45, -50
    lr = fg.spl("SPWI514")
    drops = [next(e["p1"] for e in a["effects"] if e["opcode"] == 166) for a in lr["abilities"]]
    assert drops == [-39, -40, -45, -50]
    assert "30% + 1% per level" in fg.tlk(lr["desc"])

    # 5. Power Word, Silence: school 4, excl 0x0800 (Invoker), scroll kit3 0x08 and general usab preserved
    pws_raw = fg.file("override/SPWI612.SPL")
    assert pws_raw[0x25] == 4
    assert struct.unpack_from("<I", pws_raw, 0x1E)[0] == 0x0800
    scrl_raw = fg.file("override/SCRL7P.ITM")
    assert struct.unpack_from("<I", scrl_raw, 0x1E)[0] == 0x2f7f5e80
    assert scrl_raw[0x2D] == 0x08
    assert "(Enchantment/Charm)" in fg.tlk(fg.itm_descs("SCRL7P")[1])

    # 6. Power Word, Stun: school 4, excl 0x0800, leading op324 Free Action immunities
    pwst_raw = fg.file("override/SPWI715.SPL")
    assert pwst_raw[0x25] == 4
    assert struct.unpack_from("<I", pwst_raw, 0x1E)[0] == 0x0800
    pwst = fg.spl("SPWI715")
    lead_ops = [e["opcode"] for e in pwst["abilities"][0]["effects"][:2]]
    assert lead_ops == [324, 324]
    assert "Free Action protects" in fg.tlk(pwst["desc"])

    # 7. Mantle: op120 p1=3 p2=0 added
    mnt = fg.spl("SPWI708")
    assert any(e["opcode"] == 120 and e["p1"] == 3 and e["p2"] == 0 for e in mnt["abilities"][0]["effects"])
    assert "+3 or lower" in fg.tlk(mnt["desc"])

    # 8. Project Image: PROJIMAG.SPL disables buttons 9, 11, 12, 13
    pi = fg.spl("PROJIMAG")
    disabled = {e["p2"] for e in pi["abilities"][0]["effects"] if e["opcode"] == 144}
    assert {0, 7, 9, 11, 12, 13, 14}.issubset(disabled)

    # Idempotence: running the functions again leaves all patched files byte-identical
    snap = fg.tree()
    out2 = fg.install()
    assert installed_ok(out2), out2
    assert fg.tree() == snap


def _ab_projectiles(spl_bytes):
    ab_off, = struct.unpack_from("<I", spl_bytes, 0x64)
    ab_cnt, = struct.unpack_from("<H", spl_bytes, 0x68)
    return [struct.unpack_from("<H", spl_bytes, ab_off + a * 0x28 + 0x26)[0] for a in range(ab_cnt)]


def _ab_cast_times(spl_bytes):
    ab_off, = struct.unpack_from("<I", spl_bytes, 0x64)
    ab_cnt, = struct.unpack_from("<H", spl_bytes, 0x68)
    return [struct.unpack_from("<H", spl_bytes, ab_off + a * 0x28 + 0x12)[0] for a in range(ab_cnt)]


@test
def scs_batch2_arcane_and_symbols(work, weidu):
    """Abi-Dalzim's Horrid Wilting, Improved Mantle, Power Word Blind/Kill, Simulacrum,
    Absolute Immunity, and all 6 Wizard/Priest Symbols."""
    tlk = make_tlk([
        "placeholder",
        # 1: Improved Mantle
        "Improved Mantle\nWhen the spell is cast, it confers complete invulnerability to all weapons of +3 or lower enchantment.",
        # 2: Power Word, Blind
        "Power Word, Blind\n(Conjuration/Summoning)\nArea of Effect: 4-ft. radius\nWhen a Power Word, Blind spell is cast, one or more creatures within the area of effect become sightless. The spellcaster selects one creature as the target center, and the effect spreads outward from the center, affecting all within a 4-ft. radius. This lasts for 6 rounds or until dispelled. All of the effects of blindness apply to the victims, such as a penalty to hit and to AC.",
        # 3: Absolute Immunity
        "Absolute Immunity\nWhen the spell is cast, it confers complete invulnerability to all weapons except for those of greater than +5 enchantment.",
        # 4: Power Word, Kill
        "Power Word, Kill\n(Conjuration/Summoning)\nLevel: 9",
        # 5: Symbol, Death
        "Symbol, Death\n(Conjuration/Summoning)\nThe symbol will remain there until someone comes too close, at which point it will explode, causing all those within the area to make a Save vs. Death or die.",
        # 6: Symbol, Stun
        "Symbol, Stun\n(Conjuration/Summoning)\nThe symbol will remain there until someone comes too close, at which point it will explode, causing all those within the area to make a Save vs. Spell at a -4 penalty or be stunned for 2 rounds + 1 round for every 3 levels of the caster.",
        # 7: Symbol, Fear
        "Symbol, Fear\n(Conjuration/Summoning)\nThe symbol will remain there until someone comes too close, at which point it will explode, causing all those within the area to make a Save vs. Spell at a -4 penalty or be affected by fear for 2 rounds + 1 round for every 3 levels of the caster.",
    ])
    abi_dalzim = make_spl(
        level=8, school=7,
        abilities=[{"min_level": 1, "target": 4, "projectile": 236, "effects": [
            {"opcode": 12, "p2": 0x400000, "timing": 1, "dice": 16, "sides": 8, "save": SAVE_SPELL, "special": 0x100},
        ]}],
    )
    imp_mantle = make_spl(
        level=8, school=1, desc=1,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 120, "target": 1, "power": 8, "p1": 0, "p2": 2, "duration": 24, "dispel": 3},
            {"opcode": 120, "target": 1, "power": 8, "p1": 3, "p2": 0, "duration": 24, "dispel": 3},
        ]}],
    )
    pw_blind = _spl_with_excl(
        make_spl(level=8, school=2, desc=2, abilities=[{"min_level": 1, "projectile": 218, "effects": [
            {"opcode": 74, "power": 8, "duration": 36, "dispel": 1},
        ]}]),
        excl=0x0100, cast_gfx=14,
    )
    simul_spl = make_spl(
        level=8, school=5,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 236, "target": 1, "power": 8, "p2": 3, "duration": 84, "dispel": 1},
        ]}],
    )
    simul_payload = make_spl(
        level=9, school=0,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 144, "target": 1, "p2": 14, "timing": 9},
            {"opcode": 144, "target": 1, "p2": 0, "timing": 9},
        ]}],
    )
    abs_imm = make_spl(
        level=9, school=1, desc=3,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 120, "target": 1, "power": 9, "p1": 5, "p2": 0, "duration": 24, "dispel": 3},
        ]}],
    )
    pw_kill = _spl_with_excl(
        make_spl(level=9, school=2, desc=4, abilities=[{"min_level": 1, "effects": [
            {"opcode": 209, "power": 9, "timing": 1, "dispel": 1},
        ]}]),
        excl=0x0100, cast_gfx=14,
    )
    npc_sym_death = make_spl(
        level=8, school=2,
        abilities=[{"min_level": 1, "target": 4, "projectile": 326, "effects": [
            {"opcode": 13, "power": 8, "p2": 4, "timing": 1, "save": 4},
        ]}],
    )
    wiz_sym_death = _spl_with_excl(make_spl(
        level=8, school=2, desc=5,
        abilities=[{"min_level": 1, "target": 4, "projectile": 225, "effects": [
            {"opcode": 13, "power": 8, "p2": 4, "timing": 1, "save": 4},
        ]}],
    ), excl=0x0100, cast_gfx=14)
    wiz_sym_stun = _spl_with_excl(make_spl(
        level=8, school=2, desc=6,
        abilities=[{"min_level": 1, "target": 4, "projectile": 225, "effects": [
            {"opcode": 45, "power": 8, "duration": 18, "save": SAVE_SPELL, "bonus": -4},
        ]}],
    ), excl=0x0100, cast_gfx=14)
    wiz_sym_fear = _spl_with_excl(make_spl(
        level=8, school=2, desc=7,
        abilities=[{"min_level": 1, "target": 4, "projectile": 225, "effects": [
            {"opcode": 24, "power": 8, "duration": 18, "save": SAVE_SPELL, "bonus": -4},
        ]}],
    ), excl=0x0100, cast_gfx=14)
    pri_sym_death = _spl_with_excl(wiz_sym_death, excl=0x80000000, cast_gfx=14, spell_type=2)
    pri_sym_stun = _spl_with_excl(wiz_sym_stun, excl=0x80000000, cast_gfx=14, spell_type=2)
    pri_sym_fear = _spl_with_excl(wiz_sym_fear, excl=0x80000000, cast_gfx=14, spell_type=2)
    biff = {
        "SPELL.IDS": make_ids([
            (2812, "WIZARD_ABI_DALZIMS_HORRID_WILTING"),
            (2808, "WIZARD_IMPROVED_MANTLE"),
            (2815, "WIZARD_POWER_WORD_BLIND"),
            (2804, "WIZARD_SIMULACRUM"),
            (2817, "WIZARD_SYMBOL_DEATH"),
            (2816, "WIZARD_SYMBOL_STUN"),
            (2811, "WIZARD_SYMBOL_FEAR"),
            (2897, "WIZARD_NPC_SYMBOL_DEATH"),
            (2907, "WIZARD_ABSOLUTE_IMMUNITY"),
            (2912, "WIZARD_POWER_WORD_KILL"),
            (1719, "CLERIC_SYMBOL_DEATH"),
            (1718, "CLERIC_SYMBOL_STUN"),
            (1706, "CLERIC_SYMBOL_FEAR"),
        ]),
        "RACE.IDS": make_ids([(144, "GOLEM"), (162, "SWORD")]),
        "CLASS.IDS": make_ids([(145, "ELEMENTAL_EARTH"), (182, "ELEMENTAL_FIRE"), (183, "ELEMENTAL_AIR")]),
        "SPLSTATE.IDS": make_ids([(29, "FREE_ACTION")]),
        "STATS.IDS": make_ids([(131, "CLERIC_FREE_ACTION")]),
        "SPLPROT.2DA": make_2da(["STAT", "VALUE", "RELATION"], SPLPROT_BASE),
        "SPWI812.SPL": abi_dalzim,
        "SPWI808.SPL": imp_mantle,
        "SPWI815.SPL": pw_blind,
        "SPWI804.SPL": simul_spl,
        "SIMULACR.SPL": simul_payload,
        "SPWI897.SPL": npc_sym_death,
        "SPWI817.SPL": wiz_sym_death,
        "SPWI816.SPL": wiz_sym_stun,
        "SPWI811.SPL": wiz_sym_fear,
        "SPWI907.SPL": abs_imm,
        "SPWI912.SPL": pw_kill,
        "SPPR719.SPL": pri_sym_death,
        "SPPR718.SPL": pri_sym_stun,
        "SPPR706.SPL": pri_sym_fear,
        "SCRL9U.ITM": _itm_with_fields(
            make_itm([[
                {"opcode": 146, "resource": "SPWI912"},
                {"opcode": 147, "resource": "SPWI912"},
            ]], desc=4),
            usab=0x2f7f5e80,
            kit3=0x01,
        ),
        "SCRLAO.ITM": _itm_with_fields(
            make_itm([[
                {"opcode": 146, "resource": "SPWI817"},
                {"opcode": 147, "resource": "SPWI817"},
            ]], desc=5),
            usab=0x2f7f5e80,
            kit3=0x01,
        ),
    }
    fg = FakeGame(work, weidu, tlk=tlk, biff=biff)
    out = fg.install()
    assert installed_ok(out), out

    # Abi-Dalzim: 6 leading op324 immunities (undead, golem, sword, earth/fire/air elementals)
    ad = fg.spl("SPWI812")
    lead = ad["abilities"][0]["effects"][:6]
    assert all(e["opcode"] == 324 for e in lead)
    assert {(e["p1"], e["p2"]) for e in lead} == {(0, 1), (144, 4), (162, 4), (145, 5), (182, 5), (183, 5)}

    # Improved Mantle (+4) & Absolute Immunity (+6)
    im = fg.spl("SPWI808")
    assert any(e["opcode"] == 120 and e["p1"] == 4 and e["p2"] == 0 for e in im["abilities"][0]["effects"])
    assert "+4 or lower" in fg.tlk(im["desc"])
    ai = fg.spl("SPWI907")
    assert any(e["opcode"] == 120 and e["p1"] == 6 and e["p2"] == 0 for e in ai["abilities"][0]["effects"])
    assert "up to +6 enchantment" in fg.tlk(ai["desc"])

    # Power Word, Blind: school 4, excl 0x0800, projectile 1
    pwb_raw = fg.file("override/SPWI815.SPL")
    assert pwb_raw[0x25] == 4
    assert struct.unpack_from("<I", pwb_raw, 0x1E)[0] == 0x0800
    assert _ab_projectiles(pwb_raw) == [1]
    pwb = fg.spl("SPWI815")
    assert "Area of Effect: 1 creature" in fg.tlk(pwb["desc"])
    assert "(Enchantment/Charm)" in fg.tlk(pwb["desc"])

    # Power Word, Kill: school 4, excl 0x0800
    pwk_raw = fg.file("override/SPWI912.SPL")
    assert pwk_raw[0x25] == 4
    assert struct.unpack_from("<I", pwk_raw, 0x1E)[0] == 0x0800
    scrl9u = fg.file("override/SCRL9U.ITM")
    assert struct.unpack_from("<I", scrl9u, 0x1E)[0] == 0x2f7f5e80
    assert scrl9u[0x2D] == 0x08

    # Simulacrum: buttons 9, 11, 12 disabled, button 13 NOT disabled
    sim = fg.spl("SIMULACR")
    sim_btns = {e["p2"] for e in sim["abilities"][0]["effects"] if e["opcode"] == 144}
    assert {0, 9, 11, 12, 14}.issubset(sim_btns)
    assert 13 not in sim_btns

    # All 6 Symbols: school 4, projectile 326, enemy-only + Enchantment description, wizard excl 0x0800, priest excl preserved
    for res in ("SPWI817", "SPWI816", "SPWI811", "SPPR719", "SPPR718", "SPPR706"):
        raw = fg.file(f"override/{res}.SPL")
        assert _ab_projectiles(raw) == [326], res
        assert raw[0x25] == 4, res
        if res.startswith("SPWI"):
            assert struct.unpack_from("<I", raw, 0x1E)[0] == 0x0800, res
        else:
            assert struct.unpack_from("<I", raw, 0x1E)[0] == 0x80000000, res
        parsed = fg.spl(res)
        assert "(Enchantment/Charm)" in fg.tlk(parsed["desc"])
        assert "until an opponent comes too close" in fg.tlk(parsed["desc"])
        assert "causing all enemies within" in fg.tlk(parsed["desc"])
    scrlao = fg.file("override/SCRLAO.ITM")
    assert struct.unpack_from("<I", scrlao, 0x1E)[0] == 0x2f7f5e80
    assert scrlao[0x2D] == 0x08
    assert "(Enchantment/Charm)" in fg.tlk(fg.itm_descs("SCRLAO")[1])
    for stun_res in ("SPWI816", "SPPR718"):
        parsed = fg.spl(stun_res)
        assert [e["opcode"] for e in parsed["abilities"][0]["effects"][:2]] == [324, 324]
        assert "Free Action protects" in fg.tlk(parsed["desc"])

    # Idempotence check
    snap = fg.tree()
    out2 = fg.install()
    assert installed_ok(out2), out2
    assert fg.tree() == snap


def _make_cre(xp=20000, ea=128, gender=4, ovr="GORBAT") -> bytes:
    buf = bytearray(0x2D4)
    buf[0:8] = b"CRE V1.0"
    struct.pack_into("<I", buf, 0x14, xp)
    buf[0x248:0x250] = ovr.encode("ascii").ljust(8, b"\x00")[:8]
    buf[0x250:0x258] = b"dembal01"
    buf[0x270] = ea
    buf[0x275] = gender
    return bytes(buf)


def _make_summon_eff(cre_res: str, power: int = 7) -> bytes:
    buf = bytearray(0x110)
    buf[0:8] = b"EFF V2.0"
    buf[8:16] = b"EFF V2.0"
    struct.pack_into("<I", buf, 0x10, 67)
    struct.pack_into("<I", buf, 0x14, 1)
    struct.pack_into("<I", buf, 0x18, power)
    struct.pack_into("<I", buf, 0x20, 2)
    struct.pack_into("<I", buf, 0x24, 1)
    struct.pack_into("<I", buf, 0x28, 2400)
    struct.pack_into("<H", buf, 0x2C, 100)
    buf[0x30:0x38] = cre_res.encode("ascii").ljust(8, b"\x00")[:8]
    return bytes(buf)


@test
def scs_batch3_fiends_and_divine(work, weidu):
    """Verify Batch 3: Fiend summoning (Cacofiend, Summon Fiend, Wizard/Cleric Gate),
    Blade Barrier, Globe of Blades, Call Lightning, Defensive Harmony, Glyph of Warding, Magical Stone."""
    tlk = make_tlk([
        "",
        # 1: Cacofiend
        "Cacofiend\nWhen this spell is cast, it teleports in a powerful fiend that will go on a rampage.",
        # 2: Summon Fiend
        "Summon Fiend\nCasting this spell summons a frenzied demon or devil.",
        # 3: Gate
        "Gate\nBy means of this spell, the caster calls an outer-planar creature--the pit fiend--to attack <PRO_HISHER> foes.",
        # 4: Blade Barrier
        "Blade Barrier\nCasting Time: 9\nAny creature attempting to pass through the Blade Barrier suffers 8d8 points of damage. Creatures within the area of the barrier when it is invoked are entitled to a Saving Throw vs. Spell to negate the damage.",
        # 5: Globe of Blades
        "Globe of Blades\nAny creature attempting to pass through the blade barrier suffers 10d10 points of damage. Creatures within the area of the barrier when it is invoked are entitled to a Saving Throw vs. Spell at -2. If this is successful, the blades are avoided and no damage is suffered.",
        # 6: Call Lightning
        "Call Lightning\nDuration: 1 round/4 levels\nThe spell has a duration of 1 round every 4 levels of the caster. Thus, an 8th-level caster will call down two bolts.",
        # 7: Defensive Harmony
        "Defensive Harmony\nWhile the spell is in effect, each affected creature gains a +2 bonus to <PRO_HISHER> Armor Class.",
        # 8: Glyph of Warding
        "Glyph of Warding\nCasting Time: 9\nSaving Throw: Neg.\nAny creature violating the warded area is subject to the magic it stores, although a successful Saving Throw vs. Spell enables the creature to escape the effects of the glyph.",
        # 9: Magical Stone
        "Magical Stone\nThe stone deals 1d4 points of damage to whomever it hits.",
    ])
    caco_spl = make_spl(
        level=7, school=2, desc=1,
        abilities=[{"min_level": 1, "target": 4, "effects": [
            {"opcode": 177, "target": 1, "p1": 0, "p2": 2, "duration": 90, "dispel": 2, "resource": "SPCACO"},
        ]}],
    )
    fiend_spl = make_spl(
        level=8, school=2, desc=2,
        abilities=[{"min_level": 1, "target": 4, "effects": [
            {"opcode": 177, "target": 1, "p1": 0, "p2": 2, "duration": 90, "dispel": 2, "resource": "SPFIEND"},
        ]}],
    )
    wgate_spl = make_spl(
        level=9, school=2, desc=3,
        abilities=[{"min_level": 1, "target": 4, "effects": [
            {"opcode": 177, "target": 1, "p1": 0, "p2": 2, "duration": 198, "resource": "SPGATE"},
        ]}],
    )
    cgate_spl = make_spl(
        spell_type=2, level=7, school=2, desc=3,
        abilities=[{"min_level": 1, "target": 4, "effects": [
            {"opcode": 177, "target": 1, "p1": 0, "p2": 2, "duration": 200, "resource": "SPGATE"},
        ]}],
    )
    bbar_spl = make_spl(
        spell_type=2, level=6, school=6, desc=4,
        abilities=[{"min_level": 1, "target": 5, "casting_time": 9, "effects": [
            {"opcode": 177, "target": 1, "power": 6, "p2": 2, "duration": 62, "dispel": 3, "resource": "SPPR603D"},
        ]}],
    )
    bbar_pay = make_spl(
        spell_type=2, level=6, school=6,
        abilities=[{"min_level": 1, "target": 1, "projectile": 216, "effects": [
            {"opcode": 12, "p2": 0x1000000, "timing": 1, "dice": 8, "sides": 8, "save": SAVE_SPELL, "special": 0},
        ]}],
    )
    bbar_npc_pay = make_spl(
        spell_type=2, level=6, school=6,
        abilities=[{"min_level": 1, "target": 1, "projectile": 218, "effects": [
            {"opcode": 12, "p2": 0x1000000, "timing": 1, "dice": 6, "sides": 8, "save": SAVE_SPELL, "special": 0},
        ]}],
    )
    gblades_spl = make_spl(
        spell_type=2, level=7, school=6, desc=5,
        abilities=[{"min_level": 1, "target": 5, "casting_time": 9, "effects": [
            {"opcode": 177, "target": 1, "power": 7, "p2": 2, "duration": 60, "dispel": 3, "resource": "SPPR725D"},
        ]}],
    )
    gblades_pay = make_spl(
        spell_type=2, level=7, school=6,
        abilities=[{"min_level": 1, "target": 1, "projectile": 216, "effects": [
            {"opcode": 12, "p2": 0x1000000, "timing": 1, "dice": 10, "sides": 10, "save": SAVE_SPELL, "bonus": -2, "special": 0},
        ]}],
    )
    call_lgt = make_spl(
        spell_type=2, level=3, school=8, desc=6,
        abilities=[
            {"min_level": 1, "projectile": 81, "effects": [{"opcode": 12, "p2": 0x40000, "dice": 7, "sides": 8, "save": SAVE_SPELL, "special": 0x100}]},
            {"min_level": 6, "projectile": 81, "effects": [{"opcode": 12, "p2": 0x40000, "dice": 8, "sides": 8, "save": SAVE_SPELL, "special": 0x100}]},
            {"min_level": 10, "projectile": 82, "effects": [{"opcode": 12, "p2": 0x40000, "dice": 12, "sides": 8, "save": SAVE_SPELL, "special": 0x100}]},
            {"min_level": 12, "projectile": 83, "effects": [{"opcode": 12, "p2": 0x40000, "dice": 14, "sides": 8, "save": SAVE_SPELL, "special": 0x100}]},
        ],
    )
    def_harm = make_spl(
        spell_type=2, level=4, school=4, desc=7,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 0, "power": 4, "p1": 2, "p2": 0, "duration": 36, "dispel": 3},
        ]}],
    )
    glyph_spl = make_spl(
        spell_type=2, level=3, school=1, desc=8,
        abilities=[
            {"min_level": 1, "target": 4, "casting_time": 9, "effects": [
                {"opcode": 12, "power": 3, "p2": 0x40000, "timing": 1, "dice": 5, "sides": 4, "save": SAVE_SPELL, "special": 0},
            ]},
            {"min_level": 18, "target": 4, "casting_time": 9, "effects": [
                {"opcode": 12, "power": 3, "p2": 0x40000, "timing": 1, "dice": 18, "sides": 4, "save": SAVE_SPELL, "special": 0},
            ]},
        ],
    )
    mstone_spl = make_spl(
        spell_type=2, level=1, school=4, desc=9,
        abilities=[{"min_level": 1, "target": 1, "effects": [
            {"opcode": 12, "power": 1, "p2": 0x400000, "timing": 1, "dice": 1, "sides": 4, "dispel": 1},
        ]}],
    )
    biff = {
        "SPELL.IDS": make_ids([
            (2707, "WIZARD_CACOFIEND"),
            (2807, "WIZARD_SUMMON_FIEND"),
            (2905, "WIZARD_GATE"),
            (1703, "CLERIC_GATE"),
            (1603, "CLERIC_BLADE_BARRIER"),
            (1725, "CLERIC_GLOBE_OF_BLADES"),
            (1302, "CLERIC_CALL_LIGHTNING"),
            (1406, "CLERIC_DEFENSIVE_HARMONY"),
            (1304, "CLERIC_GLYPH_OF_WARDING"),
            (1106, "CLERIC_MAGIC_STONE"),
        ]),
        "SPLPROT.2DA": make_2da(["STAT", "VALUE", "RELATION"], SPLPROT_BASE),
        "GORBAT5.CRE": _make_cre(),
        "GORBAT3.CRE": _make_cre(),
        "DEMBAL01.CRE": _make_cre(),
        "SPCACO.EFF": _make_summon_eff("demnabsu", 7),
        "SPFIEND.EFF": _make_summon_eff("demglasu", 8),
        "SPGATE.EFF": _make_summon_eff("dempitsu", 8),
        "SPWI707.SPL": caco_spl,
        "SPWI807.SPL": fiend_spl,
        "SPWI905.SPL": wgate_spl,
        "SPPR703.SPL": cgate_spl,
        "SPPR603.SPL": bbar_spl,
        "SPPR603D.SPL": bbar_pay,
        "SPPR698D.SPL": bbar_npc_pay,
        "SPPR725.SPL": gblades_spl,
        "SPPR725D.SPL": gblades_pay,
        "SPPR302.SPL": call_lgt,
        "SPPR406.SPL": def_harm,
        "SPPR304.SPL": glyph_spl,
        "SPPR106.SPL": mstone_spl,
        "SCRL9N.ITM": make_itm([[
            {"opcode": 146, "resource": "SPWI905"},
            {"opcode": 147, "resource": "SPWI905"},
        ]], desc=3),
    }
    fg = FakeGame(work, weidu, tlk=tlk, biff=biff)
    out = fg.install()
    assert installed_ok(out), out

    # Summoned CREs, species BCS scripts, and EFFs created and configured
    for cre_name in ("CBMGBONF", "CBMGCORN", "CBMGBALR"):
        cre = fg.file(f"override/{cre_name}.CRE")
        assert cre is not None
        assert struct.unpack_from("<I", cre, 0x14)[0] == 0
        assert cre[0x270] == 28  # GOODBUTRED
        assert cre[0x275] == 9   # SUMMONED_DEMON
        assert cre[0x248:0x250].rstrip(b"\x00").decode("ascii").upper() == cre_name
        assert cre[0x250:0x258] == b"\x00" * 8
        bcs = fg.file(f"override/{cre_name}.BCS")
        assert bcs is not None and bcs.startswith(b"SC")
    for eff_name, exp_cre in (("CBMGCACO", "cbmgbonf"), ("CBMGFIEN", "cbmgcorn"), ("CBMGGATE", "cbmgbalr")):
        eff = fg.file(f"override/{eff_name}.EFF")
        assert eff is not None
        assert eff[0x30:0x38].rstrip(b"\x00").decode("ascii").lower() == exp_cre

    # Fiend spells: 3 op177 effects (Lawful=16 -> eff_l, Chaotic=48 -> eff_c, Neutral=32 -> eff_c) and ability target=5
    for res, eff_l, eff_c in (
        ("SPWI707", "cbmgcaco", "spcaco"),
        ("SPWI807", "cbmgfien", "spfiend"),
        ("SPWI905", "spgate", "cbmggate"),
        ("SPPR703", "spgate", "cbmggate"),
    ):
        raw = fg.file(f"override/{res}.SPL")
        ab_off = struct.unpack_from("<I", raw, 0x64)[0]
        assert raw[ab_off + 0x0C] == 5
        parsed = fg.spl(res)
        fxs = parsed["abilities"][0]["effects"]
        assert [(e["opcode"], e["p1"], e["p2"], e["resource"].lower(), e["prob2"], e["prob1"]) for e in fxs] == [
            (177, 16, 8, eff_l, 0, 100),
            (177, 48, 8, eff_c, 0, 100),
            (177, 32, 8, eff_c, 0, 100),
        ]
    # Gate scroll cast header target updated to 5
    scrl_raw = fg.file("override/SCRL9N.ITM")
    i_ab_off = struct.unpack_from("<I", scrl_raw, 0x64)[0]
    assert scrl_raw[i_ab_off + 0x0C] == 5

    # Blade Barrier & Globe of Blades
    assert _ab_cast_times(fg.file("override/SPPR603.SPL")) == [6]
    npc_bb_raw = fg.file("override/SPPR698D.SPL")
    assert _ab_projectiles(npc_bb_raw) == [216]
    npc_ab_off = struct.unpack_from("<I", npc_bb_raw, 0x64)[0]
    assert struct.unpack_from("<H", npc_bb_raw, npc_ab_off + 0x0E)[0] == 6
    for pay_res in ("SPPR603D", "SPPR698D", "SPPR725D"):
        pay = fg.spl(pay_res)
        fxs = pay["abilities"][0]["effects"]
        assert fxs[0]["opcode"] == 318
        assert fxs[1]["opcode"] == 12 and (fxs[1]["special"] & 0x100) != 0
        if pay_res in ("SPPR603D", "SPPR698D"):
            assert fxs[1]["dice"] == 8 and fxs[1]["sides"] == 8
    assert "Any enemy attempting" in fg.tlk(fg.spl("SPPR603")["desc"])
    assert "Any enemy attempting" in fg.tlk(fg.spl("SPPR725")["desc"])

    # Call Lightning projectiles: 85, 86, 90, 91
    assert _ab_projectiles(fg.file("override/SPPR302.SPL")) == [85, 86, 90, 91]
    assert "1 round/level (maximum 11 rounds)" in fg.tlk(fg.spl("SPPR302")["desc"])

    # Defensive Harmony: cleric-only (0x20 = 0x8000) and +4 AC
    dh_raw = fg.file("override/SPPR406.SPL")
    assert struct.unpack_from("<H", dh_raw, 0x20)[0] == 0x8000
    dh = fg.spl("SPPR406")
    assert dh["abilities"][0]["effects"][0]["p1"] == 4
    assert "+4 bonus" in fg.tlk(dh["desc"])

    # Glyph of Warding: casting time 5, save vs breath (from cbmagic_fix_breath_saves) + save for half (0x100)
    assert _ab_cast_times(fg.file("override/SPPR304.SPL")) == [5, 5]
    gw = fg.spl("SPPR304")
    for ab in gw["abilities"]:
        assert ab["effects"][0]["save"] == SAVE_BREATH
        assert (ab["effects"][0]["special"] & 0x100) != 0
    assert "take half damage from the glyph" in fg.tlk(gw["desc"])

    # Magical Stone: CBMGMST1.EFF (3d4) & CBMGMST2.EFF (6d4), dispel=0 at 0x5c, 5 op177 effects on SPPR106
    mst1 = fg.file("override/CBMGMST1.EFF")
    mst2 = fg.file("override/CBMGMST2.EFF")
    assert struct.unpack_from("<II", mst1, 0x38) == (3, 4)
    assert struct.unpack_from("<II", mst2, 0x38) == (6, 4)
    assert struct.unpack_from("<I", mst1, 0x5C)[0] == 0
    assert struct.unpack_from("<I", mst2, 0x5C)[0] == 0
    ms = fg.spl("SPPR106")
    ms_fx = ms["abilities"][0]["effects"]
    assert [(e["opcode"], e["p1"], e["p2"], e["resource"].lower()) for e in ms_fx] == [
        (177, 4, 3, "cbmgmst2"),
        (177, 1, 3, "cbmgmst1"),
        (177, 2, 3, "cbmgmst1"),
        (177, 5, 3, "cbmgmst1"),
        (177, 255, 3, "cbmgmst1"),
    ]
    assert "3d4 points of crushing damage" in fg.tlk(ms["desc"])

    # Idempotence check
    snap = fg.tree()
    out2 = fg.install()
    assert installed_ok(out2), out2
    assert fg.tree() == snap


@test
def scs_batch4_insects_and_natures_beauty(work, weidu):
    """Verify Batch 4: Summon Insects, Insect Plague, Creeping Doom (+ Fire Shield, PfNW items/spells,
    Death Spell counter), Nature's Beauty, and Lesser Restoration ability drain."""
    tlk = make_tlk([
        "",
        # 1: Summon Insects
        "Summon Insects\nThe swarm will repeatedly bite the target, making it very difficult to cast spells (50% chance of spell failure).",
        # 2: Insect Plague
        "Insect Plague\nCreatures within the cloud sustain 1 point of damage every 2 seconds. Spellcasting within the swarm is impossible (100% chance of spell failure), and each victim must make a Saving Throw vs. Breath Weapon or run away in fear for 1 round.",
        # 3: Creeping Doom
        "Creeping Doom\nThose trapped by the insects suffer 2 points of damage each second and a spell failure rate of 100%.",
        # 4: Nature's Beauty
        "Nature's Beauty\nAs with a nymph, anyone viewing the disguised caster must make a Saving Throw vs. Spell with +3 bonus or die of longing for the denied illusion. Even if the Saving Throw is successful, hapless viewers of the transformed Druid are all instantly smitten with permanent blindness (until dispelled).",
        # 5: Lesser Restoration
        "Lesser Restoration\nWhen this spell is cast, the life energy level of the recipient is raised. This reverses any previous life energy level drain of the creature by a force or monster.",
    ])
    sum_ins = make_spl(
        spell_type=2, level=3, school=2, desc=1,
        abilities=[{"min_level": 1, "target": 1, "projectile": 227, "effects": [
            {"opcode": 60, "power": 3, "p1": 50, "p2": 0, "duration": 42, "save": SAVE_BREATH, "bonus": -4},
        ]}],
    )
    ins_plg = make_spl(
        spell_type=2, level=5, school=2, desc=2,
        abilities=[{"min_level": 1, "target": 1, "projectile": 228, "effects": [
            {"opcode": 60, "power": 5, "p1": 100, "p2": 0, "duration": 36},
        ]}],
    )
    crp_doom = make_spl(
        spell_type=2, level=7, school=2, desc=3,
        abilities=[{"min_level": 1, "target": 1, "projectile": 228, "effects": [
            {"opcode": 60, "power": 7, "p1": 100, "p2": 0, "duration": 18},
        ]}],
    )
    fshield_red = make_spl(
        spell_type=1, level=4, school=6,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 233, "target": 1, "power": 4, "p1": 1, "p2": 125, "duration": 60, "dispel": 3},
        ]}],
    )
    pfnw_spl = make_spl(
        spell_type=1, level=5, school=1,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 120, "target": 1, "power": 5, "p1": 0, "p2": 2, "timing": 0, "duration": 60, "dispel": 3},
        ]}],
    )
    pfnw_itm = make_itm([[
        {"opcode": 120, "target": 1, "p1": 0, "p2": 2, "timing": 2, "duration": 0},
    ]])
    death_spl = make_spl(
        spell_type=1, level=6, school=7,
        abilities=[{"min_level": 1, "target": 4, "projectile": 172, "effects": [
            {"opcode": 13, "power": 6, "p1": 8, "p2": 4, "timing": 1, "dispel": 2},
        ]}],
    )
    nat_bty = make_spl(
        spell_type=2, level=7, school=5, desc=4,
        abilities=[{"min_level": 1, "target": 5, "projectile": 159, "effects": [
            {"opcode": 55, "power": 7, "p1": 1, "p2": 3, "timing": 1, "save": SAVE_SPELL, "bonus": 3, "dispel": 1},
            {"opcode": 74, "power": 7, "p1": 0, "p2": 0, "timing": 1, "dispel": 1},
            {"opcode": 142, "power": 7, "p2": 8, "timing": 1, "dispel": 1},
            {"opcode": 215, "target": 1, "power": 7, "p2": 1, "duration": 2, "resource": "icclkfr2", "dispel": 1},
        ]}],
    )
    lesser_rest = _spl_with_excl(
        make_spl(
            spell_type=2, level=4, school=7, desc=5,
            abilities=[{"min_level": 1, "target": 1, "effects": [
                {"opcode": 224, "target": 2, "power": 4, "timing": 1},
            ]}],
        ),
        priest_type=0x8000,
    )
    greater_rest = make_spl(
        spell_type=2, level=7, school=7,
        abilities=[{"min_level": 1, "target": 1, "effects": [
            {"opcode": 224, "target": 2, "power": 7, "timing": 1},
        ]}],
    )
    drain_spl = make_spl(
        spell_type=4, level=1, school=0,
        abilities=[{"min_level": 1, "target": 1, "effects": [
            {"opcode": 12, "target": 2, "p2": 0x400000, "timing": 1, "dice": 1, "sides": 6},
            {"opcode": 44, "target": 2, "p1": -2, "p2": 0, "timing": 0, "duration": 300, "save": SAVE_SPELL},
            {"opcode": 142, "target": 2, "p2": 22, "timing": 0, "duration": 300, "save": SAVE_SPELL},
        ]}],
    )
    drain_itm = make_itm([[
        {"opcode": 12, "target": 2, "p2": 0, "timing": 1, "dice": 1, "sides": 8},
        {"opcode": 19, "target": 2, "p1": -1, "p2": 0, "timing": 1, "duration": 0},
        {"opcode": 142, "target": 2, "p2": 91, "timing": 1, "duration": 0},
    ]])
    biff = {
        "SPELL.IDS": make_ids([
            (1319, "CLERIC_SUMMON_INSECTS"),
            (1517, "CLERIC_INSECT_PLAGUE"),
            (1717, "CLERIC_CREEPING_DOOM"),
            (2418, "WIZARD_FIRE_SHIELD_RED"),
            (2511, "WIZARD_PROTECTION_FROM_NORMAL_WEAPONS"),
            (2605, "WIZARD_DEATH_SPELL"),
            (1704, "CLERIC_NATURE_BEAUTY"),
            (1417, "CLERIC_LESSER_RESTORATION"),
            (1713, "CLERIC_RESTORATION"),
        ]),
        "PROJECTL.IDS": make_ids([(157, "INAREAPA")]),
        "STATS.IDS": make_ids([
            (88, "STONESKINS"),
            (120, "CLERIC_INSECT_PLAGUE"),
            (125, "WIZARD_FIRE_SHIELD"),
        ]),
        "SPLPROT.2DA": make_2da(["STAT", "VALUE", "RELATION"], SPLPROT_BASE),
        "SPPR319.SPL": sum_ins,
        "SPPR517.SPL": ins_plg,
        "SPPR717.SPL": crp_doom,
        "SPWI418.SPL": fshield_red,
        "SPWI511.SPL": pfnw_spl,
        "SPWI605.SPL": death_spl,
        "SPPR704.SPL": nat_bty,
        "SPPR417.SPL": lesser_rest,
        "SPPR713.SPL": greater_rest,
        "SPIN912.SPL": drain_spl,
        "PFNWRING.ITM": pfnw_itm,
        "SHAD01.ITM": drain_itm,
    }
    fg = FakeGame(work, weidu, tlk=tlk, biff=biff)
    out = fg.install()
    assert installed_ok(out), out

    # Insects: main spells cast %spell%A; Stage A has undead + Fire Shield op318 immunities;
    # Stage B has damage ticks + Stoneskin op318 before %spell%C; Stage C has save vs. breath spell failure.
    for res, ov_save, ov_bonus, sf_pct, sf_bonus, has_fear in (
        ("SPPR319", SAVE_BREATH, -4, 50, 0, False),
        ("SPPR517", 0, 0, 100, -2, True),
        ("SPPR717", 0, 0, 100, -2, True),
    ):
        main = fg.spl(res)
        m_fx = main["abilities"][0]["effects"]
        assert len(m_fx) == 1
        assert m_fx[0]["opcode"] == 146 and m_fx[0]["resource"].upper() == f"{res}A"
        assert m_fx[0]["save"] == ov_save and m_fx[0]["bonus"] == ov_bonus

        st_a = fg.spl(f"{res}A")
        a_fx = st_a["abilities"][0]["effects"]
        assert [e["opcode"] for e in a_fx[:2]] == [318, 318]

        st_b = fg.spl(f"{res}B")
        b_fx = st_b["abilities"][0]["effects"]
        assert b_fx[-2]["opcode"] == 318 and b_fx[-2]["resource"].upper() == f"{res}C"
        assert b_fx[-1]["opcode"] == 177 and b_fx[-1]["resource"].upper() == f"{res}C"

        st_c = fg.spl(f"{res}C")
        c_fx = st_c["abilities"][0]["effects"]
        sf_fxs = [e for e in c_fx if e["opcode"] == 60]
        assert len(sf_fxs) == 2
        assert all(e["p1"] == sf_pct and e["save"] == SAVE_BREATH and e["bonus"] == sf_bonus for e in sf_fxs)
        assert any(e["opcode"] == 24 for e in c_fx) == has_fear

    assert "Saving Throw vs. Breath Weapon each round" in fg.tlk(fg.spl("SPPR319")["desc"])
    ip_desc = fg.tlk(fg.spl("SPPR517")["desc"])
    assert "1 point of damage each second" in ip_desc
    assert "Saving Throw vs. Breath Weapon at -2" in ip_desc
    assert "Saving Throw vs. Spell at -2 or run away in fear" in ip_desc
    assert "Saving Throw vs. Breath Weapon at -2" in fg.tlk(fg.spl("SPPR717")["desc"])

    # Fire Shield Red removes all 9 insect subspells via leading op321 and blocks %ins%A via op206
    fs = fg.spl("SPWI418")
    removed_subs = {e["resource"].upper() for e in fs["abilities"][0]["effects"] if e["opcode"] == 321}
    assert {
        "SPPR319A", "SPPR319B", "SPPR319C",
        "SPPR517A", "SPPR517B", "SPPR517C",
        "SPPR717A", "SPPR717B", "SPPR717C",
    }.issubset(removed_subs)
    blocked_subs = {e["resource"].upper() for e in fs["abilities"][0]["effects"] if e["opcode"] == 206}
    assert {"SPPR319A", "SPPR517A", "SPPR717A"}.issubset(blocked_subs)

    # PfNW spell (timed op120 p2=2) blocks %ins%B via op206 and removes %ins%A/B/C via op321
    pfnw = fg.spl("SPWI511")
    pfnw_206 = {e["resource"].upper() for e in pfnw["abilities"][0]["effects"] if e["opcode"] == 206}
    assert {"SPPR319B", "SPPR517B", "SPPR717B"}.issubset(pfnw_206)
    pfnw_321 = {e["resource"].upper() for e in pfnw["abilities"][0]["effects"] if e["opcode"] == 321}
    assert {"SPPR319A", "SPPR517A", "SPPR717A"}.issubset(pfnw_321)

    # Death Spell (SPWI605) casts CBMG605A and CBMG605B (which has projectile 158 and removes all 9 insect subspells)
    ds = fg.spl("SPWI605")
    assert [e["resource"].upper() for e in ds["abilities"][0]["effects"] if e["opcode"] == 148] == ["CBMG605A", "CBMG605B"]
    ds_b_raw = fg.file("override/CBMG605B.SPL")
    assert _ab_projectiles(ds_b_raw) == [158]
    ds_b = fg.spl("CBMG605B")
    ds_b_rem = {e["resource"].upper() for e in ds_b["abilities"][0]["effects"] if e["opcode"] == 321}
    assert {"SPPR319A", "SPPR517A", "SPPR717A"}.issubset(ds_b_rem)

    # Lesser Restoration (SPPR417) stays cleric-only (0x20 = 0x8000), removes drain sectype via op221,
    # and SPIN912.SPL extracted its STR drain into CBDRN1.SPL with matching sectype while keeping op12 damage
    lr_raw = fg.file("override/SPPR417.SPL")
    assert struct.unpack_from("<H", lr_raw, 0x20)[0] == 0x8000
    lr = fg.spl("SPPR417")
    op221_fx = [e for e in lr["abilities"][0]["effects"] if e["opcode"] == 221]
    assert len(op221_fx) == 1
    drain_sec = op221_fx[0]["p2"]
    assert "ability score drain" in fg.tlk(lr["desc"])
    s912 = fg.spl("SPIN912")
    assert [(e["opcode"], e["resource"].upper()) for e in s912["abilities"][0]["effects"]] == [
        (12, ""),
        (146, "CBDRN1"),
    ]
    cbdrn1_raw = fg.file("override/CBDRN1.SPL")
    assert cbdrn1_raw[0x27] == drain_sec
    cbdrn1 = fg.spl("CBDRN1")
    assert [e["opcode"] for e in cbdrn1["abilities"][0]["effects"]] == [44, 142]

    # Nature's Beauty: keeps op55 (save vs. spell +3) and caster op215; casts schoolless area
    # subspell CBMGNB1 (target=1 on op146; CBMGNB1 has school=0, target=5, projectile=159,
    # failed-save permanent blindness with timing=0 duration=999999 + op318, and 3-round blindness
    # with timing=0 duration=18 for targets that save).
    nb = fg.spl("SPPR704")
    nb_fx = nb["abilities"][0]["effects"]
    assert [(e["opcode"], e["target"], e["resource"].lower(), e["save"], e["bonus"]) for e in nb_fx] == [
        (55, 2, "", SAVE_SPELL, 3),
        (215, 1, "icclkfr2", 0, 0),
        (146, 1, "cbmgnb1", 0, 0),
    ]
    nb1_raw = fg.file("override/CBMGNB1.SPL")
    assert nb1_raw[0x25] == 0
    assert _ab_projectiles(nb1_raw) == [159]
    nb1 = fg.spl("CBMGNB1")
    assert nb1["abilities"][0]["target"] == 5
    nb1_fx = nb1["abilities"][0]["effects"]
    assert any(e["opcode"] == 74 and e["timing"] == 0 and e["duration"] == 999999 and e["save"] == SAVE_SPELL and e["bonus"] == 3 for e in nb1_fx)
    assert any(e["opcode"] == 318 and e["resource"].lower() == "cbmgnb1" and e["save"] == SAVE_SPELL and e["bonus"] == 3 for e in nb1_fx)
    assert any(e["opcode"] == 74 and e["timing"] == 0 and e["duration"] == 18 and e["save"] == 0 for e in nb1_fx)
    assert "blinded for 3 rounds" in fg.tlk(nb["desc"])

    # Idempotence check
    snap = fg.tree()
    out2 = fg.install()
    assert installed_ok(out2), out2
    assert fg.tree() == snap


@test
def scs_mod_variations_and_scs_coexistence(work, weidu):
    """Verify compatibility with pre-existing SCS patches and unrelated mod effects
    (casting features, extra ability effects, pre-patched SCS Nature's Beauty / Insects)."""
    tlk = make_tlk([""])
    # Mantle with casting feature + extra mod effect (op142 icon)
    mantle_mod = make_spl(
        level=7, school=1,
        casting=[{"opcode": 215, "target": 1, "duration": 2, "resource": "MODVFX"}],
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 120, "target": 1, "power": 7, "p1": 2, "p2": 0, "duration": 24, "dispel": 3},
            {"opcode": 142, "target": 1, "power": 7, "p2": 70, "duration": 24, "dispel": 3},
        ]}],
    )
    # SCS-patched Nature's Beauty (op74 already moved to dw#nbsub.spl with duration=999999) + foreign op146
    nb_scs = make_spl(
        spell_type=2, level=7, school=5,
        abilities=[{"min_level": 1, "target": 5, "projectile": 159, "effects": [
            {"opcode": 55, "power": 7, "p1": 1, "p2": 3, "timing": 1, "save": SAVE_SPELL, "bonus": 3, "dispel": 1},
            {"opcode": 146, "target": 1, "power": 7, "p2": 1, "timing": 1, "resource": "dw#nbsub"},
            {"opcode": 146, "target": 1, "power": 7, "p2": 1, "timing": 1, "resource": "MODNBSPL"},
        ]}],
    )
    nb_scs_sub = make_spl(
        spell_type=2, level=7, school=0,
        abilities=[{"min_level": 1, "target": 1, "projectile": 1, "effects": [
            {"opcode": 74, "power": 7, "timing": 0, "duration": 999999, "dispel": 1},
            {"opcode": 142, "power": 7, "p2": 8, "timing": 0, "duration": 999999, "dispel": 1},
        ]}],
    )
    # SCS-patched Insect Plague (already has op146 -> SPPR517A and valid SPPR517A.SPL)
    ins_scs = make_spl(
        spell_type=2, level=5, school=2,
        abilities=[{"min_level": 1, "target": 1, "projectile": 228, "effects": [
            {"opcode": 146, "target": 2, "p2": 1, "timing": 1, "resource": "sppr517a"},
        ]}],
    )
    ins_scs_a = make_spl(
        spell_type=2, level=1, school=0,
        abilities=[{"min_level": 1, "target": 1, "effects": [
            {"opcode": 318, "target": 2, "p2": 1, "duration": 1, "resource": "sppr517a"},
            {"opcode": 318, "target": 2, "p2": 6, "duration": 1, "resource": "sppr517a"},
            {"opcode": 233, "target": 2, "p1": 1, "p2": 120, "duration": 36},
            {"opcode": 177, "target": 2, "p2": 2, "timing": 1, "resource": "sppr517b"},
        ]}],
    )
    # Skull Trap with custom 1/10/15 layout (no min_level=12 ability) -> must cap 15d6 to 12d6 in place
    skull_custom = make_spl(
        level=3, school=7,
        abilities=[
            {"min_level": lvl, "target": 4, "projectile": 96, "effects": [
                {"opcode": 12, "p2": 0x400000, "timing": 1, "dice": max(5, lvl), "sides": 6,
                 "save": SAVE_SPELL, "special": 0x100},
            ]}
            for lvl in [1, 10, 15]
        ],
    )
    # Chromatic Orb with foreign mod effect (op206) -> must preserve op206 on rebuilt abilities
    chrom_mod = make_spl(
        level=1, school=6,
        abilities=[
            {"min_level": 1, "projectile": 24, "effects": [
                {"opcode": 12, "p2": 0x400000, "timing": 1, "dice": 1, "sides": 4},
                {"opcode": 206, "target": 2, "duration": 6, "resource": "MODORB"},
            ]},
        ],
    )
    # Defensive Harmony with specific AC modifier (p2=1, slashing +1) alongside general AC (p2=0, +2)
    dh_mod = make_spl(
        spell_type=2, level=4, school=4,
        abilities=[{"min_level": 1, "target": 5, "effects": [
            {"opcode": 0, "power": 4, "p1": 2, "p2": 0, "duration": 36, "dispel": 3},
            {"opcode": 0, "power": 4, "p1": 1, "p2": 1, "duration": 36, "dispel": 3},
        ]}],
    )
    biff = {
        "SPELL.IDS": make_ids([
            (2118, "WIZARD_CHROMATIC_ORB"),
            (2313, "WIZARD_SKULL_TRAP"),
            (2708, "WIZARD_MANTLE"),
            (1406, "CLERIC_DEFENSIVE_HARMONY"),
            (1704, "CLERIC_NATURE_BEAUTY"),
            (1517, "CLERIC_INSECT_PLAGUE"),
        ]),
        "SPLSTATE.IDS": make_ids([(29, "FREE_ACTION")]),
        "STATS.IDS": make_ids([
            (88, "STONESKINS"),
            (120, "CLERIC_INSECT_PLAGUE"),
            (125, "WIZARD_FIRE_SHIELD"),
            (131, "CLERIC_FREE_ACTION"),
            (181, "WIZARD_PROTECTION_FROM_NORMAL_WEAPONS"),
        ]),
        "SPLPROT.2DA": make_2da(["STAT", "VALUE", "RELATION"], SPLPROT_BASE),
        "SPWI118.SPL": chrom_mod,
        "SPWI313.SPL": skull_custom,
        "SPWI708.SPL": mantle_mod,
        "SPPR406.SPL": dh_mod,
        "SPPR704.SPL": nb_scs,
        "DW#NBSUB.SPL": nb_scs_sub,
        "SPPR517.SPL": ins_scs,
        "SPPR517A.SPL": ins_scs_a,
        "DUMMY.ITM": make_itm([[]]),
    }
    fg = FakeGame(work, weidu, tlk=tlk, biff=biff)
    out = fg.install()
    assert installed_ok(out), out

    # Custom Skull Trap kept its min_level=15 ability and capped dice at 12
    st = fg.spl("SPWI313")
    assert [a["min_level"] for a in st["abilities"]] == [1, 10, 15]
    assert [a["effects"][0]["dice"] for a in st["abilities"]] == [5, 10, 12]

    # Chromatic Orb preserved foreign op206 on all 6 abilities
    co = fg.spl("SPWI118")
    for a in co["abilities"]:
        assert any(e["opcode"] == 206 and e["resource"] == "MODORB" for e in a["effects"])

    # Defensive Harmony updated only p2=0 to 4 and left p2=1 at 1
    dh = fg.spl("SPPR406")
    assert [(e["p1"], e["p2"]) for e in dh["abilities"][0]["effects"] if e["opcode"] == 0] == [(4, 0), (1, 1)]

    # Mantle kept its casting feature and extra op142 effect while gaining +3 weapon immunity
    m = fg.spl("SPWI708")
    assert len(m["casting"]) == 1 and m["casting"][0]["resource"] == "MODVFX"
    m_ops = [(e["opcode"], e["p1"], e["p2"]) for e in m["abilities"][0]["effects"]]
    assert (120, 3, 0) in m_ops and (142, 0, 70) in m_ops

    # SCS Nature's Beauty upgraded to CBMGNB1 (permanent timing=0 duration=999999 + 18s) and kept foreign op146
    nb_patched = fg.spl("SPPR704")
    nb_res = [e["resource"].upper() for e in nb_patched["abilities"][0]["effects"] if e["opcode"] == 146]
    assert nb_res == ["MODNBSPL", "CBMGNB1"]
    nb1 = fg.spl("CBMGNB1")
    assert any(e["opcode"] == 74 and e["timing"] == 0 and e["duration"] == 999999 for e in nb1["abilities"][0]["effects"])
    assert any(e["opcode"] == 74 and e["timing"] == 0 and e["duration"] == 18 for e in nb1["abilities"][0]["effects"])

    # Pre-patched Insect Plague recognized as already done
    assert "CLERIC_INSECT_PLAGUE (SPPR517): changed 0, already 1." in out




