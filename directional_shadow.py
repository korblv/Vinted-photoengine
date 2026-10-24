#!/usr/bin/env python3
"""Virzīta studijas ēna kā SLAMJAM paraugā (2026-10-24).

MĒRĶIS (Δ = 243 − L, vidēji pa perimetru, 2000×2500):

    d px     2     3     4     6     8    10    14
    left   0.8   0.8   0.8   0.7   0.7   0.6   0.6      <- ēnas NAV
    right 36.7  31.1  25.5  17.3   9.7   6.0   0.5      <- spēcīga
    top    8.6   8.4   8.3   8.1   8.0   7.7   6.6      <- vāja, plata
    bottom 32.4 27.9  23.8  18.1  12.6   9.0   4.9      <- spēcīga

MODELIS — virzienā izsmērēta siluete (gaisma no augšas-kreisi, ēna uz
apakšu-labo). Punktu d px pa labi no malas klāj tās siluetes kopijas, kas
nobīdītas par ≥ d, tāpēc ēna **sākas ar maksimumu tieši kontaktā** un krīt
kā exp(−d/λ). Papildus neliels ambient slānis ar garu kritumu (top 8.6).

KĀPĒC TĀ UN NE CITĀDI — trīs iepriekšējās pieejas nokrita (sk. QA §42.3):
  1. `blur(shift(alpha))` atstāj 7-9 px joslu bez ēnas zem apakšmalas;
  2. vienmērīgs "kontakta rims" visapkārt dod uzlīmes kontūru;
  3. vecās ēnas izgriešana ar neprecīzu b_old dod gaišu gredzenu, jo malas
     joslā `delta_old` satur sajauktu AUDUMU, nevis ēnu.
Punkts 3 šeit ir atrisināts: `delta_old` netiek ņemts pa pikseli, bet gan kā
**profils pēc attāluma** (mediāna pa 0.5 px joslām tikai fona pusē, ar
lineāru pagarinājumu līdz d=0). Tāpēc tas nesatur audumu un ir vienmērīgs.

Lietošana: python3 directional_shadow.py IEVA IZVADE
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

BG = 243.0
PEAK, LAM, AMB, AMB_LEN = 52.0, 4.8, 8.0, 55.0   # kalibrēts pret SLAMJAM
UX, UY, STEPS = 1.0, 1.0, 64                     # virziens (uz apakšu-labo)
SIG, K = 0.75, 3.0                               # malas asums


def garment_hard(gray: np.ndarray) -> np.ndarray:
    g = gray.astype(np.float32)
    E = np.sqrt(np.maximum(cv2.blur((g - cv2.blur(g, (9, 9))) ** 2, (15, 15)), 0))
    m = ((E > 7) | (g < 195)).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    idx = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    m = (lab == idx).astype(np.uint8)
    ff = m.copy()
    mm = np.zeros((m.shape[0] + 2, m.shape[1] + 2), np.uint8)
    cv2.floodFill(ff, mm, (0, 0), 1)
    return (m | (1 - ff)).astype(np.float32)


def directed_field(hard: np.ndarray, peak: float = PEAK, lam: float = LAM,
                   amb: float = AMB, amb_len: float = AMB_LEN) -> np.ndarray:
    H, W = hard.shape
    acc = np.zeros((H, W), np.float32)
    norm = 0.0
    for k in range(1, STEPS + 1):          # sākam no 1: ēna sākas kontaktā
        w = float(np.exp(-k / lam))
        M = np.float32([[1, 0, UX * k], [0, 1, UY * k]])
        acc += w * cv2.warpAffine(hard, M, (W, H), flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        norm += w
    field = peak * acc / norm

    dist_out = cv2.distanceTransform((1 - hard).astype(np.uint8), cv2.DIST_L2, 5)
    field += amb * np.exp(-dist_out / amb_len)
    return np.clip(field, 0, 255)


def old_shadow_field(gray: np.ndarray, alpha: np.ndarray, scale: int = 8) -> np.ndarray:
    """Vecā ēna kā GLUDS lauks (nevis pikselī).

    `delta_old` pikseļu līmenī malas joslā satur sajauktu audumu, tāpēc jebkurš
    pikseļu inpaint tur novērtē par 25-40 % par zemu — no tā nāca gaišie
    gredzeni un tumšās līnijas. Vecā ēna tomēr ir lēns, liela mēroga lauks
    (30-40 px), tāpēc to droši var novērtēt **8× samazinātā izšķirtspējā**:
    tur malas josla ir ~0.25 px un normalizētā konvolūcija dod precīzu vērtību.
    """
    d_old = np.clip(BG - gray, 0, 255).astype(np.float32)
    w = (alpha < 0.02).astype(np.float32)          # tikai tīrs fons
    h, wd = d_old.shape
    hh, ww = h // scale, wd // scale
    d_s = cv2.resize(d_old, (ww, hh), interpolation=cv2.INTER_AREA)
    w_s = cv2.resize(w, (ww, hh), interpolation=cv2.INTER_AREA)
    num = cv2.GaussianBlur(d_s * w_s, (0, 0), 1.2)
    den = cv2.GaussianBlur(w_s, (0, 0), 1.2)
    field = num / np.maximum(den, 1e-4)
    # kur nav neviena fona pikseļa tuvumā (auduma iekšpuse) — 0, tāpat reizina
    # ar (1−alpha) ≈ 0
    field[den < 1e-4] = 0.0
    return cv2.resize(field, (wd, h), interpolation=cv2.INTER_LINEAR)


def main(src: Path, dst: Path, **kw) -> dict:
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    gray = rgb.mean(axis=2)
    hard = garment_hard(gray)
    alpha = np.clip((cv2.GaussianBlur(hard, (0, 0), SIG) - 0.5) * K + 0.5, 0, 1)

    d_old = old_shadow_field(gray, alpha)
    d_new = directed_field(hard, **kw)

    out = rgb - (d_new - d_old)[..., None] * (1.0 - alpha)[..., None]
    # fons nekad nav gaišāks par papīru (vecās ēnas noņemšana = atpakaļ uz BG)
    out = np.where((alpha < 0.5)[..., None], np.minimum(out, BG), out)
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out).save(dst, quality=95, subsampling=0)
    return {"fons_p98": round(float(np.percentile(out[:80, :80].mean(axis=2), 98)), 1),
            "auduma_izmaiņa_maks": int(np.abs(out.astype(int) - rgb.astype(int))[hard > 0.5].max())}


if __name__ == "__main__":
    print(main(Path(sys.argv[1]), Path(sys.argv[2])))
