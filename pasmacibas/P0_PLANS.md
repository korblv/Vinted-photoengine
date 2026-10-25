# P0: Pašmācību plāns (P-sērija) — lai KATRA bilde iziet KATRU ceļu

Izveidots 2026-10-25 pēc lietotāja norādes: "Taisi pašmācības, tev ir
jāiemācās viss, lai mums visas bildes izietu visus ceļus."

Mērķis: noslēgtu, atkārtojamu treniņu komplekts, kas izstaigā VISUS
ražošanas ceļus ar sintētiskām ainām (deterministisks ģenerators,
fiksēts sēklas) un reāliem kadriem, kur tie ir pieejami. Katrs treniņš
beidzas ar skaitļu tabulu `P_REZULTATI.md`. Ja treniņš atklāj defektu —
labojums TIKAI ar lietotāja pogu (§3.6 noteikums spēkā arī šeit).

## 1. Ceļu inventārs (kas jāizstaigā)

### 1.1 Masku ceļi (workflow_v2, masku fāze)
| ceļš | kad | kā izmācās |
|---|---|---|
| `isnet` | ISNet QA pieņem | P1 aina A |
| `isnet_pad_retry` | QA noraida, apmales retry iztur | P1 aina C (vai reāls 161031 gadījums) |
| `plate_texture` | fona plāksne pieņemta (Q trigeris) | vēsturisks; sintētiski grūti provocēt — P1 novēro, ja iedegas |
| `chroma_seeded` | hroma sēklas pieņemtas | P1 aina D novēro |
| `lut_only` | pilnkadra makro, verifikācija iztur | P4 |
| `needs_seed_review` (STOP) | nav drošas maskas | P1 aina D (vai reāls 145345) |
| `boundary_uncertain` (STOP) | defokusēta robeža (§116) | atlicis: P8 (nav sintētiska defokusa etalona) |
| `failed` (vide/avots) | trūkst pakotnes/bojāts fails | P1 aina "nav" (negatīvs tests) |

### 1.2 Kadrējums (renderis)
- `slamjam` (slēgts siluets, fons ap malām) — P1 aina A.
- `original` (siluets pāri malai, nav izdomāta grieziena) — P1 aina B.
- `auto` izvēle starp tiem — P1 (noklusējums).
- `plan_closeup_crop` automātiskā apgriešana (maska nesasniedz 3 malas) —
  P1 aina B novēro (ja iedegas).

### 1.3 Krāsu profils
- WB `auto` ar neitrālu fonu — P1/P4.
- WB `auto` ar SILTU fonu -> GATE_K FAIL -> `identity` pārrenderēšana
  (§128 mācība) — P3.
- `wb_trusted=False` (krāsains fons -> identitāte automātiski) — P3
  novēro (koka grīdas variants).

### 1.4 Rotācijas
- 0 / 90 / 180 / 270 + resume mantošana — P2 (90 un 270; 180 = simetriskas
 ositās pārbaudes vienības testos).

### 1.5 lut_only ceļš (§131)
- verifikācija: pass / refused / STOP (papīrs redzams) — P4 + P1 negatīvs
  (kopskats deklarēts kā makro -> STOP ar skaitļiem).
- iznākumi: MASTER centra kvadrāts + MAKRO 2000x2500; checker A2/K/D/R/T,
  pārējie izlaisti AR reason — P4.

### 1.6 Atvasinātās detaļas (closeup.py, §120-125)
- tipa zonas: bikses/jaka/flanela/tops; zones-file pārraksts; vārti
  `coverage >= 0.80`, `upscale_geom <= 2.3` — P6 (atlikts; t125 lapa
  jau sedz tipu zonu loģiku; atkārtot pēc izmaiņām closeup.py).

### 1.7 Checker vārti
- 13 vārti normālam kadrām; lut_only izkārtojums; GATE_K auto/identity;
  sabotāžas (sagandēts PARAUGS/MAKRO -> R/K/A2 krit) — P7 (atlikts;
  vienības testi sedz; ražošanas mēroga 1-2 gadījumi P4 ietvaros).

### 1.8 Piegāde
- `make_zip`: tikai PARAUGS; PARAUGS+MAKRO jaukta grupa; `--files`
  izslēgšana (§81) — P5.

## 2. Sintētisko ainu ģenerators — `gen_scenes.py`

Deterministisks (fiksēta sēkla vienai ainai). Ainas:
| nosaukums | saturs | ko treniņš gaida |
|---|---|---|
| `A_kopskats` | gaišs krekls [201,201,203] uz neitrāla papīra + grīdas stūris, mērena ēna, slēgts siluets | isnet + slamjam |
| `B_mala` | tas pats, piedurkne pāri labajai malai | isnet + original |
| `C_enskaelis` | krekla augšdaļa dziļā ēnā (reālais 145345 gadījums) | QA noraida -> pad retry (vai godīgs STOP) |
| `D_haoss` | izkaisīti auduma gabali + spēcīga ēna | STOP needs_review |
| `E_siltpapirs` | silts papīrs [232,214,186], neitrāls krekls | auto WB -> GATE_K FAIL -> identity PASS |
| `F_makro` | pilnkadrs audums ar krokom (reālais 145647 gadījums) | lut_only verifikācija refused -> PASS |

## 3. Treniņu procedūra

Drillis darbojas IZOLĒTĀ kopijā `/tmp/pdrill` (repo kopija; `SRC_DIR`
pārrakstīts uz `/tmp/pdrill/uploads`; `output/` sava), lai īstie
uploads un output nepiesārņotos. Videi jābūt gatavai
(`python3 setup_v2.py` pēc katras smilškastes pārstartes).

```bash
# kopijas būve (no repo saknes):
mkdir -p /tmp/pdrill/uploads /tmp/pdrill/output
rsync -a --exclude .git --exclude output --exclude tmp_id \
      /home/user/loop_bildes/ /tmp/pdrill/
sed -i 's|SRC_DIR = "/home/user/uploads"|SRC_DIR = "/tmp/pdrill/uploads"|' /tmp/pdrill/loop.py
sed -i 's|SRC_DIR = _HERE.parent / "uploads"|SRC_DIR = _HERE / "uploads"|' /tmp/pdrill/checker_v2.py
python3 pasmacibas/gen_scenes.py --out /tmp/pdrill/uploads
# P1:
cd /tmp/pdrill && python3 workflow_v2.py --attempt 1 --files PDR_A_kopskats.jpg PDR_B_mala.jpg PDR_C_enskaelis.jpg PDR_D_haoss.jpg
python3 checker_v2.py
# P2 (rotācijas; katrai savais attempts, lai atskaites nemaisās):
... --attempt 2 --rotate PDR_A_kopskats:90 --files PDR_A_kopskats.jpg
... --attempt 3 --rotate PDR_A_kopskats:270 --files PDR_A_kopskats.jpg
# P3 (WB):
... --attempt 4 --files PDR_E_siltpapirs.jpg        # auto -> GATE K?
... --attempt 5 --rerender-saved --wb-mode identity --files PDR_E_siltpapirs.jpg
# P4 (lut_only ražošanas mērogā):
... --attempt 6 --files PDR_A2_kopskats.jpg PDR_F_makro.jpg --lut-only PDR_F_makro
python3 checker_v2.py
# P5 (ZIP):
... --make-zip --zip-name PDR_ZIP.zip
```

## 4. Pieņemšanas kritēriji (fiksēti PIRMS treniņiem)

- P1: katrai ainai ierakstīts ceļš un skaitļi; ja gaidītais ceļš
  neiedegas, tas ir ATKLĀJUMS (ierakstāms godīgi), nevis kļūda, ko
  slēpj.
- P2: maskas QA iztur rotāciju; MASTER izmērs/rotation_cw ierakstīts.
- P3: silta papīra auto WB GATE_K shift_b < -2.5 (FAIL); identity
  |shift_b| <= 2.5 (PASS). Ja auto neizkrīt — atklājums par WBShrink
  robežu.
- P4: lut_only verifikācija refused; MAKRO 2000x2500; checker 2/2 PASS
  ar izlaistajiem vārtiem AR reason.
- P5: ZIP satur gan PARAUGS, gan MAKRO failu; CRC OK.

## 5. Statuss

- [x] P0 plāns (šis fails)
- [x] P1 masku ceļi (1. kārta; pad_retry/plate paliek neizprovocēti sintētiski)
- [x] P2 rotācijas (90/270; bonuss: chroma_seeded ceļš iedegās pats)
- [x] P3 WB auto/identity (E2: −4,13 → −0,98; E v1 deva boundary_uncertain bonusu)
- [x] P4 lut_only ražošanas mērogā (arī bez-refused atzars)
- [x] P5 make_zip jaukts (ATRASTS DEFEKTS: lut_only ieraksti izkrīt no akumulācijas — sk. P_REZULTATI §2)
- [~] P6 auto→original atzars (2. kārta: H_salocits ✓); closeup zonas joprojām t125
- [x] P7 checker sabotāža ražošanas mērogā (2. kārta: MAKRO → R FAIL ✓)
- [x] P8 boundary_uncertain (iegūts P3 E v1: zemas kontrasta robeža)

Rezultāti: `P_REZULTATI.md`.
