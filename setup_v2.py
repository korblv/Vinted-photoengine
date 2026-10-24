#!/usr/bin/env python3
"""Workflow v2 vides pārbaude un reproducējama sagatavošana.

Arena sandbox faili ārpus /home/user var nepastāvēt nākamajā sesijā.
Tāpēc smagās Python pakotnes un ISNet modeli turam /var/tmp, bet šo
skriptu un versiju piespraudes — darba telpā. `--check` neko neinstalē.
Bez `--check` trūkstošās pakotnes/modeli tiek sagatavoti.
"""
import argparse
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PYLIBS = Path("/var/tmp/pylibs")
REMBG_HOME = Path("/var/tmp/rembg_home")
MODEL_PATH = REMBG_HOME / "models" / "isnet-general-use" / "isnet-general-use.onnx"
PINS = {
    "rembg": "2.0.85",
    "onnxruntime": "1.31.0",
    # Piespraužam arī skaitlisko steku, lai rembg atkarību izšķirtspēja
    # klusām neievieš citu NumPy/SciPy/Pillow versiju nekā validētā vide.
    "numpy": "2.3.5",
    "scipy": "1.17.1",
    "Pillow": "12.3.0",
}


def _prepare_path() -> None:
    if PYLIBS.is_dir() and str(PYLIBS) not in sys.path:
        sys.path.insert(0, str(PYLIBS))


def _module_status(name: str) -> dict:
    _prepare_path()
    try:
        mod = importlib.import_module(name)
        return {"ok": True, "version": str(getattr(mod, "__version__", "?"))}
    except Exception as exc:  # noqa: BLE001 - diagnostika jāredz pilnā apjomā
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def check() -> dict:
    modules = {name: _module_status(name) for name in ["cv2", "numpy", "PIL", "scipy", "onnxruntime", "rembg"]}
    disk = shutil.disk_usage("/var/tmp")
    model_ok = MODEL_PATH.is_file() and MODEL_PATH.stat().st_size > 100_000_000
    ready = all(v["ok"] for v in modules.values()) and model_ok
    return {
        "ready": bool(ready),
        "python": sys.version.split()[0],
        "pylibs": str(PYLIBS),
        "rembg_home": str(REMBG_HOME),
        "modules": modules,
        "isnet_model": {
            "path": str(MODEL_PATH),
            "exists": MODEL_PATH.is_file(),
            "bytes": MODEL_PATH.stat().st_size if MODEL_PATH.is_file() else 0,
            "ok": bool(model_ok),
        },
        "var_tmp_free_bytes": int(disk.free),
        "pins": PINS,
    }


def install_packages() -> None:
    PYLIBS.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-cache-dir",
        "--target",
        str(PYLIBS),
        "--upgrade",
        f"rembg=={PINS['rembg']}",
        f"onnxruntime=={PINS['onnxruntime']}",
        f"numpy=={PINS['numpy']}",
        f"scipy=={PINS['scipy']}",
        f"Pillow=={PINS['Pillow']}",
    ]
    print("Instalēju piespraustās pakotnes uz /var/tmp/pylibs ...", flush=True)
    subprocess.run(cmd, check=True)


def download_model() -> None:
    _prepare_path()
    os.environ.setdefault("U2NET_HOME", str(REMBG_HOME))
    from rembg import new_session

    print("Lejupielādēju/pārbaudu isnet-general-use modeli ...", flush=True)
    # Sesijas izveide rembg pusē lejupielādē modeli, ja tā vēl nav.
    _ = new_session("isnet-general-use")
    if not MODEL_PATH.is_file():
        raise RuntimeError(f"Modelis pēc lejupielādes nav atrasts: {MODEL_PATH}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="tikai pārbaude, neko neinstalēt")
    ap.add_argument("--force", action="store_true", help="instalēt pakotnes arī tad, ja pārbaude ir OK")
    args = ap.parse_args()

    before = check()
    if args.check:
        print(json.dumps(before, indent=2, ensure_ascii=False))
        return 0 if before["ready"] else 2

    if args.force or not (before["modules"]["onnxruntime"]["ok"] and before["modules"]["rembg"]["ok"]):
        install_packages()
    if args.force or not before["isnet_model"]["ok"]:
        download_model()
    after = check()
    print(json.dumps(after, indent=2, ensure_ascii=False))
    return 0 if after["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
