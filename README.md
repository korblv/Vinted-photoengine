# Vinted bilžu dzinējs — telefona foto → profesionāli kadri

Privāts fotogrāfiju apstrādes projekts: telefona uzņemts apģērbs uz
papīra → tīri Vinted kadri 2000×2500, fons `#F3F3F3`, profesionāla
divkomponentu ēna, godīga krāsu pārvaldība (bez krāsošanas). Valoda:
latviešu. *(Private photo pipeline repo — docs in Latvian.)*

## Ieejas punkti (jaunam aģentam vai man pašam)

1. **`HANDOFF/00_SAKU_SHEIT.md`** — visa projekta atmiņa vienā failā.
   Izlasi pilnīgi pirms jebkādas darbības (~10 min).
2. **`LOOP_KOMANDAS.md`** — operatīvā komandu rokasgrāmata.
3. **`PROGRESS.md`** — hronoloģiskā vēsture (§numuri = darba sesiju
   ieraksti; jaunākie apakšā; §131 un jaunākie ir aktuālie likumi).
4. **`sesijas_atskanoshana/ATJAUNOT_SESIJU.md`** — ja sesija sākas no
   šī repo (GitHub piesaiste), tur ir aktīvās grupas stāvokļa
   atjaunošana un gaidāmie lēmumi.

## Struktūra

| Celš | Saturs |
|---|---|
| `engine/` | ražošanas dzinējs (maskas, krāsas, ēnas, renderis) |
| `workflow_v2.py`, `checker_v2.py` | ražotne + neatkarīgais vārtu tiesnesis (12 GATE) |
| `test_workflow_v2.py` | 135 vienību testi (zaļi = dzinis vesels) |
| `setup_v2.py` | vides atjaunošana jaunā smilškastē (`/var/tmp/pylibs`) |
| `config.toml` | visi QA sliekšņi (maskas, papīrs, piegāde) |
| `HANDOFF/`, `pasmacibas/` | atmiņas dokumenti + pētījumi (ēnas/maskas, licences) |
| `*_AUDITS.md`, `GALA_PARSKATS.md`, `WORKFLOW_V2.md` | padziļinātā dokumentācija |
| `sesijas_atskanoshana/` | aktīvās grupas stāvoklis GitHub pārnesumam |

## Ātra starts (jaunā sesijā / lokāli)

```bash
python3 setup_v2.py            # vides atjaunošana (~1 min)
python3 -m pytest test_workflow_v2.py -q   # 135 passed = vesels
python3 workflow_v2.py --attempt 1 --files A.jpg[,B.jpg]   # grupa
python3 checker_v2.py          # vārtu spriedums
```

Dzelzs likumi (pilnībā HANDOFF §3): apģērba pikseļi = oriģināls;
pogas apstiprinājumiem; ražošnes izmaiņām poga PIRMS koda; godīgums
par katru defektu; viena grupa vienlaikus.

## Brīdinājums

`atjaunot.py` un nesēji `01_DZINEJS.md`/`02_ATMINA.md` (tikai lietotāja
vecajās augšupielādēs) ir novecojushas §47 laika atjaunošanas kopijas —
**NEPALAIŽT** (pārrakstītu pašreizējo kodu). Repo pati ir avots.
