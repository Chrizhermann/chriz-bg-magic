"""Synthetic coverage of base-game Character Record entries and their lifetimes."""
import fakegame as fg
import ie
from harness import check, test


def effect(opcode, **kw):
    return {"opcode": opcode, **kw}


def spell(*effects, target=2, name=-1):
    return ie.make_spl(abilities=[{"target": target, "effects": list(effects)}], name=name)


def rows(game, resref):
    data = game.file(f"override/{resref}.SPL") or ie.Game(game.root).get(resref, "SPL")
    return [effect for ability in ie.parse_spl(data)["abilities"] for effect in ability["effects"]]


def icon_rows(game):
    text = game.file("override/STATDESC.2DA").decode("latin-1")
    return {parts[2].upper(): (int(parts[0]), int(parts[1])) for parts in
            (line.split() for line in text.splitlines()) if len(parts) == 3 and parts[0].isdigit()}


def statdesc_labels(game):
    text = game.file("override/STATDESC.2DA").decode("latin-1")
    return {int(parts[0]): (int(parts[1]), parts[2]) for parts in
            (line.split() for line in text.splitlines()) if len(parts) == 3 and parts[0].isdigit()}


def record_inputs():
    """One compact data set covers every requested group, with reordered neighbours too."""
    timed = dict(timing=4, duration=21, dispel=2, save=1, bonus=-2, prob1=77, prob2=9)
    resources = {
        "STATES.BAM": ie.make_states_bam(),
        "DUMMY.ITM": ie.make_itm(),
        "STATDESC.2DA": ie.make_2da(["STRREF", "BAM"],
                                     [(str(row), ["1", "****"]) for row in range(148)]),
        # A. wrong names, including the Stinking Cloud payload and Mimic Web.
        "SPWI315.SPL": spell(effect(142, p2=23), effect(54, p1=1)),
        "SPWM126.SPL": spell(effect(142, p2=23)),
        "OHBPROG.SPL": spell(effect(142, p2=9)),
        "OHBPROG1.SPL": spell(effect(142, p2=9)),
        "OHPRGD10.SPL": spell(effect(142, p2=9)),
        "SPCL938.SPL": spell(effect(142, p2=147)),
        "SPDWD02.SPL": spell(effect(142, p2=147)),
        "SPWI802.SPL": spell(effect(142, p2=28), effect(201, p2=4)),
        "SPWI618.SPL": spell(effect(201, p2=4), effect(142, p2=28)),
        "SPIN710.SPL": spell(effect(201, p2=4), effect(142, p2=28)),
        "SPWI213.SPL": spell(effect(146, resource="SPWI213D")),
        "SPWI213D.SPL": spell(effect(54, p1=2), effect(142, target=2, p2=126, **timed),
                                effect(39, target=2, **timed)),
        "SPIN940.SPL": spell(effect(39, target=2, **timed), effect(142, target=2, p2=126, **timed)),
        "SPWI004.SPL": spell(effect(39, target=2, **timed), effect(142, target=2, p2=126, **timed)),
        "SPWM187.SPL": spell(effect(39, target=2, **timed), effect(142, target=2, p2=126, **timed)),
        "SPIN566.SPL": spell(effect(142, p2=13, duration=3), effect(109, duration=21)),
        # B. missing entries, deliberately with unrelated entries between anchors and icons.
        "SPWI201.SPL": spell(effect(65, **timed), effect(174, resource="OTHER")),
        "SPDM102.SPL": spell(effect(174, resource="OTHER"), effect(65, **timed)),
        "SPIN943.SPL": spell(effect(65, **timed)),
        "SPPR613.SPL": spell(effect(174, resource="OTHER"), effect(197, **timed)),
        "OHTYR2.SPL": spell(effect(54, **timed)),
        "SPIN682.SPL": spell(effect(30, **timed)),
        "SPIN532.SPL": spell(effect(29, **timed)),
        "SPWI955.SPL": spell(effect(54, **timed)),
        "SPWI954.SPL": spell(effect(102, timing=4, duration=12), name=10),
        "SPWISH08.SPL": spell(effect(44, p1=25, **timed)),
        "SPWISH20.SPL": spell(effect(18, **timed), name=11),
        "SPWISH21.SPL": spell(effect(18, **timed), name=11),
        "SPWISH41.SPL": spell(effect(6, **timed)), "SPWISH42.SPL": spell(effect(10, **timed)),
        "SPWISH43.SPL": spell(effect(15, **timed)), "SPWISH44.SPL": spell(effect(19, **timed)),
        "SPWISH45.SPL": spell(effect(49, **timed)),
        "SPCL751A.SPL": spell(effect(128, target=2, **timed)),
        "SPPR609.SPL": spell(effect(128, target=2, **timed)),
        "OHBJOKE1.SPL": spell(effect(128, target=1, **timed)),
        "OHNWILDX.SPL": spell(effect(60, **timed)),
        # C. lifetime corrections and a private Dolorous Decay payload.
        "SPPR409.SPL": ie.make_spl(abilities=[
            {"effects": [effect(101, timing=4, duration=10), effect(142, p2=99, timing=1)]},
            {"effects": [effect(101, timing=4, duration=20), effect(142, p2=99, timing=1)]}]),
        "SPCL920A.SPL": spell(effect(142, p2=63, timing=1), effect(166, timing=4, duration=18)),
        "SPWI620.SPL": spell(effect(165, timing=9, duration=30), effect(142, p2=131, timing=1, duration=2)),
        "SPIN934.SPL": spell(effect(45), effect(142, p2=55)),
        "SPPR610.SPL": spell(effect(146, resource="SPPR610A")),
        "SPPR610A.SPL": spell(effect(25, dispel=3, duration=30), effect(142, p2=101, dispel=1, duration=30)),
        # D. stale rows after cures.  SPIN862 lacks its hold cure and must remain unchanged.
        "OHTYR1.SPL": spell(effect(54)), "SPPR212.SPL": spell(effect(174, target=1, resource="SELFVIS"), effect(25, target=2)),
        "SPIN102.SPL": spell(effect(25)),
        "SPPR900.SPL": spell(effect(25)), "SPIN201.SPL": spell(effect(25)), "SPPR607.SPL": spell(effect(17)),
        "DEVAHEAL.SPL": spell(effect(17)), "SENSPIHE.SPL": spell(effect(17)), "SPIN679.SPL": spell(effect(17)),
        "SPIN711.SPL": spell(effect(17)), "SPWISH28.SPL": spell(effect(17)), "SPWM168.SPL": spell(effect(17)),
        "SPPR308.SPL": spell(effect(162)), "SPIN862.SPL": spell(effect(54)),
        "OHBRESTO.SPL": spell(effect(224)), "SPWISH07.SPL": spell(effect(224)), "SPWISH46.SPL": spell(effect(224)),
    }
    return resources


@test
def record_base_game_entries_lifetimes_cures_and_wording(work, weidu):
    texts = [""] * 20
    texts[10] = "Selune's Blessing"
    texts[11] = "Hit Points Lowered"
    original = record_inputs()
    ids = ie.make_ids([(1900, "CLERIC_NEUTRALIZE_POISON")])
    original.pop("SPWM187.SPL")  # A listed spell may be absent without a record warning.
    game = fg.FakeGame(work / "first", weidu, tlk=ie.make_tlk(texts),
                       biff={"SPELL.IDS": ids, **original})
    out = game.install()
    check(fg.installed_ok(out), out)

    statdesc = icon_rows(game)
    expected_names = {"CBMIWRF": "Wraithform", "CBMIPFG": "Protection From Good", "CBMISHF": "Shadow Form",
                      "CBMIDFS": "Defensive Stance", "CBMIBLR": "Blur", "CBMIDVF": "Divine Favor",
                      "CBMILFR": "Fire Resistance Lowered", "CBMILER": "Electrical Resistance Lowered",
                      "CBMISEL": "Selune's Blessing", "CBMIWAT": "Enhanced Attributes", "CBMIHPL": "Hit Points Lowered"}
    for bam, text in expected_names.items():
        row, ref = statdesc[bam]
        check(game.tlk(ref) == text, f"{bam}: {row}/{game.tlk(ref)!r}")

    # A: all replacements, native pairs, an own payload, and Mimic Web's source duration.
    check(next(e for e in rows(game, "SPWI315") if e["opcode"] == 142)["p2"] == statdesc["CBMIWRF"][0], "Wraithform")
    check(next(e for e in rows(game, "SPWM126") if e["opcode"] == 142)["p2"] == 122, "Minor Globe")
    for res in ("OHBPROG", "OHBPROG1", "OHPRGD10"):
        check(next(e for e in rows(game, res) if e["opcode"] == 142)["p2"] == statdesc["CBMIPFG"][0], res)
    for res, bam in (("SPCL938", "CBMISHF"), ("SPDWD02", "CBMIDFS")):
        check(next(e for e in rows(game, res) if e["opcode"] == 142)["p2"] == statdesc[bam][0], res)
    for res in ("SPWI802", "SPWI618", "SPIN710"):
        check(not any(e["opcode"] == 142 and e["p2"] == 28 for e in rows(game, res)), res)
    check("SPWM187" not in out, "an absent record spell must be silent")
    for res in ("SPWI213D", "SPIN940", "SPWI004"):
        got = rows(game, res)
        check(all(e["special"] == 126 for e in got if e["opcode"] == 39 and e["target"] == 2), res)
        check(not any(e["opcode"] == 142 and e["p2"] == 126 for e in got), res)
    mimic = next(e for e in rows(game, "SPIN566") if e["opcode"] == 142)
    check((mimic["p2"], mimic["duration"]) == (129, 21), mimic)

    # B: anchors carry their complete lifetimes; target-one Confusion is left alone.
    for res in ("SPWI201", "SPDM102", "SPIN943"):
        check(any(e["opcode"] == 142 and e["p2"] == statdesc["CBMIBLR"][0] for e in rows(game, res)), res)
    check(any(e["opcode"] == 174 and e["resource"] == "OTHER" for e in rows(game, "SPDM102")),
          "reordered unrelated Blur effect")
    expected = {"SPPR613": 132, "OHTYR2": statdesc["CBMIDVF"][0], "SPIN682": statdesc["CBMILFR"][0],
                "SPIN532": statdesc["CBMILER"][0], "SPWI955": statdesc["CBMIPAN"][0],
                "SPWI954": statdesc["CBMISEL"][0], "SPWISH08": statdesc["CBMIWAT"][0],
                "SPWISH20": statdesc["CBMIHPL"][0], "SPWISH21": statdesc["CBMIHPL"][0], "OHNWILDX": 83}
    for res, row in expected.items():
        check(any(e["opcode"] == 142 and e["p2"] == row for e in rows(game, res)), res)
    for res in ("SPWISH41", "SPWISH42", "SPWISH43", "SPWISH44", "SPWISH45"):
        check(sum(e["opcode"] == 142 and e["p2"] == 91 for e in rows(game, res)) == 1, res)
    for res in ("SPCL751A", "SPPR609"):
        check(any(e["opcode"] == 142 and e["p2"] == 3 for e in rows(game, res)), res)
    check(not any(e["opcode"] == 142 and e["p2"] == 3 for e in rows(game, "OHBJOKE1")), "non-enemy confusion")

    # C: longest lifespan, selective duration/dispel copying, and native Salt cleanup.
    ward = game.spl("SPPR409")["abilities"]
    check([next(e for e in a["effects"] if e["opcode"] == 142)["duration"] for a in ward] == [10, 20], ward)
    check(next(e for e in rows(game, "SPCL920A") if e["opcode"] == 142)["duration"] == 18, "bard song")
    fire = next(e for e in rows(game, "SPWI620") if e["opcode"] == 142)
    check((fire["timing"], fire["duration"]) == (1, 30), fire)
    check(not any(e["opcode"] == 142 and e["p2"] == 55 for e in rows(game, "SPIN934")), "Salt Crystals")
    check(next(e for e in rows(game, "SPPR610A") if e["opcode"] == 142)["dispel"] == 3, "Dolorous Decay payload")

    # D: each named cure gets every requested removal exactly once; an absent cure anchor does not.
    check({e["p2"] for e in rows(game, "OHTYR1") if e["opcode"] == 240} == {2, 3, 44, 47, 48, 126, 130}, "Exaltation")
    for res in ("SPPR212", "SPIN102", "SPPR900", "SPIN201", "SPPR607", "DEVAHEAL", "SENSPIHE", "SPIN679", "SPIN711", "SPWISH28", "SPWM168"):
        check({e["p2"] for e in rows(game, res) if e["opcode"] == 240} == {6, 101}, res)
    check(all(e["target"] == 2 for e in rows(game, "SPPR212") if e["opcode"] == 240), "reordered poison cure target")
    check(any(e["opcode"] == 240 and e["p2"] == 129 for e in rows(game, "SPPR308")), "Remove Paralysis")
    check(not any(e["opcode"] == 240 and e["p2"] == 129 for e in rows(game, "SPIN862")), "SPIN862 no cure")
    restored = {2, 3, 6, 7, 44, 47, 48, 101, 126}
    for res in ("OHBRESTO", "SPWISH07", "SPWISH46"):
        check({e["p2"] for e in rows(game, res) if e["opcode"] == 240} == restored, res)

    # E: matching by label repoints rows even though their physical positions are arbitrary.
    by_label = statdesc_labels(game)
    check(game.tlk(by_label[55][0]) == "Stunned" and game.tlk(by_label[8][0]) == "Blinded" and
          game.tlk(by_label[112][0]) == "Deafened", by_label)

    # Reinstall against the first output: no icon/cure is appended twice.
    installed = {p.name.upper(): p.read_bytes() for p in (game.root / "override").iterdir()
                 if p.is_file() and p.suffix[1:].upper() in ie.TYPES}
    first_tlk = (game.root / "lang" / game.lang / "dialog.tlk").read_bytes()
    second = fg.FakeGame(work / "second", weidu, tlk=first_tlk,
                         biff={"SPELL.IDS": ids, **original, **installed})
    check(fg.installed_ok(second.install()), "reinstall")
    check((second.root / "lang" / second.lang / "dialog.tlk").read_bytes() == first_tlk, "duplicate Record strings")
    for res in ("SPWI201", "OHTYR1", "SPWISH45", "OHBRESTO"):
        values = rows(second, res)
        check(len(values) == len(rows(game, res)), f"duplicate effects on {res}")
