# STUDIJAS — dzinēja pašizglītošanās žurnāls

Mērķis (lietotāja uzdevums 2026-10-24): no "vidējās izglītības" līmeņa
(strādā, bet katra grupa nes pārsteigumu) uz "augstāko" (prognozē
kļūmes pirms palaišanas, mēra ar literatūras mēriem, nevis pašu
izdomātiem). Šis fails ir mana ilgtermiņa atmiņa: saruna beidzas,
fails paliek. Lasīt kopā ar `PROGRESS.md` un `PAPIRA_NOPLUDES_QA.md`.

Noteikums: studiju secinājums NAV atļauja mainīt kodu. Katrs
kandidāt-eksperiments iet parasto ceļu — mērījums, lietotāja poga,
solis, komits.

## Absolvēšanas kritēriji ("augstākā izglītība") — izmērāmi

1. Trīs pēc kārtas neredzētas grupas bez neviena koda labojuma
   (šodien: Vans prasīja parametra labojumu + ēnas pārbūvi; Henley
   — trīs labojumus; sērija = 0).
2. Pirmā mēģinājuma checker PASS ≥ 90 % bilžu (šodien: Vans A1 2/4,
   Henley A1 4/5 maskētas, no tām 4/4 PASS).
3. Katrai maskas metodei (ISNet, pad-retry, plate) zināms malas
   kvalitātes skaitlis (Boundary IoU) uz sintētiskas patiesības —
   šodien metodes izvēli vada segums un QA attiecības, ne malas
   precizitātes mērījums.
4. Ēna validēta uz neatkarīga holdout (≥5 sveši produktu foto),
   nevis tiem pašiem 2 Slam Jam paraugiem, uz kuriem kalibrēta.
5. Neviena klusa parametru ignorēšana (šodien zināms pretpiemērs:
   `--rotate` īsās atslēgas, §67).

## M1 — Sliekšņi un sadalījumi (apgūts 2026-10-24)

Fakti:
- Otsu maksimizē starpklašu dispersiju; optimāls tikai pie
  bimodāla histogrammas ar līdzīgām klašu dispersijām un
  izmēriem (saistība ar t-testu; Xue & Titterington; "Maximum
  similarity thresholding", ScienceDirect S1051200414000451).
  Novirze vienmēr ir uz lielākās dispersijas klases pusi
  (Wikipedia "Otsu's method", Limitations; Kittler–Illingworth
  minimum-error metode ir variants nevienādām dispersijām).
- Labās astes (right-skewed) sadalījumiem Otsu slieksnis sistemātiski
  aiziet par augstu; lognormālais modelis to labo (Entropy 2022,
  24(9):1204). Mūsu birkas E sadalījums (p50 6.4, p90 9.4, maks.
  31.3) ir tieši šāds — Otsu 13.73 > p90 bija paredzama kļūme,
  nevis nejaušība.
- "Valley emphasis" svari liek slieksni tuvāk histogrammas ielejai
  (IET Image Process. 2020) — alternatīva mūsu enkuriem.

Ko tas nozīmē mums:
- Mūsu §69 ģeometriskā vidējā enkurs ir log-domēna viduspunkts —
  literatūra to atbalsta tieši šķībiem sadalījumiem.
- Kandidāt-eksperiments E1: PIRMS Otsu rēķināt atdalāmības mēru
  η = σ²_starp/σ²_kopā un klašu izmēru attiecību; ja η zems vai
  attiecība galēja, Otsu neuzticēties uzreiz (tagad fallback
  atklājam tikai pēc seguma < 0.25). Mērīt uz reģistrētajiem
  gadījumiem (birka + kalibrācijas kadri + sintētika).

Paštests: Kāpēc Otsu birkā izvēlējās 13.73? — Jo starpklases
dispersiju maksimizēja dalījums "reti ekstrēmi (druka, vīles) pret
visu pārējo"; klašu dispersiju asimetrija + šķībums. ✓

## M2 — Maskēšanās literatūra (COD) un tekstūras mērogi (pamati)

Fakti:
- COD (camouflaged object detection) ir atsevišķa disciplīna tieši
  mūsu baltā-pret-pelēko gadījumam: priekšplāns pēc krāsas
  neatdalāms; divi šķēršļi — "intrinsic similarity" un "edge
  disruption" (Fan et al., CVPR 2020, COD10K; He et al., CVPR 2023).
- Krāsa ir vājākā pazīme; tekstūra strādā, bet tikai vairākos
  mērogos reizē (klasiskā apakšējā līmeņa tekstūras agregācija:
  Galun et al.; apkopots COD apskatos, arXiv:2012.13581 un
  arXiv:2408.14562). Viena mēroga tekstūras detektors (mūsu plate:
  pusizmērs, logs 25) pēc definīcijas akls pret faktūru, kuras
  periods nesakrīt ar logu — tieši mūsu makro šūnu gadījums.
- Malas COD uzdevumos jārekonstruē atsevišķi, nevis jāgaida no
  reģionu klasifikācijas (edge reconstruction virziens, CVPR 2023).

Ko tas nozīmē mums:
- Kandidāt-eksperiments E2: plate vairākmērogu versija — E kartes
  mērogos 1.0/0.5/0.25 ar logiem, kas seko mērogam; maska =
  mērogu konsenss (vairākuma balsojums), QA vārti tie paši. Vispirms
  uz sintētikas ar zināmu patiesību, tad uz birkas/apakšmalas/kakla
  (hashiem kontroles kadros jāpaliek pieņemtiem ar tiem pašiem QA
  skaitļiem vai labākiem).
- Īstermiņā lētāk: E1 (paredzēt Otsu kritienu) nekā E2 (pārbūvēt).

## M3 — Matting un krāsu dekontaminācija (pamati)

Fakti:
- Kompozīcijas vienādojums I = αF + (1−α)B. Oreols nav "slikta
  maska" — tā ir B krāsa, kas fiziski iejaukta malas pikseļos.
  Dekontaminācija rēķina F_clean = (I − (1−α)B)/α (rembg
  dokumentācija, "Color decontamination"; Photoshop "Decontaminate
  Colors"; PyMatting foreground estimation, Levin et al. 2007).
- Formula nestabila pie α→0 (dalīšana) — tāpēc ražošanā to
  ierobežo/regularizē vai pielieto tikai šaurā joslā.
- Mūsu dzinējs dara pretējo izvēli: `decontaminate_rim` nevis
  atkrāso malu, bet nogriež to (maskas erozija puscaurspīdīgajā
  zonā). Necaurspīdīgam apģērbam tas ir droši; pūkainam/šifona
  audumam tas apēdīs īstu puscaurspīdīgu detaļu. rembg 2.0.85,
  ko jau lietojam, satur gan `-dc` dekontamināciju, gan closed-form
  alpha matting (`-a`) — mēs izmantojam tikai ISNet masku.

Ko tas nozīmē mums:
- Kandidāt-eksperiments E3: uz sintētiskas kompozīcijas ar zināmu
  F un α salīdzināt (a) mūsu rim-griešanu, (b) F-atjaunošanu pēc
  formulas ar α grīdu. Mērs: ΔE malas joslā pret patieso F un
  GATE_H/GATE_R skaitļi. Tikai ja (b) uzvar ar skaitli, to vispār
  piedāvāt ražošanai.

## M4 — Malu kvalitātes mērīšana (pamati)

Fakti:
- Cilvēka vērtējums par maskas kvalitāti vislabāk korelē ar
  gradienta kļūdu (r=0.75), vāji ar SAD (0.45) un MSE (0.51)
  (Rhemann et al., CVPR 2009 matting benchmarks). Standarta
  četrinieks: SAD, MSE, Grad, Conn.
- Mask IoU lielos objektos ir nejūtīgs pret malas kļūdām
  (piemērā Mask IoU 89→97 %, kamēr Boundary IoU 69→91 %);
  Boundary IoU rēķina IoU tikai joslā d ap kontūru (bieži
  d = 2 % no attēla diagonāles) (Cheng et al., CVPR 2021,
  arXiv:2103.16562).

Ko tas nozīmē mums:
- Mūsu vārti mēra īpašības (segums, caurumi, alfa pāreja), bet ne
  VIENU tiešu malas precizitātes skaitli pret patiesību — jo
  patiesības nav. Sintētisks etalons to dod.
- Kandidāt-eksperiments E4: sintētisku zināmas patiesības kadru
  komplekts (auduma tekstūras + papīrs, dažādi kontrasti/mērogi)
  kā pastāvīgs tests: katrai metodei ziņot Boundary IoU (d=8 px
  2000 px mērogā) un Grad kļūdu. Tad metodes izvēle kļūs mērīta,
  nevis "kura pirmā izgāja QA".

## M5 — Krāsu konstante un krāsu godīgums (pamati)

Fakti:
- Klasiskie baltā balansa algoritmi (Gray-World, Shades-of-Gray,
  Gray-Edge, gamut) uz etaloniem dod mediānu leņķa kļūdu ~7°,
  ~3.7°, ~3°, ~2.1° (Finlayson & Zakizadeh, BMVC 2014 tabula).
  Mūsu pieeja ir spēcīgāka par visiem: mēs mērām PAŠU papīru kā
  zināmu neitrālu mērķi — ar noteikumu, ka papīra paraugs nav
  piesārņots un papīrs tiešām ir neitrāls. Riski: telefona AWB
  jau ir pielikusi savu korekciju (strādājam sRGB, ne RAW), un
  papīra parauga izvēle ir visa ķēdes vājākais posms.
- Krāsas atšķirību ziņošanas standarts ir ΔE2000 (izmanto arī
  WB korekcijas novērtēšanā blakus leņķa kļūdai). Mūsu GATE_K
  mēra tikai b* nobīdes mediānu (limits 2.5) — tas neredz
  gaišuma/krāsainības drebu atsevišķos auduma reģionos.

Ko tas nozīmē mums:
- Kandidāt-eksperiments E5: checker ziņojumā pievienot (tikai
  ziņot, nebļķēt) auduma kodola ΔE2000 mediānu un p95 starp
  oriģinālu un LUT rezultātu; pēc 3 grupu datiem spriest, vai
  vērts to padarīt par vārtiem.

## M6 — Ēnas un tirgus realitāte (papildināts)

Fakti:
- Divkomponentu modelis (kontakta AO + metēnā ēna) ir nozares
  konsenss; kontaktiņš ir tumšākais un gandrīz bez izplūduma
  (2–6 px uz 2000 px), metēnā kļūst gaišāka un mīkstāka ar
  attālumu (Pikes, PixelPrep, IT-S ceļveži — tie paši avoti,
  uz kuriem balstīts mūsu modelis). Mūsu īstenojums ar PCSS
  penumbru σ(d) ir fizikāli pareizais vispārinājums.
- Tirgus vietu noteikumi nav par ēnu, bet par fonu: Amazon hero
  kadram prasa tīru (255,255,255) un ~85 % aizpildījumu. Mūsu
  243 fons ar ēnu ir apzināta Slam Jam-redakcionālā izvēle
  Vinted vajadzībām — jāzina, ka tas NAV universāls.
- Kompozīcijas literatūrā (shadow harmonization) galvenais
  "viltojuma" signāls ir gaismas virziena/mīkstuma nesakritība
  starp objekta paša ēnojumu un pievienoto ēnu.

Ko tas nozīmē mums:
- Mūsu ēnas leņķis ir fiksēts 43° neatkarīgi no tā, no kurienes
  gaisma krita uzņēmumā. Kandidāt-eksperiments E6 (tikai
  brīdinājums, ne automātika): novērtēt dominējošo ēnojuma
  virzienu no auduma kroku gradientiem maskas iekšienē un
  atskaitē parādīt Δ pret 43°; lēmums paliek cilvēkam.
- Absolvēšanas punkts 4 (holdout) paliek atvērts: vajadzīgi ≥5
  sveši produktu foto ar līdzīgu uzstādījumu kā paraugiem.

## M7 — Pārizlase un asināšana (pamati)

Fakti:
- Negatīvu daivu filtri (Lanczos-3, bicubic) pēc konstrukcijas dod
  overshoot pie malām — gaiša/tumša apmalīte ir matemātika, ne
  kļūda (Wikipedia "Ringing artifacts", "Lanczos resampling").
- USM overshoot ir izmērāms kā palielināts lēciens pie pakāpes
  malām (Cao et al., IEEE Signal Process. Lett. — detektēšana
  tieši pēc overshoot artefaktiem). Mūsu GATE_R atradums
  (42 % -> p99 26/27; 25 % -> 18) ir šī paša lieluma netiešs
  mērījums.
- Pretlīdzeklis bez asuma zaudēšanas: anti-ringing clamp —
  ierobežot paraugu ar lokālo min/maks kodola centrālajā daivā
  (mpv/libplacebo prakse).

Ko tas nozīmē mums:
- Kandidāt-eksperiments E7: sintētiskas pakāpes malas tests cauri
  mūsu resize + asināšanas ķēdei; overshoot budžets skaitlī, nevis
  "25 % izskatījās labi uz vienas grupas".

## KPI žurnāls (papildināt pēc katras grupas)

| Grupa | Attempt 1 maskas | Attempt 1 checker | Koda labojumi pa ceļam | s/bilde |
|---|---|---|---|---|
| Vans (4) | 4/4 | 2/4 | asināšana 42->25 %; ēnas modeļa pārbūve | ~12 |
| Henley (5) | 4/5 | 4/4 (no pabeigtajām) | plate slieksnis; bg_inside krāsa; GATE_P | 11.08 |

## Lasāmsaraksts (izlasīts vai rindā)

- Rhemann et al. 2009, matting novērtēšanas etalons (Grad/Conn).
- Levin, Lischinski & Weiss 2007, closed-form matting; PyMatting.
- Cheng et al. 2021, Boundary IoU (arXiv:2103.16562).
- Fan et al. 2020, COD10K; COD apskati arXiv:2012.13581,
  arXiv:2408.14562.
- Otsu 1979 + Kittler–Illingworth; lognormālais Otsu (Entropy 2022).
- Finlayson & Trezzi 2004, Shades of Gray; van de Weijer, Gray-Edge.
- NVIDIA PCSS (shadow_PCSS.pdf) — mūsu ēnas fizikas pamats.
- Cao et al., USM overshoot detektēšana.

Nākamā studiju sesija (pēc nākamās grupas vai lietotāja vārda):
M4 padziļināti (uzbūvēt E4 sintētiskā etalona prototipu bez
ražošanas izmaiņām) — tas ir lētākais ceļš no "izgāja QA" uz
"izmērīti laba mala".
