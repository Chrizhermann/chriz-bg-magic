"""Made-up game folders for the offline WeiDU tests: a chitin.key with one BIFF, a
dialog.tlk, an override folder and the mod folder. All data is built in the tests; no game
files are read.
"""
import hashlib
import shutil
import subprocess
from pathlib import Path

import ie

REPO = Path(__file__).resolve().parents[1]
MOD = REPO / "chriz-bg-magic"

# Areas WeiDU's GAME_IS looks for (EET also has override/eet.flag).
GAME_MARKERS = {"bgee": ["OH1000"], "bg2ee": ["OH6000"], "eet": ["OH1000", "OH6000"]}


class FakeGame:
    """A fresh fake game (BG2:EE unless `game` says bgee or eet). biff/override:
    {"NAME.EXT": bytes}. tp2: text of the tp2 to run (default: the mod's real tp2)."""

    def __init__(self, root, weidu, tp2=None, tlk=None, biff=None, override=None, game="bg2ee",
                 files=None):
        self.root, self.weidu = Path(root), weidu
        shutil.rmtree(self.root, ignore_errors=True)
        (self.root / "override").mkdir(parents=True)
        (self.root / "lang/en_us").mkdir(parents=True)
        (self.root / "lang/en_us/dialog.tlk").write_bytes(tlk or ie.make_tlk([""]))
        shutil.copytree(MOD, self.root / "chriz-bg-magic")
        tp2_text = tp2 if tp2 is not None else (REPO / "setup-chriz-bg-magic.tp2").read_text(encoding="utf-8")
        (self.root / "setup-chriz-bg-magic.tp2").write_text(tp2_text, encoding="utf-8")
        if game == "eet":
            (self.root / "override/eet.flag").write_bytes(b"EET")
        resources = [(m, ie.TYPES["ARE"], b"AREAV1.0") for m in GAME_MARKERS[game]]
        for name, data in (biff or {}).items():
            stem, ext = name.rsplit(".", 1)
            resources.append((stem, ie.TYPES[ext.upper()], data))
        ie.write_key_bif(self.root, resources)
        for name, data in (override or {}).items():
            (self.root / "override" / name).write_bytes(data)
        for rel, data in (files or {}).items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_bytes(data)

    def run(self, action="--force-install-list", components=("0",)):
        out = subprocess.run([str(self.weidu), "setup-chriz-bg-magic.tp2", "--no-auto-tp2", "--noautoupdate",
                              "--game", str(self.root), "--language", "0", "--use-lang", "en_US", action,
                              *components, "--no-exit-pause", "--log", f"weidu{action}.debug"],
                             cwd=self.root, stdin=subprocess.DEVNULL, capture_output=True, timeout=300)
        text = (out.stdout + out.stderr).decode("utf-8", "replace")
        (self.root / f"weidu{action}.transcript").write_text(text, encoding="utf-8")
        return text

    def install(self, components=("0",)):
        return self.run("--force-install-list", components)

    def uninstall(self, components=("0",)):
        return self.run("--force-uninstall-list", components)

    def spl(self, resref):
        return ie.parse_spl((self.root / "override" / f"{resref}.SPL").read_bytes())

    def file(self, rel):
        p = self.root / rel
        return p.read_bytes() if p.exists() else None

    def tlk(self, strref):
        return ie.tlk_text((self.root / "lang/en_us/dialog.tlk").read_bytes(), strref)

    def tree(self):
        """Hashes of the game's files apart from the mod folder, WeiDU's own files and
        dialog.tlk (WeiDU keeps appended strings on uninstall)."""
        out = {}
        for p in self.root.rglob("*"):
            rel = p.relative_to(self.root).as_posix().lower()
            if p.is_file() and not (rel.startswith(("chriz-bg-magic/", "weidu", "setup-chriz-bg-magic"))
                                    or rel.endswith("dialog.tlk")):
                out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        return out


def installed_ok(out):
    return "SUCCESSFULLY INSTALLED" in out or "INSTALLED WITH WARNINGS" in out


def with_warnings(out):
    return "INSTALLED WITH WARNINGS" in out


def failed(out):
    return "NOT INSTALLED DUE TO ERRORS" in out
