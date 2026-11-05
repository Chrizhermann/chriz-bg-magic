"""In-game checks of chriz-bg-magic's five fixes in a quiet disposable lab game.

usage: python -I tests/lab/run_probe.py --game <lab game> --profile <lab profile>
           --lab-tools <folder with bg_lab_slots.py> --load-lua <lab_load.lua> --save <save folder>
           --out <evidence folder> [--seconds 900]

The lab must have EEex with LuaJIT, the EEex Remote Console, a UI.MENU with the QA button
names lab_load.lua clicks, a profile with the quiet options (windowed, muted), and the
save in the profile. The game starts only through bg_lab_slots.py (hidden desktop,
muted, guards) and stops at the end; nothing is saved.

Each check sets up its own case, reads the creatures before and after, and decides in
Python. Results: <out>/probe-report.json; every console exchange in <out>/console/.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROBE = Path(__file__).resolve().parent / "probe.lua"


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


class Console:
    """One request at a time against the lab's EEex Remote Console (file IPC)."""

    def __init__(self, override, journal):
        self.override, self.journal = Path(override), Path(journal)
        self.journal.mkdir(parents=True, exist_ok=True)

    def send(self, label, code, timeout=30.0):
        cmd, result = self.override / "eeex_remote_cmd.lua", self.override / "eeex_remote_result.json"
        for pending in (cmd, self.override / "eeex_remote_cmd.lua.run"):
            if pending.exists():
                raise RuntimeError(f"a command is already pending: {pending.name}")
        request = uuid.uuid4().hex
        tmp = self.override / f"eeex_remote_cmd.tmp.{os.getpid()}"
        tmp.write_text(f"--@id={request}\n{code}", encoding="utf-8", newline="\n")
        result.unlink(missing_ok=True)
        os.replace(tmp, cmd)
        sent, reply = time.time(), None
        while time.time() - sent < timeout:
            if result.exists():
                try:
                    body = result.read_text(encoding="utf-8")
                except OSError:
                    body = ""
                if body:
                    data = json.loads(body)
                    result.unlink(missing_ok=True)
                    if data.get("id") in (None, request):
                        reply = data
                        break
            time.sleep(0.1)
        if reply is None and not cmd.exists():
            # Claimed but not answered yet: the console is deaf while no host menu
            # polls. Never resend; wait for the same request a while longer.
            while time.time() - sent < timeout + 90 and reply is None:
                if result.exists():
                    try:
                        data = json.loads(result.read_text(encoding="utf-8") or "{}")
                    except (OSError, json.JSONDecodeError):
                        data = {}
                    if data.get("id") in (None, request) and data:
                        result.unlink(missing_ok=True)
                        reply = dict(data, late=round(time.time() - sent, 1))
                time.sleep(0.2)
        if reply is None:
            reply = {"status": "timeout", "claimed": not cmd.exists()}
        stamp = datetime.now(timezone.utc).strftime("%H%M%S.%f")[:-3]
        (self.journal / f"{stamp}-{label}.json").write_text(
            json.dumps({"label": label, "code": code, "reply": reply}, indent=1, ensure_ascii=False), encoding="utf-8")
        return reply

    def lua(self, label, code, timeout=30.0):
        reply = self.send(label, code, timeout)
        if reply.get("status") != "ok":
            raise RuntimeError(f"{label}: {json.dumps(reply, ensure_ascii=False)[:800]}")
        values = reply.get("returnValues") or [None]
        return values[0]

    def p(self, label, call, timeout=30.0):
        return self.lua(label, f"return CBMP.{call}", timeout)


SCREEN = """
local seen = {}
for _, name in ipairs({"START", "START_MAIN", "START_SP", "WORLD_ACTIONBAR", "LOAD"}) do
    local v = Infinity_IsMenuOnStack(name)
    if v ~= nil and v ~= false and v ~= 0 then seen[#seen + 1] = name end
end
return table.concat(seen, ",")
"""


def effects_of(d, op=None):
    return [e for e in d.get("effects", []) if op is None or e["op"] == op]


GROUPS = ("spirit", "msd", "wake", "web", "fireball")


def run_checks(c, report, only=GROUPS):
    checks = report["checks"]

    def check(name, ok, **facts):
        checks.append({"check": name, "ok": bool(ok), **facts})
        log(f"  {'ok  ' if ok else 'FAIL'} {name} {json.dumps(facts, ensure_ascii=False)[:300]}")

    c.lua("probe", f"return assert(loadfile([[{PROBE.as_posix()}]]))()")
    report["unpause"] = c.p("unpause", "unpause()")
    c.p("protect", "protect_party()")
    report["party"] = c.p("party", "party()")
    time.sleep(1)

    if "spirit" in only:
        spirit(c, check)
    if "msd" in only:
        msd(c, check)
    if "wake" in only:
        wake(c, check)
    if "web" in only:
        web(c, check, report["party"][0])
    if "fireball" in only:
        fireball(c, check)


def spirit(c, check):
    # 1. Spirit Armor, cast twice on the cleric (portrait 2): one +3, one expiry cast.
    s0 = c.p("sa-0", 'portrait(2, "SPWI414")')
    c.p("sa-cast1", 'cast(2, "SPWI414", "Myself")')
    time.sleep(4)
    s1 = c.p("sa-1", 'portrait(2, "SPWI414")')
    c.p("sa-cast2", 'cast(2, "SPWI414", "Myself")')
    time.sleep(4)
    s2 = c.p("sa-2", 'portrait(2, "SPWI414")')
    check("Spirit Armor: second casting replaces the first",
          abs(s1["saves"]["spell"] - s0["saves"]["spell"]) == 3 and s2["saves"]["spell"] == s1["saves"]["spell"]
          and len(effects_of(s2, 148)) == 1 and len(effects_of(s2, 37)) == 1,
          spell_save=[s0["saves"]["spell"], s1["saves"]["spell"], s2["saves"]["spell"]],
          expiry_casts_after_two=len(effects_of(s2, 148)), save_bonuses_after_two=len(effects_of(s2, 37)))


def msd(c, check):
    # 2. Minor Spell Deflection on a mage (portrait 1), the cleric (portrait 2) casts.
    c.p("msd-cast", 'cast(1, "SPWI318", "Myself")')
    time.sleep(3)
    m0 = c.p("msd-0", 'portrait(1, "SPWI318")')
    c.p("msd-fs", 'cast(2, "SPPR503", "Player2")')
    time.sleep(4)
    m1 = c.p("msd-1", 'portrait(1, "SPWI318")')
    c.p("msd-heal", "heal(1)")
    time.sleep(1)
    m1h = c.p("msd-1h", 'portrait(1, "SPWI318")')
    c.p("msd-acid", 'cast(2, "SPWI211", "Player2")')
    time.sleep(4)
    m2 = c.p("msd-2", 'portrait(1, "SPWI318")')
    pool = lambda d: sorted({e["p1"] for e in effects_of(d, 201)})  # noqa: E731
    levels = lambda d: sorted(e["p2"] for e in effects_of(d, 201))  # noqa: E731
    check("Minor Spell Deflection: a level-5 spell (Flame Strike) gets through",
          m1["hp"] < m0["hp"] and pool(m1) == pool(m0), hp=[m0["hp"], m1["hp"]], pool=[pool(m0), pool(m1)],
          levels=levels(m0))
    check("Minor Spell Deflection: a level-2 spell (Melf's Acid Arrow) is absorbed",
          m2["hp"] >= m1h["hp"] and pool(m2) and pool(m2)[0] == pool(m1h)[0] - 2,
          hp=[m1h["hp"], m2["hp"]], pool=[pool(m1h), pool(m2)])
    c.p("msd-heal2", "heal(1)")


def fireball(c, check):
    # 3. Fireball at portrait 0, twice each way: breath save 1 (always succeeds) with
    #    spell save 20 (the worst; only a natural 20 can save), then the other way round.
    #    With save vs. breath the first set takes half damage, the second full; the ratio
    #    does not depend on difficulty.
    #    The level-18 mage (portrait 1) casts, so the Fireball has its full 10d6.
    runs, flags = {}, []
    for setup, saves in (("breath-succeeds", "{breath = 1, spell = 20}"), ("breath-fails", "{breath = 20, spell = 1}")):
        c.p(f"fb-saves-{setup}", f"set_saves(0, {saves}, 120)")
        runs[setup] = []
        for k in range(2):
            c.p(f"fb-heal-{setup}{k}", "heal(0)")
            time.sleep(1)
            before = c.p(f"fb-before-{setup}{k}", "portrait(0)")
            if k == 0:
                c.p(f"fb-log-clear-{setup}", "take_log()")
                c.p(f"fb-watch-{setup}", "watch(0, 8)")
            c.p(f"fb-cast-{setup}{k}", 'cast(1, "SPWI304", "Player1")')
            time.sleep(4)
            after = c.p(f"fb-after-{setup}{k}", "portrait(0)")
            if k == 0:
                flags += [h.get("save") for h in (c.p(f"fb-log-{setup}", "take_log(12)") or [])]
            runs[setup].append(before["hp"] - after["hp"])
    half, full = (sum(runs[s]) / 2 for s in ("breath-succeeds", "breath-fails"))
    check("Fireball: the breath save decides (half damage when only it succeeds)",
          full > 0 and half < 0.7 * full and flags
          and all(isinstance(f, int) and f & 2 and not f & 1 for f in flags),
          damage=runs, save_flags=sorted({hex(f) if isinstance(f, int) else str(f) for f in flags}))
    for i in range(3):
        c.p(f"fb-heal-end{i}", f"heal({i})")


def wake(c, check):
    # 4. Damage wakes sleepers: a huge spider (level 2, 18 HP, only the generic
    #    attack-on-sight script), held in place. Sleep, Power Word: Sleep, Command, Greater
    #    Command and Emotion: Hopelessness are cast at it. Color Spray never landed on it
    #    beside the party, and Stinking Cloud lacked a target (a Dense Pudding takes no
    #    sleep, a spawned wolf was not found), so their effects are applied to the spider
    #    directly (ApplySpellRES): the delivery is the base game's, the sleep effect is
    #    what the fix changed.
    c.p("sp-spawn", 'spawn("SPIDHU01", 110, 0)')
    time.sleep(2)
    c.p("sp-pin", 'pin("spidhu01")')
    c.p("sp-saves", 'set_saves("spidhu01", {death = 20, spell = 20}, 600)')
    for spell, label in (("SPWI116", "Sleep"), ("SPWI105", "Color Spray"), ("SPWI220", "Power Word: Sleep"),
                         ("SPWI213", "Stinking Cloud"), ("SPPR102", "Command"), ("SPPR512", "Greater Command"),
                         ("SPWI411", "Emotion: Hopelessness")):
        c.p(f"wk-cure-{spell}", 'cure_sleep("spidhu01")')
        time.sleep(1)
        how = "apply_spell" if spell in ("SPWI105", "SPWI213") else "cast"
        c.p(f"wk-cast-{spell}", f'{how}(1, "{spell}", \'"spidhu01"\')')
        time.sleep(4)
        asleep = c.p(f"wk-asleep-{spell}", 'creature("spidhu01", "' + spell + '")')
        c.p(f"wk-hit-{spell}", 'damage("spidhu01", 1)')
        time.sleep(1.5)
        awake = c.p(f"wk-awake-{spell}", 'creature("spidhu01", "' + spell + '")')
        check(f"{label}: a hit wakes the sleeper",
              asleep["state"] & 1 and not awake["state"] & 1,
              state=[hex(asleep["state"]), hex(awake["state"])],
              sleep_effects=[(e["op"], e["p2"]) for e in effects_of(asleep) if e["op"] in (39, 217)])


def web(c, check, p0):
    # 5. Web, cast at a giant spider, a tasloi (kobold) and one creature of each group the
    #    fix spares that nothing in the base game protects: a green slime (its RING95
    #    stops hold and sleep, not Web), a gauth (flying; real beholders have an item
    #    against Web), a greater wraith (incorporeal) and a fire giant (very large). They
    #    get the worst saves, and the effect logger shows that the spell reached them, so
    #    only the immunity can have spared them. The tasloi, with spell save 1 and breath
    #    save 20, is caught, and its Web effects carry the breath save; Web keeps the base
    #    game's -2, so even a spell save of 1 can fail and the catch alone proves nothing
    #    about the save type. Every base-game spider carries ANTIWEB, an immunity to the
    #    projectile that brings Web's effects, so the cast cannot show the fix's spider
    #    immunity: Web is then applied to the spider directly (ApplySpellRES, no
    #    projectile), where only the fix can stop it.
    spots = {"SPIDGI01": (-280, -30), "JELGRE01": (-280, 30), "TASLOI01": (-240, 0),
             "BEHGAU01": (-320, 0), "FIRWRA01": (-240, -60), "GIANTF01": (-240, 60)}
    for res, (dx, dy) in spots.items():
        c.p(f"web-spawn-{res}", f'spawn("{res}", {dx}, {dy})')
    time.sleep(3)
    immune = ("Green Slime", "Gauth", "Greater Wraith", "Fire Giant")
    keys = ("spidgi01", "Tasloi", *immune)
    for key in keys:
        c.p(f"web-pin-{key}", f'pin("{key}")')
    c.p("web-saves", 'set_saves("Tasloi", {breath = 20, spell = 1}, 600)')
    for key in ("spidgi01", *immune):
        c.p(f"web-saves-{key}", f'set_saves("{key}", {{breath = 20, spell = 20}}, 600)')
    c.p("web-log-clear", "take_log()")
    for key in keys:
        c.p(f"web-watch-{key}", f'watch("{key}", 12)')
    c.p("web-cast", f'cast_point(1, "SPWI215", {p0["x"] - 265}, {p0["y"]})')
    time.sleep(3)
    got = {key: c.p(f"web-read-{key}", f'creature("{key}", "SPWI215")') for key in keys}
    log = c.p("web-log-cast", "take_log()") or []
    reached = {key: [e["op"] for e in log if e["who"] == key and str(e["src"]).upper() == "SPWI215"] for key in immune}
    caught = {key: bool(effects_of(d, 157)) for key, d in got.items()}
    saves = [e["save"] for e in effects_of(got["Tasloi"])]
    check("Web: slime, gauth, wraith and giant immune, the tasloi caught through its breath save "
          "(the spider through ANTIWEB)",
          caught == {"spidgi01": False, "Tasloi": True, **dict.fromkeys(immune, False)}
          and all(324 in ops for ops in reached.values())
          and all(isinstance(s, int) and s & 2 and not s & 1 for s in saves),
          caught=caught, reached=reached, tasloi_saves=saves, states={k: hex(d["state"]) for k, d in got.items()})
    # The spider's logger from above is still running: the spell reaches it now.
    c.p("web-apply-spidgi01", 'apply_spell(1, "SPWI215", \'"spidgi01"\')')
    time.sleep(3)
    direct = c.p("web-read-direct-spidgi01", 'creature("spidgi01", "SPWI215")')
    arrived = [e["op"] for e in (c.p("web-log-spidgi01", "take_log()") or []) if str(e["src"]).upper() == "SPWI215"]
    check("Web applied without its projectile: the spider immune",
          not effects_of(direct, 157) and 324 in arrived,
          state=hex(direct["state"]), effects=[(e["op"], e["save"]) for e in effects_of(direct)], arrived=arrived)


def main():
    ap = argparse.ArgumentParser()
    for name in ("--game", "--profile", "--lab-tools", "--load-lua", "--out"):
        ap.add_argument(name, required=True, type=Path)
    ap.add_argument("--save", required=True)
    ap.add_argument("--seconds", type=float, default=900)
    ap.add_argument("--only", default=",".join(GROUPS), help="comma-separated: " + ",".join(GROUPS))
    ap.add_argument("--owner", default="Claude Code: chriz-bg-magic in-game checks")
    a = ap.parse_args()
    game, out = a.game.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    stop, status = out / "stop.flag", out / "load-status.json"
    stop.unlink(missing_ok=True)
    status.unlink(missing_ok=True)
    for stale in ("eeex_remote_ready.json", "eeex_remote_result.json"):
        (game / "override" / stale).unlink(missing_ok=True)
    for pending in ("eeex_remote_cmd.lua", "eeex_remote_cmd.lua.run"):
        if (game / "override" / pending).exists():
            sys.exit(f"a remote command is pending in the lab: {pending}")
    if (game / "steam_api64.dll").exists():
        sys.exit("steam_api64.dll is active in the lab")
    report = {"save": a.save, "checks": [], "error": None}
    console = Console(game / "override", out / "console")
    launcher = subprocess.Popen(
        [sys.executable, "-I", str(a.lab_tools / "bg_lab_slots.py"), "run", str(game), str(a.profile),
         str(out / "lab-run.json"), str(a.seconds), "--owner", a.owner,
         "--purpose", "in-game checks of chriz-bg-magic's first five fixes (PR #1)", "--stop", str(stop)],
        stdout=(out / "launcher.log").open("w", encoding="utf-8"), stderr=subprocess.STDOUT)
    log(f"lab game starting (launcher pid {launcher.pid})")
    try:
        deadline = time.monotonic() + 240
        while not (game / "override/eeex_remote_ready.json").exists():
            if launcher.poll() is not None:
                raise RuntimeError(f"the launcher exited early ({launcher.returncode})")
            if time.monotonic() > deadline:
                raise TimeoutError("no remote-console handshake")
            time.sleep(1)
        log("console ready")
        deadline = time.monotonic() + 180
        while True:
            stack = console.lua("screen", SCREEN) or ""
            if any(m in stack.split(",") for m in ("START", "START_MAIN", "START_SP")):
                break
            if time.monotonic() > deadline:
                raise TimeoutError(f"no start screen; last {stack}")
            time.sleep(2)
        console.lua("load", f"return assert(loadfile([[{a.load_lua.as_posix()}]]))"
                            f"({{folder=[[{a.save}]],campaign='soa',status=[[{status.as_posix()}]]}})")
        deadline = time.monotonic() + 120
        while True:
            st = json.loads(status.read_text(encoding="utf-8")) if status.exists() else {}
            if st.get("status") == "complete":
                break
            if st.get("status") == "failed" or time.monotonic() > deadline:
                raise RuntimeError(f"loading the save failed: {st}")
            time.sleep(0.3)
        log("save loaded")
        time.sleep(3)
        run_checks(console, report, [g.strip() for g in a.only.split(",") if g.strip()])
    except Exception as problem:  # noqa: BLE001 - recorded; the lab is stopped regardless
        report["error"] = f"{type(problem).__name__}: {problem}"
        log("FAILED " + report["error"])
    finally:
        stop.write_text("stop\n", encoding="utf-8")
        try:
            launcher.wait(timeout=180)
        except subprocess.TimeoutExpired:
            log("the launcher did not stop in time; leaving it and its slot alone")
    run = json.loads((out / "lab-run.json").read_text(encoding="utf-8")) if (out / "lab-run.json").exists() else {}
    report["lab_run"] = {k: run.get(k) for k in ("tripped", "max_job_audio_peak", "left_in_job", "exit_code") if k in run}
    (out / "probe-report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    passed = sum(1 for ch in report["checks"] if ch["ok"])
    log(f"{passed} of {len(report['checks'])} checks passed; error: {report['error']}; lab run {report['lab_run']}")
    return 0 if report["error"] is None and passed == len(report["checks"]) else 1


if __name__ == "__main__":
    sys.exit(main())
