"""Masku provenance (sidecar vēsture, solis 3).

Izņemts no workflow_v2.py solī 6.2; funkciju ķermeņi nemainīti
(AST hash Pierādījums, PROGRESS §62).
"""
import json
from pathlib import Path

from engine.config import CFG  # noqa: E402
from engine.infra import atomic_write_json, sha256_file  # noqa: E402

MASK_PROVENANCE_VERSION = 1
DECONTAM_PARAMS = {"max_px": int(CFG["decontam"]["max_px"]),
                   "tex_ratio": float(CFG["decontam"]["tex_ratio"])}


def mask_provenance_path(mask_path) -> Path:
    return Path(str(mask_path).removesuffix(".png") + ".json")


def read_mask_provenance(mask_path) -> dict | None:
    p = mask_provenance_path(mask_path)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _write_mask_provenance(mask_path, prov: dict) -> dict:
    prov = dict(prov)
    prov["version"] = MASK_PROVENANCE_VERSION
    prov["mask_sha256"] = sha256_file(Path(mask_path))
    atomic_write_json(mask_provenance_path(mask_path), prov)
    return prov


def start_mask_provenance(mask_path, stem: str, source_sha256: str, method: str) -> dict:
    """Jauna maska = jauna izcelsmes ķēde (vecā vēsture vairs neattiecas)."""
    entry = {"stage": "mask", "params": {"method": str(method)},
             "input_mask_sha256": None,
             "output_mask_sha256": sha256_file(Path(mask_path))}
    return _write_mask_provenance(mask_path, {
        "stem": stem, "source_sha256": source_sha256,
        "history_known": True, "stages": [entry]})


def append_mask_stage(mask_path, stem: str, source_sha256: str, entry: dict) -> dict:
    """Pieliek posmu ķēdei. Ja esošā vēsture nesakrīt ar posma ieeju
    (masku starpposmā mainījis kāds cits), ķēde sākas no jauna un
    atzīmē, ka agrākā vēsture nav zināma."""
    entry = dict(entry)
    entry["output_mask_sha256"] = sha256_file(Path(mask_path))
    old = read_mask_provenance(mask_path)
    if old and old.get("mask_sha256") == entry.get("input_mask_sha256"):
        stages = list(old.get("stages", [])) + [entry]
        known = bool(old.get("history_known", True))
        src_sha = source_sha256 or old.get("source_sha256")
    else:
        stages = [entry]
        known = False
        src_sha = source_sha256 or (old or {}).get("source_sha256")
    return _write_mask_provenance(mask_path, {
        "stem": stem, "source_sha256": src_sha,
        "history_known": known, "stages": stages})


def decontam_needed(prov: dict | None, params: dict, current_mask_sha256: str) -> bool:
    """Tīrs lēmums: vai decontam ar šiem parametriem vēl jāizpilda.

    Nezināma vai novecojusi (hash nesakrīt) vēsture -> izpildīt
    (vēsturiskais noklusējums). Jau izpildīts ar tiem pašiem parametriem
    tieši šai maskai -> neizpildīt (posma idempotence)."""
    if not prov or prov.get("mask_sha256") != current_mask_sha256:
        return True
    for st in prov.get("stages", []):
        if st.get("stage") == "decontam" and st.get("params") == params:
            return False
    return True
