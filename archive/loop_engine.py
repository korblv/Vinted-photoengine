"""loop_engine.py — loop dzinējs: gate kritums -> diagnoze -> remēdija -> pārbaude -> eskalācija.

Kāpēc šis fails eksistē
-----------------------
Līdz šim loopu dzina cilvēks: palaid maker, palaid checker, apskati, izdomā
nākamo mēģinājumu, atkārto. Tas strādāja, bet tas nav atkārtojams: katrs
lēmums palika čatā, nevis kodā. Šis dzinējs to pārņem.

Kas paliek nemainīgs (loop engineering princips)
------------------------------------------------
AI IEROSINA, MĒRĪJUMS SPRIEŽ. Neviens remēdijs nevar "pieņemt" sevi:
katrs mēģinājums tiek pārbaudīts ar tiem pašiem gates, kas bāzes gadījumam.
Remēdija, kas uzlabo vienu skaitli un sabojā citu, tiek noraidīta.

Trīs drošības lietas
--------------------
1. Budžets: katram attēlam maks. MAX_ATTEMPTS_PER_IMAGE mēģinājumi, visam
   braucienam maks. MAX_WALL_S sekundes. Beidzoties budžetam -> eskalācija.
2. Priekšnosacījumi: remēdija tiek palaista tikai tad, ja tās priekšnosacījumi
   ir izpildīti PĒC MĒRĪJUMA, nevis pēc cerības.
3. Gala pārskrējiens vienmēr ir VIENS, ar vienu globālo LUT. Remēdiju
   eksperimenti ir atsevišķi braucieni tikai tāpēc, lai izlemtu parametrus;
   tie neietekmē gala krāsu.

Lietošana:
    python3 loop_engine.py                       # pilns komplekts no PLAN
    python3 loop_engine.py --files a.jpg b.jpg    # cits saraksts
    python3 loop_engine.py --budget-s 300         # īsāks budžets
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path("/home/user/loop_bildes")
OUT = ROOT / "output"
UPLOADS = Path("/home/user/uploads")

MAKER = ROOT / "workflow_v2.py"
CHECKER = ROOT / "checker_v2.py"

TRACE_PATH = OUT / "loop_trace.json"
ESCALATION_PATH = OUT / "LOOP_ESCALATIONS.md"
OVERRIDES_PATH = OUT / "loop_overrides.json"

MAX_ATTEMPTS_PER_IMAGE = 2
MAX_WALL_S = 600

PLAN = [
    "slamjam_mfpen_trousers.jpg",
    "slamjam_mfpen_trousers_2.jpg",
    "slamjam_mfpen_trousers_3.jpg",
    "slamjam_mfpen_trousers_4.jpg",
    "IMG_20261015_122248.jpg",
    "MVIMG_20261020_160550.jpg",
    "MVIMG_20261020_161944.jpg",
    "MVIMG_20261020_161146.jpg",
]

MASK_GATES = ("GATE_C_mask", "GATE_P_paper_at_border")

# Ko cilvēkam darīt ar konkrēto gate. Rakstīts tā, lai eskalācija būtu
# rīkojums, nevis žēlošanās.
NEXT_STEP = {
    "GATE_P_paper_at_border": ("papīrs maskā pie kadra malas. Remēdijas izsmeltas -> "
                               "vajadzīga cita maskas metode vai kadra pārstrāde"),
    "GATE_C_mask": ("maskas forma neatbilst audumam. Remēdijas izsmeltas -> "
                    "pārbaudīt oriģinālu un, ja nepieciešams, pārstrādāt kadru"),
    "NAV GATES (atteikts)": ("maska netika izveidota (sk. maker ierakstu). "
                             "Nepieciešams jauns kadrs vai cita metode"),
    "": "skatīt trace ierakstu",
}


def stem_of(name: str) -> str:
    return Path(name).stem


# Maker atgriež 0 = viss pabeigts, 2 = daļa attēlu apzināti atteikta (needs_review).
# Abi ir derīgas beigas. Tikai citi kodi nozīmē, ka rīks sabruka.
MAKER_OK_CODES = (0, 2)
# Čekeris atgriež 2, ja kāds attēls krīt — tā ir mērījuma ziņa, ne avārija.
CHECKER_OK_CODES = (0, 2)


ROTATE: list[str] = []
FRAMING: list[str] = [""]


def run_maker(files: list[str], overrides: dict | None = None) -> tuple[int, str]:
    cmd = [sys.executable, str(MAKER), "--files", *files, "--no-collage"]
    if ROTATE:
        cmd += ["--rotate", *ROTATE]
    if FRAMING[0]:
        cmd += ["--framing", FRAMING[0]]
    if overrides:
        OVERRIDES_PATH.write_text(json.dumps(overrides, indent=1), encoding="utf-8")
        cmd += ["--overrides", str(OVERRIDES_PATH)]
    t = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(f"    maker {len(files)}b -> {time.perf_counter() - t:.1f}s (exit {p.returncode})", flush=True)
    return p.returncode, p.stdout + p.stderr


def run_checker(stems: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, str(CHECKER), *stems]
    t = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(f"    checker {len(stems)}b -> {time.perf_counter() - t:.1f}s (exit {p.returncode})", flush=True)
    return p.returncode, p.stdout + p.stderr


def load_reports() -> tuple[dict, dict]:
    maker = json.loads((OUT / "report_v2_maker.json").read_text(encoding="utf-8"))
    check_p = OUT / "report_v2.json"
    if not check_p.is_file():
        # Maker atteica VISU bildi (nevis sabruka), tāpēc checkeris netika palaists
        # un atskaites nav. Tas nav dzinēja avārija: vienkārši nav neviena
        # attēla, par kuru būtu vērtējami vārti. Agrāk šeit bija traceback.
        print("    (checker atskaites nav — maker atteica; vārti nav vērtējami)",
              flush=True)
        return maker.get("images", {}), {}
    check = json.loads(check_p.read_text(encoding="utf-8"))
    return maker.get("images", {}), {k: v for k, v in check.items() if k != "_meta"}


def failing_gates(check_rec: dict) -> list[str]:
    """Kritušie gates. Uzmanību: ATTIEKTAM attēlam gate saraksts ir TUKŠS.

    Tāpēc "nav kritušu gate" NEDRĪKST tulkot kā "izturēja". Zema līmeņa funkcija
    atgriež tikai mērījumu; par PASS/FAIL lemj `passed()` zemāk.
    """
    return [g for g, v in check_rec.items() if isinstance(v, dict) and v.get("pass") is False]


def passed(check_rec: dict) -> bool:
    """Vienīgā patiesā atbilde uz "vai šis attēls ir piegādājams"."""
    return check_rec.get("ALL_PASS") is True


REASON_PRIORITY = (
    "apmales retry izlaists",     # viskonkrētāk: kāpēc remēdija nemaz nevarēja sākties
    "apmales retry noraidīts",    # remēdija sākās, bet aizsargi noraidīja
    "STOP:",
    "AI QA noraida",
    "remēdija",
)


def _extract_reason(log: str) -> str:
    """Izvelk KONKRĒTĀKO iemeslu, nevis pirmo atrasto.

    Pirmā versija paņēma pirmo rindu pēc kārtas un tāpēc 122248 gadījumā
    atdeva vispārīgo "remēdija: piespiedu...", nevis īsto cēloni — ka apmales
    ceļš nemaz nav pieejams, jo kadrā nav uzticama papīra fona.
    """
    lines = [ln.strip() for ln in log.splitlines() if ln.strip()]
    for key in REASON_PRIORITY:
        for ln in lines:
            if key in ln:
                return ln[:300]
    return ""


def _extract_detail(rec: dict) -> dict:
    """Cipari, kas pierāda kritisko gate — eskalācijai, nevis iespaidam."""
    out = {}
    p = rec.get("GATE_P_paper_at_border") or {}
    if p.get("pass") is False:
        out["GATE_P"] = {"regions": p.get("regions"), "px": p.get("px"),
                         "max_depth_px": p.get("max_depth_px")}
    c = rec.get("GATE_C_mask") or {}
    if c.get("pass") is False:
        out["GATE_C"] = {"coverage": c.get("coverage"),
                         "silhouette_fill": c.get("silhouette_fill"),
                         "largest_ratio": c.get("largest_ratio")}
    return out


@dataclass
class Remedy:
    """Viena remēdija: kad piemērojama, ko palaist, cik maksā."""

    name: str
    description: str
    overrides: dict
    estimated_s: float

    def applies(self, stem: str, maker_rec: dict, gates: list[str]) -> tuple[bool, str]:
        raise NotImplementedError

    def run(self, stem: str, files: list[str]) -> dict:
        """Palaiž maker + checker tikai šim attēlam; atgriež rezultātu."""
        code, log = run_maker([Path(f).name for f in files], {stem: self.overrides})
        if code not in MAKER_OK_CODES:
            return {"ok": False, "why": f"maker exit {code}", "log": log[-1500:]}
        code, log2 = run_checker([stem])
        if code not in CHECKER_OK_CODES:
            return {"ok": False, "why": f"checker exit {code}", "log": log2[-1500:]}
        maker_imgs, check = load_reports()
        rec = check.get(stem, {})
        gates = failing_gates(rec)
        return {
            "ok": passed(rec),
            "gates_after": gates,
            "method": maker_imgs.get(stem, {}).get("mask_method"),
            "reason": _extract_reason(log),
            "detail": _extract_detail(rec),
            "log": (log + log2)[-1500:],
        }


@dataclass
class ForcedPadRetry(Remedy):
    """Apmales retry arī tad, ja ISNet maska tika pieņemta.

    Kad lieto: maska iztur ISNet QA, bet krīt čekerī (piem. GATE_P — papīrs
    maskā pie kadra malas). Bāzes ceļš tur nepalīdzēs, jo tas ir tas pats ceļš,
    kas atdeva slikto masku. Apmale dod modelim citu kontekstu.
    Priekšnosacījums: kadrā jābūt uzticamam papīra fonam (paper_profile != None).
    """

    def applies(self, stem, maker_rec, gates):
        if not any(g in gates for g in MASK_GATES):
            return False, "nav maskas gate krituma"
        if (maker_rec or {}).get("mask_method") == "isnet_pad_retry":
            return False, "jau izmanto apmales retry"
        return True, "maska krīt čekerī -> mēģinām citu kontekstu"


@dataclass
class AltPadRetry(Remedy):
    """Tas pats, bet ar citu apmales izmēru, ja 0.90 jau izmēģināts.

    Priekšnosacījums: jābūt pierādītam, ka 0.90 pieņemts, bet gate tomēr krīt,
    vai arī 0.90 noraidīts. Mazāks pad = vairāk oriģināla = mazāk pārplūdes.
    """

    def applies(self, stem, maker_rec, gates):
        if not any(g in gates for g in MASK_GATES):
            return False, "nav maskas gate krituma"
        if (maker_rec or {}).get("mask_method") != "isnet_pad_retry":
            return False, "pamata remēdija vēl nav izmēģināta"
        return True, "apmale 0.90 bija, bet gate krīt -> mēģinām 0.85"


def write_escalation_page(trace: dict) -> int:
    """Vienīgā vieta, kur top eskalāciju lapa. Zvana gan brauciens, gan --rebuild."""
    esc = trace.get("escalations", [])
    lines = ["# Loop eskalācijas", "",
             f"Brauciens: {trace.get('started')} → {trace.get('finished')} "
             f"({trace.get('wall_s')} s, budžets {trace.get('budget_s')} s)", ""]
    if not esc:
        lines.append("Nav nevienas eskalācijas — visi attēli izturēja gates.")
    for row in esc:
        stem = row["stem"]
        gates = row.get("gates") or []
        item = trace["items"].get(stem, {})
        base = item.get("baseline", {})
        lines += [f"## {stem}", "",
                  f"- Bāze: {'PASS' if base.get('pass') else 'FAIL'} "
                  f"({base.get('method')}, segums {base.get('coverage')})",
                  f"- Kritušie gates: {', '.join(gates)}", "",
                  f"- Ko darīt: {NEXT_STEP.get(gates[0] if gates else '', NEXT_STEP[''])}", ""]
        if not item.get("attempts"):
            lines.append("- Remēdijas netika piemērotas: neviena priekšnosacījumi neizpildījās.")
        for a in item.get("attempts", []):
            if "stop" in a:
                lines.append(f"- STOP: {a['stop']}")
                continue
            lines.append(f"- `{a['remedy']}` → "
                         f"{'pieņemts' if a.get('ok') else 'noraidīts'} "
                         f"({a.get('gates_after') or '—'})")
            reason = a.get("reason") or _extract_reason(a.get("log_tail", ""))
            if reason:
                lines.append(f"  - rīks ziņo: {reason}")
            if a.get("detail"):
                lines.append(f"  - pierādījums: {json.dumps(a['detail'], ensure_ascii=False)}")
        lines.append("")
    ESCALATION_PATH.write_text("\n".join(lines), encoding="utf-8")
    return len(esc)


def rebuild_escalations() -> int:
    if not TRACE_PATH.exists():
        print("Nav loop_trace.json — nav no kā pārbūvēt", flush=True)
        return 2
    trace = json.loads(TRACE_PATH.read_text(encoding="utf-8"))
    n = write_escalation_page(trace)
    print(f"Pārbūvēts no trace: {n} eskalācijas -> {ESCALATION_PATH}", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*", default=None)
    ap.add_argument("--budget-s", type=float, default=MAX_WALL_S)
    ap.add_argument("--framing", choices=["auto", "slamjam", "original"], default="auto",
                    help="slamjam = produkta kadrs ar fona malām; original = kadrs kā "
                         "nofotografēts; auto = slamjam, ja siluets slēgts (noklusējums)")
    ap.add_argument("--rotate", nargs="*", default=[],
                    help="STEM:GRĀDI (tāpat kā workflow_v2 --rotate); dzinējs to nodod tālāk")
    ap.add_argument("--rebuild", action="store_true",
                    help="nepalaist neko; pārbūvēt LOOP_ESCALATIONS.md no loop_trace.json")
    args = ap.parse_args()
    files = args.files or PLAN
    ROTATE[:] = list(args.rotate or [])
    FRAMING[0] = args.framing
    if ROTATE:
        print(f"Rotācijas: {ROTATE}", flush=True)

    if args.rebuild:
        return rebuild_escalations()

    t_all = time.perf_counter()
    trace = {"plan": files, "started": time.strftime("%Y-%m-%d %H:%M:%S"),
             "budget_s": args.budget_s, "items": {}, "remedies": []}
    accepted_overrides: dict[str, dict] = {}

    print("== 1. Bāzes brauciens ==", flush=True)
    code, _ = run_maker(files)
    if code not in MAKER_OK_CODES:
        print("Maker sabruka — STOP", flush=True)
        return 2
    run_checker([stem_of(f) for f in files])
    maker_imgs, check = load_reports()

    for f in files:
        stem = stem_of(f)
        gates = failing_gates(check.get(stem, {}))
        trace["items"][stem] = {
            "baseline": {"pass": passed(check.get(stem, {})),
                         "failing_gates": gates,
                         "method": maker_imgs.get(stem, {}).get("mask_method"),
                         "coverage": maker_imgs.get(stem, {}).get("coverage")},
            "attempts": [],
            "final": None,
        }
        ok_base = passed(check.get(stem, {}))
        label = "PASS" if ok_base else ("FAIL " + ",".join(gates) if gates else "NAV GATES (atteikts)")
        print(f"  {stem:26s} {label}", flush=True)

    print("== 2. Remēdiju bibliotēka ==", flush=True)
    library = [
        ForcedPadRetry(
            name="pad_forced_090",
            description="apmales retry 0.90 arī pie pieņemtas bāzes maskas",
            overrides={"pad": 0.90, "force_pad_retry": True},
            estimated_s=12.0,
        ),
        AltPadRetry(
            name="pad_alt_085",
            description="apmales retry 0.85, ja 0.90 jau bija",
            overrides={"pad": 0.85, "force_pad_retry": True},
            estimated_s=12.0,
        ),
    ]

    for f in files:
        stem = stem_of(f)
        item = trace["items"][stem]
        if item["baseline"]["pass"]:
            continue

        attempts = 0
        tried: set[str] = set()
        current_gates = item["baseline"]["failing_gates"]
        maker_rec = maker_imgs.get(stem, {})

        while attempts < MAX_ATTEMPTS_PER_IMAGE:
            if time.perf_counter() - t_all > args.budget_s:
                item["attempts"].append({"stop": "budžets izsmelts"})
                print("    STOP: budžets izsmelts", flush=True)
                break
            applicable = []
            for r in library:
                if r.name in tried:
                    continue
                ok, why = r.applies(stem, maker_rec, current_gates)
                trace["remedies"].append(
                    {"stem": stem, "remedy": r.name, "applies": ok, "why": why})
                if ok:
                    applicable.append(r)
            if not applicable:
                print("    nav piemērojamu remēdiju -> eskalācija", flush=True)
                break
            r = applicable[0]
            print(f"    mēģinu {r.name}: {r.description}", flush=True)
            res = r.run(stem, [f])
            attempts += 1
            tried.add(r.name)
            item["attempts"].append({"remedy": r.name, "overrides": r.overrides,
                                     "ok": res["ok"], "gates_after": res.get("gates_after"),
                                     "method": res.get("method"), "reason": res.get("reason"),
                                     "detail": res.get("detail"),
                                     "log_tail": (res.get("log") or "")[-1200:]})
            if res["ok"]:
                accepted_overrides[stem] = dict(r.overrides)
                print(f"    {r.name}: PIEŅEMTS", flush=True)
                break
            print(f"    {r.name}: noraidīts ({res.get('gates_after') or res.get('why')})", flush=True)
            maker_imgs, check = load_reports()
            maker_rec = maker_imgs.get(stem, {})
            current_gates = failing_gates(check.get(stem, {}))

    print("== 3. Gala brauciens (viens globālais LUT) ==", flush=True)
    if accepted_overrides:
        OVERRIDES_PATH.write_text(json.dumps(accepted_overrides, indent=1), encoding="utf-8")
        code, _ = run_maker(files, accepted_overrides)
    else:
        code, _ = run_maker(files)
    if code not in MAKER_OK_CODES:
        print("Gala maker sabruka — STOP", flush=True)
        return 2
    run_checker([stem_of(f) for f in files])
    maker_imgs, check = load_reports()

    escaped = []
    for f in files:
        stem = stem_of(f)
        gates = failing_gates(check.get(stem, {}))
        item = trace["items"][stem]
        item["final"] = {"pass": passed(check.get(stem, {})),
                         "failing_gates": gates,
                         "method": maker_imgs.get(stem, {}).get("mask_method"),
                         "coverage": maker_imgs.get(stem, {}).get("coverage"),
                         "overrides": accepted_overrides.get(stem)}
        if not item["final"]["pass"]:
            escaped.append((stem, gates or ["NAV GATES (atteikts)"], item))

    trace["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    trace["wall_s"] = round(time.perf_counter() - t_all, 1)
    trace["accepted_overrides"] = accepted_overrides
    trace["escalations"] = [{"stem": s, "gates": g} for s, g, _ in escaped]
    TRACE_PATH.write_text(json.dumps(trace, indent=1, ensure_ascii=False), encoding="utf-8")

    # Eskalāciju lapa: cilvēkam lasāms pierādījumu saraksts.
    lines = ["# Loop eskalācijas", "",
             f"Brauciens: {trace['started']} → {trace['finished']} "
             f"({trace['wall_s']} s, budžets {args.budget_s} s)", ""]
    if not escaped:
        lines.append("Nav nevienas eskalācijas — visi attēli izturēja gates.")
    for stem, gates, item in escaped:
        lines += [f"## {stem}", "",
                  f"- Bāze: {'PASS' if item['baseline']['pass'] else 'FAIL'} "
                  f"({item['baseline']['method']}, segums {item['baseline']['coverage']})",
                  f"- Kritušie gates: {', '.join(gates)}", ""]
        lines.append(f"- Ko darīt: {NEXT_STEP.get(gates[0] if gates else '', NEXT_STEP[''])}")
        lines.append("")
        if not item["attempts"]:
            lines.append("- Remēdijas netika piemērotas: neviena priekšnosacījumi neizpildījās.")
        for a in item["attempts"]:
            if "stop" in a:
                lines.append(f"- STOP: {a['stop']}")
                continue
            lines.append(f"- `{a['remedy']}` → "
                         f"{'pieņemts' if a['ok'] else 'noraidīts'} "
                         f"({a['gates_after'] or '—'})")
            if a.get("reason"):
                lines.append(f"  - rīks ziņo: {a['reason']}")
            if a.get("detail"):
                lines.append(f"  - pierādījums: {json.dumps(a['detail'], ensure_ascii=False)}")
        lines.append("")
    ESCALATION_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nLOOP DONE: {len(files) - len(escaped)}/{len(files)} PASS, "
          f"{len(escaped)} eskalācijas; {trace['wall_s']} s", flush=True)
    print(f"  trace: {TRACE_PATH}\n  eskalācijas: {ESCALATION_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
