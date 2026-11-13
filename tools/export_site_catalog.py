"""Export static web catalog JSON and 64x64 WebP spell icons for bg-site."""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import zlib
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "docs" / "site-catalog-source.json"
DEFAULT_TRA = REPO_ROOT / "chriz-bg-magic" / "languages" / "english" / "setup.tra"

SCHOOL_NAMES = {
    0: "Universal",
    1: "Abjuration",
    2: "Conjuration/Summoning",
    3: "Divination",
    4: "Enchantment/Charm",
    5: "Illusion/Phantasm",
    6: "Evocation",
    7: "Necromancy",
    8: "Alteration",
}

DEFAULT_GAME_CANDIDATES = {
    "bg2ee": [
        r"C:\Program Files (x86)\Steam\steamapps\common\Baldur's Gate II Enhanced Edition",
        r"D:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition",
        r"E:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition",
        r"C:\GOG Games\Baldur's Gate II - Enhanced Edition",
    ],
    "iwdee": [
        r"C:\Program Files (x86)\Steam\steamapps\common\Icewind Dale Enhanced Edition",
        r"D:\SteamLibrary\steamapps\common\Icewind Dale Enhanced Edition",
        r"E:\SteamLibrary\steamapps\common\Icewind Dale Enhanced Edition",
        r"C:\GOG Games\Icewind Dale - Enhanced Edition",
    ],
}

IE_TOKEN_REPLACEMENTS = (
    ("<PRO_HESHE>", "he/she"),
    ("<PRO_HISHER>", "his/her"),
    ("<PRO_HIMHER>", "him/her"),
    ("<PRO_MANWOMAN>", "man/woman"),
    ("<PRO_SIRMAAM>", "sir/ma'am"),
    ("<CHARNAME>", "the caster"),
    ("<DAYNIGHT>", "day"),
)


def clean_ie_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    for token, repl in IE_TOKEN_REPLACEMENTS:
        cleaned = cleaned.replace(token, repl).replace(token.lower(), repl)
    cleaned = re.sub(r"\^0x[0-9A-Fa-f]{8}", "", cleaned)
    cleaned = cleaned.replace("^-", "")
    # Collapse excessive blank lines while preserving paragraphs
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def load_tra(path: Path) -> dict[int, str]:
    raw = path.read_text(encoding="utf-8")
    out: dict[int, str] = {}
    pattern = re.compile(r"@(\d+)\s*=\s*~([^~]*)~", re.DOTALL)
    for match in pattern.finditer(raw):
        out[int(match.group(1))] = match.group(2)
    return out


class InfinityGameArchive:
    """Read-only loader for unmodded EE game dialog.tlk and chitin.key/BIFF resources."""

    def __init__(self, game_dir: Path):
        self.game_dir = game_dir
        self._tlk: list[str] | None = None
        self._key_index: dict[tuple[str, int], int] | None = None
        self._bifs: list[str] = []
        self._bif_cache: dict[int, bytes] = {}
        self._override_dir = game_dir / "override"

    def get_tlk(self, strref: int) -> str:
        if strref < 0:
            return ""
        if self._tlk is None:
            tlk_path = self.game_dir / "lang" / "en_US" / "dialog.tlk"
            data = tlk_path.read_bytes()
            count, str_off = struct.unpack_from("<II", data, 10)
            strings: list[str] = []
            for i in range(count):
                _, _, _, _, text_off, text_len = struct.unpack_from("<H8sIIII", data, 18 + i * 26)
                strings.append(data[str_off + text_off : str_off + text_off + text_len].decode("utf-8", "replace"))
            self._tlk = strings
        if 0 <= strref < len(self._tlk):
            return self._tlk[strref]
        return ""

    def _ensure_key_index(self) -> None:
        if self._key_index is not None:
            return
        key = (self.game_dir / "chitin.key").read_bytes()
        nbif, nres, bif_off, res_off = struct.unpack_from("<IIII", key, 8)
        bifs: list[str] = []
        for i in range(nbif):
            _, fname_off, fname_len, _ = struct.unpack_from("<IIHH", key, bif_off + i * 12)
            fname = key[fname_off : fname_off + fname_len - 1].decode("ascii", "replace").replace("\\", "/")
            bifs.append(fname)
        self._bifs = bifs

        index: dict[tuple[str, int], int] = {}
        for i in range(nres):
            rname = (
                key[res_off + i * 14 : res_off + i * 14 + 8]
                .rstrip(b"\x00")
                .decode("ascii", "replace")
                .upper()
            )
            rtype, loc = struct.unpack_from("<HI", key, res_off + i * 14 + 8)
            index[(rname, rtype)] = loc
        self._key_index = index

    def get_resource(self, resref: str, rtype: int, ext: str) -> bytes | None:
        ov = self._override_dir / f"{resref}.{ext}"
        if ov.is_file():
            return ov.read_bytes()
        self._ensure_key_index()
        assert self._key_index is not None
        loc = self._key_index.get((resref.upper(), rtype))
        if loc is None:
            return None
        bidx = (loc >> 20) & 0xFFF
        fidx = loc & 0x3FFF
        bif_bytes = self._bif_cache.get(bidx)
        if bif_bytes is None:
            bif_path = self.game_dir / self._bifs[bidx]
            raw = bif_path.read_bytes()
            sig = raw[:8]
            if sig == b"BIFFV1  ":
                bif_bytes = raw
            elif sig == b"BIFCV1.0":
                # Compressed BIFC container: skip 12 bytes + block stream
                pos = 12
                out = bytearray()
                uncomp_size = struct.unpack_from("<I", raw, 8)[0]
                while len(out) < uncomp_size and pos < len(raw):
                    u_sz, c_sz = struct.unpack_from("<II", raw, pos)
                    pos += 8
                    out.extend(zlib.decompress(raw[pos : pos + c_sz])[:u_sz])
                    pos += c_sz
                bif_bytes = bytes(out)
            else:
                raise ValueError(f"Unsupported BIF signature {sig!r} in {bif_path}")
            self._bif_cache[bidx] = bif_bytes

        _, _, entries_off = struct.unpack_from("<III", bif_bytes, 8)
        _, res_off, res_size, _, _ = struct.unpack_from("<IIIHH", bif_bytes, entries_off + fidx * 16)
        return bif_bytes[res_off : res_off + res_size]


def decode_bam_frame_to_image(raw: bytes, frame_index: int = 0) -> Image.Image:
    """Decode a BAM V1 / BAMC V1 frame onto a 64x64 crisp RGBA Image."""
    if raw[:4] == b"BAMC":
        raw = zlib.decompress(raw[12:])
    if raw[:8] != b"BAM V1  ":
        raise ValueError(f"Unsupported BAM signature: {raw[:8]!r}")

    frame_count, _cycle_count, rle_idx, feo, po, _lto = struct.unpack_from("<HBBIII", raw, 8)
    if frame_index >= frame_count:
        raise IndexError(f"Requested frame {frame_index} >= frame count {frame_count}")

    # Palette entries are BGRA in BAM V1
    palette = []
    for idx in range(256):
        b, g, r, _a = struct.unpack_from("<BBBB", raw, po + idx * 4)
        if idx == rle_idx:
            palette.append((0, 0, 0, 0))
        else:
            palette.append((r, g, b, 255))

    w, h, _cx, _cy, doff = struct.unpack_from("<HHhhI", raw, feo + frame_index * 12)
    off = doff & 0x7FFFFFFF
    compressed = not bool(doff & 0x80000000)

    total = w * h
    indices = bytearray()
    p = off
    while len(indices) < total:
        val = raw[p]
        p += 1
        if compressed and val == rle_idx:
            run = raw[p] + 1
            p += 1
            indices.extend([rle_idx] * run)
        else:
            indices.append(val)

    rgba = bytearray(total * 4)
    for idx_pos, pal_idx in enumerate(indices[:total]):
        r, g, b, a = palette[pal_idx]
        out_pos = idx_pos * 4
        rgba[out_pos] = r
        rgba[out_pos + 1] = g
        rgba[out_pos + 2] = b
        rgba[out_pos + 3] = a

    frame_img = Image.frombytes("RGBA", (w, h), bytes(rgba))
    canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    if w <= 32 and h <= 32:
        canvas.paste(frame_img, ((32 - w) // 2, (32 - h) // 2))
    else:
        crop_x = max(0, (w - 32) // 2)
        crop_y = max(0, (h - 32) // 2)
        cropped = frame_img.crop((crop_x, crop_y, crop_x + min(32, w), crop_y + min(32, h)))
        canvas.paste(cropped, ((32 - cropped.width) // 2, (32 - cropped.height) // 2))

    return canvas.resize((64, 64), Image.Resampling.NEAREST)


def resolve_game_dir(explicit: str | None, env_var: str, key: str) -> Path:
    if explicit:
        p = Path(explicit)
        if not (p / "chitin.key").is_file():
            raise FileNotFoundError(f"Game directory missing chitin.key: {p}")
        return p
    env_val = os.environ.get(env_var)
    if env_val and (Path(env_val) / "chitin.key").is_file():
        return Path(env_val)
    for candidate in DEFAULT_GAME_CANDIDATES[key]:
        p = Path(candidate)
        if (p / "chitin.key").is_file():
            return p
    raise FileNotFoundError(f"Could not locate {key} installation. Set {env_var} or pass CLI flag.")


def resolve_strref_or_text(value, archive: InfinityGameArchive) -> str:
    if isinstance(value, dict):
        return str(value.get("text", ""))
    if isinstance(value, int) and value >= 0:
        return archive.get_tlk(value)
    return ""


def parse_binary_spl(raw: bytes, archive: InfinityGameArchive) -> dict:
    name_strref = struct.unpack_from("<I", raw, 0x08)[0]
    school_idx = raw[0x25]
    level = struct.unpack_from("<I", raw, 0x34)[0]
    header_icon = raw[0x3A:0x42].rstrip(b"\x00").decode("ascii", "replace")
    desc_strref = struct.unpack_from("<I", raw, 0x50)[0]
    ab_off, ab_cnt = struct.unpack_from("<IH", raw, 0x64)
    ab_icon = ""
    if ab_cnt > 0 and ab_off + 0x08 <= len(raw):
        ab_icon = raw[ab_off + 0x04 : ab_off + 0x0C].rstrip(b"\x00").decode("ascii", "replace")
    return {
        "name": archive.get_tlk(name_strref),
        "school": SCHOOL_NAMES.get(school_idx, "Unknown"),
        "level": level,
        "header_icon": header_icon,
        "ability_icon": ab_icon,
        "description": archive.get_tlk(desc_strref),
    }


def extract_school_from_desc(description: str, fallback: str) -> str:
    lines = [ln.strip() for ln in description.splitlines() if ln.strip()]
    if len(lines) >= 2 and lines[1].startswith("(") and lines[1].endswith(")"):
        return lines[1][1:-1]
    return fallback


def find_mod_bam(name: str) -> bytes | None:
    upper = name.upper()
    for folder in (REPO_ROOT / "chriz-bg-magic" / "files", REPO_ROOT / "chriz-bg-magic" / "res"):
        for candidate in (folder / f"{name.lower()}.bam", folder / f"{upper}.bam"):
            if candidate.is_file():
                return candidate.read_bytes()
    return None


def resolve_icon_bam(
    header_icon: str,
    ability_icon: str,
    prefer_iwd: bool,
    bg2ee: InfinityGameArchive,
    iwdee: InfinityGameArchive,
) -> bytes:
    candidates: list[str] = []
    if ability_icon:
        candidates.append(ability_icon)
    if header_icon:
        if header_icon.upper().endswith("C"):
            candidates.append(header_icon[:-1] + "B")
        candidates.append(header_icon)

    search_archives = (iwdee, bg2ee) if prefer_iwd else (bg2ee, iwdee)
    for icon_name in candidates:
        mod_bytes = find_mod_bam(icon_name)
        if mod_bytes is not None:
            return mod_bytes
        for archive in search_archives:
            res = archive.get_resource(icon_name, 0x3E8, "bam")
            if res is not None:
                return res

    raise FileNotFoundError(f"Could not find icon BAM among {candidates!r}")


def export_catalog(
    source_path: Path,
    out_json: Path,
    out_icons_dir: Path,
    bg2ee_dir: Path,
    iwdee_dir: Path,
) -> dict:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    tra = load_tra(DEFAULT_TRA)
    bg2ee = InfinityGameArchive(bg2ee_dir)
    iwdee = InfinityGameArchive(iwdee_dir)

    out_icons_dir.mkdir(parents=True, exist_ok=True)
    exported_spells = []

    for entry in source["spells"]:
        src_kind, src_ref = entry["source"].split(":", 1)
        prefer_iwd = src_kind == "iwd"

        if src_kind == "defs":
            spl_json = json.loads((REPO_ROOT / "defs" / f"{src_ref}.spl.json").read_text(encoding="utf-8"))
            hdr = spl_json["header"]
            abs_list = spl_json.get("abilities", [])
            raw_name = resolve_strref_or_text(hdr.get("name"), bg2ee)
            raw_desc = resolve_strref_or_text(hdr.get("description"), bg2ee)
            school_fallback = SCHOOL_NAMES.get(hdr.get("school", 0), "Unknown")
            header_icon = hdr.get("icon", "")
            ability_icon = abs_list[0].get("icon", "") if abs_list else ""
        elif src_kind in ("bg2ee", "iwd"):
            archive = iwdee if src_kind == "iwd" else bg2ee
            spl_bytes = archive.get_resource(src_ref, 0x3EE, "spl")
            if spl_bytes is None:
                raise FileNotFoundError(f"Spell {src_ref}.SPL not found in {src_kind}")
            parsed = parse_binary_spl(spl_bytes, archive)
            raw_name = parsed["name"]
            raw_desc = parsed["description"]
            school_fallback = parsed["school"]
            header_icon = parsed["header_icon"]
            ability_icon = parsed["ability_icon"]
        else:
            raise ValueError(f"Unsupported spell source kind: {entry['source']}")

        if "descriptionTra" in entry:
            tra_kind, tra_id_str = entry["descriptionTra"].split(":", 1)
            if tra_kind != "tra":
                raise ValueError(f"Unsupported descriptionTra: {entry['descriptionTra']}")
            tra_id = int(tra_id_str)
            if tra_id not in tra:
                raise KeyError(f"Missing TRA @{tra_id} in {DEFAULT_TRA}")
            raw_desc = tra[tra_id]

        description = clean_ie_text(raw_desc)
        if not description:
            raise ValueError(f"Empty resolved description for {entry['slug']} ({entry['source']})")

        name = entry.get("name") or clean_ie_text(raw_name).strip()
        if not name:
            name = description.splitlines()[0].strip()

        school = entry.get("school") or extract_school_from_desc(description, school_fallback)
        bam_bytes = resolve_icon_bam(header_icon, ability_icon, prefer_iwd, bg2ee, iwdee)
        icon_img = decode_bam_frame_to_image(bam_bytes, frame_index=0)
        icon_rel = f"/assets/spells/{entry['slug']}.webp"
        icon_file = out_icons_dir / f"{entry['slug']}.webp"
        icon_img.save(icon_file, format="WEBP", lossless=True, quality=100)

        vanilla_desc = ""
        vanilla_name = ""
        vanilla_spec = entry.get("vanillaSource")
        if entry["origin"] != "new" and vanilla_spec != "none":
            if vanilla_spec:
                v_kind, v_ref = vanilla_spec.split(":", 1)
                v_archive = iwdee if v_kind == "iwd" else bg2ee
                v_bytes = v_archive.get_resource(v_ref, 0x3EE, "spl")
            elif src_kind == "iwd":
                v_archive = iwdee
                v_bytes = iwdee.get_resource(src_ref, 0x3EE, "spl")
            else:
                v_archive = bg2ee
                v_bytes = bg2ee.get_resource(entry["resref"], 0x3EE, "spl")
                if v_bytes is None:
                    v_archive = iwdee
                    v_bytes = iwdee.get_resource(entry["resref"], 0x3EE, "spl")
            if v_bytes is not None:
                v_parsed = parse_binary_spl(v_bytes, v_archive)
                vanilla_desc = clean_ie_text(v_parsed["description"])
                vanilla_name = clean_ie_text(v_parsed["name"]).strip()

        out_entry = {
            "slug": entry["slug"],
            "name": name,
            "resref": entry["resref"],
            "tradition": entry["tradition"],
            "level": entry["level"],
            "levelLabel": entry["levelLabel"],
            "school": school,
            "origin": entry["origin"],
            "changeType": entry["changeType"],
            "tags": entry["tags"],
            "summary": entry["summary"],
            "description": description,
            "icon": icon_rel,
        }
        if vanilla_desc:
            out_entry["vanillaDescription"] = vanilla_desc
            if vanilla_name and vanilla_name.lower() != name.lower():
                out_entry["vanillaName"] = vanilla_name
        for opt in ("access", "relatedResrefs", "typedNote"):
            if opt in entry and entry[opt]:
                out_entry[opt] = entry[opt]
        exported_spells.append(out_entry)

    exported_spells.sort(key=lambda s: (0 if s["tradition"] == "wizard" else 1, s["level"], s["name"].lower(), s["slug"]))

    wizard_count = sum(1 for s in exported_spells if s["tradition"] == "wizard")
    divine_count = sum(1 for s in exported_spells if s["tradition"] == "divine")
    buff_count = sum(1 for s in exported_spells if s["changeType"] == "buff")
    minor_buff_count = sum(1 for s in exported_spells if s["changeType"] == "minor-buff")
    nerf_count = sum(1 for s in exported_spells if s["changeType"] == "nerf")
    minor_nerf_count = sum(1 for s in exported_spells if s["changeType"] == "minor-nerf")
    rework_count = sum(1 for s in exported_spells if s["changeType"] == "rework")
    new_count = sum(1 for s in exported_spells if s["changeType"] == "new")
    fix_count = sum(1 for s in exported_spells if s["changeType"] == "fix")
    iwd_count = sum(1 for s in exported_spells if s["origin"] == "iwd-optional")

    catalog = {
        "mod": source["mod"],
        "stats": {
            "totalSpells": len(exported_spells),
            "balanceChanges": len(exported_spells) - fix_count,
            "buffs": buff_count,
            "minorBuffs": minor_buff_count,
            "nerfs": nerf_count,
            "minorNerfs": minor_nerf_count,
            "reworks": rework_count,
            "newSpells": new_count,
            "fixes": fix_count,
            "wizardSpells": wizard_count,
            "divineSpells": divine_count,
            "iwdOptionalSpells": iwd_count,
        },
        "bonusTypes": source["bonusTypes"],
        "exclusiveFamilies": source["exclusiveFamilies"],
        "highlights": source["highlights"],
        "systemRules": source["systemRules"],
        "spells": exported_spells,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return catalog


def main() -> int:
    ap = argparse.ArgumentParser(description="Export Chriz BG Magic catalog & spell WebPs.")
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-icons-dir", type=Path, required=True)
    ap.add_argument("--bg2ee-dir", help="Path to unmodded BG2:EE folder")
    ap.add_argument("--iwdee-dir", help="Path to unmodded IWD:EE folder")
    args = ap.parse_args()

    bg2ee_dir = resolve_game_dir(args.bg2ee_dir, "BG2EE_DIR", "bg2ee")
    iwdee_dir = resolve_game_dir(args.iwdee_dir, "IWDEE_DIR", "iwdee")

    catalog = export_catalog(args.source, args.out_json, args.out_icons_dir, bg2ee_dir, iwdee_dir)
    print(
        f"Exported {catalog['stats']['totalSpells']} spells "
        f"({catalog['stats']['wizardSpells']} wizard, {catalog['stats']['divineSpells']} divine, "
        f"{catalog['stats']['newSpells']} new, {catalog['stats']['iwdOptionalSpells']} IWD optional) "
        f"-> {args.out_json}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
