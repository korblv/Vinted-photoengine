# Kā atjaunot sesiju no GitHub repo (jaunam aģentam)

**Kad lietot:** jaunā Arena Agent Mode sesijā, kas startēta ar piesaistītu
GitHub repo (darba telpā IR repo, bet NAV `/home/user/uploads` un
`output/`), vai pēc smilškastes zaudēšanas.

**Pirms visam:** izlasi `HANDOFF/00_SAKU_SHEIT.md` (visa projekta atmiņa,
~10 min). Šis fails atjauno tikai FAILUS, nevis zināšanas.

## 0. Rezekervs: NEIZMANTOT atjaunot.py

Repo saknē ir `atjaunot.py` un `HANDOFF/atjaunot.py` — tie ir §47 laika
atjaunošanas mehānismi, kas kodus atjauno no nesējiem `01_DZINEJS.md` /
`02_ATMINA.md` (atrodas tikai lietotāja vecajās augšupielādēs, versija
2026-10-24). Tie ir **novecojuši** — to palaišana pārrakstītu pašreizējo
kodu ar ~95 sesiju vecu versiju. GitHub repo tagad ir patiess avots.

## 1. Aktīvās grupas (145704) atjaunošana

Mapē `sesijas_atskanoshana/145704/` ir pilns grupas stāvoklis. No repo
saknes:

```bash
mkdir -p /home/user/uploads output/masks output/paraugs output/master
cp sesijas_atskanoshana/145704/IMG_20261025_145704.jpg /home/user/uploads/
cp sesijas_atskanoshana/145704/IMG_20261025_145704_MASK.png  output/masks/
cp sesijas_atskanoshana/145704/IMG_20261025_145704_MASK.json output/masks/
cp sesijas_atskanoshana/145704/report_v2_maker.json output/
cp sesijas_atskanoshana/145704/report_v2.json       output/
```

Neiekopētie faili (MASTER, ALPHA, PARAUGS_MASK, PARAUGS, profils) ir
pārrenderējami: `python3 workflow_v2.py --attempt 2 --rerender-saved
--files IMG_20261025_145704.jpg` (6.2 sadaļa HANDOFF).

## 2. Vide

Jaunā smilškastē `/var/tmp` ir tukšs — vienmēr vispirms:

```bash
cd <repo_sakne> && python3 setup_v2.py   # ~1 min; /var/tmp/pylibs + rembg_home
python3 -m pytest test_workflow_v2.py -q  # jābūt 135 passed
```

## 3. Grupas 145704 stāvoklis un nākamais solis (PROGRESS §141)

- Attempt 2 pabeigts: maska = **ISNet, pieņemta ar lietotāja pogu**
  (provenance "isnet" + `manual_adopt` ieraksts maker atskaitē);
  kompozīcija slamjam; checkeris **0/1 — krīt TIKAI GATE_C**
  (silhouette_fill 0,313 < 0,55; pārējie 11 vārti zaļi).
- Konteksts: apģērbs gaiši pelēks uz gaiši pelēkas TEKSTURĒTAS virsmas
  ar tumšām ēnām — plate ceļš satvēra visu (attempt 1 bija ALL-PASS,
  bet lietotājs SS ar sarkanajiem marķieriem norādīja virsmas ēnu
  plankumus; diagnoze PROGRESS §141).
- **Gaida lietotāja atbildi:** vai attempt 2 bilde izskatās pareizi?
  - JĀ → GATE_C grīdas pierādījuma izņēmums (0 caurumi + 0% zaudēta
    auduma + tīra robeža = nav "izēsta" maska) — RAŽOŠNES IZMAIŅA,
    AR POGU + vienības tests, pirms koda rakstīšanas.
  - NĒ → godīgais secinājums: pārfotografēt uz kontrastējoša fona
    (identiskas krāsas virsma = akls gadījums; sk. pasmacibas/
    PETIJUMS_EENAS_UN_MASKAS.md foto profilakse).
- Kolāža atsauksmei: `sesijas_atskanoshana/145704/V2_KOLAZA.jpg`.

## 4. Pēc grupas noslēguma

Piegāde tikai ar pogām (HANDOFF §3.4): apstiprinājums → `--make-zip` →
pēc "Lejupielādēju" grupas dzēšana (§3.5) — un sesijas stāvokļa mapes
`sesijas_atskanoshana/145704/` aizvākšana arī (komits).

## 5. Ko repo NESATUR

- Lietotāja foto augšupielādes (24 slamjam paraugi u.c.) — ja vajag
  pārkalibrēt, lietotājs tās augšupielādē no jauna; kalibrācijas
  REZULTĀTI ir dokumentos (WORKFLOW_V2.md, P_REZULTATI).
- `output/` saturu (gitignored) — izņemot šo atjaunošanas mapi.
