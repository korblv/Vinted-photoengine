"""Krāsu-attāluma (chroma) rezerves ceļš: sēklu paletes CIE Lab telpā.

Kāpēc tas eksistē: masku ķēde (ISNet -> apmales retry -> plate) ir būvēta
papīra fonam. Uz NE-papīra fona (koka grīda, PROGRESS §74-§75) visi papīra
instrumenti saka blēņas: papīra krāsas novērtējums atrod "papīru" tur, kur
tā nav, aizsargi (overflow/uncovered) kļūst bezjēdzīgi, un ISNet
metāliskiem audumiem slīpos kadros dod fragmentētas maskas. Bet tādās
ainās bieži ir CITS spēcīgs signāls: apģērbs un fons krāsā atšķiras tālu
(zila metāliska pufjaka pret siltu koku: b* ap -30 pret +20).

Metode (deterministiska, bez modeļa un bez RNG):
  1. Sēklas no ISNet mīkstās maskas: priekšplāns = augstas alfas kodols
     (eroģēts, tāpēc plāna pārplūde uz fona sēklās neiekļūst); fons =
     kadra malas gredzens, no kura IZMESTI pikseļi, kas krāsā tuvi
     priekšplāna paletei (apģērbs drīkst pieskarties malām — tīrā
     gredzena palete tāpēc neder; prototips #1, segums 0.0, §76).
  2. Abām klasēm mediān-griezuma (median-cut) Lab palete. Mediān-
     griezums, nevis k-means: reproducējams līdz bitam bez RNG.
  3. Klasifikācija pēc tuvākās paletes (deltaE76), malas lauks
     izlīdzināts ar Gausu; fons = ar kadra malu savienotās fona
     komponentes (plūdu princips), tāpēc ieslēgti tumši laukumi
     (rāvējslēdzējs, birka) paliek apģērbs.
  4. QA ir daļa no funkcijas: ceļš sevi NORAIDA, ja paletes pārklājas
     (min. savstarpējais deltaE), ja sēklas nestāv pārliecinoši tuvāk
     savai paletei, ja pārāk daudz pikseļu ir abu palešu vidū vai ja
     siluets nav strukturāli vesels. Noraidījums = atgriešanās pie
     STOP-eskalācijas, nevis kompromiss.

Tas ir REZERVES ceļš: to izsauc tikai, kad esošā ķēde masku nav devusi
vai kandidāts neiztur strukturālo QA (sk. `engine.masks`).
"""
import time

import cv2
import numpy as np
from PIL import Image

from loop import clean_mask  # noqa: E402

from engine.config import CFG  # noqa: E402


def _median_cut_palette(samples: np.ndarray, k: int,
                        max_samples: int = 50_000) -> tuple[np.ndarray, list[float]]:
    """Deterministiska palete: atkārtoti dala lielākā diapazona spaini
    pie mediānas. Centrs = spaiņa per-kanāla mediāna (izturīga pret
    atsevišķiem spīdumu/melno pikseļu izlecošajiem)."""
    s = np.asarray(samples, np.float32).reshape(-1, 3)
    if len(s) == 0:
        return np.zeros((0, 3), np.float32), []
    if len(s) > max_samples:
        s = s[::int(np.ceil(len(s) / max_samples))]
    buckets = [s]
    while len(buckets) < k:
        ranges = [float((b.max(axis=0) - b.min(axis=0)).max()) if len(b) > 1 else -1.0
                  for b in buckets]
        i = int(np.argmax(ranges))
        if ranges[i] <= 0 or len(buckets[i]) < 40:
            break
        b = buckets.pop(i)
        ch = int(np.argmax(b.max(axis=0) - b.min(axis=0)))
        b = b[np.argsort(b[:, ch], kind="mergesort")]
        mid = len(b) // 2
        buckets.extend([b[:mid], b[mid:]])
    centers, supports = [], []
    min_support = max(20, int(0.005 * len(s)))
    for b in buckets:
        if len(b) >= min_support:
            centers.append(np.median(b, axis=0))
            supports.append(round(float(len(b) / len(s)), 4))
    if not centers:  # visas kaudzes sīkas: viens kopējais mediānas centrs
        return np.median(s, axis=0, keepdims=True).astype(np.float32), [1.0]
    return np.asarray(centers, np.float32), supports


def _distance_map(lab: np.ndarray, centers: np.ndarray) -> np.ndarray:
    """Attālums (deltaE76) līdz tuvākajam paletes centram; gabalos, lai
    pusmēroga karte neizēstu RAM starpproduktos."""
    flat = lab.reshape(-1, 3).astype(np.float32)
    out = np.empty(len(flat), np.float32)
    for i in range(0, len(flat), 250_000):
        ch = flat[i:i + 250_000]
        out[i:i + 250_000] = np.linalg.norm(
            ch[:, None, :] - centers[None], axis=2).min(axis=1)
    return out.reshape(lab.shape[:2])


def structural_qa(binary: np.ndarray) -> dict:
    """Kandidāta strukturālais veselums — tās pašas četras īpašības,
    kuras neatkarīgais checker vērtē GATE_C (00 dokuments §5): segums
    0.15-0.98, lielākā komponente >= 0.95, silueta aizpildījums >= 0.55,
    neviens ieslēgts caurums >= 400 px. Maker to izmanto tikai kā
    TRIGERI rezerves ceļam un kā chroma pieņemšanas daļu; vārtu
    sliekšņus tas nemaina un checker paliek tiesnesis."""
    from scipy import ndimage

    m = (binary > 0).astype(np.uint8)
    cov = float(m.mean())
    out = {"coverage": round(cov, 4), "largest_ratio": 0.0,
           "silhouette_fill": 0.0, "interior_holes_ge400": 0,
           "interior_holes_px": 0, "accept": False}
    if not m.any():
        return out
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n <= 1:
        return out
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    largest = lab == idx
    out["largest_ratio"] = round(float(largest.sum() / m.sum()), 4)
    ys, xs = np.where(largest)
    out["silhouette_fill"] = round(float(
        largest.sum() / ((xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1))), 4)
    holes = ndimage.binary_fill_holes(largest) & ~largest
    if holes.any():
        hl, hn = ndimage.label(holes)
        sizes = ndimage.sum(holes, hl, range(1, hn + 1))
        out["interior_holes_ge400"] = int((sizes >= 400).sum())
        out["interior_holes_px"] = int(sizes.sum())
    out["accept"] = bool(
        0.15 <= cov <= 0.98
        and out["largest_ratio"] >= 0.95
        and out["silhouette_fill"] >= 0.55
        and out["interior_holes_ge400"] == 0)
    return out


def chroma_mask(orig: Image.Image, softs: list[np.ndarray]) -> tuple[np.ndarray, dict]:
    """Maska no krāsu attāluma. `softs` — ISNet mīkstās maskas (0-255,
    jebkādā izšķirtspējā); ar vairākām (bāze + apmales retry) priekšplāna
    pārliecība ir max, fona pārliecība min — sēklai abām jāpiekrīt.
    Atgriež (binary uint8 oriģināla izmērā, qa ar accept/reason)."""
    from paper_leak import lab_chunked

    _C = CFG["chroma"]
    t = time.perf_counter()
    W, H = orig.size
    scale = int(_C["scale"])
    sw, sh = max(64, W // scale), max(64, H // scale)
    qa: dict = {"accept": False}

    def fail(reason: str):
        qa["reason"] = reason
        qa["seconds"] = round(time.perf_counter() - t, 2)
        return np.zeros((H, W), np.uint8), qa

    if not softs:
        return fail("nav ISNet sēklu maskas")
    resized = []
    for s in softs:
        pim = Image.fromarray(np.asarray(s).astype(np.uint8)).resize(
            (sw, sh), Image.BILINEAR)
        resized.append(np.asarray(pim, np.float32) / 255.0)
    a_fg = np.max(resized, axis=0)
    a_bg = np.min(resized, axis=0)
    del resized

    lab = lab_chunked(np.asarray(
        orig.convert("RGB").resize((sw, sh), Image.LANCZOS))).astype(np.float32)

    # --- priekšplāna sēklas: augstas alfas kodols ---
    dist_in = cv2.distanceTransform(
        (a_fg >= _C["fg_core_alpha"]).astype(np.uint8), cv2.DIST_L2, 5)
    fg_seed = (a_fg >= _C["fg_alpha"]) & (dist_in >= _C["fg_core_dist_px"])
    qa["fg_seed_fraction"] = round(float(fg_seed.mean()), 4)
    if fg_seed.sum() < 0.005 * sw * sh:
        return fail(f"priekšplāna sēklu par maz ({int(fg_seed.sum())} px)")
    fg_centers, fg_supports = _median_cut_palette(lab[fg_seed], int(_C["palette_k"]))
    d_fg = _distance_map(lab, fg_centers)

    # --- fona sēklas: malas gredzens MINUS priekšplānam līdzīgie ---
    ring_w = max(6, int(round(0.01 * min(sw, sh))))
    ring = np.zeros((sh, sw), bool)
    ring[:ring_w] = ring[-ring_w:] = True
    ring[:, :ring_w] = ring[:, -ring_w:] = True
    margin = float(_C["seed_margin_dE"])
    border_seed = ring & (a_bg <= _C["border_alpha_max"]) & (d_fg >= margin)
    qa["border_seed_px"] = int(border_seed.sum())
    if border_seed.sum() < 2000:
        return fail(f"fona sēklu pie malas par maz ({int(border_seed.sum())} px)")
    bg_centers0, _ = _median_cut_palette(lab[border_seed], int(_C["palette_k"]))
    d_bg0 = _distance_map(lab, bg_centers0)
    # Papildini ar globāli drošu fonu, kas jau līdzinās malas paletei:
    # fona krāsa perspektīvā mainās, malas gredzens to visu neredz.
    bg_seed = border_seed | ((a_bg <= 0.10) & (d_fg >= margin)
                             & (d_bg0 <= _C["bg_refine_dE"]))
    del d_bg0
    bg_centers, bg_supports = _median_cut_palette(lab[bg_seed], int(_C["palette_k"]))
    qa["bg_seed_fraction"] = round(float(bg_seed.mean()), 4)
    qa["fg_centers_lab"] = np.round(fg_centers, 1).tolist()
    qa["bg_centers_lab"] = np.round(bg_centers, 1).tolist()
    qa["fg_supports"] = fg_supports
    qa["bg_supports"] = bg_supports

    # --- palešu atdalāmība: ceļa eksistences nosacījums ---
    cross = np.linalg.norm(fg_centers[:, None, :] - bg_centers[None, :, :], axis=2)
    qa["min_cross_dE"] = round(float(cross.min()), 2)
    if cross.min() < _C["min_cross_dE"]:
        return fail(f"paletes pārklājas (min. savstarpējais dE "
                    f"{float(cross.min()):.1f} < {_C['min_cross_dE']})")

    d_bg = _distance_map(lab, bg_centers)
    fg_own = float(np.median(d_fg[fg_seed]))
    fg_other = float(np.median(d_bg[fg_seed]))
    bg_own = float(np.median(d_bg[bg_seed]))
    bg_other = float(np.median(d_fg[bg_seed]))
    qa.update({
        "fg_seed_own_dE_med": round(fg_own, 2),
        "fg_seed_other_dE_med": round(fg_other, 2),
        "bg_seed_own_dE_med": round(bg_own, 2),
        "bg_seed_other_dE_med": round(bg_other, 2),
    })
    ratio_min = float(_C["seed_margin_ratio_min"])
    if fg_other < ratio_min * max(fg_own, 1e-6) or bg_other < ratio_min * max(bg_own, 1e-6):
        return fail("sēklas nestāv pārliecinoši tuvāk savai paletei")

    # --- klasifikācija + plūdu princips ---
    field = cv2.GaussianBlur(d_bg - d_fg, (0, 0),
                             sigmaX=float(_C["margin_sigma"]))
    del d_bg, d_fg
    qa["ambiguous_fraction"] = round(float((np.abs(field) < 5.0).mean()), 4)
    if qa["ambiguous_fraction"] > _C["max_ambiguous_fraction"]:
        return fail(f"pārāk daudz divdomīgo pikseļu "
                    f"({qa['ambiguous_fraction']} > {_C['max_ambiguous_fraction']})")
    cls_fg = field > 0
    cls_fg[fg_seed] = True
    cls_fg[border_seed] = False
    del field
    n, cc, _, _ = cv2.connectedComponentsWithStats(
        (~cls_fg).astype(np.uint8), connectivity=8)
    border_labels = (set(cc[0, :]) | set(cc[-1, :])
                     | set(cc[:, 0]) | set(cc[:, -1])) - {0}
    bg = np.isin(cc, list(border_labels)) if border_labels else np.zeros_like(cls_fg)
    m = (~bg).astype(np.uint8)
    del cc, bg, cls_fg
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    up = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize(
        (W, H), Image.LANCZOS))
    binary = clean_mask(up, threshold=128, erode_px=1)
    st = structural_qa(binary)
    qa.update({f"struct_{k}": v for k, v in st.items() if k != "accept"})
    if not st["accept"]:
        return fail(f"siluets nav strukturāli vesels ({st})")
    qa["accept"] = True
    qa["reason"] = "krāsu palešu QA"
    qa["seconds"] = round(time.perf_counter() - t, 2)
    return binary, qa
