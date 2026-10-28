"""Paper-leak QA + paper-background prototype.

STATUS 2026-10-22
-----------------
* `leak_probe()` / `correct_leaks()`  -- VALIDATED. Injection test: 204 800 px
  of paper found and removed, 0 px removed outside it, 0 added. Used by
  GATE_L (advisory).
* `paper_background_mask()`           -- CLOSED / NOT FOR PRODUCTION.
  Segmentation from paper appearance alone does not generalise: it is speckled
  on smooth paper and treats paper creases as fabric. Kept as a lab prototype
  only. See PAPIRA_NOPLUDES_QA.md section 12.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

# ---------------------------------------------------------------- colour ----
_XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                 [0.2126729, 0.7151522, 0.0721750],
                 [0.0193339, 0.1191920, 0.9503041]], np.float64)
_WHITE = np.array([0.95047, 1.0, 1.08883], np.float64)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    c = rgb.astype(np.float32) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = c @ _XYZ.T.astype(np.float32)
    t = xyz / _WHITE.astype(np.float32)
    d = (6.0 / 29.0) ** 3
    f = np.where(t > d, np.cbrt(t), t / (3 * (6.0 / 29.0) ** 2) + 4.0 / 29.0)
    return np.stack([116.0 * f[..., 1] - 16.0,
                     500.0 * (f[..., 0] - f[..., 1]),
                     200.0 * (f[..., 1] - f[..., 2])], axis=-1).astype(np.float32)


def lab_chunked(rgb: np.ndarray, rows: int = 512) -> np.ndarray:
    """Same as rgb_to_lab but caps peak memory on 12 MP photos."""
    h = rgb.shape[0]
    out = np.empty(rgb.shape[:2] + (3,), np.float32)
    for y in range(0, h, rows):
        out[y:y + rows] = rgb_to_lab(rgb[y:y + rows])
    return out


def _otsu(values: np.ndarray) -> float:
    """Classic Otsu threshold on a 1-D sample."""
    hist, edges = np.histogram(values, bins=128)
    centres = 0.5 * (edges[:-1] + edges[1:])
    w = hist.astype(np.float64)
    tot = w.sum()
    if tot <= 0:
        return float(np.median(values))
    cw = np.cumsum(w)
    cm = np.cumsum(w * centres)
    mu_t = cm[-1] / tot
    denom = cw * (tot - cw)
    with np.errstate(divide="ignore", invalid="ignore"):
        between = (mu_t * cw - cm) ** 2 / denom
    between[~np.isfinite(between)] = -1
    return float(centres[int(np.argmax(between))])


def measure_paper_colour(img: Image.Image, tex_limit: float = 1.0) -> dict:
    """Robust paper/backdrop estimate from the outer frame.

    Paper is assumed to be (a) present in the frame border and (b) SMOOTH.
    The frame is split into two luminance modes; the smoother mode wins.
    If the smoother mode is a negligible sliver, the brighter mode wins.
    Every candidate is reported so the decision stays auditable.
    """
    a = np.asarray(img.convert("RGB"))
    h, w = a.shape[:2]
    ring = max(10, int(round(min(h, w) * 0.02)))
    sel = np.zeros((h, w), bool)
    sel[:ring, :] = sel[-ring:, :] = True
    sel[:, :ring] = sel[:, -ring:] = True

    # work at quarter scale for the texture estimate only
    small = img.convert("RGB").resize((max(1, w // 4), max(1, h // 4)), Image.BILINEAR)
    lab_s = rgb_to_lab(np.asarray(small))
    tex_s = texture_map(lab_s[..., 0], 3)

    px = a[sel]
    lab_px = rgb_to_lab(px)
    L = lab_px[:, 0]

    t = _otsu(L)
    groups = {"dark": L <= t, "bright": L > t}
    cands = []
    for name, gm in groups.items():
        frac = float(gm.mean())
        if gm.sum() < 50:
            continue
        rgb_med = np.median(px[gm], axis=0)
        # texture of this mode, sampled from the same place at quarter scale
        ys, xs = np.nonzero(sel)
        sy, sx = np.clip(ys // 4, 0, tex_s.shape[0] - 1), np.clip(xs // 4, 0, tex_s.shape[1] - 1)
        tex_vals = tex_s[sy[gm], sx[gm]]
        cands.append({
            "mode": name,
            "ring_frac": round(frac, 4),
            "rgb": [int(round(v)) for v in rgb_med],
            "lab": [round(float(v), 2) for v in rgb_to_lab(rgb_med[None, :])[0]],
            "tex_median": round(float(np.median(tex_vals)), 3),
        })

    if not cands:
        cands = [{"mode": "all", "ring_frac": 1.0,
                  "rgb": [int(round(v)) for v in np.median(px, axis=0)],
                  "lab": [round(float(v), 2) for v in rgb_to_lab(np.median(px, axis=0)[None, :])[0]],
                  "tex_median": 0.0}]

    by_smooth = sorted(cands, key=lambda c: c["tex_median"])
    pick = by_smooth[0]
    conf = "ok"
    if pick["ring_frac"] < 0.10 and len(by_smooth) > 1:
        pick = by_smooth[1]
        conf = "smooth mode too small, used second smoothest"
    if pick["ring_frac"] < 0.02:
        conf = "no usable backdrop in frame"

    # Papīrs ir ļoti gluds. Ja "gludākais" režīms tomēr ir teksturēts, tad kadrā
    # vispār nav papīra (piem. koka grīda) - tad noplūdes tests nav piemērojams.
    # `tex_limit` ir noklusējums gludam fotopapīram (1.0). Graudains kartons
    # mērās ap 1.6 un tika noraidīts kā "nav papīra", lai gan tas ir lietojams
    # fons. Tāpēc robeža ir PARAMETRS: apmales retry to var paplašināt APZINĀTI
    # un ierakstīt atskaitē, nevis klusi samainīt visiem.
    plausible = bool(pick["tex_median"] <= tex_limit)
    conf_base = conf          # pirms plausibilitātes pārrakstīšanas
    # Ja 2–3 kadra malās iziet teksturēts apģērbs (bleed tuvplāns, piem., 145704),
    # kopīgais Otsu sadalījums sajauc fona papīru ar auduma ēnainajām rievām un
    # mākslīgi paceļ `tex_median` virs `tex_limit`. Tādā gadījumā pārbauda katru
    # no 4 kadra malām atsevišķi: ja vismaz viena pilnvērtīga mala (>=10% gredzena)
    # satur gludu fonu (<= tex_limit), izvēlas gludāko šādu malu. Pilnkadra makro
    # (audums visās 4 malās) neviena mala to neiztur un `plausible` paliek False.
    if not plausible:
        edge_masks = (
            ("top", np.r_[np.ones((ring, w), bool), np.zeros((h - ring, w), bool)]),
            ("bottom", np.r_[np.zeros((h - ring, w), bool), np.ones((ring, w), bool)]),
            ("left", np.c_[np.ones((h, ring), bool), np.zeros((h, w - ring), bool)]),
            ("right", np.c_[np.zeros((h, w - ring), bool), np.ones((h, ring), bool)]),
        )
        edge_cands = []
        tot_ring = float(max(1, int(sel.sum())))
        for ename, emask in edge_masks:
            ey, ex = np.nonzero(emask)
            if ey.size < 200 or (ey.size / tot_ring) < 0.08:
                continue
            epx = a[ey, ex]
            eL = rgb_to_lab(epx)[:, 0]
            et = _otsu(eL)
            for sub, gm in (("all", np.ones(ey.size, bool)),
                            ("dark", eL <= et), ("bright", eL > et)):
                n_gm = int(gm.sum())
                if n_gm < 200 or (n_gm / tot_ring) < 0.08:
                    continue
                sy = np.clip(ey[gm] // 4, 0, tex_s.shape[0] - 1)
                sx = np.clip(ex[gm] // 4, 0, tex_s.shape[1] - 1)
                t_med = float(np.median(tex_s[sy, sx]))
                rgb_med = np.median(epx[gm], axis=0)
                edge_cands.append({
                    "mode": f"edge_{ename}_{sub}",
                    "ring_frac": round(n_gm / tot_ring, 4),
                    "rgb": [int(round(v)) for v in rgb_med],
                    "lab": [round(float(v), 2) for v in rgb_to_lab(rgb_med[None, :])[0]],
                    "tex_median": round(t_med, 3),
                })
        qual = [ec for ec in edge_cands if ec["tex_median"] <= tex_limit]
        if qual:
            best_edge = min(qual, key=lambda ec: ec["tex_median"])
            cands.extend(edge_cands)
            pick = best_edge
            plausible = True
            conf_base = "single-edge backdrop (bleed frame)"
            conf = conf_base
        else:
            conf = "no paper-like backdrop"
    return {
        "rgb": pick["rgb"],
        "lab": pick["lab"],
        "plausible": plausible,
        "confidence_base": conf_base,
        "tex_median": pick["tex_median"],
        "confidence": conf,
        "ring_px": int(sel.sum()),
        "chosen_mode": pick["mode"],
        "candidates": cands,
        "component": "smoothness-first two-mode split of the outer "
                     f"{ring}px frame",
    }


# --------------------------------------------------------------- texture ----
def texture_map(L: np.ndarray, win: int = 5) -> np.ndarray:
    m = ndimage.uniform_filter(L, size=win, mode="nearest")
    m2 = ndimage.uniform_filter(L * L, size=win, mode="nearest")
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


# ------------------------------------------------------------ thresholds ----
def _youden(values: np.ndarray, is_pos: np.ndarray) -> tuple[float, float]:
    """Best 1-D split of `values` predicting is_pos; returns (threshold, AUC).

    Predicts is_pos by `values <= threshold`.
    """
    q = np.quantile(values, np.linspace(0.002, 0.998, 300))
    q = np.unique(q)
    best_t, best_j = float(q[0]), -1.0
    pos = values[is_pos]
    neg = values[~is_pos]
    if pos.size == 0 or neg.size == 0:
        return best_t, float("nan")
    for t in q:
        tpr = float((pos <= t).mean())
        fpr = float((neg <= t).mean())
        j = tpr - fpr
        if j > best_j:
            best_j, best_t = j, float(t)
    # AUC via the Mann-Whitney rank identity (ties get their average rank).
    sub = 150000
    rng = np.random.default_rng(0)
    p = pos if pos.size <= sub else rng.choice(pos, sub, replace=False)
    n = neg if neg.size <= sub else rng.choice(neg, sub, replace=False)
    vals = np.concatenate([p, n])
    order = np.argsort(vals, kind="mergesort")
    ranks = np.empty(vals.size, np.float64)
    ranks[order] = np.arange(1, vals.size + 1, dtype=np.float64)
    # average ranks inside tie groups
    sv = vals[order]
    starts = np.flatnonzero(np.r_[True, sv[1:] != sv[:-1]])
    ends = np.r_[starts[1:], sv.size]
    for s, e in zip(starts, ends):
        if e - s > 1:
            ranks[order[s:e]] = (s + 1 + e) / 2.0
    n_p, n_n = p.size, n.size
    u = ranks[:n_p].sum() - n_p * (n_p + 1) / 2.0
    return best_t, float(1.0 - u / (n_p * n_n))


def derive_thresholds(lab: np.ndarray, tex: np.ndarray, alpha: np.ndarray,
                      dist_in: np.ndarray, paper_lab) -> dict:
    """Thresholds come from the measured background population, not from taste.

    Two shadow-tolerant channels:
      dC  = chroma distance  sqrt((a*-a0)^2 + (b*-b0)^2)   -- survives shadow,
            because shadow scales luminance, not the a*/b* ratio
      tex = local std of L* -- paper is smooth, fabric is not

    Each threshold is the 90th percentile of the PAPER class (the pixels the
    mask already calls background), clamped to a physically sane band. Using a
    quantile instead of an optimised split is deliberate: an optimised split
    proved unstable (it jumped 14.6 -> 7.4 delta-E on a 1-unit colour change).
    """
    p0 = np.asarray(paper_lab, np.float32)
    paper = alpha < 0.05
    garment = (alpha > 0.95) & (dist_in > 25)
    if garment.sum() < 5000:
        garment = (alpha > 0.95) & (dist_in > 10)

    dC = np.linalg.norm(lab[..., 1:] - p0[1:], axis=-1)
    L = lab[..., 0]
    t_c = float(np.clip(np.percentile(dC[paper], 90), 0.5, 3.0))
    t_t = float(np.clip(np.percentile(tex[paper], 90), 0.35, 2.5))
    # nothing can be "paper in shadow" darker than the darkest paper we measured
    L_min = float(max(0.0, np.percentile(L[paper], 1) - 3.0))

    # interpretable quality numbers instead of an AUC
    fpr = float(((dC[garment] <= t_c) & (tex[garment] <= t_t) & (L[garment] >= L_min)).mean()) if garment.any() else 0.0
    recall = float(((dC[paper] <= t_c) & (tex[paper] <= t_t) & (L[paper] >= L_min)).mean()) if paper.any() else 0.0
    dC_g = float(np.percentile(dC[garment], 5)) if garment.any() else float("nan")
    return {
        "dC_threshold": round(t_c, 3),
        "tex_threshold": round(t_t, 3),
        "L_min": round(L_min, 2),
        "paper_dC_p90": round(float(np.percentile(dC[paper], 90)), 3),
        "paper_tex_p90": round(float(np.percentile(tex[paper], 90)), 3),
        "garment_dC_p05": round(dC_g, 3),
        "paper_recall": round(recall, 4),
        "garment_fpr": round(fpr, 4),
        "separation_ratio": round((dC_g / t_c) if t_c > 0 else float("nan"), 2),
        "n_paper_ref": int(paper.sum()),
        "n_garment_ref": int(garment.sum()),
    }


# ---------------------------------------------------------------- probe ----
def leak_probe(img: Image.Image, alpha: np.ndarray, *, min_area_frac: float = 0.0004) -> dict:
    rgb = np.asarray(img.convert("RGB"))
    h, w = alpha.shape
    paper = measure_paper_colour(img)
    lab = lab_chunked(rgb)
    L = lab[..., 0]
    p0 = np.array(paper["lab"], np.float32)
    dE = np.linalg.norm(lab - p0, axis=-1)
    dC = np.linalg.norm(lab[..., 1:] - p0[1:], axis=-1)
    tex = texture_map(L)

    fg = alpha >= 0.5

    # depth inside the silhouette (chebyshev-ish via EDT of the background)
    dist_in = ndimage.distance_transform_edt(fg)


    th = derive_thresholds(lab, tex, alpha, dist_in, paper["lab"])
    cand = (fg & (dC <= th["dC_threshold"]) & (tex <= th["tex_threshold"])
            & (L >= th["L_min"]))

    # clean single-pixel noise
    cand = ndimage.binary_opening(cand, structure=np.ones((3, 3)))
    lab_c, n = ndimage.label(cand)
    min_area = max(40, int(min_area_frac * h * w))
    regions = []
    if n:
        objs = ndimage.find_objects(lab_c)
        sizes = ndimage.sum(cand, lab_c, index=np.arange(1, n + 1))
        for i, sl in enumerate(objs, start=1):
            area = int(sizes[i - 1])
            if area < min_area:
                continue
            y0, y1 = sl[0].start, sl[0].stop
            x0, x1 = sl[1].start, sl[1].stop
            sub = lab_c[sl] == i
            touches_border = bool(y0 == 0 or x0 == 0 or y1 == h or x1 == w)
            # how far this blob reaches into the garment
            max_depth = float(dist_in[sl][sub].max())
            # is it enclosed by foreground (a hole) or flush with the edge?
            grown = ndimage.binary_dilation(sub, np.ones((5, 5)))
            ring = grown & ~sub
            ring_bg_frac = float((alpha[sl][ring] < 0.5).mean()) if ring.any() else 1.0
            regions.append({
                "id": i,
                "area_px": area,
                "area_pct_of_fg": round(100.0 * area / max(1, int(fg.sum())), 3),
                "bbox_xyxy": [int(x0), int(y0), int(x1), int(y1)],
                "mean_alpha": round(float(alpha[sl][sub].mean()), 4),
                "mean_dE": round(float(dE[sl][sub].mean()), 2),
                "mean_dC": round(float(dC[sl][sub].mean()), 2),
                "mean_tex": round(float(tex[sl][sub].mean()), 2),
                "max_depth_px": round(max_depth, 1),
                "touches_photo_border": touches_border,
                "enclosed_by_fg": bool(ring_bg_frac < 0.15),
            })
    regions.sort(key=lambda r: -r["area_px"])

    leak_px = int(sum(r["area_px"] for r in regions))
    fg_px = int(fg.sum())
    enclosed = [r for r in regions if r["enclosed_by_fg"]]
    # The verdict is REGION based: scattered pale pixels that never form a
    # region above the area floor are garment texture, not leaks. The pixel
    # false-positive rate only decides how much confidence to attach.
    verdict = "DUBIOUS" if leak_px > 0.005 * fg_px else "PASS"
    confidence = "high"
    if th["garment_fpr"] > 0.02 or th["separation_ratio"] < 1.2:
        confidence = "marginal"
    return {
        "verdict": verdict,
        "confidence": confidence,
        "paper": paper,
        "thresholds": th,
        "fg_px": fg_px,
        "coverage": round(fg_px / (h * w), 4),
        "leak_px": leak_px,
        "leak_pct_of_fg": round(100.0 * leak_px / max(1, fg_px), 3),
        "regions": regions[:25],
        "n_regions": len(regions),
        "enclosed_regions": len(enclosed),
    }


def render_probe(img: Image.Image, alpha: np.ndarray, result: dict, dst: str, max_w: int = 1400):
    """Red tint over every detected leak region, for eyeball QA."""
    rgb = np.asarray(img.convert("RGB")).astype(np.float32)
    overlay = rgb.copy()
    lab = lab_chunked(rgb)
    p0 = np.array(result["paper"]["lab"], np.float32)
    dC = np.linalg.norm(lab[..., 1:] - p0[1:], axis=-1)
    tex = texture_map(lab[..., 0])
    fg = alpha >= 0.5
    cand = (fg & (dC <= result["thresholds"]["dC_threshold"]) & (tex <= result["thresholds"]["tex_threshold"])
            & (lab[..., 0] >= result["thresholds"]["L_min"]))
    cand = ndimage.binary_opening(cand, structure=np.ones((3, 3)))
    lab_c, n = ndimage.label(cand)
    keep = np.zeros_like(cand)
    min_area = max(40, int(0.0004 * alpha.size))
    if n:
        sizes = ndimage.sum(cand, lab_c, index=np.arange(1, n + 1))
        good = np.flatnonzero(sizes >= min_area) + 1
        keep = np.isin(lab_c, good)
    keep = ndimage.binary_dilation(keep, np.ones((3, 3)))
    overlay[keep] = overlay[keep] * 0.25 + np.array([255, 0, 0]) * 0.75
    # silhouette contour
    edge = ndimage.binary_dilation(fg, np.ones((3, 3))) & ~ndimage.binary_erosion(fg, np.ones((3, 3)))
    overlay[edge] = overlay[edge] * 0.35 + np.array([0, 255, 120]) * 0.65
    out = Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8), "RGB")
    if out.width > max_w:
        out = out.resize((max_w, round(out.height * max_w / out.width)), Image.LANCZOS)
    out.save(dst, quality=88)
    return dst


# ------------------------------------------------------------ correction ----
def _seed_mask(img, alpha, result, min_area=None):
    """Rebuild the exact candidate mask the probe used."""
    rgb = np.asarray(img.convert("RGB"))
    lab = lab_chunked(rgb)
    p0 = np.array(result["paper"]["lab"], np.float32)

    dC = np.linalg.norm(lab[..., 1:] - p0[1:], axis=-1)
    tex = texture_map(lab[..., 0])
    th = result["thresholds"]
    Lmap = lab[..., 0]
    cand = ((alpha >= 0.5) & (dC <= th["dC_threshold"]) & (tex <= th["tex_threshold"])
            & (Lmap >= th["L_min"]))
    cand = ndimage.binary_opening(cand, structure=np.ones((3, 3)))
    if min_area is None:
        min_area = max(40, int(0.0004 * alpha.size))
    lbl, n = ndimage.label(cand)
    if n:
        sizes = ndimage.sum(cand, lbl, index=np.arange(1, n + 1))
        keep = np.isin(lbl, np.flatnonzero(sizes >= min_area) + 1)
    else:
        keep = cand
    return keep, dC, tex, th, Lmap


def correct_leaks(img: Image.Image, alpha: np.ndarray, result: dict,
                  grow: bool = True, max_grow: float = 1.6, feather_px: float = 1.2) -> tuple[np.ndarray, dict]:
    """Deterministic paper-leak removal.

    Seeds (the detected leak pixels) are grown geodesically inside the
    foreground but ONLY through pixels that are themselves paper-like
    (colour AND texture). Growth stops by construction at real fabric, and a
    per-seed cap (`max_grow`x the seed area) prevents a runaway fill.

    No model, no invention: pixels are only ever turned from opaque to
    transparent inside the mask that already contains them.
    """
    from scipy.ndimage import binary_propagation, gaussian_filter

    seeds, dC, tex, th, Lmap = _seed_mask(img, alpha, result)
    removal = seeds.copy()
    if grow and seeds.any():
        growable = ((alpha >= 0.5) & (dC <= th["dC_threshold"]) & (tex <= th["tex_threshold"])
                    & (Lmap >= th["L_min"]))
        lbl_s, ns = ndimage.label(seeds)
        grown = np.zeros_like(seeds)
        for i in range(1, ns + 1):
            comp = lbl_s == i
            if not comp.any():
                continue
            area = int(comp.sum())
            rec = binary_propagation(comp, mask=growable)
            # cap the growth per seed
            extra = int(rec.sum()) - area
            cap = int(round(area * (max_grow - 1.0)))
            if extra > cap > 0:
                # keep only the part closest to the seed: rank by distance
                dist = ndimage.distance_transform_edt(~comp)
                order = np.argsort(dist[rec].ravel())
                idx = np.flatnonzero(rec.ravel())[order][: area + cap]
                rec = np.zeros(alpha.size, bool)
                rec.ravel()[idx] = True
            grown |= rec
        removal = grown

    soft = gaussian_filter(removal.astype(np.float32), feather_px)
    soft = np.clip(soft * 1.35, 0.0, 1.0)
    new_alpha = np.minimum(alpha, 1.0 - soft)
    new_alpha[removal] = np.minimum(new_alpha[removal], 0.0)

    info = {
        "seed_px": int(seeds.sum()),
        "removed_px": int((alpha >= 0.5).sum() - (new_alpha >= 0.5).sum()),
        "removed_pct_of_fg": round(100.0 * (int((alpha >= 0.5).sum()) - int((new_alpha >= 0.5).sum()))
                                   / max(1, int((alpha >= 0.5).sum())), 3),
        "grow": grow,
    }
    return new_alpha.astype(np.float32), info


# ------------------------------------------------- paper-seeded background ----
def paper_background_mask(img: Image.Image, ring_px: int | None = None,
                          work_scale: int = 1) -> dict:
    """Model-free background segmentation driven by the measured paper.

    Works where saliency models fail (frame-filling close-ups) because it never
    looks for "an object" - it looks for the stuff that is indistinguishable
    from the paper: same chroma, same smoothness, not darker than the darkest
    measured paper, and connected to the photo border.

    Returns the background mask (True = paper) plus the numbers used.
    """
    from scipy import ndimage

    paper_probe = measure_paper_colour(img)
    if not paper_probe.get("plausible", True):
        return {"refused": True,
                "reason": "no paper-like backdrop in frame",
                "peak": paper_probe,
                "fg_coverage": None}

    full_size = img.size
    if work_scale > 1:
        # Texture and shadows live at a coarser scale than sensor noise; the
        # decision is made where the signal is, then mapped back up.
        img = img.convert("RGB").resize(
            (max(64, full_size[0] // work_scale), max(64, full_size[1] // work_scale)),
            Image.LANCZOS)
    rgb = np.asarray(img.convert("RGB"))
    h, w = rgb.shape[:2]
    if ring_px is None:
        ring_px = max(10, int(round(min(h, w) * 0.02)))
    ring = np.zeros((h, w), bool)
    ring[:ring_px, :] = ring[-ring_px:, :] = True
    ring[:, :ring_px] = ring[:, -ring_px:] = True

    lab = lab_chunked(rgb)
    L = lab[..., 0]
    tex = texture_map(L)

    # two luminance modes inside the frame ring, split by Otsu
    t = _otsu(L[ring])
    modes = []
    for name, gm in (("dark", L[ring] <= t), ("bright", L[ring] > t)):
        if gm.sum() < 50:
            continue
        px = rgb[ring][gm]
        med = np.median(px, axis=0).astype(np.float32)
        p_lab = rgb_to_lab(med[None, :])[0]
        tex_med = float(np.median(tex[ring][gm]))
        modes.append({"mode": name, "rgb": [int(round(v)) for v in med],
                      "lab": p_lab, "tex": tex_med, "frac": float(gm.mean())})
    if not modes:
        raise ValueError("paper_background_mask: no ring modes")
    modes.sort(key=lambda m: m["tex"])
    pick = modes[0]
    if pick["frac"] < 0.10 and len(modes) > 1:
        pick = modes[1]

    p0 = pick["lab"]
    dC = np.linalg.norm(lab[..., 1:] - p0[1:], axis=-1)
    # threshold population = ring pixels belonging to the chosen mode
    sel = ring & (np.abs(L - p0[0]) < 25)
    if sel.sum() < 200:
        sel = ring
    t_c = float(np.clip(np.percentile(dC[sel], 92), 0.8, 4.0))
    t_t = float(np.clip(np.percentile(tex[sel], 92), 0.5, 3.0))
    # L floor from the CORE of the paper population, not its outlier tail:
    # a shadowed transition band is darker than this and must stay garment-side.
    L_med = float(np.median(L[sel]))
    L_floor = float(max(0.0, np.percentile(L[sel], 10) - 2.0))

    paper_like = (dC <= t_c) & (tex <= t_t) & (L >= L_floor)
    paper_like = ndimage.binary_opening(paper_like, np.ones((3, 3)))

    # §131 (labots 2026-10-25): ja kadrā tomēr nav NEVIENA papīram līdzīga
    # pikseļa (pilnkadra makro ar "pieņemu" kandidātu riņķī), procentiles
    # zemāk avarēja uz tukša masīva. Tukšs rezultāts nozīmē to pašu, ko
    # measure_paper_colour atteikšanās: papīra nav — atgriežam atteikšanos.
    if not paper_like.any():
        return {"refused": True,
                "reason": "papīram līdzīgu pikseļu nav (pēc atvēršanas)",
                "peak": pick,
                "fg_coverage": None}

    # A shadow band next to the fabric is smooth and paper-coloured, so colour
    # alone cannot reject it. It can, however, be rejected by construction:
    # real paper is reachable from the frame border through paper pixels
    # WITHOUT crossing a step in luminance. Flood through a gradient-limited
    # graph instead of accepting every paper-like island.
    gy, gx = np.gradient(L)
    grad = np.hypot(gx, gy)
    g_t = float(np.clip(np.percentile(grad[paper_like], 90), 0.5, 6.0))
    passable = paper_like & (grad <= g_t)
    seed = np.zeros((h, w), bool)
    seed[0, :] = passable[0, :]
    seed[-1, :] = passable[-1, :]
    seed[:, 0] = passable[:, 0]
    seed[:, -1] = passable[:, -1]
    reached = ndimage.binary_propagation(seed, mask=passable) if seed.any() else paper_like
    paper_like = reached
    # background must be reachable from the frame border
    lbl, n = ndimage.label(paper_like)
    border_ids = np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))
    border_ids = border_ids[border_ids > 0]
    background = np.isin(lbl, border_ids)
    if background.sum() == 0:
        background = paper_like
    # drop specks
    lbl2, n2 = ndimage.label(background)
    if n2:
        sizes = np.bincount(lbl2.ravel())[1:]
        keep = np.flatnonzero(sizes >= max(200, int(2e-4 * h * w))) + 1
        background = np.isin(lbl2, keep)

    # ---- shadow model -------------------------------------------------
    # A shadow on paper is not "darker paper": it is the SAME paper under less
    # light. So compare each pixel with the paper it stands on, not with a
    # global brightness: ratio = L* / L*(nearest paper pixel).
    #   shadowed paper : ratio 0.5 - 0.98, paper chroma, paper smoothness
    #   garment        : ratio outside that band, or different chroma/texture
    # The 0.5 floor is physical: an indoor cast shadow on white paper is rarely
    # darker than half the lit value. It is reported, so it can be challenged.
    fg = ~background
    dist_bg, (iy, ix) = ndimage.distance_transform_edt(
        fg, return_indices=True)
    L_parent = L[iy, ix]                      # brightness of the paper it sits on
    ratio = np.divide(L, np.maximum(L_parent, 1e-3),
                      out=np.ones_like(L), where=L_parent > 1e-3)

    max_band = max(40.0, 0.05 * min(h, w))    # how far a shadow may reach
    near = dist_bg <= max_band
    cand = (fg & near & (dC <= t_c) & (tex <= t_t)
            & (ratio >= 0.50) & (ratio < 0.98))
    cand = ndimage.binary_opening(cand, np.ones((5, 5)))

    # a shadow must be attached to the real paper, not float inside the garment
    lbl_c, n_c = ndimage.label(cand)
    keep = np.zeros(n_c + 1, bool)
    if n_c:
        touch = np.unique(lbl_c[ndimage.binary_dilation(background, np.ones((9, 9))) & cand])
        keep[touch[touch > 0]] = True
        sz = np.bincount(lbl_c.ravel())[1:]
        enough = sz >= max(400, int(2e-3 * h * w))
        keep[1:] &= enough
    shadow = keep[lbl_c] if n_c else cand

    # and it must be smooth in ratio: a ratio cliff means a fabric edge, not light
    if shadow.any():
        gry, grx = np.gradient(ratio)
        grd = np.hypot(grx, gry)
        r_t = float(np.clip(np.percentile(grd[shadow], 85), 0.02, 0.30))
        core_s = shadow & (grd <= r_t)
        if core_s.any():
            grown = ndimage.binary_propagation(
                core_s, mask=shadow & (grd <= r_t * 1.6))
            shadow = grown
    else:
        r_t = 0.0

    background = background | shadow
    fg = ~background
    del dist_bg, iy, ix, L_parent, ratio, near, cand, lbl_c

    background = background | shadow

    if work_scale > 1:
        big = Image.fromarray((background * 255).astype(np.uint8)).resize(
            full_size, Image.BILINEAR)
        background = np.asarray(big) >= 128
        # one closing pass removes the upsampling fringe without moving the edge
        background = ndimage.binary_closing(background, np.ones((3, 3)))
    fg = ~background
    shadow_full = int(round(shadow.sum() * (work_scale ** 2)))
    return {
        "background": background,
        "shadow_px": shadow_full,
        "shadow_pct_of_fg": round(100.0 * shadow_full / max(1, int(fg.sum()) + shadow_full), 3),
        "shadow_ratio_band": [0.50, 0.98],
        "shadow_ratio_grad_t": round(float(r_t), 3),
        "fg_coverage": round(float(fg.mean()), 4),
        "paper_rgb": pick["rgb"],
        "mode": pick["mode"],
        "thresholds": {"dC": round(t_c, 3), "tex": round(t_t, 3),
                       "L_floor": round(L_floor, 2), "L_med": round(L_med, 2),
                       "grad": round(g_t, 3)},
        "refused": False,
        "work_scale": int(work_scale),
        "ring_px": int(ring.sum()),
        "lab": lab, "tex": tex,
    }
