#!/usr/bin/env python3
"""Vinted komplekta kolāža — 5 kadri vienā joslā (reproducējams).

Izkārtojums atbilst apstiprinātajai kolāžai (2026-10-23):
balts audekls 1528x414, rāmja atkāpes PAD_X=16, PAD_TOP=22, PAD_BOT=32,
flīzes 288x360, starpa GAP=14, JPEG q=95, subsampling=0.

Lietošana: python3 make_collage_vinted.py [izvades_fails]
Kārtība: priekša -> mugura -> plakāts -> aproces -> birka.
"""
import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent / "output"
TILE = (288, 360)
GAP = 14
PAD_X, PAD_TOP, PAD_BOT = 16, 22, 32
BG = (255, 255, 255)

FRAMES = [  # (fails, paraksts piezīmēm)
    ("PXL_20261022_124309570.PORTRAIT.ORIGINAL", "priekša"),
    ("PXL_20261022_124651636.PORTRAIT.ORIGINAL", "mugura"),
    ("PXL_20261022_124322251.PORTRAIT.ORIGINAL", "plakāts"),
    ("PXL_20261022_124339475.PORTRAIT.ORIGINAL", "aproces"),
    ("PXL_20261022_124406358.PORTRAIT.ORIGINAL", "birka"),
]


def build(dst: Path) -> tuple[int, int]:
    n = len(FRAMES)
    w = PAD_X * 2 + n * TILE[0] + (n - 1) * GAP
    h = PAD_TOP + TILE[1] + PAD_BOT
    canvas = Image.new("RGB", (w, h), BG)
    for i, (stem, name) in enumerate(FRAMES):
        p = OUT / "paraugs" / f"{stem}_PARAUGS_2000x2500.jpg"
        if not p.is_file():
            raise SystemExit(f"nav kadra: {p}")
        tile = Image.open(p).convert("RGB").resize(TILE, Image.LANCZOS)
        x = PAD_X + i * (TILE[0] + GAP)
        canvas.paste(tile, (x, PAD_TOP))
        print(f"  {name:9s} {stem[:22]:24s} -> x={x}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dst, quality=95, subsampling=0)
    return canvas.size


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "_KOMPLEKTS_vinted_henley.jpg"
    size = build(out)
    print(f"kolāža {out} {size[0]}x{size[1]} {out.stat().st_size/1024:.0f} KB")
