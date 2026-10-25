#!/usr/bin/env python3
"""WORKFLOW V2.1 MAKER — AI-first, ātrs un atsākams produktu foto pipeline.

AI (ISNet) veido tikai masku. Ja automātiskā QA AI masku noraida, izmanto
pārbaudīto sēklu bibliotēku; jaunam tuvplānam bez bibliotēkas ieraksta
ģenerē automātisku sēklu priekšlikumu un mēģina GrabCut ar to. Ja arī tas
neiztur QA, bilde tiek atzīmēta kā `needs_seed_review`, bet pārējā grupa
turpinās — viena problemātiska bilde vairs neaptur visu komplektu.

Apģērba saturs netiek ģenerēts/deformēts. Pirms kompozīcijas visam
komplektam piemēro vienu deterministisku Lightroom tipa LUT korekciju.
"""
import argparse
import gc
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, "/home/user/loop_bildes")
from loop import (  # noqa: E402
    CLOSEUP_CROPS,
    CLOSEUP_SEEDS,
    OUT,
    SRC_DIR,
    GARMENT_FILL_H,
    GARMENT_FILL_W,
    clean_mask,
    closeup_mask,
    extend_foreground_colors,
    decontaminate_rim,
    refine_alpha,
    render_paraugs,
    shadow_bg,
    studio_shadow_bg,
    STUDIO_SHADOW_ANGLE_DEG,
    STUDIO_SHADOW_OFFSET_PX,
    shadow_dir,
    para_scale,
    SHADOW_STRENGTH,
    SHADOW_FALLOFF_PX,
    measure_shadow_angle,
)

from engine.infra import (  # noqa: E402,F401
    ROTATIONS_CW, fit_size, normalize_rotation, parse_rotations,
    rotation_for, apply_quarter_turn, open_rgb, open_rgb_recorded,
    probe_source_image, sha256_file, atomic_write_text, atomic_write_json,
    save_image_atomic, save_gray_png, workspace_bytes,
    environment_problems, preflight,
)
from engine.provenance import (  # noqa: E402,F401
    DECONTAM_PARAMS, MASK_PROVENANCE_VERSION, append_mask_stage,
    decontam_needed, mask_provenance_path, read_mask_provenance,
    start_mask_provenance,
)
MODEL_PATH = Path("/var/tmp/rembg_home/models/isnet-general-use/isnet-general-use.onnx")

from engine.config import (  # noqa: E402,F401
    CFG, CONFIG_PATH, WORKFLOW_VERSION, load_config, _resolve_args,
    _effective_config, _config_sha256,
)


# ---------------------------------------------------------------------------
# Mazi infrastruktūras palīgrīki
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Masku provenance (produkcijas refaktors, solis 3): kurš posms ko izdarīja
# ar saglabāto masku. Kanoniskais `_MASK.png` pēc render ir PĒC-decontam
# (checker saskañai, QA §34), tāpēc bez vēstures rerender decontam
# pielietotu vēlreiz un maska katru reizi šaurinātos (izmērīts: vēl
# -102 868 px). Sidecars `{stem}_MASK.json` glabā posmu ķēdi ar faila
# sha256 pēc katras rakstīšanas; hash nesakritība (masku mainījis, piem.,
# closeup.py) vēsturi padara par nezināmu un uzvedība atgriežas pie
# vēsturiskā noklusējuma. Sk. PROGRESS §58.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# ISNet darba process
# ---------------------------------------------------------------------------

from engine.masks import (  # noqa: E402,F401
    TMP_SOFT, _mask_polygons, _mask_stats, ai_mask_qa, closeup_mask_qa,
    isnet_auto_worker, isnet_padded_mask, isnet_worker, pad_guards,
    boundary_evidence_metric, lost_fabric_metric, paper_profile,
    plan_closeup_crop, plate_mask,
    reclaim_inlets, repair_interior_holes, run_isnet, run_isnet_auto,
    save_seed_proposal, lut_only_verify, lut_only_sharpness,
)



# ---------------------------------------------------------------------------
# Masku QA un automātisko sēklu priekšlikums
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Papīra-konteksta RETRY un aizsargi (2026-10-22)
# ---------------------------------------------------------------------------
# Kāpēc: tīvs ISNet tuvplānā, kur audums aizpilda kadru, dod fragmentu
# (0.03-0.09 seguma). Papīra apmale dod modelim kontekstu un izlabo to uz
# 0.83-0.90. Bet apmale var arī pārplūst (gaišs audums uz gaiša papīra:
# 0.8075 pret patiesību 0.62), tāpēc tā ir RETRY ar diviem aizsargiem,
# nevis atsevišķs režīms. Sk. PAPIRA_NOPLUDES_QA.md 16.-17. sadaļu.
# PAD_* vērtības: config.toml [mask] (solis 4).



# --- Plakanās plāksnes ceļš ("plate_texture") ------------------------------
# Kad ISNet neredz apģērbu (balts vafeles adījums uz gaiša kartona), paliek
# mērījums: fons ir gluds (lokālais L* std ~2.8), audums ir teksturēts (~12.8).
# Sk. `plate_segment.py`. Šis NAV otrais modeļa ceļš: masku dod izmērīts
# signāls, un to pārbauda šī paša bloka QA, nevis modeļa pašapziņa.
# PLATE_* vērtības: config.toml [plate] (solis 4).



# --- Krāsu-attāluma rezerves ceļš ("chroma_seeded") -------------------------
# Papīra ķēde (ISNet -> apmales retry -> plate) uz NE-papīra fona melo:
# papīra krāsas novērtējums un aizsargi kļūst bezjēdzīgi (koka grīda,
# PROGRESS §74-§76). Ja tādā ainā apģērbs un fons krāsā ir tālu, masku dod
# sēklu paletes Lab telpā. Ceļš ir PĒDĒJAIS pirms STOP un sevi noraida, ja
# paletes nav pārliecinoši atdalāmas. Sk. `engine/chroma.py`; parametri
# config.toml [chroma].

from engine.chroma import chroma_mask, structural_qa  # noqa: E402,F401



# ---------------------------------------------------------------------------
# Krāsu profils
# ---------------------------------------------------------------------------

from engine.grade import (  # noqa: E402,F401
    apply_lut, build_lut, compute_grade_profile, linear_to_srgb,
    srgb_to_linear, _sample_clipping,
)



# ---------------------------------------------------------------------------
# Renderēšana, kolāža, ZIP
# ---------------------------------------------------------------------------

from engine.render import NO_DECONTAM, render_one, render_lut_only, write_collage  # noqa: E402,F401
from engine.report import (  # noqa: E402,F401
    CHECKER_REPORT_PATH, COLLAGE_PATH, DELIVERY_REPORT_PATH,
    PROFILE_PATH, REPORT_PATH, _persist_report, _set_run_meta,
    _summary, make_zip,
)

# §131: šīs palaišanas deklarētie pilnkadra (makro) kadri. Aizpilda
# main() no --lut-only pēc lietotāja pogas lēmuma; skaitliskā verifikācija
# notiek masku fāzē (lut_only_verify).
LUT_ONLY: set[str] = set()


# ---------------------------------------------------------------------------
# Galvenā plūsma
# ---------------------------------------------------------------------------

def _selected_files(args) -> list[str]:
    if args.files:
        files = []
        for item in args.files:
            files.extend(part.strip() for part in item.split(",") if part.strip())
        # Saglabā lietotāja secību, bet neatļauj ceļus ārpus uploads.
        return [Path(f).name for f in files]
    files = sorted(
        f for f in os.listdir(SRC_DIR)
        if (f.startswith("MVIMG") or f.startswith("IMG_"))
        and f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    if args.only:
        files = [f for f in files if args.only in f]
    return files


def choose_candidate(options):
    """Kandidātu izvēle Q trigerī (§109): starp strukturāli pieņemtajiem
    izvēlas mazāko zaudētā auduma % (lost_fabric_metric); neizšķirtā
    priekšroka union > current > plate — union pēc konstrukcijas
    nezaudē neko pret nevienu no abiem kandidātiem.
    options: [(name, q_pct | None, struct_accept), ...]."""
    rank = {"union": 0, "current": 1, "plate": 2}
    ok = [(q, rank.get(name, 9), name) for name, q, acc in options
          if acc and q is not None]
    if not ok:
        return "current"
    return min(ok)[2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*", help="precīzi failu vārdi no uploads (var atdalīt ar komatu)")
    ap.add_argument("--only", default="")
    ap.add_argument("--rotate", nargs="*", default=[],
                    help="bezspaudiena 90° soļu pagriešana: STEM:90|180|270 (grādi pulksteņrādītāja virzienā) vai STEM:cw/ccw; šķērsām gulošu apģērbu novieto vertikāli")
    ap.add_argument("--attempt", type=int, default=1)
    ap.add_argument("--closeup-proc-w", type=int, default=None,
                    help="noklusējums: config [run].closeup_proc_w")
    ap.add_argument("--png-level", type=int, choices=range(10), default=None,
                    help="noklusējums: config [run].png_level")
    ap.add_argument("--framing", choices=["auto", "slamjam", "original"], default=None,
                    help="slamjam = produkta kadrs ar fona malām (prasa, lai krekls avotā "
                         "būtu pilnībā kadrā); original = kadrs kā nofotografēts; "
                         "auto = slamjam, ja siluets slēgts, citādi original (noklusējums)")
    ap.add_argument("--resume", action="store_true", help="izmantot jau derīgas maskas no iepriekšējās atskaites, ja SHA-256 sakrīt")
    ap.add_argument("--rerender-saved", action="store_true", help="neveido maskas; pārrēķina profilu un pārrenderē no output/masks")
    ap.add_argument("--auto-closeup", action=argparse.BooleanOptionalAction, default=None,
                    help="jaunam tuvplānam mēģināt automātiski ģenerētas GrabCut sēklas")
    ap.add_argument("--auto-grabcut-iters", type=int, default=None,
                    help="noklusējums: config [run].auto_grabcut_iters")
    ap.add_argument("--pad", type=float, default=None,
                    help="apmales retry pad (noklusējums: config [mask].pad_retry); lieto loop_engine remēdijas")
    ap.add_argument("--wb-mode", choices=("auto", "identity"), default=None,
                    help="auto = baltā bilance no fona (kā līdz šim); identity = neitrāla, "
                         "ja fons nav uzticams pelēkais etalons")
    ap.add_argument("--overrides", default="",
                    help="JSON {stem: {pad: float|null, force_pad_retry: bool}} — loop_engine lēmumi")
    ap.add_argument("--force-pad-retry", action="store_true",
                    help="palaist apmales retry arī tad, ja ISNet maska tika pieņemta "
                         "(remēdija gadījumiem, kad maska iztur ISNet QA, bet krīt čekerī)")
    ap.add_argument("--no-decontam", nargs="*", default=[], metavar="STEM",
                    help="šiem stem: nepiemērot decontaminate_rim (makro kadri, kuros audums iet pāri malai)")
    ap.add_argument("--lut-only", nargs="*", default=[], metavar="STEM",
                    help="pilnkadra makro kadri (PROGRESS §131): bez maskas/fona/ēnas, "
                         "tikai grupas LUT; maker verifikācija atrod papīru un STOP, ja tāds redzams")
    ap.add_argument("--no-collage", action="store_true")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--make-zip", action="store_true")
    ap.add_argument("--zip-name", default="")
    ap.add_argument("--isnet-worker", nargs=2, metavar=("SRC", "DST"))
    ap.add_argument("--isnet-auto", nargs=6,
                    metavar=("SRC", "PLAIN", "PAD", "PADK", "FORCE", "TEXRELAXED"))
    args = ap.parse_args()
    args.overrides_map = {}
    if args.overrides:
        try:
            raw = json.loads(Path(args.overrides).read_text(encoding="utf-8"))
            args.overrides_map = {str(k): v for k, v in raw.items() if isinstance(v, dict)}
            print(f"Remēdiju pārraksti: {len(args.overrides_map)} bildēm", flush=True)
        except Exception as exc:
            print(f"Nevar nolasīt --overrides: {exc}", flush=True)
    ROTATIONS_CW.update(parse_rotations(args.rotate))
    NO_DECONTAM.update(str(x).strip() for x in (args.no_decontam or []) if str(x).strip())
    # §131: deklarētie pilnkadra (makro) kadri — tikai pēc lietotāja pogas
    # lēmuma; maker tos skaitliski verificē (lut_only_verify) un STOP, ja
    # kadrā tomēr redzams papīra fons.
    LUT_ONLY.update(str(x).strip() for x in (args.lut_only or []) if str(x).strip())
    _resolve_args(args)
    _set_run_meta(args)
    if args.isnet_worker:
        return isnet_worker(args.isnet_worker[0], args.isnet_worker[1])
    if args.isnet_auto:
        a = args.isnet_auto
        return isnet_auto_worker(a[0], a[1], a[2], float(a[3]), a[4] == "1", a[5])
    if args.make_zip:
        only = None
        if args.files:
            only = {Path(f).stem for f in _selected_files(args)}
        return make_zip(args.zip_name or None, only)

    for d in ["master", "paraugs", "masks", "audits"]:
        Path(OUT, d).mkdir(parents=True, exist_ok=True)
    TMP_SOFT.mkdir(parents=True, exist_ok=True)

    files = _selected_files(args)
    if args.preflight:
        result = preflight(files)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["ready"] else 2
    if not files:
        raise RuntimeError("Nav apstrādājamu bilžu")
    missing = [f for f in files if not (Path(SRC_DIR) / f).is_file()]
    if missing:
        print("V2.1 BLOĶĒTS: uploads mapē trūkst šo failu:", flush=True)
        for f in missing:
            print(f"  - {f}", flush=True)
        print(f"  Mape: {SRC_DIR}", flush=True)
        return 2
    # Ar --rerender-saved ISNet/rembg nav vajadzīgs. Ar --resume trūkstoša
    # vide bloķē tikai bildes, kurām tiešām jātaisa jauna maska.
    env_problems = [] if args.rerender_saved else environment_problems()

    old_images = {}
    if (args.resume or args.rerender_saved) and REPORT_PATH.is_file():
        try:
            old_images = json.loads(REPORT_PATH.read_text(encoding="utf-8")).get("images", {})
        except Exception:
            old_images = {}
    # Ar --resume/--rerender-saved pagriezieni no iepriekšējās atskaites
    # paliek spēkā, ja šajā palaišanā tie nav uzrādīti atkārtoti.
    for _stem, _rec in old_images.items():
        _r = _rec.get("rotation_cw")
        if _r:
            ROTATIONS_CW.setdefault(_stem, normalize_rotation(_r))

    records: list[dict] = []
    profile_s = None

    # 1. fāze: maskas. Kļūda vienā bildē tiek ierakstīta un grupa turpinās.
    for fname in files:
        stem = os.path.splitext(fname)[0]
        src = Path(SRC_DIR) / fname
        mask_path = Path(OUT) / "masks" / f"{stem}_MASK.png"
        source_sha = sha256_file(src)
        rot_cw = rotation_for(src)

        # Avota validācija PIRMS jebkā: citādi bojāts/tukšs fails aiziet līdz
        # ISNet apakšprocesam un tā traceback nonāk `error` laukā (sk. probe_source_image).
        _ok, _why = probe_source_image(src)
        if not _ok:
            rec = {
                "stem": stem, "source": str(src), "source_name": fname,
                "source_sha256": source_sha, "rotation_cw": rot_cw,
                "mask_path": str(mask_path), "status": "failed",
                "error": f"avots nav lasāms: {_why}",
                "timing": {"mask_total_s": 0.0},
            }
            records.append(rec)
            _persist_report(records, args.attempt, "masks", profile_s)
            print(f"[{stem}] IZLAISTS: {_why}", flush=True)
            continue

        # --- §131: pilnkadra (makro) kadrs — lut_only ceļš -----------------
        # Nav ko maskēt: fona nav. Pirms pieņemšanas skaitliska verifikācija
        # (paper_background_mask): papīra daļa katrā no 4 malu joslām < 1 %
        # un globāli < 2 % (config [lut_only]); pretējā gadījumā STOP ar
        # skaitļiem — nevis klusa pāreja uz normālo ceļu, kas tādu kadru
        # sabojātu ar izdomātu masku.
        if stem in LUT_ONLY:
            t_mask = time.perf_counter()
            try:
                orig = open_rgb_recorded(src, rot_cw)
                verify = lut_only_verify(orig)
                lapvar = lut_only_sharpness(orig)
                source_size = list(orig.size)
                del orig
                mask_s = time.perf_counter() - t_mask
                rec = {
                    "stem": stem, "source": str(src), "source_name": fname,
                    "source_sha256": source_sha, "rotation_cw": rot_cw,
                    "source_size": source_size,
                    "lut_only": True, "mask_method": "lut_only",
                    "lut_verify": verify,
                    "sharpness_lapvar": round(lapvar, 1),
                    "full_shot": None, "no_auto_crop": True,
                    "timing": {"verify_s": round(mask_s, 3),
                               "mask_total_s": round(mask_s, 3)},
                }
                if verify["pass"]:
                    rec["status"] = "mask_ready"
                    print(f"[{stem}] lut_only: verifikācija OK ({verify['reason']}); "
                          f"asums LapVar {lapvar:.0f} (informatīvi, bez vārtiem)",
                          flush=True)
                else:
                    rec["status"] = "failed"
                    rec["error"] = verify["reason"]
                    print(f"[{stem}] {verify['reason']}", flush=True)
            except Exception as exc:  # noqa: BLE001 - batch izolēšana pa bildēm
                rec = {
                    "stem": stem, "source": str(src), "source_name": fname,
                    "source_sha256": source_sha, "rotation_cw": rot_cw,
                    "lut_only": True, "mask_method": "lut_only",
                    "status": "failed",
                    "error": f"lut_only verifikācija krita: {type(exc).__name__}: {exc}",
                    "timing": {"mask_total_s": round(time.perf_counter() - t_mask, 3)},
                }
                print(f"[{stem}] FAIL: {rec['error']}", flush=True)
            records.append(rec)
            _persist_report(records, args.attempt, "masks", profile_s)
            gc.collect()
            continue

        old = old_images.get(stem)
        can_reuse = bool(
            old and mask_path.is_file()
            and int(old.get("rotation_cw") or 0) == rot_cw
            and (
                args.rerender_saved or old.get("source_sha256") == source_sha
            )
        )
        if can_reuse:
            rec = json.loads(json.dumps(old))
            rec.update({
                "source": str(src),
                "source_name": fname,
                "source_sha256": source_sha,
                "rotation_cw": rot_cw,
                "mask_path": str(mask_path),
                "status": "mask_ready",
            })
            rec.setdefault("timing", {"mask_total_s": 0.0})
            records.append(rec)
            _persist_report(records, args.attempt, "masks", profile_s)
            print(f"[{stem}] izmantoju saglabāto masku ({rec.get('mask_method')})", flush=True)
            continue
        if args.rerender_saved:
            rec = {
                "stem": stem, "source": str(src), "source_name": fname,
                "source_sha256": source_sha, "mask_path": str(mask_path),
                "status": "failed", "error": "--rerender-saved: nav derīgas saglabātas maskas/atskaites",
                "timing": {"mask_total_s": 0.0},
            }
            records.append(rec)
            _persist_report(records, args.attempt, "masks", profile_s)
            continue

        if env_problems:
            rec = {
                "stem": stem, "source": str(src), "source_name": fname,
                "source_sha256": source_sha, "mask_path": str(mask_path),
                "status": "failed",
                "error": "Vide nav gatava: " + "; ".join(env_problems) +
                         ". Palaid: python3 /home/user/loop_bildes/setup_v2.py",
                "timing": {"mask_total_s": 0.0},
            }
            records.append(rec)
            _persist_report(records, args.attempt, "masks", profile_s)
            continue

        print(f"[{stem}] v2.1 maska: ISNet ...", flush=True)
        t_mask = time.perf_counter()
        auto_info = None
        proposal_path = None
        retry_info_probe = None
        plate_info = None
        chroma_info = None
        pre_chroma_struct = None
        hole_info = None
        q_info = None
        no_auto_crop = False
        try:
            soft_path = TMP_SOFT / f"{stem}_{source_sha[:10]}_isnet_soft.png"
            pad_path = TMP_SOFT / f"{stem}_{source_sha[:10]}_isnet_pad.png"
            ov = args.overrides_map.get(stem, {})
            pad_value = ov.get("pad") or args.pad or CFG["mask"]["pad_retry"]
            force_here = bool(ov.get("force_pad_retry", args.force_pad_retry))

            # VIENS apakšprocess: imports + modeļa ielāde reizi, abi piegājieni turpat.
            # Agrāk retry bija otrs apakšprocess un `from rembg import` (2.3 s) maksāja divreiz.
            # (bija `t_net = time.perf_counter()`; `auto["wall_s"]` jau mēra
            #  visu apakšprocesa sienas laiku, tāpēc atsevišķs mainīgais bija lieks)
            auto = run_isnet_auto(src, soft_path, pad_path, pad_value, force_here)
            isnet_timing = {"wall_s": auto.get("wall_s", 0.0),
                            "init_s": auto.get("init_s"),
                            "predict_s": auto.get("predict_s"),
                            "proxy_size": auto.get("proxy_size")}
            qa = auto.get("qa") or {}
            orig = open_rgb_recorded(src, rot_cw)
            method = "isnet"
            fallback_s = 0.0
            auto_info = None
            closeup_qa = None
            proposal_path = None
            baseline_accepted = bool(qa.get("accept"))

            def _try_chroma():
                # Sēklas no ISNet mīkstajām maskām, kasšim kadram ir:
                # bāze vienmēr, apmales retry — ja tas tika palaists.
                softs = []
                for p in (soft_path, pad_path):
                    if p.is_file():
                        softs.append(np.asarray(Image.open(p).convert("L")))
                return chroma_mask(orig, softs)

            if baseline_accepted and not force_here:
                soft = np.asarray(Image.open(soft_path).convert("L"))
                soft_full = cv2.resize(soft, (orig.width, orig.height), interpolation=cv2.INTER_LINEAR)
                binary = clean_mask(soft_full, threshold=128, erode_px=1)
                del soft_full, soft
                full_shot = True
            else:
                if baseline_accepted:
                    print("  remēdija: piespiedu apmales retry (bāzes maska izturēja ISNet QA)",
                          flush=True)
                else:
                    print(f"  AI QA noraida: {qa.get('reason')} (segums={qa.get('coverage')})",
                          flush=True)

                retry_info = None
                if auto.get("retried") and pad_path.is_file():
                    t = time.perf_counter()
                    inner = Image.open(pad_path).convert("L")
                    m_pad = (np.asarray(inner.resize(orig.size, Image.LANCZOS)) > 128).astype(np.uint8)
                    inner.close()
                    guards = auto.get("guards") or {"overflow": None, "uncovered": None}
                    pad_qa = auto.get("pad_qa") or {}
                    retry_info = {
                        "pad": auto.get("pad"), "paper_rgb": auto.get("paper_rgb"),
                        "profile_relaxed": auto.get("profile_relaxed"),
                        "coverage": pad_qa.get("coverage"),
                        "largest": pad_qa.get("largest_component_ratio"),
                        "uncovered_qa": pad_qa.get("uncovered_fabric_fraction"),
                        "overflow": guards["overflow"],
                        "uncovered": guards["uncovered"],
                        "seconds": round(float(auto.get("pad_predict_s") or 0.0), 2),
                    }
                    ok = (pad_qa.get("accept")
                          and guards["overflow"] is not None
                          and guards["overflow"] <= CFG["mask"]["pad_overflow_limit"]
                          and guards["uncovered"] is not None
                          and guards["uncovered"] <= CFG["mask"]["pad_uncovered_limit"])
                    retry_info["accept"] = bool(ok)
                    retry_info_probe = retry_info
                    if ok:
                        binary = clean_mask((m_pad * 255).astype(np.uint8),
                                            threshold=128, erode_px=1)
                        method = "isnet_pad_retry"
                        full_shot = baseline_accepted
                        fallback_s = time.perf_counter() - t
                        print(f"  apmales retry pieņemts: segums={pad_qa.get('coverage')} "
                              f"overflow={guards['overflow']} uncovered={guards['uncovered']}",
                              flush=True)
                    else:
                        why = []
                        if not pad_qa.get("accept"):
                            why.append(f"QA: {pad_qa.get('reason')}")
                        if guards["overflow"] is not None and guards["overflow"] > CFG["mask"]["pad_overflow_limit"]:
                            why.append(f"pārplūde {guards['overflow']}")
                        if guards["uncovered"] is not None and guards["uncovered"] > CFG["mask"]["pad_uncovered_limit"]:
                            why.append(f"nepārklāts audums {guards['uncovered']}")
                        print(f"  apmales retry noraidīts: {'; '.join(why)}", flush=True)
                    del m_pad
                else:
                    print("  apmales retry izlaists: kadrā nav uzticama papīra fona", flush=True)

                code = stem[-6:]
                retried = method == "isnet_pad_retry"
                if retried:
                    pass                      # maska jau iegūta, GrabCut nav vajadzīgs
                elif baseline_accepted:
                    soft_full = cv2.resize(soft, (orig.width, orig.height),
                                           interpolation=cv2.INTER_LINEAR)
                    binary = clean_mask(soft_full, threshold=128, erode_px=1)
                    del soft_full
                    method = "isnet"
                    full_shot = True
                    print("  remēdija nedeva uzlabojumu -> paliek bāzes maska", flush=True)
                elif code in CLOSEUP_SEEDS:
                    t = time.perf_counter()
                    binary = closeup_mask(orig, stem, erode_px=1, proc_w=args.closeup_proc_w)
                    fallback_s = time.perf_counter() - t
                    method = "grabcut_seed_library_fallback"
                else:
                    # 3. ceļš: virsmas tekstūra. Pamats: fons gluds (~2.8),
                    # audums teksturēts (~12.8) — 4.5x atstarpe pusizmērā.
                    t = time.perf_counter()
                    plate_bin, plate_qa = plate_mask(orig)
                    fallback_s = time.perf_counter() - t
                    plate_info = plate_qa
                    if plate_qa.get("accept"):
                        binary = plate_bin
                        method = "plate_texture"
                        full_shot = False
                        print(f"  plāksnes ceļš pieņemts: segums={plate_qa['coverage']} "
                              f"iekšmala={plate_qa['inner_ratio']} ārējā={plate_qa['outer_ratio']} "
                              f"fons_iekšā={plate_qa['bg_inside']}", flush=True)
                    else:
                        print(f"  plāksnes ceļš noraidīts: {plate_qa.get('reason')}", flush=True)
                        # 4. (pēdējais) ceļš: krāsu attālums. Papīra ķēde ir
                        # izsmelta; ja arī chroma sevi noraida, paliek
                        # STOP-eskalācija zemāk.
                        t = time.perf_counter()
                        chroma_bin, chroma_qa = _try_chroma()
                        fallback_s = time.perf_counter() - t
                        chroma_info = chroma_qa
                        if chroma_qa.get("accept"):
                            binary = chroma_bin
                            method = "chroma_seeded"
                            full_shot = False
                            print(f"  chroma ceļš pieņemts: segums="
                                  f"{chroma_qa.get('struct_coverage')} min_cross_dE="
                                  f"{chroma_qa.get('min_cross_dE')}", flush=True)
                        else:
                            print(f"  chroma ceļš noraidīts: {chroma_qa.get('reason')}",
                                  flush=True)

                if method in ("plate_texture", "isnet_pad_retry", "chroma_seeded"):
                    pass          # maska jau iegūta (sk. zemāk zināmo kļūdu)
                else:
                    # ZINĀMĀ KĻŪDA, IZLABOTA 2026-10-23: šis zars agrāk sauca
                    # tikai `method == "plate_texture"`. Tāpēc QA PIEŅEMTA
                    # `isnet_pad_retry` maska tika izmesta un bilde tika
                    # noraidīta ar "nav drošas maskas" — pretrunā ar komentāru
                    # augstāk ("maska jau iegūta"). Redzams uz
                    # MVIMG_20261020_161031 ar --rotate 90: retry pieņēma
                    # segumu 0.3684 (overflow 0.0, uncovered 0.0045) un STOP.
                    #
                    # AUTO-SĒKLU CEĻŠ IR DZĒSTS (2026-10-22).
                    # Kāpēc: tas bija otrs segmentācijas ceļš (GrabCut ar
                    # automātiski ģenerētām sēklām) blakus ISNet. Uz 161146 tas
                    # iebāza maskā 8819 px papīra, kas iznākumā redzams kā bēšs
                    # ķīlis pie kadra malas. Apmales retry šo bildi jau noraida
                    # (nepārklāts audums 0.1534), tāpēc godīgais iznākums ir
                    # STOP-eskalācija cilvēkam, nevis otra modeļa maska.
                    mask_s = time.perf_counter() - t_mask
                    rec = {
                        "stem": stem,
                        "source": str(src),
                        "source_name": fname,
                        "source_sha256": source_sha,
                        "rotation_cw": rot_cw,
                        "source_size": list(orig.size),
                        "mask_path": None,
                        "mask_method": "refused_no_trusted_mask",
                        "full_shot": False,
                        "status": "needs_review",
                        "ai_qa": qa,
                        "pad_retry": retry_info_probe,
                        "coverage": qa.get("coverage"),
                        "error": ("ISNet maska noraidīta un apmales retry noraidīts; "
                                  "auto-sēklu ceļš dzēsts, tāpēc drošas maskas nav"),
                        "timing": {
                            "isnet_wall_s": round(float(isnet_timing.get("wall_s", 0.0)), 3),
                            "isnet_init_s": isnet_timing.get("init_s"),
                            "isnet_predict_s": isnet_timing.get("predict_s"),
                            "fallback_s": round(float(fallback_s), 3),
                            "mask_total_s": round(float(mask_s), 3),
                        },
                    }
                    records.append(rec)
                    _persist_report(records, args.attempt, "masks", profile_s)
                    print("  STOP: nav drošas maskas -> needs_review (auto-sēklu ceļš dzēsts)",
                          flush=True)
                    del orig
                    gc.collect()
                    continue
                full_shot = False
                if "grabcut" in method:
                    print(f"  GrabCut fallback: {fallback_s:.2f} s", flush=True)

            # --- Iekšējo caurumu klasificēšana pēc satura (PROGRESS §97) --
            # Kandidāts var izturēt sava ceļa QA un tomēr ieslēgt caurumu:
            # vai nu maska pazaudējusi audumu (vafeļadījuma ieleju josla,
            # 160550 pie pad 0.90: 53 877 px), vai īss tiltiņš pie malas
            # ieslēdz papīra šķēlumu (160601: 610 px). Pirms strukturālās
            # pārbaudes caurumu klasificē pēc satura pret auduma gredzenu
            # un lokālo fonu: audumu aizpilda, fonu tuvu malai atver,
            # pārējo atstāj — checker GATE_C paliek tiesnesis.
            binary, hole_info = repair_interior_holes(binary, orig)
            for a in hole_info.get("actions", []):
                print(f"  caurums {a['area']} px bbox={a['bbox']}: "
                      f"{a['action']}"
                      + (f" ({a.get('reason')})" if a["action"] == "left"
                         else "")
                      + f"; d_fg={a.get('d_fg')} d_bg={a.get('d_bg')}",
                      flush=True)

            # --- Strukturālais trigeris chroma ceļam ----------------------
            # Maker QA (ISNet/apmales/plate) ir per-ceļa un var pieņemt
            # masku, kas strukturāli ir fragmenti vai ar caurumu — tieši to
            # neatkarīgais checker pēc tam soda GATE_C (izmērīts §75:
            # fill 0.4058 pieņemts ar pad aizsargiem; caurums 576 px
            # pieņemts ar ISNet QA). Tāpēc PIRMS saglabāšanas kandidātu
            # pārbauda strukturāli; ja tas krīt, mēģina chroma. Ja chroma
            # sevi noraida, kandidāds PALIEK (uzvedība nemainās) un
            # checker paliek tiesnesis — šis trigeris neko neatvieglo.
            if method != "chroma_seeded":
                struct_qa = structural_qa(binary)
                # Zaudētā auduma trigeris (§103): structural_qa neredz
                # audumu ĀRPUS maskas (ar malu savienoti līči/ieleju
                # kanāli nav caurumi) — to mēra lost_fabric_metric
                # (checker GATE_Q spogulis). Kandidāts neuzticas, ja
                # strukturāli slikts VAI zaudētais audums virs trigera;
                # Q gadījumā vispirms mēģina plate (tās tekstūras
                # mērījums ielejas neatmet), tad chroma kā līdz šim.
                q_before = lost_fabric_metric(binary, orig)
                q_pct = q_before.get("lost_fabric_pct")
                q_bad = (q_pct is not None and q_pct
                         > float(CFG["mask"]["q_trigger_pct"]))
                if q_bad or not struct_qa["accept"]:
                    if not struct_qa["accept"]:
                        pre_chroma_struct = struct_qa
                    q_info = {"before": q_before,
                              "trigger": ("lost_fabric" if q_bad
                                          else "structural")}
                    print(f"  kandidāts ({method}) neuzticas: "
                          f"fill={struct_qa['silhouette_fill']} "
                          f"caurumi>={struct_qa['interior_holes_ge400']} "
                          f"lielākā={struct_qa['largest_ratio']} "
                          f"zaudētais audums={q_pct}%",
                          flush=True)
                    adopted = False
                    if q_bad:
                        # Pirmais līdzeklis (§108): atgūt līčus pašā
                        # kandidātā, nevis mest to ārā — kandidāta labās
                        # daļas (piem., apkakle) saglabājas. Pieņem tikai
                        # tad, ja Q pēc atgūšanas iztur trigeri.
                        t = time.perf_counter()
                        rec_bin, rec_info = reclaim_inlets(binary, orig)
                        fallback_s += time.perf_counter() - t
                        q_info["reclaim"] = rec_info
                        if rec_info.get("reclaimed_px"):
                            q_rec = lost_fabric_metric(rec_bin, orig)
                            q_info["reclaim_q"] = q_rec
                            if (q_rec.get("lost_fabric_pct") is not None
                                    and q_rec["lost_fabric_pct"]
                                    <= float(CFG["mask"]["q_trigger_pct"])
                                    and q_rec["lost_fabric_pct"] < q_pct):
                                binary = rec_bin
                                adopted = True
                                print(f"  līču atgūšana pieņemta: "
                                      f"+{rec_info['reclaimed_px']} px, "
                                      f"Q {q_pct}% -> "
                                      f"{q_rec['lost_fabric_pct']}%",
                                      flush=True)
                        if not adopted:
                            print("  līču atgūšana Q neizlaboja "
                                  "pietiekami", flush=True)
                        del rec_bin
                    if q_bad and method != "plate_texture":
                        # Plate vērtē arī tad, ja atgūšana jau pieņemta:
                        # Q metrika neredz PLATUS zaudējumus (līcis
                        # 154k px §108), kurus plate sedz; kandidātu
                        # izvēle (current/plate/union) izlemj pēc Q ar
                        # union priekšroku neizšķirtā (§109).
                        t = time.perf_counter()
                        p_bin, p_qa = plate_mask(orig)
                        fallback_s += time.perf_counter() - t
                        q_info["plate_accept"] = bool(p_qa.get("accept"))
                        if p_qa.get("accept"):
                            q_plate = lost_fabric_metric(p_bin, orig)
                            q_info["plate"] = q_plate
                            uni_bin = ((binary > 0)
                                       | (p_bin > 0)).astype(np.uint8)
                            q_uni = lost_fabric_metric(uni_bin, orig)
                            q_info["union"] = q_uni
                            q_cur = q_info.get(
                                "reclaim_q", {}).get("lost_fabric_pct", q_pct)
                            choice = choose_candidate([
                                ("current", q_cur, True),
                                ("plate", q_plate.get("lost_fabric_pct"),
                                 structural_qa(p_bin)["accept"]),
                                ("union", q_uni.get("lost_fabric_pct"),
                                 structural_qa(uni_bin)["accept"]),
                            ])
                            q_info["chosen"] = choice
                            if choice == "union":
                                binary = uni_bin
                                method = f"{method}+plate_union"
                                plate_info = p_qa
                                adopted = True
                                print(f"  union ar plate pieņemts: "
                                      f"Q {q_cur}% -> "
                                      f"{q_uni['lost_fabric_pct']}%",
                                      flush=True)
                            elif choice == "plate":
                                binary = p_bin
                                method = "plate_texture"
                                plate_info = p_qa
                                adopted = True
                                print(f"  plate pieņemta caur Q trigeri: "
                                      f"zaudētais {q_pct}% -> "
                                      f"{q_plate['lost_fabric_pct']}%",
                                      flush=True)
                            del uni_bin
                        if not adopted:
                            print("  plate/union Q trigerī nepalīdzēja "
                                  f"({p_qa.get('reason')})", flush=True)
                        del p_bin
                    if not adopted:
                        t = time.perf_counter()
                        chroma_bin, chroma_qa = _try_chroma()
                        fallback_s += time.perf_counter() - t
                        chroma_info = chroma_qa
                        if chroma_qa.get("accept"):
                            binary = chroma_bin
                            method = "chroma_seeded"
                            adopted = True
                            print(f"  chroma ceļš pieņemts: segums="
                                  f"{chroma_qa.get('struct_coverage')} min_cross_dE="
                                  f"{chroma_qa.get('min_cross_dE')}", flush=True)
                        else:
                            print(f"  chroma noraidīts: {chroma_qa.get('reason')} "
                                  f"-> paliek kandidāds", flush=True)
                    q_info["after"] = (lost_fabric_metric(binary, orig)
                                       if adopted else q_before)

            # --- Kadrējuma IZVĒLE ---------------------------------------
            # Divi stili, abi lietotāja izvēlē (`--framing`):
            #   slamjam  — produkta kadrs: krekls pilnībā kadrā, fons ap malām
            #              (Slam Jam kopskati: fons 64 %, krekls 60 % x 79 %)
            #   original — kadrs kā nofotografēts: krekls iet pāri malai, un
            #              īstais fona laukums paliek (Slam Jam tuvplāni: 7-10 %)
            #   auto     — slamjam, ja siluets ir slēgts; citādi original
            #
            # GODĪGAIS IEROBEŽOJUMS: `slamjam` prasa, lai krekls AVOTĀ būtu
            # pilnībā kadrā. Ja maska karājas pāri malai, trūkstošo audumu
            # nevar izdomāt (tas būtu ģeneratīvs piepildījums, kas šajā
            # projektā ir aizliegts). Tāpēc šādā gadījumā slamjam netiek
            # izpildīts — tiek atgriezts `original` un ierakstīts atskaitē,
            # KA un KĀPĒC.
            edge_contact = {
                "top": float(binary[0].mean()), "bottom": float(binary[-1].mean()),
                "left": float(binary[:, 0].mean()), "right": float(binary[:, -1].mean()),
            }
            touched = sum(v >= 0.50 for v in edge_contact.values())
            closed = touched == 0
            wanted = args.framing
            if wanted == "auto":
                chosen = "slamjam" if closed else "original"
                note = "auto: slēgts siluets -> slamjam" if closed else \
                       "auto: atvērts siluets -> original"
            elif wanted == "slamjam":
                if closed:
                    chosen, note = "slamjam", "izvēlēts slamjam"
                else:
                    chosen = "original"
                    note = (f"lūgts slamjam, bet krekls karājas pāri {touched} malām "
                            "— trūkstošo audumu neizdomājam, tāpēc original")
                    print(f"  UZMANĪBU: {note}", flush=True)
            else:
                chosen, note = "original", "izvēlēts original"
            full_shot = chosen == "slamjam"
            framing_info = {
                "requested": wanted,
                "chosen": chosen,
                "rule": note,
                "slamjam_possible": bool(closed),
                "edges": edge_contact,
                "edges_touched": int(touched),
                "closed_silhouette": bool(closed),
                "full_shot": bool(full_shot),
                "fill": [GARMENT_FILL_W, GARMENT_FILL_H],
            }
            if full_shot:
                print(f"  kompozīcija: slamjam (krekls pilnā kadrā, "
                      f"aizpildījums {GARMENT_FILL_W:.2f}x{GARMENT_FILL_H:.2f})", flush=True)
            else:
                print(f"  kompozīcija: original ({note})", flush=True)
            if not full_shot:
                no_auto_crop = True

            coverage = float(binary.mean())
            save_gray_png(binary * 255, mask_path, args.png_level)
            start_mask_provenance(mask_path, stem, source_sha, str(method))
            mask_s = time.perf_counter() - t_mask
            rec = {
                "stem": stem,
                "source": str(src),
                "source_name": fname,
                "source_sha256": source_sha,
                "rotation_cw": rot_cw,
                "source_size": list(orig.size),
                "mask_path": str(mask_path),
                "mask_method": method,
                "full_shot": bool(full_shot),
                "status": "mask_ready",
                "coverage": round(coverage, 4),
                "ai_qa": qa,
                "timing": {
                    "isnet_wall_s": round(float(isnet_timing.get("wall_s", 0.0)), 3),
                    "isnet_init_s": isnet_timing.get("init_s"),
                    "isnet_predict_s": isnet_timing.get("predict_s"),
                    "isnet_proxy_size": isnet_timing.get("proxy_size"),
                    "fallback_s": round(float(fallback_s), 3),
                    "mask_total_s": round(float(mask_s), 3),
                },
            }
            if retry_info_probe is not None:
                rec["pad_retry"] = retry_info_probe
            if plate_info is not None:
                rec["plate_qa"] = plate_info
            if chroma_info is not None:
                rec["chroma_qa"] = chroma_info
            if pre_chroma_struct is not None:
                rec["pre_chroma_structural"] = pre_chroma_struct
            if hole_info is not None and hole_info.get("holes_ge_min"):
                rec["hole_repair"] = hole_info
            if q_info is not None:
                rec["lost_fabric_trigger"] = q_info
            rec["framing"] = framing_info
            rec["no_auto_crop"] = bool(no_auto_crop)
            if auto_info is not None:
                rec["auto_seed"] = auto_info
                rec["auto_mask_qa"] = closeup_qa
                rec["seed_proposal"] = proposal_path
            records.append(rec)
            print(f"  metode={method}; segums={coverage:.4f}; maska kopā={mask_s:.2f} s", flush=True)
            del binary, orig
        except LookupError as exc:
            rec = {
                "stem": stem,
                "source": str(src),
                "source_name": fname,
                "source_sha256": source_sha,
                "mask_path": str(mask_path),
                "status": "needs_seed_review",
                "error": str(exc),
                "auto_seed": auto_info,
                "seed_proposal": proposal_path,
                "timing": {"mask_total_s": round(float(time.perf_counter() - t_mask), 3)},
            }
            records.append(rec)
            print(f"  needs_seed_review: {exc}", flush=True)
        except Exception as exc:  # noqa: BLE001 - batch izolēšana pa bildēm ir apzināta
            rec = {
                "stem": stem,
                "source": str(src),
                "source_name": fname,
                "source_sha256": source_sha,
                "mask_path": str(mask_path),
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "auto_seed": auto_info,
                "seed_proposal": proposal_path,
                "timing": {"mask_total_s": round(float(time.perf_counter() - t_mask), 3)},
            }
            records.append(rec)
            print(f"  FAIL: {rec['error']}", flush=True)
        _persist_report(records, args.attempt, "masks", profile_s)
        gc.collect()

    for r in records:
        r.setdefault("rotation_cw", rotation_for(Path(r["source"])))

    # --- Robežas pierādījuma STOP pirms rendera (2.11, §116) ----------
    # Spogulis checker GATE_S uz GALA maskas (pēc visiem trigeriem un
    # labojumiem, ieskaitot --resume/--rerender-saved saglabātās):
    # nelīdzena kontūra posmā ar vāju avota malu = robeža nav
    # pierādāma, tāpēc kadrs netiek renderēts un nevar kļūt par
    # klusu PASS kolāžā. Checker GATE_S paliek neatkarīgais tiesnesis.
    for rec in records:
        if rec.get("status") != "mask_ready":
            continue
        if rec.get("lut_only"):
            # §131: pilnkadrā nav priekšmeta robežas, ko pierādīt; GATE_S
            # checkerī tiek izlaists AR atzīmi (nevis klusi).
            rec["boundary_evidence"] = {
                "pass": None, "skipped": True,
                "reason": "lut_only: pilnkadrs, nav priekšmeta robežas (§131)",
            }
            continue
        try:
            _orig = open_rgb_recorded(rec["source"], rec.get("rotation_cw"))
            with Image.open(rec["mask_path"]).convert("L") as _im:
                _mask_bin = (np.asarray(_im) > 127).astype(np.uint8)
            _s_metric = boundary_evidence_metric(_mask_bin, _orig)
            del _orig, _mask_bin
            rec["boundary_evidence"] = _s_metric
            _tim = rec.setdefault("timing", {})
            _tim["boundary_s"] = _s_metric.get("seconds")
            _tim["mask_total_s"] = round(
                float(_tim.get("mask_total_s", 0.0))
                + float(_s_metric.get("seconds") or 0.0), 3)
            if _s_metric.get("uncertain"):
                rec["status"] = "boundary_uncertain"
                rec["stop_reason"] = "boundary_uncertain"
                rec["error"] = (
                    "boundary_uncertain: robeža nav pierādāma "
                    f"(aizdomīgi logi posmā "
                    f"{_s_metric.get('worst_span_windows')} >= "
                    f"{_s_metric.get('limit_windows')}; centrs "
                    f"{_s_metric.get('worst_center_xy_fullres')}). "
                    "Kadrs jāpārfotografē asākā fokusā vai robeža "
                    "jālabo ar atsevišķu apstiprinātu soli.")
                print(f"[{rec['stem']}] STOP boundary_uncertain: "
                      f"{rec['error']}", flush=True)
        except Exception as exc:  # noqa: BLE001 - izolēšana pa bildēm
            rec["status"] = "failed"
            rec["error"] = (f"boundary_evidence metrika krita: "
                            f"{type(exc).__name__}: {exc}")
            print(f"[{rec['stem']}] FAIL: {rec['error']}", flush=True)
        gc.collect()
    _persist_report(records, args.attempt, "masks", profile_s)

    active = [r for r in records if r.get("status") == "mask_ready"]
    if not active:
        report = _persist_report(records, args.attempt, "blocked", profile_s)
        print(f"V2.1 BLOĶĒTS: nav nevienas gatavas maskas. Kopsavilkums={report['summary']}", flush=True)
        return 2

    # §131: LUT (WB/ekspozīcija/līkne) rēķinās TIKAI no kopskatiem —
    # pilnkadra makro satur tikai audumu, no kā fona etalons nav atrodams.
    # Grupa bez neviena kopskata = STOP: lut_only kadram nav no kā manto LUT.
    profile_recs = [r for r in active if not r.get("lut_only")]
    if not profile_recs:
        report = _persist_report(records, args.attempt, "blocked", profile_s)
        print("V2.1 BLOĶĒTS: lut_only grupā nav neviena kopskata — nav no kā "
              "rēķināt LUT (§131). Piefotografē vismaz vienu kopskatu.", flush=True)
        return 2

    # 2. fāze: viens krāsu profils pabeigtajām maskām.
    t = time.perf_counter()
    profile = compute_grade_profile(profile_recs, args.wb_mode)
    profile_s = time.perf_counter() - t
    atomic_write_json(PROFILE_PATH, profile)
    # LUT tiek saglabāts ARĪ katrai bildei atsevišķi. Iemesls: globālais
    # grade_profile_v2.json tiek pārrakstīts katrā palaišanā, tāpēc pēc
    # nākamās bildes renderēšanas iepriekšējo vairs nevarēja verificēt
    # (GATE_A2 krita ar max_diff 4-5, lai gan bilde bija pareiza).
    profiles_dir = Path(OUT) / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    for rec in active:
        ppath = profiles_dir / f"{rec['stem']}_PROFILE.json"
        atomic_write_json(ppath, profile)
        rec["profile_path"] = str(ppath)
    _persist_report(records, args.attempt, "profile", profile_s)
    print(
        "Krāsu profils: "
        f"fons={profile['background_median_rgb']}, WB={profile['wb_gains_linear_rgb']}, "
        f"ekspozīcija={profile['exposure_factor']}, WB uzticams={profile['wb_trusted']}, "
        f"aprēķins={profile_s:.2f} s",
        flush=True,
    )

    # 3. fāze: renderēšana.
    alloc_profile = profile_s / max(len(active), 1)
    for rec in active:
        print(f"[{rec['stem']}] v2.1 renderēšana ...", flush=True)
        try:
            if rec.get("lut_only"):
                rt = render_lut_only(rec, profile, args.png_level)
                rec["timing"].update({"grade_s": rt["grade_s"],
                                      "render_s": rt["render_s"]})
                rec["full_shot"] = None
                rec["closeup_crop"] = None
                rec["lut_geometry"] = rt["lut_geometry"]
                rec["makro_path"] = rt["makro_path"]
                rec["shadow_model"] = rt["shadow_model"]
            else:
                rt = render_one(rec, profile, args.png_level)
                rec["timing"].update(rt)
            rec["timing"]["profile_alloc_s"] = round(alloc_profile, 3)
            rec["timing"]["total_s"] = round(
                float(rec["timing"].get("mask_total_s", 0.0)) + float(rt["render_s"]) + alloc_profile, 3
            )
            rec["full_shot"] = rt["full_shot"]
            rec["closeup_crop"] = rt["closeup_crop"]
            rec["status"] = "completed"
            rec.pop("error", None)
            print(
                f"  kopā={rec['timing']['total_s']:.2f} s "
                f"(maska {float(rec['timing'].get('mask_total_s', 0.0)):.2f} + render {rt['render_s']:.2f})",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            rec["status"] = "failed"
            rec["error"] = f"{type(exc).__name__}: {exc}"
            print(f"  RENDER FAIL: {rec['error']}", flush=True)
        _persist_report(records, args.attempt, "render", profile_s)
        gc.collect()

    collage_path = None
    collage_s = None
    if not args.no_collage:
        t = time.perf_counter()
        try:
            collage_path = write_collage(records)
        except Exception as exc:  # noqa: BLE001
            print(f"Kolāžas izveide neizdevās: {type(exc).__name__}: {exc}", flush=True)
        collage_s = time.perf_counter() - t

    report = _persist_report(records, args.attempt, "done", profile_s, collage_path, collage_s)
    print(f"KRĀTUVE: loop_bildes = {workspace_bytes('/home/user/loop_bildes') / 1048576:.2f} MiB")
    print(
        "V2.1 MAKER DONE: "
        f"{report['summary']['completed']}/{len(records)} pabeigtas; "
        f"vidēji {report['summary']['mean_s']:.2f} s/bilde; "
        f"maks. {report['summary']['max_s']:.2f} s"
        + (f"; kolāža={collage_path}" if collage_path else "")
    )
    return 0 if report["summary"]["completed"] == len(records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
