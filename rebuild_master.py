# -*- coding: utf-8 -*-
"""Atjauno `output/master/*_MASTER_1to1.png` BEZ AI modeļa.

KĀPĒC ŠIS SKRIPTS EKSISTĒ
------------------------
Masteri ir lieli un ir starpprodukts starp avotu un gala 2000x2500 kadru.
To atjaunošanai bez šī skripta vajadzētu pilnu `setup_v2.py` + `workflow_v2.py`
palaišanu ar rembg/onnxruntime un 178 MB ISNet modeli.

Masteris ir pilnībā deterministiski atvasināms no failiem, kas jau ir krātuvē:
  1. oriģināls  `uploads/<stem>.<ext>` (vai ceļš no `report_v2_maker.json`)
  2. LUT        `output/profiles/<stem>_PROFILE.json` (vai `grade_profile_v2.json`)
  3. maska      `output/masks/<stem>_MASK.png` (izņemot `lut_only` pilnkadru)

Lietošana:
    python3 rebuild_master.py                 # atjauno visus trūkstošos
    python3 rebuild_master.py --verify <stem> # salīdzina ar esošo failu
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import loop
from engine.infra import open_rgb_recorded
from engine.render import lut_only_crops
from workflow_v2 import apply_lut, rotation_for

OUT = Path(__file__).resolve().parent / "output"
UP = Path(__file__).resolve().parent.parent / "uploads"
_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff",
         ".JPG", ".JPEG", ".PNG", ".WEBP", ".TIF", ".TIFF")


def _maker_rec(stem: str) -> dict:
    try:
        data = json.loads((OUT / "report_v2_maker.json").read_text(encoding="utf-8"))
        return dict((data.get("images") or {}).get(stem) or {})
    except (OSError, ValueError):
        return {}


def rotation_for_stem(stem: str, src: Path) -> int:
    rec = _maker_rec(stem)
    if rec.get("rotation_cw") is not None:
        return int(rec["rotation_cw"]) % 360
    return rotation_for(src)


def _resolve_source(stem: str, rec: dict) -> Path:
    rec_src = rec.get("source")
    if rec_src and Path(rec_src).is_file():
        return Path(rec_src)
    if rec.get("source_name"):
        cand = UP / str(rec["source_name"])
        if cand.is_file():
            return cand
    for ext in _EXTS:
        cand = UP / f"{stem}{ext}"
        if cand.is_file():
            return cand
    raise FileNotFoundError(UP / f"{stem}.jpg")


def _load_profile(stem: str, rec: dict) -> dict:
    for cand in (
        Path(rec["profile_path"]) if rec.get("profile_path") else None,
        OUT / "profiles" / f"{stem}_PROFILE.json",
        OUT / "grade_profile_v2.json",
    ):
        if cand is not None and cand.is_file():
            return json.loads(cand.read_text(encoding="utf-8"))
    raise FileNotFoundError(OUT / "profiles" / f"{stem}_PROFILE.json")


def stem_exists(stem: str) -> bool:
    rec = _maker_rec(stem)
    has_prof = ((OUT / "profiles" / f"{stem}_PROFILE.json").is_file()
                or (OUT / "grade_profile_v2.json").is_file())
    if not has_prof:
        return False
    if rec.get("lut_only"):
        try:
            _resolve_source(stem, rec)
            return True
        except FileNotFoundError:
            return False
    return (OUT / "masks" / f"{stem}_MASK.png").is_file()


def all_stems() -> list[str]:
    found = {p.name.replace("_PROFILE.json", "")
             for p in (OUT / "profiles").glob("*_PROFILE.json")}
    try:
        data = json.loads((OUT / "report_v2_maker.json").read_text(encoding="utf-8"))
        for stem, rec in (data.get("images") or {}).items():
            if rec.get("status") == "completed":
                found.add(stem)
    except (OSError, ValueError):
        pass
    return sorted(found)


def build(stem: str) -> np.ndarray:
    """Reproducē `engine.render.render_one` vai `render_lut_only` mastera daļu."""
    rec = _maker_rec(stem)
    src = _resolve_source(stem, rec)
    rot = rotation_for_stem(stem, src)
    orig = np.asarray(open_rgb_recorded(src, rot))
    profile = _load_profile(stem, rec)
    graded = apply_lut(orig, profile["lut_rgb"])

    if rec.get("lut_only"):
        h, w = graded.shape[:2]
        m = lut_only_crops(h, w)["master"]
        return graded[m["y0"]:m["y0"] + m["size"], m["x0"]:m["x0"] + m["size"]].copy()

    binary = (np.asarray(Image.open(OUT / "masks" / f"{stem}_MASK.png")
                         .convert("L")) > 128).astype(np.uint8)
    if binary.shape != orig.shape[:2]:
        raise ValueError(
            f"{stem}: maskas izmērs {binary.shape} != attēla {orig.shape[:2]} "
            f"(rot={rot}; pārbaudi report_v2_maker.json)")

    # MASK.png krātuvē jau ir PĒC decontaminate_rim, tāpēc to atkārtoti
    # nepiemērojam — funkcija nav idempotenta.
    alpha = loop.refine_alpha(binary)
    graded = loop.extend_foreground_colors(graded, binary, alpha, max_dist=8)

    full_shot = rec.get("full_shot")
    crop_box = (rec.get("closeup_crop")
                or (rec.get("timing") or {}).get("closeup_crop"))
    ps = max(loop.para_scale(binary, full_shot_override=full_shot, crop_box=crop_box), 1e-6)
    bg = loop.studio_shadow_bg(binary.shape, binary, canvas_scale=ps)

    h, w = binary.shape
    master = np.empty((h, w, 3), np.uint8)
    for y in range(0, h, 256):
        y2 = min(h, y + 256)
        a = (alpha[y:y2].astype(np.float32) / 255.0)[..., None]
        blended = (graded[y:y2].astype(np.float32) * a
                   + bg[y:y2, :, None].astype(np.float32) * (1.0 - a))
        master[y:y2] = np.clip(blended + 0.5, 0, 255).astype(np.uint8)
    return master


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", metavar="STEM", default=None,
                    help="salīdzina atjaunoto ar esošo masteri")
    args = ap.parse_args()

    if args.verify:
        ref_p = OUT / "master" / f"{args.verify}_MASTER_1to1.png"
        if not ref_p.is_file():
            print(f"nav ar ko salīdzināt: {ref_p}")
            return 2
        new = build(args.verify)
        ref = np.asarray(Image.open(ref_p).convert("RGB"))
        d = np.abs(new.astype(np.int16) - ref.astype(np.int16))
        print(f"max diff {d.max()}  vid {d.mean():.4f}  px>2 {(d > 2).sum()}")
        return 0

    (OUT / "master").mkdir(parents=True, exist_ok=True)
    n = 0
    for stem in all_stems():
        if not stem_exists(stem):
            continue
        dst = OUT / "master" / f"{stem}_MASTER_1to1.png"
        if dst.is_file():
            print(f"  {stem}: jau ir, izlaižu")
            continue
        Image.fromarray(build(stem)).save(dst, optimize=False, compress_level=6)
        print(f"  {stem}: atjaunots ({dst.stat().st_size / 1e6:.1f} MB)")
        n += 1
    print(f"gatavs, atjaunoti {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
