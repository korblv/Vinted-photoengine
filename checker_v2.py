#!/usr/bin/env python3
"""WORKFLOW V2.1 CHECKER — neatkarīga gala bilžu verifikācija.

Vārti:
  A2: MASTER kodolā jābūt tieši `grade(original)` ar saglabāto LUT
      (maks. atšķirība <= 1). Papildus kontrolē, ka grade kodolā
      nenogriež vairāk par 2% pikseļu.
  B : tālais fons 100% #F3F3F3.
  C : maskas segums 15–98%, lielākā komponente >=95%.
  D : PARAUGS ir 2000x2500 un stūri nav caurspīdīgi/nepareizi.
  F : tuvplānam audums sniedzas līdz vismaz 3 malām.
  H : alfa mala ir precīza (kodols 255, ārpus >5px 0, daļēja alfa šaurā joslā).
  T : kopējais laiks max 25 s/bilde (mērķis 20 s).
  L : **brīdinājums, nevis bloķētājs** — papīra noplūde maskā.
      `pass` vienmēr ir None, tāpēc tas nekad neietekmē ALL_PASS.
      Skatīt `advisory_verdict` / `leak_pct_of_fg` un `PAPIRA_NOPLUDES_QA.md`.
  Q : audums ārpus maskas — auduma tekstūras pikseļi šauros silueta
      līčos/kanālos (pretējais virziens P). Sk. `lost_fabric_gate`.
  S : robežas pierādījums — nelīdzena kontūra segmentā, kur avota
      mala ir vāja/defokusēta. Sk. `boundary_evidence_gate`.

Checker apstrādā tikai maker ierakstus ar statusu `completed`.
`needs_seed_review`/`failed` ieraksti tiek uzskaitīti `_meta` sadaļā,
lai tie nevarētu klusām “pazust” no piegādes.
"""
import argparse
import json
import math
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage
from PIL import Image, ImageOps

# Neatkarības princips (produkcijas refaktors, solis 5): checker
# NEIMPORTĒ maker moduļus (workflow_v2 / loop). Sagaidāmās vērtības nāk
# no specifikācijas (00 dokuments §3/§5 un paraugu mērījumi), un
# realizācijas (LUT pielietojums, pagrieziens) ir lokālas — kopīga kļūda
# maker un checker kodā vairs nevar iziet cauri abiem. Vienīgais
# izņēmums: paper_leak tikai informatīvajiem L vārtiem, kuru `pass`
# vienmēr ir None un kuri ALL_PASS neietekmē.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:  # brīdinājuma vārti; ja modulis nav pieejams, tie vienkārši netiek rēķināti
    from paper_leak import leak_probe  # noqa: E402
except Exception:  # pragma: no cover
    leak_probe = None

OUT = _HERE / "output"
SRC_DIR = _HERE.parent / "uploads"

# Specifikācijas konstantes (apzināti NE no loop.py): ja maker tās
# kādreiz maina, checker atšķirību redz un vārti krīt, nevis peld līdzi.
SPEC_BG = 243         # #F3F3F3, izmērīts no parauga (00 §5, B vārti)
SPEC_FILL_W = 0.74    # pilna kadra aizpildījums platumā (QA §24)
SPEC_FILL_H = 0.78    # ... un augstumā
BG = SPEC_BG
# GATE_C: maskas STRUKTURĀLĀ integritāte, nevis bbox pārklājums.
# Vēsture: 0.60 slieksnis tika kalibrēts uz viena krekla (fill 0.760) un
# viltus-noraidīja bikses ar V-iecirtumu starp kājām (fill 0.591, 0 caurumu).
# Tagad primārais tests ir CAURUMI (tiešs mērījums tam, ko gāte grib — "tīkls"),
# un bbox fill paliek kā grīda pret rupju maskas izēšanu.
#
# MĒRĪTS (2026-10-23):
#   īstie:                krekls 0.760 / 0 caurumi,  bikses 0.591 / 0 caurumi
#   tīkls (25 caurumi):   0.586 / 24
#   milzīgs caurums:      0.543 / 0
#   tukšs rāmis:          0.295 / 1
#
# !! ZINĀMA VĀJUMA VIETA: 0.55 ir tikai 0.007 virs sintētiskā cauruma
#    gadījuma un 0.041 zem bikešu gadījuma. Tā ir DIVU paraugu robeža, nevis
#    statistiski pamatota. Pārskatīt, tiklīdz ir vairāk īstu apģērbu.
SILHOUETTE_FILL_MIN = 0.60            # saglabāts ziņošanai (vēsturiskā vērtība)
SILHOUETTE_FILL_FLOOR = 0.55          # grīda; sk. brīdinājumu augstāk
CHROMA_SHIFT_LIMIT = 2.5   # b* vienības; LUT drīkst nedaudz mainīt toni, ne krāsu
SPEED_LIMIT_S = 25.0
TARGET_SHAPE = (2500, 2000)  # (augstums, platums)

# --- GATE_R: piegādātā JPEG saskaņošana ar MASTER ------------------------
# Kāpēc: visas pārējās gātes lasa master, masku vai kadrējumu. Piegādāto
# PARAUGS_2000x2500.jpg saturiski skatīja tikai GATE_K (viens skalārs b*),
# tāpēc 2026-10-23 sešas apzinātas sabotāžas šajā failā izgāja ar ALL_PASS:
# izgudrots plankums, izdzēsts apģērbs, 6 px blur, 40 px nobīde, iekrāsošana,
# σ=12 troksnis. Šī gāte salīdzina piegādāto failu ar to pašu avotu, no kura
# taisīts MASTER, atkārtojot TIKAI ģeometriju (ne visu renderi).
#
# Sliekšņi NAV minēti, tie ir mērīti uz šīs bildes:
#   apģērba p99: bāze 16.0, likumīga JPEG kvalitāte q80..95 -> 16..20,
#                mazākā sabotāža 33.0  =>  viduspunkts ~24
#   fona p99:    bāze 1.0  =>  robeža 4.0 (fons ir plakans, tam jāsakrīt gandrīz precīzi)
#   malas enerģija: bāze 1.38 (asums), likumīgi 1.38..1.49,
#                blur -> 0.04, troksnis -> 2.19  =>  josla [0.80, 1.85]
# Pārkalibrēt, kad parādās bilde ar citu tekstūru vai citu JPEG kvalitāti.
GATE_R_P99_MAX = 24.0
GATE_R_BG_P99_MAX = 4.0
GATE_R_EDGE_MIN = 0.80
GATE_R_EDGE_MAX = 1.85

# --- GATE_Q: audums, kas palicis ĀRPUS maskas (zaudētais audums) ----------
# Kāpēc: visas pārējās gātes soda fonu maskas IEKŠPUSĒ (G, L, P) vai
# ieslēgtus caurumus (C). Neviens nemērīja pretējo kļūdu — audumu, ko
# maska pa ieleju kanāliem un līčiem gar robežu ir izmetusi ĀRĀ.
# MVIMG_20261020_160550 (A6) izgāja ar ALL_PASS, lai gan pret plate
# atsauci ārpus maskas bija 704 292 px auduma (baltais pleķis un
# svītras gatavajā kadrā; audits PROGRESS §99).
#
# Mērījums (lokāla matemātika, 1:4 mērogs): morfoloģiski aizvērta
# silueta (elipse R=10 ds px ~ 80 px kanāls) un maskas starpība ir
# kanālu/līču zona — lieli logi (kakla izgriezums) tur neietilpst.
# Zona ir aizdomīga, ja tās tekstūra līdzinās audumam, ne fonam.
#
# Kalibrēts uz 4 kadriem (2026-10-24, §102) — aizdomīgo px % no FG:
#   sliktais (160550 pad_retry A6): 4.27
#   labie: 160550 plate 0.031, 160601 0.065, 160538 0.101
# Robeža 1.0% ir ~10x virs labāko maksimuma un ~4x zem sliktā.
# Tā ir ČETRU paraugu robeža: pārskatīt, tiklīdz ir vairāk grupu.
GATE_Q_LIMIT_PCT = 1.0
GATE_Q_SCALE = 0.25
GATE_Q_CLOSE_R_DS = 10
GATE_Q_TEX_BG_RATIO = 2.5
GATE_Q_TEX_BG_ABS = 2.0
GATE_Q_TEX_FG_RATIO = 0.5

# --- GATE_S: robežas pierādījums (nelīdzena kontūra vājā avota malā) -----
# Kāpēc: GATE_Q mēra zaudēto audumu pēc tekstūras, bet defokusētā malā
# tekstūra ir zema un Q klusē; GATE_H mēra alfas profilu, ne kontūras
# novietojumu/ formu pret avotu. MVIMG_20261020_160601 (A9) izgāja ar
# ALL_PASS, lai gan augšējā kreisā mala defokusā bija roboti iekosta
# (lietotāja audits §110/§113; maks. kodums 94 px).
#
# Mērījums (lokāla matemātika, 1:4): gar lielāko ārējo kontūru ņem
# segmentus pa 32 paraugiem. Logs ir aizdomīgs, ja (a) vismaz 20%
# paraugu kontūra atkāpjas >=1 ds px no 21 parauga slīdošās mediānas
# (nelīdzena kontūra) UN (b) avota mediānā profila gradients šajā
# segmentā <=5 (avotā mala ir vāja/defokusēta — kontūras viļņojumam
# nav asas liecības, uz ko balstīties). Kadrs krīt, ja 160 paraugu
# posmā ir >=4 aizdomīgi logi.
#
# Kalibrēts PROGRESS §114 (sliktākais 160 posms): kontroles 1/0,
# sliktais A9 12, GrabCut atlikums 14. Slieksnis 4 = ~ģeometriskais
# vidus. ROBEŽA NAV STABILA STATISTIKA: tikai 2 kontroles no vienas
# sesijas. Pārskatīt pēc nākamajām grupām; kamēr nav vairāk datu,
# neskaidrs = kritiens ir apzināta izvēle (STOP > kluss PASS).
GATE_S_SCALE = 0.25
GATE_S_WIN_SAMPLES = 32
GATE_S_STEP_SAMPLES = 8
GATE_S_ROUGH_DS = 1.0
GATE_S_ROUGH_FRAC_MIN = 0.20
GATE_S_GRAD_MAX = 5.0
GATE_S_SPAN_SAMPLES = 160
GATE_S_LIMIT_WINDOWS = 4
GATE_S_MIN_WINDOWS = 4
RECONCILE_CANVAS = (2000, 2500)   # (platums, augstums) — kā CANVAS loop.py
REPORT_PATH = Path(OUT) / "report_v2.json"


# Bezzaudējumu ceturtdaļpagriezieni pulksteņrādītāja virzienā. Lokāla
# tabula (PIL ROTATE_* skaita pretēji pulkstenim), lai virziena kļūda
# maker pusē checkerī neatkārtotos. Ekvivalenci ar maker realizāciju
# piesprauž testi (TestCheckerIndependence).
_TURNS_CW = {0: None, 90: Image.ROTATE_270, 180: Image.ROTATE_180,
             270: Image.ROTATE_90}


def _quarter_turn_cw(img: Image.Image, degrees_cw: int) -> Image.Image:
    deg = int(degrees_cw) % 360
    if deg not in _TURNS_CW:
        raise ValueError(f"Atļauti tikai 0/90/180/270 grādi, saņemts: {degrees_cw}")
    op = _TURNS_CW[deg]
    return img if op is None else img.transpose(op)


def _apply_lut(rgb: np.ndarray, lut_rows) -> np.ndarray:
    """LUT pielietojums ar tīru NumPy indeksēšanu (ne cv2.LUT, ne maker
    funkciju): katra kanāla katram pikselim — tabulas vērtība pēc tā
    paša pikseļa. Punktveida attēlojums, tāpēc ar jebkuru citu pareizu
    realizāciju rezultāts sakrīt līdz bitam (pierāda testi). LUT rindas
    ir DATI no grade_profile_v2.json; to saturu checker neizdomā."""
    if len(lut_rows) != 3:
        raise ValueError(f"LUT vajag 3 kanālu rindas, ir {len(lut_rows)}")
    out = np.empty_like(rgb)
    for ch in range(3):
        table = np.asarray(lut_rows[ch], dtype=np.uint8)
        if table.shape != (256,):
            raise ValueError(f"LUT rinda {ch}: vajag 256 vērtības, ir {table.shape}")
        out[..., ch] = table[rgb[..., ch]]
    return out


def open_rgb(path: str | Path, rotation_cw: int = 0) -> np.ndarray:
    with Image.open(path) as im:
        img = ImageOps.exif_transpose(im).convert("RGB")
    # Ja maker avotu bezzaudējumi pagrieza vertikālā orientācijā, checker
    # salīdzinājumam piemēro to pašu pagriezienu (citādi A2 būtu veltīgs).
    return np.asarray(_quarter_turn_cw(img, int(rotation_cw or 0)))


def atomic_write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def largest_stats(m: np.ndarray):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m, 8)
    if n <= 1:
        return 0.0, lab, -1
    idx = 1 + int(np.argmax(stats[1:, 4]))
    return float(stats[idx, 4] / stats[1:, 4].sum()), lab, idx


def reconcile_reference(master_rgb: np.ndarray, mask: np.ndarray,
                        full_shot: bool, crop_box) -> np.ndarray:
    """Atkārto `render_paraugs` ĢEOMETRIJU uz MASTER, lai iegūtu references
    kadru 2000x2500 tādā pašā novietojumā kā piegādātais PARAUGS.

    Apzināti NEATKĀRTO renderi (ēna, alfa, asināšana): ēna jau ir masterī,
    un tieši tāpēc salīdzinājums ir godīgs — abiem jānāk no viena avota.
    """
    W, H = RECONCILE_CANVAS
    mh, mw = mask.shape
    pad_px = 0
    if full_shot:
        ys, xs = np.nonzero(mask)
        if len(xs) == 0:
            raise ValueError("maska tukša")
        x0, y0 = int(xs.min()), int(ys.min())
        x1, y1 = int(xs.max()) + 1, int(ys.max()) + 1
        pw, ph = max(1, x1 - x0), max(1, y1 - y0)
        scale = min((SPEC_FILL_W * W) / pw, (SPEC_FILL_H * H) / ph)
        # Master ēna sniedzas ARĪ ārpus apģērba bbox. Griežot tieši pa bbox,
        # tā tiek nogriezta pie bbox galējām malām (pa labi/kreisi/augšu/apakšu
        # no galējiem punktiem), un references fons tur paliek tīrs #F3F3F3,
        # kamēr izvadei tur ir ēna. Tas deva viltus GATE_R kritumu (bg_p99 7-9).
        # Tāpēc griežam ar rezervi; ģeometrija nemainās, jo `scale` paliek tas
        # pats un saturs tiek novietots ar nobīdi (sk. `ox`, `oy` zemāk).
        pad_px = int(math.ceil(70.0 / max(scale, 1e-6)))
    else:
        if crop_box is not None:
            fx0, fy0, fx1, fy1 = crop_box
            x0 = int(round(fx0 * mw)); y0 = int(round(fy0 * mh))
            x1 = int(round(fx1 * mw)); y1 = int(round(fy1 * mh))
        else:
            x0, y0, x1, y1 = 0, 0, mw, mh
        x0 = max(0, min(x0, mw - 1)); y0 = max(0, min(y0, mh - 1))
        x1 = max(x0 + 1, min(x1, mw)); y1 = max(y0 + 1, min(y1, mh))
        scale = max(W / (x1 - x0), H / (y1 - y0))
    src = master_rgb[y0:y1, x0:x1]
    nw = max(1, round((x1 - x0) * scale))
    nh = max(1, round((y1 - y0) * scale))
    im = Image.fromarray(src).resize((nw, nh), Image.LANCZOS)
    if not full_shot and (nw > W or nh > H):
        left, top = (nw - W) // 2, (nh - H) // 2
        im = im.crop((left, top, left + W, top + H))
        nw, nh = W, H
    ox, oy = (W - nw) // 2, (H - nh) // 2
    canvas = Image.new("RGB", (W, H), (BG, BG, BG))

    if full_shot and pad_px > 0:
        # Ārējais ēnas gredzens: master ēna sniedzas arī ārpus apģērba bbox.
        # To ņem no paplašināta griezuma un liek APAKŠĀ. Galvenais attēls
        # (precīzā bbox ģeometrija) tiek likts VIRS, tāpēc apģērba pikseļi
        # paliek 1:1 ar to, ko uzzīmēja `render_paraugs` — bez subpikseļa
        # nobīdes, kas uz džinsa pinuma radīja viltus starpību.
        cx0 = max(0, x0 - pad_px)
        cy0 = max(0, y0 - pad_px)
        cx1 = min(mw, x1 + pad_px)
        cy1 = min(mh, y1 + pad_px)
        ring = master_rgb[cy0:cy1, cx0:cx1]
        rw = max(1, round((cx1 - cx0) * scale))
        rh = max(1, round((cy1 - cy0) * scale))
        ring_im = Image.fromarray(ring).resize((rw, rh), Image.LANCZOS)
        rx = ox - int(round((x0 - cx0) * scale))
        ry = oy - int(round((y0 - cy0) * scale))
        canvas.paste(ring_im, (rx, ry))
        del ring, ring_im

    canvas.paste(im, (ox, oy))
    return np.asarray(canvas)


def reconcile_metrics(ref: np.ndarray, par: np.ndarray,
                      fore: np.ndarray, back: np.ndarray) -> dict:
    """Trīs neatkarīgi lielumi, katrs ķer citu defektu klasi."""
    d = np.abs(ref.astype(np.int16) - par.astype(np.int16)).max(axis=2)
    fore_p99 = float(np.percentile(d[fore], 99)) if fore.any() else 0.0
    fore_p95 = float(np.percentile(d[fore], 95)) if fore.any() else 0.0
    bg_p99 = float(np.percentile(d[back], 99)) if back.any() else 0.0
    g_ref = cv2.Laplacian(cv2.cvtColor(ref, cv2.COLOR_RGB2GRAY), cv2.CV_32F)
    g_par = cv2.Laplacian(cv2.cvtColor(par, cv2.COLOR_RGB2GRAY), cv2.CV_32F)
    e_ref = float(np.mean(np.abs(g_ref[fore]))) if fore.any() else 0.0
    e_par = float(np.mean(np.abs(g_par[fore]))) if fore.any() else 0.0
    return {
        "fore_p99": round(fore_p99, 2),
        "fore_p95": round(fore_p95, 2),
        "bg_p99": round(bg_p99, 2),
        "edge_ratio": round(e_par / max(e_ref, 1e-6), 3),
        "fore_px": int(fore.sum()),
        "bg_px": int(back.sum()),
    }


def gate_r_reconciliation(stem: str, maker_rec: dict, paraugs_path: Path,
                          placed_mask_path: Path) -> dict:
    """GATE_R: vai piegādātais JPEG satur to pašu, ko apstiprināja pārējās gātes."""
    mask_path = Path(maker_rec.get("mask_path") or (Path(OUT) / "masks" / f"{stem}_MASK.png"))
    master_path = Path(OUT) / "master" / f"{stem}_MASTER_1to1.png"
    if not master_path.is_file() or not mask_path.is_file():
        return {"pass": None, "skipped": True, "reason": "nav master vai maskas"}
    master = np.asarray(Image.open(master_path).convert("RGB"))
    mask = np.asarray(Image.open(mask_path).convert("L")) > 128
    if master.shape[:2] != mask.shape:
        return {"pass": False, "error": f"master {master.shape[:2]} != maska {mask.shape}"}
    full_shot = maker_rec.get("full_shot")
    if full_shot is None:
        full_shot = False
    crop_box = (maker_rec.get("timing") or {}).get("closeup_crop")
    if maker_rec.get("closeup_crop"):
        crop_box = maker_rec.get("closeup_crop")
    ref = reconcile_reference(master, mask, bool(full_shot), crop_box)
    del master
    par = np.asarray(Image.open(paraugs_path).convert("RGB"))
    if ref.shape != par.shape:
        return {"pass": False, "error": f"references {ref.shape} != paraugs {par.shape}"}

    placed = np.asarray(Image.open(placed_mask_path).convert("L")) > 128
    if placed.shape != ref.shape[:2]:
        return {"pass": False, "error": "novietotā maska citā izmērā"}
    fore = cv2.erode(placed.astype(np.uint8), np.ones((9, 9), np.uint8), 1).astype(bool)
    back_all = cv2.erode((~placed).astype(np.uint8), np.ones((9, 9), np.uint8), 1).astype(bool)
    del placed
    # Fona pārbaudi mēra TIKAI uz plakanā fona (references pikseļi = #F3F3F3).
    # Iemesls: ēnu paraugs pārrēķina NO JAUNA audekla mērogā
    # (`render_paraugs` -> shadow_bg blur=25), bet references rekonstrukcija
    # nes mastera ēnu avota mērogā (blur=35, kas pēc samazināšanas ir ~17 px).
    # Tāpēc ēnas gradientā abi attēli NEREDZAMI atšķiras pēc konstrukcijas:
    # uz šīs bildes plakanajā fonā p99=1.0, ēnas gradientā p99=6.0.
    # Mērot visu fona laukumu, gāte sodītu savu rekonstrukcijas artefaktu,
    # nevis izvades defektu. Ēnas zona paliek kā INFORMATĪVS lielums.
    flat_bg = (np.abs(ref.astype(np.int16) - BG).max(axis=2) <= 1)
    back = back_all & flat_bg
    del flat_bg
    if not fore.any():
        return {"pass": None, "skipped": True, "reason": "nav apģērba reģiona"}
    m = reconcile_metrics(ref, par, fore, back)
    if back_all.any():
        _d = np.abs(ref.astype(np.int16) - par.astype(np.int16)).max(axis=2)
        m["bg_shadow_p99"] = round(float(np.percentile(_d[back_all], 99)), 2)
        del _d
    m["bg_note"] = "bg_p99 mērīts tikai uz plakano fonu; bg_shadow_p99 = viss fons (informativi)"
    reasons = []
    if m["fore_p99"] > GATE_R_P99_MAX:
        reasons.append(f"apģērba p99 {m['fore_p99']} > {GATE_R_P99_MAX}")
    if m["bg_p99"] > GATE_R_BG_P99_MAX:
        reasons.append(f"fona p99 {m['bg_p99']} > {GATE_R_BG_P99_MAX}")
    if not (GATE_R_EDGE_MIN <= m["edge_ratio"] <= GATE_R_EDGE_MAX):
        reasons.append(f"malas enerģija {m['edge_ratio']} ārpus "
                       f"[{GATE_R_EDGE_MIN}, {GATE_R_EDGE_MAX}]")
    return {
        "pass": not reasons,
        **m,
        "limits": {"fore_p99": GATE_R_P99_MAX, "bg_p99": GATE_R_BG_P99_MAX,
                   "edge": [GATE_R_EDGE_MIN, GATE_R_EDGE_MAX]},
        "reasons": reasons,
        "rule": "piegādātais JPEG ir tas pats attēls, ko apstiprināja master/maskas gātes",
    }


def gate_p_verdict(regions) -> dict:
    """GATE_P: papīrs maskā pie kadra malas = segmentācijas ķīlis.

    Bloķējošs ir tikai reģions, kas pieskaras foto kadra malai un NAV
    audumā ieslēgts (`enclosed_by_fg` False): ķīlis ir papīrs, kas no
    ĀRPUSES ienāk maskā, tāpēc tā gredzenā ir īstais fons (alpha < 0.5).
    Pilnkadra makro kadros gludi auduma ieloki pie malas ir audumā
    ieslēgti, un bez šī dalījuma detektors tos bloķētu kā papīru
    (birkas makro `124406358`, 2026-10-24: 3 reģioni, visi ieslēgti,
    dE 9.6-13.9 pret papīra krāsu; sintētisks īsts ķīlis: nav
    ieslēgts, dE 0.46 — sk. testus un PROGRESS §70). Ieslēgtos
    reģionus vārti ziņo, bet nebloķē.
    """
    border = [r for r in regions if r.get("touches_photo_border")]
    blocking = [r for r in border if not r.get("enclosed_by_fg")]
    enclosed = [r for r in border if r.get("enclosed_by_fg")]
    return {
        "pass": len(blocking) == 0,
        "regions": len(blocking),
        "px": int(sum(r["area_px"] for r in blocking)),
        "max_depth_px": round(max([r["max_depth_px"] for r in blocking],
                                    default=0.0), 1),
        "enclosed_border_regions": len(enclosed),
        "enclosed_border_px": int(sum(r["area_px"] for r in enclosed)),
        "note": ("papīrs maskā, kas pieskaras kadra malai un nav audumā "
                 "ieslēgts; ieslēgtie = tikai ziņojums (sk. gate_p_verdict)"),
    }


def lost_fabric_gate(rgb: np.ndarray, alpha: np.ndarray) -> dict:
    """GATE_Q: auduma tekstūras pikseļi, ko maska pazaudējusi šauros
    līčos/kanālos gar silueta robežu (pretējā kļūda GATE_P virzienam).

    Zona = aizvērts(siluets) − siluets 1:4 mērogā (elipse
    R=GATE_Q_CLOSE_R_DS): ietilpst kanāli līdz ~80 px platumā,
    neietilpst īsti logi (kakla izgriezums, spraugas starp piedurkni
    un korpusu). Zonas pikselis ir aizdomīgs, ja tā lokālā tekstūra
    (pelēktoņu std, logs 5 ds px) sasniedz vismaz pusi no auduma
    kodola tekstūras un būtiski pārsniedz ārējā fona tekstūru.
    Slieksnis un kalibrācija: sk. GATE_Q_* komentāru faila augšā.
    """
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    g = cv2.resize(gray, None, fx=GATE_Q_SCALE, fy=GATE_Q_SCALE,
                   interpolation=cv2.INTER_AREA)
    m1 = ndimage.uniform_filter(g, 5, mode="nearest")
    m2 = ndimage.uniform_filter(g * g, 5, mode="nearest")
    tex = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    fg = cv2.resize((alpha > 127).astype(np.float32),
                    (g.shape[1], g.shape[0]),
                    interpolation=cv2.INTER_AREA) > 0.5
    if int(fg.sum()) < 100:
        return {"pass": False, "lost_fabric_pct": None,
                "limit_pct": GATE_Q_LIMIT_PCT,
                "note": "maska praktiski tukša — nav ko vērtēt"}
    ker = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (2 * GATE_Q_CLOSE_R_DS + 1, 2 * GATE_Q_CLOSE_R_DS + 1))
    closed = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_CLOSE, ker) > 0
    bg_lab, _ = ndimage.label(~fg)
    bords = (set(bg_lab[0].tolist()) | set(bg_lab[-1].tolist())
             | set(bg_lab[:, 0].tolist()) | set(bg_lab[:, -1].tolist()))
    bords.discard(0)
    outer = np.isin(bg_lab, list(bords)) if bords else np.zeros_like(fg)
    tex_bg = float(np.median(tex[outer])) if int(outer.sum()) >= 50 else 0.0
    core = ndimage.binary_erosion(fg, iterations=3)
    tex_fg = float(np.median(tex[core])) if core.any() \
        else float(np.median(tex[fg]))
    thr = max(GATE_Q_TEX_BG_RATIO * tex_bg, tex_bg + GATE_Q_TEX_BG_ABS,
              GATE_Q_TEX_FG_RATIO * tex_fg)
    cand = closed & (~fg) & (ndimage.distance_transform_edt(~fg) > 1)
    susp = cand & (tex >= thr)
    pct = 100.0 * float(susp.sum()) / float(fg.sum())
    return {
        "pass": bool(pct <= GATE_Q_LIMIT_PCT),
        "lost_fabric_pct": round(pct, 3),
        "limit_pct": GATE_Q_LIMIT_PCT,
        "suspicious_px_est": int(susp.sum()) * 16,
        "tex_bg": round(tex_bg, 2),
        "tex_fg": round(tex_fg, 2),
        "tex_threshold": round(thr, 2),
        "note": ("auduma tekstūras fons šauros silueta kanālos/līčos; "
                 "lieli logi (izgriezums) pēc konstrukcijas neietilpst"),
    }


def boundary_evidence_gate(rgb: np.ndarray, alpha: np.ndarray) -> dict:
    """GATE_S: nelīdzena silueta kontūra segmentā, kur avota mala ir
    vāja (defokuss / zems kontrasts) un tāpēc kontūras viļņojumam nav
    asas pikseļu liecības. Sk. GATE_S_* komentāru faila augšā.

    Logika 1:4 mērogā: gar lielāko ārējo kontūru segmentiem (32
    paraugi) salīdzina (a) kontūras nelīdzenumu pret tās pašas
    slīdošo mediānu un (b) avota mediānā normālprofila gradientu.
    Atsevišķi neviens no tiem nav defekts: asa mala drīkst būt
    nelīdzena (stūri, krokas), gluda kontūra drīkst iet cauri
    defokusam. Defekts ir KOMBINĀCIJA garā posmā.
    """
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    g = cv2.resize(gray, None, fx=GATE_S_SCALE, fy=GATE_S_SCALE,
                   interpolation=cv2.INTER_AREA)
    g = ndimage.gaussian_filter(g, 1.0)
    a_ds = cv2.resize(alpha, (g.shape[1], g.shape[0]),
                      interpolation=cv2.INTER_AREA)
    fg = a_ds >= 127
    if int(fg.sum()) < 100:
        return {"pass": False, "worst_span_windows": None,
                "limit_windows": GATE_S_LIMIT_WINDOWS,
                "note": "maska praktiski tukša — nav ko vērtēt"}
    cnts, _ = cv2.findContours(fg.astype(np.uint8), cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return {"pass": False, "worst_span_windows": None,
                "limit_windows": GATE_S_LIMIT_WINDOWS,
                "note": "kontūra nav atrasta"}
    contour = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float64)
    n = int(len(contour))
    if n < GATE_S_WIN_SAMPLES:
        return {"pass": None, "skipped": True, "contour_points": n,
                "note": "kontūra īsāka par vienu segmentu — nav vērtējama"}

    # Nelīdzenums: attālums līdz 21 parauga slīdošajai mediānai (cikliska).
    ext = np.vstack([contour[-10:], contour, contour[:10]])
    med = np.median(
        np.lib.stride_tricks.sliding_window_view(ext, 21, axis=0), axis=2)
    rough = np.linalg.norm(contour - med, axis=1)

    # Normālprofili: t=-8..+8 ds px, mīnuss = ārpusē, pluss = audumā.
    h, w = g.shape
    tangent = np.roll(contour, -5, axis=0) - np.roll(contour, 5, axis=0)
    tnorm = np.hypot(tangent[:, 0], tangent[:, 1])
    normal = np.zeros_like(contour)
    ok = tnorm > 0
    normal[ok, 0] = -tangent[ok, 1] / tnorm[ok]
    normal[ok, 1] = tangent[ok, 0] / tnorm[ok]

    def _fg_at(pts):
        xi = np.rint(pts[:, 0]).astype(int)
        yi = np.rint(pts[:, 1]).astype(int)
        inside = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
        vals = np.zeros(len(pts), bool)
        vals[inside] = fg[yi[inside], xi[inside]]
        return vals

    plus_fg = _fg_at(contour + 3.0 * normal)
    minus_fg = _fg_at(contour - 3.0 * normal)
    sign = np.zeros(n)
    sign[plus_fg & ~minus_fg] = 1.0
    sign[minus_fg & ~plus_fg] = -1.0
    t = np.arange(-8, 9, dtype=float)
    pts = (contour[:, None, :]
           + (sign[:, None] * normal)[:, None, :] * t[None, :, None])
    in_bounds = ((pts[..., 0] >= 0) & (pts[..., 0] <= w - 1)
                 & (pts[..., 1] >= 0) & (pts[..., 1] <= h - 1)).all(axis=1)
    prof = ndimage.map_coordinates(
        g, [pts[..., 1].ravel(), pts[..., 0].ravel()],
        order=1, mode="nearest").reshape(n, len(t))
    prof[~in_bounds | (sign == 0)] = np.nan

    evaluated = 0
    susp_starts = []
    susp_centers = []
    win_idx0 = np.arange(GATE_S_WIN_SAMPLES)
    for s in range(0, n, GATE_S_STEP_SAMPLES):
        idx = (s + win_idx0) % n
        block = prof[idx]
        rows_ok = np.isfinite(block).all(axis=1)
        if float(rows_ok.mean()) < 0.7:
            continue
        sm = ndimage.gaussian_filter1d(np.median(block[rows_ok], axis=0), 0.8)
        out_lvl, in_lvl = float(np.median(sm[:3])), float(np.median(sm[-3:]))
        c = in_lvl - out_lvl
        if abs(c) < 8:
            continue
        deriv = np.gradient(sm)
        ec = 3 + int(np.argmax(np.abs(deriv[3:14])))
        npf = (sm - out_lvl) / c
        lo = hi = None
        for j in range(ec, -1, -1):
            if npf[j] <= 0.1:
                lo = j
                break
        for j in range(ec, len(sm)):
            if npf[j] >= 0.9:
                hi = j
                break
        if lo is None or hi is None or hi <= lo:
            continue  # profils nav pakāpiens (ēnojums) — segmentu nevērtē
        evaluated += 1
        grad = float(abs(deriv[ec]))
        rough_frac = float(np.mean(rough[idx] >= GATE_S_ROUGH_DS))
        if rough_frac >= GATE_S_ROUGH_FRAC_MIN and grad <= GATE_S_GRAD_MAX:
            susp_starts.append(int(s))
            susp_centers.append(contour[idx].mean(axis=0))

    if evaluated < GATE_S_MIN_WINDOWS:
        return {"pass": None, "skipped": True,
                "evaluated_windows": int(evaluated),
                "contour_points": n,
                "note": ("pārāk maz vērtējamu robežas segmentu "
                         "(kontūra gandrīz tikai gar kadra malu)")}

    worst = 0
    worst_center = None
    if susp_starts:
        starts = np.array(susp_starts, dtype=int)
        centers = np.array(susp_centers, dtype=float)
        if n <= GATE_S_SPAN_SAMPLES:
            worst = int(len(starts))
            worst_center = centers.mean(axis=0)
        else:
            ext_starts = np.concatenate([starts, starts + n])
            j = 0
            for i in range(len(starts)):
                j = max(j, i)
                while (j + 1 < i + len(starts)
                       and ext_starts[j + 1] - ext_starts[i]
                       <= GATE_S_SPAN_SAMPLES):
                    j += 1
                cnt = int(j - i + 1)
                if cnt > worst:
                    worst = cnt
                    sel = [k % len(starts) for k in range(i, j + 1)]
                    worst_center = centers[sel].mean(axis=0)
    center_full = None
    if worst_center is not None:
        center_full = [int(round(float(v) / GATE_S_SCALE))
                       for v in worst_center]
    return {
        "pass": bool(worst < GATE_S_LIMIT_WINDOWS),
        "worst_span_windows": int(worst),
        "limit_windows": GATE_S_LIMIT_WINDOWS,
        "suspicious_windows": int(len(susp_starts)),
        "evaluated_windows": int(evaluated),
        "contour_points": n,
        "worst_center_xy_fullres": center_full,
        "note": ("nelīdzena kontūra segmentā ar vāju avota malas "
                 "gradientu (defokuss) — robeža nav pierādāma"),
    }


def _lut_only_crops(h: int, w: int) -> dict:
    """§131 specifikācijas ģeometrija (NEATKARĪGA no maker implementācijas —
    neatkarības princips faila augšā): MASTER = centra kvadrāts min(h, w);
    MAKRO = centra lodziņš ar malu attiecību precīzi 2000:2500, pēc iespējas
    liels. Ja maker kādreiz sāk griezt citur, šeit redzes starpību."""
    s = min(h, w)
    mx0, my0 = (w - s) // 2, (h - s) // 2
    if w / max(h, 1) <= 0.8:
        cw = w
        ch = int(round(cw / 0.8))
        if ch > h:
            ch = h
            cw = int(round(ch * 0.8))
    else:
        ch = h
        cw = int(round(ch * 0.8))
        if cw > w:
            cw = w
            ch = int(round(cw / 0.8))
    cx0, cy0 = (w - cw) // 2, (h - ch) // 2
    return {
        "master": {"x0": mx0, "y0": my0, "size": s},
        "makro": {"x0": cx0, "y0": cy0, "w": cw, "h": ch},
    }


def check_one_lut_only(stem: str, maker_rec: dict, lut_rows) -> dict:
    """§131 lut_only (pilnkadra makro) vārti.

    Patur: A2 (MASTER = LUT(oriģināls) centra kvadrāts bitu precizitātē),
    K (b* godīgums pret oriģināla to pašu kropi), D (formāts 2000x2500),
    R (piegādātais JPEG pret LUT rekonstrukciju bez asināšanas), T (ātrums).
    Izlaiž AR atzīmi "lut_only": B/C/F/H/L/P/Q/S — pilnkadrā nav fona, maskas,
    alfas, robežas, ko pārbaudīt. Nekādu klusu izlaišanu: katrs izlaistais
    vārts satur reason."""
    source = Path(maker_rec.get("source") or (Path(SRC_DIR) / f"{stem}.jpg"))
    master_p = Path(OUT) / "master" / f"{stem}_MASTER_1to1.png"
    makro_p = Path(OUT) / "paraugs" / f"{stem}_MAKRO_2000x2500.jpg"
    missing = [str(p) for p in (source, master_p, makro_p) if not p.is_file()]
    if missing:
        return {"ALL_PASS": False, "error": "trūkst failu", "missing": missing}

    orig = open_rgb(source, maker_rec.get("rotation_cw", 0))
    h, w = orig.shape[:2]
    geo = _lut_only_crops(h, w)
    graded = _apply_lut(orig, lut_rows)

    # A2: MASTER ir PNG -> jāsakrīt bitu precizitātē ar LUT centra kvadrātu.
    m = geo["master"]
    sq = graded[m["y0"]:m["y0"] + m["size"], m["x0"]:m["x0"] + m["size"]]
    master = open_rgb(master_p)
    if master.shape != sq.shape:
        shape_err = f"MASTER forma {master.shape} != gaidītā {sq.shape}"
        del master, graded, orig
        return {"ALL_PASS": False, "error": shape_err}
    diff = np.abs(master.astype(np.int16) - sq.astype(np.int16)).max(axis=2)
    max_diff = int(diff.max())
    core_n = int(sq.shape[0] * sq.shape[1])
    clipped = ((sq <= 2) | (sq >= 253)).any(axis=2)
    clipped_pct = float(clipped.mean() * 100)
    del master, diff, clipped

    # K un R: MAKRO pret oriģināla/LUT to pašu centra 4:5 kropi.
    k = geo["makro"]
    with Image.open(makro_p) as im:
        makro_size = im.size
        out_rgb = np.asarray(im.convert("RGB")) if makro_size == (2000, 2500) else None
    chroma_check = {"pass": None, "shift_b": None, "limit": CHROMA_SHIFT_LIMIT,
                    "note": "nav 2000x2500 MAKRO"}
    gate_r = {"pass": None, "skipped": True, "note": "nav 2000x2500 MAKRO"}
    if out_rgb is not None:
        src_crop = orig[k["y0"]:k["y0"] + k["h"], k["x0"]:k["x0"] + k["w"]]
        lut_crop = graded[k["y0"]:k["y0"] + k["h"], k["x0"]:k["x0"] + k["w"]]
        ref_honest = np.asarray(
            Image.fromarray(src_crop).resize((2000, 2500), Image.LANCZOS))
        ref_recon = np.asarray(
            Image.fromarray(lut_crop).resize((2000, 2500), Image.LANCZOS))
        del src_crop, lut_crop
        from paper_leak import lab_chunked

        def _bstar(arr):
            v = arr.reshape(-1, 3)
            stride = max(1, len(v) // 60000)
            lab = lab_chunked(v[::stride].reshape(1, -1, 3).astype(np.float32))[0]
            return float(np.median(lab[:, 2]))

        b_out, b_ref = _bstar(out_rgb), _bstar(ref_honest)
        shift = b_out - b_ref
        chroma_check = {
            "pass": bool(abs(shift) <= CHROMA_SHIFT_LIMIT),
            "shift_b": round(shift, 2),
            "limit": CHROMA_SHIFT_LIMIT,
            "b_out": round(b_out, 2),
            "b_ref": round(b_ref, 2),
            "note": "auduma b* pret oriģināla to pašu centra kropi (lut_only)",
        }
        fore = np.ones(out_rgb.shape[:2], bool)
        back = np.zeros_like(fore)
        mm = reconcile_metrics(ref_recon, out_rgb, fore, back)
        reasons = []
        if mm["fore_p99"] > GATE_R_P99_MAX:
            reasons.append(f"apģērba p99 {mm['fore_p99']} > {GATE_R_P99_MAX}")
        if not (GATE_R_EDGE_MIN <= mm["edge_ratio"] <= GATE_R_EDGE_MAX):
            reasons.append(f"edge_ratio {mm['edge_ratio']} ārpus "
                           f"[{GATE_R_EDGE_MIN}, {GATE_R_EDGE_MAX}]")
        gate_r = {
            "pass": bool(not reasons),
            "reasons": reasons,
            "note": ("lut_only: ref = LUT krops 2000x2500 bez asināšanas; "
                     "fona nav, tāpēc bg p99 nav definēts"),
            **mm,
        }
        del ref_honest, ref_recon, fore, back, mm
    del graded, orig

    total_s = maker_rec.get("timing", {}).get("total_s")

    def _skip(note):
        return {"pass": None, "skipped": True, "reason": note}

    why_full = "lut_only: pilnkadrs — nav fona/maskas/alfas/robežas (§131)"
    gates = {
        "GATE_A2_graded_pixels": {
            "pass": bool(max_diff <= 1 and clipped_pct <= 2.0),
            "core_px": core_n,
            "max_diff": max_diff,
            "clipped_core_pct": round(clipped_pct, 4),
            "note": "core = viss centra kvadrāts (nav maskas)",
        },
        "GATE_B_background": _skip(why_full),
        "GATE_C_mask": _skip(why_full),
        "GATE_D_format": {
            "pass": bool(makro_size == (2000, 2500)),
            "size": list(makro_size),
            "corners_info_only": None,
            "source_rotation_cw": int(maker_rec.get("rotation_cw") or 0),
        },
        "GATE_F_fullframe_closeup": _skip(
            "lut_only: visas malas mantotas no oriģināla (centra krops, §131)"),
        "GATE_H_edge": _skip(why_full),
        "GATE_K_chroma_honesty": chroma_check,
        "GATE_L_paper_leak": _skip(why_full),
        "GATE_P_paper_at_border": _skip(why_full),
        "GATE_Q_lost_fabric": _skip(why_full),
        "GATE_R_reconcile": gate_r,
        "GATE_S_boundary_evidence": _skip(why_full),
        "GATE_T_speed": {
            "pass": bool(isinstance(total_s, (int, float)) and float(total_s) <= SPEED_LIMIT_S),
            "total_s": total_s,
            "limit_s": SPEED_LIMIT_S,
            "method": maker_rec.get("mask_method"),
            "timing": maker_rec.get("timing", {}),
        },
    }
    gates["ALL_PASS"] = all(v["pass"] in (True, None) for v in gates.values())
    return gates


def _chroma_reference(src_im: Image.Image, mask_path: Path,
                      maker_rec: dict) -> np.ndarray:
    """§135: GATE_K atsauce ar RENDERA ĢEOMETRIJU (reconcile_reference —
    tā pati, ko lieto GATE_R): bbox kopskatam, crop lodziņš tuvplānam,
    vienmērīgs mērogs ar centra kropi 'original' stilam. Iepriekšējā
    būve sablīvēja visu avotu 2000x2500; kad avota un audekla proporcijas
    neatšķīrās tikai ar mērogu, `via` reģionā iekļuva arī papīrs un b_ref
    nobīdījās pret patieso auduma b* par līdz ~+2 (H_salocits treniņš)."""
    crop = (maker_rec.get("timing") or {}).get("closeup_crop")
    mask_full = np.asarray(
        Image.open(mask_path).convert("L").resize(src_im.size, Image.NEAREST)) > 128
    full_shot = maker_rec.get("full_shot")
    if full_shot is None:
        cov = float(mask_full.mean())
        ys, xs = np.nonzero(mask_full)
        bbox_frac = (((xs.max() - xs.min() + 1) / mask_full.shape[1])
                     * ((ys.max() - ys.min() + 1) / mask_full.shape[0])) if len(xs) else 0
        full_shot = bool(cov < 0.50 and bbox_frac > 0.35)
    return reconcile_reference(
        np.asarray(src_im), mask_full, bool(full_shot),
        crop if crop and len(crop) == 4 else None)


def check_one(stem: str, maker_rec: dict, lut_rows) -> dict:
    if maker_rec.get("status", "completed") != "completed":
        return {
            "ALL_PASS": False,
            "error": f"maker statuss nav completed: {maker_rec.get('status')}",
        }
    if maker_rec.get("lut_only"):
        return check_one_lut_only(stem, maker_rec, lut_rows)

    source = Path(maker_rec.get("source") or (Path(SRC_DIR) / f"{stem}.jpg"))
    mask_p = Path(maker_rec.get("mask_path") or (Path(OUT) / "masks" / f"{stem}_MASK.png"))
    master_p = Path(OUT) / "master" / f"{stem}_MASTER_1to1.png"
    alpha_p = Path(OUT) / "masks" / f"{stem}_ALPHA.png"
    paraugs_p = Path(OUT) / "paraugs" / f"{stem}_PARAUGS_2000x2500.jpg"
    placed_p = Path(OUT) / "masks" / f"{stem}_PARAUGS_MASK.png"
    required = [source, mask_p, master_p, alpha_p, paraugs_p, placed_p]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        return {"ALL_PASS": False, "error": "trūkst failu", "missing": missing}

    orig = open_rgb(source, maker_rec.get("rotation_cw", 0))
    master = open_rgb(master_p)
    if master.shape != orig.shape:
        return {
            "ALL_PASS": False,
            "error": f"MASTER forma {master.shape} != oriģināls {orig.shape}",
        }

    graded = _apply_lut(orig, lut_rows)
    mask = (np.asarray(Image.open(mask_p).convert("L")) > 128).astype(np.uint8)
    dist_in = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    core = dist_in >= 30
    diff = np.abs(master.astype(np.int16) - graded.astype(np.int16)).max(axis=2)
    core_maxdiff = int(diff[core].max()) if core.any() else 999
    core_n = int(core.sum())
    clipped = ((graded <= 2) | (graded >= 253)).any(axis=2)
    clipped_pct = float(clipped[core].mean() * 100) if core.any() else 100.0
    del diff, orig, graded, clipped

    # B: tālais fons ārpus ēnas jābūt tieši #F3F3F3.
    # 90 px bija kalibrēts uz 2000 px platu kadru. MASTER ir avota izšķirtspējā
    # (3072-4096), kur tā pati ēna aizņem proporcionāli vairāk pikseļu, tāpēc
    # fiksēts 90 px tur nogriež ēnu pārāk agri un vārts sodīja pareizu izvadi.
    # Tagad slieksnis ir tāds pats RELATĪVAIS attālums (90 px pie 2000 px platuma).
    # Tas nav vājināšana: sabotāžas testi joprojām krīt (sk. test_gate_r.py).
    dist_out = cv2.distanceTransform(1 - mask, cv2.DIST_L2, 5)
    far = dist_out >= 90.0 * (master.shape[1] / 2000.0)
    bg_ok = float((master[far] == BG).all(axis=1).mean()) if far.any() else 0.0
    del master, dist_out, far

    # C: maskas veselums.
    cov = float(mask.mean())
    largest_ratio, labels, largest_idx = largest_stats(mask)
    Hm, Wm = mask.shape
    silhouette_fill = 0.0
    interior_holes_n = 0
    interior_holes_px = 0
    interior_holes_large = False
    if largest_idx > 0:
        largest = labels == largest_idx
        ys, xs = np.where(largest)
        bbox = {
            "width_fraction": round(float((xs.max() - xs.min() + 1) / Wm), 4),
            "height_fraction": round(float((ys.max() - ys.min() + 1) / Hm), 4),
        }
        bwpx = int(xs.max() - xs.min() + 1)
        bhpx = int(ys.max() - ys.min() + 1)
        silhouette_fill = float(largest.sum()) / float(max(1, bwpx * bhpx))
        # GATE_C sākotnējais nolūks: noķert "tīklu" (audums + liels skaits
        # CAURUMU maskas iekšienē). `silhouette_fill` to darīja tikai
        # netieši, un tāpēc viltus-noraidīja bikses ar V-iecirtumu starp
        # kājām (MVIMG_20261020_161031: fill 0.5911 < 0.60, bet maska ir
        # perfekta — 0 caurumu).
        #
        # `binary_fill_holes` aizpilda tikai caurumus, kas NAV savienoti ar
        # rāmja malu, tāpēc V-iecirtums (atvērts uz leju) netiek skaitīts,
        # bet tīkla caurumi tiek. Tas ir tiešs mērījums tam, ko gāte grib.
        filled = ndimage.binary_fill_holes(largest)
        holes = filled & ~largest
        hl, hn = ndimage.label(holes)
        if hn:
            hsizes = ndimage.sum(holes, hl, range(1, hn + 1))
            interior_holes_n = int((hsizes >= 400).sum())
            interior_holes_px = int(hsizes.sum())
        else:
            interior_holes_n = 0
            interior_holes_px = 0
        interior_holes_large = interior_holes_n > 0
        mask_edges = {
            "top": round(float(largest[0].mean()), 4),
            "bottom": round(float(largest[-1].mean()), 4),
            "left": round(float(largest[:, 0].mean()), 4),
            "right": round(float(largest[:, -1].mean()), 4),
        }
        del largest, ys, xs
    else:
        bbox = {"width_fraction": 0.0, "height_fraction": 0.0}
        mask_edges = {"top": 0.0, "bottom": 0.0, "left": 0.0, "right": 0.0}
    del labels

    # H: precīza rafinētā alfa + informatīvas robežas metrikas.
    alpha = np.asarray(Image.open(alpha_p).convert("L"))
    core_alpha = float((alpha[core] == 255).mean()) if core.any() else 0.0
    dist_out_h = cv2.distanceTransform(1 - mask, cv2.DIST_L2, 5)
    far_out = dist_out_h >= 5
    out_alpha = float((alpha[far_out] == 0).mean()) if far_out.any() else 0.0
    partial = (alpha > 0) & (alpha < 255)
    bad_partial = int((partial & ((dist_out_h > 8) | (dist_in > 12))).sum())
    del dist_out_h
    soft_transition = (alpha > 16) & (alpha < 240)
    boundary_info = {
        "partial_alpha_pixels": int(partial.sum()),
        "soft_transition_pixels": int(soft_transition.sum()),
        "soft_transition_fraction": round(float(soft_transition.mean()), 6),
        "alpha_128_contour_pixels": int(((alpha >= 96) & (alpha <= 160)).sum()),
    }
    del partial, soft_transition, far_out

    # K: vai krāsu apstrāde nav izgudrojusi aukstumu/siltumu.
    # 2026-10-22: komplekts ar koka grīdu kā fonu deva b* nobīdi -4.9 abām
    # bildēm, jo baltā bilance rēķinājās no brūnā fona. Neviens gate to
    # neredzēja, jo visi pārbaudīja masku, formātu un fonu — nevis krāsu.
    chroma_check = {"pass": None, "shift_b": None, "limit": CHROMA_SHIFT_LIMIT,
                    "note": "nav pietiekamu paraugu"}
    try:
        via = np.asarray(Image.open(Path(OUT) / "masks" / f"{stem}_PARAUGS_MASK.png").convert("L")) > 128
        out_rgb = np.asarray(Image.open(paraugs_p).convert("RGB"))
        if via.any() and out_rgb.shape[:2] == via.shape:
            src_im = Image.open(source).convert("RGB")
            rot = int(maker_rec.get("rotation_cw") or 0)
            if rot:
                src_im = src_im.rotate(-rot, expand=True)
            # `source_size` maker glabā PĒC rotācijas, tāpēc asis vairs nav
            # jāmaina. Iepriekšējā versija tās mainīja vēlreiz un ieguva
            # "box can't exceed original image size" — gate klusi izslēdzās.
            sb = (maker_rec.get("source_size") or [0, 0])
            if sb[0] != src_im.width or sb[1] != src_im.height:
                src_im = src_im.resize(tuple(sb), Image.LANCZOS)
            # §135 (P_REZULTATI §7): atsauce ar rendera ģeometriju, sk.
            # _chroma_reference. b* mēra tikai apģērba novietojuma reģionā.
            ref_rgb = _chroma_reference(src_im, mask_p, maker_rec)
            if ref_rgb.shape[:2] == out_rgb.shape[:2]:
                from paper_leak import lab_chunked

                def _bstar(arr):
                    v = arr[via]
                    stride = max(1, len(v) // 60000)
                    lab = lab_chunked(v[::stride].reshape(1, -1, 3).astype(np.float32))[0]
                    return float(np.median(lab[:, 2]))

                b_out, b_ref = _bstar(out_rgb), _bstar(ref_rgb)
                shift = b_out - b_ref
                chroma_check = {
                    "pass": bool(abs(shift) <= CHROMA_SHIFT_LIMIT),
                    "shift_b": round(shift, 2),
                    "limit": CHROMA_SHIFT_LIMIT,
                    "b_out": round(b_out, 2),
                    "b_ref": round(b_ref, 2),
                    "ref_method": "render_geometry (reconcile_reference, §135)",
                    "note": "auduma dzeltenības (b*) nobīde pret oriģināla to pašu novietojumu",
                }
    except Exception as exc:
        chroma_check = {"pass": None, "error": f"{type(exc).__name__}: {exc}"}

    # L (brīdinājums): papīra noplūde maskā. Nekad nebloķē piegādi.
    # P (bloķējoša): papīrs maskas IEKŠPUSĒ, kas pieskaras kadra malai.
    #   Šis nav tas pats, kas L. L = "vai auduma iekšienē ir papīrveidīga
    #   tekstūra" (neskaidri -> tikai brīdinājums). P = "vai maska iekļauj fona
    #   gabalu, kas beidzas tieši kadra malā" -> tas ir segmentācijas defekts,
    #   kas iznākumā redzams kā bēšs ķīlis (161146: 8819 px, līdz x=3072).
    gate_l = {"pass": None, "advisory": True, "skipped": True}
    border_leak = {"pass": None, "regions": 0, "px": 0, "max_depth_px": 0.0}
    if leak_probe is not None:
        try:
            import time as _time
            _t0 = _time.perf_counter()
            src_im = Image.open(source).convert("RGB")
            rot = int(maker_rec.get("rotation_cw") or 0)
            if rot:
                src_im = src_im.rotate(-rot, expand=True)
            a_small = Image.fromarray(alpha)
            w, h = src_im.size
            longest = max(w, h)
            if longest > 3000:                      # alfa ir zemo frekvenču
                k = 3000.0 / longest
                src_im = src_im.resize((int(w * k), int(h * k)), Image.LANCZOS)
                a_small = a_small.resize(src_im.size, Image.BILINEAR)
            res = leak_probe(src_im, np.asarray(a_small, np.float32) / 255.0)
            gate_l = {
                "pass": None,
                "advisory": True,
                "skipped": False,
                "verdict": res["verdict"],
                "confidence": res["confidence"],
                "leak_px": res["leak_px"],
                "leak_pct_of_fg": res["leak_pct_of_fg"],
                "regions": len(res["regions"]),
                "paper_rgb": res["paper"]["rgb"],
                "thresholds": res["thresholds"],
                "seconds": round(_time.perf_counter() - _t0, 2),
            }
            border_leak = gate_p_verdict(res["regions"])
        except Exception as exc:                    # brīdinājums nedrīkst nogāzt čekeri
            gate_l = {"pass": None, "advisory": True, "skipped": True,
                      "error": f"{type(exc).__name__}: {exc}"}
            border_leak = {"pass": None, "error": f"{type(exc).__name__}: {exc}"}

    # Q (bloķējoša): audums ĀRPUS maskas šauros līčos/kanālos.
    # Pretējais virziens P: tur fons ieiet maskā, te audums izkrīt ārā.
    # S (bloķējoša): nelīdzena kontūra tur, kur avota mala ir vāja.
    # Kļūda šeit NEDRĪKST klusām pārvērsties par izlaistu pārbaudi
    # (kā brīdinājuma L), tāpēc izņēmums = vārti krīt.
    try:
        _src = Image.open(source).convert("RGB")
        _rot = int(maker_rec.get("rotation_cw") or 0)
        if _rot:
            _src = _src.rotate(-_rot, expand=True)
        _src_rgb = np.asarray(_src)
        gate_q = lost_fabric_gate(_src_rgb, alpha)
        gate_s = boundary_evidence_gate(_src_rgb, alpha)
        del _src, _src_rgb
    except Exception as exc:  # noqa: BLE001
        gate_q = {"pass": False, "error": f"{type(exc).__name__}: {exc}"}
        gate_s = {"pass": False, "error": f"{type(exc).__name__}: {exc}"}
    del alpha

    # D/F: gala formāts un tuvplāna pilnkadra pārklājums.
    with Image.open(paraugs_p) as im:
        paraugs_size = im.size  # (platums, augstums)
        paraugs_rgb = np.asarray(im.convert("RGB")) if paraugs_size == (2000, 2500) else None
    # Stūri vērtējam kā 8x8 LAUKUMU, nevis vienu pikseli. Viens pikselis
    # (piem. 1 px iecirtums maskā) nav piegādes defekts, bet iepriekšējais
    # noteikums tieši tāpēc noraidīja 161944.
    corner_mask_p = Path(OUT) / "masks" / f"{stem}_PARAUGS_MASK.png"
    corner_alpha = None
    corner_rgb = None
    corners_valid = False
    if paraugs_rgb is not None:
        k = 8
        A = paraugs_rgb
        corner_rgb = np.asarray([A[:k, :k].reshape(-1, 3).mean(axis=0),
                                 A[:k, -k:].reshape(-1, 3).mean(axis=0),
                                 A[-k:, :k].reshape(-1, 3).mean(axis=0),
                                 A[-k:, -k:].reshape(-1, 3).mean(axis=0)])
        with Image.open(corner_mask_p).convert("L") as cm:
            if cm.size == (2000, 2500):
                M = np.asarray(cm)
                corner_alpha = np.asarray([M[:k, :k].mean(), M[:k, -k:].mean(),
                                           M[-k:, :k].mean(), M[-k:, -k:].mean()])
        is_bg_colour = (np.abs(corner_rgb - np.asarray(BG, float)) <= 8).all(axis=1)
        if corner_alpha is not None:
            is_garment = corner_alpha >= 128
            corners_valid = bool((is_bg_colour | is_garment).all())
        else:
            corners_valid = bool(is_bg_colour.all())

    full_shot = maker_rec.get("full_shot")
    if full_shot is None:
        ys, xs = np.where(mask > 0)
        bbox_frac = ((xs.max() - xs.min() + 1) / Wm) * ((ys.max() - ys.min() + 1) / Hm) if len(xs) else 0
        full_shot = bool(cov < 0.50 and bbox_frac > 0.35)
    # --- GATE_F: kompozīcija ------------------------------------------------
    # Agrāk: "kreklam jāsasniedz >=3 malas". Tas piespieda full-bleed kadru
    # un tāpēc izslēdza iespēju taisīt produktu kadru ar fona malām (Slam Jam
    # stils), ko lietotājs prasīja 2026-10-23.
    # Tagad vārti sargā to, kas tiem jāsargā: **taisnu griezienu cauri
    # apģērbam**, ko rada novietošana ar nogriešanu (iznāca ielīmēts
    # taisnstūris). Katra mala tiek klasificēta:
    #   bleed  — krekls aiziet pāri malai, kontakts nelīdzens (dabiski)
    #   margin — mala ir tīrs fons ar >= MARGIN_MIN atstarpi
    #   cut    — krekls pieskaras malai pa GARU, TAISNU nogriezni (defekts)
    MARGIN_MIN = 0.05
    # Bija STRAIGHT_RUN / STRAIGHT_TOL (garākā taisnā kontakta robeža). Tie
    # nekad netika lietoti: izgudrotu griezienu jau nosaka `inherited` —
    # ja avotā tur bija fons, kontakts ir "cut" NEATKARĪGI no tā garuma.
    # Ilguma slieksnis bija vājāks signāls par izcelsmi, tāpēc izņemts.

    # Oriģinālās maskas malas: ja tur krekls IR, tad kontakts gatavajā kadrā
    # ir MANTOṪS (dabiska pāreja pāri malai). Ja avotā tur bija fons, bet
    # gatavajā kadrā ir krekls, tas ir IZGUDROTS grieziens.
    _sc = 255.0 if M.max() > 1 else 1.0      # maska var būt 0-255 vai 0/1
    # SVARĪGI (labojums 2026-10-23): avota kontaktu jāmēra ar TĀDU PAŠU joslas
    # platumu kā gala kadrā. Iepriekš avots tika mērīts pa vienu kolonnu/rindu
    # (M[:, 0]), bet gala kadrs pa 8 px joslu uz 3x samazinātas maskas (= 24 px
    # no 2000 px = 1.2 % platuma). Mīksta maskas mala pie x=0 deva 0.2555 vienā
    # kolonnā, kamēr tajā pašā malā 1.2 % joslā ir 0.6302 -> avots tika kļūdaini
    # atzīmēts kā "fons" un dabiska pāreja pāri malai kļuva par viltus "cut".
    # Tagad abas puses lieto vienas un tās pašas frakcijas.
    STRIP_FX = 24.0 / RECONCILE_CANVAS[0]               # 1.2 % platuma (left/right)
    STRIP_FY = 24.0 / RECONCILE_CANVAS[1]               # 0.96 % augstuma (top/bottom)

    def _src_strip(name):
        h, w = M.shape
        kx = max(1, int(round(STRIP_FX * w)))
        ky = max(1, int(round(STRIP_FY * h)))
        if name == "top":
            v = M[:ky, :].mean()
        elif name == "bottom":
            v = M[-ky:, :].mean()
        elif name == "left":
            v = M[:, :kx].mean()
        else:
            v = M[:, -kx:].mean()
        return round(float(v) / _sc, 4)

    src_edge = {n: _src_strip(n) for n in ("top", "bottom", "left", "right")}

    def _edge_report(pm):
        h, w = pm.shape
        k = 8
        out = {}
        for name, strip, along in (
            ("top", pm[:k, :], None), ("bottom", pm[-k:, :], None),
            ("left", pm[:, :k], "v"), ("right", pm[:, -k:], "v"),
        ):
            frac = float(strip.mean())
            # kontakta profils: kur gar malu krekls pieskaras (+-3 px)
            if along == "v":
                col = strip.mean(axis=1) >= 0.5          # pa y
                prof = col
            else:
                row = strip.mean(axis=0) >= 0.5          # pa x
                prof = row
            if frac >= 0.50:
                # garākais nepārtrauktais kontakts
                best = cur = 0
                for v in prof:
                    cur = cur + 1 if v else 0
                    best = max(best, cur)
                longest = best / max(len(prof), 1)
                inherited = src_edge[name] >= 0.50
                kind = "bleed" if inherited else "cut"
                out[name] = {"contact": round(frac, 4), "kind": kind,
                             "longest_run": round(longest, 3),
                             "source_contact": src_edge[name],
                             "inherited": bool(inherited)}
            else:
                out[name] = {"contact": round(frac, 4),
                             "kind": "margin" if (1.0 - frac) >= MARGIN_MIN else "cut",
                             "longest_run": 0.0}
        return out

    if full_shot:
        F_pass, edges = None, {}
    else:
        pm = (np.asarray(Image.open(placed_p).convert("L")) > 128)
        pm = pm[::3, ::3]
        edge_rep = _edge_report(pm)
        edges = {k2: v["contact"] for k2, v in edge_rep.items()}
        kinds = [v["kind"] for v in edge_rep.values()]
        F_pass = ("cut" not in kinds) and (kinds.count("bleed") >= 1 or kinds.count("margin") == 4)
        del pm

    # GATE_R: piegādātais JPEG pret master (sk. konstantes augšā)
    try:
        gate_r = gate_r_reconciliation(stem, maker_rec, paraugs_p, placed_p)
    except Exception as exc:                     # noqa: BLE001
        gate_r = {"pass": None, "skipped": True,
                  "error": f"{type(exc).__name__}: {exc}"}

    total_s = maker_rec.get("timing", {}).get("total_s")
    gates = {
        "GATE_A2_graded_pixels": {
            "pass": bool(core_maxdiff <= 1 and clipped_pct <= 2.0),
            "core_px": core_n,
            "max_diff": core_maxdiff,
            "clipped_core_pct": round(clipped_pct, 4),
        },
        "GATE_B_background": {
            "pass": bool(bg_ok >= 0.999),
            "far_bg_correct_pct": round(bg_ok * 100, 4),
        },
        "GATE_C_mask": {
            "pass": bool(0.15 <= cov <= 0.98 and largest_ratio >= 0.95
                        and not interior_holes_large
                        and silhouette_fill >= SILHOUETTE_FILL_FLOOR),
            "coverage": round(cov, 4),
            "largest_ratio": round(largest_ratio, 4),
            # Maskas laukums / bbox laukums. 161944 gadījumā 0.443: maska bija
            # "tīkls" (audums + pakaramais + milzīgi caurumi), kas izgāja cauri
            # gan seguma, gan lielākās komponentes pārbaudei.
            "silhouette_fill": round(silhouette_fill, 4),
            "silhouette_fill_min": SILHOUETTE_FILL_FLOOR,
            "silhouette_fill_floor": SILHOUETTE_FILL_FLOOR,
            "interior_holes": int(interior_holes_n),
            "interior_holes_px": int(interior_holes_px),
            "note": ("primārais tests = caurumi maskas iekšienē (tīkls); bbox fill "
                     "ir grīda pret rupju izēšanu. Sk. SILHOUETTE_FILL_FLOOR "
                     "brīdinājumu par divu paraugu robežu"),
            "bbox": bbox,
            "source_edges": mask_edges,
        },
        "GATE_D_format": {
            # GATE_D = FORMATS. Stūru krāsu pārbaude izņemta 2026-10-22:
            # tā nespēja atšķirt ēnu, mīksto alfu un oriģinālo papīru un
            # noraidīja gan īstu audumu (115/132), gan 1 px iecirtumu, gan
            # s3 gadījumu ar 289 mīkstas malas pikseļiem. Fona tīrību sedz
            # GATE_B (fons = BG, 100 %) un GATE_P (papīrs pie kadra malas).
            "pass": bool(paraugs_size == (2000, 2500)),
            "size": list(paraugs_size),
            "corners_info_only": bool(corners_valid),
            "corner_rgb_8x8": [ [int(v) for v in row] for row in (corner_rgb if corner_rgb is not None else []) ],
            "source_rotation_cw": int(maker_rec.get("rotation_cw") or 0),
        },
        "GATE_F_fullframe_closeup": {
            "pass": F_pass,
            "edges": edges,
            "edge_kinds": ({k2: v["kind"] for k2, v in edge_rep.items()}
                           if not full_shot else {}),
            "edge_detail": (edge_rep if not full_shot else {}),
            "full_shot": bool(full_shot),
                "rule": ("nav izgudrota grieziena: katra mala ir margin vai bleed, "
                     "kas mantots no oriģināla"),
        },
        "GATE_H_edge": {
            "pass": bool(core_alpha >= 0.999 and out_alpha >= 0.999 and bad_partial == 0),
            "core_opaque_pct": round(core_alpha * 100, 4),
            "outside_clear_pct": round(out_alpha * 100, 4),
            "bad_partial_px": bad_partial,
            "boundary_info": boundary_info,
        },
        "GATE_K_chroma_honesty": chroma_check,
        "GATE_L_paper_leak": gate_l,
        "GATE_P_paper_at_border": border_leak,
        "GATE_Q_lost_fabric": gate_q,
        "GATE_R_reconcile": gate_r,
        "GATE_S_boundary_evidence": gate_s,
        "GATE_T_speed": {
            "pass": bool(isinstance(total_s, (int, float)) and float(total_s) <= SPEED_LIMIT_S),
            "total_s": total_s,
            "limit_s": SPEED_LIMIT_S,
            "method": maker_rec.get("mask_method"),
            "timing": maker_rec.get("timing", {}),
        },
    }
    gates["ALL_PASS"] = all(v["pass"] in (True, None) for v in gates.values())
    return gates



def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("stems", nargs="*")
    args = ap.parse_args()

    maker = json.loads((Path(OUT) / "report_v2_maker.json").read_text(encoding="utf-8"))
    profile = json.loads((Path(OUT) / "grade_profile_v2.json").read_text(encoding="utf-8"))
    images = maker.get("images", {})
    all_stems = sorted(images)
    if args.stems:
        stems = sorted(set(args.stems) & set(all_stems))
    elif args.only:
        stems = [s for s in all_stems if args.only in s]
    else:
        stems = [s for s in all_stems if images[s].get("status", "completed") == "completed"]

    ignored = {
        stem: {
            "status": rec.get("status"),
            "error": rec.get("error"),
            "seed_proposal": rec.get("seed_proposal"),
        }
        for stem, rec in images.items()
        if rec.get("status", "completed") != "completed" and stem not in stems
    }
    report = {
        "_meta": {
            "workflow_version": maker.get("workflow_version"),
            "attempt": maker.get("attempt"),
            "checked": stems,
            "ignored_incomplete": ignored,
        }
    }

    for stem in stems:
        print(f"V2.1 CHECK {stem} ...", flush=True)
        # Katrai bildei ir sava LUT (ierakstīta renderēšanas laikā). Globālais
        # fails ir tikai atkāpšanās vecākām atskaitēm.
        rec_i = images.get(stem, {})
        lut_i = profile["lut_rgb"]
        ppath = rec_i.get("profile_path")
        if ppath and Path(ppath).is_file():
            try:
                lut_i = json.loads(Path(ppath).read_text(encoding="utf-8"))["lut_rgb"]
            except Exception:
                lut_i = profile["lut_rgb"]
        try:
            gates = check_one(stem, rec_i, lut_i)
        except Exception as exc:  # noqa: BLE001 - checker ziņo, nevis avarē bez atskaites
            gates = {"ALL_PASS": False, "error": f"{type(exc).__name__}: {exc}"}
        report[stem] = gates
        atomic_write_json(REPORT_PATH, report)

    image_results = [v for k, v in report.items() if not k.startswith("_")]
    npass = int(sum(1 for v in image_results if v.get("ALL_PASS")))
    print(f"V2.1 CHECKER: {npass}/{len(image_results)} PASS; neizturēja/nepabeigtas meta: {len(ignored)}")
    return 0 if image_results and npass == len(image_results) and not ignored else 2


if __name__ == "__main__":
    raise SystemExit(main())
