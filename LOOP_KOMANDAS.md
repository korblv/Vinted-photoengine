# Loopa komandas — īsais ceļvedis tev

Šīs ir **sarunas komandas man**. Tev pašam kods nav jāpalaiž.
Apstiprinājumus vienmēr prasīšu ar **izvēles pogām**, lai tie nebūtu jāraksta.

## 1. Kā sākt jaunu bilžu grupu

1. Augšupielādē jaunās produktu bildes — visas uzreiz vai pa daļām.
2. Vari uzrakstīt tikai:

```text
Jauns komplekts
```

3. Es vispirms **tikai uzskaitīšu bildes** un ar pogām pajautāšu:

   **Vai šīs ir visas šīs grupas bildes?**

   - `Jā, šīs ir visas — sāc darbu` — tikai tad sāku apstrādi.
   - `Nē, vēl pievienošu` — gaidu nākamās bildes un pēc to augšupielādes
     pajautāšu atkal.

> Līdz izvēlēsies `Jā, šīs ir visas — sāc darbu`, jauno grupu neapstrādāšu.

Ja mainās arī paraugs, augšupielādē to un uzraksti:

```text
Jauns komplekts + jauns paraugs
```

## 2. Komandas darba laikā

| Komanda | Ko es izdarīšu |
|---|---|
| `Turpini loopu` | Turpināšu no `PROGRESS.md` saglabātā stāvokļa. |
| `Parādi statusu` | Īsi parādīšu posmu, gatavās bildes, vārtu rezultātus, krātuvi un to, vai gaidu tavu pogas izvēli. |
| `Veic pilnu auditu` | Palaidīšu checker A2/B/C/D/F/H/T un vizuālo masku/malu pārbaudi; ziņošu par defektiem, pirms turpināšu. |
| `Pārbaudi tikai maskas` | Pārbaudīšu masku robežas, vecā fona atlikumus un apģērba „iekodienu”, pašas bildes bez vajadzības nepārrenderējot. |
| `Pārrenderē no saglabātajām maskām` | Atkārtoti izveidošu attēlus no nemainītām v2.1 maskām, piemēram, tikai krāsu profila vai renderēšanas labojumam. |
| `Izlabo: <kas nav labi>` | Veikšu jaunu iterāciju tikai par šo problēmu, pēc tam atkārtošu auditu un kolāžu. |
| `Apturi darbu` | Apstāšos un ierakstīšu precīzu pašreizējo stāvokli `PROGRESS.md`. |
| `Notīri krātuvi` | Izmērīšu krātuvi un dzēsīšu vecos pagaidu/testa failus; aktīvo grupu bez lejupielādes apstiprinājuma nedzēsīšu. |
| `Pilotē ViTMatte` | Tikai kā kontrolētu eksperimentu uz vienas bildes; ražošanā pieņemšu vienīgi tad, ja tas būs labāks par pašreizējo malas apstrādi un izies H vārtus. |

## 3. Beigu posms — tikai ar pogām

1. Es izveidoju un parādu **kolāžu ar visām grupas bildēm**.
2. Tu izvēlies:
   - `Apstiprināt` — izveidoju `.zip` ar gala `PARAUGS_2000x2500` bildēm;
   - `Noraidīt` — laboju norādīto problēmu un kolāžu parādu atkārtoti.
3. Kad `.zip` būs gatavs un tu to lejupielādēsi, izvēlies:
   - `Lejupielādēju — dzēst grupu` — izdzēsīšu grupas attēlu failus;
   - `Vēl nedzēst` — grupa pagaidām paliks darba telpā.
4. Pēc grupas dzēšanas darba telpa ir gatava **tikai nākamajai vienai**
   bilžu grupai.

## 4. Pilna secība vienā rindā

```text
Augšupielāde
→ poga „Vai šīs ir visas bildes?”
→ inventārs, krātuves pārbaude un v2.1 preflight
→ ISNet maska → QA → vajadzības gadījumā GrabCut fallback
→ viens krāsu profils visam komplektam un renderēšana
→ checker A2/B/C/D/F/H/T + vizuālais zoom audits
→ kolāža
→ poga „Apstiprināt / Noraidīt”
→ .zip (tikai pēc apstiprinājuma un checker PASS)
→ poga „Lejupielādēju — dzēst grupu / Vēl nedzēst”
→ nākamā grupa
```

## 5. Rīki, kurus izmantošu nākamajai grupai

Pašreizējais noklusējuma ceļš ir **Workflow v2.1**.

- **Vide:** `setup_v2.py` pārbauda/atajauno piesprausto rembg,
  ONNX Runtime un ISNet modeli ārpus darba telpas, lai darba telpa
  paliktu maza arī pēc sandbox atiestatīšanas.
- **Pilns apģērba kadrs:** `isnet-general-use` caur `rembg` /
  ONNX Runtime. Masku pieņem tikai pēc automātiskas QA.
- **Tuvplāni:** vispirms pārbaudītā sēklu bibliotēka; jaunai bildei
  automātisks sēklu priekšlikums un eksperimentāls GrabCut. Ja QA to
  noraida, bilde tiek atzīmēta `needs_seed_review` un netiek klusām
  paslīdēta kā gatava.
- **Orientācija:** ja bilde atnāk šķērsām (piemēram, bikšu jostasvieta
  pie kadra sāna, staras horizontāli), pirms apstrādes to pagriežu
  vertikāli bezzaudējumu 90° pagriezienā, lai apģērbs stāvētu dabiskā
  pozīcijā. Tev bildes pirms augšupielādes nav jāpagriež.
- **Krāsas:** viens deterministisks LUT profils visam komplektam ar
  baltā balansa, ekspozīcijas, maiga kontrasta un clipping aizsardzības
  korekciju. Apģērba forma, krokas, birkas un tekstūra netiek ģenerētas.
- **Malas:** 7. iterācijas alfa apstrāde, priekšplāna krāsas
  paplašināšana un premultiplicēta izmēra maiņa.
- **Pārbaude:** `checker_v2.py` vārti A2/B/C/D/F/H/T plus piezūmēta
  vizuāla masku/malu pārbaude.

## 6. Ko nozīmē galvenie faili

- `uploads/` — tavas oriģinālbildes un parauga atsauces.
- `output/master/*_MASTER_1to1.png` — 1:1 meistari oriģināla
  koordinātās pēc viena deterministiska komplekta LUT krāsu profila.
- `output/paraugs/*_PARAUGS_2000x2500.jpg` — publicēšanai gatavās bildes.
- `output/masks/` — maskas un malas alfa auditam.
- `output/audits/*_SEED_PROPOSAL.jpg` — automātisko tuvplāna sēklu
  vizuālais priekšlikums, ja bildes nav pārbaudītajā bibliotēkā.
- `output/report_v2_maker.json` — maker atskaite ar metodēm, statusiem,
  SHA-256 un laikiem; to raksta inkrementāli pēc katras bildes.
- `output/report_v2.json` — neatkarīgie checker rezultāti.
- `output/grade_profile_v2.json` — komplekta LUT un clipping audita dati.
- `output/delivery_v2.json` — pēc ZIP izveides: ZIP izmērs, SHA-256
  un katra ieraksta kontroles dati.
- `output/V2_KOLAZA.jpg` — standarta kolāža pirms apstiprinājuma.
- `PROGRESS.md` — loopa atmiņa un pašreizējais stāvoklis.
- `LOOP.md` — v1 vēsturiskie noteikumi; `WORKFLOW_V2.md` — pašreizējā
  v2.1 specifikācija.

## 7. Tehniskās komandas

Šīs komandas darba laikā palaižu es; tev tās nav jāpalaiž. Tās šeit ir
tikai caurspīdīgumam:

```bash
cd /home/user/loop_bildes

# Vides pārbaude / atjaunošana pēc sandbox atiestatīšanas
python3 setup_v2.py --check
python3 setup_v2.py

# Precīzs jaunas grupas failu saraksts un preflight
python3 workflow_v2.py --preflight --files FAILS1.jpg,FAILS2.jpg

# Pilna v2.1 apstrāde un automātiska kolāža
python3 workflow_v2.py --attempt 1 --files FAILS1.jpg,FAILS2.jpg

# Turpināšana ar SHA-256 pārbaudītām saglabātajām maskām
python3 workflow_v2.py --attempt <n> --resume --files FAILS1.jpg,FAILS2.jpg

# Tikai jauna krāsu profila/renderējuma atkārtojums no saglabātajām maskām
python3 workflow_v2.py --attempt <n> --rerender-saved --files FAILS1.jpg,FAILS2.jpg

# Neatkarīgā pārbaude
python3 checker_v2.py

# ZIP tikai pēc lietotāja apstiprinājuma un checker PASS
python3 workflow_v2.py --make-zip --zip-name GALA_BILDES.zip

# Vienību testi
python3 test_workflow_v2.py
```

## 8. Parasti pietiek ar divām frāzēm

- Sākumam pēc augšupielādes: **`Jauns komplekts`**
- Ja saruna vai darbs ir pārtraukts: **`Turpini loopu`**

Visus pārējos apstiprinājumus turpmāk veiksim ar pogām.
