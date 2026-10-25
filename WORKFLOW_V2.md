# WORKFLOW V2.1 — ātruma ražošanas modelis

## Mērķis
Apstrādāt vienas kompozīcijas bildes ražošanas tempā: mērķis ir aptuveni
**20 sekundes vienai bildei**, nezaudējot apģērba oriģinālo saturu.

## Sarkanās līnijas v2 režīmā
- AI drīkst veidot tikai apģērba masku / nošķirt fonu.
- Apģērbu nedrīkst ģeneratīvi pārzīmēt, deformēt vai izdomāt tam jaunas
  detaļas. **Vienīgais atļautais pagrieziens** ir visa kadra bezzaudējumu
  pagriešana par 90° soļiem (`transpose` — pikseļu vērtības nemainās,
  tikai pārkārtojas), lai šķērsām nofotografēts apģērbs stāvētu
  vertikāli dabiskā orientācijā (apkakle/jostasvieta augšā, apakšmala
  lejā; birkas teksts lasāms). Brīva leņķa iztaisnošana un apģērba
  ģeometrijas korekcija joprojām ir aizliegta.
- Atļauta viena globāla Lightroom tipa krāsu un kontrasta korekcija visam
  komplektam. Tā maina pikseļu vērtības, bet nemaina apģērba ģeometriju,
  krokas, birkas, tekstūru vai defektus.
- Fons ir deterministisks `#F3F3F3`, ar mīkstu ēnu un 2000×2500 kadru.
- Vienīgais izņēmums deformācijas aizliegumam ir **atvasinātie detaļu
  kadri** (skat. sadaļu zemāk): deterministiska perspektīvas
  transformācija no MASTER pikseļiem, bez ģeneratīvas pārzīmēšanas,
  ar vārtiem, izcelsmes pierakstu un marķējumu faila nosaukumā.
  Galvenie priekšas/aizmugures kadri šim izņēmumam neattiecas.

## Pipeline
0. Pirms grupas palaiž `setup_v2.py --check` vai maker `--preflight`.
   Piespraustās pakotnes un ISNet modelis atrodas `/var/tmp`, tāpēc pēc
   sandbox atiestatīšanas tos reproducējami atjauno `setup_v2.py`, bet
   pašā darba telpā paliek tikai kods un atskaites.
1. Katrai bildei atsevišķā procesā palaiž ISNet (`isnet-general-use`) uz
   **malu attiecību saglabājošas** darba kopijas ar maksimālo izmēru
   768×1024. Atsevišķs process novērš ONNX atmiņas uzkrāšanos.
2. AI maskai veic automātisku QA: segums, lielākās komponentes īpatsvars un
   apģērba robežkastes proporcijas. Ja AI ir izvēlējies tikai birku,
   apkakli vai citu mazu objektu, masku noraida.
3. Noraidītam tuvplānam vispirms izmanto pārbaudīto GrabCut sēklu
   bibliotēku. Ja bildes bibliotēkā nav, v2.1 automātiski veido sēklu
   priekšlikumu no ar malu savienota gluda fona un augstas tekstūras
   auduma kodola, saglabā `output/audits/*_SEED_PROPOSAL.jpg` un mēģina
   eksperimentālu auto-GrabCut. Ja rezultāts neiztur QA, bilde iegūst
   statusu `needs_seed_review`, bet pārējā grupa turpinās.
4. Pēc masku izveides no komplekta fona un apģērba pikseļiem aprēķina
   vienu krāsu profilu: daļēju baltās krāsas balansa neitralizēšanu,
   ekspozīcijas normalizēšanu pēc apģērba gaišajiem toņiem, maigu
   S-līknes kontrastu un automātisku clipping drošības korekciju.
   Profils tiek saglabāts kā 3×256 LUT.
5. Renderē `MASTER_1to1` tajās pašās koordinātās un `PARAUGS_2000x2500`
   ar esošo 7. iterācijas malas alfa, priekšplāna krāsas paplašināšanu un
   premultiplicēto samazināšanu. Gala JPG piemēro vieglu izvades asināšanu.
   Maker pats izveido standarta `V2_KOLAZA.jpg`; ZIP veido tikai atsevišķa
   `--make-zip` komanda **pēc lietotāja apstiprinājuma** un tikai tad,
   ja checker visām bildēm saka PASS.
6. `checker_v2.py` pārbauda, ka MASTER kodols atbilst deterministiski
   koriģētajam oriģinālam, fons ir `#F3F3F3`, maska un formāts ir veseli,
   tuvplāns ir full-bleed, alfa paliek šaurā malas joslā un kopējais laiks
   ir mērķa zonā. Nepabeigtie/`failed` ieraksti tiek atsevišķi uzskaitīti
   checker `_meta` sadaļā un bloķē sekmīgu koprezultātu.

## Atvasinātās detaļas (Slam Jam režīms, PROGRESS §118–§123)
No pabeigtiem priekšas/aizmugures `MASTER_1to1` kadriem (ar masku un
profilu) `closeup.py --mode slamjam` veido 2000×2500 detaļu kadrus
Slam Jam ģeometrijā (STUDIJAS M9 mērījumi; POC-1..3 kvalitātes
robežas).
- **Zonas:** ražošanas lietojumā 2 detaļas vienam apģērbam; zonas
  norāda ar `--zones-file` (JSON `{stem: [{tag, center_xy, src_h}]}`,
  koordinātas MASTER pikseļos). Bez zonu faila Slam Jam režīms lieto
  tipa apzinīgu automātisko priekšlikumu: augšdaļai kakls/birka +
  aproce vai apakšmala, apakšdaļai jostasvieta + kabata vai
  apakšmala (tips no apģērba bbox malu attiecības; ja kandidātu
  nepietiek — kritiens atpakaļ uz veco akcentu meklētāju).
  Priekšlikums nav piegādes lēmums: zonas un rezultātu rāda
  lietotājam kolāžā apstiprināšanai pirms piegādes.
- **Ģeometrija (D recepte):** novirze no normāles 34° (kamera ~56°
  virs plaknes), pagrieziens −7°, perspektīvas gradients 1.22,
  LANCZOS4, USM r=2/60%/slieksnis 3. Audums un maska tiek
  transformēti atsevišķi; LUT no avota profila; studijas ēna tiek
  ģenerēta no jauna izejas mērogā.
- **Vārti:** efektīvais ģeometriskais palielinājums ≤ 2.3×, avota
  reģions ≥ 19% no izejas pikseļiem, apģērba segums ≥ 0.80
  (pazemināt drīkst tikai apzināti ar CLI, piem. diagonālai
  piedurknei). Ja vārti neiziet: fails netiek rakstīts, tāda paša
  nosaukuma novecojusi versija tiek noņemta, iemesls paliek
  `_TUVPLANI.json`. Lauka noklusējums: `max(0.45 × apģērba bbox
  augstums, vārtu minimums)` vai `src_h` no zonu faila.
- **Izcelsme un robežas:** failos marķējums `_ATVASINATA`; atskaite
  glabā avota MASTERI, centru, četrstūri, ģeometrijas parametrus un
  vārtu skaitļus. Mikrodetalizācija nerodas no jauna: 100% mērogā
  atvasināta detaļa ir mīkstāka par īstu tuvplānu, un birkas teksts
  ir salasāms tikai tad, ja tas ir salasāms avota reģionā.
- Piemērs: `python3 closeup.py --stems STEM_FRONT STEM_BACK
  --mode slamjam --zones-file zones.json`.

## Orientācijas noteikums (lietotāja norāde 2026-10-21)
Ja atsūtītā bilde ir „uz sāniem" (piemēram, bikšu jostasvieta ir pie kadra
labās malas un staras plešas pa kreisi), bildi pirms apstrādes pagriež
vertikāli — piemērā ar jostasvietu labajā malā tā ir pagriešana par 90°
pret pulksteņrādītāja virzienu (`270` grādi pulksteņrādītāja virzienā),
lai jostasvieta būtu augšā un staras vērstas uz leju. Lēmumu pieņem
vizuāli pēc apģērba dabiskās „augšas" (apkakle, jostasvieta, birkas
teksta lasāmība), to ieraksta `PROGRESS.md` un maker izsauc ar
`--rotate STEM:270` (pieļauj arī `STEM:ccw`/`STEM:cw`). Pagrieziens:
- notiek pirms maskas veidošanas un attiecas uz visu plūsmu (ISNet
  worker to saņem caur `WORKFLOW_V2_ROTATE`);
- tiek fiksēts maker atskaitē kā `rotation_cw`; checker oriģinālu
  salīdzina tajā pašā pagrieztā orientācijā;
- ir bezzaudējumu pikseļu pārkārtojums — apģērbs, krokas un tekstūra
  nekādi citādi nemainās;
- ar `--resume`/`--rerender-saved` tiek pārmantots no iepriekšējās
  atskaites, un maska ar citu pagriezienu netiek izmantota atkārtoti.
Demonstrācijas bilde (`MVIMG_20261020_161031.jpg`, 4096×3072) pēc
lietotāja lūguma netika apstrādāta un tika izdzēsta no krātuves.

## Pilotā izmērītie modeļu fakti šajā sandboxā
- `u2netp`: 0,23–0,28 s, bet pilnajam kadram izlaiž piedurknes un
  tuvplānos izvēlas tikai daļu apģērba.
- `silueta`: 0,81–0,92 s, bet pilnajam kadram izlaiž vienu piedurkni;
  tuvplānos arī izvēlas birkas/apkakles daļu.
- `isnet-general-use`: pilnajam kadram 1,45 s un vizuāli pilns siluets;
  tuvplānos izvēlas birku/apkakli, tāpēc QA to noraida.
- SegFormer ADE un clothes-seg modeļi bija ātri, bet plakaniski izklāta
  apģērba tuvplānos nedeva izmantojamu pilnu auduma masku.
- Smagie BiRefNet/BEN2/SAM ceļi šajā 2 vCPU / ~1,9 GB RAM vidē vai nu
  pārsniedz ātruma mērķi, vai izsauc OOM bez pagaidu swap.

## Secinājums pilotam un v2.1 statuss
Šajā vidē godīgs v2 joprojām ir **AI-first hibrīds**, nevis apgalvojums,
ka katru tuvplānu 20 sekundēs ideāli izdara viens lokāls AI modelis.
Pilniem kadriem AI jau ir pietiekami ātrs un labs. Tuvplāniem ražošanas
ātrumu dod QA + GrabCut fallback. Pēc lietotāja lēmuma pagaidām paliekam
pie šī lokālā modeļa; GPU/mākoņa maskas pilots ir atlikts. v2.1
auto-sēklas var paātrināt jaunas grupas sākšanu, bet tās ir
**eksperimentālas**, līdz tiek pārbaudītas uz neredzētiem tuvplāniem un
zoom malu audita. Pārbaudītā sēklu bibliotēka vienmēr ir prioritāte.

## Henley pilota izmērītais rezultāts
- 160538: ISNet, **7,80 s**.
- 160550: ISNet QA noraidīja → GrabCut fallback, **10,63 s**.
- 160601: ISNet QA noraidīja → GrabCut fallback, **13,33 s**.
- 160608: ISNet QA noraidīja → GrabCut fallback, **10,17 s**.
- 160645: ISNet QA noraidīja → GrabCut fallback, **10,52 s**.
- Vidēji: **10,49 s/bilde**; visas 5 bildes iztur `checker_v2.py`.
- Krāsu LUT: WB `(0.956044, 1.0, 1.109544)`, ekspozīcija `1.06`,
  gaišo toņu rolloff no `0.86`, S-līknes kontrasts `0.18`.
- Būtiskākais renderēšanas paātrinājums bija atteikšanās no PIL PNG
  `optimize=True`; tas augstfrekvences auduma attēliem varēja pievienot
  apmēram 10–12 sekundes bez proporcionāla vietas ieguvuma.

## v2.1 profesionālais cietināšanas posms (2026-10-21)
Bez jaunām produktu bildēm veikti koda, drošības un testēšanas
uzlabojumi:
- `setup_v2.py` reproducējami atjauno rembg 2.0.85, onnxruntime 1.31.0,
  piesprausto NumPy/SciPy/Pillow steku un 178,648,008 baitu ISNet modeli
  ārpus darba telpas.
- Izvēlēto failu sarakstu tagad var nodot precīzi ar `--files`;
  EXIF orientācija visos maker/checker posmos tiek interpretēta vienādi.
- Maker atskaite tiek rakstīta atomiski pēc katras bildes; `--resume`
  atkārtoti izmanto masku tikai tad, ja avota SHA-256 sakrīt.
- Viena kļūdaina bilde vairs neaptur grupu. Statusi: `completed`,
  `needs_seed_review`, `failed`.
- Krāsu profils automātiski samazina ekspozīciju, ja paraugu kodolos
  prognozētā clipping daļa pārsniedz drošības slieksni.
- Maker izveido standarta kolāžu; `--make-zip` pārbauda checker PASS,
  ZIP CRC un ierakstu baitiskā identiskuma atbilstību JPG failiem.
- Checker vairs neavarē bez atskaites un pievieno malas informatīvās
  metrikas, nemainot esošos A2/B/C/D/F/H/T sliekšņus.
- `test_workflow_v2.py`: 8/8 vienību testu iziet (t.sk. bezzaudējumu
  90° pagriešanas tests). Sintētiskā tuvplāna
  auto-sēklu + GrabCut integrācijas testā IoU bija 0,990 un maskas QA
  bija PASS; tas nav pierādījums kvalitātei uz reāliem audumiem.

### Jaunas grupas pamatkomandas
```bash
python3 /home/user/loop_bildes/setup_v2.py          # tikai ja preflight ziņo, ka vide pazudusi
python3 /home/user/loop_bildes/workflow_v2.py --preflight --files FAILS1.jpg,FAILS2.jpg
python3 /home/user/loop_bildes/workflow_v2.py --attempt 1 --files FAILS1.jpg,FAILS2.jpg
python3 /home/user/loop_bildes/checker_v2.py
# Tikai pēc kolāžas apstiprinājuma ar pogu:
python3 /home/user/loop_bildes/workflow_v2.py --make-zip --zip-name GALA_BILDES.zip
```
