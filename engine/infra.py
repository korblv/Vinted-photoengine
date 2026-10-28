"""Infrastruktūra: rotācijas, attēlu I/O, atomiskie raksti, vide.

Izņemts no workflow_v2.py solī 6.2; funkciju ķermeņi nemainīti
(AST hash Pierādījums, PROGRESS §62).
"""
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from loop import SRC_DIR  # noqa: E402

from engine.config import WORKFLOW_VERSION  # noqa: E402

# Bezzaudējumu ceturtdaļas pagriezieni (grādi pulksteņrādītāja virzienā),
# ko drīkst piemērot, lai šķērsām nofotografēts apģērbs gala bildē stāvētu
# dabiskā vertikālā orientācijā. Tas nav brīva leņķa "iztaisnojums":
# PIL transpose tikai pārkārto tos pašus pikseļus, vērtības nemainās.
ROTATIONS_CW: dict[str, int] = {}
_QUARTER_TURNS_CW = {
    0: None,
    90: Image.ROTATE_270,   # PIL ROTATE_270 = 270° pret pulksteni = 90° CW
    180: Image.ROTATE_180,
    270: Image.ROTATE_90,   # PIL ROTATE_90 = 90° pret pulksteni = 270° CW
}
_ROTATION_ALIASES = {"cw": 90, "right": 90, "ccw": 270, "left": 270}


def fit_size(width: int, height: int, max_w: int = 768, max_h: int = 1024) -> tuple[int, int]:
    """Samazina izmēru, saglabājot malu attiecību (nekad nepalielina)."""
    if width <= 0 or height <= 0:
        raise ValueError("Nederīgs attēla izmērs")
    scale = min(max_w / width, max_h / height, 1.0)
    return max(1, int(round(width * scale))), max(1, int(round(height * scale)))


def normalize_rotation(value: str | int) -> int:
    if isinstance(value, str):
        v = value.strip().lower()
        if v in _ROTATION_ALIASES:
            return _ROTATION_ALIASES[v]
        value = int(v)
    deg = int(value) % 360
    if deg not in _QUARTER_TURNS_CW:
        raise ValueError(f"Atļauti tikai 0/90/180/270 grādu pagriezieni, saņemts: {value}")
    return deg


def parse_rotations(items) -> dict[str, int]:
    """Parsē `--rotate` ierakstus formā `STEM:270`, `STEM:ccw` u.tml."""
    out: dict[str, int] = {}
    for item in items or []:
        for part in str(item).split(","):
            part = part.strip()
            if not part:
                continue
            key, sep, val = part.rpartition(":")
            if not sep:
                raise ValueError(f"Nederīgs --rotate ieraksts (vajag STEM:GRĀDI): {part}")
            # NB: ne visi foto vārdi beidzas ar vienu paplašinājumu. Pixel
            # kameras dod `...PORTRAIT.ORIGINAL.jpg`, un `splitext` noņem TIKAI
            # `.jpg`, atstājot `...PORTRAIT.ORIGINAL`. Bet `Path.stem` noņem visu
            # pēc PĒDĒJĀ punkta tikai vienu reizi — tāpēc abas puses jāsaskaņo:
            # atslēga ir pilnais vārds bez galīgā paplašinājuma.
            key = Path(key.strip()).name
            if key.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp")):
                key = key[: -len(Path(key).suffix)]
            out[key] = normalize_rotation(val)
    return out


def rotation_for(path: str | Path) -> int:
    stem = Path(path).stem
    if stem in ROTATIONS_CW:
        return ROTATIONS_CW[stem]
    return ROTATIONS_CW.get(stem[-6:], 0)


def validate_rotations_against_files(rot_map: dict[str, int], files: list[str]) -> list[str]:
    """Atrod `--rotate` atslēgas, kas neatbilst nevienam no izvēlētajiem failiem
    (pilns `stem` vai pēdējie 6 simboli, kā `rotation_for`).

    Novērš kluso drukas kļūdu režīmu (PROGRESS §67): neesošs kods vairs
    nepaliek nepamanīts ar 0° rotāciju.
    """
    stems = [Path(f).stem for f in files]
    return [
        k for k in (rot_map or {})
        if not any(k == s or k == s[-6:] for s in stems)
    ]


def apply_quarter_turn(img: Image.Image, degrees_cw: int) -> Image.Image:
    deg = normalize_rotation(degrees_cw)
    op = _QUARTER_TURNS_CW[deg]
    return img if op is None else img.transpose(op)


def open_rgb(path: str | Path) -> Image.Image:
    """Atver attēlu, piemēro EXIF orientāciju un, ja šim failam noteikts,
    bezzaudējumu 90° soļu pagriezienu dabiskā vertikālā orientācijā.

    NB: rotāciju ņem no GLOBĀLĀ `ROTATIONS_CW`, kas ir tikai būvēšanas laika
    sānkanāls (to piepilda `--rotate`). Ja strādā no saglabāta ieraksta, lieto
    `open_rgb_recorded` — citādi `rec["rotation_cw"]` tiek ignorēts."""
    with Image.open(path) as im:
        img = ImageOps.exif_transpose(im).convert("RGB")
    return apply_quarter_turn(img, rotation_for(path))


def open_rgb_recorded(path: str | Path, rotation_cw) -> Image.Image:
    """Atver attēlu ar IERAKSTĪTO rotāciju, nevis globālo `ROTATIONS_CW`.

    Kāpēc tas ir atsevišķi: `--rerender-saved` un jebkurš ceļš, kas strādā no
    `report_v2_maker.json`, nesaņem `--rotate` — tāpēc globālais ir tukšs un
    `open_rgb` atgriež NEPAGRIEZTO attēlu, kamēr saglabātā maska ir pagrieztā
    izmērā. Rezultāts bija `ValueError: Maskas izmērs (4080, 3072) nesakrīt ar
    (4080, 3072)` (abi skaitļi vienādi, jo (H,W) pret (W,H)) — un sliktākajā
    gadījumā klusa segmentācija nepareizā orientācijā.

    `None` = ierakstā nav -> atkāpjamies uz globālo uzvedību.
    """
    with Image.open(path) as im:
        img = ImageOps.exif_transpose(im).convert("RGB")
    rot = rotation_for(path) if rotation_cw is None else normalize_rotation(rotation_cw)
    return apply_quarter_turn(img, rot)


def probe_source_image(path: str | Path) -> tuple[bool, str]:
    """Vai avota failu var atvērt kā attēlu. Atgriež (ok, cilvēkam lasāms iemesls).

    Kāpēc pirms darba: bez šīs pārbaudes tukšs vai bojāts JPEG aizgāja līdz
    ISNet APAKŠPROCESAM, un tā traceback (12+ rindas) tika ielīmēts
    `report_v2_maker.json` `error` laukā. Partija nekrīt, bet ziņojums kļūst
    nelasāms un īstais iemesls ("fails ir tukšs") pazūd.

    Pārbauda pirms jebkā cita: eksistenci, izmēru, atvēršanu un pilnu nolasīšanu.
    """
    p = Path(path)
    if not p.is_file():
        return False, "fails neeksistē"
    try:
        size = p.stat().st_size
    except OSError as exc:
        return False, f"failu nevar nolasīt: {exc}"
    if size == 0:
        return False, "fails ir tukšs (0 baiti)"
    try:
        with Image.open(p) as im:
            w, h = ImageOps.exif_transpose(im).size
        # `exif_transpose` nelasa pikseļus; `verify()` nolasa visu failu, tāpēc
        # tas noķer arī nogrieztu JPEG ("Truncated File Read").
        with Image.open(p) as im2:
            im2.verify()
    except Image.UnidentifiedImageError:
        return False, "nav atpazīstams attēla formāts (bojāts fails vai nav bilde)"
    except OSError as exc:
        return False, f"attēls bojāts: {exc}"
    except Exception as exc:                     # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"
    if w < 64 or h < 64:
        return False, f"attēls pārāk mazs ({w}x{h})"
    return True, ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def atomic_write_json(path: Path, obj) -> None:
    atomic_write_text(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def save_image_atomic(img: Image.Image, path: Path, **kwargs) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.stem + ".", suffix=path.suffix)
    os.close(fd)
    try:
        img.save(tmp_name, **kwargs)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def save_gray_png(arr: np.ndarray, path: Path, level: int = 3) -> None:
    # Ražošanas režīmā `optimize=False`: PIL optimizācija augstfrekvences
    # auduma PNG maksāja līdz ~12 s, bet ietaupīja tikai ~10% vietas.
    save_image_atomic(
        Image.fromarray(arr.astype(np.uint8)), path, optimize=False, compress_level=level
    )


def workspace_bytes(root: str = "/home/user/loop_bildes") -> int:
    total = 0
    for base, _, names in os.walk(root):
        for name in names:
            try:
                total += os.path.getsize(os.path.join(base, name))
            except OSError:
                pass
    return total


def environment_problems() -> list[str]:
    """Ātra pārbaude pirms batch darba, lai viena trūkstoša pakotne
    neizraisītu neveiksmi katrai bildei atsevišķi."""
    problems = []
    if os.path.isdir("/var/tmp/pylibs") and "/var/tmp/pylibs" not in sys.path:
        sys.path.insert(0, "/var/tmp/pylibs")
    for name in ["cv2", "numpy", "PIL", "scipy", "onnxruntime", "rembg"]:
        if importlib.util.find_spec(name) is None:
            problems.append(f"nav Python pakotnes: {name}")
    home = Path(os.environ.get("U2NET_HOME", "/var/tmp/rembg_home"))
    model = home / "models" / "isnet-general-use" / "isnet-general-use.onnx"
    if not model.is_file() or model.stat().st_size <= 100_000_000:
        problems.append(f"nav derīga ISNet modeļa: {model}")
    return problems


def preflight(files: list[str]) -> dict:
    sources = []
    total = 0
    for name in files:
        p = Path(SRC_DIR) / name
        size = p.stat().st_size if p.is_file() else 0
        total += size
        item = {"name": name, "exists": p.is_file(), "bytes": size}
        if p.is_file():
            try:
                with Image.open(p) as im:
                    w, h = ImageOps.exif_transpose(im).size
                rot = rotation_for(p)
                item["size"] = [h, w] if rot in (90, 270) else [w, h]
                item["rotation_cw"] = rot
            except Exception as exc:  # noqa: BLE001
                item["error"] = f"{type(exc).__name__}: {exc}"
        sources.append(item)
    problems = environment_problems()
    if not files:
        problems.append("nav izvēlētu avota bilžu")
    bad_rot = validate_rotations_against_files(ROTATIONS_CW, files)
    if bad_rot:
        problems.append(f"--rotate atslēga neatbilst nevienam failam: {bad_rot}")
    disk = shutil.disk_usage("/var/tmp")
    return {
        "ready": not problems and all(s["exists"] and "error" not in s for s in sources),
        "workflow_version": WORKFLOW_VERSION,
        "problems": problems,
        "sources": sources,
        "source_total_bytes": total,
        "workspace_bytes": workspace_bytes("/home/user"),
        "loop_bildes_bytes": workspace_bytes("/home/user/loop_bildes"),
        "var_tmp_free_bytes": int(disk.free),
        "setup_command": "python3 /home/user/loop_bildes/setup_v2.py",
    }
