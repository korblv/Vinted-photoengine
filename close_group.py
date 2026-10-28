#!/usr/bin/env python3
"""Aizver vienu bilžu grupu: dzēš tikai ŠĪS grupas attēlu failus (LOOP.md §8).

Noteikums (2026-10-21, atkārtoti atgādināts 2026-10-23):
  Darba telpā vienlaikus tur tikai vienu aktīvu produktu bilžu grupu. Kad
  lietotājs ar izvēles pogu apstiprina, ka `.zip` ir lejupielādēts, grupas
  attēlu failus — `uploads/` avotus, MASTER, PARAUGS, maskas, kolāžu un
  **`.zip`** — dzēš. Saglabā kodu, dokumentāciju, tekstuālo vēsturi un
  parauga atsauces. Bez lejupielādes apstiprinājuma grupu NEDZĒŠ.

Atbalsta gan pilnus `stem` vārdus (`IMG_20261025_145704`), gan 6+ simbolu
kodus (`145704`), un attīra slēgtos ierakstus no `output/report_v2*.json`
(vai dzēš grupas JSON atskaites, ja slēgta visa grupa).

Lietošana:
  python3 close_group.py STEM [STEM ...]        # tikai parāda, ko dzēstu
  python3 close_group.py --yes STEM [STEM ...]  # dzēš
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
UPLOADS = ROOT.parent / "uploads"
COLLAGES = [OUT / "_KOMPLEKTS_vinted_henley.jpg", OUT / "V2_KOLAZA.jpg"]
GROUP_REPORTS = [
    OUT / "report_v2_maker.json",
    OUT / "report_v2.json",
    OUT / "delivery_v2.json",
    OUT / "grade_profile_v2.json",
]


def _matches_token(stem: str, token: str) -> bool:
    if stem == token or stem.startswith(token):
        return True
    return len(token) >= 6 and (stem.endswith(token) or token in stem)


def _known_report_stems() -> set[str]:
    known: set[str] = set()
    mp = OUT / "report_v2_maker.json"
    if mp.is_file():
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
            known.update((data.get("images") or {}).keys())
        except Exception:
            pass
    rp = OUT / "report_v2.json"
    if rp.is_file():
        try:
            data = json.loads(rp.read_text(encoding="utf-8"))
            known.update(k for k in data if not k.startswith("_"))
        except Exception:
            pass
    return known


def matched_report_stems(tokens: list[str]) -> tuple[set[str], set[str]]:
    known = _known_report_stems()
    matched = {s for s in known if any(_matches_token(s, t) for t in tokens)}
    return matched, known


def targets(stems: list[str]) -> list[Path]:
    out: list[Path] = []
    dirs = [OUT / "paraugs", OUT / "master", OUT / "masks",
            OUT / "profiles", OUT / "audits", UPLOADS]
    ses_root = ROOT / "sesijas_atskanoshana"
    for s in stems:
        pat = f"*{s}*" if len(s) >= 6 else f"{s}*"
        for d in dirs:
            if d.is_dir():
                out += sorted(d.glob(pat))
        if ses_root.is_dir():
            for sub in sorted(ses_root.glob(pat)):
                if sub.is_dir():
                    out += sorted(f for f in sub.rglob("*") if f.is_file())
                elif sub.is_file():
                    out.append(sub)
    out += sorted(OUT.glob("*.zip"))
    out += [c for c in COLLAGES if c.is_file()]
    matched, known = matched_report_stems(stems)
    if known and matched == known:
        out += [r for r in GROUP_REPORTS if r.is_file()]
    seen, uniq = set(), []
    for p in out:
        if p.is_file() and p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def _prune_partial_reports(closed_stems: set[str]) -> None:
    if not closed_stems:
        return
    mp = OUT / "report_v2_maker.json"
    if mp.is_file():
        try:
            data = json.loads(mp.read_text(encoding="utf-8"))
            imgs = data.get("images") or {}
            for s in closed_stems:
                imgs.pop(s, None)
            data["images"] = imgs
            mp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        except Exception:
            pass
    rp = OUT / "report_v2.json"
    if rp.is_file():
        try:
            data = json.loads(rp.read_text(encoding="utf-8"))
            for s in closed_stems:
                data.pop(s, None)
            meta = data.get("_meta")
            if isinstance(meta, dict) and isinstance(meta.get("checked"), list):
                meta["checked"] = [s for s in meta["checked"] if s not in closed_stems]
            rp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        except Exception:
            pass


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--yes"]
    do = "--yes" in sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    files = targets(args)
    matched, known = matched_report_stems(args)
    partial = bool(matched and matched != known)
    total = sum(p.stat().st_size for p in files)
    for p in files:
        try:
            rel = p.relative_to(ROOT.parent)
        except ValueError:
            rel = p
        print(f"  {'DZĒŠU' if do else 'dzēstu'}  {rel}  {p.stat().st_size/1e6:6.2f} MB")
    if partial:
        print(f"  {'ATJAUNINĀŠU' if do else 'atjauninātu'}  atskaišu ierakstus (-{len(matched)} kadri)")
    if do:
        for p in files:
            p.unlink()
        if partial:
            _prune_partial_reports(matched)
        print(f"\nizdzēti {len(files)} faili, atbrīvoti {total/1e6:.2f} MB")
    else:
        print(f"\n(DEMO) {len(files)} faili, kopā {total/1e6:.2f} MB — palaid ar --yes, lai dzēstu")


if __name__ == "__main__":
    main()
