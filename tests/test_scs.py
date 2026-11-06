"""Tests for the SCS spell changes in chriz-bg-magic (cbmagic_scs.tpa)."""
import struct

from fakegame import FakeGame, installed_ok
from harness import test
from ie import SAVE_BREATH, SAVE_SPELL, make_2da, make_ids, make_itm, make_spl, make_tlk


def _spl_with_excl(data, excl=0, cast_gfx=0, priest_type=0):
    b = bytearray(data)
    struct.pack_into("<I", b, 0x1E, excl)
    struct.pack_into("<H", b, 0x20, priest_type)
    struct.pack_into("<H", b, 0x22, cast_gfx)
    return bytes(b)


def _itm_with_fields(data, usab=0, ench=0):
    b = bytearray(data)
    struct.pack_into("<I", b, 0x1E, usab)
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
            (2325, "WIZARD_MELFS_MINUTE_METEORS"),
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
            usab=0x0100,
        ),
    }
    fg = FakeGame(work, weidu, tlk=tlk, biff=biff)
    out = fg.install()
    assert installed_ok(out), out

    # 1. Chromatic Orb: 6 abilities (1, 2, 3, 4, 5, 7), no petrify/slay, l7 has 2d8 (no save) + hold 78s
    co = fg.spl("SPWI118")
    assert [a["min_level"] for a in co["abilities"]] == [1, 2, 3, 4, 5, 7]
    for a in co["abilities"]:
        assert all(e["opcode"] not in (55, 134) for e in a["effects"])
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

    # 5. Power Word, Silence: school 4, excl 0x0080, scroll usab 0x0080
    pws_raw = fg.file("override/SPWI612.SPL")
    assert pws_raw[0x25] == 4
    assert struct.unpack_from("<I", pws_raw, 0x1E)[0] == 0x0080
    scrl_raw = fg.file("override/SCRL7P.ITM")
    assert struct.unpack_from("<I", scrl_raw, 0x1E)[0] == 0x0080
    assert "(Enchantment/Charm)" in fg.tlk(fg.itm_descs("SCRL7P")[1])

    # 6. Power Word, Stun: school 4, excl 0x0080, leading op324 Free Action immunities
    pwst_raw = fg.file("override/SPWI715.SPL")
    assert pwst_raw[0x25] == 4
    assert struct.unpack_from("<I", pwst_raw, 0x1E)[0] == 0x0080
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
        "Symbol, Death\nThe symbol will remain there until someone comes too close, at which point it will explode, causing all those within the area to make a Save vs. Death or die.",
        # 6: Symbol, Stun
        "Symbol, Stun\nThe symbol will remain there until someone comes too close, at which point it will explode, causing all those within the area to make a Save vs. Spell at a -4 penalty or be stunned for 2 rounds + 1 round for every 3 levels of the caster.",
        # 7: Symbol, Fear
        "Symbol, Fear\nThe symbol will remain there until someone comes too close, at which point it will explode, causing all those within the area to make a Save vs. Spell at a -4 penalty or be affected by fear for 2 rounds + 1 round for every 3 levels of the caster.",
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
            {"opcode": 144, "target": 1, "p2": 13, "timing": 9},  # e.g. from SCS; should be removed for Simulacrum
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
    sym_death = make_spl(
        level=8, school=2, desc=5,
        abilities=[{"min_level": 1, "target": 4, "projectile": 225, "effects": [
            {"opcode": 13, "power": 8, "p2": 4, "timing": 1, "save": 4},
        ]}],
    )
    sym_stun = make_spl(
        level=8, school=2, desc=6,
        abilities=[{"min_level": 1, "target": 4, "projectile": 225, "effects": [
            {"opcode": 45, "power": 8, "duration": 18, "save": SAVE_SPELL, "bonus": -4},
        ]}],
    )
    sym_fear = make_spl(
        level=8, school=2, desc=7,
        abilities=[{"min_level": 1, "target": 4, "projectile": 225, "effects": [
            {"opcode": 24, "power": 8, "duration": 18, "save": SAVE_SPELL, "bonus": -4},
        ]}],
    )
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
        "SPWI817.SPL": sym_death,
        "SPWI816.SPL": sym_stun,
        "SPWI811.SPL": sym_fear,
        "SPWI907.SPL": abs_imm,
        "SPWI912.SPL": pw_kill,
        "SPPR719.SPL": sym_death,
        "SPPR718.SPL": sym_stun,
        "SPPR706.SPL": sym_fear,
        "SCRL9U.ITM": _itm_with_fields(
            make_itm([[
                {"opcode": 146, "resource": "SPWI912"},
                {"opcode": 147, "resource": "SPWI912"},
            ]], desc=4),
            usab=0x0100,
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

    # Power Word, Blind: school 4, excl 0x0080, projectile 1
    pwb_raw = fg.file("override/SPWI815.SPL")
    assert pwb_raw[0x25] == 4
    assert struct.unpack_from("<I", pwb_raw, 0x1E)[0] == 0x0080
    assert _ab_projectiles(pwb_raw) == [1]
    pwb = fg.spl("SPWI815")
    assert "Area of Effect: 1 creature" in fg.tlk(pwb["desc"])
    assert "(Enchantment/Charm)" in fg.tlk(pwb["desc"])

    # Power Word, Kill: school 4, excl 0x0080
    pwk_raw = fg.file("override/SPWI912.SPL")
    assert pwk_raw[0x25] == 4
    assert struct.unpack_from("<I", pwk_raw, 0x1E)[0] == 0x0080

    # Simulacrum: buttons 9, 11, 12 disabled, button 13 NOT disabled
    sim = fg.spl("SIMULACR")
    sim_btns = {e["p2"] for e in sim["abilities"][0]["effects"] if e["opcode"] == 144}
    assert {0, 9, 11, 12, 14}.issubset(sim_btns)
    assert 13 not in sim_btns

    # All 6 Symbols: projectile 326, enemy-only description, and Symbol Stun has Free Action immunity
    for res in ("SPWI817", "SPWI816", "SPWI811", "SPPR719", "SPPR718", "SPPR706"):
        raw = fg.file(f"override/{res}.SPL")
        assert _ab_projectiles(raw) == [326], res
        parsed = fg.spl(res)
        assert "until an opponent comes too close" in fg.tlk(parsed["desc"])
        assert "causing all enemies within" in fg.tlk(parsed["desc"])
    for stun_res in ("SPWI816", "SPPR718"):
        parsed = fg.spl(stun_res)
        assert [e["opcode"] for e in parsed["abilities"][0]["effects"][:2]] == [324, 324]
        assert "Free Action protects" in fg.tlk(parsed["desc"])

    # Idempotence check
    snap = fg.tree()
    out2 = fg.install()
    assert installed_ok(out2), out2
    assert fg.tree() == snap

