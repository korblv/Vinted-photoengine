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

## M8 — Padziļinātā sesija pēc pufjakas grupas (2026-10-24)

Pufjakas grupa (§74–§82) atklāja četras vājās vietas, kuras papīra
grupas neskāra: (a) tumšajā zonā CIE Lab krāsas sabrūk (līcis pret
audumu neatdalījās); (b) maskas dzimst pusmērogā un mala ir
interpolēta, ne piesieta foto malām; (c) pikseļu līmeņa lēmumi dod
raupju robežu gradientā; (d) metālisks spīdums paletēm ir "daudz
krāsu", fizikāli — viena krāsa + gaisma. Plus biznesa risks (N9).

### N1 — OKLab tumšajai zonai
- CIE Lab zilajos/tumšajos toņos nokrāsa līkumo (hue bending);
  OKLab (Ottosson 2020) to labo: vienādības RMS kļūdas pret
  uztveres datiem Lab 1.70 (L), 1.84 (C), 0.69 (H) -> OKLab 0.20,
  0.81, 0.49. Transformācija: 2 matricas + kubsakne — lēta.
- Mūsu līcis bija tieši Lab vājajā zonā (tumši zils pret tumši
  siltu). Kandidāt-eksperiments **E8**: tumšo palešu atdalāmība
  (min. savstarpējais attālums, sēklu malu attiecība) Lab pret
  OKLab uz sintētikas un §77 izmērītajiem centriem. Pieņemt tikai
  ar skaitli un tikai tumšajai zonai (bool config slēdzis).
  **E8 veikts 2026-10-24 (§84): NAV pierādīts** — ar ražošanas
  sliekšņiem 1:1 OKLab sēklu robežas attiecības visos gadījumos
  sliktākas, testa kļūda uz 122248 nav mazāka. Bet eksperiments
  atklāja skalas faktu: Lab76 tumšos attālumus dod ~2.5x lielākus
  nekā OKLab x100, tāpēc absolūtie sliekšņi nav pārvietojami
  (attīrīšana OKLab nogāza pusi centru). Līča pikselis — vienīgais
  skalas-neatkarīgais tests — OKLab telpā pārvietojas pareizā
  virzienā (0.67->0.91/1.13). Kandidāts **E8b**: tas pats tests ar
  katrai telpai kalibrētiem sliekšņiem, tie paši uzvaras kritēriji.
  **E8b veikts 2026-10-24 (§85): tēma SLĒGTA.** Ar kalibrētiem
  sliekšņiem (s=0.30-0.40; centri 4/4) OKLab zaudē visos trīs
  kritērijos (M2 sliktāka 12/14; M3 122248: 0.0027 pret 0.0000;
  M5 līcis 0.44 pret 0.67 — E8 "pluss" bija attīrīšanas artefakts).
  Mācība: uztveres vienmērība ≠ klašu atdalāmība; Lab tumšais
  izstiepums mūsu klasifikatoram ir priekšrocība. Paliek CIE Lab.

### N2 — Guided filter / joint upsampling malām
- Guided filter (He, Sun, Tang): lokāli lineārs modelis q=aI+b,
  ∇q=a∇I — izvadei mala ir tikai tur, kur vadattēlam; O(N);
  teorētiska saistība ar matting Laplacian. Joint upsampling:
  lēti pusmērogā rēķinātu lauku (mūsu maskas lauku) paceļ pilnā
  izšķirtspējā, struktūru ņemot no oriģināla. Fast GF: >10x
  paātrinājums ar apakšizlasi.
- Mums tas ir tiešs kandidāts `LANCZOS` maskas vilkšanas vietā.
  Kandidāt-eksperiments **E9** (= E4 etalona turpinājums):
  sintētiska zināma mala; salīdzināt Lanczos pret guided
  upsampling ar Boundary IoU un malas nobīdi pikseļos.
  **E9 veikts 2026-10-24 (§86): NAV pierādīts.** Binārā 2x režīmā
  (chroma/plate) guided zaudē visur (BIoU5 0.79-0.81 pret 0.8353);
  mīkstā 4x režīmā krāsu variants (r=4, eps=1e-3) kritēriju (a)
  zaudē par 0.005, toties atgūst plānas struktūras (siksnu chamfer
  1.43 pret 8.23) un iztur viltus šuves slazdu; pelēktoņu variants
  slazdā iekrīt (3.49) - tas mūsu jomā aizliegts. Paliek LANCZOS.
  Atlikums: E9b tikai uz īstām ISNet mīkstajām maskām, ja kāda
  grupa uzrādīs plānu struktūru zudumu.

### N3 — Superpikseļi (SLIC) pret robežas troksni
- SLIC reģioni seko attēla malām un vidējo pikseļu troksni; SLIC+
  GrabCut/Bayes literatūrā dod gludākas robežas nekā pikseļu
  grafs. Risks: līdzīgu krāsu reģionos SLIC veido viltus zonas
  (maskēšanās) — tāpēc mums tikai kā lēmuma vienība `chroma`
  nedrošajā zonā, nevis globāli.
- Kandidāt-eksperiments **E10**: nedrošajā zonā lauku un E7
  vērtēt superpikseļa mediānai; sintētikā mērīt robežas
  robainību (perimetrs pret ideālo) un kļūdu laukumu.
  **E10 veikts 2026-10-24 (§88): formāli NAV pierādīts** -
  robainības kritērijs bija tukšs (ražošanas robeža sintētikā jau
  gludāka par patieso: 0.9916). BET variants V1 (SLIC mediāna
  galvenā lauka |lauks|<5 zonā) precizitātē uzvarēja abos
  līmeņos: kļūdas -33%/-28%, Boundary IoU 0.59->0.73. V2 (tumšā
  zona) sliktāks. Replika pret īsto chroma: IoU 1.00000.
  Kandidāts **E10b**: V1 A/B uz īstas ne-papīra grupas aiz
  config slēdža (SLIC ~4.5 s/bilde).

### N4 — Ēnas invariante (Finlayson)
- Log-hromas telpā apgaismojuma izmaiņa guļ uz vienas taisnes
  (virziens atkarīgs tikai no kameras); projekcija ortogonāli
  tai dod attēlu bez ēnām. Virzienu atrod bez kalibrācijas:
  pareizā projekcija minimizē entropiju (Finlayson et al.,
  PAMI 2006; IJCV 2009 — kvadrātiskā entropija, viens minimums).
- Brīdinājums no literatūras: metode krīt uz gandrīz
  ahromatiskām virsmām.
- Kandidāt-eksperiments **E11**: sintētiska ēna pāri divu krāsu
  robežai; vai invarianta pazīme tumšajā piegājienā atdala
  labāk nekā (a*,b*) attālums (mērīt sēklu malu attiecību).
  **E11 veikts 2026-10-24 (§87): NAV pierādīts, tēma slēgta.**
  Entropijas theta izgāzās uz divu virsmu ainas (45° nepareizi;
  kļūda 0.43 pret Lab 0.0); pat ar teorētisko theta=35°
  (invariance strādā: korelācija ar ēnu 0.024) klasifikācija
  zaudē (0.12 pret 0.0), jo projekcija izmet diskriminantes
  virzienu; JPEG invarianci lauž (0.024->0.46). §78 pieeja
  (paraugot ēnu paletēs) paliek pareizā ģimene.

### N5 — Dihromatiskais modelis spīdumam
- Shafer: pikselis = m_b * ķermeņa krāsa + m_s * gaismas krāsa.
  Vienas virsmas pikseļi veido "T" klasteri: matēto līniju
  (ķermeņa virziens) un spīduma līniju (gaismas virziens).
- Mūsu mediān-griezuma paletes metāliskam audumam tērē centrus
  gar abām līnijām; fizikāli precīzāk būtu attālums līdz līnijai
  (ķermeņa krāsa -> gaismas krāsa), nevis līdz punktiem — mazāk
  centru, mazāka "zagšanas" virsma.
- Kandidāt-eksperiments **E12**: sintētisks zils audums ar
  spīduma gradientu; punktu palete pret līnijas attālumu:
  atdalāmība un centru skaits pie vienādas kļūdas.
  **E12 veikts 2026-10-24 (§89): NAV pierādīts, tēma slēgta.**
  Ar patieso S segmenti perfekti (L2 kļūda 0.0), bet S novērtēšana
  no datiem izgāzās: spilgtākie pikseļi apgriezti baltā
  ([100,0,0] pret [98.8,0.3,3.3]) un 3.6 dE virziena kļūda svītru
  iznīcina (spīduma kļūda 0.04-0.16 pret punktu 0.002-0.017).
  Plus: segmenti beidzas vienā S -> palešu QA attālums 0 pēc
  konstrukcijas. Punktu paletes paliek.

### N6 — Caurspīdīgi audumi: īsts matting (nākotnes specifikācija)
- Tills, siets, mežģīnes: bināra maska pēc definīcijas melo —
  pikseļi ir maisījums. PyMatting (closed-form/KNN) ar trimap
  no mūsu maskas (erozija=drošs FG, dilatācija=drošs BG) to
  risina; KNN matting etalona ir spēcīgs tieši caurspīdīgiem
  objektiem (alfa ~0.5, nevis 0/1).
- Bet mūsu renderis un GATE_H ir bināri. Vajadzīgs lietotāja
  specifikācijas lēmums PIRMS koda: ko rādīt pircējam
  (caurspīdīgumu pret #F3F3F3 vai necaurspīdīgu siluetu).
  Kandidāt-eksperiments **E13** (bez ražošanas izmaiņām):
  sintētisks tills pār rakstu; izmērīt binārā ceļa alfa kļūdu,
  lai lēmums būtu ar skaitli.
  **E13 veikts 2026-10-24 (§90): izmērīts, gaida lietotāja
  specifikācijas lēmumu.** ISNet alfa tīklā kļūdās par 0.47-0.60
  (melnu tillu sauc par necaurspīdīgu, baltu par fonu). Chroma
  melnā tillā sevi noraida (FG palete saindēta caur caurumiem:
  56% masas = fons). Pašreizējā rendera kļūda tīkla zonās:
  dE mediāna 50-56 (melns) / 10-16 (balts) - vecā fona spoks.
  Varianti lēmumam: STOP-eskalācija / E13b matting prototips /
  pieņemt ierobežojumu / atlikt līdz pirmajai tādai grupai.

### N7 — Dekontaminācija (E3 apstiprinājums no nozares)
- rembg 2.x dokumentācija tagad eksplicīti apraksta krāsu
  dekontamināciju ar to pašu formulu F=(I-(1-a)B)/a — nozare
  iet F-atjaunošanas, nevis griešanas ceļu. Mūsu E3 kandidāts
  paliek spēkā; nestabilitāte pie a->0 attiecas tikai uz
  ~5 px malas joslu (GATE_H zona).

### N8 — Modeļu ainava 2026-10 (bez maiņas)
- rembg noklusējums tagad bria-rmbg (~1.02 GB; RMBG-2.0
  komerciālai lietošanai prasa maksas licenci) — neder ne RAM,
  ne licences dēļ. birefnet-general-lite ~214 MB ONNX (MIT),
  bet kopā ar mūsu ķēdi joprojām riskants pie 1982 MB RAM.
  Kopienas INT8 ISNet (~44 MB) maina svaru, ne malu klasi.
- Secinājums nemainīgs: ISNet + izmērīti rezerves ceļi.
  Modeļa maiņa tikai caur E4/E9 etalonu ar skaitli.

### N9 — Platformas noteikumi (svarīgs biznesa risks)
- Vinted Catalog Rules (burtiski): "They have to represent the
  item as it is - no image editing is allowed." Pirmajai bildei
  jāparāda visa prece; bildēm jābūt paša uzņemtām.
  https://www.vinted.com/catalog-rules
- Vinted preses komentārs (2026-10-23): AI kā uzlabošanas rīks
  (piem., fona noņemšana) pats par sevi nav aizliegts, ja
  bilde paliek precīza; maldināšana par stāvokli ir aizliegta
  (sankcijas līdz konta apturēšanai). Pārdevēju pieredze
  papildina: tīri balts fons var iedarbināt "stock photo"
  automoderāciju.
- ES AI akts: no 2026-08-02 AI-ģenerētam saturam jābūt
  atpazīstamam/marķētam. Mūsu izvade nav ģenerēta (pikseļi
  oriģināli, mainīts fons), bet godīga deklarācija sludinājumā
  ("fons digitāli notīrīts, prece bez retušas") ir drošākā
  pozīcija. **Praktisks ieteikums lietotājam** (lēmums viņa):
  mūsu bildes kā papildu foto + vismaz viena neapstrādāta
  bilde sludinājumā; defektus vienmēr tuvplānā (darām jau).

### Video avoti (YouTube; pēc noklusējuma aprakstu/metadatu līmenis; ar yt-dlp varu arī transkriptu + kadrus — tad atzīmēts atsevišķi)
- **"Stop Prompting Claude. Use Karpathy's Method Instead."**
  (Austin Marchese, 2026-06-09, 13:18; youtu.be/7zZy1QTvokM) —
  NOSKATĪTS PILNĪBĀ 2026-10-24 pēc lietotāja saites (transkripts
  3336 vārdi + kadri /30 s). Metode: 3 slāņi — (1) SPEC:
  detalizēts specifikācijas dokuments prompta vietā (mērķis caur
  interviju, agile mazie soļi ar kontrolpunktiem, precizitāte,
  eksplicīta lēmumu verifikācija); (2) VERIFIER: vērtēšanas
  kritēriji PIRMS darba + otrs modelis-kritiķis + ārējie signāli;
  Karpathy "dzīvnieki pret spokiem" = modelim nav motivācijas un
  tas nezina, kad tam trūkst zināšanu; (3) ENVIRONMENT:
  CLAUDE.md, zināšanu bāze, atkārtojamās prasmes (skills),
  aizsargnoteikumi rīku līmenī (hooks), nevis promptā; kategorijas
  always/ask first/never. Finale (Karpathy): "You can outsource
  your thinking, but you can't outsource your understanding."
  Sasaiste ar mums: mūsu sistēma lielāko daļu jau dara (00 dokuments
  un reģistrēti kritēriji = spec; checker_v2 un vārti = verifier;
  HANDOFF/dokumenti un pogas = environment). Atšķirības: otra
  modeļa-kritiķa mums nav (deterministisks checker + lietotāja acs
  ir stiprāk tur, kur ir metrikas); video solījumi "10x" ir
  mārketings bez mērījumiem. **Viena aizgūta kandidātidēja:** mūsu
  "never do" noteikumi šobrīd dzīvo prozā un testos; kur kļūdas cena
  augsta (§91 caurspīdīgo audumu karogs), tos būtu vērts kādreiz
  pārnest koda līmenī (piem., preflight pārbaude). Lēmums lietotājam,
  kods nemainīts. Avota svars: satura veidotājs + pārdošanas
  piltuve; Karpathy citāti īsti, sistēma — autora iepakojums.
  Ideju, ne pierādījumu avots.
- Apģērbu foto uzstādījums eBay/Vinted: youtube.com/watch?v=jeriM7YyLm0
  un DIY foto dēlis: watch?v=y7TskuVvp6w — uzņemšanas puse
  (vienmērīgs fons+gaisma) noņem vairāk segmentācijas darba
  nekā jebkurš algoritms pēc fakta.
- Baltā fona apgaismojums: watch?v=1wS6rdH8gzI, watch?v=MNnIvZu-PQ0
  — fons gaišāks par preci, prece atdalīta no fona (tieši mūsu
  fona mērījumu pieņēmumi).
- Flatlay e-komercijai ar 2 gaismām: watch?v=u2SjB-mF6ec.
- OpenCV GrabCut: watch?v=aOqOwM-Qbtg; GIMP matting izvēle:
  watch?v=QG5NYDp-kj8 — ROI rīku uzvedības salīdzinājumam.
- Gabor filtri tekstūrai: watch?v=QEz4bG9P3Qs — virzienjutīga
  tekstūras pazīme (kandidāts E7 paplašinājumam pret mūsu E7 std).
- Lejupizlases lekcija: watch?v=mDDp6qoG7dA (M7 papildinājums).

### Telegram kanāli (publiskie priekšskatījumi t.me/s/<kanāls> lasāmi bez konta)
- @AI_DeepLearning ("AI with Papers") — CV/DL raksti ar arXiv+repo
  saitēm; pārbaudīts 2026-10-24, aktīvs un akadēmisks.
- @gradientdude — CV rakstu TL;DR no praktiķa (FAIR/CVPR).
- @computer_science_and_programming — plašs ML/CV/Python (139k),
  kvalitāte jaukta. RU OpenCV kopienas (piem. @opencv_ru) —
  praktiski piemēri, valoda RU.
- Brīdinājums: "AI tools" kanālu vairākums ir mārketings; vērtība
  tikai rakstu kanālos, un arī tie ir ideju, ne pierādījumu avots.

### Prioritātes pirms nākamās grupas (cena/ieguvums)
1. **E9** guided upsampling uz sintētiskā etalona (ar E4 metrikām).
2. **E8** OKLab tumšajai zonai (sintētika + §77 centri).
3. **E11** ēnas invariante kā tumšā piegājiena pazīme.
4. **E10** superpikseļi nedrošajā zonā.
5. **E12** dihromatiskā līnija paletēm.
6. **E13** caurspīdīgo audumu mērījums + lietotāja lēmums.

**Statuss 2026-10-24 (2. kārta pabeigta, §84-§91):** visi seši
eksperimenti veikti. Slēgti ar pierādījumu: E8/E8b, E11, E12.
Nepierādīts: E9 (atlikums E9b tikai uz ISNet mīkstā ceļa).
Atvērtais ieguvums: **E10b** (SLIC V1) - vērtēt uz nākamās īstās
ne-papīra grupas. E13: lietotājs lēmumu atlika (§91) - pie
inventarizācijas caurspīdīgu apģērbu KAROGOT un jautāt pirms
apstrādes. Ražošana 2. kārtā nemainīta.

## KPI žurnāls (papildināt pēc katras grupas)

| Grupa | Attempt 1 maskas | Attempt 1 checker | Koda labojumi pa ceļam | s/bilde |
|---|---|---|---|---|
| Vans (4) | 4/4 | 2/4 | asināšana 42->25 %; ēnas modeļa pārbūve | ~12 |
| Henley (5) | 4/5 | 4/4 (no pabeigtajām) | plate slieksnis; bg_inside krāsa; GATE_P | 11.08 |
| Pufjaka (4, koks) | 4/4 | 2/4 | chroma ceļš (2.4); tumšais piegājiens (2.5); ROI GrabCut labojums; ZIP apakškopa | 10.77 |

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
- Ottosson 2020, "A perceptual color space for image processing"
  (OKLab) — N1/E8.
- He, Sun, Tang, "Guided Image Filtering" (PAMI 2013); Fast GF
  arXiv:1505.00996 — N2/E9.
- Achanta et al. 2012, "SLIC Superpixels" (PAMI) — N3/E10.
- Finlayson et al., PAMI 2006 (invariantais attēls); IJCV 2009
  (entropijas minimizācija bez kalibrācijas) — N4/E11.
- Shafer 1985 dihromatiskais modelis; Klinker T-klasteris — N5/E12.
- Chen, Li, Tang, "KNN Matting" (PAMI 2013) — N6/E13.
- Vinted Catalog Rules (vinted.com/catalog-rules); ES AI akta
  marķēšanas prasības no 2026-08-02 — N9.

Nākamā studiju sesija (pēc nākamās grupas vai lietotāja vārda):
M4 padziļināti (uzbūvēt E4+E9 sintētiskā etalona prototipu bez
ražošanas izmaiņām) — tas ir lētākais ceļš no "izgāja QA" uz
"izmērīti laba mala".
