"""Tests of the installer frame: games, the Spell Revisions policy, spell lookup."""
import fakegame as fg
import fixtures as fx
import ie
from harness import check, probe, test


@test
def installs_and_uninstalls_on_bg2ee_and_eet(work, weidu):
    """The main component installs on BG2:EE and EET and its uninstall leaves the game as it was."""
    for game in ("bg2ee", "eet"):
        g = fg.FakeGame(work / game[:2], weidu, game=game, tlk=fx.tlk(), biff=fx.game())
        before = g.tree()
        out = g.install()
        check("SUCCESSFULLY INSTALLED" in out, f"{game}: install failed:\n{out}")
        out = g.uninstall()
        check("SUCCESSFULLY REMOVED" in out or "REMOVED" in out, f"{game}: uninstall:\n{out}")
        check(g.tree() == before, f"{game}: uninstall left changes")


@test
def refuses_bgee(work, weidu):
    g = fg.FakeGame(work, weidu, game="bgee")
    out = g.install()
    check(not fg.installed_ok(out), f"installed on BG:EE:\n{out}")
    check("Enhanced Edition Trilogy" in out, "no reason given")


@test
def spell_revisions_policy(work, weidu):
    """With Spell Revisions' marker present the installer follows cbmagic_sr_policy:
    refuse (the default until Christopher decides), warn and coexist."""
    g = fg.FakeGame(work / "refuse", weidu, tlk=fx.tlk(), biff=fx.game(), override={"DVIMHERE.MRK": b"x"})
    out = g.install()
    check(fg.failed(out) and "Spell Revisions is installed" in out, f"refuse:\n{out}")
    lib = (fg.MOD / "lib/cbmagic_shared.tpa").read_text(encoding="utf-8")
    for policy, expect in (("warn", fg.with_warnings), ("coexist", lambda o: "SUCCESSFULLY INSTALLED" in o)):
        g = fg.FakeGame(work / policy, weidu, tlk=fx.tlk(), biff=fx.game(), override={"DVIMHERE.MRK": b"x"})
        (g.root / "chriz-bg-magic/lib/cbmagic_shared.tpa").write_text(
            lib.replace("OUTER_SPRINT cbmagic_sr_policy ~refuse~", f"OUTER_SPRINT cbmagic_sr_policy ~{policy}~"),
            encoding="utf-8")
        out = g.install()
        check(expect(out), f"{policy}:\n{out}")
    g = fg.FakeGame(work / "none", weidu, tlk=fx.tlk(), biff=fx.game())
    check("SUCCESSFULLY INSTALLED" in g.install(), "no SR: should install without warnings")


@test
def spell_resref_from_symbol(work, weidu):
    body = r"""
ACTION_FOR_EACH s IN WIZARD_SPIRIT_ARMOR CLERIC_COMMAND TRAP_FIREBALL WIZARD_FIREBALL NO_SUCH_SPELL BEGIN
  LAF cbmagic_spell_resref STR_VAR symbol = EVAL ~%s%~ RET r = resref f = found END
  PRINT ~RESULT %s% %r% %f%~
END
"""
    ids = ie.make_ids([(1102, "CLERIC_COMMAND"), (2414, "WIZARD_SPIRIT_ARMOR"), (2001, "TRAP_FIREBALL"),
                       (2304, "WIZARD_FIREBALL")])
    spl = ie.make_spl(level=1, abilities=[{"effects": []}])
    _, out, res = probe(work, weidu, body, biff={"SPELL.IDS": ids, "SPWI414.SPL": spl, "SPPR102.SPL": spl,
                                                  "SPWI001.SPL": spl})
    check(res == ["WIZARD_SPIRIT_ARMOR SPWI414 1", "CLERIC_COMMAND SPPR102 1", "TRAP_FIREBALL SPWI001 1",
                  "WIZARD_FIREBALL SPWI304 0", "NO_SUCH_SPELL  0"], f"got {res}\n{out}")
