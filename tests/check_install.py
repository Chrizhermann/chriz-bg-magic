"""Checks an installed game for chriz-bg-magic's changes and prints a report. Read-only:
it never writes to the game.

usage: python -I tests/check_install.py <game folder> [--json out.json]

Each changed spell is compared with its state before the install: WeiDU's backup copy
(weidu_external/backup/chriz-bg-magic/0) when the install replaced an override file,
otherwise the game's BIFF copy. Exit code 0 when every check passes.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ie  # noqa: E402

SAVE_RULE = ["WIZARD_FIREBALL", "WIZARD_DELAYED_BLAST_FIREBALL", "WIZARD_SUN_FIRE", "WIZARD_CONE_OF_COLD",
             "CLERIC_FLAME_STRIKE", "WIZARD_SKULL_TRAP", "CLERIC_GLYPH_OF_WARDING", "WIZARD_INCENDIARY_CLOUD",
             "WIZARD_LIGHTNING_BOLT"]
KEEP_SAVE = ["WIZARD_CHAIN_LIGHTNING", "WIZARD_METEOR_SWARM", "CLERIC_FIRE_STORM"]
SLEEP = ["WIZARD_SLEEP", "WIZARD_COLOR_SPRAY", "WIZARD_STINKING_CLOUD", "WIZARD_POWER_WORD_SLEEP",
         "CLERIC_COMMAND", "CLERIC_GREATER_COMMAND", "WIZARD_EMOTION_HOPELESSNESS"]
WEB_RACES = ["SPIDER", "SLIME", "WYVERN", "BEHOLDER", "MEPHIT", "SPECTRE", "WRAITH", "SHADOW", "MIST", "DRAGON",
             "GIANT", "ETTIN"]


class Installed:
    def __init__(self, root):
        self.root = Path(root)
        self.game = ie.Game(root)
        self.backup = self.root / "weidu_external/backup/chriz-bg-magic/0"
        # Files the install wrote (WeiDU's uninstall list); it left the others alone.
        listing = self.backup / "UNINSTALL.0"
        self.written = {Path(ln.strip()).name.upper() for ln in listing.read_text(encoding="latin-1").splitlines()
                        if ln.strip()} if listing.exists() else set()
        ids = self.game.get("SPELL", "IDS").decode("latin-1")
        self.ids = {}
        for line in ids.splitlines():
            p = line.split()
            if len(p) >= 2 and p[0].isdigit():
                self.ids[p[1]] = int(p[0])

    def resref(self, symbol):
        n = self.ids[symbol]
        return {1: "SPPR", 2: "SPWI", 3: "SPIN", 4: "SPCL"}[n // 1000] + f"{n % 1000:03d}"

    def now(self, res, ext="SPL"):
        return self.game.get(res, ext)

    def before(self, res, ext="SPL"):
        """The file before the install: WeiDU's backup copy when the install replaced an
        override file, the BIFF copy when it created one, the file itself otherwise."""
        name = f"{res}.{ext}".upper()
        if name not in self.written:
            return self.now(res, ext)
        b = next((p for p in self.backup.glob("*") if p.name.upper() == name), None)
        return b.read_bytes() if b else self.game.biff(res, ext)

    def text(self, strref):
        return self.game.tlk(strref, "en_us") if strref >= 0 else None


def same_but(a, b, fields):
    return {k: v for k, v in a.items() if k not in fields} == {k: v for k, v in b.items() if k not in fields}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("game", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    g = Installed(args.game)
    report, failures = [], []

    def ok(cond, msg):
        (report if cond else failures).append(("ok   " if cond else "FAIL ") + msg)

    def spl(res):
        return ie.parse_spl(g.now(res)), ie.parse_spl(g.before(res))

    log = (args.game / "WeiDU.log").read_text(encoding="latin-1")
    ok(re.search(r"(?im)^~SETUP-CHRIZ-BG-MAGIC\.TP2~ #0 #0", log) is not None, "WeiDU.log lists chriz-bg-magic #0")

    # Spirit Armor
    res = g.resref("WIZARD_SPIRIT_ARMOR")
    now, old = spl(res)
    for a, b in zip(now["abilities"], old["abilities"]):
        first = a["effects"][0]
        ok(first["opcode"] == 321 and first["resource"] == res and first["timing"] == 1
           and first["target"] == (1 if a["target"] in (5, 7) else 2) and a["effects"][1:] == b["effects"],
           f"Spirit Armor {res}: refresh first, rest unchanged ({len(b['effects'])} effects)")

    # Minor Spell Deflection
    res = g.resref("WIZARD_MINOR_SPELL_DEFLECTION")
    now, old = spl(res)
    for i, (a, b) in enumerate(zip(now["abilities"], old["abilities"])):
        lv = sorted(e["p2"] for e in a["effects"] if e["opcode"] == 201)
        ok(lv == sorted(e["p2"] for e in b["effects"] if e["opcode"] == 201 and e["p2"] <= 4)
           and max(lv) == 4 and [e for e in a["effects"] if e["opcode"] != 201] == [e for e in b["effects"] if e["opcode"] != 201]
           and any(e["resource"] for e in a["effects"] if e["opcode"] == 201) ==
           any(e["resource"] for e in b["effects"] if e["opcode"] == 201),
           f"Minor Spell Deflection {res} ability {i} (min level {a['min_level']}): levels {lv}")
    t = g.text(now["desc"]) or ""
    ok("up to 4th-level spells" in t and "up to 7th-level" not in t, "Minor Spell Deflection text says up to 4th-level spells")

    # Save vs. breath
    for sym in SAVE_RULE:
        res = g.resref(sym)
        targets = [res]
        now, old = spl(res)
        targets += sorted({e["resource"] for a in old["abilities"] for e in a["effects"]
                           if e["opcode"] in (146, 148) and e["resource"].startswith(res) and e["resource"] != res})
        switched, good, parts = 0, True, []
        for r in targets:
            now, old = spl(r)
            n = 0
            for a, b in zip(now["abilities"], old["abilities"]):
                for e, f in zip(a["effects"], b["effects"]):
                    if f["opcode"] == 12 and f["save"] & 1:
                        good &= e["save"] == (f["save"] & ~1) | 2 and same_but(e, f, {"save"})
                        n += 1
                    else:
                        good &= e == f
            switched += n
            parts.append(f"{r} {n}")
        ok(good and switched > 0, f"{sym}: damage effects saving vs. breath ({', '.join(parts)}), nothing else changed")
        now = ie.parse_spl(g.now(res))
        t = g.text(now["desc"]) or ""
        names = "names vs. Breath" if "vs. Breath" in t else "names no save type"
        ok("vs. Spell" not in t, f"{sym} text: {names}, no vs. Spell left")
    for sym in KEEP_SAVE:
        res = g.resref(sym)
        ok(f"{res}.SPL" not in g.written, f"{sym} {res}: unchanged")

    # Damage wakes sleepers
    for sym in SLEEP:
        res = g.resref(sym)
        now, _ = spl(res)
        # EE Fixpack moves Emotion: Hopelessness' sleep into a spell of its own.
        targets = [res] + sorted({e["resource"] for a in now["abilities"] for e in a["effects"]
                                  if e["opcode"] in (146, 148) and e["resource"].startswith(res) and e["resource"] != res})
        p2, rest = [], True
        for r in targets:
            now, old = spl(r)
            p2 += [e["p2"] for a in now["abilities"] for e in a["effects"] if e["opcode"] in (39, 217)]
            rest &= all(same_but(e, f, {"p2"}) if f["opcode"] in (39, 217) else e == f
                        for a, b in zip(now["abilities"], old["abilities"]) for e, f in zip(a["effects"], b["effects"]))
        ok(p2 and set(p2) == {0} and rest,
           f"{sym} {', '.join(targets)}: {len(p2)} sleep effects wake on damage, nothing else changed")

    # Web
    res = g.resref("WIZARD_WEB")
    now, old = spl(res)
    races = {}
    for line in g.game.get("RACE", "IDS").decode("latin-1").splitlines():
        p = line.split()
        if len(p) >= 2 and p[0].isdigit():
            races[p[1]] = int(p[0])
    rows = [ln.split() for ln in g.game.get("SPLPROT", "2DA").decode("latin-1").splitlines()]
    rows = [r for r in rows[3:] if len(r) >= 4]
    for i, (a, b) in enumerate(zip(now["abilities"], old["abilities"])):
        imm = a["effects"][:len(WEB_RACES)]
        row_ok = all(int(rows[e["p2"]][1], 0) == 0x10c and rows[e["p2"]][2] == "-1" and rows[e["p2"]][3] == "1"
                     for e in imm if e["opcode"] == 324)
        ok(sorted((e["opcode"], e["p1"]) for e in imm) == sorted((324, races[r]) for r in WEB_RACES)
           and all(e["resource"] == res for e in imm) and row_ok,
           f"Web {res} ability {i}: {len(WEB_RACES)} races immune (SPLPROT row {imm[0]['p2']})")
        rest = a["effects"][len(WEB_RACES):]
        group = {f["bonus"] for f in b["effects"] if f["opcode"] == 157 and f["save"] & 1}
        good = len(rest) == len(b["effects"])
        for e, f in zip(rest, b["effects"]):
            if f["save"] & 1 and f["bonus"] in group:
                good &= e["save"] == (f["save"] & ~1) | 2 and same_but(e, f, {"save"})
            else:
                good &= e == f
        ok(good, f"Web {res} ability {i}: the web's roll saves vs. breath (bonus {sorted(group)}), nothing else changed")
    t = g.text(now["desc"]) or ""
    ok("vs. Breath with a -2 penalty" in t and "vs. Spell" not in t, "Web text says vs. Breath with a -2 penalty")

    print("\n".join(report + failures))
    print(f"{len(report)} checks passed, {len(failures)} failed")
    if args.json:
        args.json.write_text(json.dumps({"passed": report, "failed": failures}, indent=1), encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
