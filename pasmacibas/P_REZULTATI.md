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
