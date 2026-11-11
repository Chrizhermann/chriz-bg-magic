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
GROUPS = ("haste", "curse", "control", "strength", "mr", "image", "sword", "newspells", "breathless", "insects", "nature", "fiends", "sequencer", "record", "live", "bonus", "attacks", "smoke", "decided", "iwdbatch", "celestials", "celweapons", "restoration", "simulacrum", "floor", "polymorph", "shapechange", "touch", "unseen")


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


def fist_hits(c, tag, seconds=24):
    """Hit point losses of the spider while Korgan punches it."""
    c.p(f"{tag}-unpause", "unpause()")
    c.p(f"{tag}-go", """order("korgan", 'Attack(NearestEnemyOf(Myself))')""")
    last, drops = c.p(f"{tag}-at", 'creature("spidhu01")')["hp"], []
    for i in range(int(seconds / 0.25)):
        time.sleep(0.25)
        if i % 8 == 0:
            c.p(f"{tag}-unpause-{i}", "unpause()")
        hp = c.p(f"{tag}-{i}", 'creature("spidhu01")')["hp"]
        if hp < last:
            drops.append(last - hp)
        last = hp
    return drops


MIGHT, ANIMAL = None, None


def floor(c, check):
    # A spell that gives a fixed Strength never lowers a higher one; bonuses and penalties count on
    # top of it, in either order. A timed set stands for what the game works out without the floor.
    pair = lambda s: (s["str"], s["strex"])  # noqa: E731
    spells = ["SPPR412", "SPPR507", "SPWI214", "SPPR312", *(r for r in (MIGHT, ANIMAL) if r)]

    def fresh(i, strength, extra=0):
        c.p(f"fl-clear{i}-{strength}", f"clear({i}, {lua_strings(spells)})")
        c.p(f"fl-set{i}-{strength}", f"fx({i}, 44, {strength}, 1, 900)")
        c.p(f"fl-setx{i}-{strength}", f"fx({i}, 97, {extra}, 1, 900)")
        time.sleep(1.5)
        return pair(c.p(f"fl-before{i}-{strength}", f"stats({i})"))

    def cast(i, res, wait=2.5):
        c.p(f"fl-cast{i}-{res}", f'on_member({i}, "{res}")')
        time.sleep(wait)
        return pair(c.p(f"fl-after{i}-{res}", f"stats({i})"))

    last = None
    for name, res, cases in (("Divine Power", "SPPR412", (((10, 0), (18, 100)), ((19, 0), (19, 0)))),
                             ("Champion's Strength", "SPPR507", (((12, 0), (18, 100)), ((20, 0), (20, 0)))),
                             ("Strength", "SPWI214", (((10, 0), (18, 50)), ((18, 30), (18, 80)), ((19, 0), (19, 0)))),
                             ("Animal Rage", ANIMAL, (((10, 0), (19, 0)), ((22, 0), (22, 0))))):
        if not res:
            continue
        for (strength, extra), expected in cases:
            before = fresh(0, strength, extra)
            after = cast(0, res)
            check(f"{name}: {strength}/{extra} becomes {expected[0]}/{expected[1]}", after == expected,
                  before=before, after=after)
            last = (strength, extra)
    c.p("fl-end", f"clear(0, {lua_strings(spells)})")
    time.sleep(2)
    gone = pair(c.p("fl-gone", "stats(0)"))
    check("the floor gone: Strength back to what the game works out", gone == last, gone=gone, expected=last)

    if MIGHT:
        results = {}
        for order in ((MIGHT, "SPPR412"), ("SPPR412", MIGHT)):
            fresh(0, 10)
            for res in order:
                after = cast(0, res)
            bonus = [e["p1"] for e in c.p(f"fl-might-{order[0]}", "ops(0, {132})") or []]
            results[order[0]] = (after, bonus)
        first, second = results[MIGHT], results["SPPR412"]
        check("Draw Upon Divine Might counts on top of Divine Power, in either order",
              first[0] == second[0] and bool(first[1]) and first[0][0] == 18 + first[1][0],
              might_first=first, divine_first=second)
        c.p("fl-end2", f"clear(0, {lua_strings(spells)})")

    # In a fight: Korgan without his gear, Strength 10, under Divine Power punches for 7 or 8.
    c.p("fl-clear", "remove_all_others()")
    time.sleep(1.5)
    c.p("fl-foe", 'spawn("SPIDHU01", 110, 0)')
    c.p("fl-korgan", 'spawn("KORGAN15", 60, 0)')
    time.sleep(2.5)
    c.p("fl-live", 'fx("spidhu01", 208, 1, 0, 600)')
    c.p("fl-hp", 'fx("spidhu01", 18, 900, 0, 600)')
    c.p("fl-ally", """order("korgan", 'ChangeEnemyAlly(Myself,ALLY)')""")
    c.p("fl-strip", """order("korgan", 'DestroyAllEquipment()')""")
    c.p("fl-weak", 'fx("korgan", 44, 10, 1, 600)')
    time.sleep(2)
    weak = fist_hits(c, "fl-weak", 16)
    c.p("fl-divine", 'cast_now("korgan", "SPPR412")')
    time.sleep(2.5)
    strong_stats = c.p("fl-strong-stats", 'stats("korgan")')
    strong = fist_hits(c, "fl-strong", 20)
    check("Divine Power in a fight: Strength 10 punches for 1 or 2, under the floor 7 or 8",
          bool(weak) and max(weak) <= 4 and bool(strong) and min(strong) >= 7, weak=weak, strong=strong,
          stats=strong_stats)
    c.p("fl-tidy", "remove_all_others()")


# Touch spells: (the touch weapon the spell gives, lowest and highest roll); Harm leaves 1 Hit Point.
TOUCH = {
    "SPPR414": ("Cause Serious Wounds", "CBHT40", 10, 31),      # 3d8 + 7
    "SPPR510": ("Cause Critical Wounds", "CRITICAL", 16, 44),   # 4d8 + 12
    "SPPR608": ("Harm", "CBHT70", None, None),
}


def first_change(c, tag, target, seconds=16):
    """The target's Hit Points before and after the first change while Korgan attacks it."""
    c.p(f"{tag}-unpause", "unpause()")
    start = c.p(f"{tag}-at", f'creature("{target}")')["hp"]
    c.p(f"{tag}-go", """order("korgan", 'Attack(NearestEnemyOf(Myself))')""")
    for i in range(int(seconds / 0.25)):
        time.sleep(0.25)
        if i % 8 == 0:
            c.p(f"{tag}-unpause-{i}", "unpause()")
        hp = c.p(f"{tag}-{i}", f'creature("{target}")')["hp"]
        if hp != start:
            return start, hp
    return start, start


def touch(c, check):
    # Cause Serious Wounds, Cause Critical Wounds and Harm give a touch weapon; its first hit harms the
    # living and heals the undead. A spawned Korgan without gear or scripts casts and strikes a held
    # huge spider and a held zombie, both with Hit Points to spare.
    for res, name, undead in (("SPIDHU01", "spidhu01", False), ("ZOMBIE01", "Zombie", True)):
        for spell, (title, weapon, low, high) in TOUCH.items():
            tag = f"to-{name[:4]}-{spell}"
            fresh_foe(c, tag, res, name, 110)
            c.p(f"{tag}-hp", f'fx("{name}", 18, 900, 0, 600)')
            c.p(f"{tag}-korgan", 'spawn("KORGAN15", 60, 0)')
            time.sleep(2.5)
            for level in ("OVERRIDE", "CLASS", "RACE", "GENERAL", "DEFAULT"):
                c.p(f"{tag}-script-{level}", f"""order("korgan", 'ChangeAIScript("",{level})')""")
            c.p(f"{tag}-ally", """order("korgan", 'ChangeEnemyAlly(Myself,ALLY)')""")
            c.p(f"{tag}-strip", """order("korgan", 'DestroyAllEquipment()')""")
            c.p(f"{tag}-live", 'fx("korgan", 208, 1, 0, 600)')
            time.sleep(2)
            full = c.p(f"{tag}-full", f'creature("{name}")')["hp"]
            if undead:
                c.p(f"{tag}-hurt", f'damage("{name}", 400)')
                time.sleep(1)
            c.p(f"{tag}-cast", f'cast_now("korgan", "{spell}")')
            time.sleep(1.5)
            armed = c.p(f"{tag}-armed", 'form_state("korgan")')["items"]
            start, after = first_change(c, tag, name)
            spent = c.p(f"{tag}-spent", 'form_state("korgan")')["items"]
            facts = dict(full=full, start=start, after=after, armed=armed, spent=spent)
            check(f"{title}: the spell gives its touch weapon, and the hit uses it up",
                  weapon in armed and weapon not in spent, **facts)
            if undead and low is None:
                check(f"{title} on a zombie: healed completely", after == full and start < full, **facts)
            elif undead:
                check(f"{title} on a zombie: heals {low} to {high}", low <= after - start <= high, **facts)
            elif low is None:
                check(f"{title} on a spider: down to 1 Hit Point", after == 1 and start > 1, **facts)
            else:
                check(f"{title} on a spider: {low} to {high} damage", low <= start - after <= high, **facts)
    c.p("to-tidy", "remove_all_others()")


# Form innate: (animation, Strength, exceptional, Dexterity, attacks, weapon, power it gives).
FORMS = {
    "CBMPHG": (0xE293, 19, 0, 10, 1, "CBMPHGW", "CBMPHGR"),
    "CBMPOM": (0x2200, 18, 100, 12, 1, "CBMPOMW", None),
    "SPWI495": (0x7A00, 15, 0, 17, 2, "PLYSPID", "CBMPSPW"),
    "SPWI496": (0x7902, 14, 0, 9, 1, "PLYJELLY", None),
    "CBMPHH": (0x7B04, 18, 0, 15, 1, "CBMPHHW", "CBMPHHB"),
    "CBMPRT": (0xC300, 10, 0, 20, 1, "CBMPRTW", "CBMPRTH"),
}
POWERS = {"CBMPHGR", "CBMPSPW", "CBMPHHB", "CBMPRTH"}
# Shapechange's forms: (animation, Strength, exceptional, Dexterity, attacks, weapon, power).
SHAPES = {
    "SPIN152": (0x7F01, 10, 0, 10, 4, "CDMINDFL", "CBMSFPB"),
    "SPIN153": (0x7F04, 24, 0, 9, 1, "CDGOLIRO", "CBMSGOC"),
    "SPIN154": (0x7F00, 22, 0, 18, 3, "TROLLALL", None),
    "CBMSMA": (0xE090, 19, 0, 19 - 1, 5, "CBMSMAW", "CBMSMAT"),
    "CBMSBA": (0x7101, 18, 0, 10, 3, "CBMSBAW", "CBMSBAZ"),
    "CBMSIS": (0x6405, 18, 10, 17, 1, "CBMSISW", None),
}
SHAPE_POWERS = {"CBMSFPB", "CBMSGOC", "CBMSMAT", "CBMSBAZ"}


def shapechange(c, check):
    # As for Polymorph Self: a spawned Korgan without gear or scripts takes every form in turn.
    c.p("sh-clear", "remove_all_others()")
    time.sleep(1.5)
    c.p("sh-korgan", 'spawn("KORGAN15", 60, 0)')
    time.sleep(2.5)
    for level in ("OVERRIDE", "CLASS", "RACE", "GENERAL", "DEFAULT"):
        c.p(f"sh-script-{level}", f"""order("korgan", 'ChangeAIScript("",{level})')""")
    c.p("sh-strip", """order("korgan", 'DestroyAllEquipment()')""")
    time.sleep(2)
    natural = c.p("sh-natural", 'form_state("korgan")')
    c.p("sh-cast", 'cast_now("korgan", "SPWI916")')
    time.sleep(2)
    cast = c.p("sh-after-cast", 'form_state("korgan")')
    check("Shapechange gives the natural form and the six forms", {"CBMSNAT", *SHAPES} <= set(cast["innates"]),
          innates=sorted(cast["innates"]))
    one_attack = None
    for form, (anim, strength, extra, dex, apr, weapon, power) in SHAPES.items():
        c.p(f"sh-{form}", f'cast_now("korgan", "{form}")')
        time.sleep(2.5)
        state = c.p(f"sh-{form}-state", 'form_state("korgan")')
        powers = set(state["innates"]) & SHAPE_POWERS
        if form == "SPIN153":
            one_attack = state["apr"]
        exceptional = extra if extra or strength != 18 else natural["strex"]
        check(f"form {form}: look, body, weapon and powers", state["anim"] == anim and
              (state["str"], state["strex"]) == (strength, exceptional) and weapon in state["items"] and
              powers == ({power} if power else set()) and form in state["innates"], state=state)
        if form == "SPIN152":
            check("mind flayer: Magic Resistance 90", state["mr"] == 90, state=state)
        if form == "SPIN153":
            check("iron golem: Magic Resistance 100, fire 125", (state["mr"], state["fire"]) == (100, 125), state=state)
        if form == "SPIN154":
            c.p("sh-hurt", 'damage("korgan", 100)')
            time.sleep(0.5)
            points = []
            for i in range(25):
                points.append(c.p(f"sh-regen-{i}", 'form_state("korgan")')["hp"])
                time.sleep(1)
            gains = [b - a for a, b in zip(points, points[1:]) if b > a]
            check("giant troll: regenerates", bool(gains), points=points, gains=gains,
                  per_second=round((points[-1] - points[0]) / 24, 2))
        if form == "CBMSMA":
            check("marilith: Magic Resistance 85, fire 100", (state["mr"], state["fire"]) == (85, 100), state=state)
        if form == "CBMSIS":
            time.sleep(4)
            seen = c.p("sh-stalker-seen", 'form_state("korgan")')
            check("invisible stalker: invisible", seen["state"] % 32 >= 16, state=seen["state"])
    c.p("sh-home", 'cast_now("korgan", "CBMSNAT")')
    time.sleep(8)
    home = c.p("sh-home-state", 'form_state("korgan")')
    check("natural form: own look, no form weapon, no powers, no more invisibility, the forms stay",
          home["anim"] == natural["anim"] and not any(i in home["items"] for i in ("CDMINDFL", "CDGOLIRO", "TROLLALL",
          "CBMSMAW", "CBMSBAW", "CBMSISW")) and not set(home["innates"]) & SHAPE_POWERS
          and home["state"] % 32 < 16 and {"CBMSNAT", *SHAPES} <= set(home["innates"]), home=home, natural=natural)
    c.p("sh-tidy", "remove_all_others()")


def polymorph(c, check):
    # A spawned Korgan without gear or scripts casts Polymorph Self and takes every form in turn: no
    # party member, so no form menu opens. Korgan is a fighter: the game adds his extra attacks to a
    # form's, so attacks are compared between forms.
    c.p("po-clear", "remove_all_others()")
    time.sleep(1.5)
    c.p("po-korgan", 'spawn("KORGAN15", 60, 0)')
    time.sleep(2.5)
    for level in ("OVERRIDE", "CLASS", "RACE", "GENERAL", "DEFAULT"):
        c.p(f"po-script-{level}", f"""order("korgan", 'ChangeAIScript("",{level})')""")
    c.p("po-strip", """order("korgan", 'DestroyAllEquipment()')""")
    time.sleep(2)
    natural = c.p("po-natural", 'form_state("korgan")')
    c.p("po-cast", 'cast_now("korgan", "SPWI416")')
    time.sleep(2)
    cast = c.p("po-after-cast", 'form_state("korgan")')
    granted = set(cast["innates"])
    check("Polymorph Self gives the natural form and the six forms", {"CBMPNAT", *FORMS} <= granted,
          innates=sorted(granted))
    previous, one_attack = None, None
    for form, (anim, strength, extra, dex, apr, weapon, power) in FORMS.items():
        c.p(f"po-{form}", f'cast_now("korgan", "{form}")')
        time.sleep(2.5)
        state = c.p(f"po-{form}-state", 'form_state("korgan")')
        powers = set(state["innates"]) & POWERS
        if one_attack is None:
            one_attack = state["apr"]
        exceptional = extra if extra or strength != 18 else natural["strex"]
        check(f"form {form}: look, body, weapon and powers", state["anim"] == anim and
              (state["str"], state["strex"], state["dex"]) == (strength, exceptional, dex) and
              state["apr"] == one_attack + apr - 1 and weapon in state["items"] and
              powers == ({power} if power else set()) and form in state["innates"],
              state=state, previous=previous)
        previous = form
        if form == "SPWI496":
            check("mustard jelly: Magic Resistance 125", state["mr"] == 125, state=state)
        if form == "CBMPHH":
            check("hell hound: fire 100, cold -50", (state["fire"], state["cold"]) == (100, -50), state=state)
            c.p("po-breath", 'cast_now("korgan", "CBMPHHB")')
            time.sleep(1.5)
            spent = c.p("po-breath-spent", 'form_state("korgan")')
            time.sleep(19)
            back = c.p("po-breath-back", 'form_state("korgan")')
            check("hell hound: Fiery Breath comes back after 3 rounds", "CBMPHHB" not in spent["innates"]
                  and "CBMPHHB" in back["innates"], spent=spent["innates"], back=back["innates"])
    c.p("po-home", 'cast_now("korgan", "CBMPNAT")')
    time.sleep(2.5)
    home = c.p("po-home-state", 'form_state("korgan")')
    check("natural form: own look and body, no form weapon, no powers, the forms stay",
          home["anim"] == natural["anim"] and (home["str"], home["strex"], home["dex"], home["ac"], home["apr"]) ==
          (natural["str"], natural["strex"], natural["dex"], natural["ac"], natural["apr"])
          and not any(i.startswith(("CBMP", "PLY")) for i in home["items"])
          and not set(home["innates"]) & POWERS and {"CBMPNAT", *FORMS} <= set(home["innates"]),
          home=home, natural=natural)
    c.p("po-rat", 'cast_now("korgan", "CBMPRT")')
    time.sleep(2)
    c.p("po-divine", 'cast_now("korgan", "SPPR412")')
    time.sleep(2.5)
    under = c.p("po-divine-state", 'form_state("korgan")')
    check("a form keeps its Strength under Divine Power", (under["str"], under["strex"]) == (10, 0), state=under)
    # The spell runs 1 turn + 3 rounds a level; Korgan casts at level 1: 78 seconds after the cast.
    time.sleep(40)
    end = c.p("po-end-state", 'form_state("korgan")')
    check("the spell ends: natural form, forms and powers gone",
          end["anim"] == natural["anim"] and not ({"CBMPNAT", *FORMS, *POWERS} & set(end["innates"]))
          and not any(i.startswith(("CBMP", "PLY")) for i in end["items"]), end=end)
    c.p("po-tidy", "remove_all_others()")


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
    states_312 = c.p("rc-strength", 'ops("Tasloi", {328})') or []
    info_312 = c.p("rc-str-be", 'being("Tasloi")') or {}
    rows = shown()
    has_floor = bool(GAME and (GAME / "override" / "splstate.ids").exists()
                     and "CBM_STR_FLOOR" in (GAME / "override" / "splstate.ids").read_text(encoding="latin-1"))
    if has_floor:
        check("Strength of One: a stronger target gets the floor entry and keeps Strength 19",
              "Strength" in rows and bool(states_312) and (info_312.get("attributes") or [0])[0] == 19,
              rows=rows, str=(info_312.get("attributes") or [None])[0], effects=states_312)
    else:
        check("Strength of One: who is left out gets neither entry nor spell state",
              "Strength" not in rows and not states_312, rows=rows, effects=states_312)
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


def class_abilities(game, table, level):
    """{resref: times} of the GA_ entries of an ability table up to a level, read from the game."""
    data = game.get(table, "2DA")
    if not data:
        return {}
    lines = [line.split() for line in data.decode("latin-1").splitlines()[2:] if line.strip()]
    levels = [int(x) if x.isdigit() else 0 for x in lines[0]]
    got = {}
    for row in lines[1:]:
        for at, value in zip(levels, row[1:]):
            if 0 < at <= level and value.upper().startswith("GA_"):
                got[value[3:].upper()] = got.get(value[3:].upper(), 0) + 1
    return got


def simulacrum(c, check):
    # Korgan at level 12, a Berserker: Berserker Rage at levels 1, 5 and 9, given here as his levels
    # would (a spawned creature has none). His copy is level 7 and may keep two. An ability of a
    # quest and one of an item must go.
    spec = importlib.util.spec_from_file_location("simulacrum_ie", HERE.parent / "ie.py")
    ie = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ie)
    game = ie.Game(GAME)
    c.p("sm-protect", "protect_party()")
    c.p("sm-clear", "remove_all_others()")
    time.sleep(1)
    c.p("sm-spawn", 'spawn("KORGAN15", 120, 0)')
    time.sleep(2)
    korgan = [o for o in c.p("sm-others", "others()") or [] if o["dv"].upper() == "KORGAN"]
    check("Simulacrum: Korgan is there", len(korgan) == 1, korgan=korgan)
    if len(korgan) != 1:
        return
    original = korgan[0]["id"]
    c.p("sm-rage", 'give_innate("korgan", "SPCL321", 3)')
    c.p("sm-quest", 'give_innate("korgan", "SPIN101", 1)')
    c.p("sm-item", 'give_innate("korgan", "SPIN102", 2)')
    time.sleep(1)
    before = c.p("sm-before", f"innates({original})")
    c.p("sm-cast", """order("korgan", 'ReallyForceSpellRES("SPWI804",Myself)')""")
    time.sleep(13)
    copies = [o for o in c.p("sm-others2", "others()") or [] if o["name"] == "Korgan" and o["id"] != original]
    check("Simulacrum: one copy", len(copies) == 1, copies=copies)
    if len(copies) != 1:
        return
    copy = c.p("sm-copy", f'innates({copies[0]["id"]})')
    after = c.p("sm-after", f"innates({original})")
    for got in (before, copy, after):
        got["ready"] = got["ready"] or {}  # an empty table comes back as a list
    allowed = class_abilities(game, "CLABFI02", copy["levels"][0])
    facts = dict(allowed=allowed, before=before, copy=copy, after=after)
    check("Simulacrum: the copy is lower than the caster", 0 < copy["levels"][0] < before["levels"][0], **facts)
    check("Simulacrum: Berserker Rage stays, as often as its level gives it",
          "SPCL321" in copy["known"] and
          copy["ready"].get("SPCL321", 0) == min(allowed.get("SPCL321", 0), before["ready"].get("SPCL321", 0)), **facts)
    check("Simulacrum: abilities of a quest and an item are gone",
          "SPIN101" not in copy["known"] and "SPIN102" not in copy["known"], **facts)
    check("Simulacrum: the caster keeps everything", all(s in after["known"] for s in ("SPCL321", "SPIN101", "SPIN102")),
          **facts)

    # Spent uses stay spent: Korgan rages twice first, then has one use left; so has his copy.
    c.p("sm-clear2", "remove_all_others()")
    time.sleep(1)
    c.p("sm-spawn2", 'spawn("KORGAN15", 120, 0)')
    time.sleep(2)
    original = [o for o in c.p("sm-others3", "others()") or [] if o["name"] == "Korgan"][0]["id"]
    c.p("sm-rage2", 'give_innate("korgan", "SPCL321", 3)')
    time.sleep(1)
    for i in range(2):
        c.p(f"sm-use-{i}", """order("korgan", 'SpellRES("SPCL321",Myself)')""")
        time.sleep(4)
    spent = c.p("sm-spent", f"innates({original})")
    spent["ready"] = spent["ready"] or {}
    c.p("sm-cast2", """order("korgan", 'ReallyForceSpellRES("SPWI804",Myself)')""")
    time.sleep(13)
    copies = [o for o in c.p("sm-others4", "others()") or [] if o["name"] == "Korgan" and o["id"] != original]
    copy = c.p("sm-copy2", f'innates({copies[0]["id"]})') if copies else None
    if copy:
        copy["ready"] = copy["ready"] or {}
    check("Simulacrum: no more uses than the caster had left",
          copy is not None and spent["ready"].get("SPCL321", 0) < 3 and
          copy["ready"].get("SPCL321", 0) <= spent["ready"].get("SPCL321", 0), spent=spent, copy=copy)
    c.p("sm-tidy", "remove_all_others()")


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


SPELLS_6B0D6A9 = (
    "SPPR105", "SPPR303", "SPPR409", "SPPR412", "SPPR507", "SPPR512", "SPPR513",
    "SPWI101", "SPWI105", "SPWI116", "SPWI120", "SPWI125", "SPWI212", "SPWI213",
    "SPWI215", "SPWI220", "SPWI302", "SPWI304", "SPWI305", "SPWI312", "SPWI315",
    "SPWI326", "SPWI403", "SPWI418", "SPWI503", "SPWI511", "SPWI513", "SPWI603",
    "SPWI605", "SPWI616", "SPWI812",
)

ELEMENTAL_NAMES = (
    ("cbmwla", "Lesser Air Elemental"), ("cbmwa1", "Air Elemental"), ("cbmair1", "Air Elemental"),
    ("cbmwa2", "Greater Air Elemental"), ("cbmair2", "Greater Air Elemental"),
    ("cbmwa3", "Elder Air Elemental"), ("cbmair3", "Elder Air Elemental"),
    ("cbmwle", "Lesser Earth Elemental"), ("cbmwe1", "Earth Elemental"),
    ("cbmwe2", "Greater Earth Elemental"), ("cbmwe3", "Elder Earth Elemental"),
    ("cbmwlf", "Lesser Fire Elemental"), ("cbmwf1", "Fire Elemental"),
    ("cbmwf2", "Greater Fire Elemental"), ("cbmwf3", "Elder Fire Elemental"),
    ("cbmwlw", "Lesser Water Elemental"), ("cbmww1", "Water Elemental"),
    ("cbmww2", "Greater Water Elemental"), ("cbmww3", "Elder Water Elemental"),
)


def scrolls_for_spells(game_dir, spells):
    """Scroll ITM resrefs in override/ whose opcode-147 effect learns one of `spells`."""
    wanted = {s.upper() for s in spells}
    found = {}
    for path in sorted((game_dir / "override").glob("*.itm")):
        data = path.read_bytes()
        if len(data) < 0x72 or data[:8] != b"ITM V1  ":
            continue
        ab_off, ab_cnt, fx_off = struct.unpack_from("<IHI", data, 0x64)
        for a in range(ab_cnt):
            ab = ab_off + a * 0x38
            if ab + 0x22 > len(data):
                break
            cnt, first = struct.unpack_from("<HH", data, ab + 0x1E)
            for k in range(cnt):
                fx = fx_off + (first + k) * 0x30
                if fx + 0x30 <= len(data) and struct.unpack_from("<H", data, fx)[0] == 147:
                    target = data[fx + 0x14:fx + 0x1C].split(b"\0", 1)[0].decode("latin-1").upper()
                    if target in wanted:
                        found[path.stem.upper()] = target
    return found


def unseen(c, check):
    # 1. Grease (SPWI101): 3 rounds + 1 round/level via cbmgr01..cbmgr20 (4, 13, 23 pulses at 100-tick spacing).
    orig_level = c.p("un-gr-lvl0", "level(1)")
    c.p("un-gr-clear1", "remove_all_others()")
    time.sleep(1)
    c.p("un-gr-spawn1", 'spawn("TASLOI01", 140, 0)')
    time.sleep(2)
    c.p("un-gr-pin1", 'pin("Tasloi", 400)')
    c.p("un-gr-take0", "take_grease_log()")
    c.p("un-gr-watch1", 'grease_watch("Tasloi", 60)')
    at1 = c.p("un-gr-at1", 'creature("Tasloi")')
    c.p("un-gr-lvl1", "set_level(1, 1)")
    c.p("un-gr-cast1", f'cast_point(1, "SPWI101", {at1["x"]}, {at1["y"]})')
    time.sleep(32)
    ticks1 = [e["tick"] for e in (c.p("un-gr-log1", "take_grease_log()") or []) if e["who"] == "Tasloi"]
    span1 = (ticks1[-1] - ticks1[0]) if len(ticks1) >= 2 else -1
    check("Grease at caster level 1: 4 rounds (4 pulses, ~300 ticks)",
          len(ticks1) == 4 and 285 <= span1 <= 315, pulses=len(ticks1), span=span1, ticks=ticks1)

    c.p("un-gr-clear2", "remove_all_others()")
    time.sleep(1.5)
    c.p("un-gr-spawn10", 'spawn("HOBGOB01", -240, 0)')
    c.p("un-gr-spawn20", 'spawn("GNOLL01", 140, 0)')
    time.sleep(2.5)
    c.p("un-gr-pin10", 'pin("Gerg", 400)')
    c.p("un-gr-pin20", 'pin("Gnoll", 400)')
    c.p("un-gr-watch10", 'grease_watch("Gerg", 220)')
    c.p("un-gr-watch20", 'grease_watch("Gnoll", 220)')
    at10 = c.p("un-gr-at10", 'creature("Gerg")')
    at20 = c.p("un-gr-at20", 'creature("Gnoll")')
    c.p("un-gr-lvl10", "set_level(1, 10)")
    c.p("un-gr-cast10", f'cast_point(1, "SPWI101", {at10["x"]}, {at10["y"]})')
    time.sleep(2.5)
    c.p("un-gr-lvl20", "set_level(1, 20)")
    c.p("un-gr-cast20", f'cast_point(1, "SPWI101", {at20["x"]}, {at20["y"]})')
    time.sleep(162)
    c.p("un-gr-lvl-restore", f"set_level(1, {orig_level})")
    log2 = c.p("un-gr-log2", "take_grease_log()") or []
    ticks10 = [e["tick"] for e in log2 if e["who"] == "Gerg"]
    ticks20 = [e["tick"] for e in log2 if e["who"] == "Gnoll"]
    span10 = (ticks10[-1] - ticks10[0]) if len(ticks10) >= 2 else -1
    span20 = (ticks20[-1] - ticks20[0]) if len(ticks20) >= 2 else -1
    check("Grease at caster level 10: 13 rounds (13 pulses, ~1200 ticks)",
          len(ticks10) == 13 and 1170 <= span10 <= 1230, pulses=len(ticks10), span=span10)
    check("Grease at caster level 20: 23 rounds (23 pulses, ~2200 ticks)",
          len(ticks20) == 23 and 2160 <= span20 <= 2240, pulses=len(ticks20), span=span20)
    c.p("un-gr-tidy", "remove_all_others()")
    time.sleep(1)

    # 2. Unholy Blight (SPPR314): portrait icon is Cursed (row 35), not Aid / row 208.
    c.p("un-ub-spawn", 'spawn("ACOLYTE2", 120, 0)')
    time.sleep(2)
    others = c.p("un-ub-who", "others()") or []
    good = others[0]["name"] if others else "Dawnbringer Alvanna"
    c.p("un-ub-pin", f'pin("{good}", 120)')
    c.p("un-ub-live", f'fx("{good}", 208, 1, 0, 120)')
    c.p("un-ub-saves", f'set_saves("{good}", {{spell = 20, breath = 20, death = 20}}, 120)')
    time.sleep(0.8)
    c.p("un-ub-cast", f'self_apply("{good}", "SPPR314")')
    time.sleep(2)
    ub_raw = c.p("un-ub-icons", f'icons("{good}")') or []
    ub_rows = sorted(RECORD.get(r, str(r)) for r in ub_raw)
    check("Unholy Blight shows Cursed and not Aid on a good target",
          "Cursed" in ub_rows and "Aid" not in ub_rows and 208 not in ub_raw, raw=ub_raw, rows=ub_rows)
    c.p("un-ub-tidy", "remove_all_others()")
    time.sleep(1)

    # 3. Form weapons of Polymorph Self (SPWI416) and Shapechange (SPWI916) carry no unwanted portrait icon.
    allowed_form_icons = {
        "Increased Movement Rate", "Regenerating", "Protection From Poison",
        "Resist Fear", "Mind Shield", "Negative Plane Protection",
    }
    c.p("un-fw-korgan", 'spawn("KORGAN15", 60, 0)')
    time.sleep(2.5)
    for level in ("OVERRIDE", "CLASS", "RACE", "GENERAL", "DEFAULT"):
        c.p(f"un-fw-scr-{level}", f"""order("korgan", 'ChangeAIScript("",{level})')""")
    c.p("un-fw-strip", """order("korgan", 'DestroyAllEquipment()')""")
    time.sleep(2)
    unwanted_icons, missing_weapons = {}, []
    for spell, home, table in (("SPWI416", "CBMPNAT", FORMS), ("SPWI916", "CBMSNAT", SHAPES)):
        c.p(f"un-fw-cast-{spell}", f'cast_now("korgan", "{spell}")')
        time.sleep(2)
        for form, (_, _, _, _, _, weapon, _) in table.items():
            c.p(f"un-fw-{form}", f'cast_now("korgan", "{form}")')
            time.sleep(2)
            st = c.p(f"un-fw-st-{form}", 'form_state("korgan")')
            raw = c.p(f"un-fw-ic-{form}", 'icons("korgan")') or []
            if weapon not in st["items"]:
                missing_weapons.append((form, weapon, st["items"]))
            bad = [RECORD.get(r, f"ROW_{r}") for r in raw if r == 207 or RECORD.get(r, f"ROW_{r}") not in allowed_form_icons]
            if bad:
                unwanted_icons[form] = bad
        c.p(f"un-fw-home-{spell}", f'cast_now("korgan", "{home}")')
        time.sleep(2.5)
    check("Polymorph Self and Shapechange form weapons show no unwanted portrait or record icon",
          not missing_weapons and not unwanted_icons, missing_weapons=missing_weapons, unwanted_icons=unwanted_icons)
    c.p("un-fw-tidy", "remove_all_others()")
    time.sleep(1.5)

    # 4. Dispel Magic (SPWI326, SPPR303) and Remove Magic (SPWI302) destroy Nishruu and Hakeashar.
    p0 = c.p("un-nh-party", "party()")[0]
    for summon, name, dispel, caster, hostile in (
        ("SPWI624", "Nishruu", "SPWI326", 1, False),
        ("SPWI719", "Hakeashar", "SPPR303", 2, False),
        ("SPWI624", "Nishruu", "SPWI302", 1, True),
        ("SPWI719", "Hakeashar", "SPWI302", 1, True),
    ):
        tag = f"{dispel}-{name[:4]}"
        c.p(f"un-nh-sum-{tag}", f'cast_point(1, "{summon}", {p0["x"] + 120}, {p0["y"]})')
        time.sleep(6.5)
        for lvl in ("OVERRIDE", "CLASS", "RACE", "GENERAL", "DEFAULT"):
            c.p(f"un-nh-scr-{tag}-{lvl}", f"""order("{name}", 'ChangeAIScript("",{lvl})')""")
        if hostile:
            c.p(f"un-nh-foe-{tag}", f"""order("{name}", 'ChangeEnemyAlly(Myself,ENEMY)')""")
            time.sleep(1.5)
        where = c.p(f"un-nh-pin-{tag}", f'pin("{name}", 120)')
        info = c.p(f"un-nh-be-{tag}", f'being("{name}")')
        c.p(f"un-nh-disp-{tag}", f'cast_point({caster}, "{dispel}", {where["x"]}, {where["y"]})')
        time.sleep(4.5)
        left = [o for o in (c.p(f"un-nh-left-{tag}", "others()") or []) if o["name"] == name]
        label = "Remove Magic (SPWI302)" if hostile else f"Dispel Magic ({dispel})"
        check(f"{label} destroys {'hostile ' if hostile else ''}summoned {name} (specific 25)",
              bool(info) and info["specific"] == 25 and not left, specific=info and info["specific"], left=left)
        c.p(f"un-nh-tidy-{tag}", "remove_all_others()")
        time.sleep(1)

    # 5. Live Spellbook UI (MAGE and PRIEST), Find Familiar (SPWI123 / SCRL6D), synced scrolls, and elementals.
    defs_dir = HERE.parents[1] / "defs"
    norm = lambda s: (s or "").replace("\r\n", "\n").strip()  # noqa: E731

    def desc_pattern(template):
        parts = []
        for token in re.split(r"(<[A-Z0-9_]+>|[^\x00-\x7f]+)", norm(template)):
            if not token:
                continue
            if token.startswith("<") and token.endswith(">"):
                parts.append(r"[A-Za-z']+")
            elif any(ord(ch) > 127 for ch in token):
                parts.append(r"\S+")
            else:
                parts.append(re.escape(token))
        return re.compile("^" + "".join(parts) + "$", re.S)

    expected_desc, expected_re = {}, {}
    for res in SPELLS_6B0D6A9:
        raw = json.loads((defs_dir / f"{res.lower()}.spl.json").read_text(encoding="utf-8"))
        expected_desc[res] = norm(raw["header"]["description"]["text"])
        expected_re[res] = desc_pattern(expected_desc[res])
    scrl6d_def = json.loads((defs_dir / "scrl6d.itm.json").read_text(encoding="utf-8"))
    expected_desc["SPWI123"] = norm(scrl6d_def["header"]["description_identified"]["text"])
    expected_re["SPWI123"] = desc_pattern(expected_desc["SPWI123"])

    wiz_spells = sorted(r for r in expected_desc if r.startswith("SPWI"))
    pri_spells = sorted(r for r in expected_desc if r.startswith("SPPR"))
    c.p("un-bk-learnw", f"learn_wizard(1, {lua_strings(wiz_spells)})")
    c.p("un-bk-learnp", f"learn_priest(2, {lua_strings(pri_spells)})")
    time.sleep(1)
    c.p("un-bk-openw", 'book_open("mage", 1)')
    time.sleep(1.2)
    mage_book = c.p("un-bk-readw", 'book_read("mage")') or {}
    time.sleep(0.8)
    c.p("un-bk-openp", 'book_open("priest", 2)')
    time.sleep(1.2)
    priest_book = c.p("un-bk-readp", 'book_read("priest")') or {}
    time.sleep(0.8)

    bad_book = {}
    for res in wiz_spells:
        entry = mage_book.get(res)
        if not entry or norm(entry["desc"]) != norm(entry["pane"]) or not expected_re[res].match(norm(entry["pane"])):
            bad_book[res] = None if not entry else {"got": norm(entry["pane"])[:120]}
    for res in pri_spells:
        entry = priest_book.get(res)
        if not entry or norm(entry["desc"]) != norm(entry["pane"]) or not expected_re[res].match(norm(entry["pane"])):
            bad_book[res] = None if not entry else {"got": norm(entry["pane"])[:120]}
    check("Mage Book and Priest Scroll show the new descriptions for all 31 spells and Find Familiar",
          not bad_book, checked=len(expected_desc), mismatches=bad_book)

    fam_hp = {
        **{f"FAM{k}_": 12 for k in ("CAT", "DUST", "FAIR", "FER", "PSD", "QUAS", "RAB")}, "FAMIMP_": 9,
        **{f"FAM{k}": 24 for k in ("CAT", "DUST", "FAIR", "FER", "PSD", "QUAS", "RAB")}, "FAMIMP": 18,
        **{f"FAM{k}25": 48 for k in ("CAT", "DUS", "FAI", "FER", "IMP", "PSD", "QUA", "RAB")},
    }
    scroll_map = scrolls_for_spells(GAME, wiz_spells)
    meta = c.p("un-meta", f"res_meta({lua_strings(sorted(expected_desc))}, {lua_strings(sorted(scroll_map))}, "
                          f"{lua_strings(sorted(fam_hp))})")
    bad_scrolls = {}
    for scrl, target in scroll_map.items():
        got_itm = meta["items"].get(scrl)
        got_spl = meta["spells"].get(target)
        if (not got_itm or not got_spl or norm(got_itm["desc"]) != norm(got_spl["desc"])
                or not expected_re[target].match(norm(got_itm["desc"]))):
            bad_scrolls[scrl] = {"spell": target, "present": bool(got_itm)}
    ff_spl = meta["spells"].get("SPWI123") or {}
    ff_itm = meta["items"].get("SCRL6D") or {}
    check("Synced scrolls match their wizard spell descriptions in the running game",
          bool(scroll_map) and "SCRL6D" in scroll_map and not bad_scrolls,
          scrolls=len(scroll_map), mismatches=bad_scrolls)
    check("Find Familiar and SCRL6D: Universal school, specialist exclusions cleared, 3-campaign text",
          ff_spl.get("school") == 0 and (ff_spl.get("excl", 0xFFFF) & 0x3FC0) == 0
          and (ff_itm.get("u3", 0xFF) & 0x3F) == 0 and (ff_itm.get("u4", 0xFF) & 0xC0) == 0
          and "Baldur's Gate and Siege of Dragonspear" in norm(ff_spl.get("desc"))
          and norm(ff_spl.get("desc")) == norm(ff_itm.get("desc")),
          spwi123={k: ff_spl.get(k) for k in ("school", "excl")},
          scrl6d={k: ff_itm.get(k) for k in ("u3", "u4")})

    bad_fam_cre = {cre: got for cre, got in (meta.get("cres") or {}).items()
                   if (got["cur_hp"], got["max_hp"]) != (fam_hp[cre], fam_hp[cre])}
    spawned_fam = {}
    for cre in ("FAMIMP", "FAMPSD", "FAMPSD25"):
        c.p(f"un-fam-sp-{cre}", f'spawn("{cre}", 120, 0)')
        time.sleep(0.9)
        others = c.p(f"un-fam-ot-{cre}", "others()") or []
        spawned_fam[cre] = others[0]["hp"] if others else None
        c.p(f"un-fam-rm-{cre}", "remove_all_others()")
        time.sleep(0.5)
    check("Campaign familiar creatures have their pinned Hit Points in the game",
          len(meta.get("cres") or {}) >= 16 and not bad_fam_cre
          and spawned_fam == {"FAMIMP": 18, "FAMPSD": 24, "FAMPSD25": 48},
          checked=len(meta.get("cres") or {}), mismatches=bad_fam_cre, spawned=spawned_fam)

    bad_elem = {}
    for cre, wanted in ELEMENTAL_NAMES:
        c.p(f"un-el-sp-{cre}", f'spawn("{cre.upper()}", 120, 0)')
        time.sleep(0.9)
        seen = [o["name"] for o in (c.p(f"un-el-ot-{cre}", "others()") or [])]
        if seen != [wanted]:
            bad_elem[cre] = {"wanted": wanted, "seen": seen}
        c.p(f"un-el-rm-{cre}", "remove_all_others()")
        time.sleep(0.5)
    check("All 19 summoned elemental creatures carry their size-by-HD names in the game",
          not bad_elem, checked=len(ELEMENTAL_NAMES), mismatches=bad_elem)

    # 6. Priest Slow Poison (SPPR212): cures active opcode-25 poison immediately instead of slowing it.
    c.p("un-sp-heal0", 'on_member(0, "SPPR607")')
    time.sleep(1.5)
    hp_start = c.p("un-sp-hp0", "stats(0)")["hp"]
    c.p("un-sp-psn", "fx(0, 25, 2, 2, 30)")
    time.sleep(2.5)
    hp_poisoned = c.p("un-sp-hp1", "stats(0)")["hp"]
    ops_before = c.p("un-sp-ops0", "ops(0, {25, 329})") or []
    c.p("un-sp-cure", 'on_member(0, "SPPR212")')
    time.sleep(1.5)
    hp_cured = c.p("un-sp-hp2", "stats(0)")["hp"]
    ops_after = c.p("un-sp-ops1", "ops(0, {25, 329})") or []
    time.sleep(4.0)
    hp_later = c.p("un-sp-hp3", "stats(0)")["hp"]
    c.p("un-sp-heal1", 'on_member(0, "SPPR607")')
    time.sleep(1.2)
    check("Slow Poison (SPPR212) cures active poison immediately with no opcode-329 slowing",
          hp_poisoned <= hp_start - 2 and any(e["op"] == 25 for e in ops_before)
          and not ops_after and hp_later == hp_cured,
          hp=[hp_start, hp_poisoned, hp_cured, hp_later], before=ops_before, after=ops_after)


BONUS_SYMBOLS = {
    "bless": "CLERIC_BLESS", "prayer": "CLERIC_PRAYER", "recitation": "CLERIC_RECITATION",
    "hope": "WIZARD_EMOTION_HOPE", "luck": "WIZARD_LUCK", "doom": "CLERIC_DOOM",
    "curse": "CLERIC_CURSE", "blight": "CLERIC_UNHOLY_BLIGHT", "pierce": "WIZARD_PIERCE_MAGIC",
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
         "rest and change areas, then compare fresh CBMP.bonus_snapshot(0) values for 60 seconds "
         "(automated in tests/lab/run_player1.py).", "status": "covered_in_run_player1"},
        {"group": "bonus", "check": "Equip an actual item granting +1 to a tested value (RING06) and confirm "
         "it adds to the corrected spell total.", "status": "automated"},
        {"group": "bonus", "check": "Capture the character sheet with the five-spell combination and after "
         "Recitation expires, showing the corrected totals.", "status": "not_run"},
        {"group": "bonus", "check": "In a separate disposable installation without EEex, verify ordinary "
         "stacking and self-refresh and one Lua fallback message. This EEex-console runner cannot run there.", "status": "not_run"},
        {"group": "bonus", "check": "Verify ordinary spellbook casting and projectile targeting; direct "
         "ApplySpellRES below tests installed effects and nested delivery only.", "status": "not_run"},
        {"group": "bonus", "check": "Apply Unholy Blight, Doom, and a weaker Curse penalty to an eligible good "
         "target and verify non-stacking, expiry fallback, and evil-target exclusion (SPPR314 delivers direct "
         "CBTCURSE effects; M_CBMBON.lua's opcode-177 external-EFF path is covered by offline Lua unit tests).", "status": "automated"},
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

    # Blood Rage requires an allied non-lawful humanoid, so its family pairs run on KORGAN15 below.
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

    # Real equipped item (+1 saves and AC from RING06) adds to the corrected Favor spell total.
    if need("bless"):
        clear(0, all_keys)
        base = snap(0)
        apply(0, "bless")
        if "recitation" in BONUS:
            apply(0, "recitation")
        else:
            c.p("bo-ring-fav2", f'bonus_fx(0, 325, 2, 0, "CBTFAVOR", {state}, 180)')
        typed = snap(0)
        c.p("bo-ring-give", """order_party(0, 'CreateItem("RING06",1,0,0)')""")
        time.sleep(1.2)
        c.p("bo-ring-eq", """order_party(0, 'XEquipItem("RING06",Myself,SLOT_RING_LEFT,EQUIP)')""")
        time.sleep(2.2)
        items_on = c.p("bo-ring-items", "form_state(0)")["items"]
        equipped = snap(0)
        check("Bonus: real equipped RING06 (+1 saves, +1 AC) stacks with highest Favor +2",
              "RING06" in items_on
              and typed["saves"] == [v - 2 for v in base["saves"]]
              and equipped["saves"] == [v - 1 for v in typed["saves"]]
              and equipped["ac"] == typed["ac"] - 1,
              items=items_on, base=bonus_values(base), typed=bonus_values(typed), equipped=bonus_values(equipped))
        c.p("bo-ring-drop", """order_party(0, 'DestroyItem("RING06")')""")
        time.sleep(1.5)
        c.p("bo-ring-fxclear", 'bonus_clear(0, {"CBMQLAB"})')
        clear(0, tuple(k for k in ("bless", "recitation") if k in BONUS))

    # Unholy Blight (SPPR314), Doom (SPPR113), and a weaker -1 Curse on an eligible good target vs evil target.
    if need("blight", "doom"):
        blight_res = BONUS["blight"]["res"]
        c.p("bo-ub-clear0", "remove_all_others()")
        time.sleep(1)
        c.p("bo-ub-spawn", 'spawn("ACOLYTE2", 120, 0)')
        time.sleep(2)
        others = c.p("bo-ub-who", "others()") or []
        good = others[0]["name"] if others else "Dawnbringer Alvanna"
        for lvl in ("OVERRIDE", "CLASS", "RACE", "GENERAL", "DEFAULT"):
            c.p(f"bo-ub-scr-{lvl}", f"""order({json.dumps(good)}, 'ChangeAIScript("",{lvl})')""")
        time.sleep(1)
        c.p("bo-ub-pin", f'pin({json.dumps(good)}, 600)')
        c.p("bo-ub-live", f'fx({json.dumps(good)}, 208, 1, 0, 600)')
        c.p("bo-ub-saves", f'set_saves({json.dumps(good)}, {{spell = 20}}, 600)')
        time.sleep(1)
        base_g = snap(good)
        if "curse" in BONUS:
            apply(good, "curse")
        else:
            c.p("bo-ub-c1", f'bonus_fx({json.dumps(good)}, 54, -1, 0, "CBTCURSE", {state}, 180)')
            c.p("bo-ub-c2", f'bonus_fx({json.dumps(good)}, 325, -1, 0, "CBTCURSE", {state}, 180)')
        weaker_g = snap(good)
        for _ in range(4):
            apply(good, "doom")
            with_doom = snap(good)
            if relevant(with_doom, "doom"):
                break
        for _ in range(4):
            c.p("bo-ub-cast", f'self_apply({json.dumps(good)}, {json.dumps(blight_res)})')
            time.sleep(2.2)
            all_three = snap(good)
            if relevant(all_three, "blight"):
                break
        check("Bonus: Unholy Blight, Doom, and Curse on a good target apply only the worst -2 Curse",
              bool(relevant(all_three, "blight")) and bool(relevant(all_three, "doom"))
              and weaker_g["thac0"] == base_g["thac0"] + 1
              and weaker_g["saves"][1:3] == [v + 1 for v in base_g["saves"][1:3]]
              and all_three["thac0"] == base_g["thac0"] + 2
              and all_three["saves"][1:3] == [v + 2 for v in base_g["saves"][1:3]],
              has_blight=bool(relevant(all_three, "blight")), has_doom=bool(relevant(all_three, "doom")),
              thac0=[base_g["thac0"], weaker_g["thac0"], all_three["thac0"]],
              wand_poly=[base_g["saves"][1:3], weaker_g["saves"][1:3], all_three["saves"][1:3]])
        changed_b = expire(good, "blight")
        changed_d = expire(good, "doom")
        resumed_g = snap(good)
        check("Bonus: weaker -1 Curse resumes when Unholy Blight and Doom expire",
              changed_b > 0 and changed_d > 0
              and not relevant(resumed_g, "blight") and not relevant(resumed_g, "doom")
              and resumed_g["thac0"] == weaker_g["thac0"]
              and resumed_g["saves"][1:3] == weaker_g["saves"][1:3],
              changed=[changed_b, changed_d],
              thac0=[all_three["thac0"], resumed_g["thac0"]], saves=resumed_g["saves"][1:3])
        c.p("bo-ub-tidy1", "remove_all_others()")
        time.sleep(1)

        c.p("bo-ub-evil", 'spawn("TASLOI01", 120, 0)')
        time.sleep(2)
        c.p("bo-ub-epin", 'pin("Tasloi", 300)')
        c.p("bo-ub-elive", 'fx("Tasloi", 208, 1, 0, 300)')
        c.p("bo-ub-esaves", 'set_saves("Tasloi", {spell = 20}, 300)')
        time.sleep(1)
        evil_base = snap("Tasloi")
        c.p("bo-ub-ecast", f'self_apply("Tasloi", {json.dumps(blight_res)})')
        time.sleep(2.2)
        evil_after = snap("Tasloi")
        check("Bonus: Unholy Blight adds no Curse payload on an ineligible evil target",
              not relevant(evil_after, "blight") and bonus_values(evil_after) == bonus_values(evil_base),
              before=bonus_values(evil_base), after=bonus_values(evil_after))
        c.p("bo-ub-tidy2", "remove_all_others()")
        time.sleep(1)

    # Live Blood Rage (IWDification SPPR421): requires an allied non-lawful humanoid (KORGAN15).
    if "blood" in BONUS:
        c.p("bo-br-clear0", "remove_all_others()")
        time.sleep(1)
        c.p("bo-br-spawn", 'spawn("KORGAN15", 180, 0)')
        time.sleep(2.5)
        for lvl in ("OVERRIDE", "CLASS", "RACE", "GENERAL", "DEFAULT"):
            c.p(f"bo-br-scr-{lvl}", f"""order("korgan", 'ChangeAIScript("",{lvl})')""")
        c.p("bo-br-strip", """order("korgan", 'DestroyAllEquipment()')""")
        c.p("bo-br-ally", """order("korgan", 'ChangeEnemyAlly(Myself,ALLY)')""")
        c.p("bo-br-live", 'fx("korgan", 208, 1, 0, 900)')
        c.p("bo-br-slow", 'fx("korgan", 126, 0, 1, 900)')
        time.sleep(2)

        if "hope" in BONUS:
            c.p("bo-br-str25", 'bonus_fx("korgan", 44, 25, 1, "", nil, 600)')
            time.sleep(1)
            base_k = snap("korgan")
            c.p("bo-br-hope", f'cast_now("korgan", {json.dumps(BONUS["hope"]["res"])})')
            time.sleep(2)
            hope_k = snap("korgan")
            c.p("bo-br-cast", f'cast_now("korgan", {json.dumps(BONUS["blood"]["res"])})')
            time.sleep(2.5)
            both_k = snap("korgan")
            check("Bonus: Blood Rage lands on an allied non-lawful target and does not stack Morale with Emotion: Hope",
                  bool(relevant(hope_k, "hope")) and bool(relevant(both_k, "hope")) and bool(relevant(both_k, "blood"))
                  and hope_k["thac0"] == base_k["thac0"] - 2 and hope_k["dmg"] == base_k["dmg"] + 2
                  and both_k["thac0"] == base_k["thac0"] - 2 and both_k["dmg"] == base_k["dmg"] + 3,
                  base=bonus_values(base_k), hope=bonus_values(hope_k), both=bonus_values(both_k))
            clear("korgan", ("hope", "blood"))
            c.p("bo-br-unstr", 'bonus_clear("korgan", {"CBMQLAB"})')

        tr_keys = [k for k in ("tenser", "divine", "righteous", "champion", "blood", "animal") if k in BONUS]
        for other in tr_keys:
            if other == "blood":
                continue
            for old, new in (("blood", other), (other, "blood")):
                clear("korgan", tr_keys)
                c.p(f"bo-br-old-{old}-{new}", f'cast_now("korgan", {json.dumps(BONUS[old]["res"])})')
                time.sleep(2.2)
                before_k = snap("korgan")
                c.p(f"bo-br-new-{old}-{new}", f'cast_now("korgan", {json.dumps(BONUS[new]["res"])})')
                time.sleep(2.2)
                after_k = snap("korgan")
                winner = new if BONUS[new]["level"] >= BONUS[old]["level"] else old
                loser = old if winner == new else new
                check(f"Transformation (Blood Rage): {old} then {new} keeps {winner}",
                      bool(relevant(before_k, old)) and bool(relevant(after_k, winner))
                      and not relevant(after_k, loser),
                      levels={old: BONUS[old]["level"], new: BONUS[new]["level"]})
        clear("korgan", tr_keys)
        c.p("bo-br-tidy1", "remove_all_others()")
        time.sleep(1)

        c.p("bo-br-keld", 'spawn("KELDOR10", 180, 0)')
        time.sleep(2.5)
        for lvl in ("OVERRIDE", "CLASS", "RACE", "GENERAL", "DEFAULT"):
            c.p(f"bo-br-kscr-{lvl}", f"""order("keldorn", 'ChangeAIScript("",{lvl})')""")
        c.p("bo-br-kally", """order("keldorn", 'ChangeEnemyAlly(Myself,ALLY)')""")
        c.p("bo-br-klive", 'fx("keldorn", 208, 1, 0, 300)')
        time.sleep(2)
        keld_info = c.p("bo-br-kinfo", 'being("keldorn")')
        c.p("bo-br-lawcast", f'cast_now("keldorn", {json.dumps(BONUS["blood"]["res"])})')
        time.sleep(2.2)
        lawful_k = snap("keldorn")
        check("Blood Rage spares an allied Lawful target",
              keld_info["alignment"] == 0x11 and not relevant(lawful_k, "blood"),
              alignment=keld_info["alignment"], ea=keld_info["ea"], effects=lawful_k["effects"])
        c.p("bo-br-tidy", "remove_all_others()")
        time.sleep(1)


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
    if "floor" in selected and "--game" in args:
        global MIGHT, ANIMAL
        ids = (Path(args[args.index("--game") + 1]) / "override" / "spell.ids")
        text = ids.read_text(encoding="latin-1") if ids.exists() else ""
        found = {symbol: re.search(rf"^\s*(\d+)\s+{symbol}\s*$", text, re.M)
                 for symbol in ("CLERIC_DRAW_UPON_HOLY_MIGHT", "CLERIC_ANIMAL_RAGE")}
        MIGHT, ANIMAL = (f"SPPR{int(m[1]) % 1000:03d}" if m else None for m in found.values())
    if "decided" in selected and "--game" in args:
        global AIR, LANCE
        game = Path(args[args.index("--game") + 1])
        AIR = added_spell(game, "CLERIC_CBMAGIC_CONJURE_AIR_ELEMENTAL")
        LANCE = added_spell(game, "CLERIC_CBMAGIC_ICELANCE")
    if "attacks" in selected and "--game" in args:
        WRATH = wrath_payload(Path(args[args.index("--game") + 1]))
    if {"record", "live", "unseen"} & set(selected) and "--game" in args:
        record_rows(Path(args[args.index("--game") + 1]))
    sys.argv = [sys.argv[0], *args]
    rp.GROUPS = GROUPS
    rp.run_checks = run_checks
    return rp.main()


if __name__ == "__main__":
    sys.exit(main())
