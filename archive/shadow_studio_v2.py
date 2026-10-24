#!/usr/bin/env python3
"""Studijas ēna pēc SLAMJAM parauga — virzīta, blīva, īsa (2026-10-24).

Kāpēc: lietotājs norādīja, ka mūsu ēna atšķiras no `slamjam_mfpen_trousers`
paraugiem. Mērījums apstiprināja — mūsu ēna bija **simetrisks halo**:

    Δ (243-L) attālumā no siluetes, MŪSU vecā versija
    d px   left  right  top  bottom
       1   44.9   28.0  34.7   29.5
      12   23.1   16.2  21.9   15.9
      30    2.5    3.0   5.2    2.4

    SLAMJAM_2 (paraģis)
    d px   left  right  top  bottom
       1    0.9   42.6   9.2   37.2
       6    0.7   17.3   8.1   18.1
      12    0.6    1.2   7.2    5.7
      30    0.4    0.4   4.5    2.8

T.i. paraugā ēna ir **vienpusēja**: gaisma no augšas-kreisi, ēna metama pa labi
un uz leju, blīva pie kontakta un izzūd ~12-20 px laikā. Pa kreisi ēnas nav.

Modelis (fizikāls, divi slāņi kā fotogrāfijā):
  * cast    = nobīdīts + izpludināts siluets (gaisma no augšas-kreisi)
  * contact = šaurs, tuvs kontakts VISAPKĀRT (0.10 — gandrīz nemanāms, bet
              neļauj izskatīties kā izgrieztam ar šķērēm)
  * fons    = 243 - Δ, tikai ārpus apģērba; apģērba pikseļi netiek aiztikti.

Lietošana:
  python3 shadow_studio_v2.py IEVA IZVADE [--cast 0.62 --blur 3.2 --dx 7 --dy 6]
"""
import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

BG = 243.0


def garment_alpha(gray: np.ndarray) -> np.ndarray:
    """Mīksta alfa 0..1. Audums ir teksturēts un/vai tumšs, ēna ir gluda."""
    g = gray.astype(np.float32)
    E = cv2.blur((g - cv2.blur(g, (9, 9))) ** 2, (15, 15)) ** 0.5
    m = ((E > 7) | (g < 195)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    idx = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = (lab == idx).astype(np.uint8)
    # aizpilda iekšējos caurumus (smooth cuff, bikses V-iecirtums paliek)
    ff = m.copy()
    mm = np.zeros((m.shape[0] + 2, m.shape[1] + 2), np.uint8)
    cv2.floodFill(ff, mm, (0, 0), 1)
    m = (m | (1 - ff)).astype(np.uint8)
    a = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.0)
    return np.clip(a, 0.0, 1.0)


def shadow_field(alpha: np.ndarray, cast: float, blur: float, dx: int, dy: int,
                 contact: float = 0.10) -> np.ndarray:
    """Δ lauks (0..255 vienībās)."""
    H, W = alpha.shape
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    shifted = cv2.warpAffine(alpha, M, (W, H), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    s_cast = cv2.GaussianBlur(shifted, (0, 0), blur)
    s_contact = cv2.GaussianBlur(alpha, (0, 0), 1.6)
    delta = (cast * s_cast + contact * s_contact) * (1.0 - alpha)
    return np.clip(delta * 100.0, 0.0, 255.0)   # 1.0 = 100 līmeņi tumšāks


def apply(src: Path, dst: Path, **kw) -> dict:
    im = Image.open(src).convert("RGB")
    rgb = np.asarray(im).astype(np.float32)
    gray = rgb.mean(axis=2)
    a = garment_alpha(gray)
    delta = shadow_field(a, **kw)
    out = rgb * a[..., None] + (BG - delta)[..., None] * (1.0 - a[..., None])
    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(dst, quality=95, subsampling=0)
    return {"alpha_cover": float(a.mean())}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--cast", type=float, default=0.62)
    ap.add_argument("--blur", type=float, default=3.2)
    ap.add_argument("--dx", type=int, default=7)
    ap.add_argument("--dy", type=int, default=6)
    ap.add_argument("--contact", type=float, default=0.10)
    a = ap.parse_args()
    r = apply(Path(a.src), Path(a.dst), cast=a.cast, blur=a.blur, dx=a.dx,
              dy=a.dy, contact=a.contact)
    print(r)
