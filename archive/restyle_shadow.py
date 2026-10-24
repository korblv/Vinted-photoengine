#!/usr/bin/env python3
"""Ēnas saspiešana/ pastiprināšana pēc SLAMJAM parauga (2026-10-24).

LIETOTĀJA PIEZĪME: "ēna — ja salīdzina ar slamjam bildēm, tad ir liela
atšķirība... taisām tumšāku".

MĒRĪJUMS (Δ pret fonu 243, 2000×2500, vidēji pa visu siluetes perimetru):

    attālums no malas   1.5   2.5   4.0   6.0   8.0  10.0  14.0  18.0 px
    SLAMJAM (mērķis)   34.5  29.5  24.6  17.7  11.1   7.5   2.7   0.3
    MŪSU vecā          33.8  31.6  28.0  25.5  20.0  16.7   6.0   1.5
    pēc šī skripta     34.2  29.6  23.7  16.9  12.0   8.1   3.2   1.1

T.i. kontaktā mūsējā jau bija gandrīz tikpat tumša, bet tā **stiepās divreiz
tālāk** — tāpēc izskatījās kā liels, gaišs halo, nevis kompakta ēna. Risinājums
ir nevis "uzlikt tumšāku ēnu", bet **saspiest esošo tuvāk malai**.

KĀPĒC TIEŠI ŠĪ METODE (pārbaudīts 2026-10-24, sk. PAPIRA_NOPLUDES_QA.md §41.6):
  * esošā ēna tiek tikai **mērogota** ar attāluma koeficientu f(d); netiek
    nekas aizvietots un netiek izgudrots — tāpēc nevar rasties ne šuve, ne
    gaišs rimbulis (abas kļūdas tika iegūtas ar "izgriešanas" un
    "aizvietošanas" pieejām);
  * auduma pikseļi netiek aiztikti nemaz: reizinātājs (1−α) = 0 audumā;
  * f(d) = A·exp(−(d/L)^p) ar A=1.10, L=10, p=1.3 — piemeklēts pret paraugu.

Lietošana: python3 restyle_shadow.py IEVA IZVADE
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

BG = 243.0
A_MUL, L_LEN, P_POW = 1.10, 10.0, 1.3
SIG, K = 0.75, 3.0            # malas asums


def garment_hard(gray: np.ndarray) -> np.ndarray:
    """Cieta siluete 0/1: audums ir teksturēts un/vai tumšs, ēna ir gluda."""
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


def main(src: Path, dst: Path, a_mul: float = 1.10, l_len: float = 10.0,
         p_pow: float = 1.35, w_left: float = 0.05, w_right: float = 1.45,
         w_top: float = 0.09, w_bottom: float = 1.65, edge_bind: float = 1.5) -> dict:
    """Ēnas mērogošana arī VIRZIENĀ (2026-10-24, 2. iterācija).

    Pirmā versija mērogoja tikai pēc attāluma (`f(d)`), tāpēc ēna palika
    simetriska. Mēģinājums to aizstāt ar jaunu virzītu ēnu nokrita: noņemot
    veco ēnu, rodas pāreja, kas 1:1 izskatās kā uzlīmes mala (sk. §42.5).

    Šeit tiek mērogota **jau esošā** ēna divos faktoros, kas abi ir gludi:
      f(d)      = a_mul · exp(−(d/L)^p)          — saspiež tuvāk malai
      w(side)   = svars atkarībā no tā, kurā pusē pikselis atrodas
    Tā kā tiek tikai reizināts ar gludām funkcijām, **nevar rasties jauna
    mala, šuve vai rimbulis**, un audums paliek burtiski neskarts.

    Virziena svars: distance-transformas gradients norāda prom no apģērba, tāpēc
    tā zīme pasaka, kurā pusē pikselis ir. Gaisma no augšas-kreisi → ēna
    pastiprinās pa labi/uz leju un vājinās pa kreisi/augšu (kā SLAMJAM).
    """
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    gray = rgb.mean(axis=2)
    hard = garment_hard(gray)
    alpha = np.clip((cv2.GaussianBlur(hard, (0, 0), SIG) - 0.5) * K + 0.5, 0, 1)

    dist = cv2.distanceTransform((1 - hard).astype(np.uint8), cv2.DIST_L2, 5)
    # Virzienu ņem no IZPLUDINĀTAS maskas gradienta, nevis distance-transformas:
    # pie pašas malas distance-transformas gradients nav definēts (atteices
    # līnija), tāpēc svars tur kļuva trokšņains un ēna malā tika NOŅEMTA —
    # tā radās baltā līnija (redzēta 2026-10-24 1:1).
    smooth = cv2.GaussianBlur(hard, (0, 0), 22.0)
    gx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=9)
    gy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=9)
    n = np.sqrt(gx * gx + gy * gy)
    ok = n > 1e-6
    n = np.where(ok, n, 1.0)
    gx, gy = gx / n, gy / n
    # Maskas gradients rāda UZ IEKŠU (maskas vērtība aug pret apģērbu), tāpēc
    # ārējais virziens ir ar pretēju zīmi. Bez šī labojuma svars pastiprināja
    # tieši to pusi, kuru vajadzēja vājināt (pārbaudīts 2026-10-24).
    gx, gy = -gx, -gy

    rightness = np.clip(gx, 0, 1)
    leftness = np.clip(-gx, 0, 1)
    downness = np.clip(gy, 0, 1)
    upness = np.clip(-gy, 0, 1)
    wdir = (1.0 + rightness * (w_right - 1) + downness * (w_bottom - 1)
            - leftness * (1 - w_left) - upness * (1 - w_top))
    # tuvu malai svars tiek maigi piesaistīts pie 1.0 (kontakta josla paliek
    # dabiska), tālāk — pilns virziena efekts
    wdir = 1.0 + (wdir - 1.0) * np.clip((dist - 0.3) / edge_bind, 0, 1)
    wdir = cv2.GaussianBlur(np.clip(wdir, 0.12, 2.6), (0, 0), 3.0)

    delta_old = np.clip(BG - gray, 0, 255)
    factor = a_mul * np.exp(-np.power(dist / l_len, p_pow)) * wdir
    delta_new = np.clip(delta_old * factor, 0, 255)

    out = rgb - (delta_new - delta_old)[..., None] * (1.0 - alpha)[..., None]
    out = np.where((alpha < 0.5)[..., None], np.minimum(out, BG), out)
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out).save(dst, quality=95, subsampling=0)
    return {"auduma_izmaiņa_maks": int(np.abs(out.astype(int) - rgb.astype(int))[hard > 0.5].max()),
            "ēna_maks": round(float(delta_new.max()), 1)}


if __name__ == "__main__":
    print(main(Path(sys.argv[1]), Path(sys.argv[2])))
