"""The main character as a statue or imprisoned (lua/M_CBMP1.lua): the states, the install with and
without EEex, and the Lua under mocked engines."""
import importlib
import re
from pathlib import Path

import fakegame as fg
import fixtures as fx
import ie
from harness import check, test
from test_resources import check_every_resource, definitions, install

EMPTY_BCS = b"SC\nSC\n"
CAMPAIGN = ie.make_2da(["WORLDSCRIPT", "DESCRIPTION"], [("SOA", ["BALDUR", "-1"]), ("TOB", ["BALDUR25", "-1"]),
                                                        ("BP1", ["BALDUR", "-1"])])
PARTY_RESTED, GLOBAL = 16531, 0x400F
EEEX = {
    "M___EEex.lua": b"-- synthetic EEex bootstrap\n",
    "TRIGGER.IDS": ie.make_ids([(0x410E, "EEex_LuaTrigger(S:Chunk*)"), (PARTY_RESTED, "PartyRested()"),
                                (GLOBAL, "Global(S:Name*,S:Area*,I:Value*)")]),
    "ACTION.IDS": ie.make_ids([(0, "NoAction()"), (366, "GameOver(I:StrRef*)")]),
    "OBJECT.IDS": ie.make_ids([(1, "Myself")]),
}
NULL_OB = b'0 0 0 0 0 0 0 0 0 0 0 0 ""OB\n'
# AR4000: one block, PartyRested() -> NoAction(), as the Solar's call after a rest starts.
SOLAR_BCS = (b"SC\nCR\nCO\nTR\n" + str(PARTY_RESTED).encode() + b' 0 0 0 0 "" "" OB\n' + NULL_OB + b"TR\nCO\n"
             b"RS\nRE\n100AC\n0OB\n" + NULL_OB + b"OB\n" + NULL_OB + b"OB\n" + NULL_OB
             + b'0 0 0 0 0"" "" AC\nRE\nRS\nCR\nSC\n')
PDIALOG = ie.make_2da(["POST_DIALOG_FILE", "JOIN_DIALOG_FILE", "DREAM_SCRIPT_FILE", "25POST_DIALOG_FILE",
                       "25JOIN_DIALOG_FILE", "25DREAM_SCRIPT_FILE", "25OVERRIDE_SCRIPT_FILE"],
                      [("AERIE", ["AERIEP", "AERIEJ", "AERIED", "AERIE25P", "AERIE25J", "AERIE25D", "AERI25"])])
# BG2:EE's own table is only the heading: the game's world scripts then.
CAMPAIGN_BG2EE = ie.make_2da(["WORLDSCRIPT", "DESCRIPTION", "ICON"], [])
PATTERNS = {"EEex_scripts/extra_pattern_dbs/v2.7.3.0.db": b"; EEex's own\n"}


def effects(defn):
    return [e for a in defn["abilities"] for e in a["effects"]]


@test
def player1_definitions(work, weidu):
    defs = definitions()
    statue = effects(defs["cbmp1st.spl"])
    ops = [(e["opcode"], e["p1"], e["p2"]) for e in statue]
    check((185, 0, 2) in ops, "held by opcode 185, which Free Action does not stop")
    check(sorted(e["p2"] for e in statue if e["opcode"] == 7) == list(range(7))
          and all(e["p1"] == 23 for e in statue if e["opcode"] == 7), "stone grey in all seven colour slots")
    check((142, 0, 13) in ops and (139, 14665, 0) in ops, "the Held icon and the game's Petrified message")
    check({e["p2"]["state"] for e in statue if e["opcode"] == 328} == {"CBM_P1_OUT", "CBM_P1_STATUE"}, "states")
    check({(e["opcode"], e["p1"]) for e in statue if e["opcode"] in (86, 87, 88, 89, 30, 28, 29)} ==
          {(86, 50), (88, 50), (89, 50), (87, 25), (30, 50), (28, 50), (29, 75)}, "tough, not glass")
    check({e["p2"] for e in statue if e["opcode"] == 101} == {25, 78, 216, 13}, "stone does not sicken or die")
    lasting = [e for e in statue if e["opcode"] != 139]
    check(all(e["timing"] == 0 and e["duration"] >= 60000000 and e["dispel"] == 2 for e in lasting),
          "lasting, removable, not dispellable")
    prison = effects(defs["cbmp1im.spl"])
    maze = [e for e in prison if e["opcode"] == 213]
    check(len(maze) == 1 and maze[0]["p2"] == 1 and maze[0]["duration"] >= 60000000, "a maze with a fixed duration")
    check({e["p2"]["state"] for e in prison if e["opcode"] == 328} == {"CBM_P1_OUT", "CBM_P1_PRISON"}, "states")
    check(any(e["opcode"] == 142 and e["p2"] == 79 for e in prison), "the Imprisonment icon")
    net = effects(defs["cbmp1nt.spl"])
    check([(e["opcode"], e["resource"], e["timing"]) for e in net if e["opcode"] == 403] == [(403, "CBMP1SCR", 9)],
          "the screen, kept through death")
    check([e["p2"] for e in net if e["opcode"] == 328] == [{"state": "CBM_P1_NET"}], "its state")
    check([(e["opcode"], e["resource"]) for e in effects(defs["cbmp1cu.spl"])] == [(321, "CBMP1ST")], "the cure")
    check([(e["opcode"], e["resource"]) for e in effects(defs["cbmp1fr.spl"])] == [(321, "CBMP1IM")], "the release")


@test
def player1_without_and_with_eeex(work, weidu):
    """Without EEex nothing of this is installed; with EEex the module knows its states, the pattern
    file sits beside EEex's own, and every campaign world script starts with the tick."""
    biff = fx.game(BALDUR_BCS=EMPTY_BCS, BALDUR25_BCS=EMPTY_BCS, CAMPAIGN_2DA=CAMPAIGN, PLAYER1D_BCS=EMPTY_BCS,
                   AERIED_BCS=EMPTY_BCS, AERIE25D_BCS=EMPTY_BCS, AR4000_BCS=SOLAR_BCS, PDIALOG_2DA=PDIALOG)
    g = fg.FakeGame(work / "plain", weidu, tlk=fx.tlk(), biff=biff, files=PATTERNS)
    out = install(g)
    check("the main character's petrification and imprisonment stay as in the base game" in out, out[-600:])
    check(g.file("override/M_CBMP1.lua") is None and g.file("EEex_scripts/extra_pattern_dbs/CBMP1.db") is None,
          "the module without EEex")
    check(all(g.file(f"override/{name}.BCS") is None for name in ("BALDUR", "PLAYER1D", "AERIED", "AR4000")),
          "a script changed without EEex")
    check_every_resource(g)

    g = fg.FakeGame(work / "eeex", weidu, tlk=fx.tlk(), biff=biff, override=EEEX, files=PATTERNS)
    install(g)
    check_every_resource(g)
    lua = g.file("override/M_CBMP1.lua").decode("utf-8")
    found = re.search(r"P\.NET, P\.OUT, P\.STATUE, P\.PRISON = (\d+), (\d+), (\d+), (\d+)", lua)
    check(found and "%CBM_" not in lua, "the states were not filled in")
    ids = g.file("override/splstate.ids").decode("latin-1")
    for value, symbol in zip(found.groups(), ("CBM_P1_NET", "CBM_P1_OUT", "CBM_P1_STATUE", "CBM_P1_PRISON")):
        check(re.search(rf"^{value}\s+{symbol}\s*$", ids, re.M) and int(value) <= 255, f"{symbol} = {value}")
    check(g.file("EEex_scripts/extra_pattern_dbs/CBMP1.db") == (fg.MOD / "eeex/CBMP1.db").read_bytes(), "patterns")
    for world in ("BALDUR", "BALDUR25"):
        script = g.file(f"override/{world}.BCS")
        check(script is not None and script.count(b"CBMP1_Tick") == 1, f"{world}: the tick")
    check(g.file("override/BDBALDUR.BCS") is None, "a world script the game does not have")
    # Scripts read the global the tick keeps: a prisoner's spell states are not kept up.
    guard = str(GLOBAL).encode() + b' 1 0 0 0 "GLOBALCBM_P1_OUT"'
    for dream in ("PLAYER1D", "AERIED", "AERIE25D"):
        script = g.file(f"override/{dream}.BCS")
        check(script is not None and script.count(guard) == 1, f"{dream}: no dream while he is out")
    solar = g.file("override/AR4000.BCS")
    check(solar is not None and solar.count(str(GLOBAL).encode() + b' 1 1 0 0 "GLOBALCBM_P1_OUT"') == 1
          and solar.count(str(PARTY_RESTED).encode() + b" 0 0 ") == 1, "the Solar waits too")
    installed = g.tree()
    install(g)
    check(g.tree() == installed, "a second install changed the game")

    biff = fx.game(BALDUR_BCS=EMPTY_BCS, BALDUR25_BCS=EMPTY_BCS, CAMPAIGN_2DA=CAMPAIGN_BG2EE)
    g = fg.FakeGame(work / "bg2ee", weidu, tlk=fx.tlk(), biff=biff, override=EEEX, files=PATTERNS)
    install(g)
    for world in ("BALDUR", "BALDUR25"):
        script = g.file(f"override/{world}.BCS")
        check(script is not None and script.count(b"CBMP1_Tick") == 1, f"BG2:EE {world}: the tick")


@test
def player1_lua_runtime_lua53_and_luajit(work, weidu):
    template = (fg.MOD / "lua/M_CBMP1.lua").read_text(encoding="utf-8")
    suite = (Path(__file__).parent / "player1_runtime.lua").read_text(encoding="utf-8")
    for implementation in ("lupa.lua53", "lupa.luajit21"):
        runtime = importlib.import_module(implementation).LuaRuntime()
        count = runtime.execute(suite)(template)
        check(count >= 60, f"{implementation}: only {count} runtime checks ran")
