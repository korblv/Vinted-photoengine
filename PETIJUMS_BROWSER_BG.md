# STATUSS 2026-10-22: **BG0 VIRZIENS SLĒGTS UN ARHIVĒTS**

Lietotājs izvēlējās arhivēt bez turpmākas izmantošanas. Iemesls: BG0
BiRefNet-lite 512 neizturēja generalizāciju — uz trim jauniem attēliem tas
deva segumu 0.9990, "nav piemērojams" un 0.0000, kamēr iepriekšējais
panākums (161146 → 0.7472) bija viens gadījums. Sīkāk:
`PAPIRA_NOPLUDES_QA.md` 9. sadaļa. Kods `lab/lab_bg0.py` paliek tikai kā
vēsturisks pieraksts; to nedrīkst ieslēgt ražošanā.

---

# Pētījums: pārlūka fona noņemšanas lapas un idejas mūsu workflow

Datums: 2026-10-21

## Mērķis un robeža
Meklēt tikai tādas idejas, kas var uzlabot mūsu lokālo Workflow v2.1:

1. kadru piepildošu auduma tuvplānu semantisko atlasi;
2. BRIA tipa masku defektu noteikšanu/labojumu, īpaši aizpildītus fona ķīļus;
3. malas kvalitāti pilnā izšķirtspējā;
4. ātrumu un atmiņas drošību 2 CPU / ~1,9 GB RAM sandboxā;
5. juridiski izmantojamu licenci.

Pētījums bija tikai publisko lapu/repozitoriju lasīšana. Neviena lietotāja
produktu bilde netika augšupielādēta nevienā pakalpojumā; ražošanas kods
netika mainīts.

## Interesantākās atrastās lapas/projekti

| Projekts | Ko tas dara | Vērtīgākā ideja mums |
|---|---|---|
| Xenova Remove Background Web | Transformers.js + BRIA RMBG-1.4, 100% pārlūkā | Kanoniskais mazais references piemērs; tas pats ceļš, ko izmanto dverso fallback |
| Nuki (`nuki.akr.moe`) | Vienā lapā RMBG-1.4 FP16, ISNet FP16, MODNet un BiRefNet-lite 1024 | Godīga atteikto modeļu tabula: BiRefNet oriģināleksports saduras ar WebGPU storage-buffer limitu; q8 WebGPU var būt lēnāks par FP16 |
| Cutout Model Lab | Viena bilde pret ORMBG/BRIA/MODNet ar WASM/WebGPU un q8/FP16 variantiem | Salīdzinājuma laboratorijas modelis: viens attēls, vairāki modeļi, backend/dtype un laiks blakus |
| Begone (`bg.gnass.buzz`) | BiRefNet-lite, Restore/Erase ota, caurumu meklēšana, priekšplāna krāsas novērtēšana un īstas ēnas ekstrakcija | “Clean plate” polinoma fons ēnas formai/krāsai; caurumu QA ar border flood-fill un cietas malas īpatsvaru |
| Clipout | BiRefNet-lite + pilnas izšķirtspējas guided filter + krāsu dekontaminācija + touch-up ota | Publisks AIM-500 mērījums: GPU ceļā pēcapstrāde pret tīru masku samazina MSE par 22% un gradienta kļūdu par 31% |
| BG0 | Automātiska full/lite BiRefNet izvēle pēc ierīces, WebGPU→WASM fallback kāpnes, atsevišķs zema RAM iOS ceļš | Ražošanas līmeņa modeļa reģistrs: piespraustas revīzijas, timeouti, bojāta keša izmešana, worker izbeigšana, lai WASM heap atbrīvotu |
| Evan remove-bg | BiRefNet-lite/ISNet, iterēts krāsu guided filter un Segment Anything objektu pievienošana/noņemšana ar klikšķi/kasti | Kļūdas labošana objekta līmenī bez modeļa atkārtotas palaišanas; optimizēts BiRefNet eksports ar native DeformConv un FP16 glabātiem svariem (~90 MB) |
| Removed-Background (Villariasa) | RMBG-1.4 + keep/remove ota + YOLOS-tiny/SlimSAM punktu atlase | Mazs prompt modelis var noņemt tieši konkrētu fona gabalu, piemēram, mūsu BRIA ķīli |
| bg-gone | Tas pats modelis pārlūkā un CLI; var izvadīt tikai matte | Laba atdalīšana: maska kā atsevišķs artefakts, ne tikai gala PNG |

## Modeļu secinājumi mūsu videi

### 1. BiRefNet-lite ir nākamais loģiskais kandidāts
Iemesli:
- MIT licence modeļiem/eksportiem ir daudz piemērotāka nekā BRIA nekomerciālā licence.
- Ir speciāli pārlūkam optimizēti ONNX eksporti:
  - `jiabins0303/birefnet-lite-1024-webgpu`, FP16, 114 834 127 baiti;
  - `studioludens/birefnet-lite-512`, FP16, 98 484 532 baiti, FP32 191 877 254 baiti;
  - `onnx-community/BiRefNet_lite-ONNX`, FP16, 114 538 221 baits.
- Evan projektā deformējamās konvolūcijas aizstātas ar ONNX Runtime native
  `DeformConv`, izvairoties no ļoti lielām gather operācijām un iegūstot
  aptuveni 4× ātrumu. Tas ir tieši jāpārbauda mūsu CPU sandboxā, jo agrāk
  izmantotais rembg BiRefNet ceļš bija pārāk lēns/smags.

### 2. BRIA RMBG-1.4 joprojām ir kvalitātes etalons tuvplānam, bet licence ir šķērslis
Mūsu vienas bildes testā tā bija daudz labāka par ISNet. Tomēr BRIA
RMBG-1.4 un RMBG-2.0 modeļa kartes norāda nekomerciālu lietošanu, tāpēc
bez atsevišķas BRIA vienošanās to nevajadzētu izmantot komerciālu
produktu foto ražošanā. Salīdzināšanai var vēlāk pārbaudīt BRIA FP16
(88 MB) pret q8, bet tas neatrisina licenci.

### 3. MVANet ir otra prioritāte, nevis pirmais tests
MIT licence un DIS fokuss ir pievilcīgi. Mazākais atrastais ONNX fails ir
`model_q4f16.onnx` — 85 027 081 baits, bet FP16 ir 211 405 738 baiti.
Swin arhitektūras CPU/RAM uzvedība mūsu sandboxā nav zināma.

### 4. ORMBG un MODNet nav mūsu galvenā cerība
ORMBG ir Apache-2.0, bet augšupējais modelis ir optimizēts cilvēkiem un
portretiem; neatkarīgs 2026. gada apskats to atzīmē kā vājāku
ne-cilvēku/produktu objektiem. MODNet ir portretu matting modelis.

### 5. BEN2 un smagie jaunie modeļi pagaidām nav praktiski
BEN2 FP16 ONNX ir 219 121 675 baiti, un mūsu vidē tas jau iepriekš
beidzās ar OOM. FeyNoBg ir 263M parametru BiRefNet atvasinājums; bez neliela ONNX eksporta un ar licences signālu neatbilstību starp repozitoriju
un modeļa karti tas nav pirmais kandidāts 1,9 GB RAM videi.

## Algoritmiskās idejas, ko vērts pārņemt

### A. Fona ķīļa/caurumu QA
Begone izmanto rupju režģi un flood-fill no attēla malām: ar malu saistīts
tukšums ir īsts fons, bet ieslēgtas tukšas zonas ar cietu objekta malu apkārt
tiek atzīmētas kā iespējamie caurumi. Mums vajag arī pretējo testu:
ar malu vai šauru atveri saistītas, gludas, papīra krāsai līdzīgas zonas,
ko modelis kļūdaini iekļāvis apģērbā. Tās jāatzīmē kā `paper_leak`, nevis
automātiski jādzēš, jo balts audums var izskatīties līdzīgi papīram.

### B. Prompt korekcija tikai kļūdas apgabalā
SlimSAM (~14 MB kvantizēts) vai līdzīgs mazs prompt modelis varētu ar
negatīvu punktu/kasti izvēlēties konkrēto fona ķīli. Mūsu gadījumā aģents
pēc zoom audita var deterministiski norādīt punktu, bet checker pēc tam
pārbauda, vai nav noņemts audums. Tas ir precīzāk nekā jauns pilns GrabCut.

### C. Guided filter tikai nenoteiktajā malas joslā
Clipout un Evan pieeja: modeļa masku vispirms notīra, pēc tam ar oriģinālu
kā krāsu vadoni tikai malas joslā “pievelk” alfai pie īstajām pikseļu
malām pilnā izšķirtspējā. Mums to vajadzētu salīdzināt ar pašreizējo
`refine_alpha`, nevis uzreiz aizstāt.

### D. Priekšplāna krāsas dekontaminācija
Begone izmanto “blur fusion” priekšplāna krāsas novērtēšanu ar diviem
rādiusiem un flīzēm ar 96 px halo. Tas var būt precīzāks par mūsu
pašreizējo krāsas paplašināšanu zem daļēji caurspīdīgas malas, īpaši
šuvēm un smalkiem pavedieniem. Jāuzmanās, lai dekontaminācija nemaina
pilnībā necaurspīdīgā apģērba kodolu.

### E. Īstas ēnas ekstrakcija no “clean plate”
Begone pielāgo gludu kubisku polinomu vienkāršam fonam, vairākas reizes
izslēdz ēnas kā tumšus izlecējus un pieņem ēnu tikai tad, ja pielāgošanas
RMS ir mazs. Pikseļi, kas ir tumšāki par fona plati, kļūst par atsevišķu
daļējas alfas ēnas slāni ar izmērītu krāsu. Mums tas varētu dot
dabiskāku ēnas formu nekā pašreizējā no maskas nobīdītā sintētiskā ēna,
bet gala fons joprojām paliktu #F3F3F3 un ēnu varētu neitralizēt.

### F. Modeļu reģistrs un atteikumu kāpnes
BG0 pieeja ir profesionāla: katram modelim piesprausta revīzija un
izmērs, ierīces spēju pārbaude pirms lejupielādes, atsevišķi lejupielādes
un inference timeouti, bojātas keša atpazīšana un secīga pāreja
pilnais → lite → cits backend. Mūsu Python pusē ekvivalents ir atsevišķs
process katram modelim, SHA-256 un skaidrs `needs_review` bez klusas
kvalitātes pasliktināšanās.

## Ieteiktais nākamais ierobežotais eksperiments

Katrā pilotā tikai 1–3 jau apstiprinātas testa bildes, bez ražošanas
integrācijas:

1. **BiRefNet-lite optimizētais ONNX** pret BRIA q8 un ISNet:
   viens grūts auduma tuvplāns + viens pilns kadrs; mēra inference,
   kopējo laiku, max RSS, segumu, ķīļa noplūdi un zoom malas.
2. Ja BiRefNet semantika ir laba, pārbaudīt **guided filter** kā
   alternatīvu pašreizējai malas apstrādei tikai uz tās pašas maskas.
3. Ja paliek fona ķīlīši, prototipēt **paper-leak QA**; korekciju vispirms
   veikt ar lokālu GrabCut vai SlimSAM negatīvo punktu un salīdzināt.
4. Ēnas clean-plate eksperimentu atlikt līdz brīdim, kad masku jautājums
   ir stabilāks.

Apstāšanās noteikums: ja BiRefNet-lite mūsu CPU pārsniedz 25 s/bilde,
OOM vai kvalitātē nepārspēj BRIA/ISNet hibrīdu, to neintegrējam un
neturpinām ar smagākiem modeļiem bez jaunas lietotāja izvēles.

## Galvenie avoti
- https://github.com/fgnass/begone
- https://github.com/evanfournier/remove-bg
- https://github.com/opencoredev/bg0
- https://github.com/AkaraChen/nuki
- https://github.com/mullojo/background-removal
- https://github.com/villariasa/removed-background
- https://github.com/bentossell/bg-gone
- https://clipout.io/guide
- https://huggingface.co/spaces/Xenova/remove-background-web
- https://github.com/yocreoquesi/nukebg/issues/431
- https://huggingface.co/briaai/RMBG-1.4
- https://huggingface.co/briaai/RMBG-2.0

## Papildinājums: BiRefNet dzīvotspējas pārbaude mūsu sandboxā

2026-10-21 lietotājs apstiprināja sākt ar ieteikumiem. Tā kā darba
telpā nebija mājas testa bildes, vispirms tika veikta tikai modeļu
dzīvotspējas pārbaude uz parauga atsauces; tas nav mājas tuvplāna
kvalitātes secinājums.

- Evan native-DeformConv BiRefNet 1024 (91 708 456 baiti,
  SHA-256 `159e8f2bede6be58b614bfcda4a4f2de4cddbe7fbbb475464fb427caf026ab9d`):
  sesijas izveide sasniedza 506 100 KB RSS, bet inference tika
  nogalināta ar exit 137 arī ar 1 pavedienu, izslēgtu CPU mem arenu un
  mem-pattern. Secinājums: 1024 grafa aktivācijas mūsu 1,9 GB vidē
  nav dzīvotspējīgas.
- `studioludens/birefnet-lite-512` FP16 (98 484 532 baiti,
  SHA-256 `eff9216bb2f9d3f023d9c2b7196845a7485739ab1f231593633e4d2344ffc516`):
  arī OOM inference laikā, visticamāk GatherND deformējamo konvolūciju
  emulācijas lielo starptensoru dēļ.
- **BG0 optimizētais `int8-full-512.ort`** (55 563 408 baiti,
  SHA-256 `6fa08dc7df0417597454e52e2b721b2c190b13545a46a6bd3a8bac1ebf0709dc`):
  sesijas izveide 0,881 s, inference **3,754 s**, max RSS
  **740 336 KB**. Parauga atsaucei segums 0,3335, nenoteiktā alfa
  0,87%; vizuāli pilns bikšu siluets un tīra iekšējā atstarpe.
  Secinājums: šis eksports iztur dzīvotspējas vārtus un ir nākamais
  reālais kandidāts vienai grūtai mājas tuvplāna bildei.

Audita attēls un JSON atrodas `output/birefnet_test/`. BG0 modelis
pagaidām glabājas tikai `/var/tmp/birefnet_test/`; ražošanas kods nav
mainīts.

## Reālais vienas bildes tests: konteksta apmale ir izšķiroša

Uz tās pašas `MVIMG_20261020_161146.jpg` (SHA-256
`50f58532febffe031b12e312f799f7751ecb36fb01c24a717e73535084959e8a`):

- BG0 dzimtajā 512×512 kvadrāta ievadē deva tikai negatīvus logits
  (maksimums -9,75), tātad maskas segums bija **0,0000**. Modelis
  kadru piepildošu audumu vispār neatpazina kā objektu.
- Aspect saglabājošs `letterbox` ar vidēji pelēkām sānu joslām deva
  tikai 0,2412 segumu attēla laukumā.
- Kad oriģināls tika samazināts līdz **80%** un novietots 512×512
  kanvā ar no bildes fona nomērītu papīra krāsu `RGB(206,202,190)`,
  segums kļuva **0,7455**, viena komponente 1,000 un closeup QA PASS.
  IoU pret BRIA ir **0,9750**. 65% variants ir līdzīgs (0,7473; IoU
  0,9770), bet 80% saglabā vairāk efektīvās izšķirtspējas.
- Garantētās auduma zonas BG0 pad80 maskā visas ir 100% virs sliekšņa.
  Fona ķīlī kļūdaini iekļauti 37,29% pikseļu (BRIA: 100%), tātad BG0
  ar kontekstu šajā defektā ir labāks, bet vēl nav ideāls.
- Laiki: BG0 inference atsevišķā procesā 3,248 s (variants tajā pašā
  sesijā 2,724 s), max RSS 839 244 KB. BRIA inference 2,310 s, ISNet
  predict 2,637 s. BG0 ir pietiekami ātrs mūsu mērķim.
- Guided-filter A/B (grayscale guide, 1536×2048 darba mērogs) tika
  noraidīts: neapstrādātas BG0 malas pārejas mediāna bija 9 px,
  guided variantiem 14–29 px, un nenoteiktā alfa pieauga no 1,68%
  līdz 2,21–3,18%. Kontūras gradienta metrika pieauga tikai tāpēc,
  ka kontūra kļuva teksturētāka/zobaināka.

Secinājums: daudzsološais ražošanas kandidāts nav “BG0 kā ir”, bet
**BG0 + deterministiska papīra konteksta apmale kā tuvplānu fallback**.
Pirms integrācijas tas jāpārbauda uz citiem audumiem/krāsām un
jāpievieno paper-leak QA/korekcija atlikušajiem fona ķīļiem.
