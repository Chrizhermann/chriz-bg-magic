"""Writes tools/rows.json: the English name, group, level and (where unambiguous) the vanilla
resrefs of every row on Christopher's decision page. build_list.py joins it with his
decisions. Run it again when the page gains rows.

usage: python -I tools/make_rows.py --ideas <folder with ideas_*.json> --iwd-rows <iwd_rows.json>
                                    --game <vanilla BG2:EE folder> [--out tools/rows.json]

--ideas and --iwd-rows are the design chat's working data (row ids, English names, levels);
--game is a game whose BIFFs are read (read-only) to find each spell's vanilla resref by its
name, type and level. Only the fields named above are taken over.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import ie  # noqa: E402

# The page's own rows: cross-cutting rules (x.*) and SR components or fork parts (k.*).
PAGE_ROWS = {
    "x.beschreibungen": ("Accurate descriptions", "all spells"),
    "x.nur-feinde": ("Area spells that hit only enemies", "several levels"),
    "x.druiden-kleriker": ("Separate cleric and druid spell lists", "priest"),
    "x.buff-dauern": ("Longer buff durations (prebuff style)", "several levels"),
    "x.buff-stacking": ("Limit buff stacking", "priest and wizard"),
    "x.universal": ("Universal school for Contingency, Sequencer, Trigger, Wish", "wizard"),
    "k.10": ("Deva and Planetar avatars (SR component 10)", "HLA summons"),
    "k.20": ("Mirror Image fix (SR component 20)", "wizard 2"),
    "k.30": ("Dispel Magic fix (SR component 30)", "Dispel Magic, Remove Magic"),
    "k.55": ("Spell Deflection stops area spells (SR component 55)", "Spell Deflection, Turning, Trap"),
    "k.60": ("Joinable NPCs' spellbooks (SR component 60)", "joinable NPCs"),
    "k.65": ("Revised warrior HLAs (SR component 65)", "warrior HLAs"),
    "k.70": ("Revised saving throws (SR component 70)", "all classes"),
    "k.80": ("Lightning Bolt: classic or without bouncing (fork components 80/81)", "wizard 3"),
    "k.refresh": ("Protection refresh on the right target (fork)", "wizard 6-8"),
    "k.rr": ("Rogue Rebalancing with SR (fork tail)", "enemy mages"),
}


def vanilla_spells(game):
    """{(type, lowercase name): [(resref, level)]} for the wizard and priest spells that
    SPELL.IDS lists as WIZARD_* or CLERIC_* (the learnable ones; unused copies such as a
    second "Lightning Bolt" are left out)."""
    g = ie.Game(game)
    learnable = set()
    for line in g.get("SPELL", "IDS").decode("latin-1").splitlines():
        p = line.split()
        if len(p) >= 2 and p[0].isdigit() and p[1].startswith(("WIZARD_", "CLERIC_")):
            n = int(p[0])
            learnable.add(("SPPR" if n // 1000 == 1 else "SPWI") + f"{n % 1000:03d}")
    out = {}
    for (name, kind) in g.index:
        if kind != ie.TYPES["SPL"] or name not in learnable:
            continue
        data = g.biff(name, "SPL")
        try:
            spl = ie.parse_spl(data)
        except ValueError:
            continue
        text = g.tlk(spl["name"]) if spl["name"] >= 0 else None
        if text:
            out.setdefault((spl["type"], norm(text)), []).append((name, spl["level"]))
    return out


def norm(name):
    """Names compare without case and punctuation: "Power Word, Sleep" = "Power Word Sleep"."""
    return re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()


def level_of(row):
    m = re.search(r"(\d+)", row.get("level_label", ""))
    return int(m.group(1)) if m else None


def resolve(row, spells):
    kind = 1 if row["id"].startswith("arcane.") else 2 if row["id"].startswith("divine.") else None
    if kind is None or row.get("kind") == "bundle":
        return []
    found = spells.get((kind, norm(row["name"])), [])
    level = level_of(row)
    if level and level <= 9:
        found = [f for f in found if f[1] == level]
    return [found[0][0]] if len(found) == 1 else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ideas", required=True, type=Path)
    ap.add_argument("--iwd-rows", required=True, type=Path)
    ap.add_argument("--game", required=True, type=Path)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "rows.json")
    args = ap.parse_args()
    spells = vanilla_spells(args.game)
    rows = {}
    for f in sorted(args.ideas.glob("ideas_*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            rows[r["id"]] = {"name": r["name"], "group": r["group"], "level": r["level_label"],
                             "kind": r["kind"], "source": "sr-catalog", "resrefs": resolve(r, spells)}
    iwd = json.loads(args.iwd_rows.read_text(encoding="utf-8"))
    for r in iwd["rows"] if isinstance(iwd, dict) else iwd:
        rows[r["id"]] = {"name": r["name"], "group": r["group"], "level": r["level_label"], "kind": "spell",
                         "source": "iwd", "resrefs": []}
    # A resref that two rows claim (e.g. a row named after another spell) is ambiguous.
    claims = {}
    for rid, r in rows.items():
        for ref in r["resrefs"]:
            claims.setdefault(ref, []).append(rid)
    for ref, rids in claims.items():
        if len(rids) > 1:
            for rid in rids:
                rows[rid]["resrefs"] = [x for x in rows[rid]["resrefs"] if x != ref]
    for rid, (name, level) in PAGE_ROWS.items():
        rows[rid] = {"name": name, "group": rid.split(".")[0], "level": level, "kind": "page", "source": "page",
                     "resrefs": []}
    args.out.write_text(json.dumps(dict(sorted(rows.items())), indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"{len(rows)} rows, {sum(1 for r in rows.values() if r['resrefs'])} with a vanilla resref -> {args.out.name}")


if __name__ == "__main__":
    main()
