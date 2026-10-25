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

Slam Jam režīms (`--mode slamjam`, PROGRESS §118-§123, STUDIJAS M9)
-----------------------------------------------------------------
Atvasināta detaļa no tā paša MASTERA ar perspektīvas transformāciju,
kas simulē Slam Jam tuvplāna ģeometriju: kamera ~56° virs auduma
plaknes (novirze no normāles 34°, priekšsaīsinājums cos34°), apģērba
pagrieziens -7°, perspektīvas mēroga gradients apakša/augša 1.22.
Kvalitātes vārti (D recepte, POC-3): efektīvais ģeometriskais
palielinājums <= 2.3x (ekvivalenti avota reģions >= 19% no izejas
pikseļiem) un apģērba segums kadrā >= 0.70; ja vārti neiziet, detaļa
netiek rakstīta, bet tiek ierakstīta atskaitē ar iemeslu. Katrs
atvasinātais kadrs atskaitē nes pilnu izcelsmi (avota MASTERIS, centrs,
lauks, ģeometrija, vārtu skaitļi) un faila nosaukumā marķējums
_ATVASINATA. Zonas var norādīt precīzi ar `--zones-file` (JSON:
{stem: [{"tag": ..., "center_xy": [x, y], "src_h": px}]}); bez tā
darbojas automātiskā akcenta izvēle, kurai jebkurā gadījumā
nepieciešams lietotāja apstiprinājums kolāžā.
"""
from __future__ import annotations

import argparse
import json
import math
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

# Slam Jam režīma noklusējumi (STUDIJAS M9, POC-3 "D" recepte).
SLAMJAM_TILT_DEG = 34.0        # novirze no normāles; 56° virs plaknes
SLAMJAM_ROTATION_DEG = -7.0    # apģērba pagrieziens kadrā (mediāna)
SLAMJAM_PERSPECTIVE = 1.22     # mēroga attiecība apakša/augša
SLAMJAM_FIELD_FRAC = 0.45      # vēlamais lauka augstums / apģērba bbox augstums
SLAMJAM_MAX_UPSCALE = 2.3      # kvalitātes vārti: efektīvais palielinājums
SLAMJAM_MIN_SOURCE_FRAC = 0.19  # tas pats vārtu slieksnis laukuma izteiksmē
SLAMJAM_MIN_COVERAGE = 0.80    # apģērba segums; Slam Jam detaļās fons <=17%
                               # (diagonālām piedurknēm izņēmumu dod ar CLI)
SLAMJAM_USM_RADIUS = 2.0
SLAMJAM_USM_PERCENT = 60
SLAMJAM_USM_THRESHOLD = 3


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


def _pick_slamjam_from_maps(mask, detail, chroma, src_h, canvas=CANVAS,
                            tilt_deg=SLAMJAM_TILT_DEG,
                            rotation_deg=SLAMJAM_ROTATION_DEG,
                            perspective=SLAMJAM_PERSPECTIVE,
                            min_render_cov=SLAMJAM_MIN_COVERAGE):
    """Zonu priekšlikums no struktūras/hromas kartēm (tīra funkcija).

    Loģika ir tipa apzinīga: pēc apģērba bbox malu attiecības izšķir
    augšdaļu (tops/jaka) un apakšdaļu (bikses). Pirmā zona vienmēr ir
    augšējā centrālā (kakls/birka vai jostasvieta), otrā — aproce,
    kabata vai apakšmala. Segumu vērtē ar lauka taisnstūri; detaļu un
    hromu — ar mazāku centrālo logu, lai maza birka nepazustu lielā
    lauka vidējā vērtībā. Izvēlētais kandidāts vēl jāiziet rendera
    seguma prognozei (``_warp_coverage``); ja neiziet, ņem nākamo
    pēc vērtējuma. Atgriež [(tag, (cy, cx), src_h), ...] vai
    [] ja pārliecinošu kandidātu nav.
    """
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return []
    bx0, bx1 = int(xs.min()), int(xs.max())
    by0, by1 = int(ys.min()), int(ys.max())
    bw, bh = bx1 - bx0 + 1, by1 - by0 + 1
    is_top = (bw / max(bh, 1)) >= 0.75

    ow, oh = canvas
    cos_t = math.cos(math.radians(tilt_deg))
    fw = int(max(80, round(src_h * (ow / oh) * cos_t)))
    fh = int(max(100, round(src_h)))
    if fw >= mask.shape[1] or fh >= mask.shape[0]:
        return []
    iw, ih = max(60, fw // 2), max(80, fh // 2)
    idet = _integral(detail)
    ichr = _integral(chroma)
    imsk = _integral(mask.astype(np.uint8))

    cands = []
    step = max(12, min(fw, fh) // 16)
    for (y, x) in _windows(mask.shape, (fw, fh), step):
        cov = _box_mean(imsk, y, x, fh, fw)
        if cov < 0.50:
            continue
        cy, cx = y + fh / 2.0, x + fw / 2.0
        iy = int(np.clip(cy - ih / 2, 0, mask.shape[0] - ih))
        ix = int(np.clip(cx - iw / 2, 0, mask.shape[1] - iw))
        cands.append({
            "cy": cy, "cx": cx, "cov": float(cov),
            "det": float(_box_mean(idet, iy, ix, ih, iw)),
            "chr": float(_box_mean(ichr, iy, ix, ih, iw)),
            "u": (cx - bx0) / bw, "v": (cy - by0) / bh,
        })
    if not cands:
        return []

    def _norm(key):
        vals = np.array([c[key] for c in cands], np.float64)
        p95 = float(np.percentile(vals, 95)) if len(vals) else 0.0
        return p95 if p95 > 0 else 1.0

    det_n, chr_n = _norm("det"), _norm("chr")
    for c in cands:
        c["det_n"] = min(c["det"] / det_n, 1.5)
        c["chr_n"] = min(c["chr"] / chr_n, 1.5)

    def best(pred, score_fn, min_cov, exclude=None, min_sep=0.0):
        pool = []
        for c in cands:
            if c["cov"] < min_cov or not pred(c):
                continue
            if exclude is not None and np.hypot(
                    c["cy"] - exclude["cy"], c["cx"] - exclude["cx"]) < min_sep:
                continue
            pool.append((score_fn(c), c))
        pool.sort(key=lambda t: t[0], reverse=True)
        for _s, c in pool:
            wc = _warp_coverage(mask, (c["cy"], c["cx"]), src_h, canvas,
                                tilt_deg, rotation_deg, perspective)
            if wc >= min_render_cov:
                return c
        # Ja neviens neiziet rendera segumu, atgriežam augstāko —
        # gala vārti to godīgi noraidīs ar iemeslu.
        return pool[0][1] if pool else None

    def central(c):
        return max(0.0, 1.0 - abs(c["u"] - 0.5) / 0.5)

    if is_top:
        def score_neck(c):
            v_prior = max(0.0, 1.0 - abs(c["v"] - 0.22) / 0.22)
            return (0.45 * c["det_n"] + 0.65 * c["chr_n"] + 0.35 * c["cov"]
                    + 0.30 * central(c) + 0.20 * v_prior)

        z1 = best(lambda c: 0.32 <= c["u"] <= 0.68 and 0.10 <= c["v"] <= 0.40,
                  score_neck, min_cov=0.70)
        tag1 = "kakls"
    else:
        # Jostas logs balstās uz apģērba augšmalu: ja lauka augstums
        # nesasniedz vidukli, centra mērķis ir "puse lauka no bbox
        # augšas", nevis fiksēts 0.16 — citādi logs sniedzas virs
        # jostas malas fona un rendera seguma vārti to noraida.
        waist_v = max(0.16, 0.5 * fh / max(bh, 1))

        def score_waist(c):
            v_prior = max(0.0, 1.0 - abs(c["v"] - waist_v) / 0.18)
            return (0.50 * c["det_n"] + 0.55 * c["chr_n"] + 0.35 * c["cov"]
                    + 0.25 * central(c) + 0.20 * v_prior)

        z1 = best(lambda c: 0.22 <= c["u"] <= 0.78 and 0.05 <= c["v"] <= 0.40,
                  score_waist, min_cov=0.70)
        tag1 = "josta"
    if z1 is None:
        return []

    def score_second(c, bonus=0.0):
        return (0.75 * c["det_n"] + 0.20 * c["chr_n"] + 0.50 * c["cov"]
                + bonus)

    # Apakšmalai centram jābūt tik zemu, lai apakšmala būtu kadra
    # apakšējā trešdaļā, nevis vienkārši "zemākajā auduma vietā".
    hem_v = 1.0 - 0.42 * (src_h / max(bh, 1))

    def score_hem(c):
        v_prior = max(0.0, 1.0 - abs(c["v"] - hem_v) / 0.18)
        return score_second(c) + 0.30 * v_prior

    # Semantiskās zonas jau atšķiras pēc reģiona; attāluma sargs tikai
    # novērš to pašu vietu divreiz. Augšdaļām zona atšķiras pēc augstuma
    # (kakls/apakšmala), bet bikšu kabatas pie jostas vietas ir tuvu
    # centram, tāpēc tur sargs ir piesaistīts lauka platumam.
    min_sep = 0.5 * src_h if is_top else 0.15 * fw
    if is_top:
        # Aproci meklē kā piedurknes gala klasteri maskas sānu apakšējā
        # daļā; kadra centru nobīda uz iekšu, lai aproce būtu kadrā.
        # Ja šāds kadrs nesasniedz segumu 0.80, aproci nepiedāvā.
        cuff, cuff_score = None, None
        total_mask = int(mask.sum())
        y_start = by0 + int(0.55 * bh)
        for side in ("left", "right"):
            if side == "left":
                sub = mask[y_start:by1 + 1, bx0:bx0 + int(0.16 * bw)]
                x_off = bx0
            else:
                x0c = bx0 + int(0.84 * bw)
                sub = mask[y_start:by1 + 1, x0c:bx1 + 1]
                x_off = x0c
            sy, sx = np.nonzero(sub)
            if len(sx) < 0.003 * total_mask:
                continue
            y_lo = sy.min() + 0.75 * (sy.max() - sy.min())
            end = sy >= y_lo
            cuff_cx = float(np.median(sx[end]) + x_off)
            cuff_cy = float(np.median(sy[end]) + y_start)
            want_cx = cuff_cx + (0.22 * fw if side == "left" else -0.22 * fw)
            want_cy = cuff_cy - 0.18 * fh
            near = min(cands, key=lambda c: (c["cx"] - want_cx) ** 2
                       + (c["cy"] - want_cy) ** 2)
            if near["cov"] < 0.80:
                continue
            if _warp_coverage(mask, (near["cy"], near["cx"]), src_h, canvas,
                              tilt_deg, rotation_deg,
                              perspective) < min_render_cov:
                continue
            if np.hypot(near["cy"] - z1["cy"], near["cx"] - z1["cx"]) < min_sep:
                continue
            s = score_second(near, 0.10)
            if cuff_score is None or s > cuff_score:
                cuff, cuff_score = near, s
        hem = best(lambda c: 0.22 <= c["u"] <= 0.78
                   and c["v"] >= max(0.68, hem_v - 0.10),
                   score_hem, min_cov=0.80,
                   exclude=z1, min_sep=min_sep)
        options = [(score_second(cuff, 0.10), "aproce", cuff) if cuff else None,
                   (score_hem(hem), "apaksmala", hem) if hem else None]
    else:
        pocket = best(lambda c: (c["u"] <= 0.38 or c["u"] >= 0.62)
                      and 0.10 <= c["v"] <= 0.48,
                      lambda c: score_second(c, 0.10), min_cov=0.80,
                      exclude=z1, min_sep=min_sep)
        hem = best(lambda c: c["v"] >= max(0.72, hem_v - 0.10),
                   score_hem, min_cov=0.80,
                   exclude=z1, min_sep=min_sep)
        options = [(score_second(pocket, 0.10), "kabata", pocket)
                   if pocket else None,
                   (score_hem(hem), "apaksmala", hem) if hem else None]
    options = [o for o in options if o is not None]
    if not options:
        return [(tag1, (int(z1["cy"]), int(z1["cx"])), float(src_h))]
    _score, tag2, z2 = max(options, key=lambda t: t[0])
    return [(tag1, (int(z1["cy"]), int(z1["cx"])), float(src_h)),
            (tag2, (int(z2["cy"]), int(z2["cx"])), float(src_h))]


def pick_slamjam_centers(master, mask, src_h=None, canvas=CANVAS,
                         tilt_deg=SLAMJAM_TILT_DEG,
                         rotation_deg=SLAMJAM_ROTATION_DEG,
                         perspective=SLAMJAM_PERSPECTIVE,
                         field_frac=SLAMJAM_FIELD_FRAC,
                         max_upscale=SLAMJAM_MAX_UPSCALE,
                         min_source_fraction=SLAMJAM_MIN_SOURCE_FRAC):
    """Automātisks Slam Jam zonu priekšlikums (2 zonas vai kritiens atpakaļ)."""
    chosen_h, _bbox_h = choose_slamjam_src_h(
        mask, src_h, field_frac, max_upscale, canvas, tilt_deg,
        min_source_fraction)
    detail, chroma = _maps(master, mask)
    zones = _pick_slamjam_from_maps(mask, detail, chroma, chosen_h,
                                    canvas, tilt_deg, rotation_deg,
                                    perspective)
    if len(zones) >= 2:
        return zones
    # Ja tipa loģika deva vienu pārliecinošu zonu, to paturam un mēģinām
    # pievienot otru no vecā akcentu meklētāja — bet tikai tad, ja tā
    # nav praktiski tajā pašā vietā. Divas dublētas zonas ir sliktāk
    # par vienu godīgu.
    out = list(zones)
    try:
        old_centers = pick_centers(master, mask)
    except ValueError:
        old_centers = []
    for tag, center in old_centers:
        if len(out) >= 2:
            break
        if all(np.hypot(center[0] - z[1][0], center[1] - z[1][1])
               >= 0.5 * chosen_h for z in out):
            out.append((tag, center, float(chosen_h)))
    return out


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


def slamjam_metrics(src_h, canvas=CANVAS, tilt_deg=SLAMJAM_TILT_DEG):
    """Efektīvie mērogi Slam Jam laukam ar avota augstumu ``src_h`` px.

    Ģeometriskais palielinājums ir ``sqrt(sx*sy)``; avota daļa ir
    ``1/(sx*sy)``, tāpēc abi vārtu sliekšņi (2.3x un 19%) ir viens
    un tas pats kritērijs divās izteiksmēs.
    """
    ow, oh = canvas
    cos_t = math.cos(math.radians(tilt_deg))
    avg_w = src_h * (ow / oh) * cos_t
    sx = ow / avg_w
    sy = oh / src_h
    return {
        "src_h": float(src_h),
        "src_avg_w": float(avg_w),
        "scale_x": float(sx),
        "scale_y": float(sy),
        "upscale_geom": float(math.sqrt(sx * sy)),
        "source_fraction": float(avg_w * src_h / (ow * oh)),
    }


def min_src_h_for_upscale(max_upscale=SLAMJAM_MAX_UPSCALE, canvas=CANVAS,
                          tilt_deg=SLAMJAM_TILT_DEG,
                          min_source_fraction=SLAMJAM_MIN_SOURCE_FRAC):
    """Mazākais avota lauka augstums, kas iziet abus vārtu sliekšņus."""
    _ow, oh = canvas
    cos_t = math.cos(math.radians(tilt_deg))
    by_upscale = oh / (max_upscale * math.sqrt(cos_t))
    by_fraction = oh * math.sqrt(min_source_fraction) / math.sqrt(cos_t)
    return max(by_upscale, by_fraction)


def slamjam_quad(center_yx, src_h, canvas=CANVAS,
                 tilt_deg=SLAMJAM_TILT_DEG,
                 rotation_deg=SLAMJAM_ROTATION_DEG,
                 perspective=SLAMJAM_PERSPECTIVE):
    """Avota četrstūris (x, y) izejas kadra stūriem TL, TR, BR, BL."""
    ow, oh = canvas
    cos_t = math.cos(math.radians(tilt_deg))
    avg_w = src_h * (ow / oh) * cos_t
    top_w = avg_w * 2 * perspective / (1 + perspective)
    bot_w = avg_w * 2 / (1 + perspective)
    rel = np.float32([[-top_w / 2, -src_h / 2], [top_w / 2, -src_h / 2],
                      [bot_w / 2, src_h / 2], [-bot_w / 2, src_h / 2]])
    th = math.radians(rotation_deg)
    rot = np.float32([[math.cos(th), -math.sin(th)],
                      [math.sin(th), math.cos(th)]])
    cy, cx = center_yx
    return rel @ rot.T + np.float32([cx, cy])


def _warp_coverage(mask, center_yx, src_h, canvas=CANVAS,
                   tilt_deg=SLAMJAM_TILT_DEG,
                   rotation_deg=SLAMJAM_ROTATION_DEG,
                   perspective=SLAMJAM_PERSPECTIVE, ds=8):
    """Lēta rendera seguma prognoze: perspektīvas kvadrāts uz mazas maskas.

    Tas pats, ko rēķina ``render_slamjam`` kā ``alpha > 0.5`` segumu,
    bet 1:8 mērogā — pietiek zonu izvēlei, pirms kaut kas tiek
    renderēts pilnā izmērā.
    """
    ow, oh = canvas
    h, w = mask.shape
    m_small = cv2.resize(np.where(mask, 255, 0).astype(np.uint8),
                         (max(1, w // ds), max(1, h // ds)),
                         interpolation=cv2.INTER_AREA)
    quad = slamjam_quad(center_yx, src_h, canvas, tilt_deg, rotation_deg,
                        perspective)
    dst = np.float32([[0, 0], [ow / ds - 1, 0],
                      [ow / ds - 1, oh / ds - 1], [0, oh / ds - 1]])
    mtx = cv2.getPerspectiveTransform(
        (quad / ds).astype(np.float32), dst)
    alpha = cv2.warpPerspective(m_small, mtx, (int(ow / ds), int(oh / ds)),
                                flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return float((alpha > 127).mean())


def choose_slamjam_src_h(mask, src_h=None, field_frac=SLAMJAM_FIELD_FRAC,
                         max_upscale=SLAMJAM_MAX_UPSCALE, canvas=CANVAS,
                         tilt_deg=SLAMJAM_TILT_DEG,
                         min_source_fraction=SLAMJAM_MIN_SOURCE_FRAC):
    """Lauka augstums: vēlamā apģērba daļa, bet ne zem vārtu minimuma."""
    if src_h:
        return float(src_h), None
    ys, _xs = np.nonzero(mask)
    bbox_h = int(ys.max() - ys.min() + 1) if len(ys) else mask.shape[0]
    desired = field_frac * bbox_h
    minimum = min_src_h_for_upscale(max_upscale, canvas, tilt_deg,
                                    min_source_fraction)
    return float(max(desired, minimum)), bbox_h


def slamjam_gate(metrics, coverage, max_upscale=SLAMJAM_MAX_UPSCALE,
                 min_source_fraction=SLAMJAM_MIN_SOURCE_FRAC,
                 min_coverage=SLAMJAM_MIN_COVERAGE):
    """Atgriež (iziet, [iemesli]); sliekšņus nekad nepielāgo klusi."""
    reasons = []
    if metrics["upscale_geom"] > max_upscale:
        reasons.append(
            f"upscale_geom {metrics['upscale_geom']:.2f}x > {max_upscale}x")
    if metrics["source_fraction"] < min_source_fraction:
        reasons.append(
            f"source_fraction {metrics['source_fraction']:.3f} "
            f"< {min_source_fraction}")
    if coverage < min_coverage:
        reasons.append(f"coverage {coverage:.3f} < {min_coverage}")
    return (not reasons), reasons


def render_slamjam(master, mask, profile, center_yx, src_h, canvas=CANVAS,
                   tilt_deg=SLAMJAM_TILT_DEG,
                   rotation_deg=SLAMJAM_ROTATION_DEG,
                   perspective=SLAMJAM_PERSPECTIVE,
                   usm_radius=SLAMJAM_USM_RADIUS,
                   usm_percent=SLAMJAM_USM_PERCENT,
                   usm_threshold=SLAMJAM_USM_THRESHOLD):
    """Perspektīvas atvasinātā detaļa: warp no MASTERA + svaiga ēna.

    Audums un maska tiek transformēti atsevišķi; studijas fons ar ēnu
    tiek ģenerēts no jauna izejas mērogā, lai avota ēna netiktu
    izstiepta līdzi audumam.
    """
    ow, oh = canvas
    graded = apply_lut(np.asarray(master), profile["lut_rgb"])
    quad = slamjam_quad(center_yx, src_h, canvas, tilt_deg, rotation_deg,
                        perspective)
    dst = np.float32([[0, 0], [ow - 1, 0], [ow - 1, oh - 1], [0, oh - 1]])
    mtx = cv2.getPerspectiveTransform(quad, dst)
    fg = cv2.warpPerspective(graded, mtx, (ow, oh),
                             flags=cv2.INTER_LANCZOS4,
                             borderMode=cv2.BORDER_CONSTANT,
                             borderValue=(243, 243, 243))
    alpha = cv2.warpPerspective(mask.astype(np.float32), mtx, (ow, oh),
                                flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT,
                                borderValue=0)
    alpha = np.clip(alpha, 0.0, 1.0)
    coverage = float((alpha > 0.5).mean())
    bg = studio_shadow_bg((oh, ow), (alpha > 0.5).astype(np.uint8),
                          canvas_scale=1.0)
    comp = (fg.astype(np.float32) * alpha[..., None]
            + bg.astype(np.float32)[..., None] * (1.0 - alpha[..., None]))
    comp = np.clip(comp, 0, 255).astype(np.uint8)
    if usm_percent > 0:
        comp = np.asarray(Image.fromarray(comp).filter(
            ImageFilter.UnsharpMask(radius=float(usm_radius),
                                    percent=int(usm_percent),
                                    threshold=int(usm_threshold))))
    metrics = slamjam_metrics(src_h, canvas, tilt_deg)
    return comp, quad, metrics, coverage


def load_zones(path):
    """JSON zonu fails -> {stem: [(tag, (cy, cx), src_h|None), ...]}."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("zonu fails: gaidīts objekts {stem: [...]}")
    out = {}
    for stem, entries in data.items():
        parsed = []
        for e in entries:
            cx, cy = e["center_xy"]
            parsed.append((str(e.get("tag", "detaļa")),
                           (int(cy), int(cx)),
                           (float(e["src_h"]) if e.get("src_h") else None)))
        out[str(stem)] = parsed
    return out


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
    ap.add_argument("--mode", choices=["crop", "slamjam"], default="crop",
                    help="crop: līdzšinējais taisnstūra logs; slamjam: "
                         "atvasināta detaļa ar perspektīvas transformāciju")
    ap.add_argument("--zones-file", default=None,
                    help="JSON {stem: [{tag, center_xy, src_h}]}; bez tā "
                         "centrus izvēlas pick_centers")
    ap.add_argument("--tilt-deg", type=float, default=SLAMJAM_TILT_DEG)
    ap.add_argument("--rotation-deg", type=float,
                    default=SLAMJAM_ROTATION_DEG)
    ap.add_argument("--perspective", type=float,
                    default=SLAMJAM_PERSPECTIVE)
    ap.add_argument("--field-frac", type=float, default=SLAMJAM_FIELD_FRAC)
    ap.add_argument("--max-upscale", type=float,
                    default=SLAMJAM_MAX_UPSCALE)
    ap.add_argument("--min-source-frac", type=float,
                    default=SLAMJAM_MIN_SOURCE_FRAC)
    ap.add_argument("--min-coverage", type=float,
                    default=SLAMJAM_MIN_COVERAGE)
    ap.add_argument("--usm-radius", type=float, default=SLAMJAM_USM_RADIUS)
    ap.add_argument("--usm-percent", type=int, default=SLAMJAM_USM_PERCENT)
    ap.add_argument("--usm-threshold", type=int,
                    default=SLAMJAM_USM_THRESHOLD)
    args = ap.parse_args(argv)
    zones = load_zones(args.zones_file) if args.zones_file else {}

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

        if stem in zones:
            centers = zones[stem]
        elif args.mode == "slamjam":
            centers = pick_slamjam_centers(
                master, mask, canvas=CANVAS, tilt_deg=args.tilt_deg,
                rotation_deg=args.rotation_deg,
                perspective=args.perspective,
                field_frac=args.field_frac, max_upscale=args.max_upscale,
                min_source_fraction=args.min_source_frac)
        else:
            centers = [(tag, center, None)
                       for tag, center in pick_centers(master, mask)]
        rec = []
        for i, (tag, center, zone_src_h) in enumerate(centers, start=1):
            if args.mode == "slamjam":
                src_h, _bbox_h = choose_slamjam_src_h(
                    mask, zone_src_h, args.field_frac, args.max_upscale,
                    CANVAS, args.tilt_deg, args.min_source_frac)
                img, quad, metrics, cov = render_slamjam(
                    master, mask, profile, center, src_h, CANVAS,
                    args.tilt_deg, args.rotation_deg, args.perspective,
                    args.usm_radius, args.usm_percent, args.usm_threshold)
                passed, reasons = slamjam_gate(
                    metrics, cov, args.max_upscale, args.min_source_frac,
                    args.min_coverage)
                entry = {
                    "index": i, "tag": tag, "derived": True,
                    "mode": "slamjam", "source_master": master_p.name,
                    "center_xy": [int(center[1]), int(center[0])],
                    "src_h": round(float(src_h), 1),
                    "quad_xy": [[round(float(x), 1), round(float(y), 1)]
                                for x, y in quad],
                    "tilt_deg": args.tilt_deg,
                    "rotation_deg": args.rotation_deg,
                    "perspective": args.perspective,
                    "upscale_geom": round(metrics["upscale_geom"], 3),
                    "source_fraction": round(metrics["source_fraction"], 4),
                    "coverage": round(float(cov), 4),
                    "gate_pass": bool(passed), "gate_reasons": reasons,
                }
                name = f"{stem}_DETALA_{i}_{tag}_ATVASINATA.jpg"
                if passed:
                    Image.fromarray(img).save(outdir / name, quality=95,
                                              subsampling=0)
                    entry["file"] = name
                    entry["status"] = "written"
                    print(f"  {stem[:22]:24s} #{i} {tag:7s} slamjam "
                          f"lauks h={src_h:.0f} segums {cov:.3f} "
                          f"palielin. {metrics['upscale_geom']:.2f}x "
                          f"-> {name}")
                else:
                    entry["status"] = "gate_fail"
                    stale = outdir / name
                    if stale.exists():
                        stale.unlink()
                        entry["removed_stale_file"] = name
                    print(f"  {stem[:22]:24s} #{i} {tag:7s} slamjam "
                          f"VARTI NEIZGĀJA: {'; '.join(reasons)}")
                rec.append(entry)
                continue
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
