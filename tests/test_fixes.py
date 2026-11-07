"""Tests of the five fixes on made-up spells shaped like the base game's, and on the
variations the compatibility policy asks for: other layouts, already-changed input, a
second install, missing and broken files, an unclear spell, other text languages."""
import fakegame as fg
import fixtures as fx
import ie
from harness import PROBE_TP2, check, test

SAVE_RULE = ["SPWI304", "SPWI712", "SPWI523D", "SPWI503", "SPPR503", "SPWI313", "SPPR304", "SPWI810", "SPWI308"]


def ops(effects):
    return [e["opcode"] for e in effects]


def without(effects, *opcodes):
    return [e for e in effects if e["opcode"] not in opcodes]


def fresh(work, weidu, replace=None, splprot=fx.SPLPROT_ROWS, **kw):
    return fg.FakeGame(work, weidu, tlk=kw.pop("tlk", fx.tlk()), biff=fx.game(splprot=splprot, **(replace or {})),
                       **kw)


@test
def five_fixes_on_vanilla_shaped_spells(work, weidu):
    """Every fix does what was decided, keeps everything else of the spell, updates the
    texts that named the old behaviour, and the uninstall puts the game back."""
    g = fresh(work, weidu)
    before = g.tree()
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, f"install:\n{out}")
    orig = {k[:-4]: ie.parse_spl(v) for k, v in fx.game().items() if k.endswith(".SPL")}

    # Spirit Armor: refresh first; the final bonus pass tags saves and adds its state/text.
    s = g.spl("SPWI414")
    first = s["abilities"][0]["effects"][0]
    check((first["opcode"], first["resource"], first["target"], first["power"], first["timing"], first["dispel"])
          == (321, "SPWI414", 2, 4, 1, 3), f"Spirit Armor refresh: {first}")
    check(without(s["abilities"][0]["effects"][1:], 328) ==
          [{**e, "resource": "CBTDEFLE"} if e["opcode"] == 37 else e
           for e in orig["SPWI414"]["abilities"][0]["effects"]], "Spirit Armor unrelated fields changed")
    check("save vs. spell +3 (Deflection)" in g.tlk(s["desc"]), "Spirit Armor type text")
    check(g.itm_descs("SCRL5K")[1] == s["desc"], "Spirit Armor scroll type text")
    check(g.tlk(fx.SPIRIT_DESC) == fx.TEXTS[fx.SPIRIT_DESC], "shared Spirit Armor string retained")

    # Minor Spell Deflection: levels 1-4 only, the rest kept, the text says so.
    s = g.spl("SPWI318")
    for a, o in zip(s["abilities"], orig["SPWI318"]["abilities"]):
        levels = sorted(e["p2"] for e in a["effects"] if e["opcode"] == 201)
        check(levels == [1, 2, 3, 4], f"MSD levels {levels}")
        check([e for e in a["effects"] if e["opcode"] == 201 and e["resource"]] ==
              [e for e in o["effects"] if e["opcode"] == 201 and e["p2"] == 1], "MSD end-of-spell resource")
        check(without(a["effects"], 201) == without(o["effects"], 201), "MSD other effects changed")
    text = g.tlk(s["desc"])
    check(s["desc"] != fx.MSD_DESC and "up to 4th-level spells" in text and "7th" not in text, f"MSD text: {text}")
    check(g.itm_descs("SCRL6G")[1] == s["desc"], "MSD scroll text not repointed")
    check(g.tlk(fx.MSD_DESC) == fx.TEXTS[fx.MSD_DESC], "the old, shared string must stay")

    # Save vs. breath: only the save type bit changes.
    for res in SAVE_RULE:
        s, o = g.spl(res), orig[res]
        for a, b in zip(s["abilities"], o["abilities"]):
            for e, f in zip(a["effects"], b["effects"]):
                if f["opcode"] == 12:
                    check(e["save"] == (f["save"] & ~1) | 2, f"{res}: save {e['save']:#x} from {f['save']:#x}")
                    exp_spec = (f["special"] | 0x100) if res == "SPPR304" else f["special"]
                    exp_dice = min(f["dice"], 12) if res == "SPWI313" else f["dice"]
                    check({**e, "save": 0} == {**f, "save": 0, "special": exp_spec, "dice": exp_dice}, f"{res}: damage effect changed beyond its save")
                else:
                    check(e == f, f"{res}: other effect changed")
    for untouched in ("SPWI523", "SPWI900", "SPWI615", "SPWI911", "SPPR705", "SPWI220"):
        check(g.file(f"override/{untouched}.SPL") is None, f"{untouched} must stay untouched")
    check("vs. Breath for half" in g.tlk(g.spl("SPWI712")["desc"]), "DBF text")
    check(g.itm_descs("SCRL8N")[1] == g.spl("SPWI712")["desc"], "DBF scroll text")
    check("Saving Throw vs. Breath enables" in g.tlk(g.spl("SPPR304")["desc"]), "Glyph text")
    check("Save vs. Breath for half" in g.tlk(g.spl("SPWI810")["desc"]), "Incendiary Cloud text")
    check(g.spl("SPWI304")["desc"] == fx.FIREBALL_DESC and g.file("override/SCRL1G.ITM") is None,
          "Fireball's text names no save type and must stay")
    check("[SPWI900]" in out and "not its own" in out, "Sunfire's foreign cast not reported")

    # Damage wakes sleepers.
    for res in ("SPWI116", "SPWI105", "SPWI213", "SPPR102", "SPPR512", "SPWI411"):
        s, o = g.spl(res), orig[res]
        for a, b in zip(s["abilities"], o["abilities"]):
            check([e["p2"] for e in a["effects"] if e["opcode"] == 39] == [0] * ops(b["effects"]).count(39),
                  f"{res}: sleep still does not wake")
            expected_other = without(b["effects"], 39)
            if res == "SPWI213":
                expected_other = [e for e in expected_other if not (e["opcode"] == 142 and e["p2"] == 126)]
            check(without(a["effects"], 39) == expected_other, f"{res}: other effects changed")
            expected_sleep = [{**e, "p2": 0,
                               "special": 126 if res == "SPWI213" else (44 if res == "SPWI411" else e["special"])}
                              for e in b["effects"] if e["opcode"] == 39]
            check([{**e, "p2": 0} for e in a["effects"] if e["opcode"] == 39] == expected_sleep,
                  f"{res}: sleep changed beyond its owned fields")
    check("WIZARD_POWER_WORD_SLEEP (SPWI220): its 1 sleep effects end on damage already" in out, "PWS")

    # Web: immunities first, the web's roll vs. breath (the -2 stays), the own save kept.
    s, o = g.spl("SPWI215"), orig["SPWI215"]
    effects = s["abilities"][0]["effects"]
    imm = effects[:len(fx.WEB_RACES)]
    check(sorted((e["opcode"], e["p1"], e["p2"], e["resource"], e["target"], e["power"], e["timing"], e["dispel"])
                 for e in imm) == [(324, race, 4, "SPWI215", 2, 2, 0, 2) for race, _ in fx.WEB_RACES],
          f"Web immunities: {imm}")
    for e, f in zip(effects[len(fx.WEB_RACES):], o["abilities"][0]["effects"]):
        if f["opcode"] == 12:
            check(e == f, "Web: the effect with its own save must keep it")
        else:
            check(e["save"] == 2 and e["bonus"] == -2 and {**e, "save": 0} == {**f, "save": 0}, f"Web: {e}")
    check(g.tlk(s["desc"]) == fx.TEXTS[fx.WEB_DESC].replace("vs. Spell", "vs. Breath"), f"Web text: {g.tlk(s['desc'])}")
    check(g.itm_descs("SCRL99")[1] == s["desc"], "Web scroll text")
    check(g.file("override/SWORD.ITM") is None, "a non-scroll item must stay")
    check(g.file("override/SPLPROT.2DA") is None, "SPLPROT already had the row")

    out = g.uninstall()
    check(g.tree() == before, f"uninstall left changes:\n{out}")


@test
def second_install_changes_nothing(work, weidu):
    """On spells the fixes already changed (the first install's results as the game's own
    files), a second install finds everything correct and writes nothing."""
    g = fresh(work / "a", weidu)
    check("SUCCESSFULLY INSTALLED" in g.install(), "first install")
    done = {p.name.upper(): p.read_bytes() for p in (g.root / "override").iterdir()
            if p.is_file() and p.suffix.upper() in (".SPL", ".ITM")}
    tlk = (g.root / "lang" / g.lang / "dialog.tlk").read_bytes()
    h = fg.FakeGame(work / "b", weidu, tlk=tlk, biff={**fx.game(), **done})
    out = h.install()
    check(fg.installed_ok(out), f"second install:\n{out}")
    written = sorted(p.name.upper() for p in (h.root / "override").iterdir() if p.suffix.upper() in (".SPL", ".ITM"))
    check(written == [], f"second install rewrote {written}")
    for needle in ("Spirit Armor (SPWI414): a new casting replaces the old one in 0 abilities; 1 did so already",
                   "Minor Spell Deflection (SPWI318): stops spell levels 1-4 only; 0 higher-level",
                   "WIZARD_FIREBALL (SPWI304) saves vs. breath already",
                   "WIZARD_SLEEP (SPWI116): its 3 sleep effects end on damage already",
                   "race SPIDER (116) immune in 0 abilities; 1 were already"):
        check(needle in out, f"missing: {needle}\n{out}")


@test
def other_layouts_and_mod_variations(work, weidu):
    """Casting effects stored behind the abilities, extra and reordered effects, a
    self-cast Spirit Armor copy, MSD levels in reverse with the end-of-spell resource on a
    removed level, a Web that already has one of the immunities, and a sleep that sits in
    a spell of its own (EE Fixpack's Emotion: Hopelessness)."""
    sa = ie.make_spl(1, 4, [{"target": 5, "effects": [fx.fx(opcode=174, target=1, resource="EFF_E02"),
                                                    fx.fx(opcode=37, target=1, power=4, p1=3, duration=600)]},
                           {"target": 1, "effects": [fx.fx(opcode=321, power=4, timing=1, resource="spwi414"),
                                                    fx.fx(opcode=37, power=4, p1=3, duration=600)]}],
                     casting=[fx.fx(opcode=139, target=1, p1=5, timing=1)], extra_fx_first=True, desc=fx.SPIRIT_DESC)
    msd = fx.minor_spell_deflection(levels=range(7, 0, -1), resource_on=7)
    fireball = ie.make_spl(1, 3, fx.by_level([1, 10], lambda lvl: [fx.fx(opcode=215, timing=1, resource="X"),
                                                                    fx.damage(fx.FIRE, lvl)]),
                           casting=[fx.fx(opcode=265, target=1, timing=1, resource="mgArea1")], extra_fx_first=True,
                           desc=fx.FIREBALL_DESC)
    hopeless = ie.make_spl(1, 4, fx.by_level([1, 8], lambda lvl: [
        fx.fx(opcode=142, power=4, p2=37, duration=54),
        fx.fx(opcode=146, power=4, p2=2, timing=1, save=ie.SAVE_SPELL, resource="SPWI411B")]))
    hopeless_sleep = ie.make_spl(1, 4, fx.by_level([1, 8], lambda lvl: [
        fx.fx(opcode=142, target=2, power=4, p2=44, duration=54),
        fx.fx(opcode=39, power=4, p2=1, duration=54),
        fx.fx(opcode=142, target=1, power=4, p2=44, duration=54),
        fx.fx(opcode=174, power=4, timing=4, duration=54)]))
    pre = fresh(work / "pre", weidu, tp2=PROBE_TP2.replace("%BODY%", r"""
COPY_EXISTING ~spwi215.spl~ ~override~
  LPF cbmagic_add_immunity INT_VAR row = 4 value = 119 RET added present END
"""))
    check(fg.installed_ok(pre.install()), "pre-patch")
    web_pre = pre.file("override/SPWI215.SPL")
    g = fresh(work / "main", weidu, replace={"SPWI414_SPL": sa, "SPWI318_SPL": msd, "SPWI304_SPL": fireball,
                                             "SPWI215_SPL": web_pre, "SPWI411_SPL": hopeless,
                                             "SPWI411B_SPL": hopeless_sleep})
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, f"install:\n{out}")
    s = g.spl("SPWI414")
    check(ops(s["abilities"][0]["effects"]) == [321, 174, 37, 328] and s["abilities"][0]["effects"][0]["target"] == 1,
          f"self-cast ability: {s['abilities'][0]['effects']}")
    check(ops(s["abilities"][1]["effects"]) == [321, 37, 328], "existing refresh and typed save retained")
    check(ops(s["casting"]) == [139], "casting effects changed")
    s = g.spl("SPWI318")
    for a in s["abilities"]:
        d = [e for e in a["effects"] if e["opcode"] == 201]
        check([e["p2"] for e in d] == [4, 3, 2, 1], f"MSD reverse: {[e['p2'] for e in d]}")
        check([e["resource"] for e in d] == ["SPWI318B", "", "", ""], f"MSD resource moved: {[e['resource'] for e in d]}")
    s = g.spl("SPWI304")
    check(ops(s["casting"]) == [265] and all(ops(a["effects"]) == [215, 12] for a in s["abilities"]), "fireball layout")
    check(all(a["effects"][1]["save"] & 3 == 2 for a in s["abilities"]), "fireball save")
    imm = [e for e in g.spl("SPWI215")["abilities"][0]["effects"] if e["opcode"] == 324]
    check(sorted(e["p1"] for e in imm) == [race for race, _ in fx.WEB_RACES], f"Web immunities: {imm}")
    check("WIZARD_EMOTION_HOPELESSNESS (SPWI411): 2 sleep effects now end on damage" in out, f"Hopelessness:\n{out}")
    check(g.file("override/SPWI411.SPL") is None, "the spell that only casts the sleep must stay")
    check([e["p2"] for a in g.spl("SPWI411B")["abilities"] for e in a["effects"] if e["opcode"] == 39] == [0, 0],
          "the sleep in its own spell still does not wake")
    emotion_fx = [e for a in g.spl("SPWI411B")["abilities"] for e in a["effects"]]
    check(all(e["special"] == 44 for e in emotion_fx if e["opcode"] == 39),
          f"Hopelessness sleep row: {emotion_fx}")
    check(not any(e["opcode"] == 142 and e["target"] == 2 and e["p2"] == 44 for e in emotion_fx),
          f"Hopelessness target icon survived: {emotion_fx}")
    check(sum(e["opcode"] == 142 and e["target"] == 1 and e["p2"] == 44 for e in emotion_fx) == 2,
          f"Hopelessness caster icon was changed: {emotion_fx}")


@test
def honest_outcomes_for_missing_odd_and_unclear_input(work, weidu):
    """A missing spell, a broken file, an MSD that deflects only high levels and a sleep
    effect that cannot wake: each is named in the log, the rest installs."""
    ids = ie.make_ids([p for p in fx.SPELL_SYMBOLS if p[1] != "WIZARD_WEB"])
    color = ie.make_spl(1, 1, [{"target": 4, "effects": [fx.fx(opcode=39, power=1, p2=1, timing=1, special=14)]}])
    g = fresh(work, weidu, replace={"SPELL_IDS": ids, "SPWI414_SPL": b"SPL V1  " + bytes(30),
                                    "SPWI318_SPL": fx.minor_spell_deflection(levels=range(5, 8), resource_on=5),
                                    "SPWI105_SPL": color})
    out = g.install()
    check(fg.with_warnings(out), f"expected warnings:\n{out}")
    for needle in ("Web (WIZARD_WEB) is not in this game; left out",
                   "Spirit Armor (SPWI414) left as it is: shorter than an SPL header",
                   "Minor Spell Deflection (SPWI318) left as it is: ability 2 deflects only spell levels above 4",
                   "WIZARD_COLOR_SPRAY (SPWI105) has 1 sleep effects with a permanent timing that never wake"):
        check(needle in out, f"missing: {needle}\n{out}")
    for res in ("SPWI414", "SPWI318", "SPWI105", "SPWI215"):
        check(g.file(f"override/{res}.SPL") is None, f"{res} must stay untouched")
    check(g.file("override/SPWI304.SPL") is not None and g.file("override/SPWI116.SPL") is not None,
          "the other fixes must still install")


@test
def a_race_the_game_lacks_is_named(work, weidu):
    """A RACE.IDS without one of the races: that immunity is named and left out, the others
    install."""
    ids = ie.make_ids([p for p in fx.RACES if p[1] != "MEPHIT"])
    g = fresh(work, weidu, replace={"RACE_IDS": ids})
    out = g.install()
    check(fg.with_warnings(out) and "RACE.IDS has no MEPHIT; that immunity is left out" in out, f"warning:\n{out}")
    imm = [e for e in g.spl("SPWI215")["abilities"][0]["effects"] if e["opcode"] == 324]
    check(sorted(e["p1"] for e in imm) == [race for race, name in fx.WEB_RACES if name != "MEPHIT"],
          f"Web immunities: {imm}")


@test
def splprot_row_is_appended_when_missing(work, weidu):
    rows = [r for r in fx.SPLPROT_ROWS if r[0] != "4_RACE=n"]
    g = fresh(work, weidu, splprot=rows)
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, f"install:\n{out}")
    table = g.file("override/SPLPROT.2DA").decode("ascii").split()
    check(table[-4:] == ["5_CBMAGIC", "268", "-1", "1"], f"appended row: {table[-4:]}")
    imm = [e for e in g.spl("SPWI215")["abilities"][0]["effects"] if e["opcode"] == 324]
    check({e["p2"] for e in imm} == {5}, f"Web immunity row: {imm}")


@test
def other_text_languages_are_named(work, weidu):
    g = fresh(work, weidu, lang="de_DE")
    out = g.install()
    check(fg.with_warnings(out) and "descriptions are updated only in English; in this game (de_de)" in out,
          f"language warning:\n{out}")
    check(g.spl("SPWI215")["abilities"][0]["effects"][0]["opcode"] == 324, "mechanics must still install")


@test
def late_self_removal_is_named(work, weidu):
    """A Spirit Armor whose self-removal comes after its effects cancels itself already;
    the early fix names it and the final bonus pass moves the removal ahead of the bonus."""
    late = ie.make_spl(1, 4, [{"target": 1, "effects": [fx.fx(opcode=37, power=4, p1=3, duration=600),
                                                     fx.fx(opcode=321, power=4, timing=1, resource="SPWI414")]}])
    g = fresh(work, weidu, replace={"SPWI414_SPL": late})
    out = g.install()
    check(fg.with_warnings(out) and "1 abilities remove the spell's own effects after applying them" in out,
          f"missing warning:\n{out}")
    effects = g.spl("SPWI414")["abilities"][0]["effects"]
    check(ops(effects) == [321, 37, 328], "late refresh must move before the typed save")
    check(effects[1]["p1"] == 3 and effects[1]["duration"] == 600, "save bonus preserved")
