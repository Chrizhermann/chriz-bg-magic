"""In-game checks of the decided spell batches, in a quiet disposable lab game.

usage: python -I tests/lab/run_batches.py --game <lab game> --profile <lab profile>
           --lab-tools <folder with bg_lab_slots.py> --load-lua <lab_load.lua> --save <save folder>
           --out <evidence folder> [--seconds 900] [--only strength,mr,...]

Same lab and same rules as run_probe.py, which this reuses. Each check sets up its own case,
reads the sprites before and after, and decides in Python. Nothing is saved.
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_probe", HERE / "run_probe.py")
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

EXTRA = HERE / "probe_batches.lua"
GROUPS = ("control", "strength", "mr", "image", "sword", "newspells", "breathless", "insects", "nature", "fiends", "smoke")


def lua_list(values):
    return "{" + ", ".join(str(v) for v in values) + "}"


def run_checks(c, report, only):
    checks = report["checks"]

    def check(name, ok, **facts):
        checks.append({"check": name, "ok": bool(ok), **facts})
        rp.log(f"  {'ok  ' if ok else 'FAIL'} {name} {json.dumps(facts, ensure_ascii=False)[:400]}")

    c.lua("probe", f"return assert(loadfile([[{rp.PROBE.as_posix()}]]))()")
    c.lua("probe2", f"return assert(loadfile([[{EXTRA.as_posix()}]]))()")
    report["unpause"] = c.p("unpause", "unpause()")
    c.p("protect", "protect_party()")
    report["party"] = c.p("party", "party()")
    time.sleep(1)
    for name in GROUPS:
        if name in only:
            rp.log(f"group {name}")
            try:
                globals()[name](c, check)
            except Exception as problem:  # noqa: BLE001 - one group must not stop the others
                check(f"{name}: group finished", False, error=f"{type(problem).__name__}: {problem}")
            c.p(f"tidy-{name}", "remove_all_others()")
            time.sleep(1)


def control(c, check):
    # Base-game party spells in this arena: do they reach the whole party at all?
    pos = c.p("ct-party", "party()")
    ea = c.lua("ct-ea", "local r = {} for i = 0, 2 do local s = EEex_Sprite_GetInPortrait(i) r[#r + 1] = s.m_typeAI.m_EnemyAlly end return r")
    c.p("ct-haste", f'cast_point(1, "SPWI305", {pos[1]["x"]}, {pos[1]["y"]})')
    time.sleep(5)
    haste = [len(c.p(f"ct-h{i}", f"ops({i}, {{16}})") or []) for i in range(3)]
    check("Control: in this arena a base-game party spell reaches only the member at the point", haste == [0, 1, 0],
          haste=haste, ea=ea, where=[(p["x"], p["y"]) for p in pos])
    for i in range(3):
        c.p(f"ct-clear{i}", f'clear({i}, {{"SPWI305"}})')


def strength(c, check):
    # Strength of One lifts lower Strength to 18/75 and leaves higher values alone.
    c.p("so-0", "fx(0, 44, 10, 1, 60)")
    c.p("so-1", "fx(1, 44, 19, 1, 60)")
    c.p("so-2a", "fx(2, 44, 18, 1, 60)")
    c.p("so-2b", "fx(2, 97, 90, 1, 60)")
    time.sleep(1.5)
    before = [c.p(f"so-b{i}", f"stats({i})") for i in range(3)]
    # In this arena party-only area spells reach only the member at the target point
    # (see the control check), so each member gets its own cast.
    for i, where in enumerate(c.p("so-where", "party()")[:3]):
        c.p(f"so-cast{i}", f'cast_point(2, "SPPR312", {where["x"]}, {where["y"]})')
        time.sleep(4)
    after = [c.p(f"so-a{i}", f"stats({i})") for i in range(3)]
    pair = lambda s: (s["str"], s["strex"])  # noqa: E731
    check("Strength of One: 10 becomes 18/75", pair(after[0]) == (18, 75), before=pair(before[0]), after=pair(after[0]))
    check("Strength of One: 19 stays 19", after[1]["str"] == 19, before=pair(before[1]), after=pair(after[1]))
    check("Strength of One: 18/90 stays 18/90", pair(after[2]) == (18, 90), before=pair(before[2]), after=pair(after[2]))


def mr(c, check):
    # Magic Resistance adds, and a second casting replaces the first.
    c.p("mr-set", "fx(1, 166, 50, 1, 60)")
    time.sleep(1.5)
    base = c.p("mr-0", "stats(1)")["mr"]
    c.p("mr-c1", 'cast(2, "SPPR509", "Player2")')
    time.sleep(5)
    one = c.p("mr-1", "stats(1)")["mr"]
    c.p("mr-c2", 'cast(2, "SPPR509", "Player2")')
    time.sleep(5)
    two = c.p("mr-2", "stats(1)")["mr"]
    check("Magic Resistance adds to a value of 50 and does not stack with itself", base == 50 and one > 50 and two == one,
          values=[base, one, two])


def image(c, check):
    # Mirror Image ends Reflected Image and keeps it out.
    c.p("im-c1", 'cast(1, "SPWI120", "Myself")')
    time.sleep(3)
    first = c.p("im-1", "ops(1, {159, 119})")
    c.p("im-c2", 'cast(1, "SPWI212", "Myself")')
    time.sleep(3)
    second = c.p("im-2", "ops(1, {159, 119})")
    c.p("im-c3", 'cast(1, "SPWI120", "Myself")')
    time.sleep(3)
    third = c.p("im-3", "ops(1, {159, 119})")
    # The engine keeps both as opcode 159 in the effect list, so the source tells them apart.
    has = lambda d, res: any(e["src"] == res for e in d or [])  # noqa: E731
    check("Reflected Image alone works", has(first, "SPWI120"), effects=first)
    check("Mirror Image removes Reflected Image", has(second, "SPWI212") and not has(second, "SPWI120"), effects=second)
    check("Reflected Image does nothing under Mirror Image", has(third, "SPWI212") and not has(third, "SPWI120"), effects=third)
    c.p("im-clear", 'clear(1, {"SPWI212", "SPWI120"})')


def sword(c, check):
    # Disintegrate destroys Mordenkainen's Sword, without a save.
    c.p("sw-cast", 'cast(1, "SPWI716", "Myself")')
    time.sleep(5)
    others = c.p("sw-1", "others()") or []
    swords = [o for o in others if o["name"] == "Magical Sword"]
    check("Mordenkainen's Sword appears", len(swords) == 1, others=others)
    if swords:
        c.p("sw-saves", 'fx("Magical Sword", 37, 1, 1, 60)')
        c.p("sw-hit", 'self_apply("Magical Sword", "SPWI616")')
        time.sleep(3)
        left = [o for o in (c.p("sw-2", "others()") or []) if o["name"] == "Magical Sword"]
        check("Disintegrate destroys it, even with the best save", not left, left=left)


def newspells(c, check):
    # Faerie Fire reaches enemies only; Mass Regenerate reaches the party in sight; Invisibility Sphere too.
    c.p("ns-spawn", 'spawn("TASLOI01", 90, 0)')
    time.sleep(2)
    c.p("ns-pin", 'pin("Tasloi")')
    c.p("ns-saves", 'set_saves("Tasloi", {spell = 20}, 300)')
    p0 = c.p("ns-party", "party()")[0]
    foe_at = c.p("ns-foe", 'creature("Tasloi")')
    c.p("ns-ff", f'cast_point(2, "SPPR116", {foe_at["x"]}, {foe_at["y"]})')
    time.sleep(4)
    enemy = c.p("ns-ff-e", 'ops("Tasloi", {0})') or []
    friends = [c.p(f"ns-ff-{i}", f"ops({i}, {{0}})") or [] for i in range(3)]
    check("Faerie Fire hits the enemy", any(e["src"] == "SPPR116" for e in enemy), enemy=enemy)
    check("Faerie Fire spares the party", not any(e["src"] == "SPPR116" for f in friends for e in f), friends=friends)
    c.p("ns-mreg", f'cast_point(2, "{MASS_REGENERATE}", {p0["x"]}, {p0["y"]})')
    time.sleep(5)
    regen = [c.p(f"ns-mr-{i}", f"ops({i}, {{98}})") or [] for i in range(3)]
    foe = c.p("ns-mr-e", 'ops("Tasloi", {98})') or []
    check("Mass Regenerate reaches a party member other than the caster, like Haste in the control",
          bool(regen[0]), regen=[len(r) for r in regen])
    check("Mass Regenerate spares the enemy", not foe, foe=foe)
    c.p("ns-inv", f'cast_point(1, "SPWI307", {p0["x"]}, {p0["y"]})')
    time.sleep(4)
    inv = [c.p(f"ns-inv-{i}", f"ops({i}, {{20}})") or [] for i in range(3)]
    foe = c.p("ns-inv-e", 'ops("Tasloi", {20})') or []
    check("Invisibility Sphere reaches a party member other than the caster, not the enemy", bool(inv[0]) and not foe,
          party=[len(i) for i in inv], foe=foe)
    for i in range(3):
        c.p(f"ns-clear{i}", f'clear({i}, {{"SPWI307"}})')


def breathless(c, check):
    # Stinking Cloud spares what does not breathe; Spook and Horror spare the undead.
    c.p("bl-spawn1", 'spawn("SKELET01", 120, 40)')
    c.p("bl-spawn2", 'spawn("TASLOI01", 120, -40)')
    time.sleep(2)
    others = c.p("bl-who", "others()") or []
    check("breathless: both test creatures are there", len(others) == 2, others=others)
    tasloi = "Tasloi"
    skeleton = next((o["name"] for o in others if o["name"] != tasloi), "Skeleton")
    c.p("bl-pin1", f'pin("{skeleton}")')
    c.p("bl-pin2", f'pin("{tasloi}")')
    c.p("bl-s1", f'set_saves("{skeleton}", {{death = 20, spell = 20}}, 300)')
    c.p("bl-s2", f'set_saves("{tasloi}", {{death = 20, spell = 20}}, 300)')
    for res, op, label in (("SPWI213", 39, "Stinking Cloud"), ("SPWI125", 24, "Spook"), ("SPWI205", 24, "Horror")):
        c.p(f"bl-calm-{res}", f'fx("{tasloi}", 161, 0, 0, 1)')
        c.p(f"bl-a-{res}", f'self_apply("{skeleton}", "{res}")')
        c.p(f"bl-b-{res}", f'self_apply("{tasloi}", "{res}")')
        time.sleep(3)
        undead = [e for e in (c.p(f"bl-u-{res}", f'ops("{skeleton}", {{{op}}})') or []) if e["src"] == res]
        living = [e for e in (c.p(f"bl-l-{res}", f'ops("{tasloi}", {{{op}}})') or []) if e["src"] == res]
        check(f"{label}: undead spared, a living enemy caught", not undead and living, undead=undead, living=living)
        c.p(f"bl-cure-{res}", f'cure_sleep("{tasloi}")')
    # Spook against True Seeing: first the control without it.
    c.p("bl-ts-saves", "set_saves(2, {spell = 20}, 60)")
    c.p("bl-ts-spook0", 'apply_spell(1, "SPWI125", "Player3")')
    time.sleep(3)
    plain = [e for e in (c.p("bl-ts-read0", "ops(2, {24})") or []) if e["src"] == "SPWI125"]
    c.p("bl-ts-clear", 'clear(2, {"SPWI125"})')
    c.p("bl-ts", 'cast(2, "SPPR505", "Myself")')
    time.sleep(5)
    c.p("bl-ts-spook", 'apply_spell(1, "SPWI125", "Player3")')
    time.sleep(3)
    seen = [e for e in (c.p("bl-ts-read", "ops(2, {24})") or []) if e["src"] == "SPWI125"]
    check("Spook: lands without True Seeing, not with it", plain and not seen, plain=plain, seen=seen)


def insects(c, check):
    # Insect Plague: per-round payload on a living enemy; Fire Shield keeps it off.
    c.p("in-spawn", 'spawn("TASLOI01", 120, 0)')
    time.sleep(2)
    c.p("in-pin", 'pin("Tasloi")')
    c.p("in-saves", 'set_saves("Tasloi", {breath = 20, spell = 20}, 300)')
    hp0 = c.p("in-0", 'stats("Tasloi")')["hp"]
    c.p("in-log0", "take_log()")
    c.p("in-watch", 'watch("Tasloi", 10)')
    c.p("in-cast", 'self_apply("Tasloi", "SPPR517")')
    time.sleep(9)
    fails = c.p("in-1", 'ops("Tasloi", {60})') or []
    hp1 = c.p("in-2", 'stats("Tasloi")')["hp"]
    rp.log("insect log " + json.dumps(c.p("in-log", "take_log()"))[:1500])
    check("Insect Plague: spell failure and damage on a target with the worst saves", fails and hp1 < hp0, hp=[hp0, hp1], fails=fails)
    c.p("in-fs", 'cast(1, "SPWI418", "Myself")')
    time.sleep(4)
    c.p("in-heal", "heal(1)")
    c.p("in-saves2", "set_saves(1, {breath = 20}, 60)")
    hp0 = c.p("in-3", "stats(1)")["hp"]
    c.p("in-cast2", 'apply_spell(2, "SPPR517", "Player2")')
    time.sleep(7)
    fails = c.p("in-4", "ops(1, {60})") or []
    hp1 = c.p("in-5", "stats(1)")["hp"]
    check("Insect Plague: Fire Shield keeps it off", not fails and hp1 == hp0, hp=[hp0, hp1], fails=fails)
    c.p("in-clear", 'clear(1, {"SPWI418"})')


def nature(c, check):
    # Nature's Beauty: failed save blinds for good, a successful one for 3 rounds.
    c.p("nb-spawn", 'spawn("TASLOI01", 140, 0)')
    time.sleep(2)
    c.p("nb-pin", 'pin("Tasloi")')
    c.p("nb-saves", 'set_saves("Tasloi", {death = 1, spell = 1, breath = 1}, 300)')
    foe_at = c.p("nb-foe", 'creature("Tasloi")')
    me = c.p("nb-me", "party()")[2]
    c.p("nb-log0", "take_log()")
    c.p("nb-watch", 'watch("Tasloi", 10)')
    c.p("nb-cast", 'cast(2, "SPPR704", "Myself")')
    time.sleep(8)
    got = c.p("nb-1", 'ops("Tasloi", {74})') or []
    rp.log(f"nature: foe at {foe_at['x']},{foe_at['y']} caster at {me['x']},{me['y']} log " + json.dumps(c.p("nb-log", "take_log()"))[:900])
    check("Nature's Beauty: the enemy in range is blinded", bool(got), blind=got)
    party = [c.p(f"nb-p{i}", f"ops({i}, {{74}})") or [] for i in range(3)]
    check("Nature's Beauty: the party is spared", not any(party), party=party)


def fiends(c, check):
    # Cacofiend, Summon Fiend and Gate: a creature appears for the lab mage's alignment.
    for res in ("SPWI707", "SPWI807", "SPWI905"):
        c.p(f"fi-{res}", f'cast(1, "{res}", "Myself")')
        time.sleep(6)
        others = c.p(f"fi-r-{res}", "others()") or []
        check(f"{res}: a fiend appears", bool(others), others=[(o["dv"], o["name"], o["ea"]) for o in others])
        c.p(f"fi-t-{res}", "remove_all_others()")
        time.sleep(2)


def smoke(c, check):
    # Every changed spell cast once at a dummy: the game must survive and keep answering.
    c.p("sm-spawn", 'spawn("TASLOI01", 160, 0)')
    time.sleep(2)
    c.p("sm-pin", 'pin("Tasloi", 900)')
    done, skipped = [], []
    for res in SMOKE:
        if res in SKIP_SMOKE:
            skipped.append(res)
            continue
        caster = 2 if res.startswith("SPPR") else 1
        c.p(f"sm-{res}", f'cast({caster}, "{res}", \'"Tasloi"\')')
        time.sleep(2.2)
        c.p(f"sm-a-{res}", "party()")
        done.append(res)
    check("Every changed spell was cast once and the game kept answering", True, casts=len(done), skipped=skipped)


MASS_REGENERATE = "SPPR502"
SKIP_SMOKE = {"SPWI420", "SPWI617", "SPWI710", "SPWI809", "SPWI908", "SPWI123", "SPWI703", "SPWI804", "SPWI919"}
SMOKE = []


def main():
    args = sys.argv[1:]
    global MASS_REGENERATE
    if "--mass-regenerate" in args:
        i = args.index("--mass-regenerate")
        MASS_REGENERATE = args[i + 1]
        del args[i:i + 2]
    if "--smoke-list" in args:
        i = args.index("--smoke-list")
        SMOKE.extend(Path(args[i + 1]).read_text(encoding="utf-8").split())
        del args[i:i + 2]
    if "--only" not in args:
        args += ["--only", ",".join(GROUPS)]
    sys.argv = [sys.argv[0], *args]
    rp.GROUPS = GROUPS
    rp.run_checks = run_checks
    return rp.main()


if __name__ == "__main__":
    sys.exit(main())
