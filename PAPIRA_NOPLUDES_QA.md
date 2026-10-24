# Papīra noplūdes QA + korekcija + regresija

Datums: 2026-10-22
Statuss: **laboratorijas prototips validēts; ražošanas kodā NAV iekļauts**
Kods: `lab/lab_leak.py`, `lab/lab_common.py`, `lab/lab_bg0.py`, `lab/test_leak_injection.py`,
`lab/run_leak_161146.py`, `lab/run_samples.py`, `lab/analyze_channels.py`

---

## 1. Mērķis

Pārbaudīt, vai pēc maskas iegūšanas var **droši un deterministiski** atrast
gadījumus, kad maskā iekļuvis **papīrs** (fona materiāls), un to izņemt, nemainot
apģērbu. Šis bija trešais solis apstiprinātajā secībā (BG0 → guided filter →
papīra noplūdes QA → lokālā korekcija).

## 2. Konstrukcija

### 2.1 Fona (papīra) krāsas mērīšana

`measure_paper_colour()` — ārējais rāmis 2 % no īsās malas, sadalīts **divos
gaišuma režīmos** (Ostū slieksnis). Uzvar **gludākais** režīms (papīram tekstūra
≈ 0, audumam nav). Ja gludākais režīms aizņem < 10 % rāmja, ņem otru. Katrs
kandidāts tiek ziņots ar tekstūru un rāmja daļu — lēmums ir auditējams.

Rezultāti (5 attēli, visi pareizi):

| attēls | izmērītais papīrs | režīms | rāmja daļa |
|---|---|---|---|
| MVIMG_…161146 | (203, 199, 187) | bright, tex 0.58 | 74.1 % |
| paraugs 1 | (243, 243, 243) | bright, tex 0.00 | 100 % |
| paraugs 2 | (243, 243, 243) | bright, tex 0.00 | 100 % |
| paraugs 3 | (243, 243, 243) | bright, tex 0.00 | 54.0 % |
| paraugs 4 | (243, 243, 243) | bright, tex 0.00 | 26.1 % |

Iepriekšējais vienkāršais rāmja mediāns uz parauga 4 **neizdevās** (atgrieza
(67, 64, 69) — pašu apģērbu, jo tas aizņem 74 % rāmja).

### 2.2 Detektors — trīs kanāli

Pikselis skaitās papīrs maskas iekšienē, ja **visi trīs** nosacījumi izpildās:

1. **hroma** `dC = √((a*−a₀*)² + (b*−b₀*)²)` ≤ slieksnis — noturīga pret ēnu,
   jo ēna samazina L*, nevis a*/b*;
2. **tekstūra** (lokālā L* standartnovirze 5×5) ≤ slieksnis;
3. **gaišums** `L* ≥ L_min` — neviens pikselis nevar būt "papīrs ēnā" tumšāks
   par tumšāko izmērīto papīru (p1 − 3).

Sliekšņi **netiek izdomāti**: tie ir papīra klases (tie pikseļi, ko maska jau
uzskata par fonu) **90. procentiles**, iegrieztas fiziski saprātīgā diapazonā
(dC 0.5–3.0, tex 0.35–2.5). Atsevišķi tiek ziņots `garment_fpr` (cik % no
apģērba pikseļiem detektors maldīgi atzīmētu) un `separation_ratio`.

### 2.3 Korekcija

`correct_leaks()` — detektētie sēkliņu apgabali tiek **ģeodēziski audzēti** tikai
caur pikseļiem, kas paši ir papīrveidīgi; augšana apstājas pie auduma. Katram
sēklam ir augšanas griesti (1.6×). Pēc tam alfa tiek nolaista līdz 0 ar 1.2 px
mīkstu pāreju. **Nekas netiek zīmēts no jauna** — pikseļi tikai pāriet no
necaurspīdīga uz caurspīdīgu, un tikai tur, kur maska tos jau saturēja.

### 2.4 Sliekšņu atvasināšanas mācība

Pirmā versija izmantoja **Youden J optimumu** uz ΔE76. Tā izrādījās **nestabila**:
papīra klasei ir smaga aste (p95 ΔE = 42 ēnu dēļ), un 1 RGB vienības izmaiņa
fona krāsā pārlēca slieksni **14.63 → 7.39**. Aizstāts ar kvantiles metodi
augstāk. Šis ir ierakstīts kā negatīvs rezultāts — pie tā neatgriezties.

## 3. Rezultāti

### 3.1 Cietais tuvplāns 161146 (BG0, pad 80 %)

- fons izmērīts (203, 199, 187), uzticamība ok
- BG0 segums **0.7472**, lielākā komponente 1.0000, nenoteikta alfa 2.27 %
- infer 2.2 s
- **zonde: PASS, 0 noplūdes pikseļi**, ticamība *marginal*
- dC slieksnis 2.928, tex 1.706, L_min 29.09, garment_fpr **0.18 %**, recall 85.1 %

### 3.2 Paraugi — BG0 pret ISNet

| # | BG0 segums | ISNet segums | IoU | ISNet zonde | BG0 zonde |
|---|---|---|---|---|---|
| 1 | 0.3349 | 0.3327 | 0.9924 | PASS 0.000 % | PASS 0.000 % |
| 2 | 0.3377 | 0.3346 | 0.9836 | PASS 0.000 % | PASS 0.000 % |
| 3 | 0.8278 | 0.8278 | 0.9898 | PASS 0.375 % | PASS 0.000 % |
| 4 | **0.9298** | **0.4035** | 0.4340 | **DUBIOUS 9.606 %** | PASS 0.000 % |

Uz parauga 4 ISNet+GrabCut maska faktiski ir sabrukusi (0.4035 pret patieso
≈0.96), un zonde to godīgi atzīmē: 9.6 % maskas ir papīrs. BG0 tajā pašā attēlā
dod 0.9298 — pareizi.

Uz parauga 3 ISNet maskā ir reāls papīra halo virs jostas (vid. ΔE 0.26,
tekstūra 0.13, 0.375 %) — zem 0.5 % sliekšņa, tāpēc PASS, bet skaitlis ir redzams.

### 3.3 Injekcijas tests (galvenais pierādījums)

Tīšs papīrs tika **iestrādāts** maskā uz īstiem fona pikseļiem: 2 laukumi,
kopā **204 800 px**.

| solis | rezultāts |
|---|---|
| zonde pirms | **DUBIOUS**, 204 772 px atrasti (99.99 %), 2 reģioni |
| korekcija | izņemti 204 789 px |
| … no tiem injekcijas iekšienē | **99.99 %** |
| … **ārpus injekcijas** | **0 px** |
| pievienotie pikseļi | **0** |
| zonde pēc | **PASS**, 0.0 % |

Tas ir kontrolēts eksperiments ar zināmu patiesību: detektors atrod, korekcija
izņem tieši to, un nekas cits maskā nemainās.

## 4. Divi svarīgi negatīvi atklājumi

1. **ΔE/Youden pieeja neder** — sk. 2.4.
2. **Pirmā, vaļīgā zonde uz 161146 deva 7 viltus pozitīvus** (63 790 px,
   "DUBIOUS"). Pārbaudot katru apgabalu ar izgriezumiem acu pārbaudei:
   6 bija **gaišāki džinsa laukumi** (kabatas iekšpuse, ΔE 6.6–9.5, dC 4.2–5.6),
   bet 1 — **baltā cauruļu bante** gar kabatas malu (L* 91, dC 2.14).
   Neviens nebija papīrs. Stingrā zonde pareizi atgriež 0.
   Sk.: `output/birefnet_test/WEDGE_471.jpg`, `WEDGE_82.jpg`.

Secinājums: **baltas detaļas uz balta fona nav atšķiramas tikai pēc krāsas.**
Tāpēc korekcija nedrīkst strādāt bez uzraudzības — tā ir jāapstiprina vai
jāierobežo (sk. 6. punktu).

## 5. Pilnas darbplūsmas regresija (v2.1, 4 paraugi)

`workflow_v2.py --files` + `checker_v2.py`, 4 attēli:

- izgatavotas **4/4**, vid. **8.61 s/attēls**, maks. 11.79 s (limits 25 s)
- vienību testi **8/8 PASS**
- čekeris **2/4 PASS**

Neizturēja paraugs 3 un 4 — abi ir **full-bleed tuvplāni** (melns ripšķūdis
pa visu kadru). ISNet tur atrod tikai fragmentu (segums 0.0875 / 0.0277), pēc
tam auto-seed GrabCut **norij visu kadru** (mala 99 %), un gala vārti to
pareizi noraida: `GATE_D corners_valid=False`, `GATE_F full_shot=False`.

Tas **nav** orientācijas izmaiņu regresija: visiem paraugiem `rotation_cw = 0`,
un orientācijas kods šos ceļus neskar. Tas ir iepriekšējs ierobežojums:
auto-sēklas GrabCut strādā tikai tad, ja kadrā ir pietiekami daudz fona.

## 6. Kas nav izdarīts (apzināti)

- **Nekas nav iekļauts `workflow_v2.py` / `checker_v2.py`.** Vārti paliek A2, B,
  C, D, F, H, T — tie nemainījās. Jauna vārtu prasība bez lietotāja lēmuma
  netiek pievienota.
- Zonde maksā **5.4–6.4 s** uz 12.6 MP attēla (korekcija ~3 s). Tas ir par dārgu
  blakus 20 s mērķim; pirms iekļaušanas jārēķina uz samazināta mēroga
  (alfa ir zemo frekvenču, ±4000 px garā mala dod to pašu lēmumu).
- Korekcija ir validēta tikai ar **vienu** kontrolētu injekciju. Vajadzīgi
  vēl 3–5 dažādi foni (balts, krēmkrāsa, pelēks) un vismaz 2 balti apģērbi
  ar baltām etiķetēm.

## 7. Ieteikums

Papīra noplūdes QA ir **pietiekami labs, lai būtu brīdinājums, nevis bloķētājs**:
tas atrod īstu papīru (99.99 % kontrolē), klusē uz tīrām maskām (0.000 % uz
visiem 4 paraugiem un 161146) un godīgi atzīmē gadījumus, kur krāsa nepietiek
(`confidence: marginal`, piem. 161146 ar dC/tex attiecību 0.96).

Pirms iekļaušanas ražošanā vajadzīgs lietotāja lēmums par diviem jautājumiem
(uzdoti ar pogām).

---

## 8. Papildinājums pēc lietotāja lēmumiem (2026-10-22)

Lietotājs izvēlējās: **GATE_L kā brīdinājums**, **vēl testi ar citiem audumiem**,
**tūlīt labot tuvplānu auto-sēklu**.

### 8.1 GATE_L — ieviests un pārbaudīts

`checker_v2.py` tagad satur `GATE_L_paper_leak` ar `pass = None` un
`advisory = True`. Tā kā `ALL_PASS` rēķina `pass in (True, None)`, šie vārti
**nevar bloķēt piegādi**. Kļūda zondē tiek noķerta un ierakstīta kā
`skipped`, nevis nogāž čekeri. Zonde rēķinās uz samazināta mēroga (≤3000 px
garā mala), tāpēc maksā **1.8–2.1 s** uz 5 MP attēlu, nevis 5–6 s.

Pārbaude uz 4 paraugiem (pilna darbplūsma + čekeris):

| # | ALL_PASS | GATE_L | leak % | reģioni | laiks |
|---|---|---|---|---|---|
| 1 | True | PASS (high) | 0.000 | 0 | 1.82 s |
| 2 | True | PASS (high) | 0.000 | 0 | 1.86 s |
| 3 | False (D/F) | PASS (high) | 0.375 | 1 | 1.97 s |
| 4 | False (D/F) | **DUBIOUS** (marginal) | 9.606 | 25 | 2.09 s |

Vienību testi joprojām **8/8 PASS**.

### 8.2 Uz papīra balstītā fona maska (tuvplānu auto-sēklas pamats)

Jauna funkcija `paper_background_mask()` — **bez modeļa**: fons = tas, kas
neatšķiras no papīra (hroma + tekstūra + gaišuma grīda) **un** ir sasniedzams
no kadra malas. Tā nekad nemeklē "objektu", tāpēc tuvplānā, kur saliency modelis
atrod tikai fragmentu, tā darbojas.

| attēls | papīra-maska segums | atsauce | starpība |
|---|---|---|---|
| 161146 | 0.7722 | 0.7472 (BG0) | +0.025 |
| paraugs 1 | 0.3652 | 0.3327 (ISNet) | +0.033 |
| paraugs 2 | 0.3598 | 0.3346 (ISNet) | +0.025 |
| paraugs 3 | 0.9062 | 0.8278 (ISNet/BG0) | +0.078 |
| paraugs 4 | **0.9334** | 0.9298 (BG0) | **+0.004** |

Tas ir krietni labāk par pašreizējo auto-sēklu uz paraugiem 3 un 4, kur
ISNet+GrabCut dod 0.828 / **0.404**. Pārpalikums +0.025…+0.078 ir ēna ap
apģērbu (ēna ir gluda, bet tumšāka par papīru, tāpēc tā paliek "priekšplānā") —
tas jārisina kopā ar ēnu soli, kas līdz šim tika atlikts.

### 8.3 Auto-sēklas labošana — pārtraukta apzināti

Mēģināju atkārtoti izsaukt `closeup_mask()` ar saglabāto `cfg` no atskaites un
apgrieztu `init_bg`, lai izmērītu hipotēzi "tukšais fons sākas kā PR_BGD".
Abos gadījumos atgriezās **tukša maska**, lai gan tā pati funkcija darbplūsmā
šiem pašiem failiem deva 0.8278 / 0.4035. Tas nozīmē, ka starp sēklas
ģenerēšanu un `closeup_mask` ir sāniedarbības, ko es vēl nepārvaldu
(iespējams, atkarība no `ai_soft`/`small` mēroga vai no iepriekšēja stāvokļa).

**Lēmums: ražošanas `workflow_v2.py` netiek mainīts, kamēr tas nav izskaidrots.**
Pareizais ceļš: `paper_background_mask()` kā **raster** `sure_bg` padot
GrabCut tieši (nevis caur `bg_polys`), ar atsevišķu parametru, un tad to testēt.
Tas ir atsevišķs, mērāms darbs — nevis steigā veikts hot-patch.

---

## 9. Trīs jauni testa attēli (lietotāja pievienotie, 2026-10-22)

| fails | saturs | fons |
|---|---|---|
| `MVIMG_20261020_160550.jpg` | krēmbalts vafeles henlijs, balta etiķete | pelēkbrūns papīrs, L* 56 |
| `IMG_20261015_122248.jpg` | spīdīga zila pūkaina jaka | **koka grīda, nevis papīrs** |
| `MVIMG_20261020_161944.jpg` | melni Vans svārki | gaišs papīrs ar krokām, L* 84 |

Metode: ISNet (ražošanas ceļš, 768×1024 proxy), BG0 (pad 80 %), papīra-fona
prototips `paper_background_mask()`, un GATE_L zonde katrai maskai.
Salīdzinājuma lapa: `output/birefnet_test/COMPARE3.jpg` (oriģināls | ISNet |
BG0 | papīra-fons). Skaitļi: `COMPARE3.json`.

### 9.1 Rezultāti

| attēls | ISNet | BG0 | papīra-fons | patiesība (aptuveni) |
|---|---|---|---|---|
| 160550 | 0.1851 ⚠ fragments, noplūde **5.545 %** | **0.9990** ✗ | 0.6480, noplūde 0.163 % | ~0.62 |
| 122248 | 0.6347 | — (nav papīra) | 0.9737 ✗ | ~0.65 |
| 161944 | 0.2976 (blāva alfa) | **0.0000** ✗ | 0.6135 | ~0.30 |

### 9.2 Secinājumi

1. **BG0 neiztur generalizāciju.** Uz trim jauniem attēliem tas dod 0.999,
   “nav piemērojams” un 0.000. Vienīgais iepriekšējais panākums (161146,
   0.7472) bija **viens** gadījums, nevis likumsakarība. Ieteikums: **BG0
   virzienu slēgt** — tas nav uzticams ne uz vienu jauno audumu.
2. **Papīra-fona prototips ir labākais uz 160550 un 161944** (0.648 / 0.6135
   pret patiesību ~0.62 / ~0.30), un tam ir pareiza uzvedība arī uz 122248:
   kad papīra nav, tas atzīmē “nav papīra-fona” (`plausible=False`), tāpēc BG0
   un noplūdes zonde tiek **izlaistas**, nevis melo.
3. **Jauns, svarīgs defekts papīra-fona prototipā:** uz spīdīgās jakas tas
   izgriež caurumus spoguļatspīdumos — spīdums ir gluds, tāpēc izskatās pēc
   papīra. Tas jālabo ar papildu nosacījumu (spīdums ir gaišāks par papīru
   un tam ir asa gradienta mala).
4. **Ēna paliek priekšplānā** visos gadījumos (161944: +0.31 pret patiesību).
   Tas ir iepriekš atliktais ēnu solis, nevis maskas kļūda.
5. **GATE_L uzvedas godīgi** arī uz šiem: 160550 ISNet maskai → DUBIOUS
   (5.545 %, 4 reģioni — pareizi, jo maska ir fragments), 161944 → PASS 0.000 %.

### 9.3 Ieteikums pēc šī testa

- **BG0: apstādināt.** Nav pierādījumu, ka tas strādā ārpus viena attēla.
- Papīra-fona prototips: divi konkrēti labojumi (spīdums, ēna), tad atkārtot
  šo pašu testu. Ja pēc tiem 160550 un 161944 sasniedz ±0.02 no patiesības,
  to var likt kā tuvplānu fallback ar GATE_L uzraudzību.
- 122248 (koka grīda) paliek ārpus papīra režīma — tam vajag citu ceļu.

---

## 10. Defektu tuvplāni (lietotāja lūgums: vispirms parādīt)

Lapa: `output/birefnet_test/DEFECTS.jpg` (katrā rindā: oriģināls |
fons atzīmēts fuksijā | tekstūras karte 0–20). Skaitļi: `DEFECTS.json`.

### 10.1 Ko attēli parāda

**160550 (pleca mala).** Fuksija pareizi noklāj papīru augšā, bet tā **iekožas
apģērba plecā** — gar apkakles augšmalu un piedurknes malu iet robaina josla.
Tekstūras kartē redzams, ka tie ir **gludie, ēnotie pārejas joslas** pikseļi:
tie ir gludi (kā papīrs) un tumšāki, bet ne tumšāki par `L_min`, tāpēc iztur
visus trīs filtrus. Cēlonis: **ēnas pārejas josla pie auduma malas**, nevis
audums pats.

**122248 (zilā jaka).** Fuksija sēž tieši uz **tumšākajām, gludākajām jakas
krokām**. Iemesls nav spīdums, kā es sākotnēji domāju: fona krāsa tika
izmērīta no pašas jakas (37, 34, 41), tāpēc tumšās gludās krokas tai atbilst.
`plausible=False` to jau atzīmē, bet `paper_background_mask()` **joprojām
izpildās** un dod masku. Trūkst aizsarga: ja papīrs nav uzticams, funkcijai
jāatsakās, nevis jāmin.

**161944 (apakša).** Fuksija noklāj papīru labajā malā, bet robeža ir
**raiba/robotaina**, nevis tīra mala. Un **ēna zem svārkiem paliek
priekšplānā** — tā nav fuksijā, tāpēc tā nonāks gatavajā bildē kā tumšs
plankums.

### 10.2 Trīs konkrēti labojumi, kas izriet no šiem attēliem

1. **Aizsargs:** `paper_background_mask()` atgriež `refuse` un tukšu masku, ja
   `measure_paper_colour().plausible` ir False. (Šobrīd tas ir vienīgais
   cēlonis, kāpēc jaka sabrūk.)
2. **Ēnas josla pie malas:** papīra klasei jāpievieno nosacījums, ka pikselim
   jābūt **sasniedzamam no īstā fona caur citiem papīrveidīgiem pikseļiem ar
   nelielu lokālu gradientu** — ēnas pāreja pie auduma ir tieši tur, kur
   gradients aug, tāpēc tā apstāsies.
3. **Ēna zem apģērba:** atsevišķs solis (atliktais ēnu darbs) — ēna ir gluda,
   ar papīra hromu, bet tumšāka par `L_min`; to var atpazīt un noņemt vai
   aizstāt ar sintētisko ēnu, ko darbplūsma jau zīmē.

---

## 11. Trīs labojumi ieviesti — un to mērītais rezultāts

Lietotājs apstiprināja visus trīs labojumus un testu uz visiem 8 attēliem.

| attēls | pirms | pēc | atsauce | starpība |
|---|---|---|---|---|
| 160550 | 0.6480 | **0.7003** | 0.620 | +0.080 |
| 122248 | 0.9737 | **REFUSED** | 0.650 | — |
| 161944 | 0.6135 | **0.6735** | 0.300 | +0.373 |
| 161146 | 0.7722 | 0.7978 | 0.747 | +0.051 |
| paraugs 1 | 0.3652 | 0.3655 | 0.333 | +0.033 |
| paraugs 2 | 0.3598 | 0.3601 | 0.335 | +0.025 |
| paraugs 3 | 0.9062 | 0.9064 | 0.828 | +0.079 |
| paraugs 4 | 0.9334 | 0.9334 | 0.930 | +0.004 |

### 11.1 Kas nostrādāja

- **Labojums 1 (aizsargs) — strādā pilnībā.** Uz 122248 (koka grīda) prototips
  tagad atsakās, nevis min. Tas bija vienīgais cēlonis, kāpēc jaka sabruka.
- **Labojums 2 (sasniedzamība caur mazu gradientu) — novērsa konkrēto defektu.**
  Uz 160550 pleca mala vairs netiek apēsta. Cena: ēnas josla tagad paliek
  priekšplānā, tāpēc segums pieauga 0.648 → 0.700.

### 11.2 Kas nenostrādāja

- **Labojums 3 (ēna) — neizšāvās ne reizi** (`shadow 0.0 %` visos 8). Logika
  meklēja joslu `[shadow_lo, L_floor)`, bet īstā ēna ir daudz platāka
  diapazonā, un 161944 gadījumā "ēna" izrādījās **paša papīra krokas**, kas arī
  ir tumšas. Modelis ir pārāk šaurs.
- **Kopējais segums pasliktinājās** uz 160550 (+0.028 → +0.080), 161146
  (+0.025 → +0.051) un 161944 (+0.31 → +0.37). Uz studijas paraugiem nekas
  nemainījās (tie jau bija gandrīz ideāli).

### 11.3 Secinājums, kas jāpieņem

Abi labojumi **pārbīda kļūdu, nevis to novērš**: iepriekš algoritms apēda
apģērbu, tagad tas patur ēnu. Iemesls ir fundamentāls un to nevar atrisināt ar
sliekšņiem: **ēnots papīrs un apgaismots audums var būt vienā gaišumā**. Šim
jautājumam vajag īstu ēnu modeli (ēna = papīra hroma × vājāks apgaismojums,
ar paredzamu gradientu no malas), nevis vēl vienu slieksni.

**Statuss: papīra-fona prototips NAV gatavs ražošanai.** 3 no 8 attēlu tas ir
±0.03–0.08 robežās (labi), bet 161944 un 160550 ir ārpus pieņemamā. Ražošanas
kods nav mainīts; `workflow_v2.py` un vārti A2/B/C/D/F/H/T paliek kā bija.

---

## 12. Ēnu modelis un mēroga lēmums — gala spriedums

### 12.1 Kas tika izdarīts

1. **Ēnas modelis pārrakstīts uz apgaismojuma attiecību.** Papildu sliekšņa
   vietā katrs pikselis tiek salīdzināts ar **papīru, uz kura tas atrodas**:
   `ratio = L* / L* (tuvākais papīra pikselis)`. Josla 0.50–0.98 = ēnots
   papīrs; ārpus tās = audums. 0.50 ir fizikāla apakšējā robeža (iekštelpu
   metēna ēna uz balta papīra reti tumšāka par pusi no apgaismotās vērtības).
2. **Mērogs.** Tekstūra un ēnas dzīvo rupjākā mērogā nekā sensora grauds —
   pāreja uz 1/3–1/4 izšķirtspēju novērsa fragmentāciju (no 2891 komponentes
   uz 1).
3. **Gradienta vārti** pārbūvēti: blurēt L* **pirms** diferencēšanas.

### 12.2 Kāpēc ēnas modelis tomēr nedeva 0

Instrumentējot katru soli uz 160550 (mērogs 1/3):

```
pēc sasniedzamības:  bg=0.257  fg=0.743
fg ar ratio:  p5=0.49  p25=0.76  p50=0.96  p75=1.15  p95=1.47
  +near          127592
  +dC            107977
  +tex            40214
  +ratio>=0.5     40065
  +ratio<0.98     10831
  pēc atvēršanas   3516   (13 komponentes, lielākā 1959 < slieksnis 2795)
```

Ķēde ir loģiska un strādā — tā vienkārši **atrod ļoti maz**. Iemesls: īstā
ēna jau ir iekšā fona maskā kā "papīrs ar mazāku L*", jo `L_floor` tika
aprēķināts no papīra **10. procentiles mīnus 2**, kas uz šī attēla ir 46.4 —
zem ēnas, kas ir gaišāka par to. Savukārt 161944 gadījumā tumšās vietas ir
**paša papīra krokas**, nevis ēna.

### 12.3 Gala verdikts (vizuāli apstiprināts)

Lapa: `output/birefnet_test/PAPERBG_VERDICT.jpg`.

**160550** — augšējā mala ir tīra un precīza, bet **papīrs ir ķērpjains**:
fuksijas punkti izmētāti pa visu fona laukumu, un lieli laukumi nav paņemti.
Segums 0.746 pret patiesību ~0.62.

**161944** — **papīra krokas tiek uzskatītas par audumu**. Fuksija klāj tikai
daļu fona; krokainā tekstūra pārsniedz tekstūras slieksni. Segums 0.656 pret
patiesību ~0.30.

### 12.4 Lēmums

**Papīra-fona prototips tiek slēgts tāpat kā BG0.** Divi mēģinājumi to salabot
(mērogs + ēnas modelis) noveda pie tā, ka kļūda mainīja formu, nevis izzuda:
vispirms apēda apģērbu, tad paturēja ēnu, tagad ķērpo papīru un neņem krokas.
Katrs labojums ir atrisinājis vienu gadījumu un atvēris citu.

Cēlonis ir tas pats, ko jau pierakstīju 11.3: **bez modeļa, kas saprot
materiālu, "līdzīgs papīram" nav pietiekami.** Krāsas + tekstūras + gradienta
kombinācija nespēj atšķirt kroku papīrā no kroku audumā.

Ražošanas kods (`workflow_v2.py`, `checker_v2.py` vārti) nav mainīts.
`paper_leak.py` paliek darba telpā kā laboratorijas prototips ar skaidru
brīdinājumu virsrakstā. **Noplūdes zonde un GATE_L ir vienīgā daļa, kas
pierādīti strādā** (injekcijas tests 99.99 % / 0 px), un tā paliek spēkā.

---

## 13. 1. prioritāte izpildīta — iekšējā QA tagad paredz ārējos vārtus

### 13.1 Kas mainīts

`closeup_mask_qa(binary, orig)` (workflow_v2.py:367) ieguva trīs daļas:

1. **veselums** — kā līdz šim (segums 0.25–0.98, lielākā komponente ≥0.90,
   bbox ≥0.30);
2. **nepārklāts audums** — ārpus maskas palicis reģions, kas pēc tekstūras ir
   audums: `tex > max(p95(papīra tekstūra), 0.5)` un
   `(dC > 2.0 vai L < 0.70·L_papīra)`. Tekstūras reference nāk **tikai no
   papīrveidīgiem** rāmja pikseļiem, citādi apģērbs, kas pieskaras malai,
   piesārņo slieksni;
3. **malas** — tuvplānam audumam jāsasniedz ≥3 malas (tieši GATE_F noteikums).

### 13.2 Slieksnis atvasināts, ne izdomāts

| attēls | nepārklāts audums |
|---|---|
| paraugs 1 | 0.0087 |
| paraugs 2 | 0.0072 |
| paraugs 3 | 0.0200 |
| paraugs 4 | **0.5120** |

25× atstarpe starp labajām un bojāto masku → sliekmis **0.05**. Pirmā versija
ar 0.005 tika noraidīta, jo tā karodināja arī labās maskas.

### 13.3 Rezultāts uz 4 paraugiem (pilna darbplūsma)

| | pirms | pēc |
|---|---|---|
| maker pabeidza | 4/4 | **2/4** |
| čekeris PASS | 2/4 | **2/2** |
| klusi bojātas bildes iznākumā | **2** | **0** |
| atzīmētas `needs_seed_review` | 0 | **2** (ar priekšlikuma bildēm) |

Vienību testi **9/9** (jauns tests `test_closeup_qa_predicts_external_gates`,
kas pārbauda: 3 malas → pieņem, 1 mala → noraida, maska pusceļā → noraida).

### 13.4 Jauns atklājums par īsto cēloni

Mērījums apgāza manu sākotnējo vizuālo lasījumu:

- **Paraugs 3**: maska ir **laba** (nepārklāts audums tikai 0.0200, lielākā
  komponente 1.0). Tās problēma ir **kompozīcija** — tā sasniedz tikai 2 malas,
  tāpēc nav ne tīrs pilnuzņēmums, ne īsts full-bleed.
- **Paraugs 4**: maska ir **patiešām bojāta** — 0.5120 jeb 51 % kadra ir
  nepārklāts audums. GrabCut apstājās uz pusi.

Tas nozīmē, ka 2. prioritāte (tuvplānu prese) jāsadala: 3. paraugam vajag
**kompozīcijas** labojumu, 4. paraugam — **labāku sēklu**.

## 14. 3. prioritāte — atbilde par tukšo masku

- `cv2.grabCut` **ir determinisks**: trīs atkārtojumi ar vienu un to pašu
  `cfg` deva tieši 0.8278 (arī ar fiksētu RNG).
- Tātad agrākais 0.0000 nebija GrabCut nenoteiktība. Visticamākais cēlonis ir
  **bojāts faila nolasījums** tajā brīdī (`/var/tmp` tīrīšana darba laikā, ko
  vēlāk pierādīju). Tolaik `open_rgb` nelika `im.load()` un nelaboja kļūdu.
- **Jauns atradums:** GrabCut karājas (100 % CPU, >15 min) uz deģenerētiem
  vienkrāsainiem ievadiem. Ražošanā tas nav sasniedzams (sēklas nāk no īsta
  attēla), bet laboratorijas testos ar sintētiskiem ievadiem jāņem vērā.

---

## 15. Koriģēti skaitļi un gala stāvoklis

### 15.1 Divas manas kļūdas, kas atrastas un izlabotas

1. **`binary > 128` vietā jānormalizē.** `closeup_mask()` atgriež uint8 ar
   vērtībām **0/1**, nevis 0/255. Mans kritērijs `binary > 128` bija nepatiess
   visur — no tā nāca absurdais "0/4 malas" un "nepārklāts audums 0.91", kas
   matemātiski nav iespējams pie 87 % seguma. Labots uz `binary > 0`.
2. **Malu noteikums attiecas tikai uz tuvplāniem.** Pilns kadrs (segums < 0.60)
   pēc definīcijas nesasniedz malas, tāpēc tam šis kritērijs nav jēgpilns.
   Ieviests `is_closeup = coverage >= 0.60`.

### 15.2 Precīzie mērījumi (9/9 testi)

| attēls | segums | malas | nepārklāts audums | QA |
|---|---|---|---|---|
| 1 | 0.333 | 0 (pilns kadrs) | 0.0087 | PASS (malu rule neattiecas) |
| 2 | 0.335 | 0 (pilns kadrs) | 0.0072 | PASS |
| 3 | 0.830 | **2** | 0.0180 | REVIEW — 2/4 malas |
| 4 | 0.874 | 3 | **0.0558** | REVIEW — nepārklāts audums |

### 15.3 Otrs reāls labojums: tumšs audums kā "drošais fons"

`auto_closeup_seed_config`: `tex_bg_thr = max(42.0, ...)` un krāsu centri no
paša kadra nozīmēja, ka **tumšais ripšķūdis kļuva par savu krāsu centru** un
tika pieņemts par fonu. Uz parauga 4 tas apklāja pusi kadra (zilā zona
sēklu priekšlikumā klāj apģērba apakšējo pusi). Pievienots nosacījums
`L* >= 0.60 × L*_papīra`.

Rezultāts: paraugs 4 segums **0.4035 → 0.8736**. Tā ir lielākā vienreizējā
uzlabošanās šajā sērijā.

### 15.4 Gala stāvoklis uz 4 paraugiem

| | vērtība |
|---|---|
| maker pabeidza | 2/4 |
| čekeris PASS | **2/2** |
| klusi bojātas bildes izdotas | **0** |
| `needs_seed_review` ar priekšlikumu | 2 |
| vienību testi | **9/9** |
| vidējais laiks | 6.66 s/bilde |

Abi noraidījumi ir **pareizi un ar konkrētu iemeslu**:
- paraugs 3 — kompozīcija (2 malas; GATE_F to noraidītu);
- paraugs 4 — maska atstāj 5.6 % auduma (mala apakšā).

### 15.5 Kas palicis 2. prioritātē

- **Paraugs 3**: vajag kompozīcijas lēmumu (kura mala jāpievelk), nevis
  labāku masku — maska jau ir laba (0.0180).
- **Paraugs 4**: vajag sēklas/malas labojumu apakšā, kur ēna saplūst ar audumu.

---

## 16. Kur AI ir piesaistīts — un izšķirošais apmales tests

### 16.1 Pašreizējā arhitektūra (fakti no koda)

| slānis | kas to dara | kur |
|---|---|---|
| semantika (kas ir apģērbs) | **ISNet** (rembg, 178 MB ONNX) | viens izsaukums, 768×1024 proxy |
| maskas veselums | `ai_mask_qa` | prognozes rezultāts |
| fallback, ja AI noraidīts | GrabCut + k-means krāsu centri + `tex_bg_thr` | 4 sliekšņi, 42.0 cietais minimums |
| alfa mala | `refine_alpha`, `clean_mask` | klasiska |
| krāsa | deterministisks LUT | klasiska |
| fons, ēna, kompozīcija | deterministiska | klasiska |

**AI ir piesaistīts tieši vienā vietā** — un tikai kā varbūtību lauks. Viss
pārējais ir deterministisks. Tas ir pareizi.

### 16.2 Apmales tests: `ISNet` + papīra konteksts

``` 
attēls                     bez apmales  pad 0.80  pad 0.65  atsauce   labākais
slamjam_mfpen_trousers_3        0.0859    0.8256    0.8267   0.8278   pad 0.65  (+0.001)
slamjam_mfpen_trousers_4        0.0277    0.8985    0.9291   0.9298   pad 0.65  (+0.001)
MVIMG_20261020_160550           0.1849    0.8075    0.9996   0.6200   pad 1.00  (bez apmales)
MVIMG_20261020_161944           0.3172    0.5448    0.5449   0.3000   pad 1.00  (bez apmales)
MVIMG_20261020_161146           0.1639    0.2776    0.3831   0.7472   — (neizglābj)
slamjam_mfpen_trousers          0.3342    0.3352    0.3365   0.3327   pad 1.00  (bez apmales)
```

**Kas no tā izriet:**

1. **Apmale izlabo tieši tos divus attēlus, kuros pašreizējā darbplūsma
   sabrūk** — pilnbleed tuvplānus ar tumšu audumu: 0.0859 → **0.8256** un
   0.0277 → **0.9291**, ar kļūdu **+0.001** pret atsauci. Tas ir gandrīz ideāli.
2. **Apmale sabojā gaišu audumu uz gaiša papīra** (160550: 0.1849 → 0.8075
   pret patiesību 0.62; pie 0.65 pilnībā pārplūst līdz 0.9996). Iemesls
   fizikāls: ja audums un papīrs ir vienā gaišumā, apmale nedod kontrastu, bet
   dod modelim vairāk "priekšmeta" konteksta.
3. **Apmali nedrīkst lietot akli.** Tā jālieto kā **atkārtots mēģinājums tikai
   tad, ja pirmais gājiens deva fragmentu** (< 0.25 segums). Pārbaudīts:
   - paraugs 1 (0.3342) → nav fragmenta → bez apmales, paliek 0.3342 ✓
   - 161944 (0.3172) → nav fragmenta → bez apmales, paliek 0.3172 ✓
   - paraugs 3 (0.0859) → fragments → apmale → 0.8256 ✓
   - paraugs 4 (0.0277) → fragments → apmale → 0.9291 ✓
   - 160550 (0.1849) → fragments → apmale → 0.8075 ✗ (pārplūst)
   - 161146 (0.1639) → fragments → apmale → 0.3831 ✗ (joprojām fragments)

4/6 pareizi, un abi pārējie ir gaiša-auduma gadījumi, kur vajag citu zīmi.

### 16.3 Kļūda manā testā (pierakstīta apzināti)

Pirmā testa versija rādīja, ka pat tīrais paraugs 1 dod 0.0493, lai gan
darbplūsmā tas ir 0.3327. Iemesls: worker atgriež masku **proxy izmērā**
(768×1024), bet es to apgriezu pilna izmēra koordinātēs. **Tests, kas noliedz
zināmu labu gadījumu, ir bojāts tests — nevis atradums.** Salabots, un tikai
tad skaitļi kļuva lietojami.

## 17. Apmales retry ražošanā + divi atklāti gates caurumi (2026-10-22)

### 17.1 Kas tika izlabots, integrējot retry
| # | Simptoms | Īstais cēlonis | Labojums |
|---|---|---|---|
| 1 | Retry "noraidīts: fragments", lai gan laboratorijā 0.8256 | Retry masku (segums 0.83) vērtēja ar **pilna kadra** QA, kas pieprasa 0.15–0.65 | Retry validē ar `closeup_mask_qa` |
| 2 | `metode=isnet_pad_retry; segums=0.0000` | `clean_mask` saņēma 0/1 masku ar slieksni 128 | padod `(m*255)` |
| 3 | Print "GrabCut fallback" arī bez GrabCut | Nepareiza zara loģika | print tikai ja `"grabcut" in method` |
| 4 | `plan_closeup_crop` atrada logu 0.56× → 1.79× uzskalošana | Distance transform argmax uzkrita uz **kadra malas** (ārpus kadra netiek skaitīts) | 1 px nulles apmale pirms DT |
| 5 | Uzskalošana joprojām 1.79× | Meklēja tikai "pilnībā maskas iekšienē" logu | Kritērijs = tas pats, ko prasa GATE_F: ≥3 malas ≥50 % |
| 6 | **Redzama 199 px (8 %) gaiša josla augšā** uz s3/s4 | Mērķis maksimizēja tikai izmēru | Leksikogrāfisks mērķis: **vispirms 4 malas, tad izmērs** |
| 7 | 160550: 1141 px (30 %) josla | 4 malas tur nav iespējamas (apkakles loks) | Joslu apgriešana no joslas malas uz iekšu, kamēr <4 % |

### 17.2 Divi gates caurumi, ko atklāja kolāža
- **161944 izgāja visus gates, bet bija fragmentu tīkls.** Segums 0.3017 un lielākā komponente 1.0 to nenoķēra, jo maska bija viens savienots "tīkls" ar milzīgiem caurumiem.
  → Jauns kritērijs `silhouette_fill` = maskas laukums / bbox laukums. 161944 = **0.443**, visi pārējie 0.72–0.98. Slieksnis **0.60**. Ieviests gan `ai_mask_qa` (lai iedarbotos retry), gan GATE_C.
  → 161944 tagad iet retry: 0.5454, overflow 0.0, uncovered 0.0067 → pieņemts.
- **161146 izgāja ar 8819 px papīra maskā** (bēšs ķīlis pie labās malas, līdz x=3072, dziļums 40 px). GATE_L to redzēja, bet GATE_L pēc lēmuma ir tikai brīdinājums.
  → Jauna **GATE_P**: papīra reģions maskas iekšpusē, kas pieskaras kadra malai. Tas nav gaumes jautājums (atšķirībā no GATE_L), tāpēc bloķē.
  GATE_L paliek brīdinājums — lēmums nav mainīts.

### 17.3 GATE_D stūru noteikums
Vecais "stūris = BG vai ≥140" noraidīja **īstu vidēja toņa audumu** (115, 132) tuvplāna stūrī. Aizstāts ar maskas pārbaudi (BG krāsa VAI maska tur apstiprina audumu). Pēc tam 161944 krita uz **viena pikseļa** (1 px iecirtums) → stūrus vērtē kā 8×8 laukumu.

### 17.4 Auto-sēklu ceļš dzēsts
`auto_closeup_seed_config` + tā zars izņemti. Iemesls: tas bija otrais segmentācijas ceļš blakus ISNet, un uz 161146 tas iebāza maskā papīru. Tagad, ja ISNet un apmales retry abi noraidīti → `needs_review`, nevis otra modeļa maska.

### 17.4b Pad mērījums pēc aizsarga labojuma
`paper_like` bija tikai apakšējā robeža (`L >= L_floor`), tāpēc **balts trikotāža tika skaitīta kā papīrs**: 160550 maskā "papīrveidīgo" pikseļu krāsa bija (186,185,181), kamēr īstais papīrs ir (139,137,130). Pievienota augšējā robeža `L <= L_paper + 14`.

Pēc labojuma, pad 0.90 (aizstāj 0.80):
| bilde | cov | siluete | ovf | unc | lēmums |
|---|---|---|---|---|---|
| s1 | 0.3349 | 0.742 | 0.0000 | 0.0071 | (jau pieņemts bez retry) |
| s2 | 0.3381 | 0.746 | 0.0000 | 0.0052 | (jau pieņemts bez retry) |
| s3 | 0.8228 | 0.883 | 0.0000 | 0.0214 | pieņemts |
| s4 | 0.9135 | 0.958 | 0.0000 | 0.0002 | pieņemts |
| 160550 | 0.6209 | 0.795 | 0.0134 | 0.0026 | pieņemts (sk. 17.6 — defekta nav) |
| 161944 | 0.5452 | 0.721 | 0.0000 | 0.0068 | pieņemts |
| 161146 | 0.3310 | 0.574 | 0.0012 | 0.1382 | noraidīts |

### 17.6 160550 "papīra josla" — MANA KĻŪDA, defekta NAV
Sākumā ziņoju, ka 160550 iznākumam augšā ir papīra josla. Pārbaude to **neapstiprināja**:

- Papīrs bildes stūros ir (138,138,128) … (145,141,140) — L* ~56.
- "Josla" ir (172,172,170) … (179,176,171) — **gaišāka par papīru**. Ēna uz papīra nevar būt gaišāka par pašu papīru.
- Renderis ir godīgs: iznākuma (1500,20) = (172,172,170) un oriģināla atbilstošajā punktā (1989,1210) = (172,172,170).
- Godīgs tests — tas pats izgriezums no oriģināla, pārskalēts tieši uz 2000×2500: starpība >25 tikai **2.6 %** pikseļu (maskas iekšpusē 1.4 %), un tā ir LUT + ēna, nevis papīrs.

Kas notika: salīdzināju iznākuma augšējās 700 rindas ar oriģināla izgriezuma augšējiem 28 % — **dažādus laukumus**. Kolāžā redzamais "bloks" bija arī samazināšanas artefakts.

Secinājums: 160550 ir kārtībā, un ēnas atņemšana pie robežas tam **apēstu īstu audumu**. Gradienta modelis arī nav vajadzīgs — fona gradients ir tikai 6.5 L*, un defekta, ko tas risinātu, nav.

### 17.7 GATE_D stūru klauzula izņemta
Tā nespēja atšķirt ēnu, mīksto alfu un oriģinālo papīru: noraidīja īstu vidēja toņa audumu (115/132), pēc tam 1 px iecirtumu, pēc tam s3 ar 289 mīkstas malas pikseļiem. Fona tīrību sedz GATE_B (fons = BG, 100 %) un GATE_P (papīrs pie kadra malas). GATE_D paliek formātam.

**`closeup_mask` (GrabCut) vēl NAV dzēsts**: no tā atkarīgs 160550 caur `CLOSEUP_SEEDS` (gaišs audums uz gaiša papīra; apmales retry tur pārplūst 0.1391). Šis ir atvērts lēmums cilvēkam.

### 17.5 Rezultāts (7 bildes)
6/7 pabeigtas, 6/6 PASS, 161146 godīgi REFUSED. Vidēji **12.75 s/bilde**, maks. 19.25 s.

## 18. Otra modeļa pārbaude 122248 / 161146 (2026-10-22) — NAV IESPĒJAMA

Uzdevums: noskaidrot, vai cits atvērts modelis šīs divas bildes izdara tīri.

| modelis | izmērs | rezultāts |
|---|---|---|
| `bria-rmbg` (RMBG-1.4, rembg 2.0.85) | 1.02 GB | process nomirst sesijas ielādē |
| `u2net_cloth_seg` | ~50 MB | sesija ielādējas, **inference OOM (exit 137)** |
| `birefnet-general-lite` | — | iepriekš jau konstatēts OOM 1024 |

Iemesls: sandbox RAM 1982 MB, brīvi ~1505 MB, bez swap. 1 GB modeļa svari + inference tur neietilpst.

**Secinājums: otrs modelis šajā vidē nav izpildāms.** Tas nav pieņēmums — divi mēģinājumi, abi beidzās ar SIGKILL.

Praktiskās paliekas šīm divām bildēm:
1. Atteikt abas (komplekts 5 bildes).
2. Atļaut izņēmumu GrabCut ceļam (`closeup_mask`) — tam šobrīd **nav** sēklu 122248 un 161146 kodu (`CLOSEUP_SEEDS` = 160550, 160601, 160608, 160645, 161944, 161959, 162013, 162101), tāpēc tas prasītu rakstīt jaunu sēklu.
3. Pārstrādāt bildes ar citu uzņemšanas fonu.

## 19. Loop dzinējs (`loop_engine.py`) — 2026-10-22

Līdz šim loopu dzina cilvēks: maker → checker → apskate → nākamais mēģinājums. Tas strādāja, bet nebija atkārtojams — lēmumi palika čatā. Tagad to dara dzinējs.

**Princips paliek:** AI ierosina, mērījums spriež. Neviens remēdijs nevar pieņemt sevi; katrs mēģinājums iet caur tiem pašiem gates.

**Trīs fāzes:** (1) bāzes brauciens, (2) remēdiju bibliotēka ar priekšnosacījumiem un budžetu, (3) gala brauciens ar VIENU globālo LUT (remēdiju eksperimenti krāsu neietekmē).

**Remēdiju bibliotēka tagad:**
| remēdija | kad piemērojama | priekšnosacījums |
|---|---|---|
| `pad_forced_090` | maskas gate krīt, bet ISNet maska tika pieņemta | jābūt uzticamam papīra fonam |
| `pad_alt_085` | 0.90 jau izmēģināts, gate joprojām krīt | — |

**Divi defekti, ko dzinējs pats sev atklāja:**
1. Maker atgriež 2 arī pie **godīga atteikuma** — pirmā versija to uzskatīja par avāriju un apstājās.
2. **Atteiktam attēlam nav neviena gate**, un pirmā versija to skaitīja kā PASS (`nav kritušu gate` ≠ `izturēja`). Tagad par PASS lemj tikai `ALL_PASS is True`. Paštests to nofiksē.

**Pirmais brauciens (8 bildes, 287.3 s):** 6/8 PASS, 2 eskalācijas.
- `IMG_20261015_122248` — GATE_P, 4 reģioni, 105 544 px, dziļums 789.9 px. Remēdija `pad_forced_090` nevarēja sākties: *"apmales retry izlaists: kadrā nav uzticama papīra fona"*.
- `MVIMG_20261020_161146` — atteikts, remēdiju priekšnosacījumi neizpildījās.

Eskalāciju lapa top no trace un ir pārbūvējama ar `--rebuild`, bez jauna brauciena.

## 20. Jauns komplekts: zila jaka + balts krekls (2026-10-22)

Divas bildes no vienas sesijas: `IMG_20261015_121740` (jaka uz koka grīdas) un
`MVIMG_20261020_160550` (balts krekls uz papīra). Dzinējs: 2/2 PASS, 80 s.

### 20.1 Krāsu defekts, ko neviens gate nenoķēra
Pirmais brauciens abām bildēm atdeva audumu **par ~4.6 b\* aukstāku**:
jaka −4.87, krekls −4.49. Iemesls: baltā bilance rēķinājās no **koka grīdas**
(brūns etalons), un viens globālais LUT pārnāca uz abām bildēm.

Labojumi:
1. **Fona uzticamība:** `bg_chroma = (max-min)/mean` fona lineārajā RGB. Ja > 0.18, WB kļūst neitrāla. Šodien: 121740 → neticams (L\* 31.5, hroma 16.1), 160550 → ticams (hroma 4.7).
2. **GATE_K (bloķējošs):** auduma b\* nobīde pret oriģinālu, limits ±2.5. Pirms: −4.49. Pēc: **−1.59 un +0.20**.

Kāpēc to nenoķēra esošie gates: GATE_A2 pārbauda **klipingu**, ne toni;
GATE_B — fona krāsu; GATE_C/H/P — masku. Krāsu ticamība nebija nevienā gate.

### 20.2 121740 paliek pilns kadrs
Maska tīra (silhouette 0.667, fons 100 %), bet jaka aizpilda 0.540 kadra, un
ap 30 % malās ir fons. Full-bleed nav iespējams, tāpēc centrēts pilns kadrs,
GATE_F izslēgts ar iemeslu (nevis ar klusumu).

## 21. Viena bilde: balts vafeles krekls, graudains kartons (2026-10-22)

`PXL_20261022_124322251.PORTRAIT.ORIGINAL.jpg`, 4080×3072 (guļus), 3.7 MB.

### 21.1 Divi klusi defekti, ko atklāja šī bilde
1. **Rotācija tika ignorēta.** `parse_rotations` grieza atslēgu ar `os.path.splitext`, kas noņem tikai pēdējo paplašinājumu, tāpēc `X.PORTRAIT.ORIGINAL.jpg` kļuva par `X.PORTRAIT`, bet `rotation_for` meklēja `X.PORTRAIT.ORIGINAL`. Rezultāts: bilde palika guļus, un **neviens gate to nenoķēra**, jo maska, fons un formāts bija kārtībā. Labots; tests `test_rotation_key_with_multiple_dots`.
2. **GATE_K klusi izslēdzās.** Maker glabā `source_size` PĒC rotācijas, bet gate vēlreiz apmainīja asis, saņēma `box can't exceed original image size` un atgrieza `pass: None` ar kļūdu. Gates, kas krīt ar izņēmumu, nav gates. Labots.

### 21.2 Graudains kartons pret gludu fotopapīru
`measure_paper_colour` noraidīja fonu kā "nav papīra": tekstūra **1.61**, slieksnis **1.0**. Tas ir kalibrēts uz gludu fotopapīru; kartons ir lietojams fons.

Risinājums nav sliekšņa klusa maiņa, bet **parametrs ar ierakstu**:
- `measure_paper_colour(img, tex_limit=1.0)` — noklusējums nemainīts.
- `paper_profile(img, tex_limit=...)` — apmales retry vispirms mēģina strikto, tad `PAD_TEX_RELAXED = 2.5`.
- Atskaitē parādās `profile_relaxed: true`.

Rezultāts ar pad 0.90 un paplašinātu robežu: segums 0.7662, pārplūde **0.0009**, nepārklāts **0.0003** — aizsargi palika tie paši un izlēma.

### 21.3 Rezultāts
`ALL_PASS = True`, 17.05 s. Segums 0.7692, siluete 0.9568, **4 malas 1.0/1.0/1.0/1.0**, b\* nobīde −0.91, GATE_P 0 reģioni, GATE_L PASS.

Salīdzinājums ar to pašu izgriezumu no oriģināla: vidējā atšķirība 13.3, >25 tikai 5.6 % un **vienmērīgi pa visu lauku** (3.5–5.6 % katrā malā) — tas ir LUT + asināšana, ne lokāls defekts.

### 21.4 Laiks
17.1 s pie 20 s mērķa. Iemesls: retry (13.6 s maska) + render. Bāzē bez retry tas būtu ~10 s, bet ISNet šai bildei atdeva fragmentu (segums 0.0446).

## 22. Ātrums: 17.05 s -> ~10-12.8 s, maska bitu identiska (2026-10-22)

Mērķis bija "ātrāk par 20 s" **nezaudējot nevienu vārtu**. Katra izmaiņa tika
pieņemta tikai tad, ja pilns dzinējs deva `ALL_PASS=True` un vārtu vērtības
palika tieši tās pašas (segums 0.7679, silhouette 0.9551, GATE_K −0.91,
`closeup_crop` 0.054/0.256/0.819/0.976).

**Kas tika atrasts mērot (nevis minot):**

| atradums | cena | risinājums |
|---|---|---|
| `from rembg import new_session, remove` | **2.3–2.4 s** katrā apakšprocesā | `isnet_native.py`: tas pats ONNX tieši uz onnxruntime (imports 0.03 s) |
| divi apakšprocesi (bāze + apmales retry) | imports maksāts DIVREIZ | viens workers, viens imports |
| otra inference tajā pašā procesā | `SIGKILL` pie 1215 MB | `enable_cpu_mem_arena=False` → 611 MB, maska bitu identiska |
| `closeup_mask_qa` mērīja papīru vēlreiz | 1.07 s → 0.68 s | viens `measure_paper_colour`, padots abiem |
| `paper_profile(tex_limit=2.5)` otrs pilns skenējums | 0.73 s | `tex_limit` maina tikai lēmumu, nevis mērījumu → atvasina no pirmā |
| master PNG `compress_level=3` | 1.64 s (līmenis 6: 5.46 s) | `--png-level 1` = 1.18 s, bez zudumiem |
| pilna izmēra pad maskas PNG | 0.60 s | raksta iekšējā loga izmērā |

**Kāpēc tas nav kvalitātes kompromiss:**

1. Arēnas izslēgšana: maska **bitu identiska** (maks. atšķirība 0, 0 atšķirīgu px).
2. `isnet_native` pret `rembg`: **bitu identiska** abos ievados (proxy 783 360 px,
   pad 589 824 px; maks.diff 0). Pārbauda `test_isnet_parity.py`.
3. Papīra atvasināšana: `atšķirīgās atslēgas: nav — BITU EKVIVALENTS`.
4. PNG ir bezzudumu formāts pie jebkura līmeņa — mainās tikai faila izmērs.
5. Pad audekls vairs netiek saspiests JPEG q95: vecais ceļš masku **piepūta**
   (0.7662 pret 0.7584), jo JPEG artefakti uz vienkārša fona izskatās pēc auduma.

**Mērījumu disciplīna.** Šai mašīnai ir 2 kodoli un mainīga blakus slodze, tāpēc
ISNet inference lēkā **1.6–3.0 s** un kopējais laiks ar to. Absolūtos skaitļus
drīkst salīdzināt tikai vienā laika logā; stabilas ir komponentes, nevis summa.
Tāpēc visi ieguvumi iepriekšējā tabulā ir mērīti kā atsevišķi komponenti.

Rezultāts: 17.05 s -> **12.80 s** tajā pašā logā, kur iepriekšējais builds deva
13.27–13.79 s; uz klusas mašīnas (inference 1.6 s) ~10 s. Vārti nemainījās.

## 23. Atteikums: balts vafeles adījums uz pelēka kartona (2026-10-23)

Bilde `PXL_20261022_124339475.PORTRAIT.ORIGINAL` (4080×3072 gulēja, rotācija 270).
Dzinējs **atteica** — tā ir pareizā atbilde, nevis kļūda, ko slēpt.

**Mērījumi (visi uz rotētā attēla):**

| mērījums | vērtība |
|---|---|
| bāzes ISNet maska | segums **0.0311**, `silhouette_fill` 1.1076, `accept=False` |
| apmales retry, pad 0.70–0.95 | overflow **0.0276–0.0346** pret limitu 0.02 → visi noraidīti |
| papīra profils | lab `[67.85, 0.55, −0.39]`, tex **1.565** → `plausible=False`, tikai `relaxed` ceļš |
| papīra rgb (relaxed) | `[166, 165, 166]` — tas ir **krekls**; fons ir `[117, 115, 115]` |
| izšķirtspēja 1024 / 1536 | segums 0.0259 / 0.0261 — nav izšķirtspējas problēma |
| izplūdināšana 3 / 5 / 8 px | segums 0.0810 / 0.0092 / 0.0028 — nav trokšņa problēma |
| tekstūras slieksnis tex>1.0 | segums **1.0000** — fons ir tikpat teksturēts kā krekls |
| augstfrekvences enerģija e>2.0 | segums **1.0000** — nenošķir arī tas |

**Diagnoze.** ISNet (saliency modelis) balto vafeles adījumu neuzskata par objektu:
tas saķer tikai **gludos** aproču gabalus un tievu slāni malā — skat.
`output/FAIL_124339475.png`. Divi papīra krāsas režīmi (`bright` 166 / `dark` 117)
sakrīt ar krekls / fons, un tekstūras mērītājs kā \"papīri\" izvēlas **kreklu**,
tāpēc `pad_guards` overflow ceļā visu laiku lec pāri limitam.

**Secinājums.** Šī bilde ir **ārpus ISNet sadalījuma**: pilnkadra trikotāža bez
atpazīstamas \"drēbes\" silueta, ar fona/krekla toni 1–2 % attālumā. Neviens
likumīgais ievades variants (izšķirtspēja, izplūdināšana, pad) to nelabo.

**Kas netika darīts un kāpēc:** vārti netika vājināti; maska netika zīmēta ar
roku; `profile_relaxed` netika pagarināts, lai \"papīrs\" būtu krekls; nekas
netika pārkrāsots. Visi šie soļi dotu bildi, kuru nevar aizstāvēt.

**Blakusatklājums (salabots):** `loop_engine.load_reports()` krita ar
`FileNotFoundError`, kad maker atteica VISU bildi un checkeris netika palaists.
Tagad tas izdrukā paskaidrojumu un dod `0/1 PASS, 1 eskalācija`.

## 24. Virsmas tekstūras ceļš (`plate_texture`) — bilde, ko ISNet neredz (2026-10-23)

`PXL_20261022_124339475` (balts vafeles krekls uz gaiši pelēka kartona, 4080×3072
gulēja, rotācija 270). ISNet atteicās (§23). Atteikums **netika pieņemts kā gala
atbilde**, jo bilde satur spēcīgāku signālu par semantiku.

**Kas tika atrasts mērot.** Fons un krekls atšķiras pēc *virsmas reljefa*, nevis
pēc krāsas (krāsa: 166 pret 117, abi gaiši; tekstūra: atstarpe 4.5×):

| mērījums (pusizmērs, L*) | kartons | vafeles adījums |
|---|---|---|
| lokālais std, logs 25 px | **2.8** | **12.8** |
| lokālais std, logs 13 px | — | — |
| Gabor λ=16–24 px | 77–135 | 207–975 |
| Otsu slieksnis | \multicolumn — | **7.6**, tieši starp abiem |

Kritiska detaļa: **pilnā izšķirtspējā atstarpe pazūd** (kartona grauds 5.0 pret
adījumu 5.0), jo grauds ir nesakorelēts un sīks. Pusizmēra LANCZOS samazināšana
nesakorelēto graudu noslāpē, bet korelēto adījumu ne. Tāpēc detektors strādā
**pusizmērā** — tas nav kompromiss, tas ir mērījuma nosacījums.

**Kā maska tiek iegūta** (`plate_segment.py`):
1. `_detect` — Otsu uz lokālā std, morfoloģija, lielākā komponente.
2. `_keep_garment` — fons = komponenti, kas pieskaras kadra malai. Tāpēc īstie
   robi starp piedurkni un kleitu paliek robi, bet aproces iekšpuse paliek krekls.
3. `_smooth_mask` — ārējo kontūru izlīdzina (RETR_CCOMP: caurumi netiek aizpildīti).
4. `EDGE_CALIB_PX = 2` — maska paplašināta par 2 px pusizmērā. Iemesls: 25 px
   logs izplūdina tekstūru pāri malai, un Otsu nogriež to, kur tekstūra jau pusē;
   mērītā nobīde −2.3 px mediāna. +2 px vizuāli atgriež auduma tumšo malu un
   neko nesašaurina; +3 jau zīmē malu biezāku, nekā tā ir.

**QA (mērīts, nevis acs)** — visi četri iztur ar lielu rezervi:

| metrika | vērtība | limits |
|---|---|---|
| segums | 0.7011 | 0.25–0.95 |
| iekšmalas tekstūra / iekšpuse | **0.655** | > 0.50 (augsts = iekšā nav fona) |
| ārējās malas tekstūra / iekšpuse | **0.365** | < 0.60 (zems = ārā nav auduma) |
| fons maskas iekšpusē | **0.007** | < 0.02 |

Audits atsevišķi: 11 slēgti zema-tekstūras apgabali maskas iekšpusē — apskatīti,
tie **visi ir aproču iekšpuse** (gluds trikotāžas audums), t.i. maska tur ir
pareiza, nevis caurums.

**Rezultāts:** `plate_texture`, segums 0.7002, `silhouette_fill` 0.7508,
GATE_F 0.888/1.0/0.952/0.919, GATE_K −0.68, **ALL_PASS=True**, 13.64 s,
1/1 PASS, 0 eskalācijas.

**Kas netika darīts:** ISNet ceļš nav mainīts (plate ir tikai trešais ceļš pēc
`isnet` un `isnet_pad_retry`); vārti nav vājināti; `GATE_L` šai bildei paliek
`advisory` ar `marginal` — tā ir godīga atzīme, papīra references šeit sakrīt ar
kreklu, tāpēc noplūdes tests nav nošķirams un tā vietu ieņem plate QA.

## 25. Divi viltus caurumi, kadrējuma politika un GATE_F pārformulējums (2026-10-23)

Lietotājs atzīmēja divus defektus uz izvades: plānus baltus "spraugus" un to,
ka kadrs ir pārāk ciets salīdzinājumā ar Slam Jam referencēm.

### 25.1 Viltus caurumi — mērītais cēlonis

Oriģinālā abās vietās ir **nepārtraukts audums**; maskā tur bija caurums.

| viltus caurums | L* | tekstūra | īstais papīrs |
|---|---|---|---|
| 7345 px @ y1367 | **19.9** | zema | L* 66.8 |
| 5553 px @ y973 | **79.2** | zema | L* 66.8 |

Abi ir **gludi**, tāpēc tekstūras detektors tos sauca par fonu: pirmais ir ēnas
kroka (42 L* zem papīra), otrais gaismas atspīdums (17 L* virs). Risinājums nav
sliekšņa grozīšana, bet **otrs nosacījums**: fona komponente drīkst būt arī
*tikai papīram līdzīga* (`L_TOL = (-14, +8)` L* ap papīra līmeni).

Kalibrācija mērīta, ne izvēlēta: −18 → viltus caurums paliek; **−14 → pazūd,
īstais fons malā paliek 99.5 %**; −12 → tas pats ar mazāku rezervi; −10 → fons
pārstāj atpazīties pavisam (segums 1.0). Rezerve abos virzienos 4 L*.

### 25.2 Kadrējums — kāpēc tas bija par ciešu

Mērīts uz referencēm: Slam Jam **kopskati** — fons 64 %, apģērbs 60 % platuma ×
79 % augstuma, malu pieskāriens 0/0/0/0. Slam Jam **tuvplāni** — fons 7–10 %,
apģērbs pāri 2–3 malām. Mūsu iepriekšējais full-bleed: fons **1.4 %**, pāri
visām 4 malām. Tas nav "nedaudz par tuvu" — tas ir cits žanrs.

**Politika tagad** (`--framing auto`, noklusējums): ja siluets ir **slēgts**,
krekls tiek novietots uz fona ar malām (`GARMENT_FILL_W/H = 0.74/0.78`). Ja
siluets jau karājas pāri kadra malai, kadrs tiek atstāts **tāds, kā
nofotografēts** — jo novietošana tādu kreklu nogrieztu pa taisnu līniju
(pārbaudīts: iznāca ielīmēts taisnstūris). Šai bildei: fons **28.8 %**.

Piezīme par robežu: šis avots ir īsts kadrs no kreklam pāri, tāpēc pilnu
"Slam Jam kopskatu" ar kreklu ap visām malām no tā iegūt nevar — tas
jāfotografē no tālāk. Tas ir avota, ne apstrādes ierobežojums.

### 25.3 GATE_F pārformulēts (lūgts apzināti, ar pierādījumu)

Vecais noteikums "kreklam jāsasniedz >=3 malas" **piespieda** full-bleed un tā
izslēdza produkta kadru, ko lietotājs prasīja. Tas bija vārtu mērķa kļūda: tiem
jāsargā **taisns grieziens cauri apģērbam**, nevis konkrēts kadrs.

Jaunais noteikums — katra mala tiek klasificēta:

| klase | nozīme |
|---|---|
| `margin` | tīrs fons ar >= 5 % atstarpi |
| `bleed` | krekls iet pāri malai, un **oriģinālā arī gāja** (mantots) |
| `cut` | krekls pieskaras, bet oriģinālā tur bija fons (izgudrots grieziens) |

`GATE_F` iztur, ja nav neviena `cut` un ir vismaz viens `bleed` vai visas 4 ir
`margin`. Pārbaudīts arī uz iepriekšējās bildes loģikas: taisnais grieziens,
kas rodas novietojot atvērtu siluetu, dod `cut` un **netiek pieņemts**.

### 25.4 Rezultāts

`plate_texture`, segums 0.7116, fons 28.8 %, viltus caurumi 0, **ALL_PASS=True**,
13.17 s, 1/1 PASS. Determinsms pārbaudīts: divi skrējieni dod **bitu identiskus**
SHA-256 maskai, novietotajai maskai un paraugam. Testi 11/11.

## 26. Metēnā ēna kā "krekla turpinājums" — mērījumi un divi atcelti mēģinājumi (2026-10-23)

Lietotājs norādīja: piedurknes labajā malā palikusi pelēka josla, kas lasās kā
krekls. Tā **nav** renderēšanas alfa — mērīts izvadē: alfa tur ir 255 (pilna
necaurredzamība), t.i. maskā ir oriģinālais papīrs ar ēnu.

### 26.1 Divi mēģinājumi, kas tika atcelti

| mēģinājums | kāpēc atcelts |
|---|---|
| **Gradienta/līmeņa robežas precizējums** (`_refine_edge`, E krustpunkts) | pārbīda robežu uz ēnas->papīra pāreju un **apgrauž kontūru**: auduma E loga malā nokrītas, tāpēc kritērijs nogriež īstu audumu. Perimetrs/sqrt(area) uzlēca, mala kļuva robotaina. |
| **Aklā dilatācija +2 px** (`EDGE_CALIB_PX`, ieviesta §24) | tā **pastiprināja** tieši šo defektu. Kalibrēta pēc acs uz 4 izgriezumiem, un tas, ko tur redzēju kā "auduma malu", lielākoties bija ēna. Tagad `EDGE_CALIB_PX = 0`. |

### 26.2 Kas nostrādāja

`_trim_shadow`: maskas malas joslā (±40 px pusizmērā) noņem tos pikseļus, kas
ir **bez tekstūras UN tumšāki par papīru** — tā ir ēnas definīcija, un audums
nekad nav abi uzreiz (audumam vienmēr ir vafeļu reljefs, E25 ≈ 12, ēnai ≈ 2).

Pēc tam `SHADOW_TRIM_PX = 3` (pusizmērā = 6 px pilnā): atlikušo mīksto ēnas
malu nogriež kā fonu. **Pamatojums mērīts, ne izvēlēts:** 98 % kontūras īstais
audums sākas ≤ 4 px no malas (p50 = 0, p75 = 3, p90 = 4), tāpēc 3 px nogriež
ēnu, nevis audumu. Alfa pēc tam tiek izplūdināta, tāpēc mala paliek mīksta,
nevis cieta — kā Slam Jam referencēs.

Mērījums pirms/pēc: segums 0.7098 -> 0.7058 (zudums 0.4 %, tas ir ēna).
Globālais audits: tikai 2 % kontūras punktu bija platāki par 12 px, un tie
galvenokārt bija augšmalā — tāpēc defekts bija lokāls, ne sistēmisks.

### 26.3 Rezultāts

**ALL_PASS=True**, segums 0.7058, 13.23 s, 1/1 PASS, 0 eskalācijas.
Determinsms: divi skrējieni dod bitu identiskus SHA-256. Testi 11/11.

## 27. Kadrējums kā lietotāja IZVĒLE: `--framing slamjam|original` (2026-10-23)

Lietotājs: „tai vajadzētu būt kā opcija, lai es varētu izvēlēties slamjam vai
oriģinālos". Ieviests abos slāņos — `workflow_v2.py` un `loop_engine.py`.

| režīms | ko dara |
|---|---|
| `slamjam` | produkta kadrs: krekls pilnībā kadrā, aizpildījums 0.74 × 0.78, fons ap visām malām |
| `original` | kadrs kā nofotografēts: krekls iet pāri malai, īstais fona laukums paliek |
| `auto` (noklusējums) | `slamjam`, ja siluets slēgts; citādi `original` |

### 27.1 Godīgais ierobežojums, kas tiek ziņots, nevis slēpts

`slamjam` prasa, lai krekls **avotā** būtu pilnībā kadrā. Ja maska karājas pāri
malai, trūkstošo audumu nevar izdomāt — tas būtu ģeneratīvs piepildījums, kas
šajā projektā ir aizliegts. Tāpēc šādā gadījumā tiek atgriezts `original`, bet
atskatē (`framing.requested`, `.chosen`, `.slamjam_possible`, `.rule`) un
konsolē ir ierakstīts, ka un kāpēc.

### 27.2 Kā pārbaudīts, ka `slamjam` tiešām strādā

Uz `PXL_20261022_124339475` tas nav izpildāms (krekls jau iet pāri 2 malām), tāpēc
pārbaudīts uz īstas bildes ar slēgtu siluetu — `slamjam_mfpen_trousers.jpg`:

| | rezultāts |
|---|---|
| izvēlēts | `slamjam` (`slamjam_possible: True`) |
| fons | **65.9 %** (referencei 64.3 %) |
| malu pieskāriens | 0.00 / 0.00 / 0.00 / 0.00 |

Vizuāli salīdzināts ar oriģinālo Slam Jam kadru — kompozīcija sakrīt.

Mēģinājums pārbaudīt ar sintētisku bildi (krekls ielīmēts uz lielāka papīra
audekla) **neizdevās un tas ir pareizi**: ielīmētais krekls joprojām ir nogriezts,
tāpēc siluets palika atvērts un `slamjam` netika izpildīts. Tas apstiprina, ka
pārbaude nevis apstiprina jebko, bet tiešām mēra nosacījumu.

### 27.3 Statuss

Uz `PXL_20261022_124339475`: abi režīmi dod `original` (fons 27.9 %, 2 malas),
`ALL_PASS=True`, 1/1 PASS, 0 eskalācijas, 13.2 s. Testi 11/11.

---

## 28. Ēnas virziens — profesionālās prakses audits (2026-10-23)

### 28.1 Kas tika audēts

Pirms visas sistēmas debuga: kā fona maiņu dara Nuke compositing, Photoshop produktu retuša un ghost-mannequin studijas. 6 meklējumu kārtas, 12 tehnikas, katra pārbaudīta ar mērījumu uz mūsu pašas bildes. Pilns audits: `PROFESIONALAS_METODES.md`.

### 28.2 Atrastais defekts

Ēna krita **54°** virzienā (lejup-pa labi), bet bilde ir apgaismota no **~315°** (augšā-pa labi), t.i. ēnai jākrīt uz **120–135°** (lejup-pa kreisi). Kļūda **~70°**: ēna krita tajā pašā pusē, no kuras nāk gaisma. Ghost-mannequin literatūra to sauc par *"divām saulēm"* — ainu, ko cilvēks nevar artikulēt, bet smadzenes reģistrē kā nepareizu.

### 28.3 Kā tas tika izmērīts (4 metodes)

1. Virziena skenējums no kontūras → 135° (piesārņots ar papīra gradientu)
2. Apģērba četrstūru tests → gaišāk pa labi un augšā
3. Lokālais kontrasts L(10px)−L(45px) → 105–120°
4. **Fona plāksne ar inpaint** (IBK principa būtība) → 135°, reziduāla std 2.69 L*

Metodes #1–#3 sajauca ēnu ar papīra gradientu (fons 133 tālu pret 156–160 tuvu). #4 to atrisina, aizpildot apģērbu no apkārtējā papīra un atņemot iegūto virsmu.

**Vizuālais apstiprinājums:** oriģinālā pie apģērba *labās* malas papīrs ir vienmērīgs, ēnas nav; gar *apakšējo* malu ir plata mīksta ēna. Mērījums un acs saskan.

### 28.4 Labojums

```python
SHADOW_ANGLE_DEG = 125.0     # bija (dx=+25, dy=+35) = 54°
SHADOW_STRENGTH  = 0.26
def shadow_dir(dist_px): ...  # saglabā |d|, maina tikai leņķi
# avota mērogā shadow_dir(43.01) -> (-25, +35); audeklā shadow_dir(25.62) -> (-15, +21)
```

Trīs cieto skaitļu kopijas (`loop.py:408`, `loop.py:496`, `workflow_v2.py:1155`) konsolidētas vienā konstantē. Iepriekš abi pāri — `(25,35)` avota un `(16,20)` audekla mērogā — bija **tā pati ēna divos mērogos**, tāpēc leņķis tagad ir viena konstante un mērogi nevar atšķirties.

### 28.5 Pārbaude

| pārbaude | rezultāts |
|---|---|
| apģērba kodolā mainīts | **0.00 %** |
| fonā >120 px no malas | **0.0 %** |
| fonā <90 px (ēnas zona) | 39.9 % — gaidīts |
| maska | `744890376d…` / `48a207ed4d…` — **nemainīta** |
| determinisms (2 palaidieni) | `663179f3…` bitu identisks |
| testi | 11/11 OK |
| laiks | 13.9–14.0 s |

### 28.6 Zināmais blakusefekts

Apģērbs ir pieskarts kadra **kreisajai** malai, tāpēc ēna 125° virzienā daļēji aiziet aiz kadra: redzamās ēnas laukums 110 842 → ~50 857 px. Tas ir fiziski godīgi (tāpat notiek oriģinālā), bet šai bildei ēna vairs nav tik izteikta. Ja tas traucē, risinājums ir **nevis** atgriezties pie 54°, bet gan:

- samazināt ēnas nobīdi un palielināt kontūras piegulumu (AO josla + neliela virziena nobīde), vai
- izvēlēties kadrējumu ar lielāku kreiso malu.

### 28.7 Latentā kļūda, kas atrasta ceļā (debugam)

`workflow_v2.py --rerender-saved` bez `--rotate` salauž renderēšanu: `ROTATIONS_CW` ir tukšs pēc noklusējuma, un `open_rgb()` atgriež **nepagriezto** attēlu, kamēr saglabātā maska ir **pagrieztā** izmērā → `ValueError: Maskas izmērs (4080, 3072) nesakrīt ar (4080, 3072)`. Ziņojums izskatās muļķīgi, jo `binary.shape` ir (H,W) un `orig.size` ir (W,H).

Turklāt `--rerender-saved` **pārrēķina krāsu profilu** un deva citādu grade (apģērba vidējais 154.66 pret 158.94 pilnajā caurulē) — tāpēc tas nav līdzvērtīgs ceļš akceptētā rezultāta atkārtošanai.

Īstais labojums: `render_one` jāizmanto `rec["rotation_cw"]`, nevis globālais `ROTATIONS_CW`.

---

## 29. GATE_R un rotācijas labojums (2026-10-23)

### 29.1 Kāpēc GATE_R vajadzēja

Debugā atklājās, ka **neviena gāte nesaturiski nepārbauda piegādāto JPEG**.
Gātes lasa master (A2, B), masku (C, H) un novietoto masku (F); paraugu skata
tikai GATE_D (izmērs) un GATE_K (viens skalārs b\*). Sešas apzinātas sabotāžas
tikai piegādātajā failā izgāja ar `ALL_PASS=True`.

Tas nav teorētisks risks: **tieši tā izgāja ēnas virziena defekts** (§28).
`master` un `paraugs` ir divi atsevišķi renderēšanas ceļi, un ēna, novietošana
un samazināšana dzīvo tikai otrajā.

### 29.2 Ko GATE_R dara

Atkārto **tikai `render_paraugs` ģeometriju** uz MASTER, nevis visu renderi.
Pamatprincips: ēna jau ir masterī, tāpēc abiem attēliem jānāk no viena avota —
salīdzinājums ir godīgs bez atkārtotas renderēšanas.

Trīs neatkarīgi lielumi:

| lielums | slieksnis | bāze | mazākā sabotāža | likumīgā variācija |
|---|---|---|---|---|
| `fore_p99` | ≤ 24.0 | 16.0 | 33.0 | 16–20 (JPEG q80–95) |
| `bg_p99` | ≤ 4.0 | 1.0 | 27.0 | — |
| `edge_ratio` | 0.80–1.85 | 1.381 | 0.044 (blur) | 1.38–1.49 |

Sliekšņi ir **viduspunkti starp izmērīto likumīgo un izmērīto defektu**, nevis
izvēlēti. Tas pats princips kā `L_TOL`: konstante jāizriet no mērījuma.

### 29.3 Rezultāts

`python3 test_gate_r.py` — 7/7 OK. Regresijas tests paliek darbvietā.

| sabotāža | pirms GATE_R | ar GATE_R |
|---|---|---|
| bāze | PASS | PASS |
| izgudrots taisnstūris fonā | PASS | **FAIL** (p99 33, bg 72) |
| apģērbs izdzēsts | PASS | **FAIL** (p99 159) |
| izpludināts 6 px | PASS | **FAIL** (p99 67, edge 0.044) |
| nobīdīts par 40 px | PASS | **FAIL** (p99 146, bg 108) |
| iekrāsošs R+10% B−10% | PASS | **FAIL** (p99 33, bg 27) |
| troksnis σ=12 | PASS | **FAIL** (p99 34, edge 2.221) |

### 29.4 Rotācija

`open_rgb_recorded(path, rotation_cw)` — ieraksts ir patiesais avots; globālais
`ROTATIONS_CW` paliek tikai būvēšanas laikam. Aizstāts 3 vietās
(`render_one`, krāsu profils, maskas ģenerēšana).

Pirms: `--rerender-saved` bez `--rotate` → `ValueError: Maskas izmērs
(4080, 3072) nesakrīt ar (4080, 3072)` (abi skaitļi vienādi, jo `(H,W)` pret
`(W,H)`), un maskas ceļš varēja **klusi** pārsegmentēt nepareizā orientācijā.
Pēc: bitu identisks `663179f3…`.

### 29.5 Atklātais, kas jāpieraksta

- GATE_R sliekšņi kalibrēti uz **vienas** bildes. Ja sāk false-fail, vispirms
  jāmēra `fore_p99`, nevis jāceļ slieksnis.
- `full_shot=True` zars implementēts, bet **nav validēts** (nav tādas bildes).
- `--rerender-saved` "grade neatbilstība" no §28.7 **neapstiprinājās** — tas
  bija novecojis `report_v2_maker.json` no neizdevušās ISNet palaišanas, t.i.
  rotācijas kļūdas sekas. Atskaite izlabota.
- `/var/tmp` tika iztīrīts starp sesijām: sistēma godīgi atteicās
  (`NAV GATES`), `setup_v2.py` atjaunoja 74 s laikā. Uzvedība pareiza.

---

## 30. Koda higiēna un ievades validācija (2026-10-23)

### 30.1 Mirusī koda

`pyflakes`: **15 → 0** atradumi, neviens nav nomaskēts ar `# noqa`.
Vienīgais, kas varēja izskatīties pēc loģikas cauruma — `STRAIGHT_RUN` /
`STRAIGHT_TOL` — nav: izgudrotu griezienu nosaka `inherited` (avotā tur bija
fons → `"cut"`), un tas ir spēcīgāks signāls par kontakta garumu. Kodā atstāta
piezīme, lai tos nepieviestu atpakaļ.

### 30.2 `BG` vienā avotā

Bija `243` trīs failos neatkarīgi (`loop.py`, `checker.py`, `checker_v2.py`).
Tagad `loop.BG_GRAY` ir vienīgais avots; pārējie to importē.

### 30.3 Ievades validācija

Bojāts/tukšs JPEG aizgāja līdz ISNet **apakšprocesam**, un tā traceback tika
ielīmēts `report_v2_maker.json` `error` laukā (12+ rindas). Ieviests
`probe_source_image()` — eksistence, 0 baitu pārbaude, atvēršana, pilna
nolasīšana (`verify()`), minimālais izmērs — izsaukts **pirms** jebkā cita.

| ievade | pēc labojuma |
|---|---|
| neesošs | `V2.1 BLOĶĒTS: uploads mapē trūkst šo failu:` → exit 2 |
| tukšs | `IZLAISTS: fails ir tukšs (0 baiti)` — uzreiz, bez 7 s ISNet palaišanas |
| bojāts | `IZLAISTS: attēls bojāts: Truncated File Read` |

`report` `error`: viena lasāma rinda, bez traceback.

### 30.4 Statuss

`test_workflow_v2.py` **20/20**, `test_gate_r.py` **7/7**, `loop_engine`
**1/1 PASS**, 53.8 s, izvade bitu identiska `663179f3…`. Visas sešas debuga
pozīcijas aizvērtas.

---

## 31. `slamjam` uz īstas bildes ar slēgtu siluetu (2026-10-23)

Bilde: `MVIMG_20261020_161031.jpg` — džinsi, 4096×3072, bez EXIF rotācijas.

### 31.1 Rezultāts

| pārbaude | vērtība |
|---|---|
| siluets slēgts | **jā**, malas 0/0/0/0 |
| kompozīcija | `slamjam` (pieprasīts un izvēlēts) |
| `full_shot` | True |
| bbox | 63.3 % × **78.0 %** (GARMENT_FILL_H = 0.78, izpildīts precīzi) |
| fons | 70.8 % (slamjam reference 64.3 %) |
| fona krāsa | **243, 243, 243** (66.1 % no visiem pikseļiem; stūri 243) |
| maskas caurumi | **0** |
| GATE_R | fore_p99 24.0, bg_p99 2.0, edge 1.391 |
| `ALL_PASS` | **True** |

**Kāpēc fons 70.8 %, ne 64.3 %.** Reference ir krekls, kura aizpildījums bbox ir
~0.76. Džinsi ar V-iecirtumu starp kājām aizpilda tikai **0.591**. Ar tādu pašu
bbox (78 % augstuma) V-forma dabiski atstāj vairāk fona. Tā ir apģērba formas
īpašība, ne kadrējuma kļūda — bbox augstums ir tieši tāds, kā konfigurēts.

### 31.2 Rotācija ir OBLIGĀTA šai bildei

Bez `--rotate` džinsi guļ horizontāli un `slamjam` ievieto tos kā joslu:

| rotācija | fons | bbox | piezīme |
|---|---|---|---|
| **0 (nav)** | **79.7 %** | 75.9 % × 41.3 % | nepieņemami — apģērbs aizņem 40 % augstuma |
| 90 | 67.3 % | 65.3 % × 79.7 % | **apgriež otrādi** (jostasvieta apakšā) |
| **270** | **70.8 %** | 63.3 % × 78.0 % | pareizi — jostasvieta un sarkanā birka augšā |

Lēmums par 270 nav gaumes jautājums: 90 pagriež džinsus **ar galvu uz leju**, un
tas redzams uzreiz. Mērījums (aptuveni vienāds fons abiem) to neatklāj — tāpēc
vizuālā pārbaude šeit ir obligāta, un tā jāveic pirms piegādes.

### 31.3 Atrastā ĪSTĀ kļūda: pieņemta maska tika izmesta

Ar `--rotate 90` (pirms labojuma):

```
AI QA noraida: sadrumstalota siluete (0.584 < 0.6) (segums=0.364)
apmales retry pieņemts: segums=0.3684 overflow=0.0 uncovered=0.0045
STOP: nav drošas maskas -> needs_review
```

**Pretruna:** apmales retry QA pieņēma masku (`overflow 0.0`,
`uncovered 0.0045` — abi tālu zem limitiem), un kods pats komentārā raksta
`if retried: pass  # maska jau iegūta`. Bet nākamais zars pārbaudīja tikai
`method == "plate_texture"`, tāpēc QA pieņemtais `isnet_pad_retry` iekrita
zarā "nav drošas maskas" un **tika izmests**.

Labojums: `if method in ("plate_texture", "isnet_pad_retry")`.
Pēc labojuma: `metode=isnet_pad_retry; segums=0.3671` — bilde turpinās normāli.

### 31.4 Divas gātes viltus-noraidīja (kalibrācijas kļūdas, ne izvades kļūdas)

Pēc kļūdas labošanas džinsi sasniedza gātes, un **divas noraidīja**:

**GATE_C `silhouette_fill 0.5911 < 0.60`.** Maska ir perfekta (0 caurumu,
seko kabatām un jostai, bez papīra noplūdes). Slieksnis 0.60 bija kalibrēts uz
**viena krekla** (0.760). V-veida bikses dabiski aizpilda mazāk bbox.

Gātes sākotnējais nolūks bija noķert **"tīklu"** (masku ar daudziem caurumiem).
Tas tagad ir tiešs mērījums: `binary_fill_holes` atrod caurumus, kas **nav**
savienoti ar rāmja malu — tāpēc V-iecirtums (atvērts uz leju) netiek skaitīts,
bet tīkla caurumi tiek.

**GATE_R `bg_p99 5.0 > 4.0`.** Mērījums sadalījumā:

| zona | p99 |
|---|---|
| plakanais fons (ref = 243) | **1.0** |
| ēnas gradients | 6.0 |

Cēlonis: ēnu paraugā pārrēķina **no jauna audekla mērogā**
(`render_paraugs` → `shadow_bg blur=25`), bet references rekonstrukcija ņem
mastera ēnu **avota mērogā** (`blur=35`, pēc samazināšanas ~17 px). Tāpēc ēnas
gradientā abi attēli atšķiras **pēc konstrukcijas**. Mērot visu fona laukumu,
gāte sodīja savu rekonstrukcijas artefaktu, nevis izvades defektu.

Labojums: `bg_p99` mēra **tikai uz plakano fonu**; visa fona vērtība paliek kā
informatīvs `bg_shadow_p99`. Ēnas zona joprojām ir pārklāta ar GATE_F un GATE_L.

### 31.5 Ko šie labojumi NEDRĪKST darīt — un nedara

Pēc abiem gātu labojumiem pārbaudīts, ka tās joprojām sargā:

| gadījums | bbox_fill | caurumi | rezultāts | pareizi? |
|---|---|---|---|---|
| krekls #2 (īstā) | 0.760 | 0 | iztur | ✓ |
| džinsi (īstā) | 0.591 | 0 | iztur | ✓ |
| tīkls (25 caurumi) | 0.586 | 24 | **noraida** | ✓ |
| milzīgs caurums | 0.543 | 0 | **noraida** | ✓ |
| tukšs rāmis | 0.295 | 1 | **noraida** | ✓ |

GATE_R sabotāžas: **7/7 joprojām noķertas**. Krekls #2: `663179f3…` — bitu
identisks, `ALL_PASS=True`.

### 31.6 ZINĀMA VĀJUMA VIETA — jāpieraksta, nevis jāslēpj

`SILHOUETTE_FILL_FLOOR = 0.55` ir tikai **0.007** virs sintētiskā milzīgā
cauruma gadījuma (0.543) un **0.041** zem īsto bi­kšu gadījuma (0.591).

Tā ir **divu paraugu** robeža, nevis statistiski pamatota. Ja nāks apģērbs ar
vēl izteiktāku V-formu (piem., plati bikses, halāts), tas var viltus-noraidīt.
Risinājums **nav** sliekšņa celšana vai nomešana, bet gan vairāk īstu paraugu
izmērīšana. Kodā tas ierakstīts pie konstantes.

### 31.7 Cits novērojums: viens globālais LUT pār divām dažādām bildēm

`loop_engine` ar divām bildēm rēķina **vienu** LUT abām. Palaists uz krekla +
džinsiem, krekla izvade mainījās (maks. atšķirība 14, vidēji 1.2) salīdzinot ar
tā atsevišķo braucienu. Tas ir dizains ("viens deterministisks globālais LUT
komplektam"), bet nozīmē: **komplekta izvade ir atkarīga no komplekta sastāva.**
Ja krekla piegāde ir akceptēta, to nedrīkst pārrenderēt kopā ar citām bildēm.

---

## 32. Melnā līnija gar apģērba malu (2026-10-23)

### 32.1 Simptoms un pirmā (nepareizā) hipotēze

Lietotājs atzīmēja `IMG_20261023_110348.jpg`: tumša līnija gar **labajām**
(uz labo pusi vērstajām) malām — kreisās kājas iekšmala un labās kājas ārmala.
Sākotnēji likās, ka vainīga mūsu ēna (blur 25, nobīde 25.62 px audekla mērogā).

Mērījums to noraidīja: horizontālos skanos ārpus maskas fons uzreiz ir 243,
tāpēc mūsu ēna tur neko nav sabojājusi. Līnija ir **oriģināla tumšā džinsa
mala**, kas palikusi bez jebkādas pārejas.

### 32.2 Īstā sakne: ēna krita nepareizajā pusē

Ēnas virziens bija iekodēts `SHADOW_ANGLE_DEG = 125°` — **lejup-pa kreisi**.
Tas tika noteikts pēc vienas bildes (krekls). Džinsiem ēna oriģinālā krīt
**pa labi un uz leju**, tāpēc 125° nozīmēja: labajām malām ēnas nav vispār.
Tur džinsa tumšā mala karājās pret tīru #F3F3F3 — acs to nolasa kā uzzīmētu
melnu līniju, jo tai nav nekādas mīkstās pārejas, kas oriģinālā to "nesa".

Mērījums pa pusēm (cik L* tumšāks par papīru, ejot prom no maskas):

| d no malas | LABĀ | KREISĀ | APAKŠA | AUGŠA |
|---|---|---|---|---|
| 1 px | **−42.0** | −15.0 | −25.9 | −5.9 |
| 5 px | **−21.7** | +9.4 | −21.6 | +7.4 |
| 12 px | −9.0 | +7.4 | −13.9 | +7.2 |
| 25 px | −1.1 | +6.2 | −9.7 | +6.4 |

Labā puse ir viennozīmīgi tumšākā → ēna pa labi, nevis pa kreisi.

### 32.3 Kāpēc fiksēta konstante ir principiāli nepareiza

Ar vienu un to pašu gradienta-koriģēto metodi abas bildes dod **atšķirīgu**
virzienu: džinsi 21°, krekls 90°. Fiksēts 125° kļūdās par 104° un 35°.
Apgaismojums mainās pa kadriem, tāpēc virziens ir **jāmēra katrā bildē** —
tas atbilst jau pieņemtajam principam "AI piedāvā, mērījums izlemj".

### 32.4 Divas nepareizas mērīšanas metodes (fiksētas, lai neatkārtotu)

1. **Kontūras skenēšana ar leņķu siju** deva vājnu signālu (kreklam −0.1 pret
   +0.1) — neizmantojama.
2. **Krusteniskā korelācija ar masku** (meklē vienu globālu nobīdi) uz džinsiem
   deva nestabilus 45°/0°/27°, bet uz krekla — 131°, kas ir acīm redzami
   nepareizi (ēna ir lejup). Iemesls: krekls aizņem 70 % kadra, tāpēc
   normalizācija paliek bez nosacījumiem. Noraidīta.
3. **"Tumšāks par tālu papīru"** sajaucas ar papīra apgaismojuma gradientu
   (stūri tumšāki); krekla bildē tālu papīru gandrīz nav vispār (R=0).
   Pareizi: salīdzināt **tuvu (4–24 px) ar tālu (60–120 px) tajā pašā virzienā** —
   gradients saīsinās.

### 32.5 Ieviestais risinājums

`loop.measure_shadow_angle(L, mask)` → `(leņķis, stiprums)`, ceturtdaļizšķirtspējā
(~900 px), 0.2–0.4 s. Mēra četras puses, katrai `max(0, tālu − tuvu)`, vektors
`(R−L, D−U)` dod `atan2`. Ja stiprums < 5 % no papīra L* — atkāpjas uz
`SHADOW_ANGLE_DEG` (125°, tikai kā drošinātājs).

Izmērītais leņķis tiek ierakstīts atskaitē (`shadow_angle_deg`,
`shadow_measure_strength`, `shadow_measure_s`) — lēmums ir auditējams.

Rezultāti: džinsi 3.6°, krekls 87.9°. Abos virziens tagad ir **pa labi/lejup**.

### 32.6 Otrs atrastais defekts: globālais LUT un atskaites pārrakstīšana

Pēc džinsu renderēšanas `grade_profile_v2.json` un `report_v2_maker.json`
tika pārrakstīti. Sekas: `test_gate_r.py` bāzes gadījums sāka krist ar
`GATE_A2 max_diff=4` — krekls tika pārbaudīts pret **džinsu** LUT. Tā nav
produkta kļūda, bet gan verifikācijas atkarība no palaišanas secības, un tā
nozīmēja, ka pieņemto kreklu vairs nevar pārbaudīt.

Krekla vēsturiskais LUT nebija atjaunojams: tas nāca no **komplekta**, kas
vairs neeksistē. Pārrēķins no krekla vien deva `max_diff=5` (270°) un 237 (90°).

Labojumi:
- `workflow_v2` raksta **LUT arī katrai bildei** `output/profiles/<stem>_PROFILE.json`
  un ieraksta `profile_path` atskaitē;
- `checker_v2` izmanto bildes pašas LUT, globālais paliek kā atkāpšanās;
- `_persist_report` **uzkrāj** ierakstus starp palaišanām (iepriekš katrs
  `--files` palaišanas gadījums izdzēsa pārējo bilžu ierakstus, jo to izvades
  faili eksistē);
- `test_gate_r` lasa krekla LUT no `output/profiles/`.

### 32.7 Krekls (#2) tika pārrenderēts

Krekla ēna arī bija par 35° nepareizi. Tā kā vienīgais veids, kā atjaunot
konsekventu LUT + JPEG pāri, ir pilna pārrenderēšana, krekls tika pārrenderēts
ar izlaboto modeli: **`663179f3` → `bf5287c0`**.

Pieņemtā versija saglabāta `_accepted/PXL_124339475_ACCEPTED_663179f3.jpg`
(sha `663179f3e6442531`) un `_backup_good/`. Jaunā versija: `ALL_PASS`, 18.4 s,
ēna lejup (87.9°) — atbilst oriģināla mērījumam.

### 32.8 Gala stāvoklis

| bilde | sha | laiks | vārti |
|---|---|---|---|
| džinsi #3 | `0b974708` | 14.4 s | 9 PASS + 2 advisory |
| krekls #2 | `bf5287c0` | 18.4 s | 9 PASS + 2 advisory |

Regresijas: `test_workflow_v2.py` 20/20, `test_gate_r.py` 7/7, čekeris 2/2 PASS,
pyflakes 0.

Ēnas profils džinsu izvadē: +18.6 L* 1 px, maksimums +22.2 pie 3 px, nulle pie
48 px — mīksta pāreja, līnijas vairs nav.

### 32.9 Neatrisināts (nākamais solis)

Ēnas **attālums** joprojām ir fiksēts (43.01 avota px / 25.62 audekla px),
kamēr tiek mērīts tikai virziens. Mērītais džinsu profils norāda uz īsāku,
blīvāku ēnu (oriģinālā izzūd ~25 px, mūsu 48 px). Tas ir nākamais uzlabojums,
nevis defekts — lietotāja atzīmētā līnija ir novērsta.

---

## 33. Ēna pārāk tumša (2026-10-23, otrā iterācija)

### 33.1 Kas bija nepareizi

Lietotājs noraidīja iepriekšējo labojumu ar SS `IMG_20261023_082656.jpg`
(krekls) un `IMG_20261023_110348.jpg` (džinsi): ēna ir **pārāk tumša** tajās
pašās vietās, kur iepriekš bija melnā līnija.

Iepriekšējais modelis bija: nobīdīts binārais siluets → GaussianBlur → viena
konstante `strength = 0.26` visā joslā. Tas dod **VIENMĒRĪGU PLATO**: tumšu
joslu ar asu ārējo robežu, kuras dziļums visā platumā ir vienāds. Zoom
salīdzinājumā tas izskatās kā ar marķieri uzkrāsota josla, nevis ēna.

### 33.2 Ko saka profesionālā prakse (izpēte)

Atslēgas atradnes šai iterācijai:

- **Ēna ir DIVAS daļas.** Kontakta ēna (blīva, šaura, tieši pie malas) +
  metamā ēna (mīksta, dilstoša, tālāk). "(it-s.com)" — veidot tās atsevišķi dod
  reālistiskāku rezultātu nekā viens izpludināts slānis.
- **Uz balta fona 8–20 % necaurspīdības**, nevis 26 %. (pikes.ai: "8 to 20 %
  opacity in a neutral grey reads correctly"; roundcut: "20 % to 50 %" kā
  vispārējs sākums, bet "too high looks dirty and theatrical").
- **Dilšana ir obligāta.** roundcut: *"A shadow with the wrong fade looks like
  a sticker; a softer one with clear ambient occlusion feels expensive."*
  Mūsu vecais modelis dilšanas nebija vispār — tikai izpludināta mala.
- **Tumsākajam punktam jābūt PIE MALAS**, nevis nobīdes vidū
  (pikes.ai: "Anchor the contact point... the darkest part of any shadow").
- **Nekad tīri melns** — ēna ir virsmas krāsa ar mazāk gaismas.
- Fizikālais dilšanas modelis: eksponenciāls `exp(−d/λ)`. Rendering praksē
  (SSAO, Blender AO, ESM) tas ir standarts; lineāra dilšana izskatās
  "nepareizi" (Blender manual, od|forum).

### 33.3 Jaunais modelis

```
shade(d, θ) = strength · exp(−d/λ) · window(d) · (ambient + (1−ambient)·w(θ))
```

- `d` = attālums ārpus maskas (`distanceTransform`), `θ` = virziens prom no
  apģērba (distance-transform gradients pretī ēnas vektoram)
- `strength = 0.18` (maksimums pie malas, 18 %)
- `λ = 10 px` audekla mērogā (mērogots avota izšķirtspējā pēc platuma)
- `window` = smoothstep uz nulli pirms 80 px (sk. 33.4)
- `ambient = 0.22` — daļa, kas paliek arī gaismas pusē (kontakta aptumšojums),
  lai apģērbs nav "pielīmēts" tikai no vienas puses

Mērītais profils (džinsi, L* zem fona): **+8.3 pie 1 px, maksimums +11.0 pie
3 px, +1.4 pie 24 px, 0 pie 48 px.** Vecais: +18.6 / +22.2 / +12.4 / +0.3.
Maksimums samazinājās no 22 L* uz 11 L* un pārcēlās uz pašu malu.

### 33.4 Blakusdefekts: GATE_B mēroga neatbilstība

Pirmais mēģinājums ar λ=10 izgāza `GATE_B_background` (72 %). Iemesls nav
ēstētisks: eksponenciālā aste turpināja tumšot arī 100–160 px attālumā, bet
GATE_B pieprasa, lai viss fons tālāk par 90 px būtu **precīzi** #F3F3F3.
Eksponenciāla funkcija nekad nav tieši nulle, tāpēc aste ir jānogriež ar logu.

Otrs atklājums: GATE_B mēra **master telpā** (3072–4096 px plata), kur 90 px ir
cits relatīvais attālums nekā 2000 px kadrā. Mans logs tur mērogojās uz 122 px
(proporcionāli pareizi), bet vārts gaidīja 90. Tas sodīja **pareizu** izvadi.
Labots: `far = dist_out >= 90 · (master_width / 2000)` — tas pats relatīvais
attālums, nevis vājināts slieksnis. Sabotāžas testi joprojām krīt 6/6.

### 33.5 Kāpēc ne "vienkārši samazināt 0.26 → 0.18"

Tas būtu tas pats platо, tikai gaišāks — ar asu ārējo robežu un vienmērīgu
dziļumu. SS zoom rāda, ka problēma ir **forma**, nevis tikai līmenis: lietotājs
iezīmēja tieši to joslu, kurai bija redzama beigu līnija. Dilšana noņem beigu
līniju, un maksimums pāriet pie pašas apģērba malas, kur tam jābūt.

### 33.6 Rezultāts

| bilde | sha | laiks |
|---|---|---|
| džinsi #3 | `c409ba57` | 15.9 s |
| krekls #2 | `c00c4cc6` | 18.7 s |

Čekeris 2/2 PASS; `test_workflow_v2` 20/20; `test_gate_r` 7/7; pyflakes 0.

### 33.7 Atklātais ierobežojums

`SHADOW_STRENGTH`, `λ`, `ambient` un logs ir **fiksētas konstantes** — tās
nemēra no oriģināla. Mērījums rāda, ka oriģināla ēna ir 27 % pie malas, bet uz
mūsu gaišā papīra (L* 96 pret oriģināla 56) tas lasītos smagāk; tāpēc 18 % ir
apzināta kompozīcijas izvēle, ne oriģināla kopija. Nākamais solis, ja
nepieciešams: mērīt ēnas **profilu** no oriģināla un normalizēt pēc papīra
gaišuma starpības, nevis lietot fiksētu procentu.

---

## 34. Melnā maliņa: maskā palikusi papīra ēna (2026-10-23, trešā iterācija)

### 34.1 Kas patiesībā bija defekts

Divas iepriekšējās iterācijas laboja **ēnu ārpus apģērba** (vispirms virzienu, tad
dziļumu). Abas bija garām, un lietotājs to pateica tieši: *"ēnai nebija ne vainas,
bet galvenā problēma ir pikseļi kas krīt no ēnas vai fons kas ir tieši pie biksēm
kur es atzīmēju ir melns tā kā fons kas nav nogriezts"*.

Defekts ir **maskas iekšpusē**: segmentācija aprija oriģināla papīra ēnu, tāpēc
gar apģērba malu palika 5–20 px plata josla ar PAPĪRA krāsu. Uz balta fona tā
lasās kā melna līnija, kas pie malas "pielīp".

Pierādījums ar pikseļu skenēšanu oriģinālā (y=1800, maskas labā mala x=2442):

| x | maska | R | G | B | L | B−R |
|---|---|---|---|---|---|---|
| 2430–2442 | **iekšā** | 47–55 | 32–38 | 25–29 | 36–42 | **−20…−26** |
| 2443–2448 | ārpus | 73–136 | 59–130 | 46–114 | 62–130 | −22…−31 |

Džinss ir **zilgans** (B−R +5…+10), papīra ēna ir **silta** (B−R −20…−25).
Josla maskas iekšpusē ir −25 → tā ir papīrs, nevis audums. Pie y=1800 maska
saturēja **13+ px papīra**.

### 34.2 Kāpēc iepriekšējie mēģinājumi to neredzēja

`extend_foreground_colors` apstrādā tikai pikseļus **ārpus** maskas
(`binary_u8 == 0`). Iekšējo malu tas nekad nepieskārās — tāpēc kontaminācija
izturēja gan ēnas virziena, gan dziļuma labojumus.

### 34.3 Kas tika izmēģināts un neizdevās (fiksēts, lai neatkārtotu)

1. **Krāsas aizvietošana maskas iekšpusē** (`decontaminate_edge`, delta hroma
   > 1.5): strādāja tikai 1.4 % joslas, jo `clean` slieksnis 12 px vēl nebija
   tīrs — aizvietotā krāsa nāca no tikpat kontaminēta pikseļa.
2. **Alfa atšķetināšana** (matting: `C = a·F + (1−a)·B`, risinot `a`):
   `a` mediāna 1.00, izmaiņa 0.008 — jo `C_f` (tuvākais "tīrais" pikselis) pats
   ir kontaminēts. Maska satur papīru dziļāk, nekā matting pieņem.
3. **Akls erozijas choke** 6/10/14 px: noņem joslu, bet **apgraiza siluetu** un
   pazaudē auduma detaļas — tieši tas anti-pattern, no kā brīdināja izpēte.
4. **Pa pikselim griezta hromas maska**: rim krita par 85 %, bet mala **saplīsa
   robos** (1–2 px zobi) — jo lēmums tiek pieņemts katram pikselim atsevišķi.

### 34.4 Ieviestais risinājums: `decontaminate_rim`

Griež **gar kontūru, nevis pa pikselim**:

1. Katram kontūras punktam mēra, **cik dziļi sākas auduma krāsa**. Apstājas, kad
   atgriezusies GAN auduma hroma (B−R > lokālā − 3), GAN normāls spilgtums
   (L > 60 % no lokālā auduma). Tikai hroma nepietiek: izspīlējuma vietā josla
   bija hromatiski tuva (–1), bet 3× tumšāka (L 30 pret 105).
2. Šo dziļumu izlīdzina **GAR KONTŪRU** (`gaussian_filter1d`, sigma=120 punkti,
   cirkulāri). Tas ir galvenais — izlīdzināšana notiek kontūras virzienā, tāpēc
   mala paliek gluda; pa pikselim griežot, tā saplīst.
3. Kontūras punktus nobīda uz iekšu par izlīdzināto dziļumu, aizpilda poligonu,
   `MORPH_CLOSE` 9×9 + `MORPH_OPEN` 11×11 noņem atlikušos izspīlējumus.

Nav agresīva erozija: punkti, kur auduma krāsa sākas uzreiz, netiek aiztikti
(dziļums 0). Uz džinsiem vidējais apgriezums 7.3 px, maksimālais 16 px, noņemti
90 990 px (maska 0.3654 → 0.3472).

### 34.5 Rezultāts

| rādītājs | pirms | pēc |
|---|---|---|
| malas hroma (B−R) | **−15.0** | **−1.0** (audums +10) |
| tumšo rim pikseļu | 23 802 | 17 051 (īsts džinss) |

Melnā josla ir pazudusi, mala palika gluda, auduma detaļas (šaures, kabatas
apmales, kroku ēnas) saglabātas.

### 34.6 Blakusdefekts: `_MASK.png` tika saglabāta PIRMS apgriešanas

Pēc ieviešanas `GATE_R` krita ar `fore_p99=171`, lai gan izvade bija pareiza.
Iemesls: `_MASTER_1to1.png` tiek rakstīts jau apgriezts, bet `_MASK.png` — no
sākotnējās maskas. Čekeris rekonstruēja references kadru pēc nepareizās
ģeometrijas. Labots: ja `decontaminate_rim` kaut ko mainīja, apgrieztā maska
tiek pārrakstīta kā kanoniskā.

### 34.7 Kontroles

Čekeris 2/2 PASS; `test_workflow_v2` 20/20; `test_gate_r` 7/7; pyflakes 0.
Laiks: džinsi 17.4 s, krekls 20.6 s (no tiem apgriešana ~1.1 s).

### 34.8 Atklātais ierobežojums

Kontūras dziļuma mērījums pieņem, ka **aiz kontaminētās joslas vienmēr ir
audums**. Uz šīm divām bildēm tas ir pareizi (V-iecirtums ir atvērts uz leju, ne
uz sāniem). Ja apģērbam ir šaura sprauga vai atvērums tieši malā, normāle var
iziet cauri spraugai un atrast papīru aiz tās — tad apgriezums var būt par lielu.
Šobrīd to ierobežo `max_trim_px = 16` un `MORPH_OPEN 11×11`.

---

## §35. Malu defekts, otrā kārta: kritērijs ir TEKSTŪRA, nevis krāsa

### 35.1 Kāpēc §34 neizturēja

Lietotājs atzīmēja trīs joslas (`uploads/IMG_20261023_122322.jpg`) un uzrakstīja:
"Ir labāk, bet joprojām nav ideāli." §34 grieza pēc **hromas un spilgtuma**:
apstājās, kad `B−R > fab_br−3` **un** `L > 0.60·fab_L`. Mērījumi rādīja, ka šis
kritērijs ir principiāli nepareizs.

**Spilgtums neder.** MASTER audumā (d>60) L p1 = 9.7, p5 = 25.7, p10 = 38.3 —
pats džinss sasniedz L = 2–40 (tumšas šuves, kabatu apmales, kroku ēnas).
Maskā pikseļi ar L<40 ir **12.05 %**, un **73.8 % no tiem atrodas dziļumā >60 px**,
t.i. dziļi audumā; tikai 9.8 % ir tuvu malai. Spilgtuma slieksnis nogrieztu īstu
audumu un joprojām palaistu garām papīru.

**Hroma arī neder.** Auduma `B−R` mainās pa bildi no −30 līdz +20 (mērīts
lokāli, vidēji pa 15×15 logu), tāpēc lokālais vidējais nepareizi atzīmēja īstu
audumu par papīru. Konkrēts piemērs: pie y=520 lokālais auduma vidējais
`B−R = −20`, bet faktiskais audums tur ir **+19**; noteikums `br > fb−3` iedarbojās
uzreiz un neko negrieza (klusais no-op).

### 35.2 Kritērijs, kas strādā: tekstūra

Papīra ēna ir **gluda**, džinsam ir redzams reljefs. Mērīts ar
`|L − uniform_filter(L,5)|` — augstfrekvences enerģija:

| reģions | joslā | audumā | attiecība |
|---|---|---|---|
| jostasvieta | **1.4** | 11–12 | 0.12 |
| kreisā kāja | **1.4–4.1** | 22 | 0.06–0.19 |
| labā kāja (dziļi) | — | 19.7 | — |

Slieksnis `0.45 · auduma_tekstūra` atdala abus ar ~3× rezervi. Uz džinsiem
auduma tekstūra 20.69 → slieksnis 9.31; uz krekla 6.17 → 2.78.

### 35.3 Kāpēc griež GAR KONTŪRU

Katram kontūras punktam mēra, cik dziļi atgriežas auduma tekstūra (meklē 3
pēc kārtējos paraugus virs sliekšņa), tad izlīdzina dziļumu **gar kontūru**
(mediāna 25 + Gausa σ=40) un nobīda punktu uz iekšu. Pa pikselim griežot, mala
saplīst robos; gar kontūru tā paliek gluda.

Svarīgi: izlīdzinājums drīkst būt tikai **gar** kontūru. Platas Gausa
izlīdzināšanas mēģinājums izplata griezumu pāri kontūrai (5340 punkti bez
pierādījumiem), un siluets kļūst šaurāks un taisnāks.

### 35.4 Otrs solis: izvirzījumu noņemšana

Nobīdes metode **nevar** noņemt izvirzījumu: šaurā smailē normāle iet šķērsām,
tāpēc tekstūra atgriežas jau pēc 4 px un griezums nenotiek. Pievienots solis,
kas salīdzina kontūru ar tās pašas kontūras izlīdzinātu versiju un atvelk
atpakaļ tikai tos punktus, kas (a) izvirzās uz āru >6 px un (b) ir gludi
(tekstūra < 0.45·auduma). Darbojas tikai uz teksturēta auduma
(`fabric_tex ≥ 10`), lai krekla gludās aproces netiktu aizskartas; kopējais
limits 3 % punktu. Džinsi: 89 punkti, 419 px. Krekls: **0 px** (sha nemainīgs).

### 35.5 Rezultāts un robeža

Trīs atzīmētās joslas ir noņemtas; siluets nav sašaurināts. Džinsi
`1d2a493d5c4fe601`, 20.4 s; krekls `2b4f912c6ca4fbb0`, 22.5 s (nav mainījies).
Čekeris 2/2 PASS; `test_workflow_v2` 20/20; `test_gate_r` 7/7; pyflakes 0.

**Svarīga robeža.** Pēc griezuma pie jostasvietas paliek neliels tumšs
pakāpiens. Tā **nav** kontaminācija: izvirzījumu tekstūra ir 18.8 pret auduma
20.9, un krāsa L 90 / B−R +6 — abi rādītāji atbilst audumam, ne papīram
(papīrs būtu L 200+, B−R −25, tekstūra 1–4). Tas ir īsts džinsa kroku izvirzījums,
un kritērijs pareizi atsakās to griezt. Pirms turpināt griešanu, jāpārliecinās,
ka lietotāja atzīme neattiecas tieši uz šo vietu.

### 35.6 Nodalītās kļūdas

- Spilgtuma slieksnis (L<40) kā malas kritērijs — neder, skat. 35.1.
- Lokālais `uniform_filter` vidējais hromai — neder, skat. 35.1.
- Lokālā tekstūra pa visu kontūru (logs ±40 punkti) — neatdala (josla ir
  teksturēta, jo tā ir papīra un džinsa sajaukums).
- Lokālais tekstūras references logs (d 35–55) kā slieksnis — p10 = 4.9,
  p50 = 20.1; pārāk mainīgs, ievieš ragainu malu. Noraidīts.
- `grey_closing` 31/61/101 — noņem joslu, bet mala kļūst daudzstūraina.
- Krāsu aizvietošana joslā bez griezuma — saglabā siluetu, bet noņem tikai
  ~22 % malas punktu (2417→1879). Nepietiek.
- Sarkanā marķiera ekstrakcija trāpa arī apģērba detaļās (sarkanā ādas
  etiķete) — vienmēr pārbaudīt ar izgriezumu.

### 35.7 Trešā kārta: pakāpienu izlīdzināšana (produkcijas prasība)

Lietotājs: bilde paredzēta **Vinted** tirdzniecībai, tāpēc jābūt bez kompromisiem.
Apskatot 1:1, atklājās cits defekts nekā josla: **mala bija robaina** —
ISNet seko papīra ēnas mēlei un vietām dod taisnstūra pakāpienus ap 15 px
dziļumā. `MORPH_OPEN 11×11` uz raupjas kontūras tos tikai pastiprināja.

Mērījumi, kas to apstiprināja un izslēdza citas hipotēzes:
- Absolūti pieskaņots profils (mala ar `|`) rāda, ka **tumšās joslas vairs nav**:
  neviens pikselis pie malas (15–45) nav tumšāks par auduma tumšākajiem
  pikseļiem (27–45 pie auduma vidējā 70–115). Tātad krāsa vairs nav problēma.
- Troksnis nav vainīgs: hromas troksnis 0.87, denoise dod 18.10 → 18.13 un
  korelācija 0.999 — tā ir īsta džinsa tekstūra, ne troksnis.
- Edge snapping (gradients ±16 px) neko nemaina: gradients pie maskas malas
  155–235, maska jau seko īstajai malai. Noraidīts.
- Guided filter alfa (r=8, ε=1e-3) padara malu **izplūdušu**. Noraidīts.
- BiRefNet_lite (MIT, 224 MB) lejupielādēts, bet **neiederas RAM**: 1024×1024
  ievade prasa >1.4 GB; ar `enable_cpu_mem_arena=False` joprojām
  `Failed to allocate 25 MB`. Šī vide to nevar izpildīt.

**Risinājums:** pēc dziļuma nobīdes kontūru salīdzina ar tās pašas kontūras
izlīdzinātu versiju (logs 35) un pievelk **tikai tad, ja novirze ≤ 14 px**;
lielas novirzes (īstas apģērba formas) paliek neskartas. Pildījums ar
`LINE_AA` un `shift=4` (16× subpikseļu precizitāte), `MORPH_CLOSE 5×5`;
`MORPH_OPEN` noņemts, jo tas bija pakāpienu avots.

Rezultāts: džinsi `600e00ea578f977a` 18.7 s; krekls `1d93c7a735975bd4` 21.2 s.
Čekeris 2/2 PASS; `test_workflow_v2` 20/20; `test_gate_r` VISI OK.

### 35.8 Atlikusī atšķirība, kas jāzina

Pie jostasvietas (reģions B) saglabājas **neliels izvirzījums**, kas pēc
visiem mērījumiem ir īsts džinsa kroku audums (tekstūra 18.8 pret auduma 20.9,
L 90 / B−R +6; papīram būtu tekstūra 1–4, L 200+). To apzināti negriež.
C un A reģionos mala tagad ir gluda, bez pakāpieniem un bez joslas.

---

## §36. Studijas tipa ēna un fotogrāfiska mala

Lietotājs: "malas ir pārāk robainas vietām drukas audums... un nav vispār ēnas...
jādabū ir studijas tipa rezultāts."

### 36.1 Ēna bija pārāk vāja un pārāk cieša

Izmērīts izvadē: fona L pēc attāluma no apģērba 219 / 231 / 236 / 239 / 242 —
t.i. 24 vienības pie malas, un 50 px attālumā jau 243. Atsauces
slamjam_mfpen_trousers.jpg: 87 / 68 / 54 / 27 / 0 pie 1 / 6 / 10 / 16 / 25 px.
Tātad atsaucei ēna ir 3× stiprāka un sniedzas 2× tālāk.

Izmaiņas (shadow_bg konstantes):
| parametrs | bija | tagad |
|---|---|---|
| SHADOW_STRENGTH | 0.18 | 0.32 |
| SHADOW_FALLOFF_PX | 10.0 | 18.0 |
| SHADOW_AMBIENT | 0.22 | 0.55 |
| SHADOW_CUTOFF_PX | 80.0 | 34.0 |

AMBIENT celts no 0.22 uz 0.55, jo atsauces ēna ir gandrīz vienmērīga visapkārt
(7.5 virs / 13.7 apakšā / 9.8 kreisi / 12.8 pa labi pēc L) ar vieglu virzienu.
Iepriekšējais modelis deva gandrīz tikai virziena komponenti.

Rezultāts: d1 54 / d3 39 / d6 33 / d10 26 / d16 19 / d25 6 / d40 0.
Tuvu atsauces formai, ar saglabātu #F3F3F3 aiz 40 px (GATE_B).

### 36.2 "Robainība" nebija ģeometrijā

Kontūras raupjums izmērīts: mūsu džinsi 0.29, krekls 0.12; atsauces
0.45 / 0.34 / 0.39. Mūsu kontūra jau bija GLUDĀKA par atsauci. Pārejas
platums: mūsu 3.7 px, atsauce 4.2–8.4 px.

Īstais iemesls: mala bija šķēru asa (feather 1.6, contrast 1.65), savukārt
atsaucē ir fotogrāfiska pāreja. 4× palielinājumā tas redzams tieši: atsauces
mala ir mīksta, mūsējā — asa līnija ar tumšu rētu pie malas.

Izmaiņas (refine_alpha): feather 1.6 → 3.0, smooth 1.6 → 2.0,
contrast 1.65 → 1.25, band 5 → 6.5. Pārejas platums 3.7 → 5+ px.

Vairāk nevar: feather 6.0 / band 14 deva 6 px (kā atsaucei), bet tad krita
GATE_H_edge — alfa sniedzās tālāk par 8 px ārpus malas
(outside_clear 99.77 % < 99.9 %), un GATE_R fore_p99 27 > 24.
Tāpēc 3.0/6.5: GATE_H_edge 100.0 %, GATE_R p99 = 24.0 (tieši uz robežas).

### 36.3 Pārbaudītie un noraidītie "gludie tumšie" apgabali

Izvadē atrasti 15 gludi tumši apgabali (tekstūra < 0.45·auduma, L<120),
daži līdz 287 px dziļi. Pārbaudot katru ar izgriezumu, visi izrādījās
īstas auduma detaļas: kroku ēnas, šuves, sarkanā ādas etiķete. Iemesls:
dziļā ēnā džinsa tekstūras kontrasts krīt, tāpēc tekstūras kritērijs tur
nešķir. Salīdzinājums ar oriģinālu apstiprināja — nav artefaktu.
Šis ir tas pats kļūdas veids, kas jau atzīts §35.5: tekstūra nav derīga
dziļi ēnā, tikai pie malas.

### 36.4 Kontroles

Džinsi 75f5307291410183, 18.8 s; krekls 6b63665df9a5d99b, 21.6 s.
Čekeris 2/2 PASS; test_workflow_v2 20/20; test_gate_r VISI OK.

---

## §37. Tuvplāni (detail crops) — slamjam stila papildskati

Uzdevums: no divām bildēm (priekšpuse/aizmugure) izveidot vēl divus
pietuvinātus skatus, kā to dara slamjam.

### 37.1 Atslēgas atklājums no atsauces

`slamjam_mfpen_trousers_3.jpg` un `_4.jpg`: apģērbs **aizpilda kadru un iet
pāri malām** (segums 0.93–1.00), fons gandrīz nav. Tas nozīmē, ka tuvplānam
nav vajadzīga segmentācija — un tāpēc nepastāv arī malas defekti (fringe,
robainība, pakāpieni), kas maksāja visu §34–§36 darbu.

### 37.2 Kāpēc tuvplāns ir ASĀKS, nevis sliktāks

Negaidītais: griežot 1:1 no master (3072x4096), tuvplānu var iegūt bez
palielināšanas, jo overview pati tiek SAMAZINĀTA uz ~1267x1950. Izmērīts
gradienta asums tajā pašā apgabalā:

| avots | gradienta vid. | p99 |
|---|---|---|
| griezts no gatavās overview (3.5× palielinājums) | 89.9 | 357 |
| **griezts no master (2.0×)** | **213.9** | **621** |

T.i. 2.4× vairāk malas enerģijas. Vizuāli: kreisajā šuves izplūdušas un džinsa
pinums pazudis, labajā viss ass.

### 37.3 Loga izmērs ir kompromiss, kas jāmēra

Cik lielu 4:5 logu var atļauties, nosaka segums (cik daļa loga ir apģērbs).
Izmērītā līkne džinsiem (master): 2000×2500 → 0.682; 1600×2000 → 0.819;
1400×1750 → 0.882; 1000×1250 → 0.969. Tāpēc logs tiek izvēlēts **adaptīvi**:
lielākais 4:5 logs, kurā segums ≥ 0.88 (atsauces slamjam_3 blīvums).
Krekls ir tuvplāns oriģinālā, segums 1.00 → logs 2000×2500 pie 1:1.

Džinsi: logs 1023×1279, palielinājums 1.96×.
Krekls: logs 2000×2500, palielinājums **1.00×** (bez palielināšanas).

### 37.4 Akcentu izvēle ir mērīta, nevis nejauša

- **"detaļa"** — augstākā detaļu enerģija (Laplacian, tikai apģērba iekšpusē,
  mala nogriezta ar eroziju 31 px, lai malas gradients netiktu skaitīts).
- **"zīmols"** — lielākā hromas novirze (>45) no auduma mediānas; ja izteiktas
  nav, ņem nākamo labāko detaļu. Džinsiem šis trāpīja sarkanajai ādas etiķetei.

### 37.5 Profesionālais paņēmiens palielināšanai

Lanczos interpolācija + acutance atjaunošana ar UnsharpMask, izmantojot
profila pašu `output_sharpen` (radius 1.4, percent 42, **threshold 3**) un
pastiprinot tikai `percent` proporcionāli palielinājumam (max +50 %).
`threshold` ir būtiskais: tas neļauj pastiprināt troksni plakanos laukos.
Nekas netiek ģenerēts — tikai atgriezts asums, ko interpolācija paņem.

### 37.6 Rezultāti

`output/tuvplani/` — 4 faili (2 uz drēbi), 2000×2500, kvalitāte 95,
subsampling 0 (pilna hroma izšķirtspēja). Palete un ēna nāk no tā paša
per-image profila, tāpēc tuvplāni saskan ar overview.

Kontroles: `test_workflow_v2` 20/20, `test_gate_r` VISI OK (netika skartas).

---

## §38. Otrā drēbe (henley krekls): ēnas mēroga defekts + akcentu kritērijs

Dotas divas bildes — priekšpuse un aizmugure. Uzdevums: abas slamjam stilā
+ divi tuvplāni.

### 38.1 Kritisks atklājums: master un gala ēna bija dažādā mērogā

`GATE_R_reconcile` krita ar `bg_p99` 7–9 (limits 4). Cēlonis **nebija** izvadē:

- `MASTER_1to1.png` ēna tiek rēķināta ar `blur=35`, `falloff=18` px **avota**
  mērogā (3072 px plats);
- `render_paraugs` uzliek ēnu ar `blur=25`, `falloff=18` **audekla** mērogā
  (2000 px plats);
- master pēc tam tiek SAMAZINĀTS ar koeficientu ~0.52, tāpēc tā ēna izvadē
  iznāk 35·0.52 = 18 px, bet vajag 25 px.

Tāpēc referencei (kas nāk no master) ēna beidzas agrāk nekā izvadei — un
`GATE_R` to pamatoti saskata. Labots: master ēna tagad tiek rēķināta
**audekla mērogā, dalot ar ielīmēšanas koeficientu** (`para_scale`), t.i.
blur, falloff un pārvietojums visi dalīti ar to. Rezultāts: `bg_p99` 0–1.

### 38.2 Otrs defekts: čekeris grieza master tieši pa bbox

`reconcile_reference` grieza `master[y0:y1, x0:x1]` pa apģērba bbox. Tā kā
master ēna sniedzas **arī ārpus** bbox, tā tika nogriezta, un references fons
pie bbox galējām malām palika tīrs #F3F3F3, kamēr izvadei tur ir ēna.
Tas deva viltus `GATE_R` kritumu tieši gar kontūru (sarkanās joslas
vizualizācijā).

Šis defekts iepriekš nebija redzams, jo visas iepriekšējās bildes gāja
`closeup` zarā (kur pad nav vajadzīgs) — tikai otrā drēbe pirmo reizi
izmantoja `full_shot=True`.

Labots: referencei tagad ir **divi slāņi** — ārējais ēnas gredzens no
paplašināta griezuma (apakšā) un precīzais bbox attēls virsū. Galvenais
attēls paliek 1:1 ar renderētāju, bez subpikseļa nobīdes (mēģinājums ar
vienu paplašinātu griezumu un nobīdi deva `fore_p99` 65, jo 0.2 px nobīde uz
džinsa pinuma ir milzīga).

### 38.3 Trešais defekts: `test_isnet_parity.py` rādīja uz dzēstu bildi

Tests kopš bildes #1 dzēšanas krita ar `FileNotFoundError`, nevis ar reālu
paritātes kļūdu — t.i. tas neko nepārbaudīja. Pārvirzīts uz esošu avotu.
Tagad: `maks.diff=0`, bitu identiski.

### 38.4 Akcentu kritērijs: tekstūra jānoņem PIRMS struktūras meklēšanas

Pirmā versija (`Laplacian(lum)`) uz vafeļu kreklu izvēlējās **tukšu audumu**:
vafeļu raksts visur ir vienādi spēcīgs, tāpēc maksimums ir vienkārši
"blīvākās tekstūras" vieta. Mērīts: pirms izlīdzināšanas vid 42.7, pēc σ=6 —
0.68, bet kontrasts (max/vid) pieaug 7.5 → 12.1. T.i. pēc tekņa noņemšanas
paliek TIKAI lokalizētā struktūra.

Labots: detaļu karte = `|Laplacian(gaussian(lum, σ))|`, kur σ = 0.003 · apģērba
platums (mērogam piesaistīts). Akcents tiek meklēts 500×625 logā (nevis
uzreiz lielajā), tad ap to ņemts lielākais 4:5 logs ar segumu ≥ 0.88.
Abi akcenti tiek turēti vismaz 0.28·dimensijas attālumā.

Rezultāts uz henley kreklu: piedurknes krokas (izteikts akcents, kā atsauces
`slamjam_mfpen_trousers_3`), un otrs — piedurknes/aproces šuve.

### 38.5 Kontroles

Krekls priekša `PXL_...124309570`, aizmugure `PXL_...124651636`.
Čekeris **4/4 PASS**; `test_workflow_v2` 20/20; `test_gate_r` VISI OK;
`test_isnet_parity` PARITY OK. Abas bildes ~10 s katrā.

---

## §40 — Pirmā Vinted komplekta bildes (henley): divi jauni kadri

### 40.1 Kas tika apstrādāts

Pieci vienas uzņemšanas kadri. Trīs jau bija gatavi no iepriekšējā darba
(priekša `124309570` → `3dc8f806`, mugura `124651636` → `c11e478c`,
aproces `124339475` → `6b63665d`) un pēc atkārtotas palaišanas palika **bitu
identiski**. Divi jauni:

* `124322251` — pogu plāksne pie kakla (rotācija 270°, jo oriģināls ir
  ainavas formātā ar apkakli labajā malā);
* `124406358` — etiķete (UNIQLO, L, MADE IN INDIA).

### 40.2 Defekts, ko atrada tikai šī bilde: maskas "kabata"

`decontaminate_rim` ir paredzēts oriģināla **papīra ēnas** noņemšanai gar
apģērba malu (QA §34–35). Uz kadra, kurā audums sniedzas pāri kadra malai,
"mala" nav īsta apģērba mala, un funkcija pa kontūru izdur **tievas plaisas
audumā** — pēc tam tās aizpildās ar fonu (vērtības ~207, bez vafeļu
tekstūras). Cēlonis nav decontam vien: ISNet arī pati bija atzinusi divus
izbalējušus, gludus auduma laukumus par fonu.

Kas tika izmērīts un kā labots:

1. Fona komponentes analīze: lielākā (2 898 407 px) ir papīrs augšā un
   pieskaras augšas/kreisajai/labajai malai; atsevišķa komponente
   **38 813 px, box (2589, 3435, 185×645)**, pieskaras TIKAI apakšējai
   malai — tā ir plaisa.
2. Noteikums: aizpildīt tās fona komponentes, kas nav ne papīrs (tā, kas
   satur augšējo kreiso stūri), ne tieva malas josla (min. dimensija
   ≤ 1.2 % no platuma). Aizpildīta tieši viena komponente — 38 813 px,
   t.i. 0.4 % maskas.
3. Pievienota CLI opcija **`--no-decontam STEM`**, kas šiem kadriem izlaiž
   `decontaminate_rim` (rec iznāk `{"applied": false, "skipped": true}`).

Pārbaude pēc labojuma: plaisas pazuda, tekstūra nepārtraukta; pārējie
attēli nav aiztikti.

### 40.3 Etiķetes kadrs: pipeline pamatoti atteicās

`124406358` apstājās ar `STOP: nav drošas maskas -> needs_review`
(segums 0.050; apmales retry arī noraidīts). Tas ir pareizi: krekls
aizpilda **visu** kadru, tāpēc segmentācijai nav ko atdalīt un jebkurš
mēģinājums izgriezt "apģērbu" būtu izdomāts.

Tāpēc etiķete tika apstrādāta bez izgriešanas — tā ir godīgā pieeja
(sk. arī slamjam principu: ja apģērbs aizpilda kadru, cutout nav vajadzīgs):

* oriģināls 4080×3072, etiķetes teksts ir **sānos** (nevis augšpēdējs) —
  pagriezts 90° pretēji pulksteņa virzienam;
* papīra josla pēc pagriešanas nonāk augšā (446 px) un tiek **nogriezta**,
  tāpēc kadrā nav neviena fona pikseļa;
* 4:5 griezums 2700×3375, etiķete novietota 45 % no kreisās;
* krāsojums ar tās pašas uzņemšanas LUT (profils no `124322251`).

Tona pārbaude: p50 171 pret 190–191 pārējiem; gaišākais RGB 233/237/239
pret 248/251/253. Atšķirība ir dabiska (kadrā ir apkakles josla un etiķetes
ēna), tāpēc apzināti **netika** izlīdzināta ar papildu ekspozīcijas
celšanu — tas skartu etiķetes melno tekstu.

### 40.4 Komplekts

Piecas bildes 2000×2500 `output/paraugs/`, kopskats
`output/_KOMPLEKTS_vinted_henley.jpg`. Kārtība Vinted sludinājumam:
priekša → mugura → pogas → aproces → etiķete.

---

## §41. Plakāta kadra atrisinājums un divi čekera/labošanas principi (2026-10-23)

### 41.1 Kas patiesībā notika
Pēc pēdējās apstiprinātās kolāžas plakāta kadrs (`PXL_20261022_124322251`) krita
`GATE_F_fullframe_closeup` ar `left = cut` (kontakts 0.6496, avotā 0.4608).
Mēģinājums labot ar manuālu 4:5 apgriešanu **sabojāja vēl vairāk**: `GATE_R`
nokrita (fore_p99 138 pret bg_p99 159), jo manuālais ceļš apiet pipeline
krāsu profilu. Secinājums: gatavo kadru nedrīkst pārgriezt ārpus pipeline.

### 41.2 Kļūda čekerī, nevis kompozīcijā
`_edge_report()` gala kadru mēra pa **8 px joslu** uz 3× samazinātas maskas
(= 24 px no 2000 px = 1.2 % platuma), bet `src_edge` avotu mērīja pa **vienu
kolonnu** (`M[:, 0]`). Mīksta maskas mala pie x=0 deva 0.2555 vienā kolonnā,
kamēr tajā pašā malā 1.2 % joslā ir 0.6302. Tāpēc dabiska pāreja pāri malai
tika atzīta par „izgudrotu griezienu".

Labojums: abas puses mēra ar vienām un tām pašām frakcijām
(`STRIP_FX = 24/2000`, `STRIP_FY = 24/2500`). Tas **nav vārtiņu vājināšana** —
definīcija tagad ir vienāda abās pusēs; slieksnis (`src >= 0.50`) nav mainīts.
Pārbaudīts: ar veco mērījumu plakāts krita, ar jauno iztur, un neviens cits
vārtiņš nemainījās.

### 41.3 Otrs defekts: 418 px caurums maskā
`clean_mask` jau aizpilda visus iekšējos caurumus, bet 2026-10-23 ad-hoc solis
(tas, kas aizpildīja 38 813 px slitas) atstāja kā fona komponentes ar
`min(w,h) <= 0.012*W`. Tā rezultātā palika 418 px caurums (16×40 @(2689,3697)) —
izbalējis vafeļu adījuma izcēlums (maks. kanālis **207**), ko ISNet bija
atzinis par papīru (papīrs = **243**). Čekeris to godīgi nosauca:
`interior_holes = 1`.

Risinājums `fix_mask_holes.py` (fizikāls kritērijs, nevis gaume):
komponente, kas nav savienota ar kadra malu, ir īsts fons **tikai tad**, ja tajā
ir papīram raksturīgs pikselis (`max(channel) >= paper_med - 12`). Citādi tā ir
auduma gaišā daļa un tiek aizpildīta. Rezultāts: aizpildīts tieši 1 komponente
(418 px), segums 0.81588 → 0.81591, neviena īsta sprauga netika aizskarta.

### 41.4 Gala stāvoklis
- Kanoniskais celms `PXL_20261022_124322251.PORTRAIT.ORIGINAL` renderēts no
  **neskartā 4080 px meistara** (`--resume --no-decontam`), bez apgriešanas.
- Čekeris: **1/1 PASS, ALL_PASS = true**; `GATE_L` = n/a (nav papīra).
- `GATE_F`: top `margin`, bottom/left/right `bleed` (visas mantotas).
- `GATE_C`: `interior_holes = 0`, segums 0.7676.
- Gala sha256 `f2d552993db074df…`, 2.37 MB.
- Kolāža pārbūvēta ar `make_collage_vinted.py` (1528×414, flīzes 288×360,
  starpa 14, atkāpes 16/22/32, q=95).

### 41.5 Mācība
Kad vārtiņš krīt, vispirms jāpārbauda, **vai mērījums abās pusēs ir vienāds**.
Divas reizes pēc kārtas „laboju" kompozīciju, kamēr kļūda bija salīdzināšanā
(41.2) un maskas aizpildes klauzulā (41.3).

---

## §42. Ēnas modelis pēc SLAMJAM parauga (2026-10-24)

### 42.1 Lietotāja piezīme
"ēna — ja salīdzina ar slamjam bildēm, tad ir liela atšķirība... taisām tumšāku".
Attēls: `02_mugura.jpg` (2000×2500, henley mugura no iepriekšējās partijas).

### 42.2 Mērījums, kas pārvērš gaumi skaitļos
Δ = 243 − L, vidēji pa visu siluetes perimetru (2000×2500 kadrā):

| attālums no malas | 1.5 | 2.5 | 4.0 | 6.0 | 8.0 | 10.0 | 14.0 | 18.0 px |
|---|---|---|---|---|---|---|---|---|
| **SLAMJAM (paraģis)** | 34.5 | 29.5 | 24.6 | 17.7 | 11.1 | 7.5 | 2.7 | 0.3 |
| **mūsu vecā** | 33.8 | 31.6 | 28.0 | 25.5 | 20.0 | 16.7 | 6.0 | 1.5 |

Secinājums: kontaktā mūsējā **jau bija gandrīz tikpat tumša**, bet stiepās
**divreiz tālāk** (30+ px pret 12-18 px). Tāpēc tā izskatījās kā liels gaišs
halo, nevis kompakta ēna. Problēma nav "par gaišu", bet **par platu**.

Papildu atšķirība: SLAMJAM ēna ir virzīta (pa labi 36.7 / apakšu 32.4, bet
kreisajā pusē 0.8 un augšā 8.6 — gaisma no augšas-kreisi). Mūsējā ir simetriska.
Virzienu **apzināti nemainījām**: tā ir ielikta oriģinālajos kadros, un
pārbūve no nulles radīja defektus (sk. 42.3).

### 42.3 Trīs nepareizās pieejas (visas pārbaudītas un atmestas)
1. **Nobīdīts + izpludināts siluets** (`blur(shift(alpha))`): ēna tiek nobīdīta
   prom no apakšmalas, tāpēc tieši zem malas paliek 7-9 px josla bez ēnas →
   gaišs rimbulis ap visu apģērbu.
2. **Vienmērīgs "kontakta rims" visapkārt** (12 līmeņi): dod uzlīmes kontūru —
   vienmērīgu līniju pa visu apģērbu, kādas dabā nav (paraugā kreisajā pusē 0.0).
3. **Vecās ēnas "izgriešana"** (`rgb + (δ_old − δ_new)(1−a)`) un
   **aizvietošana ar fona vērtību**: malas pikseļos jau ir sajaukts audums, tāpēc
   abas dod vai nu gaišu gredzenu, vai redzamu šuvi. Cēlonis: `cv2.inpaint` un
   normalizētā konvolūcija malā novērtē par 25-40 % par zemu.

### 42.4 Atrisinājums, kas iztur 1:1
Esošā ēna tiek **tikai mērogota** ar attāluma koeficientu (nekas netiek
aizvietots un nekas netiek izgudrots):

    f(d) = 1.10 · exp(−(d/10)^1.3)
    δ_new = δ_old · f(d),  izvade = rgb − (δ_new − δ_old)·(1−α)

- auduma pikseļos (1−α)=0 → **apģērbs paliek burtiski neskarts** (maks. izmaiņa
  2 līmeņi, un tie ir no JPEG pārakstīšanas);
- tā kā mērogo esošo, **nevar rasties** ne šuve, ne rimbulis, ne uzlīmes kontūra;
- rezultāts: 34.2 / 29.6 / 23.7 / 16.9 / 12.0 / 8.1 / 3.2 / 1.1 pret mērķi
  34.5 / 29.5 / 24.6 / 17.7 / 11.1 / 7.5 / 2.7 / 0.3.

Skripts: `restyle_shadow.py`. Fons paliek precīzi 243 (#F3F3F3).

---

## §43. Virzīta ēna kā SLAMJAM (2026-10-24, 2. iterācija)

Lietotājs izvēlējās variantu **"Vispirms virziens — taisi kā slamjam"**, t.i.
ēna jābūvē no jauna ar gaismu no augšas-kreisi, nevis tikai jāmērogo.

### 43.1 Pieeja, kas beidzot iztur 1:1
Esošā ēna netiek noņemta un aizstāta; tā tiek **mērogota ar diviem gludiem
faktoriem**, kas abi ir funkcijas no pozīcijas:

    f(d)   = a_mul · exp(−(d/L)^p)                # saspiež tuvāk malai
    wdir   = 1 + ēnas_puse·(w_side − 1) − ēnaspretējā·(1 − w_side)
    faktors = f(d)/f(0) · wdir                    # normalizēts uz 1.0 kontaktā
    izvade  = rgb − (δ_old·faktors − δ_old)·(1−α)

Normalizācija uz 1.0 kontaktā ir kritiska: bez tās `f(0)=a_mul` nozīmē
pastiprinājumu **arī pretējā pusē**, un ēna paliek simetriska.

### 43.2 Divas kļūdas, kas šeit tika noķertas
1. **Apgriezta gradienta zīme.** Maskas gradients rāda uz maskas iekšpusi, tāpēc
   ārējais virziens ir ar pretēju zīmi. Bez `gx, gy = -gx, -gy` svars
   pastiprināja tieši to pusi, kuru vajadzēja vājināt — kreisā mala kļuva
   tumšāka par labo. Pārbaudīts: kreisi `gx` jābūt negatīvam.
2. **Tokenizēta piesaiste malai** (`wdir` piespiests 1.0 pirmos 8 px) izslēdza
   virzienu tieši tur, kur tas visvairāk vajadzīgs — gaišā josla zem apakšmalas.
   Tagad piesaiste sākas no 0.3 px ar platumu 1.5 px.

### 43.3 Rezultāts (Δ pret fonu 243, malas vidējais)

| d px | 2 | 3 | 4 | 6 | 8 | 10 | 14 | 18 |
|---|---|---|---|---|---|---|---|---|
| kreisi | 20.9 | 15.6 | 11.6 | 6.7 | 4.7 | 3.6 | 2.2 | 1.9 |
| pa labi | 30.7 | 28.0 | 25.4 | 20.2 | 15.8 | 12.0 | 6.6 | 3.8 |
| augšā | 19.9 | 16.8 | 13.8 | 10.0 | 7.7 | 6.2 | 4.2 | 3.1 |
| apakšā | 37.7 | 34.9 | 31.9 | 25.3 | 19.1 | 13.9 | 6.8 | 3.3 |

Kreisā/augšējā puse tagad ir vismaz **divreiz vājāka** par labo/apakšējo, t.i.
ēna ir virzīta kā paraugā. Absolūtie lielumi ir nedaudz augstāki par SLAMJAM
biksēm, bet tās ir **melnas** — gaišam kreklam tāda pati Δ būtu pārāk agresīva.

### 43.4 Neskartais
- Audums 1:1 ir burtiski identisks oriģinālam (maks. izmaiņa 6 līmeņi, tie ir
  JPEG pārakstīšanā, ne modelī). Pārbaudīts ar 1:1 izgriezumu.
- Fons paliek precīzi 243 (#F3F3F3).
- Nekas nav izgudrots: tiek mērogota **esošā** ēna, tāpēc nevar rasties ne
  šuve, ne uzlīmes kontūra, ne jauns rims.

---

## §44. Metēnā ēna uz fona — PCSS modelis (2026-10-24, 3. iterācija)

### 44.1 Lietotāja piezīme
"ēna kas krīt no apģērba uz fonu, šobrīd tā nav dabiska, pārāk pelēka, šaura,
kaut kas nav kā reālajā dzīvē".

Mērījums apstiprināja, ka tā nav gaumes lieta — esošā ēna **nomira 20-30 px
attālumā**, tālāk fons bija pilnīgi tukšs (Δ = 0.0 jau pie 30-40 px). Tāpēc tā
izskatījās kā šaura pelēka josla, kas pieguļ siluetam.

Iemesls: §42/§43 pieejas ņēma **esošo** ēnu un tikai mērogoja to. Esošā ēna
pati ir šaura, tāpēc arī pēc mērogošanas palika šaura.

### 44.2 Modelis
PCSS (percentage-closer soft shadows) — tāpat kā 3D renderētājos. Gaisma ir
**laukums**, nevis punkts, tāpēc katrs fona punkts redz daļu avota:

    ēna(p) = (1/N) · Σ_k M(p + d + r_k),   r_k = punkti uz gaismas diska

Dabiskās īpašības, kas izriet no modeļa (nevis jāpieliek ar roku):
- blīva ēna pie kontakta (punktu klāj gandrīz visi paraugi);
- mala kļūst **mīkstāka ar attālumu** (jo tālāk, jo lielāku daļu avota redz);
- plašs izpletums — nobīde + avota rādiuss;
- gradients, nevis vienmērīgs pelēks lauks.

Papildu **astes slānis** (otrs PCSS ar 2.4× lielāku avotu un 1.45× nobīdi,
svars 0.26-0.30): viena slāņa ēna nomirst 40 px un izskatās uzzīmēta; reālai
ēnai ir gara, vāja aste.

### 44.3 Divi noteikumi, bez kuriem modelis nestrādā
1. **Nobīdei jābūt lielākai par avota rādiusu** (`ox, oy > spread`). Citādi
   ēna pie kontakta *vājinās* un tālāk *pastiprinās* — rodas balta josla tieši
   pie auduma. Tieši šī kļūda sabojāja pirmos variantus (spread=32, ox=24).
2. **Aste jānovirza vēl vairāk gaismas virzienā**, citādi tā izplūst arī pret
   gaismu (kreisajā pusē) un ēna atkal kļūst simetriska.

### 44.4 Rezultāts (Δ pret fonu 243)

| d px | 5 | 15 | 30 | 50 | 80 |
|---|---|---|---|---|---|
| kreisi | 8.2 | 3.0 | 2.0 | 1.4 | 0.9 |
| pa labi | 39.2 | 31.3 | 20.0 | 8.4 | 3.8 |
| augšā | 12.6 | 6.8 | 4.4 | 2.3 | 1.3 |
| apakšā | 46.2 | 41.5 | 28.5 | 11.5 | 4.1 |

Ēna ir **4-5× stiprāka** pa labi/apakšā nekā kreisi/augšā, sniedzas ~80 px
(vecā: 20-30 px), un tās kritums ir monotons — bez plakanas joslas.

### 44.5 Neskartais
- Audums netiek aiztikts nemaz (`auduma_izmaiņa = 0`): ēna tiek likta tikai
  tur, kur α < 1, un tuvā 2 px mala paliek oriģinālā.
- Fons paliek precīzi 243 (#F3F3F3).
- Vecā ēna netiek noņemta: abas apvienotas ar **p-normas gludo maksimumu**,
  nevis `max()`, lai pāreja būtu nepārtraukta.

Skripts: `cast_shadow.py`. Fails: `02_mugura_ena_metena.jpg` (sha f01c567d611387a4).

---

## §45. Neēnotā līnija pirms ēnas — cēlonis un labojums (2026-10-24)

### 45.1 Lietotāja piezīme
"ir palikusi neieēnota līnija pirms vispār ēna sākas, būtībā ēnai ir jāsākas
zem krekla un nav jābūt kaut kādam tukšumam pirms ēnas sākumā, un tā ir par
gaišu kopumā".

### 45.2 Cēlonis (divi slāņi, abi bija jālabo)
1. **`(1 − α)` faktors.** `α` malā ir ~0.5, tāpēc pēdējie 1-2 px tika noēnoti
   tikai pa pusei. Starp audumu un ēnu palika gaiša līnija. Ēnas maskēšanai
   jālieto tikai attāluma maska `w` (kas jau ir 0 auduma iekšpusē), nevis α.
2. **Mīkstā auduma mala.** Auduma vizuālā mala (kur tumšais adījums beidzas)
   ir ~3 px *pirms* maskas robežas — starp tām ir gaišs apmales rims, kas
   pieder apģērbam, nevis fonam. Ja ēnu sāk no maskas robežas, šis rims paliek
   gaišs. Fizikāli tas arī nav pareizi: apģērba apakšējā mala ir kontaktā ar
   papīru, tāpēc pēdējie 1-2 px ir ēnā.

### 45.3 Labojums
- `w` tiek būvēts no **2 px sašaurinātas** siluetes (`cv2.erode`, 5×5), tāpēc
  ēna sākas dažus px auduma iekšpusē, kur ir īstais kontakts;
- ēnas maskēšana notiek tikai ar `w`, bez `(1−α)`;
- auduma iekšpuse aiz 9 px no malas paliek neskarta (vid. izmaiņa **0.15**,
  maks 8 līmeņi, un tie ir JPEG).

### 45.4 Kopējais tumšums
`peak` pacelts 48 → 96 (`spread=28, ox=52, oy=60`). Ēna pie kontakta tagad ir
Δ ≈ 100 (L ≈ 143) pret fona 243, un tā saglabā gradienu līdz ~90 px.

Pārbaudīts 5× tuvumā: pāreja audums → ēna ir **tieša** (211 → 160 vienā
pikselī), bez gaišas joslas. Fails: `02_mugura_ena_metena.jpg`
(sha 9597a617f45eabce).

## §46. Ēnas rādiuss samazināts (2026-10-24)

Lietotājs: "samazini rādiusu, pārāk gara".

Saspiests no `spread=28, ox=52, oy=60, tail=0.30` uz
`spread=14, ox=26, oy=32, tail=0.14` (peak paliek 96 — **kontakta tumšums
nemainījās**, Δ 102.9 visos variantos; mainījās tikai ēnas garums).

| d px | 1-4 | 4-10 | 10-18 | 18-28 | 28-45 | 45-70 |
|---|---|---|---|---|---|---|
| Δ | 29.4 | 14.9 | 5.1 | 2.7 | 1.0 | 0.1 |

Ēna tagad nomirst ~30-35 px attālumā (iepriekš ~90 px). Saglabātais: ēna
sākas tiešā kontaktā (bez gaišās līnijas, sk. §45), ir tumša pie auduma un
pakāpeniski izplūst. Fails: `02_mugura_ena_metena.jpg` (sha 3d106d7dec67c04f).

---

## §47. Vai var pārnest oriģinālo ēnu no oriģinālā foto? (2026-10-24)

### 47.1 Atbilde
**Tehniski jā, un metode ir uzrakstīta** (`real_shadow.py`). Bet ir divi
ierobežojumi, kas jāzina pirms lēmuma:

1. **Oriģinālie faili lielākoties vairs neeksistē.** Grupas tiek dzēstas pēc
   `.zip` lejupielādes (§ LOOP.md 8), tāpēc Henley kadriem (t.sk. `02_mugura`)
   oriģināla vairs nav. Saglabājies ir tikai `uploads/MVIMG_20261020_161031.jpg`
   (džinsi, 4096×3072).
2. **Pašā oriģinālā ēnas praktiski nav.** Izmērīts uz džinsiem (sk. 47.2):
   vienīgā "ēna" ir plāna tumša kontūra 10-25 px platumā, un to nav iespējams
   automātiski atšķirt no papīra krokām.

### 47.2 Mērījums, kas to pierāda
Papīra gaišums pēc attāluma no apģērba (tikai virzienos ar ēnu, uzpūsta maska,
lai izslēgtu maskas nepilnību):

| virziens | 3-10 px | 10-25 | 25-50 | 50-100 | 100-200 | 200-400 |
|---|---|---|---|---|---|---|
| kreisi | 167.7 | 172.6 | 175.9 | 178.6 | 188.3 | 190.8 |
| pa labi | 202.6 | 200.9 | 198.4 | 195.2 | 193.6 | 190.9 |
| augšā | 215.3 | 213.7 | 212.1 | 211.7 | 212.8 | 211.3 |
| apakšā | 167.9 | 170.9 | 171.1 | 173.5 | 173.2 | 169.9 |

Kreisajā pusē starpība +23.1 līmenis **izskatās** kā ēna, bet, izgūstot ēnas
karti un ierobežojot to 1-110 px joslā, paliek tikai **plāna kontūra ap
siluetu** — t.i. tā ir papīra loka/kroka ēna, nevis gara metēnā ēna. Tālu no
apģērba (>200 px) "ēnas" lielums ir tāds pats kā pie apģērba (abi 14.2) →
to nevar atšķirt pēc lieluma.

Trijos mēģinājumos izgūt tīru ēnu:
  * 2. kārtas virsmas fits — papīra krokas to izgāž;
  * liela rādiusa izlīdzinājums — "apēd" gan gradientu, gan ēnu;
  * rolling ball (lokālais gaišākais papīrs) — vislabākais, bet joprojām
    atstāj kroku "ēnas", kas fonā izskatās kā netīrumi.

### 47.3 Kā pareizi dabūt īsto ēnu
Ir divi ceļi, abi labāki par pārnešanu no veca foto:

1. **Fotografēt ar izteiktu metēno ēnu jau uzņemšanā** — vienpusējs gaismas
   avots no sāna, papīrs nevis gluds bet ar vienu lielu loku. Tad ēna ir īsta
   un to var izmērīt tieši (nav jāatjauno).
2. **Sintētiskā ēna (pašreizējā, §44-46)** — tā ir tīra, bet nomirst 30-35 px.
   Reāla ēna parasti ir 60-150 px gara. Ja vajag garāku dabiskumu, jāpalielina
   `spread`, nevis jāņem no foto.

### 47.4 Secinājums
Pārnese no oriģināla **ir iespējama tikai tad, ja oriģinālā tiešām ir metēnā
ēna**. Konkrētajos Henley/jeans kadros tādas nav, tāpēc sintētiskā ēna šobrīd
ir pareizā izvēle. Ja turpmāk gribam īstu ēnu — tā jāiegūst uzņemšanā.
---

## §48. Vans chino: GATE_R kritums no izvades asināšanas; papīra noplūde 0; ēnas virziena audits (2026-10-24)

### 48.1 Problēma
Jaunā Vans grupa Attempt 1 deva maker 4/4, bet checker tikai 2/4 PASS.
Abi tuvplāni krita **tikai GATE_R**: fore_p99 26.0 (`MVIMG_20261020_161944`)
un 28.0 (`MVIMG_20261020_161959`) pret limitu 24.0. Visi citi piemērojamie
vārti izgāja, ieskaitot A2 `max_diff=0`, B far background 100.0%, H malas
alfu un papīra testus: L advisory verdict PASS ar `leak_px=0`, P ar
regions=0 / px=0 / max_depth_px=0.0 visām 4 bildēm.

### 48.2 Ko mērīju (cēlonis izolēts)
- Nobīde atmesta: ±1 px nobīde tuvplānos p99 paceļ līdz 87-155, bet bez
  nobīdes tie ir 26/28; tātad references un PARAUGS ģeometrija sakrīt.
- JPEG viens pats atmests: references -> JPEG q95 dod fore_p99=7 abiem
  tuvplāniem.
- Asināšana pierādīta: references -> UnsharpMask (r=1.4, 42%, thr=3) bez
  JPEG dod 26/27; ar JPEG dod 26/28 — precīzi checker skaitļi. Augsta
  gradienta auduma pikseļos p99 ir 33/36, zema gradienta pikseļos 12/12:
  atšķirību koncentrē pinuma/rāvējslēdzēja augstfrekvences tekstūra.
- Sweep simulācija checker references telpā 42% gadījumā visām 4 bildēm
  precīzi atkārtoja checker fore_p99/fore_p95/edge_ratio. Grupas
  maksimālais p99: 42%->28, 35%->24 (bez rezerves), 30%->21,
  25%->18, 20%->15, 0%->7.

### 48.3 Ko mainīju
- `workflow_v2.py:1193`: globālā profila `output_sharpen.percent` 42 -> 25;
  radius 1.4 un threshold 3 nemainīti. Koda sha256(16):
  `2829a92a582b0f92` -> `b9484cdb0a0afa64`.
- GATE_R slieksnis 24.0 **netika pārvietots**, lai gan checker komentārs
  pieļauj pārkalibrēšanu citai tekstūrai. Šeit bija izmērāms likumīgs
  labojums pašā izvadē: samazināt asināšanas radīto novirzi no MASTER.
- Palaists `--attempt 2 --rerender-saved`. Pilniem kadriem maskas/ALPHA/
  MASTER bitiski nemainījās. Tuvplāniem konstatēta rerender blakne:
  `decontaminate_rim` uz saglabātās maskas noņēma vēl 102 868 px un
  44 627 px (A1 bija noņemti 109 568 px un 56 690 px). Tas jāuzskata par
  zināmu ne-idempotenci: atkārtoti rerenderi var turpināt šaurināt masku.

### 48.4 Kas mainījās skaitļos
- Checker Attempt 2: **4/4 PASS**. GATE_R fore_p99 tagad 6.0 / 7.0 /
  17.0 / 18.0 (secībā 161746, 201332, 161944, 161959), edge_ratio
  1.181 / 1.220 / 1.232 / 1.231 — pilnā sakritībā ar 25% simulāciju.
- A2 kodolos joprojām `max_diff=0`; tuvplānu core_px pēc papildu
  decontamination ir 6 479 363 un 8 997 479. B=100.0%, H
  core_opaque/outside_clear=100.0%/100.0%, bad_partial_px=0.
  L/P papīra noplūde joprojām 0. Laiki 10.048-16.755 s (< 25 s).
- Gala PARAUGS sha256(16): `e370ddff20459b70`, `ef7e836cbdcd64f3`,
  `9dd96f1b6deebffb`, `a297c6bf7bd8f38e` (secībā augstāk).
  Kolāža `fae2ae65bcac533a`.

### 48.5 Ēnas mērīšanas piezīme un neatrisinātais virziens
- `measure_shadow.py` uz šīm bildēm rāda kodola Δ 7.0, bet Slam Jam
  paraugiem tikai 4.0/3.0. Tas nav salīdzināms ar §46 kontakta Δ~100:
  skripta siluete sākas ar `gray < bg - 12`, tāpēc tumšākā ēnas daļa tiek
  ieskaitīta apģērbā, un gredzenā paliek tikai gaišā aste. Šo skaitli
  nedrīkst citēt kā kontakta Δ bez maskas attāluma audita.
- Pēc faktiskās `*_PARAUGS_MASK.png` attāluma transformas pilnim kadriem
  E/W/N/S vidējais Δ <=40 px joslā ir 26.3/14.7/14.8/16.0 un
  26.4/14.8/14.9/15.8. Paraugiem (audums ar slieksni L<150) tas ir
  34.8/1.1/1.9/34.2 un 17.8/1.5/1.8/16.1. Mūsu krituma garums sakrīt
  (28-45 px vidēji Δ=0.8), bet W/N ambient atlikums ir izmērāma
  atšķirība no parauga. Vizuālais E lēmums paliek lietotājam.
- `/tmp` eksperiments: `restyle_shadow` W/N samazināja tikai līdz ~10.2;
  `cast_shadow` S2 pacēla E/S līdz ~46/42, bet simulētais GATE_R
  bg_p99 kļuva 18-25 (limits 4.0) un tālais fons vairs nebija 100%=243.
  Secinājums: vēsturisko cast S2 nedrīkst mehāniski likt virsū v2.1
  kanoniskajām izvadēm, ja pēc tam prasa checker PASS. Ja lietotājs ēnu
  noraida, virziens jālabo integrēti renderī (MASTER+PARAUGS vienādi),
  nevis ar pēcapstrādi tikai JPEG failam.
---

## §49. Jauns studijas ēnas modelis no nulles (kontakta AO + PCSS redzamība), kalibrēts pret Slam Jam (2026-10-24)

### 49.1 Problēma un mērījums
Lietotājs Attempt 2 ēnu nepieņēma un uzdeva ēnas modeli izveidot no 0,
izmantojot profesionālus piemērus no interneta. Vecā workflow ēna
(`shadow_bg`: eksponenciāls kritums + SHADOW_AMBIENT=0.55 visapkārt)
pēc faktiskās novietotās maskas deva pilniem kadriem W/N vidējo Δ
<=40 px joslā 14.7-14.9 (2-4 px joslā 35.3-36.0), kamēr diviem Slam Jam
pilniem kadriem W/N ir 1.05-1.93 (2-4 px: W 1.4/2.6, N 5.7/1.4). SE pusē
vecais modelis bija tuvu paraugam, bet virziens nebija vienpusīgs.

Parauga mērķis šajā sadaļā ir divu pilno Slam Jam kadru vidējais ar
auduma siluetu pēc sliekšņa L<150 (tuvplānu paraugu sliekšņa maskas
skaitliskai kalibrācijai neder: velveta gaišās ribiņas masku sašķeļ un
"ārpus maskas" zonās nonāk pats audums ar Δ~200; tie izmantoti tikai
vizuāli). Mērķa tabulu sk. PROGRESS §51.

### 49.2 Profesionālie principi (avoti)
- PCSS: penumbras platums `w = (dReceiver - dBlocker) * wLight / dBlocker`;
  ēna kontaktā asāka, tālāk mīkstāka (NVIDIA, shadow_PCSS.pdf).
- E-komercijas prakse: viens gaismas virziens visam katalogam; ja gaisma
  ir augšā-kreisi, ēna krīt apakšā-labi; mīkstas malas, pelēka nevis melna
  ēna, īsa un tumšākā kontaktā (PixelPrep e-komercijas ceļvedis).
- Kontakta ēna un metēnā ēna ir divas atsevišķas komponentes: kontakta
  ir maza/tumša/tuva, metēnā ir lielāka/mīkstāka/tālāka (IT-S; Pikes:
  kontakta izplūdums ~2-6 px uz 2000 px attēla). Pilnu URL sarakstu sk.
  PROGRESS §51.

### 49.3 Modelis (`loop.studio_shadow_bg`, `studio_v1_contact_pcss`)
- Vispirms tika izmēģināta virziena ekstrūzija (nobīdītu siluetu svērta
  summa). Tā likvidēja NW halo, bet SE palika par vāju (labākais RMSE
  14.68; SE 61.9/42.7/25.0/11.0/2.0 pret mērķi 79.6/66.5/42.9/18.7/3.05),
  tāpēc atmesta: normalizācija pa nobīdes soļiem nav gaismas redzamība.
- Gala modelis: siluets projicēts par 16 audekla px 43° virzienā;
  redzamība V ir projicētā silueta izplūdums ar sigma(d)=0.9+0.28*d
  (d = attālums ārpus maskas; līmeņi 0.8/1.8/3.2/5.0/7.5 px,
  log-interpolācija, aprēķins pusizšķirtspējā). Metēnā daļa
  `0.32 * V^0.80`; kontakta AO `0.10 * exp(-d/1.4)`; abas apvienotas
  multiplikatīvi transmisijā. Logs 42->58 px padara tālo fonu tieši 243.
- Kalibrācija bija režģa meklēšana (leņķis, nobīde, sigma pieaugums,
  peak, gamma, kontakta peak/lambda) pret mērķa E/S/W/N×attāluma
  vidējiem. Labākais prototips: RMSE 1.69. Parametri fiksēti kā
  `STUDIO_*` konstantes `loop.py`; koda sha256(16) `fe7bc60d892ca0d5`
  (loop), `d2c84350ffcc40a8` (workflow), `a5339e97f63edc2e`
  (rebuild_master), `c96f11a89ccdad07` (closeup).
- Integrācija ir renderī, nevis JPEG pēcapstrādē: MASTER to saņem ar
  `canvas_scale=para_scale`, PARAUGS ar 1.0. Tāpēc checker GATE_R
  references rekonstrukcija no MASTER redz to pašu ēnas ģeometriju un
  bg_p99 paliek 0. Tas ir pretstats §50 izmērītajam cast S2
  pēcapstrādes eksperimentam, kur bg_p99 simulācijā bija 18-25 > 4.

### 49.4 Attempt 3 rezultāts
- Rerender ar `--no-decontam` tuvplāniem izolēja tikai ēnu: visas
  maskas/ALPHA/PARAUGS_MASK pret A2 ir bitiski SAME (12/12), LUT
  identisks (maks. starpība 0), A2 kodola max_diff joprojām 0.
- Checker 4/4 PASS; GATE_R fore_p99 nemainījās (6/7/17/18), bg_p99=0,
  B=100.0%, laiki 9.741-14.604 s. Gala ēnas agregāts pilniem kadriem:
  E 78.1/72.0/46.9/19.0/4.0/0; S 75.0/69.0/43.7/17.2/3.5/0;
  W 2.5/1.1/0.2/0.1/0/0; N 1.7/0.6/0/0/0/0; kardinālais RMSE pret
  paraugu = 1.85 Δ līmeņi. Tuvplāniem nav S sektora (audums līdz apakšai);
  161959 N/W atklātajās malās paliek tikai kontakta AO (N 2.4/1.2/0.2/0.1),
  kas ir modeļa apzināta sekas: metēnā ēna atrodas zem apģērba uz SE.
- Ierobežojumi: virziens tagad ir fiksēta studijas konstante, nevis katrā
  avotā mērīts leņķis; tas ir kataloga konsekvences lēmums pēc parauga.
  Kalibrācija balstās uz 2 pilniem paraugiem ar sliekšņa siluetu, tāpēc
  2-4 px joslā iespējama ~1-2 px malas nobīdes kļūda. Modelis nav
  lietotāja apstiprināts, kamēr nav nospiesta poga pie A3 kolāžas; ja to
  noraida, jāmaina viens lielums (virziens/peak/nobīde) un jāpārmēra ar
  šo pašu sektoru×attāluma tabulu, nevis jāslēdz atpakaļ ambient halo.

## §50 — Henley grupa (2026-10-24): plate ceļš baltajam makro kadram
- Grupa: 2 pilni kadri ISNet + 2 tuvplāni `isnet_pad_retry` izgāja
  pirmajā piegājienā (checker 4/4). Birkas makro `124406358` krita
  visos ceļos (ISNet 0.0501, retry 0.0462, plate 0.0219) — godīgs
  `needs_review` STOP, nevis klusa slikta maska.
- Cēloņa ķēdes pierādījums (PROGRESS §68-§70): (1) plate Otsu
  slieksnis 13.73 > auduma E mediāna 7.06 ekstrēmas astes dēļ;
  enkurētais fallback (ģeom. vid. no papīra 2.24 / auduma p90 9.38
  = 4.58) atgūst segumu 0.8696, kontroles kadros bitiski identisks.
  (2) `bg_inside` bez krāsas nosacījuma vafeļu ēnu līnijas sauca
  par fonu (0.0284); ar papīra L* logu 0.0145, bet papīra krāsas
  pleķis sintētikā joprojām 0.1719 -> noraidīts. (3) GATE_P
  bloķēja audumā ieslēgtus ielokus pie malas (dE 9.6-13.9,
  `garment_fpr=0.196`); ķīļa paraksts tagad ir "nav ieslēgts",
  sintētiskais ķīlis (dE 0.46) joprojām krīt.
- Pēc trim pierādītiem precizējumiem: checker 5/5 PASS (exit 0),
  lietotājs apstiprināja kolāžu, ZIP verificēts pret checker
  hashiem. Mācība: baltam audumam uz pelēka papīra krāsa neatdala
  neko (L* 58 pret 64) — vienīgais signāls ir tekstūras MĒROGA
  izvēle, un katrs vārti, kas balstās uz "gluds = papīrs", makro
  kadram vispirms jāpārbauda pret auduma paša gludajām daļām
  (birka, aproce, ieloku ēnas).
