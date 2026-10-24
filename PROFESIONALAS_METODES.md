# Profesionālās prakses audits — ko dara Holivudas/Nuke un produktu retušas līmenis

**Datums:** 2026-10-23
**Mērķis:** pirms visas sistēmas debuga pārbaudīt, kā fona maiņu dara profesionāļi (Nuke compositing, Photoshop produktu retuša, ghost-mannequin studijas), un atrast, ko esam palaiduši garām vai varam aizņemties.
**Metode:** 6 meklējumu kārtas (Foundry/Nuke rokasgrāmata, Dune VFX supervizors, Adobe, produktu retušas blogi, marketplace specifikācijas) + **mērījumi uz mūsu pašu bildes**, lai katru tehniku pārbaudītu, nevis pieņemtu uz ticību.

> Princips, kas vadīja šo auditu: **profesionāļa padoms nav pierādījums mūsu bildei.** Katra tehnika tika pārbaudīta ar skaitli uz `PXL_20261022_124339475`. Kur mērījums neapstiprināja problēmu, tehnika noraidīta — arī tad, ja tā ir "pareizā" profesionālā prakse.

---

## 1. Kopsavilkums vienā rindkopā

No divpadsmit pārbaudītajām profesionālajām tehnikām **viena ir īsts, izmērīts defekts mūsu izvadē**: sintētiskā ēna krīt **~60° nepareizā virzienā** attiecībā pret bildes faktisko apgaismojumu. Tas nav gaumes jautājums — tā ir fiziski neiespējama aina (ēna pret gaismu), un profesionālajā literatūrā tai ir savs nosaukums: *"divas saules"*. Pārējās tehnikas vai nu mums jau ir, vai arī mērījums rāda, ka tās **radītu defektu, kas oriģinālā neeksistē**. Papildus atrasts viens strukturāls iemesls, kāpēc `L_TOL` vispār nācās kalibrēt ar roku.

---

## 2. Galvenais atradums: ēnas virziens

### 2.1 Ko mērījām

Trīs neatkarīgas metodes, jo pirmā izrādījās piesārņota ar papīra apgaismojuma gradientu:

| # | metode | ēna krīt uz | gaisma no | piezīme |
|---|---|---|---|---|
| 1 | neapstrādāts virziena skenējums no kontūras | 135° | 315° | **piesārņots** — papīrs gaišāks centrā, tumšāks malās |
| 2 | apģērba četrstūru tests (kreisi/labi, augšā/apakšā) | 135° | 315° | gaišāk pa labi (−5.4 L*) un augšā (+3.2 L*) |
| 3 | **lokālais kontrasts** L(10px) − L(45px), vignete atcelta | 105–120° | 285–300° | gradientu atceļ |
| 4 | **fona plāksne ar inpaint** (IBK principa būtība) | **135°** | **315°** | visuzticamākais — sk. 2.1a |

### 2.1a Kāpēc metode #4 ir uzticamākā

Metodes #1–#3 cieta no tā, ka papīrs kadrā nav vienmērīgs: fons tuvu apģērbam ir RGB ≈ 156–160, tālu un stūros ≈ 133. Jebkurš mērījums, kas salīdzina "pie malas" ar "tālu", sajauc ēnu ar šo gradientu.

Metode #4 to atrisina tā, kā to dara IBK: **aizpilda apģērbu no apkārtējā papīra** (`cv2.inpaint`, rādiuss 31), izgludina iegūto virsmu (σ=70) un atņem to no oriģināla. Rezultāts ir tīrs ēnas signāls — fona plāksnes reziduāls ar std **2.69 L\***.

```
   135°   -6.36 L*   n= 92     <- tumšākais
   120°   -4.75 L*   n=372
   105°   -2.28 L*   n=478
   ------------------------------------
   300°   +0.82 L*   n=454     <- gaišākais
   270°   +0.66 L*   n=372
   255°   +1.05 L*   n=244
```

Ēna uz **120–135°**, gaisma no **300–315°**. Visas četras metodes tagad saskan (izņemot #1 piesārņojumu). **Izvēlēts 125°** — abu spēcīgāko binu vidus.

### 2.1b Vizuālais apstiprinājums

Izgriezums no oriģināla pie apģērba labās malas: papīrs **vienmērīgs, ēnas praktiski nav**. Izgriezums gar apakšējo malu: plata, mīksta ēna, kas seko kontūrai. Tas apstiprina mērījumu ar aci — vecais 54° (lejup-pa labi) lika ēnu tieši tur, kur oriģinālā tās nav.

```
   120°   -4.96 L*   n=219     <- tumšākais pie malas
   105°   -4.84 L*   n=282
    90°   -3.90 L*   n=321
  ------------------------------------------------
   315°   +2.40 L*   n=341     <- gaišākais pie malas
   300°   +2.67 L*   n=272
   270°   +2.05 L*   n=221
```

Ēna uz **105–120°** (lejup, nedaudz pa kreisi). Gaisma no **285–300°** (augšup, nedaudz pa labi). Tas saskan ar #2 un ir fizikā konsekventi ar studijas apgaismojumu no augšas.

### 2.2 Mūsu kods

```python
# loop.py:408, loop.py:496, workflow_v2.py:1155  — trīs identiskas kopijas
shadow_bg(binary.shape, binary, dx=25, dy=35, blur=35, strength=0.26)
```

`dx=+25, dy=+35` = **54°**. Faktiskais: **~112°**. **Atpalšana ≈ 60°.**

```
          mūsu: 54°  ↘ (lejup-pa labi)
      faktiskais: 112° ↙ (lejup-pa kreisi)
      gaisma: 292°    ↗ (no augšas-pa labi)
```

Ēna krīt **tajā pašā pusē, no kuras nāk gaisma**. Apģērba labā puse ir gaišākā (mērīts: +5.4 L*), bet ēna tiek likta tieši zem tās pašas labās puses.

### 2.3 Kāpēc tas ir defekts, nevis gaume

Ghost-mannequin studiju ceļveži to nosauc tieši ([snappyit.ai](https://snappyit.ai/blog/ghost-mannequin-product-photography)):

> *"If a light was accidentally angled differently, the shadow falls in a slightly different direction than the shadow on the exterior. The result is a mannequin picture where the lighting feels contradictory, **as if two different suns are illuminating the same garment**."*

Cilvēks to nespēj artikulēt, bet smadzenes to reģistrē kā "kaut kas nav pareizi". Tā ir tieši tā kategorija, ko mēs gribam izslēgt pirms nodošanas.

### 2.4 Ieteiktais labojums

Saglabājot ēnas **lielumu** (tagad `hypot(25,35)=43`) un samainot virzienu:

```python
SHADOW_ANGLE_DEG = 125.0     # bija (dx=+25, dy=+35) = 54°
SHADOW_STRENGTH  = 0.26

def shadow_dir(dist_px):     # |d| tiek saglabāts, mainās tikai leņķis
    a = math.radians(SHADOW_ANGLE_DEG)
    return int(round(dist_px*math.cos(a))), int(round(dist_px*math.sin(a)))
#  avota mērogā:  shadow_dir(43.01) -> (-25, +35)
#  audekla mērogā: shadow_dir(25.62) -> (-15, +21)
```

**Viena vieta, ne trīs.** Pašlaik tie paši burta skaitļi ir nokopēti 3 failos — tāpēc vienkārša virziena maiņa šodien būtu riskanta. Konsolidēt vienā nosauktā konstantē (`SHADOW_DIR`) un izsaukt no visām trim vietām.

### 2.5 Statuss — IZDARĪTS 2026-10-23

Labojums ieviests un pārbaudīts: apģērba kodolā **0.00 %** izmaiņu, fonā tālāk par 120 px — **0.0 %**; mainījies tikai ēnas apgabals. Maska nemainīta (`744890376d…` / `48a207ed4d…`). Divi palaidieni dod bitu identisku rezultātu (`663179f3…`). Testi 11/11.

**Blakusefekts, kas jāzina:** apģērbs ir pieskarts kadra kreisajai malai, tāpēc ēna 125° virzienā daļēji aiziet aiz kadra. Redzamā ēna kļuva vājāka (laukums 110 842 → ~51 000 px). Tas ir fiziski godīgi — tāda pati aiziešana notiek arī oriģinālā —, bet nozīmē, ka šai bildei ēna vairs nav tik izteikta.

Ēnas **lielums** ir pareizs — pārbaudīts: oriģinālā fons 5→25 px no malas gaišo par 12 L* (181→193), mūsu izvadē 181→193, t.i. **vienādi**. Nepareizs ir tikai **virziens**. Tāpēc labojums neskar to, ko tu jau akceptēji: malas, segumu, ēnas stiprumu.

---

## 3. Strukturālais atradums: kāpēc `L_TOL` nācās kalibrēt ar roku

Papīrs kadrā **nav vienmērīgs**: tuvu apģērbam fons ir RGB ≈ 156–160, tālu/stūros ≈ 133. Tas ir **~8–10 L\* pāri kadram** — normāla softbox gaismas atkrišana.

Mūsu segmantācija izmanto **vienu globālu papīra līmeni** (`_paper_level` → 66.1 L*) un **vienu globālu tolerances logu** `L_TOL = (-14, +8)` = 22 L* plats.

> **Fona dreifs (~10 L*) apēd ~45 % no tolerances budžeta.**

Tas izskaidro, kāpēc `L_TOL` vajadzēja meklēt ar roku (−18 → caurums paliek; −14 → caurums pazūd; −10 → segums 1.0). **Tas, ka konstante bija jāmin, ir pierādījums, ka modelis ir nepareizs — nevis ka konstante ir grūti uzminama.** Mūsu paša princips saka: *izminēta kalibrācijas konstante nav pierādījums.*

Profesionālā atbilde uz tieši šo problēmu ir **IBK** (Image Based Keyer, Paul Lambert, Dune) — lietot **fona plāksni ar tā krāsu variāciju**, nevis vienu krāsas paraugu. Foundry dokumentācija to formulē kā risinājumu tieši nevienmērīgam fonam.

**Praktiskā versija mums (IBK-lite):** aizstāt globālo `_paper_level` skalāru ar **lokālu, gludu papīra modeļa karti** (`gaussian_filter` uz fona maskas, vai zema grāda virsmas fits), un toleranci piemērot pret *lokālo* līmeni, nevis globālo.

**Ko tas dotu:** `L_TOL` beigtu būt jākalibrē ar roku katrai bildei. Tas ir vienīgais priekšlikums šajā auditā, kas noņem minētu konstanti — un tāpēc **arī vienīgais, kas tieši atbilst mūsu dizaina principam.**

**Cena:** vidēja. `plate_segment.py` jāpārraksta `_paper_level` → `_paper_map`. Jāpārbauda, ka GATE_A2/B/C/D nemirst. Nav šodienas defekts — šodienas bilde iztur ar globālo slieksni.

**Statuss: P2, izmeklēt pēc ēnas virziena.**

---

## 4. Pilna tabula ar spriedumiem

| # | Tehnika (profesionālā prakse) | Mums | Spriedums | Pamatojums |
|---|---|---|---|---|
| 1 | **Ēnas virziens atbilst gaismai** | bija 54° → **125°** | **IZDARĪTS** | izmērīts ~70° defekts; 2. sadaļa |
| 2 | **IBK / lokāla fona plāksne** | globāls `L_TOL` | **PIEŅEMT (P2)** | fona dreifs 8–10 L* pret 22 L* logu; 3. sadaļa |
| 3 | `shadow_bg` kā viena vienība 3 failos | 3 kopijas | **PIEŅEMT** | higiēna; bez tā #1 ir riskants |
| 4 | **Kontakta ēna** (2–6 px, tumšākā, asā) | nav | **NORAIDĪT** | sk. 5.1 — oriģinālā tādas nav |
| 5 | **Graudu saskaņošana** (re-grain) | fons 0.06 pret apģērbu 17.17 = 268× | **NORAIDĪT** | sk. 5.2 — plakans fons ir prasība |
| 6 | **Light wrap** (atstarotā gaisma) | nav | **NORAIDĪT** | sk. 5.3 — mērījums: noplūdes nav |
| 7 | **Screen subtraction** (fona RGB atņemšana malās) | nav | **NORAIDĪT** | nav krāsu noplūdes (ΔR≈ΔG≈ΔB); nav ko atņemt |
| 8 | **Core + edge + light wrap, 3 caurlaidēm** | 1 maska + distance feather | **DAĻĒJI, atstāt** | lietotāja screenshot bija spec; `_refine_edge` noraidīts |
| 9 | **Edge extend = normalizēta konvolūcija, krauta pakāpeniski** (2,4,8…px) | tuvākā pikseļa distance-transform, `max_dist=8` | **P3, nosacīti** | kāpnes lielos attālumos; bet defekts nav izmērīts — sk. 5.4 |
| 10 | **Detaļu atjaunošana pēc extend** (Merge min/max) | nav | **NORAIDĪT šobrīd** | rievojumu atjaunošana = ģeometrijas izgudrošana |
| 11 | **Frekvenču separācija** (low/high) | `texture_map`, lokālais std 7px | **JAU IR** | tā ir tā pati saime; strādā (`plate_texture`) |
| 12 | **Grain reģistrācija pa spilgtumu** | — | **NORAIDĪT** | fons ir digitāls pildījums pēc definīcijas |

---

## 5. Noraidītās tehnikas — ar mērījumu, ne ar viedokli

### 5.1 Kontakta ēna — **nav, un nevajag**

Profesionālā literatūra: kontakta ēna 2–6 px, tumšākā un asākā, tieši pie saskares līnijas; cast ēna ar blāvēšanu.

**Mērījums oriģinālā** (profils zem malas, d = attālums px):

```
d=1:163  d=2:182  d=5:181  d=8:181  d=12:183  d=18:186  d=25:193
```

Kritums 163→182 notiek **vienā pikselī** — tas ir malas antialiasing, nevis ēna. Pēc tam 181→193 pāri 20 px — **lēns, mīksts gradients**, bez asa pleca.

> Šai bildei oriģinālā **nav izteiktas kontakta ēnas**. Pievienot 2–6 px asu kontakta terminu nozīmētu **izgudrot ēnu, kas avotā neeksistē** — tas pārkāptu "neizgudrot" principu tieši tikpat, cik izgudrots fons.

*(Kamēr šis ir pareizi: apģērbs guļ uz papīra, nevis karājas. Kontakta ēna ir spēcīga pie *karājoša* priekšmeta.)*

### 5.2 Graudu saskaņošana — **plakans fons ir prasība, ne defekts**

Mērījums izvadē: augstfrekvences std **fons 0.06**, **apģērbs 17.17** — attiecība **268×**.

Compositing literatūra saka: elementam jāsaskan ar plāksni, citādi tas "izlec" ([lazi-akademie.de](https://www.lazi-akademie.de/wiki/animation-vfx/compositing/grain-matching/)): *"Grain wird ganz am Ende … über den final fertiggestellten Shot gelegt"*.

**Bet tas ir VFX konteksts.** Mūsu fons ir **digitāls pildījums** ar definētu vērtību `#F3F3F3`, un marketplace specifikācijas to pieprasa:
- Zalando — *"pure white (#FFFFFF) backgrounds with **hard automated rejection**"*
- Amazon — *"Pure white RGB 255,255,255"*; *"Off-white, light grey, or **shadow gradients** all trigger suppression"*

Graudu pievienošana fonā padarītu to **neviendabīgu** un varētu izraisīt automātisku noraidījumu. **268× attiecība ir apzināta prasība, nevis nokavēta darbība.** Fiksēts dokumentā, lai nākotnē kāds to nepārprot par defektu un "nelabo".

### 5.3 Light wrap un screen subtraction — **mērījums: noplūdes nav**

Pārbaudīts tieši (fons dažādos attālumos no malas pret tālu fonu):

| attālums | ΔR | ΔG | ΔB | interpretācija |
|---|---|---|---|---|
| 1–3 px | +23 | +24 | +24 | vienādi visos kanālos |
| 3–6 px | +25 | +26 | +25 | vienādi |
| 25–60 px | +22 | +21 | +19 | vienādi |

Divas lietas:
1. **ΔR ≈ ΔG ≈ ΔB** — nav krāsu nokrāsas pret apģērba krāsu. Light wrap un spill vienmēr ir **krāsaini**. Šeit nav.
2. Fons pie malas ir **gaišāks**, nevis tumšāks vai krāsots — tas ir papīra apgaismojuma gradients (3. sadaļa), nevis atstarotā gaisma.

Tuvuma tests: starpība 1–4 px pret tālu fonu = Δ 42.73, kas ir **127 %** no apģērba-fona starpības — bet tā ir **spilgtuma** atšķirība bez krāsas komponentes. Screen subtraction neko neatņemtu, jo nav ko atņemt.

> Un pats svarīgākais: Nuke literatūra par light wrap saka *"samazini par ~90 % no tā, kas šķiet pareizi"*. Tas ir **tieši tas aizliegtais** — konstante, kas jāmin ar aci. Mēs nevaram izmērīt atstaroto gaismu fonā, kuru paši esam izdzēsuši, tāpēc šodien tas paliktu minējums.

### 5.4 Edge extend — kāpņu risks ir, bet nav izmērīts

`extend_foreground_colors` aizpilda joslu ar **tuvākā pikseļa krāsu** (distance transform), `max_dist=8`. Profesionālā metode ir **normalizēta konvolūcija** `blur(c·m)/blur(m)`, **krauta ar dubultojošiem izmēriem** (2, 4, 8 px), jo *"viens blur nekad nav pietiekams"*.

Tuvākā pikseļa metode pie lielākiem attālumiem dod **rievotu** pildījumu (viena avota kolonna aizpilda visu joslu). Pie `max_dist=8` tas var būt redzams.

**Bet:** mēs to neesam izmērījuši, un lietotājs jau vienreiz noraidīja malas pārveidošanu (`_refine_edge` → zāģis). **Nepieskaramies bez izmērīta defekta.** Ja parādās — risinājums ir 2–3 krautas konvolūcijas, nevis viens lielāks izpludinājums.

---

## 6. Ko profesionāļi dara, ko mums jau ir (un tas ir labi)

Lai būtu skaidrs, ka auditu nesākām no nulles — šīs lietas jau atbilst praksei:

| prakse | mums |
|---|---|
| Fons un ēna **pilnībā pārbūvēta no nulles**, nevis "notīrīta" | ✅ `bg_gray` ģenerēta no nulles |
| Ēna **atsevišķā slānī zem** apģērba | ✅ `shadow_bg` → `bg_gray`, apģērbs virsū |
| Ēnas **necaurspīdība 15–30 %**, nevis melna | ✅ `strength=0.26`, un `#F3F3F3` reizinājums (nevis melns) |
| Ēna **mīksta, konsekventa, minimāla** | ✅ `blur=35` |
| Garments **nav peldošs kā izgriezums** | ✅ ēna eksistē; profesionāļi: *"without a shadow it reads as a floating flat cutout"* |
| Frekvenču domāšana (tekstūra pret toni) | ✅ `texture_map` + `L_TOL` atdalīti |
| Malas **netehniskas, nevis asas** | ✅ `refine_alpha` smoothstep, `feather_px 1.6` |
| **Determenisms** kā kataloga prasība | ✅ *"verify every image uses the same shadow style, angle, opacity"* — mums tas ir burtiski |

Pēdējais punkts ir svarīgs niansē: **ghost-mannequin prakse pieprasa vienādu ēnas leņķi visā katalogā.** Tas nozīmē, ka fiksēts leņķis *nav nepareizs pēc būtības* — nepareizs ir tikai tas, ka **izvēlētais** leņķis (54°) neatbilst bildei, ko apgaismoja no 292°. Ja visu komplektu fotografē vienā sesijā, izmērītais leņķis būs vienāds visām bildēm — tāpēc mērījums un kataloga konsekvence nav pretrunā.

---

## 7. Rangu saraksts pirms debuga

| prioritāte | darbs | risks | ieguvums |
|---|---|---|---|
| **P1** | Ēnas virziens 54° → 112°, konsolidēt 3 kopijas vienā konstantē | zems — skar tikai `dx,dy`, lielums nemainās | noņem fiziski neiespējamu ainu |
| **P2** | IBK-lite: globāls `_paper_level` → lokāla papīra karte | vidējs — skar segmantāciju, jāpārbauda GATE_A2/B/C/D | noņem ar roku minētu `L_TOL` |
| **P3** | Edge extend → krauta normalizēta konvolūcija | vidējs | tikai ja parādās izmērīts kāpņu defekts |
| — | Kontakta ēna, grain, light wrap, screen subtraction, Merge min/max | — | **noraidīts ar mērījumu** |

---

## 8. Ko šis audits nemaina

- Dizaina princips paliek: **AI piedāvā, mērījums izlemj.**
- Neizgudrot fona: P1 un P2 **neskar** apģērba pikseļus, tikai ēnu un slieksni.
- Akceptētā izvade paliek akceptēta: ēnas **lielums** ir izmērīts kā pareizs (181→193 abos), mainās tikai virziens.
- GATE komplekts nemainās.

---

## 9. Ārējie avoti

**Nuke / compositing**
- Foundry, IBK gizmo — https://learn.foundry.com/nuke/content/reference_guide/keyer_nodes/ibkgizmo.html
- Foundry, image-based keying pamācība — https://learn.foundry.com/nuke/content/tutorials/written_tutorials/tutorial3/image_based_keying.html
- Before & Afters, Paul Lambert (Dune) par IBK izgudrošanu — https://beforesandafters.com/2022/03/25/how-dune-vfx-supervisor-paul-lambert-invented-nukes-ibk-keyer/
- Andrea Geremia, edge extend matemātika — https://www.andreageremia.it/tutorial_math_edgeextend.html
- Keheka, detaļu atjaunošana pēc extend — https://www.keheka.com/restoring-details-when-edge-extending-in-nuke/
- Taukeke, light wrap — https://taukeke.com/2015/02/lightwrap-in-nuke/
- Provideocoalition, trīs caurlaidžu metode — https://www.provideocoalition.com/keying-and-compositing-in-nukex/

**Photoshop / produktu retuša**
- Adobe, frekvenču separācija — https://www.adobe.com/products/photoshop/frequency-separation.html
- Photoshop, fona noņemšana pēc malas tipa — https://photoshoptutorial.com/posts/background-removal-in-photoshop-the-right-tool-for-every-edge/
- Pikes, produktu ēnas — https://pikes.ai/blog/product-photo-drop-shadows
- CloudRetouch, kontakta ēnas — https://www.cloudretouch.com/realistic-contact-shadows-ai-background-replacement/
- ImageWork, contact vs cast shadow — https://imageworkindia.com/contact-shadow-vs-drop-shadow-photoshop/

**Ghost mannequin / katalogs**
- Snappyit, ēnas virziena kontradikcija ("divas saules") — https://snappyit.ai/blog/ghost-mannequin-product-photography
- Bright Image, ēna kā "peldoša izgriezuma" pretlīdzeklis — https://brightimage.studio/blog/ghost-mannequin-service-invisible-mannequin-editing-brightimage-studio
- FixAnyPhoto, ēnas necaurspīdība 15–30 % — https://fixanyphoto.com/guide/ghost-mannequin-product-photography/
- JinkoMage, marketplace prasības (Amazon/Zalando/ASOS) — https://jinkomage.com/blog/fashion-ecommerce-image-requirements/

**Graudu saskaņošana**
- Lazi Akademie, grauds kā pēdējais slānis — https://www.lazi-akademie.de/wiki/animation-vfx/compositing/grain-matching/
- Ben McEwan, re-grain ar plāksnes graudu — https://benmcewan.com/blog/2018/05/29/re-graining-your-comp-using-existing-plate-grain/
