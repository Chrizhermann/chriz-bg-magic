"""Offline checks for the website spell catalog source and BAM/WebP exporter."""
from __future__ import annotations

import json
import re
import struct
import sys
import tempfile
import zlib
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
TOOLS_DIR = REPO_ROOT / "tools"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from export_site_catalog import clean_ie_text, decode_bam_frame_to_image, load_tra  # noqa: E402
from harness import check, test  # noqa: E402

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_TRADITIONS = {"wizard", "divine"}
ALLOWED_ORIGINS = {"modified", "new", "iwd-optional"}
ALLOWED_CHANGE_TYPES = {"buff", "minor-buff", "nerf", "minor-nerf", "rework", "new", "fix"}
ALLOWED_TAGS = {
    "typed-bonus",
    "family",
    "healing",
    "summon",
    "celestial",
    "save-mechanics",
    "dispel-protection",
    "casting-time",
    "druid",
    "iwd-optional",
    "eeex",
}


def _build_synthetic_bam(compressed_bamc: bool = False) -> bytes:
    """Builds a minimal 4x4 BAM V1 with rle=0 transparent and pal[1] pure red (BGRA=0,0,255,255)."""
    w, h = 4, 4
    rle_idx = 0
    # 1 frame, 1 cycle, rle=0, frame_entries_off=24, palette_off=40, lookup_off=1064
    feo = 24
    po = feo + 12 + 4  # 1 frame (12B) + 1 cycle (4B) = 40
    lto = po + 256 * 4  # 1064
    data_off = lto + 2  # 1066

    pal = bytearray(256 * 4)
    # index 0 = unused magenta (transparent via rle_idx=0)
    struct.pack_into("<BBBB", pal, 0, 255, 0, 255, 0)
    # index 1 = red in BGRA (B=0, G=0, R=255, A=255)
    struct.pack_into("<BBBB", pal, 4, 0, 0, 255, 255)

    # 4x4 pixels: border index 0 (transparent), center 2x2 index 1 (red), compressed RLE
    raw_pixels = [
        0, 0, 0, 0,
        0, 1, 1, 0,
        0, 1, 1, 0,
        0, 0, 0, 0,
    ]
    # RLE encode against rle_idx=0
    frame_bytes = bytearray()
    i = 0
    while i < len(raw_pixels):
        if raw_pixels[i] == rle_idx:
            run = 1
            while i + run < len(raw_pixels) and raw_pixels[i + run] == rle_idx and run < 256:
                run += 1
            frame_bytes.extend((rle_idx, run - 1))
            i += run
        else:
            frame_bytes.append(raw_pixels[i])
            i += 1

    header = struct.pack("<8sHBBIII", b"BAM V1  ", 1, 1, rle_idx, feo, po, lto)
    frame_entry = struct.pack("<HHhhI", w, h, 0, 0, data_off)  # bit 31 clear => RLE compressed
    cycle_entry = struct.pack("<HH", 1, 0)
    lookup = struct.pack("<H", 0)
    uncompressed = header + frame_entry + cycle_entry + bytes(pal) + lookup + bytes(frame_bytes)
    if not compressed_bamc:
        return uncompressed
    zdata = zlib.compress(uncompressed)
    return struct.pack("<8sI", b"BAMCV1  ", len(uncompressed)) + zdata


@test
def test_site_catalog(work, _weidu=None):
    source_path = REPO_ROOT / "docs" / "site-catalog-source.json"
    check(source_path.is_file(), f"Missing {source_path}")
    raw_source = source_path.read_text(encoding="utf-8")
    source = json.loads(raw_source)

    for forbidden in ("Flind", "PLANGOOD", "expect bugs", "OneDrive", "C:\\" + "Users"):
        check(forbidden not in raw_source, f"Forbidden text {forbidden!r} in site-catalog-source.json")

    exporter_text = (TOOLS_DIR / "export_site_catalog.py").read_text(encoding="utf-8")
    for forbidden in ("OneDrive", "C:\\" + "Users"):
        check(forbidden not in exporter_text, f"Forbidden personal path {forbidden!r} in export_site_catalog.py")

    tra = load_tra(REPO_ROOT / "chriz-bg-magic" / "languages" / "english" / "setup.tra")
    for required_tra in (50100, 50101, 60100, 60101, 60102, 60105, 60106, 60107, 60108):
        check(required_tra in tra, f"Expected @{required_tra} in setup.tra")

    seen_slugs = set()
    covered_defs = set()
    for entry in source["spells"]:
        slug = entry["slug"]
        check(SLUG_RE.match(slug), f"Invalid slug: {slug}")
        check(slug not in seen_slugs, f"Duplicate slug: {slug}")
        seen_slugs.add(slug)

        check(entry["tradition"] in ALLOWED_TRADITIONS, f"Bad tradition on {slug}")
        check(entry["level"] in (*range(1, 10), 10), f"Bad level on {slug}")
        check(entry["origin"] in ALLOWED_ORIGINS, f"Bad origin on {slug}")
        check(entry.get("changeType") in ALLOWED_CHANGE_TYPES, f"Bad changeType on {slug}")
        check((entry["origin"] == "new") == (entry["changeType"] == "new"), f"Mismatched new changeType/origin on {slug}")
        check("Quest" not in entry["levelLabel"], f"Forbidden 'Quest' in levelLabel on {slug}")
        check("Quest" not in entry.get("access", ""), f"Forbidden 'Quest' in access on {slug}")
        check(bool(entry["summary"].strip()), f"Empty summary on {slug}")
        check(set(entry["tags"]).issubset(ALLOWED_TAGS) and entry["tags"], f"Bad tags on {slug}")

        src_kind, src_ref = entry["source"].split(":", 1)
        check(src_kind in {"defs", "bg2ee", "iwd"}, f"Bad source on {slug}")
        if src_kind == "defs":
            check((REPO_ROOT / "defs" / f"{src_ref}.spl.json").is_file(), f"Missing defs SPL for {slug}: {src_ref}")
            covered_defs.add(src_ref.lower())
        for rel in entry.get("relatedResrefs", []):
            if (REPO_ROOT / "defs" / f"{rel.lower()}.spl.json").is_file():
                covered_defs.add(rel.lower())

    for hl in source.get("highlights", []):
        check(hl.get("direction") in ALLOWED_CHANGE_TYPES, f"Bad direction on highlight {hl.get('id')}")
        slugs = hl.get("spellSlugs")
        check(isinstance(slugs, list) and len(slugs) > 0, f"Missing spellSlugs on highlight {hl.get('id')}")
        for hl_slug in slugs:
            check(hl_slug in seen_slugs, f"Unknown spellSlug {hl_slug!r} on highlight {hl.get('id')}")

    internal_set = {r.lower() for r in source["internalResrefs"]}
    check(not (covered_defs & internal_set), f"Overlap between spells and internalResrefs: {covered_defs & internal_set}")

    all_tracked = {
        p.name[:-9].lower()
        for p in (REPO_ROOT / "defs").glob("*.spl.json")
        if p.name.lower().startswith(("sppr", "spwi", "cbm"))
        or p.name[:-9].lower() in {"spcl923", "spcl935", "projimag", "simulacr"}
    }
    uncategorized = all_tracked - covered_defs - internal_set
    check(not uncategorized, f"Uncategorized defs spell files: {sorted(uncategorized)}")

    # Verify BAM V1 + BAMC V1 decoding & lossless 64x64 WebP output
    for compressed in (False, True):
        img = decode_bam_frame_to_image(_build_synthetic_bam(compressed_bamc=compressed), frame_index=0)
        check(img.size == (64, 64), f"Expected 64x64 image, got {img.size}")
        check(img.getpixel((0, 0)) == (0, 0, 0, 0), f"Expected transparent corner, got {img.getpixel((0, 0))}")
        # Center of 32x32 frame (15,15) scaled 2x -> (30,30) should be pure red from BGRA palette
        check(img.getpixel((30, 30)) == (255, 0, 0, 255), f"Expected red center pixel, got {img.getpixel((30, 30))}")
        out_webp = Path(work) / f"test_{compressed}.webp"
        img.save(out_webp, format="WEBP", lossless=True, quality=100)
        check(out_webp.is_file() and out_webp.stat().st_size > 0, "Failed saving lossless WebP")

    cleaned = clean_ie_text("Gives <PRO_HISHER> ally ^0xFF00FF00bonus^-.\r\n\r\n\r\nDone")
    check("<PRO_" not in cleaned and "^0x" not in cleaned and "^-" not in cleaned, f"Token not cleaned: {cleaned!r}")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        test_site_catalog(Path(tmp))
    print("test_site_catalog OK")
