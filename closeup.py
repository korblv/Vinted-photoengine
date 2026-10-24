"""Tuvplānu (detail crop) ģenerators — slamjam stila papildskati.

Kāpēc šī pieeja
---------------
Atsauces bildēs (slamjam_mfpen_trousers_3/_4) apģērbs aizpilda kadru un iet
pāri malām, tāpēc fonā gandrīz nav ko segmentēt. Tas nozīmē, ka tuvplānam
nepastāv arī malas defekti (fringe, robainība, pakāpieni) — tie visi nāk no
matēšanas. Tāpēc tuvplāns tiek griezts NO MASTERA, bez segmentācijas.

Izšķirtspēja
------------
Master ir avota izšķirtspējā (3072x4096). Cik lielu logs var atļauties, nosaka
tas, cik lielu daļu loga aizņem apģērbs (segums). Izmērītā līkne džinsiem:

    2000x2500 segums 0.682   1400x1750 segums 0.882
    1600x2000 segums 0.819   1000x1250 segums 0.969

Tāpēc logs tiek izvēlēts ADAPTĪVI: lielākais 4:5 logs, kurā segums >= 0.88
(tas atbilst atsauces slamjam_3 blīvumam). Ja avots ir tuvplāns (krekls),
segums ir 1.00 un logs ir 2000x2500 pie 1:1 — bez palielināšanas.

Palielināšana ir ar Lanczos un pēc tam vieglu acutance atjaunošanu (unsharp).
Tas ir standarta poligrāfijas paņēmiens: tas neatjauno izdomātas detaļas, bet
atgriež malas asumu, ko interpolācija paņem. Nekas netiek ģenerēts.

Akcenta izvēle ir mērīta, nevis nejauša:
  A) "detaļa" — augstākā detaļu enerģija (Laplacian) apģērba iekšpusē
  B) "zīmols" — lielākā hromas novirze no auduma vidējā (etiķete, aplikācija);
     ja izteiktas novirzes nav, ņem nākamo labāko detaļu.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageFilter

sys.path.insert(0, "/var/tmp/pylibs")
sys.path.insert(0, str(Path(__file__).parent))

from loop import studio_shadow_bg  # noqa: E402
from workflow_v2 import apply_lut  # noqa: E402

OUT = Path(__file__).parent / "output"
CANVAS = (2000, 2500)      # 4:5, tāds pats kā overview
ASPECT = 1.25              # h / w
MIN_COVERAGE = 0.88        # kā atsauces slamjam_3 blīvums
SCORE_SIZE = (800, 1000)   # ar ko meklē akcentu (smalkākā granularitāte)


def _integral(img: np.ndarray) -> np.ndarray:
    return cv2.integral(img.astype(np.float64))


def _box_mean(integ: np.ndarray, y0: int, x0: int, h: int, w: int) -> float:
    s = integ[y0 + h, x0 + w] - integ[y0, x0 + w] - integ[y0 + h, x0] + integ[y0, x0]
    return float(s) / (h * w)


def _windows(shape, wh, step):
    H, W = shape
    w, h = wh
    if h > H or w > W:
        return []
    ys = list(range(0, H - h + 1, step))
    xs = list(range(0, W - w + 1, step))
    if ys[-1] != H - h:
        ys.append(H - h)
    if xs[-1] != W - w:
        xs.append(W - w)
    return [(y, x) for y in ys for x in xs]


def _maps(master, mask):
    """STRUKTŪRAS enerģija un hromas novirze, tikai apģērba iekšpusē.

    Kāpēc strukturālā, nevis parastā Laplacian: vafeļu/pinuma tekstūra visur ir
    vienlīdz spēcīga, tāpēc `Laplacian(lum)` maksimums ir vienkārši
    "blīvākās tekstūras" vieta — iznāca tuvplāns ar tukšu audumu, nevis ar
    detaļu. Mērīts: pirms izlīdzināšanas vid 42.7, pēc σ=6 — 0.68, bet
    kontrasts (max/vid) pieaug 7.5 -> 12.1. Tas nozīmē, ka pēc tekņa
    noņemšanas paliek TIKAI lokalizētā struktūra: šuves, pogas, apkakle,
    aproces. Tieši to vajag akcentam.
    """
    m8 = mask.astype(np.uint8)
    lum = master.astype(np.float32).mean(axis=2)
    ys, xs = np.nonzero(mask)
    gw = int(xs.max() - xs.min() + 1) if len(xs) else 2000
    sig = max(4.0, 0.0030 * gw)          # mērogam piesaistīts, ne fiksēts
    from scipy.ndimage import gaussian_filter
    detail = np.abs(cv2.Laplacian(gaussian_filter(lum, sig),
                                  cv2.CV_32F, ksize=3))
    inner = cv2.erode(m8, np.ones((31, 31), np.uint8)).astype(bool)
    detail = np.where(inner, detail, 0.0)

    core = cv2.erode(m8, np.ones((81, 81), np.uint8)).astype(bool)
    med = (np.median(master[core].astype(np.float32), axis=0)
           if core.sum() > 1000 else np.zeros(3, np.float32))
    dev = np.linalg.norm(master.astype(np.float32) - med[None, None, :], axis=2)
    chroma = np.where(core, np.clip(dev - 45.0, 0, None), 0.0)
    del dev, lum
    return detail, chroma


def pick_centers(master, mask):
    """Atrod akcenta centrus (detaļa, zīmols) ar smalku logu."""
    H, W = mask.shape
    w, h = SCORE_SIZE
    if h > H or w > W:
        w, h = W // 2, int(W // 2 * ASPECT)
    detail, chroma = _maps(master, mask)
    idet, ichr, imsk = _integral(detail), _integral(chroma), _integral(mask.astype(np.uint8))
    del detail, chroma

    scored = []
    for (y, x) in _windows((H, W), (w, h), max(16, w // 12)):
        cov = _box_mean(imsk, y, x, h, w)
        if cov < 0.95:
            continue
        scored.append((y + h // 2, x + w // 2,
                       _box_mean(idet, y, x, h, w),
                       _box_mean(ichr, y, x, h, w)))
    if not scored:
        raise ValueError("nevar atrast akcentu: nav vietas, kur apģērbs aizņem 95%")

    ys, xs = np.nonzero(mask)
    span = float(np.hypot(xs.max() - xs.min(), ys.max() - ys.min())) if len(xs) else 2000.0
    min_sep = 0.28 * span        # abi akcenti nedrīkst būt vienā vietā

    best_detail = max(scored, key=lambda t: t[2])
    far = [t for t in scored
           if np.hypot(t[0] - best_detail[0], t[1] - best_detail[1]) >= min_sep]

    by_chroma = sorted([t for t in far] or scored, key=lambda t: t[3], reverse=True)
    if by_chroma and by_chroma[0][3] > 2.0:
        best_brand, tag = by_chroma[0], "zīmols"
    else:
        rest = sorted(far or scored, key=lambda t: t[2], reverse=True)
        best_brand = rest[0] if rest else scored[len(scored) // 2]
        tag = "detaļa2"
    return [("detaļa", (best_detail[0], best_detail[1])),
            (tag, (best_brand[0], best_brand[1]))]


def fit_window(center, mask, want=(2000, 2500)):
    """Lielākais 4:5 logs ap centru, kurā segums >= MIN_COVERAGE."""
    H, W = mask.shape
    cy, cx = center
    imsk = _integral(mask.astype(np.uint8))
    chosen = None
    w = want[0]
    while w >= 400:
        h = int(round(w * ASPECT))
        if w <= W and h <= H:
            y0 = int(np.clip(cy - h // 2, 0, H - h))
            x0 = int(np.clip(cx - w // 2, 0, W - w))
            cov = _box_mean(imsk, y0, x0, h, w)
            if cov >= MIN_COVERAGE:
                chosen = (x0, y0, w, h, cov)
                break
        w = int(w * 0.92)
    if chosen is None:
        w, h = 800, 1000
        y0 = int(np.clip(cy - h // 2, 0, max(0, H - h)))
        x0 = int(np.clip(cx - w // 2, 0, max(0, W - w)))
        chosen = (x0, y0, w, h, _box_mean(imsk, y0, x0, h, w))
    return chosen


def render(master, mask, profile, win, sharpen_extra=0.35):
    """Izgriež, palielina uz 2000x2500, uzliek LUT un ēnu."""
    x0, y0, cw, ch, _cov = win
    graded = apply_lut(np.asarray(master), profile["lut_rgb"])

    H, W = mask.shape
    # canvas_scale = audekla px / avota px; jaunais studijas modelis pats
    # pārrēķina savas audekla konstantes avota mērogā.
    bg = studio_shadow_bg((H, W), mask.astype(np.uint8),
                          canvas_scale=2000.0 / max(W, 1))

    g = graded[y0:y0 + ch, x0:x0 + cw]
    m = mask[y0:y0 + ch, x0:x0 + cw]
    b = bg[y0:y0 + ch, x0:x0 + cw]
    comp = np.where(m[..., None], g, b[..., None]).astype(np.uint8)

    ow, oh = CANVAS
    if (cw, ch) != (ow, oh):
        # Lanczos: labākā malas saglabāšana no klasiskajiem interpolatoriem.
        comp = cv2.resize(comp, (ow, oh), interpolation=cv2.INTER_LANCZOS4)

    # Acutance atjaunošana pēc palielināšanas. Izmanto profila pašu
    # UnsharpMask (radius/percent/threshold) un pastiprina TIKAI percent,
    # jo `threshold` ir tas, kas neļauj pastiprināt troksni plakanos laukos.
    # Nekas netiek zīmēts no jauna — tikai atgriezts interpolācijas paņemtais asums.
    us = profile.get("output_sharpen") or {}
    radius = float(us.get("radius", 1.4))
    percent = float(us.get("percent", 42))
    threshold = int(us.get("threshold", 3))
    if upscale := CANVAS[0] / cw:
        if upscale > 1.15:
            percent *= 1.0 + min(0.5, (upscale - 1.0) * 0.45)
    percent += sharpen_extra * 100.0
    if percent > 0:
        im = Image.fromarray(comp).filter(
            ImageFilter.UnsharpMask(radius=radius, percent=int(round(percent)),
                                    threshold=threshold))
        comp = np.asarray(im)
    return np.clip(comp, 0, 255).astype(np.uint8)


def main(argv=None):
    ap = argparse.ArgumentParser(description="slamjam stila tuvplāni")
    ap.add_argument("--stems", nargs="+", required=True)
    args = ap.parse_args(argv)

    outdir = OUT / "tuvplani"
    outdir.mkdir(parents=True, exist_ok=True)
    report = {}
    for stem in args.stems:
        prof_p = OUT / "profiles" / f"{stem}_PROFILE.json"
        if not prof_p.exists():
            print(f"  {stem}: nav profila, izlaižu")
            continue
        profile = json.loads(prof_p.read_text(encoding="utf-8"))
        master_p = OUT / "master" / f"{stem}_MASTER_1to1.png"
        mask_p = OUT / "masks" / f"{stem}_MASK.png"
        if not (master_p.exists() and mask_p.exists()):
            print(f"  {stem}: nav master/maskas, izlaižu")
            continue
        master = np.asarray(Image.open(master_p).convert("RGB"))
        mask = (np.asarray(Image.open(mask_p).convert("L")) > 128)

        rec = []
        for i, (tag, center) in enumerate(pick_centers(master, mask), start=1):
            win = fit_window(center, mask)
            img = render(master, mask, profile, win)
            name = f"{stem}_TUVPLANS_{i}_{tag}.jpg"
            Image.fromarray(img).save(outdir / name, quality=95, subsampling=0)
            x0, y0, cw, ch, cov = win
            up = CANVAS[0] / cw
            rec.append({"index": i, "tag": tag, "x": int(x0), "y": int(y0),
                        "crop_w": int(cw), "crop_h": int(ch),
                        "coverage": round(float(cov), 4),
                        "upscale": round(float(up), 3), "file": name})
            print(f"  {stem[:22]:24s} #{i} {tag:7s} logs {cw}x{ch} @({x0},{y0}) "
                  f"segums {cov:.3f} palielin. {up:.2f}x -> {name}")
        report[stem] = rec
    (outdir / "_TUVPLANI.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
