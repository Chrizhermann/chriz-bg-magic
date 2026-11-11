"""In-game checks of M_CBMP1.lua (main character as statue or imprisoned) and cold save reloads.

usage: python -I tests/lab/run_player1.py --game <lab game> --profile <lab profile>
           --lab-tools <folder with bg_lab_slots.py> --load-lua <lab_load.lua> --save <save folder>
           --out <evidence folder> [--seconds 900] [--owner <text>]

Covers the four runtime scenarios not exercised by run_batches.py:
  1. Map-edge / world-map gather check (CBMP1-LeaveArea-DeadTest on LeaveArea, action 91) and
     world-map travel while Player1 is a statue and while imprisoned, plus negative counter-test.
  2. Dreams on rest (PLAYER1D.BCS / RestParty): suppressed while CBM_P1_OUT == 1 without consuming
     the dream variable, then firing once cured.
  3. SaveGame(0) and cold reload from disk in fresh processes while Player1 is a statue, while
     imprisoned, and with overlapping typed spell bonuses across reload, area change, 60s, and rest.
  4. Real melee combat during the 30-second dead-end clock (CBMP1_Stuck): CBM_P1_CLOCK pauses while
     ActuallyInCombat() holds and resumes afterward to game over (>= 450 ticks).

Auto-Save (000000000-Auto-Save) is backed up into memory before the run and restored byte-for-byte
in finally:, creating and deleting zero folders inside the profile directory.
"""
import argparse
import importlib.util
import json
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec_rp = importlib.util.spec_from_file_location("run_probe", HERE / "run_probe.py")
rp = importlib.util.module_from_spec(spec_rp)
spec_rp.loader.exec_module(rp)

spec_rb = importlib.util.spec_from_file_location("run_batches", HERE / "run_batches.py")
rb = importlib.util.module_from_spec(spec_rb)
spec_rb.loader.exec_module(rb)

EXTRA = HERE / "probe_batches.lua"
AUTOSAVE_FOLDER = "000000000-Auto-Save"

POLL_SETUP_LUA = """
if not CBMP1_REMOTE_POLL then
    CBMP1_REMOTE_POLL = true
    if EEex_Opcode_AddListsResolvedListener then
        EEex_Opcode_AddListsResolvedListener(function()
            pcall(EEexRemote.Poll)
        end)
    end
    local mt = worldMapScreen and getmetatable(worldMapScreen)
    if mt and type(mt.IsTravelButtonVisible) == "function" and not CBMP1_WMAP_ORIG then
        CBMP1_WMAP_ORIG = mt.IsTravelButtonVisible
        mt.IsTravelButtonVisible = function(self, ...)
            pcall(EEexRemote.Poll)
            return CBMP1_WMAP_ORIG(self, ...)
        end
    end
end
return true
"""

P1_HELPERS_LUA = """
function CBMP.p1_status()
    local p1 = CBMPlayer1.protagonist()
    if not p1 then return nil end
    local scan = CBMPlayer1.scan(p1)
    local cell_val = CBMPlayer1.hook and CBMPlayer1.hook.cell and EEex_ReadPtr(CBMPlayer1.hook.cell) or 0
    local areas = {}
    for i = 0, 2 do
        local s = EEex_Sprite_GetInPortrait(i)
        areas[i + 1] = s and s.m_pArea and s.m_pArea.m_resref:get():upper() or ""
    end
    return {
        p1_ptr = EEex_UDToPtr(p1),
        cell = cell_val,
        hook = CBMPlayer1.hook and CBMPlayer1.hook.status or "",
        scan = scan,
        out = EEex_GameState_GetGlobalInt("CBM_P1_OUT"),
        stuck = EEex_GameState_GetGlobalInt("CBM_P1_STUCK"),
        clock = EEex_GameState_GetGlobalInt("CBM_P1_CLOCK"),
        tick = EngineGlobals.g_pBaldurChitin.m_pObjectGame.m_worldTime.m_gameTime,
        prison_area = (EEex_Sprite_GetLocalString(p1, "CBMP1AR") or ""):upper(),
        prison_x = EEex_Sprite_GetLocalInt(p1, "CBMP1X"),
        prison_y = EEex_Sprite_GetLocalInt(p1, "CBMP1Y"),
        x = p1.m_pos.x,
        y = p1.m_pos.y,
        areas = areas,
        wmap = (Infinity_IsMenuOnStack("WORLD_MAP") ~= nil
                and Infinity_IsMenuOnStack("WORLD_MAP") ~= false
                and Infinity_IsMenuOnStack("WORLD_MAP") ~= 0),
    }
end

function CBMP.p1_global(name, val)
    if val ~= nil then EEex_GameState_SetGlobalInt(name, val) end
    return EEex_GameState_GetGlobalInt(name)
end

function CBMP.p1_stash_cell(disable)
    if disable then
        if CBMPlayer1.hook.cell then
            CBMP_SAVED_CELL = CBMPlayer1.hook.cell
            CBMPlayer1.hook.cell = nil
            EEex_WritePtr(CBMP_SAVED_CELL, 0)
        end
        return true
    else
        if CBMP_SAVED_CELL then
            CBMPlayer1.hook.cell = CBMP_SAVED_CELL
            CBMP_SAVED_CELL = nil
            local p1 = CBMPlayer1.protagonist()
            local scan = p1 and CBMPlayer1.scan(p1)
            local active = (scan and (scan.statue or scan.maze)) and EEex_UDToPtr(p1) or 0
            EEex_WritePtr(CBMPlayer1.hook.cell, active)
        end
        return true
    end
end

function CBMP.p1_petrify()
    local p1 = CBMPlayer1.protagonist()
    EEex_GameObject_ApplyEffect(p1, {
        effectID = 37, effectAmount = -80, dwFlags = 0, durationType = 0, duration = 60,
        m_sourceRes = "CBMP1SAV", sourceID = p1.m_id, sourceTarget = p1.m_id,
    })
    EEex_Action_QueueResponseStringOnAIBase('ApplySpellRES("SPWI604",Myself)', p1)
    return true
end

function CBMP.p1_clear_save_pen()
    local p1 = CBMPlayer1.protagonist()
    EEex_GameObject_ApplyEffect(p1, {
        effectID = 321, res = "CBMP1SAV", durationType = 1,
        sourceID = p1.m_id, sourceTarget = p1.m_id,
    })
    return true
end

function CBMP.p1_cure_statue()
    local p1 = CBMPlayer1.protagonist()
    EEex_Action_QueueResponseStringOnAIBase('ApplySpellRES("SPWI625",Myself)', p1)
    return true
end

function CBMP.p1_imprison()
    local p1 = CBMPlayer1.protagonist()
    EEex_Action_QueueResponseStringOnAIBase('ApplySpellRES("SPWI910",Myself)', p1)
    return true
end

function CBMP.p1_spawn_on_p2(res, dx, dy)
    local p2 = EEex_Sprite_GetInPortrait(1)
    local x, y = p2.m_pos.x + dx, p2.m_pos.y + dy
    EEex_Action_QueueResponseStringOnAIBase(string.format('CreateCreature("%s",[%d.%d],0)', res, x, y), p2)
    return {x = x, y = y}
end

function CBMP.p1_wmap_close()
    if worldMapScreen then pcall(function() worldMapScreen:OnCancelButtonClick() end) end
    return true
end

function CBMP.p1_wmap_travel(dest_idx)
    local ptr = EEex_UDToPtr(worldMapScreen)
    EEex_Write32(ptr + 0xE78, dest_idx)
    worldMapScreen:TravelToSelected()
    return true
end

function CBMP.p1_in_combat()
    local s = EEex_Sprite_GetInPortrait(1)
    if not s then return false end
    return EEex_Trigger_EvalConditionalStringAsAIBase("ActuallyInCombat()", s)
end

return true
"""


def wmp_area_indices(game_dir):
    spec = importlib.util.spec_from_file_location("p1_ie", HERE.parent / "ie.py")
    ie = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ie)
    ie.TYPES["WMP"] = 0x03F7
    g = ie.Game(game_dir)
    wmp = g.get("WORLDMAP", "WMP")
    _, entry_off = struct.unpack_from("<II", wmp, 8)
    area_cnt, area_off = struct.unpack_from("<II", wmp, entry_off + 0x20)
    indices = {}
    for idx in range(area_cnt):
        off = area_off + idx * 240
        res = wmp[off:off + 8].split(b"\0", 1)[0].decode("latin-1").upper()
        indices[res] = idx
    return indices


class LabRunner:
    def __init__(self, args, report):
        self.args = args
        self.game = args.game.resolve()
        self.profile = args.profile.resolve()
        self.out = args.out.resolve()
        self.report = report
        self.report.setdefault("lab_runs", {})

    def start(self, tag, save_folder, seconds=None):
        sub = self.out / tag
        sub.mkdir(parents=True, exist_ok=True)
        stop = sub / "stop.flag"
        status = sub / "load-status.json"
        stop.unlink(missing_ok=True)
        status.unlink(missing_ok=True)
        for stale in ("eeex_remote_ready.json", "eeex_remote_result.json"):
            (self.game / "override" / stale).unlink(missing_ok=True)
        for pending in ("eeex_remote_cmd.lua", "eeex_remote_cmd.lua.run"):
            if (self.game / "override" / pending).exists():
                raise RuntimeError(f"a remote command is pending in the lab: {pending}")
        console = rp.Console(self.game / "override", sub / "console")
        launcher = subprocess.Popen(
            [sys.executable, "-I", str(self.args.lab_tools / "bg_lab_slots.py"), "run",
             str(self.game), str(self.profile), str(sub / "lab-run.json"),
             str(seconds or self.args.seconds), "--owner", self.args.owner,
             "--purpose", f"chriz-bg-magic M_CBMP1 checks ({tag})", "--stop", str(stop)],
            stdout=(sub / "launcher.log").open("w", encoding="utf-8"), stderr=subprocess.STDOUT,
        )
        rp.log(f"[{tag}] starting (launcher pid {launcher.pid}, save {save_folder})")
        deadline = time.monotonic() + 240
        while not (self.game / "override/eeex_remote_ready.json").exists():
            if launcher.poll() is not None:
                raise RuntimeError(f"[{tag}] launcher exited early ({launcher.returncode})")
            if time.monotonic() > deadline:
                raise TimeoutError(f"[{tag}] no remote-console handshake")
            time.sleep(1)
        deadline = time.monotonic() + 180
        while True:
            stack = console.lua(f"{tag}-screen", rp.SCREEN) or ""
            if any(m in stack.split(",") for m in ("START", "START_MAIN", "START_SP")):
                break
            if time.monotonic() > deadline:
                raise TimeoutError(f"[{tag}] no start screen; last {stack}")
            time.sleep(2)
        console.lua(f"{tag}-load", f"return assert(loadfile([[{self.args.load_lua.as_posix()}]]))"
                                   f"({{folder=[[{save_folder}]],campaign='soa',status=[[{status.as_posix()}]]}})")
        deadline = time.monotonic() + 120
        while True:
            st = json.loads(status.read_text(encoding="utf-8")) if status.exists() else {}
            if st.get("status") == "complete":
                break
            if st.get("status") == "failed" or time.monotonic() > deadline:
                raise RuntimeError(f"[{tag}] loading {save_folder} failed: {st}")
            time.sleep(0.3)
        rp.log(f"[{tag}] save loaded")
        time.sleep(2.5)
        console.lua(f"{tag}-probe", f"return assert(loadfile([[{rp.PROBE.as_posix()}]]))()")
        console.lua(f"{tag}-probe2", f"return assert(loadfile([[{EXTRA.as_posix()}]]))()")
        console.lua(f"{tag}-poll", POLL_SETUP_LUA)
        console.lua(f"{tag}-p1h", P1_HELPERS_LUA)
        console.p(f"{tag}-unpause", "unpause()")
        console.p(f"{tag}-protect", "protect_party()")
        time.sleep(2)
        return tag, launcher, stop, sub, console

    def stop(self, handle):
        tag, launcher, stop, sub, _ = handle
        stop.write_text("stop\n", encoding="utf-8")
        try:
            launcher.wait(timeout=180)
        except subprocess.TimeoutExpired:
            rp.log(f"[{tag}] launcher did not stop in time")
        run_file = sub / "lab-run.json"
        run = json.loads(run_file.read_text(encoding="utf-8")) if run_file.exists() else {}
        self.report["lab_runs"][tag] = {
            k: run.get(k) for k in ("tripped", "max_job_audio_peak", "left_in_job", "exit_code") if k in run
        }
        rp.log(f"[{tag}] stopped: {self.report['lab_runs'][tag]}")


def archive_autosave(autosave_dir, dest_dir):
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in autosave_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, dest_dir / item.name)


def move_party(c, tag, area, points):
    c.p(f"{tag}-clr", """order_party(2, 'ClearAllActions()')""")
    c.p(f"{tag}-unp0", "unpause()")
    time.sleep(0.5)
    st0 = c.p(f"{tag}-st0", "p1_status()")
    start_idx = 1 if st0["out"] == 1 else 0
    for idx in range(start_idx, len(points)):
        x, y = points[idx]
        c.p(f"{tag}-mv{idx}", f"""order_party({idx}, 'LeaveAreaLUA("{area}","",[{x}.{y}],0)')""")
    st = None
    for i in range(18):
        time.sleep(0.5)
        c.p(f"{tag}-unp-{i}", "unpause()")
        st = c.p(f"{tag}-st-{i}", "p1_status()")
        if st["areas"] == [area, area, area]:
            break
    if not st or st["areas"] != [area, area, area]:
        raise RuntimeError(f"{tag}: move_party to {area} left areas={st and st['areas']}")
    c.p(f"{tag}-prot", "protect_party()")
    time.sleep(1.0)


def save_autosave(c, tag, autosave_dir, dest_dir):
    gam = autosave_dir / "BALDUR.gam"
    sav = autosave_dir / "BALDUR.SAV"
    before_gam = gam.stat().st_mtime_ns
    before_sav = sav.stat().st_mtime_ns
    c.p(f"{tag}-clr", """order_party(2, 'ClearAllActions()')""")
    c.p(f"{tag}-unp0", "unpause()")
    time.sleep(0.5)
    c.p(f"{tag}-save", """order_party(2, 'SaveGame(0)')""")
    updated = False
    for i in range(20):
        time.sleep(0.4)
        c.p(f"{tag}-unp-{i}", "unpause()")
        if gam.stat().st_mtime_ns != before_gam and sav.stat().st_mtime_ns != before_sav:
            updated = True
            break
    if not updated:
        st = c.p(f"{tag}-fail-st", "p1_status()")
        raise RuntimeError(f"{tag}: SaveGame(0) did not update {autosave_dir}; status={st}")
    time.sleep(0.6)
    archive_autosave(autosave_dir, dest_dir)


def rest_party(c, tag):
    c.p(f"{tag}-clr", """order_party(2, 'ClearAllActions()')""")
    c.p(f"{tag}-unp0", "unpause()")
    time.sleep(0.5)
    c.p(f"{tag}-rest", """order_party(2, 'RestPartyEx(0,10,TRUE)')""")
    time.sleep(2.5)
    c.p(f"{tag}-unp1", "unpause()")


def run_all(runner, check, autosave_dir):
    wmp = wmp_area_indices(runner.game)
    idx_ar0020 = wmp["AR0020"]
    idx_ar0900 = wmp["AR0900"]

    # --- Session 1: World-map gather & travel (statue + prison) + Dreams on rest + Statue SaveGame(0) ---
    s1 = runner.start("s1-worldmap-dreams", runner.args.save)
    try:
        c = s1[4]
        st0 = c.p("s1-init", "p1_status()")
        check("M_CBMP1 hook and protagonist screen active on baseline load",
              st0["hook"] == "active" and st0["scan"]["net"] is True, status=st0)

        c.p("s1-bribe", 'p1_global("BribedCowled", 1)')
        c.p("s1-wmp-open1", """order_party(1, 'RevealAreaOnMap("AR0020")')""")
        c.p("s1-wmp-flag1", """order_party(1, 'AddWorldmapAreaFlag("AR0020",EXPLORABLE)')""")
        c.p("s1-wmp-open2", """order_party(1, 'RevealAreaOnMap("AR0900")')""")
        c.p("s1-wmp-flag2", """order_party(1, 'AddWorldmapAreaFlag("AR0900",EXPLORABLE)')""")
        time.sleep(2.0)

        move_party(c, "s1-ar0020", "AR0020", ((277, 853), (310, 853), (340, 853)))

        # Statue map-edge gather check (negative without cell, then positive -> world map -> AR0900).
        c.p("s1-petrify", "p1_petrify()")
        st_statue = None
        for i in range(12):
            time.sleep(0.5)
            st_statue = c.p(f"s1-statue-{i}", "p1_status()")
            if st_statue["scan"]["statue"] and st_statue["out"] == 1 and st_statue["cell"] == st_statue["p1_ptr"]:
                break
        c.p("s1-rm-pen1", "p1_clear_save_pen()")
        check("AR0020: Player1 becomes a statue with CBM_P1_OUT == 1 and travel cell set",
              st_statue["scan"]["statue"] and st_statue["out"] == 1
              and st_statue["cell"] == st_statue["p1_ptr"], status=st_statue)

        c.p("s1-cell-off", "p1_stash_cell(true)")
        c.p("s1-edge-neg", """order_party(1, 'LeaveArea("",[310.853],1)')""")
        time.sleep(2.5)
        st_neg = c.p("s1-neg-check", "p1_status()")
        if st_neg["wmap"]:
            c.p("s1-neg-close", "p1_wmap_close()")
            time.sleep(1.0)
        c.p("s1-clear-neg", """order_party(2, 'ClearAllActions()')""")
        time.sleep(0.5)
        c.p("s1-cell-on", "p1_stash_cell(false)")
        check("LeaveArea map-edge gather refuses to open WORLD_MAP when hook cell is cleared",
              not st_neg["wmap"] and st_neg["areas"] == ["AR0020", "AR0020", "AR0020"], status=st_neg)

        c.p("s1-edge-pos", """order_party(1, 'LeaveArea("",[310.853],1)')""")
        time.sleep(2.5)
        st_wmap = c.p("s1-wmap-open", "p1_status()")
        check("LeaveArea map-edge gather opens WORLD_MAP while Player1 is a statue",
              st_wmap["wmap"] is True, status=st_wmap)
        if st_wmap["wmap"]:
            c.p("s1-travel-0900", f"p1_wmap_travel({idx_ar0900})")
            time.sleep(4.5)
            c.p("s1-unp-0900", "unpause()")
            time.sleep(1.5)
        st_0900 = c.p("s1-at-0900", "p1_status()")
        if st_0900["wmap"]:
            c.p("s1-close-0900", "p1_wmap_close()")
            time.sleep(1.0)
        check("World-map travel brings statue Player1 and companions to AR0900",
              st_0900["areas"] == ["AR0900", "AR0900", "AR0900"]
              and st_0900["scan"]["statue"] and st_0900["out"] == 1, status=st_0900)

        c.p("s1-cure1", "p1_cure_statue()")
        st_cured = None
        for i in range(14):
            time.sleep(0.5)
            c.p(f"s1-cure1-unp-{i}", "unpause()")
            st_cured = c.p(f"s1-cured1-{i}", "p1_status()")
            if not st_cured["scan"]["statue"] and st_cured["out"] == 0:
                break
        check("Stone to Flesh cures Player1 after world-map travel",
              not st_cured["scan"]["statue"] and st_cured["out"] == 0, status=st_cured)

        # Imprisoned world-map travel (AR0900 -> WORLD_MAP -> AR0020 -> Freedom blocked -> back to AR0900 -> Freedom).
        c.p("s1-imprison", "p1_imprison()")
        st_pris = None
        for i in range(20):
            time.sleep(0.5)
            c.p(f"s1-pris-unp-{i}", "unpause()")
            st_pris = c.p(f"s1-pris-{i}", "p1_status()")
            if st_pris["scan"]["maze"] and st_pris["out"] == 1 and st_pris["cell"] == st_pris["p1_ptr"]:
                break
        c.p("s1-clr-pris", """order_party(2, 'ClearAllActions()')""")
        time.sleep(0.5)
        p2_pos = c.p("s1-p2pos", "party()")[1]
        c.p("s1-edge-pris", f"""order_party(1, 'LeaveArea("",[{p2_pos["x"]}.{p2_pos["y"]}],1)')""")
        time.sleep(2.5)
        st_wmap2 = c.p("s1-wmap2", "p1_status()")
        check("LeaveArea map-edge gather opens WORLD_MAP while Player1 is imprisoned",
              st_pris["scan"]["maze"] and st_wmap2["wmap"] is True, pris=st_pris, wmap=st_wmap2)
        if st_wmap2["wmap"]:
            c.p("s1-travel-0020", f"p1_wmap_travel({idx_ar0020})")
            time.sleep(4.5)
            c.p("s1-unp-0020", "unpause()")
            time.sleep(1.5)
        st_pris_0020 = c.p("s1-pris-0020", "p1_status()")
        if st_pris_0020["wmap"]:
            c.p("s1-close-0020", "p1_wmap_close()")
            time.sleep(1.0)
        check("World-map travel brings imprisoned Player1 to AR0020 still imprisoned",
              st_pris_0020["areas"] == ["AR0020", "AR0020", "AR0020"]
              and st_pris_0020["scan"]["maze"] and st_pris_0020["out"] == 1, status=st_pris_0020)

        c.p("s1-clr-fw", """order_party(2, 'ClearAllActions()')""")
        time.sleep(0.4)
        c.p("s1-free-wrong", 'cast(1, "SPWI917", "Myself")')
        time.sleep(6.5)
        c.p("s1-unp-fw", "unpause()")
        st_still = c.p("s1-still-pris", "p1_status()")
        check("Freedom in AR0020 leaves Player1 imprisoned when vanished in AR0900",
              st_still["scan"]["maze"] and st_still["out"] == 1, status=st_still)

        c.p("s1-clr-eb", """order_party(2, 'ClearAllActions()')""")
        time.sleep(0.5)
        p2_pos2 = c.p("s1-p2pos2", "party()")[1]
        c.p("s1-edge-back", f"""order_party(1, 'LeaveArea("",[{p2_pos2["x"]}.{p2_pos2["y"]}],1)')""")
        st_wmap3 = None
        for i in range(10):
            time.sleep(0.5)
            st_wmap3 = c.p(f"s1-wmap3-{i}", "p1_status()")
            if st_wmap3["wmap"]:
                break
        if st_wmap3 and st_wmap3["wmap"]:
            c.p("s1-travel-back", f"p1_wmap_travel({idx_ar0900})")
            time.sleep(4.5)
            c.p("s1-unp-back", "unpause()")
            time.sleep(1.5)
        if c.p("s1-wmap3-after", "p1_status()")["wmap"]:
            c.p("s1-close-back", "p1_wmap_close()")
            time.sleep(1.0)
        c.p("s1-clr-fr", """order_party(2, 'ClearAllActions()')""")
        time.sleep(0.4)
        c.p("s1-free-right", 'cast(1, "SPWI917", "Myself")')
        st_freed = None
        for i in range(18):
            time.sleep(0.5)
            c.p(f"s1-fr-unp-{i}", "unpause()")
            st_freed = c.p(f"s1-freed-{i}", "p1_status()")
            if not st_freed["scan"]["maze"] and not st_freed["scan"]["marker"] and st_freed["out"] == 0:
                break
        check("Returning via world map to AR0900 and casting Freedom frees Player1",
              not st_freed["scan"]["maze"] and not st_freed["scan"]["marker"] and st_freed["out"] == 0,
              status=st_freed)

        # Return to BFQAAR for Statue SaveGame(0) and PLAYER1D dream-on-rest test.
        move_party(c, "s1-bfqa", "BFQAAR", ((3070, 3120), (3100, 3135), (3130, 3120)))
        c.p("s1-petrify2", "p1_petrify()")
        for i in range(14):
            time.sleep(0.5)
            st_bfqa_st = c.p(f"s1-bfqa-st-{i}", "p1_status()")
            if st_bfqa_st["scan"]["statue"] and st_bfqa_st["out"] == 1:
                break
        c.p("s1-rm-pen2", "p1_clear_save_pen()")
        save_autosave(c, "s1-save-statue", autosave_dir, runner.out / "saved_games" / "statue")

        c.p("s1-dr-imoen", 'p1_global("HadImoenDream1", 1)')
        c.p("s1-dr-jon1", 'p1_global("HadJonDream1", 1)')
        c.p("s1-dr-jon2", 'p1_global("HadJonDream2", 1)')
        c.p("s1-dr-drow", 'p1_global("DrowTalk", 4)')
        c.p("s1-dr-asyl", 'p1_global("AsylumPlot", 55)')
        c.p("s1-dr-slay", 'p1_global("HadSlayerDream", 0)')
        tick_before_rest1 = c.p("s1-dr-st0", "p1_status()")["tick"]
        rest_party(c, "s1-rest-out")
        dream_while_out = c.p("s1-dr-read1", 'p1_global("HadSlayerDream")')
        st_after_rest1 = c.p("s1-dr-st1", "p1_status()")
        check("Dreams on rest: PLAYER1D dream is suppressed while Player1 is a statue and not consumed",
              dream_while_out == 0 and st_after_rest1["areas"] == ["BFQAAR", "BFQAAR", "BFQAAR"]
              and st_after_rest1["out"] == 1 and st_after_rest1["tick"] - tick_before_rest1 >= 2000,
              had_dream=dream_while_out, tick_delta=st_after_rest1["tick"] - tick_before_rest1, status=st_after_rest1)

        c.p("s1-cure2", "p1_cure_statue()")
        for i in range(14):
            time.sleep(0.5)
            c.p(f"s1-cure2-unp-{i}", "unpause()")
            if c.p(f"s1-cure2-st-{i}", "p1_status()")["out"] == 0:
                break
        rest_party(c, "s1-rest-in")
        dream_after_cure = 0
        for i in range(20):
            time.sleep(0.5)
            c.p(f"s1-dr-unp2-{i}", "unpause()")
            dream_after_cure = c.p(f"s1-dr-read2-{i}", 'p1_global("HadSlayerDream")')
            if dream_after_cure == 1:
                break
        check("Dreams on rest: PLAYER1D dream fires on rest once Player1 is cured",
              dream_after_cure == 1, had_dream=dream_after_cure)
    finally:
        runner.stop(s1)

    # --- Session 2: Cold reload of Statue SaveGame(0), cure, then Imprisoned SaveGame(0) ---
    s2 = runner.start("s2-reload-statue", AUTOSAVE_FOLDER)
    try:
        c = s2[4]
        st_rel = c.p("s2-status", "p1_status()")
        check("Cold reload (statue): Player1 remains a statue with active hook cell and CBM_P1_OUT == 1",
              st_rel["scan"]["statue"] and st_rel["scan"]["net"] and st_rel["out"] == 1
              and st_rel["areas"] == ["BFQAAR", "BFQAAR", "BFQAAR"]
              and st_rel["hook"] == "active" and st_rel["cell"] == st_rel["p1_ptr"], status=st_rel)
        c.p("s2-cure", "p1_cure_statue()")
        st_cured = None
        for i in range(14):
            time.sleep(0.5)
            c.p(f"s2-cure-unp-{i}", "unpause()")
            st_cured = c.p(f"s2-cured-{i}", "p1_status()")
            if not st_cured["scan"]["statue"] and st_cured["out"] == 0 and st_cured["cell"] == 0:
                break
        check("Cold reload (statue): Stone to Flesh cures Player1 cleanly after reload",
              not st_cured["scan"]["statue"] and st_cured["out"] == 0 and st_cured["cell"] == 0,
              status=st_cured)

        c.p("s2-imprison", "p1_imprison()")
        st_pris = None
        for i in range(20):
            time.sleep(0.5)
            c.p(f"s2-pris-unp-{i}", "unpause()")
            st_pris = c.p(f"s2-pris-{i}", "p1_status()")
            if st_pris["scan"]["maze"] and st_pris["out"] == 1 and st_pris["cell"] == st_pris["p1_ptr"]:
                break
        check("Before prison save: Player1 is imprisoned in BFQAAR",
              st_pris["scan"]["maze"] and st_pris["prison_area"] == "BFQAAR", status=st_pris)
        save_autosave(c, "s2-save-pris", autosave_dir, runner.out / "saved_games" / "prison")
    finally:
        runner.stop(s2)

    # --- Session 3: Cold reload of Prison SaveGame(0), Freedom, then Typed-Bonus SaveGame(0) ---
    base_unbuffed = None
    expected_buffed = None
    s3 = runner.start("s3-reload-prison", AUTOSAVE_FOLDER)
    try:
        c = s3[4]
        st_rel = c.p("s3-status", "p1_status()")
        check("Cold reload (prison): Player1 remains imprisoned with stored origin coordinates intact",
              st_rel["scan"]["maze"] and st_rel["scan"]["marker"] and st_rel["out"] == 1
              and st_rel["cell"] == st_rel["p1_ptr"] and st_rel["prison_area"] == "BFQAAR"
              and st_rel["prison_x"] > 0 and st_rel["prison_y"] > 0, status=st_rel)
        c.p("s3-clr-fr", """order_party(2, 'ClearAllActions()')""")
        time.sleep(0.4)
        c.p("s3-free", 'cast(1, "SPWI917", "Myself")')
        st_freed = None
        for i in range(18):
            time.sleep(0.5)
            c.p(f"s3-fr-unp-{i}", "unpause()")
            st_freed = c.p(f"s3-freed-{i}", "p1_status()")
            if not st_freed["scan"]["maze"] and not st_freed["scan"]["marker"] and st_freed["out"] == 0:
                break
        check("Cold reload (prison): Freedom frees Player1 and restores origin spot after reload",
              not st_freed["scan"]["maze"] and not st_freed["scan"]["marker"] and st_freed["out"] == 0
              and abs(st_freed["x"] - st_rel["prison_x"]) <= 64
              and abs(st_freed["y"] - st_rel["prison_y"]) <= 64, status=st_freed)

        # Clear any temporary saves on portrait 0 and prepare overlapping base-game typed spells:
        # Blur (SPWI201: +3 Dodge AC, +1 Dodge saves), Defensive Harmony (SPPR406: +4 Dodge AC),
        # Bless (SPPR101: +1 Favor THAC0, +1 Favor dmg), and Luck (SPWI209: +1 Luck, +1 Luck saves).
        overlap_spells = ("SPWI201", "SPPR406", "SPPR101", "SPWI209")
        c.p("s3-bo-clear", f"bonus_clear(0, {rb.lua_strings(['CBMQLAB', *overlap_spells])})")
        c.lua("s3-rm-saves", """
            local s = EEex_Sprite_GetInPortrait(0)
            local now = EngineGlobals.g_pBaldurChitin.m_pObjectGame.m_worldTime.m_gameTime
            EEex_Utility_IterateCPtrList(s.m_timedEffectList, function(e)
                if (e.m_effectId == 33 or e.m_effectId == 36 or e.m_effectId == 37) and e.m_dWFlags == 1 then
                    e.m_duration = now
                end
            end)
            return true
        """)
        time.sleep(2)
        c.p("s3-bo-reb0", "bonus_rebuild(0)")
        time.sleep(1.2)
        base_unbuffed = rb.bonus_values(c.p("s3-bo-base", "bonus_snapshot(0)"))
        for res in overlap_spells:
            c.p(f"s3-bo-ap-{res}", f"bonus_apply(0, {json.dumps(res)})")
            time.sleep(2.5)
        # Extend active timed spell durations to 240s (still < 8h so Rest expires them, > 60s drift window).
        c.p("s3-bo-ext", f"bonus_expire(0, {rb.lua_strings(overlap_spells)}, 240)")
        time.sleep(1.5)
        c.p("s3-bo-reb1", "bonus_rebuild(0)")
        time.sleep(1.2)
        snap_before_save = c.p("s3-bo-snap", "bonus_snapshot(0)")
        expected_buffed = rb.bonus_values(snap_before_save)
        delta = {
            "ac": base_unbuffed["ac"] - expected_buffed["ac"],
            "thac0": base_unbuffed["thac0"] - expected_buffed["thac0"],
            "dmg": expected_buffed["dmg"] - base_unbuffed["dmg"],
            "luck": expected_buffed["luck"] - base_unbuffed["luck"],
            "saves": [a - b for a, b in zip(base_unbuffed["saves"], expected_buffed["saves"])],
        }
        check("Before bonus save: overlapping Blur, Defensive Harmony, Bless, and Luck give +4 AC, +1 THAC0/dmg/luck, +2 saves",
              delta == {"ac": 4, "thac0": 1, "dmg": 1, "luck": 1, "saves": [2] * 5},
              base=base_unbuffed, buffed=expected_buffed, delta=delta)
        save_autosave(c, "s3-save-bonus", autosave_dir, runner.out / "saved_games" / "bonus")
    finally:
        runner.stop(s3)

    # --- Session 4: Cold reload of Typed-Bonus Save + Area Change + 60s + Rest + Dead-End Combat Clock ---
    s4 = runner.start("s4-reload-bonus-and-combat", AUTOSAVE_FOLDER, seconds=600)
    try:
        c = s4[4]
        c.p("s4-bo-reb0", "bonus_rebuild(0)")
        time.sleep(1.2)
        reload_vals = rb.bonus_values(c.p("s4-bo-rel", "bonus_snapshot(0)"))
        check("Cold reload (typed bonuses): corrected values match pre-save totals without drift",
              reload_vals == expected_buffed, expected=expected_buffed, got=reload_vals)

        move_party(c, "s4-ar0020", "AR0020", ((277, 853), (310, 853), (340, 853)))
        c.p("s4-bo-reb1", "bonus_rebuild(0)")
        time.sleep(1.2)
        area_snap0 = c.p("s4-bo-ar0", "bonus_snapshot(0)")
        samples = [area_snap0]
        for i in range(6):
            time.sleep(10)
            c.p(f"s4-bo-rebl-{i}", "bonus_rebuild(0)")
            time.sleep(1.0)
            samples.append(c.p(f"s4-bo-smp-{i}", "bonus_snapshot(0)"))
        check("Typed bonuses across area change and 60 seconds: totals stay constant without drift",
              all(rb.bonus_values(s) == expected_buffed for s in samples)
              and samples[-1]["time"] - samples[0]["time"] >= 60 * 15,
              ticks=samples[-1]["time"] - samples[0]["time"], first=rb.bonus_values(samples[0]),
              last=rb.bonus_values(samples[-1]))

        move_party(c, "s4-bfqa", "BFQAAR", ((3070, 3120), (3100, 3135), (3130, 3120)))
        tick_before_rest = c.p("s4-bo-pre-rest", "bonus_snapshot(0)")["time"]
        rest_party(c, "s4-rest")
        c.p("s4-bo-rebr", "bonus_rebuild(0)")
        time.sleep(1.2)
        rest_snap = c.p("s4-bo-rest", "bonus_snapshot(0)")
        rest_vals = rb.bonus_values(rest_snap)
        check("Typed bonuses after rest: expired buffs leave clean unbuffed totals with zero residue",
              rest_vals == base_unbuffed and rest_snap["time"] - tick_before_rest >= 2000,
              base=base_unbuffed, after_rest=rest_vals, tick_delta=rest_snap["time"] - tick_before_rest)

        # 4. Real melee combat during the 30-second dead-end clock (CBMP1_Stuck), in AR0330 (open floor, no area script).
        move_party(c, "s4-ar0330", "AR0330", ((235, 360), (265, 360), (250, 385)))
        c.p("s4-clr-area", "remove_all_others()")
        for idx in range(3):
            c.p(f"s4-clr-p{idx}", f"""order_party({idx}, 'ClearAllActions()')""")
        for i in range(40):
            time.sleep(0.5)
            c.p(f"s4-calm-unp-{i}", "unpause()")
            if not c.p(f"s4-calm-{i}", "p1_in_combat()"):
                break
        c.lua("s4-deadend-cfg", """
            CBMPlayer1.DEAD_ENDS[#CBMPlayer1.DEAD_ENDS + 1] = {areas = {AR0330 = true}}
            CBMPlayer1.CURES.statue = {spells = {}, items = {}}
            return true
        """)
        c.p("s4-prot", "protect_party()")
        c.p("s4-petrify", "p1_petrify()")
        clock_before = 0
        for i in range(60):
            time.sleep(0.5)
            c.p(f"s4-wunp-{i}", "unpause()")
            st = c.p(f"s4-wait-clk-{i}", "p1_status()")
            if st["stuck"] == 1 and st["clock"] >= 120:
                clock_before = st["clock"]
                break
        c.p("s4-rm-pen", "p1_clear_save_pen()")
        check("Dead-end clock starts counting while out of combat",
              120 <= clock_before < 350, clock_before=clock_before)

        # Spawn hostile Tasloi via Player2 (since Player1 is a statue!) right next to the party in AR0330.
        c.p("s4-clr-foe", """order_party(2, 'ClearAllActions()')""")
        time.sleep(0.4)
        c.p("s4-foe", 'p1_spawn_on_p2("TASLOI01", 25, 0)')
        seen = []
        for i in range(25):
            time.sleep(0.4)
            c.p(f"s4-kunp-{i}", "unpause()")
            seen = [o for o in (c.p(f"s4-kwho-{i}", "others()") or []) if o["name"] == "Tasloi"]
            if seen:
                break
        if not seen:
            raise RuntimeError(f"s4-foe: Tasloi did not spawn; status={c.p('s4-foe-st', 'p1_status()')}")
        c.p("s4-foe-live", 'fx("Tasloi", 208, 1, 0, 600)')
        c.p("s4-foe-hp", 'fx("Tasloi", 18, 900, 0, 600)')
        c.p("s4-p2-att", """order_party(1, 'AttackReevaluate("Tasloi",30)')""")
        c.p("s4-p3-att", """order_party(2, 'AttackReevaluate("Tasloi",30)')""")
        c.p("s4-tatt", """order("Tasloi", 'AttackReevaluate(Player2,30)')""")

        combat_start_clock = None
        combat_start_tick = None
        combat_clocks = []
        for i in range(45):
            time.sleep(0.5)
            c.p(f"s4-cunp-{i}", "unpause()")
            fighting = c.p(f"s4-fight-{i}", "p1_in_combat()")
            st = c.p(f"s4-cst-{i}", "p1_status()")
            if fighting:
                if combat_start_clock is None:
                    combat_start_clock = st["clock"]
                    combat_start_tick = st["tick"]
                combat_clocks.append(st["clock"])
                if st["tick"] - combat_start_tick >= 180:
                    break
        combat_span = (st["tick"] - combat_start_tick) if combat_start_tick is not None else 0
        check("Dead-end clock pauses without resetting during >= 12 seconds of real melee combat",
              combat_start_clock is not None and combat_start_clock > 0
              and combat_span >= 180 and len(set(combat_clocks)) == 1
              and combat_clocks[-1] < 450,
              combat_start_clock=combat_start_clock, combat_clocks=combat_clocks, combat_ticks=combat_span)

        c.p("s4-end-fight", "remove_all_others()")
        c.p("s4-clear-all", """order_party(2, 'ClearAllActions()')""")
        resume_start_tick = None
        final_clock = combat_clocks[-1] if combat_clocks else 0
        for i in range(100):
            time.sleep(0.5)
            c.p(f"s4-runp-{i}", "unpause()")
            fighting = c.p(f"s4-rfight-{i}", "p1_in_combat()")
            st = c.p(f"s4-rst-{i}", "p1_status()")
            if not fighting and resume_start_tick is None:
                resume_start_tick = st["tick"]
            final_clock = st["clock"]
            if final_clock >= 450:
                break
        resume_ticks = (st["tick"] - resume_start_tick) if resume_start_tick is not None else -1
        check("After combat ends, dead-end clock resumes from its paused value to >= 450 (game over)",
              final_clock >= 450 and combat_start_clock is not None
              and 0 < resume_ticks < (450 - combat_start_clock + 90),
              paused_at=combat_start_clock, final_clock=final_clock, resume_ticks=resume_ticks)
    finally:
        runner.stop(s4)


def main():
    ap = argparse.ArgumentParser()
    for name in ("--game", "--profile", "--lab-tools", "--load-lua", "--out"):
        ap.add_argument(name, required=True, type=Path)
    ap.add_argument("--save", required=True)
    ap.add_argument("--seconds", type=float, default=540)
    ap.add_argument("--owner", default="Antigravity: chriz-bg-magic M_CBMP1 checks")
    args = ap.parse_args()

    game, profile, out = args.game.resolve(), args.profile.resolve(), args.out.resolve()
    if (game / "steam_api64.dll").exists():
        sys.exit("steam_api64.dll is active in the lab")
    out.mkdir(parents=True, exist_ok=True)

    autosave_dir = profile / "save" / AUTOSAVE_FOLDER
    if not autosave_dir.is_dir():
        sys.exit(f"missing {autosave_dir}")
    autosave_backup = {p.name: p.read_bytes() for p in autosave_dir.iterdir() if p.is_file()}
    initial_saves = sorted(p.name for p in (profile / "save").iterdir())

    report = {"save": args.save, "checks": [], "error": None}

    def check(name, ok, **facts):
        report["checks"].append({"check": name, "ok": bool(ok), **facts})
        rp.log(f"  {'ok  ' if ok else 'FAIL'} {name} {json.dumps(facts, ensure_ascii=False)[:360]}")

    runner = LabRunner(args, report)
    try:
        run_all(runner, check, autosave_dir)
    except Exception as problem:  # noqa: BLE001
        report["error"] = f"{type(problem).__name__}: {problem}"
        rp.log("FAILED " + report["error"])
    finally:
        backup_lower = {k.lower() for k in autosave_backup}
        for item in list(autosave_dir.iterdir()):
            if item.is_file() and item.name.lower() not in backup_lower:
                item.unlink()
        for fname, raw in autosave_backup.items():
            (autosave_dir / fname).write_bytes(raw)
        final_saves = sorted(p.name for p in (profile / "save").iterdir())
        report["profile_saves_unchanged"] = (final_saves == initial_saves)

    (out / "probe-report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    passed = sum(1 for ch in report["checks"] if ch["ok"])
    rp.log(f"{passed} of {len(report['checks'])} checks passed; error: {report['error']}; "
           f"saves unchanged: {report['profile_saves_unchanged']}")
    return 0 if report["error"] is None and passed == len(report["checks"]) and report["profile_saves_unchanged"] else 1


if __name__ == "__main__":
    sys.exit(main())
