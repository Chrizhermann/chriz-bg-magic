"""Record entries that follow a state: the rows and the listener."""
import importlib
import re
from pathlib import Path

import fakegame as fg
import ie
from harness import check, test

TP2 = r"""BACKUP ~weidu_external/backup/chriz-bg-magic~
AUTHOR ~test~
ALWAYS
  INCLUDE ~chriz-bg-magic/lib/cbmagic_shared.tpa~
  INCLUDE ~chriz-bg-magic/lib/cbmagic_spells.tpa~
  INCLUDE ~chriz-bg-magic/lib/cbmagic_live.tpa~
END
LANGUAGE ~English~ ~english~ ~chriz-bg-magic/languages/english/setup.tra~
BEGIN ~probe~ DESIGNATED 0
LAF cbmagic_record_live END
"""
ROWS = {"INVISIBLE": ("Invisible", "CBMIINV"), "IMPROVED_INVISIBILITY": ("Improved Invisibility", "CBMIIMP"),
        "SANCTUARY": ("Sanctuary", "CBMISAN"), "MIRROR_IMAGE": ("Mirror Image", "CBMIMIR"),
        "REFLECTED_IMAGE": ("Reflected Image", "CBMIMIR"), "ARCHONS": ("Shield of the Archons", "CBMISOA"),
        "MINOR_DEFLECTION": ("Minor Spell Deflection", "CBMIMSD"), "MINOR_TURNING": ("Minor Spell Turning", "CBMIMST")}


def fx(opcode, **kw):
    return {**ie.FX_DEFAULTS, "opcode": opcode, **kw}


def spell(opcode, duration=90):
    effects = [fx(opcode, target=1, power=3, p1=4, p2=level, timing=0, dispel=1, duration=duration) for level in (1, 2)]
    return ie.make_spl(1, 3, [{"target": 5, "min_level": 1, "effects": effects}])


def game(work, weidu, resources, eeex=True):
    biff = {"STATDESC.2DA": ie.make_2da(["DESCRIPTION", "BAM_FILE"], [("206", ["10554", "SPPR313D"])]), **resources}
    return fg.FakeGame(work, weidu, tp2=TP2, tlk=ie.make_tlk([""]), biff=biff,
                       override={"M___EEex.lua": b"-- synthetic EEex bootstrap\n"} if eeex else {})


def statdesc(g):
    rows = {}
    for line in g.file("override/STATDESC.2DA").decode("latin-1").splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0].isdigit():
            rows[int(parts[0])] = (g.tlk(int(parts[1])), parts[2])
    return rows


@test
def live_rows_and_icons(work, weidu):
    g = game(work, weidu, {"SPPR701.SPL": spell(201, 252)})
    check("SUCCESSFULLY INSTALLED" in g.install(), "the install runs")
    rows = statdesc(g)
    lua = g.file("override/M_CBMREC.lua").decode("latin-1")
    check("%CBM_ROW" not in lua, "every row is stamped")
    for name, (text, bam) in ROWS.items():
        found = [row for row, value in rows.items() if value == (text, bam)]
        check(len(found) == 1, f"{text}: one row, found {found}")
        check(f"row = {found[0]}" in lua, f"{text}: row {found[0]} in the listener")
        check((fg.MOD / f"files/{bam.lower()}.bam").is_file(), f"{bam}: the icon does not ship with the mod")
    check(not (Path(g.root) / "override/SPPR701.SPL").exists(), "no spell changes")
    # A second install changes nothing.
    check("SUCCESSFULLY INSTALLED" in g.install(), "the second install runs")
    check(len(statdesc(g)) == len(rows), "no second set of rows")


@test
def live_without_eeex_changes_nothing(work, weidu):
    g = game(work, weidu, {"SPPR701.SPL": spell(201)}, eeex=False)
    check("SUCCESSFULLY INSTALLED" in g.install(), "the install runs")
    check(not (Path(g.root) / "override/M_CBMREC.lua").exists(), "no listener")
    check(not (Path(g.root) / "override/SPPR701.SPL").exists(), "the spell stays")


@test
def live_lua_runtime_lua53_and_luajit(work, weidu):
    template = (fg.MOD / "lua/M_CBMREC.lua").read_text(encoding="utf-8")
    check(set(re.findall(r"%CBM_ROW_([A-Z_]+)%", template)) == set(ROWS), "the template's rows are the installer's")
    suite = (Path(__file__).parent / "live_runtime.lua").read_text(encoding="utf-8")
    for implementation in ("lupa.lua53", "lupa.luajit21"):
        runtime = importlib.import_module(implementation).LuaRuntime()
        count = runtime.execute(suite)(template)
        check(count >= 30, f"{implementation}: only {count} checks ran")
