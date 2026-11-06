"""Tests for chriz-bg-magic's more batch (cbmagic_more.tpa):
1. Priest Protection From Cold (level 3) and Protection From Acid (level 4) via ADD_SPELL
2. Dispelling Screen replacing Spell Immunity (SPWI510, SPWI590..597, SCRL6S, Breach, Dispel, Pierce Shield, Spellstrike)
3. Nahal's Reckless Dweomer (SPWI124) without Aura Cleansing
"""
import struct

import fakegame as fg
import fixtures as fx
import ie
from harness import check, test

BASE_STRREF = len(fx.TEXTS)
MORE_TEXTS = [
    # +0: Spell Immunity name
    "Spell Immunity",
    # +1: Spell Immunity desc
    "Spell Immunity\n(Abjuration)\n\nLevel: 5\nRange: 0\nDuration: 1 round/level\nCasting Time: 5\n"
    "Area of Effect: The caster\nSaving Throw: None\n\n"
    "Casting this spell grants the wizard protection from one spell school of <PRO_HISHER> choice.",
    # +2: Pierce Shield desc
    "Pierce Shield\n(Abjuration) \n\nLevel: 8\nRange: 40 ft.\nDuration: Instant\nCasting Time: 8\n"
    "Area of Effect: 1 creature\nSaving Throw: None \n\n"
    "The list of spells that this includes: Minor Spell Deflection, Minor Spell Turning, Spell Deflection, "
    "Minor Globe of Invulnerability, Spell Immunity, Globe Of Invulnerability, Spell Turning, Spell Shield, and Spell Trap.",
    # +3: Spellstrike desc
    "Spellstrike\n(Abjuration)\n\nLevel: 9\nRange: 80 ft.\nDuration: Instant\nCasting Time: 5\n"
    "Area of Effect: 1 creature\nSaving Throw: None \n\n"
    "When this spell is cast at a target creature, it will dispel all of the magical protections that surround "
    "that creature. This includes Minor Spell Turning, Minor Globe of Invulnerability, Spell Immunity, "
    "Globe Of Invulnerability, Minor Spell Deflection, Spell Turning, Spell Shield, Spell Deflection, and Spell Trap.",
    # +4: Nahal's Reckless Dweomer desc
    "Nahal's Reckless Dweomer\n(Invocation/Evocation)\n\nLevel: 1\nRange: Special\nDuration: Special\n"
    "Casting Time: Special\nArea of Effect: Special\nSaving Throw: Special\n\n"
    "This spell is the Wild Mage's ultimate last-resort spell.",
]
(
    SI_NAME,
    SI_DESC,
    PIERCE_SHIELD_DESC,
    SPELLSTRIKE_DESC,
    NAHAL_DESC,
) = range(BASE_STRREF, BASE_STRREF + len(MORE_TEXTS))

MORE_SYMBOLS = [
    *fx.SPELL_SYMBOLS,
    (1303, "CLERIC_DISPEL_MAGIC"),
    (2124, "WIZARD_NAHALS_RECKLESS_DWEOMER"),
    (2302, "WIZARD_REMOVE_MAGIC"),
    (2326, "WIZARD_TRUE_DISPEL_MAGIC"),
    (2510, "WIZARD_SPELL_IMMUNITY"),
    (2513, "WIZARD_BREACH"),
    (2590, "WIZARD_SPELL_IMMUNITY_ABJURATION"),
    (2591, "WIZARD_SPELL_IMMUNITY_CONJURATION"),
    (2592, "WIZARD_SPELL_IMMUNITY_DIVINATION"),
    (2593, "WIZARD_SPELL_IMMUNITY_ENCHANTMENT"),
    (2594, "WIZARD_SPELL_IMMUNITY_ILLUSIONIST"),
    (2595, "WIZARD_SPELL_IMMUNITY_INVOCATION"),
    (2596, "WIZARD_SPELL_IMMUNITY_NECROMANCY"),
    (2597, "WIZARD_SPELL_IMMUNITY_ALTERATION"),
    (2805, "WIZARD_PIERCE_SHIELD"),
    (2903, "WIZARD_SPELL_STRIKE"),
]

MSECTYPE_2DA = (
    b"2DA V1.0\r\n4294967296\r\n            RES_REF\r\n"
    b"None        4294967296\r\n"
    b"SpellProtections        27980\r\n"
    b"SpecificProtections     27981\r\n"
    b"IllusionaryProtections  27982\r\n"
    b"MagicAttack             27983\r\n"
    b"DivinationAttack        27984\r\n"
    b"Conjuration             27986\r\n"
    b"CombatProtections       34558\r\n"
    b"Contingency             34559\r\n"
    b"Battleground            34560\r\n"
    b"OffensiveDamage         34561\r\n"
    b"Disabling               34562\r\n"
    b"Combination             34564\r\n"
    b"Non-combat              34565\r\n"
)

STATDESC_2DA = (
    f"2DA V1.0\r\n****\r\n    DESCRIPTION BAM_FILE\r\n"
    f"24  7566        ****\r\n"
    f"25  7565        ****\r\n"
    f"106 14790       ****\r\n"
    f"107 {SI_NAME}   ****\r\n"
).encode("latin-1")


def make_spl_with_excl(spell_type, level, abilities, excl=0, priest_excl=0, icon="", **kw):
    raw = bytearray(ie.make_spl(spell_type, level, abilities, **kw))
    struct.pack_into("<H", raw, 0x1E, excl)
    struct.pack_into("<H", raw, 0x20, priest_excl)
    if icon:
        raw[0x3A:0x42] = icon.encode("ascii").ljust(8, b"\x00")[:8]
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


def make_more_biff():
    biff = fx.game()
    biff.update({
        "SPELL.IDS": ie.make_ids(MORE_SYMBOLS),
        "MSECTYPE.2DA": MSECTYPE_2DA,
        "STATDESC.2DA": STATDESC_2DA,
        # Vanilla SPWI510 (Spell Immunity menu wrapper: target=7, ctime=0, op214 -> SpWi510)
        "SPWI510.SPL": make_spl_with_excl(
            1, 5,
            [{
                "target": 7, "range": 1, "min_level": 1, "casting_time": 0, "projectile": 1,
                "effects": [
                    fx.fx(opcode=214, target=1, power=5, p1=0, p2=0, timing=1, dispel=3, resource="SpWi510"),
                    fx.fx(opcode=141, target=1, power=5, p1=0, p2=14, timing=1, dispel=2),
                    fx.fx(opcode=174, target=1, power=5, p1=0, p2=0, timing=1, dispel=3, resource="EFF_M02"),
                ],
            }],
            name=SI_NAME, desc=SI_DESC, school=0, sectype=1, excl=0x2000, icon="SPWI510C",
        ),
        "SCRL6S.ITM": fx.scroll("SPWI510", SI_DESC),
        # Vanilla SPWI513 (Breach)
        "SPWI513.SPL": make_spl_with_excl(
            1, 5,
            [{
                "target": 1, "range": 40, "min_level": 1, "casting_time": 5, "projectile": 221,
                "effects": [
                    fx.fx(opcode=221, target=2, power=5, p1=9, p2=2, timing=1, dispel=2),
                    fx.fx(opcode=215, target=2, power=5, p1=0, p2=0, timing=1, dispel=2, resource="SPATTCK1"),
                    fx.fx(opcode=240, target=2, power=5, p1=0, p2=28, timing=1, dispel=2),
                    fx.fx(opcode=139, target=2, power=5, p1=40690, p2=0, timing=1, dispel=2),
                    fx.fx(opcode=221, target=2, power=5, p1=9, p2=7, timing=1, dispel=2),
                ],
            }],
            school=1, sectype=4, excl=0x2000, icon="SPWI513C",
        ),
        # Vanilla SPWI302 (Remove Magic) and SPPR303 (Dispel Magic) and TROLLREG (self-only op58)
        "SPWI302.SPL": ie.make_spl(
            1, 3,
            [{
                "target": 4, "range": 40, "min_level": 1, "casting_time": 3, "projectile": 177,
                "effects": [
                    fx.fx(opcode=58, target=2, power=0, p1=0, p2=0x20001, timing=1),
                    fx.fx(opcode=139, target=2, power=0, p1=14056, p2=0, timing=1),
                ],
            }],
            school=1, sectype=0,
        ),
        "SPPR303.SPL": ie.make_spl(
            2, 3,
            [{
                "target": 4, "range": 40, "min_level": 1, "casting_time": 6, "projectile": 158,
                "effects": [
                    fx.fx(opcode=58, target=2, power=0, p1=0, p2=0x20001, timing=1),
                    fx.fx(opcode=139, target=2, power=0, p1=14056, p2=0, timing=1),
                ],
            }],
            school=1, sectype=0,
        ),
        "TROLLREG.SPL": ie.make_spl(
            1, 1,
            [{
                "target": 5, "range": 1, "min_level": 1, "casting_time": 0, "projectile": 1,
                "effects": [
                    fx.fx(opcode=58, target=1, power=0, p1=99, p2=0, timing=1),
                ],
            }],
        ),
        # Vanilla SPWI805 (Pierce Shield, 5 abilities) and SPWI903 (Spellstrike)
        "SPWI805.SPL": ie.make_spl(
            1, 8,
            [
                {
                    "form": 2, "target": 1, "range": 40, "min_level": ml, "casting_time": 8, "projectile": 221,
                    "effects": [
                        fx.fx(opcode=166, target=2, power=8, p1=-26, p2=0, timing=0, duration=96, dispel=2),
                        fx.fx(opcode=230, target=2, power=8, p1=9, p2=1, timing=1, dispel=2),
                    ],
                }
                for ml in (1, 17, 18, 19, 20)
            ],
            desc=PIERCE_SHIELD_DESC, school=1, sectype=4,
        ),
        "SCRL9A.ITM": fx.scroll("SPWI805", PIERCE_SHIELD_DESC),
        "SPWI903.SPL": ie.make_spl(
            1, 9,
            [{
                "form": 2, "target": 1, "range": 80, "min_level": 1, "casting_time": 5, "projectile": 221,
                "effects": [
                    fx.fx(opcode=221, target=2, power=9, p1=9, p2=1, timing=1, dispel=2),
                    fx.fx(opcode=139, target=2, power=9, p1=40690, p2=1, timing=1, dispel=2),
                ],
            }],
            desc=SPELLSTRIKE_DESC, school=1, sectype=4,
        ),
        "SCRL9M.ITM": fx.scroll("SPWI903", SPELLSTRIKE_DESC),
        # Vanilla SPWI124 (Nahal's Reckless Dweomer: target=7, ctime=5, op214 p2=2, op280 p2=1)
        "SPWI124.SPL": make_spl_with_excl(
            1, 1,
            [{
                "target": 7, "range": 30, "min_level": 1, "casting_time": 5, "projectile": 1,
                "effects": [
                    fx.fx(opcode=214, target=1, power=0, p1=0, p2=2, timing=1, dispel=2),
                    fx.fx(opcode=280, target=1, power=0, p1=0, p2=1, timing=1, dispel=2),
                ],
            }],
            desc=NAHAL_DESC, school=6, excl=0x7FC0, icon="SPWI124C",
        ),
    })
    # Add SPWI590..SPWI597 (the 8 school subspells of Spell Immunity)
    for idx, school_id in enumerate(range(1, 9)):
        res = f"SPWI59{idx}.SPL"
        biff[res] = ie.make_spl(
            1, 5,
            [
                {
                    "target": 5, "range": 1, "min_level": ml, "casting_time": 5, "projectile": 1,
                    "effects": [
                        fx.fx(opcode=204, target=1, power=5, p1=0, p2=school_id, timing=0, duration=54),
                        fx.fx(opcode=142, target=1, power=5, p1=0, p2=196 + idx, timing=0, duration=54),
                    ],
                }
                for ml in [1, *range(10, 21)]
            ],
            school=1, sectype=1,
        )
    return biff


@test
def more_batch_on_vanilla_shaped_inputs(work, weidu):
    tlk = ie.make_tlk(fx.TEXTS + MORE_TEXTS)
    g = fg.FakeGame(work, weidu, tlk=tlk, biff=make_more_biff())
    before = g.tree()
    out = g.install()
    check(fg.installed_ok(out) and not fg.with_warnings(out), f"expected clean install:\n{out}")

    # --- Row 1: Priest Protection From Cold (level 3) & Protection From Acid (level 4) ---
    spell_ids = g.file("override/SPELL.IDS").decode("latin-1")
    check("CLERIC_CBMAGIC_PROTECTION_FROM_COLD" in spell_ids, spell_ids)
    check("CLERIC_CBMAGIC_PROTECTION_FROM_ACID" in spell_ids, spell_ids)

    pcold_raw = g.file("override/SPPR301.SPL")
    check(pcold_raw is not None, "expected SPPR301.SPL (Protection From Cold)")
    pcold = parse_spl_full(pcold_raw)
    check(pcold["type"] == 2 and pcold["level"] == 3 and pcold["school"] == 1 and pcold["sectype"] == 2, pcold)
    check(pcold["priest_excl"] == 0, "expected usable by both clerics and druids (0x20 == 0)")
    check(pcold["icon"] == "SPWI320C", pcold["icon"])
    check(g.tlk(pcold["name"]) == "Protection From Cold", g.tlk(pcold["name"]))
    check("absorbing 80% of all the damage dealt by such magical sources" in g.tlk(pcold["desc"]), g.tlk(pcold["desc"]))
    check(len(pcold["abilities"]) == 20, len(pcold["abilities"]))
    for idx, ab in enumerate(pcold["abilities"]):
        lvl = idx + 1
        dur = 18 + 6 * lvl
        check(
            ab["location"] == 2 and ab["min_level"] == lvl and ab["casting_time"] == 6
            and ab["target"] == 1 and ab["range"] == 1 and ab["icon"] == "SPWI320B",
            ab,
        )
        ops = [(e["opcode"], e["p1"], e["p2"], e["duration"], e["resource"].upper()) for e in ab["effects"]]
        check(ops[0] == (321, 0, 0, 0, "SPPR301"), ops[0])
        check((85, 80, 0, dur, "") in ops, ops)
        check((28, 100, 0, dur, "") in ops, ops)
        check((139, 7565, 0, 0, "") in ops, ops)
        check((142, 0, 25, dur, "") in ops, ops)
        check((328, 0, 65, dur, "") in ops, ops)
        check((174, 0, 0, dur, "EFF_E04") in ops, ops)
        check((215, 0, 1, 1, "ICRMPARI") in ops, ops)

    pacid_raw = g.file("override/SPPR401.SPL")
    check(pacid_raw is not None, "expected SPPR401.SPL (Protection From Acid)")
    pacid = parse_spl_full(pacid_raw)
    check(pacid["type"] == 2 and pacid["level"] == 4 and pacid["school"] == 1 and pacid["sectype"] == 2, pacid)
    check(pacid["priest_excl"] == 0, "expected usable by both clerics and druids (0x20 == 0)")
    check(pacid["icon"] == "SPWI517C", pacid["icon"])
    check(g.tlk(pacid["name"]) == "Protection From Acid", g.tlk(pacid["name"]))
    check("5 rounds/level" in g.tlk(pacid["desc"]) and "Melf's Acid Arrow" in g.tlk(pacid["desc"]), g.tlk(pacid["desc"]))
    expected_acid_lvls = [1, *range(8, 19)]
    check([ab["min_level"] for ab in pacid["abilities"]] == expected_acid_lvls, pacid["abilities"])
    for idx, ab in enumerate(pacid["abilities"]):
        eff_lvl = 7 if idx == 0 else ab["min_level"]
        dur = eff_lvl * 30
        check(
            ab["location"] == 2 and ab["casting_time"] == 7 and ab["target"] == 1
            and ab["range"] == 1 and ab["icon"] == "SPWI517B",
            ab,
        )
        ops = [(e["opcode"], e["p1"], e["p2"], e["duration"], e["resource"].upper()) for e in ab["effects"]]
        check((27, 100, 1, dur, "") in ops, ops)
        check((142, 0, 24, dur, "") in ops, ops)
        check((328, 0, 65, dur, "") in ops, ops)
        check((174, 0, 0, dur, "EFF_E04") in ops, ops)
        check((215, 0, 1, 1, "ICRMPARI") in ops, ops)

    # --- Row 2: Dispelling Screen replacing Spell Immunity ---
    check("2510 WIZARD_DISPELLING_SCREEN" in spell_ids and "2510 WIZARD_SPELL_IMMUNITY" in spell_ids, spell_ids)
    msectype_txt = g.file("override/MSECTYPE.2DA").decode("latin-1")
    check("cbm_DispelScreen" in msectype_txt, msectype_txt)

    ds = parse_spl_full(g.file("override/SPWI510.SPL"))
    ds_sectype = ds["sectype"]
    check(ds_sectype >= 14 and ds["school"] == 1 and ds["level"] == 5, ds)
    check(g.tlk(ds["name"]) == "Dispelling Screen", g.tlk(ds["name"]))
    check("5 turns" in g.tlk(ds["desc"]) and "Pierce Shield and Spellstrike" in g.tlk(ds["desc"]), g.tlk(ds["desc"]))
    check(len(ds["abilities"]) == 1, ds["abilities"])
    ds_ab = ds["abilities"][0]
    check(ds_ab["target"] == 5 and ds_ab["casting_time"] == 5 and ds_ab["projectile"] == 158, ds_ab)
    ds_ops = [(e["opcode"], e["p1"], e["p2"], e["duration"], e["dispel"], e["resource"].upper()) for e in ds_ab["effects"]]
    check((321, 0, 0, 0, 2, "SPWI510") in ds_ops, ds_ops)
    check((206, -1, 0, 300, 2, "SPWI513B") in ds_ops, ds_ops)
    check((101, 0, 58, 300, 2, "") in ds_ops, ds_ops)
    check((267, 14056, 0, 300, 2, "") in ds_ops, ds_ops)
    check(any(o[0] == 142 and o[2] != 107 for o in ds_ops), f"Dispelling Screen needs its own effect-list row, not Spell Immunity: {ds_ops}")
    check((215, 0, 1, 300, 2, "SPTURNI2") in ds_ops, ds_ops)

    # Scroll SCRL6S.ITM updated
    scrl6s_raw = g.file("override/SCRL6S.ITM")
    scrl_n2, = struct.unpack_from("<i", scrl6s_raw, 0x0C)
    check(g.tlk(scrl_n2) == "Dispelling Screen", g.tlk(scrl_n2))
    check("5 turns" in g.tlk(g.itm_descs("SCRL6S")[1]), g.tlk(g.itm_descs("SCRL6S")[1]))

    # SPWI590..SPWI597 redirected to cast SPWI510
    for idx in range(8):
        sub = parse_spl_full(g.file(f"override/SPWI59{idx}.SPL"))
        check(len(sub["abilities"]) == 1, sub["abilities"])
        sub_ab = sub["abilities"][0]
        check(sub_ab["target"] == 5 and sub_ab["casting_time"] == 5 and sub_ab["projectile"] == 1, sub_ab)
        check(len(sub_ab["effects"]) == 1, sub_ab["effects"])
        ef = sub_ab["effects"][0]
        check(ef["opcode"] == 146 and ef["target"] == 1 and ef["p2"] == 1 and ef["resource"].upper() == "SPWI510", ef)

    # Breach split into SPWI513 -> SPWI513B + SPWI513C
    br = parse_spl_full(g.file("override/SPWI513.SPL"))
    br_ops = [(e["opcode"], e["p2"], e["resource"].upper()) for e in br["abilities"][0]["effects"]]
    check(br_ops == [(146, 1, "SPWI513B"), (146, 1, "SPWI513C")], br_ops)
    br_b = parse_spl_full(g.file("override/SPWI513B.SPL"))
    check(br_b["sectype"] == 0 and br_b["abilities"][0]["projectile"] == 1, br_b)
    br_b_ops = [(e["opcode"], e["p1"], e["p2"]) for e in br_b["abilities"][0]["effects"]]
    check((221, 9, 2) in br_b_ops and (221, 9, 7) in br_b_ops, br_b_ops)
    br_c = parse_spl_full(g.file("override/SPWI513C.SPL"))
    br_c_ops = [(e["opcode"], e["p1"], e["p2"]) for e in br_c["abilities"][0]["effects"]]
    check(br_c_ops == [(221, 9, ds_sectype)], br_c_ops)

    # Dispel Magic (SPWI302, SPPR303) gets trailing op221 for ds_sectype; self-only TROLLREG does not
    for d_res in ("SPWI302", "SPPR303"):
        d_spl = g.spl(d_res)
        d_ops = [(e["opcode"], e["p1"], e["p2"]) for e in d_spl["abilities"][0]["effects"]]
        check(d_ops[-1] == (221, 9, ds_sectype), (d_res, d_ops))
    check(g.file("override/TROLLREG.SPL") is None, "self-only TROLLREG should not be modified")

    # Pierce Shield (SPWI805) and Spellstrike (SPWI903) remove ds_sectype and update descriptions
    ps = g.spl("SPWI805")
    check(len(ps["abilities"]) == 5, len(ps["abilities"]))
    for ab in ps["abilities"]:
        check((221, 9, ds_sectype) in [(e["opcode"], e["p1"], e["p2"]) for e in ab["effects"]], ab["effects"])
    check("Dispelling Screen, Globe Of Invulnerability" in g.tlk(ps["desc"]), g.tlk(ps["desc"]))
    check("Dispelling Screen, Globe Of Invulnerability" in g.tlk(g.itm_descs("SCRL9A")[1]), g.tlk(g.itm_descs("SCRL9A")[1]))

    ss = g.spl("SPWI903")
    check((221, 9, ds_sectype) in [(e["opcode"], e["p1"], e["p2"]) for e in ss["abilities"][0]["effects"]], ss)
    check("Dispelling Screen, Globe Of Invulnerability" in g.tlk(ss["desc"]), g.tlk(ss["desc"]))
    check("Dispelling Screen, Globe Of Invulnerability" in g.tlk(g.itm_descs("SCRL9M")[1]), g.tlk(g.itm_descs("SCRL9M")[1]))

    # --- Row 3: Nahal's Reckless Dweomer (SPWI124) without Aura Cleansing ---
    nahal = parse_spl_full(g.file("override/SPWI124.SPL"))
    check(nahal["school"] == 6 and nahal["excl"] == 0x7FC0, nahal)
    nahal_ab = nahal["abilities"][0]
    check(nahal_ab["target"] == 5 and nahal_ab["casting_time"] == 5, nahal_ab)
    nahal_ops = [(e["opcode"], e["p2"]) for e in nahal_ab["effects"]]
    check(nahal_ops == [(214, 2), (280, 1)], nahal_ops)

    # Idempotency on second install
    after_first = g.tree()
    out2 = g.install()
    check(fg.installed_ok(out2) and not fg.with_warnings(out2), f"expected clean second install:\n{out2}")
    check(g.tree() == after_first, "second install should not alter any game files")

    # Clean uninstall restores original tree
    out_un = g.uninstall()
    check("SUCCESSFULLY REMOVED" in out_un, out_un)
    check(g.tree() == before, "uninstall should restore original tree")


@test
def more_batch_variations_and_invalid_inputs(work, weidu):
    tlk = ie.make_tlk(fx.TEXTS + MORE_TEXTS)
    biff = make_more_biff()
    # Modded Nahal's Reckless Dweomer with two ability breakpoints (levels 1 and 10),
    # an explicit opcode 188 (Cleanse Aura), and a custom mod marker effect (opcode 139)
    # that must be preserved alongside both abilities.
    biff["SPWI124.SPL"] = make_spl_with_excl(
        1, 1,
        [
            {
                "target": 7, "range": 30, "min_level": ml, "casting_time": 5, "projectile": 1,
                "effects": [
                    fx.fx(opcode=188, target=1, power=0, p1=1, p2=1, timing=0, duration=6),
                    fx.fx(opcode=214, target=1, power=0, p1=0, p2=2, timing=1, dispel=2),
                    fx.fx(opcode=280, target=1, power=0, p1=0, p2=1, timing=1, dispel=2),
                    fx.fx(opcode=139, target=1, power=0, p1=9999 + ml, p2=0, timing=1),
                ],
            }
            for ml in (1, 10)
        ],
        desc=NAHAL_DESC, school=6, excl=0x7FC0,
    )
    # Wish Breach (SPWISH26, SPWISH38)
    for w_res in ("SPWISH26.SPL", "SPWISH38.SPL"):
        biff[w_res] = ie.make_spl(
            4, 9,
            [{
                "target": 4, "range": 40, "min_level": 1, "casting_time": 1, "projectile": 1,
                "effects": [
                    fx.fx(opcode=221, target=4, power=9, p1=9, p2=2, timing=1, dispel=2),
                    fx.fx(opcode=221, target=4, power=9, p1=9, p2=7, timing=1, dispel=2),
                ],
            }],
        )
    # Dispel item (AROW07.ITM) with target=2 opcode 58 vs self-only item (SELF58.ITM) with target=1 opcode 58
    biff["AROW07.ITM"] = ie.make_itm([[fx.fx(opcode=58, target=2, power=0, p1=0, p2=0, timing=1)]])
    biff["SELF58.ITM"] = ie.make_itm([[fx.fx(opcode=58, target=1, power=0, p1=99, p2=0, timing=1)]])
    g = fg.FakeGame(work / "v1", weidu, tlk=tlk, biff=biff)
    out = g.install()
    check(fg.installed_ok(out) and not fg.with_warnings(out), f"expected clean install:\n{out}")

    ds_sectype = parse_spl_full(g.file("override/SPWI510.SPL"))["sectype"]

    nahal = parse_spl_full(g.file("override/SPWI124.SPL"))
    check([ab["min_level"] for ab in nahal["abilities"]] == [1, 10], nahal["abilities"])
    for idx, ml in enumerate((1, 10)):
        nahal_ab = nahal["abilities"][idx]
        check(nahal_ab["target"] == 5, nahal_ab)
        nahal_ops = [(e["opcode"], e["p1"], e["p2"]) for e in nahal_ab["effects"]]
        check(nahal_ops == [(214, 0, 2), (280, 0, 1), (139, 9999 + ml, 0)], nahal_ops)

    for w_res in ("SPWISH26", "SPWISH38"):
        wish_br = g.spl(w_res)
        wish_ops = [(e["opcode"], e["target"], e["p2"], e["resource"].upper()) for e in wish_br["abilities"][0]["effects"]]
        check(wish_ops == [(146, 4, 1, "SPWI513B"), (146, 4, 1, "SPWI513C")], wish_ops)

    arow_raw = g.file("override/AROW07.ITM")
    check(arow_raw is not None, "expected AROW07.ITM to be patched with Dispelling Screen cleanup")
    arow_fx_off, = struct.unpack_from("<I", arow_raw, 0x6A)
    arow_fx1 = ie.unpack_fx(arow_raw, arow_fx_off + 48)
    check(arow_fx1["opcode"] == 221 and arow_fx1["p1"] == 9 and arow_fx1["p2"] == ds_sectype, arow_fx1)
    check(g.file("override/SELF58.ITM") is None, "self-only SELF58.ITM should not be modified")

    # Corrupted/truncated SPWI124.SPL warns cleanly without aborting the install
    biff_bad = make_more_biff()
    biff_bad["SPWI124.SPL"] = b"SPL V1  short"
    g_bad = fg.FakeGame(work / "v2", weidu, tlk=tlk, biff=biff_bad)
    out_bad = g_bad.install()
    check(fg.installed_ok(out_bad) and fg.with_warnings(out_bad), out_bad)
    check("Nahal's Reckless Dweomer (SPWI124) left as it is" in out_bad, out_bad)

