# Pētījums: ēnas un masku malas profesionālajā praksē (2026-10-26)

Mērķis: interneta avotu apguve par (1) produktu ēnām e-komercijā, (2) masku
malu apstrādi pie mīkstām/ēnotām robežām — ar akcentu uz mūsu pašreizējo
klupšanas akmeni: **gaišo piepumas joslu maskas iekšpusē** (§137: rim
0–3px L 221 pret kodolu 56; plate/pad maskas iekļauj optisko piepumu).

---

## 1. Ēnas: profesionālie skaitļi pret mūsu studijas modeli

### Ko saka avoti

| Parametrs | Profesionālā prakse | Avots |
|---|---|---|
| Metēnās ēnas stiprums uz balta/gaiša fona | **8–20%** (pikes.ai); 20–40% (fixphotolab); 20–50% (clippingexpertasia); apģērbam ghost-mannequin gidā **5–15%** otela | pikes.ai, snappyit |
| Kontaktēna | tumšākā un asākā tieši pieskaršanās vietā; 2–6px blur uz 2000px attēla; ~80% opacity plānai līnijai | pikes.ai, imageworkindia |
| Krāsa | **nekad tīri melns** — fona krāsa ar mazāk gaismas; siltā gaismā — silti pelēcīgs tonis | pikes.ai, roundcut |
| Virziens | VIENS gaismas virziens visā katalogā; mīkstas malas; ēna mīkstinās tālāk no objekta (kontaktcietināšana) | pixel-prep, clippingexpertasia |
| Garums | īsa, cieši pie pamatnes; gara ēna "aiznes" skatienu | pixel-prep, pikes |
| Slāņi | 2–3 ēnu slāņi: kontaktēna + ambientā (mīkstāka, platāka, 15% / 15px blur) | imageworkindia, roundcut |
| Flat-lay apģērbs | ļoti subtīlas ēnas vai tikai kontaktēna; daži katalogi metēnas ēnu nelieto vispār | snappyit, nightjar |

### Mūsu modelis (`loop.py` studio_shadow_bg) pret to

| Mūsu konstante | Vērtība | Vērtējums pret praksi |
|---|---|---|
| STUDIO_SHADOW_PEAK | 0,32 (32% maks. aiztumšošana) | **augšgalā / pāri** apģērba joslai (5–20%); vispārējā e-komercijas joslā (20–40%) — ietilpst, bet apģērbam stipri |
| STUDIO_SHADOW_OFFSET_PX | 16 px | ✓ īsa, cieši (profesionālie "2–8px offset" katalogos uz 2000px; 16 ir保守ākā pusē, pieņemami) |
| STUDIO_SHADOW_SIGMA0_PX / K | 0,9 + 0,28·d | ✓ kontaktcietināšana — tieši kā praksē ("asāka kontaktā, mīkstāka tālāk") |
| Virziens | fiksēts 43° visam katalogam | ✓ kataloga konsistence |
| Krāsa | fona pelēkuma aiztumšošana (243 → ~201), ne melns pārklājs | ✓ pareizi |
| Komponentes | 2: kontaktAO + metēnās | ✓ atbilst "contact + ambient" divslāņu praksei |

**Izmērīts renderī (§137 grupas PARAUGS):** fona tumšākais punkts
L 151/243 = **38% aiztumšošana**, 1% tumšākā zona ~24%. Tātad
efektīvā ēna ir virs apģērba joslai ieteiktā 8–20% un augšgalā
vispārējai e-komercijas joslai (20–40%). V1 (peak 0,22) to novestu
uz ~16–26% — profesionālajā joslā.

**Secinājums:** arhitektūra atbilst profesionālajai praksei; novirze — PEAK 0,32 ir stiprāka nekā apģērba nozarei ieteiktās vērtības.
Variantu lapa (§137, enas_varianti.jpg): **V1 (peak 0,22) iekrīt
profesionālajā joslā**; V3 (0,10) ≈ "tikai kontaktēna" stils, ko daži
apģērbu katalogi lieto apzināti. — Nomainīt var tikai ar pogu.

---

## 2. Masku malas: mūsu defekts ir Macbuks no mācību grāmatas

### Diagnozes apstiprinājums avotos

- "White or dark halo = **background-contaminated foreground color**"
  (backgrounerase.com tabula) — tieši mūsu gaišā josla maskas iekšpusē.
- Dev.to mērījumu raksts: balta apmale ir **ieglabāta pašos malas
  pikseļos**, nevis kompozīcijas artefakts — premultiply to nelabo
  (mērīts: luminance 75,4 gan pirms, gan pēc). Mūsu gadījumā tieši tā:
  josla ir avota piepuma pikseļi ar alfa=1.
- Photoshop profesionālā rīku kārta šim defektam (Adobe HelpX +
  retoušētāju gidu konsense):
  1. **Defringe** (1–2px; spītīgiem 4–5px): aizvieto malas joslas
     krāsu ar krāsu no dziļāk iekšpuses — "pushes interior pixels out
     to cover the white fringe". **Brīdinājums (Adobe community): ja
     frinža ir liela, defringe rezultāts izskatās dīvains** — mūsu
     12–16px josla ir pāri par lielu vienkāršam defringe.
  2. **Maskas sašaurināšana (choke)**: Filter > Minimum 0,5–1,5px vai
     Select&Mask Shift Edge −10…−15% — **mūsu erozija 8px ir tieši
     šis līdzeklis** (8px uz 4096px avota ≈ 2px uz 1000px skatu —
     praksē esošā diapazona augšgalā, jo josla plata).
  3. **Color Decontaminate** (25–50%): malu krāsu pārkrāsošana pret
     iekšpuses toņiem — mūsu `extend_foreground_colors` darbojas
     pretējā virzienā (stiepj krāsas āRĀ alfas joslā), bet
     **ne-pārkrāso nesegto joslu maskas IEKŠPUSĒ** — tātad defringe
     solis mums trūkst.
  4. **Robustais risinājums lielām frinžām / mīkstām malām**:
     **trimaps + matting modelis** (FBA / ViTMatte / Information-Flow)
     — novērtē alfu un F krāsu pikselī pa pikselim piepumas joslā.

### Matting modeļu karte mūsu gadījumam

| Modelis | Ievade | Licence | Ātrums (CPU) | Piezīmes |
|---|---|---|---|---|
| ViTMatte (base-composition-1k, ~370–390 MB) | **trimaps** (obligāts) | ⚠️ **svari trenažēti uz Adobe datiem — nekomerciāli** (MatteDesk brīdinājums) | sekundes/attēlam | SOTA malu kvalitāte; trimaps no mūsu maskas: erodēt ~10 + dilatēt ~20 (ComfyUI noklusējumi); max_resolution 2048 (VRAM), auto_crop_by_mask |
| BiRefNet (MIT; HR-matting ~444 MB) | brīva (maska/nav) | ✓ **MIT — komerciāli OK** | sekundes/attēlam (CPU), <1s uz GPU | **"ēna zem objekta tiek pareizi izslēgta, nevis ieblurēta alfā"** — tieši mūsu ēnainā papīra problēma; natīvi 2048; DIS5k SOTA |
| mūsu ISNet (isnet-general-use) | brīva | ✓ | ~3–9 s | pašreizējais; piepumu iekļauj maskā |

**Svarīgākā licenču atklāsme:** "Pilotē ViTMatte" komanda (LOOP_KOMANDAS)
ir OK kā eksperiments, bet **ražošanā pārdošanas attēliem tas nav
lietojams** (Adobe-trenažēti svaru faili, non-commercial). Komerciāli
drošais ceļas alternatīvs ir **BiRefNet** (MIT) — kā segmentācijas
kvalitātes pakāpi (ēnu atgrūšana!) vai trimap-avots.

### Trimap prakse

- Trimapu gūst no rupjās maskas: erodēt (drošā priekšpuse) + dilatēt
  (nezināmā josla). **Adaptīvs joslas platums** sekojot lokālajam
  saturam ir "production pipelines" iezīme (bestaiweb + IEEE 2013
  adaptive trimap darbs) — fiksēts radiuss visur ir kompromiss.
- Pār šauru joslu → cieta, robota mala; pār platu → "minēšana" un
  pārmīkstināts rezultāts. Mūsu piepumai ~12–16px: erode ~8–12,
  dilate ~16–24 būtu sākumpunkts.

---

## 3. Saknes cēlonis avotā (fotografēšana) — profilakse

Profesionālais flat-lay standarts (frameonce.io, fixanyphoto, gdefoto):
- **Divas mīkstās gaismas 45°** no abām pusēm (vai liels ziemeļu logs +
  balts putuplasta reflekors pretējā pusē) — iznīdina dziļās ēnas,
  kuras (a) maldina ISNetu pad-retry mērogos (§136/§137), (b) rada
  kontrasta zudumu robežās → piepumas josla.
- f/8–f/11, ISO 100–200, VB fiksēts, manuāls fokuss uz apģērba plakni.
- **Mūsu ierobežojums:** Poco F7 fiksēts f/1,5 — DOF nevar padziļināt
  ar diafragmu. Praktiskais kompromiss: **fotografēt tālāk** (1,8–2,5 m;
  DOF aug ar attālumu) un izmantot 50 MP režīma izšķirtspējas rezervi
  kadrējumam; vai nu gaisma jābūt tik spilgtai un izkliedētai, cik
  iespējams (ārs, mākoņains), lai vismaz ēnas dziļumu samazinātu
  (mūsu grupas p10 14–19 ir dziļākas par jebkuru profesionālo studiju).
- Squareshot (apģērbu studija) triks: **divi kadri** — viens ar
  augšējo gaismu izskatam, ots ar sānu gaismu reālai ēnai, kompozīcija
  pēc. Mums: ēnu jau zīmē modelis, tāpēc pietiek ar pirmo.

---

## 4. Konkrētie priekšlikumi mūsu pipeline (katram vajadzīga poga)

1. **Defringe solis maskas iekšpusē** (jauns, mazs): pirms alfas —
   joslas (piem. 4–8px avota mērogā) krāsu aizvietošana ar krāsu no
   dziļāk iekšpuses gar kontūru (Photoshop Defringe analogs ar
   kontūr-gludu paraugu ņemšanu kā decontaminate_rim). Atšķirībā no
   erozijas — **nesamazina siluetu**, tikai novāc halo krāsu. Erozija
   paliek dziļākai piepumai. (Ražošnes izmaiņa → poga.)
2. **Ēnas PEAK 0,32 → 0,22** (V1 no §137 lapas) — ieietu
   profesionālajā joslā apģērbam. Varianti jau uzģenerēti un parādīti.
   (Konstanšu maiņa → poga.)
3. **BiRefNet pilots** (MIT, komerciāli drošs) vienai bildei ar
   ēnaino papīru (piem., nākamā grupa): salīdzināt maskas pret ISNet
   (ēnu atgrūšana, malu asums) ar mūsu pašu vārtiem H/S/R — kā
   "Pilotē ViTMatte" komandai, tikai ar pareizo licenci. ViTMatte
   atstāt tikai QA eksperimentiem (non-commercial svaru dēļ).
4. **Fotografēšanas padomu atjauninājums** (P0_PLANS / nākamās grupas
   sagatave): divas 45° mīkstās gaismas vai logs+reflektors;
   fotografēt no 1,8–2,5 m (DOF); mērķis — avota ēnu p10 ≥ 35 un
   robežas kontrasts. Bez dziļām ēnām arī ISNet/plate malas kļūst
   asas un defringe vairs nav vajadzīgs.

## 5. Avoti

- pixel-prep.com — Product Photography Shadows (Amazon prasības; mīkstas
  malas; zemāka necaurspīdība; īsas ēnas; kontaktēna tumšākā)
- pikes.ai — Drop Shadows (kontaktpunkta blur 2–6px uz 2000px; 8–20%
  uz balta; nekad melns)
- imageworkindia.com — Contact vs Drop (kontaktēna 2px blur 80%;
  ambientā 15px blur 15%)
- roundcut.app — 7 tehnikas 2026 (apģērbam cast/natural; 2–3 slāņi;
  silti pelēcīga ēna siltai gaismai)
- snappyit.ai — ghost mannequin gidai (apģērba ēna 5–15% otela gar
  apakšmalu)
- fixphotolab.com — 12-soļu darba plūsma (20–40%; fotografēt uz gaiši
  pelēka, ne tīri balta — malu informācija!)
- frameonce.io — Clothing Photography (flat-lay 2×45° softbox, f/8–11,
  ISO 100–200, VB 5500K fiksēts, manuāls fokuss)
- squareshot.com — 10 flat-lay ieteikumi (divu kadru ēnas tehnika)
- adobe helpx — Defringe / Remove White Matte / Color Decontaminate
  (fringe noņemšanas rīku kārta)
- reliabless.com — White Glow cēloņi (premultiplied alpha nepalīdz, ja
  krāsa ieģenerēta malas pikseļos; defringe 1–2px + maskas kontrakcija
  kā ātrais; krāsu dekontaminācija kā robustais)
- dev.to (pm_cheng) — mērījums: balta frinža saglabājas arī pēc
  premultiply (luminance 75,4 = 75,4)
- cloudretouch.com — Select&Mask Shift Edge −10…−15%, Contrast +5–10%
- backgrounderase.com — segm. vs matting tabula (halo cēloņi)
- bestaiweb / IEEE — trimap ģenerēšana; adaptīvs joslas platums
- comfy.icu — ViTMatte parametri (trimap_erode 10 / dilate 20;
  max_resolution 2048; auto_crop_by_mask)
- ice-ice-bear.github.io — matting bibliotēku karte (BiRefNet → ViTMatte
  divpakāpju shēma; BiRefNet CPU sekundes; ēna zem objekta pareizi
  atgrūsta)
- github ZhengPeng7/BiRefNet — MIT licence, modeļu zoods (SwinL 215MB
  parametri; DIS5k SOTA)
- fishfinger44/MatteDesk — **ViTMatte svaru licence: non-commercial
  (Adobe-trenažēti)**; BiRefNet_HR-matting MIT
- arxiv 2305.15272 (ViTMatte), 2401.03407 (BiRefNet), 2306.04121
  (Matte Anything — SAM+GroundingDINO+ViTMatte ķēde)
