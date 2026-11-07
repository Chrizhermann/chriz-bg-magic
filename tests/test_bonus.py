"""Typed bonuses: real WeiDU installs into fabricated games, plus mocked Lua runtimes.

Fixtures reproduce the delivery/field shapes of spell data without reading or copying
any installed game or third-party resources at test runtime.
"""
import importlib
import re
import struct
from pathlib import Path

import fakegame as fg
import ie
from harness import check, test


TP2 = r"""BACKUP ~weidu_external/backup/chriz-bg-magic~
AUTHOR ~test~
ALWAYS
  INCLUDE ~chriz-bg-magic/lib/cbmagic_shared.tpa~
  INCLUDE ~chriz-bg-magic/lib/cbmagic_spells.tpa~
  INCLUDE ~chriz-bg-magic/lib/cbmagic_fixes.tpa~
  INCLUDE ~chriz-bg-magic/lib/cbmagic_bonus.tpa~
  INCLUDE ~chriz-bg-magic/lib/cbmagic_more.tpa~
END
LANGUAGE ~English~ ~english~ ~chriz-bg-magic/languages/english/setup.tra~
BEGIN ~bonus probe~ DESIGNATED 0
%BODY%
"""
DESCRIPTION = "An existing spell description. This unrelated sentence must survive."


def effect(opcode, p1=0, **kw):
    return {**ie.FX_DEFAULTS, "opcode": opcode, "p1": p1, "duration": 60, "dispel": 3, **kw}


def spell(rows, level=1, **kw):
    return ie.make_spl(level=level, abilities=[{"target": 5, "effects": rows}], desc=0, **kw)


def resref(number):
    return ("SPPR" if number // 1000 == 1 else "SPWI") + f"{number % 1000:03}"


def make_game(work, weidu, resources=None, symbols=(), body="LAF cbmagic_bonus END", **kw):
    biff = {"SPELL.IDS": ie.make_ids(symbols), "INERT.ITM": ie.make_itm(), **(resources or {})}
    return fg.FakeGame(work, weidu, tp2=TP2.replace("%BODY%", body),
                       tlk=ie.make_tlk([DESCRIPTION]), biff=biff, **kw)


def install(g):
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, out)
    return out


def rows(g, name, ability=0):
    return g.spl(name)["abilities"][ability]["effects"]


def resource(g, name):
    """Current bytes through the fake game's own KEY, including unchanged BIFF files."""
    stem, ext = name.rsplit(".", 1)
    return ie.Game(g.root).get(stem, ext)


def state_ids(g):
    text = resource(g, "SPLSTATE.IDS").decode("ascii")
    result = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                result[parts[1].upper()] = int(parts[0], 0)
            except ValueError:
                pass
    return result


def packed(row):
    return ie.pack_fx(**row)


def assert_preserved(original, actual, owned=("resource",)):
    check(all(original[key] == actual[key] for key in ie.FX_FIELDS if key not in owned),
          f"unowned effect fields changed: {original} -> {actual}")


def eff_v2(opcode, p1=0, resource_name="", *, flags=0x103, timing=0):
    """An external effect with independent level bounds and provenance metadata."""
    raw = bytearray(0x110)
    raw[:8] = raw[8:16] = b"EFF V2.0"
    for at, value in ((0x10, opcode), (0x14, 2), (0x18, 4), (0x1C, p1),
                      (0x20, 0), (0x24, timing), (0x28, 72), (0x38, 19), (0x3C, 2),
                      (0x40, 1), (0x44, -2), (0x48, 0x100), (0x4C, 5),
                      (0x54, 4), (0x58, 18), (0x5C, flags), (0x60, 123),
                      (0x90, 1), (0x9C, 0x42), (0xC8, 13), (0xD0, 7)):
        struct.pack_into("<I", raw, at, value & 0xFFFFFFFF)
    struct.pack_into("<HH", raw, 0x2C, 80, 21)
    raw[0x30:0x38] = resource_name.encode("ascii").ljust(8, b"\0")
    raw[0x94:0x9C] = b"UNOWNED\0"
    raw[0xA8:0xAF] = b"Foreign"
    return bytes(raw)


def eff_op(data):
    return struct.unpack_from("<I", data, 0x10)[0]


def eff_tag(data):
    return data[0x30:0x38].rstrip(b"\0").decode("ascii")


@test
def bonus_types_symbols_and_preservation(work, weidu):
    cases = [
        (2950, "WIZARD_EMOTION_HOPE", "CBTMORAL", {54, 73, 33, 34, 35, 36, 37, 325}),
        (1950, "CLERIC_PRAYER", "CBTFAVOR", {54, 73, 33, 34, 35, 36, 37, 325}),
        (2951, "WIZARD_LUCK", "CBTLUCK", {22, 33, 34, 35, 36, 37, 325}),
        (2952, "WIZARD_BLUR", "CBTDODGE", {0, 33, 34, 35, 36, 37, 325}),
        (1952, "CLERIC_ENTROPY_SHIELD", "CBTDEFLE", {0, 33, 34, 35, 36, 37, 325}),
        (2953, "WIZARD_SPIRIT_ARMOR", "CBTDEFLE", {33, 34, 35, 36, 37, 325}),
        (1953, "CLERIC_CURSE", "CBTCURSE", {54, 73, 33, 34, 35, 36, 37, 325, 22}),
    ]
    for number, symbol, existing in (
        (2956, "WIZARD_EMOTION_COURAGE", 0), (1956, "CLERIC_RIGHTEOUS_WRATH_OF_THE_FAITHFUL", 0),
        (1957, "CLERIC_BLOOD_RAGE", 0), (1958, "CLERIC_ANIMAL_RAGE", 0),
        (1959, "CLERIC_BLESS", 1), (1960, "CLERIC_RECITATION", 1),
        (1962, "CLERIC_DEFENSIVE_HARMONY", 3), (1963, "CLERIC_AURA_OF_FLAMING_DEATH", 4),
        (1964, "CLERIC_BARKSKIN", 5), (1965, "CLERIC_DOOM", 6), (1966, "CLERIC_UNHOLY_BLIGHT", 6),
    ):
        cases.append((number, symbol, cases[existing][2], cases[existing][3]))
    cases.append((1961, "CLERIC_CHANT", "CHANT", {22, 33, 34, 35, 36, 37, 325}))
    resources, originals = {}, {}
    for number, symbol, tag, eligible in cases:
        sign = -1 if tag == "CBTCURSE" else 1
        values = [effect(op, sign * 2, power=4, save=0x1000001, bonus=-3, prob1=83, prob2=19,
                         dice=12, sides=3, special=0x400) for op in (0, 22, 33, 34, 35, 36, 37, 54, 73, 325)]
        # These are semantically outside the typed stat rules.
        values += [effect(0, -4), effect(0, 3, p2=1), effect(166, -20), effect(60, 25),
                   effect(44, 2), effect(1, 1), effect(18, 9), effect(132, 1)]
        originals[resref(number)] = values
        resources[resref(number) + ".SPL"] = spell(values)
    unrelated = spell([effect(325, -4), effect(54, -4), effect(0, -4)])
    resources["SPWI954.SPL"] = resources["SPWI955.SPL"] = unrelated
    symbols = [(n, sym) for n, sym, _, _ in cases] + [(2954, "WIZARD_GREATER_MALISON"), (2955, "WIZARD_SLOW")]
    g = make_game(work, weidu, resources, symbols)
    install(g)
    typed_state = state_ids(g)["CBM_BONUS_TYPED"]
    for number, symbol, tag, eligible in cases:
        name, expected = resref(number), originals[resref(number)]
        result = rows(g, name)
        refresh = [r for r in result if r["opcode"] == 321 and r["resource"] == name]
        check(len(refresh) == 1 and refresh[0]["target"] == 2 and result.index(refresh[0]) <
              next(i for i, row in enumerate(result) if row["opcode"] not in (206, 321)),
              f"{symbol}: recipient refresh must precede the payload despite ability target 5")
        retained = [r for r in result if r["opcode"] not in (321, 328)]
        check(len(retained) == len(expected), f"{symbol}: lost or duplicated original effects")
        tagged = []
        for before, after in zip(expected, retained):
            selected = before["opcode"] in eligible
            if before["opcode"] == 0:
                selected = selected and before["p2"] == 0 and before["p1"] > 0
            selected = selected and (tag != "CBTCURSE" or before["p1"] < 0)
            expected_tag = ("CBTLUCK" if before["opcode"] == 22 else "CBTFAVOR") if tag == "CHANT" else tag
            if symbol == "CLERIC_RIGHTEOUS_WRATH_OF_THE_FAITHFUL" and before["opcode"] == 1:
                # An extra attack: a tag of its own, and its value kept for the runtime.
                selected, expected_tag = True, "CBTAPR"
                check(after["special"] == before["p1"], f"{symbol}: extra attack value not kept: {after}")
                after = {**after, "special": before["special"]}
            check(after["resource"] == (expected_tag if selected else before["resource"]), f"{symbol}: {after}")
            assert_preserved(before, after)
            if selected:
                tagged.append(after)
        markers = [r for r in result if r["opcode"] == 328]
        check(len(markers) == len(tagged), f"{symbol}: marker coverage differs from typed effects")
        for marker, original in zip(markers, tagged):
            check(marker["p2"] == typed_state and marker["resource"] == "CBTSTATE", "wrong typed state")
            assert_preserved(original, marker, ("opcode", "p1", "p2", "resource", "special"))
    for name in ("SPWI954", "SPWI955"):
        check(resource(g, name + ".SPL") == unrelated, f"unlisted spell {name} changed")


@test
def bonus_count_once_conversions_and_chant_split(work, weidu):
    specs = [(1950, "CLERIC_BLESS", 130, 1), (1951, "CLERIC_CHANT", 131, 2),
             (2951, "WIZARD_LUCK", 133, 1), (1953, "CLERIC_CURSE", 137, 2)]
    resources = {}
    for number, symbol, op, amount in specs:
        main = effect(op, amount, duration=90, power=3, save=1, bonus=-2, prob1=81, prob2=17)
        additional = [effect(33, 1), effect(132, 1)] if op == 131 else [effect(142, p2=32)]
        resources[resref(number) + ".SPL"] = spell([main, *additional])
    # A native count-once effect reads its signed low byte.
    chant_first = ie.parse_spl(resources["SPPR951.SPL"])["abilities"][0]
    resources["SPPR951.SPL"] = ie.make_spl(abilities=[chant_first, {"effects": [effect(131, 255)]}], desc=0)
    symbols = [(n, sym) for n, sym, _, _ in specs]
    g = make_game(work, weidu, resources, symbols)
    install(g)
    for number, symbol, op, amount in specs:
        result = rows(g, resref(number))
        check(not any(r["opcode"] in (130, 131, 133, 137) for r in result), symbol + " not converted")
        check(result[0]["opcode"] == 321 and result[0]["target"] == 2, symbol + " refresh missing")
        converted = [r for r in result if r["opcode"] in (54, 73, 23, 22)]
        if op == 130:
            check([(r["opcode"], r["p1"], r["resource"]) for r in converted] ==
                  [(54, 1, "CBTFAVOR"), (73, 1, "CBTFAVOR"), (23, 5, "")], "Bless native benefits")
        else:
            check(len(converted) == 1 and converted[0]["opcode"] == 22, symbol + " luck conversion")
            check(converted[0]["p1"] == (-amount if op == 137 else amount), symbol + " sign")
            check(converted[0]["resource"] == ("CBTCURSE" if op == 137 else "CBTLUCK"), symbol + " type")
        for converted_row in converted:
            check((converted_row["duration"], converted_row["save"], converted_row["bonus"],
                   converted_row["prob1"], converted_row["prob2"]) == (90, 1, -2, 81, 17), "conversion lost conditions")
    chant = rows(g, "SPPR951")
    check(any(r["opcode"] == 33 and r["resource"] == "CBTFAVOR" for r in chant), "Chant save type")
    check(any(r["opcode"] == 132 and r["resource"] == "" for r in chant), "opcode 132 changed")
    check(any(r["opcode"] == 22 and r["p1"] == -1 for r in rows(g, "SPPR951", 1)), "signed low byte lost")


@test
def bonus_optional_spells_missing_and_stamped_states(work, weidu):
    g = make_game(work, weidu)
    out = install(g)
    check(not fg.with_warnings(out), "missing IWD spells must not warn")
    for symbol in ("CLERIC_PRAYER", "CLERIC_RECITATION", "WIZARD_EMOTION_HOPE", "CLERIC_ENTROPY_SHIELD"):
        check(symbol + " absent; skipped" in out, symbol + " not explicitly logged")
    ids = state_ids(g)
    check(0 <= ids["CBM_BONUS_PASS"] <= 255 and 0 <= ids["CBM_BONUS_TYPED"] <= 255, "invalid state")
    check(ids["CBM_BONUS_PASS"] != ids["CBM_BONUS_TYPED"], "private states collide")
    runtime = g.file("override/M_CBMBON.lua").decode("utf-8")
    check("%CBM_BONUS_" not in runtime, "unexpanded runtime token")
    check(f'local PASS_STATE = {ids["CBM_BONUS_PASS"]}' in runtime, "wrong pass state stamp")
    check(f'local TYPED_STATE = {ids["CBM_BONUS_TYPED"]}' in runtime, "wrong typed state stamp")


@test
def bonus_effects_that_cannot_be_counted_stay_untyped(work, weidu):
    """An effect that sets a value or changes base stats keeps working; its neighbours get a type."""
    for index, (op, mode, timing) in enumerate(((54, 1, 0), (73, 2, 0), (325, 1, 0), (54, 0, 1))):
        g = make_game(work / str(index), weidu,
                      {"SPWI950.SPL": spell([effect(op, 2, p2=mode, timing=timing), effect(37, 1)])},
                      [(2950, "WIZARD_EMOTION_HOPE")])
        out = install(g)
        check(not fg.with_warnings(out), out)
        check("stays without a type" in out, "the effect left out is not named in the log")
        found = rows(g, "SPWI950")
        check(any(r["opcode"] == op and r["p2"] == mode and r["timing"] == timing and r["resource"] == ""
                  for r in found), f"effect {op}/{mode}/{timing} changed")
        check(any(r["opcode"] == 37 and r["resource"] == "CBTMORAL" for r in found), "its neighbour got no type")


@test
def righteous_wrath_and_haste_leave_each_other_alone(work, weidu):
    payload = spell([effect(321, resource="SPWI305", p2=16, timing=1), effect(321, resource="OTHERSPL", timing=1),
                     effect(206, -1, resource="SPRA301", p2=16), effect(206, -1, resource="SPWI613"),
                     effect(101, p2=16), effect(101, p2=5), effect(169, p2=38), effect(169, p2=13),
                     effect(267, 14667, p2=16), effect(54, 2), effect(1, 1)], level=5)
    root = spell([effect(146, resource="WRATHA", p2=1, timing=1)], level=5)
    improved = spell([effect(1, 1), effect(54, 2)], level=6)
    g = make_game(work, weidu,
                  {"SPPR518.SPL": root, "WRATHA.SPL": payload, "SPWI613.SPL": improved, "SPWI305.SPL": spell([effect(16)])},
                  [(1518, "CLERIC_RIGHTEOUS_WRATH_OF_THE_FAITHFUL"), (2613, "WIZARD_IMPROVED_HASTE"), (2305, "WIZARD_HASTE")],
                  body="LAF cbmagic_more_righteous_wrath END\nLAF cbmagic_bonus END")
    install(g)
    child = next(r for r in rows(g, "SPPR518") if r["opcode"] == 146)["resource"]
    found = rows(g, child)
    kept = {(r["opcode"], r["p2"], r["resource"]) for r in found}
    for gone in ((321, 16, "SPWI305"), (206, 16, "SPRA301"), (206, 0, "SPWI613"), (101, 16, ""), (169, 38, ""), (267, 16, "")):
        check(gone not in kept, f"still blocks Haste: {gone}")
    for stays in ((321, 0, "OTHERSPL"), (101, 5, ""), (169, 13, "")):
        check(stays in kept, f"unrelated row lost: {stays}")
    attack = next(r for r in found if r["opcode"] == 1)
    check((attack["resource"], attack["special"], attack["p1"]) == ("CBTAPR", 1, 1), "extra attack not tagged")
    check(any(r["opcode"] == 54 and r["resource"] == "CBTMORAL" for r in found), "THAC0 lost its type")
    haste = rows(g, "SPWI613")
    check(any(r["opcode"] == 1 and r["resource"] == "CBTAPR" for r in haste), "Improved Haste's attack not tagged")
    check(any(r["opcode"] == 54 and r["resource"] == "" for r in haste), "Improved Haste's THAC0 got a type")
    text = g.tlk(g.spl("SPPR518")["desc"])
    check("only one extra attack counts" in text and "canceling" not in text, "description not written")


@test
def bonus_all_abilities_and_casting_order(work, weidu):
    untouched = effect(139, 1234, target=1, timing=1, duration=0)
    data = ie.make_spl(level=2, desc=0, extra_fx_first=True, casting=[untouched], abilities=[
        {"min_level": level, "target": 5, "effects": [effect(142, p2=65), effect(54, value, duration=duration)]}
        for level, value, duration in ((1, 1, 60), (9, 2, 90), (17, 3, 120))])
    g = make_game(work, weidu, {"SPPR950.SPL": data}, [(1950, "CLERIC_PRAYER")])
    install(g)
    parsed = g.spl("SPPR950")
    check(parsed["casting"] == [untouched], "casting effects after abilities corrupted")
    for ability, amount, duration in zip(parsed["abilities"], (1, 2, 3), (60, 90, 120)):
        typed = [r for r in ability["effects"] if r["opcode"] == 54]
        check(len(typed) == 1 and typed[0]["p1"] == amount and typed[0]["duration"] == duration,
              "multiple abilities lost their values")


@test
def bonus_shared_eff_and_payload_chain_preserve_originals(work, weidu):
    shared = eff_v2(54, -2)
    bridge = eff_v2(146, resource_name="ODDCHILD")
    child = spell([effect(177, resource="SHARED"), effect(142, p2=41)])
    root = spell([effect(177, resource="BRIDGE")])
    outsider = spell([effect(177, resource="SHARED")])
    resources = {"SPPR950.SPL": root, "BRIDGE.EFF": bridge, "ODDCHILD.SPL": child,
                 "SHARED.EFF": shared, "OUTSIDE.SPL": outsider}
    g = make_game(work, weidu, resources, [(1950, "CLERIC_UNHOLY_BLIGHT")])
    out = install(g)
    for name in ("BRIDGE.EFF", "ODDCHILD.SPL", "SHARED.EFF", "OUTSIDE.SPL"):
        check(resource(g, name) == resources[name], name + " changed in place")
    delivery = [r for r in rows(g, "SPPR950") if r["opcode"] == 177]
    check(len(delivery) == 1 and delivery[0]["resource"] != "BRIDGE", "root not redirected")
    private_bridge = resource(g, delivery[0]["resource"] + ".EFF")
    private_child = eff_tag(private_bridge)
    check(private_child != "ODDCHILD", "unrelated-name payload not isolated")
    effects = rows(g, private_child)
    effs = [resource(g, r["resource"] + ".EFF") for r in effects if r["opcode"] == 177]
    tagged = [data for data in effs if eff_op(data) == 54]
    markers = [data for data in effs if eff_op(data) == 328]
    check(len(tagged) == len(markers) == 1 and eff_tag(tagged[0]) == "CBTCURSE", "EFF typed values/markers")
    for actual in (tagged[0], markers[0]):
        for start, stop in ((0x14, 0x1C), (0x24, 0x30), (0x38, 0x48), (0x4C, 0x110)):
            check(actual[start:stop] == shared[start:stop], f"V2 metadata lost at {start:#x}")
    check("direct spell users; isolating" in out, "sharing analysis not logged")


@test
def bonus_external_timing_comes_from_delivery(work, weidu):
    # Native 177 overwrites the decoded EFF timing and duration on every application.
    # A stored permanent EFF is therefore a timed modifier under a timed wrapper.
    for index, stored_timing in enumerate((1, 4, 7)):
        original = eff_v2(54, -2, timing=stored_timing)
        g = make_game(work / str(index), weidu,
                      {"SPPR950.SPL": spell([effect(177, resource="TIMED", duration=24)]),
                       "TIMED.EFF": original}, [(1950, "CLERIC_UNHOLY_BLIGHT")])
        install(g)
        leaves = [resource(g, r["resource"] + ".EFF") for r in rows(g, "SPPR950") if r["opcode"] == 177]
        check(any(eff_op(data) == 54 and eff_tag(data) == "CBTCURSE" for data in leaves),
              "timed wrapper's external modifier was not tagged")
        check(all(struct.unpack_from("<I", data, 0x24)[0] == stored_timing for data in leaves),
              "stored EFF timing was unnecessarily overwritten")
        check(resource(g, "TIMED.EFF") == original, "shared EFF changed")
    # Conversely, an immediate permanent wrapper makes its child a base-stat change.
    original = spell([effect(177, resource="BASE", timing=1)])
    g = make_game(work / "invalid", weidu,
                  {"SPPR950.SPL": original, "BASE.EFF": eff_v2(54, -2)}, [(1950, "CLERIC_UNHOLY_BLIGHT")])
    out = install(g)
    check("base stats for good" in out and not fg.with_warnings(out), out)
    check(resource(g, "SPPR950.SPL") == original, "a permanent wrapper's spell changed")


@test
def bonus_conditional_delivery_and_invalid_graphs(work, weidu):
    leaf = spell([effect(54, 2), effect(73, 1)])
    root = spell([effect(148, resource="ROUTE", p2=1)])
    route = spell([effect(326, resource="PAYLOAD", p2=7)])
    resources = {"SPPR950.SPL": root, "ROUTE.SPL": route, "PAYLOAD.SPL": leaf}
    g = make_game(work / "valid", weidu, resources, [(1950, "CLERIC_PRAYER")])
    install(g)
    first = next(r for r in rows(g, "SPPR950") if r["opcode"] == 148)
    check(first["p2"] == 1 and first["resource"] != "ROUTE", "point-target delivery changed")
    second = next(r for r in rows(g, first["resource"]) if r["opcode"] == 326)
    check(second["p2"] == 7 and second["resource"] != "PAYLOAD", "conditional delivery filter changed")
    check(any(r["opcode"] == 54 and r["resource"] == "CBTFAVOR" for r in rows(g, second["resource"])),
          "conditional payload not tagged")
    for name in ("ROUTE.SPL", "PAYLOAD.SPL"):
        check(resource(g, name) == resources[name], "shared conditional delivery changed")
    # A branch that cannot be followed stays as it is; the rest of the spell gets its type.
    broken = [
        (146, "SPPR950", {}, "reached a second time"),
        (177, "MISSING", {}, "not in this game"),
        (177, "TRUNC", {"TRUNC.EFF": b"EFF V2.0"}, "shorter than an EFF file"),
        (146, "BADSPL", {"BADSPL.SPL": b"SPL V1  "}, "shorter than an SPL header"),
    ]
    for index, (op, target, extra, reason) in enumerate(broken):
        files = {"SPPR950.SPL": spell([effect(op, resource=target), effect(54, 2)]), **extra}
        g = make_game(work / str(index), weidu, files, [(1950, "CLERIC_PRAYER")])
        out = install(g)
        check(not fg.with_warnings(out), out)
        check(reason in out, "the branch left out is not named in the log:\n" + out)
        found = rows(g, "SPPR950")
        check(any(r["opcode"] == op and r["resource"] == target for r in found), "the branch changed")
        check(any(r["opcode"] == 54 and r["resource"] == "CBTFAVOR" for r in found), "the rest of the spell got no type")


@test
def bonus_second_direct_pass_is_stable(work, weidu):
    resources = {"SPPR950.SPL": spell([effect(177, resource="BLSSDATA")]),
                 "BLSSDATA.EFF": eff_v2(130, 1, flags=3),
                 "SPWI950.SPL": spell([effect(146, resource="ODDHOPE")]),
                 "ODDHOPE.SPL": spell([effect(54, 2), effect(73, 2)]),
                 "SPPR951.SPL": spell([effect(98, 1, p2=3)], level=5),
                 "SPPR952.SPL": spell([effect(98, 2, p2=3)], level=7)}
    symbols = [(1950, "CLERIC_BLESS"), (2950, "WIZARD_EMOTION_HOPE"),
               (1951, "CLERIC_CBMAGIC_MASS_REGENERATE"), (1952, "CLERIC_REGENERATE")]
    body = "LAF cbmagic_bonus END\nCOPY ~override~ ~first-pass~\nLAF cbmagic_bonus END"
    g = make_game(work, weidu, resources, symbols, body=body)
    install(g)
    first = {p.name.upper(): p.read_bytes() for p in (g.root / "first-pass").iterdir() if p.is_file()}
    second = {p.name.upper(): p.read_bytes() for p in (g.root / "override").iterdir() if p.is_file()}
    check(first.keys() == second.keys(), f"second pass changed resources: {first.keys() ^ second.keys()}")
    for name in first:
        check(first[name] == second[name], "second direct pass changed " + name)


@test
def bonus_families_every_pair_and_linked_payloads(work, weidu):
    specs = [(2950, "WIZARD_TENSERS_TRANSFORMATION", 6), (1950, "CLERIC_HOLY_POWER", 4),
             (1951, "CLERIC_RIGHTEOUS_MAGIC", 5), (1952, "CLERIC_CHAMPIONS_STRENGTH", 5),
             (1953, "CLERIC_BLOOD_RAGE", 4), (1954, "CLERIC_ANIMAL_RAGE", 5)]
    resources = {}
    for number, _, level in specs:
        resources[resref(number) + ".SPL"] = spell([effect(44, 18, p2=1, duration=42),
                                                    effect(206, resource="FOREIGN", duration=19)], level=level)
    regeneration = [(1955, "CLERIC_REGENERATE", 7), (1956, "CLERIC_CBMAGIC_MASS_REGENERATE", 5),
                    (2951, "WIZARD_TROLLISH_FORTITUDE", 6)]
    for number, _, level in regeneration:
        resources[resref(number) + ".SPL"] = spell([effect(146, resource="REGEN" + str(level))], level=level)
        resources["REGEN" + str(level) + ".SPL"] = spell([effect(98, 1, p2=3, duration=54)], level=level)
    g = make_game(work, weidu, resources, [(n, sym) for n, sym, _ in specs + regeneration])
    install(g)
    for number, _, level in specs:
        result = rows(g, resref(number))
        remove_positions = [i for i, r in enumerate(result) if r["opcode"] == 321]
        check(remove_positions == list(range(len(remove_positions))),
              "family removals must precede new protections and buffs")
        foreign = [r for r in result if r["resource"] == "FOREIGN"]
        check(foreign == [effect(206, resource="FOREIGN", duration=19)], "unrelated protection changed")
        for other, _, other_level in specs:
            removes = [r for r in result if r["opcode"] == 321 and r["resource"] == resref(other)]
            blocks = [r for r in result if r["opcode"] == 206 and r["resource"] == resref(other)]
            check(len(removes) == int(other_level <= level), f"remove pair {number}/{other}")
            check(len(blocks) == int(other_level < level), f"block pair {number}/{other}")
            check(all(r["duration"] == 42 and r["dispel"] == 3 for r in blocks), "family lifetime/dispellability")
            check(all(result.index(r) < next(i for i, row in enumerate(result) if row["opcode"] == 44)
                      for r in removes), "family removal occurs after buff")
    children = {}
    for number, _, level in regeneration:
        child = next(r["resource"] for r in rows(g, resref(number)) if r["opcode"] == 146)
        check(child != "REGEN" + str(level), "family payload not isolated")
        children[number] = child
        check(resource(g, "REGEN" + str(level) + ".SPL") == resources["REGEN" + str(level) + ".SPL"],
              "family original child changed")
    for number, _, level in regeneration:
        result = rows(g, children[number])
        for other, _, other_level in regeneration:
            if other == number:
                continue
            for target in (resref(other), children[other]):
                check(any(r["opcode"] == 321 and r["resource"] == target for r in result) == (other_level <= level),
                      f"family child removal {number}/{other}/{target}")
                block = [r for r in result if r["opcode"] == 206 and r["resource"] == target]
                check(bool(block) == (other_level < level), f"family child block {number}/{other}/{target}")
                check(all(r["duration"] == 54 for r in block), "child family lifetime")


@test
def bonus_pierce_magic_install_choice_and_preservation(work, weidu):
    mr = effect(166, -15, duration=90, power=6, dispel=2, save=1, bonus=-3, prob1=83, prob2=12)
    other = [effect(221, 8, resource="PROTECT"), effect(166, 25, p2=1), effect(174, resource="VISUAL")]
    # The callback and its portrait row are deliberately reordered around an unrelated
    # effect. A second ability has the same native row but no callback and must stay put.
    portrait = effect(142, p2=106, target=2, timing=4, duration=99, dispel=2, save=1, bonus=-3)
    foreign_portrait = effect(142, p2=106, target=1, timing=4, duration=98, dispel=3, save=2, bonus=4)
    data = ie.make_spl(level=6, abilities=[
        {"target": 5, "effects": [other[0], portrait, mr, *other[1:]]},
        {"target": 5, "effects": [foreign_portrait, effect(174, resource="SECOND")]},
    ], desc=0)
    resources = {"SPWI950.SPL": data}
    for enabled in (False, True):
        g = make_game(work / str(int(enabled)), weidu, resources, [(2950, "WIZARD_PIERCE_MAGIC")],
                      override={"M___EEex.lua": b"-- synthetic EEex bootstrap\n"} if enabled else {})
        out = g.install()
        check(fg.installed_ok(out), out)  # Deliberately varied prose may log an owned-sentence warning.
        if not enabled:
            check(resource(g, "SPWI950.SPL") == data, "without EEex Pierce changed")
            check("EEex bootstrap absent" in out, "install choice not explained")
        else:
            result = rows(g, "SPWI950")
            callbacks = [r for r in result if r["opcode"] == 402]
            check(len(callbacks) == 1 and callbacks[0]["resource"] == "CBMBPM", "MR callback missing")
            assert_preserved(mr, callbacks[0], ("opcode", "p1", "p2", "resource", "timing", "duration"))
            check(callbacks[0]["timing"] == 1 and callbacks[0]["duration"] == 0, "callback must fire once")
            icons = [r for r in result if r["opcode"] == 142 and r["p2"] == 106]
            check(len(icons) == 1 and icons[0]["timing"] == 0 and icons[0]["duration"] == 30,
                  f"Pierce portrait duration: {icons}")
            check([r for r in result if r["opcode"] not in (402, 142)] == other,
                  "Pierce unrelated effects changed")
            check(rows(g, "SPWI950", 1) == [foreign_portrait, effect(174, resource="SECOND")],
                  "Pierce changed a native portrait row outside its callback group")


@test
def bonus_state_allocation_collisions_and_exhaustion(work, weidu):
    existing = [(0, "CHAOTIC_COMMANDS"), (255, "FOREIGN_HIGH"), (254, "CBM_BONUS_PASS")]
    g = make_game(work / "reuse", weidu, {"SPLSTATE.IDS": ie.make_ids(existing)})
    install(g)
    ids = state_ids(g)
    check(ids["FOREIGN_HIGH"] == 255 and ids["CBM_BONUS_PASS"] == 254 and ids["CBM_BONUS_TYPED"] == 253,
          "allocation did not preserve/reuse existing states")
    # A marker that is not ours alone is given up for a free one.
    moved = (
        [(255, "CBM_BONUS_PASS"), (255, "FOREIGN")],
        [(254, "CBM_BONUS_PASS"), (255, "CBM_BONUS_PASS")],
        [(256, "CBM_BONUS_PASS")],
    )
    for index, entries in enumerate(moved):
        g = make_game(work / str(index), weidu, {"SPLSTATE.IDS": ie.make_ids(entries)})
        install(g)
        runtime = g.file("override/M_CBMBON.lua").decode("utf-8")
        passes = int(re.search(r"local PASS_STATE = (\d+)", runtime).group(1))
        typed = int(re.search(r"local TYPED_STATE = (\d+)", runtime).group(1))
        taken = {value for value, _ in entries}
        check(passes != typed and passes <= 255 and typed <= 255 and not taken & {passes, typed},
              f"markers {passes}, {typed} clash with {entries}")
    # No free state at all: only the bonus types stay out.
    full = [(value, "FOREIGN_" + str(value)) for value in range(256)]
    data = spell([effect(54, 2)])
    g = make_game(work / "full", weidu, {"SPLSTATE.IDS": ie.make_ids(full), "SPPR950.SPL": data},
                  [(1950, "CLERIC_PRAYER")])
    out = install(g)
    check("bonus types left out" in out and not fg.with_warnings(out), out)
    check(resource(g, "SPPR950.SPL") == data, "a spell changed without a marker to count it")
    check(not (Path(g.root) / "override/M_CBMBON.lua").exists(), "listener installed without markers")


@test
def bonus_description_strings_and_scrolls(work, weidu):
    data = spell([effect(54, 2), effect(73, 1), effect(37, 3)])
    scroll = ie.make_itm([[effect(146, resource="SPPR950"), effect(147, resource="SPPR950")]],
                         desc=0, desc_unid=0)
    untouched = spell([effect(139, 7)])
    g = make_game(work, weidu, {"SPPR950.SPL": data, "SCROLL.ITM": scroll, "OUTSIDE.SPL": untouched},
                  [(1950, "CLERIC_PRAYER")])
    install(g)
    new_ref = g.spl("SPPR950")["desc"]
    check(new_ref != 0 and g.tlk(0) == DESCRIPTION, "shared description overwritten")
    text = g.tlk(new_ref)
    for fragment in (DESCRIPTION, "THAC0 +2 (Favor)", "damage +1 (Favor)", "save vs. spell +3 (Favor)"):
        check(fragment in text, "missing description fragment " + fragment)
    for scroll_ref in g.itm_descs("SCROLL"):
        check(scroll_ref != 0 and "THAC0 +2 (Favor)" in g.tlk(scroll_ref), "scroll description not updated")
    check(resource(g, "OUTSIDE.SPL") == untouched, "shared strref consumer changed")


@test
def bonus_lua_runtime_lua53_and_luajit(work, weidu):
    template = (fg.MOD / "lua/M_CBMBON.lua").read_text(encoding="utf-8")
    suite = (Path(__file__).parent / "bonus_runtime.lua").read_text(encoding="utf-8")
    for implementation in ("lupa.lua53", "lupa.luajit21"):
        runtime = importlib.import_module(implementation).LuaRuntime()
        count = runtime.execute(suite)(template)
        check(count >= 600, implementation + " runtime assertions, including inline EFF cases, were not run")
