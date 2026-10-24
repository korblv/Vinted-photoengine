#!/usr/bin/env python3
"""Oriģinālās ēnas pārnešana no telefona foto uz gatavo kadru (2026-10-24).

ATBILDE UZ JAUTĀJUMU "vai var iebāzt oriģinālo ēnu no oriģinālā foto":
tehniski **jā**, un tas dod to, ko sintētika nevar — īstu gaismas avotu, īstu
astīti un īstu mīkstuma pieaugumu ar attālumu. Pārbaudīts uz `MVIMG_20261020_161031`
(džinsi), kuram vienīgajam vēl ir saglabājies oriģināls.

Mērījums oriģinālā (papīrs, Δ pret lokālo bāzi, 4096×3072):
    attālums no apģērba   8     15     30     60    120 px
    kreisā puse          26.8  23.2   15.0   11.6   11.9
    (labā/augšējā ~0 — gaisma no augšas-labās)
T.i. ēna ir īsta, virzīta, ar garu asti (>120 px). Salīdzinājumam sintētiskā
attiecīgi 30/15/5 — tā nomirst daudz ātrāk.

KĀ IEGŪST TĪRU ĒNU (trīs mēģinājumi, pirmie divi nederēja):
  * 2. kārtas virsmas fits — papīra krokas to izgāž;
  * liela rādiusa izlīdzinājums — "apēd" gan gradientu, gan ēnu;
  * **rolling ball** (lokālais gaišākais papīrs logā, normalizēts) — strādā:
    bāze seko apgaismojumam un krokām, bet ne ēnai, jo ēna nekad nav gaišākā.

PĀRNESE: ēna ir piesaistīta siluetei, tāpēc to nedrīkst pārnest kā attēlu —
jātransformē kopā ar apģērbu. Transformāciju nosaka pēc siluetes bbox
(avots → gals); tā kā pipeline novieto proporcionāli bez deformācijas, šī ir
tieši tā pati transformācija.

Lietošana:
  python3 real_shadow.py AVOTS.jpg GALA.jpg IZVADE.jpg [--gain 1.0]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

BG = 243.0


def garment_mask(rgb: np.ndarray, paper_mode: bool = False) -> np.ndarray:
    """Apģērba maska.

    `paper_mode=True` — telefona oriģināls (fons ir papīrs uz galda). Tur
    tekstūras kritērijs vien neietilpst, jo koka grīda arī ir teksturēta un
    saliptu ar apģērbu; tāpēc tur apģērbs = tumšs objekts uz gaišā papīra.
    """
    g = rgb.mean(axis=2).astype(np.float32)
    E = np.sqrt(np.maximum(cv2.blur((g - cv2.blur(g, (9, 9))) ** 2, (15, 15)), 0))
    if paper_mode:
        m = ((g < 35) | ((E > 6) & (g < 150))).astype(np.uint8)
    else:
        m = ((E > 7) | (g < 195)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((13, 13), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return np.zeros(g.shape, np.uint8)
    idx = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = (lab == idx).astype(np.uint8)
    ff = m.copy()
    mm = np.zeros((m.shape[0] + 2, m.shape[1] + 2), np.uint8)
    cv2.floodFill(ff, mm, (0, 0), 1)
    return (m | (1 - ff)).astype(np.uint8)


def extract_shadow(rgb: np.ndarray, scale: int = 4, win: int = 60) -> np.ndarray:
    """Ēnas karte: rolling ball bāze uz papīra, atņemta no gaišuma."""
    g = rgb.mean(axis=2).astype(np.float32)
    garment = garment_mask(rgb, paper_mode=True)
    sat = (rgb.max(axis=2) - rgb.min(axis=2)).astype(np.float32)
    paper = ((garment == 0) & (sat < 16) & (g > 90)).astype(np.float32)

    h, w = g.shape
    gs = cv2.resize(g, (w // scale, h // scale), interpolation=cv2.INTER_AREA)
    ps = cv2.resize(paper, (gs.shape[1], gs.shape[0]), interpolation=cv2.INTER_AREA)

    ker = np.ones((win, win), np.uint8)
    base = cv2.dilate(gs * ps, ker) / np.maximum(cv2.dilate(ps, ker), 1e-6)
    bad = cv2.dilate(ps, ker) < 0.05
    base[bad] = gs[bad]
    base = cv2.GaussianBlur(base, (0, 0), win / 4.0)
    base = cv2.resize(base, (w, h), interpolation=cv2.INTER_LINEAR)

    delta = np.clip(base - g, 0, 255)
    delta[garment > 0] = 0.0
    delta = cv2.GaussianBlur(delta, (0, 0), 2.0)
    # nogriež astes izlecējus (papīra kroku malas), nevis īsto ēnu
    lim = float(np.percentile(delta[paper > 0], 99.5)) if (paper > 0).sum() > 1000 else 60.0
    return np.clip(delta, 0, lim).astype(np.float32)


def bbox_of(mask: np.ndarray):
    ys, xs = np.where(mask > 0)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def main(src: Path, fin: Path, dst: Path, gain: float = 1.0) -> dict:
    a_src = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    a_fin = np.asarray(Image.open(fin).convert("RGB")).astype(np.float32)

    delta = extract_shadow(a_src)
    g_src = garment_mask(a_src, paper_mode=True)
    g_fin = garment_mask(a_fin)

    x0, y0, x1, y1 = bbox_of(g_src)
    X0, Y0, X1, Y1 = bbox_of(g_fin)
    sc = ((X1 - X0 + 1) / (x1 - x0 + 1) + (Y1 - Y0 + 1) / (y1 - y0 + 1)) / 2.0

    hh, ww = a_fin.shape[:2]
    M = np.float32([[sc, 0, X0 - x0 * sc], [0, sc, Y0 - y0 * sc]])
    d_t = cv2.warpAffine(delta, M, (ww, hh), flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0) * gain

    keep = cv2.dilate(g_fin.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    out = np.where(keep[..., None], a_fin, BG - d_t[..., None])
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out).save(dst, quality=95, subsampling=0)
    return {"skala": round(float(sc), 4),
            "ēna_avotā_maks": round(float(delta.max()), 1),
            "ēna_gala_maks": round(float(d_t.max()), 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("fin")
    ap.add_argument("dst")
    ap.add_argument("--gain", type=float, default=1.0)
    a = ap.parse_args()
    print(main(Path(a.src), Path(a.fin), Path(a.dst), a.gain))
