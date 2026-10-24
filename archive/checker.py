#!/usr/bin/env python3
"""CHECKER — neatkarīga pārbaude pēc LOOP.md 5. sadaļas (vārti A–D; E = vizuāli).
Nelabo neko — tikai mēra un ziņo PASS/FAIL. Maker un checker ir atdalīti apzināti."""
import json, os
import cv2
import numpy as np
from PIL import Image

SRC = "/home/user/uploads"
OUT = "/home/user/loop_bildes/output"

import sys
sys.path.insert(0, "/home/user/loop_bildes")
from loop import BG_GRAY as BG  # noqa: E402,F401 — vienīgais avots, sk. loop.py

def check_one(stem):
    g = {}
    # uint8 (nevis int64!) + rindkopas — sandboxam tikai ~2GB RAM
    orig = np.asarray(Image.open(f"{SRC}/{stem}.jpg").convert("RGB"))
    master = np.asarray(Image.open(f"{OUT}/master/{stem}_MASTER_1to1.png").convert("RGB"))
    mask = (np.asarray(Image.open(f"{OUT}/masks/{stem}_MASK.png").convert("L")) > 128)

    # A) Pikseļi: maskas kodols (erodēts 5px) — MASTER jābūt identiskam oriģinālam
    core = cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8), iterations=5) > 0
    max_diff, equal, total = 0, 0, int(core.sum())
    for y in range(0, orig.shape[0], 256):
        y2 = min(orig.shape[0], y + 256)
        c = core[y:y2]
        if c.any():
            d = np.abs(master[y:y2].astype(np.int16) - orig[y:y2].astype(np.int16))[c]
            max_diff = max(max_diff, int(d.max()))
            equal += int((d.max(axis=1) == 0).sum())
    g["A_pixels"] = {"max_diff": max_diff, "pct_equal": float(equal / max(total, 1) * 100),
                     "core_pixels": total, "PASS": bool(max_diff == 0)}

    # B) Fons: >120px no apģērba (ārpus ēnas) jābūt tieši (243,243,243).
    # Attāluma transformācija 120 dilate iterāciju vietā (ātrāk, mazāk RAM).
    dist = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
    far_bg = dist > 120
    del dist
    if far_bg.sum() > 1000:
        vals = master[far_bg]
        ok = bool(((vals == BG).all(axis=1).mean()) > 0.999)
        g["B_background"] = {"far_bg_pixels": int(far_bg.sum()), "pct_exact_F3": float((vals == BG).all(axis=1).mean() * 100), "PASS": ok}
        del vals
    else:
        g["B_background"] = {"far_bg_pixels": int(far_bg.sum()), "PASS": True,
                             "note": "fons gandrīz nav kadrā (tuvplāns) — pārbauda vizuāli (E)"}

    # C) Maskas veselums
    cov = float(mask.mean())
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    largest_ratio = float(stats[1:, cv2.CC_STAT_AREA].max() / mask.sum()) if n > 1 else 1.0
    g["C_mask"] = {"coverage": round(cov, 4), "largest_component_ratio": round(largest_ratio, 4),
                   "PASS": bool(0.15 <= cov <= 0.98 and largest_ratio >= 0.95)}

    # D) Parauga formāts: 2000x2500; stūri, kur maska=0, ir 243±3
    par = Image.open(f"{OUT}/paraugs/{stem}_PARAUGS_2000x2500.jpg").convert("RGB")
    pmask = np.asarray(Image.open(f"{OUT}/masks/{stem}_PARAUGS_MASK.png").convert("L")) > 128
    pa = np.asarray(par).astype(np.int16)
    corners, corner_ok = [], True
    for (y, x) in [(8, 8), (8, -9), (-9, 8), (-9, -9)]:
        if not pmask[y, x]:
            corners.append([int(v) for v in pa[y, x]])
            if np.abs(pa[y, x] - BG).max() > 3:
                corner_ok = False
    g["D_format"] = {"size": list(par.size), "bg_corners": corners,
                     "PASS": bool(par.size == (2000, 2500) and corner_ok)}

    # F) Pilns kadrs tuvplāniem (pievienots pēc lietotāja korekcijas, iter.4):
    # apģērbam jāsasniedz kadra malas tur, kur tas oriģinālā iziet no kadra —
    # vismaz 3 no 4 malām maska aizņem >=50% tieši pie ārējās rindas/kolonnas
    # (t.i., nav "ierāmētas" sānu joslas kā contain variantā).
    try:
        from loop import CLOSEUP_SEEDS
        is_closeup = stem[-6:] in CLOSEUP_SEEDS
    except Exception:
        is_closeup = False
    if is_closeup:
        edges = {"augša": float(pmask[0].mean()), "apakša": float(pmask[-1].mean()),
                 "kreisi": float(pmask[:, 0].mean()), "labi": float(pmask[:, -1].mean())}
        n_full = sum(1 for v in edges.values() if v >= 0.50)
        g["F_full_frame"] = {"edges": {k: round(v, 3) for k, v in edges.items()},
                             "edges_ge_50pct": n_full, "PASS": bool(n_full >= 3)}

    # H) Malas alfa kvalitāte (iterācija 7): mīkstināšana drīkst skart tikai
    # šauru joslu ap bināro masku. Kodolā alfa=255, tālu ārpusē alfa=0, un
    # kopējais alfa laukums nedrīkst būt būtiski nobīdījies no audita maskas.
    alpha_path = f"{OUT}/masks/{stem}_ALPHA.png"
    if os.path.exists(alpha_path):
        alpha = np.asarray(Image.open(alpha_path).convert("L"))
        dist_out = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
        far_out = dist_out > 5
        far_max = int(alpha[far_out].max()) if np.any(far_out) else 0
        dist_in = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
        signed = dist_in - dist_out
        del dist_in, dist_out, far_out
        partial = (alpha > 0) & (alpha < 255)
        partial_max = float(np.max(np.abs(signed[partial]))) if np.any(partial) else 0.0
        del signed, partial
        core_min = int(alpha[core].min()) if total else 255
        alpha_cov = float(alpha.mean() / 255.0)
        cov_delta = abs(alpha_cov - cov)
        g["H_edge_alpha"] = {
            "core_min_alpha": core_min,
            "far_outside_max_alpha": far_max,
            "partial_max_abs_distance_px": round(partial_max, 3),
            "alpha_coverage": round(alpha_cov, 4),
            "coverage_delta_vs_binary": round(cov_delta, 5),
            "PASS": bool(core_min == 255 and far_max == 0 and partial_max <= 5.1 and cov_delta <= 0.0025),
        }
        del alpha
    g["ALL_ABCD_PASS"] = all(g[k]["PASS"] for k in g)
    return g

def main():
    stems = sorted(f.replace("_MASTER_1to1.png", "") for f in os.listdir(f"{OUT}/master")
                   if f.endswith("_MASTER_1to1.png"))
    report = {}
    for stem in stems:
        report[stem] = check_one(stem)
        r = report[stem]
        print(f"{stem}: A(pikseļi maxdiff={r['A_pixels']['max_diff']}) "
              f"B(fons)={r['B_background']['PASS']} C(maska seg={r['C_mask']['coverage']}) "
              f"D(2000x2500)={r['D_format']['PASS']} -> {'PASS' if r['ALL_ABCD_PASS'] else 'FAIL'}")
    with open(f"{OUT}/report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("CHECKER DONE -> output/report.json")

if __name__ == "__main__":
    main()
