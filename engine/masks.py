"""Masku ceļš: ISNet workeri, QA, papīra/plate/closeup atbalsts.

Izņemts no workflow_v2.py solī 6.4. Ķermeņi nemainīti, izņemot divas
apzinātas rindas: workera pašizsaukumā `__file__` aizstāts ar
ENTRY_SCRIPT (fasādes fails), jo šis modulis vairs nav CLI ieeja
(AST Pierādījums ar šo vienu izņēmumu, PROGRESS §64).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from loop import OUT, clean_mask  # noqa: E402

from engine.config import CFG  # noqa: E402
from engine.infra import (  # noqa: E402
    ROTATIONS_CW, fit_size, open_rgb, parse_rotations, save_image_atomic,
)

ENTRY_SCRIPT = Path(__file__).resolve().parents[1] / "workflow_v2.py"
TMP_SOFT = Path("/tmp/workflow_v2_soft")

def isnet_worker(src: str, dst: str) -> int:
    """Atsevišķs process vienai ISNet inferencei (atmiņas higiēnai)."""
    ROTATIONS_CW.update(parse_rotations([os.environ.get("WORKFLOW_V2_ROTATE", "")]))
    os.environ.setdefault("U2NET_HOME", "/var/tmp/rembg_home")
    if os.path.isdir("/var/tmp/pylibs") and "/var/tmp/pylibs" not in sys.path:
        sys.path.insert(0, "/var/tmp/pylibs")
    prof_t: dict = {}
    _t = time.perf_counter()
    # Tieši onnxruntime, nevis rembg: `import rembg` maksā 2.3-2.4 s, `import
    # onnxruntime` 0.15 s. Maskas ir bitu identiskas (skat. isnet_native.py).
    import isnet_native as _isnet
    prof_t["import_s"] = round(time.perf_counter() - _t, 3)

    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    session = _isnet.make_session()
    init_s = time.perf_counter() - t0
    full = open_rgb(src)
    proxy_size = fit_size(full.width, full.height, 768, 1024)
    img = full.resize(proxy_size, Image.LANCZOS)
    del full
    t0 = time.perf_counter()
    mask = _isnet.predict_mask(session, img)
    pred_s = time.perf_counter() - t0
    save_image_atomic(mask, Path(dst))
    print(
        json.dumps(
            {
                "init_s": round(init_s, 3),
                "predict_s": round(pred_s, 3),
                "proxy_size": list(proxy_size),
            }
        ),
        flush=True,
    )
    return 0


def isnet_auto_worker(src: str, plain_dst: str, pad_dst: str, pad: float,
                      force: str, tex_relaxed: str) -> int:
    """Viens process, viens modelis: parastā ISNet maska un, ja vajag, apmales retry.

    Kāpēc tā: `from rembg import ...` maksā ~2.3 s katrā apakšprocesā, un retry
    gadījumā to maksājām DIVREIZ. Tagad imports un modeļa ielāde notiek reizi.

    Kā tas ietilpst RAM (mērīts): ar noklusēto onnxruntime atmiņas arēnu pēc
    pirmās inference process bija 1215 MB un otra inference nomira ar SIGKILL.
    Ar `enable_cpu_mem_arena=False, enable_mem_pattern=False` tas ir **611 MB**,
    un abas inferences iztur. Maska ir **bitu identiska** (maks. atšķirība 0),
    laiks tāds pats (2.62 s pret 2.67 s). Tāpēc šis nav kompromiss kvalitātē.

    Uzvedība nemainās: tie paši QA, tie paši aizsargi, tas pats pad.
    """
    ROTATIONS_CW.update(parse_rotations([os.environ.get("WORKFLOW_V2_ROTATE", "")]))
    os.environ.setdefault("U2NET_HOME", "/var/tmp/rembg_home")
    if os.path.isdir("/var/tmp/pylibs") and "/var/tmp/pylibs" not in sys.path:
        sys.path.insert(0, "/var/tmp/pylibs")
    prof_t: dict = {}
    _t = time.perf_counter()
    # Tieši onnxruntime, nevis rembg: `import rembg` maksā 2.3-2.4 s, `import
    # onnxruntime` 0.15 s. Maskas ir bitu identiskas (skat. isnet_native.py).
    import isnet_native as _isnet
    prof_t["import_s"] = round(time.perf_counter() - _t, 3)

    t0 = time.perf_counter()
    session = _isnet.make_session()
    init_s = round(time.perf_counter() - t0, 3)

    _t = time.perf_counter()
    full = open_rgb(src)
    W, H = full.size
    prof_t["open_s"] = round(time.perf_counter() - _t, 3)
    res: dict = {"init_s": init_s, "retried": False, "prof": prof_t}

    proxy = fit_size(W, H, 768, 1024)
    small = full.resize(proxy, Image.LANCZOS)
    t = time.perf_counter()
    soft = _isnet.predict_mask(session, small)
    res["predict_s"] = round(time.perf_counter() - t, 3)
    res["proxy_size"] = list(proxy)
    save_image_atomic(soft, Path(plain_dst))
    qa = ai_mask_qa(np.asarray(soft))
    res["qa"] = qa
    del small

    if qa["accept"] and not force:
        print(json.dumps(res), flush=True)
        return 0

    _t = time.perf_counter()
    from paper_leak import measure_paper_colour as _mpc
    probe_strict = _mpc(full)            # viens mērījums, izmanto profils UN QA
    prof_t["paper_strict_s"] = round(time.perf_counter() - _t, 3)
    _t = time.perf_counter()
    prof = paper_profile(full, probe=probe_strict)
    relaxed = False
    if prof is None:
        # `tex_limit` maina TIKAI lēmumu "vai tas skaitās papīrs", nevis mērījumu
        # (rgb/lab/candidates ir identiski). Tāpēc otro pilno skenēšanu var atvasināt
        # no pirmās: tā ir bitu ekvivalenta atsevišķam `paper_profile(tex_limit=2.5)`
        # izsaukumam, bet maksā 0.7 s mazāk. Pārbaudīts ar tiešu salīdzinājumu.
        _t = time.perf_counter()
        if probe_strict.get("tex_median", 9e9) <= float(tex_relaxed):
            probe_relaxed = dict(probe_strict)
            probe_relaxed["plausible"] = True
            probe_relaxed["confidence"] = probe_strict.get("confidence_base")
            prof = paper_profile(full, probe=probe_relaxed)
            relaxed = prof is not None
        prof_t["paper_relaxed_s"] = round(time.perf_counter() - _t, 3)
    if prof is None:
        res["no_profile"] = True
        print(json.dumps(res), flush=True)
        return 0

    pw, ph = proxy
    C = 768
    inner_w = max(1, int(round(C * pad * pw / max(pw, ph))))
    inner_h = max(1, int(round(C * pad * ph / max(pw, ph))))
    x0, y0 = (C - inner_w) // 2, (C - inner_h) // 2
    _t = time.perf_counter()
    canvas = Image.new("RGB", (C, C), tuple(prof["rgb"]))
    canvas.paste(full.convert("RGB").resize((inner_w, inner_h), Image.LANCZOS), (x0, y0))
    prof_t["canvas_s"] = round(time.perf_counter() - _t, 3)
    t = time.perf_counter()
    pad_soft = _isnet.predict_mask(session, canvas)
    res["pad_predict_s"] = round(time.perf_counter() - t, 3)
    del canvas

    # Saglabājam apmales masku IEKŠĒJĀ loga izmērā; pārskalošanu uz oriģinālu
    # veic galvenais process. Pilna izmēra PNG rakstīšana maksāja 0.6 s.
    pad_inner = pad_soft.crop((x0, y0, x0 + inner_w, y0 + inner_h))
    _t = time.perf_counter()
    save_image_atomic(pad_inner, Path(pad_dst))
    m_pad = (np.asarray(pad_inner.resize((W, H), Image.LANCZOS)) > 128).astype(np.uint8)
    del pad_inner, pad_soft
    prof_t["pad_upscale_s"] = round(time.perf_counter() - _t, 3)

    _t = time.perf_counter()
    guards = pad_guards(m_pad, prof, (W, H))
    prof_t["guards_s"] = round(time.perf_counter() - _t, 3)
    _t = time.perf_counter()
    pad_qa = closeup_mask_qa(m_pad, full, paper=probe_strict)
    prof_t["closeup_qa_s"] = round(time.perf_counter() - _t, 3)
    res.update({
        "retried": True,
        "pad": pad,
        "paper_rgb": prof["rgb"],
        "profile_relaxed": relaxed,
        "guards": guards,
        "pad_qa": pad_qa,
    })
    del m_pad, full
    print(json.dumps(res), flush=True)
    return 0


def run_isnet(src: Path, dst: Path) -> dict:
    env = os.environ.copy()
    env["U2NET_HOME"] = env.get("U2NET_HOME", "/var/tmp/rembg_home")
    env["OMP_NUM_THREADS"] = env.get("OMP_NUM_THREADS", "2")
    pp = ["/home/user/loop_bildes"]
    if os.path.isdir("/var/tmp/pylibs"):
        pp.insert(0, "/var/tmp/pylibs")
    if env.get("PYTHONPATH"):
        pp.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pp)
    if ROTATIONS_CW:
        env["WORKFLOW_V2_ROTATE"] = ",".join(f"{k}:{v}" for k, v in ROTATIONS_CW.items())
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(ENTRY_SCRIPT), "--isnet-worker", str(src), str(dst)],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        tail = "\n".join(proc.stdout.splitlines()[-30:])
        raise RuntimeError(f"ISNet worker exit={proc.returncode}\n{tail}")
    worker = {}
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                worker = json.loads(line)
                break
            except Exception:
                pass
    return {"wall_s": wall, **worker}


def run_isnet_auto(src: Path, plain_dst: Path, pad_dst: Path, pad: float,
                   force: bool) -> dict:
    """Palaiž `isnet_auto_worker`: parastā maska + (ja vajag) apmales retry.

    Atgriež worker atbildi: qa, retried, guards, pad_qa, paper_rgb, profile_relaxed.
    """
    env = os.environ.copy()
    env["U2NET_HOME"] = env.get("U2NET_HOME", "/var/tmp/rembg_home")
    env["OMP_NUM_THREADS"] = env.get("OMP_NUM_THREADS", "2")
    pp = ["/home/user/loop_bildes"]
    if os.path.isdir("/var/tmp/pylibs"):
        pp.insert(0, "/var/tmp/pylibs")
    if env.get("PYTHONPATH"):
        pp.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pp)
    if ROTATIONS_CW:
        env["WORKFLOW_V2_ROTATE"] = ",".join(f"{k}:{v}" for k, v in ROTATIONS_CW.items())
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(ENTRY_SCRIPT), "--isnet-auto",
         str(src), str(plain_dst), str(pad_dst), str(pad),
         "1" if force else "0", str(CFG["mask"]["pad_tex_relaxed"])],
        env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300,
    )
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        tail = "\n".join(proc.stdout.splitlines()[-30:])
        raise RuntimeError(f"ISNet auto worker exit={proc.returncode}\n{tail}")
    res: dict = {}
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                res = json.loads(line)
                break
            except Exception:
                pass
    res["wall_s"] = round(wall, 3)
    return res


def _mask_stats(binary: np.ndarray) -> dict:
    b = (binary > 0).astype(np.uint8)
    cov = float(b.mean())
    n, lab, stats, _ = cv2.connectedComponentsWithStats(b, connectivity=8)
    if n <= 1 or b.sum() == 0:
        return {
            "coverage": round(cov, 4),
            "largest_component_ratio": 0.0,
            "bbox_fraction": [0.0, 0.0],
            "bbox_area_fraction": 0.0,
            "silhouette_fill": 0.0,
            "edges": {"top": 0.0, "bottom": 0.0, "left": 0.0, "right": 0.0},
        }
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    largest_ratio = float(stats[idx, cv2.CC_STAT_AREA] / max(int(b.sum()), 1))
    x, y, w, h, _ = [int(v) for v in stats[idx]]
    H, W = b.shape
    largest = lab == idx
    return {
        "coverage": round(cov, 4),
        "largest_component_ratio": round(largest_ratio, 4),
        "bbox_fraction": [round(w / W, 4), round(h / H, 4)],
        "bbox_area_fraction": round((w / W) * (h / H), 4),
        # Cik pilna ir siluete: maskas laukums / tās bbox laukums. Sadrumstalota
        # maska (audums + pakaramais + caurumi) dod ~0.44, vesela ~0.74-0.97.
        "silhouette_fill": round(float(b.sum()) / float(max(1, w * h)), 4),
        "edges": {
            "top": round(float(largest[0].mean()), 4),
            "bottom": round(float(largest[-1].mean()), 4),
            "left": round(float(largest[:, 0].mean()), 4),
            "right": round(float(largest[:, -1].mean()), 4),
        },
    }


def ai_mask_qa(soft: np.ndarray) -> dict:
    """Noraida gadījumus, kad AI ir izvēlējies birku/apkakli, nevis apģērbu.
    Robežas: config.toml [mask] (solis 4)."""
    _M = CFG["mask"]
    q = _mask_stats((soft >= 128).astype(np.uint8))
    accept = bool(
        _M["ai_qa_coverage_min"] <= q["coverage"] <= _M["ai_qa_coverage_max"]
        and q["largest_component_ratio"] >= _M["ai_qa_largest_min"]
        and q["bbox_area_fraction"] >= _M["ai_qa_bbox_area_min"]
        and q["bbox_fraction"][0] >= _M["ai_qa_bbox_w_min"]
        and q["bbox_fraction"][1] >= _M["ai_qa_bbox_h_min"]
        and q["silhouette_fill"] >= _M["silhouette_fill_min"]
    )
    q.update(
        {
            "soft_uncertain_fraction": round(float(((soft > 16) & (soft < 240)).mean()), 4),
            "accept": accept,
            "reason": ("pilna silueta QA" if accept else
                       (f"sadrumstalota siluete ({q['silhouette_fill']:.3f} < {_M['silhouette_fill_min']})"
                        if q["silhouette_fill"] < _M["silhouette_fill_min"]
                        else "iespējams izvēlēts tikai objekta fragments")),
        }
    )
    return q


def paper_profile(img: Image.Image, tex_limit: float = 1.0, probe: dict | None = None):
    """Papīra krāsa + papīrveidīgo pikseļu karte 1/4 mērogā. None, ja nav papīra.

    `tex_limit`: cik teksturēts fons vēl skaitās papīrs. Noklusējums 1.0 domāts
    gludam fotopapīram. Graudains kartons (tex ~1.6) ir lietojams, bet to
    ieslēdz APZINĀTI — retry ceļš to dara un ieraksta `profile_relaxed` atskaitē.
    """
    try:
        from paper_leak import measure_paper_colour, lab_chunked, texture_map
    except Exception:
        return None
    if probe is None:                     # ļauj atkārtoti izmantot jau izmērīto
        probe = measure_paper_colour(img, tex_limit=tex_limit)
    if not probe.get("plausible", True):
        return None
    small = img.convert("RGB").resize(
        (max(64, img.width // 4), max(64, img.height // 4)), Image.LANCZOS)
    lab = lab_chunked(np.asarray(small))
    L = lab[..., 0]
    tex = texture_map(L, 5)
    h, w = L.shape
    rp = max(6, int(round(min(h, w) * 0.02)))
    ring = np.zeros((h, w), bool)
    ring[:rp] = ring[-rp:] = True
    ring[:, :rp] = ring[:, -rp:] = True
    p0 = np.array(probe["lab"], np.float32)
    dC = np.linalg.norm(lab[..., 1:] - p0[1:], axis=-1)
    sel = ring & (np.abs(L - p0[0]) < 20)
    if sel.sum() < 200:
        sel = ring
    t_c = float(np.clip(np.percentile(dC[sel], 92), 0.8, 4.0))
    t_t = float(np.clip(np.percentile(tex[sel], 92), 0.5, 3.0))
    L_floor = float(max(0.0, np.percentile(L[sel], 10) - 2.0))
    L_paper = float(np.median(L[sel]))
    # SVARĪGI: papīram ir arī AUGŠĒJĀ robeža. Bez tās `L >= L_floor` pieļauj
    # VISU, kas gaišāks par papīru, un balts trikotāža (L* 75) tiek saskaitīta
    # kā papīrs (L* 58). Tieši tā radās viltus pārplūde 160550 bildē: aizsargs
    # skaitīja pašu kreklu. Papīrs ir šaurs joslas ap L_paper, nevis "viss
    # gaišais".
    paper_like = ((dC <= t_c) & (tex <= t_t) & (L >= L_floor)
                  & (L <= L_paper + 14.0))
    return {
        "rgb": probe["rgb"], "shape": (h, w), "paper_like": paper_like,
        "tex_p95": float(np.percentile(tex[sel], 95)),
        "lab": lab, "tex": tex,
        "L_paper": L_paper,
    }


def pad_guards(mask_bin: np.ndarray, prof, orig_size) -> dict:
    """Divi aizsargi: cik maska aizņem papīru un cik auduma paliek ārpusē."""
    if prof is None:
        return {"overflow": None, "uncovered": None}
    m = Image.fromarray((mask_bin.astype(np.uint8) * 255)).resize(
        (prof["shape"][1], prof["shape"][0]), Image.NEAREST)
    m = np.asarray(m) > 128
    if not m.any():
        return {"overflow": 1.0, "uncovered": 1.0}
    overflow = float((m & prof["paper_like"]).sum() / m.sum())
    L = prof["lab"][..., 0]
    fabric = (prof["tex"] > max(prof["tex_p95"], 0.5)) & (L < 0.70 * prof["L_paper"])
    uncovered = float(((~m) & fabric).mean())
    return {"overflow": round(overflow, 4), "uncovered": round(uncovered, 4)}


def plate_mask(orig: Image.Image) -> tuple[np.ndarray, dict]:
    """Maska no virsmas tekstūras. Atgriež (binary uint8, info ar QA)."""
    try:
        import plate_segment as _ps
        from scipy.ndimage import binary_erosion, binary_dilation
    except Exception as exc:                       # pragma: no cover
        return np.zeros((orig.height, orig.width), np.uint8), {"ok": False, "error": str(exc)}

    t = time.perf_counter()
    m_half, L, info = _ps.garment_mask_half(orig)
    m = m_half.astype(bool)
    W, H = orig.size

    def lstd(a, w):
        mu = cv2.boxFilter(a, -1, (w, w))
        mu2 = cv2.boxFilter(a * a, -1, (w, w))
        return np.sqrt(np.maximum(mu2 - mu * mu, 0))

    E7 = lstd(L, 7)
    interior = binary_erosion(m, iterations=60)
    if not interior.any():
        return np.zeros((H, W), np.uint8), {"ok": False, "error": "maska pārāk maza QA"}
    gi = float(np.median(E7[interior]))
    b_in = m & ~binary_erosion(m, iterations=4)
    b_out = binary_dilation(m, iterations=4) & ~m
    inner_ratio = float(np.median(E7[b_in])) / gi if b_in.any() else 0.0
    outer_ratio = float(np.median(E7[b_out])) / gi if b_out.any() else 0.0

    # fons maskas iekšpusē: nospiest L* no vietējās plaknes + zema tekstūra
    # + papīra krāsa. Krāsas nosacījums pielikts 2026-10-24 (birkas makro
    # `124406358`, PROGRESS §69): "gluds + plakans" vien karogoja vafeļu
    # rindu ēnu līnijas (2.8 % sīku plankumiņu, L* med 66.8), kas nav
    # papīrs (īstais papīrs L* 49-61). Logs = tas pats `L_TOL`, ar ko
    # `_keep_garment` nošķir papīru no gludas krokas. Ja papīra līmeni
    # nevar izmērīt (gredzenā <200 px), paliek vecais skaitījums bez
    # krāsas — nekad ne mīkstāks par iepriekšējo.
    from scipy.ndimage import gaussian_filter
    base = gaussian_filter(L, 60)          # pusizmērā: lokālais L* līmenis
    bg_like = interior & (E7 < 0.55 * gi) & (np.abs(L - base) < 4.0)
    paper_L, paper_E = _ps._paper_level(L, m.astype(np.uint8))
    if np.isfinite(paper_E):
        lo, hi = _ps.L_TOL
        bg_like &= (L >= paper_L + lo) & (L <= paper_L + hi)
    bg_inside = float(bg_like.sum() / max(int(interior.sum()), 1))

    hover = float(m.mean())
    qa = {
        "coverage": round(hover, 4),
        "inner_ratio": round(inner_ratio, 3),
        "outer_ratio": round(outer_ratio, 3),
        "bg_inside": round(bg_inside, 4),
        "paper_L": round(float(paper_L), 1) if np.isfinite(paper_E) else None,
        "interior_E7": round(gi, 2),
        "edge_calib_px": info.get("edge_calib_px"),
        "offset_before_calib": info.get("offset_before_calib"),
        "offset_after_calib": info.get("offset_after_calib"),
        "otsu": float(info["otsu"]) if info.get("otsu") is not None else None,
        "bg_med_E": float(info["bg_med"]) if info.get("bg_med") is not None else None,
        "fg_med_E": float(info["fg_med"]) if info.get("fg_med") is not None else None,
    }
    _P = CFG["plate"]
    reasons = []
    if not (_P["cover_min"] <= hover <= _P["cover_max"]):
        reasons.append(f"segums {hover:.3f} ārpus {_P['cover_min']}-{_P['cover_max']}")
    if inner_ratio < _P["inner_min"]:
        reasons.append(f"iekšmalā fons (attiecība {inner_ratio:.3f} < {_P['inner_min']})")
    if outer_ratio > _P["outer_max"]:
        reasons.append(f"ārpusē audums (attiecība {outer_ratio:.3f} > {_P['outer_max']})")
    if bg_inside > _P["bg_inside_max"]:
        reasons.append(f"fons maskas iekšpusē {bg_inside:.3f} > {_P['bg_inside_max']}")
    qa["accept"] = not reasons
    qa["reason"] = "; ".join(reasons) if reasons else "plāksnes tekstūras QA"
    qa["seconds"] = round(time.perf_counter() - t, 2)
    up = np.asarray(Image.fromarray((m.astype(np.uint8) * 255)).resize((W, H), Image.LANCZOS))
    binary = clean_mask(up, threshold=128, erode_px=1)
    return binary, qa


def isnet_padded_mask(orig: Image.Image, paper_rgb, pad: float | None = None) -> np.ndarray:
    """ISNet uz papīra-konteksta audekla; atgriež masku oriģināla izmērā."""
    if pad is None:
        pad = float(CFG["mask"]["pad_retry"])
    W, H = orig.size
    pw, ph = fit_size(W, H, 768, 1024)
    C = 768
    inner_w = max(1, int(round(C * pad * pw / max(pw, ph))))
    inner_h = max(1, int(round(C * pad * ph / max(pw, ph))))
    canvas = Image.new("RGB", (C, C), tuple(paper_rgb))
    inner = orig.convert("RGB").resize((inner_w, inner_h), Image.LANCZOS)
    x0, y0 = (C - inner_w) // 2, (C - inner_h) // 2
    canvas.paste(inner, (x0, y0))
    del inner
    tmp_in = TMP_SOFT / "pad_retry_in.jpg"
    tmp_out = TMP_SOFT / "pad_retry_out.png"
    tmp_in.parent.mkdir(parents=True, exist_ok=True)
    save_image_atomic(canvas, tmp_in, quality=95)
    del canvas
    run_isnet(tmp_in, tmp_out)
    a = Image.open(tmp_out).convert("L")
    a = a.crop((x0, y0, x0 + inner_w, y0 + inner_h)).resize((W, H), Image.LANCZOS)
    m = np.asarray(a)
    a.close()
    for f in (tmp_in, tmp_out):
        try:
            f.unlink()
        except OSError:
            pass
    return (m > 128).astype(np.uint8)


def plan_closeup_crop(mask_bin: np.ndarray, aspect: float = 2000 / 2500,
                      want_edges: int = 3, min_linear: float = 0.55,
                      max_shrink_for_4: float = 0.15) -> tuple:
    """4:5 logs, kurā audums sasniedz vismaz `want_edges` malas (GATE_F kritērijs).

    Mērķis ir LEKSIKOGRĀFISKS, nevis "lielākais logs":
      1) vispirms maksimizē to malu skaitu, kas sasniegtas (4 labāk par 3),
      2) tad maksimizē loga izmēru.

    Kāpēc tā: pirmā versija maksimizēja tikai izmēru un atrada logu, kas
    sākās VIRS apģērba augšmalas — iznākumā bija redzama 199 px (8 %) gaiša
    josla augšā. Full-bleed tuvplānā tāda josla ir defekts. To novērš tikai
    tas, ka 4. mala tiek pieprasīta AUGSTĀK par izmēru.

    `max_shrink_for_4` ierobežo, cik daudz drīkst samazināt logu, lai
    iegūtu 4. malu (0.15 = 15 procentpunkti no kadra malas).
    """
    ys, xs = np.nonzero(mask_bin)
    if len(xs) == 0:
        return None, 0
    H, W = mask_bin.shape
    m = (mask_bin > 0).astype(np.uint8)
    integral = cv2.integral(m)

    def frac(x0, y0, x1, y1):
        s = (integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0])
        return float(s) / float(max(1, (x1 - x0) * (y1 - y0)))

    # Mala tiek vērtēta JOSLĀ, nevis vienā rindā. Viena rinda ar slieksni 0.5
    # bija pārāk trausla: 160550 gadījumā tā atzina par "sasniegtu" malu, aiz
    # kuras vēl bija ~2 % oriģinālā papīra (197-209 pret BG 243).
    def edges_of(x0, y0, x1, y1):
        b = max(4, int(round(0.005 * max(x1 - x0, y1 - y0))))
        return [frac(x0, y0, x1, min(y1, y0 + b)), frac(x0, max(y0, y1 - b), x1, y1),
                frac(x0, y0, min(x1, x0 + b), y1), frac(max(x0, x1 - b), y0, x1, y1)]

    best3 = None            # (scale, box, edges)
    scale3 = None
    for scale in np.arange(0.98, min_linear - 1e-9, -0.02):
        h = int(round(scale * H))
        w = int(round(h * aspect))
        if w > W:
            w = int(round(scale * W))
            h = int(round(w / aspect))
        if w < 16 or h < 16 or w > W or h > H:
            continue
        if scale3 is not None and scale < scale3 - max_shrink_for_4:
            break
        step_x = max(8, w // 14)
        step_y = max(8, h // 14)
        found4 = None
        for y0 in range(0, H - h + 1, step_y):
            for x0 in range(0, W - w + 1, step_x):
                e = edges_of(x0, y0, x0 + w, y0 + h)
                n = sum(v >= 0.85 for v in e)
                if n >= 4 and found4 is None:
                    found4 = (x0, y0, x0 + w, y0 + h, e)
                if n >= want_edges and best3 is None:
                    best3 = (x0, y0, x0 + w, y0 + h, e)
                    scale3 = scale
            if found4 is not None:
                break
        if found4 is not None:
            x0, y0, x1, y1, e = found4
            return (x0 / W, y0 / H, x1 / W, y1 / H), 4
    if best3 is None:
        return None, 0
    x0, y0, x1, y1, e = best3

    # Joslu apgriešana: 3-malu logs var sākties virs apģērba (piem. apkakles
    # loks), un tad augšā paliek redzama gaiša josla. Tā nav full-bleed.
    # Griežam no joslas malas uz iekšu, saglabājot 4:5, kamēr josla < 4 %
    # un logs joprojām sasniedz 3 malas un nav mazāks par min_linear.
    def band(box):
        bx0, by0, bx1, by1 = box
        sub = m[by0:by1, bx0:bx1]
        rows = sub.mean(axis=1)
        cols = sub.mean(axis=0)
        t = int((rows > 0.5).argmax()) if (rows > 0.5).any() else (by1 - by0)
        b = int((rows[::-1] > 0.5).argmax()) if (rows > 0.5).any() else (by1 - by0)
        l = int((cols > 0.5).argmax()) if (cols > 0.5).any() else (bx1 - bx0)
        r = int((cols[::-1] > 0.5).argmax()) if (cols > 0.5).any() else (bx1 - bx0)
        return {"top": t, "bottom": b, "left": l, "right": r}

    for _ in range(40):
        bx0, by0, bx1, by1 = x0, y0, x1, y1
        bd = band((bx0, by0, bx1, by1))
        side = max(bd, key=lambda k: bd[k])
        sh = max(bd.values())
        if sh <= 0.04 * min(bx1 - bx0, by1 - by0):
            break
        if side in ("top", "bottom"):
            drop = bd[side]
            nh = (by1 - by0) - drop
            nw = int(round(nh * aspect))
            if nh < min_linear * H or nw > W:
                break
            if side == "top":
                ny0, ny1 = by0 + drop, by0 + drop + nh
            else:
                ny0, ny1 = by0, by0 + nh
            nx0 = min(max(0, (bx0 + bx1 - nw) // 2), W - nw)
            nx1 = nx0 + nw
        else:
            drop = bd[side]
            nw = (bx1 - bx0) - drop
            nh = int(round(nw / aspect))
            if nw < min_linear * W or nh > H:
                break
            if side == "left":
                nx0, nx1 = bx0 + drop, bx0 + drop + nw
            else:
                nx0, nx1 = bx0, bx0 + nw
            ny0 = min(max(0, (by0 + by1 - nh) // 2), H - nh)
            ny1 = ny0 + nh
        e2 = edges_of(nx0, ny0, nx1, ny1)
        if sum(v >= 0.85 for v in e2) < want_edges:
            break
        x0, y0, x1, y1, e = nx0, ny0, nx1, ny1, e2

    n_ok = sum(v >= 0.85 for v in e)
    return (x0 / W, y0 / H, x1 / W, y1 / H), n_ok


def closeup_mask_qa(binary: np.ndarray, orig: Image.Image | None = None,
                    uncovered_fabric_limit: float = 0.05,
                    paper: dict | None = None) -> dict:
    """Tuvplāna maskas QA — paredz arī to, ko teiks ārējie vārti D un F.

    Bez šīs pārbaudes maker varēja izdot bildi, kuru checkeris pēc tam
    noraida (tā notika uz paraugiem 3 un 4). Trīs daļas:

    1. veselums       — segums, lielākā komponente, bbox (kā līdz šim);
    2. nepārklāts audums — ārpus maskas palicis reģions, kas pēc tekstūras un
       krāsas ir audums, nevis papīrs. Slieksnis 5 % no kadra ir atvasināts no
       datiem: uz trim labajām/daļēji labajām maskām 0.0072–0.0200, uz bojātās
       (maska apstājusies pusceļā) 0.5120 — 25x atstarpe;
    3. malas          — tuvplānam audumam jāsasniedz vismaz 3 malas, citādi
       GATE_F to noraidīs.
    """
    q = _mask_stats(binary)
    # masks come as bool, 0/1 uint8 or 0/255 uint8 - normalise, do not assume
    m = binary.astype(bool) if binary.dtype == bool else (binary > 0)
    edges = {
        "top": round(float(m[0].mean()), 4),
        "bottom": round(float(m[-1].mean()), 4),
        "left": round(float(m[:, 0].mean()), 4),
        "right": round(float(m[:, -1].mean()), 4),
    }
    edges_ok = sum(v >= 0.50 for v in edges.values())
    q["edges"] = edges
    q["edges_at_50pct"] = int(edges_ok)

    uncovered = None
    if orig is not None:
        try:
            from paper_leak import texture_map, measure_paper_colour, lab_chunked
            small = orig.convert("RGB")
            k = 2
            small = small.resize((max(64, small.width // k), max(64, small.height // k)),
                                 Image.LANCZOS)
            lab = lab_chunked(np.asarray(small))
            tex = texture_map(lab[..., 0], 5)
            mm = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize(
                small.size, Image.NEAREST)) > 128
            if paper is None:                 # ļauj atkārtoti izmantot jau izmērīto
                paper = measure_paper_colour(orig)
            p0 = np.array(paper["lab"], np.float32)
            dC = np.linalg.norm(lab[..., 1:] - p0[1:], axis=-1)
            rp = max(6, int(round(0.02 * min(mm.shape))))
            ring = np.zeros_like(mm)
            ring[:rp] = ring[-rp:] = True
            ring[:, :rp] = ring[:, -rp:] = True
            # Reference texture must come from PAPER pixels only: if the garment
            # touches the frame, a plain ring percentile would be inflated by
            # fabric and nothing would ever be flagged.
            near_paper = ring & (dC < 3.0) & (np.abs(lab[..., 0] - p0[0]) < 25.0)
            ref = near_paper if near_paper.sum() >= 200 else ring
            t95 = float(np.percentile(tex[ref], 95))
            t_cut = max(t95, 0.5)
            # Textured AND (colour-cast OR clearly darker than the paper).
            # Chroma alone would miss neutral grey fabric, whose chroma equals
            # the paper's; texture is the primary signal, darkness/chroma guard.
            is_fabric = ((tex > t_cut)
                         & ((dC > 2.0) | (lab[..., 0] < 0.70 * p0[0])))
            uncovered = float(((~mm) & is_fabric).mean())
        except Exception as exc:      # QA nedrīkst nogāzt ražošanu
            q["uncovered_fabric_error"] = f"{type(exc).__name__}: {exc}"
    q["uncovered_fabric_fraction"] = None if uncovered is None else round(uncovered, 5)

    reasons = []
    if not (0.25 <= q["coverage"] <= 0.98):
        reasons.append(f"segums {q['coverage']:.3f} ārpus 0.25–0.98")
    if q["largest_component_ratio"] < 0.90:
        reasons.append(f"lielākā komponente {q['largest_component_ratio']:.3f} < 0.90")
    if q["bbox_area_fraction"] < 0.30:
        reasons.append(f"bbox {q['bbox_area_fraction']:.3f} < 0.30")
    if uncovered is not None and uncovered > uncovered_fabric_limit:
        reasons.append(f"nepārklāts audums {uncovered:.4f} > {uncovered_fabric_limit}")
    # Malu kritērijs šeit NAV iekļauts apzināti: maskas pareizība un
    # kompozīcija ir divas dažādas lietas. Ja maska ir laba, bet nesasniedz
    # malas, to atrisina `plan_closeup_crop`, nevis cita maska.
    q["is_closeup"] = bool(q["coverage"] >= 0.60)

    q.update(
        {
            "accept": not reasons,
            "reason": "auto-tuvplāna maskas QA" if not reasons else "; ".join(reasons),
        }
    )
    return q


def _mask_polygons(mask: np.ndarray, min_area_frac: float, max_polys: int) -> list[list[list[float]]]:
    m = (mask > 0).astype(np.uint8)
    H, W = m.shape
    cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    out = []
    for cnt in cnts:
        area = float(cv2.contourArea(cnt))
        if area < min_area_frac * W * H:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, max(2.0, 0.008 * peri), True).reshape(-1, 2)
        if len(approx) < 3:
            x, y, w, h = cv2.boundingRect(cnt)
            approx = np.array([[x, y], [x + w, y], [x + w, y + h], [x, y + h]], np.float32)
        if len(approx) > 28:
            idx = np.linspace(0, len(approx) - 1, 28).round().astype(int)
            approx = approx[np.unique(idx)]
        out.append([[round(float(x / W), 4), round(float(y / H), 4)] for x, y in approx])
        if len(out) >= max_polys:
            break
    return out


def save_seed_proposal(stem: str, small: Image.Image, sure_bg: np.ndarray,
                       sure_fg: np.ndarray, ai: np.ndarray) -> str:
    arr = np.asarray(small).astype(np.float32)
    arr[sure_bg] = arr[sure_bg] * 0.45 + np.array([30, 80, 255], np.float32) * 0.55
    arr[sure_fg] = arr[sure_fg] * 0.55 + np.array([40, 220, 80], np.float32) * 0.45
    ai_bin = (ai >= 128).astype(np.uint8)
    contours, _ = cv2.findContours(ai_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.clip(arr, 0, 255).astype(np.uint8)
    cv2.drawContours(out, contours, -1, (255, 40, 40), 3)
    img = Image.fromarray(out)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, 54], fill=(255, 255, 255))
    d.text((8, 7), f"{stem} SEED PROPOSAL", fill=(0, 0, 0))
    d.text((8, 29), "zils=sure BG, zaļš=sure FG, sarkana kontūra=ISNet", fill=(0, 0, 0))
    path = Path(OUT) / "audits" / f"{stem}_SEED_PROPOSAL.jpg"
    save_image_atomic(img, Path(path), quality=92)
    return str(path)


# ---------------------------------------------------------------------------
# Iekšējo caurumu klasificēšana pēc satura (PROGRESS §97)
# ---------------------------------------------------------------------------
def _hole_channel_cut(m: np.ndarray, hole: np.ndarray, outer_bg: np.ndarray,
                      max_cut: int) -> list[tuple[int, int]] | None:
    """Lētākais 4-savienotais ceļš no cauruma līdz ārējam fonam (0-1 BFS
    ierobežotā ROI): solis pa fonu maksā 0, pa priekšplānu 1. Atgriež
    ceļā esošos FG pikseļus (izgriežamais tiltiņš) vai None, ja ārējais
    fons ROI nav sasniedzams vai tiltiņš pārsniedz `max_cut`."""
    from collections import deque

    H, W = m.shape
    ys, xs = np.where(hole)
    pad = int(CFG["mask"]["hole_border_px"]) + 16
    ry0, ry1 = max(0, int(ys.min()) - pad), min(H, int(ys.max()) + pad + 1)
    rx0, rx1 = max(0, int(xs.min()) - pad), min(W, int(xs.max()) + pad + 1)
    sub_m = m[ry0:ry1, rx0:rx1]
    sub_hole = hole[ry0:ry1, rx0:rx1]
    sub_tgt = outer_bg[ry0:ry1, rx0:rx1]
    if not sub_tgt.any():
        return None
    h, w = sub_m.shape
    dist = np.full((h, w), 10 ** 9, np.int32)
    prev = np.full((h, w), -1, np.int32)
    dq: deque[tuple[int, int]] = deque()
    hy, hx = np.where(sub_hole)
    for y, x in zip(hy.tolist(), hx.tolist()):
        dist[y, x] = 0
        dq.append((y, x))
    target = None
    while dq:
        y, x = dq.popleft()
        d = int(dist[y, x])
        if sub_tgt[y, x]:
            target = (y, x)
            break
        if d > max_cut:
            break
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w:
                nd = d + (1 if sub_m[ny, nx] else 0)
                if nd < dist[ny, nx]:
                    dist[ny, nx] = nd
                    prev[ny, nx] = y * w + x
                    if sub_m[ny, nx]:
                        dq.append((ny, nx))
                    else:
                        dq.appendleft((ny, nx))
    if target is None:
        return None
    cut: list[tuple[int, int]] = []
    cy, cx = target
    while prev[cy, cx] >= 0:
        if sub_m[cy, cx]:
            cut.append((cy + ry0, cx + rx0))
        cy, cx = divmod(int(prev[cy, cx]), w)
    return cut if len(cut) <= max_cut else None


def repair_interior_holes(binary: np.ndarray,
                          orig: Image.Image) -> tuple[np.ndarray, dict]:
    """Ieslēgtus maskas caurumus (>= config [mask].hole_min_px) klasificē
    pēc SATURA, salīdzinot cauruma Lab mediānu un tekstūru (arī
    samazinātā mērogā, §98) ar divām no paša attēla ņemtām referencēm:
    auduma gredzenu ap caurumu un lokālo ārējo fonu. Audumam līdzīgu
    caurumu aizpilda (maska audumu bija pazaudējusi);
    fonam līdzīgu caurumu tuvu kadra malai atver ar šauru kanālu pāri
    tiltiņam; fonam līdzīgu tālu no malas (īsts logs starp apģērba daļām)
    un neskaidru saturu NEAIZTIEK — checker GATE_C paliek tiesnesis.
    Parametri: config.toml [mask] hole_*. Atgriež (binary, info); ja nekas
    nemainās, atgriež ieejas masīvu nemainītu."""
    from scipy import ndimage

    from paper_leak import lab_chunked, measure_paper_colour, texture_map

    t0 = time.perf_counter()
    C = CFG["mask"]
    info: dict = {"holes_total": 0, "holes_ge_min": 0, "actions": [],
                  "seconds": 0.0}
    m = binary > 0
    if not m.any():
        info["seconds"] = round(time.perf_counter() - t0, 3)
        return binary, info
    n, lab, stats, _ = cv2.connectedComponentsWithStats(
        m.astype(np.uint8), connectivity=8)
    if n <= 1:
        info["seconds"] = round(time.perf_counter() - t0, 3)
        return binary, info
    largest = lab == (1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA])))
    holes = ndimage.binary_fill_holes(largest) & ~largest
    if not holes.any():
        info["seconds"] = round(time.perf_counter() - t0, 3)
        return binary, info
    hl, hn = ndimage.label(holes)
    sizes = ndimage.sum(holes, hl, range(1, hn + 1))
    info["holes_total"] = int(hn)
    min_px = int(C["hole_min_px"])
    cand = [i for i in range(1, hn + 1) if sizes[i - 1] >= min_px]
    info["holes_ge_min"] = len(cand)
    if not cand:
        info["seconds"] = round(time.perf_counter() - t0, 3)
        return binary, info

    bg_lab, _ = ndimage.label(~m)
    border_ids = (set(bg_lab[0].tolist()) | set(bg_lab[-1].tolist())
                  | set(bg_lab[:, 0].tolist()) | set(bg_lab[:, -1].tolist()))
    border_ids.discard(0)
    outer_bg = np.isin(bg_lab, list(border_ids)) if border_ids \
        else np.zeros_like(m)
    lab3 = lab_chunked(np.asarray(orig.convert("RGB")))
    tex = texture_map(lab3[..., 0])
    # Tekstūra arī samazinātā mērogā: win=5 pilnā izšķirtspējā ribu
    # audumu (periods ~30 px) mēra kā gludu (izmērīts §97); mērogā
    # 1:hole_tex_scale efektīvais logs ~20 px noķer ribu kontrastu.
    _scale = int(C["hole_tex_scale"])
    _Lds = cv2.resize(lab3[..., 0], None, fx=1.0 / _scale, fy=1.0 / _scale,
                      interpolation=cv2.INTER_AREA)
    tex_s = texture_map(_Lds, 5)

    def _tex_s_med(sel: np.ndarray, oy: int = 0, ox: int = 0) -> float:
        ys, xs = np.where(sel)
        return float(np.median(tex_s[(ys + oy) // _scale,
                                     (xs + ox) // _scale]))

    # Fona tekstūras atsauce mērogā: pie bojātas maskas lokālais "fons"
    # ir piesārņots ar pašu audumu (izmērīts §98: tex 6.97 pret papīra
    # 0.75), tāpēc atsaucei ņem ārējā fona pikseļus, kuru krāsa ir tuva
    # izmērītajai papīra krāsai (E < hole_bg_E), rēķinot samazinātā
    # mērogā. Ja papīra nav (ne-papīra fons), paliek lokālais paraugs.
    _ds_hw = (tex_s.shape[1], tex_s.shape[0])
    _outer_ds = cv2.resize(outer_bg.astype(np.float32), _ds_hw,
                           interpolation=cv2.INTER_AREA) > 0.5
    ts_b_global = None
    _paper = measure_paper_colour(orig)
    if _paper.get("plausible"):
        _lab_ds = cv2.resize(lab3, _ds_hw, interpolation=cv2.INTER_AREA)
        _E = np.linalg.norm(
            _lab_ds - np.array(_paper["lab"], np.float32), axis=2)
        _bg_ref = _outer_ds & (_E < float(C["hole_bg_E"]))
        if int(_bg_ref.sum()) >= 50:
            ts_b_global = float(np.median(tex_s[_bg_ref]))
    H, W = m.shape
    margin = float(C["hole_margin_de"])
    out = m.copy()
    changed = False
    for i in cand:
        hole = hl == i
        area = int(sizes[i - 1])
        ys, xs = np.where(hole)
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        rec_h: dict = {"area": area, "bbox": bbox, "action": "left"}
        inner = ndimage.binary_erosion(hole, iterations=2)
        if not inner.any():
            inner = hole
        ring = (ndimage.binary_dilation(hole, iterations=8) & largest
                & ~ndimage.binary_dilation(hole, iterations=2))
        ex = 128
        x0e, x1e = max(0, bbox[0] - ex), min(W, bbox[2] + ex + 1)
        y0e, y1e = max(0, bbox[1] - ex), min(H, bbox[3] + ex + 1)
        bg_local = outer_bg[y0e:y1e, x0e:x1e]
        if not ring.any() or int(bg_local.sum()) < 200:
            rec_h["reason"] = "nav references parauga"
            info["actions"].append(rec_h)
            continue
        h_med = np.median(lab3[inner], axis=0)
        f_med = np.median(lab3[ring], axis=0)
        b_med = np.median(lab3[y0e:y1e, x0e:x1e][bg_local], axis=0)
        d_fg = float(np.linalg.norm(h_med - f_med))
        d_bg = float(np.linalg.norm(h_med - b_med))
        t_h = float(np.median(tex[inner]))
        t_b = float(np.median(tex[y0e:y1e, x0e:x1e][bg_local]))
        # Asimetrisks tekstūras pierādījums mērogā: AIZPILDĪŠANAI pietiek
        # ar struktūras nepārtrauktību cauruma vietā (logi drīkst skart
        # gredzenu — tieši to mēra ts_h), bet ATVĒRŠANAI gludums jāpierāda
        # ar logiem, kas pilnībā ietilpst caurumā (erodēts kodols ts_h_core);
        # ja kodola nav, gludumu vērtē pilnizšķirtspējas tekstūra.
        ts_h = _tex_s_med(inner)
        _hole_ds = cv2.resize(hole.astype(np.float32),
                              (tex_s.shape[1], tex_s.shape[0]),
                              interpolation=cv2.INTER_AREA) > 0.5
        _hole_core = ndimage.binary_erosion(_hole_ds, iterations=2)
        ts_h_core = (float(np.median(tex_s[_hole_core]))
                     if int(_hole_core.sum()) >= 2 else None)
        ts_r = _tex_s_med(ring)
        ts_b_local = _tex_s_med(bg_local, y0e, x0e)
        ts_b = ts_b_global if ts_b_global is not None else ts_b_local
        # L diapazona sargam ņem auduma L sadalījumu paplašinātā
        # apkārtnē, ne šaurā gredzenā: gredzens ap ieleju joslu satur
        # gandrīz tikai ribu virsotnes (izmērīts §98).
        fg_local = largest[y0e:y1e, x0e:x1e]
        if int(fg_local.sum()) >= 200:
            fg_L = lab3[y0e:y1e, x0e:x1e][fg_local][:, 0]
            fg_L_p5 = float(np.percentile(fg_L, 5))
            fg_L_p95 = float(np.percentile(fg_L, 95))
        else:
            fg_L_p5, fg_L_p95 = float("inf"), float("-inf")
        hole_L = float(h_med[0])
        # Mediāna pret mediānu ribu audumiem melo (caurums = ielejas,
        # gredzena mediāna = ribu virsotnes, §97); tekstūras pierādījums
        # mērogā ar L diapazona sargu tāpēc drīkst pārspēt krāsas
        # spriedumu. Teksturēts fons (koks) sevi aizsargā ar ts_b
        # attiecību: cauruma tekstūrai jābūt būtiski lielākai par paša
        # lokālā fona tekstūru.
        tex_fabric = (ts_h >= float(C["hole_tex_fg_ratio"]) * ts_r
                      and ts_h <= float(C["hole_tex_fg_ratio_max"]) * ts_r
                      and ts_h >= float(C["hole_tex_bg_ratio"]) * ts_b
                      and ts_h >= float(C["hole_tex_min"])
                      and fg_L_p5 - float(C["hole_L_slack"]) <= hole_L
                      <= fg_L_p95 + float(C["hole_L_slack"]))
        color_fabric = d_fg + margin < d_bg
        color_bg = d_bg + margin < d_fg
        if ts_h_core is not None:
            tex_bg_ok = ts_h_core <= max(ts_b * float(C["hole_tex_ratio"]),
                                         ts_b + float(C["hole_tex_abs"]))
        else:
            # Kodola nav: gludumu vērtē pilnizšķirtspējas tekstūra kā 2.6.
            tex_bg_ok = t_h <= max(t_b * float(C["hole_tex_ratio"]),
                                   t_b + float(C["hole_tex_abs"]))
        rec_h.update(d_fg=round(d_fg, 2), d_bg=round(d_bg, 2),
                     tex_hole=round(t_h, 2), tex_bg=round(t_b, 2),
                     tex_hole_s=round(ts_h, 2),
                     tex_hole_core_s=(None if ts_h_core is None
                                      else round(ts_h_core, 2)),
                     tex_ring_s=round(ts_r, 2),
                     tex_bg_s=round(ts_b, 2),
                     tex_bg_local_s=round(ts_b_local, 2),
                     hole_L=round(hole_L, 1),
                     fg_L_p5=round(fg_L_p5, 1), fg_L_p95=round(fg_L_p95, 1),
                     tex_fabric=bool(tex_fabric))
        if tex_fabric or color_fabric:
            if area <= float(C["hole_max_fill_frac"]) * H * W:
                out[hole] = True
                rec_h["action"] = "filled_fabric"
                rec_h["via"] = "texture" if tex_fabric else "color"
                changed = True
            else:
                rec_h["reason"] = "auduma caurums pārsniedz hole_max_fill_frac"
        elif color_bg and tex_bg_ok:
            dist_border = min(bbox[0], bbox[1], W - 1 - bbox[2],
                              H - 1 - bbox[3])
            rec_h["border_dist"] = int(dist_border)
            if dist_border <= int(C["hole_border_px"]):
                cut = _hole_channel_cut(out, hole, outer_bg,
                                        int(C["hole_max_cut_px"]))
                if cut:
                    for y, x in cut:
                        out[y, x] = False
                    rec_h["action"] = "opened_bg"
                    rec_h["cut_px"] = len(cut)
                    changed = True
                else:
                    rec_h["reason"] = "kanāls nav atrasts limita ietvaros"
            else:
                rec_h["reason"] = "fona caurums tālu no malas"
        else:
            rec_h["reason"] = "neskaidrs saturs"
        info["actions"].append(rec_h)
    info["seconds"] = round(time.perf_counter() - t0, 3)
    if changed:
        return out.astype(np.uint8), info
    return binary, info


def lost_fabric_metric(binary: np.ndarray, orig: Image.Image) -> dict:
    """Zaudētā auduma mērījums kandidāta maskai — maker puses spogulis
    checker GATE_Q (PROGRESS §102/§103): auduma tekstūras pikseļi
    šauros silueta līčos/kanālos (aizvērts(siluets) − siluets
    1:q mērogā), % no priekšplāna. Maker to izmanto tikai kā
    TRIGERI rezerves ceļiem (plate/chroma), tāpat kā structural_qa;
    vārtu slieksnis dzīvo checkerī un checker paliek tiesnesis.
    Parametri: config.toml [mask] q_* (piesprausti pret GATE_Q_*)."""
    from scipy import ndimage

    t0 = time.perf_counter()
    C = CFG["mask"]
    rgb_arr = np.asarray(orig.convert("RGB"))
    gray = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2GRAY).astype(np.float32)
    sc = float(C["q_scale"])
    g = cv2.resize(gray, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    m1 = ndimage.uniform_filter(g, 5, mode="nearest")
    m2 = ndimage.uniform_filter(g * g, 5, mode="nearest")
    tex = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    fg = cv2.resize((binary > 0).astype(np.float32),
                    (g.shape[1], g.shape[0]),
                    interpolation=cv2.INTER_AREA) > 0.5
    out: dict = {"lost_fabric_pct": None, "seconds": 0.0}
    if int(fg.sum()) < 100:
        out["seconds"] = round(time.perf_counter() - t0, 3)
        return out
    r_close = int(C["q_close_r_ds"])
    ker = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * r_close + 1, 2 * r_close + 1))
    closed = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_CLOSE, ker) > 0
    bg_lab, _ = ndimage.label(~fg)
    bords = (set(bg_lab[0].tolist()) | set(bg_lab[-1].tolist())
             | set(bg_lab[:, 0].tolist()) | set(bg_lab[:, -1].tolist()))
    bords.discard(0)
    outer = np.isin(bg_lab, list(bords)) if bords else np.zeros_like(fg)
    h, w = g.shape
    s_edge = max(4, int(round(min(h, w) * 0.03)))
    edge_meds = [
        float(np.median(t_sl[o_sl]))
        for t_sl, o_sl in ((tex[:s_edge, :], outer[:s_edge, :]),
                           (tex[-s_edge:, :], outer[-s_edge:, :]),
                           (tex[:, :s_edge], outer[:, :s_edge]),
                           (tex[:, -s_edge:], outer[:, -s_edge:]))
        if int(o_sl.sum()) >= 50
    ]
    tex_bg_outer = float(np.median(tex[outer])) if int(outer.sum()) >= 50 else 0.0
    tex_bg = min([tex_bg_outer] + edge_meds) if edge_meds else tex_bg_outer
    core = ndimage.binary_erosion(fg, iterations=3)
    tex_fg = float(np.median(tex[core])) if core.any() \
        else float(np.median(tex[fg]))
    thr = max(float(C["q_tex_bg_ratio"]) * tex_bg,
              tex_bg + float(C["q_tex_bg_abs"]),
              float(C["q_tex_fg_ratio"]) * tex_fg)
    dist_out = ndimage.distance_transform_edt(~fg)
    cand = closed & (~fg) & (dist_out > 1)
    susp_bays = cand & (tex >= thr)

    hp = g - ndimage.gaussian_filter(g, 1.5)
    hm1 = ndimage.uniform_filter(hp, 5, mode="nearest")
    hm2 = ndimage.uniform_filter(hp * hp, 5, mode="nearest")
    hp_tex = np.sqrt(np.maximum(hm2 - hm1 * hm1, 0.0))
    hp_env = ndimage.median_filter(hp_tex, size=3)
    hp_edge_meds = [
        float(np.median(t_sl[o_sl]))
        for t_sl, o_sl in ((hp_tex[:s_edge, :], outer[:s_edge, :]),
                           (hp_tex[-s_edge:, :], outer[-s_edge:, :]),
                           (hp_tex[:, :s_edge], outer[:, :s_edge]),
                           (hp_tex[:, -s_edge:], outer[:, -s_edge:]))
        if int(o_sl.sum()) >= 50
    ]
    hp_bg_outer = float(np.median(hp_tex[outer])) if int(outer.sum()) >= 50 else 0.0
    hp_bg = min([hp_bg_outer] + hp_edge_meds) if hp_edge_meds else hp_bg_outer
    hp_fg = float(np.median(hp_tex[core])) if core.any() \
        else float(np.median(hp_tex[fg]))
    hp_thr = max(float(C["q_tex_bg_ratio"]) * hp_bg,
                 hp_bg + float(C["q_tex_bg_abs"]),
                 float(C["q_tex_fg_ratio"]) * hp_fg)
    rgb_ds = cv2.resize(rgb_arr, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32)
    rgb_sm = cv2.GaussianBlur(rgb_ds, (0, 0), 2.5)
    chr_vec = rgb_sm - rgb_sm.mean(axis=2, keepdims=True)
    ref_sel = core if core.any() else fg
    chr_med = np.median(chr_vec[ref_sel], axis=0)
    chr_diff = np.linalg.norm(chr_vec - chr_med, axis=2)
    chr_lim = max(12.0, float(np.percentile(chr_diff[ref_sel], 95)) * 1.5)
    sheet_raw = outer & (dist_out >= 3) & (hp_env >= hp_thr) & (chr_diff <= chr_lim)
    sheet_core = ndimage.binary_erosion(sheet_raw, iterations=4)
    cc_s, cn_s = ndimage.label(sheet_core)
    adj_ids = set(np.unique(cc_s[sheet_core & (dist_out <= 8)])) - {0} if cn_s else set()
    susp_sheet = (np.isin(cc_s, list(adj_ids)) & (dist_out <= r_close)
                  if adj_ids else np.zeros_like(fg))

    susp = susp_bays | susp_sheet
    out.update(lost_fabric_pct=round(100.0 * float(susp.sum())
                                      / float(fg.sum()), 3),
               tex_bg=round(tex_bg, 2), tex_fg=round(tex_fg, 2),
               tex_threshold=round(thr, 2),
               seconds=round(time.perf_counter() - t0, 3))
    return out


def boundary_evidence_metric(binary: np.ndarray, orig: Image.Image) -> dict:
    """Robežas pierādījuma mērījums gala maskai — maker puses spogulis
    checker GATE_S (PROGRESS §114-§116): nelīdzena kontūra garā posmā,
    kur avota malas gradients ir vājš (defokuss), nozīmē, ka robeža
    nav pierādāma no pikseļiem. Maker to izmanto kā STOP pirms
    rendera (statuss boundary_uncertain); slieksnis dzīvo checkerī
    un checker paliek tiesnesis. Parametri: config.toml [mask] s_*
    (piesprausti pret GATE_S_*)."""
    from scipy import ndimage

    t0 = time.perf_counter()
    C = CFG["mask"]
    sc = float(C["s_scale"])
    win = int(C["s_win_samples"])
    step = int(C["s_step_samples"])
    limit = int(C["s_limit_windows"])
    out: dict = {"worst_span_windows": None, "limit_windows": limit,
                 "suspicious_windows": 0, "evaluated_windows": 0,
                 "uncertain": False, "seconds": 0.0}

    def done(**kw):
        out.update(kw)
        out["seconds"] = round(time.perf_counter() - t0, 3)
        return out

    gray = cv2.cvtColor(np.asarray(orig.convert("RGB")),
                        cv2.COLOR_RGB2GRAY).astype(np.float32)
    g = cv2.resize(gray, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    g = ndimage.gaussian_filter(g, 1.0)
    fg = cv2.resize((binary > 0).astype(np.float32),
                    (g.shape[1], g.shape[0]),
                    interpolation=cv2.INTER_AREA) > 0.5
    if int(fg.sum()) < 100:
        return done(skipped=True, note="maska praktiski tukša")
    cnts, _ = cv2.findContours(fg.astype(np.uint8), cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return done(skipped=True, note="kontūra nav atrasta")
    contour = max(cnts, key=cv2.contourArea)[:, 0, :].astype(np.float64)
    n = int(len(contour))
    out["contour_points"] = n
    if n < win:
        return done(skipped=True, note="kontūra īsāka par vienu segmentu")

    ext = np.vstack([contour[-10:], contour, contour[:10]])
    med = np.median(
        np.lib.stride_tricks.sliding_window_view(ext, 21, axis=0), axis=2)
    rough = np.linalg.norm(contour - med, axis=1)

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
    susp_starts: list[int] = []
    susp_centers: list[np.ndarray] = []
    win0 = np.arange(win)
    for s in range(0, n, step):
        idx = (s + win0) % n
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
            continue
        evaluated += 1
        grad = float(abs(deriv[ec]))
        rough_frac = float(np.mean(rough[idx] >= float(C["s_rough_ds"])))
        if (rough_frac >= float(C["s_rough_frac_min"])
                and grad <= float(C["s_grad_max"])):
            susp_starts.append(int(s))
            susp_centers.append(contour[idx].mean(axis=0))

    if evaluated < int(C["s_min_windows"]):
        return done(skipped=True, evaluated_windows=int(evaluated),
                    note="pārāk maz vērtējamu robežas segmentu")

    worst = 0
    worst_center = None
    span = int(C["s_span_samples"])
    if susp_starts:
        starts = np.array(susp_starts, dtype=int)
        centers = np.array(susp_centers, dtype=float)
        if n <= span:
            worst = int(len(starts))
            worst_center = centers.mean(axis=0)
        else:
            ext_starts = np.concatenate([starts, starts + n])
            j = 0
            for i in range(len(starts)):
                j = max(j, i)
                while (j + 1 < i + len(starts)
                       and ext_starts[j + 1] - ext_starts[i] <= span):
                    j += 1
                cnt = int(j - i + 1)
                if cnt > worst:
                    worst = cnt
                    sel = [k % len(starts) for k in range(i, j + 1)]
                    worst_center = centers[sel].mean(axis=0)
    center_full = None
    if worst_center is not None:
        center_full = [int(round(float(v) / sc)) for v in worst_center]
    return done(worst_span_windows=int(worst),
                suspicious_windows=int(len(susp_starts)),
                evaluated_windows=int(evaluated),
                uncertain=bool(worst >= limit),
                worst_center_xy_fullres=center_full)


def reclaim_inlets(binary: np.ndarray,
                   orig: Image.Image) -> tuple[np.ndarray, dict]:
    """Atgūst audumu, ko kandidāta maska pazaudējusi līčos un ieleju
    kanālos gar robežu (PROGRESS §104-§108): ģeodēziska audzēšana no
    FG caur teksturētiem pikseļiem samazinātā mērogā ar divu līmeņu
    slieksni (aizvēršanas zonā vājais, ārpus tās stiprais + audums
    vismaz 2 virzienos pret ēnas maliņas noplūdi), tad silueta
    iekšpuses aizvēršana pilnā izšķirtspējā (ieleju dibenu
    mikrosegmenti) un kadra malas josla (audums iziet no kadra,
    sprauga <= reclaim_band_px). Drošības vāks: atgūtais kopā
    <= reclaim_max_frac no FG, citādi atgriež ieeju nemainītu.
    Parametri: config.toml [mask] reclaim_*.
    Atgriež (binary, info)."""
    from scipy import ndimage

    from paper_leak import lab_chunked, measure_paper_colour, texture_map

    t0 = time.perf_counter()
    C = CFG["mask"]
    info: dict = {"reclaimed_px": 0, "seconds": 0.0}
    m = binary > 0
    if not m.any():
        info["seconds"] = round(time.perf_counter() - t0, 3)
        return binary, info
    ds = int(C["reclaim_ds"])
    rgb = np.asarray(orig.convert("RGB"))
    lab = lab_chunked(rgb)
    Lds = cv2.resize(lab[..., 0], None, fx=1.0 / ds, fy=1.0 / ds,
                     interpolation=cv2.INTER_AREA)
    tex_s = texture_map(Lds, 5)
    fg = cv2.resize(m.astype(np.float32), (Lds.shape[1], Lds.shape[0]),
                    interpolation=cv2.INTER_AREA) > 0.5
    if int(fg.sum()) < 100:
        info["seconds"] = round(time.perf_counter() - t0, 3)
        return binary, info
    bg_lab, _ = ndimage.label(~fg)
    bords = (set(bg_lab[0].tolist()) | set(bg_lab[-1].tolist())
             | set(bg_lab[:, 0].tolist()) | set(bg_lab[:, -1].tolist()))
    bords.discard(0)
    outer = np.isin(bg_lab, list(bords)) if bords else np.zeros_like(fg)
    plab = np.array(measure_paper_colour(orig)["lab"], np.float32)
    lab_ds = cv2.resize(lab, (Lds.shape[1], Lds.shape[0]),
                        interpolation=cv2.INTER_AREA)
    E_ds = np.linalg.norm(lab_ds - plab, axis=2)
    bg_ref = outer & (E_ds < float(C["reclaim_bg_E"]))
    tex_bg = float(np.median(tex_s[bg_ref])) if int(bg_ref.sum()) >= 50 \
        else float(np.median(tex_s[outer]))
    core = ndimage.binary_erosion(fg, iterations=3)
    tex_fg = float(np.median(tex_s[core])) if core.any() \
        else float(np.median(tex_s[fg]))
    lo = max(float(C["reclaim_tex_bg_ratio"]) * tex_bg,
             tex_bg + float(C["reclaim_tex_bg_abs"]),
             float(C["reclaim_tex_lo_fg_ratio"]) * tex_fg,
             float(C["reclaim_tex_min"]))
    hi = max(float(C["reclaim_tex_hi_ratio"]) * tex_fg, lo)
    info.update(tex_bg=round(tex_bg, 2), tex_fg=round(tex_fg, 2),
                tex_lo=round(lo, 2), tex_hi=round(hi, 2))

    dist = ndimage.distance_transform_edt(~fg)
    r_close = int(C["reclaim_close_r_ds"])
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                    (2 * r_close + 1, 2 * r_close + 1))
    in_close = cv2.morphologyEx(fg.astype(np.uint8), cv2.MORPH_CLOSE,
                                ker) > 0
    D = int(C["reclaim_dir_dist_ds"])
    dirs = np.zeros(fg.shape, np.uint8)
    for ax, sgn in ((1, 1), (1, -1), (0, 1), (0, -1)):
        accd = np.zeros_like(fg)
        for k in range(1, D + 1):
            sh = np.roll(fg, sgn * k, axis=ax)
            sl = [slice(None), slice(None)]
            sl[ax] = slice(0, k) if sgn > 0 else slice(-k, None)
            sh[tuple(sl)] = False
            accd |= sh
        dirs += accd.astype(np.uint8)
    max_dist = int(C["reclaim_max_dist_ds"])
    growable = (dist <= max_dist) & (
        ((tex_s >= lo) & in_close) | ((tex_s >= hi) & (dirs >= 2)))
    cur = fg.copy()
    for _ in range(max_dist):
        nxt = ndimage.binary_dilation(cur, iterations=1) & (growable | fg)
        if (nxt == cur).all():
            break
        cur = nxt
    grown_ds = (cur & (~fg)) & (dirs >= 2)
    min_comp = int(C["reclaim_min_comp_ds"])
    cc, cn = ndimage.label(grown_ds)
    if cn:
        sizes = np.bincount(cc.ravel())
        strong = np.bincount(cc[tex_s >= hi].ravel(), minlength=cn + 1)
        ok_ids = [i for i in range(1, cn + 1)
                  if sizes[i] >= min_comp and strong[i] >= min_comp]
        grown_ds = np.isin(cc, ok_ids) if ok_ids else np.zeros_like(grown_ds)
    out = m.copy()
    ys, xs = np.where(~out)
    sel = grown_ds[ys // ds, xs // ds] & (tex_s[ys // ds, xs // ds] >= lo)
    out[ys[sel], xs[sel]] = True
    info["grown_px"] = int(sel.sum())

    r_sol = int(C["reclaim_solidify_r_px"])
    if r_sol > 0:
        ker_f = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                          (2 * r_sol + 1, 2 * r_sol + 1))
        closed = cv2.morphologyEx(out.astype(np.uint8), cv2.MORPH_CLOSE,
                                  ker_f) > 0
        info["solidified_px"] = int((closed & ~out).sum())
        out = closed

    band = int(C["reclaim_band_px"])
    if band > 0:
        dist_f = ndimage.distance_transform_edt(~out)
        # Josla darbojas tikai rindās/kolonnās, kur audums tajā malā
        # tiešām iziet no kadra (FG jau ir joslā) — citādi ds tekstūras
        # logs stūros pāršautu pāri apģērba stūrim uz papīra.
        bandmask = np.zeros_like(out)
        bandmask[:, -band:] |= out[:, -band:].any(axis=1)[:, None]
        bandmask[:, :band] |= out[:, :band].any(axis=1)[:, None]
        bandmask[-band:, :] |= out[-band:, :].any(axis=0)[None, :]
        bandmask[:band, :] |= out[:band, :].any(axis=0)[None, :]
        by, bx = np.where(~out & bandmask & (dist_f <= band))
        bsel = tex_s[by // ds, bx // ds] >= hi
        out[by[bsel], bx[bsel]] = True
        info["band_px"] = int(bsel.sum())

    reclaimed = int((out & ~m).sum())
    info["seconds"] = round(time.perf_counter() - t0, 3)
    if reclaimed > float(C["reclaim_max_frac"]) * float(m.sum()):
        info["refused"] = "atgūtais pārsniedz reclaim_max_frac"
        return binary, info
    info["reclaimed_px"] = reclaimed
    if reclaimed:
        return out.astype(np.uint8), info
    return binary, info


# --- lut_only: pilnkadra (makro) verifikācija (PROGRESS §131) -------------
# Kadrs, kurā audums aizpilda visu rāmi, nav ko maskēt: fona nav, ko
# aizvietot. Pirms šāda kadra pieņemšanas uz lut_only ceļa, skaitliski
# jāpierāda, ka papīra fons tiešām nav redzams. Papīru atrod esošais
# `paper_background_mask` (tekstūras-tolerants, no kadra malas
# sasniedzams); ja rīks atsakās ("kadrā nav papīram līdzīga fona"),
# papīra daļas ir 0. Sliekšņi dzīvo config.toml [lut_only] un tika
# fiksēti PIRMS mērījuma (pogu lēmums 2026-10-25).

def lut_only_verify(img: Image.Image) -> dict:
    """§131: papīra daļa katrā no 4 malu joslām (platums
    strip_width_pct no malas, min strip_min_px) < strip_paper_max UN
    globāli < global_paper_max. Atgriež daļas, iemeslu un pass."""
    from paper_leak import paper_background_mask

    _C = CFG["lut_only"]
    res = paper_background_mask(img)
    w, h = img.size
    kx = max(int(round(_C["strip_width_pct"] * w)), int(_C["strip_min_px"]))
    ky = max(int(round(_C["strip_width_pct"] * h)), int(_C["strip_min_px"]))
    if res.get("refused"):
        fr = {"top": 0.0, "bottom": 0.0, "left": 0.0, "right": 0.0}
        glob = 0.0
        why = f"paper_background_mask atteicās: {res.get('reason')}"
    else:
        bg = res["background"]
        fr = {
            "top": float(bg[:ky, :].mean()),
            "bottom": float(bg[-ky:, :].mean()),
            "left": float(bg[:, :kx].mean()),
            "right": float(bg[:, -kx:].mean()),
        }
        glob = float(bg.mean())
        why = ("papīra daļa: " +
               ", ".join(f"{k}={v:.4f}" for k, v in fr.items()) +
               f", globāli {glob:.4f}")
    lim = {"strip_paper_max": _C["strip_paper_max"],
           "global_paper_max": _C["global_paper_max"]}
    ok = (all(v < _C["strip_paper_max"] for v in fr.values())
          and glob < _C["global_paper_max"])
    return {
        "pass": bool(ok),
        "reason": why if ok else
                  f"STOP lut_only verifikācija: {why} (sliekšņi: katra mala "
                  f"< {lim['strip_paper_max']}, globāli < {lim['global_paper_max']})",
        "strip_fracs": {k: round(v, 5) for k, v in fr.items()},
        "global_frac": round(glob, 5),
        "strip_px": {"x": kx, "y": ky},
        "refused": bool(res.get("refused")),
        "paper_rgb": res.get("paper_rgb"),
        "limits": lim,
    }


def lut_only_sharpness(img: Image.Image) -> float:
    """Laplace dispersija uz centra kvadrāta. TIKAI informatīvi (§131):
    bez priekšmeta robežas defokuss nav pierādāms, tāpēc nav vārtu —
    gala QA ir lietotāja acs."""
    g = np.asarray(img.convert("L"), dtype=np.float32)
    h, w = g.shape
    s = min(h, w)
    y0, x0 = (h - s) // 2, (w - s) // 2
    c = g[y0:y0 + s, x0:x0 + s]
    return float(cv2.Laplacian(c, cv2.CV_32F).var())
