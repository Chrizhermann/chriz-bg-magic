"""In-game checks of the decided spell batches, in a quiet disposable lab game.

usage: python -I tests/lab/run_batches.py --game <lab game> --profile <lab profile>
           --lab-tools <folder with bg_lab_slots.py> --load-lua <lab_load.lua> --save <save folder>
           --out <evidence folder> [--seconds 900] [--only strength,mr,...]

Same lab and same rules as run_probe.py, which this reuses. Each check sets up its own case,
reads the sprites before and after, and decides in Python. Nothing is saved.
"""
import importlib.util
import json
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_probe", HERE / "run_probe.py")
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

EXTRA = HERE / "probe_batches.lua"
GROUPS = ("haste", "curse", "control", "strength", "mr", "image", "sword", "newspells", "breathless", "insects", "nature", "fiends", "sequencer", "record", "live", "bonus", "smoke")


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
                if name == "bonus":
                    bonus(c, check, report)
                else:
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


def curse(c, check):
    # Doom's penalties sit in the spell, Unholy Blight's arrive through EFF wrappers (opcode 177,
    # good targets only): both are Curse, so only the worst counts, also through a wrapper.
    c.p("cu-spawn", 'spawn("ACOLYTE2", 120, 0)')
    time.sleep(2)
    others = c.p("cu-who", "others()") or []
    who = others[0]["name"] if others else "Dawnbringer Alvanna"
    c.p("cu-pin", f'pin("{who}")')
    c.p("cu-saves", f'set_saves("{who}", {{spell = 20, death = 20, breath = 20}}, 120)')
    time.sleep(1)
    base = c.p("cu-0", f'stats("{who}")')["thac0"]
    c.p("cu-blight", f'self_apply("{who}", "SPPR314")')
    time.sleep(3)
    blight = c.p("cu-1", f'stats("{who}")')["thac0"]
    check("Unholy Blight lands on someone good, through its wrappers", blight == base + 2, who=who, values=[base, blight])
    c.p("cu-doom", f'self_apply("{who}", "SPPR113")')
    time.sleep(3)
    both = c.p("cu-2", f'stats("{who}")')["thac0"]
    check("Doom on top of Unholy Blight: only the worst counts", both == blight, values=[base, blight, both])


def haste(c, check):
    # Haste and Slow cancel each other; Improved Haste works on the slowed, ends Slow, keeps it out.
    state = lambda d: sorted({e["op"] for e in d or []})  # noqa: E731
    c.p("ha-saves", "set_saves(0, {spell = 20, breath = 20, death = 20}, 300)")
    c.p("ha-slow", 'apply_spell(1, "SPWI312", "Player1")')
    time.sleep(3)
    slowed = c.p("ha-1", "ops(0, {16, 40})")
    check("Slow lands", 40 in state(slowed), effects=slowed)
    c.p("ha-haste", 'apply_spell(1, "SPWI305", "Player1")')
    time.sleep(3)
    after = c.p("ha-2", "ops(0, {16, 40})")
    check("Haste on a slowed target: both gone", not after, effects=after)
    c.p("ha-haste2", 'apply_spell(1, "SPWI305", "Player1")')
    time.sleep(3)
    hasted = c.p("ha-3", "ops(0, {16, 40})")
    check("Haste lands on a free target", 16 in state(hasted), effects=hasted)
    c.p("ha-slow2", 'apply_spell(1, "SPWI312", "Player1")')
    time.sleep(3)
    after = c.p("ha-4", "ops(0, {16, 40})")
    check("Slow on a hasted target: both gone", not after, effects=after)
    c.p("ha-slow3", 'apply_spell(1, "SPWI312", "Player1")')
    time.sleep(3)
    before = c.p("ha-5", "stats(0)")
    c.p("ha-ih", 'apply_spell(1, "SPWI613", "Player1")')
    time.sleep(3)
    improved = c.p("ha-6", "ops(0, {16, 40, 1, 176})")
    stats = c.p("ha-7", "stats(0)")
    check("Improved Haste ends Slow, without the Haste opcode", 40 not in state(improved) and 16 not in state(improved)
          and 1 in state(improved), effects=improved, before=before, after=stats)
    c.p("ha-slow4", 'apply_spell(1, "SPWI312", "Player1")')
    time.sleep(3)
    held = c.p("ha-8", "ops(0, {40})")
    check("Improved Haste keeps Slow out", not held, effects=held)
    c.p("ha-end", 'clear(0, {"SPWI613", "SPWI312", "SPWI305"})')


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
    # Nature's Beauty, on the target directly (this arena's area delivery: see the control):
    # made save: alive, blind for 3 rounds. Failed save: humanoids die, everyone blind for good.
    c.p("nb-spawn", 'spawn("TASLOI01", 140, 0)')
    time.sleep(2)
    c.p("nb-pin", 'pin("Tasloi")')
    c.p("nb-saves", 'set_saves("Tasloi", {spell = 1}, 300)')
    c.p("nb-a", 'self_apply("Tasloi", "CBMGNB1")')
    time.sleep(3)
    made = c.p("nb-1", 'ops("Tasloi", {74})') or []
    alive = [o for o in (c.p("nb-2", "others()") or []) if o["name"] == "Tasloi" and o["hp"] > 0]
    check("Nature's Beauty, made save: blind, not for good, alive", len(made) == 1 and alive, blind=made)
    c.p("nb-tidy", "remove_all_others()")
    time.sleep(1)
    c.p("nb-spawn2", 'spawn("SPIDHU01", 140, 0)')
    time.sleep(2)
    c.p("nb-pin2", 'pin("spidhu01")')
    c.p("nb-saves2", 'set_saves("spidhu01", {spell = 20}, 300)')
    c.p("nb-b", 'self_apply("spidhu01", "CBMGNB1")')
    time.sleep(3)
    failed = c.p("nb-3", 'ops("spidhu01", {74})') or []
    check("Nature's Beauty, failed save on a non-humanoid: blind once, longer than the made-save case",
          len(failed) == 1 and made and failed[0]["dur"] > made[0]["dur"] + 1000, blind=failed)
    c.p("nb-tidy2", "remove_all_others()")
    time.sleep(1)
    c.p("nb-spawn3", 'spawn("TASLOI01", 140, 0)')
    time.sleep(2)
    c.p("nb-saves3", 'set_saves("Tasloi", {spell = 20}, 300)')
    c.p("nb-hold", 'fx("Tasloi", 109, 0, 2, 60)')
    c.p("nb-c", 'self_apply("Tasloi", "CBMGNB1")')
    time.sleep(3)
    left = [o for o in (c.p("nb-4", "others()") or []) if o["name"] == "Tasloi" and o["hp"] > 0]
    check("Nature's Beauty, failed save on a humanoid: dead", not left, left=left)


def fiends(c, check):
    # Cacofiend, Summon Fiend and Gate: a creature appears for the lab mage's alignment.
    for res in ("SPWI707", "SPWI807", "SPWI905"):
        c.p(f"fi-{res}", f'cast(1, "{res}", "Myself")')
        time.sleep(6)
        others = c.p(f"fi-r-{res}", "others()") or []
        check(f"{res}: a fiend appears", bool(others), others=[(o["dv"], o["name"], o["ea"]) for o in others])
        c.p(f"fi-t-{res}", "remove_all_others()")
        time.sleep(2)
    # No fight check: spawned creatures do not act in this arena, the base game's Pit Fiend
    # (DEMPIT, whose script turns hostile on sight) stayed idle for 20 s just like ours.


def sequencer(c, check):
    # The screen swaps a spell for the rows of the 2DA of the same name: one row, one entry.
    c.p("sq-console", "book_console()")
    c.p("sq-open", 'apply_spell(1, "SPWI809", "Player2")')
    time.sleep(4)
    book = c.p("sq-book", "book_list(5)")
    screens = [r for r in book["rows"] if r["name"] == "Dispelling Screen"]
    check("Spell Trigger lists Dispelling Screen once, with its own icon and description",
          book["screen"] == "SPWI809" and len(screens) == 1 and screens[0]["res"] == "SPWI510"
          and screens[0]["icon"] == "SPWI510C" and screens[0]["desc"] > 0, book=book)
    check("No school choices are left", not [r for r in book["rows"] if r["res"].startswith("SPWI59")], rows=book["rows"])
    picked = c.p("sq-pick", 'book_pick({{"SPWI510", "SPWI510"}, {"SPWI510", "SPWI510"}, {"SPWI511", ""}})')
    check("It can be chosen", picked == 3, picked=picked)
    c.p("sq-done", "book_done()")
    time.sleep(2)
    c.p("sq-fire", 'force(1, "SPWI809D")')
    time.sleep(9)
    landed = c.p("sq-landed", "ops(1, {101, 142, 206})")
    from_screen = [e for e in landed if e["src"] == "SPWI510"]
    check("The trigger releases it: Dispel protection and its own effect-list row", {101, 142, 206} <= {e["op"] for e in from_screen},
          effects=from_screen)
    c.p("sq-end", 'clear(1, {"SPWI510", "SPWI511"})')


RECORD = {}


def record_rows(game):
    """Row label to text, from the installed STATDESC.2DA."""
    spec = importlib.util.spec_from_file_location("record_ie", HERE.parent / "ie.py")
    ie = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ie)
    game = ie.Game(game)
    for line in game.get("STATDESC", "2DA").decode("latin-1").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].isdigit():
            RECORD[int(parts[0])] = game.tlk(int(parts[1]))


def record(c, check):
    # What the character record lists, on a fresh dummy per case: the sprite's portrait icons.
    def fresh(save):
        c.p("rc-spawn", 'spawn("TASLOI01", 160, 0)')
        time.sleep(1.1)
        c.lua("rc-prep", f'CBMP.set_saves("Tasloi", {{spell = {save}, breath = {save}, death = {save}}}, 120) '
                         'CBMP.fx("Tasloi", 208, 1, 0, 120) return true')

    def apply(res, wait=1.6):
        c.p(f"rc-{res}", f'self_apply("Tasloi", "{res}")')
        time.sleep(wait)

    def shown():
        return sorted(RECORD.get(row, str(row)) for row in c.p("rc-rows", 'icons("Tasloi")') or [])

    def done():
        c.p("rc-tidy", "remove_all_others()")
        time.sleep(0.8)

    fresh(20)
    apply("SPPR116")
    rows = shown()
    check("Faerie Fire is listed on a failed save", "Faerie Fire" in rows, rows=rows)
    done()
    fresh(1)
    apply("SPPR116")
    rows = shown()
    check("Faerie Fire is not listed on a made save", "Faerie Fire" not in rows, rows=rows)
    done()
    for res in ("SPPR319", "SPPR517", "SPPR717"):
        fresh(20)
        apply(res)
        rows = shown()
        check(f"{res}: a failed save lists the swarm and the spell failure",
              "Insect Swarm" in rows and "Spell Failure" in rows, rows=rows)
        done()
        # The best save the stat holds is 0 (a negative value wraps to the worst one), and these
        # saves carry -2, so one roll in twenty still fails: a few tries settle it.
        for attempt in range(4):
            fresh(0)
            apply(res)
            rows = shown()
            done()
            # Only Summon Insects has a save against the whole swarm.
            made = not rows if res == "SPPR319" else (
                "Insect Swarm" in rows and "Spell Failure" not in rows and "Panic" not in rows)
            if made:
                break
        check(f"{res}: a made save lists the swarm only, or nothing for a save against all of it", made,
              rows=rows, attempts=attempt + 1)
    fresh(20)
    apply("SPPR412")
    rows = shown()
    check("Divine Power is listed by its name", "Divine Power" in rows and "Holy Power" not in rows, rows=rows)
    done()
    fresh(20)
    apply("SPWI608")
    effects = c.p("rc-pierce", 'ops("Tasloi", {142, 166})') or []
    icon = [e["dur"] for e in effects if e["op"] == 142 and e["p2"] == 106]
    lowered = [e["dur"] for e in effects if e["op"] == 166]
    check("Pierce Magic: the entry ends with the lowered resistance",
          icon and lowered and abs(icon[0] - lowered[0]) <= 45, effects=effects)
    done()
    fresh(20)
    apply("SPWI411")
    rows = shown()
    check("Hopelessness: one entry for the sleeper", "Hopelessness" in rows and "Sleep" not in rows, rows=rows)
    c.p("rc-wake", 'damage("Tasloi", 1)')
    time.sleep(1.5)
    rows = shown()
    check("Hopelessness: the entry goes when the target wakes", "Hopelessness" not in rows, rows=rows)
    done()
    fresh(20)
    c.p("rc-immune", 'fx("Tasloi", 101, 0, 39, 60)')
    time.sleep(0.5)
    apply("SPWI411")
    rows = shown()
    check("Hopelessness: no entry on a creature immune to sleep", "Hopelessness" not in rows, rows=rows)
    done()
    fresh(20)
    c.p("rc-strong", 'fx("Tasloi", 44, 19, 1, 60)')
    time.sleep(0.5)
    apply("SPPR312")
    left_out = c.p("rc-strength", 'ops("Tasloi", {328})') or []
    rows = shown()
    check("Strength of One: who is left out gets neither entry nor spell state", "Strength" not in rows and not left_out,
          rows=rows, effects=left_out)
    done()
    stale = {"Feebleminded", "Confused", "Rigid Thinking", "Chaos", "Nauseated", "Decaying", "Poisoned"}
    for res in ("SPWI509", "SPWI401", "SPPR311", "SPWI508", "SPWI213", "SPPR610"):
        fresh(20)
        apply(res, 1.4)
        before = shown()
        apply("SPPR713", 1.8)
        rows = shown()
        check(f"Greater Restoration clears the entries of {res}", (set(before) & stale) and not (set(rows) & stale),
              before=before, after=rows)
        done()


def live(c, check):
    # Entries that follow a state, on party members: only they have a record.
    def shown(who):
        return sorted(RECORD.get(row, str(row)) for row in c.p("lv-rows", f"icons({who})") or [])

    def wait(seconds=1.6):
        time.sleep(seconds)

    def apply(res, target=1):
        c.p(f"lv-{res}", f'apply_spell(1, "{res}", "Player{target}")')
        wait()

    def clear(who, *resources):
        c.p("lv-clear", f"clear({who}, {{{', '.join(repr(r).replace(chr(39), chr(34)) for r in resources)}}})")
        wait()

    for res, name, other in (("SPWI206", "Invisible", "Improved Invisibility"), ("SPWI405", "Improved Invisibility", "Invisible")):
        apply(res)
        rows = shown(0)
        check(f"{name} is listed, once", name in rows and other not in rows, rows=rows)
        clear(0, res)
        rows = shown(0)
        check(f"{name} goes with the state", name not in rows, rows=rows)
    c.p("lv-potion", "fx(0, 20, 0, 0, 30)")
    wait()
    rows = shown(0)
    check("Any source of invisibility counts, not only spells", "Invisible" in rows, rows=rows)
    c.lua("lv-visible", "EEex_GameObject_ApplyEffect(EEex_Sprite_GetInPortrait(0), { effectID = 116, durationType = 1, "
                        "sourceID = EEex_Sprite_GetInPortrait(0).m_id, sourceTarget = EEex_Sprite_GetInPortrait(0).m_id }) return true")
    wait()
    rows = shown(0)
    check("Revealed: the entry goes", "Invisible" not in rows, rows=rows)

    apply("SPPR109", 2)
    rows = shown(1)
    check("Sanctuary is listed", "Sanctuary" in rows, rows=rows)
    clear(1, "SPPR109")
    rows = shown(1)
    check("Sanctuary goes with the state", "Sanctuary" not in rows, rows=rows)

    apply("SPWI212", 2)
    rows = shown(1)
    check("Mirror Image is listed", "Mirror Image" in rows and "Reflected Image" not in rows, rows=rows)
    clear(1, "SPWI212")
    rows = shown(1)
    check("Mirror Image goes with the images", "Mirror Image" not in rows, rows=rows)
    apply("SPWI120", 2)
    rows = shown(1)
    check("Reflected Image is listed", "Reflected Image" in rows and "Mirror Image" not in rows, rows=rows)
    # A missile finds the image or the character at random.
    for attempt in range(6):
        c.p("lv-missile", 'cast(2, "SPWI112", "Player2")')
        wait(4)
        rows = shown(1)
        if "Reflected Image" not in rows:
            break
    check("A hit on the image ends the entry", "Reflected Image" not in rows, rows=rows, missiles=attempt + 1)
    clear(1, "SPWI120")

    apply("SPPR701", 2)
    rows = shown(1)
    check("Shield of the Archons shows its own name", "Shield of the Archons" in rows and "Spell Deflection" not in rows, rows=rows)
    c.p("lv-record", "record_open()")
    wait()
    record = c.p("lv-record-read", "record_read()") or []
    wait()
    check("The Record itself says so, with the spell's icon", [r for r in record if r["text"] == "Shield of the Archons"
                                                               and r["bam"] == "STATES" and r["current"] == 181], record=record)
    c.p("lv-spend", "spend(1, 201, 1)")
    c.p("lv-missile2", 'cast(2, "SPWI112", "Player2")')
    wait(5)
    rows = shown(1)
    check("Spent, the entry goes", "Shield of the Archons" not in rows and "Spell Deflection" not in rows, rows=rows)
    clear(1, "SPPR701")

    apply("SPWI318", 2)
    rows = shown(1)
    check("Minor Spell Deflection shows its own name", "Minor Spell Deflection" in rows and "Spell Deflection" not in rows, rows=rows)
    apply("SPWI618", 2)
    clear(1, "SPWI318")
    wait()
    rows = shown(1)
    check("The real Spell Deflection shows again after the minor one", "Spell Deflection" in rows
          and "Minor Spell Deflection" not in rows, rows=rows)
    clear(1, "SPWI618")
    rows = shown(1)
    check("Nothing stays", "Spell Deflection" not in rows, rows=rows)

    apply("SPWI522", 2)
    rows = shown(1)
    check("Minor Spell Turning shows its own name", "Minor Spell Turning" in rows and "Spell Turning" not in rows, rows=rows)
    clear(1, "SPWI522")
    rows = shown(1)
    check("Minor Spell Turning goes", "Minor Spell Turning" not in rows, rows=rows)

    c.p("lv-spawn", 'spawn("TASLOI01", 160, 0)')
    wait(1.2)
    c.p("lv-dummy", 'self_apply("Tasloi", "SPWI206")')
    wait()
    rows = c.p("lv-dummy-rows", 'icons("Tasloi")') or []
    check("No entry for who has no record", not rows, rows=rows)


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


BONUS_SYMBOLS = {
    "bless": "CLERIC_BLESS", "prayer": "CLERIC_PRAYER", "recitation": "CLERIC_RECITATION",
    "hope": "WIZARD_EMOTION_HOPE", "luck": "WIZARD_LUCK", "doom": "CLERIC_DOOM",
    "curse": "CLERIC_CURSE", "pierce": "WIZARD_PIERCE_MAGIC",
    "tenser": "WIZARD_TENSERS_TRANSFORMATION", "divine": "CLERIC_HOLY_POWER",
    "righteous": "CLERIC_RIGHTEOUS_MAGIC", "champion": "CLERIC_CHAMPIONS_STRENGTH",
    "blood": "CLERIC_BLOOD_RAGE", "animal": "CLERIC_ANIMAL_RAGE",
    "regenerate": "CLERIC_REGENERATE", "mass": "CLERIC_CBMAGIC_MASS_REGENERATE",
    "troll": "WIZARD_TROLLISH_FORTITUDE",
}
BONUS = {}
# Mechanical payloads used to establish that a family member actually took effect.
# Icons, spell states, exclusions, delayed expiry sounds and visuals are not evidence.
BONUS_PAYLOAD_OPS = {
    "tenser": {0, 1, 18, 33, 34, 35, 36, 37, 44, 54, 73, 97},
    "divine": {18, 44, 54, 97}, "righteous": {18, 44, 285},
    "champion": {44, 54, 132}, "blood": {3, 18, 54, 73}, "animal": {3, 18, 44, 73},
    "regenerate": {98}, "mass": {98}, "troll": {98}, "pierce": {166, 402},
}
BONUS_TYPED_OPS = {0, 22, 33, 34, 35, 36, 37, 54, 73, 130, 131, 133, 137, 325}


def bonus_resources(game):
    """Read installed symbols and payload ownership; never assume IWD spell slots."""
    spec = importlib.util.spec_from_file_location("bonus_ie", HERE.parent / "ie.py")
    ie = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ie)
    game = ie.Game(game)

    def ids(resource):
        result = {}
        for line in (game.get(resource, "IDS") or b"").decode("latin-1").splitlines():
            parts = line.split()
            if len(parts) >= 2:
                try:
                    result[parts[1].upper()] = int(parts[0], 16 if parts[0].lower().startswith("0x") else 10)
                except ValueError:
                    pass
        return result

    def sources(root, key):
        seen, payload, pending = set(), {root}, [(root, "SPL", ())]
        meaningful = BONUS_PAYLOAD_OPS.get(key, BONUS_TYPED_OPS)
        while pending:
            res, kind, ancestors = pending.pop()
            if (res, kind) in seen:
                continue
            if len(seen) >= 128:
                raise ValueError(f"bonus probe: delivery chain exceeds 128 resources for {root}")
            seen.add((res, kind))
            path = (*ancestors, res)
            data = game.get(res, kind)
            if not data:
                raise ValueError(f"bonus probe: missing delivery {res}.{kind}")
            if kind == "SPL":
                spl = ie.parse_spl(data)
                effects = spl["casting"] + [e for a in spl["abilities"] for e in a["effects"]]
            else:
                if len(data) < 0x110 or data[:8] != b"EFF V2.0":
                    raise ValueError(f"bonus probe: malformed {res}.EFF")
                effects = [{"opcode": struct.unpack_from("<I", data, 0x10)[0],
                            "resource": data[0x30:0x38].split(b"\0", 1)[0].decode("ascii").upper()}]
            for e in effects:
                if e["opcode"] in meaningful:
                    payload.update(path)
                child = e["resource"]
                if child and e["opcode"] in (146, 148, 326):
                    pending.append((child, "SPL", path))
                elif child and e["opcode"] in (177, 183, 272):
                    pending.append((child, "EFF", path))
        return sorted({res for res, _ in seen}), sorted(payload)

    spells, result = ids("SPELL"), {"typed_state": ids("SPLSTATE").get("CBM_BONUS_TYPED")}
    for key, symbol in BONUS_SYMBOLS.items():
        number = spells.get(symbol, 0)
        prefix = {1: "SPPR", 2: "SPWI", 3: "SPIN", 4: "SPCL"}.get(number // 1000)
        res = f"{prefix}{number % 1000:03d}" if prefix else None
        data = game.get(res, "SPL") if res else None
        if data:
            chain, payload = sources(res, key)
            result[key] = {"res": res, "symbol": symbol, "level": ie.parse_spl(data)["level"],
                           "sources": chain, "payload_sources": payload}
    return result


def bonus(c, check, report):
    """Installed spell probes plus isolated engine arithmetic, with manual gaps explicit."""
    report["bonus_resources"] = BONUS
    report.setdefault("manual_checks", []).extend([
        {"group": "bonus", "check": "Save and reload a disposable save with overlapping typed effects; "
         "rest and change areas, then compare fresh CBMP.bonus_snapshot(0) values for 60 seconds.", "status": "not_run"},
        {"group": "bonus", "check": "Equip an actual item granting +1 to a tested value and confirm it adds "
         "to the corrected spell total; the scripted untagged effect is only an arithmetic control.", "status": "not_run"},
        {"group": "bonus", "check": "Capture the character sheet with the five-spell combination and after "
         "Recitation expires, showing the corrected totals.", "status": "not_run"},
        {"group": "bonus", "check": "In a separate disposable installation without EEex, verify ordinary "
         "stacking and self-refresh and one Lua fallback message. This EEex-console runner cannot run there.", "status": "not_run"},
        {"group": "bonus", "check": "Verify ordinary spellbook casting and projectile targeting; direct "
         "ApplySpellRES below tests installed effects and nested delivery only.", "status": "not_run"},
        {"group": "bonus", "check": "Apply Unholy Blight and Doom to the same eligible enemy in a disposable lab. "
         "Confirm the active opcode-177 EFF penalty appears in bonus_snapshot external metadata, only the worst "
         "Curse penalty affects THAC0 and saves, and the weaker penalty resumes when the stronger expires. "
         "Also check an ineligible target and a delayed or expired wrapper contribute no external payload. "
         "The external-EFF runtime path still needs live verification.", "status": "not_run"},
    ])
    available = c.lua("bo-runtime", "return type(CBMBonus) == 'table' and type(CBMBonus.Listener) == 'function' "
                      "and type(CBMBPM) == 'function'")
    check("Bonus: runtime and allocated typed state are present", available and BONUS.get("typed_state") is not None)
    if not available or BONUS.get("typed_state") is None:
        return

    def need(*keys):
        missing = [BONUS_SYMBOLS[k] for k in keys if k not in BONUS]
        if missing:
            report.setdefault("skipped", []).append({"group": "bonus", "missing": missing})
            rp.log("  skip bonus case: absent " + ", ".join(missing))
        return not missing

    def sources(*keys):
        # Keep unrelated maintenance deliveries out of cleanup and expiry edits.
        return sorted({r for k in keys for r in BONUS[k]["payload_sources"]})

    def clear(who, keys):
        c.p("bo-clear", f"bonus_clear({json.dumps(who)}, {lua_strings(sources(*keys))})")
        time.sleep(1.2)

    def apply(who, key):
        c.p("bo-apply-" + key, f"bonus_apply({json.dumps(who)}, {json.dumps(BONUS[key]['res'])})")
        time.sleep(3)

    def snap(who=0):
        c.p("bo-rebuild", f"bonus_rebuild({json.dumps(who)})")
        time.sleep(1.2)
        return c.p("bo-snapshot", f"bonus_snapshot({json.dumps(who)})")

    def expire(who, key):
        changed = c.p("bo-expire-" + key,
                      f"bonus_expire({json.dumps(who)}, {lua_strings(sources(key))}, 2)")
        time.sleep(4)
        return changed

    def relevant(snapshot, key):
        return bonus_payload_effects(snapshot, BONUS[key], BONUS_PAYLOAD_OPS.get(key, BONUS_TYPED_OPS))

    all_keys = [k for k in BONUS_SYMBOLS if k in BONUS]
    for who in range(3):
        clear(who, all_keys)
    combo = ("bless", "prayer", "recitation", "hope", "luck")
    if need(*combo):
        base = snap()
        for key in combo:
            apply(0, key)
        full = snap()
        actual = {"thac0": base["thac0"] - full["thac0"], "damage": full["dmg"] - base["dmg"],
                  "saves": [a - b for a, b in zip(base["saves"], full["saves"])]}
        check("Bonus: Bless, Prayer, Recitation, Hope and Luck totals", actual == {"thac0": 4, "damage": 3, "saves": [5] * 5},
              delta=actual, effects=full["effects"])
        apply(0, "bless")
        again = snap()
        check("Bonus: another Bless refreshes without adding a second bonus", bonus_values(again) == bonus_values(full),
              first=bonus_values(full), second=bonus_values(again))
        changed = expire(0, "recitation")
        after = snap()
        check("Bonus: Prayer resumes when Recitation expires without another cast",
              changed > 0 and bool(relevant(after, "prayer")) and not relevant(after, "recitation")
              and after["thac0"] == full["thac0"] + 1
              and after["saves"] == [v + 1 for v in full["saves"]],
              before=bonus_values(full), after=bonus_values(after))
        clear(0, combo)

    if need("doom", "curse"):
        c.p("bo-spawn", 'spawn("TASLOI01", 90, 0)')
        time.sleep(2)
        c.p("bo-pin", 'pin("Tasloi", 600)')
        c.p("bo-saves", 'set_saves("Tasloi", {death = 20, breath = 20, spell = 20}, 600)')
        base = snap("Tasloi")
        apply("Tasloi", "curse")
        curse = snap("Tasloi")
        apply("Tasloi", "doom")
        both = snap("Tasloi")
        check("Bonus: enemy has both Doom and Curse, with only the worst THAC0 penalty",
              bool(relevant(both, "doom")) and bool(relevant(both, "curse")) and both["thac0"] == base["thac0"] + 2,
              values=[base["thac0"], curse["thac0"], both["thac0"]], effects=both["effects"])
        changed = expire("Tasloi", "doom")
        after = snap("Tasloi")
        check("Bonus: Curse resumes on an enemy when Doom expires", changed > 0
              and not relevant(after, "doom") and bool(relevant(after, "curse")) and after["thac0"] == curse["thac0"],
              values=[curse["thac0"], both["thac0"], after["thac0"]])

    if need("prayer"):
        if not need("doom", "curse"):
            c.p("bo-prayer-spawn", 'spawn("TASLOI01", 90, 0)')
            time.sleep(2)
            c.p("bo-prayer-pin", 'pin("Tasloi", 600)')
        clear(0, ("prayer",))
        base = snap()
        apply(0, "prayer")
        friend = snap()
        c.p("bo-prayer-enemy", f'bonus_enemy_prayer("Tasloi", 0, "{BONUS["prayer"]["res"]}")')
        time.sleep(4)
        mixed = snap()
        signs = {1 if e["p1"] > 0 else -1 for e in mixed["effects"] if e["tag"] == "CBTFAVOR" and e["op"] == 54 and e["p1"]}
        check("Bonus: friendly Prayer and hostile Prayer both apply", signs == {-1, 1}
              and friend["thac0"] == base["thac0"] - 1 and mixed["thac0"] == base["thac0"],
              values=[base["thac0"], friend["thac0"], mixed["thac0"]], effects=mixed["effects"])
        clear(0, ("prayer",))
    c.p("bo-enemies-done", "remove_all_others()")

    # Controlled effects isolate the marker and untyped-source behavior from spell durations.
    for who in range(3):
        clear(who, all_keys)
    base = snap()
    state = BONUS["typed_state"]
    for amount in (2, 1):
        c.p("bo-tagged", f'bonus_fx(0, 54, {amount}, 0, "CBTFAVOR", {state}, 180)')
    typed = snap()
    c.p("bo-untagged", 'bonus_fx(0, 54, 1, 0, "", nil, 180)')
    untyped = snap()
    check("Bonus: untagged +1 stacks with highest Favor +2", typed["thac0"] == base["thac0"] - 2
          and untyped["thac0"] == typed["thac0"] - 1,
          values=[base["thac0"], typed["thac0"], untyped["thac0"]])
    samples = [untyped]
    for _ in range(6):
        time.sleep(10)
        samples.append(snap())
    check("Bonus: corrected values do not drift over 60 seconds with repeated rebuilds",
          all(bonus_values(s) == bonus_values(untyped) for s in samples)
          and samples[-1]["time"] - samples[0]["time"] >= 60 * 15,
          values=[bonus_values(s) for s in samples], ticks=samples[-1]["time"] - samples[0]["time"])
    c.p("bo-fixture-clear", 'bonus_clear(0, {"CBMQLAB"})')
    time.sleep(1.2)

    if need("pierce"):
        for mr in (10, 20, 50, 100):
            clear(0, ("pierce",))
            c.p("bo-mr-set", f'bonus_fx(0, 166, {mr}, 1, "", nil, 90)')
            before = snap()
            apply(0, "pierce")
            after = snap()
            reduction = max(10, min(40, mr // 2))
            check(f"Pierce Magic: current MR {mr} loses {reduction} points for five rounds",
                  before["mr"] == mr and after["mr"] == max(0, mr - reduction)
                  and any(e["op"] == 166 and e["p1"] == -reduction and e["p2"] == 0
                          and e["dt"] == 4096 and 23 * 15 <= e["dur"] - after["time"] <= 30 * 15
                          for e in after["effects"]), before=before["mr"], after=after["mr"], effects=after["effects"])
            c.p("bo-mr-clear", 'bonus_clear(0, {"CBMQLAB"})')
        clear(0, ("pierce",))

    for family, keys in (("Transformation", ("tenser", "divine", "righteous", "champion", "blood", "animal")),
                         ("Regeneration", ("regenerate", "mass", "troll"))):
        present = [k for k in keys if k in BONUS]
        need(*keys)
        for old in present:
            for new in present:
                if old == new:
                    continue
                clear(0, present)
                apply(0, old)
                before = snap()
                apply(0, new)
                after = snap()
                winner = new if BONUS[new]["level"] >= BONUS[old]["level"] else old
                loser = old if winner == new else new
                check(f"{family}: {old} then {new} keeps {winner}", bool(relevant(before, old))
                      and bool(relevant(after, winner)) and not relevant(after, loser),
                      levels={old: BONUS[old]["level"], new: BONUS[new]["level"]}, effects=after["effects"])
        clear(0, present)


def lua_strings(values):
    return "{" + ", ".join(json.dumps(v) for v in values) + "}"


def bonus_values(snapshot):
    return {key: snapshot[key] for key in ("thac0", "dmg", "ac", "luck", "saves")}


def bonus_payload_effects(snapshot, spell, opcodes):
    """Only active intended mechanics prove presence; pending or expired effects do not."""
    candidates = list(snapshot["effects"])
    candidates.extend(e["external"] for e in snapshot["effects"] if isinstance(e.get("external"), dict))
    return [e for e in candidates
            if e["src"] in spell["payload_sources"] and e["op"] in opcodes
            and ((e["dt"] == 4096 and e["dur"] > snapshot["time"]) or e["dt"] in (1, 2, 9))]


MASS_REGENERATE = "SPPR502"
SKIP_SMOKE = {"SPWI420", "SPWI617", "SPWI710", "SPWI809", "SPWI908", "SPWI123", "SPWI703", "SPWI804", "SPWI919"}
SMOKE = []


def main():
    args = sys.argv[1:]
    global MASS_REGENERATE, BONUS
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
    selected = args[args.index("--only") + 1].split(",")
    if "bonus" in selected and "--game" in args:
        BONUS = bonus_resources(Path(args[args.index("--game") + 1]))
    if {"record", "live"} & set(selected) and "--game" in args:
        record_rows(Path(args[args.index("--game") + 1]))
    sys.argv = [sys.argv[0], *args]
    rp.GROUPS = GROUPS
    rp.run_checks = run_checks
    return rp.main()


if __name__ == "__main__":
    sys.exit(main())
