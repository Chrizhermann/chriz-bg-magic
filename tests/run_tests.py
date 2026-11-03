"""Offline tests for the installer: real WeiDU runs in small made-up game folders. No game
installation or game files are needed; every test builds its own data.

usage: python tests/run_tests.py --weidu <path to weidu.exe> [--keep DIR] [-k NAME]
Exit code 0 when every test passes.
"""
import argparse
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fakegame as fg  # noqa: E402
import ie  # noqa: E402

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


SPELL_IDS = ie.make_ids([(1102, "CLERIC_COMMAND"), (2414, "WIZARD_SPIRIT_ARMOR"), (2001, "TRAP_FIREBALL"),
                         (2304, "WIZARD_FIREBALL")])
PROBE_TP2 = r"""BACKUP ~weidu_external/backup/chriz-bg-magic~
AUTHOR ~test~
ALWAYS
  INCLUDE ~chriz-bg-magic/lib/cbmagic_shared.tpa~
END
LANGUAGE ~English~ ~english~ ~chriz-bg-magic/languages/english/setup.tra~
BEGIN ~probe~ DESIGNATED 0
%BODY%
"""


def probe(work, weidu, body, **kw):
    g = fg.FakeGame(work, weidu, tp2=PROBE_TP2.replace("%BODY%", body), **kw)
    out = g.install()
    return g, out, [ln[len("RESULT "):].strip() for ln in out.splitlines() if ln.startswith("RESULT ")]


# --- the frame ---------------------------------------------------------------------------

@test
def installs_and_uninstalls_on_bg2ee_and_eet(work, weidu):
    """The main component installs on BG2:EE and EET and its uninstall leaves the game as it was."""
    for game in ("bg2ee", "eet"):
        g = fg.FakeGame(work / game[:2], weidu, game=game, biff={"SPELL.IDS": SPELL_IDS})
        before = g.tree()
        out = g.install()
        check(fg.installed_ok(out), f"{game}: install failed:\n{out}")
        out = g.uninstall()
        check("SUCCESSFULLY REMOVED" in out or "Uninstalled" in out or "REMOVED" in out, f"{game}: uninstall:\n{out}")
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
    g = fg.FakeGame(work / "refuse", weidu, override={"DVIMHERE.MRK": b"x"})
    out = g.install()
    check(fg.failed(out) and "Spell Revisions is installed" in out, f"refuse:\n{out}")
    lib = (fg.MOD / "lib/cbmagic_shared.tpa").read_text(encoding="utf-8")
    for policy, expect in (("warn", fg.with_warnings), ("coexist", lambda o: "SUCCESSFULLY INSTALLED" in o)):
        g = fg.FakeGame(work / policy, weidu, override={"DVIMHERE.MRK": b"x"})
        (g.root / "chriz-bg-magic/lib/cbmagic_shared.tpa").write_text(
            lib.replace("OUTER_SPRINT cbmagic_sr_policy ~refuse~", f"OUTER_SPRINT cbmagic_sr_policy ~{policy}~"),
            encoding="utf-8")
        out = g.install()
        check(expect(out), f"{policy}:\n{out}")
    g = fg.FakeGame(work / "none", weidu)
    check("SUCCESSFULLY INSTALLED" in g.install(), "no SR: should install without warnings")


@test
def spell_resref_from_symbol(work, weidu):
    body = r"""
ACTION_FOR_EACH s IN WIZARD_SPIRIT_ARMOR CLERIC_COMMAND TRAP_FIREBALL WIZARD_FIREBALL NO_SUCH_SPELL BEGIN
  LAF cbmagic_spell_resref STR_VAR symbol = EVAL ~%s%~ RET r = resref f = found END
  PRINT ~RESULT %s% %r% %f%~
END
"""
    spl = ie.make_spl(level=1, abilities=[{"effects": []}])
    _, out, res = probe(work, weidu, body, biff={"SPELL.IDS": SPELL_IDS, "SPWI414.SPL": spl, "SPPR102.SPL": spl,
                                                  "SPWI001.SPL": spl})
    check(res == ["WIZARD_SPIRIT_ARMOR SPWI414 1", "CLERIC_COMMAND SPPR102 1", "TRAP_FIREBALL SPWI001 1",
                  "WIZARD_FIREBALL SPWI304 0", "NO_SUCH_SPELL  0"], f"got {res}\n{out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weidu", required=True, type=Path)
    ap.add_argument("--keep", type=Path, help="keep the test games in this folder")
    ap.add_argument("-k", help="run only tests whose name contains this")
    args = ap.parse_args()
    base = args.keep or Path(tempfile.mkdtemp(prefix="cbm-"))
    failed = 0
    for number, fn in enumerate(TESTS, 1):
        if args.k and args.k not in fn.__name__:
            continue
        # Short folder names: WeiDU fails on paths near the Windows 260-character limit.
        work = base / f"t{number:02d}"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        try:
            fn(work, args.weidu.resolve())
            print(f"ok    t{number:02d} {fn.__name__}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL  t{number:02d} {fn.__name__}\n{traceback.format_exc()}")
    if not args.keep:
        shutil.rmtree(base, ignore_errors=True)
    print(f"{len(TESTS) if not args.k else 'selected'} tests, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
