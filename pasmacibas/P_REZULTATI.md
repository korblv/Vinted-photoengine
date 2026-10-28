# P_REZULTATI: 1. pašmācību kārta (2026-10-25)

Vide: izolēta kopija `/tmp/pdrill` (SRC_DIR pārrakstīts; īstie uploads
netika aiztikti). Ainas: `pasmacibas/gen_scenes.py` (deterministiskas).
Attempts 1–11 šajā kopijā; komandas: sk. P0_PLANS.md §3.

## 1. Treniņu tabula

| # | aina / darbība | gaidīja | faktiski | skaitļi | secinājums |
|---|---|---|---|---|---|
| P1 | A_kopskats | isnet + slamjam | ✓ isnet + slamjam | seg. 0,2856 | mācīts |
| P1 | B_mala v1 (26% kontakta josla) | isnet + original | isnet + slamjam | kontakts 0,26 < 0,50 | mācība: slēgta silueta kritērijs ir ≥50% kontakta malā |
| P1 | B_mala v2 (56% TAINSTŪRA josla) | original | STOP refused_no_trusted_mask | — | mākslīga taisnstūra forma → ISNet noraida; dabiskums ir svarīgs |
| P1 | B_mala v3 (slīpa elipse pāri malai) | original | isnet + slamjam | kontakts 0,21 | vēl zem sliekšņa |
| P1 | A + `--framing original` (fallback) | original renderis | ✓ "izvēlēts original" | — | original RENDERA ceļš izstaigāts ar karogu |
| P1 | C_enskaelis (ēnu sašķelts krekls) | QA noraida → pad retry | isnet tīri | seg. 0,2854 | sintētiskā ēna ISNet ir par vieglu; isnet_pad_retry paliek segts tikai ar REĀLO 161031 gadījumu |
| P1 | D_haoss | STOP | ✓ needs_review | retry pārplūde 0,859; plate seg. 0,066 ārpus 0,25–0,95; chroma sēklas 0 px | mācīts |
| P2 | A --rotate 90 | maska iztur rotāciju | **chroma_seeded**! | seg. 0,2857; GATE_K auto −3,12 → identity −2,13 PASS | rotācijā ISNet QA noraida, hroma ceļš glābj; grīdas stūris + auto WB → GATE_K risks (§128 mehānisms atkārtojās) |
| P2 | A --rotate 270 | tas pats | chroma_seeded | D vārtos rotation_cw=270 ✓ | mācīts |
| P3 | E_siltpapirs v1 (gaišs krekls uz spilgta silta papīra) | GATE_K fail | **STOP boundary_uncertain** | aizdomīgi logi 4 ≥ 4, centrs [522,1307] | zemas kontrasta robeža → GATE_S STOP (P8 ceļš iegūts kā bonuss!): papīram JĀkontrastē ar apģērbu |
| P3 | E2_siltpapirs (tumšāks krekls, maigi silts papīrs) auto WB | GATE_K fail | ✓ FAIL | fons [194,190,180]; WB [0,972; 1; 1,078] (īstajā §128: [0,977; 1; 1,073]); shift_b −4,13 | §128 gadījums precīzi reproducēts |
| P3 | E2 identity WB | PASS | ✓ PASS | shift_b −0,98 | risinājuma ceļš izstaigāts |
| P4 | A2 + F_makro --lut-only | lut_only | ✓ 2/2 | verifikācija: visas 4 malu daļas 0,0000, globāli 0,0000 (bez refused — izstaigāts arī "pieņemts kandidāts, bet papīra nav" atzars); LapVar 2436; MAKRO 2000×2500 no 1888×2360; checker ALL_PASS ar A2/K/D/R/T | mācīts |
| P5 | make_zip (6 kadrī atskaitē) | ZIP ar 5 PARAUGS + 1 MAKRO | **ZIP bez MAKRO** | ZIP 5 faili; CRC OK | **ATRASTS DEFEKTS — sk. §2** |

Papildus mācība (rīku higiēna): `checker_v2.py STEM` ar pozicionālo
filtru PĀRRAKSTA report_v2.json tikai ar pārbaudītajiem stumbriem —
pirms make_zip vienmēr jāpalaiž pilns checker (bez filtra), citādi
make_zip krīt ar "Checker atskaitē trūkst".

## 2. Atrastais defekts (labojumam vajag lietotāja pogu)

`engine/report.py` `_persist_report` akumulācijas loģika patur veco
ierakstu tikai tad, ja eksistē `paraugs/{stem}_PARAUGS_2000x2500.jpg`.
lut_only kadram PARAUGS nekad nav (ir MAKRO) → jebkurā nākamajā
palaišanā ar citu `--files` lut_only ieraksts KLUSSI izkrīt no
report_v2_maker.json → izkrīt no checker un make_zip. Reprodukcija:
attempt 10 (F pabeigts, 6/6 atskaitē) → attempt 11 (cits --files) →
F vairs nav atskaitē → ZIP bez MAKRO.

Piedāvātais labojums: izdzīvošanas pārbaudei lut_only ierakstam
jāskatās `paraugs/{stem}_MAKRO_2000x2500.jpg` (rec.get("lut_only")
→ MAKRO ceļš). + vienības tests: lut_only ieraksts izdzīvo _persist_report
atkārtotu palaišanos ar citiem --files.

## 3. Ceļu seguma tabula pēc šīs kārtas

| ceļš | segums |
|---|---|
| isnet | ✓ P1 (A, B, C, E2, A2) + reālie |
| isnet_pad_retry | tikai reālais 161031; sintētiski neizprovocēts (godīgi: nav izdevies) |
| chroma_seeded | ✓ P2 (rotētās A ainas) |
| plate_texture | vēsturiski reāls; sintētiski neizprovocēts (D ainā plate noraidīja) |
| lut_only | ✓ P4 + reālais 145647 |
| needs_seed_review STOP | ✓ P1 D_haoss + reālais 145345 |
| boundary_uncertain STOP | ✓ P3 E v1 (bonuss — bija plānots P8) |
| failed (vide) | ✓ reālās sesijas pārstartes |
| slamjam | ✓ |
| original (renderis) | ✓ ar `--framing original` |
| auto→original (atvērts siluets) | ✗ nav dabiski izprovocēts (trīs mēģinājumi P1) |
| WB auto→GATE_K fail→identity | ✓ P3 E2 |
| rotācijas 90/270 | ✓ P2 |
| make_zip (PARAUGS+MAKRO) | ✕ atrasts defekts §2 |

## 4. Nākamās kārtas uzdevumi

1. §2 defekta labojums (pēc pogas) + regresa tests.
2. auto→original atzara provocēšana (cita ainas forma) VAI apziņa,
   ka tas segts vēsturiski + vienības testos.
3. plate_texture / isnet_pad_retry sintētiska provocēšana (grūti;
   alternatīva: reģistrēt reālos gadījumus kā etalonu bibliotēku).
4. GATE_K sadalījums rotētajai A ainai (−3,12 auto → −2,13 identity):
   atlikusī daļa no chroma_seeded maskas/ēnas — izpētīt, vai maska
   neiekļauj zilganu ēnas joslu.

---

# 2. kārta (2026-10-25, pēc §133 defekta labojuma pogas)

## 5. Defekta labojums un P5 pierādījums

- Labojums `engine/report.py` `_persist_report`: lut_only ieraksta
  izdzīvošanas pārbaude skatās `makro_path` / `MAKRO_2000x2500.jpg`.
- 2 jauni regresa testi (131 → 133; visi zaļi): lut_only ieraksts
  izdzīvo nākamo palaišanu ar citiem --files; bez MAKRO faila — izzūd.
- P5 atkārtots end-to-end: attempt 13 (F atpakaļ atskaitē) → attempt 14
  (citi --files) → **F izdzīvo** (completed/lut_only True) →
  **checker 6/6 PASS** → **ZIP satur 5 PARAUGS + 1 MAKRO**, CRC OK.
- Komits `3dd0569`.

## 6. 2. kārtas treniņi

| # | aina / darbība | gaidīja | faktiski | secinājums |
|---|---|---|---|---|
| P6 | G_plats (elipses krekls pāri platumam, scale 1.95) | auto→original | slamjam (kontakts 0,46 < 0,50), tad **STOP boundary_uncertain** (9 logi ≥ 4) | elipse malās sašaurinās uz punktu → kontakts nepietiek; sašaurinātā, mīkstā robeža dod GATE_S STOP — taisnas malas ir svarīgas |
| P6b | C2_zemkontrasts (krekls [178] uz [156] + cietā ēna 0,8) | isnet_pad_retry | isnet tīri (seg. 0,2854) | ISNet uz sintētikas pārāk robusts; pad_retry paliek segts tikai ar reālo 161031 |
| P6c | **H_salocits (salocīts apģērbs: noapaļots taisnstūris pāri pilnam platumam, kontakts 0,58)** | auto→original | ✓ **"original (auto: atvērts siluets -> original)"**; isnet seg. 0,618; 12/13 vārti zaļi (arī F: malas mantotas) | **pēdējais auto atzars iegūts**; vienīgais kritums — GATE_K (sk. §7) |
| P7 | Sabotāža ražošanas mērogā: MAKRO aizstāts ar viendabīgu pelēku | R/K krit | ✓ **GATE_R FAIL** (K palika True — mediāna b\* viendabīgā krāsā ietilpst limitā; R ķer) | R ir tam notvērējs; pēc atjaunošanas atkal PASS |
| — | GATE_K sadalījums (H) | izprast −3,27 | b\* soļi: audums −1,11 → LUT −2,30 → PARAUGS −2,34; **checker ref +0,93** | sk. §7 |

## 7. ATklājums par GATE_K atsauces būvi (labojumam vajag pogu)

GATE_K reference tiek būvēta, VISPĀRĒJO avotu sablīvējot 2000×2500
(`src_im.resize((2000,2500))`) un mērot `via` (novietojuma maskas)
reģionā. Kad avota un audekla proporcijas neatšķiras tikai ar
augšupielādes mērogu (H: avots 0,46 platums/augstums pret audeklu 0,8;
`via` sedz 94,7% audekla), `via` reģionā iekļūst ARĪ papīrs →
b_ref nobīdās pret patieso auduma b\* par **+2,04** (H: ref +0,93 pret
audumu −1,11). Kopā ar LUT zilo pieguvumu (−1,19 no WB [1,1,1,026] uz
nedaudz sarkanīga papīra fona [161,161,158]) tas dod −3,27 > limits 2,5.

- Uz REĀLIEM slamjam kopskatiem (portrets → portrets, via ≈ 0,74×0,78)
  šī approksimācija ir maza (145603: identity −0,98 PASS), bet eksistē.
- GATE_R jau lieto ĢEOMETRIJAI korektu rekonstrukciju
  (`reconcile_reference`); GATE_K to nedara.
- Piedāvātais labojums (pēc pogas): GATE_K atsaucei izmantot to pašu
  ģeometriju kā renderim (bbox kopskatam / crop lodziņš tuvplānam /
  lut_only krops — tam jau tā ir), nevis visa avota sablīvējumu.

## 8. Ceļu segums pēc 2. kārtas

| ceļš | segums |
|---|---|
| isnet | ✓ |
| isnet_pad_retry | tikai reālais 161031 (godīgi: sintētiski nav izdevies 2 mēģinājumos) |
| chroma_seeded | ✓ P2 |
| plate_texture | vēsturiski reāls; sintētiski nav provocēts |
| lut_only | ✓ P4 + 145647; akumulācijas defekts izlabots (§5) |
| needs_seed_review STOP | ✓ |
| boundary_uncertain STOP | ✓ 2 gadījumi (E v1 zemas kontrasta; G mīkstā sašaurinātā robeža) |
| slamjam | ✓ |
| original (renderis) | ✓ (karogs + AUTO atzars caur H_salocits) |
| WB auto→fail→identity | ✓ |
| rotācijas 90/270 | ✓ |
| make_zip PARAUGS+MAKRO | ✓ pēc labojuma |
| checker sabotāžas (R) | ✓ P7 |

Atlikušais godīgais parāds: pad_retry un plate sintētiskā provocēšana;
GATE_K atsauces ģeometrijas labojums (§7, gaida pogu).

---

# 3. KĀRTA (2026-10-25)

## 9. GATE_K atsauces labojums (§7 izpilde, pēc pogas "Labot")

`checker_v2.py`: jauna funkcija `_chroma_reference(src_im, mask_p, maker_rec)`
— GATE_K atsaucei tagad TĀ PAT rendera ģeometrija kā GATE_R
(`reconcile_reference`): bbox kopskatam, `timing.closeup_crop` lodziņš
tuvplānam, uniforma mērogošana + centra krops "original" stilam.
lut_only zars nemainīgs (tam jau bija sava krops ģeometrija).
Vienības testi: `TestChromaReferenceGeometry` (2) — bbox ģeometrija
aizpilda novietojumu; "original" gadījumā apģērbs nonāk rindās, kā paredz
uniformā mērogošana+centra krops (0..250), nevis sablīvējuma (0..625).

### Rezultāti (pirms → pēc)

| kadrējums | vecā atsauce | jaunā atsauce | secinājums |
|---|---|---|---|
| H_salocits (sintēt., original) | −3,27 FAIL (viltus) | **−1,34 PASS** | viltus trauksme novērsta |
| E2 auto WB (sintēt., silts papīrs) | −4,13 (pārspīlēts) | **−2,82 FAIL** | ĪSTĀ problēma saglabāta |
| E2 identity | −0,98 | 0,33 | atbilstoši |
| treniņi kopā (8 kadri) | — | **8/8 PASS** | — |
| reāls 145603 (isnet pilnais ceļš) | — | **−0,01 PASS** (`ref_method: render_geometry`) | reālie netraucēti |
| reāls 145647 (lut_only) | — | **+0,84 PASS** | lut_only zars nemainīgs |

Testi: **135/135** (+2 `TestChromaReferenceGeometry`).

Piezīme par atkārtojamību: treniņu karte `/tmp/pdrill` dzēšas ar sandbox
pārstartu; 8 kadru momentuzņēmumi vairs nav atjaunojami bez kārtas
atkārtotas izpildes (P0_PLANS §3 komandas). Pārbaudīts pēc refaktora ar
vienības testiem + abiem reālajiem kadriem + izdzīvojušo E2 checker
ierakstu (−2,82 saglabāts).

## 10. 3. kārtas mēģinājumi

| aina | ceļš | iznākums |
|---|---|---|
| I_dividots (krekls + atsevišķs piedurkņu rullis) | isnet | STOP needs_review: AI QA "fragments" seg. 0,1326; pad retry noraidīts (seg. 0,146 ārpus 0,25–0,98, bbox 0,169 < 0,30); plate noraidīts (seg. 0,153 < 0,25) |

Iemācītie QA minimumi (no pad_retry/plate noraidījumiem): segmentācijas
segumam jābūt 0,25–0,98; bbox daļai ≥ 0,30; plate tekstūras iekšpusei
≥ 0,5.

## 11. Ceļu segums pēc 3. kārtām (galīgais)

| ceļš | segums |
|---|---|
| isnet | ✓ |
| isnet_pad_retry | **tikai reālais 161031** (godīgi: 4 sintētiski mēģinājumi neizdevās — C, C2, G, I_dividots; ISNet uz sintētikas pārāk robusts) |
| chroma_seeded | ✓ P2 |
| plate_texture | vēsturiski reāls; sintētiski nav provocēts (4 mēģinājumi) |
| lut_only | ✓ P4 + 145647 (abēji atzari) |
| needs_seed_review STOP | ✓ (arī I_dividots) |
| boundary_uncertain STOP | ✓ 2 gadījumi |
| slamjam | ✓ |
| original (renderis) + AUTO atzars | ✓ H_salocits |
| WB auto→fail→identity | ✓ (ar jauno atsauci E2 auto −2,82 joprojām FAIL) |
| rotācijas 90/270 | ✓ |
| make_zip PARAUGS+MAKRO | ✓ pēc §5 labojuma |
| checker sabotāžas (R) | ✓ P7 |
| GATE_K atsauces ģeometrija | ✓ izlabota (§9) |

Godīgais parāds pēc 3 kārtām: pad_retry + plate sintētiskā provocēšana
(nepieciešama reālai tuvināšanai — mazi/fragmentāri objekti ar QA
minimumiem seg. ≥0,25, bbox ≥0,30), plate_texture; auto WB atsauces
izmaiņu ietekme uz vēsturiskajām siltā papīra grupām (jāpārbaud, ja
tādas atkal ražo).

## 12. Papildinājums (reālais 145345, 2026-10-25): pad_retry robustuma karte

Reālajā Uniqlo kadrā 145345 (dziļo ēnu kopskats) izstaigāti 7 pad
mēģinājumi ar `--isnet-auto` worker tieši (bez atskaites ietekmes):

| pad | iznākums |
|---|---|
| 0,50 / 0,60 | maska = viss kadrs (seg. 1,0) → noraidīts |
| 0,70 | QA ✓ BET pārplūde 0,184 > 0,02 (papīrs maskā) → noraidīts |
| 0,75 / 0,80 / 0,95 / 0,98 | sašķeltas (largest 0,67–0,69) |
| 0,85 / 0,90 (attempt 2) | sašķeltas (0,76–0,79) + nepārklāts audums 0,06 > 0,05 |

Mācība: ēnains papīrs maldina ISNetu visos kvadrātproxy mērogos —
pad_retry ceļš šādā kadrā nav izsaucams ar NEVIENU pad vērtību. Bāzes
(portreta proxy) maska bija struktūrā vesela (structural QA ✓,
zaudētais audums 0,64% < 1,0%), bet AI fragmentu heirisika to atgrūda
par 0,005 (bbox_area 0,3451 < 0,35). Izšķīra cilvēka lēmums (poga) +
checkera vārti kā tiesnesis: manuālā pieņemšana → attempt 3 →
3/3 PASS (K +0,01, R/C/H/S zaļi). Sk. PROGRESS §136.

## 13. 4. pašmācību kārta un pilna koda audita verifikācija (2026-10-28, §144)

Vide: izolēta kopija `/tmp/pdrill` (attīrīta pēc skrējiena; aktīvā grupa
`145704` ražošanas `output/` nav aiztikta). Ainas papildinātas
`pasmacibas/gen_scenes.py --round4` (tagad visas 3./4. kārtas ainas ir
reproducējamas no viena skripta ar `--gt-dir` GT maskām un zemu RAM patēriņu).

### 13.1. Pozitīvā un negatīvā treniņu tabula (reāls ISNet + čekeris)

| aina | gaidītais ceļš | faktiski | IoU pret GT | laiks (s) | GATE_K `shift_b` | GATE_R (`fore`/`bg`) | spriedums |
|---|---|---|---|---|---|---|---|
| `PDR_H_salocits` | `isnet_pad_retry` + `original` (2 bleed + 2 margin) | ✓ `isnet_pad_retry` (`original`) | **0,9947** | 12,77 | −1,99 | 13,0 / 2,0 | **12/12 PASS** |
| `PDR_H2_slamjam_mala` | `isnet_pad_retry` + `slamjam` pie sensora malas | ✓ `isnet_pad_retry` (`slamjam`) | **0,9934** | 11,45 | −1,95 | 14,0 / 0,0 | **12/12 PASS** |
| `PDR_J_henley_bleed` | `isnet_pad_retry` + `original` (3 malu bleed) | ✓ `isnet_pad_retry` (`original`) | **0,9990** | 12,36 | −0,06 | 10,0 / 0,0 | **12/12 PASS** |
| `PDR_M_plate_only` | **`plate_texture`** + `original` | ✓ **`plate_texture`** (`original`) | **0,9979** | 13,90 | 0,00 | 6,0 / 0,0 | **12/12 PASS** |
| `PDR_K_exif6_portrets` | `isnet` + `slamjam` ar `EXIF=6` | ✓ `isnet` (`slamjam`) | **0,9886** | 8,31 | −1,90 | 14,0 / 0,0 | **12/12 PASS** |
| `PDR_L_makro_pilnkadrs` | `lut_only` (`--lut-only`) | ✓ `lut_only` (`LapVar=2876`) | — | 1,52 | −1,39 | 15,0 / — | **12/12 PASS** |
| `PDR_I_dividots` | STOP (divi nesavienoti objekti) | ✓ `needs_review` (`largest 0,546 < 0,90`) | — | — | — | — | **STOP ✓** |
| `PDR_D_haoss` | STOP (izkaisīti plankumi) | ✓ `needs_review` (`overflow 0,8587`) | — | — | — | — | **STOP ✓** |

### 13.2. Pretinieka (adversarial) un rīku higiēnas pārbaudes

| pārbaude | mērījums pirms remonta | mērījums pēc remonta |
|---|---|---|
| `--rotate TYPO99:90` drukas kļūda | klusi ignorēta (`rotation_cw = 0`) | tūlītējs `ValueError` pirms ISNet (`< 0,1 s`) |
| `EXIF=6` avots čekerī (`K`, `L/P`, `Q`, `S`) | viltus kritiens: `GATE_K shift_b = +34,55`, `GATE_Q = 5,556%` | visi 12 vārti zaļi (`shift_b = −1,90`, `Q = 0,028%`) |
| `GATE_F` izgudrots apakšas grieziens (`avots=0,0`, `paraugs=0,76`) | pašapstiprinošs `PASS` (`M` bija `PARAUGS_MASK`) | noķerts: `pass=False`, `kind="cut"`, `inherited=False` |
| `PARAUGS` ar nepareizu izmēru (`1999×2500`) | `UnboundLocalError: local variable 'M'` | tīrs `GATE_D: pass=False, size=[1999, 2500]` |
| `para_scale` uz atvērta silueta (`cov=0,60, full_shot=False`) | `0,7839` pret `render_paraugs` `1,0593` (`26,0%` ēnas nobīde) | `1,059322` (`0,000000` starpība) |
| Daļējs `checker_v2.py STEM` + `--make-zip` | pārrakstīja `report_v2.json`, izmetot pārējos kadrus | saglabā izdzīvojušos ierakstus; `GALA_P4.zip` (`PARAUGS` + `MAKRO`, `bad_crc=None`) |
| `rebuild_master.py` bez AI modeļa + atkārtots čekeris | trūka `exif_transpose`, `lut_only` un precīza `para_scale` | `max diff = 0` (`145704` un `EXIF=6`), `3/3 PASS` pēc pilnas pārbūves |
| `close_group.py` ar sufiksu / grupas slēgšana | neatrada `IMG_..._145704.jpg` un atstāja vecos JSON | atrod visus 14 grupas failus (`18,48 MB`) vai 59 treniņa failus (`107,71 MB`) |
| **Jauns 4. kārtā atklāts defekts (`H2_slamjam_mala`):** `slamjam` pie sensora malas (`x1 + pad_px > mw`) | `GATE_R` viltus kritiens (`bg_p99 = 7,0 > 4,0`, `max = 80`) tur, kur MASTER fiziski beidzās pie sensora malas | izslēgta neierakstāmā `<=70 px` sensora ārējā ēnas josla → `bg_p99 = 0,0` (`2,66M` fona px), slieksnis `4,0` nemainīts |

### 13.3. Pilnā ceļu seguma tabula pēc 4. kārtas

| ceļš | segums pēc 4. kārtas |
|---|---|
| `isnet` | ✓ sintētiski (`A`, `K_exif6_portrets`) + reālie |
| `isnet_pad_retry` | ✓ **sintētiski pirmo reizi** (`H_salocits`, `H2_slamjam_mala`, `J_henley_bleed`) + reālais `161031` |
| `plate_texture` | ✓ **sintētiski pirmo reizi** (`M_plate_only`, IoU `0,9979`) + reālais `145704` |
| `chroma_seeded` | ✓ sintētiski (`P2` rotētās `A` ainas) |
| `lut_only` | ✓ sintētiski (`F_makro`, `L_makro_pilnkadrs`) + reālais `145647` |
| `needs_review` STOP | ✓ sintētiski (`D_haoss`, `I_dividots`) + reālais `145345` |
| `make_zip` (`PARAUGS` + `MAKRO`) pēc daļēja čekera | ✓ verificēts 4. kārtā (`GALA_P4.zip`, CRC OK) |
| `rebuild_master.py` + pilns čekeris (`A2`/`R`) | ✓ verificēts 4. kārtā (`max diff = 0`) |

