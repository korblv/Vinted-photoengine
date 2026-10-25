"""Konfigurācijas ielāde un palīgfunkcijas (engine pakotne).

Izņemts no workflow_v2.py produkcijas refaktora solī 6.1; funkciju
ķermeņi nav mainīti (pierāda AST hash salīdzinājums, PROGRESS §61).
"""
import hashlib
import json
import tomllib
from pathlib import Path

WORKFLOW_VERSION = "2.10"

# ---------------------------------------------------------------------------
# Konfigurācija (solis 4): parametri dzīvo config.toml, specifikācija —
# kodā. Sk. config.toml galveni un PROGRESS §59. Ielāde ir stingra:
# nezināma atslēga, trūkstoša sekcija vai nepareizs tips = kļūda.
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.toml"  # engine/ -> repo sakne
_CONFIG_SCHEMA: dict[str, dict[str, type]] = {
    "run": {"closeup_proc_w": int, "png_level": int, "framing": str,
            "wb_mode": str, "auto_closeup": bool, "auto_grabcut_iters": int},
    "mask": {"silhouette_fill_min": float, "pad_retry": float,
             "pad_overflow_limit": float, "pad_uncovered_limit": float,
             "pad_tex_relaxed": float, "ai_qa_coverage_min": float,
             "ai_qa_coverage_max": float, "ai_qa_largest_min": float,
             "ai_qa_bbox_area_min": float, "ai_qa_bbox_w_min": float,
             "ai_qa_bbox_h_min": float, "hole_min_px": int,
             "hole_margin_de": float, "hole_tex_ratio": float,
             "hole_tex_abs": float, "hole_border_px": int,
             "hole_max_cut_px": int, "hole_max_fill_frac": float,
             "hole_tex_scale": int, "hole_tex_fg_ratio": float,
             "hole_tex_bg_ratio": float, "hole_tex_min": float,
             "hole_L_slack": float, "hole_tex_fg_ratio_max": float,
             "hole_bg_E": float, "q_scale": float, "q_close_r_ds": int,
             "q_tex_bg_ratio": float, "q_tex_bg_abs": float,
             "q_tex_fg_ratio": float, "q_trigger_pct": float,
             "reclaim_ds": int, "reclaim_max_dist_ds": int,
             "reclaim_tex_bg_ratio": float, "reclaim_tex_bg_abs": float,
             "reclaim_tex_lo_fg_ratio": float, "reclaim_tex_min": float,
             "reclaim_tex_hi_ratio": float, "reclaim_close_r_ds": int,
             "reclaim_dir_dist_ds": int, "reclaim_min_comp_ds": int,
             "reclaim_solidify_r_px": int, "reclaim_band_px": int,
             "reclaim_bg_E": float, "reclaim_max_frac": float},
    "plate": {"inner_min": float, "outer_max": float, "bg_inside_max": float,
              "cover_min": float, "cover_max": float},
    "chroma": {"scale": int, "palette_k": int, "fg_alpha": float,
               "fg_core_alpha": float, "fg_core_dist_px": float,
               "border_alpha_max": float, "seed_margin_dE": float,
               "bg_refine_dE": float, "margin_sigma": float,
               "min_cross_dE": float, "seed_margin_ratio_min": float,
               "max_ambiguous_fraction": float, "dark_L": float,
               "dark_palette_k": int, "dark_min_cross_dE": float,
               "dark_uncertain_field": float, "dark_tex_ratio": float,
               "dark_seed_min_frac": float, "dark_carve_max_frac": float},
    "decontam": {"max_px": int, "tex_ratio": float},
    "grade": {"curve_blend": float, "highlight_knee": float,
              "exposure_target": float, "exposure_min": float,
              "exposure_max": float, "exposure_step": float,
              "exposure_max_adjustments": int, "wb_chroma_max": float,
              "wb_shrink": float, "gain_clip_min": float,
              "gain_clip_max": float, "clipping_limit_pct": float,
              "sharpen_radius": float, "sharpen_percent": int,
              "sharpen_threshold": int},
}
_CONFIG_CHOICES = {("run", "framing"): ("auto", "slamjam", "original"),
                   ("run", "wb_mode"): ("auto", "identity")}


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Nolasa config.toml un validē pret shēmu. Nekādu klusu noklusējumu:
    ja failā kaut kas nav kārtībā, kļūda pasaka precīzi, kas un kur."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Trūkst konfigurācijas faila: {path}")
    with path.open("rb") as f:
        raw = tomllib.load(f)
    if raw.get("config_version") != 1:
        raise ValueError(f"config_version jābūt 1, ir {raw.get('config_version')!r}")
    unknown = set(raw) - {"config_version", *_CONFIG_SCHEMA}
    if unknown:
        raise ValueError(f"Nepazīstamas config sekcijas: {sorted(unknown)}")
    cfg: dict = {"config_version": 1}
    for section, fields in _CONFIG_SCHEMA.items():
        if section not in raw:
            raise ValueError(f"config trūkst sekcijas [{section}]")
        got = raw[section]
        extra = set(got) - set(fields)
        missing = set(fields) - set(got)
        if extra:
            raise ValueError(f"[{section}] nepazīstamas atslēgas: {sorted(extra)}")
        if missing:
            raise ValueError(f"[{section}] trūkst atslēgu: {sorted(missing)}")
        out: dict = {}
        for key, typ in fields.items():
            v = got[key]
            if typ is float and isinstance(v, int) and not isinstance(v, bool):
                v = float(v)  # TOML `2` float laukā ir pieņemams
            if not isinstance(v, typ) or (typ is int and isinstance(v, bool)):
                raise ValueError(f"[{section}].{key}: gaidīts {typ.__name__}, "
                                 f"saņemts {type(v).__name__}")
            choices = _CONFIG_CHOICES.get((section, key))
            if choices is not None and v not in choices:
                raise ValueError(f"[{section}].{key}: {v!r} nav {choices}")
            out[key] = v
        cfg[section] = out
    return cfg


CFG = load_config()


def _resolve_args(args, cfg: dict | None = None):
    """CLI parametru noklusējumi (None) -> vērtības no config [run].
    Eksplicīti padoti karogi vienmēr uzvar (CLI > config)."""
    run = (cfg or CFG)["run"]
    if args.closeup_proc_w is None:
        args.closeup_proc_w = int(run["closeup_proc_w"])
    if args.png_level is None:
        args.png_level = int(run["png_level"])
    if args.framing is None:
        args.framing = str(run["framing"])
    if args.wb_mode is None:
        args.wb_mode = str(run["wb_mode"])
    if args.auto_closeup is None:
        args.auto_closeup = bool(run["auto_closeup"])
    if args.auto_grabcut_iters is None:
        args.auto_grabcut_iters = int(run["auto_grabcut_iters"])
    return args


def _effective_config(args, cfg: dict | None = None) -> dict:
    """Efektīvā konfigurācija šai palaišanai: config + CLI pārraksti."""
    eff = json.loads(json.dumps(cfg or CFG))
    eff["run"].update({
        "closeup_proc_w": args.closeup_proc_w,
        "png_level": args.png_level,
        "framing": args.framing,
        "wb_mode": args.wb_mode,
        "auto_closeup": bool(args.auto_closeup),
        "auto_grabcut_iters": args.auto_grabcut_iters,
    })
    return eff


def _config_sha256(eff: dict) -> str:
    return hashlib.sha256(
        json.dumps(eff, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
