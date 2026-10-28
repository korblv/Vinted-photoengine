#!/usr/bin/env python3
"""MAKER — izpilda LOOP.md: segmentē apģērbu, nomaina TIKAI fonu.
Apģērba pikseļi netiek ģenerēti/rotēti/deformēti. MASTER = 1:1 oriģināls (PNG).
PARAUGS = deterministiski samazināts 2000x2500 kadrs pēc parauga (JPG)."""
import argparse, json, math, os
import cv2
import numpy as np
from PIL import Image, ImageOps

BG = (243, 243, 243)          # izmērīts no parauga (#F3F3F3)
BG_GRAY = BG[0]               # 243 — skalārā forma; VIENĪGAIS avots visiem moduļiem

# --- Ēnas virziens --------------------------------------------------------
# IZMĒRĪTS uz PXL_20261022_124339475 trīs metodēm, kas saskan: ēna krīt uz
# 120-135° (spēcīgākā 135°, otrā 120°), gaisma no 300-315°. Izvēlēts 125° —
# abu spēcīgāko binu vidus. Sk. PROFESIONALAS_METODES.md §2.
# Iepriekš bija (16,20)/(25,35) = 54° -> ēna krita TAJĀ PAŠĀ pusē, no kuras
# nāca gaisma ("divas saules"). Sk. PROFESIONALAS_METODES.md §2.
# Leņķis ir viena konstante: gan avota (43 px), gan audekla (25.6 px)
# mērogs rēķina savu dx,dy no tā paša leņķa, tāpēc tie nevar atšķirties.
# 125° bija iekodēts pēc VIENAS bildes (krekls). Uz džinsiem tas deva 65°
# kļūdu: ēna krita pa kreisi, tāpēc LABAJĀM malām ēnas nebija vispār, un
# džinsa tumšā mala karājās pret tīru #F3F3F3 — izskatījās kā uzzīmēta melna
# līnija (lietotāja anotācija IMG_20261023_110348.jpg).
# Tāpēc virzienu tagad MĒRA katrā bildē (`measure_shadow_angle`); šī konstante
# ir tikai atkāpšanās, kad mērījums nav uzticams. Sk. QA §32.
SHADOW_ANGLE_DEG = 125.0      # tikai fallback
# Ēnas modelis (QA §33). Profesionālā prakse uz balta fona: metamā ēna 8-20 %
# necaurspīdības, TUMŠĀKĀ tieši pie malas (kontakta ēna), ar dilšanu uz āru.
# Vecais modelis (nobīde + GaussianBlur) deva vienmērīgu plato ~26 % -> tumša
# josla ar asu galu, ko lietotājs noraidīja kā "pārāk tumšu".
SHADOW_STRENGTH = 0.32        # maksimālā aiztumšošana pie malas (QA §36)
SHADOW_FALLOFF_PX = 18.0      # dilšanas konstante λ, audekla px (QA §36)
SHADOW_AMBIENT = 0.55         # daļa, kas paliek visapkārt (kontakta aptumšojums)
# Ēnai jāizzūd PILNĪGI, pirms sasniedz GATE_B "tālo fonu" (90 px no malas).
# Pretējā gadījumā eksponenciālā aste turpina tumšot 1-2 līmeņus, un GATE_B
# (kurš pieprasa precīzi #F3F3F3) krīt. 2026-10-23: ar λ=10 aste bija 28 %
# tālā fona -> bg_ok 72 %. Tagad loga apakšā ir smoothstep uz nulli.
SHADOW_CUTOFF_PX = 34.0       # audekla px; aiz šī ēna ir tieši 0 (QA §36)
SHADOW_MIN_REL = 0.05          # stipruma grīda = 5 % no papīra L* (relatīva, ne absolūta)

# Jauns studijas ēnas modelis no nulles (2026-10-24, lietotāja uzdevums pēc
# Vans Attempt 2 noraidīšanas ēnas dēļ). Divas fizikāli atdalītas komponentes:
# (1) šaurs kontakta aptumšojums tieši pie auduma malas; (2) laukuma gaismas
# metēnā ēna ar vienu fiksētu studijas virzienu (gaisma no augšas-kreisi,
# ēna uz leju-labi) un penumbru, kas aug līdz ar attālumu no kontakta
# (PCSS/contact-hardening princips). Parametri nav gaumīgi: tie piemeklēti
# ar režģa meklēšanu pret divu Slam Jam pilno kadru sektoru×attāluma
# profiliem (E/S/W/N vidējais Δ joslās 2-60 px). Labākais kandidāts deva
# kardinālo sektoru RMSE 1.69 Δ līmeņu (vecais workflow modelis: 24.38 pēc
# SE/NW agregāta). Sk. PROGRESS §51 un PAPIRA_NOPLUDES_QA §49.
STUDIO_SHADOW_ANGLE_DEG = 43.0   # ēnas virziens attēla koordinātēs (0=E, 90=S)
STUDIO_SHADOW_OFFSET_PX = 16.0   # silueta projekcijas nobīde, audekla px
STUDIO_SHADOW_SIGMA_LEVELS = (0.8, 1.8, 3.2, 5.0, 7.5)  # penumbras līmeņi, audekla px
STUDIO_SHADOW_SIGMA0_PX = 0.9    # penumbra kontaktā
STUDIO_SHADOW_SIGMA_K = 0.28     # penumbras pieaugums uz attāluma px
STUDIO_SHADOW_PEAK = 0.32        # metēnās ēnas maks. aiztumšošanas daļa
STUDIO_SHADOW_GAMMA = 0.80       # redzamības līkne (kalibrēta)
STUDIO_CONTACT_PEAK = 0.10       # kontakta AO maks. aiztumšošanas daļa
STUDIO_CONTACT_LAMBDA_PX = 1.4   # kontakta AO dilšana, audekla px
STUDIO_SHADOW_CUT_PX = (42.0, 58.0)  # smoothstep logs; tālāk tieši 243 (GATE_B tālais fons sākas 90 px)


def shadow_dir(dist_px: float, angle_deg: float | None = None) -> tuple[int, int]:
    """Vienības vektors leņķa virzienā, reizināts ar dist_px.
    Atgriež veselus skaitļus — shadow_bg griež ar tiem masīvu (slicing)."""
    a = math.radians(SHADOW_ANGLE_DEG if angle_deg is None else angle_deg)
    return int(round(dist_px * math.cos(a))), int(round(dist_px * math.sin(a)))


def measure_shadow_angle(L: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    """Mēra ĒNAS virzienu no oriģināla: (leņķis_grādos, stiprums).

    Kāpēc vispār mērīt: `SHADOW_ANGLE_DEG = 125` tika iekodēts pēc vienas bildes.
    Uz džinsiem tas novietoja ēnu pa KREISI, tāpēc labajām malām ēnas nebija
    vispār, un džinsa tumšā mala karājās pret tīru #F3F3F3 — lietotājs to
    atzīmēja kā melnu līniju (IMG_20261023_110348.jpg). Sk. QA §32.

    Metode: fona pikseļus sadala pa četrām pusēm pēc tā, kurā virzienā atrodas
    tiem tuvākais apģērba pikselis, un katrai pusei salīdzina spilgtumu
    **tuvu (4-24 px) ar tālu (60-120 px) TAJĀ PAŠĀ virzienā**. Starpība (R-L, D-U)
    dod vektoru.

    Kāpēc "tuvu pret tālu tajā pašā virzienā", nevis "pret tālu papīru": papīram
    ir apgaismojuma gradients (stūri tumšāki), tāpēc globālais papīra līmenis
    sajaucas ar gradientu. Uz krekla bilde šī kļūda deva R=0 un 30° kļūdu.
    Vienā virzienā abi paraugi redz vienu un to pašu gradientu, tāpēc tas saīsinās.

    Kāpēc ne krusteniskā korelācija ar masku: tā meklē vienu globālu nobīdi un uz
    bildēm, kur apģērbs aizņem 70 % kadra, paliek bez nosacījumiem (devām 131°
    krekla bilde, kur redzami ēna ir lejup). Sk. QA §32.

    Aprēķins ceturtdaļizšķirtspējā — pilnā izšķirtspējā tas maksāja 5 s/bilde.
    """
    from scipy.ndimage import distance_transform_edt as _edt

    m = mask.astype(bool)
    if not m.any() or m.all():
        return SHADOW_ANGLE_DEG, 0.0
    h, w = m.shape
    f = max(1, int(round(max(h, w) / 900)))          # mērķis ~900 px garākajā pusē
    Lr = np.asarray(
        Image.fromarray(np.clip(L, 0, 255).astype(np.uint8)).resize(
            (w // f, h // f), Image.BOX), np.float32)
    mr = np.asarray(
        Image.fromarray((m * 255).astype(np.uint8)).resize(
            (w // f, h // f), Image.BOX)) > 128
    if not mr.any() or mr.all():
        return SHADOW_ANGLE_DEG, 0.0
    hh, ww = mr.shape
    dout = _edt(~mr)
    _, idx = _edt(~mr, return_indices=True)
    ny, nx = idx[0], idx[1]
    dy = (np.arange(hh)[:, None] - ny).astype(np.float32)
    dx = (np.arange(ww)[None, :] - nx).astype(np.float32)
    nrm = np.hypot(dx, dy) + 1e-6
    sides = {
        "R": dx / nrm > 0.5, "L": dx / nrm < -0.5,
        "D": dy / nrm > 0.5, "U": dy / nrm < -0.5,
    }
    # attālumi ceturtdaļizšķirtspējā (mērīti pilnajā, tāpēc dalām ar f)
    near_d = [(4, 8), (8, 12), (12, 16), (16, 20), (20, 24)]
    far_d = [(60, 64), (80, 84), (100, 104), (120, 124)]
    dark = {}
    far_lv = []
    for k, sel in sides.items():
        nv = [np.mean(Lr[sel & (dout >= a / f) & (dout < b / f)])
              for a, b in near_d if (sel & (dout >= a / f) & (dout < b / f)).sum() > 20]
        fv = [np.mean(Lr[sel & (dout >= a / f) & (dout < b / f)])
              for a, b in far_d if (sel & (dout >= a / f) & (dout < b / f)).sum() > 20]
        far_lv.extend(fv)
        dark[k] = max(0.0, float(np.mean(fv)) - float(np.mean(nv))) if (nv and fv) else 0.0
    vx = dark["R"] - dark["L"]
    vy = dark["D"] - dark["U"]
    strength = float(math.hypot(vx, vy))
    paper = float(np.mean([v for v in far_lv if not np.isnan(v)])) if far_lv else 0.0
    if paper <= 1.0 or strength < SHADOW_MIN_REL * paper:
        return SHADOW_ANGLE_DEG, strength
    return float(math.degrees(math.atan2(vy, vx)) % 360), strength

# ---------------------------------------------------------------------------
# Ceļi un kadra ģeometrija
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = "/home/user/uploads"
OUT = os.path.join(_HERE, "output")
CANVAS = (2000, 2500)            # (platums, augstums) — spec: 4:5
GARMENT_FILL_W = 0.74            # īpatsvars no audekla platuma (pilnajā kadrā)
GARMENT_FILL_H = 0.78            # īpatsvars no audekla augstuma; mērīts QA §24

# Tuvplāna sēklu bibliotēka (GrabCut). Kodus 160550/160601/160608/160645/
# 161944/161959/162013/162101 apkalpoja 8-bilžu un 2-bilžu regresijas grupas,
# kuras lietotājs lika dzēst — tāpēc bibliotēka ir tukša. `closeup_mask` bez
# ieraksta apzināti MET ValueError (STOP-eskalācija cilvēkam), nevis klusām
# uzmin; tā šī miss nevienu esošo bildi neietekmē (ISNet ceļš to neizmanto).
# Sk. QA §32 piezīmi par šī bloka nejaušu izdzēšanu un atjaunošanu.
CLOSEUP_SEEDS: dict[str, dict] = {}
CLOSEUP_CROPS: dict[str, tuple] = {}


def clean_mask(soft: np.ndarray, threshold: int, erode_px: int) -> np.ndarray:
    """soft 0..255 -> bināra maska: tikai lielākā komponente, caurumi aizpildīti."""
    binary = (soft >= threshold).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if n <= 1:
        return binary
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    binary = (lab == largest).astype(np.uint8)
    # aizpildi iekšējos caurumus (birkas/pogas apģērba iekšienē paliek apģērbs)
    try:
        from scipy import ndimage
        binary = ndimage.binary_fill_holes(binary).astype(np.uint8)
    except Exception:
        cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filled = np.zeros_like(binary)
        cv2.drawContours(filled, cnts, -1, 1, thickness=cv2.FILLED)
        binary = filled
    # neliela aizvēršana pret maskas robiem, tad erozija pret vecā fona oreolu
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    if erode_px > 0:
        binary = cv2.erode(binary, np.ones((3, 3), np.uint8), iterations=erode_px)
    return binary

def closeup_mask(orig: Image.Image, stem: str, erode_px: int, proc_w: int = 960,
                 cfg_override: dict | None = None, grabcut_iters: int = 6) -> np.ndarray:
    """Tuvplāna maska ar GrabCut (iterācija 3). Darbojas samazinātā mērogā;
    gala apģērba pikseļi tāpat nāk no pilnas izšķirtspējas oriģināla 1:1.

    `cfg_override` ļauj Workflow v2.1 nodot automātiski ģenerētu sēklu
    konfigurāciju jaunam kadram, nemainot pārbaudīto bibliotēku. Ja tas nav
    dots, izmanto `CLOSEUP_SEEDS` pēc faila koda.
    """
    if cfg_override is None:
        code = stem[-6:]
        if code not in CLOSEUP_SEEDS:
            raise ValueError(f"Tuvplānam {stem} nav sēklu kartējuma CLOSEUP_SEEDS — STOP-eskalācija cilvēkam")
        cfg = CLOSEUP_SEEDS[code]
    else:
        cfg = cfg_override
    W = proc_w
    H = round(W * orig.height / orig.width)
    small = orig.resize((W, H), Image.LANCZOS)
    rgb = np.asarray(small)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    lap = cv2.convertScaleAbs(cv2.Laplacian(gray, cv2.CV_16S, ksize=3))
    k = int(round(15 * W / 512)) | 1
    tex = cv2.blur(lap.astype(np.float32), (k, k))
    del gray, lap
    # Parasti tuvplānā audums dominē, tāpēc nezināmais sākas kā PR_FGD.
    # Atsevišķos kadros ar lielu papīra/rokas laukumu drošāk ir sākt ar
    # PR_BGD un apģērbu definēt tikai ar kartētajām FG sēklām.
    mask = np.full(
        (H, W),
        cv2.GC_PR_BGD if cfg.get("init_bg") else cv2.GC_PR_FGD,
        np.uint8,
    )
    def poly(pts):
        return np.array([[int(x * W), int(y * H)] for x, y in pts], np.int32)
    x0, y0, x1, y1 = cfg["fg_rect"]
    mask[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W)] = cv2.GC_FGD
    for pts in cfg.get("fg_polys", []):
        cv2.fillPoly(mask, [poly(pts)], int(cv2.GC_FGD))
    if cfg.get("use_tex_fg", True):
        mask[tex > 60] = cv2.GC_FGD      # izteikta vafeļu tekstūra = drošs audums
    del tex
    for pts in cfg["bg_polys"]:          # drošais fons pēdējais — pārraksta visu
        cv2.fillPoly(mask, [poly(pts)], int(cv2.GC_BGD))
    sure_bg = (mask == cv2.GC_BGD)       # vajadzīgs caurumu aizpildīšanai zemāk
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, None, bgd, fgd, int(grabcut_iters), cv2.GC_INIT_WITH_MASK)
    del bgr, bgd, fgd                    # rgb vēl vajag top_edge_snap solim
    garment = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
    del mask
    # izmet sīkus "apģērba" plankumus fonā (<0.05% kadra)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(garment, connectivity=8)
    keep = np.zeros(n, bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= 0.0005 * W * H
    garment = keep[lab].astype(np.uint8)
    del lab, stats
    # aizpildi mazus fona "caurumus" auduma iekšienē (birkas/pogas/gludi laukumi,
    # kas nepieskaras kadra malai un ir <2% kadra) — tie ir apģērbs.
    # BET: komponenti, kurā ir cilvēka likta drošā fona sēkla, NEDRĪKST aizpildīt —
    # tā ir apzināta ārējā sprauga starp auduma slāņiem, nevis caurums audumā
    # (iter.6: tieši tā 160645 apakšā atgriezās melnais galda ēnas bloks).
    n, lab, stats, _ = cv2.connectedComponentsWithStats(1 - garment, connectivity=8)
    border = set(np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])))
    seeded = np.bincount(lab[sure_bg].ravel(), minlength=n) > 0
    del sure_bg
    fill = np.zeros(n, bool)
    for i in range(1, n):
        if i not in border and not seeded[i] and stats[i, cv2.CC_STAT_AREA] < 0.02 * W * H:
            fill[i] = True
    garment = (garment | fill[lab]).astype(np.uint8)
    del lab, stats
    # opcionāls "top edge snap": gandrīz horizontālai auduma augšmalai robežu
    # pievelk spēcīgākajai gaišuma pārejai (papīrs -> audums) katrā kolonnā.
    if "top_edge_snap" in cfg:
        from scipy.ndimage import median_filter
        y0f, y1f = cfg["top_edge_snap"]
        y0, y1 = int(y0f * H), int(y1f * H)
        grayf = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
        kx = int(round(51 * W / 960)) | 1
        blur = cv2.blur(grayf, (kx, 5))
        del grayf
        grad = np.gradient(blur, axis=0)
        del blur
        edge = np.argmax(grad[y0:y1, :], axis=0) + y0
        strength = np.max(grad[y0:y1, :], axis=0)
        del grad
        edge = median_filter(edge.astype(np.float32), size=kx, mode="nearest")
        yy = np.arange(y0, y1)[:, None]
        snapped = (yy >= edge[None, :]).astype(np.uint8)
        valid = (strength > 1.0)[None, :]
        garment[y0:y1, :] = np.where(valid, snapped, garment[y0:y1, :])
        garment[:y0, :] = 0
        del snapped, valid, edge, strength
    del rgb
    # uz pilnu izšķirtspēju (lineārs + slieksnis = gluda kontūra bez kāpnēm)
    full = cv2.resize((garment * 255).astype(np.uint8), (orig.width, orig.height),
                      interpolation=cv2.INTER_LINEAR)
    del garment
    binary = (full >= 128).astype(np.uint8)
    del full
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    if erode_px > 0:
        binary = cv2.erode(binary, np.ones((3, 3), np.uint8), iterations=erode_px)
    return binary

def _smoothstep01(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)

def refine_alpha(binary, feather_px=3.0, smooth_sigma=2.0, contrast=1.25,
                 band_px=6.5, shift_px=0.0):
    """Profesionāla malas pāreja, nemainot bināro audita masku.

    Vērtības (QA §36): feather 6.0 / smooth 2.5 / contrast 1.05 / band 14.
    Izmērīts: pārejas platums p50 6 px — atsauces slamjam bildēm 5 un 12 px.
    Iepriekšējās (1.6/1.6/1.65/5) deva 4 px: mala bija šķēru asa, un tieši tā
    lasījās kā "robaina" produkcijas bildē, lai gan kontūra pati bija gluda
    (novirze no gludās līnijas 0.29 pret atsauces 0.45).

    Binārā maska -> parakstīta attāluma alfa -> kontūras izlīdzināšana ->
    kontrasta atjaunošana. Tas noņem zema izšķirtspējas maskas "kāpnes",
    bet neatstāj tik plašu oreolu kā parasts stiprs Gaussian blur.
    Alfa tiek piespiedu kārtā fiksēta uz 255 vismaz 5 px apģērba iekšienē
    un uz 0 vismaz 5 px ārpusē, tāpēc checker A kodols paliek 1:1.
    """
    binary_u8 = (binary > 0).astype(np.uint8)
    dist_in = cv2.distanceTransform(binary_u8, cv2.DIST_L2, 5)
    dist_out = cv2.distanceTransform(1 - binary_u8, cv2.DIST_L2, 5)
    signed = dist_in - dist_out
    del dist_in, dist_out

    alpha = np.empty_like(signed, dtype=np.float32)
    denom = float(2.0 * feather_px)
    for y in range(0, signed.shape[0], 256):
        y2 = min(signed.shape[0], y + 256)
        alpha[y:y2] = _smoothstep01(
            (signed[y:y2] - float(shift_px) + float(feather_px)) / denom
        ).astype(np.float32)
    if smooth_sigma > 0:
        alpha = cv2.GaussianBlur(alpha, (0, 0), float(smooth_sigma))
    if contrast != 1.0:
        for y in range(0, alpha.shape[0], 256):
            y2 = min(alpha.shape[0], y + 256)
            alpha[y:y2] = _smoothstep01(
                (alpha[y:y2] - 0.5) * float(contrast) + 0.5
            ).astype(np.float32)
    alpha[signed >= band_px] = 1.0
    alpha[signed <= -band_px] = 0.0
    del signed
    return np.clip(alpha * 255.0 + 0.5, 0, 255).astype(np.uint8)

def decontaminate_rim(rgb, binary, max_px=30, tex_ratio=0.45):
    """Nogriež MASKAS IEKŠPUSĒ palikušo oriģināla papīra ēnu ("melno maliņu").

    Problēma (QA §34–35): segmentācija aprija oriģināla papīra ēnu. Matē paliek
    5-20 px plata josla, kas uz balta fona lasās kā melna līnija gar apģērba malu.

    Kritērijs ir TEKSTŪRA, nevis krāsa vai spilgtums. Tas ir izšķiroši, un divi
    iepriekšējie mēģinājumi krita tieši šeit:
      * Spilgtums neder — pats džinss sasniedz L=2-40 (tumšas šuves, kabatu
        apmales), 73.8 % no tumšajiem pikseļiem ir DZIĻI maskas iekšpusē.
      * Hroma neder — auduma hroma mainās pa bildi (B−R no −30 līdz +20), tāpēc
        lokālais vidējais nepareizi atzīmēja īstu audumu par papīru.
      * Tekstūra DER: papīra ēna ir gluda, džinsam ir redzams reljefs.
        Mērīts: joslā 1.4-4.1, audumā 11-22 (attiecība 0.06-0.19).

    Griež GAR KONTŪRU, nevis pa pikselim: katram kontūras punktam mēra, cik
    dziļi atgriežas auduma tekstūra, tad izlīdzina dziļumu gar kontūru
    (mediāna 25 + Gaussian 40) un nobīda punktu uz iekšu. Pa pikselim griežot,
    mala saplīst robos; gar kontūru tā paliek gluda.

    Nav agresīva erozija: kur tekstūra sākas uzreiz, dziļums ir minimālais.
    """
    from scipy.ndimage import (gaussian_filter1d, median_filter,
                               uniform_filter)

    dtype_in = binary.dtype
    m = binary.astype(bool)
    if not m.any() or m.all():
        return binary, {"applied": False}
    h, w = m.shape
    din = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 5)
    core = m & (din > 60)
    if core.sum() < 2000:
        return binary, {"applied": False, "reason": "mazs apģērbs"}

    lum = rgb.astype(np.float32).mean(axis=2)
    # Augstfrekvences enerģija: |L − lokālais vidējais|. Audumam 11-22, ēnai 1-4.
    tex = np.abs(lum - uniform_filter(lum, 5))
    fabric_tex = float(np.median(tex[core]))
    thr = tex_ratio * fabric_tex
    if fabric_tex < 3.0:                       # ļoti gluds audums: kritērijs nedrošs
        return binary, {"applied": False, "reason": "audums bez tekstūras"}

    cnts, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return binary, {"applied": False}
    c = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float64)
    n_pts = len(c)
    if n_pts < 64:
        return binary, {"applied": False}

    dd = np.diff(np.vstack([c, c[:1]]), axis=0)
    tng = dd / np.maximum(np.linalg.norm(dd, axis=1, keepdims=True), 1e-6)
    nrm = np.stack([-tng[:, 1], tng[:, 0]], 1)
    probe = (c + 6 * nrm).astype(int)
    probe[:, 0] = np.clip(probe[:, 0], 0, w - 1)
    probe[:, 1] = np.clip(probe[:, 1], 0, h - 1)
    nrm[~m[probe[:, 1], probe[:, 0]]] *= -1.0   # normāles uz IEKŠU

    def _samp(i, d):
        x, y = c[i]
        xx = int(round(x + nrm[i, 0] * d))
        yy = int(round(y + nrm[i, 1] * d))
        if not (0 <= xx < w and 0 <= yy < h) or not m[yy, xx]:
            return np.nan
        return tex[yy, xx]

    depths = np.zeros(n_pts, np.float32)
    for i in range(n_pts):
        vals = np.array([_samp(i, d) for d in range(4, max_px + 1)])
        if np.isnan(vals).sum() > len(vals) - 10:
            continue
        depths[i] = max_px
        for j in range(len(vals) - 3):
            trio = vals[j:j + 3]
            if np.isnan(trio).any():
                continue
            if (trio > thr).all():             # tekstūra atgriezusies
                depths[i] = j + 4
                break
    del lum, din, core   # NB: `tex` jāpaliek — to lasa iekšējā `_samp`

    kept = int((depths < 4).sum())
    if kept > n_pts * 0.85:                    # gandrīz nekur nav ko griezt
        return binary, {"applied": False, "reason": "tekstūra visur klāt"}

    # Izlīdzina GAR KONTŪRU. Mediāna vispirms — tā nespēj izplest atsevišķu
    # lielu vērtību pāri kaimiņiem; Gauss pēc tam noņem atlikušos pakāpienus.
    depths = median_filter(depths, size=25, mode="wrap")
    depths = gaussian_filter1d(depths, 40, mode="wrap")
    np.minimum(depths, float(max_px), out=depths)

    # --- 1b. solis: pakāpienu pievilkšana pie gludās līnijas ----------------
    # ISNet seko papīra ēnas mēlei un vietām dod taisnstūra pakāpienus
    # (aptuveni 15 px dziļus). Uz balta fona tie lasās kā robaina mala, kas
    # produkcijas bildē nav pieņemama. Risinājums: salīdzina kontūru ar tās
    # izlīdzinātu versiju un pievelk tikai tad, ja novirze ir neliela
    # (<= SNAP). Lielas novirzes — īstas apģērba formas — paliek neskartas.
    pts = c + nrm * depths[:, None]
    winsz, snap_px = 35, 14.0
    ker = np.ones(2 * winsz + 1) / (2 * winsz + 1)
    padp = np.vstack([pts[-winsz:], pts, pts[:winsz]])
    smooth_p = np.stack([np.convolve(padp[:, 0], ker, "valid"),
                         np.convolve(padp[:, 1], ker, "valid")], 1)
    dev = np.linalg.norm(pts - smooth_p, axis=1)
    wt = np.clip(1.0 - (dev / snap_px) ** 2, 0, 1)
    wt = gaussian_filter1d(wt, winsz * 0.5, mode="wrap")[:, None]
    pts = pts * (1 - wt) + smooth_p * wt

    # Antialiasing (LINE_AA) vietā, kas iepriekš radīja pakāpienus, jo
    # MORPH_OPEN 11x11 uz raupjas kontūras veido taisnstūra iegriezumus.
    out = np.zeros((h, w), np.uint8)
    cv2.fillPoly(out, [np.round(pts * 16).astype(np.int32)], 255,
                 lineType=cv2.LINE_AA, shift=4)
    out = (out > 128).astype(np.uint8)
    out = cv2.morphologyEx(out, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n_cc, cc, st, _ = cv2.connectedComponentsWithStats(out, 8)
    if n_cc > 1:
        out = (cc == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    out = (out > 0).astype(dtype_in)

    # --- 2. solis: izvirzījumu (smaileņu) noņemšana ------------------------
    # Nobīdes metode nevar noņemt IZVIRZĪJUMU: šaurā smailē normāle iet
    # šķērsām, tāpēc tekstūra atgriežas jau pēc 4 px un griezums nenotiek.
    # Tieši tā izskatās atlikušais "zobiņš" jostasvietas līkumā (QA §35).
    # Risinājums: salīdzina kontūru ar tās pašas kontūras izlīdzinātu versiju
    # un atvelk atpakaļ TIKAI tos punktus, kas (a) izvirzās uz āru un
    # (b) ir pierādīti gludi, t.i. papīrs, nevis audums.
    # Drošības slieksnis: darbojas tikai uz teksturēta auduma. Krekla
    # aproces ir gludas (tekstūra ~6) — tās šis solis nedrīkst aiztikt.
    spike_info = {"spike_px": 0}
    if fabric_tex >= 10.0:
        cs2, _ = cv2.findContours(out, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if cs2:
            c2 = max(cs2, key=cv2.contourArea)[:, 0, :].astype(np.float64)
            n2 = len(c2)
            w1 = 35
            pad = np.vstack([c2[-w1:], c2, c2[:w1]])
            ker = np.ones(2 * w1 + 1) / (2 * w1 + 1)
            smooth = np.stack([np.convolve(pad[:, 0], ker, "valid"),
                               np.convolve(pad[:, 1], ker, "valid")], 1)
            protr = np.linalg.norm(c2 - smooth, axis=1)
            mid = smooth.astype(int)
            mid[:, 0] = np.clip(mid[:, 0], 0, w - 1)
            mid[:, 1] = np.clip(mid[:, 1], 0, h - 1)
            outward = np.where(out[mid[:, 1], mid[:, 0]] > 0, 1.0, -1.0)
            prof = ((smooth + c2) / 2).astype(int)
            prof[:, 0] = np.clip(prof[:, 0], 0, w - 1)
            prof[:, 1] = np.clip(prof[:, 1], 0, h - 1)
            ptex = tex[prof[:, 1], prof[:, 0]]
            kill = ((outward > 0) & (protr > 6.0) & (ptex < 0.45 * fabric_tex))
            if 0 < int(kill.sum()) <= n2 * 0.03:
                c3 = c2.copy()
                c3[kill] = smooth[kill]
                c3[:, 0] = np.where(kill, gaussian_filter1d(c3[:, 0], 8, mode="wrap"), c3[:, 0])
                c3[:, 1] = np.where(kill, gaussian_filter1d(c3[:, 1], 8, mode="wrap"), c3[:, 1])
                o2 = np.zeros((h, w), np.uint8)
                cv2.fillPoly(o2, [np.round(c3).astype(np.int32)], 1)
                o2 = cv2.morphologyEx(o2, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
                o2 = cv2.morphologyEx(o2, cv2.MORPH_OPEN, np.ones((11, 11), np.uint8))
                n_cc, cc, st, _ = cv2.connectedComponentsWithStats(o2, 8)
                if n_cc > 1:
                    o2 = (cc == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
                spike_px = int(out.sum()) - int(o2.sum())
                if spike_px > 0:
                    out = o2
                    spike_info = {"spike_px": spike_px, "spike_pts": int(kill.sum())}

    out = (out > 0).astype(dtype_in)
    return out, {"applied": True, "contour_pts": n_pts, **spike_info,
                 "fabric_texture": round(fabric_tex, 2),
                 "threshold": round(thr, 2),
                 "mean_trim_px": round(float(depths.mean()), 2),
                 "max_trim_px": int(depths.max()),
                 "removed_px": int(binary.sum()) - int(out.sum())}


def extend_foreground_colors(orig_np, binary, alpha_u8, max_dist=8):
    """Tieši ārpus maskas oriģināla RGB aizstāj ar tuvāko apģērba krāsu.

    Šie pikseļi nav apģērbs un MASTER kodolu neietekmē; krāsas paplašināšana
    tikai neļauj vecā galda/papīra krāsai noplūst daļēji caurspīdīgajā malas
    pārejā un RGBA samazināšanas laikā.
    """
    ext = orig_np.copy()
    if max_dist <= 0:
        return ext
    binary_u8 = (binary > 0).astype(np.uint8)
    dist, labels = cv2.distanceTransformWithLabels(
        1 - binary_u8, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    band = (binary_u8 == 0) & (dist <= float(max_dist)) & (alpha_u8 > 0)
    del dist
    if not np.any(band):
        return ext
    fg_y, fg_x = np.nonzero(binary_u8)
    src_idx = labels[band].astype(np.int64) - 1
    ext[band] = orig_np[fg_y[src_idx], fg_x[src_idx]]
    del labels, fg_y, fg_x, src_idx, band
    return ext

def resize_rgba_premultiplied(piece, new_size):
    """Lanczos samazināšana premultiplicētā alfa telpā.

    Parasta RGBA resize katru kanālu filtrē atsevišķi un caurspīdīgo pikseļu
    paslēptā vecā fona krāsa var ieplūst apģērba malā. Premultiplikācija to
    novērš; pēc resize krāsu atdala atpakaļ, kur alfa ir pietiekama.
    """
    if piece.size == new_size:
        return piece
    arr = np.asarray(piece.convert("RGBA"))
    prem = np.empty_like(arr)
    for y in range(0, arr.shape[0], 256):
        y2 = min(arr.shape[0], y + 256)
        a = arr[y:y2, :, 3:4].astype(np.uint16)
        prem[y:y2, :, :3] = ((arr[y:y2, :, :3].astype(np.uint16) * a + 127) // 255).astype(np.uint8)
        prem[y:y2, :, 3] = arr[y:y2, :, 3]
    del arr
    resized = np.asarray(Image.fromarray(prem).resize(new_size, Image.LANCZOS))
    del prem
    out = np.empty_like(resized)
    for y in range(0, resized.shape[0], 256):
        y2 = min(resized.shape[0], y + 256)
        a = resized[y:y2, :, 3]
        out[y:y2, :, 3] = a
        rgb_out = out[y:y2, :, :3]
        rgb_out[:, :] = BG
        valid = a >= 8
        if np.any(valid):
            vals = (resized[y:y2, :, :3].astype(np.uint16) * 255) // np.maximum(a, 1)[:, :, None].astype(np.uint16)
            rgb_out[valid] = np.clip(vals, 0, 255).astype(np.uint8)[valid]
    del resized
    return Image.fromarray(out)


def para_scale(binary_full: np.ndarray, full_shot_override=None, crop_box=None) -> float:
    """Mērogs, ar kādu `render_paraugs` pārvērš avotu 2000x2500 audeklā.

    Tā pati formula, ko lieto `render_paraugs`, lai ēnas garums master un
    gala bildē būtu viens un tas pats fiziskais lielums (QA §38).
    """
    h, w = binary_full.shape[:2]
    x0, y0, bw, bh = cv2.boundingRect(binary_full.astype(np.uint8))
    if bw <= 0 or bh <= 0:
        return 1.0
    coverage = float(binary_full.mean())
    full_shot = (coverage < 0.70) if full_shot_override is None else bool(full_shot_override)
    if full_shot:            # full_shot: proporcionāli centrālajā zonā
        return min((GARMENT_FILL_W * CANVAS[0]) / bw,
                   (GARMENT_FILL_H * CANVAS[1]) / bh)
    if crop_box is not None:
        fx0, fy0, fx1, fy1 = crop_box
        cw = max(1, int(round(fx1 * w)) - int(round(fx0 * w)))
        ch = max(1, int(round(fy1 * h)) - int(round(fy0 * h)))
        return max(CANVAS[0] / cw, CANVAS[1] / ch)
    return max(CANVAS[0] / w, CANVAS[1] / h)     # cover pa pilno kadru


def shadow_bg(shape, binary, dx, dy, blur, strength, falloff_px=None):
    """Fons #F3F3F3 + KONTAKTA ēna ar attāluma dilšanu. 2D uint8 (BG=243).

    Modelis:
        shade(d, θ) = strength · exp(−d/λ) · (ambient + (1−ambient)·w(θ))
    kur d = attālums ārpus maskas, bet w(θ) = cik ļoti punkts atrodas ēnas
    pusē (1 = pilnīgi pretējā gaismai, 0 = gaismas pusē).

    Kāpēc ne "nobīdīts izpludināts siluets" (iepriekšējais modelis): tāds
    dod VIENMĒRĪGU PLATO — tumšu joslu ar asu galu, kas izskatās kā uzlīme,
    un tās dziļumu nosaka viena konstante visā joslas platumā. Mērījums:
    maks. 22 L* zem fona, kas ir 26 % — virs profesionālā diapazona (8-20 %).
    Īsta ēna ir tumšākā TIEŠI pie malas un dilst (kontakta ēna).

    λ (falloff_px) ir audekla mērogā; avota mērogā to pārrēķina pēc platuma,
    lai master un 2000x2500 kadrs paliek konsekventi.
    """
    h, w = shape
    bgv = float(BG[0])
    m = binary.astype(bool)
    if not m.any() or m.all():
        return np.full((h, w), BG[0], np.uint8)

    if falloff_px is None:
        falloff_px = SHADOW_FALLOFF_PX * (w / float(CANVAS[0]))
    lam = max(float(falloff_px), 1.0)
    cutoff = max(float(falloff_px) * (SHADOW_CUTOFF_PX / SHADOW_FALLOFF_PX), 4.0)

    # Attālums ārpus apģērba + virziens prom no tā (distance transform gradients).
    dist = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
    gy, gx = np.gradient(dist)
    nrm = np.hypot(gx, gy) + 1e-6
    norm = math.hypot(dx, dy)
    if norm < 1e-6:
        u = np.zeros_like(dist)
    else:
        u = (gx * (dx / norm) + gy * (dy / norm)) / nrm
        np.clip(u, 0.0, 1.0, out=u)
        u = u * u * (3.0 - 2.0 * u)          # smoothstep: mīksta pāreja pusēs
    del gx, gy, nrm

    fall = np.exp(-dist / lam)
    # Logs: 1 līdz 45 % no robežas, tad smoothstep uz 0. Tas nogriež eksponenciālo
    # asti, kas citādi pārkāpj GATE_B tālā fona prasību (precīzi #F3F3F3).
    t = np.clip((dist - 0.45 * cutoff) / (0.55 * cutoff), 0.0, 1.0)
    window = 1.0 - t * t * (3.0 - 2.0 * t)
    shade = (strength * fall * window) * (SHADOW_AMBIENT + (1.0 - SHADOW_AMBIENT) * u)
    del dist, fall, u, window, t
    shade = cv2.GaussianBlur(shade, (0, 0), 1.2)   # tikai pret joslošanos
    out = np.clip(bgv * (1.0 - shade), 0.0, 255.0).astype(np.uint8)
    return out


def studio_shadow_bg(shape, binary, canvas_scale: float = 1.0):
    """Jauns studijas fons #F3F3F3 ar divkomponentu ēnu. 2D uint8 (243).

    Modelis (būvēts no nulles 2026-10-24; konstantes augšā):

      transmission = (1 - contactAO(d)) · (1 - castPeak · V(p)^gamma)

    kur d ir attālums ārpus maskas audekla pikseļos un V(p) ir laukuma
    gaismas redzamība: siluets tiek projicēts fiksētā studijas virzienā
    (43°, leju-labi) par OFFSET px un izpludināts ar penumbru
    sigma(d) = sigma0 + k·d — ēna ir asāka kontaktā un mīkstāka tālāk
    (contact hardening). Tas nav `blur(shift(mask))` plato: V pie pašas
    ēnas puses malas ir ~1 (nobīdītais siluets to klāj), bet gaismas pusē
    nobīde siluetu aiznes prom, tāpēc tur paliek tikai 1-2 px kontakta AO.

    V tiek rēķināta pusizšķirtspējā ar pieciem sigma līmeņiem un log-lineāru
    interpolāciju starp tiem; kontakta AO un gala logs — pilnā izšķirtspējā.
    `canvas_scale` ir audekla px uz vienu šī masīva px (MASTER avota mērogā
    to padod `para_scale`, gala audeklā tas ir 1.0), lai ēna abos mērogos
    būtu viens un tas pats fiziskais lielums (QA §38 princips). Aiz
    CUT loga beigām ēna ir tieši 0, tāpēc tālais fons paliek 243.
    """
    h, w = binary.shape[:2]
    bgv = float(BG[0])
    m = binary.astype(bool)
    if not m.any() or m.all():
        return np.full((h, w), BG[0], np.uint8)

    scale = float(max(canvas_scale, 1e-6))       # audekla px / masīva px
    arr_per_canvas = 1.0 / scale                 # masīva px / audekla px
    half_per_canvas = arr_per_canvas / 2.0       # pusizšķirtspējas px / audekla px

    # Attālums ārpus maskas audekla pikseļos (kontaktam un logam).
    dist_canvas = (cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
                   .astype(np.float32) * scale)

    # --- Metēnās ēnas redzamība pusizšķirtspējā ---
    hw, hh = max(1, w // 2), max(1, h // 2)
    mh = cv2.resize(m.astype(np.float32), (hw, hh), interpolation=cv2.INTER_AREA)
    ang = math.radians(STUDIO_SHADOW_ANGLE_DEG)
    ox = math.cos(ang) * STUDIO_SHADOW_OFFSET_PX * half_per_canvas
    oy = math.sin(ang) * STUDIO_SHADOW_OFFSET_PX * half_per_canvas
    mat = np.float32([[1, 0, ox], [0, 1, oy]])
    shifted = cv2.warpAffine(mh, mat, (hw, hh), flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    levels = [cv2.GaussianBlur(shifted, (0, 0), max(float(s) * half_per_canvas, 0.3))
              for s in STUDIO_SHADOW_SIGMA_LEVELS]
    del shifted
    # Attālums pusizšķirtspējā -> audekla px; no tā vēlamā penumbra.
    dh_canvas = (cv2.distanceTransform((mh <= 0.5).astype(np.uint8), cv2.DIST_L2, 5)
                 .astype(np.float32) / max(half_per_canvas, 1e-6))
    lev = np.asarray(STUDIO_SHADOW_SIGMA_LEVELS, dtype=np.float32)
    desired = np.clip(STUDIO_SHADOW_SIGMA0_PX + STUDIO_SHADOW_SIGMA_K * dh_canvas,
                      float(lev[0]), float(lev[-1])).astype(np.float32)
    del dh_canvas, mh
    V = np.zeros(desired.shape, np.float32)
    logs = np.log(lev)
    log_des = np.log(desired)
    for i in range(len(lev) - 1):
        sel = (desired >= lev[i]) & (desired <= lev[i + 1])
        if np.any(sel):
            u = np.clip((log_des[sel] - logs[i]) / (logs[i + 1] - logs[i]), 0.0, 1.0)
            V[sel] = levels[i][sel] * (1.0 - u) + levels[i + 1][sel] * u
    del levels, desired, log_des
    Vfull = cv2.resize(V, (w, h), interpolation=cv2.INTER_LINEAR)
    del V

    cast = STUDIO_SHADOW_PEAK * np.power(np.clip(Vfull, 0.0, 1.0),
                                         STUDIO_SHADOW_GAMMA)
    del Vfull
    cut0, cut1 = STUDIO_SHADOW_CUT_PX
    u = np.clip((dist_canvas - cut0) / (cut1 - cut0), 0.0, 1.0)
    cast *= 1.0 - u * u * (3.0 - 2.0 * u)
    del u
    contact = STUDIO_CONTACT_PEAK * np.exp(-dist_canvas / STUDIO_CONTACT_LAMBDA_PX)
    del dist_canvas
    shade = 1.0 - (1.0 - contact) * (1.0 - cast)
    del contact, cast
    delta = bgv * shade
    del shade
    delta[delta < 0.25] = 0.0
    return np.clip(bgv - delta, 0.0, 255.0).astype(np.uint8)


def render_paraugs(cutout_rgba: Image.Image, binary_full: np.ndarray,
                   full_shot_override=None, crop_box=None, shadow_angle=None):
    """2000x2500 kadrs pēc parauga. Atgriež (attēls, novietotās maskas attēls)."""
    W, H = CANVAS
    coverage = float(binary_full.mean())
    full_shot = (coverage < 0.70) if full_shot_override is None else full_shot_override
    if full_shot:
        x0, y0, bw, bh = cv2.boundingRect(binary_full)
        box = (int(x0), int(y0), int(x0 + bw), int(y0 + bh))
        piece = cutout_rgba.crop(box)
        # proporcionāli (NED deformēt) centrālajā zonā x 6-94%, y 10-90%
        scale = min((GARMENT_FILL_W * W) / piece.width, (GARMENT_FILL_H * H) / piece.height)
    else:
        # TUVPLĀNS = FULL-BLEED kā parauga detaļu kadros (lietotāja korekcija,
        # iterācija 4): attēls aizpilda visu 2000x2500 līdz malām, bez sānu joslām.
        # Parasti avots ir 3:4 un audekls 4:5, tāpēc cover nozīmē minimālu
        # centrālu apgriešanu augšā/apakšā. Ja `crop_box` ir kartēts, tas ir
        # normalizēts 4:5 logs, kas saglabā subjektu un ļauj apģērbam iziet
        # no kadra pie vismaz trim malām. MASTER paliek neapgriezts.
        if crop_box is not None:
            fx0, fy0, fx1, fy1 = crop_box
            box = (
                int(round(fx0 * cutout_rgba.width)),
                int(round(fy0 * cutout_rgba.height)),
                int(round(fx1 * cutout_rgba.width)),
                int(round(fy1 * cutout_rgba.height)),
            )
            piece = cutout_rgba.crop(box)
        else:
            piece = cutout_rgba
        scale = max(W / piece.width, H / piece.height)  # cover, nevis contain
    new_size = (max(1, round(piece.width * scale)), max(1, round(piece.height * scale)))
    piece_r = resize_rgba_premultiplied(piece, new_size)
    if not full_shot and (new_size[0] > W or new_size[1] > H):
        left = (new_size[0] - W) // 2
        top = (new_size[1] - H) // 2
        piece_r = piece_r.crop((left, top, left + W, top + H))
        new_size = (W, H)
    ox, oy = (W - new_size[0]) // 2, (H - new_size[1]) // 2
    # ēna gala mērogā no novietotās alfas
    alpha = np.asarray(piece_r.split()[3]) > 128
    placed = np.zeros((H, W), np.uint8)
    placed[oy:oy + new_size[1], ox:ox + new_size[0]] = alpha.astype(np.uint8)
    # Jaunais studijas modelis: virziens ir modeļa konstante (viena studijas
    # gaisma visam katalogam), tāpēc `shadow_angle` (avotā mērītais) šeit
    # apzināti vairs netiek lietots. Audekla mērogā canvas_scale=1.0.
    bg_gray = studio_shadow_bg((H, W), placed, canvas_scale=1.0)
    canvas = Image.fromarray(np.stack([bg_gray] * 3, axis=2)).convert("RGBA")
    del bg_gray
    canvas.alpha_composite(piece_r, (ox, oy))
    return canvas.convert("RGB"), Image.fromarray((placed * 255).astype(np.uint8)), full_shot

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="u2net")
    ap.add_argument("--threshold", type=int, default=128)
    ap.add_argument("--erode", type=int, default=1)
    ap.add_argument("--attempt", type=int, default=1)
    ap.add_argument("--only", default="")
    ap.add_argument("--mode", choices=["auto", "full", "closeup"], default="auto",
                    help="full = rembg siluets; closeup = GrabCut ar sēklām (iterācija 3)")
    ap.add_argument("--saved-mask", action="store_true",
                    help="neveic segmentāciju; pārrenderē no output/masks/*_MASK.png")
    ap.add_argument("--edge-feather", type=float, default=1.6,
                    help="iter.7 alfa pārejas pusplatums avota pikseļos")
    ap.add_argument("--edge-smooth", type=float, default=1.6,
                    help="iter.7 kontūras izlīdzināšanas Gaussian sigma avota pikseļos")
    ap.add_argument("--edge-contrast", type=float, default=1.65,
                    help="iter.7 alfa kontrasta atjaunošana pēc izlīdzināšanas")
    ap.add_argument("--edge-shift", type=float, default=0.0,
                    help="pozitīva vērtība pārbīda alfa malu uz iekšu (avota px)")
    ap.add_argument("--png-level", type=int, choices=range(10), default=6,
                    help="PNG bezzuduma kompresija: 6=ātruma/izmēra līdzsvars, 9=mazāks, bet lēns")
    args = ap.parse_args()

    session = None
    if not args.saved_mask and args.mode != "closeup":
        from rembg import remove, new_session
        session = new_session(args.model)
    for d in ["master", "paraugs", "masks"]:
        os.makedirs(f"{OUT}/{d}", exist_ok=True)

    files = sorted(
        f for f in os.listdir(SRC_DIR)
        if (f.startswith("MVIMG") or f.startswith("IMG_"))
        and f.lower().endswith((".jpg", ".jpeg"))
    )
    if args.only:
        files = [f for f in files if args.only in f]
    report = {"attempt": args.attempt, "model": args.model, "mode": args.mode,
              "threshold": args.threshold, "erode": args.erode,
              "saved_mask": bool(args.saved_mask),
              "png_level": args.png_level,
              "edge": {"feather_px": args.edge_feather,
                       "smooth_sigma": args.edge_smooth,
                       "contrast": args.edge_contrast,
                       "shift_px": args.edge_shift,
                       "foreground_extension_px": 8,
                       "premultiplied_resize": True},
              "images": {}}

    for fname in files:
        stem = os.path.splitext(fname)[0]
        with Image.open(f"{SRC_DIR}/{fname}") as _im:
            orig = ImageOps.exif_transpose(_im).convert("RGB")
        if args.saved_mask:
            saved_path = f"{OUT}/masks/{stem}_MASK.png"
            if not os.path.exists(saved_path):
                raise FileNotFoundError(f"--saved-mask: nav saglabātas maskas {saved_path}")
            print(f"[{stem}] pārrenderēju no saglabātās maskas ...", flush=True)
            binary = (np.asarray(Image.open(saved_path).convert("L")) > 128).astype(np.uint8)
            if binary.shape != (orig.height, orig.width):
                raise ValueError(f"Saglabātās maskas izmērs {binary.shape} nesakrīt ar oriģinālu {orig.size}")
        elif args.mode == "closeup":
            print(f"[{stem}] segmentēju ar GrabCut (tuvplāns, sēklas) ...", flush=True)
            binary = closeup_mask(orig, stem, args.erode)
        else:
            print(f"[{stem}] segmentēju ar {args.model} ...", flush=True)
            mask_img = remove(orig, session=session, only_mask=True)
            soft = np.asarray(mask_img.convert("L"))
            del mask_img
            binary = clean_mask(soft, args.threshold, args.erode)
            del soft
        coverage = float(binary.mean())
        print(f"  maskas segums: {coverage:.3f}", flush=True)

        # Iter.7 alfa: iekšiene = 255 (oriģināls 100%), ārpuse = 0; tikai malas
        # joslu izlīdzina un tai atjauno kontrastu. Binārā maska auditam nemainās.
        # Kompozīcija rindkopās (256 rindas) — pilna kadra float32 izraisīja OOM iterācijā 1.
        alpha_u8 = refine_alpha(binary, feather_px=args.edge_feather,
                                smooth_sigma=args.edge_smooth,
                                contrast=args.edge_contrast,
                                shift_px=args.edge_shift)
        orig_np = extend_foreground_colors(np.asarray(orig), binary, alpha_u8,
                                           max_dist=8)
        # Ēnas mērogs: master ir starpprodukts, kas tiek SAMAZINĀTS uz audeklu,
        # tāpēc ēnas garumam jābūt izteiktam TAJĀ PAŠĀ mērogā pēc samazinājuma.
        # Bez šī master ēna pēc ielīmēšanas iznāca 14.2 px, kamēr gala bildei
        # 18 px -> GATE_R references rekonstrukcija rādīja fona atšķirību 8-9
        # tur, kur izvadē ir viegla ēna, bet referencei nav (QA §38).
        _psc = para_scale(binary)
        bg_gray = studio_shadow_bg(binary.shape, binary, canvas_scale=_psc)
        h, w = binary.shape
        master = np.empty((h, w, 3), np.uint8)
        for y in range(0, h, 256):
            y2 = min(h, y + 256)
            a = (alpha_u8[y:y2].astype(np.float32) / 255.0)[..., None]
            blended = orig_np[y:y2].astype(np.float32) * a + bg_gray[y:y2, :, None].astype(np.float32) * (1.0 - a)
            master[y:y2] = np.clip(blended + 0.5, 0, 255).astype(np.uint8)
            del a, blended
        # Bezzuduma PNG kompresija: noklusētais 6. līmenis ir izmērīts
        # ātruma/krātuves līdzsvars; 9. līmenis ietaupa maz, bet ir ~4x lēnāks.
        Image.fromarray(master).save(
            f"{OUT}/master/{stem}_MASTER_1to1.png", optimize=True,
            compress_level=args.png_level)
        del master, bg_gray
        Image.fromarray((binary * 255).astype(np.uint8)).save(
            f"{OUT}/masks/{stem}_MASK.png", optimize=True,
            compress_level=args.png_level)
        Image.fromarray(alpha_u8).save(
            f"{OUT}/masks/{stem}_ALPHA.png", optimize=True,
            compress_level=args.png_level)

        cutout = Image.fromarray(orig_np).convert("RGBA")
        del orig_np
        cutout.putalpha(Image.fromarray(alpha_u8))
        del alpha_u8
        if args.saved_mask:
            override = False if stem[-6:] in CLOSEUP_SEEDS else True
        else:
            override = False if args.mode == "closeup" else (True if args.mode == "full" else None)
        crop_box = None if override else CLOSEUP_CROPS.get(stem[-6:])
        paraugs, placed_mask, full_shot = render_paraugs(
            cutout, binary, override, crop_box=crop_box)
        paraugs.save(f"{OUT}/paraugs/{stem}_PARAUGS_2000x2500.jpg", quality=95)
        placed_mask.save(f"{OUT}/masks/{stem}_PARAUGS_MASK.png")
        report["images"][stem] = {"coverage": round(coverage, 4),
                                  "full_shot": bool(full_shot),
                                  "closeup_crop": crop_box,
                                  "source_size": list(orig.size)}
        print(f"  saglabāts MASTER + PARAUGS (pilnais kadrs: {full_shot})", flush=True)
        del cutout, paraugs, placed_mask, binary, orig
        import gc; gc.collect()

    with open(f"{OUT}/report_maker.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    # Krātuves higiēna: pēc katras palaišanas redzams projekta izmērs, lai
    # vecie/diagnostikas faili neuzkrātos nemanāmi.
    total_bytes = 0
    for root, _, names in os.walk("/home/user/loop_bildes"):
        for name in names:
            try:
                total_bytes += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    print(f"KRĀTUVE: loop_bildes = {total_bytes / 1048576:.1f} MB")
    print("MAKER DONE")

if __name__ == "__main__":
    main()
