"""Krāsu grade: sRGB pārveides, LUT būve un pielietojums, profils.

Izņemts no workflow_v2.py solī 6.3; funkciju ķermeņi nemainīti
(AST hash Pierādījums, PROGRESS §63).
"""
import cv2
import numpy as np
from PIL import Image

from engine.config import CFG  # noqa: E402
from engine.infra import fit_size, open_rgb_recorded  # noqa: E402

def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float64) / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055) * 255.0


def build_lut(gains: np.ndarray, exposure: float, curve_blend: float = 0.18,
              highlight_knee: float = 0.86) -> list[np.ndarray]:
    base = np.arange(256, dtype=np.float64)
    lut = []
    for ch in range(3):
        y = linear_to_srgb(srgb_to_linear(base) * float(gains[ch])) / 255.0
        y = y * float(exposure)
        # Filmisks gaišo toņu plecs: paceļ vidējos toņus, bet baltā auduma
        # detaļas netiek masveidā nogrieztas pie 255.
        z = np.maximum(y - highlight_knee, 0.0) / (1.0 - highlight_knee)
        y = np.where(
            y > highlight_knee,
            highlight_knee + (1.0 - highlight_knee) * (1.0 - 1.0 / (1.0 + z * 1.8)),
            y,
        )
        y = np.clip(y, 0.0, 1.0)
        smooth = y * y * (3.0 - 2.0 * y)
        y = (1.0 - curve_blend) * y + curve_blend * smooth
        lut.append(np.clip(np.rint(y * 255.0), 0, 255).astype(np.uint8))
    return lut


def _sample_clipping(samples_by_stem: dict[str, np.ndarray], lut: list[np.ndarray]) -> dict[str, float]:
    out = {}
    for stem, samples in samples_by_stem.items():
        if len(samples) == 0:
            out[stem] = 0.0
            continue
        graded = np.stack([lut[ch][samples[:, ch]] for ch in range(3)], axis=1)
        out[stem] = round(float((((graded <= 2) | (graded >= 253)).any(axis=1)).mean() * 100), 4)
    return out


def compute_grade_profile(records: list[dict], wb_mode: str = "auto") -> dict:
    """Viens Lightroom tipa profils visam komplektam.

    WB novērtē no neitrāliem, no apģērba attāliem fona pikseļiem, bet
    neitralizē tikai daļēji, jo mājas papīrs/galds pats var būt silts un
    produkta krēmkrāsa nedrīkst kļūt mākslīgi balta/zila. Pēc sākotnējā
    LUT vēl veic parauga clipping pārbaudi un, ja nepieciešams, automātiski
    nedaudz samazina ekspozīciju.
    """
    bg_medians = []
    garment_p99 = []
    garment_p50 = []
    core_samples: dict[str, np.ndarray] = {}
    for rec in records:
        orig_full = open_rgb_recorded(rec["source"], rec.get("rotation_cw"))
        size = fit_size(orig_full.width, orig_full.height, 768, 1024)
        rgb = np.asarray(orig_full.resize(size, Image.LANCZOS))
        del orig_full
        mask = np.asarray(Image.open(rec["mask_path"]).convert("L").resize(size, Image.NEAREST)) > 128
        dist_out = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5)
        lum = rgb.mean(axis=2)
        sat = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
        bg = (dist_out > 18) & (lum >= 70) & (lum <= 245) & (sat <= 38)
        if bg.sum() > 5000:
            bg_medians.append(np.median(rgb[bg].astype(np.float64), axis=0))
        dist_in = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
        core = dist_in > 8
        if core.sum() > 5000:
            vals = lum[core]
            garment_p50.append(float(np.percentile(vals, 50)))
            garment_p99.append(float(np.percentile(vals, 99)))
            samples = rgb[core]
            stride = max(1, len(samples) // 50_000)
            core_samples[rec["stem"]] = samples[::stride].copy()
        del rgb, mask, dist_out, dist_in, lum, sat, bg, core

    bg_median = np.median(np.stack(bg_medians), axis=0) if bg_medians else np.array([180.0, 175.0, 165.0])
    # Vai fons vispār ir KRĀSU etalons? Koka grīda (rūgtā brūnā) nav.
    # Baltā bilance no brūnas virsmas atņem no zilā auduma 4.9 b* vienības —
    # tieši to parādīja šī komplekta pirmā bilde.
    fbg = srgb_to_linear(bg_median)
    _G = CFG["grade"]  # visi grade parametri: config.toml [grade] (solis 4)
    bg_chroma = float(np.max(fbg) - np.min(fbg)) / max(float(np.mean(fbg)), 1e-6)
    wb_trusted = bool(bg_chroma <= _G["wb_chroma_max"])
    wb_note = ("fons ir neitrāls -> WB no fona" if wb_trusted else
               f"fons ir krāsains (hroma {bg_chroma:.2f} > {_G['wb_chroma_max']}) -> WB neitrāla, "
               "citādi audums iegūst viltus aukstumu")
    bg_linear = srgb_to_linear(bg_median)
    gains = float(bg_linear.mean()) / np.maximum(bg_linear, 1e-9)
    gains = gains / gains[1]
    gains = np.exp(np.log(np.maximum(gains, 1e-9)) * _G["wb_shrink"])
    gains = np.clip(gains, _G["gain_clip_min"], _G["gain_clip_max"])
    if wb_mode == "identity" or not wb_trusted:
        gains = np.ones(3, np.float64)

    p99 = float(np.median(garment_p99)) if garment_p99 else 240.0
    p50 = float(np.median(garment_p50)) if garment_p50 else 180.0
    exposure = float(np.clip(_G["exposure_target"] / max(p99, 1.0),
                             _G["exposure_min"], _G["exposure_max"]))
    curve_blend = _G["curve_blend"]
    highlight_knee = _G["highlight_knee"]
    lut = build_lut(gains, exposure, curve_blend, highlight_knee)
    clipping = _sample_clipping(core_samples, lut)
    adjustments = 0
    while (clipping and max(clipping.values()) > _G["clipping_limit_pct"]
           and exposure > _G["exposure_min"]
           and adjustments < _G["exposure_max_adjustments"]):
        exposure = max(_G["exposure_min"], exposure - _G["exposure_step"])
        lut = build_lut(gains, exposure, curve_blend, highlight_knee)
        clipping = _sample_clipping(core_samples, lut)
        adjustments += 1

    return {
        "version": "workflow_v2_grade_3_auto_clipping_guard",
        "background_median_rgb": [round(float(v), 3) for v in bg_median],
        "wb_gains_linear_rgb": [round(float(v), 6) for v in gains],
        "background_chroma": round(bg_chroma, 4),
        "wb_trusted": wb_trusted,
        "wb_note": wb_note,
        "garment_luminance_p50_median": round(p50, 3),
        "garment_luminance_p99_median": round(p99, 3),
        "exposure_factor": round(exposure, 6),
        "exposure_auto_adjustments": adjustments,
        "sample_clipped_core_pct": clipping,
        "highlight_rolloff_knee": highlight_knee,
        "contrast_smoothstep_blend": curve_blend,
        "output_sharpen": {"radius": _G["sharpen_radius"],
                           "percent": _G["sharpen_percent"],
                           "threshold": _G["sharpen_threshold"]},
        "lut_rgb": [list(map(int, row)) for row in lut],
    }


def apply_lut(rgb: np.ndarray, lut_rows) -> np.ndarray:
    out = np.empty_like(rgb)
    for ch in range(3):
        table = np.asarray(lut_rows[ch], dtype=np.uint8).reshape(256, 1)
        out[:, :, ch] = cv2.LUT(rgb[:, :, ch], table)
    return out
