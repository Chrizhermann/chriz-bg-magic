"""Synthetic installer tests for the healing of IWDification's spells, which we may not ship.

The fixtures include both direct Cause Wounds spells and the touch-charge delivery a Cause spell
can use.  They contain extra abilities/effects and a shared charge item so preservation and
private cloning are checked without reading an installed game.
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
  INCLUDE ~chriz-bg-magic/lib/cbmagic_fixes.tpa~
END
LANGUAGE ~English~ ~english~ ~chriz-bg-magic/languages/english/setup.tra~
BEGIN ~healing~ DESIGNATED 0
LAM cbmagic_index_scrolls
LAF cbmagic_healing_cure_moderate END
LAF cbmagic_healing_cause_iwd END
"""


def fx(**kw):
    return kw


def _spell(data):
    parsed = ie.parse_spl(data)
    ab_off = struct.unpack_from("<I", data, 0x64)[0]
    for i, ability in enumerate(parsed["abilities"]):
        ability["range"] = struct.unpack_from("<H", data, ab_off + i * 0x28 + 0x0E)[0]
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


def _item_ranges(data):
    ab_off = struct.unpack_from("<I", data, 0x64)[0]
    ab_cnt = struct.unpack_from("<H", data, 0x68)[0]
    return [struct.unpack_from("<H", data, ab_off + a * 0x38 + 0x0E)[0] for a in range(ab_cnt)]


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
        {"target": 5, "range": 1, "casting_time": ct, "effects": [
            fx(opcode=111, target=1, power=level, timing=0, duration=15, resource=item),
            fx(opcode=174, target=1, power=level, timing=1, resource="EFF_P06"),
        ]}
    ], desc=desc)


def _scroll(spell, desc, *, rng=1, learn=False):
    abilities = [[fx(opcode=146, target=1, p2=1, timing=1, resource=spell)]]
    if learn:
        abilities.append([fx(opcode=147, target=1, timing=1, resource=spell)])
    raw = bytearray(ie.make_itm(abilities, desc=desc))
    ab_off = struct.unpack_from("<I", raw, 0x64)[0]
    struct.pack_into("<H", raw, ab_off + 0x0E, rng)
    return bytes(raw)


def _texts():
    values = {
        "CMOD": "Cure Moderate Wounds\n\nCasting Time: 5\nCure Moderate Wounds heals 11 Hit Points and cures intoxication.",
        "CMODER": "Cause Moderate Wounds\n\nCasting Time: 5\nBy casting this spell, the priest deals 11 points of damage. This spell has no effect on undead, constructs, or extraplanar creatures.",
        "CMEDIU": "Cause Medium Wounds\n\nCasting Time: 5\nBy casting this spell, the priest deals 14 points of damage. This spell has no effect on undead, constructs, or extraplanar creatures.",
        "CSERIO": "Cause Serious Wounds\n\nCasting Time: 7\nIt inflicts 17 points of damage. There is no Saving Throw.",
        "CCRITI": "Cause Critical Wounds\n\nCasting Time: 8\nIt inflicts 27 points of damage. There is no Saving Throw.",
    }
    names = list(values)
    refs = {name: i + 1 for i, name in enumerate(names)}
    return refs, ie.make_tlk(["", *(values[name] for name in names)])


SPLPROT = [("0_EA", ["0x10a", "0", "4"]), ("1_GENERAL=UNDEAD", ["0x10b", "4", "1"]),
           ("2_GENERAL!=UNDEAD", ["0x10b", "4", "5"])]


def _game():
    refs, tlk = _texts()
    ids = ie.make_ids([
        (1217, "CLERIC_CURE_MODERATE_WOUNDS"), (1220, "CLERIC_CAUSE_MODERATE_WOUNDS"),
        (1330, "CLERIC_CAUSE_MEDIUM_WOUNDS"), (1414, "CLERIC_CAUSE_SERIOUS_WOUNDS_IWD"),
        (1510, "CLERIC_CAUSE_CRITICAL_WOUNDS_IWD"),
    ])
    spells = {
        "SPPR217.SPL": ie.make_spl(2, 2, [
            {"target": 1, "range": 0, "casting_time": 5, "effects": [fx(opcode=17, target=2, power=2, p1=11, timing=1), fx(opcode=215, target=2, resource="SPHEALIN")]},
            {"target": 1, "range": 30, "casting_time": 5, "min_level": 9, "effects": [fx(opcode=17, target=2, power=2, p1=11, timing=1), fx(opcode=61, target=2, p1=10)]},
        ], desc=refs["CMOD"]),
        "SPPR220.SPL": ie.make_spl(2, 2, [
            {"target": 1, "range": 1, "casting_time": 5, "effects": _direct_damage(2, 11, save=1, special=0x100, extra=True)},
            {"target": 1, "range": 1, "casting_time": 5, "min_level": 9, "effects": _direct_damage(2, 11, save=1, special=0x100)},
        ], desc=refs["CMODER"]),
        "SPPR330.SPL": ie.make_spl(2, 3, [{"target": 1, "range": 1, "casting_time": 5, "effects": _direct_damage(3, 14, save=1, special=0x100)}], desc=refs["CMEDIU"]),
        "SPPR414.SPL": _charge_spell(4, "SERIOUS", 7, refs["CSERIO"]),
        "SPPR510.SPL": _charge_spell(5, "CRITICAL", 8, refs["CCRITI"]),
        # Another producer makes SERIOUS shared; Cause Serious must use a private clone.
        "SPPR999.SPL": _charge_spell(9, "SERIOUS", 5, refs["CSERIO"]),
    }
    scrolls = {
        "SCRL02.ITM": _scroll("SPPR217", refs["CMOD"]), "SCRLC1.ITM": _scroll("SPPR103", refs["CMOD"], rng=30),
        "SCRL08.ITM": _scroll("SPPR220", refs["CMODER"]), "SCRL09.ITM": _scroll("SPPR330", refs["CMEDIU"]),
        "SCRL10.ITM": _scroll("SPPR414", refs["CSERIO"]), "SCRL11.ITM": _scroll("SPPR510", refs["CCRITI"]),
    }
    biff = {
        "SPELL.IDS": ids, "SPLPROT.2DA": ie.make_2da(["STAT", "VALUE", "RELATION"], SPLPROT), **spells, **scrolls,
        "SERIOUS.ITM": _charge_item(4, 17), "CRITICAL.ITM": _charge_item(5, 27),
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
    """The cure rolls, Cause spells keep their delivery, and undead get payload healing first."""
    g = _healing_game(work, weidu)
    before = g.tree()
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, out)

    cure = _spell(g.file("override/SPPR217.SPL"))
    check(all(ability["casting_time"] == 2 and ability["range"] == 10 for ability in cure["abilities"]), f"SPPR217 delivery: {cure}")
    for ability in cure["abilities"]:
        heal = _single_fx(ability["effects"], 17)
        check((heal["p1"], heal["dice"], heal["sides"]) == (4, 2, 8), f"SPPR217: {heal}")
    check("Casting Time: 2" in g.tlk(cure["desc"]) and "Range: 10 ft." in g.tlk(cure["desc"])
          and "heals 2d8 + 4 points" in g.tlk(cure["desc"]), g.tlk(cure["desc"]))
    check(_item_ranges(g.file("override/SCRL02.ITM")) == [10], "SCRL02 range")
    check(_item_ranges(g.file("override/SCRLC1.ITM")) == [10], "SCRLC1 base Cure scroll range")

    # Direct Cause Moderate: two abilities, its Spell save and unrelated fire damage survive.
    direct = _spell(g.file("override/SPPR220.SPL"))
    check(all(ability["casting_time"] == 2 and ability["range"] == 1 for ability in direct["abilities"]), direct)
    for index, ability in enumerate(direct["abilities"]):
        effects = ability["effects"]
        guard, cast, block = effects[:3]
        payload = f"CBHD2{index}"
        check((guard["opcode"], guard["p2"], guard["resource"]) == (318, 2, payload), f"guard: {effects}")
        check((cast["opcode"], cast["resource"], cast["p2"]) == (146, payload, 1), f"cast: {effects}")
        check((block["opcode"], block["p2"], block["resource"]) == (324, 1, "SPPR220"), f"block: {effects}")
        damage = _single_fx(effects, 12, p2=0x400000)
        check((damage["p1"], damage["dice"], damage["sides"], damage["save"], damage["special"]) == (4, 2, 8, 1, 0x100), damage)
        payload_spell = _spell(g.file(f"override/{payload}.SPL"))
        heal = _single_fx(payload_spell["abilities"][0]["effects"], 17)
        check((heal["p1"], heal["dice"], heal["sides"]) == (4, 2, 8), heal)
    check(_single_fx(direct["abilities"][0]["effects"], 12, p2=0x80000)["p1"] == 99, "unrelated damage changed")
    check("Casting Time: 2" in g.tlk(direct["desc"]) and "Range: Touch" in g.tlk(direct["desc"])
          and "Undead are healed for 2d8 + 4" in g.tlk(direct["desc"]), g.tlk(direct["desc"]))

    medium = _spell(g.file("override/SPPR330.SPL"))
    check((medium["abilities"][0]["casting_time"], medium["abilities"][0]["range"]) == (3, 1), medium)
    damage = _single_fx(medium["abilities"][0]["effects"], 12, p2=0x400000)
    check((damage["p1"], damage["dice"], damage["sides"]) == (7, 2, 8), damage)
    check("Casting Time: 3" in g.tlk(medium["desc"]) and "Range: Touch" in g.tlk(medium["desc"])
          and "Undead are healed for 2d8 + 7" in g.tlk(medium["desc"]), g.tlk(medium["desc"]))

    # The shared Serious charge is cloned and retargeted only in Cause Serious.
    serious = _spell(g.file("override/SPPR414.SPL"))
    check((serious["abilities"][0]["casting_time"], serious["abilities"][0]["range"]) == (4, 1), serious)
    create = _single_fx(serious["abilities"][0]["effects"], 111)
    check(create["resource"] == "CBHT90", f"Cause Serious did not retarget private item: {create}")
    check(g.file("override/SERIOUS.ITM") is None, "shared SERIOUS item was edited")
    serious_item = _item(g.file("override/CBHT90.ITM"))[0]
    guard, cast, block = serious_item[:3]
    check((guard["opcode"], guard["p2"], guard["resource"]) == (318, 2, "CBHI900"), serious_item)
    check((cast["opcode"], cast["resource"]) == (146, "CBHI900"), serious_item)
    check((block["opcode"], block["p2"], block["resource"]) == (324, 1, "CBHT90"), serious_item)
    serious_damage = _single_fx(serious_item, 12, p2=0x400000)
    check((serious_damage["p1"], serious_damage["dice"], serious_damage["sides"]) == (7, 3, 8), serious_damage)
    check(_item(g.file("override/CBHT90.ITM"))[1][0]["p1"] == 77, "unrelated charge ability changed")
    check("Undead are healed for 3d8 + 7" in g.tlk(serious["desc"]), g.tlk(serious["desc"]))

    critical_spell = _spell(g.file("override/SPPR510.SPL"))
    check((critical_spell["abilities"][0]["casting_time"], critical_spell["abilities"][0]["range"]) == (5, 1), critical_spell)
    critical = _item(g.file("override/CRITICAL.ITM"))[0]
    critical_damage = _single_fx(critical, 12, p2=0x400000)
    check((critical_damage["p1"], critical_damage["dice"], critical_damage["sides"]) == (12, 4, 8), critical_damage)

    for scroll in ("SCRL02", "SCRL08", "SCRL09", "SCRL10", "SCRL11"):
        _, desc = g.itm_descs(scroll)
        check(desc > 5, f"{scroll} did not get a private updated description")
    for scroll in ("SCRL08", "SCRL09", "SCRL10", "SCRL11"):
        check(_item_ranges(g.file(f"override/{scroll}.ITM")) == [1], f"{scroll} should keep Touch range")
    installed = g.tree()
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, out)
    check(g.tree() == installed, "a second healing install changed the generated resources")
    out = g.uninstall()
    check("SUCCESSFULLY REMOVED" in out, out)
    check(g.tree() == before, "uninstall did not restore the healing batch")


@test
def healing_batch_missing_optional_spells_and_extra_abilities(work, weidu):
    """Absent IWD symbols are logs, while all abilities of the spell that is there still update."""
    refs, tlk = _texts()
    biff = {
        "SPELL.IDS": ie.make_ids([(1217, "CLERIC_CURE_MODERATE_WOUNDS")]),
        "SPLPROT.2DA": ie.make_2da(["STAT", "VALUE", "RELATION"], SPLPROT),
        "SPPR217.SPL": ie.make_spl(2, 2, [
            {"target": 1, "range": 0, "casting_time": 5, "effects": [fx(opcode=17, target=2, p1=11, timing=1), fx(opcode=174, resource="EXTRA")]},
            {"target": 1, "range": 30, "min_level": 12, "casting_time": 5, "effects": [fx(opcode=17, target=2, p1=11, timing=1), fx(opcode=12, target=2, p1=4, p2=0x80000)]},
            {"target": 1, "range": 1, "min_level": 20, "casting_time": 1, "effects": [fx(opcode=17, target=2, p1=11, timing=1)]},
        ], desc=refs["CMOD"]),
        "SCRL02.ITM": _scroll("SPPR217", refs["CMOD"], rng=30, learn=True),
    }
    g = fg.FakeGame(work, weidu, tp2=HEALING_TP2, tlk=tlk, biff=biff)
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, out)
    spell = _spell(g.file("override/SPPR217.SPL"))
    check([ability["casting_time"] for ability in spell["abilities"]] == [2, 2, 2], spell)
    check([ability["range"] for ability in spell["abilities"]] == [10, 10, 10], spell)
    check(_item_ranges(g.file("override/SCRL02.ITM")) == [10, 0], "cast ability range updated without touching learn ability")
    check(all(((_single_fx(a["effects"], 17)["p1"], _single_fx(a["effects"], 17)["dice"], _single_fx(a["effects"], 17)["sides"]) == (4, 2, 8)) for a in spell["abilities"]), spell)
    check(_single_fx(spell["abilities"][1]["effects"], 12, p2=0x80000)["p1"] == 4, "extra effect changed")
    check("CLERIC_CAUSE_MODERATE_WOUNDS) is not in this game; skipped" in out, out)


@test
def healing_other_wording_changes_the_spell_all_the_same(work, weidu):
    """Whatever the old text says, the spell changes and the description is ours."""
    biff = {
        "SPELL.IDS": ie.make_ids([(1217, "CLERIC_CURE_MODERATE_WOUNDS")]),
        "SPPR217.SPL": ie.make_spl(2, 2, [
            {"target": 1, "casting_time": 5, "effects": [fx(opcode=17, target=2, p1=11, timing=1)]},
        ], desc=1),
        "SCRL02.ITM": _scroll("SPPR217", 1),
    }
    g = fg.FakeGame(work, weidu, tp2=HEALING_TP2, tlk=ie.make_tlk(["", "Heilt elf Punkte."]), biff=biff)
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, out)
    spell = _spell(g.file("override/SPPR217.SPL"))
    roll = _single_fx(spell["abilities"][0]["effects"], 17)
    check((roll["p1"], roll["dice"], roll["sides"]) == (4, 2, 8), "the roll depends on the text")
    check(spell["abilities"][0]["casting_time"] == 2, "the casting time depends on the text")
    check(spell["abilities"][0]["range"] == 10, "the range depends on the text")
    check("2d8 + 4" in g.tlk(spell["desc"]) and "Heilt" not in g.tlk(spell["desc"]), "the whole text is ours")


@test
def healing_odd_spells_lose_only_the_part_that_cannot_be_done(work, weidu):
    """No healing effect, or a touch charge that does not exist: the casting time still changes.
    A file too damaged to write into costs only that file."""
    refs, tlk = _texts()
    biff = {
        "SPELL.IDS": ie.make_ids([(1217, "CLERIC_CURE_MODERATE_WOUNDS"), (1414, "CLERIC_CAUSE_SERIOUS_WOUNDS_IWD"),
                                  (1330, "CLERIC_CAUSE_MEDIUM_WOUNDS")]),
        "SPLPROT.2DA": ie.make_2da(["STAT", "VALUE", "RELATION"], SPLPROT),
        "SPPR217.SPL": ie.make_spl(2, 2, [
            {"target": 1, "casting_time": 5, "effects": [fx(opcode=146, target=2, p2=1, timing=1, resource="ELSEWHER")]},
        ], desc=refs["CMOD"]),
        "SPPR414.SPL": _charge_spell(4, "NOITEM", 7, refs["CSERIO"]),
        "SPPR330.SPL": b"not a spell file at all",
        "INERT.ITM": ie.make_itm(),
    }
    g = fg.FakeGame(work, weidu, tp2=HEALING_TP2, tlk=tlk, biff=biff)
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, out)
    check("no healing effect to roll" in out and "NOITEM.itm is not in this game" in out, out)
    check("Cause Medium Wounds (SPPR330) is not patched" in out, out)
    sppr217 = _spell(g.file("override/SPPR217.SPL"))
    check((sppr217["abilities"][0]["casting_time"], sppr217["abilities"][0]["range"]) == (2, 10), "Cure delivery")
    sppr414 = _spell(g.file("override/SPPR414.SPL"))
    check((sppr414["abilities"][0]["casting_time"], sppr414["abilities"][0]["range"]) == (4, 1), "Cause delivery")
