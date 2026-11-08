"""Polymorph Self's forms, as decided: SCS's forms with SCS's real values, built from our own files."""
import fakegame as fg
from harness import check, test
from test_resources import definitions

# Form innate: (weapon, look, Strength, exceptional, Dexterity, attacks, base AC or None, power).
POLYMORPH = {
    "cbmphg.spl": ("CBMPHGW", "CBMPHGC", 19, 0, 10, 1, 3, "CBMPHGR"),
    "cbmpom.spl": ("CBMPOMW", "CBMPOMC", 18, 100, 12, 1, 4, None),
    "spwi495.spl": ("PLYSPID", "PLYSPID2", 15, 0, 17, 2, 4, "CBMPSPW"),
    "spwi496.spl": ("PLYJELLY", "JELLMU", 14, 0, 9, 1, None, None),
    "cbmphh.spl": ("CBMPHHW", "CBMPHHC", 18, 0, 15, 1, 4, "CBMPHHB"),
    "cbmprt.spl": ("CBMPRTW", "CBMPRTC", 10, 0, 20, 1, 4, "CBMPRTH"),
}
LOOKS = {"cbmphgc.cre": 0xE293, "cbmpomc.cre": 0x2200, "cbmphhc.cre": 0x7B04, "cbmprtc.cre": 0xC300}


def effects(defn):
    return [e for a in defn.get("abilities", []) for e in a["effects"]]


@test
def polymorph_self_is_what_was_decided(work, weidu):
    defs = definitions()
    forms = [name.split(".")[0].upper() for name in POLYMORPH]
    spell = defs["spwi416.spl"]
    check([a["min_level"] for a in spell["abilities"]] == list(range(1, 21)), "Polymorph Self: one ability a level")
    for ability in spell["abilities"]:
        level, rows = ability["min_level"], ability["effects"]
        duration = 60 + 18 * level
        granted = [e["resource"].upper() for e in rows if e["opcode"] == 171 and e["timing"] == 1]
        removed = {e["resource"].upper(): e["duration"] for e in rows if e["opcode"] == 172 and e["timing"] == 4}
        end = [e for e in rows if e["opcode"] == 146 and e["resource"].upper() == "CBMPEND"]
        check(sorted(granted) == sorted(["CBMPNAT", *forms]), f"level {level}: grants {granted}")
        check(all(removed[f] == duration for f in forms) and removed["CBMPNAT"] == duration + 1
              and len(end) == 1 and (end[0]["timing"], end[0]["duration"]) == (4, duration + 1),
              f"level {level}: the forms last {duration} seconds: {removed}")
        check(any(e["opcode"] == 214 and e["resource"].upper() == "CBMPOLY" for e in rows), f"level {level}: menu")
    rows = (fg.MOD / "files" / "cbmpoly.2da").read_text(encoding="ascii").split()
    check([rows[i] for i in range(6, len(rows), 3)] == forms, f"the form menu: {rows}")

    remover = {(e["opcode"], e["resource"].upper()) for e in effects(defs["cbmfrem.spl"])}
    for name, (weapon, look, strength, extra, dex, apr, ac, power) in POLYMORPH.items():
        rows = effects(defs[name])
        check(rows[0]["opcode"] == 146 and rows[0]["resource"].upper() == "CBMFREM", f"{name}: clears other forms' powers first")
        check(any(e["opcode"] == 111 and e["resource"].upper() == weapon for e in rows), f"{name}: weapon")
        check({(171, name.split(".")[0].upper()), (172, name.split(".")[0].upper())} <=
              {(e["opcode"], e["resource"].upper()) for e in rows}, f"{name}: can be taken again")
        item = defs[weapon.lower() + ".itm"]["casting"]
        values = {(e["opcode"], e["p2"]): e["p1"] for e in item}
        check(any(e["opcode"] == 135 and e["p2"] == 1 and e["resource"].upper() == look for e in item), f"{weapon}: look")
        check(values.get((44, 1)) == strength and values.get((97, 1), 0) == extra and values.get((15, 1)) == dex
              and values.get((1, 1)) == apr and values.get((0, 16)) == ac, f"{weapon}: {values}")
        if power:
            granter = [e for e in rows if e["opcode"] == 146 and e["resource"].upper().startswith("CBMP")][-1]
            check({(e["opcode"], e["resource"].upper()) for e in effects(defs[granter["resource"].lower() + ".spl"])}
                  == {(172, power), (171, power)}, f"{name}: grants {power}")
            check({(172, power), (321, power)} <= remover, f"the remover misses {power}")
    for name, animation in LOOKS.items():
        check(defs[name]["animation"] == animation, f"{name}: animation {defs[name]['animation']:#x}")
    # The hill giant wears Icewind Dale's verbeeg art; BG2:EE has none, so the mod brings it.
    art = fg.MOD / "files"
    ini = (art / "e293.ini").read_text(encoding="latin-1").lower()
    check("resref=mgve" in ini, "the hill giant look names the verbeeg art")
    bams = sorted(p.name.lower() for p in art.glob("*.bam") if p.name.lower().startswith("mgve"))
    check(len(bams) == 24, f"the verbeeg art ships whole: {bams}")
    sounds = {s.strip() for line in ini.splitlines() if "=" in line and not line.split("=")[0].strip().endswith("_frame")
              for s in line.split("=", 1)[1].split(",") if s.strip().startswith("verbee")}
    check(sounds and all((art / f"{s}.wav").exists() for s in sounds), f"the hill giant's sounds: {sorted(sounds)}")
    breath = {(e["opcode"], e["timing"], e["duration"]) for e in effects(defs["cbmphhb.spl"]) if e["resource"].upper() == "CBMPHHB"}
    check(breath == {(172, 1, 0), (171, 4, 18)}, f"Fiery Breath comes back after 3 rounds: {breath}")
    for name in ("spwi416.spl", *POLYMORPH):
        check("text" in defs[name]["header"]["description"], f"{name}: our own description")


# Shapechange: (weapon, look, Strength, exceptional, Dexterity, attacks, base AC, THAC0, power).
SHAPECHANGE = {
    "spin152.spl": ("CDMINDFL", "SHMIND", 10, 0, 10, 4, 3, 11, "CBMSFPB"),
    "spin153.spl": ("CDGOLIRO", "SHIRON", 24, 0, 9, 1, 3, 3, "CBMSGOC"),
    "spin154.spl": ("TROLLALL", "SHTROLL", 22, 0, 18, 3, 4, 8, None),
    "cbmsma.spl": ("CBMSMAW", "CBMSMAC", 19, 0, 18, 5, -6, 8, "CBMSMAT"),
    "cbmsba.spl": ("CBMSBAW", "CBMSBAC", 18, 0, 10, 3, 2, 11, "CBMSBAZ"),
    "cbmsis.spl": ("CBMSISW", "STALKE", 18, 10, 17, 1, -3, 11, None),
}


@test
def shapechange_is_what_was_decided(work, weidu):
    defs = definitions()
    forms = [name.split(".")[0].upper() for name in SHAPECHANGE]
    spell = defs["spwi916.spl"]
    check(len(spell["abilities"]) == 1, "Shapechange: one ability")
    rows = spell["abilities"][0]["effects"]
    granted = sorted(e["resource"].upper() for e in rows if e["opcode"] == 171 and e["timing"] == 1)
    removed = {e["resource"].upper(): e["duration"] for e in rows if e["opcode"] == 172 and e["timing"] == 4}
    check(granted == sorted(["CBMSNAT", *forms]), f"Shapechange grants {granted}")
    check(all(removed[f] == 360 for f in forms) and removed["CBMSNAT"] == 361, f"six turns: {removed}")
    check(any(e["opcode"] == 146 and e["resource"].upper() == "CBMSEND" and e["duration"] == 361 for e in rows), "the end")
    menu = (fg.MOD / "files" / "cbmshap.2da").read_text(encoding="ascii").split()
    check([menu[i] for i in range(6, len(menu), 3)] == forms, f"the form menu: {menu}")
    remover = {(e["opcode"], e["resource"].upper()) for e in effects(defs["cbmfrem.spl"])}
    for name, (weapon, look, strength, extra, dex, apr, ac, thac0, power) in SHAPECHANGE.items():
        rows = [(e["opcode"], e["resource"].upper()) for e in effects(defs[name])]
        check((146, "CBMFREM") in rows and (111, weapon) in rows and rows.index((146, "CBMFREM")) < rows.index((111, weapon)),
              f"{name}: clears other powers, then takes the weapon: {rows}")
        item = defs[weapon.lower() + ".itm"]["casting"]
        values = {(e["opcode"], e["p2"]): e["p1"] for e in item}
        check(any(e["opcode"] == 135 and e["p2"] == 1 and e["resource"].upper() == look for e in item), f"{weapon}: look")
        check(values.get((44, 1)) == strength and values.get((97, 1), 0) == extra and values.get((15, 1)) == dex
              and values.get((1, 1)) == apr and values.get((0, 16)) == ac and values.get((54, 1)) == thac0,
              f"{weapon}: {values}")
        if power:
            check({(172, power), (321, power)} <= remover, f"the remover misses {power}")
    golem = {(e["opcode"], e["p1"], e["p2"]) for e in defs["cdgoliro.itm"]["casting"] if e["opcode"] == 120}
    check(golem == {(120, 0, 2), (120, 1, 0), (120, 2, 0)}, f"iron golem: weapons below +3 cannot hurt it: {golem}")
    check((321, "CBMSISL") in remover, "the stalker's invisibility stops with the form")
    for name in ("spwi916.spl", *SHAPECHANGE):
        check("text" in defs[name]["header"]["description"], f"{name}: our own description")
