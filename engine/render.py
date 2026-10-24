"""Renderēšana: MASTER/PARAUGS būve un kolāža.

Izņemts no workflow_v2.py solī 6.5; funkciju ķermeņi nemainīti
(AST hash Pierādījums, PROGRESS §65).
"""
import gc
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from loop import (  # noqa: E402
    CLOSEUP_CROPS, OUT, STUDIO_SHADOW_ANGLE_DEG, STUDIO_SHADOW_OFFSET_PX,
    decontaminate_rim, extend_foreground_colors, measure_shadow_angle,
    para_scale, refine_alpha, render_paraugs, studio_shadow_bg,
)

from engine.grade import apply_lut  # noqa: E402
from engine.infra import (  # noqa: E402
    open_rgb_recorded, save_gray_png, save_image_atomic, sha256_file,
)
from engine.masks import _mask_stats, plan_closeup_crop  # noqa: E402
from engine.provenance import (  # noqa: E402
    DECONTAM_PARAMS, append_mask_stage, decontam_needed, read_mask_provenance,
)
from engine.report import COLLAGE_PATH  # noqa: E402

# Stems, kuriem NEpiemērot decontaminate_rim (audums pāri kadra malai).
# main() to piepilda ar --no-decontam (mutācija, nevis pārsiešana).
NO_DECONTAM: set[str] = set()

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
