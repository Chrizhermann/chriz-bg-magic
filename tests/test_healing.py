"""Synthetic installer tests for the decided healing batch.

The fixtures deliberately include both IWD-style direct Cause Wounds spells and the BG2
touch-charge delivery used by Cause Serious, Cause Critical and Harm.  They contain extra
abilities/effects and a shared charge item so preservation and private cloning are checked
without reading an installed game.
"""
import struct

import fakegame as fg
import ie
from harness import check, test


HEALING_TP2 = r"""BACKUP ~weidu_external/backup/chriz-bg-magic~
AUTHOR ~test~
ALWAYS
  INCLUDE ~chriz-bg-magic/lib/cbmagic_shared.tpa~
  INCLUDE ~chriz-bg-magic/lib/cbmagic_spells.tpa~
  INCLUDE ~chriz-bg-magic/lib/cbmagic_healing.tpa~
END
LANGUAGE ~English~ ~english~ ~chriz-bg-magic/languages/english/setup.tra~
BEGIN ~healing~ DESIGNATED 0
LAM cbmagic_index_scrolls
LAF cbmagic_healing_cure_light END
LAF cbmagic_healing_cure_moderate END
LAF cbmagic_healing_cure_medium END
LAF cbmagic_healing_cure_serious END
LAF cbmagic_healing_cure_critical END
LAF cbmagic_healing_mass_cure END
LAF cbmagic_healing_cause_wounds END
LAF cbmagic_healing_mass_cause_light END
LAF cbmagic_healing_harm END
"""


def fx(**kw):
    return kw


def _spell(data):
    parsed = ie.parse_spl(data)
    ab_off = struct.unpack_from("<I", data, 0x64)[0]
    for i, ability in enumerate(parsed["abilities"]):
        ability["casting_time"] = struct.unpack_from("<H", data, ab_off + i * 0x28 + 0x12)[0]
    return parsed


def _item(data):
    ab_off = struct.unpack_from("<I", data, 0x64)[0]
    ab_cnt = struct.unpack_from("<H", data, 0x68)[0]
    fx_off = struct.unpack_from("<I", data, 0x6A)[0]
    out = []
    for a in range(ab_cnt):
        off = ab_off + a * 0x38
        count, first = struct.unpack_from("<HH", data, off + 0x1E)
        out.append([ie.unpack_fx(data, fx_off + (first + i) * 48) for i in range(count)])
    return out


def _direct_damage(power, fixed, *, save=0, special=0, extra=False):
    effects = [fx(opcode=12, target=2, power=power, p1=fixed, p2=0x400000, timing=1,
                  dispel=1, save=save, special=special)]
    if extra:
        effects += [fx(opcode=12, target=2, power=power, p1=99, p2=0x80000, timing=1),
                    fx(opcode=215, target=2, power=power, timing=1, resource="UNCHANGED")]
    return effects


def _charge_item(power, fixed, *, kind=0x400000):
    return ie.make_itm([
        [fx(opcode=12, target=2, power=power, p1=fixed, p2=kind, timing=1, dispel=1),
         fx(opcode=215, target=2, power=power, timing=1, resource="SPCAUSEW"),
         fx(opcode=61, target=2, power=power, timing=1, p1=1234, p2=5678)],
        [fx(opcode=12, target=2, power=power, p1=77, p2=0x80000, timing=1)],
    ], item_type=3)


def _charge_spell(level, item, ct, desc):
    return ie.make_spl(2, level, [
        {"target": 5, "casting_time": ct, "effects": [
            fx(opcode=111, target=1, power=level, timing=0, duration=15, resource=item),
            fx(opcode=174, target=1, power=level, timing=1, resource="EFF_P06"),
        ]}
    ], desc=desc)


def _scroll(spell, desc):
    return ie.make_itm([[fx(opcode=146, target=1, p2=1, timing=1, resource=spell)]], desc=desc)


def _texts():
    values = {
        "CLW": "Cure Light Wounds\n\nCasting Time: 5\nBy casting this spell, the priest causes 8 points of wound or other injury damage to the creature's body to be healed.",
        "CMOD": "Cure Moderate Wounds\n\nCasting Time: 5\nCure Moderate Wounds heals 11 Hit Points and cures intoxication.",
        "CMED": "Cure Medium Wounds\n\nCasting Time: 5\nThe priest heals 14 points of wound or other injury damage from the creature's body.",
        "CSER": "Cure Serious Wounds\n\nCasting Time: 7\nThe priest heals 17 points of wound or other injury damage to the creature's body.",
        "CCRI": "Cure Critical Wounds\n\nCasting Time: 8\nThe priest heals 27 points of damage from wounds or other injuries.",
        "MCURE": "Mass Cure\n\nCasting Time: 5\nAll party members are healed.",
        "CLIGHT": "Cause Light Wounds\n\nCasting Time: 5\nBy casting this spell, the priest deals 8 points of damage. This spell has no effect on undead, constructs, or extraplanar creatures.",
        "CMODER": "Cause Moderate Wounds\n\nCasting Time: 5\nBy casting this spell, the priest deals 11 points of damage. This spell has no effect on undead, constructs, or extraplanar creatures.",
        "CMEDIU": "Cause Medium Wounds\n\nCasting Time: 5\nBy casting this spell, the priest deals 14 points of damage. This spell has no effect on undead, constructs, or extraplanar creatures.",
        "CSERIO": "Cause Serious Wounds\n\nCasting Time: 7\nIt inflicts 17 points of damage. There is no Saving Throw.",
        "CCRITI": "Cause Critical Wounds\n\nCasting Time: 8\nIt inflicts 27 points of damage. There is no Saving Throw.",
        "MCAUSE": "Mass Cause Light Wounds\n\nCasting Time: 5\nThis spell has no effect on undead, constructs, or extraplanar creatures.",
        "HARM": "Harm\n\nCasting Time: 9\nThe spell reduces the target to 1 Hit Point. There is no Saving Throw.",
    }
    names = list(values)
    refs = {name: i + 1 for i, name in enumerate(names)}
    return refs, ie.make_tlk(["", *(values[name] for name in names)])


def _game():
    refs, tlk = _texts()
    ids = ie.make_ids([
        (1103, "CLERIC_CURE_LIGHT_WOUNDS"), (1114, "CLERIC_CAUSE_LIGHT_WOUNDS"),
        (1217, "CLERIC_CURE_MODERATE_WOUNDS"), (1220, "CLERIC_CAUSE_MODERATE_WOUNDS"),
        (1315, "CLERIC_CURE_MEDIUM_WOUNDS"), (1330, "CLERIC_CAUSE_MEDIUM_WOUNDS"),
        (1401, "CLERIC_CURE_SERIOUS_WOUNDS"), (1414, "CLERIC_CAUSE_SERIOUS_WOUNDS"),
        (1502, "CLERIC_CURE_CRITICAL_WOUNDS"), (1510, "CLERIC_CAUSE_CRITICAL_WOUNDS"),
        (1514, "CLERIC_MASS_CURE"), (1523, "CLERIC_MASS_CAUSE_LIGHT_WOUNDS"), (1608, "CLERIC_HARM"),
    ])
    splprot = ie.make_2da(["STAT", "VALUE", "RELATION"], [
        ("0_EA", ["0x10a", "0", "4"]),
        ("1_GENERAL=UNDEAD", ["0x10b", "4", "1"]),
        ("2_GENERAL!=UNDEAD", ["0x10b", "4", "5"]),
    ])
    cures = {
        "SPPR103.SPL": ie.make_spl(2, 1, [
            {"target": 1, "casting_time": 5, "effects": [fx(opcode=17, target=2, power=1, p1=8, timing=1), fx(opcode=215, target=2, resource="SPHEALIN")]},
            {"target": 1, "casting_time": 5, "min_level": 9, "effects": [fx(opcode=17, target=2, power=1, p1=8, timing=1), fx(opcode=61, target=2, p1=10)]},
        ], desc=refs["CLW"]),
        "SPPR217.SPL": ie.make_spl(2, 2, [{"target": 1, "casting_time": 5, "effects": [fx(opcode=17, target=2, power=2, p1=11, timing=1)]}], desc=refs["CMOD"]),
        "SPPR315.SPL": ie.make_spl(2, 3, [{"target": 1, "casting_time": 5, "effects": [fx(opcode=17, target=2, power=3, p1=14, timing=1)]}], desc=refs["CMED"]),
        "SPPR401.SPL": ie.make_spl(2, 4, [{"target": 1, "casting_time": 7, "effects": [fx(opcode=17, target=2, power=4, p1=17, timing=1)]}], desc=refs["CSER"]),
        "SPPR502.SPL": ie.make_spl(2, 5, [{"target": 1, "casting_time": 8, "effects": [fx(opcode=17, target=2, power=5, p1=27, timing=1)]}], desc=refs["CCRI"]),
        "SPPR514.SPL": ie.make_spl(2, 5, [{"target": 5, "casting_time": 5, "effects": [fx(opcode=17, target=2, power=5, p1=9, dice=1, sides=8, timing=1)]}], desc=refs["MCURE"]),
    }
    causes = {
        "SPPR114.SPL": ie.make_spl(2, 1, [
            {"target": 1, "casting_time": 5, "effects": _direct_damage(1, 8, save=1, special=0x100, extra=True)},
            {"target": 1, "casting_time": 5, "min_level": 9, "effects": _direct_damage(1, 8, save=1, special=0x100)},
        ], desc=refs["CLIGHT"]),
        "SPPR220.SPL": ie.make_spl(2, 2, [{"target": 1, "casting_time": 5, "effects": _direct_damage(2, 11, save=1, special=0x100)}], desc=refs["CMODER"]),
        "SPPR330.SPL": ie.make_spl(2, 3, [{"target": 1, "casting_time": 5, "effects": _direct_damage(3, 14, save=1, special=0x100)}], desc=refs["CMEDIU"]),
        "SPPR414.SPL": _charge_spell(4, "SERIOUS", 7, refs["CSERIO"]),
        "SPPR510.SPL": _charge_spell(5, "CRITICAL", 8, refs["CCRITI"]),
        "SPPR523.SPL": ie.make_spl(2, 5, [
            {"target": 5, "casting_time": 5, "effects": [
                fx(opcode=12, target=2, power=5, p1=9, p2=0x400000, timing=1,
                   dispel=1, dice=1, sides=8, save=1, special=0x100)
            ]},
            {"target": 5, "min_level": 15, "casting_time": 5, "effects": [
                fx(opcode=12, target=2, power=5, p1=15, p2=0x400000, timing=1,
                   dispel=1, dice=1, sides=8, save=1, special=0x100)
            ]},
        ], desc=refs["MCAUSE"]),
        "SPPR608.SPL": _charge_spell(6, "HARM", 9, refs["HARM"]),
        # Another producer makes SERIOUS shared; Cause Serious must use a private clone.
        "SPPR999.SPL": _charge_spell(9, "SERIOUS", 5, refs["HARM"]),
    }
    scrolls = {
        "SCRL01.ITM": _scroll("SPPR103", refs["CLW"]), "SCRL02.ITM": _scroll("SPPR217", refs["CMOD"]),
        "SCRL03.ITM": _scroll("SPPR315", refs["CMED"]), "SCRL04.ITM": _scroll("SPPR401", refs["CSER"]),
        "SCRL05.ITM": _scroll("SPPR502", refs["CCRI"]), "SCRL06.ITM": _scroll("SPPR514", refs["MCURE"]),
        "SCRL07.ITM": _scroll("SPPR114", refs["CLIGHT"]), "SCRL08.ITM": _scroll("SPPR220", refs["CMODER"]),
        "SCRL09.ITM": _scroll("SPPR330", refs["CMEDIU"]), "SCRL10.ITM": _scroll("SPPR414", refs["CSERIO"]),
        "SCRL11.ITM": _scroll("SPPR510", refs["CCRITI"]), "SCRL12.ITM": _scroll("SPPR523", refs["MCAUSE"]),
        "SCRL13.ITM": _scroll("SPPR608", refs["HARM"]),
    }
    biff = {
        "SPELL.IDS": ids, "SPLPROT.2DA": splprot, **cures, **causes, **scrolls,
        "SERIOUS.ITM": _charge_item(4, 17), "CRITICAL.ITM": _charge_item(5, 27),
        "HARM.ITM": _charge_item(6, 1, kind=0x400001),
    }
    return tlk, biff


def _healing_game(work, weidu):
    tlk, biff = _game()
    return fg.FakeGame(work, weidu, tp2=HEALING_TP2, tlk=tlk, biff=biff)


def _single_fx(effects, opcode, *, resource=None, p2=None):
    found = [effect for effect in effects if effect["opcode"] == opcode
             and (resource is None or effect["resource"] == resource)
             and (p2 is None or effect["p2"] == p2)]
    check(len(found) == 1, f"wanted one op{opcode}: {effects}")
    return found[0]


@test
def healing_batch_rolls_and_undead_delivery(work, weidu):
    """Cures roll, Cause spells preserve their delivery, and undead get payload healing first."""
    g = _healing_game(work, weidu)
    before = g.tree()
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, out)

    for res, ct, dice, sides, bonus in [
        ("SPPR103", 4, 1, 8, 5), ("SPPR217", 4, 2, 8, 4), ("SPPR315", 4, 2, 8, 7),
        ("SPPR401", 6, 3, 8, 7), ("SPPR502", 7, 4, 8, 12),
    ]:
        spell = _spell(g.file(f"override/{res}.SPL"))
        check(all(ability["casting_time"] == ct for ability in spell["abilities"]), f"{res} ct: {spell}")
        for ability in spell["abilities"]:
            heal = _single_fx(ability["effects"], 17)
            check((heal["p1"], heal["dice"], heal["sides"]) == (bonus, dice, sides), f"{res}: {heal}")
        check(f"Casting Time: {ct}" in g.tlk(spell["desc"]), f"{res} text: {g.tlk(spell['desc'])}")

    mass = _spell(g.file("override/SPPR514.SPL"))
    original_mass = ie.parse_spl(_game()[1]["SPPR514.SPL"])
    check(mass["abilities"][0]["effects"] == original_mass["abilities"][0]["effects"], "Mass Cure effect changed")
    check(mass["abilities"][0]["casting_time"] == 4, f"Mass Cure ct: {mass}")

    # Direct IWD-style Cause Light: two abilities, its Spell save and unrelated fire damage survive.
    direct = _spell(g.file("override/SPPR114.SPL"))
    check(all(ability["casting_time"] == 4 for ability in direct["abilities"]), direct)
    for index, ability in enumerate(direct["abilities"]):
        effects = ability["effects"]
        guard, cast, block = effects[:3]
        payload = f"CBHD1{index}"
        check((guard["opcode"], guard["p2"], guard["resource"]) == (318, 2, payload), f"guard: {effects}")
        check((cast["opcode"], cast["resource"], cast["p2"]) == (146, payload, 1), f"cast: {effects}")
        check((block["opcode"], block["p2"], block["resource"]) == (324, 1, "SPPR114"), f"block: {effects}")
        damage = _single_fx(effects, 12, p2=0x400000)
        check((damage["p1"], damage["dice"], damage["sides"], damage["save"], damage["special"]) == (5, 1, 8, 1, 0x100), damage)
        payload_spell = _spell(g.file(f"override/{payload}.SPL"))
        heal = _single_fx(payload_spell["abilities"][0]["effects"], 17)
        check((heal["p1"], heal["dice"], heal["sides"]) == (5, 1, 8), heal)
    check(_single_fx(direct["abilities"][0]["effects"], 12, p2=0x80000)["p1"] == 99, "unrelated damage changed")
    check("Undead are healed for 1d8 + 5" in g.tlk(direct["desc"]), g.tlk(direct["desc"]))

    # The shared Serious charge is cloned and retargeted only in Cause Serious.
    serious = _spell(g.file("override/SPPR414.SPL"))
    check(serious["abilities"][0]["casting_time"] == 6, serious)
    create = _single_fx(serious["abilities"][0]["effects"], 111)
    check(create["resource"] == "CBHT40", f"Cause Serious did not retarget private item: {create}")
    check(g.file("override/SERIOUS.ITM") is None, "shared SERIOUS item was edited")
    serious_item = _item(g.file("override/CBHT40.ITM"))[0]
    guard, cast, block = serious_item[:3]
    check((guard["opcode"], guard["p2"], guard["resource"]) == (318, 2, "CBHI400"), serious_item)
    check((cast["opcode"], cast["resource"]) == (146, "CBHI400"), serious_item)
    check((block["opcode"], block["p2"], block["resource"]) == (324, 1, "CBHT40"), serious_item)
    serious_damage = _single_fx(serious_item, 12, p2=0x400000)
    check((serious_damage["p1"], serious_damage["dice"], serious_damage["sides"]) == (7, 3, 8), serious_damage)
    check(_item(g.file("override/CBHT40.ITM"))[1][0]["p1"] == 77, "unrelated charge ability changed")

    critical_spell = _spell(g.file("override/SPPR510.SPL"))
    check(critical_spell["abilities"][0]["casting_time"] == 7, critical_spell)
    critical = _item(g.file("override/CRITICAL.ITM"))[0]
    critical_damage = _single_fx(critical, 12, p2=0x400000)
    check((critical_damage["p1"], critical_damage["dice"], critical_damage["sides"]) == (12, 4, 8), critical_damage)

    # Mass Cause retains each rolling damage effect and gains a matching one-per-ability heal payload.
    mass_cause = _spell(g.file("override/SPPR523.SPL"))
    for index, (ability, fixed) in enumerate(zip(mass_cause["abilities"], (9, 15))):
        check(ability["casting_time"] == 5, "Mass Cause Light Wounds casting time changed")
        damage = _single_fx(ability["effects"], 12, p2=0x400000)
        check((damage["p1"], damage["dice"], damage["sides"]) == (fixed, 1, 8), damage)
        payload = _spell(g.file(f"override/CBHD6{index}.SPL"))
        heal = _single_fx(payload["abilities"][0]["effects"], 17)
        check((heal["p1"], heal["dice"], heal["sides"]) == (fixed, 1, 8), heal)

    harm = _item(g.file("override/HARM.ITM"))[0]
    harm_damage = _single_fx(harm, 12, p2=0x400001)
    check((harm_damage["p1"], harm_damage["dice"], harm_damage["sides"]) == (1, 0, 0), harm_damage)
    harm_payload = _spell(g.file("override/CBHI700.SPL"))
    full_heal = _single_fx(harm_payload["abilities"][0]["effects"], 17)
    check((full_heal["p1"], full_heal["p2"], full_heal["dice"], full_heal["sides"]) == (100, 2, 0, 0), full_heal)
    harm_spell = _spell(g.file("override/SPPR608.SPL"))
    check(harm_spell["abilities"][0]["casting_time"] == 7, harm_spell)
    check("Undead are healed completely" in g.tlk(harm_spell["desc"]), g.tlk(harm_spell["desc"]))

    for scroll in (f"SCRL{i:02d}" for i in range(1, 14)):
        _, desc = g.itm_descs(scroll)
        check(desc > 13, f"{scroll} did not get a private updated description")
    installed = g.tree()
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, out)
    check(g.tree() == installed, "a second healing install changed the generated resources")
    out = g.uninstall()
    check("SUCCESSFULLY REMOVED" in out, out)
    check(g.tree() == before, "uninstall did not restore the healing batch")


@test
def healing_batch_missing_optional_spells_and_extra_abilities(work, weidu):
    """Absent IWD symbols are logs, while all normal Cure Light abilities still update."""
    refs, tlk = _texts()
    biff = {
        "SPELL.IDS": ie.make_ids([(1103, "CLERIC_CURE_LIGHT_WOUNDS")]),
        "SPLPROT.2DA": ie.make_2da(["STAT", "VALUE", "RELATION"], [
            ("0_EA", ["0x10a", "0", "4"]), ("1_GENERAL=UNDEAD", ["0x10b", "4", "1"]),
            ("2_GENERAL!=UNDEAD", ["0x10b", "4", "5"]),
        ]),
        "SPPR103.SPL": ie.make_spl(2, 1, [
            {"target": 1, "casting_time": 5, "effects": [fx(opcode=17, target=2, p1=8, timing=1), fx(opcode=174, resource="EXTRA")]},
            {"target": 1, "min_level": 12, "casting_time": 5, "effects": [fx(opcode=17, target=2, p1=8, timing=1), fx(opcode=12, target=2, p1=4, p2=0x80000)]},
            {"target": 1, "min_level": 20, "casting_time": 3, "effects": [fx(opcode=17, target=2, p1=8, timing=1)]},
        ], desc=refs["CLW"]),
        "SCRL01.ITM": _scroll("SPPR103", refs["CLW"]),
    }
    g = fg.FakeGame(work, weidu, tp2=HEALING_TP2, tlk=tlk, biff=biff)
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, out)
    spell = _spell(g.file("override/SPPR103.SPL"))
    check([ability["casting_time"] for ability in spell["abilities"]] == [4, 4, 3], spell)
    check(all(((_single_fx(a["effects"], 17)["p1"], _single_fx(a["effects"], 17)["dice"], _single_fx(a["effects"], 17)["sides"]) == (5, 1, 8)) for a in spell["abilities"]), spell)
    check(_single_fx(spell["abilities"][1]["effects"], 12, p2=0x80000)["p1"] == 4, "extra effect changed")
    check("CLERIC_CURE_MODERATE_WOUNDS) is not in this game; skipped" in out, out)
