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
    # +5: Improved Haste name
    "Improved Haste",
    # +6: Improved Haste desc
    "Improved Haste\n(Alteration)\n\nLevel: 6\nRange: 40 ft.\nDuration: 3 rounds + 1 round/level\nCasting Time: 3\n"
    "Area of Effect: 1 creature\nSaving Throw: None\n\n"
    "When cast, this spell doubles the recipient's movement and attacks per round.",
]
(
    SI_NAME,
    SI_DESC,
    PIERCE_SHIELD_DESC,
    SPELLSTRIKE_DESC,
    NAHAL_DESC,
    IH_NAME,
    IH_DESC,
) = range(BASE_STRREF, BASE_STRREF + len(MORE_TEXTS))

MORE_SYMBOLS = [
    *fx.SPELL_SYMBOLS,
    (1303, "CLERIC_DISPEL_MAGIC"),
    (2124, "WIZARD_NAHALS_RECKLESS_DWEOMER"),
    (2302, "WIZARD_REMOVE_MAGIC"),
    (2305, "WIZARD_HASTE"),
    (2312, "WIZARD_SLOW"),
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
    (2613, "WIZARD_IMPROVED_HASTE"),
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
        # Vanilla SPWI613 (Improved Haste: 9 abilities, min_level 1, 13..20, single-target, op16 p2=1)
        "SPWI613.SPL": make_spl_with_excl(
            1, 6,
            [
                {
                    "target": 1, "range": 40, "min_level": ml, "casting_time": 3, "projectile": 1,
                    "effects": [
                        fx.fx(opcode=16, target=2, power=6, p1=0, p2=1, timing=0, dispel=3, duration=18 + 6 * (12 if ml == 1 else ml)),
                        fx.fx(opcode=141, target=2, power=6, p1=0, p2=4, timing=1, dispel=3),
                        fx.fx(opcode=61, target=2, power=6, p1=2017213440, p2=1638400, timing=1, dispel=3),
                        fx.fx(opcode=139, target=2, power=6, p1=14023, p2=0, timing=1, dispel=3),
                        fx.fx(opcode=174, target=2, power=6, p1=0, p2=0, timing=1, dispel=3, resource="EFF_M28"),
                        fx.fx(opcode=174, target=2, power=6, p1=0, p2=0, timing=4, dispel=3, duration=18 + 6 * (12 if ml == 1 else ml), resource="EFF_M29"),
                        fx.fx(opcode=206, target=2, power=6, p1=0, p2=0, timing=0, dispel=1, duration=18 + 6 * (12 if ml == 1 else ml), resource="SPWI305"),
                    ],
                }
                for ml in [1, *range(13, 21)]
            ],
            name=IH_NAME, desc=IH_DESC, school=8, sectype=13, excl=0x0040, icon="SPWI613C",
        ),
        "SCRL7Q.ITM": fx.scroll("SPWI613", IH_DESC),
        # Vanilla SPWI305 (Haste: 3 sample abilities at min_level 1, 6, 7 with op16 + fatigue op93)
        "SPWI305.SPL": make_spl_with_excl(
            1, 3,
            [
                {
                    "target": 4, "range": 15, "min_level": ml, "casting_time": 3, "projectile": 156,
                    "effects": [
                        fx.fx(opcode=16, target=2, power=3, p1=0, p2=0, timing=0, dispel=3, duration=18 + 6 * (5 if ml == 1 else ml)),
                        fx.fx(opcode=141, target=2, power=3, p1=0, p2=4, timing=1, dispel=3),
                        fx.fx(opcode=61, target=2, power=3, p1=2017213440, p2=1638400, timing=1, dispel=3),
                        fx.fx(opcode=139, target=2, power=3, p1=14023, p2=0, timing=1, dispel=3),
                        fx.fx(opcode=142, target=2, power=3, p1=0, p2=38, timing=0, dispel=3, duration=18 + 6 * (5 if ml == 1 else ml)),
                        fx.fx(opcode=174, target=2, power=3, p1=0, p2=0, timing=1, dispel=3, resource="EFF_M28"),
                        fx.fx(opcode=174, target=2, power=3, p1=0, p2=0, timing=4, dispel=3, duration=18 + 6 * (5 if ml == 1 else ml), resource="EFF_M29"),
                        fx.fx(opcode=93, target=2, power=3, p1=4, p2=0, timing=4, dispel=2, duration=18 + 6 * (5 if ml == 1 else ml)),
                    ],
                }
                for ml in (1, 6, 7)
            ],
            school=8, sectype=13, excl=0x0040, icon="SPWI305C",
        ),
        # Vanilla SPWI312 (Slow: save vs. spell at -4, op40 + -4 AC op0 + -4 THAC0 op54 + icon 41)
        "SPWI312.SPL": make_spl_with_excl(
            1, 3,
            [{
                "target": 4, "range": 25, "min_level": 1, "casting_time": 3, "projectile": 177,
                "effects": [
                    fx.fx(opcode=321, target=2, power=3, p1=0, p2=0, timing=1, dispel=1, save=1, bonus=-4, resource="spin977"),
                    fx.fx(opcode=321, target=2, power=3, p1=0, p2=0, timing=1, dispel=1, save=1, bonus=-4, resource="spwi312"),
                    fx.fx(opcode=40, target=2, power=3, p1=0, p2=0, timing=0, dispel=1, duration=60, save=1, bonus=-4),
                    fx.fx(opcode=0, target=2, power=3, p1=-4, p2=0, timing=0, dispel=1, duration=60, save=1, bonus=-4),
                    fx.fx(opcode=54, target=2, power=3, p1=-4, p2=0, timing=0, dispel=1, duration=60, save=1, bonus=-4),
                    fx.fx(opcode=141, target=2, power=3, p1=0, p2=6, timing=1, dispel=1, save=1, bonus=-4),
                    fx.fx(opcode=139, target=2, power=3, p1=14668, p2=0, timing=1, dispel=1, save=1, bonus=-4),
                    fx.fx(opcode=142, target=2, power=3, p1=0, p2=41, timing=0, dispel=1, duration=60, save=1, bonus=-4),
                    fx.fx(opcode=240, target=2, power=3, p1=0, p2=38, timing=1, dispel=1, save=1, bonus=-4),
                ],
            }],
            school=8, sectype=11, excl=0x0040, icon="SPWI312C",
        ),
        # Vanilla POTN14.ITM (Oil of Speed: target=1, 300s Haste + *gulp* string 16233)
        "POTN14.ITM": ie.make_itm([[
            fx.fx(opcode=16, target=1, power=0, p1=0, p2=0, timing=0, dispel=1, duration=300),
            fx.fx(opcode=139, target=1, power=0, p1=16233, p2=0, timing=1, dispel=0),
            fx.fx(opcode=142, target=1, power=0, p1=0, p2=38, timing=0, dispel=1, duration=300),
        ]], item_type=9),
        # Vanilla BLUN30.ITM (Flail of Ages: elemental damage + 33% Slow for 20s + Undead/Golem poison gate)
        "BLUN30.ITM": ie.make_itm([[
            fx.fx(opcode=12, target=2, power=0, p1=2, p2=0x10000, timing=1, dispel=0),
            fx.fx(opcode=40, target=2, power=0, p1=0, p2=0, timing=0, dispel=0, duration=20, prob1=33, prob2=0),
            fx.fx(opcode=139, target=2, power=0, p1=14000, p2=0, timing=9, dispel=0, prob1=33, prob2=0),
            fx.fx(opcode=318, target=2, power=0, p1=0, p2=55, timing=0, dispel=0, duration=0, resource="BLUN30"),
            fx.fx(opcode=12, target=2, power=0, p1=2, p2=0x200000, timing=1, dispel=0),
        ]], item_type=22),
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

    # --- Row 4: Improved Haste (SPWI613) and Haste / Slow mutual cancellation ---
    check("cbm_Haste" in msectype_txt and "cbm_Slow" in msectype_txt, msectype_txt)
    ih = parse_spl_full(g.file("override/SPWI613.SPL"))
    check(ih["level"] == 6 and ih["school"] == 8 and ih["sectype"] == 13, ih)
    check(g.tlk(ih["name"]) == "Improved Haste", g.tlk(ih["name"]))
    check("+6 movement rate" in g.tlk(ih["desc"]) and "immune to Slow" in g.tlk(ih["desc"]), g.tlk(ih["desc"]))
    check([ab["min_level"] for ab in ih["abilities"]] == [1, *range(13, 21)], ih["abilities"])
    for ab in ih["abilities"]:
        check(
            ab["location"] == 2 and ab["target"] == 4 and ab["range"] == 30
            and ab["casting_time"] == 6 and ab["projectile"] == 158,
            ab,
        )
        ih_ops = [(e["opcode"], e["p1"], e["p2"], e["duration"], e["dispel"], e["resource"].upper()) for e in ab["effects"]]
        # Must NOT use opcode 16
        check(all(e["opcode"] != 16 for e in ab["effects"]), ih_ops)
        # Core party buff bonuses for 60s
        check((176, 6, 0, 60, 3, "") in ih_ops, ih_ops)
        check((1, 1, 0, 60, 3, "") in ih_ops, ih_ops)
        check((54, 2, 0, 60, 3, "") in ih_ops, ih_ops)
        check((0, 2, 0, 60, 3, "") in ih_ops, ih_ops)
        check((36, 2, 0, 60, 3, "") in ih_ops, ih_ops)
        # Slow cure and Slow immunity
        check((240, 0, 41, 0, 3, "") in ih_ops, ih_ops)
        check((101, 0, 40, 60, 3, "") in ih_ops, ih_ops)
        check((169, 0, 41, 60, 3, "") in ih_ops, ih_ops)
        check((206, -1, 0, 60, 3, "SPWI312") in ih_ops, ih_ops)
        check((206, -1, 0, 60, 3, "SPWI305") in ih_ops, ih_ops)
        # Self non-stacking last
        check(ih_ops[-1] == (206, -1, 0, 60, 3, "SPWI613"), ih_ops[-1])

    # Scroll SCRL7Q.ITM updated for Area target (target=4, op148) and new description
    scrl7q_raw = g.file("override/SCRL7Q.ITM")
    check("immune to Slow" in g.tlk(g.itm_descs("SCRL7Q")[1]), g.tlk(g.itm_descs("SCRL7Q")[1]))
    scrl7q_ab_off, = struct.unpack_from("<I", scrl7q_raw, 0x64)
    scrl7q_fx_off, = struct.unpack_from("<I", scrl7q_raw, 0x6A)
    check(scrl7q_raw[scrl7q_ab_off + 0x0C] == 4, scrl7q_raw[scrl7q_ab_off + 0x0C])
    scrl7q_fx0 = ie.unpack_fx(scrl7q_raw, scrl7q_fx_off)
    check(scrl7q_fx0["opcode"] == 148 and scrl7q_fx0["target"] == 1, scrl7q_fx0)

    # Haste (SPWI305 -> SPWI305A) and Slow (SPWI312 -> SPWI312A) mutual cancellation
    neg16 = parse_spl_full(g.file("override/CBMNEG16.SPL"))
    check(g.tlk(neg16["abilities"][0]["effects"][0]["p1"]) == "Haste cancelled by Slow", neg16)
    neg40 = parse_spl_full(g.file("override/CBMNEG40.SPL"))
    check(g.tlk(neg40["abilities"][0]["effects"][0]["p1"]) == "Slow cancelled by Haste", neg40)

    haste_parent = parse_spl_full(g.file("override/SPWI305.SPL"))
    haste_sub = parse_spl_full(g.file("override/SPWI305A.SPL"))
    haste_sectype = haste_sub["sectype"]
    slow_parent = parse_spl_full(g.file("override/SPWI312.SPL"))
    slow_sub = parse_spl_full(g.file("override/SPWI312A.SPL"))
    slow_sectype = slow_sub["sectype"]
    check(haste_sectype != slow_sectype and haste_sectype >= 14 and slow_sectype >= 14, (haste_sectype, slow_sectype))

    for idx, ml in enumerate((1, 6, 7)):
        dur = 18 + 6 * (5 if ml == 1 else ml)
        p_ops = [(e["opcode"], e["p1"], e["p2"], e["resource"].upper()) for e in haste_parent["abilities"][idx]["effects"]]
        check(p_ops == [(146, 0, 1, "SPWI305A"), (221, 10, slow_sectype, "")], p_ops)
        s_ops = [(e["opcode"], e["p1"], e["p2"], e["duration"], e["resource"].upper()) for e in haste_sub["abilities"][idx]["effects"]]
        # Prepend gates: 324 (HASTE_IMMUNITY), 221 (cbm_Haste), 326 (STATE_SLOWED -> CBMNEG40), 318 (STATE_SLOWED -> SPWI305A)
        check(s_ops[0][0] == 324 and s_ops[0][4] == "SPWI305A", s_ops[0])
        check(s_ops[1] == (221, 10, haste_sectype, 0, ""), s_ops[1])
        check(s_ops[2][:3] == (326, 0x00010000, 138) and s_ops[2][4] == "CBMNEG40", s_ops[2])
        check(s_ops[3][:3] == (318, 0x00010000, 138) and s_ops[3][4] == "SPWI305A", s_ops[3])
        # Vanilla Haste bonus, duration, and fatigue preserved inside SPWI305A
        check((16, 0, 0, dur, "") in s_ops, s_ops)
        check((93, 4, 0, dur, "") in s_ops, s_ops)
        check((142, 0, 38, dur, "") in s_ops, s_ops)

    sp_ops = [(e["opcode"], e["p1"], e["p2"], e["save"], e["bonus"], e["resource"].upper()) for e in slow_parent["abilities"][0]["effects"]]
    check(sp_ops == [(146, 0, 1, 0, 0, "SPWI312A"), (221, 10, haste_sectype, 0, 0, "")], sp_ops)
    ss_ops = [(e["opcode"], e["p1"], e["p2"], e["duration"], e["save"], e["bonus"], e["resource"].upper()) for e in slow_sub["abilities"][0]["effects"]]
    check(ss_ops[0] == (221, 10, slow_sectype, 0, 1, -4, ""), ss_ops[0])
    check(ss_ops[1][:3] == (326, 0x00008000, 138) and ss_ops[1][6] == "CBMNEG16", ss_ops[1])
    check(ss_ops[2][:3] == (318, 0x00008000, 138) and ss_ops[2][6] == "SPWI312A", ss_ops[2])
    check(ss_ops[3][0] == 324 and ss_ops[3][6] == "SPWI312A", ss_ops[3])
    check((40, 0, 0, 60, 1, -4, "") in ss_ops, ss_ops)
    check((0, -4, 0, 60, 1, -4, "") in ss_ops, ss_ops)
    check((54, -4, 0, 60, 1, -4, "") in ss_ops, ss_ops)
    check((142, 0, 41, 60, 1, -4, "") in ss_ops, ss_ops)

    # Oil of Speed (POTN14.ITM -> POTN14.SPL) keeps *gulp* string (16233) on item and extracts Haste to POTN14.SPL
    potn14_raw = g.file("override/POTN14.ITM")
    potn14_fx_off, = struct.unpack_from("<I", potn14_raw, 0x6A)
    potn14_ab_off, = struct.unpack_from("<I", potn14_raw, 0x64)
    potn14_na, = struct.unpack_from("<H", potn14_raw, potn14_ab_off + 0x1E)
    potn14_ops = [ie.unpack_fx(potn14_raw, potn14_fx_off + i * 48) for i in range(potn14_na)]
    check([(e["opcode"], e["target"], e["p1"], e["p2"], e["resource"]) for e in potn14_ops] == [
        (146, 1, 0, 1, "POTN14"),
        (221, 1, 10, slow_sectype, ""),
        (139, 1, 16233, 0, ""),
    ], potn14_ops)
    potn14_sub = parse_spl_full(g.file("override/POTN14.SPL"))
    check(potn14_sub["sectype"] == haste_sectype, potn14_sub)

    # Flail of Ages (BLUN30.ITM -> BLUN30.SPL) preserves 33% probability on 146/221 and keeps elemental/poison effects
    blun30_raw = g.file("override/BLUN30.ITM")
    blun30_fx_off, = struct.unpack_from("<I", blun30_raw, 0x6A)
    blun30_ab_off, = struct.unpack_from("<I", blun30_raw, 0x64)
    blun30_na, = struct.unpack_from("<H", blun30_raw, blun30_ab_off + 0x1E)
    blun30_ops = [ie.unpack_fx(blun30_raw, blun30_fx_off + i * 48) for i in range(blun30_na)]
    check([(e["opcode"], e["prob1"], e["p2"], e["resource"]) for e in blun30_ops] == [
        (12, 100, 0x10000, ""),
        (146, 33, 1, "BLUN30"),
        (221, 33, haste_sectype, ""),
        (318, 100, 55, "BLUN30"),
        (12, 100, 0x200000, ""),
    ], blun30_ops)

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
    # Multi-ability Slow spell (SPCL123.SPL): ability 0 has no Slow; ability 1 has Slow + non-Slow op54 (p1=0)
    biff["SPCL123.SPL"] = ie.make_spl(
        4, 1,
        [
            {
                "target": 1, "range": 1, "min_level": 1, "casting_time": 1, "projectile": 1,
                "effects": [fx.fx(opcode=126, target=2, power=0, p1=0, p2=0, timing=0, dispel=2, duration=40)],
            },
            {
                "target": 1, "range": 1, "min_level": 12, "casting_time": 1, "projectile": 1,
                "effects": [
                    fx.fx(opcode=126, target=2, power=0, p1=0, p2=0, timing=0, dispel=2, duration=50),
                    fx.fx(opcode=54, target=2, power=0, p1=0, p2=0, timing=0, dispel=2, duration=50),
                    fx.fx(opcode=40, target=2, power=0, p1=0, p2=0, timing=0, dispel=2, duration=12),
                ],
            },
        ],
    )
    # Item with opcode 16 p2=1 (BRAC16.ITM)
    biff["BRAC16.ITM"] = ie.make_itm([[
        fx.fx(opcode=16, target=1, power=0, p1=0, p2=1, timing=0, dispel=1, duration=20),
        fx.fx(opcode=142, target=1, power=0, p1=0, p2=110, timing=0, dispel=1, duration=20),
    ]], item_type=19)
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

    # Multi-ability SPCL123.SPL: ability 0 untouched, ability 1 keeps op126 + op54(p1=0) and extracts op40 to SPCL123A.SPL
    spcl123 = g.spl("SPCL123")
    check([(e["opcode"], e["p1"]) for e in spcl123["abilities"][0]["effects"]] == [(126, 0)], spcl123["abilities"][0])
    ab1_ops = [(e["opcode"], e["p1"], e["resource"].upper()) for e in spcl123["abilities"][1]["effects"]]
    check(ab1_ops[:3] == [(126, 0, ""), (54, 0, ""), (146, 0, "SPCL123A")] and ab1_ops[3][0] == 221, ab1_ops)

    # BRAC16.ITM (op16 p2=1) sets HASTE_IMMUNITY (op328) inside BRAC16.SPL
    brac16_sub = parse_spl_full(g.file("override/BRAC16.SPL"))
    check(any(e["opcode"] == 328 and e["duration"] == 20 for e in brac16_sub["abilities"][0]["effects"]), brac16_sub)

    # Corrupted/truncated SPWI124.SPL warns cleanly without aborting the install
    biff_bad = make_more_biff()
    biff_bad["SPWI124.SPL"] = b"SPL V1  short"
    g_bad = fg.FakeGame(work / "v2", weidu, tlk=tlk, biff=biff_bad)
    out_bad = g_bad.install()
    check(fg.installed_ok(out_bad) and fg.with_warnings(out_bad), out_bad)
    check("Nahal's Reckless Dweomer (SPWI124) left as it is" in out_bad, out_bad)

