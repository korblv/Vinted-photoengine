"""Atskaites un piegāde: maker report, ZIP, palaišanas meta.

Izņemts no workflow_v2.py solī 6.5. Ķermeņi nemainīti, izņemot
_code_commit repo ceļu (parents[1], jo modulis dzīvo engine/).
"""
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

import numpy as np

from loop import OUT  # noqa: E402

from engine.config import WORKFLOW_VERSION, _config_sha256, _effective_config  # noqa: E402
from engine.infra import atomic_write_json, sha256_file  # noqa: E402

PROFILE_PATH = Path(OUT) / "grade_profile_v2.json"
REPORT_PATH = Path(OUT) / "report_v2_maker.json"
CHECKER_REPORT_PATH = Path(OUT) / "report_v2.json"
DELIVERY_REPORT_PATH = Path(OUT) / "delivery_v2.json"
COLLAGE_PATH = Path(OUT) / "V2_KOLAZA.jpg"


_RUN_META: dict = {}


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


def _code_commit() -> str:
    """Git HEAD šim repozitorijam; '-dirty', ja ir neiekomitētas izmaiņas.
    Bez repozitorija/git: 'unknown' (nekad nekrīt dēļ atskaites lauka)."""
    try:
        here = Path(__file__).resolve().parents[1]
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
