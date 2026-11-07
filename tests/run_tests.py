"""Offline tests for the installer: real WeiDU runs in small made-up game folders. No game
installation or game files are needed; every test builds its own data.

usage: python tests/run_tests.py --weidu <path to weidu.exe> [--keep DIR] [-k NAME]
Exit code 0 when every test passes.
"""
import argparse
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_frame  # noqa: E402,F401  (registers its tests)
import test_healing  # noqa: E402,F401
import test_bonus  # noqa: E402,F401
import test_live  # noqa: E402,F401
import test_resources  # noqa: E402,F401
from harness import TESTS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weidu", required=True, type=Path)
    ap.add_argument("--keep", type=Path, help="keep the test games in this folder")
    ap.add_argument("-k", help="run only tests whose name contains this")
    args = ap.parse_args()
    base = args.keep or Path(tempfile.mkdtemp(prefix="cbm-"))
    failed = ran = 0
    for number, fn in enumerate(TESTS, 1):
        if args.k and args.k not in fn.__name__:
            continue
        # Short folder names: WeiDU fails on paths near the Windows 260-character limit.
        work = base / f"t{number:02d}"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        ran += 1
        try:
            fn(work, args.weidu.resolve())
            print(f"ok    t{number:02d} {fn.__name__}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL  t{number:02d} {fn.__name__}\n{traceback.format_exc()}")
    if not args.keep:
        shutil.rmtree(base, ignore_errors=True)
    print(f"{ran} tests, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
