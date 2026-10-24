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

from engine.config import WORKFLOW_VERSION  # noqa: E402,F401
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
PROFILE_PATH = Path(OUT) / "grade_profile_v2.json"
REPORT_PATH = Path(OUT) / "report_v2_maker.json"
CHECKER_REPORT_PATH = Path(OUT) / "report_v2.json"
DELIVERY_REPORT_PATH = Path(OUT) / "delivery_v2.json"
COLLAGE_PATH = Path(OUT) / "V2_KOLAZA.jpg"
MODEL_PATH = Path("/var/tmp/rembg_home/models/isnet-general-use/isnet-general-use.onnx")

from engine.config import (  # noqa: E402
    CFG, CONFIG_PATH, load_config, _resolve_args, _effective_config,
    _config_sha256,
)


# ---------------------------------------------------------------------------
# Mazi infrastruktūras palīgrīki
# ---------------------------------------------------------------------------


# Stems, kuriem NEpiemērot decontaminate_rim. Vajadzīgs kadriem, kuros
# audums sniedzas pāri kadra malai: tur "mala" nav īsta apģērba mala, un
# decontam nogriež pa kontūru, izdurdam tievas plaisas audumā.
NO_DECONTAM: set[str] = set()



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
    paper_profile, plan_closeup_crop, plate_mask, run_isnet,
    run_isnet_auto, save_seed_proposal,
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

def render_one(rec: dict, profile: dict, png_level: int) -> dict:
    t_all = time.perf_counter()
    stem = rec["stem"]
    orig = open_rgb_recorded(rec["source"], rec.get("rotation_cw"))
    binary = (np.asarray(Image.open(rec["mask_path"]).convert("L")) > 128).astype(np.uint8)
    if binary.shape != (orig.height, orig.width):
        raise ValueError(f"Maskas izmērs {binary.shape} nesakrīt ar {stem} {orig.size}")

    t = time.perf_counter()
    graded = apply_lut(np.asarray(orig), profile["lut_rgb"])
    grade_s = time.perf_counter() - t

    # Ēnas virziens tiek MĒRĪTS šai bildei (sk. loop.measure_shadow_angle).
    # Fiksēta konstante uz džinsiem deva 65° kļūdu -> labajām malām ēnas
    # nebija, un džinsa tumšā mala lasījās kā melna līnija.
    t = time.perf_counter()
    _L = (np.asarray(orig).astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32))
    shadow_angle, shadow_strength = measure_shadow_angle(_L, binary.astype(bool))
    del _L
    shadow_measure_s = time.perf_counter() - t

    t = time.perf_counter()
    # Noņem fona kontamināciju maskas IEKŠPUSĒ (papīra ēna, ko segmentācija
    # aprija) — sk. QA §34. Tas ir pirms alfa ģenerēšanas, jo maina pašu mati.
    t = time.perf_counter()
    mask_sha_in = sha256_file(Path(rec["mask_path"]))
    if stem in NO_DECONTAM:
        decontam_info = {"applied": False, "skipped": True,
                         "why": "--no-decontam: audums sniedzas pāri kadram"}
    elif not decontam_needed(read_mask_provenance(rec["mask_path"]),
                             DECONTAM_PARAMS, mask_sha_in):
        decontam_info = {"applied": False, "skipped": True,
                         "why": "provenance: decontam ar šiem parametriem jau izpildīts"}
    else:
        binary, decontam_info = decontaminate_rim(
            graded, binary,
            max_px=DECONTAM_PARAMS["max_px"], tex_ratio=DECONTAM_PARAMS["tex_ratio"])
    decontam_s = time.perf_counter() - t
    if decontam_info.get("applied"):
        # Maska FAILĀ ir tā, kas faktiski izmantota renderēšanā. Bez šī
        # čekeris rekonstruēja references kadru pēc NEAPGRIEZTĀS maskas un
        # GATE_R viltus-krita (fore_p99=171): master jau bija apgriezts, bet
        # _MASK.png vēl nē. Sk. QA §34.
        save_gray_png(binary.astype(np.uint8) * 255,
                      Path(OUT) / "masks" / f"{stem}_MASK.png", png_level)
        append_mask_stage(
            rec["mask_path"], stem, rec.get("source_sha256") or "",
            {"stage": "decontam", "params": dict(DECONTAM_PARAMS),
             "input_mask_sha256": mask_sha_in,
             "removed_px": decontam_info.get("removed_px")})
    alpha_u8 = refine_alpha(binary)
    graded = extend_foreground_colors(graded, binary, alpha_u8, max_dist=8)
    # Master ir STARPPRODUKTS, kas tiek samazināts uz 2000x2500 audeklu. Tāpēc
    # visiem ēnas garuma mēriem (blur, falloff) jābūt izteiktiem audekla mērogā
    # un pārrēķinātiem ar 1/scale. Citādi pēc samazināšanas master ēna ir 14-17 px,
    # bet `render_paraugs` uzliek 25 px — un GATE_R references rekonstrukcija saskata
    # atšķirību tur, kur izvadē ir viegla ēna, bet referencei tā jau beigusies.
    # Sk. QA §38.
    _psc = para_scale(binary)
    # Jaunais studijas ēnas modelis (sk. loop.studio_shadow_bg): virziens un
    # penumbra ir modeļa konstantes audekla pikseļos; MASTER mērogā tas tiek
    # pārrēķināts ar canvas_scale=_psc, lai MASTER un PARAUGS ēna būtu viens
    # un tas pats fiziskais lielums. Avotā mērītais `shadow_angle` paliek
    # atskaitē kā mērījums, bet renderī vairs netiek lietots.
    bg_gray = studio_shadow_bg(binary.shape, binary, canvas_scale=_psc)
    h, w = binary.shape
    master = np.empty((h, w, 3), np.uint8)
    for y in range(0, h, 256):
        y2 = min(h, y + 256)
        a = (alpha_u8[y:y2].astype(np.float32) / 255.0)[..., None]
        blended = graded[y:y2].astype(np.float32) * a + bg_gray[y:y2, :, None].astype(np.float32) * (1.0 - a)
        master[y:y2] = np.clip(blended + 0.5, 0, 255).astype(np.uint8)
        del a, blended
    del bg_gray
    save_image_atomic(
        Image.fromarray(master), Path(OUT) / "master" / f"{stem}_MASTER_1to1.png",
        optimize=False, compress_level=png_level,
    )
    del master
    save_gray_png(alpha_u8, Path(OUT) / "masks" / f"{stem}_ALPHA.png", png_level)
    master_s = time.perf_counter() - t

    t = time.perf_counter()
    cutout = Image.fromarray(graded).convert("RGBA")
    del graded
    cutout.putalpha(Image.fromarray(alpha_u8))
    del alpha_u8
    full_shot_pref = rec.get("full_shot")
    if full_shot_pref is None:
        stats = _mask_stats(binary)
        full_shot_pref = bool(stats["coverage"] < 0.50 and stats["bbox_area_fraction"] > 0.35)
    crop_box = None if full_shot_pref else CLOSEUP_CROPS.get(stem[-6:])
    crop_info = None
    if rec.get("no_auto_crop"):
        # framing=bleed: kadrs paliek tāds, kā nofotografēts. Automātiskā
        # tuvplāna apgriešana (plan_closeup_crop) šeit būtu kaitīga: tā tuvina
        # un nogriež tieši to fonu, kura dēļ kadrs tiek atstāts.
        crop_info = {"auto": False, "reason": "framing=bleed"}
    elif not full_shot_pref and crop_box is None:
        # Automātiska full-bleed kompozīcija: ja maska ir laba, bet nesasniedz
        # 3 malas, to atrisina apgriešana, nevis cita maska.
        t = time.perf_counter()
        crop_box, n_edges = plan_closeup_crop(binary)
        crop_info = {"auto": True, "edges_after": n_edges,
                     "seconds": round(time.perf_counter() - t, 2)}
        if crop_box is None:
            raise ValueError(
                f"{stem}: nevar izveidot full-bleed kompozīciju ar 3 malām "
                f"(maska nesasniedz malas un apgriešana nelīdz)")
    paraugs, placed_mask, full_shot = render_paraugs(
        cutout, binary, full_shot_override=bool(full_shot_pref), crop_box=crop_box,
        shadow_angle=shadow_angle,
    )
    sharp = profile.get("output_sharpen", {})
    if sharp:
        paraugs = paraugs.filter(
            ImageFilter.UnsharpMask(
                radius=float(sharp.get("radius", 1.4)),
                percent=int(sharp.get("percent", 42)),
                threshold=int(sharp.get("threshold", 3)),
            )
        )
    save_image_atomic(paraugs, Path(OUT) / "paraugs" / f"{stem}_PARAUGS_2000x2500.jpg", quality=95)
    save_image_atomic(placed_mask, Path(OUT) / "masks" / f"{stem}_PARAUGS_MASK.png")
    paraugs_s = time.perf_counter() - t

    del cutout, paraugs, placed_mask, binary, orig
    gc.collect()
    return {
        "grade_s": round(grade_s, 3),
        "master_s": round(master_s, 3),
        "paraugs_s": round(paraugs_s, 3),
        "render_s": round(time.perf_counter() - t_all, 3),
        "full_shot": bool(full_shot),
        "closeup_crop": crop_box,
        "closeup_crop_info": crop_info,
        "shadow_angle_deg": round(float(shadow_angle), 1),
        "shadow_measure_strength": round(float(shadow_strength), 1),
        "shadow_model": "studio_v1_contact_pcss",
        "studio_shadow_angle_deg": STUDIO_SHADOW_ANGLE_DEG,
        "studio_shadow_offset_px": STUDIO_SHADOW_OFFSET_PX,
        "shadow_measure_s": round(shadow_measure_s, 3),
        "decontaminate_s": round(decontam_s, 3),
        "decontaminate": decontam_info,
    }


def write_collage(records: list[dict], out_path: Path = COLLAGE_PATH) -> str | None:
    completed = [r for r in records if r.get("status") == "completed"]
    if not completed:
        return None
    tw, th, label_h, margin, gap = 620, 775, 44, 16, 14
    cols = min(3, len(completed))
    rows = (len(completed) + cols - 1) // cols
    W = margin * 2 + cols * tw + (cols - 1) * gap
    H = margin * 2 + rows * (th + label_h) + (rows - 1) * gap
    sheet = Image.new("RGB", (W, H), (222, 222, 222))
    d = ImageDraw.Draw(sheet)
    short_method = {
        "isnet": "ISNet",
        "grabcut_seed_library_fallback": "GrabCut/bibl.",
    }
    for i, rec in enumerate(completed):
        r, c = divmod(i, cols)
        x = margin + c * (tw + gap)
        y = margin + r * (th + label_h + gap)
        method = short_method.get(rec.get("mask_method", ""), rec.get("mask_method", ""))
        total = rec.get("timing", {}).get("total_s")
        label = f"{rec['stem'][-6:]}  {method}" + (f"  {total:.1f}s" if isinstance(total, (int, float)) else "")
        d.text((x + 5, y + 13), label, fill=(0, 0, 0))
        p = Path(OUT) / "paraugs" / f"{rec['stem']}_PARAUGS_2000x2500.jpg"
        with Image.open(p) as im:
            thumb = im.convert("RGB").resize((tw, th), Image.LANCZOS)
        sheet.paste(thumb, (x, y + label_h))
    save_image_atomic(sheet, Path(out_path), quality=92)
    return str(out_path)


def make_zip(zip_name: str | None = None) -> int:
    """Izveido ZIP tikai tad, ja checker visām pabeigtajām bildēm saka PASS.

    Cilvēka apstiprinājums joprojām notiek ārpus koda ar pogu; šī funkcija
    ir tikai deterministiska piegādes darbība pēc apstiprinājuma.
    """
    maker = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    checker = json.loads(CHECKER_REPORT_PATH.read_text(encoding="utf-8"))
    completed = {
        stem: rec for stem, rec in maker.get("images", {}).items()
        if rec.get("status", "completed") == "completed"
    }
    if not completed:
        raise RuntimeError("Maker atskaitē nav pabeigtu bilžu")
    incomplete = sorted(
        stem for stem, rec in maker.get("images", {}).items()
        if rec.get("status", "completed") != "completed"
    )
    if incomplete:
        raise RuntimeError(f"Grupā ir nepabeigtas bildes, ZIP netiek veidots: {incomplete}")
    missing_checker = sorted(set(completed) - set(checker))
    if missing_checker:
        raise RuntimeError(f"Checker atskaitē trūkst: {missing_checker}")
    failed = sorted(stem for stem in completed if not checker[stem].get("ALL_PASS"))
    if failed:
        raise RuntimeError(f"Checker FAIL, ZIP netiek veidots: {failed}")

    files = []
    for stem in sorted(completed):
        p = Path(OUT) / "paraugs" / f"{stem}_PARAUGS_2000x2500.jpg"
        if not p.is_file():
            raise FileNotFoundError(p)
        files.append(p)
    out = Path(OUT) / Path(zip_name or "V2_GALA_BILDES.zip").name
    fd, tmp_name = tempfile.mkstemp(dir=OUT, prefix=out.stem + ".", suffix=".zip")
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp_name, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p in files:
                z.write(p, arcname=p.name)
        entries = []
        with zipfile.ZipFile(tmp_name) as z:
            bad = z.testzip()
            if bad is not None:
                raise RuntimeError(f"ZIP CRC kļūda: {bad}")
            for p in files:
                data = z.read(p.name)
                original = p.read_bytes()
                if data != original:
                    raise RuntimeError(f"ZIP ieraksts nav identisks oriģinālam: {p.name}")
                entries.append({
                    "name": p.name,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                })
        os.replace(tmp_name, out)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    delivery = {
        "zip": str(out),
        "bytes": out.stat().st_size,
        "sha256": sha256_file(out),
        "files": entries,
        "workflow_version": WORKFLOW_VERSION,
        "attempt": maker.get("attempt"),
    }
    atomic_write_json(DELIVERY_REPORT_PATH, delivery)
    print(json.dumps(delivery, indent=2, ensure_ascii=False))
    return 0


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


def _summary(records: list[dict]) -> dict:
    totals = [
        float(r["timing"]["total_s"])
        for r in records
        if r.get("status") == "completed" and "total_s" in r.get("timing", {})
    ]
    return {
        "started": len(records),
        "completed": int(sum(1 for r in records if r.get("status") == "completed")),
        "mask_ready": int(sum(1 for r in records if r.get("status") == "mask_ready")),
        "needs_seed_review": int(sum(1 for r in records if r.get("status") == "needs_seed_review")),
        "failed": int(sum(1 for r in records if r.get("status") == "failed")),
        "total_s": round(sum(totals), 3),
        "mean_s": round(float(np.mean(totals)) if totals else 0.0, 3),
        "min_s": round(float(np.min(totals)) if totals else 0.0, 3),
        "max_s": round(float(np.max(totals)) if totals else 0.0, 3),
        "within_25s": int(sum(1 for v in totals if v <= 25.0)),
    }


_RUN_META: dict = {}



def _code_commit() -> str:
    """Git HEAD šim repozitorijam; '-dirty', ja ir neiekomitētas izmaiņas.
    Bez repozitorija/git: 'unknown' (nekad nekrīt dēļ atskaites lauka)."""
    try:
        here = Path(__file__).resolve().parent
        sha = subprocess.run(["git", "-C", str(here), "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        if not sha:
            return "unknown"
        dirty = subprocess.run(["git", "-C", str(here), "status", "--porcelain"],
                               capture_output=True, text=True, timeout=10).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def _set_run_meta(args) -> None:
    eff = _effective_config(args)
    _RUN_META.update({"code_commit": _code_commit(), "config": eff,
                      "config_sha256": _config_sha256(eff)})


def _persist_report(records: list[dict], attempt: int, stage: str,
                    profile_s: float | None = None, collage_path: str | None = None,
                    collage_s: float | None = None) -> dict:
    # Atskaite uzkrājas starp palaišanām. Bez šī katrs atsevišķs `--files`
    # palaišanas gadījums izdzēsa pārējo bilžu ierakstus, un tās vairs nevarēja
    # pārbaudīt ar čekeri (2026-10-23: pazuda džinsu ieraksts pēc krekla
    # pārrenderēšanas). Saglabājam tikai tos vecos ierakstus, kuru izvades
    # faili joprojām eksistē un kuru stem šajā palaišanā nav.
    merged = {r["stem"]: r for r in records}
    if REPORT_PATH.is_file():
        try:
            prev = json.loads(REPORT_PATH.read_text(encoding="utf-8")).get("images", {})
        except Exception:
            prev = {}
        for stem, rec in prev.items():
            if stem in merged:
                continue
            para = rec.get("paraugs_path") or str(
                Path(OUT) / "paraugs" / f"{stem}_PARAUGS_2000x2500.jpg")
            if Path(para).is_file():
                merged[stem] = rec
    report = {
        "attempt": attempt,
        "workflow": "v2_ai_first_hybrid",
        "workflow_version": WORKFLOW_VERSION,
        "code_commit": _RUN_META.get("code_commit"),
        "config_sha256": _RUN_META.get("config_sha256"),
        "config": _RUN_META.get("config"),
        "stage": stage,
        "target_seconds_per_image": 20,
        "grade_profile": str(PROFILE_PATH),
        "profile_compute_s": None if profile_s is None else round(float(profile_s), 3),
        "collage": collage_path,
        "collage_s": None if collage_s is None else round(float(collage_s), 3),
        "images": merged,
        "summary": _summary(records),
    }
    atomic_write_json(REPORT_PATH, report)
    return report


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
    _resolve_args(args)
    _set_run_meta(args)
    if args.isnet_worker:
        return isnet_worker(args.isnet_worker[0], args.isnet_worker[1])
    if args.isnet_auto:
        a = args.isnet_auto
        return isnet_auto_worker(a[0], a[1], a[2], float(a[3]), a[4] == "1", a[5])
    if args.make_zip:
        return make_zip(args.zip_name or None)

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

                if method in ("plate_texture", "isnet_pad_retry"):
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

    active = [r for r in records if r.get("status") == "mask_ready"]
    if not active:
        report = _persist_report(records, args.attempt, "blocked", profile_s)
        print(f"V2.1 BLOĶĒTS: nav nevienas gatavas maskas. Kopsavilkums={report['summary']}", flush=True)
        return 2

    # 2. fāze: viens krāsu profils pabeigtajām maskām.
    t = time.perf_counter()
    profile = compute_grade_profile(active, args.wb_mode)
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
