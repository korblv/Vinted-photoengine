#!/usr/bin/env python3
"""Metēnā ēna uz fona — fizikāls modelis ar mīksto malu (2026-10-24).

PROBLĒMA (lietotāja piezīme): "ēna kas krīt no apģērba uz fonu... šobrīd tā nav
dabiska, pārāk pelēka, šaura, kaut kas nav kā reālajā dzīvē".

MĒRĪJUMS apstiprināja: esošā ēna nomirst 20-30 px attālumā, tālāk fons ir
pilnīgi tukšs (Δ = 0.0 jau pie 30-40 px). Tāpēc tā izskatās kā šaura pelēka
josla, kas pieguļ siluetam, nevis kā ēna telpā.

KĀPĒC TĀ: iepriekšējais modelis ņēma **esošo** ēnu un tikai mērogoja to. Esošā
ēna pati ir šaura, tāpēc arī pēc mērogošanas tā palika šaura — nomirstot turpat
pie malas.

MODELIS (PCSS — percentage-closer soft shadows, kā 3D renderētājos):
  Gaisma ir **laukums**, nevis punkts. Tāpēc katrs fona punkts redz daļu no
  avota: jo tālāk punkts no apģērba, jo lielāku daļu avota tas redz. To iegūst,
  vidējojot siluetu pa daudziem gaismas avota punktiem:

      ēna(p) = (1/N) · Σ_k  M(p + d + r_k)

  kur d ir ēnas nobīde (gaisma no augšas-kreisi) un r_k ir punkti uz gaismas
  avota diska. Rezultāts dabiski dod to, ko prasa realitāte:
    * blīva, tumša ēna pie kontakta (punktu klāj gandrīz visi paraugi);
    * **pakāpeniska, mīksta mala** — mala kļūst mīkstāka, jo tālāk no apģērba;
    * **plašs izpletums** (offset + avota rādiuss), nevis 20 px josla;
    * gradients, nevis vienmērīgs pelēks lauks.

  Vecā ēna netiek noņemta: abas tiek apvienotas ar **gludo maksimumu**
  (p-norma), tāpēc pāreja ir nepārtraukta un nevar rasties ne šuve, ne rimbulis.

Lietošana: python3 cast_shadow.py IEVA IZVADE [--spread 26 --offset 13 --peak 46]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

BG = 243.0


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


def light_disc(n: int, radius: float) -> np.ndarray:
    """Vienmērīgi izvietoti punkti uz diska (spirāle, bez tukšumiem centrā)."""
    out = []
    golden = np.pi * (3.0 - np.sqrt(5.0))
    for i in range(n):
        rr = radius * np.sqrt((i + 0.5) / n)
        th = golden * i
        out.append((rr * np.cos(th), rr * np.sin(th)))
    return np.array(out, np.float32)


def pcss_shadow(hard: np.ndarray, spread: float, offset: tuple[float, float],
                samples: int, peak: float) -> np.ndarray:
    """Vidējais siluets pa gaismas avota punktiem (sk. moduļa docstring)."""
    H, W = hard.shape
    acc = np.zeros((H, W), np.float32)
    for dx, dy in light_disc(samples, spread):
        M = np.float32([[1, 0, offset[0] + dx], [0, 1, offset[1] + dy]])
        acc += cv2.warpAffine(hard, M, (W, H), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    acc /= float(samples)
    return np.clip(acc * peak, 0, 255)


def main(src: Path, dst: Path, spread: float = 14.0, ox: float = 22.0,
         oy: float = 26.0, samples: int = 28, peak: float = 52.0,
         soft: float = 1.4, tail: float = 0.22) -> dict:
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
    gray = rgb.mean(axis=2)
    hard = garment_hard(gray)
    alpha = np.clip((cv2.GaussianBlur(hard, (0, 0), 0.75) - 0.5) * 3.0 + 0.5, 0, 1)
    dist = cv2.distanceTransform((1 - hard).astype(np.uint8), cv2.DIST_L2, 5)

    delta_old = np.clip(BG - gray, 0, 255)
    # Divi slāņi: blīvais kodols (mazāks avots, mazāka nobīde) + plata, vāja aste.
    # Viena slāņa ēna nomirst 40 px attālumā un izskatās kā uzzīmēta josla;
    # reālai ēnai ir gara, pakāpeniska aste (sk. §44).
    core_s = pcss_shadow(hard, spread, (ox, oy), samples, peak)
    tail_s = pcss_shadow(hard, spread * 2.4, (ox * 1.45, oy * 1.45),
                         samples, peak)
    delta_new = core_s * (1.0 - tail) + tail_s * tail
    # ēna nedrīkst būt gaišāka par esošo tieši pie kontakta
    if soft > 0:
        delta_new = cv2.GaussianBlur(delta_new, (0, 0), soft)

    # gludais maksimums: p-norma, nevis max() — max() radītu redzamu šuvi
    p = 2.0
    delta = (delta_old ** p + delta_new ** p) ** (1.0 / p)

    # Ēnas maska tiek būvēta no **2 px sašaurinātas** siluetes.
    #
    # Kāpēc: auduma mala kadrā ir mīksta — vizuālā mala (kur tumšais adījums
    # beidzas) ir ~3 px pirms maskas robežas, un starp tām ir gaišs apmales rims.
    # Ja ēnu sāk no maskas robežas, šis rims paliek daļēji noēnots un izskatās
    # kā "neēnota līnija pirms ēnas" (lietotāja piezīme 2026-10-24). Fizikāli
    # tas arī nav pareizi: apģērba apakšējā mala ir kontaktā ar papīru, tāpēc
    # pēdējie 1-2 px ir ēnā, nevis gaiši.
    er = cv2.erode(hard.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
    dist_e = cv2.distanceTransform((1 - er).astype(np.uint8), cv2.DIST_L2, 5)
    w = np.clip(dist_e / 0.8, 0.0, 1.0).astype(np.float32)
    # Ēnu maskē tikai `w` (attālums no sašaurinātās siluetes), NEVIS (1−alpha):
    # (1−alpha) malā ir ~0.5, tāpēc pēdējie 1-2 px palika tikai pa pusei noēnoti
    # un izskatījās kā gaiša līnija. `w` pats ir 0 auduma iekšpusē (aiz 2 px
    # erozijas), tāpēc apģērbs paliek pasargāts.
    out = rgb - (delta - delta_old)[..., None] * w[..., None]
    out = np.where((alpha < 0.5)[..., None], np.minimum(out, BG), out)
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out).save(dst, quality=95, subsampling=0)
    return {"fons": round(float(np.percentile(out[:60, :60].mean(axis=2), 98)), 1),
            "ēna_izpletums_px": round(float(spread + max(abs(ox), abs(oy))), 1),
            "auduma_izmaiņa": int(np.abs(out.astype(int) - rgb.astype(int))[hard > 0.5].max())}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--spread", type=float, default=26.0)
    ap.add_argument("--ox", type=float, default=10.0)
    ap.add_argument("--oy", type=float, default=13.0)
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--peak", type=float, default=46.0)
    ap.add_argument("--soft", type=float, default=1.4)
    ap.add_argument("--tail", type=float, default=0.22)
    a = ap.parse_args()
    print(main(Path(a.src), Path(a.dst), a.spread, a.ox, a.oy, a.samples,
               a.peak, a.soft, a.tail))
