"""In-game checks of the decided spell batches, in a quiet disposable lab game.

usage: python -I tests/lab/run_batches.py --game <lab game> --profile <lab profile>
           --lab-tools <folder with bg_lab_slots.py> --load-lua <lab_load.lua> --save <save folder>
           --out <evidence folder> [--seconds 900] [--only strength,mr,...]

Same lab and same rules as run_probe.py, which this reuses. Each check sets up its own case,
reads the sprites before and after, and decides in Python. Nothing is saved.
"""
import importlib.util
import json
import re
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("run_probe", HERE / "run_probe.py")
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

EXTRA = HERE / "probe_batches.lua"
WRATH = ""
AIR, LANCE = "", ""
GAME = Path(".")
GROUPS = ("haste", "curse", "control", "strength", "mr", "image", "sword", "newspells", "breathless", "insects", "nature", "fiends", "sequencer", "record", "live", "bonus", "attacks", "smoke", "decided", "iwdbatch", "celestials", "celweapons", "restoration")


def lua_list(values):
    return "{" + ", ".join(str(v) for v in values) + "}"


RAGE = None

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
    # Errors of the base game.
    for res, wanted, unwanted in (("SPWI315", "Wraithform", "Invulnerable"), ("SPWI802", "Spell Deflection", "Protection From Magic"),
                                  ("SPWI201", "Blur", None), ("SPPR613", "Physical Mirror", None),
                                  ("SPWI213", "Nauseated", "Sleep"), ("SPWI816", "Stunned", "Stun"),
                                  ("SPWI106", "Blinded", "Blind"), ("SPWI223", "Deafened", "Deaf")):
        fresh(20)
        apply(res)
        rows = shown()
        check(f"{res} is listed as {wanted}", wanted in rows and unwanted not in rows, rows=rows)
        done()
    # Exaltation turns enemies away (opcode 324), so a party member takes it.
    c.p("rc-saves", "set_saves(0, {spell = 20, breath = 20, death = 20}, 60)")
    for bad, gone in (("SPWI509", "Feebleminded"), ("SPWI401", "Confused")):
        c.p(f"rc-{bad}", f'apply_spell(1, "{bad}", "Player1")')
        time.sleep(1.4)
        before = [RECORD.get(row, str(row)) for row in c.p("rc-rows0", "icons(0)") or []]
        c.p("rc-exalt", 'apply_spell(1, "OHTYR1", "Player1")')
        time.sleep(1.8)
        rows = [RECORD.get(row, str(row)) for row in c.p("rc-rows0", "icons(0)") or []]
        check(f"Exaltation clears {gone}", gone in before and gone not in rows, before=before, after=rows)
        c.p("rc-exalt-end", f'clear(0, {{"{bad}", "OHTYR1"}})')
        time.sleep(1)
    for bad, cure, gone in (("SPPR610", "SPPR212", "Decaying"), ("SPPR610", "SPPR404", "Decaying"),
                            ("SPPR610", "SPPR607", "Decaying"), ("SPWI215", "SPPR308", "Webbed")):
        fresh(20)
        apply(bad, 1.4)
        before = shown()
        apply(cure, 1.8)
        rows = shown()
        check(f"{cure} clears {gone}", gone in before and gone not in rows, before=before, after=rows)
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


def attacks(c, check):
    # Needs IWDification: Righteous Wrath of the Faithful is its spell. The same-alignment payload
    # is what the spell delivers to a party member; its name comes from the installed spell.
    if not WRATH:
        check("Extra attack: Righteous Wrath is not in this game", True)
        return
    who = 2

    def read():
        time.sleep(1.6)
        return c.p("at-read", f"attacks({who})")

    base = read()
    c.p("at-wrath", f'on_member({who}, "{WRATH}")')
    wrath = read()
    check("Extra attack: Righteous Wrath gives one", wrath["tagged"] == [1], base=base, wrath=wrath)
    c.p("at-haste", f"fx({who}, 16, 0, 0, 6)")
    both = read()
    check("Extra attack: under Haste only Haste counts", both["tagged"] == [0] and both["apr"] == base["apr"], both=both)
    time.sleep(6)
    after = read()
    check("Extra attack: when Haste ends, Righteous Wrath works again", after == wrath, after=after)
    c.p("at-improved", f'on_member({who}, "SPWI613")')
    improved = read()
    check("Extra attack: beside Improved Haste only one counts", sorted(improved["tagged"]) == [0, 1], improved=improved)


def added_spell(game, symbol):
    """The file an install gave a spell it added."""
    number = int(re.search(rf"^\s*(\d+)\s+{symbol}\s*$",
                           (game / "override" / "spell.ids").read_text(encoding="latin-1"), re.M)[1])
    return f"{'SPPR' if number < 2000 else 'SPWI'}{number % 1000:03d}"


def fresh_foe(c, tag, res="SPIDHU01", name="spidhu01", distance=260):
    c.p(f"{tag}-clear", "remove_all_others()")
    time.sleep(1)
    c.p(f"{tag}-spawn", f'spawn("{res}", {distance}, 0)')
    time.sleep(2)
    c.p(f"{tag}-pin", f'pin("{name}", 900)')
    return name


def decided(c, check):
    # Command: one round of sleep, and a hit ends it.
    foe = fresh_foe(c, "dc")
    c.p("dc-saves", f'set_saves("{foe}", {{spell = 20}}, 900)')
    c.p("dc-cmd", f"""cast(2, "SPPR102", '"{foe}"')""")
    time.sleep(3.5)
    asleep = c.p("dc-asleep", f'creature("{foe}")')
    time.sleep(7)
    over = c.p("dc-over", f'creature("{foe}")')
    check("Command: the target sleeps for one round", asleep["state"] & 1 and not over["state"] & 1,
          state=[hex(asleep["state"]), hex(over["state"])])
    c.p("dc-cmd2", f"""cast(2, "SPPR102", '"{foe}"')""")
    time.sleep(3.5)
    asleep = c.p("dc-asleep2", f'creature("{foe}")')
    c.p("dc-hit", f'damage("{foe}", 1)')
    time.sleep(1.5)
    awake = c.p("dc-awake", f'creature("{foe}")')
    check("Command: a hit wakes the target", asleep["state"] & 1 and not awake["state"] & 1,
          state=[hex(asleep["state"]), hex(awake["state"])])

    # Chaos: confusion lasts what the caster's level says.
    foe = fresh_foe(c, "dx")
    c.p("dx-saves", f'set_saves("{foe}", {{spell = 20}}, 900)')
    level = c.p("dx-level", "level(1)")
    expected = 36 if level >= 20 else 30 if level >= 15 else 24
    c.p("dx-cast", f"""cast(1, "SPWI508", '"{foe}"')""")
    started = ended = None
    for _ in range(120):
        confused = c.p("dx-ops", f'ops("{foe}", {{128}})') or []
        now = time.time()
        if confused and started is None:
            started = now
        if not confused and started is not None:
            ended = now
            break
        if started is None and now > 0 and _ > 20:
            break
        time.sleep(0.5)
    lasted = round(ended - started, 1) if started and ended else None
    check(f"Chaos: confusion lasts {expected} seconds at caster level {level}",
          lasted is not None and abs(lasted - expected) <= 3, lasted=lasted)

    # Priest Sphere of Chaos: the field reaches enemies, not the party.
    foe = fresh_foe(c, "ds")
    c.p("ds-saves", f'set_saves("{foe}", {{spell = 20}}, 900)')
    at = c.p("ds-at", f'creature("{foe}")')
    c.p("ds-cast", f'cast_point(2, "SPPR709", {at["x"]}, {at["y"]})')
    effects, touched = [], []
    for _ in range(16):
        time.sleep(1)
        effects = [e for e in (c.p("ds-ops", f'ops("{foe}", {{76, 128, 24, 39, 175}})') or []) if e["src"] == "SPPR709"]
        if effects:
            break
    for i in range(3):
        touched += [e for e in (c.p(f"ds-p{i}", f"ops({i}, {{76, 128, 24, 39, 175}})") or []) if e["src"] == "SPPR709"]
    check("Priest Sphere of Chaos affects the enemy", bool(effects), effects=effects)
    check("Priest Sphere of Chaos spares the party", not touched, touched=touched)
    c.p("ds-tidy", "remove_all_others()")
    time.sleep(1)

    # Druid Conjure Air Elemental: an ally at once, and it stays one.
    p0 = c.p("da-party", "party()")[0]
    c.p("da-cast", f'cast_point(2, "{AIR}", {p0["x"] + 90}, {p0["y"]})')
    time.sleep(13)
    first = [o for o in c.p("da-others", "others()") or [] if "Air" in (o["name"] or "")]
    time.sleep(20)
    later = [o for o in c.p("da-others2", "others()") or [] if "Air" in (o["name"] or "")]
    check("Druid Conjure Air Elemental summons one elemental on the party's side", len(first) == 1 and first[0]["ea"] < 30,
          first=first)
    check("Druid Conjure Air Elemental: no control contest, it stays on the party's side after three rounds",
          len(later) == 1 and later[0]["ea"] < 30, later=later)

    # Icelance: damage always, the save only against the stun, immunity to stun keeps the damage.
    def lance(tag):
        before = c.p(f"{tag}-b", f'creature("{foe}")')
        c.p(f"{tag}-c", f"""cast(2, "{LANCE}", '"{foe}"')""")
        time.sleep(6)
        after = c.p(f"{tag}-a", f'creature("{foe}")')
        return before["hp"] - after["hp"], bool(after["state"] & 8)

    foe = fresh_foe(c, "dl")
    c.p("dl-hp", f'fx("{foe}", 18, 300, 0, 600)')
    c.p("dl-pass", f'set_saves("{foe}", {{spell = 1}}, 600)')
    time.sleep(1)
    damage, stunned = lance("dl1")
    check("Icelance: a saved target takes 5d6 and is not stunned", 5 <= damage <= 30 and not stunned, damage=damage, stunned=stunned)
    c.p("dl-fail", f'set_saves("{foe}", {{spell = 20}}, 600)')
    c.p("dl-immune", f'fx("{foe}", 101, 0, 45, 600)')
    time.sleep(1)
    damage, stunned = lance("dl2")
    check("Icelance: immunity to stun keeps the damage", 5 <= damage <= 30 and not stunned, damage=damage, stunned=stunned)
    foe = fresh_foe(c, "dm")
    c.p("dm-hp", f'fx("{foe}", 18, 300, 0, 600)')
    c.p("dm-fail", f'set_saves("{foe}", {{spell = 20}}, 600)')
    time.sleep(1)
    damage, stunned = lance("dm1")
    check("Icelance: a failed save stuns and takes 5d6", 5 <= damage <= 30 and stunned, damage=damage, stunned=stunned)

    # Champion's Strength and Draw Upon Divine Might never stand together on one creature.
    who, duhm, champion, tenser = 0, "SPPR214", "SPPR507", "SPWI603"

    def on(res):
        return c.p(f"dd-{res}", f'portrait({who}, "{res}")')["effects"]

    def give(res):
        c.p(f"dd-give-{res}", f'on_member({who}, "{res}")')
        time.sleep(1.6)

    c.p("dd-clear", f'clear({who}, {{"{duhm}", "{champion}", "{tenser}"}})')
    time.sleep(1)
    give(duhm)
    landed = on(duhm)
    give(champion)
    check("Champion's Strength removes Draw Upon Divine Might", landed and on(champion) and not on(duhm),
          landed=len(landed), champion=len(on(champion)), left=len(on(duhm)))
    give(duhm)
    check("Draw Upon Divine Might does not land under Champion's Strength", not on(duhm), left=len(on(duhm)))
    give(champion)
    give(duhm)
    check("A second Champion's Strength keeps the protection", on(champion) and not on(duhm), left=len(on(duhm)))
    c.p("dd-clear2", f'clear({who}, {{"{champion}"}})')
    time.sleep(1)
    give(duhm)
    check("Draw Upon Divine Might lands again once Champion's Strength is gone", bool(on(duhm)), landed=len(on(duhm)))
    give(tenser)
    check("Draw Upon Divine Might stands beside the other transformations", bool(on(duhm)) and bool(on(tenser)),
          duhm=len(on(duhm)), tenser=len(on(tenser)))
    c.p("dd-tidy", f'clear({who}, {{"{duhm}", "{champion}", "{tenser}"}})')


def iwdbatch(c, check):
    # Needs IWDification's spells. Emotion: Hopelessness and Symbol: Hopelessness are not cast here
    # at an area: the stun of each is applied, and a hit must end it, an unrelated stun must stay.
    foe = fresh_foe(c, "ih")
    c.p("ih-hp", f'fx("{foe}", 18, 300, 0, 600)')
    c.p("ih-saves", f'set_saves("{foe}", {{spell = 20}}, 600)')
    at = c.p("ih-at", f'creature("{foe}")')
    c.p("ih-cast", f'cast_point(1, "SPWI411", {at["x"]}, {at["y"]})')
    time.sleep(6)
    stunned = c.p("ih-stun", f'creature("{foe}")')
    held = c.p("ih-ops", f'ops("{foe}", {{45, 232}})') or []
    check("Emotion: Hopelessness stuns through its own area", bool(stunned["state"] & 8), state=hex(stunned["state"]), effects=held)
    c.p("ih-hit", f'damage("{foe}", 1)')
    time.sleep(2.5)
    after = c.p("ih-after", f'creature("{foe}")')
    left = [e for e in (c.p("ih-left", f'ops("{foe}", {{45, 142}})') or []) if e["src"] == "SPWI411"]
    check("Emotion: Hopelessness: a hit ends it, its icon too", not after["state"] & 8 and not left,
          state=hex(after["state"]), left=left)
    c.p("ih-other", f'fx("{foe}", 45, 0, 0, 30)')
    time.sleep(0.5)
    c.p("ih-cast2", f'cast_point(1, "SPWI411", {at["x"]}, {at["y"]})')
    time.sleep(6)
    c.p("ih-hit2", f'damage("{foe}", 1)')
    time.sleep(2.5)
    other = c.p("ih-after2", f'creature("{foe}")')
    check("Emotion: Hopelessness: a stun from elsewhere stays after the hit", bool(other["state"] & 8), state=hex(other["state"]))

    # Every wizard elemental: on the party's side during the contest, then an ally or hostile.
    p0 = c.p("ie-party", "party()")[0]
    for name, res in (("Fire", "SPWI620"), ("Air", "SPWI621"), ("Earth", "SPWI622"), ("Water", "SPWI633"),
                      ("Lesser Fire", "SPWI516"), ("Lesser Air", "SPWI520"), ("Lesser Earth", "SPWI521"),
                      ("Lesser Water", "SPWI526")):
        c.p(f"ie-clear-{res}", "remove_all_others()")
        time.sleep(1)
        c.p(f"ie-cast-{res}", f'cast_point(1, "{res}", {p0["x"] + 90}, {p0["y"]})')
        time.sleep(11)
        early = c.p(f"ie-early-{res}", "others()") or []
        time.sleep(21)
        late = c.p(f"ie-late-{res}", "others()") or []
        check(f"Conjure {name} Elemental: one elemental, on the party's side during the contest",
              len(early) == 1 and early[0]["ea"] < 30, early=early)
        check(f"Conjure {name} Elemental: after the contest ally or hostile", len(late) == 1 and late[0]["ea"] in (4, 255),
              late=late)


def celestials(c, check):
    defs = Path(__file__).resolve().parents[2] / "defs"
    c.p("ce-protect", "protect_party()")
    p0 = c.p("ce-party", "party()")[0]

    def clear(tag):
        c.p(f"ce-clear-{tag}", "remove_all_others()")
        time.sleep(1.5)

    def call(tag, res, dx=90, wait=11):
        c.p(f"ce-cast-{tag}", f'cast_point(1, "{res}", {p0["x"] + dx}, {p0["y"]})')
        time.sleep(wait)

    def present(tag):
        return [o for o in c.p(f"ce-others-{tag}", "others()") or [] if o["ea"] < 30]

    # The numbers the descriptions give, read from the running game.
    table = (("SPPR726", "Deva", "cbmdevag", 136, -5, 14, [18, 18, 18, 18], 70, 10, [50, 100, 100, 0]),
             ("SPPR727", "Fallen Deva", "cbmdevae", 136, -5, 14, [18, 18, 18, 18], 70, 10, [100, 0, 100, 50]),
             ("SPWI923", "Planetar", "cbmplang", 152, -7, 18, [18, 21, 19, 18], 75, 20, [50, 100, 100, 0]),
             ("SPWI924", "Fallen Planetar", "cbmplane", 152, -7, 18, [18, 21, 19, 18], 75, 20, [100, 0, 100, 50]))
    for res, name, file, hp, ac, level, abilities, mr, physical, elements in table:
        clear(res)
        call(res, res)
        one = c.p(f"ce-being-{res}", f'being("{name}")')
        check(f"{name}: arrives on the party's side", one and one["ea"] < 30, being=one)
        if not one:
            continue
        book = json.loads((defs / f"{file}.cre.json").read_text(encoding="utf-8"))["spells"]
        known = sorted(f"{i}:{spell}" for i, spells in enumerate(book) for spell in spells)
        check(f"{name}: {hp} Hit Points, AC {ac}", (one["maxhp"], one["ac"]) == (hp, ac), maxhp=one["maxhp"], ac=one["ac"])
        check(f"{name}: level, attributes, saves", one["level"] == level and one["attributes"][1:5] == abilities and
              one["saves"] == [3, 5, 4, 4, 6], level=one["level"], attributes=one["attributes"], saves=one["saves"])
        check(f"{name}: resistances", one["resist"] == [*elements, mr, physical, physical, physical, physical], resist=one["resist"])
        check(f"{name}: spell book", sorted(one["known"]) == known, known=one["known"])
        check(f"{name}: no SUMMONED gender; attacks", (one["gender"], one["apr"]) == (5, 2 if level == 14 else 3),
              gender=one["gender"], apr=one["apr"], thac0=one["thac0"], equipped=one["equipped"])

    # One of each kind: the second of a kind leaves, the first stays, the other kind comes.
    clear("cap")
    call("cap", "SPPR726")
    first = present("cap-first")
    check("Limit: one deva arrives", len(first) == 1, present=first)
    call("cap2", "SPPR726")
    now = present("cap2")
    check("Limit: a second deva leaves, the first stays", [o["id"] for o in now] == [first[0]["id"]], present=now)
    call("cap3", "SPPR727")
    now = present("cap3")
    check("Limit: a fallen deva leaves beside a deva", [o["id"] for o in now] == [first[0]["id"]], present=now)
    call("cap4", "SPCL935")
    now = present("cap4")
    check("Limit: the paladin's Summon Fallen Deva counts too", [o["id"] for o in now] == [first[0]["id"]], present=now)
    call("cap5", "SPWI923", dx=-90)
    now = present("cap5")
    planetar = [o for o in now if o["name"] == "Planetar"]
    check("Limit: a planetar comes beside the deva", len(now) == 2 and len(planetar) == 1, present=now)
    call("cap6", "SPWI924", dx=-90)
    now = present("cap6")
    check("Limit: a dark planetar leaves beside a planetar", len(now) == 2 and bool(planetar) and
          planetar[0]["id"] in [o["id"] for o in now], present=now)

    # The first one gone, a new one may come.
    clear("again")
    call("again", "SPPR727")
    now = present("again")
    check("Limit: after the first is gone another comes", len(now) == 1 and now[0]["name"] == "Fallen Deva", present=now)

    # The party AI button off, then on again.
    clear("ai")
    call("ai1", "SPPR726")
    off = c.p("ce-ai-off", "party_ai(false)")
    call("ai2", "SPPR726")
    during = present("ai2")
    c.p("ce-ai-on", "party_ai(true)")
    time.sleep(4)
    after = present("ai3")
    check("Limit with the party AI off", len(after) == 1, ai=off, during=during, after=after)

    # A deva out of sight.
    clear("far")
    call("far1", "SPPR726")
    c.p("ce-far", f"""order("Deva", 'JumpToPoint([{p0["x"] + 1400}.{p0["y"]}])')""")
    time.sleep(2)
    apart = present("far1")
    call("far2", "SPPR726")
    now = present("far2")
    check("Limit: a second deva leaves while the first is out of sight", len(now) == 1 and now[0]["id"] == apart[0]["id"],
          apart=apart, present=now)

    # Enemy casters are not limited.
    clear("foe")
    call("foe1", "SPPR726")
    enemy = fresh_foe(c, "cf")
    call("foe0", "SPPR726")
    c.p("cf-cast", f"""order("{enemy}", 'ReallyForceSpellPointRES("SPPR726",[{p0["x"] + 200}.{p0["y"]}])')""")
    time.sleep(11)
    c.p("cf-cast2", f"""order("{enemy}", 'ReallyForceSpellPointRES("SPPR726",[{p0["x"] + 240}.{p0["y"]}])')""")
    time.sleep(11)
    everyone = c.p("cf-others", "others()") or []
    devas = [o for o in everyone if o["name"] == "Deva"]
    check("Limit: enemy casters are not limited", sum(o["ea"] >= 200 for o in devas) == 2 and sum(o["ea"] < 30 for o in devas) == 1,
          devas=devas)
    check("An enemy's deva casts with the game's celestial script, the party's does not",
          all(o["class_script"].upper() in (("DEVAGOOD",) if o["ea"] >= 200 else ("", "NONE")) for o in devas), devas=devas)

    # Its book and its nature in play.
    clear("book")
    call("book", "SPPR726")
    c.p("cb-spell", """order("Deva", 'Spell(Myself,CLERIC_BLESS)')""")
    time.sleep(6)
    blessed = [e for e in (c.p("cb-ops", """ops("Deva", {54, 318, 321})""") or []) if e["src"] == "SPPR101"]
    check("Deva: it casts from its book", bool(blessed), effects=blessed)

    clear("regen")
    call("regen", "SPWI923")
    c.p("cr-hit", 'damage("Planetar", 30)')
    time.sleep(0.5)
    hurt = c.p("cr-hurt", 'being("Planetar")')
    time.sleep(12)
    healed = c.p("cr-healed", 'being("Planetar")')
    check("Planetar: regenerates about 2 Hit Points per round", 3 <= healed["hp"] - hurt["hp"] <= 6,
          hurt=hurt["hp"], healed=healed["hp"])

    clear("end")


def restoration(c, check):
    # Drain of several kinds on the second portrait, as the spell or weapon would leave it, then
    # Lesser Restoration from the first.
    c.p("rs-protect", "protect_party()")
    foe = fresh_foe(c, "rs")
    before = c.p("rs-before", "attributes(1)")
    SPELL, ITEM = 1, 2
    rows = [("SPWI221", SPELL, 44, 5, 1), ("SPWI221", SPELL, 142, 0, 113),       # Ray of Enfeeblement
            ("MINDFLAY", ITEM, 19, -5, 0),                                      # a mind flayer's hit
            ("SPWI928", SPELL, 10, -2, 0), ("SPWI928", SPELL, 15, -2, 0),       # Energy Drain: attributes,
            ("SPWI928", SPELL, 33, -2, 0), ("SPWI928", SPELL, 142, 0, 53),     # a save and its icon stay
            ("SPPR321", SPELL, 78, 2, 6)]                                       # disease: Constitution -2
    if RAGE:
        rows.append((RAGE, SPELL, 49, 3, 1))                                  # Blood Rage's own weakness
    for i, (res, kind, op, p1, p2) in enumerate(rows):
        c.p(f"rs-fx-{i}", f'fx_from(1, "{foe}", "{res}", {kind}, {op}, {p1}, {p2}, 300)')
    time.sleep(1.5)
    drained = c.p("rs-drained", "attributes(1)")
    c.p("rs-cast", 'cast(0, "SPPR417", "Player2")')
    time.sleep(6)
    after = c.p("rs-after", "attributes(1)")
    left = [(e["src"], e["op"], e["p2"]) for e in c.p("rs-left", "ops(1, {10, 15, 19, 33, 44, 49, 78, 142})") or []]
    facts = dict(before=before, drained=drained, after=after, left=left)
    check("Lesser Restoration: Strength, Intelligence and Dexterity come back, Constitution all but the disease",
          [after[k] for k in ("str", "int", "dex")] == [before[k] for k in ("str", "int", "dex")] and
          after["con"] == before["con"] - 2 and drained["con"] == before["con"] - 4 and
          [drained[k] for k in ("str", "int", "dex")] != [before[k] for k in ("str", "int", "dex")], **facts)
    check("Lesser Restoration: Ray of Enfeeblement's icon goes with it", ("SPWI221", 142, 113) not in left, **facts)
    check("Lesser Restoration: Energy Drain's save penalty and icon stay", ("SPWI928", 33, 0) in left and
          ("SPWI928", 142, 53) in left, **facts)
    check("Lesser Restoration: disease stays", ("SPPR321", 78, 6) in left, **facts)
    if RAGE:
        check("Lesser Restoration: Blood Rage's weakness stays", (RAGE, 49, 1) in left, **facts)
    c.p("rs-tidy", "remove_all_others()")


def celweapons(c, check):
    # A foe that cannot die, and the celestial called next to it: in this room walls stand between
    # the party and a foe further out.
    c.p("cw-protect", "protect_party()")
    # The fallen deva: 1d8+10 slashing and 1d8 fire, and the bleeding of earlier hits, 1 Hit Point
    # a pulse, can land in the same quarter second.
    for res, name, low, high, bleed in (("SPPR726", "Deva", 11, 20, 0), ("SPPR727", "Fallen Deva", 12, 26, 3),
                                        ("SPWI923", "Planetar", 12, 22, 0)):
        c.p(f"cw-clear-{res}", "remove_all_others()")
        time.sleep(1.5)
        c.p(f"cw-spawn-{res}", 'spawn("SPIDHU01", 100, 0)')
        time.sleep(2)
        c.p(f"cw-live-{res}", 'fx("spidhu01", 208, 1, 0, 600)')
        c.p(f"cw-hp-{res}", 'fx("spidhu01", 18, 900, 0, 600)')
        at = c.p(f"cw-foe-{res}", 'creature("spidhu01")')
        c.p(f"cw-cast-{res}", f'cast_point(1, "{res}", {at["x"] - 30}, {at["y"]})')
        time.sleep(10)
        # A foe in sight pauses the game when the game's auto-pause says so.
        paused = c.p(f"cw-unpause-{res}", "unpause()")
        c.p(f"cw-go-{res}", f"""order("{name}", 'Attack(NearestEnemyOf(Myself))')""")
        last, drops = c.p(f"cw-at-{res}", 'creature("spidhu01")')["hp"], []
        for i in range(100):
            time.sleep(0.25)
            if i % 8 == 0:
                c.p(f"cw-unpause-{res}-{i}", "unpause()")
            hp = c.p(f"cw-{res}-{i}", 'creature("spidhu01")')["hp"]
            if hp < last:
                drops.append(last - hp)
            last = hp
        hits = [d for d in drops if d > bleed]
        check(f"{name}: every hit {low} to {high}, twice that on a critical hit", bool(hits) and low <= min(hits) and
              all(d <= high + bleed or low * 2 <= d <= high * 2 + bleed for d in hits), drops=drops, paused=paused)
    c.p("cw-tidy", "remove_all_others()")


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


def prayer_penalty(root):
    """The part of Prayer that lands on the caster's enemies: the sub-spell with a negative THAC0."""
    data = (GAME / "override" / f"{root}.spl").read_bytes()
    fx_off = struct.unpack_from("<I", data, 0x6A)[0]
    for at in range(fx_off, len(data) - 0x2F, 0x30):
        if struct.unpack_from("<H", data, at)[0] != 146:
            continue
        name = data[at + 0x14:at + 0x1C].split(b"\0", 1)[0].decode("latin-1")
        child = (GAME / "override" / f"{name}.spl").read_bytes()
        child_fx = struct.unpack_from("<I", child, 0x6A)[0]
        for row in range(child_fx, len(child) - 0x2F, 0x30):
            if struct.unpack_from("<H", child, row)[0] == 54 and struct.unpack_from("<i", child, row + 4)[0] < 0:
                return name
    raise ValueError("Prayer has no part with a THAC0 penalty")


def wrath_payload(game):
    """The spell Righteous Wrath delivers to allies of the caster's alignment, if the game has it."""
    ids = (game / "override/spell.ids").read_text(encoding="latin-1")
    found = re.search(r"(?m)^\s*(\d+)\s+CLERIC_RIGHTEOUS_WRATH_OF_THE_FAITHFUL\b", ids)
    if not found:
        return ""
    root = game / "override" / f"SPPR{int(found.group(1)) % 1000:03}.spl"
    data = root.read_bytes()
    fx_off = struct.unpack_from("<I", data, 0x6A)[0]
    for at in range(fx_off, len(data) - 0x2F, 0x30):
        if struct.unpack_from("<H", data, at)[0] == 146:
            name = data[at + 0x14:at + 0x1C].split(b"\0", 1)[0].decode("latin-1")
            child = (game / "override" / (name + ".spl"))
            if child.exists() and b"CBTAPR" in child.read_bytes():
                return name
    return ""


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
        # An enemy's area spell does not reach the party in this arena, so its payload lands directly.
        c.p("bo-prayer-enemy", f'on_member(0, "{prayer_penalty(BONUS["prayer"]["res"])}")')
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

    # IWDification's Blood Rage keeps itself off this lab party through its own conditions, so its
    # place in the family is covered offline only.
    for family, keys in (("Transformation", ("tenser", "divine", "righteous", "champion", "animal")),
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
    global MASS_REGENERATE, BONUS, WRATH, GAME
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
    if "--game" in args:
        GAME = Path(args[args.index("--game") + 1])
    if "bonus" in selected and "--game" in args:
        BONUS = bonus_resources(Path(args[args.index("--game") + 1]))
    if "restoration" in selected and "--game" in args:
        global RAGE
        ids = (Path(args[args.index("--game") + 1]) / "override" / "spell.ids")
        found = re.search(r"^\s*(\d+)\s+CLERIC_BLOOD_RAGE\s*$", ids.read_text(encoding="latin-1"), re.M) if ids.exists() else None
        RAGE = f"SPPR{int(found[1]) % 1000:03d}" if found else None
    if "decided" in selected and "--game" in args:
        global AIR, LANCE
        game = Path(args[args.index("--game") + 1])
        AIR = added_spell(game, "CLERIC_CBMAGIC_CONJURE_AIR_ELEMENTAL")
        LANCE = added_spell(game, "CLERIC_CBMAGIC_ICELANCE")
    if "attacks" in selected and "--game" in args:
        WRATH = wrath_payload(Path(args[args.index("--game") + 1]))
    if {"record", "live"} & set(selected) and "--game" in args:
        record_rows(Path(args[args.index("--game") + 1]))
    sys.argv = [sys.argv[0], *args]
    rp.GROUPS = GROUPS
    rp.run_checks = run_checks
    return rp.main()


if __name__ == "__main__":
    sys.exit(main())
