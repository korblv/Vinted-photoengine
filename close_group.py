#!/usr/bin/env python3
"""Aizver vienu bilžu grupu: dzēš tikai ŠĪS grupas attēlu failus (LOOP.md §8).

Noteikums (2026-10-21, atkārtoti atgādināts 2026-10-23):
  Darba telpā vienlaikus tur tikai vienu aktīvu produktu bilžu grupu. Kad
  lietotājs ar izvēles pogu apstiprina, ka `.zip` ir lejupielādēts, grupas
  attēlu failus — `uploads/` avotus, MASTER, PARAUGS, maskas, kolāžu un
  **`.zip`** — dzēš. Saglabā kodu, dokumentāciju, tekstuālo vēsturi un
  parauga atsauces. Bez lejupielādes apstiprinājuma grupu NEDZĒŠ.

Kāpēc skripts: 2026-10-23 šis solis tika aizmirsts — `.zip` palika darba
telpā. Skripts padara soli vienu komandu un izdrukā atbrīvotos baitus.

Lietošana:
  python3 close_group.py STEM [STEM ...]        # tikai parāda, ko dzēstu
  python3 close_group.py --yes STEM [STEM ...]  # dzēš
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
UPLOADS = ROOT.parent / "uploads"
COLLAGES = [OUT / "_KOMPLEKTS_vinted_henley.jpg", OUT / "V2_KOLAZA.jpg"]


def targets(stems: list[str]) -> list[Path]:
    out: list[Path] = []
    for s in stems:
        out += sorted((OUT / "paraugs").glob(f"{s}*"))
        out += sorted((OUT / "master").glob(f"{s}*"))
        out += sorted((OUT / "masks").glob(f"{s}*"))
        out += sorted((OUT / "profiles").glob(f"{s}*"))
        out += sorted(UPLOADS.glob(f"{s}*"))
    out += sorted(OUT.glob("*.zip"))
    out += [c for c in COLLAGES if c.is_file()]
    seen, uniq = set(), []
    for p in out:
        if p.is_file() and p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--yes"]
    do = "--yes" in sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    files = targets(args)
    total = sum(p.stat().st_size for p in files)
    for p in files:
        print(f"  {'DZĒŠU' if do else 'dzēstu'}  {p.relative_to(ROOT.parent)}  {p.stat().st_size/1e6:6.2f} MB")
    if do:
        for p in files:
            p.unlink()
        print(f"\nizdzēti {len(files)} faili, atbrīvoti {total/1e6:.2f} MB")
    else:
        print(f"\n(DEMO) {len(files)} faili, kopā {total/1e6:.2f} MB — palaid ar --yes, lai dzēstu")


if __name__ == "__main__":
    main()
