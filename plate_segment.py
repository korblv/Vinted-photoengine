"""Plakanās plāksnes segmentācija — kad ISNet neredz apģērbu.

Kāpēc tas pastāv
----------------
ISNet ir *semantiskais* (saliency) modelis: tas meklē atpazīstamu objektu.
Uz šīs bildes (`PXL_20261022_124339475`) tas atrada tikai gludās aproces,
jo balts vafeles adījums uz gaiši pelēka kartona tam nešķiet nekas. Segums
3.1 % pret vajadzīgo ~70 %.

Bet bilde pati satur daudz spēcīgāku signālu: **virszemes faktūru**. Mērīts:

    lokālais L* std, pusizmērs, logs 25 px
        kartons   ~ 2.8      (vienmērīgs, izotrops grauds)
        vafeles adījums ~ 12.8 (periodisks, virzīts reljefs)
        Otsu slieksnis   7.6   — tieši starp abiem, atstarpe 4.5x

Šī atšķirība ir mēroga lieta: pilnā izšķirtspējā kartona grauds ir tikpat
enerģisks kā adījums (5.0 pret 5.0), tāpēc detektors strādā **pusizmērā**,
kur 2x samazināšana nesakorelēto graudu noslāpē, bet korelēto adījumu ne.

Principi, kas tiek ievēroti
---------------------------
1. Nekas netiek izdomāts: maska nāk no izmērīta signāla, ne no modeļa fantāzijas.
2. Fons = viss, kas savienots ar kadra malu. Tāpēc īstie robi starp aproci un
   kleitu paliek robi, bet aproces iekšpuse (slēgts apgabals) paliek krekls.
3. Mala tiek izlīdzināta (kontūras vidējais), jo 25 px logs dod ~10 px
   viļņainību; izlīdzināšana nesamazina segumu vairāk par ~1 %.
4. Sliekšņi ir mērīti (Otsu + starpība starp fona un auduma līmeņiem), nevis
   pielāgoti acij.
"""

from __future__ import annotations

import numpy as np
import cv2
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion, gaussian_filter

try:
    from paper_leak import lab_chunked
except Exception:  # pragma: no cover - ļauj lietot moduli atsevišķi
    from .paper_leak import lab_chunked


def _local_std(L: np.ndarray, win: int) -> np.ndarray:
    mu = cv2.boxFilter(L, -1, (win, win))
    mu2 = cv2.boxFilter(L * L, -1, (win, win))
    return np.sqrt(np.maximum(mu2 - mu * mu, 0))


def _paper_level(L: np.ndarray, m: np.ndarray) -> tuple[float, float]:
    """Papīra L* un tekstūras līmenis no malas gredzena (tikai gludie px)."""
    h, w = L.shape
    ring = np.zeros((h, w), bool)
    s = max(4, int(0.012 * min(h, w)))
    ring[:s, :] = ring[-s:, :] = True
    ring[:, :s] = ring[:, -s:] = True
    ring &= (m == 0)
    if ring.sum() < 200:
        return float(np.median(L)), float("inf")
    E = _local_std(L, 25)
    smooth = ring & (E <= np.percentile(E[ring], 40))
    if smooth.sum() < 100:
        smooth = ring
    return float(np.median(L[smooth])), float(np.median(E[smooth]))


# Krāsu tolerance pret papīra L*. Izmērīta uz `PXL_20261022_124339475`:
#   -18 -> paliek viltus caurums (ēnots audums L* 51.5 pie papīra 66.8)
#   -14 -> viltus caurums pazūd, īstais fons paliek 99.5 % malā   <- izvēlēts
#   -12 -> tas pats, bet mazāka rezerve
#   -10 -> fons pārstāj atpazīties pavisam (segums 1.0) — katastrofa
# Rezervi abos virzienos nosaka mērījums, nevis gaume.
L_TOL = (-14.0, 8.0)


def _keep_garment(m: np.ndarray, L: np.ndarray | None = None,
                  L_tol: tuple[float, float] = L_TOL) -> np.ndarray:
    """Fons = ar malu savienoti komponenti, kas ir ARĪ papīram līdzīgi.

    Kāpēc krāsu tests: tekstūra viena pati pieņem par fonu **ēnas kroku** (L* 20)
    un **gaismas atspīdumu** (L* 79), jo abi ir gludi. Uz `PXL_20261022_124339475`
    tas izgrieza divus baltus "spraugus" tur, kur oriģinālā ir nepārtraukts
    audums. Īstais papīrs tur ir L* ~62, tāpēc fona komponente drīkst būt tikai
    `paper + (-18..+8)` L* robežās. Kroka (20) un atspīdums (79) to nepāriet un
    paliek kreklā. Sk. QA §25.
    """
    inv = (m == 0).astype(np.uint8)
    _, cc, st, _ = cv2.connectedComponentsWithStats(inv, 8)
    border = set(cc[0, :]) | set(cc[-1, :]) | set(cc[:, 0]) | set(cc[:, -1])
    bg_ids = set()
    if L is not None:
        pL, pE = _paper_level(L, m)
        lo, hi = pL + L_tol[0], pL + L_tol[1]
        E_loc = _local_std(L, 25) if np.isfinite(pE) else None
        e_lim = max(2.2 * pE, pE + 2.0) if np.isfinite(pE) else float("inf")
        small_pocket_lim = int(0.005 * L.size)
    for i in border - {0}:
        if L is None:
            bg_ids.add(i)
            continue
        comp = cc == i
        area = int(comp.sum())
        if area < 50:
            bg_ids.add(i)
            continue
        if E_loc is not None and area < small_pocket_lim:
            if float(np.median(E_loc[comp])) > e_lim:
                continue
        med = float(np.median(L[comp]))
        if lo <= med <= hi:
            bg_ids.add(i)
        # pretējā gadījumā: gluds, bet NAV papīrs -> kroka/atspīdums, paliek kreklā
    bg = np.isin(cc, list(bg_ids)) if bg_ids else np.zeros_like(m, bool)
    return (~bg).astype(np.uint8)


# Otsu maskas seguma grīda, zem kuras ieslēdzas enkurētais slieksnis.
# Tā pati vērtība, ko plāksnes QA prasa kā seguma minimumu
# (config.toml [plate] cover_min=0.25): zem tās Otsu masku QA tāpat
# noraidītu, tāpēc fallback neko nezaudē, bet var glābt kadru.
DETECT_COVER_FLOOR = 0.25


def _anchored_threshold(E: np.ndarray) -> float | None:
    """Slieksnis no izmērītiem līmeņiem, ja Otsu izkropļo sadalījumu.

    Papīra līmenis = malas gredzena gludās daļas (E <= p40) mediāna
    (tas pats paraugs, ko `_paper_level` ņem L* līmenim); auduma
    līmenis = visa kadra E p90. Slieksnis = ģeometriskais vidējais:
    tekstūras enerģija ir reizinājuma mēroga lielums, tāpēc viduspunkts
    log skalā ir tas pats, ko dotu Otsu log-domēnā (uz `124406358` abi
    deva 4.6 pret Otsu 13.7).

    Mērīts 2026-10-24 uz `PXL_20261022_124406358` (birkas makro):
    papīrs 2.24, audums p90 9.38 -> slieksnis 4.58, segums 0.8717
    (Otsu 13.73 deva 0.0237: virs auduma mediānas 7.06, jo E maksimumu
    31.3 nosaka reti ekstrēmi — birkas melnā druka un vīļu ēnas).
    Kalibrācijas bildē `124339475` Otsu segums ir 0.71, tāpēc fallback
    tur NEIESLĒDZAS un maska paliek bitiski identiska vecajai.
    """
    h, w = E.shape
    ring = np.zeros((h, w), bool)
    s = max(4, int(0.012 * min(h, w)))
    ring[:s, :] = ring[-s:, :] = True
    ring[:, :s] = ring[:, -s:] = True
    ring_E = E[ring]
    if ring_E.size < 200:
        return None
    bg = float(np.median(ring_E[ring_E <= np.percentile(ring_E, 40)]))
    fg = float(np.percentile(E, 90))
    if bg <= 0 or fg <= bg:
        return None
    return float(np.sqrt(bg * fg))


def _detect(L: np.ndarray, win: int) -> tuple[np.ndarray, dict]:
    E = _local_std(L, win)
    thr, _ = cv2.threshold(
        np.clip(E / E.max() * 255, 0, 255).astype(np.uint8), 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    thr = float(thr) / 255 * E.max()

    def build(t: float) -> np.ndarray:
        m = (E > t).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((win, win), np.uint8))
        n, cc, st, _ = cv2.connectedComponentsWithStats(m, 8)
        if n > 1:
            m = (cc == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
        return _keep_garment(m, L)

    m = build(thr)
    thr_used, method = thr, "otsu"
    if float(m.mean()) < DETECT_COVER_FLOOR:
        anchored = _anchored_threshold(E)
        if anchored is not None:
            m2 = build(anchored)
            if float(m2.mean()) > float(m.mean()):
                m, thr_used, method = m2, anchored, "anchored_fallback"
    return m, {"win": win, "otsu": round(thr, 3),
               "thr": round(float(thr_used), 3), "thr_method": method,
               "bg_med": round(float(np.median(E[_bg_sample(m)])), 2),
               "fg_med": round(float(np.median(E[binary_erosion(m > 0, iterations=12)])), 2)
               if binary_erosion(m > 0, iterations=12).any() else None}


def _bg_sample(m: np.ndarray) -> np.ndarray:
    """Neliels tīra fona paraugs: 8 % kvadrāts pie labās malas, zem vidus.
    Ja 3 malu bleed tuvplānā šis kvadrāts iekrīt apģērbā, ņem visu tālo
    fonu (lai nerastos tukša griezuma NaN)."""
    h, w = m.shape
    far = binary_dilation(m > 0, iterations=3) == 0
    s = np.zeros((h, w), bool)
    s[int(h * 0.80):int(h * 0.92), int(w * 0.90):int(w * 0.98)] = True
    sel = s & far
    return sel if sel.any() else far


EDGE_CALIB_PX = 0   # aklā dilatācija atcelta; to aizstāj `_refine_edge` (QA §26)


def _smooth_mask(m: np.ndarray, win: int = 15, step: int = 2) -> np.ndarray:
    """Izlīdzina ārējās kontūras, bet saglabā iekšējos caurumus (īstos robus)."""
    m8 = m.astype(np.uint8)
    cnts, hier = cv2.findContours(m8, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return m8
    hier = hier[0]
    out = np.zeros_like(m8)
    for i, c in enumerate(cnts):
        if cv2.contourArea(c) < 2000:
            continue
        pts = c[:, 0, :].astype(np.float64)
        if len(pts) < 20:
            continue
        seg = np.sqrt(((np.roll(pts, -1, 0) - pts) ** 2).sum(1))
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        total = cum[-1]
        if total < 40:
            continue
        ns = max(40, int(total / step))
        t = np.linspace(0, total, ns, endpoint=False)
        x = np.interp(t, cum, np.r_[pts[:, 0], pts[0, 0]])
        y = np.interp(t, cum, np.r_[pts[:, 1], pts[0, 1]])
        kk = win // 2
        ker = np.ones(win) / win
        xs = np.convolve(np.r_[x[-kk:], x, x[:kk]], ker, "same")[kk:kk + ns]
        ys = np.convolve(np.r_[y[-kk:], y, y[:kk]], ker, "same")[kk:kk + ns]
        poly = np.round(np.stack([xs, ys], 1)).astype(np.int32)
        cv2.fillPoly(out, [poly], 1 if hier[i][3] == -1 else 0)
    return out


def _refine_edge(m: np.ndarray, L: np.ndarray, win: int = 13,
                 band_px: int = 10) -> np.ndarray:
    """Pārbīda robežu uz īsto auduma malu pēc tekstūras LĪMEŅA.

    Kāpēc ne gradients: auduma malā ir arī metēna ēna uz papīra, un gradienta
    maksimums ir tieši uz ēnas->papīra pārejas, ne uz auduma->ēnas. Tāpēc
    gradienta metode masku velk UZ ĀRU (uz ēnu), un ēna iznāk kā krekla
    turpinājums. Līmenis ir noturīgs: audums E≈5.6, papīrs E≈1.7 neatkarīgi
    no tā, cik tumša ir ēna (ēna ir gluda — tāpēc tā ir zema E, t.i. fons).

    Robežu liek tur, kur E nokrītas līdz pusei starp auduma un papīra līmeni.
    """
    Ef = _local_std(L, win)
    core = cv2.erode(m.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    if not core.any():
        return m
    fabric_med = float(np.median(Ef[core]))
    h, w = m.shape
    ring = np.zeros((h, w), bool)
    s0 = max(4, int(0.012 * min(h, w)))
    ring[:s0, :] = ring[-s0:, :] = True
    ring[:, :s0] = ring[:, -s0:] = True
    far_bg = ring & (m == 0) & (cv2.dilate(m.astype(np.uint8), np.ones((15, 15), np.uint8)) == 0)
    paper_med = float(np.median(Ef[far_bg])) if far_bg.sum() > 100 else 1.5
    thr = max(paper_med * 1.5, 0.5 * fabric_med)

    m8 = m.astype(np.uint8)
    band = (cv2.dilate(m8, np.ones((band_px, band_px), np.uint8)) > 0) & \
           ~(cv2.erode(m8, np.ones((band_px, band_px), np.uint8)) > 0)
    new = np.where(band, (Ef > thr), m.astype(bool)).astype(np.uint8)
    # notur to, kas savienots ar iekšpusi
    n, cc, st, _ = cv2.connectedComponentsWithStats(new, 8)
    keep = set(np.unique(cc[core])) - {0}
    if not keep:
        return m
    new = np.isin(cc, list(keep)).astype(np.uint8)
    return new


def _trim_shadow(m: np.ndarray, L: np.ndarray, band_px: int = 80,
                 lab: np.ndarray | None = None) -> np.ndarray:
    """Noņem metēno ēnu, kas pielipusi pie krekla ārējās robežas.

    Kāpēc augstfrekvences tekstūra + stari gar kontūras normāli (2026-10-28):
    nefiltrēts `_local_std(L, 25)` uz stāvas ēnas slīpuma (piem., M1/M2 uz
    `145704`, kur L* krīt 68.7 -> 30.2) izmēra apgaismojuma rampu kā E25=9.1
    (> Otsu 7.02 un > 0.45*fabric_E) un atstāj gludu metēno ēnu maskā.
    Augstfrekvences atlikums `L - gaussian(L, 3)` pilnībā nodzēš lēzeno
    ēnas slīpumu (ēnai E_hp≈1.4 kā papīram 1.37, vafeļaudumam ≈9.5).

    Griež gar kontūras iekšējo normāli (nevis pa pikselim), apstājoties,
    tiklīdz sasniegta:
      1) auduma mikro-tekstūra (`E_hp >= 0.42 * fabric_Ehp`),
      2) par papīru gaišāks apģērbs (`L > pL + 3.0`),
      3) kāpums ārā no ēnas kontakta ieplakas uz apģērba malu (`L > l_min + 4.5`),
      4) apģērba hroma (`dC > 6.0` pret papīru, pasargājot siltas iekšējās
         apkakles krokas ēnā, kur starpatstarošana dod dC≈12).
    Kontūras punktos, kur jau uz robežas ir ass apģērba pakāpiens
    (`|L(+3) - L(-3)| > 14`), stars nemaz nesākas (depth=0). Brīvo loku
    galapunkti pie kadra malām tiek piesaistīti malai, lai 3 malu bleed
    stūros nepaliktu ēnas trīsstūris.
    """
    from scipy.ndimage import gaussian_filter1d, median_filter

    hh, hw = L.shape
    core = cv2.erode(m.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
    if not core.any():
        return m
    s0 = max(4, int(0.012 * min(hh, hw)))
    ring = np.zeros((hh, hw), bool)
    ring[:s0, :] = ring[-s0:, :] = True
    ring[:, :s0] = ring[:, -s0:] = True
    ring &= (m == 0)
    if ring.sum() < 200:
        return m
    E25 = _local_std(L, 25)
    sr = ring & (E25 <= np.percentile(E25[ring], 40))
    if sr.sum() < 100:
        sr = ring
    pL = float(np.median(L[sr]))
    if lab is not None:
        A, B = lab[..., 1], lab[..., 2]
        pA, pB = float(np.median(A[sr])), float(np.median(B[sr]))
        dC = np.hypot(A - pA, B - pB)
    else:
        dC = None

    hp = L - gaussian_filter(L, 3.0)
    E_hp = _local_std(hp, 9)
    fabric_Ehp = float(np.median(E_hp[core]))
    if fabric_Ehp < 1.5:
        return m
    tex_thr = 0.42 * fabric_Ehp
    Ls = gaussian_filter(L, 1.0)
    max_d = max(12, int(round(band_px * 0.6875)))  # noklusēti 55 pusizm. px

    cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return m
    c = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float64)
    n_pts = len(c)
    if n_pts < 64:
        return m

    k = 12
    dd = np.roll(c, -k, axis=0) - np.roll(c, k, axis=0)
    tng = dd / np.maximum(np.linalg.norm(dd, axis=1, keepdims=True), 1e-6)
    nrm = np.stack([-tng[:, 1], tng[:, 0]], 1)
    pr = np.clip(np.round(c + 4.0 * nrm).astype(int), [0, 0], [hw - 1, hh - 1])
    nrm[m[pr[:, 1], pr[:, 0]] == 0] *= -1.0

    on_border = ((c[:, 0] <= 2) | (c[:, 0] >= hw - 3)
                 | (c[:, 1] <= 2) | (c[:, 1] >= hh - 3))
    depths = np.zeros(n_pts, np.float32)
    for i in range(n_pts):
        if on_border[i]:
            continue
        x0, y0 = c[i]
        nx, ny = nrm[i]
        xo = int(np.clip(round(x0 - 3 * nx), 0, hw - 1))
        yo = int(np.clip(round(y0 - 3 * ny), 0, hh - 1))
        xi = int(np.clip(round(x0 + 3 * nx), 0, hw - 1))
        yi = int(np.clip(round(y0 + 3 * ny), 0, hh - 1))
        if abs(float(Ls[yi, xi]) - float(Ls[yo, xo])) > 14.0:
            continue
        l_min = float(Ls[int(round(y0)), int(round(x0))])
        d_stop = 0
        for d in range(1, max_d + 1):
            xx = int(round(x0 + nx * d))
            yy = int(round(y0 + ny * d))
            if not (0 <= xx < hw and 0 <= yy < hh) or m[yy, xx] == 0:
                break
            lv = float(Ls[yy, xx])
            if lv < l_min:
                l_min = lv
            if (E_hp[yy, xx] >= tex_thr
                    or lv > pL + 3.0
                    or lv > l_min + 4.5
                    or (dC is not None and dC[yy, xx] > 6.0)):
                break
            d_stop = d
        depths[i] = float(d_stop)

    if int((depths > 1.0).sum()) == 0:
        return m

    if not on_border.any():
        depths = median_filter(depths, size=19, mode="wrap")
        depths = gaussian_filter1d(depths, 7.0, mode="wrap")
        pts = c + nrm * depths[:, None]
    else:
        b0 = int(np.argmax(on_border))
        c_r = np.roll(c, -b0, axis=0)
        n_r = np.roll(nrm, -b0, axis=0)
        d_r = np.roll(depths, -b0, axis=0)
        ob_r = np.roll(on_border, -b0, axis=0)
        pts_r = c_r.copy()
        free = ~ob_r
        starts = np.where(free & ~np.r_[False, free[:-1]])[0]
        ends = np.where(free & ~np.r_[free[1:], False])[0]
        for s_idx, e_idx in zip(starts, ends):
            if e_idx - s_idx + 1 < 8:
                continue
            msz = min(19, e_idx - s_idx + 1)
            seg_d = median_filter(d_r[s_idx:e_idx + 1], size=msz, mode="nearest")
            seg_d = gaussian_filter1d(seg_d, 7.0, mode="nearest")
            pts_r[s_idx:e_idx + 1] = (c_r[s_idx:e_idx + 1]
                                      + n_r[s_idx:e_idx + 1] * seg_d[:, None])
            for end_i, step in ((s_idx, -1), (e_idx, +1)):
                b_i = (end_i + step) % n_pts
                bx, by = c_r[b_i]
                px, py = pts_r[end_i]
                if bx <= 2:
                    px = 0.0
                elif bx >= hw - 3:
                    px = float(hw - 1)
                if by <= 2:
                    py = 0.0
                elif by >= hh - 3:
                    py = float(hh - 1)
                pts_r[end_i] = [px, py]
                collapse = int(round(seg_d[0 if end_i == s_idx else -1])) + 6
                for k_step in range(1, collapse + 1):
                    bi = (end_i + step * k_step) % n_pts
                    if not ob_r[bi]:
                        break
                    pts_r[bi] = [px, py]
        pts = np.roll(pts_r, b0, axis=0)

    pts[:, 0] = np.clip(pts[:, 0], 0, hw - 1)
    pts[:, 1] = np.clip(pts[:, 1], 0, hh - 1)
    out = np.zeros((hh, hw), np.uint8)
    cv2.fillPoly(out, [np.round(pts * 16).astype(np.int32)], 1,
                 lineType=cv2.LINE_AA, shift=4)
    n, cc, st, _ = cv2.connectedComponentsWithStats(out, 8)
    if n > 1:
        out = (cc == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    return _smooth_mask(out, win=15)


SHADOW_TRIM_PX = 3   # pusizmērā (=6 px pilnā); mērīts, sk. QA §26


def boundary_offset(m: np.ndarray, L: np.ndarray) -> dict:
    """Cik tālu maskas mala ir no spēcīgākās tekstūras gradienta grēdas.

    Mērīts uz `PXL_20261022_124339475`: mediāna −2.5 px (pusizmērā), t.i. mala
    sistemātiski **iekšā** par ~5 px pilnā izmērā. Iemesls godīgs: 25 px logs
    izplūdina tekstūru pāri malai, un Otsu nogriež to, kur tekstūra jau pusē.
    Tāpēc pēc izlīdzināšanas maska tiek paplašināta par šo izmērīto daudzumu,
    nevis par "lai izskatās labi".
    """
    E = _local_std(L, 13)
    gy, gx = np.gradient(E)
    mag = np.hypot(gx, gy)
    cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return {"mean": 0.0, "median": 0.0}
    c = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float64)
    if len(c) < 40:
        return {"mean": 0.0, "median": 0.0}
    kk = max(1, int(round(len(c) / 20)))
    off = []
    for i in np.linspace(0, len(c) - 1, min(300, len(c))).astype(int):
        x, y = c[i]
        tx, ty = c[(i + kk) % len(c)] - c[(i - kk) % len(c)]
        nrm = np.hypot(tx, ty)
        if nrm < 1e-6:
            continue
        nx, ny = -ty / nrm, tx / nrm
        best, bo = 0.0, 0.0
        for d in np.arange(-6, 6.5, 0.5):
            xi, yi = int(round(x + nx * d)), int(round(y + ny * d))
            if 0 <= yi < mag.shape[0] and 0 <= xi < mag.shape[1] and mag[yi, xi] > best:
                best, bo = mag[yi, xi], float(d)
        off.append(bo)
    if not off:
        return {"mean": 0.0, "median": 0.0}
    off = np.asarray(off)
    return {"mean": round(float(off.mean()), 2),
            "median": round(float(np.median(off)), 2),
            "p10": round(float(np.percentile(off, 10)), 1),
            "p90": round(float(np.percentile(off, 90)), 1)}


def garment_mask_half(img: Image.Image, scale: int = 2, win: int = 25,
                      smooth_win: int = 15) -> tuple[np.ndarray, np.ndarray, dict]:
    """Maska PUSIZMĒRĀ + tās pašas izšķirtspējas L* kanāls (QA vajadzībām).

    QA jāstrādā tajā pašā mērogā, kurā maska tika atrasta: 4 px josla pusizmērā
    atbilst 8 px pilnā, un tas ir vienīgais godīgais veids, kā mērīt malas
    piesārņojumu. Pilnā izšķirtspējā `gaussian_filter(sigma=120)` vien maksā
    vairāk par visu pārējo ceļu.
    """
    W, H = img.size
    hw, hh = W // scale, H // scale
    small = img.convert("RGB").resize((hw, hh), Image.LANCZOS)
    lab = lab_chunked(np.asarray(small)).astype(np.float32)
    L = lab[..., 0]
    m, info = _detect(L, win)
    sm = _smooth_mask(m, win=smooth_win)
    info["offset_before_calib"] = boundary_offset(sm, L)
    sm_pre_trim = sm.copy()
    sm = _trim_shadow(sm, L, lab=lab)
    trimmed_shadow = (sm_pre_trim > 0) & (sm == 0)
    # Metēno ēnu no auduma atdalīt nevar (tā ir mīksta kroka pāreja), tāpēc tā
    # tiek nogriezta kā fons: maska sašaurināta par SHADOW_TRIM_PX. Mērīts:
    # 98 % kontūras īstais audums sākas <= 4 px (pusizm.) no malas, tāpēc
    # 3 px nogriež ēnu, nevis audumu. Alfa pēc tam tiek izplūdināta, tāpēc
    # mala paliek mīksta, nevis cieta.
    if SHADOW_TRIM_PX > 0:
        sm = cv2.erode(sm, np.ones((3, 3), np.uint8), iterations=int(SHADOW_TRIM_PX))
    if EDGE_CALIB_PX > 0:
        sm = cv2.dilate(sm, np.ones((3, 3), np.uint8), iterations=int(EDGE_CALIB_PX))
    sm = (_keep_garment(sm, L).astype(bool) & ~trimmed_shadow).astype(np.uint8)
    info["offset_after_calib"] = boundary_offset(sm, L)
    info["edge_calib_px"] = int(EDGE_CALIB_PX)
    info["coverage_half"] = round(float(sm.mean()), 4)
    info["fraction_before_smooth"] = round(float(m.mean()), 4)
    return sm.astype(np.uint8), L, info


def garment_alpha(img: Image.Image, scale: int = 2, win: int = 25,
                  smooth_win: int = 15, feather: float = 0.8) -> tuple[np.ndarray, dict]:
    """Atgriež (alpha float32 0..1 pilnā izmērā, info).

    `img` ir jau sagatavots (orientēts) RGB attēls. Alpha ir 1 kreklā, 0 fonā,
    ar `feather` px mīkstu malu. Binārā maska = alpha >= 0.5.
    """
    W, H = img.size
    sm, _L, info = garment_mask_half(img, scale=scale, win=win, smooth_win=smooth_win)
    up = np.asarray(Image.fromarray((sm * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS))
    up = up.astype(np.float32) / 255.0
    # anti-aliasing: mīksta mala bez seguma maiņas
    alpha = gaussian_filter(up, feather)
    info["coverage_full"] = round(float((alpha >= 0.5).mean()), 4)
    return np.clip(alpha, 0.0, 1.0), info
