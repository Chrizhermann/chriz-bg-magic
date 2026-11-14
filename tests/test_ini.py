"""Offline WeiDU and Lua tests for the 3-tier chriz-bg-magic.ini system."""
import importlib
from pathlib import Path

import fakegame as fg
import fixtures as fx
import ie
from harness import check, test

EEEX_LUA = {"M___EEex.lua": b"-- synthetic EEex bootstrap\n"}
IGNORED_TREE_PREFIXES = ("weidu_external/",)
IGNORED_TREE_EXACT = {"chriz-bg-magic.ini", "SETUP-CHRIZ-BG-MAGIC.DEBUG"}


def effect(opcode, p1=0, **kw):
    return {**ie.FX_DEFAULTS, "opcode": opcode, "p1": p1, **kw}


def make_scroll(resref, desc=1):
    return ie.make_itm(
        [[effect(146, target=2, timing=1, resource=resref), effect(147, target=2, timing=1, resource=resref)]],
        desc=desc,
        desc_unid=desc,
    )


def make_spell(ct=9, range_=30, duration=60, desc=1):
    return ie.make_spl(
        abilities=[{
            "target": 4,
            "range": range_,
            "min_level": 1,
            "casting_time": ct,
            "effects": [effect(142, duration=duration)],
        }],
        desc=desc,
    )


def ids_map(g):
    out = {}
    for line in ie.Game(g.root).get("SPELL", "IDS").decode("ascii").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                out[parts[1].upper()] = int(parts[0], 0)
            except ValueError:
                pass
    return out


def spl_effects(g, resref, ability=0):
    return g.spl(resref)["abilities"][ability]["effects"]


def spl_ability_headers(g, resref):
    data = ie.Game(g.root).get(resref, "SPL")
    ab_off = int.from_bytes(data[0x64:0x68], "little")
    ab_cnt = int.from_bytes(data[0x68:0x6A], "little")
    out = []
    for idx in range(ab_cnt):
        o = ab_off + idx * 0x28
        out.append({
            "range": int.from_bytes(data[o + 0x0E:o + 0x10], "little"),
            "min_level": int.from_bytes(data[o + 0x10:o + 0x12], "little"),
            "casting_time": int.from_bytes(data[o + 0x12:o + 0x14], "little"),
        })
    return out


def itm_first_ability_range(g, resref):
    data = ie.Game(g.root).get(resref, "ITM")
    ab_off = int.from_bytes(data[0x64:0x68], "little")
    return int.from_bytes(data[ab_off + 0x0E:ab_off + 0x10], "little")


def cre_override_script(g, resref):
    data = ie.Game(g.root).get(resref, "CRE")
    return data[0x248:0x250].split(b"\x00", 1)[0].decode("ascii").upper()


def base_biff(extra=None):
    resources = {
        "TRIGGER.IDS": ie.make_ids([
            (0x400A, "Alignment(O:Object*,I:Alignment*Align)"),
            (0x400B, "Allegiance(O:Object*,I:Allegience*EA)"),
            (0x400F, "Global(S:Name*,S:Area*,I:Value*)"),
        ]),
        "ACTION.IDS": ie.make_ids([
            (30, "SetGlobal(S:Name*,S:Area*,I:Value*)"),
            (36, "Continue()"),
            (60, "ChangeAIScript(S:ScriptFile*,I:Level*Scrlev)"),
        ]),
        "OBJECT.IDS": ie.make_ids([(1, "Myself")]),
        "EA.IDS": ie.make_ids([(30, "GOODCUTOFF")]),
        "ALIGNMEN.IDS": ie.make_ids([(1, "MASK_GOOD")]),
        "SCRLEV.IDS": ie.make_ids([(4, "CLASS")]),
        "SPIN682.SPL": make_spell(ct=1, range_=0, duration=18),
        "SPWI212.SPL": make_spell(ct=2, range_=0, duration=18),
        "SPWI120.SPL": make_spell(ct=1, range_=0, duration=18),
        "SCRL1B.ITM": make_scroll("SPPR103"),
        "SCRLBLS.ITM": make_scroll("SPPR101"),
        "SCRLDOM.ITM": make_scroll("SPPR113"),
        "SCRLDS.ITM": make_scroll("SPWI510"),
        "SCRLPM.ITM": make_scroll("SPWI608"),
        "SCRLIH.ITM": make_scroll("SPWI613"),
        "SCRLST.ITM": make_scroll("SPWI313"),
        "SCRLPLN.ITM": make_scroll("SPWI923"),
        **(extra or {}),
    }
    return fx.game(**resources)


def normalized_game_tree(tree):
    return {
        k: v
        for k, v in tree.items()
        if k not in IGNORED_TREE_EXACT and not any(k.startswith(p) for p in IGNORED_TREE_PREFIXES)
    }


def test_pierce_callback_in_lua(lua_text, mr_value):
    # Strip bonus_runtime.lua-style listener registration requirements by running M_CBMBON.lua in a sandboxed table.
    prelude = """
    return function(code, mr)
        local logs, applied = {}, {}
        local env
        env = {
            math = math, string = string, table = table, pairs = pairs, ipairs = ipairs,
            type = type, pcall = pcall, tonumber = tonumber, tostring = tostring,
            assert = assert, error = error, next = next, setmetatable = setmetatable,
            print = function(msg) logs[#logs + 1] = tostring(msg) end,
            EEex_Opcode_AddListsResolvedListener = function(fn) env._listener = fn end,
            EEex_Sprite_GetStat = function(sprite, id) return sprite.currentMR end,
            EEex_GameObject_ApplyEffect = function(sprite, args) applied[#applied + 1] = args end,
            EEex_BAnd = function(a, b)
                a, b = a % 4294967296, b % 4294967296
                local r, p = 0, 1
                while a > 0 or b > 0 do
                    if (a % 2 == 1) and (b % 2 == 1) then r = r + p end
                    a, b, p = math.floor(a / 2), math.floor(b / 2), p * 2
                end
                return r
            end,
            EEex_BOr = function(a, b)
                return (a + b - env.EEex_BAnd(a, b)) % 4294967296
            end,
            EEex_LShift = function(a, b) return a * (2 ^ b) end,
            EEex_Utility_IterateCPtrList = function() end,
            EEex_Resource_Demand = function() return nil end,
            Infinity_DisplayString = function(msg) logs[#logs + 1] = msg end,
        }
        if load and setfenv == nil then
            assert(load(code, "M_CBMBON.lua", "t", env))()
        else
            local fn = assert(loadstring(code, "M_CBMBON.lua"))
            setfenv(fn, env)
            fn()
        end
        env.CBMBPM({
            m_spellLevel = 6, m_flags = 3, m_sourceId = 1, m_sourceTarget = 2,
            m_sourceRes = { get = function() return "SPWI608" end },
            m_sourceType = 1, m_sourceFlags = 0, m_casterLevel = 15, m_school = 5, m_secondaryType = 4,
        }, { currentMR = mr })
        assert(#applied == 1, "CBMBPM did not apply MR reduction")
        return applied[1].effectAmount, applied[1].duration
    end
    """
    results = {}
    for impl in ("lupa.lua53", "lupa.luajit21"):
        rt = importlib.import_module(impl).LuaRuntime()
        amt, dur = rt.execute(prelude)(lua_text, mr_value)
        results[impl] = (int(amt), int(dur))
    return results


@test
def ini_default_matches_clean_install_and_uninstalls(work, weidu):
    shipped_game = fg.FakeGame(work / "shipped", weidu, tlk=fx.tlk(), biff=base_biff(), override=EEEX_LUA)
    out1 = shipped_game.install()
    check(fg.installed_ok(out1) and not fg.with_warnings(out1), out1)

    root_game = fg.FakeGame(work / "root_defaults", weidu, tlk=fx.tlk(), biff=base_biff(), override=EEEX_LUA)
    default_ini = (fg.MOD / "chriz-bg-magic.ini").read_bytes()
    (root_game.root / "chriz-bg-magic.ini").write_bytes(default_ini)
    before_root = root_game.tree()

    out2 = root_game.install()
    check(fg.installed_ok(out2) and not fg.with_warnings(out2), out2)

    check(
        normalized_game_tree(shipped_game.tree()) == normalized_game_tree(root_game.tree()),
        "Default game-root INI install diverged from shipped mod INI install",
    )

    before_reinstall = shipped_game.tree()
    out3 = shipped_game.install()
    check(fg.installed_ok(out3) and not fg.with_warnings(out3), out3)
    check(
        normalized_game_tree(shipped_game.tree()) == normalized_game_tree(before_reinstall),
        "Reinstall with default INI was not idempotent",
    )

    out_u1 = shipped_game.uninstall()
    check("SUCCESSFULLY REMOVED" in out_u1, out_u1)
    out_u2 = root_game.uninstall()
    check("SUCCESSFULLY REMOVED" in out_u2, out_u2)
    check(
        normalized_game_tree(root_game.tree()) == normalized_game_tree(before_root),
        "Uninstall altered pre-install files or removed game-root chriz-bg-magic.ini",
    )
    check((root_game.root / "chriz-bg-magic.ini").read_bytes() == default_ini, "Game-root INI modified on uninstall")


@test
def ini_parser_precedence_and_tolerance(work, weidu):
    g = fg.FakeGame(work, weidu, tlk=fx.tlk(), biff=base_biff(), override=EEEX_LUA)
    # Game-root copy with UTF-8 BOM, CRLF, comments, synonym booleans, invalid entries, and out-of-range ints.
    ini_body = "\r\n".join([
        "# Full-line hash comment",
        "; Full-line semicolon comment",
        "[systems]",
        "typed_bonuses = On ; inline semicolon comment",
        "player1_protection = False # inline hash comment",
        "unknown_option = 42",
        "broken_line_without_equals",
        "[new_spells]",
        "new_icelance = off",
        "[reworks]",
        "rework_doom = TRUE",
        "[tuning]",
        "cure_range_feet = 1",
        "cure_light_ct = -5",
        "heal_ct = abc",
        "harm_ct = 99",
        "skull_trap_max_dice = 99",
        "pierce_magic_mr_min = 60",
        "pierce_magic_mr_max = 20",
        "",
    ])
    (g.root / "chriz-bg-magic.ini").write_bytes(b"\xef\xbb\xbf" + ini_body.encode("utf-8"))

    out = g.install()
    check(fg.installed_ok(out) and not fg.with_warnings(out), out)
    for expected_msg in (
        "reading configuration from chriz-bg-magic.ini.",
        "ignoring unknown option 'unknown_option'",
        "ignoring malformed line 'broken_line_without_equals'",
        "clamping 'cure_range_feet' from 1 to 2",
        "clamping 'cure_light_ct' from -5 to 1",
        "invalid integer 'abc' for 'heal_ct'; keeping default",
        "clamping 'harm_ct' from 99 to 9",
        "clamping 'skull_trap_max_dice' from 99 to 30",
        "pierce_magic_mr_min (60) > pierce_magic_mr_max (20); raising max to 60",
    ):
        check(expected_msg in out, f"Expected INI diagnostic missing: {expected_msg!r}\n{out}")

    check(not (g.root / "override" / "chriz-bg-magic.ini").exists(), "INI leaked into override/")
    check(not (g.root / "override" / "M_CBMP1.lua").exists(), "player1_protection = False still wrote M_CBMP1.lua")
    check("CLERIC_CBMAGIC_ICELANCE" not in ids_map(g), "new_icelance = off still added spell symbol")
    check(spl_ability_headers(g, "SPPR103")[0]["range"] == 2, "cure_range_feet clamp 1->2 failed")
    check(spl_ability_headers(g, "SPPR103")[0]["casting_time"] == 1, "cure_light_ct clamp -5->1 failed")
    check(spl_ability_headers(g, "SPPR607")[0]["casting_time"] == 6, "heal_ct invalid int did not keep default 6")
    check(spl_ability_headers(g, "SPPR608")[0]["casting_time"] == 9, "harm_ct clamp 99->9 failed")
    st_headers = spl_ability_headers(g, "SPWI313")
    check(st_headers[-1]["min_level"] == 30, f"skull_trap_max_dice clamp 99->30 failed: {st_headers[-1]}")

    lua_code = (g.root / "override" / "M_CBMBON.lua").read_text(encoding="utf-8")
    check("PIERCE_MIN = 60" in lua_code and "PIERCE_MAX = 60" in lua_code, "Pierce MR max auto-raise failed")


@test
def ini_tier2_toggles_isolate_owned_systems_and_reworks(work, weidu):
    # Case A: Disable new spells, Dispelling Screen, Mirror Image, Celestial party cap,
    # typed bonuses (keeping APR cap), exclusive families, strength floors, player1 protection, and live icons.
    extra = {
        "SPELL.IDS": fx.game()["SPELL.IDS"] + b"1321 CLERIC_PRAYER\r\n",
        "SPPR321.SPL": ie.make_spl(
            spell_type=2,
            abilities=[{"target": 5, "effects": [effect(54, p1=1, duration=60, dispel=3)]}],
            desc=1,
        ),
    }
    g = fg.FakeGame(work / "case_a", weidu, tlk=fx.tlk(), biff=base_biff(extra), override=EEEX_LUA)
    sentinel_mirror = ie.Game(g.root).get("SPWI212", "SPL")
    sentinel_reflected = ie.Game(g.root).get("SPWI120", "SPL")
    sentinel_malison = ie.Game(g.root).get("SPIN682", "SPL")
    (g.root / "chriz-bg-magic.ini").write_text("\n".join([
        "[systems]",
        "typed_bonuses = 0",
        "extra_attack_cap = 1",
        "exclusive_families = 0",
        "strength_floors = 0",
        "player1_protection = 0",
        "live_record_icons = 0",
        "[new_spells]",
        "new_faerie_fire = 0",
        "new_icelance = 0",
        "new_protection_from_cold = 0",
        "new_protection_from_acid = 0",
        "new_mass_regenerate = 0",
        "new_conjure_air_elemental = 0",
        "[reworks]",
        "rework_dispelling_screen = 0",
        "rework_mirror_image = 0",
        "celestial_party_cap = 0",
        "",
    ]), encoding="utf-8")

    out = g.install()
    check(fg.installed_ok(out) and not fg.with_warnings(out), out)

    spells = ids_map(g)
    for sym in (
        "CLERIC_CBMAGIC_FAERIE_FIRE",
        "CLERIC_CBMAGIC_ICELANCE",
        "CLERIC_CBMAGIC_PROTECTION_FROM_COLD",
        "CLERIC_CBMAGIC_PROTECTION_FROM_ACID",
        "CLERIC_CBMAGIC_MASS_REGENERATE",
        "CLERIC_CBMAGIC_CONJURE_AIR_ELEMENTAL",
        "WIZARD_DISPELLING_SCREEN",
    ):
        check(sym not in spells, f"{sym} should not be added when toggled off")

    check(not (g.root / "override" / "spwi510.2da").exists(), "spwi510.2da copied despite rework_dispelling_screen=0")
    check(not (g.root / "override" / "spwi510.spl").exists(), "spwi510.spl written despite rework_dispelling_screen=0")
    check(ie.Game(g.root).get("SPWI212", "SPL") == sentinel_mirror, "SPWI212 modified despite rework_mirror_image=0")
    check(ie.Game(g.root).get("SPWI120", "SPL") == sentinel_reflected, "SPWI120 modified despite rework_mirror_image=0")
    check(not (g.root / "override" / "spwi298.spl").exists(), "SPWI298 written despite rework_mirror_image=0")
    check(ie.Game(g.root).get("SPIN682", "SPL") != sentinel_malison, "Tier 1 fix SPIN682 should still install")
    check(not (g.root / "override" / "M_CBMSTR.lua").exists(), "M_CBMSTR.lua installed despite strength_floors=0")
    check(not (g.root / "override" / "spwi214.spl").exists(), "SPWI214 modified despite strength_floors=0")
    check(not (g.root / "override" / "M_CBMP1.lua").exists(), "M_CBMP1.lua installed despite player1_protection=0")
    check(not (g.root / "override" / "M_CBMREC.lua").exists(), "M_CBMREC.lua installed despite live_record_icons=0")

    check((g.root / "override" / "CBMDEVAU.BCS").is_file(), "CBMDEVAU.BCS not compiled when celestial_party_cap=0")
    check((g.root / "override" / "CBMPLANU.BCS").is_file(), "CBMPLANU.BCS not compiled when celestial_party_cap=0")
    check(cre_override_script(g, "CBMDEVAG") == "CBMDEVAU", "CBMDEVAG script not switched to CBMDEVAU")
    check(cre_override_script(g, "CBMDEVAE") == "CBMDEVAU", "CBMDEVAE script not switched to CBMDEVAU")
    check(cre_override_script(g, "CBMPLANG") == "CBMPLANU", "CBMPLANG script not switched to CBMPLANU")
    check(cre_override_script(g, "CBMPLANE") == "CBMPLANU", "CBMPLANE script not switched to CBMPLANU")

    lua_code = (g.root / "override" / "M_CBMBON.lua").read_text(encoding="utf-8")
    check("TYPED_ENABLED = (0 ~= 0)" in lua_code, "M_CBMBON.lua missing TYPED_ENABLED = false")
    check("APR_CAP_ENABLED = (1 ~= 0)" in lua_code, "M_CBMBON.lua missing APR_CAP_ENABLED = true")

    bless_text = g.tlk(g.spl("SPPR101")["desc"])
    check("Typed spell effects:" not in bless_text, f"Bless kept baked typed summary: {bless_text!r}")
    bless_scroll = g.tlk(g.itm_descs("SCRLBLS")[1])
    check("Typed spell effects:" not in bless_scroll, f"Bless scroll kept baked typed summary: {bless_scroll!r}")
    check(not (g.root / "override" / "SPPR321.SPL").exists(),
          "CLERIC_PRAYER (SPPR321) copied to override despite typed_bonuses=0")
    prayer_fx = ie.parse_spl(ie.Game(g.root).get("SPPR321", "SPL"))["abilities"][0]["effects"]
    check(
        all(fx_row["resource"] not in ("CBTSTATE", "CBTFAVOR") for fx_row in prayer_fx),
        "CLERIC_PRAYER (SPPR321) gained typed bonus markers despite typed_bonuses=0",
    )
    check(
        any(fx_row["resource"] == "CBTAPR" for fx_row in spl_effects(g, "SPWI613")),
        "Improved Haste lost CBTAPR despite extra_attack_cap=1",
    )
    tenser_res = {fx_row["resource"] for fx_row in spl_effects(g, "SPWI603")}
    check("SPPR412" not in tenser_res and "SPPR513" not in tenser_res,
          "Transformation exclusive family still injected when exclusive_families=0")


@test
def ini_tier3_tuning_updates_binaries_lua_and_descriptions(work, weidu):
    g1 = fg.FakeGame(work / "tuned_1", weidu, tlk=fx.tlk(), biff=base_biff(), override=EEEX_LUA)
    (g1.root / "chriz-bg-magic.ini").write_text("\n".join([
        "[tuning]",
        "cure_range_feet = 25",
        "cure_light_ct = 3",
        "cure_medium_ct = 5",
        "cure_serious_ct = 6",
        "cure_critical_ct = 7",
        "mass_cure_ct = 6",
        "heal_ct = 8",
        "cause_serious_ct = 6",
        "cause_critical_ct = 7",
        "harm_ct = 8",
        "doom_ct = 3",
        "improved_haste_ct = 4",
        "improved_haste_base_rounds = 0",
        "dispelling_screen_turns = 8",
        "pierce_magic_mr_min = 15",
        "pierce_magic_mr_max = 65",
        "pierce_magic_rounds = 9",
        "skull_trap_max_dice = 25",
        "celestial_ct = 5",
        "deva_duration_turns = 6",
        "planetar_duration_turns = 4",
        "",
    ]), encoding="utf-8")
    out1 = g1.install()
    check(fg.installed_ok(out1) and not fg.with_warnings(out1), out1)

    # Cure / Cause / Heal / Harm
    for resref, expected_ct, expected_range in (
        ("SPPR103", 3, 25),
        ("SPPR315", 5, 25),
        ("SPPR401", 6, 25),
        ("SPPR502", 7, 25),
        ("SPPR514", 6, None),
        ("SPPR607", 8, None),
        ("SPPR414", 6, None),
        ("SPPR510", 7, None),
        ("SPPR608", 8, None),
    ):
        hdr = spl_ability_headers(g1, resref)[0]
        check(hdr["casting_time"] == expected_ct, f"{resref} CT {hdr['casting_time']} != {expected_ct}")
        if expected_range is not None:
            check(hdr["range"] == expected_range, f"{resref} range {hdr['range']} != {expected_range}")
            txt = g1.tlk(g1.spl(resref)["desc"])
            check(f"Range: {expected_range} ft." in txt, f"{resref} desc missing Range: {expected_range} ft.")
        txt = g1.tlk(g1.spl(resref)["desc"])
        check(f"Casting Time: {expected_ct}" in txt, f"{resref} desc missing Casting Time: {expected_ct}")

    for cure_scroll in ("SCRL56", "SCRL1B"):
        check(itm_first_ability_range(g1, cure_scroll) == 25, f"{cure_scroll} range != 25")
        check("Range: 25 ft." in g1.tlk(g1.itm_descs(cure_scroll)[1]), f"{cure_scroll} desc not synced")

    # Doom
    check(spl_ability_headers(g1, "SPPR113")[0]["casting_time"] == 3, "Doom CT != 3")
    check("Casting Time: 3" in g1.tlk(g1.spl("SPPR113")["desc"]), "Doom desc missing CT 3")
    check("Casting Time: 3" in g1.tlk(g1.itm_descs("SCRLDOM")[1]), "Doom scroll not synced")

    # Improved Haste base_rounds = 0 (pure 1 round/level)
    ih_headers = spl_ability_headers(g1, "SPWI613")
    check(ih_headers[0]["casting_time"] == 4, "Improved Haste CT != 4")
    check(max(fx_row["duration"] for fx_row in spl_effects(g1, "SPWI613", 0)) == 12 * 6,
          "Improved Haste ability 0 duration != 72s")
    check(max(fx_row["duration"] for fx_row in spl_effects(g1, "SPWI613", len(ih_headers) - 1)) == 20 * 6,
          "Improved Haste ability max duration != 120s")
    ih_desc = g1.tlk(g1.spl("SPWI613")["desc"])
    check("Casting Time: 4" in ih_desc and "Duration: 1 round/level" in ih_desc and "for 1 round per level" in ih_desc,
          f"Improved Haste base=0 desc mismatch: {ih_desc!r}")
    check("for 1 round per level" in g1.tlk(g1.itm_descs("SCRLIH")[1]), "Improved Haste scroll not synced")

    # Dispelling Screen
    ds_durations = {fx_row["duration"] for fx_row in spl_effects(g1, "SPWI510") if fx_row["timing"] == 0}
    check(8 * 60 in ds_durations and 300 not in ds_durations and 4 in ds_durations,
          f"Dispelling Screen durations mismatch: {ds_durations}")
    check("Duration: 8 turns" in g1.tlk(g1.spl("SPWI510")["desc"]), "Dispelling Screen desc missing 8 turns")
    check("for 8 turns" in g1.tlk(g1.itm_descs("SCRLDS")[1]), "Dispelling Screen scroll not synced")

    # Pierce Magic binary icon + Lua execution (Lua 5.3 & LuaJIT 2.1)
    pm_icons = [fx_row["duration"] for fx_row in spl_effects(g1, "SPWI608")
                if fx_row["opcode"] == 142 and fx_row["p2"] == 106]
    check(pm_icons == [54], f"Pierce Magic icon duration mismatch: {pm_icons}")
    pm_desc = g1.tlk(g1.spl("SPWI608")["desc"])
    check(
        "minimum reduction of 15 and a maximum of 65 percentage points" in pm_desc
        and "for 9 rounds" in pm_desc,
        f"Pierce Magic desc mismatch: {pm_desc!r}",
    )
    check("for 9 rounds" in g1.tlk(g1.itm_descs("SCRLPM")[1]), "Pierce Magic scroll not synced")

    lua_code = (g1.root / "override" / "M_CBMBON.lua").read_text(encoding="utf-8")
    for mr, expected_amt in ((10, -15), (80, -40), (160, -65)):
        res = test_pierce_callback_in_lua(lua_code, mr)
        for impl, (amt, dur) in res.items():
            check((amt, dur) == (expected_amt, 54), f"{impl} CBMBPM(mr={mr}) returned {(amt, dur)}")

    # Skull Trap max_dice = 25 (adds level 21..25 abilities -> 21 abilities)
    st_headers = spl_ability_headers(g1, "SPWI313")
    check(len(st_headers) == 21 and st_headers[-1]["min_level"] == 25, f"Skull Trap abilities != 21..25: {len(st_headers)}")
    st_last_dmg = [fx_row["dice"] for fx_row in spl_effects(g1, "SPWI313", 20) if fx_row["opcode"] == 12]
    check(st_last_dmg == [25], f"Skull Trap lvl 25 dice != 25: {st_last_dmg}")
    check("maximum of 25d6" in g1.tlk(g1.spl("SPWI313")["desc"]), "Skull Trap desc missing 25d6")
    check("maximum of 25d6" in g1.tlk(g1.itm_descs("SCRLST")[1]), "Skull Trap scroll not synced")

    # Celestials (Deva 6 turns, Planetar 4 turns, CT 5)
    for deva_res in ("SPPR726", "SPPR727", "SPCL923", "SPCL935"):
        check(spl_ability_headers(g1, deva_res)[0]["casting_time"] == 5, f"{deva_res} CT != 5")
        durs = {fx_row["duration"] for fx_row in spl_effects(g1, deva_res)}
        check(360 in durs, f"{deva_res} duration 360 missing: {durs}")
        txt = g1.tlk(g1.spl(deva_res)["desc"])
        check("Casting Time: 5" in txt and "Duration: 6 turns" in txt, f"{deva_res} desc mismatch")
    for plan_res in ("SPWI923", "SPWI924"):
        check(spl_ability_headers(g1, plan_res)[0]["casting_time"] == 5, f"{plan_res} CT != 5")
        durs = {fx_row["duration"] for fx_row in spl_effects(g1, plan_res)}
        check(240 in durs, f"{plan_res} duration 240 missing: {durs}")
        txt = g1.tlk(g1.spl(plan_res)["desc"])
        check("Casting Time: 5" in txt and "Duration: 4 turns" in txt, f"{plan_res} desc mismatch")
    check("Duration: 4 turns" in g1.tlk(g1.itm_descs("SCRLPLN")[1]), "Planetar scroll not synced")

    # Case 2: Skull Trap max_dice = 8 & Improved Haste base_rounds = 5
    g2 = fg.FakeGame(work / "tuned_2", weidu, tlk=fx.tlk(), biff=base_biff(), override=EEEX_LUA)
    (g2.root / "chriz-bg-magic.ini").write_text("\n".join([
        "[tuning]",
        "improved_haste_base_rounds = 5",
        "skull_trap_max_dice = 8",
        "",
    ]), encoding="utf-8")
    out2 = g2.install()
    check(fg.installed_ok(out2) and not fg.with_warnings(out2), out2)

    check(max(fx_row["duration"] for fx_row in spl_effects(g2, "SPWI613", 0)) == (5 + 12) * 6,
          "Improved Haste base=5 ability 0 duration != 102s")
    check(max(fx_row["duration"] for fx_row in spl_effects(g2, "SPWI613", 8)) == (5 + 20) * 6,
          "Improved Haste base=5 ability max duration != 150s")
    ih2_desc = g2.tlk(g2.spl("SPWI613")["desc"])
    check("Duration: 5 rounds + 1 round/level" in ih2_desc and "for 5 rounds plus 1 round per level" in ih2_desc,
          f"Improved Haste base=5 desc mismatch: {ih2_desc!r}")

    st2_headers = spl_ability_headers(g2, "SPWI313")
    check(len(st2_headers) == 16, f"Skull Trap max_dice=8 changed ability count: {len(st2_headers)}")
    st2_last_dmg = [fx_row["dice"] for fx_row in spl_effects(g2, "SPWI313", 15) if fx_row["opcode"] == 12]
    check(st2_last_dmg == [8], f"Skull Trap max_dice=8 cap failed: {st2_last_dmg}")
    check("maximum of 8d6" in g2.tlk(g2.spl("SPWI313")["desc"]), "Skull Trap max_dice=8 desc mismatch")
