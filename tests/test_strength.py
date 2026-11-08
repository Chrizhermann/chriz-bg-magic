"""Strength floors: a spell of this mod that gives a fixed Strength never lowers a higher one, and
bonuses and penalties from other sources count on top of it (lua/M_CBMSTR.lua). Real WeiDU installs
into made-up games, the definitions themselves, and the Lua under mocked engines.
"""
import copy
import importlib
import re
from pathlib import Path

import fakegame as fg
import fixtures as fx
import ie
from harness import check, test
from test_resources import ALT, check_every_resource, definitions, install

EEEX = {"M___EEex.lua": b"-- synthetic EEex bootstrap\n"}
FLOORS = {"spwi214.spl": 18000, "sppr312.spl": 18075, "sppr412.spl": 18100, "sppr507.spl": 18100}
STATE = {"state": "CBM_STR_FLOOR"}


def all_effects(defn):
    return [e for a in defn.get("abilities", []) for e in a["effects"]] + list(defn.get("casting", []))


def is_floor(e):
    return e["opcode"] == 44 and e["resource"] == "CBTSTRF"


@test
def strength_floor_definitions(work, weidu):
    """Each floor spell carries the marker with its value and the spell state beside it, and sets no
    Strength itself; its version without EEex sets Strength as the game does and is otherwise the
    same spell."""
    main, alt = definitions(), definitions(ALT)
    for name, value in FLOORS.items():
        for number, ability in enumerate(main[name]["abilities"]):
            effects = ability["effects"]
            floors = [i for i, e in enumerate(effects) if is_floor(e)]
            check(len(floors) == 1, f"{name} ability {number}: {len(floors)} floors")
            mark, state = effects[floors[0]], effects[floors[0] + 1]
            check((mark["p1"], mark["p2"], mark["special"]) == (0, 0, value), f"{name}: marker {mark}")
            check(state["opcode"] == 328 and state["p2"] == STATE and state["special"] == 1
                  and (state["duration"], state["target"], state["timing"]) ==
                  (mark["duration"], mark["target"], mark["timing"]), f"{name}: state {state}")
            check(not any(e["opcode"] in (44, 97) and e["p2"] == 1 for e in effects), f"{name}: still sets Strength")
        check(not any(is_floor(e) or e["p2"] == STATE for e in all_effects(alt[name])), f"{name}: floor without EEex")
        check(any(e["opcode"] == 44 and e["p2"] == 1 for e in all_effects(alt[name]) + all_effects(alt["sppr312a.spl"])),
              f"{name}: the version without EEex does not set Strength")
    check("not lowered" in main["sppr312.spl"]["header"]["description"]["text"], "Strength of One's text")
    # Apart from Strength and text the two versions are one spell (Strength of One without EEex
    # keeps its sub-spell and is checked in game).
    for name in ("spwi214.spl", "sppr412.spl", "sppr507.spl", "scrl98.itm"):
        def plain(defn):
            out = copy.deepcopy(defn)
            for key in ("description", "description_identified"):
                out["header"].pop(key, None)
            for ability in out.get("abilities", []):
                ability["effects"] = [e for e in ability["effects"]
                                      if not (is_floor(e) or e["p2"] == STATE or (e["opcode"] in (44, 97) and e["p2"] == 1))]
            return out
        check(plain(main[name]) == plain(alt[name]), f"{name}: the two versions differ in more than Strength")


# The Transformation family links its members to the game's Animal Rage.
FAMILY = ("sppr507.spl", "sppr513.spl", "spwi603.spl")
ANIMAL_RAGE = ie.make_spl(2, 5, [{"target": 1, "effects": [
    fx.fx(opcode=18, target=2, power=5, p1=20, duration=90, dispel=3),
    fx.fx(opcode=44, target=2, power=5, p1=19, p2=1, duration=90, dispel=3),
    fx.fx(opcode=97, target=2, power=5, p1=40, p2=1, duration=90, dispel=3),
    fx.fx(opcode=142, target=2, power=5, p2=227, duration=90, dispel=3)]}], desc=1)


@test
def strength_floor_without_and_with_eeex(work, weidu):
    """Without EEex the floor spells set Strength as the game does and the log says why; with EEex
    they carry the marker, the module knows the state, and IWDification's Animal Rage gets its floor
    in whatever slot this game gave it."""
    biff = fx.game(SPELL_IDS=fx.spell_ids([(1522, "CLERIC_ANIMAL_RAGE")]), SPPR522_SPL=ANIMAL_RAGE)
    g = fg.FakeGame(work / "plain", weidu, tlk=fx.tlk(), biff=biff)
    out = install(g)
    check("sppr412.spl is written without its new rule, which needs EEex" in out, out)
    check(g.file("override/M_CBMSTR.lua") is None, "the module without EEex")
    divine = [e for a in g.spl("SPPR412")["abilities"] for e in a["effects"]]
    check(any(e["opcode"] == 44 and (e["p1"], e["p2"]) == (18, 1) for e in divine), "Divine Power without EEex")
    check(not any(e["resource"] == "CBTSTRF" for e in divine), "a floor without EEex")
    check(g.file("override/SPPR312A.SPL") is not None, "Strength of One's guarded sub-spell")
    rage = [e for a in g.spl("SPPR522")["abilities"] for e in a["effects"]]
    check([(e["opcode"], e["p1"], e["p2"]) for e in rage if e["opcode"] in (44, 97)] == [(44, 19, 1), (97, 40, 1)]
          and not any(e["resource"] == "CBTSTRF" for e in rage), f"Animal Rage without EEex: {rage}")
    check_every_resource(g, derived=FAMILY)

    g = fg.FakeGame(work / "eeex", weidu, tlk=fx.tlk(), biff=biff, override=EEEX)
    install(g)
    check_every_resource(g, derived=FAMILY)
    lua = g.file("override/M_CBMSTR.lua").decode("utf-8")
    state = int(re.search(r"local FLOOR_STATE = (\d+)", lua)[1])
    check("%CBM_STR_FLOOR_STATE%" not in lua and "FLOOR_STATE % 32" in lua, "the state was not filled in")
    ids = g.file("override/splstate.ids").decode("latin-1")
    check(re.search(rf"^{state}\s+CBM_STR_FLOOR\s*$", ids, re.M), "the state is not in SPLSTATE.IDS")
    for name, value in FLOORS.items():
        effects = [e for a in g.spl(name.split(".")[0].upper())["abilities"] for e in a["effects"]]
        floors = [e for e in effects if e["resource"] == "CBTSTRF"]
        check(floors and all(e["special"] == value for e in floors), f"{name}: {floors[:2]}")
        states = [e for e in effects if e["opcode"] == 328 and e["p2"] == state]
        check(len(states) == len(floors) and all((s["duration"], s["target"], s["special"]) ==
                                                 (f["duration"], f["target"], 1) for s, f in zip(states, floors)),
              f"{name}: states {states[:2]}")
    check(g.file("override/SPPR312A.SPL") is None, "Strength of One's sub-spell with EEex")
    rage = [e for a in g.spl("SPPR522")["abilities"] for e in a["effects"]]
    check(not any(e["opcode"] in (44, 97) and e["p2"] == 1 for e in rage), f"Animal Rage still sets Strength: {rage}")
    marks = [e for e in rage if e["resource"] == "CBTSTRF"]
    states = [e for e in rage if e["opcode"] == 328 and e["p2"] == state]
    check(len(marks) == 1 and len(states) == 1, f"Animal Rage: {[(e['opcode'], e['resource']) for e in rage]}")
    mark, mark_state = marks[0], states[0]
    check((mark["p1"], mark["p2"], mark["special"], mark["resource"], mark["duration"], mark["power"], mark["dispel"])
          == (0, 0, 19000, "CBTSTRF", 90, 5, 3), f"Animal Rage's floor: {mark}")
    check((mark_state["p2"], mark_state["special"], mark_state["duration"]) == (state, 1, 90), f"its state: {mark_state}")
    check("Strength score of 19 unless it is already higher" in g.tlk(g.spl("SPPR522")["desc"]), "Animal Rage's text")
    installed = g.tree()
    install(g)
    check(g.tree() == installed, "a second install changed the game")


@test
def strength_lua_runtime_lua53_and_luajit(work, weidu):
    template = (fg.MOD / "lua/M_CBMSTR.lua").read_text(encoding="utf-8")
    suite = (Path(__file__).parent / "strength_runtime.lua").read_text(encoding="utf-8")
    for implementation in ("lupa.lua53", "lupa.luajit21"):
        runtime = importlib.import_module(implementation).LuaRuntime()
        count = runtime.execute(suite)(template)
        check(count >= 37, f"{implementation}: only {count} runtime checks ran")
