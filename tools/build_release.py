"""Build release archive and SHA-256 checksum for Chriz BG Magic."""
from __future__ import annotations

import argparse
import hashlib
import re
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TP2_PATH = REPO_ROOT / "setup-chriz-bg-magic.tp2"
VERSION_RE = re.compile(r"^VERSION\s+~v?([^~\s]+)~", re.MULTILINE)


def read_tp2_version() -> str:
    match = VERSION_RE.search(TP2_PATH.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"Could not find VERSION in {TP2_PATH}")
    return match.group(1)


def build_release(version: str, weidu_path: Path, out_dir: Path) -> tuple[Path, Path]:
    clean_version = version.lstrip("v")
    tp2_version = read_tp2_version()
    if clean_version != tp2_version:
        raise ValueError(f"Requested version {clean_version!r} does not match .tp2 VERSION {tp2_version!r}")
    if not weidu_path.is_file():
        raise FileNotFoundError(f"WeiDU binary not found: {weidu_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"chriz-bg-magic-v{clean_version}.zip"
    zip_path = out_dir / zip_name
    sha_path = out_dir / f"{zip_name}.sha256"

    mod_dir = REPO_ROOT / "chriz-bg-magic"
    if not mod_dir.is_dir():
        raise FileNotFoundError(f"Mod directory missing: {mod_dir}")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(TP2_PATH, "setup-chriz-bg-magic.tp2")
        zf.write(weidu_path, "setup-chriz-bg-magic.exe")
        for doc_name in ("README.md", "CHANGELOG.md", "LICENSE"):
            doc_path = REPO_ROOT / doc_name
            if doc_path.is_file():
                zf.write(doc_path, doc_name)
        for item in sorted(mod_dir.rglob("*")):
            if item.is_file() and "__pycache__" not in item.parts and item.suffix != ".pyc":
                arcname = item.relative_to(REPO_ROOT).as_posix()
                zf.write(item, arcname)

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    sha_path.write_text(f"{digest}  {zip_name}\n", encoding="utf-8", newline="\n")
    return zip_path, sha_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Package Chriz BG Magic release zip and sha256.")
    ap.add_argument("--version", default=None, help="Release version (defaults to .tp2 VERSION)")
    ap.add_argument("--weidu", required=True, type=Path, help="Path to weidu.exe")
    ap.add_argument("--out-dir", type=Path, default=REPO_ROOT / "dist")
    args = ap.parse_args()

    version = args.version or read_tp2_version()
    zip_path, sha_path = build_release(version, args.weidu, args.out_dir)
    print(f"Built {zip_path} and {sha_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
