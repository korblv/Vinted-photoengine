#!/usr/bin/env python3
"""Aizpilda maskas iekšējos caurumus, kas NAV īsts papīrs (2026-10-23).

Kāpēc: `clean_mask` jau aizpilda visus iekšējos caurumus, bet 2026-10-23
ad-hoc solis (tas, kas aizpildīja 38 813 px slitas) atstāja kā fona
komponentes ar `min(w,h) <= 0.012*W`. Rezultātā plakāta kreisajā malā
palika 418 px caurums (16x40 px) — izbalējis vafeļu adījuma izcēlums
(maks. 207), ko ISNet bija atzinis par papīru (papīrs = 243). Čekeris to
godīgi nosauca par `interior_holes`.

Noteikums (fizikāls, nevis gaumes): komponente, kas **nav** savienota ar
kadra malu, ir īsts fons tikai tad, ja tajā IR papīram raksturīgs pikselis
(vismaz viens kanālis >= paper_med - 12). Ja nav — tā ir auduma gaišā daļa
un tā jāaizpilda. Tas pats neskar īstas spraugas starp piedurkni un ķermeni:
tur redzams īsts papīrs.

Lietošana:  python3 fix_mask_holes.py STEM [STEM ...]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

OUT = Path(__file__).resolve().parent / "output"
PAPER_TOL = 12          # cik tuvu papīra līmenim jābūt, lai to atzītu par papīru
MIN_AREA = 50           # mazākus plankumus ignorē (troksnis, <0.002 % kadra)


def fix(stem: str) -> dict:
    mask_p = OUT / "masks" / f"{stem}_MASK.png"
    cands = [OUT / "master" / f"{stem}_MASTER_1to1.png"]
    cands += sorted((OUT / "master").glob("*MASTER_1to1*"))
    master_p = next((p for p in cands if p.is_file()), None)
    if not mask_p.is_file() or master_p is None:
        raise SystemExit(f"nav maskas/meistara: {mask_p} / {master_p}")

    m = (np.asarray(Image.open(mask_p).convert("L")) > 128)
    rgb = np.asarray(Image.open(master_p).convert("RGB"))
    if rgb.shape[:2] != m.shape:
        raise SystemExit(f"izmēri nesakrīt: maska {m.shape} != meistars {rgb.shape[:2]}")

    h, w = m.shape
    bg = (~m).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(bg, 8)
    # papīra līmenis: tie fona pikseļi, kas pieskaras kadra malai
    ring = np.zeros((h, w), bool)
    ring[0, :] = ring[-1, :] = True
    ring[:, 0] = ring[:, -1] = True
    ring_bg = ring & (m == 0)
    paper_med = float(np.median(rgb[ring_bg])) if ring_bg.sum() > 100 else 243.0
    thr = paper_med - PAPER_TOL

    border_ids = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    filled, kept = [], []
    out = m.copy()
    for i in range(1, n):
        a = int(st[i, cv2.CC_STAT_AREA])
        if a < MIN_AREA or i in border_ids:
            continue
        comp = lab == i
        has_paper = bool(rgb[comp].max(axis=1).max() >= thr)
        if has_paper:
            kept.append((i, a, float(rgb[comp].max(axis=1).max())))
        else:
            out |= comp
            filled.append((i, a, int(st[i, cv2.CC_STAT_LEFT]), int(st[i, cv2.CC_STAT_TOP]),
                           int(st[i, cv2.CC_STAT_WIDTH]), int(st[i, cv2.CC_STAT_HEIGHT])))

    if filled:
        tmp = mask_p.with_name(mask_p.name + ".tmp.png")
        Image.fromarray((out.astype(np.uint8) * 255)).save(tmp)
        tmp.replace(mask_p)
    return {"paper_med": round(paper_med, 1), "thr": round(thr, 1),
            "filled": filled, "kept_real_gaps": kept,
            "coverage_before": round(float(m.mean()), 5),
            "coverage_after": round(float(out.mean()), 5)}


if __name__ == "__main__":
    for s in sys.argv[1:]:
        r = fix(s)
        print(f"[{s}] papīrs={r['paper_med']} slieksnis={r['thr']}")
        for i, a, x, y, cw, ch in r["filled"]:
            print(f"   aizpildīts  #{i} {cw}x{ch} @({x},{y}) {a} px")
        for i, a, mx in r["kept_real_gaps"]:
            print(f"   paturēts    #{i} {a} px (maks. {mx:.0f} = papīrs)")
        print(f"   segums {r['coverage_before']} -> {r['coverage_after']}")
