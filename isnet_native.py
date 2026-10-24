"""ISNet tieši uz onnxruntime — bez `rembg` čaulas.

Kāpēc: `from rembg import new_session, remove` maksā **2.3-2.4 s** katrā
apakšprocesā, kamēr `import onnxruntime` maksā 0.15 s. Pats modelis un tā
matemātika ir maza; pārējais ir rembg atkarību (pooch, click, ...) imports.

Šī funkcija atkārto `rembg` ceļu **dilstoši** (rembg 2.0.85):

    bg.remove(img, only_mask=True)
      -> ImageOps.exif_transpose(img)          # mūsu PIL bildēm EXIF nav
      -> DisSession.predict(img)               # isnet-general-use
           normalize(img, mean=(.5,.5,.5), std=(1,1,1), size=(1024,1024))
           inner_session.run(...)
           min-max normalizācija -> uint8 -> resize atpakaļ uz img.size

Normalizācijas matemātika ir nokopēta 1:1, ieskaitot `float64` starprezultātu
un dalījumu ar attēla maksimumu, tāpēc ievades tensors ir bitu identisks un
maska arī. To pārbauda `test_isnet_parity.py` pret īsto rembg.

Nekas šeit nemaina lēmumus: tā ir tā pati maska, tikai pa īsāku ceļu.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image
from PIL.Image import Image as PILImage

MODEL_NAME = "isnet-general-use"
INPUT_SIZE = (1024, 1024)
MEAN = (0.5, 0.5, 0.5)
STD = (1.0, 1.0, 1.0)


def model_path() -> Path:
    """Atrod jau lejupielādēto ONNX failu (to pašu, ko izmanto rembg)."""
    home = os.environ.get("U2NET_HOME") or os.path.expanduser("~/.rembg")
    candidates = [
        Path(home) / "models" / MODEL_NAME / f"{MODEL_NAME}.onnx",
        Path(home) / f"{MODEL_NAME}.onnx",          # vecais plakanais izkārtojums
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(
        f"{MODEL_NAME}.onnx nav atrasts ({', '.join(str(c) for c in candidates)}); "
        "palaid setup_v2.py vai uzstādi U2NET_HOME"
    )


def make_session(cpu_mem_arena: bool = False) -> ort.InferenceSession:
    """Sesija ar izslēgtu atmiņas arēnu.

    Arēnа ir tas, kāpēc pēc pirmās inferences process uzkrāja 1215 MB un otra
    inference krita ar SIGKILL. Bez tās tas ir ~611 MB, un maska ir bitu
    identiska (maks. atšķirība 0), tāpēc tas nav kvalitātes kompromiss.
    """
    so = ort.SessionOptions()
    so.enable_cpu_mem_arena = cpu_mem_arena
    so.enable_mem_pattern = cpu_mem_arena
    return ort.InferenceSession(
        str(model_path()), sess_options=so, providers=["CPUExecutionProvider"]
    )


def _normalize(img: PILImage) -> np.ndarray:
    """rembg `BaseSession.normalize` 1:1, tikai bez rembg importa."""
    im = img.convert("RGB").resize(INPUT_SIZE, Image.Resampling.LANCZOS)
    im_ary = np.array(im)
    im_ary = im_ary / max(np.max(im_ary), 1e-6)

    tmp = np.zeros((im_ary.shape[0], im_ary.shape[1], 3))
    tmp[:, :, 0] = (im_ary[:, :, 0] - MEAN[0]) / STD[0]
    tmp[:, :, 1] = (im_ary[:, :, 1] - MEAN[1]) / STD[1]
    tmp[:, :, 2] = (im_ary[:, :, 2] - MEAN[2]) / STD[2]
    tmp = tmp.transpose((2, 0, 1))
    return np.expand_dims(tmp, 0).astype(np.float32)


def predict_mask(session: ort.InferenceSession, img: PILImage) -> PILImage:
    """Atgriež L režīma masku `img.size` izmērā — tāpat kā rembg `only_mask`."""
    name = session.get_inputs()[0].name
    ort_outs = session.run(None, {name: _normalize(img)})

    pred = ort_outs[0][:, 0, :, :]
    ma = np.max(pred)
    mi = np.min(pred)
    pred = (pred - mi) / (ma - mi)
    pred = np.squeeze(pred)

    mask = Image.fromarray((pred * 255).astype("uint8"), mode="L")
    return mask.resize(img.size, Image.Resampling.LANCZOS)
