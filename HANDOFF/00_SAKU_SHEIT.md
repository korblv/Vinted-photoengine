# SAKU ŠEIT — Vinted bilžu dzinējs

**Dokumenta versija:** 2026-10-24 (pēc §65 — produkcijas refaktors pabeigts;
ēnas modelis `studio_v1_contact_pcss`, kods pakotnē `engine/`, versijas git)
**Kam:** jaunam aģentam, kurš atver sarunu no nulles un nezina neko par projektu.
**Kas šis ir:** visa projekta atmiņa vienā failā. Izlasi to pilnībā (~10 min) un
vari turpināt darbu tā, it kā būtu strādājis pie tā nedēļu.

---

## 0. Trīs teikumi, kas jāsaprot pirms visa cita

1. **Mēs nepārveidojam apģērbu.** Mēs ņemam lietotāja telefona foto uz papīra un
   izgriežam apģērbu, nomainot tikai fonu uz plakanu `#F3F3F3` un pievienojot ēnu.
   Apģērba pikseļi paliek oriģinālie — bez ģeneratīvas pār-zīmēšanas, bez
   deformācijas, bez "izdomātām" detaļām.
2. **Katrs lēmums ir izmērīts, nevis gaumīgs.** Ja kaut ko maini, to pierādi ar
   skaitli (Δ līmeņi, px, sha256). Lietotājs ķer neprecizitātes un nepieņem
   "izskatās labāk".
3. **Galavārds ir lietotājam.** Tu piedāvā, mēri un parādi; viņš apstiprina ar pogām.
   Nekad nepasludini kaut ko par gatavu bez viņa apstiprinājuma.

---

## 1. Projekts vienā rindkopā

Lietotājs pārdod lietotas drēbes (Vinted). Viņš fotografē apģērbu, izklātu uz balta
papīra, ar telefonu. Mēs no šiem foto izgatavojam tīrus e-komercijas kadrus, kas
izskatās kā profesionāla studija: 2000×2500 px, vienmērīgs `#F3F3F3` fons,
apģērbs centrēts, mīksta metēnā ēna, asas malas bez oreola. Atsauce jeb "paraugs"
ir `slamjam_mfpen_trousers*.jpg` (Slam Jam veikala foto).

---

## 2. Ko darīt pirmajās 60 sekundēs jaunā sarunā

1. Pajautā lietotājam, ko viņš grib: **jauns komplekts**, **turpināt iepriekšējo**,
   vai **labot kādu konkrētu bildi**.
2. Kods un dokumenti dzīvo darba telpas git repozitorijā (`loop_bildes/`) —
   parasti nekas nav jāatjauno. `.md` pakotnes `uploads/` ir **sasalusi
   v2.1 kopija no laika pirms produkcijas refaktora**: tās nedrīkst
   atjaunot pāri pašreizējam kodam (sk. 14. sadaļu). Pirms darba pārbaudi
   `git -C /home/user/loop_bildes log --oneline | head` un
   `python3 -m unittest test_workflow_v2` (64 testi, ~2 s).
3. **Neuzsāc jaunu grupu**, pirms neesi uzdevis starta jautājumu ar pogām (3.1).
4. Pirms jebkādas apstrādes pārbaudi vidi: `python3 setup_v2.py --check`.

---

## 3. Dzelzs noteikumi (pārkāpt nedrīkst NEKAD)

### 3.1 Starta protokols — viena grupa vienlaikus
Pēc **katras** jaunu produktu bilžu augšupielādes, pirms jebkādas apstrādes:
1. tikai inventarizē bildes un izmēri krātuvi (`du -sh`);
2. ar **izvēles pogām** jautā: **"Vai šīs ir visas šīs grupas bildes?"**
   - `Jā, šīs ir visas — sāc darbu`
   - `Nē, vēl pievienošu`
3. ja `Nē` → apstājies un gaidi; pēc nākamās augšupielādes jautā atkārtoti;
4. tikai pēc `Jā` fiksē pilno sarakstu `PROGRESS.md` un sāc darbu.

Darba telpā vienlaikus ir **tikai viena aktīva grupa**.

### 3.2 Apģērba pikseļi = oriģināls
- Aizliegta jebkāda ģeneratīva pār-zīmēšana uz apģērba (arī `generate_image`).
- Nedrīkst mainīt tekstūru, krāsu, krokas, birkas, pogas, defektus.
- Nedrīkst "izdomāt" neredzamas daļas (piem., mugurpusi, ja nav nobildēta).
- Drīkst mainīt **tikai**: fonu, ēnu uz fona, audekla izmēru, kadrējumu.
- Vienīgais atļautais pagrieziens: visa kadra bezzaudējumu 90° (`transpose`),
  lai šķērsām nofotografēts apģērbs stāvētu vertikāli. Nekāda brīva leņķa
  iztaisnošana, nekāda perspektīvas korekcija.
- Atļauta **viena globāla** Lightroom tipa krāsu korekcija visam komplektam
  (baltais balanss, ekspozīcija, maigs kontrasts) — tā nemaina formu.

### 3.3 Divi izvades faili katrai bildei
"Tieši 2000×2500" un "100% oriģinālie pikseļi" vienā failā nesanāk (mērogošana
pār-interpolē). Tāpēc:
- `output/master/*_MASTER_1to1.png` — 1:1 oriģinālmērogā un pozīcijā, PNG
  bezzudumu, apģērba kodols pikselis-pret-pikseli identisks avotam.
- `output/paraugs/*_PARAUGS_2000x2500.jpg` — veikalam gatavais kadrs (JPG q95).

### 3.4 Piegādes protokols — tikai ar pogām
1. Izveido **kolāžu** ar visām grupas gala bildēm un parādi to (`present_file`).
2. Pogas: `Apstiprināt` / `Noraidīt`.
3. Tikai pēc `Apstiprināt` veido `.zip` (un tikai ja checker saka PASS).
4. Kad lietotājs lejupielādējis — pogas: `Lejupielādēju — dzēst grupu` /
   `Vēl nedzēst`. Dzēš grupu tikai pēc pirmās.
5. Brīvs teksts vajadzīgs tikai tad, ja viņš noraida un apraksta, kas jālabo.

### 3.5 Krātuves higiēna
- Pirms un pēc katras iterācijas mēri `du -sh /home/user` un `loop_bildes`.
- Mērķis: darba telpa **zem 100 MB**.
- Glabā pastāvīgi: aktuālos MASTER/PARAUGS, maskas, `report*.json`, kodu, dokumentus.
- Dzēš uzreiz pēc apstiprināšanas: A/B arhīvus, diagnostikas attēlus, `__pycache__`.
- `uploads/` oriģinālus bez lietotāja lēmuma **nedzēš**.

### 3.6 Godīgums pret lietotāju
- Ja kaut kas nav pierādīts — saki "nav pierādīts", nevis "izskatās labi".
- Ja esi kļūdījies, ieraksti to dokumentā (projekta vēsturē tādi ieraksti ir;
  tie ir vērtīgi, ne apkaunojoši).
- Nekad nepaaugstini vārtu slieksni, lai "izietu". Nekad neklusām neizlaiž
  defektu.

---

## 4. Kā lietotājs strādā ar tevi

- Raksta **latviski**, īsi, bieži vien vienā teikumā ("ēna pārāk gara",
  "samazini rādiusu"). Atbildi latviski, bez liekvārdības.
- Viņš **vērtē pēc acs, bet pārbauda pēc skaitļiem** — ja saki "uzlaboju", viņš
  prasīs mērījumu. Vienmēr nāc ar skaitli.
- Apstiprinājumus vienmēr prasi ar **izvēles pogām**, nevis liekot rakstīt.
- Viņam patīk, ja tu pasaki, kas tieši mainījās un **kas palika nemainīgs**.
- Viņš nepieņem atrunas. Ja nevar — saki kāpēc, ar pierādījumu.

Biežākās komandas:

| Viņš raksta | Tu dari |
|---|---|
| `Jauns komplekts` | Inventarizē, jautā ar pogām par pilnīgumu, tad sāc |
| `Turpini loopu` | Turpini no `PROGRESS.md` stāvokļa |
| `Parādi statusu` | Posms, gatavās bildes, vārti, krātuve, vai gaidu lēmumu |
| `Veic pilnu auditu` | `checker_v2.py` + vizuālā masku/malu pārbaude |
| `Pārrenderē no saglabātajām maskām` | `workflow_v2.py --rerender-saved` |
| `Izlabo: <kas>` | Jauna iterācija tikai par šo problēmu, tad audits un kolāža |
| `Notīri krātuvi` | `du -sh`, dzēš pagaidu failus, aktīvo grupu nedzēš |
| `Apturi darbu` | Apstājies un ieraksti precīzu stāvokli `PROGRESS.md` |

---

## 5. Pieņemšanas kritēriji (vārti)

Bilde ir "gatava" tikai tad, ja **visi** piemērojamie vārti iziet. Sliekšņi ir
atvasināti no mērījumiem, neizdomāti — tos nepazemina.

| Vārts | Prasība |
|---|---|
| **A / A2** | MASTER kodolā (erodēts ~5 px) apģērba pikseļi == avots (v2: deterministiski koriģētais oriģināls) |
| **B** | Fons ārpus apģērba un ēnas zonas == `(243,243,243)` |
| **C** | Maska vesela: segums 15–98 % kadra, lielākā komponente ≥ 95 % maskas |
| **D** | `PARAUGS` precīzi 2000×2500; stūri (kur nav apģērba) 243 ± 3 |
| **E** | Vizuāli: nav oreola, nav nogrieztu piedurkņu, nav palikušu priekšmetu, ēna kā paraugā |
| **F** | Tuvplānos audums sasniedz kadra malu vismaz 3 no 4 malās (full-bleed, bez joslām) |
| **G** | Fona atlieku audits: maskas iekšienē nav redzama vecā papīra vai uz tā mestās ēnas pleķa; pieļaujama tikai ≤ 2 px antialias pāreja |
| **H** | Malas alfa: 5 px kodolā alfa = 255, > 5 px ārpusē = 0, daļēji caurspīdīgie ≤ 5,1 px no robežas |
| **T** | Laiks mērķa zonā (~20 s/bilde) |

---

## 6. Dzinēja arhitektūra

### 6.1 Faili

| Fails | Loma |
|---|---|
| `workflow_v2.py` | **CLI ieeja un fasāde** (741 r.): argumenti, `main` orķestrācija, vārdu re-eksports no `engine/` |
| `engine/` | Ražošanas loģika: `config.py` (ielāde+validācija), `infra.py` (rotācijas, I/O, preflight), `provenance.py` (masku sidecar vēsture), `masks.py` (ISNet, QA, pad/plate/closeup), `grade.py` (LUT/profils), `render.py` (MASTER/PARAUGS, kolāža), `report.py` (atskaite, ZIP) |
| `config.toml` | Visi parametri (39 vērtības; stingra validācija; CLI > config). Vārti/specifikācija apzināti paliek kodā |
| `checker_v2.py` | Neatkarīga pārbaude (vārti A2/B/C/D/F/H/T + R). **Neimportē maker moduļus**; lokāls LUT/pagrieziens, spec konstantes |
| `test_workflow_v2.py` | 64 vienību/regresijas/golden testi (`python3 -m unittest`, ~2 s) |
| `setup_v2.py` | Atjauno vidi pēc sandbox atiestatīšanas (rembg 2.0.85, onnxruntime 1.31.0, ISNet uz `/var/tmp`); modelis piesprausts ar sha256 |
| `isnet_native.py` | ISNet worker atsevišķā procesā (novērš ONNX atmiņas uzkrāšanos) |
| `loop.py` | Koplietojamās deterministiskās funkcijas: ēnas modelis `studio_shadow_bg` (8. sadaļa), `refine_alpha`, `decontaminate_rim`, `render_paraugs`, masku tīrīšana |
| `plate_segment.py`, `paper_leak.py` | Papīra/fona segmentācija un noplūdes QA |
| `closeup.py` | Tuvplānu apstrāde (GrabCut, sēklas) |
| `close_group.py` | Grupas slēgšana pēc lejupielādes (`--yes` lai tiešām dzēstu) |
| `rebuild_master.py` | MASTER pārbūve no saglabātajām maskām |
| `measure_shadow.py` | Ēnas diagnostika (uzmanību: tā "kodola Δ" siluetē ieskaita arī tumšu ēnu — kalibrācijai neder, sk. 8.4) |
| `archive/` | Sasalusi vēsture: vecie ēnu modeļi (`cast_shadow` S2 u.c.), v1 dzinējs, vecais checker. Ražošanā netiek importēti |

### 6.2 Pamatkomandas

```bash
cd /home/user/loop_bildes

python3 setup_v2.py --check                    # vai vide ir vietā
python3 setup_v2.py                            # atjauno vidi (tikai ja vajag)

python3 workflow_v2.py --preflight --files A.jpg,B.jpg
python3 workflow_v2.py --attempt 1 --files A.jpg,B.jpg
python3 workflow_v2.py --attempt 1 --resume --files A.jpg,B.jpg        # atsāk
python3 workflow_v2.py --attempt 2 --rerender-saved --files A.jpg,B.jpg # tikai renderis

python3 checker_v2.py                          # neatkarīgā pārbaude
python3 measure_shadow.py BILDE [...]          # ēnas skaitļi

# ZIP tikai pēc pogas "Apstiprināt" un checker PASS:
python3 workflow_v2.py --make-zip --zip-name GALA_BILDES.zip

python3 close_group.py STEM --yes              # dzēst grupu PĒC lejupielādes pogas
python3 -m unittest test_workflow_v2           # 64 testi, ~2 s (pirms katras koda maiņas)
git log --oneline | head                       # versiju vēsture (repozitorijs loop_bildes/)
```

### 6.3 Plūsma

```
augšupielāde → poga "Vai šīs ir visas bildes?"
  → inventārs + du -sh + preflight
  → ISNet maska → automātiska QA
       └ ja QA noraida → GrabCut ar pārbaudītām sēklām
  → viens LUT krāsu profils visam komplektam
  → renderis: MASTER_1to1 (PNG) + PARAUGS_2000x2500 (JPG q95) + ēna
  → checker_v2 A2/B/C/D/F/H/T + vizuālais zoom audits
  → kolāža → poga "Apstiprināt / Noraidīt"
  → .zip → poga "Lejupielādēju — dzēst grupu"
  → nākamā grupa
```

### 6.4 Orientācijas noteikums
Ja bilde atnāk "uz sāniem" (jostasvieta pie kadra sāna), pirms apstrādes visu
kadru pagriež bezzaudējumu 90° tā, lai apģērba dabiskā "augša" (apkakle,
jostasvieta, lasāmas birkas) būtu augšā. Ieraksti `PROGRESS.md` un palaid ar
`--rotate STEM:270` (pieņem arī `:cw` / `:ccw`). Pagrieziens ir pikseļu
pārkārtojums, nevis transformācija.

---

## 7. Pašreizējais stāvoklis (2026-10-24)

- **Aktīva produktu grupa: nav.** Pēdējā piegādātā un slēgtā grupa —
  Vans bikses (4 kadri, Attempt 3, checker 4/4 PASS, ZIP lejupielādēts,
  faili izdzēsti; visas gala hash vērtības `PROGRESS.md` §48–§53).
  Darba telpa gatava vienai jaunai grupai pēc 3.1 protokola.
- **Produkcijas refaktors pabeigts (§54–§65):** git versijas; 64 testi;
  modeļa sha256 piespraude; masku provenance (rerender vairs nepārgriež
  masku, `--no-decontam` kā drošības līdzeklis vairs nav vajadzīgs);
  `config.toml` + koda/config hash atskaitēs; pilnībā neatkarīgs
  checker; `engine/` pakotne ar fasādi. Plāns un statuss:
  `PRODUKCIJAS_PLANS.md`.
- **Ēnas modelis:** `studio_v1_contact_pcss`, lietotāja apstiprināts
  Vans piegādē (8. sadaļa). Vecie modeļi — arhīvā.
- **`uploads/`** satur tikai 4 Slam Jam paraugus un sasaldētās
  `00/01/02` pakotnes. Neapskatītu produktu oriģinālu pašlaik nav.
- **§47 tēma** (īstās ēnas pārnese) lietotāja lēmumā atlikta —
  **necel to atkal, ja viņš pats nejautā**.

---

## 8. Ēnas apakšsistēma — viss, kas zināms

Pašreizējais ražošanas modelis ir **`studio_v1_contact_pcss`**
(`loop.studio_shadow_bg`). To izsauc MASTER renderis (`engine/render.py`,
ar `canvas_scale=para_scale`) un `loop.render_paraugs` gala audeklā
(`canvas_scale=1.0`), tāpēc ēna abos mērogos ir viens un tas pats fiziskais
lielums. Visi citi modeļi (`cast_shadow` S2 u.c.) ir **vēsture `archive/`
mapē** un kanoniskajām izvadēm netiek lietoti.

### 8.1 Modelis

Divi komponenti samazina fona caurlaidību:

```
transmission = (1 − contactAO(d)) · (1 − 0.32 · V^0.80)
contactAO(d) = 0.10 · exp(−d/1.4)
```

- `d` = attālums ārpus maskas **audekla pikseļos**;
- `V` = laukuma-gaismas redzamība: siluets projicēts **43°** (attēla
  koordinātēs — leju-labi; viena studijas gaisma no augšas-kreisās visam
  katalogam) par **16** audekla px; penumbra aug ar attālumu
  **σ(d) = 0.9 + 0.28·d** (PCSS princips: ēna asākā kontaktā, mīkstāka
  tālāk), rēķināta pusizšķirtspējā ar 5 līmeņiem (0.8/1.8/3.2/5.0/7.5);
- metēnā daļa logā **42→58 px** izdziest līdz nullei — tālāk fons ir
  tieši 243.

### 8.2 Kalibrācija un godīguma piezīme

Konstantes pielāgotas diviem pilniem Slam Jam paraugiem pēc
sektoru×attāluma profiliem (E/W/N/S joslas pret maskas attālumu).
Piegādātā Vans komplekta pilno kadru agregāts pret paraugu mērķi:
E pie kontakta Δ≈78 (mērķis 79,7), W ≈2,5 (mērķis 2,0); RMSE pa
joslām **1,85**. Tuvplānu paraugi skaitliski **netika** kalibrēti
(velveta ribiņas šķeļ sliekšņa masku) — tos vērtēja vizuāli.

**Nav vēl pierādīts:** modelis nav validēts uz neatkarīga (holdout)
komplekta — kalibrācija un pārbaude notika uz tiem pašiem diviem
paraugiem. Pie pirmās jaunas grupas salīdzini sektoru profilus, pirms
maini konstantes.

### 8.3 Noteikumi, kas nedrīkst atgriezties

1. Simetriska/ambient ēna vai vienmērīgs halo visapkārt — lietotājs
   noraidīja (Vans Attempt 2). Virzienam jābūt vienam: tumšs kontakts
   gaismas pusē gandrīz nulle, metēnā daļa leju-labi.
2. Ēna kā JPEG pēcapstrāde virs gatava faila nedrīkst: simulētais
   GATE_R `bg_p99` bija 18–25 pret limitu 4. Ēnai jāiet caur integrēto
   MASTER+PARAUGS renderi.
3. Ēnas veidošanu nedrīkst balstīt uz nobīdītu siluetu ar vienmērīgu
   blur (plato ar gaišu joslu) vai maskēt `(1−α)` (neēnota līnija).
4. Veco `cast_shadow` S2 (tagad `archive/`) neliec virs pašreizējām
   izvadēm. S2 parametri vēsturei: `spread 14 · ox 26 · oy 32 ·
   soft 1.8 · tail 0.14` (tā `main()` noklusējumi bija citi).

### 8.4 Pārbaude pēc katra ēnas labojuma

- Invarianti piesprausti testos (`TestStudioShadow`, palaišana
  `python3 -m unittest test_workflow_v2`): tālais fons tieši 243;
  austrumu kontakts Δ 60–95, rietumu <8; Δ monotoni dilst ar attālumu;
  ārpus 58 px loga Δ=0.
- Ražošanas bildē mēri sektorus pēc **faktiskās maskas attāluma**.
  `measure_shadow.py` "kodola Δ" kalibrācijai neder: tas siluetu sāk
  ar `gray < bg−12`, tāpēc tumšu ēnu ieskaita apģērbā (paraugiem deva
  Δ 3–4, kas nav kontakta mērījums).

---

## 9. Kas ir izmērīts un strādā

- **ISNet (`isnet-general-use`)** uz pilna kadra: 1,45 s, tīrs siluets.
- **Henley pilots:** 5 bildes, vidēji **10,49 s/bilde**, visas iziet checker.
  Trīs no piecām ISNet QA noraidīja → GrabCut fallback strādāja.
- **Krāsu LUT (henley komplekts):** WB `(0.956044, 1.0, 1.109544)`,
  ekspozīcija `1.06`, gaišo toņu rolloff no `0.86`, S-līknes kontrasts `0.18`.
- **Malas alfa:** pusplatums 1,6 avota px, kontūra izlīdzināta ar σ = 1,6,
  kontrasts atjaunots 1,65; alfa piespiedu kārtā 255 vismaz 5 px iekšpusē un
  0 vismaz 5 px ārpusē.
- **V2 vienību testi:** 8/8 iziet.
- **Papīra noplūdes detektors** strādā un izgāja injekcijas testu.

---

## 10. Aklie ceļi — NEDARĪT (katrs ir izmēģināts un atmests)

### 10.1 Modeļi
- **BiRefNet / BEN2 / SAM** — neder: 1982 MB RAM, 2 vCPU, nav GPU, nav swap.
  OOM vai ārpus laika mērķa. Modelis tika dzēsts.
- **`u2netp`** — ātrs, bet pilnā kadrā izlaiž piedurkni.
- **`silueta`** — izlaiž vienu piedurkni pilnā kadrā; tuvplānos izvēlas birku.
- **SegFormer ADE / clothes-seg** — plakaniski izklātā apģērba tuvplānos nedeva
  lietojamu pilnu auduma masku.
- **ISNet tuvplānos** — izvēlas birku/apkakli, nevis audumu. Tāpēc QA to noraida
  un notiek GrabCut fallback.

### 10.2 Malas un maskas
- **Maskas sašaurināšana "uz drošo"** — nav atļauta; lietotājs to noraidīja.
- **Malu krāsošana ar fona krāsu** (recolour) — aizliegta.
- **Maskas slīpēšana / pievilkšana / izpludināšana** kā labojums — aizliegta.
- **Caurumu aizpildīšana pēcapstrādē** — nedrīkst aizpildīt fona komponenti,
  kurā ir drošā fona (`GC_BGD`) sēkla: tā var būt apzināta sprauga starp auduma
  slāņiem. Aizpildīšana atjauno galdu kā melnu bloku.

### 10.3 Ēna
- Vienkāršs izpludināts nobīdīts siluets — pārāk šaurs, uzlīmes efekts.
- Vienmērīgs halo ap visu apģērbu — nav fiziski iespējams, lietotājs noraidīja.
- Simetriska ēna — noraidīta; virziens ir augšā-kreisi.
- Kontakta ēnas atsevišķa zīmēšana — izmērīts, ka nevajag, dod dubultu maliņu.

### 10.4 Citas tehnikas, kas pārbaudītas ar mērījumu un noraidītas
Graudu pievienošana fonam (plakans fons ir prasība, ne defekts),
light wrap / screen subtraction (noplūdes nav), edge extend (kāpņu risks).
Sīkāk `PROFESIONALAS_METODES.md` §5.

### 10.5 Īstas ēnas pārnese no oriģināla (`real_shadow.py`)
Metode strādā (rolling-ball izgūšana + afīnā pārnese), **bet**:
- Vienīgajā oriģinālā ar ēnu (`MVIMG_20261020_161031.jpg`, džinsi) īstās
  metēnās ēnas nav — ir tikai plāna kontūra 10–25 px un **papīra kroku** ēnas.
- Kroku ēna un īstā ēna **nav atšķiramas pēc stipruma** (abas vidēji Δ 14,2,
  p95 32,7). Ierobežojot joslu 1–110 px, paliek tikai kontūra.
- Henley kadru oriģināli tika dzēsti pēc ZIP piegādes — to vairs nav.
- Secinājums: īstu ēnu var iegūt tikai **uzņemšanā** (vienpusējs gaismas avots
  no sāna). Nepiedāvā pārnesi no veca foto.

---

## 11. Vides ierobežojumi (šie ir fiksi, pielāgojies)

- **RAM: 1982 MB, bez swap.** 2 vCPU, nav GPU.
- Tāpēc smagi modeļi nav iespējami; ISNet worker iet atsevišķā procesā.
- PNG `optimize=True` uz augstfrekvences auduma ir ļoti lēns — v2.1 to atmeta
  (ietaupīja 10–12 s/bilde).
- `/var/tmp` satur instalētās pakotnes un modeli; pēc sandbox atiestatīšanas
  tās atjauno `setup_v2.py`. Darba telpā paliek tikai kods un atskaites.
- `PIL.Image.open()` uz jau atvērta faila objekta met `AttributeError` —
  ielādē datus vienreiz.

---

## 12. Failu karte

```
/home/user/
  uploads/                     lietotāja oriģināli + paraugi + sasaldētās .md
                               pakotnes (nedzēst bez lēmuma)
  loop_bildes/                 git repozitorijs (versiju avots)
    workflow_v2.py             CLI ieeja + fasāde (741 r.)
    engine/                    config, infra, provenance, masks, grade,
                               render, report — ražošanas loģika
    config.toml                parametri (vārti/spec nav šeit)
    checker_v2.py  setup_v2.py  isnet_native.py  loop.py
    test_workflow_v2.py        64 testi
    closeup.py  close_group.py  plate_segment.py  paper_leak.py
    rebuild_master.py  measure_shadow.py
    archive/                   vecie ēnu modeļi un v1 — sasalusi vēsture
    LOOP.md                 v1 noteikumi, starta protokols, sarkanās līnijas
    WORKFLOW_V2.md          v2.1 specifikācija un izmērītie modeļu fakti
    LOOP_KOMANDAS.md        lietotāja komandu ceļvedis (ko viņš var rakstīt)
    PRODUKCIJAS_PLANS.md    refaktora plāns un statuss (soļi 1–6 pabeigti)
    PROGRESS.md             hronoloģiskā vēsture (§1–§6x) — lasi pēdējos §
    PAPIRA_NOPLUDES_QA.md   lielākais mērījumu dokuments (2400+ r.)
    PROFESIONALAS_METODES.md  profesionālo tehniku audits + noraidījumi
    MASKU_AUDITS.md, MALU_AUDITS_ITER7.md, ATMINAS_UN_ATRUMA_TESTI.md
    output/
      master/        MASTER_1to1 PNG
      paraugs/       PARAUGS_2000x2500 JPG
      masks/         binārās maskas + *_ALPHA.png + *_MASK.json provenance
      profiles/      per-bildes profili
      audits/        sēklu priekšlikumi, attempt atskaites/hash
      report_v2.json, report_v2_maker.json, grade_profile_v2.json
      V2_KOLAZA.jpg
    HANDOFF/
      00_SAKU_SHEIT.md   šis fails (kanoniskā kopija)
      atjaunot.py        vecās pakotņu sistēmas rīks (vairs nelieto atjaunošanai)
```

---

## 13. Kā uzturēt šo atmiņu (lai tā nenoveco)

- Pēc katra nozīmīga labojuma pievieno jaunu sadaļu `PROGRESS.md` un
  `PAPIRA_NOPLUDES_QA.md` ar numuru (`§48`, `§49`, …).
- Katrā ierakstā: **kas bija problēma → ko mērīju → ko mainīju → kas mainījās
  skaitļos → jauns sha256**.
- Ja mainās kāds no 3., 5. vai 8. sadaļas faktiem — atjauno **šo failu** un
  pārģenerē pakotnes (14. sadaļa).
- Kad lietotājs izsaka jaunu pastāvīgu prasību — ieraksti to 3. vai 4. sadaļā
  ar datumu. Tās nav pagaidu piezīmes; tās paliek spēkā.

---

## 14. Pakotnes un atjaunošana

> **Statuss kopš produkcijas refaktora (2026-10-24):** primārais
> versiju avots ir **git repozitorijs** `loop_bildes/` darba telpā.
> `01_DZINEJS.md` / `02_ATMINA.md` mapē `uploads/` ir sasaldēts v2.1
> momentuzņēmums no laika pirms refaktora — **neatjaunot tos pāri
> pašreizējam kodam**. Zemāk esošā atjaunošanas instrukcija ir vēsture
> gadījumam, ja darba telpa kādreiz ir tukša.

Lai jaunā sarunā būtu kods un dokumenti, lietotājs augšuplādē:

- `01_DZINEJS.md` (308 KB) — viss ražošanas kods
- `02_ATMINA.md` (279 KB) — visi dokumenti
- `atjaunot.py` — atjaunošanas rīks

Tad:

```bash
cd /home/user/loop_bildes
python3 atjaunot.py 01_DZINEJS.md      # raksta kodu, pārbauda sha256
python3 atjaunot.py 02_ATMINA.md       # raksta dokumentus
python3 atjaunot.py 01_DZINEJS.md --check   # tikai pārbaude, neko neraksta
```

Katrs fails tiek pārbaudīts pēc sha256 no manifesta. Ja fails jau eksistē ar citu
saturu, vecais tiek pārsaukts par `*.bak-<laiks>`, nevis pazaudēts.

**Svarīgi:** `01_DZINEJS.md` un `02_ATMINA.md` nav lasāmi dokumenti — tie ir datu
nesēji. Nepūlies tos lasīt ar acīm; palaid `atjaunot.py` un lasi oriģinālos
failus.

### Pārģenerēšana

**Pašlaik nav iespējama:** `izveidot_pakotni.py` darba telpā nav (ne
saknē, ne `HANDOFF/`). Ar git kā primāro avotu pakotnes pārģenerēšana
nav nekā vajadzīga; ja lietotājs kādreiz lūdz, ģenerators vispirms
jāizveido no jauna un jāpārbauda pret `atjaunot.py` formātu.

---

## 15. Viena lapa — ja nevari atcerēties neko citu

- Fons `#F3F3F3` (243), 2000×2500, apģērbs centrēts.
- Apģērbu nepār-zīmē. Tikai fonu un ēnu.
- Ēna: `studio_v1_contact_pcss` — viena gaisma no augšas-kreisās (metēnā daļa
  43° leju-labi), ass tumšs kontakts, logs līdz 58 px, tālāk tieši 243.
- Apstiprinājumi ar pogām. Kolāža → ZIP → dzēst tikai pēc lejupielādes.
- Pirms jaunas grupas vienmēr: "Vai šīs ir visas šīs grupas bildes?"
- Skaitļi, nevis gaume. Godīgums, nevis pārliecība.
- Krātuve zem 100 MB.

---

## Pielikums A — `atjaunot.py` pilns teksts (drošības tīkls)

Ja atjaunošanas rīka nav, izveido to no šī bloka:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atjaunot.py — atjauno darba telpu no HANDOFF pakotnes.

Lietošana:
    python3 atjaunot.py 01_DZINEJS.md            # atjauno kodu uz /home/user/loop_bildes
    python3 atjaunot.py 01_DZINEJS.md --target /tmp/test
    python3 atjaunot.py 01_DZINEJS.md --check     # tikai pārbauda, neko neraksta

Pakotnes formāts (vienkāršs, bez atkarībām):
    === MANIFEST ===
    ceļš<TAB>baits<TAB>sha256
    === END MANIFEST ===
    === FILE: relative/path.py ===
    ...faila saturs burtiski...
    === END FILE ===

Nekas netiek pārrakstīts klusām: ja fails jau eksistē ar citu saturu,
skripts to pārsauc uz *.bak-<laiks>.
"""
import os
import sys
import hashlib
import time

MARK_MAN = "=== MANIFEST ==="
MARK_MAN_END = "=== END MANIFEST ==="
MARK_F = "=== FILE: "
MARK_F_END = "=== END FILE ==="


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def parse(path):
    with open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    manifest = {}
    files = {}
    mode = None
    cur = None
    buf = []

    for ln in lines:
        if mode is None:
            if ln.rstrip(" \t") == MARK_MAN:
                mode = "manifest"
                continue
            if ln.startswith(MARK_F) and ln == ln.lstrip():
                mode = "file"
                cur = ln[len(MARK_F):].rstrip(" =").strip()
                buf = []
                continue
            continue

        if mode == "manifest":
            if ln.rstrip(" \t") == MARK_MAN_END:
                mode = None
                continue
            if not ln.strip():
                continue
            parts = ln.split("\t")
            if len(parts) == 3:
                manifest[parts[0].strip()] = (int(parts[1]), parts[2].strip())
            continue

        if mode == "file":
            if ln.rstrip(" \t") == MARK_F_END:
                files[cur] = "\n".join(buf)
                mode = None
                cur = None
                buf = []
                continue
            buf.append(ln)

    return manifest, files


def main():
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 2

    bundle = args[0]
    target = "/home/user/loop_bildes"
    check_only = False
    i = 1
    while i < len(args):
        if args[i] == "--target" and i + 1 < len(args):
            target = args[i + 1]
            i += 2
        elif args[i] == "--check":
            check_only = True
            i += 1
        else:
            print("Nezināma opcija: %s" % args[i])
            return 2

    if not os.path.isfile(bundle):
        print("Nav atrasta pakotne: %s" % bundle)
        return 2

    manifest, files = parse(bundle)
    print("Pakotne : %s" % bundle)
    print("Faili   : %d" % len(files))
    print("Mērķis  : %s" % target)
    print("Režīms  : %s" % ("TIKAI PĀRBAUDE" if check_only else "RAKSTĪŠANA"))
    print("-" * 72)

    ok = 0
    bad = 0
    wrote = 0

    for name in sorted(files):
        data = (files[name] + "\n").encode("utf-8")
        got = sha256_bytes(data)
        exp = manifest.get(name)
        good = (exp is None) or (exp[1] == got)
        if good:
            ok += 1
        else:
            bad += 1

        mark = "OK " if good else "SHA!"
        extra = ""
        if not check_only:
            dst = os.path.join(target, name)
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            if os.path.isfile(dst):
                with open(dst, "rb") as fh:
                    if sha256_bytes(fh.read()) == got:
                        print("%s  %-42s (jau identisks)" % (mark, name))
                        continue
                os.replace(dst, dst + ".bak-" + time.strftime("%Y%m%d-%H%M%S"))
                extra = " (vecais -> .bak)"
            with open(dst, "wb") as fh:
                fh.write(data)
            wrote += 1
            extra += "  %d B" % len(data)
        print("%s  %-42s%s" % (mark, name, extra))

    print("-" * 72)
    print("Pārbaudīti: %d   OK: %d   SHA nesakrīt: %d   Ierakstīti: %d"
          % (len(files), ok, bad, wrote))

    missing = [m for m in manifest if m not in files]
    if missing:
        print("UZMANĪBU — manifestā ir, bet pakotnē nav: %s" % ", ".join(missing))
        bad += len(missing)

    if bad:
        print("REZULTĀTS: NEPILNĪGI — skat. rindas ar SHA!")
        return 1
    print("REZULTĀTS: VISS LABI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Palaid:
```bash
python3 atjaunot.py 01_DZINEJS.md
```

---

## Pielikums B — ātrā pašpārbaude pēc atjaunošanas

```bash
cd /home/user/loop_bildes
git status --short                            # jābūt tukšam (tīrs repo)
python3 -m py_compile *.py engine/*.py        # viss kompilējas
python3 -m unittest test_workflow_v2          # 64 testi, OK
python3 setup_v2.py --check                   # vide gatava apstrādei
du -sh /home/user
```
