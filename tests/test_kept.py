"""Tests of the kept and adjusted Spell Revisions batch (cbmagic_sr.tpa) on made-up
spells shaped like the base game's, and on variations, idempotence, and invalid inputs."""
import struct

import fakegame as fg
import fixtures as fx
import ie
from harness import check, test

# Additional TLK strings for the SR batch tests (appended after fx.TEXTS).
BASE_STRREF = len(fx.TEXTS)
SR_TEXTS = [
    # +0: Invisibility
    "Invisibility\nDuration: Special\nThe creature remains invisible until 24 hours have passed.",
    # +1: Luck
    "Luck\nDuration: 3 rounds\nThe recipient is lucky for the next 3 rounds.",
    # +2: Clairvoyance
    "Clairvoyance\nRange: 0\nDuration: Instant\nArea of Effect: Entire area\n"
    "Clairvoyance empowers the wizard to see into the mind of any creature within the area "
    "and Look through its eyes. In effect, this reveals the entire map of the current area to "
    "the caster. It only functions outdoors, however, and does not show the location of any creatures.",
    # +3: Invisibility 10' Radius
    "Invisibility 10' Radius\nCasting Time: 9\nThe affected creatures remain invisible until 24 hours have passed.",
    # +4: Confusion
    "Confusion\nDuration: 5 rounds + 1 round/6 levels\n"
    "The spell lasts for 5 rounds plus 1 round every 6 levels of the caster.",
    # +5: Minor Sequencer
    "Minor Sequencer\n(Invocation/Evocation)\nLevel: 4",
    # +6: Teleport Field
    "Teleport Field\nSaving Throw: None\n"
    "This spell creates an active teleportation field that randomly teleports all enemies in this area for the duration of the spell.",
    # +7: Oracle
    "Oracle\nArea of Effect: 120-ft. radius\n"
    "This spell will dispel all Illusion/Phantasm spells of 5th level and lower in the area.",
    # +8: Contingency
    "Contingency\n(Evocation)\nLevel: 6",
    # +9: Sphere of Chaos
    "Sphere of Chaos\nLevel: 7\n"
    "Any enemy entering the sphere must save vs. Spell or suffer one of the following random effects:\n"
    " - polymorph into a squirrel;\n"
    " - confusion;\n"
    " - hasted.",
    # +10: Spell Sequencer
    "Spell Sequencer\n(Invocation/Evocation)\nLevel: 7",
    # +11: Spell Trigger
    "Spell Trigger\n(Invocation/Evocation)\nLevel: 8",
    # +12: Chain Contingency
    "Chain Contingency\n(Evocation)\nLevel: 9",
]

INVIS_DESC = BASE_STRREF + 0
LUCK_DESC = BASE_STRREF + 1
CLAIR_DESC = BASE_STRREF + 2
INVIS10_DESC = BASE_STRREF + 3
CONF_DESC = BASE_STRREF + 4
MSEQ_DESC = BASE_STRREF + 5
TFIELD_DESC = BASE_STRREF + 6
ORACLE_DESC = BASE_STRREF + 7
CONT_DESC = BASE_STRREF + 8
CHAOS_DESC = BASE_STRREF + 9
SSEQ_DESC = BASE_STRREF + 10
STRIG_DESC = BASE_STRREF + 11
CCONT_DESC = BASE_STRREF + 12

ARCANE_SYMBOLS = [
    (2206, "WIZARD_INVISIBILITY"),
    (2209, "WIZARD_LUCK"),
    (2301, "WIZARD_CLAIRVOYANCE"),
    (2307, "WIZARD_INVISIBILITY_10_FOOT"),
    (2401, "WIZARD_CONFUSION"),
    (2420, "WIZARD_MINOR_SEQUENCER"),
    (2421, "WIZARD_TELEPORT_FIELD"),
    (2515, "WIZARD_ORACLE"),
    (2617, "WIZARD_CONTINGENCY"),
    (2710, "WIZARD_SPELL_SEQUENCER"),
    (2711, "WIZARD_SPHERE_OF_CHAOS"),
    (2809, "WIZARD_SPELL_TRIGGER"),
    (2908, "WIZARD_CHAIN_CONTINGENCY"),
]


def make_spl_with_excl(excl=0, **kw):
    raw = bytearray(ie.make_spl(**kw))
    struct.pack_into("<H", raw, 0x1E, excl)
    return bytes(raw)


def make_scroll_with_excl(spell, desc, u1=0x04, u3=0x80):
    raw = bytearray(ie.make_itm([[fx.fx(opcode=146, resource=spell), fx.fx(opcode=147, resource=spell)]], desc=desc))
    raw[0x2D] = u1
    raw[0x2F] = u3
    return bytes(raw)


def parse_spl_full(data):
    base = ie.parse_spl(data)
    base["flags"], = struct.unpack_from("<I", data, 0x18)
    base["excl"], = struct.unpack_from("<H", data, 0x1E)
    base["priest_excl"], = struct.unpack_from("<H", data, 0x20)
    base["school"] = data[0x25]
    base["sectype"] = data[0x27]
    ab_off, = struct.unpack_from("<I", data, 0x64)
    for i, ab in enumerate(base["abilities"]):
        o = ab_off + i * 0x28
        ab["range"], ab["min_level"], ab["casting_time"] = struct.unpack_from("<HHH", data, o + 0x0E)
        ab["projectile"], = struct.unpack_from("<H", data, o + 0x26)
    return base


def sr_tlk():
    return ie.make_tlk(fx.TEXTS + SR_TEXTS)


def sr_biff(extra=None):
    base = fx.game()
    base["SPELL.IDS"] = ie.make_ids(fx.SPELL_SYMBOLS + ARCANE_SYMBOLS)
    base["PROJECTL.IDS"] = ie.make_ids([(159, "SPARBLPA"), (168, "SPARBLNP"), (189, "HOLD"), (337, "ohvrnp")])
    # SPWI206 Invisibility
    base["SPWI206.SPL"] = ie.make_spl(1, 2, [{"target": 1, "effects": [
        fx.fx(opcode=20, power=2, timing=0, dispel=3, duration=7200),
        fx.fx(opcode=215, power=2, timing=1, dispel=3, resource="SPMAJINV"),
    ]}], desc=INVIS_DESC)
    base["SCRL90.ITM"] = fx.scroll("SPWI206", INVIS_DESC)
    # SPWI209 Luck
    base["SPWI209.SPL"] = ie.make_spl(1, 2, [{"target": 1, "effects": [
        fx.fx(opcode=133, power=2, p1=1, timing=0, dispel=3, duration=18),
        fx.fx(opcode=142, power=2, p2=32, timing=0, dispel=3, duration=18),
        fx.fx(opcode=174, power=2, timing=4, dispel=3, duration=18, resource="EFF_E04"),
    ]}], desc=LUCK_DESC)
    base["SCRL93.ITM"] = fx.scroll("SPWI209", LUCK_DESC)
    # SPWI301 Clairvoyance (flags 0x2000 outdoors only, opcode 117 reveal map)
    base["SPWI301.SPL"] = ie.make_spl(1, 3, [{"target": 5, "range": 0, "effects": [
        fx.fx(opcode=117, target=1, power=3, timing=0, duration=20),
        fx.fx(opcode=141, target=1, power=3, p2=24, timing=1),
        fx.fx(opcode=61, target=1, power=3, timing=0, duration=3),
    ]}], flags=0x2000, desc=CLAIR_DESC)
    base["SCRL1D.ITM"] = fx.scroll("SPWI301", CLAIR_DESC)
    # SPWI307 Invisibility 10' Radius
    base["SPWI307.SPL"] = ie.make_spl(1, 3, [{"target": 5, "casting_time": 9, "effects": [
        fx.fx(opcode=20, power=3, timing=0, dispel=3, duration=7200),
        fx.fx(opcode=174, power=3, timing=4, dispel=3, duration=7200, resource="EFF_E06"),
        fx.fx(opcode=141, power=3, p2=20, timing=1, dispel=3),
    ]}], desc=INVIS10_DESC)
    base["SCRL1J.ITM"] = fx.scroll("SPWI307", INVIS10_DESC)
    # SPWI401 Confusion (4 abilities at minlvl 1, 12, 18, 24 with durations 36, 42, 48, 54)
    base["SPWI401.SPL"] = ie.make_spl(1, 4, [
        {"target": 4, "min_level": ml, "casting_time": 4, "effects": [
            fx.fx(opcode=128, power=4, timing=0, duration=dur, save=ie.SAVE_SPELL, bonus=-2),
            fx.fx(opcode=139, power=4, p1=14782, timing=1, duration=0, save=ie.SAVE_SPELL, bonus=-2),
            fx.fx(opcode=142, power=4, p2=3, timing=0, duration=dur, save=ie.SAVE_SPELL, bonus=-2),
            fx.fx(opcode=174, power=4, timing=4, duration=dur, save=ie.SAVE_SPELL, bonus=-2, resource="EFF_E05"),
        ]} for ml, dur in ((1, 36), (12, 42), (18, 48), (24, 54))
    ], desc=CONF_DESC)
    base["SCRL1U.ITM"] = fx.scroll("SPWI401", CONF_DESC)
    # Sequencers and Contingencies (school 6 Evocation, excl 0x0800 Diviner)
    for res, desc, scrl in (
        ("SPWI420", MSEQ_DESC, "SCRL6D"),
        ("SPWI617", CONT_DESC, "SCRL7U"),
        ("SPWI710", SSEQ_DESC, "SCRL8L"),
        ("SPWI809", STRIG_DESC, "SCRL9D"),
        ("SPWI908", CCONT_DESC, "SCRL9Q"),
    ):
        base[f"{res}.SPL"] = make_spl_with_excl(
            excl=0x0800, spell_type=1, level=int(res[4]), school=6,
            abilities=[{"target": 5, "effects": [fx.fx(opcode=232, target=1, timing=0, duration=600)]}],
            desc=desc,
        )
        base[f"{scrl}.ITM"] = make_scroll_with_excl(res, desc, u1=0x04, u3=0x80)
    # SPWI421 Teleport Field
    base["SPWI421.SPL"] = ie.make_spl(1, 4, [{"target": 4, "casting_time": 4, "effects": [
        fx.fx(opcode=222, power=4, p1=30, timing=1, dispel=1, save=0, bonus=0),
        fx.fx(opcode=215, power=4, p2=1, timing=0, dispel=1, duration=3, save=0, bonus=0, resource="SPDIMNDR"),
        fx.fx(opcode=174, power=4, timing=1, dispel=1, save=0, bonus=0, resource="EFF_M13"),
    ]}], desc=TFIELD_DESC)
    base["SCRL6E.ITM"] = fx.scroll("SPWI421", TFIELD_DESC)
    # SPWI515 Oracle
    base["SPWI515.SPL"] = ie.make_spl(1, 5, [{"target": 5, "range": 100, "casting_time": 3, "projectile": 159, "effects": [
        fx.fx(opcode=220, power=5, p1=5, p2=5, timing=1, dispel=3),
        fx.fx(opcode=221, power=5, p1=5, p2=3, timing=1, dispel=3),
        fx.fx(opcode=136, power=5, timing=1, dispel=3),
    ]}], desc=ORACLE_DESC)
    base["SCRL6W.ITM"] = fx.scroll("SPWI515", ORACLE_DESC)
    # SPWI711 Sphere of Chaos
    base["SPWI711.SPL"] = ie.make_spl(1, 7, [{"target": 5, "range": 40, "casting_time": 7, "projectile": 238, "effects": [
        fx.fx(opcode=141, power=7, p2=6, timing=1, dispel=1, prob1=100, prob2=0, save=ie.SAVE_SPELL, bonus=0),
        fx.fx(opcode=174, power=7, timing=1, dispel=1, prob1=100, prob2=0, save=ie.SAVE_SPELL, bonus=0, resource="EFF_M06C"),
        fx.fx(opcode=111, power=7, timing=0, dispel=1, duration=40, prob1=10, prob2=0, save=ie.SAVE_SPELL, bonus=0, resource="SQUIRP"),
        fx.fx(opcode=128, power=7, timing=0, dispel=1, duration=40, prob1=25, prob2=11, save=ie.SAVE_SPELL, bonus=0),
        fx.fx(opcode=13, power=7, p2=64, timing=1, dispel=1, prob1=60, prob2=51, save=ie.SAVE_SPELL, bonus=0),
        fx.fx(opcode=39, power=7, p2=1, timing=0, dispel=1, duration=40, prob1=90, prob2=81, save=ie.SAVE_SPELL, bonus=0),
        fx.fx(opcode=16, power=7, timing=0, dispel=1, duration=40, prob1=100, prob2=91, save=ie.SAVE_SPELL, bonus=0),
    ]}], desc=CHAOS_DESC)
    base["SCRL8M.ITM"] = fx.scroll("SPWI711", CHAOS_DESC)
    if extra:
        base.update(extra)
    return base


@test
def kept_arcane_spells_on_vanilla_shaped_inputs(work, weidu):
    """All 13 kept/decided arcane spell changes patch the intended fields and effects,
    update spell and scroll descriptions, are idempotent on a second install, and restore
    cleanly on uninstall."""
    g = fg.FakeGame(work / "a", weidu, tlk=sr_tlk(), biff=sr_biff())
    before = g.tree()
    out = g.install()
    check("SUCCESSFULLY INSTALLED" in out, f"install:\n{out}")

    # 1. Invisibility: duration 2400s, instant visual untouched.
    s = parse_spl_full(g.file("override/SPWI206.SPL"))
    check([e["duration"] for e in s["abilities"][0]["effects"]] == [2400, 0], f"SPWI206: {s['abilities'][0]['effects']}")
    check("until 8 hours have passed" in g.tlk(s["desc"]), f"SPWI206 text: {g.tlk(s['desc'])}")
    check(g.itm_descs("SCRL90")[1] == s["desc"], "SCRL90 text")

    # 2. Luck: self-refresh first, duration 90s on all timed/expiry effects.
    s = parse_spl_full(g.file("override/SPWI209.SPL"))
    efx = s["abilities"][0]["effects"]
    check(efx[0]["opcode"] == 321 and efx[0]["resource"] == "SPWI209", f"SPWI209 refresh: {efx[0]}")
    check([e["duration"] for e in efx[1:]] == [90, 90, 90], f"SPWI209 durations: {efx[1:]}")
    check("Duration: 15 rounds" in g.tlk(s["desc"]) and "next 15 rounds" in g.tlk(s["desc"]), f"SPWI209 text: {g.tlk(s['desc'])}")

    # 3. Clairvoyance: outdoors bit cleared, 8 abilities (minlvl 1, 7..19), durations 18..60s, op 292 + op 142(57) + op 321.
    s = parse_spl_full(g.file("override/SPWI301.SPL"))
    check((s["flags"] & 0x2000) == 0 and s["sectype"] == 2, f"SPWI301 header: {s}")
    check([a["min_level"] for a in s["abilities"]] == [1, 7, 9, 11, 13, 15, 17, 19],
          f"SPWI301 min_levels: {[a['min_level'] for a in s['abilities']]}")
    for idx, ab in enumerate(s["abilities"]):
        dur = 18 + idx * 6
        ops = [e["opcode"] for e in ab["effects"]]
        check(ops == [321, 292, 142, 141, 61], f"SPWI301 ab {idx} ops: {ops}")
        check(ab["effects"][1]["p2"] == 1 and ab["effects"][1]["duration"] == dur and ab["effects"][1]["dispel"] == 3,
              f"SPWI301 ab {idx} op292: {ab['effects'][1]}")
    check("immune to backstab attacks" in g.tlk(s["desc"]) and "Range: Caster" in g.tlk(s["desc"]),
          f"SPWI301 text: {g.tlk(s['desc'])}")

    # 4. Invisibility 10' Radius: casting time 1, duration 60s.
    s = parse_spl_full(g.file("override/SPWI307.SPL"))
    check(s["abilities"][0]["casting_time"] == 1, f"SPWI307 casting_time: {s['abilities'][0]}")
    check([e["duration"] for e in s["abilities"][0]["effects"]] == [60, 60, 0], f"SPWI307 durations: {s['abilities'][0]['effects']}")
    check("Casting Time: 1" in g.tlk(s["desc"]) and "until 1 turn has passed" in g.tlk(s["desc"]),
          f"SPWI307 text: {g.tlk(s['desc'])}")

    # 5. Confusion: 3 abilities at 1, 15, 20 with durations 24, 30, 36.
    s = parse_spl_full(g.file("override/SPWI401.SPL"))
    check([a["min_level"] for a in s["abilities"]] == [1, 15, 20], f"SPWI401 levels: {[a['min_level'] for a in s['abilities']]}")
    for ab, exp_dur in zip(s["abilities"], (24, 30, 36)):
        check([e["duration"] for e in ab["effects"]] == [exp_dur, 0, exp_dur, exp_dur], f"SPWI401 ab: {ab['effects']}")
    check("Duration: 4 rounds (5 at 15th level, 6 at 20th level)" in g.tlk(s["desc"]), f"SPWI401 text: {g.tlk(s['desc'])}")

    # 6, 8, 10, 11, 12. Universal school sequencers & contingencies.
    for res, scrl in (("SPWI420", "SCRL6D"), ("SPWI617", "SCRL7U"), ("SPWI710", "SCRL8L"),
                      ("SPWI809", "SCRL9D"), ("SPWI908", "SCRL9Q")):
        s = parse_spl_full(g.file(f"override/{res}.SPL"))
        check(s["school"] == 0 and (s["excl"] & 0x3FC0) == 0, f"{res} school/excl: {s}")
        check("(Universal)" in g.tlk(s["desc"]), f"{res} text: {g.tlk(s['desc'])}")
        itm = g.file(f"override/{scrl}.ITM")
        check((itm[0x2D] & 0x3F) == 0 and (itm[0x2F] & 0xC0) == 0, f"{scrl} usability: {itm[0x2D]:#x}, {itm[0x2F]:#x}")

    # 7. Teleport Field: Save vs. Spell at -4.
    s = parse_spl_full(g.file("override/SPWI421.SPL"))
    for e in s["abilities"][0]["effects"]:
        check(e["save"] == 1 and e["bonus"] == -4, f"SPWI421 fx: {e}")
    check("Saving Throw: Neg." in g.tlk(s["desc"]) and "Saving Throw vs. Spell with a -4 penalty" in g.tlk(s["desc"]),
          f"SPWI421 text: {g.tlk(s['desc'])}")

    # 9. Oracle: range 1, projectile 338 (ohvrnp+1), p1=9 on op 220 and 221.
    s = parse_spl_full(g.file("override/SPWI515.SPL"))
    ab = s["abilities"][0]
    check(ab["range"] == 1 and ab["projectile"] == 338, f"SPWI515 ab: {ab}")
    check([e["p1"] for e in ab["effects"][:2]] == [9, 9], f"SPWI515 effects: {ab['effects']}")
    check("30-ft. radius" in g.tlk(s["desc"]) and "9th level and lower" in g.tlk(s["desc"]),
          f"SPWI515 text: {g.tlk(s['desc'])}")

    # 13. Sphere of Chaos: 5 outcomes (76, 128, 24, 39 p2=0, 175), all dur 6, save vs. spell at -4.
    s = parse_spl_full(g.file("override/SPWI711.SPL"))
    efx = s["abilities"][0]["effects"]
    check([e["opcode"] for e in efx[:2]] == [141, 174], f"SPWI711 hit visuals kept: {efx[:2]}")
    outcomes = [(e["opcode"], e["p2"], e["duration"], e["prob1"], e["prob2"], e["save"], e["bonus"])
                for e in efx if e["opcode"] in (76, 128, 24, 39, 175)]
    check(outcomes == [
        (76, 0, 6, 20, 0, 1, -4),
        (128, 0, 6, 40, 21, 1, -4),
        (24, 0, 6, 60, 41, 1, -4),
        (39, 0, 6, 80, 61, 1, -4),
        (175, 2, 6, 100, 81, 1, -4),
    ], f"SPWI711 outcomes: {outcomes}")
    check("save vs. Spell at -4 or suffer one of the following random effects for 1 round" in g.tlk(s["desc"]),
          f"SPWI711 text: {g.tlk(s['desc'])}")

    # Second install writes nothing.
    done = {p.name.upper(): p.read_bytes() for p in (g.root / "override").iterdir()
            if p.is_file() and p.suffix.upper() in (".SPL", ".ITM")}
    tlk = (g.root / "lang" / g.lang / "dialog.tlk").read_bytes()
    h = fg.FakeGame(work / "b", weidu, tlk=tlk, biff=sr_biff(done))
    out2 = h.install()
    check("SUCCESSFULLY INSTALLED" in out2, f"second install:\n{out2}")
    written = sorted(p.name.upper() for p in (h.root / "override").iterdir() if p.suffix.upper() in (".SPL", ".ITM"))
    check(written == [], f"second install rewrote {written}")

    # Uninstall restores the first game.
    out_un = g.uninstall()
    check(g.tree() == before, f"uninstall left changes:\n{out_un}")
