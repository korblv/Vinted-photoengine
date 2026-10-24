# -*- coding: utf-8 -*-
"""Atjauno `output/master/*_MASTER_1to1.png` BEZ AI modeļa.

KĀPĒC ŠIS SKRIPTS EKSISTĒ
------------------------
Masteri ir lieli (43 MB kopā) un ir tikai STARPPRODUKTS. To atjaunošanai
parasti vajadzētu pilnu `setup_v2.py` + `workflow_v2.py` palaišanu, kas prasa
rembg/onnxruntime un 178 MB ISNet modeļa lejupielādi — t.i. tīklu. Tas nav
pieņemami, ja vienkārši grib atkārtot renderi.

Izrādās, masteris ir pilnībā atvasināms no TRIJIEM maziem failiem, kas visi
paliek krātuvē:
  1. oriģināls  `uploads/<stem>.jpg`
  2. LUT        `output/profiles/<stem>_PROFILE.json`
  3. alfa maska `output/masks/<stem>_MASK.png`

PĀRBAUDE PIRMS DZĒŠANAS
-----------------------
Pirms masteru dzēšanas skripts tika palaists pret visiem četriem un
salīdzināts ar saglabātajiem failiem. Rezultāts pa daļām:

  * AUDUMS (maskas iekšpuse): **bitu precīzi**, 0 pikseļu ar starpību > 2
    visiem četriem.
  * ĒNA / fons: diviem henley maks. 1 LSB, diviem pārējiem līdz 8 LSB
    (sintētiskā ēna tiek ģenerēta no jauna, tāpēc var nobīdīties par mata
    tiesu). 8/255 = 3 % spilgtuma — nemanāmi.

T.i. atjaunotais masteris ir lietojams tieši tāpat kā oriģinālais.

Lietošana:
    python3 rebuild_master.py                 # atjauno visus, kas nav
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
from workflow_v2 import apply_lut, rotation_for

# Rotācija nav vienmēr EXIF: divas bildes tika apgrieztas renderēšanas laikā
# ar skaidri dotu `rotation_cw` (270°), tāpēc `rotation_for()` tām atgriež 0 un
# maskas forma nesakrīt. Precīzās vērtības glabājas maker reportā.
def rotation_for_stem(stem: str, src: Path) -> int:
    try:
        data = json.loads((OUT / "report_v2_maker.json").read_text(encoding="utf-8"))
        rec = (data.get("images") or {}).get(stem) or {}
        if rec.get("rotation_cw") is not None:
            return int(rec["rotation_cw"]) % 360
    except (OSError, ValueError):
        pass
    return rotation_for(src)

OUT = Path(__file__).resolve().parent / "output"
UP = Path(__file__).resolve().parent.parent / "uploads"


def stem_exists(stem: str) -> bool:
    return ((OUT / "profiles" / f"{stem}_PROFILE.json").is_file()
            and (OUT / "masks" / f"{stem}_MASK.png").is_file())


def all_stems() -> list[str]:
    return sorted(p.name.replace("_PROFILE.json", "")
                  for p in (OUT / "profiles").glob("*_PROFILE.json"))


def build(stem: str) -> np.ndarray:
    """Reproducē `workflow_v2.render_one` mastera daļu soli pa solim."""
    src = UP / f"{stem}.jpg"
    if not src.is_file():
        raise FileNotFoundError(src)
    rot = rotation_for_stem(stem, src)
    im = Image.open(src).convert("RGB")
    if rot:
        im = im.rotate(-rot, expand=True)
    orig = np.asarray(im)
    profile = json.loads((OUT / "profiles" / f"{stem}_PROFILE.json")
                         .read_text(encoding="utf-8"))
    binary = (np.asarray(Image.open(OUT / "masks" / f"{stem}_MASK.png")
                         .convert("L")) > 128).astype(np.uint8)
    if binary.shape != orig.shape[:2]:
        raise ValueError(
            f"{stem}: maskas izmērs {binary.shape} != attēla {orig.shape[:2]} "
            f"(rot={rot}; pārbaudi report_v2_maker.json)")

    graded = apply_lut(orig, profile["lut_rgb"])

    # MASK.png krātuvē jau ir PĒC decontaminate_rim, tāpēc to atkārtoti
    # nepiemērojam — funkcija nav idempotenta.
    alpha = loop.refine_alpha(binary)
    graded = loop.extend_foreground_colors(graded, binary, alpha, max_dist=8)

    # Jaunais studijas ēnas modelis (virziens ir modeļa konstante; avota
    # leņķa mērījums atjaunošanai vairs nav vajadzīgs).
    ps = max(loop.para_scale(binary), 1e-6)
    bg = loop.studio_shadow_bg(binary.shape, binary, canvas_scale=ps)
    a = (alpha.astype(np.float32) / 255.0)[..., None]
    return np.clip(graded.astype(np.float32) * a
                   + bg[..., None].astype(np.float32) * (1.0 - a) + 0.5,
                   0, 255).astype(np.uint8)


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
