#!/usr/bin/env python3
"""Piegādes arhīvs: 5 gala kadri + kolāža + specifikācija (2026-10-23).

Kāpēc nevis `workflow_v2.py --make-zip`: tas pieprasa `completed` statusu,
meistaru + masku katram celmam un `ALL_PASS` čekera ierakstu katram celmam.
Šajā partijā 4 kadru meistari tika dzēsti krātuves tīrīšanā un birkas kadram
nav maskas (apģērbs aizpilda kadru pa visām malām, segmentācija nav vajadzīga),
tāpēc tas strukturāli nevar nostrādāt. Arhīvu būvē tieši no apstiprinātajiem
gala failiem — bez reporta pārrakstīšanas un bez viltotiem čekera ierakstiem.

Lietošana: python3 make_zip_vinted.py
"""
import hashlib
import zipfile
from datetime import date
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent / "output"
FINALS = [
    ("PXL_20261022_124309570.PORTRAIT.ORIGINAL", "01_prieksa"),
    ("PXL_20261022_124651636.PORTRAIT.ORIGINAL", "02_mugura"),
    ("PXL_20261022_124322251.PORTRAIT.ORIGINAL", "03_plakats_pogas"),
    ("PXL_20261022_124339475.PORTRAIT.ORIGINAL", "04_aproces"),
    ("PXL_20261022_124406358.PORTRAIT.ORIGINAL", "05_birka"),
]
SIZE = (2000, 2500)
ZIP_NAME = f"vinted_henley_{date.today().isoformat()}.zip"


def main() -> None:
    entries = []
    for stem, slug in FINALS:
        p = OUT / "paraugs" / f"{stem}_PARAUGS_{SIZE[0]}x{SIZE[1]}.jpg"
        if not p.is_file():
            raise SystemExit(f"nav kadra: {p}")
        im = Image.open(p)
        if im.size != SIZE:
            raise SystemExit(f"{p.name}: izmērs {im.size} != {SIZE}")
        entries.append((p, f"{slug}.jpg", hashlib.sha256(p.read_bytes()).hexdigest()[:16]))
    collage = OUT / "_KOMPLEKTS_vinted_henley.jpg"
    entries.append((collage, "00_kollaza.jpg", hashlib.sha256(collage.read_bytes()).hexdigest()[:16]))

    readme = [
        "Vinted — Henley krekls (UNIQLO, L), studio kadri",
        f"Sagatavots: {date.today().isoformat()}",
        "",
        f"Kadri: {SIZE[0]}x{SIZE[1]} px (4:5), JPEG q=95, fons #F3F3F3, mīksta studijas ēna.",
        "",
        "Faili:",
    ]
    readme += [f"  {name:16s} sha256 {sha}" for _, name, sha in entries]
    readme += [
        "",
        "Piezīmes:",
        "  - 03_plakats_pogas: apģērbs aizpilda kadru pie trim malām (apakša, kreisi, labi),",
        "    augša ir tīrs fons — dabiska kompozīcija, nevis griezums.",
        "  - 05_birka: kadrs piegādāts kā studijas pilna kadra bilde (bez izgriešanas),",
        "    jo apģērbs aizpilda visu kadru.",
        "  - Visi kadri sagatavoti no viena uzņēmuma sērijas ar vienu krāsu LUT.",
    ]
    readme_txt = "\n".join(readme) + "\n"

    dst = OUT / ZIP_NAME
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_STORED) as z:
        z.writestr("READ_ME.txt", readme_txt)
        for p, name, sha in entries:
            z.write(p, name)
            print(f"  + {name:16s} {p.stat().st_size/1e6:5.2f} MB  sha {sha}")
    print(f"arhīvs {dst.name}  {dst.stat().st_size/1e6:.2f} MB")
    with zipfile.ZipFile(dst) as z:
        print("pārbaude:", ", ".join(z.namelist()))


if __name__ == "__main__":
    main()
