#!/usr/bin/env python3
"""Ēnas profila mērījums produktu kadriem (2026-10-24).

Mēra to, kas acīm redzams kā "ēna", skaitļos — lai salīdzinājums ar paraugu
nav gaumes jautājums:
  * fona līmenis (L* un 0-255),
  * ēnas maksimālais tumšums pret fonu (Δ),
  * cik tālu ēna stiepjas no siluetes (px un % no kadra),
  * cik vienmērīgi ēna apņem objektu (halo) pret vienpusēju metēno ēnu.

Lietošana: python3 measure_shadow.py BILDE [BILDE ...]
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

BAND = 90  # px josla ārpus siluetes, kurā meklējam ēnu


def measure(path: Path) -> dict:
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    gray = rgb.mean(axis=2)
    H, W = gray.shape
    bg = float(np.median(gray[:100, :100]))

    # siluete: audums ir krietni tumšāks par papīru
    solid = (gray < bg - 12).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(solid, 8)
    idx = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    garment = (lab == idx).astype(np.uint8)
    garment = cv2.morphologyEx(garment, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    garment = cv2.dilate(garment, np.ones((5, 5), np.uint8))

    ring = (cv2.dilate(garment, np.ones((BAND, BAND), np.uint8)) > 0) & (garment == 0)
    if not ring.any():
        return {"path": str(path), "kļūda": "nav ēnas joslas"}

    darkening = bg - gray.astype(np.float32)
    vals = darkening[ring]
    # ēnas kodols = tumšākie 2 % joslā
    core = float(np.percentile(vals, 98))
    mean_ring = float(vals.mean())

    # virziens: cik liela daļa ēnas ir zem objekta pret sāniem/augšu
    ys, xs = np.where(garment > 0)
    y1 = int(ys.max())
    x_mid = int((xs.min() + xs.max()) / 2)
    ry, rx = np.where(ring)
    below = ry > y1
    above = ry < int(ys.min())
    left = (rx < int(xs.min())) & ~below & ~above
    right = (rx > int(xs.max())) & ~below & ~above

    def core_of(sel):
        return float(np.percentile(darkening[ry[sel], rx[sel]], 98)) if sel.sum() > 50 else float("nan")

    # cik tālu ēna sniedzas (Δ >= 2) no siluetes malas uz leju
    ext = 0
    colx = slice(max(0, x_mid - 30), min(W, x_mid + 30))
    prof = darkening[:, colx].mean(axis=1)
    for dy in range(1, 400):
        if y1 + dy < H and prof[y1 + dy] >= 2.0:
            ext = dy
    softness = 0.0
    if ext:
        seg = prof[y1:y1 + ext]
        softness = float(seg.max() / max(1e-6, np.gradient(seg).max()))

    return {
        "path": path.name,
        "fons": round(bg, 1),
        "ēna_kodols_Δ": round(core, 1),
        "ēna_vidēji_Δ": round(mean_ring, 1),
        "zem_Δ": round(core_of(below), 1),
        "virs_Δ": round(core_of(above), 1),
        "pa_kreisi_Δ": round(core_of(left), 1),
        "pa_labi_Δ": round(core_of(right), 1),
        "izpletums_px": ext,
        "izpletums_%": round(100 * ext / H, 1),
        "objekta_platums_%": round(100 * (xs.max() - xs.min()) / W, 1),
    }


if __name__ == "__main__":
    rows = [measure(Path(p)) for p in sys.argv[1:]]
    keys = [k for k in rows[0] if k != "path"]
    w = max(len(k) for k in keys) + 2
    print(f"{'':{w}}" + "".join(f"{r['path'][:22]:>24s}" for r in rows))
    for k in keys:
        print(f"{k:{w}}" + "".join(f"{str(r[k]):>24s}" for r in rows))
