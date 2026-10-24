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
     (rāvējslēdzējs, birka) paliek apģērbs. Plūdi drīkst iet arī
     caur tumšās zonas nedrošajiem pikseļiem — ēnas līčiem, kurus
     krāsa viena pati neatšķir (sk. `_dark_uncertain`, §78).
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


def _local_std(a: np.ndarray, win: int) -> np.ndarray:
    mu = cv2.boxFilter(a, -1, (win, win))
    mu2 = cv2.boxFilter(a * a, -1, (win, win))
    return np.sqrt(np.maximum(mu2 - mu * mu, 0))


def _dark_uncertain(lab: np.ndarray, a_bg: np.ndarray, fg_seed: np.ndarray,
                    fg_centers: np.ndarray, bg_centers: np.ndarray,
                    cfg: dict) -> tuple[np.ndarray | None, dict]:
    """Tumšās zonas nedrošie pikseļi: ēnas līču izšķīrējs (PROGRESS §78).

    Dziļā ēnā abu klašu krāsas sabrūk gandrīz melnā neitrālā un galvenā
    palete līci kļūdaini sauc par apģērbu (izmērīts 122248: līcis Lab
    [6.5, 3.2, 2.6]; FG centrs 7.2, BG 16.7 — jo BG paletē dziļās ēnas
    parauga nav: sēklu atlase to bija izslēgusi). Otrais piegājiens
    būvē TUMŠĀS paletes no tumšajām sēklām (fona pusei — zema alfa +
    nokrāsa (a*,b*) tuvāk fona paletei; tā ēnainais fons beidzot tiek
    paraugots), attīra sakrītošus centrus un atzīmē kā nedrošus tos
    tumšos pikseļus, kurus tumšais lauks pārliecinoši nesauc par
    apģērbu UN kuru tekstūra ir fona ēnai līdzīga. Nedrošs nenozīmē
    fons: par fonu tie kļūst tikai, ja plūdi no kadra malas tos
    sasniedz caur nedrošo zonu (līcis); ieslēgti tumši auduma laukumi
    (rāvējslēdzējs, odere) paliek apģērbs.

    Atgriež (uncertain|None, info). None = piegājiens sevi izslēdz
    (par maz sēklu / paletes neatdalās / sēklu robeža vāja) un maska
    paliek pirmā piegājiena — nekad sliktāka par to.
    """
    info: dict = {"dark_pass": False}
    L = lab[..., 0]
    dark = L <= float(cfg["dark_L"])
    if not dark.any():
        info["dark_reason"] = "nav tumšo pikseļu"
        return None, info
    # nokrāsu (bez L) attālumi fona ēnas sēklu atlasei
    lab_ab = lab.copy()
    lab_ab[..., 0] = 0.0
    fg_ab = fg_centers.copy()
    fg_ab[:, 0] = 0.0
    bg_ab = bg_centers.copy()
    bg_ab[:, 0] = 0.0
    dab_f = _distance_map(lab_ab, fg_ab)
    dab_b = _distance_map(lab_ab, bg_ab)
    del lab_ab
    bg_dark_seed = dark & (a_bg <= 0.10) & (dab_b < dab_f)
    fg_dark_seed = dark & fg_seed
    info["dark_bg_seed_px"] = int(bg_dark_seed.sum())
    info["dark_fg_seed_px"] = int(fg_dark_seed.sum())
    min_seeds = max(200, int(float(cfg["dark_seed_min_frac"]) * L.size))
    if bg_dark_seed.sum() < min_seeds or fg_dark_seed.sum() < min_seeds:
        info["dark_reason"] = "par maz tumšo sēklu"
        return None, info
    k = int(cfg["dark_palette_k"])
    bgd, _ = _median_cut_palette(lab[bg_dark_seed], k)
    fgd, _ = _median_cut_palette(lab[fg_dark_seed], k)
    # savstarpēja attīrīšana: centrs, kas sakrīt ar otras klases
    # centru, ir divdomīgs (arī paletes piesārņojums) — ārā abi
    cross = np.linalg.norm(fgd[:, None, :] - bgd[None, :, :], axis=2)
    pur = float(cfg["dark_min_cross_dE"])
    fgd = fgd[cross.min(axis=1) >= pur]
    bgd = bgd[cross.min(axis=0) >= pur]
    info["dark_fg_centers_lab"] = np.round(fgd, 1).tolist()
    info["dark_bg_centers_lab"] = np.round(bgd, 1).tolist()
    if len(fgd) == 0 or len(bgd) == 0:
        info["dark_reason"] = "tumšās paletes sakrīt"
        return None, info
    d_fd = _distance_map(lab, fgd)
    d_bd = _distance_map(lab, bgd)
    ratio_min = float(cfg["seed_margin_ratio_min"])
    fg_own = float(np.median(d_fd[fg_dark_seed]))
    fg_oth = float(np.median(d_bd[fg_dark_seed]))
    bg_own = float(np.median(d_bd[bg_dark_seed]))
    bg_oth = float(np.median(d_fd[bg_dark_seed]))
    info.update({"dark_fg_own_med": round(fg_own, 2),
                 "dark_fg_other_med": round(fg_oth, 2),
                 "dark_bg_own_med": round(bg_own, 2),
                 "dark_bg_other_med": round(bg_oth, 2)})
    if (fg_oth < ratio_min * max(fg_own, 1e-6)
            or bg_oth < ratio_min * max(bg_own, 1e-6)):
        info["dark_reason"] = "tumšo sēklu robeža vāja"
        return None, info
    field_dark = cv2.GaussianBlur(d_bd - d_fd, (0, 0),
                                  sigmaX=float(cfg["margin_sigma"]))
    del d_fd, d_bd
    e7 = _local_std(L, 7)
    e_bg_med = float(np.median(e7[bg_dark_seed]))
    info["dark_bg_tex_med"] = round(e_bg_med, 3)
    uncertain = (dark & (field_dark < float(cfg["dark_uncertain_field"]))
                 & (e7 < float(cfg["dark_tex_ratio"]) * e_bg_med))
    info["dark_pass"] = True
    return uncertain, info


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

    def _flood_bg(trav: np.ndarray) -> np.ndarray:
        """Ar kadra malu savienotā traversējamā zona = fons."""
        _, cc, _, _ = cv2.connectedComponentsWithStats(
            trav.astype(np.uint8), connectivity=8)
        border_labels = (set(cc[0, :]) | set(cc[-1, :])
                         | set(cc[:, 0]) | set(cc[:, -1])) - {0}
        if not border_labels:
            return np.zeros_like(cls_fg)
        return np.isin(cc, list(border_labels))

    # Otrais piegājiens: plūdi drīkst iet arī caur tumšās zonas
    # nedrošajiem pikseļiem (ēnas līči). Drošinātājs: izgrebums no
    # pirmā piegājiena GALVENĀS komponentes (paša apģērba) drīkst būt
    # tikai neliels — atsevišķu fona pleķu aizvākšana neskaitās, tie
    # maskā tāpat nenonāktu (clean_mask ņem lielāko komponenti).
    uncertain, dark_info = _dark_uncertain(
        lab, a_bg, fg_seed, fg_centers, bg_centers, _C)
    qa.update(dark_info)
    bg = None
    if uncertain is not None:
        bg_first = _flood_bg(~cls_fg)
        first = ~bg_first
        n1, cc1, st1, _ = cv2.connectedComponentsWithStats(
            first.astype(np.uint8), connectivity=8)
        if n1 > 1:
            largest1 = cc1 == (1 + int(np.argmax(st1[1:, cv2.CC_STAT_AREA])))
        else:
            largest1 = first
        bg_try = _flood_bg((~cls_fg) | uncertain)
        carve = bg_try & largest1
        qa["dark_carve_px"] = int((bg_try & cls_fg).sum())
        qa["dark_carve_garment_px"] = int(carve.sum())
        if carve.sum() <= float(_C["dark_carve_max_frac"]) * max(int(largest1.sum()), 1):
            bg = bg_try
        else:
            qa["dark_pass"] = False
            qa["dark_reason"] = "izgrebums par lielu"
        del bg_try, carve, bg_first, first, largest1
    if bg is None:
        bg = _flood_bg(~cls_fg)
    m = (~bg).astype(np.uint8)
    del bg, cls_fg
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
