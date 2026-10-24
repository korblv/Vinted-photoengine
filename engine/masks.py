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
    from scipy.ndimage import gaussian_filter
    base = gaussian_filter(L, 60)          # pusizmērā: lokālais L* līmenis
    bg_like = interior & (E7 < 0.55 * gi) & (np.abs(L - base) < 4.0)
    bg_inside = float(bg_like.sum() / max(int(interior.sum()), 1))

    hover = float(m.mean())
    qa = {
        "coverage": round(hover, 4),
        "inner_ratio": round(inner_ratio, 3),
        "outer_ratio": round(outer_ratio, 3),
        "bg_inside": round(bg_inside, 4),
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
