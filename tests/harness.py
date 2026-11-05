"""Shared pieces of the offline tests: the test registry, checks and the probe tp2."""
import fakegame as fg

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


# A tp2 that loads the libraries and runs %BODY% as its only component.
PROBE_TP2 = r"""BACKUP ~weidu_external/backup/chriz-bg-magic~
AUTHOR ~test~
ALWAYS
  INCLUDE ~chriz-bg-magic/lib/cbmagic_shared.tpa~
  INCLUDE ~chriz-bg-magic/lib/cbmagic_spells.tpa~
  INCLUDE ~chriz-bg-magic/lib/cbmagic_fixes.tpa~
END
LANGUAGE ~English~ ~english~ ~chriz-bg-magic/languages/english/setup.tra~
BEGIN ~probe~ DESIGNATED 0
%BODY%
"""


def probe(work, weidu, body, **kw):
    """Installs the probe tp2; returns the game, WeiDU's output and its RESULT lines."""
    g = fg.FakeGame(work, weidu, tp2=PROBE_TP2.replace("%BODY%", body), **kw)
    out = g.install()
    return g, out, [ln[len("RESULT "):].strip() for ln in out.splitlines() if ln.startswith("RESULT ")]
