# PROGRESS — loopa atmiņa (ārpus sarunas)

Komplekts: Uniqlo waffle henley (balts/krēmkrāsas), izmērs L
Avots: uploads/MVIMG_20261020_*.jpg (5 bildes, 3072×4096, mājas apstākļi)
Paraugs: uploads/slamjam_mfpen_trousers*.jpg (2000×2500, fons #F3F3F3)

Bilžu kartējums:
- MVIMG_20261020_160538 — pilnais kadrs no priekšas (kadrā arī kājas/apavi — jāpazūd)
- MVIMG_20261020_160550 — tuvplāns: kakla izgriezums + birka
- MVIMG_20261020_160601 — tuvplāns šķērsām: izgriezums + pogas
- MVIMG_20261020_160608 — tuvplāns: izmēra birka (L, Made in Indija)
- MVIMG_20261020_160645 — tuvplāns: kopšanas/sastāva birka
- Mugurpuses kadra komplektā NAV — loops to neizdomā (sarkanā līnija Nr.1)

## Iterācijas
- [x] Iterācija 1: pilots (160538), u2net — maska OK (segums 0.355), bet process
      nogalināts (OOM) kompozīcijas solī (float32 pilna kadra masīvi).
      Stratēģijas maiņa: uint8 + apstrāde rindkopās, ēnai pelēktoņu fons.
- [x] Iterācija 1 vizuālā pārbaude E: **FAIL** — u2net maska pilnībā izlaida krekla
      labo piedurkni (maskā tās nav), lai gan fons/ēna un pārējais siluets pareizi.
      Secinājums: skaitliskie vārti vien nepietiek; modelis jāmaina.
- [x] Iterācija 2: pilots ar isnet-general-use + atmiņu taupoša kompozīcija
      → pilnais kadrs (160538) iziet VISUS vārtus A–E (maska 0.403, abas
      piedurknes vietā, pikseļi maxdiff=0). Stratēģija pilnajam kadram apstiprināta.
- [x] Iterācija 2 partija uz tuvplāniem: **FAIL (E un daļēji C)** — isnet par
      "objektu" izvēlas birku/pogu laukumu (segumi 0.007–0.245), audumu uzskata
      par fonu. Diagnostika: output/diagnostika_tuvplani_iter2.jpg
- [x] Iterācija 3 diagnostika: watershed (tekstūra+krāsa) — vājš, noraidīts;
      u2net_cloth_seg — nomira atmiņas dēļ (768×768 U-Net > 2GB), noraidīts;
      **GrabCut ar konservatīvām sēklām (512px tests) — segumi 0.65–0.93,
      robežas vizuāli pareizas.** Diagnostika: diagnostika_tuvplani_grabcut.jpg
      (160601 sēkla koriģēta pēc augšmalas piezūmēšanas: augša = drošs fons.)
- [x] Iterācija 3: tuvplāni produkcijā ar GrabCut (--mode closeup, 960px)
      → A–D PASS visām 5 bildēm; E: 160550/160601/160645 PASS,
      160608 FAIL — virs apmales palika vecā fona pleķis (papīra šķiedru
      tekstūra 960px mērogā deva viltus auduma sēklas).
- [x] Iterācija 3b (sēklas korekcija): 160608 drošā fona josla līdz y=0.315 —
      pleķis samazinājās, bet E joprojām FAIL (pelēka ēnas josla virs apmales;
      GrabCut robežu velk pa ēnas ārējo pāreju). Diagnostikā salīdzināti
      varianti (512/960, ar/bez tekstūras sēklām).
- [x] Iterācija 3c: 160608 bez tekstūras sēklām + top_edge_snap → E PASS
      (robeža iet pa auduma augšējo vīli, pleķis/ēnas josla pazuduši).
- [x] Checker A–D + vizuālā pārbaude E visam komplektam: **5/5 PASS**
      (skat. output/report.json un GALA_PARSKATS.md)

## STĀVOKLIS: GAIDA CILVĒKA LĒMUMU (ārējā cilpa)
Komplekts ir gatavs apstiprināšanai pēc output/paraugs/*_PARAUGS_2000x2500.jpg.
Apstiprinājums → publicēt. Noraidījums ar iemeslu → jauna iterācija ar
mainītu parametru (piem., ēnas stiprums/nobīde, sēklas, kadrējums).

## Ārējās cilpas atgriezeniskā saite (2026-10-21)
- Lietotājs: "Priekšpuse ir labi, bet pārējām ir nogrieztas malas, vajadzētu
  būt pilnā izmērā." → Priekšpuse APSTIPRINĀTA. Tuvplāni NORAIDĪTI kadrējuma
  dēļ: contain (1875×2500 + sānu joslas) lika audumam izskatīties nogrieztam
  pirms malas; parauga tuvplāni ir full-bleed līdz kadra malām.
- [x] Iterācija 4: tuvplāni → cover uz 2000×2500 (bez sānu joslām; griež tikai
      ~6.25% augstuma centrāli), pievienoti F vārti checker.py (PASS: 3/4, 3/4,
      3/4, 4/4 malas), E pārbaude: birkas/pogas nav apgrieztas, audums sasniedz
      kadra malas. Vecie contain varianti → output/archive_iter3_contain/.
      Pārskata lapa PARSKATS_5_bildes.jpg un GALA_PARSKATS.md atjaunoti.
- STĀVOKLIS: atkal GAIDA CILVĒKA LĒMUMU par koriģētajiem tuvplāniem.

## Ārējās cilpas atgriezeniskā saite #2 (2026-10-21)
- Lietotājs 160550 bildē atrada palikušu papīra gabalu augšā labajā pusē un
  pieprasīja pārliecināties, ka VISĀM bildēm maska ir ideāla.
- Audits (output/audits/, piezūmētas visas robežas + koordinātu režģi):
  160538 tīrs; 160550 defekts apstiprināts (papīra/ēnas ķīlis aiz apkakles
  x~0.82–0.92, y~0.285–0.315); 160601 tīrs; 160608 tīrs;
  160645 atrasts papildu defekts — galda plakne tās ēnā (diagonālā josla +
  sprauga zem apakšējās malas) bija maskā kā "audums".
- [x] Iterācija 5: BG sēklas ķīlī (160550, 2 sēklas — pēc pirmās vēl palika
      mazs atlikums, noķerts 2× zūmā) un ēnas zonās (160645) iestrādātas
      CLOSEUP_SEEDS, G vārti pievienoti LOOP.md. Pārpalaišana + checker A–F
      (5/5 PASS) + atkārtots audits: pleķi pazuduši, audums nav skarts.
      (Procesu piezīme: pirmā 160550 pārpalaišana sēklu nepielietoja paralēlu
      loop.py labojumu konflikta dēļ — noķerts ar hash salīdzinājumu, izlabots.)
      Audita protokols: MASKU_AUDITS.md; pārskata lapa atjaunota.
- STĀVOKLIS: GAIDA CILVĒKA APSTIPRINĀJUMU izlabotajām 160550/160645 bildēm.

## Ārējās cilpas atgriezeniskā saite #3 (2026-10-21)
- Lietotājs: "MVIMG_20261020_160645_PARAUGS_2000x2500 ir melni pikseļi apakšā
  nav ideāli." Atkārtotais audits apstiprināja, ka iter.5 secinājums par
  160645 apakšmalu bija nepilnīgs: pēdējās 50 rindās bija 5 625 pikseļi ar
  vidējo luminanci <60, galvenokārt zem baltās vīles izvirzītā galda/spraugas
  blokā. Iter.5 izvade arhivēta `output/archive_iter5_pirms_apaksas_labojuma/`.
- [x] Iterācija 6: `closeup_mask` vairs neaizpilda fona komponenti, kurā ir
      drošā fona (`GC_BGD`) sēkla; 160645 apakšējās spraugas sēkla paplašināta
      slīpi gar vīli līdz y=1.000 un x≈0.690. Pārpalaišana tikai 160645,
      checker visām 5 bildēm: A–D/F 5/5 PASS; 160645 segums 0.8819,
      A kodols 11 078 083 px, max diff 0. Tumšie (<60) pikseļi pēdējās
      50 rindās: 5 625 → 407; pikseļu mēroga salīdzinājums apstiprina, ka
      atlikusī šaurā josla ir īstā apakšējā auduma slāņa sānu mala, bet galda
      sprauga ir ārpus maskas. Atjaunotas `audits_160645.jpg`,
      `PARSKATS_5_bildes.jpg`, `MASKU_AUDITS.md` un `GALA_PARSKATS.md`.
- STĀVOKLIS: GAIDA CILVĒKA APSTIPRINĀJUMU iter.6 160645 bildei; pārējās
  4 bildes šajā iterācijā nav mainītas.

## Ārējās cilpas atgriezeniskā saite #4 (2026-10-21)
- Lietotājs: 160645 ir labāk, maska ir laba, bet vietām drēbju maliņas
  izskatās robainas; jautāja, vai profesionāli būtu pielietot nedaudz blur.
  Ieteikums: neblurēt attēlu, tikai maskas alfa pāreju. Lietotājs apstiprināja:
  "Veido 7 iterāciju".
- [x] Iterācija 7: A/B testos salīdzināta pašreizējā alfa, attāluma pāreja,
      guided-filter varianti un kontūras izlīdzināšana + kontrasta
      atjaunošana. Guided varianti noraidīti redzamāka oreola dēļ. Ražošanā
      visām 5 bildēm no saglabātajām binārajām maskām: attāluma alfa ±1,6 px,
      Gaussian kontūras izlīdzināšana σ=1,6, kontrasts 1,65, priekšplāna
      krāsas paplašināšana tieši ārpus maskas un premultiplicēta RGBA
      samazināšana. Checker pievienoti H vārti; visas 5 bildes A–D/F/H PASS,
      A max diff joprojām 0, daļējā alfa ne tālāk par 2,0 px no robežas.
      Iter.6 izvades: `output/archive_iter6_pirms_malu_labojuma/`; protokols:
      `MALU_AUDITS_ITER7.md`; audita lapas un pārskats atjaunoti.
- STĀVOKLIS: GAIDA CILVĒKA APSTIPRINĀJUMU iter.7 malu kvalitātei visam
  komplektam.

## Ārējās cilpas atgriezeniskā saite #5 — krātuve (2026-10-21)
- Lietotājs norādīja uz Workspace brīdinājumu (128,6/128,0 MB) un noteica:
  vienmēr sekot krātuvei, vecos failus neglabāt un brīvo vietu turēt pēc
  iespējas lielāku.
- [x] Tīrīšana: dzēsti visi veco iterāciju arhīvi, audita/testa/diagnostikas
      attēli, SOFTMASK dublikāti un `__pycache__` (atbrīvoti 28 076 379 baiti).
      Aktuālie MASTER PNG papildus bezzudumā optimizēti ar kompresiju 9
      (vēl 1 911 982 baiti; dekodēto pikseļu SHA-256 pirms/pēc identiski).
      Saglabāti tikai aktuālie MASTER/PARAUGS, maskas/ALPHA, JSON, kopskats,
      kods un dokumenti; `uploads/` oriģināli nav aiztikti.
- [x] Pastāvīga kārtība ierakstīta `LOOP.md` 7. sadaļā; `loop.py` vairs
      nesaglabā SOFTMASK, PNG raksta ar `compress_level=9` un beigās izdrukā
      `KRĀTUVE:` izmēru. Pēc tīrīšanas: `/home/user` 100,41 MB (46 faili),
      `loop_bildes` 55,56 MB (36 faili), `uploads` 44,86 MB.

## Atmiņas/swap un ātruma side-by-side (2026-10-21)
- Inventārs: 2 vCPU, 1,9 GB RAM, cgroup limits 1 944 915 968 baiti, bez GPU;
  swap rīki un sudo pieejami. Fizisko RAM no sandbox iekšpuses palielināt
  nevar.
- [x] 2 GB faila swap tests: īstais 160645 saved-mask renderings bez swap
      2,025 s/473 MB, ar swap 2,046 s/473 MB — ātruma ieguvuma nav. 2400 MB
      stresa tests bez swap tika OOM-nogalināts, ar swap pabeigts 11,26 s
      (VmSwap ~990 MB). Swap pēc testa izslēgts un fails dzēsts; secinājums:
      swap tikai kā īslaicīga OOM drošība, nevis paātrinājums.
- [x] Lielākais atrastais ātruma zudums bija PNG 9. līmenis: 12,365 s pret
      3,248 s 6. līmenī, ietaupot tikai 0,43 MB. `loop.py` pievienots
      `--png-level` ar noklusēto 6. Pilns protokols:
      `ATMINAS_UN_ATRUMA_TESTI.md`.
- [ ] Checker A–D + vizuālā pārbaude E pilotam
- [ ] Ja pilots iziet vārtus → visa partija (5 bildes) ar to pašu stratēģiju
- [ ] Ja neiziet → iterācija 2 (isnet-general-use) / iterācija 3 (parametri)
- [ ] Gala lēmums: cilvēks (ārējā cilpa)

## Pastāvīgais piegādes noteikums (2026-10-21)
- Lietotājs noteica turpmāko secību: pirms gala rezultāta vispirms jāizveido
  un jāparāda kolāža ar visām komplekta `PARAUGS_2000x2500` bildēm.
- `.zip` arhīvu ar apstiprinātajām gala bildēm veido tikai pēc tam, kad
  lietotājs kolāžu ir skaidri apstiprinājis. Noteikums ierakstīts
  `LOOP.md` 8. sadaļā.
- Lietotājs lika šo secību piemērot arī pašreizējam Henley komplektam.
  Darba telpā vienlaikus tur tikai vienu aktīvu produktu bilžu grupu:
  pēc lejupielādes apstiprinājuma grupas attēlu failus (`uploads/`
  avotus, MASTER/PARAUGS, maskas, kolāžu un `.zip`) dzēš, saglabājot
  kodu, dokumentāciju, īsu tekstuālu vēsturi un parauga atsauces.
- Lietotājs apstiprināja pašreizējo kolāžu un noteica, ka turpmāk
  apstiprinājumi jāprasa ar saskarnes izvēles pogām, nevis rakstītu
  tekstu. Noteikums ierakstīts `LOOP.md` 8. sadaļā.
- [x] Izveidots `output/Uniqlo_Polo_20261020_GALA_BILDES.zip`
      (6 689 288 baiti; SHA-256
      `4231d1c69d4915c505d6f3829f7bb4808cda6f98d84181ef26700431a214c4bd`)
      ar visām 5 apstiprinātajām `PARAUGS_2000x2500` JPG bildēm;
      arhīva CRC pārbaude izieta.
- [x] Lietotājs ar izvēles pogu apstiprināja `Lejupielādēju — dzēst
      grupu`. Dzēsti 32 šīs grupas faili: 5 `uploads/` avoti, 5 MASTER,
      5 PARAUGS, 15 maskas/ALPHA, kolāža un `.zip`; atbrīvoti
      108 887 837 baiti (103,84 MB). Pēc tīrīšanas `/home/user` ir
      2,96 MB un `loop_bildes` 0,07 MB. Saglabāts kods, dokumentācija,
      JSON atskaites un parauga atsauces.
- STĀVOKLIS: Henley komplekts ir piegādāts un slēgts; darba telpa ir
  gatava vienai jaunai bilžu grupai.

## Pastāvīgais jaunas grupas starta noteikums (2026-10-21)
- Lietotājs noteica: pēc katras jaunas produktu foto augšupielādes vispirms
  ar izvēles pogām jāpajautā, vai šīs ir visas šīs grupas bildes.
- Ja atbilde ir `Nē, vēl pievienošu`, darbu nesāk; gaida nākamo
  augšupielādi un jautājumu uzdod atkārtoti. Tikai pēc
  `Jā, šīs ir visas — sāc darbu` sāk komplekta inventarizācijas fiksēšanu
  un loopa izpildi. Noteikums ierakstīts `LOOP.md` 1. sadaļā.
- Lietotājam sagatavotas īsās sarunas komandas un pilna procesa secība
  failā `LOOP_KOMANDAS.md`.

## Atkāpes no parauga (apzinātas, pikseļu saglabāšanas dēļ)
- Apģērbs netiek rotēts/iztaisnots, krokas un mājas apgaismojums UZ APĢĒRBA paliek
  kā oriģinālā — citādi tiktu pārkāpta "oriģinālo pikseļu" prasība.
- Parauga bikšu bbox proporcijas (platums ~60%) attiecas uz biksēm; krekls ar
  izplestām piedurknēm dabiski aizņem platāku kadru. Tiek ievērots parauga
  fons/audekls/centrējums/ēna, nevis cita apģērba gabala silueta proporcijas.

## Jauna aktīva grupa — Vans Authentic Chino bikses (2026-10-21)
- Pēc pirmās augšupielādes lietotājs izvēlējās `Nē, vēl pievienošu`; darbs
  netika sākts. Pēc otrās augšupielādes lietotājs ar pogu izvēlējās
  `Jā, šīs ir visas — sāc darbu`.
- Pilns apstiprinātais komplekts (6 bildes pirms apstrādes 60,30 MB,
  katra 3072×4096, izņemot `IMG_20261020_201332.jpg` 3071×4096):
  - `MVIMG_20261020_161746.jpg` — pilnais kadrs no aizmugures.
  - `MVIMG_20261020_161944.jpg` — tuvplāns: priekšējā jostasvieta un
    labā kabata.
  - `MVIMG_20261020_161959.jpg` — tuvplāns: atvērta jostasvieta/rāvējslēdzējs.
  - `MVIMG_20261020_162013.jpg` — tuvplāns: iekšējā jostasvieta un birkas.
  - `MVIMG_20261020_162101.jpg` — tuvplāns: kopšanas birka rokā; roka un
    fons nav apģērbs.
  - `IMG_20261020_201332.jpg` — pilnais kadrs no priekšas; kadra stūros
    ķivere un kāja jāpaliek ārpus apģērba maskas.
- Stratēģija: pilniem kadriem vispirms pilots ar
  `birefnet-general-lite`; ja tas neiziet vārtus, nākamais mēģinājums ir
  pārbaudītais `isnet-general-use`. Tuvplāniem izmanto vizuāli kartētas
  sēklas + GrabCut 960 px; malas apstrādā ar 7. iterācijas alfa.
- [x] Pilnie kadri pabeigti ar BiRefNet-General-Lite optimizēto ONNX ceļu
      (768×1024 host attēls, īslaicīgs 6 GB swap, pēc izpildes izslēgts).
      Zoom audits atrada un atsevišķi izlaboja vecā papīra/ēnas sloksnes pie
      iekšmalām: IMG_201332 noņemti 12 608 silti pikseļi gar iekšējo vīli;
      161746 starpkājē noņemta mērīta daudzstūra zona un nelieli ēnas
      atlikumi. Gala segumi: IMG 0.3553, 161746 0.4321.
- [x] Tuvplāni ar kartētām sēklām/GrabCut: 161944 5. mēģinājums,
      161959 3. mēģinājums, 162013 1. mēģinājums, 162101 5. mēģinājums.
      162101 papildus precīzi noņemta roka garās birkas galā, saglabājot
      birkas tekstu un fiziskās malas. Segumi: 0.5436 / 0.7339 / 0.6197 /
      0.6023.
- [x] Trīs tuvplāniem pievienoti deterministiski PARAUGS 4:5 kadrēšanas logi,
      lai apģērbs sasniegtu vismaz trīs ārējās malas un vienlaikus
      saglabātu birkas/pogas: 161944 `(0, 0.2325, 0.8175, 0.9989)`,
      162013 `(0, 0.0800, 0.9800, 0.99875)`,
      162101 `(0, 0.0200, 0.8500, 0.816875)`. MASTER joprojām ir pilnā
      1:1 avota kadrā.
- [x] Checker gala pārbaude: visas 6 bildes A–D/F/H **PASS**; A vārtiem
      `maxdiff=0`. Veikts E/G vizuālais audits ar piezūmētām kritiskajām
      malām. Kolāža:
      `output/Vans_Authentic_Chino_20261020_KOLAZA.jpg`.
- STĀVOKLIS: GAIDA LIETOTĀJA APSTIPRINĀJUMU kolāžai. `.zip` veidot tikai
  pēc pogas `Apstiprināt`; noraidījuma gadījumā turpināt iterāciju.
- [x] Lietotājs ar pogu `Apstiprināt` apstiprināja kolāžu. Izveidots
      `output/Vans_Authentic_Chino_20261020_GALA_BILDES.zip`
      (8 054 065 baiti; SHA-256
      `291f4cf10668a28e3b633652e9fadb185fbaf9f1072355f7847402a3352dcb29`)
      ar visām 6 apstiprinātajām `PARAUGS_2000x2500` JPG bildēm.
      Arhīva CRC un katra faila baitu identitāte ar avota JPG pārbaudīta.
      Lai nepārsniegtu krātuves limitu, pēc pārbaudes dzēsti vaļējie JPG
      dublikāti `output/paraugs/`; to vienīgās gala kopijas tagad ir ZIP.
- STĀVOKLIS: GAIDA LEJUPIELĀDES/DZĒŠANAS pogas lēmumu.
- [x] Lietotājs ar pogu izvēlējās `Lejupielādēju — dzēst grupu`.
      Dzēsti 32 Vans grupas faili (6 avoti, 6 MASTER, 18 maskas/ALPHA,
      kolāža un ZIP), kopā 128 205 561 baiti. Vaļējie PARAUGS JPG
      dublikāti jau bija dzēsti pēc ZIP baitu pārbaudes. Pārbaudīts, ka
      grupas attēlu failu vairs nav; saglabāts kods, dokumentācija, JSON
      atskaites un parauga atsauces. Pēc tīrīšanas `/home/user` ir
      3 143 324 baiti (3,00 MiB).
- STĀVOKLIS: Vans komplekts ir piegādāts un slēgts; darba telpa ir gatava
  vienai jaunai bilžu grupai.

## Workflow v2 pilots — Henley testa grupa (2026-10-21)
- Lietotājs augšupielādēja 5 bildes un ar pogu apstiprināja
  `Jā, šīs ir visas — sāc darbu`. Komplekts pirms apstrādes: 41,97 MiB,
  visas 3072×4096:
  `MVIMG_20261020_160538.jpg`, `MVIMG_20261020_160550.jpg`,
  `MVIMG_20261020_160601.jpg`, `MVIMG_20261020_160608.jpg`,
  `MVIMG_20261020_160645.jpg`.
- Pilota mērķis: AI izmanto tikai apģērba maskai/fona nošķiršanai; apģērba
  ģeometrija, krokas, birkas un tekstūra netiek ģenerēti vai pārzīmēti.
  Atļauta viena globāla, deterministiska Lightroom tipa krāsu/kontrasta
  korekcija visam komplektam. Fons, ēna un 2000×2500 kompozīcija paliek
  deterministiska. Mērķa ātrums: **20 s ± 1 bilde**, ko mēra un ziņo
  atsevišķi maskai un kopējai apstrādei.
- [x] Modeļu salīdzināšana šajā sandboxā: `u2netp` 0,23–0,28 s, bet
      izlaida piedurknes; `silueta` 0,81–0,92 s, bet izlaida vienu
      piedurkni; abi tuvplānos izvēlējās tikai fragmentu. ISNet pilnajam
      kadram deva pilnu siluetu 1,45 s predikcijā, bet tuvplānos izvēlējās
      birku/apkakli (segumi 0,0135–0,2449). SegFormer ADE un
      clothes-seg arī nedeva pilnu auduma masku tuvplānos; smagie
      BEN2/SAM/cloth-seg ceļi beidzās ar OOM vai neatbilst ātrumam.
- [x] Izveidots `workflow_v2.py`: katrai bildei ISNet atsevišķā procesā,
      automātiska AI maskas QA un noraidītajiem tuvplāniem GrabCut
      fallback no sēklu bibliotēkas 768 px mērogā. Pilnajam kadram metode
      ir `isnet`; četriem tuvplāniem atskaitē atklāti atzīmēts
      `grabcut_seed_library_fallback`.
- [x] Krāsu profils visam komplektam: fona mediāna RGB
      `(154, 149, 138)`, WB pastiprinājumi `(0.956044, 1.0, 1.109544)`,
      ekspozīcija `1.06`, gaišo toņu rolloff no `0.86` un S-līknes
      kontrasts `0.18`. Pēc rolloff ieviešanas nogriezto kodola pikseļu
      īpatsvars ir tikai 0–0,136%.
- [x] Ātruma optimizācija: MASTER/masku PNG raksta ar 3. līmeni un bez
      PIL `optimize`; augstfrekvences auduma PNG optimizācija vien varēja
      maksāt ~12 s. Gala komponentu laiki: kopā **7,80–13,33 s/bilde**,
      vidēji **10,49 s/bilde**. Checker v2: visas 5 bildes **PASS**
      (A2 maxdiff=0 pret deterministiski koriģēto oriģinālu, B/C/D/F/H/T).
      Kolāža: `output/Uniqlo_Henley_20261020_V2_KOLAZA.jpg`.
- [x] Lietotājs ar pogu `Apstiprināt` apstiprināja v2 kolāžu. Izveidots
      `output/Uniqlo_Henley_20261020_V2_GALA_BILDES.zip`
      (7 843 480 baiti; SHA-256
      `2fbcf28f911e95996bcb8dd81fd1496d80a86a6c6e5305bad8426f682d4a7216`)
      ar visām 5 apstiprinātajām `PARAUGS_2000x2500` JPG bildēm. Arhīva
      CRC un katra faila baitu identitāte ar vaļējo JPG pārbaudīta.
- STĀVOKLIS: GAIDA LEJUPIELĀDES/DZĒŠANAS pogas lēmumu.
- [x] Lietotājs ar pogu izvēlējās `Lejupielādēju — dzēst grupu`. Dzēsti
      32 Henley v2 grupas faili (5 avoti, 5 MASTER, 5 PARAUGS,
      15 maskas/ALPHA, kolāža un ZIP), kopā 125 645 021 baiti.
      Pārbaudīts, ka grupas attēlu failu vairs nav; saglabāts kods,
      dokumentācija, grade profils, JSON atskaites un parauga atsauces.
      Pēc tīrīšanas `/home/user` ir 3 240 146 baiti (3,09 MiB).
- STĀVOKLIS: Workflow v2 pilots ir piegādāts un slēgts; darba telpa ir
  gatava vienai jaunai bilžu grupai.

## Workflow v2.1 cietināšana (2026-10-21)
- Lietotāja lēmums: pagaidām paliekam pie pašreizējā lokālā v2 loop
  modeļa; GPU/mākoņa maskas pilots atlikts, neviena ārēja servisa
  konta vai API atslēga nav izveidota.
- Konstatēts, ka pēc sandbox atiestatīšanas `/var/tmp/pylibs` un
  `/var/tmp/rembg_home` bija pazuduši. Pievienots `setup_v2.py`, kas
  reproducējami atjauno piespraustās versijas (rembg 2.0.85,
  onnxruntime 1.31.0, NumPy 2.3.5, SciPy 1.17.1, Pillow 12.3.0) un
  ISNet modeli (178 648 008 baiti) ārpus darba telpas. Pēc atjaunošanas
  `setup_v2.py --check` un workflow `--preflight` ir `ready: true`.
- [x] `workflow_v2.py` atjaunināts uz v2.1: malu attiecību saglabājošs
      ISNet proxy, EXIF orientācijas vienādošana, precīzs `--files`
      saraksts, atomiska inkrementāla atskaite, `--resume` tikai ar
      sakrītošu avota SHA-256, per-image kļūdu izolēšana, standarta
      kolāža un checker-gated `--make-zip` režīms.
- [x] Jaunam tuvplānam bez sēklu bibliotēkas ieraksta pievienots
      automātisks sēklu priekšlikums (`output/audits/*_SEED_PROPOSAL.jpg`)
      un eksperimentāls auto-GrabCut ar atsevišķu QA. Noraidīta bilde
      iegūst `needs_seed_review`; pārbaudītā bibliotēka paliek prioritāra.
- [x] Krāsu LUT pievienota paraugu clipping aplēse un automātiskas
      ekspozīcijas drošības samazināšanas cilpa pirms renderēšanas.
- [x] `checker_v2.py` tagad nepārtrauc darbu pie vienas bojātas bildes,
      nepabeigtos ierakstus uzskaita `_meta` sadaļā, raksta atskaiti
      atomiski un Gate H pievieno informatīvas malas metrikas. Esošie
      A2/B/C/D/F/H/T sliekšņi nav mīkstināti.
- [x] Testi: `test_workflow_v2.py` **7/7 PASS**. ISNet dūmu tests uz
      parauga atsauces deva 768×960 proxy (bez 768×1024 izstiepšanas),
      `predict_s=3.052`, segumu 0,3343 un QA PASS. Sintētiskā tuvplāna
      auto-sēklu + GrabCut integrācijas testā IoU bija 0,990; reālos
      jaunus tuvplānus joprojām jānovērtē ar zoom auditu, pirms auto
      režīmu uzskata par pārbaudītu.
- Atjaunināta dokumentācija: `WORKFLOW_V2.md`, `LOOP_KOMANDAS.md` un
  `LOOP.md` tagad skaidri norāda v2.1 kā pašreizējo ražošanas dzinēju.
- Aktīvas produktu bilžu grupas nav; šis posms neizveidoja nevienu
  produktu MASTER/PARAUGS/ZIP failu.
- STĀVOKLIS: Workflow v2.1 ir gatavs nākamajai vienai bilžu grupai pēc
  obligātā starta pogu protokola.

## Pastāvīgais orientācijas noteikums (2026-10-21)
- Lietotājs demonstrēja piemēru `MVIMG_20261020_161031.jpg` (4096×3072,
  10 365 849 baiti): pelēki džinsi kadrā guļ šķērsām — jostasvieta pie
  labās malas, staras horizontāli pa kreisi. Norāde: **nākotnē šādas
  bildes pirms apstrādes pagriezt vertikāli**. Bilde bija tikai
  izskaidrošanai: tā netika apstrādāta, netika sākta jauna grupa un pēc
  lietotāja lūguma fails tika izdzēsts no krātuves.
- Noteikuma izpilde: atļauts tikai visa kadra bezzaudējumu pagrieziens
  par 90° soļiem tā, lai apģērba dabiskā augša (apkakle/jostasvieta,
  birkas teksts) būtu uz augšu. Iepriekšminētajā piemērā tie ir 90°
  pret pulksteņrādītāja virzienu (`270` CW): jostasvieta augšā, staras
  uz leju. Brīva leņķa iztaisnošana/deformēšana joprojām aizliegta;
  pikseļu vērtības nemainās (tikai pārkārtojas) — mainās tikai
  komplekta LUT kā līdz šim.
- [x] Ieviests kodā: `workflow_v2.py --rotate STEM:90|180|270`
      (arī `:cw`/`:ccw`); pagrieziens tiek piemērots visos posmos
      (arī ISNet worker), fiksēts maker atskaitē kā `rotation_cw`,
      pārmantots ar `--resume`/`--rerender-saved`; maska ar citu
      pagriezienu atkārtoti netiek izmantota. `checker_v2.py`
      salīdzina oriģinālu tajā pašā orientācijā. Pievienots vienību
      tests (pagriešana 270° CW un atpakaļ baitu līmenī identiska);
      kopā `test_workflow_v2.py` **8/8 PASS**.
- Noteikums ierakstīts arī `WORKFLOW_V2.md` (sarkanās līnijas +
  atsevišķa sadaļa) un `LOOP_KOMANDAS.md`.
- STĀVOKLIS: aktīvas grupas joprojām nav; gatavs nākamajai vienai
  grupai pēc starta pogu protokola. Orientāciju katrai bildei
  novērtēt inventarizācijā un pagriezienus fiksēt grupas ierakstā.

## BRIA RMBG-1.4 vienas bildes pilots (2026-10-21)
- Lietotājs pēc dverso lapas analīzes apstiprināja izolētu testu ar
  vienu attēlu: `MVIMG_20261020_161146.jpg`, 3072×4096,
  14 563 477 baiti, SHA-256
  `50f58532febffe031b12e312f799f7751ecb36fb01c24a717e73535084959e8a` (skat.
  testa JSON). Šī nav jauna produktu grupa un nav sākts ražošanas loop.
- Vidu atjaunoja ar `setup_v2.py`. BRIA modelis lejupielādēts tikai uz
  `/var/tmp/bria_test/model_quantized.onnx`: 44 403 226 baiti,
  SHA-256 `a6648479275dfd0ede0f3a8abc20aa5c437b394681b05e5af6d268250aaf40f3`.
  Bilde netika sūtīta ārējam servisam; abi modeļi palaisti lokāli.
- BRIA noklusējuma (kvadrātā izstiepta 1024×1024) rezultāts:
  segums 0,7637, viena komponente 1,000, closeup QA PASS;
  inference 2,646 s, kopā skriptā 3,354 s, max RSS 955 268 KB.
  Garantētās auduma zonas (apakšējā kreisā daļa un abas kabatas)
  visas bija 100% virs sliekšņa 128.
- ISNet salīdzinājums uz tās pašas bildes: segums 0,1643, lielākā
  komponente 0,7127; modelis izvēlējās galvenokārt kabatas, šuves un
  birku, bet apakšējo audumu gandrīz pilnībā izlaida. Worker wall
  6,341 s (predict 3,076 s), child max RSS 1 171 420 KB.
- Binarizēto masku IoU ir tikai 0,2148; BRIA-only daļa ir 0,5997 no
  kadra, ISNet-only 0,0002. Secinājums: BRIA šajā grūtajā auduma
  tuvplānā atrisina galveno semantisko problēmu, ko ISNet neatrisina.
- [ ] Būtisks defekts: redzamais papīra/ēnas ķīlis starp bikšu krokām
      (92 596 px pārbaudes daudzstūris) BRIA maskā ir 100% virs 128
      sliekšņa ar mean alpha 0,9957 — tas tiktu saglabāts kā apģērbs.
      Tāpēc BRIA masku pagaidām nedrīkst bez papildu QA/korekcijas
      likt ražošanā. Malu attiecību saglabājošs letterbox variants
      defektu neizlaboja (wedge mean alpha 0,9959; segums pat 0,867).
- Testa materiāli tika sagatavoti `output/bria_test/`
  (`BRIA_RMBG14_161146_SALIDZINAJUMS.jpg`,
  `BRIA_RMBG14_161146_ZOOM.jpg`,
  `BRIA_RMBG14_161146_REZULTATI.json`) un parādīti lietotājam.
  Ražošanas kods nav mainīts; pirms iespējamas integrācijas
  nepieciešama papildu caurumu/fona savienojamības QA, korekcijas
  stratēģija un BRIA licences pārbaude.
- [x] Lietotājs ar pogu izvēlējās `Dzēst testu`. Izdzēsti 4 darba
      telpas faili (avots + 2 audita JPG + rezultātu JSON), kopā
      17 607 208 baiti; notīrīti arī `/var/tmp/bria_test` pagaidu
      artefakti. Pēc tīrīšanas `/home/user` ir 3 271 497 baiti.
      Saglabāts tikai šis teksta rezultāts un darba kods/dokumentācija.
- STĀVOKLIS: BRIA pilots ir slēgts; aktīvas produktu grupas nav.

## Pārlūka BG rīku izpēte (2026-10-21)
- Pēc lietotāja ierosinājuma veikts ierobežots interneta pētījums par
  dverso līdzīgām klienta puses fona noņemšanas lapām un atvērtā koda
  projektiem. Neviena produktu bilde netika augšupielādēta; ražošanas
  kods nav mainīts.
- Pilns kopsavilkums un avotu saraksts: `PETIJUMS_BROWSER_BG.md`.
- Galvenais secinājums: lielākā daļa šādu lapu izmanto vienu no trim
  ceļiem — ISNet, BRIA RMBG-1.4 vai BiRefNet-lite. BRIA ir stiprākā
  mūsu pārbaudītajā tuvplānā, bet tās nekomerciālā licence ir šķērslis
  ražošanai; nākamais loģiskais vienas bildes kandidāts ir optimizēts
  MIT licences BiRefNet-lite ONNX eksports.
- Pārņemamas idejas: modeļu salīdzinājuma laboratorija vienai bildei,
  border flood-fill/paper-leak QA, SlimSAM tipa punktu korekcija,
  guided filter tikai malas joslā, blur-fusion krāsu dekontaminācija,
  īstas ēnas clean-plate ekstrakcija un BG0 tipa modeļu reģistrs ar
  timeout/fallback kāpnēm.
- STĀVOKLIS: tikai izpēte pabeigta; jauna modeļa tests vēl nav sākts
  un aktīvas produktu grupas nav.

## BiRefNet-lite dzīvotspējas posms (2026-10-21)
- Lietotājs apstiprināja sākt ar izpētes ieteikumiem. Darba telpā nav
  mājas testa bildes (tikai parauga atsauces un ekrānuzņēmums), tāpēc
  vispirms veikts tikai modeļu CPU/RAM dzīvotspējas tests.
- [ ] Evan native-DeformConv BiRefNet 1024 (91 708 456 baiti):
      sesija izveidojās, bet inference tika nogalināta ar exit 137
      arī ar zema RAM ORT iestatījumiem. Šai 1,9 GB videi neder.
- [ ] `studioludens/birefnet-lite-512` FP16 (98 484 532 baiti): arī
      OOM inference laikā; GatherND ceļš nav piemērots.
- [x] BG0 optimizētais `int8-full-512.ort` (55 563 408 baiti,
      SHA-256 `6fa08dc7df0417597454e52e2b721b2c190b13545a46a6bd3a8bac1ebf0709dc`)
      izturēja vārtus: sesija 0,881 s, inference 3,754 s, max RSS
      740 336 KB. Uz parauga atsauces segums 0,3335 un vizuāli pilns
      siluets; tas pierāda tikai izpildāmību, ne mājas tuvplāna kvalitāti.
- Testa artefakti: `output/birefnet_test/BG0_BIREFNET512_SMOKE.jpg`
  un `.json`. BG0 modelis atrodas tikai `/var/tmp/birefnet_test/`.
- NĀKAMAIS SOLIS: vajadzīga viena grūta mājas tuvplāna bilde īstajam
  BG0 BiRefNet-lite pret BRIA/ISNet salīdzinājumam; vislabāk tā pati
  iepriekšējā `MVIMG_20261020_161146.jpg`, jo tai jau ir BRIA/ISNet
  mērījumi. Ražošanas kods joprojām nav mainīts.

## BG0 BiRefNet-lite reālais vienas bildes tests (2026-10-22)
- Lietotājs atkārtoti augšupielādēja tieši to pašu
  `MVIMG_20261020_161146.jpg`; SHA-256 sakrīt ar iepriekšējo BRIA
  pilotu. Šis joprojām ir izolēts tests, nevis jauna produktu grupa.
- [ ] BG0 dzimtajā 512×512 kvadrāta ievadē pilnībā izgāzās: visi
      logits bija negatīvi (maks. -9,75), segums 0,0000. Aspect
      letterbox ar pelēkām joslām deva tikai 0,2412.
- [x] Diagnostika atrada konteksta triku: samazinot oriģinālu līdz
      80% un novietojot to 512×512 kanvā ar no fona nomērītu papīra
      krāsu `RGB(206,202,190)`, BG0 deva segumu 0,7455, vienu
      komponenti un closeup QA PASS. IoU pret BRIA 0,9750; 65%
      variants deva 0,7473 un IoU 0,9770.
- BG0 pad80 garantētās auduma zonas visas ir 100%; fona ķīlī kļūdaini
  iekļauti 37,29% pikseļu pret BRIA 100%. Tātad BG0 ar kontekstu ir
  semantiskiski līdzvērtīgs BRIA un šajā konkrētajā defektā labāks,
  bet ķīlis vēl nav pilnībā tīrs.
- Laiki/RAM: BG0 pad variants inference 2,724 s tajā pašā sesijā;
  atsevišķs BG0 process 3,248 s un 839 244 KB. BRIA 2,310 s /
  924 900 KB; ISNet predict 2,637 s / 1 166 760 KB child RSS.
- [ ] Guided-filter A/B noraidīts: pārejas mediāna pasliktinājās no
      9 px līdz 14–29 px (1536×2048 mērogā), nenoteiktā alfa pieauga
      no 1,68% līdz 2,21–3,18%. Pašreizējo malas apstrādi ar to
      neaizstāt bez jauna, labāk pamatota varianta.
- Testa materiāli: `output/birefnet_test/`
  (`BG0_BIREFNET_161146_SALIDZINAJUMS.jpg`, `_ZOOM.jpg`,
  `_GUIDED_ZOOM.jpg`, `_REZULTATI.json`).
- STĀVOKLIS: BG0 + 80% papīra konteksta apmale ir daudzsološs
  eksperimentāls tuvplānu fallback kandidāts ar MIT modeli, bet vēl
  nav integrēts ražošanā. Pirms integrācijas jāvalidē uz citiem
  audumiem un jāizveido paper-leak QA/korekcija. Lietotājs ar pogu
  izvēlējās testa bildi un audita failus pagaidām paturēt.

## 2026-10-22 — Papīra noplūdes QA + korekcija + regresija (3. solis)

Pilna atskaite: `PAPIRA_NOPLUDES_QA.md`. Kods: `lab/`.

- [x] `lab/lab_common.py` — modeļu lejupielāde ar SHA-256 pin, `pad_with`
      (audekls = garā mala / pct; agrākā īsās malas definīcija deva
      negatīvu nobīdi uz 4:5 foto), `alpha_stats`, `open_rgb` ar rotāciju.
- [x] `lab/lab_bg0.py` — BG0 BiRefNet-lite 512 (int8, 55 563 408 B,
      SHA `6fa08dc7…`) palaišana; ImageNet normalizācija, sigmoida
      ārpus modeļa, 1 pavediens, izslēgti arenas/mem-pattern.
- [x] `lab/lab_leak.py` — fona krāsas mērītājs (divi gaišuma režīmi,
      uzvar gludākais), trīskanālu detektors (dC + tekstūra + L_min ar
      kvantiļu sliekšņiem) un deterministiskā ģeodēziskā korekcija.
- [x] ΔE/Youden sliekšņu metode **noraidīta**: 1 RGB vienības izmaiņa
      pārlēca slieksni 14.63 → 7.39. Aizstāta ar kvantilēm.
- [x] Injekcijas tests `lab/test_leak_injection.py`: 204 800 px papīra →
      zonde DUBIOUS (99.99 % atrasts) → korekcija izņēma 99.99 % injekcijas,
      **0 px ārpus**, 0 pievienotu → zonde PASS 0.0 %.
- [x] 161146 (BG0, pad 80 %): segums 0.7472, infer 2.2 s, zonde PASS 0
      noplūdes, garment_fpr 0.18 %, ticamība "marginal".
- [x] Paraugi, BG0 pret ISNet: IoU 0.9924 / 0.9836 / 0.9898 / 0.4340;
      uz parauga 4 BG0 0.9298 pret ISNet+GrabCut 0.4035, un zonde ISNet
      maskai atzīmē 9.606 % papīra — godīgs patiesi pozitīvs.
- [x] **Viltus pozitīvu atklājums**: vaļīgā ΔE zonde uz 161146 deva
      7 "noplūdes" (63 790 px); acu pārbaude parādīja, ka visas 7 ir
      apģērba detaļas — gaišāki džinsa laukumi un baltā cauruļu bante.
      Stingrā zonde atgriež 0.
- [x] Pilnas darbplūsmas regresija uz 4 paraugiem: 4/4 izgatavotas,
      vid. 8.61 s/bilde, čekeris 2/4 PASS. Neiztur paraugi 3 un 4 —
      full-bleed tuvplāni, kur ISNet atrod fragmentu un auto-seed
      GrabCut norij kadru; gala vārti D/F to pareizi noraida.
      Nav orientācijas regresija (`rotation_cw = 0` visiem).
- [ ] NAV integrēts ražošanā. Vārti paliek A2, B, C, D, F, H, T.
      Zonde maksā 5.4–6.4 s uz 12.6 MP — pirms iekļaušanas jārēķina
      samazinātā mērogā.

## 2026-10-22 (turpinājums) — lietotāja lēmumi izpildīti daļēji

- [x] **GATE_L_paper_leak** pievienots `checker_v2.py` kā **brīdinājums**:
      `pass=None`, `advisory=True`, `ALL_PASS` to ignorē, kļūda → `skipped`.
      Zonde rēķinās uz ≤3000 px, maksā 1.8–2.1 s. Pārbaudīts uz 4 paraugiem:
      PASS 0.000 / 0.000 / 0.375 %, DUBIOUS 9.606 % (paraugs 4, pareizi).
      Vienību testi 8/8.
- [x] `paper_background_mask()` — modelim nepiederoša fona segmentācija no
      izmērītā papīra. Segums pret atsauci: 161146 +0.025, paraugi 1–2
      +0.033/+0.025, paraugs 3 +0.078, paraugs 4 **+0.004**.
- [!] **Tuvplānu auto-sēklas labošana pārtraukta**: `closeup_mask()` atkārtota
      izsaukšana ar saglabāto `cfg` atgriež tukšu masku, lai gan darbplūsmā tā
      deva 0.8278/0.4035. Sāniedarbība nav izskaidrota → ražošanas kods
      netiek mainīts. Nākamais solis: padot `paper_background_mask()` kā
      raster `sure_bg` tieši GrabCut, ar atsevišķu parametru un testu.
- [ ] Gaida lietotāja bildes: 3–5 dažādi foni un vismaz 2 balti apģērbi ar
      baltām etiķetēm, lai pabeigtu noplūdes validāciju.

## 2026-10-22 (turpinājums 2) — 3 jauni testa attēli, BG0 spriedums

- [x] Lietotājs apstiprināja: 3 bildes ir viss komplekts, laist pilnu salīdzinājumu.
- [x] `paper_leak.measure_paper_colour` ieguva `plausible` karogu (papīrs ir
      gluds; ja gludākais režīms ir teksturēts, kadrā nav papīra). Uz 122248
      (koka grīda) tas pareizi atgriež `no paper-like backdrop`.
- [x] `lab/run_compare3.py`: ISNet atsevišķos procesos, tad BG0 + papīra-fons +
      GATE_L. Pirmā versija nomira ar exit 137 (vecāks turēja BG0 sesiju un
      pilnas izšķirtspējas mozaīkas) — pārrakstīta divās fāzēs.
- [x] Rezultāti: BG0 → 0.9990 / izlaists / 0.0000. **BG0 neiztur
      generalizāciju**; ieteikums to slēgt. Papīra-fons → 0.6480 / 0.9737 /
      0.6135. Uz spīdīgās jakas papīra-fons izgriež caurumus spoguļatspīdumos.
- [x] GATE_L uz jaunajiem: 160550 ISNet → DUBIOUS 5.545 % (maska ir fragments),
      161944 → PASS 0.000 %.
- [x] Salīdzinājuma lapa `output/birefnet_test/COMPARE3.jpg` un `COMPARE3.json`.
- [ ] Atlikts: spīduma un ēnas labojumi papīra-fona prototipā, tad atkārtot
      šo pašu testu. 122248 (koka grīda) paliek ārpus papīra režīma.

## 2026-10-22 (turpinājums 3) — BG0 arhivēts, defekti parādīti

- [x] Lietotāja lēmums: **BG0 arhivēt bez turpmākas izmantošanas**. Statuss
      ierakstīts `PETIJUMS_BROWSER_BG.md` sākumā un `PAPIRA_NOPLUDES_QA.md`
      9.2. sadaļā. `lab/lab_bg0.py` paliek tikai kā vēsturisks pieraksts.
- [x] Defektu tuvplāni: `output/birefnet_test/DEFECTS.jpg` + `DEFECTS.json`.
      Trīs atklājumi: (1) ēnas pārejas josla pie pleca malas tiek uzskatīta
      par papīru; (2) uz jakas fona krāsa tiek izmērīta no pašas jakas un
      `paper_background_mask()` joprojām izpildās, lai gan `plausible=False`;
      (3) robeža ir raiba un ēna zem apģērba paliek priekšplānā.
- [x] Trīs konkrēti labojumi formulēti (`PAPIRA_NOPLUDES_QA.md` 10.2).
- [ ] Nav ieviesti — gaida lietotāja apstiprinājumu.

## 2026-10-22 (turpinājums 4) — 3 labojumi, 8 attēlu retests

- [x] Labojums 1 (aizsargs `plausible`): 122248 tagad **REFUSED**, nevis
      0.9737. Strādā pilnībā.
- [x] Labojums 2 (sasniedzamība no malas caur mazu gradientu + `L_floor` no
      papīra kodola, ne astes): 160550 pleca defekts novērsts, bet segums
      0.648 → 0.700 (ēna tagad paliek priekšplānā).
- [!] Labojums 3 (ēna): `shadow 0.0 %` visos 8 — modelis pārāk šaurs.
- [!] Kopumā segums pasliktinājās uz 160550, 161146, 161944; uz studijas
      paraugiem 1–4 bez izmaiņām.
- [x] Secinājums: abi labojumi **pārbīda kļūdu** (apēda apģērbu → patur ēnu).
      Cēlonis fundamentāls: ēnots papīrs un apgaismots audums var būt vienā
      gaišumā. Vajadzīgs ēnu modelis, nevis slieksnis.
- [ ] Prototips NAV gatavs ražošanai. `workflow_v2.py` nav mainīts.

## 2026-10-22 (turpinājums 5) — ēnu modelis, mērogs, papīra-fona slēgšana

- [x] Ēnas modelis pārrakstīts uz **apgaismojuma attiecību** pret tuvāko papīra
      pikseli (josla 0.50–0.98), nevis absolūto gaišumu.
- [x] `paper_background_mask(work_scale=N)` — lēmums rupjā mērogā, atpakaļ
      uz augšu ar bilineāru + vienu closing. Fragmentācija 2891 → 1 komponente.
- [x] Gradienta vārti: blurē L* pirms diferencēšanas.
- [!] Ēnas modelis dod `shadow 0.0 %` — instrumentēts soli pa solim: ķēde
      strādā, bet atrod maz, jo ēna jau ir fona maskā, bet 161944 "ēna" ir
      papīra krokas.
- [x] **Vizuāls gala tests** (`output/birefnet_test/PAPERBG_VERDICT.jpg`):
      160550 → papīrs ķērpjains; 161944 → papīra krokas tiek uzskatītas par
      audumu (segums 0.656 pret patiesību ~0.30).
- [x] **Lēmums: papīra-fona prototips slēgts** tāpat kā BG0. Trīs labojumu
      kārtas mainīja kļūdas formu, nevis to novērsa.
- [x] Regresijas pārbaude: noplūdes zonde un GATE_L nav bojātas — injekcijas
      tests atkārtots pēc visām izmaiņām: 204 800 px → DUBIOUS, izņemti
      99.99 % iekšienē, **0 px ārpus**, pēc tam PASS.
- [x] `paper_leak.py` ieguva statusa galveni: `leak_probe`/`correct_leaks`
      VALIDATED, `paper_background_mask` CLOSED.
- [x] Infrastruktūra: `/var/tmp` tiek tīrīts arī darba laikā (ne tikai starp
      gājieniem) → lielie faili jālasa no `/home/user/uploads`, un katrs
      attēls jāapstrādā atsevišķā procesā. `setup_v2.py` pārinstalēja vidi;
      BG0 SHA pārbaudīts (`6fa08dc7…`).

## 2026-10-22 (turpinājums 6) — 1. prioritāte pabeigta, 3. atbildēta

- [x] `closeup_mask_qa(binary, orig)` tagad paredz GATE_D/F: nepārklāts
      audums + malu kritērijs (>=3 malas). Slieksnis 0.05 atvasināts no
      datiem (labās maskas 0.0072–0.0200, bojātā 0.5120 → 25x atstarpe).
- [x] Tekstūras reference ņemta tikai no papīrveidīgiem rāmja pikseļiem —
      citādi apģērbs, kas pieskaras malai, piesārņo slieksni (to atrada tests).
- [x] Vienību testi **9/9**; jauns `test_closeup_qa_predicts_external_gates`.
- [x] Darbplūsma: maker 2/4 pabeigta, čekeris **2/2 PASS**, 2 atzīmētas
      `needs_seed_review` ar priekšlikumiem; `_meta.ignored_incomplete` tās
      uzskaita. **Neviena klusi bojāta bilde vairs netiek izdota.**
- [x] Atklāts īstais cēlonis: paraugs 3 maska ir **laba** (0.0200), problēma ir
      **kompozīcija** (2 malas). Paraugs 4 maska ir **bojāta** (0.5120).
      Tāpēc 2. prioritāte jāsadala: kompozīcija (3.) un sēkla (4.).
- [x] 3. prioritāte atbildēta: GrabCut deterministisks (3/3 = 0.8278). Agrākais
      0.0000 = bojāts faila nolasījums. Jauns atradums: GrabCut karājas uz
      deģenerētiem vienkrāsainiem ievadiem (>15 min, 100 % CPU).

## 2026-10-22 (turpinājums 7) — koriģēti skaitļi, divas manas kļūdas

- [x] Atklāta un labota kļūda: `closeup_mask` atgriež 0/1, nevis 0/255, tāpēc
      `binary > 128` bija nepatiess visur (no tā "0/4 malas", "0.91").
- [x] Malu noteikums piemērojams tikai tuvplāniem (`coverage >= 0.60`).
- [x] Otrs reāls labojums: `auto_closeup_seed_config` pievienots
      `L* >= 0.60 x L*_papīra`, lai tumšs audums, kas pieskaras malai, nekļūtu
      par "drošo fonu". Paraugs 4: **0.4035 → 0.8736**.
- [x] Gala stāvoklis: maker 2/4, čekeris **2/2 PASS**, 0 klusi bojātu bilžu,
      2 `needs_seed_review` ar konkrētu iemeslu, testi **9/9**.
- [ ] 2. prioritāte: paraugam 3 vajag kompozīcijas lēmumu (maska laba),
      paraugam 4 — sēklas labojumu apakšā pie ēnas.

## 2026-10-22 (turpinājums 8) — AI piesaistes punkts un apmales tests

- [x] Inventarizēts: AI = **viens** ISNet izsaukums 768x1024, tikai varbūtību
      lauks. Viss pārējais deterministisks.
- [x] Apmales tests (6 attēli x 3 režīmi): apmale izlabo abus pilnbleed
      tuvplānus ar tumšu audumu — 0.0859 → 0.8256 un 0.0277 → 0.9291
      (kļūda +0.001 pret atsauci).
- [x] Bet apmale sabojā gaišu audumu uz gaiša papīra (160550 → 0.8075 pret
      patiesību 0.62; pie pad 0.65 → 0.9996).
- [x] Noteikums: apmale tikai kā **retry**, ja pirmais gājiens < 0.25 segums.
      4/6 pareizi; abi pārējie ir gaiša-auduma gadījumi.
- [x] Mana testa kļūda: proxy izmēra maska tika apgriezta pilna izmēra
      koordinātēs. Tests, kas noliedz zināmu labu gadījumu, ir bojāts tests.

## 2026-10-22 — apmales retry ražošanā, auto-sēklu ceļš dzēsts
- Retry kā RETRY (ne režīms) strādā: s3 0.8252, s4 0.9291, 161944 0.5449.
- Kompozīcija pārbūvēta: leksikogrāfisks mērķis (4 malas pirms izmēra) + joslu apgriešana.
- Divi gates caurumi aizvērti: `silhouette_fill` ≥ 0.60 (GATE_C + ai QA), GATE_P (papīrs pie kadra malas).
- GATE_D stūri: krāsu slieksnis → maska; viens pikselis → 8×8 laukums.
- `auto_closeup_seed_config` dzēsts. `closeup_mask` paliek tikai 160550 dēļ (atvērts lēmums).
- 6/7 pabeigtas, 6/6 PASS, vidēji 12.75 s/bilde.
- Pad 0.80 -> 0.90; `paper_like` ieguva augšējo robežu (balts audums vairs nav "papīrs").
- Jauns: mala tiek vērtēta JOSLĀ (0.5 % no malas, slieksnis 0.85), nevis vienā rindā.
- GATE_D stūru klauzula izņemta (nespēja atšķirt ēnu/mīksto alfu/papīru).
- 8 bilžu regress: 6 PASS, 1 GATE_P (122248), 1 refused (161146). Vidēji 12.18 s/bilde.
- 160550 "papīra josla" izrādījās MANA kļūda (nepareizs salīdzinājums); godīgs tests: 2.6 % atšķirību, tas ir LUT + ēna. Defekta nav.
- Otra modeļa pārbaude: bria-rmbg 1.02 GB -> OOM; u2net_cloth_seg -> OOM (137). Otrs modelis šajā sandboxā nav izpildāms.
- .rembg (169 MB) un bria_test izdzēsti; darba telpa atpakaļ uz 127 MB.
- Uzbūvēts `loop_engine.py`: bāze -> remēdiju bibliotēka -> gala brauciens -> trace + eskalācijas lapa.
- Maker ieguva `--pad`, `--force-pad-retry`, `--overrides`; remēdija maina masku, nevis kompozīciju.
- Dzinējs pats sev atklāja 2 kļūdas: exit 2 pie godīga atteikuma; atteikts attēls tika skaitīts kā PASS.
- Pirmais brauciens: 6/8 PASS, 2 eskalācijas ar pierādījumiem (287.3 s).
- Jauns komplekts (zila jaka + balts krekls): 2/2 PASS; 121740 10.6 s, 160550 16.6 s.
- Atrasts kluss krāsu defekts: WB no koka grīdas atņēma ~4.6 b* abiem audumiem. Ieviesta fona hromas pārbaude + GATE_K (±2.5).
- Viena bilde (PXL...PORTRAIT.ORIGINAL, guļus 4080x3072): 1/1 PASS, 17.05 s, 4 malas 1.0.
- Salabots: rotācijas atslēga ar vairākiem punktiem; GATE_K avārija pie rotētas bildes; graudaina kartona atbalsts ar `profile_relaxed` ierakstu.
- Testi: 11/11.
- Ātrums 17.05 -> 12.80 s (tajā pašā logā; uz klusas mašīnas ~10 s), vārti nemainījās.
- `isnet_native.py`: ISNet tieši uz onnxruntime, imports 2.4 s -> 0.03 s; maska bitu identiska (`test_isnet_parity.py`).
- Arēna izslēgta: otrā inference vienā procesā vairs nekrit ar SIGKILL (1215 MB -> 611 MB).
- Viens workers abiem piegājieniem; papīra mērījums koplietots; PNG līmenis 1.
- Jauna bilde 124339475 (balts vafeles krekls uz pelēka kartona): dzinējs ATTEICA, 1 eskalācija. ISNet saķer tikai gludās aproces (segums 3.1 %); fons un krekls tekstūras ziņā neatšķirami. Sk. QA §23.
- Salabots: `load_reports()` vairs nekrīt ar FileNotFoundError, ja maker atteicis visu bildi.
- Jauns ceļš `plate_texture` (plate_segment.py): kad ISNet neredz apģērbu, masku dod virsmas tekstūras mērījums. 124339475 -> PASS, 13.64 s.
- Pamats: lokālais L* std pusizmērā — kartons 2.8, vafeles adījums 12.8, Otsu 7.6. Pilnā izšķirtspējā atstarpe pazūd.
- Robeža kalibrēta +2 px (mērītā nobīde −2.3 px); QA: iekšmala 0.655, ārējā 0.365, fons iekšā 0.007.
- Salabots: `load_reports()` vairs nekrīt, ja maker atteicis visu bildi.
- 124339475: novērsti divi viltus caurumi (ēnas kroka L* 20, atspīdums L* 79) — fona komponents tagad jābūt arī papīram līdzīgam, L_TOL (-14,+8). Mērīta kalibrācija.
- Kadrējuma politika: `--framing auto` — slēgts siluets -> novietots ar malām; atvērts -> kadrs kā nofotografēts. Fons 1.4 % -> 28.8 %.
- GATE_F pārformulēts: sargā izgudrotu taisnu griezienu (mala `cut`), nevis pieprasa 3 malas. Mala ir margin / bleed (mantots) / cut (izgudrots).
- Determinsms: 2 skrējieni -> bitu identiski SHA. Testi 11/11.
- Metēnā ēna pie piedurknes malas (izskatījās kā krekla turpinājums): atcelts gradienta precizējums (apgrauž kontūru) un aklā dilatācija +2 (to pastiprināja). Ieviests `_trim_shadow` + `SHADOW_TRIM_PX=3` (mērīts: 98 % auduma sākas <=4 px).
- Segums 0.7058, ALL_PASS, 13.23 s. Determinsms pārbaudīts.
- Kadrējums tagad ir lietotāja izvēle: `--framing slamjam|original|auto` (abi slāņi). `slamjam` = produkta kadrs ar fona malām; prasa slēgtu siluetu, citādi ziņo un atgriež `original`.
- `slamjam` pārbaudīts uz īstas bildes ar slēgtu siluetu: fons 65.9 % pret references 64.3 %, malas 0/0/0/0.
- Profesionālās prakses audits (Nuke IBK, edge extend, light wrap; Photoshop frekvenču separācija; ghost-mannequin ēnas; marketplace specifikācijas): 12 tehnikas, katra ar mērījumu. Dokuments `PROFESIONALAS_METODES.md`.
- Atrasts īsts defekts: ēna krita 54° pret gaismu no 315° (~70° kļūda, "divas saules"). Izmērīts 4 metodēm; uzticamākā — fona plāksne ar inpaint (135°, reziduāla std 2.69 L*). Labots uz 125°.
- `dx,dy` cietie skaitļi (3 kopijas: loop.py:408/496, workflow_v2.py:1155) konsolidēti `SHADOW_ANGLE_DEG` + `shadow_dir()`. Apģērba kodolā 0.00 % izmaiņu, maska nemainīta, determinisms bitu identisks, testi 11/11.
- Noraidīts ar mērījumu: graudu saskaņošana (plakans fons ir marketplace prasība), kontakta ēna (oriģinālā nav asa pleca), light wrap/screen subtraction (ΔR≈ΔG≈ΔB, noplūdes nav).
- Atklāta latentā kļūda debugam: `--rerender-saved` bez `--rotate` salauž renderēšanu (`open_rgb` ignorē saglabāto `rotation_cw`) un pārrēķina grade citādi.
- Sistēmas debug 2026-10-23: 11 faili, 5061 rinda. Statiskā tīra (0 nenoteiktu mainīgo). Atskaite `DEBUG_2026-10-23.md`.
- KRITISKI: piegādātais PARAUGS netiek saskaņots ar MASTER. 6/6 apzinātas sabotāžas (izgudrots plankums, izdzēsts apģērbs, blur, nobīde, iekrāsošana, troksnis) izgāja ar ALL_PASS=True. Vienīgā gāte, kas paraugu saturiski skata, ir GATE_K (viens skalārs b*).
- KRITISKI: rotācija ir globāls sānkanāls, nevis ieraksta daļa. `render_one` ignorē `rec["rotation_cw"]`; `--rerender-saved` bez `--rotate` krīt, maskas ceļš klusi pārsegmentē nepareizā orientācijā. Checker to dara pareizi — asimetrija.
- `--rerender-saved` pārrēķina grade citādi (154.66 vs 158.94) — nav līdzvērtīgs ceļš.
- Pierādīts, ka gātes uz master/masku STRĀDĀ: 5/5 sabotāžas noķertas (GATE_A2, B, H).
- Robustums: 3/3 sliktas ievades nenogāž partiju (bet traceback, ne strukturēta kļūda). Atmiņa 984/1982 MB. loop_engine 1/1 PASS 38 s.
- GATE_R ieviests (`checker_v2.py`): piegādātais JPEG pret master, 3 lielumi (fore_p99 ≤24, bg_p99 ≤4, edge_ratio 0.80–1.85), sliekšņi = viduspunkti starp mērīto likumīgo un mērīto defektu. 6/6 sabotāžas noķertas, bāze iztur.
- `test_gate_r.py` — pastāvīgs regresijas tests (7/7). `test_workflow_v2.py` 15/15 (+4).
- Rotācija: `open_rgb_recorded()` lasa `rec["rotation_cw"]`, nevis globālo; aizstāts 3 vietās. `--rerender-saved` bez `--rotate` tagad dod bitu identisku rezultātu.
- Atskaite labota: `--rerender-saved` grade neatbilstība NEAPSTIPRINĀJĀS — bija novecojis report no neizdevušās ISNet palaišanas (rotācijas kļūdas sekas).
- `/var/tmp` iztīrīšanās starp sesijām apstiprināja atradumu 3.4: sistēma atteicās godīgi (`NAV GATES`), `setup_v2.py` atjaunoja 74 s.
- Mirusī koda tīrīšana: pyflakes 15 -> 0, neviens nav `# noqa`. STRAIGHT_RUN/STRAIGHT_TOL izņemti ar paskaidrojumu (izgudrotu griezienu nosaka `inherited`, ne kontakta garums).
- BG vienā avotā: `loop.BG_GRAY`; checker.py un checker_v2.py to importē (bija 243 trīs failos).
- Ievades validācija: `probe_source_image()` pirms jebkā. Bojāts/tukšs JPEG vairs neaiziet līdz ISNet apakšprocesam, tāpēc traceback vairs netiek ielīmēts `report` `error` laukā. Tukšs fails atkrīt uzreiz (bija 7 s).
- Trūkstošie faili: `raise FileNotFoundError` -> strukturēts paziņojums + exit 2.
- Testi 20/20 (+5 TestSourceProbe), GATE_R 7/7, loop_engine 1/1 PASS 53.8 s, izvade bitu identiska.
- DEBUG pozīcijas 1-6 visas aizvērtas.
- `slamjam` pārbaudīts uz īstas bildes (džinsi): siluets slēgts, malas 0/0/0/0, kompozīcija slamjam, bbox 63.3%x78.0%, fons 70.8%, ALL_PASS.
- Rotācija šai bildei OBLIGĀTA: bez tās fons 79.7% (josla), 90 apgriež otrādi, 270 pareizi. Mērījums neatšķir 90/270 — vizuālā pārbaude obligāta.
- ĪSTA KĻŪDA atrasta un labota: QA pieņemta `isnet_pad_retry` maska tika izmesta (`if method == "plate_texture"` ignorēja retry), pretrunā ar sava komentāra `if retried: pass`. Ar --rotate 90 tas deva STOP, lai gan retry pieņēma (overflow 0.0, uncovered 0.0045).
- GATE_C kalibrācijas kļūda: `silhouette_fill` 0.60 bija uz vienu kreklu; V-veida bikses dod 0.591. Aizstāts ar caurumu pārbaudi (`binary_fill_holes`, caurumi kas nav savienoti ar rāmi) + grīda 0.55.
- GATE_R kalibrācijas kļūda: bg_p99 mērīja arī ēnas gradientu, kur paraugs un reference atšķiras PĒC KONSTRUKCIJAS (ēna renderēta no jauna audekla mērogā, blur 25 vs 35). Tagad bg_p99 tikai uz plakano fonu; ēna paliek informatīvi bg_shadow_p99.
- Zināma vājuma vieta: SILHOUETTE_FILL_FLOOR 0.55 ir 0.007 virs sintētiskā cauruma — divu paraugu robeža, dokumentēta kodā.
- Regresija: krekls #2 `663179f3` bitu identisks, ALL_PASS; GATE_R sabotāžas 7/7; GATE_C 5/5 gadījumi pareizi; testi 20/20.

## 2026-10-23 — melnā līnija gar malu novērsta (§32)

- Sakne: `SHADOW_ANGLE_DEG = 125°` bija iekodēts pēc vienas bildes. Džinsiem ēna oriģinālā krīt pa labi/uz leju, tāpēc labajām malām ēnas nebija un tumšā džinsa mala lasījās kā melna līnija.
- Ēnas virziens tagad MĒRĪTS katrā bildē (`loop.measure_shadow_angle`, gradienta-koriģēts: tuvu 4-24 px pret tālu 60-120 px tajā pašā virzienā). Džinsi 3.6°, krekls 87.9°.
- Divas mērīšanas metodes atmestas ar mērījumiem: kontūras skenēšana (vājš signāls) un krusteniskā korelācija (kreklam 131°, acīm redzami nepareizi, jo aizņem 70% kadra).
- Atklāts līdztekus: globālais LUT + maker atskaite pārrakstījās katrā palaišanā, tāpēc iepriekšējo bilžu nevarēja verificēt (GATE_A2 max_diff=4, viltus kritums). Labots: LUT katrai bildei `output/profiles/`, atskaite uzkrājas, čekeris lieto bildes pašo LUT.
- Krekls #2 pārrenderēts ar izlaboto modeli: 663179f3 -> bf5287c0 (vecais saglabāts `_accepted/` un `_backup_good/`).
- Gala: džinsi `0b974708` 14.4 s; krekls `bf5287c0` 18.4 s; čekeris 2/2 PASS; testi 20/20; GATE_R 7/7; pyflakes 0.
- Neatrisināts: ēnas ATTĀLUMS joprojām fiksēts (43 avota px), tikai virziens mērīts. Oriģināla ēna ir īsāka/blīvāka — nākamais uzlabojums, ne defekts.

## 2026-10-23 — ēna pārāk tumša: modelis pārrakstīts (§33)

- Lietotājs noraidīja iepriekšējo labojumu (SS 082656 krekls, 110348 džinsi): ēna pārāk tumša tieši iezīmētajās vietās.
- Sakne: vecais modelis = nobīdīts izpludināts siluets ar vienu konstanti 0.26 -> VIENMĒRĪGS PLATO ar asu ārējo robežu. Zoom rāda "uzkrāsotu joslu", ne ēnu.
- Izpēte (8 avoti): ēna = kontakta + metamā daļa; uz balta fona 8-20 %, ne 26 %; tumsākais PIE malas; dilšana obligāta, citādi "izskatās kā uzlīme"; eksponenciāls exp(-d/λ) ir rendering standarts.
- Jauns modelis: shade = strength·exp(-d/λ)·window·(ambient + (1-ambient)·w(θ)); strength 0.18, λ 10 px, ambient 0.22, logs uz nulli pirms 80 px.
- Rezultāts: maksimums 22 L* -> 11 L*, pārcelts no nobīdes vidus uz pašu malu, nulle pie 48 px.
- Blakusdefekts atrasts un labots: GATE_B mēra master telpā (3072 px), kur 90 px nav tas pats relatīvais attālums kā 2000 px kadrā -> pareiza izvade krita. Slieksnis tagad mērogots, sabotāžas joprojām 6/6.
- Gala: džinsi `c409ba57` 15.9 s; krekls `c00c4cc6` 18.7 s; čekeris 2/2; testi 20/20; GATE_R 7/7; pyflakes 0.
- Ierobežojums: ēnas parametri fiksēti, nav mērīti no oriģināla (oriģināls 27 % pie malas, mums 18 % — apzināta kompozīcijas izvēle gaišajam papīram).

## 2026-10-23 — īstais defekts: papīra ēna MASKAS IEKŠPUSĒ (melna maliņa) (§34)

- Divas iepriekšējās iterācijas laboja ēnu ĀRPUS apģērba — abas garām. Lietotājs: "ēnai nebija ne vainas, bet fons kas ir tieši pie biksēm ir melns tā kā fons kas nav nogriezts".
- Defekts: segmentācija aprija oriģināla papīra ēnu; matē palika 5-20 px josla ar PAPĪRA krāsu. Pikseļu skenēšana: maskas iekšpusē B-R -25, audumam +5…+10 (džinss zilgans, papīra ēna silta).
- Kāpēc iepriekš neuztvēra: `extend_foreground_colors` apstrādā tikai pikseļus ĀRPUS maskas.
- 4 neizdevušies mēģinājumi dokumentēti: krāsas aizvietošana (1.4% joslas), alfa atšķetināšana (C_f pats kontaminēts), akls choke (apgraiza siluetu), pa pikselim griezta hroma maska (mala saplīsa robos).
- Risinājums `decontaminate_rim`: griež GAR KONTŪRU — mēra papīra dziļumu katram kontūras punktam (hroma UN spilgtums), izlīdzina ar gaussian sigma=120 gar kontūru, nobīda punktus uz iekšu. Vidēji 7.3 px, max 16.
- Rezultāts: malas B-R -15.0 -> -1.0 (audums +10). Melnā josla pazudusi, mala gluda, detaļas saglabātas.
- Blakusdefekts: `_MASK.png` rakstījās PIRMS apgriešanas -> GATE_R fore_p99=171 viltus kritums. Tagad apgrieztā maska tiek saglabāta kā kanoniskā.
- Gala: čekeris 2/2 PASS; testi 20/20; GATE_R 7/7; pyflakes 0; džinsi 17.4 s, krekls 20.6 s.
- Ierobežojums: ja apģērbam ir sprauga tieši malā, normāle var iziet cauri spraugai; ierobežo max_trim_px=16 un MORPH_OPEN 11×11.

## 2026-10-23 §35 — malas kritērijs pārbūvēts uz tekstūru
§34 (hroma+spilgtums) krita lietotāja pārbaudē. Mērījumi: 73.8 % tumšo pikseļu
ir dziļi audumā, tāpēc spilgtums neder. Jauns kritērijs: papīra ēna gluda
(tekstūra 1.4), džinss teksturēts (11–22). Griež gar kontūru, izlīdzina tikai gar
to; otrs solis noņem izvirzījumus (tikai teksturētiem audumiem). Džinsi
1d2a493d (20.4 s), krekls 2b4f912c (22.5 s, nav mainījies). Čekeris 2/2,
testi 20/20, gate_r 7/7. Skat. QA §35.

## 2026-10-23 §35.7 — pakāpienu izlīdzināšana (Vinted produkcijas prasība)
Lietotājs: bildes vajadzīgas Vinted tirdzniecībai, jābūt bez kompromisiem.
1:1 pārbaudē atklāts, ka īstais defekts nav krāsu josla, bet **robaina mala**:
ISNet seko papīra ēnas mēlei un dod taisnstūra pakāpienus ~15 px.
`MORPH_OPEN 11×11` tos pastiprināja. Labots: kontūru pievelk pie gludās
līnijas, ja novirze ≤14 px; LINE_AA + shift=4 pildījums; MORPH_OPEN noņemts.
Noraidīts ar mērījumiem: edge snapping (gradients pie malas 155–235, maska jau
seko īstajai malai), guided filter (malu izpludina), BiRefNet_lite (neiederas
1982 MB RAM). Džinsi 600e00ea, krekls 1d93c7a7. Čekeris 2/2, testi 20/20, gate_r OK.

## 2026-10-23 §36 — studijas ēna + fotogrāfiska mala
Ēna bija 3× vājāka par atsauci (24 vs 87 vienības pie malas, pazuda 50 px).
STRENGTH 0.18→0.32, FALLOFF 10→18, AMBIENT 0.22→0.55, CUTOFF 80→34.
"Robainība" nebija ģeometrijā (mūsu kontūra 0.29 gludāka par atsauces 0.45) —
mala bija šķēru asa. refine_alpha feather 1.6→3.0, contrast 1.65→1.25, band→6.5.
Vairāk nevar: feather 6.0 krita GATE_H (alfa >8px ārpus) un GATE_R (27>24).
Džinsi 75f53072, krekls 6b63665d. Čekeris 2/2, testi 20/20.

## 2026-10-23 PIEŅEMTS — §36 džinsi
Lietotājs: "Ir labi, ļoti labs rezultāts." Džinsi 75f53072 pieņemti un
saglabāti _accepted/MVIMG_161031_ACCEPTED_75f53072.jpg.
Krekls 6b63665d arī saglabāts (jaunais, ar ēnu un mīksto malu);
vecais fallback 663179f3 paliek _accepted blakus.
Šis ir atskaites punkts: ēna (0.32/18/0.55/34) + refine_alpha (3.0/2.0/1.25/6.5)
+ decontaminate_rim ar tekstūras kritēriju + snap w35 s14. Nediagnostīcēts
paliek: uploads/IMG_20261023_075010.jpg baltie stieņi pie aprocēm.

## 2026-10-23 Krātuves tīrīšana
Dzēsts (dublēts vai viennozīmīgi atkritumi, pirms tam pārbaudot):
- `_backup_good/` 34 MB — rezerves LUT (`grade_profile_v2.json`, sha 316b8164)
  ir identiska `output/grade_profile_v2.json` un
  `output/profiles/PXL_...PROFILE.json`; fallsback `663179f3` jau ir `_accepted/`.
- `_backup_pre_fix_54deg/` 2.7 MB — pirms-54° vecais krekls, aizstāts.
- `__pycache__/`, `PIRMS_PEC_ena.jpg` — pagaidu artefakti.
- `/var/tmp/models/birefnet_lite.onnx` 224 MB — BiRefNet, kas neiederas RAM.

Saglabāts tīši:
- `output/master/` 25 MB — **čekeris to lieto** (`reconcile_reference`), bez tā
  GATE_R nevar pārbaudīt; izmērīts checker_v2.py:187,258.
- `.md` dokumentācija (t.sk. QA §31–36), `lab/`, `_accepted/`, `output/`.

Rezultāts: /home/user 98 MB -> 60 MB, 118 -> 95 faili.

## 2026-10-23 §37 — tuvplāni (slamjam stila papildskati)
Jauns modulis `closeup.py`. Galvenais: tuvplānam nav vajadzīga segmentācija
(atsaucē apģērbs iet pāri malām), tāpēc nav arī malas defektu. Griež 1:1 no
master -> asāks par overview (gradienta vid. 213.9 vs 89.9, t.i. 2.4x).
Logs adaptīvs: lielākais 4:5 ar segumu >=0.88. Akcenti mērīti:
"detaļa" = Laplacian maksimums, "zīmols" = hromas novirze (trāpīja sarkanajai
etiķetei). Palielinājums ar Lanczos + UnsharpMask(threshold 3).
Džinsi 1023x1279 -> 1.96x; krekls 2000x2500 -> 1.00x (bez palielināšanas).

## 2026-10-23 §38 — otrā drēbe (henley), divas bildes + tuvplāni
Atklāti un laboti TRĪS defekti:
1) master ēna bija avota mērogā (blur 35), gala — audekla (blur 25); pēc
   samazināšanas x0.52 tā iznāca 18 px vietā 25 -> GATE_R bg_p99 7-9.
   Labots ar para_scale: visi ēnas mēri dalīti ar ielīmēšanas koeficientu.
2) reconcile_reference grieza master pa bbox un nogrieza ēnu ārpus bbox ->
   viltus GATE_R kritums gar kontūru. Labots ar divslāņu referencei.
3) test_isnet_parity rādīja uz dzēsto bildi #1 -> neko nepārbaudīja. Pārvirzīts.
Akcentu kritērijs: Laplacian uz neapstrādāta spilgtuma izvēlas blīvāko
TEKSTŪRU (tukšs audums). Labots: |Laplacian(gaussian(lum, σ))|, σ=0.003·platums,
meklē 500x625 logā. Čekeris 4/4, testi 20/20, gate_r OK, parity OK.

## 2026-10-23 — 45° tuvplāni ATMESTI (lietotāja lēmums)
Visa ar tiem saistītā izstrāde dzēsta pēc lietotāja lūguma: 4 bildes,
kolāža, JSON, `closeup45.py`, `closeup45_set.py` un QA §39. Šo virzienu
NEATKĀRTOT. Galvenās bildes nav aiztikts (4/4 PASS).

## 2026-10-23 — krātuves tīrīšana (88 MB -> 41 MB)
Izdzēsts:
- `output/master/*_MASTER_1to1.png` (43 MB). Tie ir STARPPRODUKTS un ir pilnībā
  atjaunojami BEZ AI modeļa ar jauno `rebuild_master.py` (~19 s visiem 4).
  Pārbaudīts pirms dzēšanas: audums atjaunojas bitu precīzi, ēna līdz 8 LSB.
  Atslēga: masteris = oriģināls + LUT (profils) + `_MASK.png` + ēnas konstantes.
  Rotācija jāņem no `output/report_v2_maker.json`, NEVIS `rotation_for()` —
  divām bildēm tā atgriež 0, lai gan reālā rotācija bija 270°.
- `_accepted/` dublikāti, kas bitu precīzi sakrita ar `output/paraugs/`.
  `PXL_124339475_ACCEPTED_663179f3.jpg` saglabāts — tas ir atšķirīgs.
- Novecojušas QA salīdzinājumu bildes (`_PARBAUDE_*`, `_SALIDZINAJUM*`).
Saglabāts: `uploads/` 32 MB (oriģināli, neaizvietojami), 4 galvenās bildes,
maskas + LUT profili (vajadzīgi atjaunošanai), visi skripti un dokumenti.

## 2026-10-23 §40 — pirmais Vinted komplekts (henley), 5 bildes
Trīs jau gatavās bildes pēc atkārtotas palaišanas palika bitu identiskas.
Divi jauni kadri: pogu plāksne (124322251, rotācija 270°) un etiķete
(124406358). Atrasts jauns defekts: kad audums sniedzas pāri kadra malai,
`decontaminate_rim` pa kontūru izdur plaisas (un ISNet bija atzinusi divus
izbalējušus auduma laukumus par fonu). Labots: fona komponentes analīze +
jauna opcija `--no-decontam STEM`. Etiķetes kadrs pipeline pamatoti
noraidīts (nav ko segmentēt) -> 4:5 griezums no oriģināla, 90° pagrieziens,
papīra josla nogriezta, tās pašas uzņemšanas LUT.

## Jauna aktīva grupa — Henley krekls (2026-10-23)
- Starta noteikums ievērots ar nokavēšanos: darbs tika iesākts pirms
  jautājuma, lietotājs to norādīja. Jautājums uzdots ar izvēles pogām;
  atbilde `Jā, šīs ir visas — sāc darbu`, un `Paturēt — tās ir pareizas`.
- INVENTARIZĀCIJA fiksēta (5 bildes, visas no 2026-10-22 uzņemšanas):
  1. `PXL_20261022_124309570.PORTRAIT.ORIGINAL.jpg` — priekša (3072×4080)
  2. `PXL_20261022_124651636.PORTRAIT.ORIGINAL.jpg` — mugura (3072×4080)
  3. `PXL_20261022_124322251.PORTRAIT.ORIGINAL.jpg` — pogas, rotācija 270° (4080×3072)
  4. `PXL_20261022_124339475.PORTRAIT.ORIGINAL.jpg` — aproces, rotācija 270° (4080×3072)
  5. `PXL_20261022_124406358.PORTRAIT.ORIGINAL.jpg` — etiķete, rotācija 90° (4080×3072)
- Statuss: kolāža `output/_KOMPLEKTS_vinted_henley.jpg` nodota vērtēšanai.
  `.zip` NEVEIDOT, kamēr lietotājs kolāžu nav apstiprinājis ar izvēles pogu.

### §41 — Plakāts izlabots (2026-10-23)
- `checker_v2.py`: `src_edge` tagad mēra ar to pašu joslas platumu kā gala
  kadrs (1.2 % platums / 0.96 % augstums). Bez tā plakāts viltus krita kā `cut`.
- `fix_mask_holes.py` (jauns, reproducējams): aizpilda iekšējās fona
  komponentes, kurās nav papīra pikseļa. Aizpildīja 418 px izcēlumu.
- Plakāts renderēts no neskartā 4080 px meistara; čekeris **1/1 PASS**.
- `make_collage_vinted.py` (jauns): kolāža reproducējama, nevis ar roku.
- Gala sha256 `f2d552993db074df…` (2.37 MB).

### Piegāde (2026-10-23)
- Kolāža ar izlaboto plakātu apstiprināta (`Apstiprinu — veido .zip`).
- Arhīvs: `output/vinted_henley_2026-10-23.zip` (8.88 MB) — 5 kadri 2000x2500,
  kolāža, READ_ME.txt. Būvēts ar `make_zip_vinted.py` tieši no gala failiem.
- `workflow_v2.py --make-zip` apzināti nav lietots (sk. skripta docstring:
  4 kadriem nav meistara pēc krātuves tīrīšanas, birkai nav maskas).
- Apstiprinātie sha256 (16): prieksa 3dc8f80606b3095c · mugura c11e478ce0461898 ·
  plakats **f2d552993db074df** · aproces 6b63665df9a5d99b · birka 31b7feee5102c033

### Grupas slēgšana — noteikums atgādināts (2026-10-23)
- Lietotājs norādīja uz izlaistu soli: **pēc `.zip` lejupielādes jādzēš arī pats
  `.zip`** — darba telpā vienlaikus tur tikai vienu aktīvu bilžu grupu
  (noteikums jau bija `LOOP.md` 8. sadaļā un "Pastāvīgais piegādes noteikums"
  blokā; šoreiz tas netika izpildīts).
- Šī soļa izpildei izveidots `close_group.py` (demo pēc noklusējuma, `--yes`
  dzēš). Tas dzēš tikai norādīto celmu failus + kolāžu + `.zip`, un izdrukā
  atbrīvotos baitus.
- Piegādātais arhīvs pirms dzēšanas nofiksēts:
  `output/vinted_henley_2026-10-23.zip`, 8 878 628 baiti,
  SHA-256 `678aa5aeae9d7e198c4341baff4b86e78c9942f37f0ad50be47d8c06049c6e84`.
- Grupas failu saraksts dzēšanai: 30 faili, 50,59 MB (5 PARAUGS, 4 avoti bez
  birkas maskām, 1 MASTER, 15 maskas/ALPHA + `_pirms` dublējums, 5 profili,
  kolāža, `.zip`).
- CITAS GRUPAS NETIEK SKARTAS: `uploads/MVIMG_20261020_161031.jpg` (džinsi),
  4 `IMG_20261023_*` avoti un `slamjam_*` parauga atsauces paliek vietā.
- [x] Lietotājs ar izvēles pogu `Lejupielādēju — dzēst grupu` apstiprināja
      lejupielādi. Dzēšana izpildīta ar `close_group.py --yes`: **30 faili,
      50,59 MB** (5 PARAUGS, 5 `uploads/` avoti, 1 MASTER, 15 maskas/ALPHA
      ieskaitot `_pirms` dublējumu, 5 profili, kolāža, `.zip`).
- Pēc tīrīšanas `output/master/` ir tukšs, `output/*.zip` nav, `output/paraugs/`
  satur tikai iepriekšējās grupas `MVIMG_20261020_161031_PARAUGS_2000x2500.jpg`.
- STĀVOKLIS: Henley (2026-10-23) grupa ir piegādāta un **slēgta**. Darba telpa
  gatava vienai jaunai bilžu grupai.

### §42 — Ēna saspiesta pēc SLAMJAM parauga (2026-10-24)
- Mērījums: mūsu ēna kontaktā bija tikpat tumša kā paraugam, bet stiepās
  divreiz tālāk (30+ px pret 12-18 px) → izskatījās kā gaišs halo.
- `restyle_shadow.py`: esošās ēnas mērogošana ar f(d)=1.10·exp(−(d/10)^1.3);
  audums netiek aiztikts (maks. 2 līmeņi no JPEG).
- Atmestas 3 pieejas (nobīdīts siluets, vienmērīgs rims, izgriešana/aizvietošana)
  — visas deva rimbuli, uzlīmes kontūru vai šuvi. Sk. QA §42.
- Fails: `output/paraugs/02_mugura_ena_slamjam.jpg`.

### §43 — Virzīta ēna (2026-10-24)
- Lietotājs izvēlējās "taisi kā slamjam" → ēna mērogota ar virziena svaru.
- Divas kļūdas atrastas: apgriezta gradienta zīme un pārmērīga piesaiste malai.
- Rezultāts: kreisi augšā 20.9, pa labi 30.7, augšā 19.9, apakšā 37.7 pret
  veco 42.8/26.7/33.3/28.0 — ēna tagad virzīta, nevis simetriska.
- Audums 1:1 identisks (6 līmeņi no JPEG). Fons 243.
- Fails: `output/paraugs/02_mugura_ena_slamjam.jpg` (sha 54c865c8aa3e94bd).

### §44 — Metēnā ēna uz fona (2026-10-24)
- Mērījums: vecā ēna nomira 20-30 px attālumā → izskatījās kā šaura josla.
- `cast_shadow.py`: PCSS modelis (gaisma kā laukums) + astes slānis.
- Divi obligāti noteikumi: nobīde > avota rādiuss; aste novirzīta gaismas virzienā.
- Rezultāts: labi 39.2 pret kreisi 8.2 pie 5 px; sniedzas ~80 px; monotons kritums.
- Audums netiek aiztikts (0 izmaiņu), fons 243.
- Fails: `output/paraugs/02_mugura_ena_metena.jpg` (sha f01c567d611387a4).

### §45 — Neēnotā līnija novērsta (2026-10-24)
- Cēlonis: (1−α) faktors malā (~0.5) + mīkstā auduma mala 3 px pirms maskas.
- Labojums: ēnas maska no 2 px sašaurinātas siluetes, bez (1−α).
- peak 48→96; ēna pie kontakta Δ≈100, saglabā gradients līdz ~90 px.
- Audums neskarts (vid. 0.15 līmeņi). Fails sha 9597a617f45eabce.

### §46 — Ēnas rādiuss samazināts (2026-10-24)
- spread 28→14, ox/oy 52/60→26/32, tail 0.30→0.14. peak 96 nemainīts.
- Kontakta tumšums Δ 102.9 visos variantos — mainījās tikai garums.
- Ēna nomirst ~30-35 px (iepriekš ~90). Fails sha 3d106d7dec67c04f.

### §47 — Vai var pārnest oriģinālo ēnu? (2026-10-24)
- Uzrakstīts `real_shadow.py` (rolling ball izgūšana + afīnā pārnese).
- Pārbaudīts uz `MVIMG_20261020_161031`: oriģinālā ir tikai plāna kontūras
  "ēna" (papīra kroka), ne gara metēnā ēna; nav atšķirama no krokām.
- Henley kadriem oriģināli dzēsti pēc ZIP piegādes.
- Secinājums: sintētiskā ēna paliek; īsta ēna iegūstama tikai uzņemšanā.

---

> Turpinājums no pagaidu `PROGRESS.md` (jaunās sarunas sākumā izveidots, pirms `02_ATMINA.md` pienākšanas; oriģināls saglabāts kā `PROGRESS.md.bak-20261024-064617`). §48 pārņemts burtiski; tajā minētais “nav verificēts” par numerāciju atrisināts §49.

## §48 — Jauna grupa fiksēta: Vans melnas chino bikses (2026-10-24)

Numurs §48: nākamais pēc §47 pēc `00_SAKU_SHEIT.md` §7/§13.
**Nav verificēts** pret `02_ATMINA.md` (faila nav).

### Lēmums
- Lietotājs ar pogu apstiprināja: **„Jā, šīs ir visas — sāc darbu“**
  (pēc diviem inventāra jautājumiem; pirmais bija „Nē, vēl pievienošu“).

### Aktīvā grupa — PILNS SARAKSTS (4 bildes, fiksēts)

| Fails | px | baiti | sha256 (16) |
|---|---|---|---|
| `MVIMG_20261020_161746.jpg` | 3072×4096 | 9 679 802 | `51950c1c5a474bf9` |
| `IMG_20261020_201332.jpg` | 3071×4096 | 11 694 232 | `efe6453067fdd41f` |
| `MVIMG_20261020_161944.jpg` | 3072×4096 | 11 611 809 | `da48767d2713290a` |
| `MVIMG_20261020_161959.jpg` | 3072×4096 | 9 817 831 | `85043fff5debb732` |

- Vizuālā identifikācija (nav mērījums): melnas Vans „Authentic Chino“
  bikses — 2 pilni kadri (priekšpuse/mugurpuse) + 2 jostasvietas tuvplāni.
- Faila → satura atbilstība (kurš ir priekšpuse u. tml.) **vēl nav
  verificēta** — tiks noteikta preflight posmā.
- Kadros redzami sveši priekšmeti (zeķe, ķivere) — **risks vārtam E**,
  jāpaliek ārpus maskas.
- Glabāšanas orientācija: vertikāla (~3072×4096). Lēmums par 90°
  pagriezienu **vēl nav pieņemts** — tikai preflight laikā.
- Oriģināli glabājas `/home/user/uploads/` — nedzēst bez lēmuma (§3.5).

### Paraugs / atsauce (grupā NEietilpst, 4 faili)

| Fails | px | baiti | sha256 (16) |
|---|---|---|---|
| `slamjam_mfpen_trousers.jpg` | 2000×2500 | 439 351 | `bb0e436bff3ebb42` |
| `slamjam_mfpen_trousers_2.jpg` | 2000×2500 | 433 790 | `cdbca1dd3cdd11b3` |
| `slamjam_mfpen_trousers_3.jpg` | 2000×2500 | 918 743 | `49fa45698c4ee120` |
| `slamjam_mfpen_trousers_4.jpg` | 2000×2500 | 796 266 | `669263eb8388f3a3` |

Izmērs 2000×2500 sakrīt ar izvades specifikāciju (galvenes mērījums).
Fons/ēna no parauga **vēl nav mērīti** (`measure_shadow.py` nav palaists).

### Stāvoklis
- Apstrādātas bildes: **0 / 4**. Maskas: 0. MASTER: 0. PARAUGS izvades: 0.
- Krātuve ieraksta brīdī: `/home/user` = 44M (mērķis < 100 MB ✓),
  `uploads/` = 44M, `loop_bildes/` = 44K.
- `atjaunot.py` izveidots no `00_SAKU_SHEIT.md` Pielikuma A:
  4554 B, 163 rindas, sha256 `a98287f0af60b1af`, `py_compile` OK.

### Bloķētāju statuss (atjaunināts pēc dzinēja atjaunošanas, 2026-10-24)
- `01_DZINEJS.md` — **ATRISINĀTS** (atjaunots, sk. zemāk).
- Vide — **BLOĶĒ**: `setup_v2.py --check` → `ready: false`, exit 2.
  Pirms preflight jāpalaiž `python3 setup_v2.py` (instalācija).
- `02_ATMINA.md` — **NAV** (nebloķē ražošanu; bloķē vēstures
  nepārtrauktību un § numerācijas verifikāciju).

### Atjaunošanas mēģinājums (2026-10-24)
- Pēc lietotāja komandas palaists: `python3 atjaunot.py 01_DZINEJS.md`
- Rezultāts: `Nav atrasta pakotne: 01_DZINEJS.md`, exit 2. Meklēts visā
  `/home/user` — fails neeksistē. **Atjaunoti faili: 0.** Stāvoklis nemainīgs.
- Komanda atkārtota otro reizi — tas pats rezultāts (exit 2).
  `uploads/` joprojām 9 faili, jaunākais laika zīmogs 06:26 — jauns
  pielikums nav pienācis.

### Dzinējs atjaunots (2026-10-24)
- Pakotne: `/home/user/uploads/01_DZINEJS.md`, 315 937 B,
  sha256 `c9de6f3b20b3b0a78d6659add61394f9cac6d49f2c2ab3032795a62735cca723`
  — prefikss sakrīt ar lietotāja norādīto `c9de6f3b…` ✓
- `atjaunot.py`: pārbaudīti 23, OK 23, SHA nesakrīt 0, ierakstīti 22,
  1 izlaists kā jau identisks (`HANDOFF/atjaunot.py`),
  `REZULTĀTS: VISS LABI`, exit 0. `.bak` failu: 0.
- Kompilācija: 22/22 `*.py` (`loop_bildes/` sakne), exit 0.
- `PROGRESS.md` atjaunošana neskāra (sha pirms/pēc `dd0926a3d38b924b`).
- Krātuve: `/home/user` 44M → 45M; `loop_bildes/` 48K → 396K.
- 3. solis (`02_ATMINA.md` atjaunošana): `Nav atrasta pakotne`, exit 2 —
  fails nav augšuplādēts. Dokumenti atjaunoti: 0.
- Vide (`setup_v2.py --check`, exit 2): `ready: false`.
  OK: cv2 4.11.0, numpy 2.3.5, PIL 12.3.0, scipy 1.17.1, Python 3.13.16.
  Trūkst: `onnxruntime` (pin 1.31.0), `rembg` (pin 2.0.85),
  ISNet modelis `/var/tmp/rembg_home/models/isnet-general-use/isnet-general-use.onnx`
  (exists: false, 0 B). `/var/tmp` brīvs: 21 475 565 568 B (~20 GiB).
- Apstrādātas bildes joprojām: **0 / 4**.

### Nākamie soļi
1. `python3 setup_v2.py` (vides instalācija uz `/var/tmp`), tad atkārtots
   `--check` — jābūt `ready: true`.
2. `python3 workflow_v2.py --preflight --files <4 grupas faili>`
3. Attempt 1 → `checker_v2.py` → vizuālais audits → kolāža → pogas
   „Apstiprināt / Noraidīt“ (§3.4). ZIP tikai pēc apstiprinājuma + PASS.
4. Kad pienāks `02_ATMINA.md`: `python3 atjaunot.py /home/user/uploads/02_ATMINA.md`
   (šis `PROGRESS.md` tiks pārsaukts par `*.bak-*`; §48 ieraksts jāpārnes).

---

## §49 — Vide un atmiņa atjaunotas jaunā sarunā (2026-10-24)

### Problēma → mērījums → izmaiņa → rezultāts
- Problēma (§48 beigu stāvoklis): dzinējs atjaunots, bet vide
  `ready: false` (nav onnxruntime/rembg/ISNet) un nav `02_ATMINA.md`.
- Mērījums PIRMS: `/var/tmp/pylibs` un `/var/tmp/rembg_home` neeksistē;
  `/home/user` 45M, `loop_bildes/` 400K.
- Izmaiņa 1: palaists `python3 setup_v2.py 2>&1 | tee /tmp/setup.logw`
  (loga fails ar lietotāja doto nosaukumu; 148 rindas, 11 912 B;
  visas komandas izpilde kopā ar atkārtotu pārbaudi ~63 s).
- Rezultāts 1: `ready: true` — gan setup iekšējā, gan neatkarīga
  `--check` pārbaude (abi exit 0). Versijas == piespraudēm: cv2 4.11.0,
  numpy 2.3.5, PIL 12.3.0, scipy 1.17.1, onnxruntime 1.31.0,
  rembg 2.0.85 (Python 3.13.16). ISNet modelis 178 648 008 B:
  `/var/tmp/rembg_home/models/isnet-general-use/isnet-general-use.onnx`.
  `/var/tmp/pylibs` 572M, `/var/tmp/rembg_home` 171M;
  `/var/tmp` brīvs pēc instalācijas 20 697 120 768 B.
  `/home/user` nemainīgs 45M — instalācija darba telpu neaizņem ✓
- Izmaiņa 2: atjaunots `02_ATMINA.md` (285 534 B, sha256
  `f7078736a7289c7984866b090578fd105df7547459d5a59a0b447dd2dd463706`):
  12/12 OK, 0 SHA neatbilstību, ierakstīti 12, `REZULTĀTS: VISS LABI`.
- Rezultāts 2: vēsturiskais `PROGRESS.md` pirms apvienošanas 68 810 B,
  959 rindas, sha `ca6d440ebe840d55`, pēdējā sadaļa §47 — līdz ar to
  §48 numerācija, kas pagaidu failā bija **nav verificēta**, tagad ir
  **verificēta** (nākamā aiz §47). Pagaidu fails (5 225 B, sha
  `9b7a258cd98f0a51`) saglabāts kā `PROGRESS.md.bak-20261024-064617`,
  netiek dzēsts; tā §48 saturs zemāk pārņemts burtiski.
- Krātuve pēc dokumentu atjaunošanas: `/home/user` 45M,
  `loop_bildes/` 700K. Apstrādātas bildes: **0 / 4** (nemainīgi).
- `PAPIRA_NOPLUDES_QA.md` ieraksts šoreiz netiek veidots: šis ir
  infrastruktūras atjaunošanas solis bez neviena bilžu mērījuma;
  pirmais QA ieraksts sekos ar preflight/Attempt skaitļiem.

### Stāvoklis un nākamais solis
- Visi §48 bloķētāji novērsti: dzinējs ✓, vide `ready: true` ✓,
  dokumenti ✓. Aktīvā grupa un paraugi — kā §48 sarakstā.
- Nākamais: `workflow_v2.py --preflight` ar 4 grupas failiem, tad
  Attempt 1 → checker → audits → kolāža → pogas (§3.4).
---

## §50 — Vans grupa: Attempt 1–2, GATE_R labojums, checker 4/4 PASS; gaida lietotāja pogu (2026-10-24)

### Preflight un failu atbilstība
- `workflow_v2.py --preflight`: ready true, problems [], exit 0. Avoti kopā
  42 803 674 B; visi saglabātie izmēri vertikāli, `rotation_cw=0`.
  Pagrieziens nav vajadzīgs: EXIF orientācijas 0/1 un vizuāli jostasvieta
  visos kadros ir augšā.
- Fails -> saturs (tagad verificēts pēc izvades kolāžas):
  `MVIMG_20261020_161746` = mugura; `IMG_20261020_201332` = priekšpuse;
  `MVIMG_20261020_161944` = aizvērtas jostasvietas tuvplāns;
  `MVIMG_20261020_161959` = atvērta rāvējslēdzēja/oderes tuvplāns.

### Attempt 1 — problēma atrasta ar checker
- Maker 4/4 completed: kopā 53.985 s, vidēji 13.496 s/bilde, maks. 17.796 s.
  Pilnie kadri: ISNet pieņemts (segums 0.4329 un 0.3557, framing=slamjam).
  Tuvplāni: ISNet QA noraidīts (silhouette_fill 0.4365 un 0.1193 < 0.6),
  `isnet_pad_retry` pieņemts (segums pēc maker 0.5446 un 0.7328,
  framing=original). Profils: fons [212.0, 208.5, 196.5],
  WB [0.977046, 1.0, 1.085985], ekspozīcija 1.06, WB uzticams.
- Checker: **2/4 PASS**, exit 2. Vienīgais bloķējošais kritums abiem
  tuvplāniem bija GATE_R: fore_p99 26.0 un 28.0 > limits 24.0
  (fore_p95 20.0/21.0; edge_ratio 1.376/1.381; bg_p99 1.0).
  Pārējie piemērojamie vārti izgāja; F pilniem kadriem ir pass=None (N/A),
  L ir advisory pass=None ar verdict PASS un leak_px=0.

### Diagnoze — izvades asināšana, ne nobīde un ne JPEG viens pats
- Nobīdes tests: jebkura vesela pikseļa nobīde tuvplāniem paceļ p99 uz
  87-155; bez nobīdes tas ir 26/28 -> ģeometrijas nobīde nav cēlonis.
- No checker references: JPEG q95 vien dod p99=7; UnsharpMask 42% bez JPEG
  dod 26/27; 42%+JPEG dod 26/28 — precīzi faktiskais rezultāts. Augsta
  gradienta pikseļos p99=33/36, zema gradienta pikseļos 12/12.
- Pilna sweep simulācija visām 4 bildēm 42% gadījumā bitiski sakrita ar
  checker p99/p95/edge. Maksimālais p99 pa grupu: 42%->28, 35%->24
  (0 rezerve), 30%->21, **25%->18**, 20%->15, 0%->7. Izvēlēts 25%:
  6 līmeņu rezerve līdz 24 un edge_ratio prognoze 1.181-1.232.
  **Checker slieksnis netika mainīts.**

### Izmaiņa un Attempt 2
- Viena koda rinda `workflow_v2.py:1193`: `output_sharpen.percent` 42 -> 25
  (radius 1.4, threshold 3 nemainīti). Sha pirms `2829a92a582b0f92`,
  pēc `b9484cdb0a0afa64`; `py_compile` OK. `test_workflow_v2.py`
  atjaunotajos 23 failos nav, tāpēc vienību testi šajā sarunā nav palaisti;
  validācija ir pilns maker + neatkarīgs checker.
- Palaists `--attempt 2 --rerender-saved`. Pilniem kadriem maskas, ALPHA un
  MASTER palika bitiski identiski Attempt 1. Tuvplāniem atklāts svarīgs
  fakts: rerenderī `decontaminate_rim` nav idempotents — uz jau saglabātajām
  maskām tas vēl noņēma 102 868 px (161944) un 44 627 px (161959);
  checker C segums mainījās 0.5359->0.5277 un 0.7283->0.7247. Abi kadri
  pēc tam joprojām iziet visus vārtus un vizuāli malas ir veselas, bet
  turpmākiem rerenderiem šis efekts jāatceras.
- Maker Attempt 2: 4/4, vidēji 13.514 s/bilde, maks. 16.755 s
  (masku laiki ierakstā pārmantoti no saglabātajām maskām).
- Checker Attempt 2: **4/4 PASS**, exit 0. A2 max_diff=0 visiem;
  B far_bg=100.0%; H core/outside=100.0%/100.0%, bad_partial_px=0;
  R fore_p99: 6.0 (161746), 7.0 (201332), 17.0 (161944), 18.0 (161959);
  T: 10.613 / 10.048 / 16.638 / 16.755 s pret limitu 25.0 s.

### Vizuālais audits un ēna — kas ir pierādīts un kas nav
- Aģents apskatīja Attempt 2 kolāžu un abus tuvplānus pilnā izmērā.
  Zeķe un ķivere no oriģināliem izvadēs nav; staras, jostasvietas, birkas,
  pogas, rāvējslēdzējs un odere saglabāti; acīmredzama oreola vai papīra
  joslas nav. To atbalsta L verdict PASS/leak 0 un P regions=0, px=0.
- `measure_shadow.py` deva ēna_kodols Δ 7.0 mūsu pilniem kadriem un 4.0/3.0
  Slam Jam paraugiem. Tas ir metodes artefakts: ēna ar Δ>12 tur tiek
  pieskaitīta siluetam. Tāpēc veikts atsevišķs audits pēc faktiskās
  novietotās maskas attāluma. Pilniem kadriem vidējais Δ joslās
  2-4 / 4-10 / 10-18 / 18-28 / 28-45 px = 47.6/39.2/26.6/10.8/0.8 un
  47.4/39.1/26.6/10.7/0.8. Virzieni <=40 px (vidēji/p95): E 26.3/65 un
  26.4/65; S 16.0/39 un 15.8/38; W 14.7/36 un 14.8/36; N 14.8/36 un 14.9/36.
  Paraugiem ar auduma slieksni L<150: E 34.8/90 un 17.8/80; S 34.2/91 un
  16.1/79; W 1.1/3 un 1.5/8; N 1.9/2 un 1.8/0. Secinājums: mūsu ēna
  nomirst līdzīgā attālumā, bet pretējā (W/N) pusē saglabā workflow
  ambient komponenti; tā nav tik vienpusīga kā paraugā. E-vārtu ēnas daļa
  ar to **nav pasludināta par pierādītu** — gala lēmums lietotājam.
- Ēnas eksperimenti tikai `/tmp` (gala faili nemainīti): `restyle_shadow`
  W/N vidējo samazināja tikai 14.7->10.2; `cast_shadow` S2 E/S pacēla līdz
  ~46/42, bet simulētais GATE_R bg_p99 kļuva 18-25 > 4 un tālā fona
  (=243, d>60 px) īpatsvars nokrita līdz 96.35-96.79%. Tāpēc cast S2
  kanoniskajām izvadēm **netika lietots**, lai nesalauztu checker 4/4 PASS.

### Gala faili (Attempt 2; vēl nav lietotāja apstiprināti, ZIP nav)
| Fails | baiti | sha256 (16) |
|---|---:|---|
| `output/paraugs/MVIMG_20261020_161746_PARAUGS_2000x2500.jpg` | 585 187 | `e370ddff20459b70` |
| `output/paraugs/IMG_20261020_201332_PARAUGS_2000x2500.jpg` | 627 090 | `ef7e836cbdcd64f3` |
| `output/paraugs/MVIMG_20261020_161944_PARAUGS_2000x2500.jpg` | 1 753 199 | `9dd96f1b6deebffb` |
| `output/paraugs/MVIMG_20261020_161959_PARAUGS_2000x2500.jpg` | 2 222 564 | `a297c6bf7bd8f38e` |
| `output/master/MVIMG_20261020_161746_MASTER_1to1.png` | 7 684 973 | `8356381521829a05` |
| `output/master/IMG_20261020_201332_MASTER_1to1.png` | 7 297 805 | `b13dbff7b1c6d588` |
| `output/master/MVIMG_20261020_161944_MASTER_1to1.png` | 12 940 213 | `7d21213cf76ea5fc` |
| `output/master/MVIMG_20261020_161959_MASTER_1to1.png` | 15 681 916 | `83180246cfc5f2d6` |
| `output/V2_KOLAZA.jpg` | 407 293 | `fae2ae65bcac533a` |

- Krātuve: pirms apstrādes `/home/user` 45M (du -sh); pēc Attempt 2 checker
  un pirms šī ieraksta 93M / 97 149 086 B, no tiem `output/` 48M. Oriģināli
  `uploads/` nav dzēsti un nav mainīti. Apstrādātas/renderētas 4/4 bildes;
  piegāde joprojām gaida pogas `Apstiprināt / Noraidīt`. ZIP veidot drīkst
  tikai pēc `Apstiprināt` (checker PASS jau ir). Pēc apstiprināšanas
  jātīra `__pycache__` un pagaidu diagnostika; pirms ZIP vēlreiz jāmēra du.
- Atgādinājums koda līmenī: `workflow_v2.py` tagad atšķiras no
  `01_DZINEJS.md` pakotnes (sha augstāk). Pēc grupas noslēgšanas handoff
  pakotnes jāpārģenerē; veco pakotni nedrīkst klusi atjaunot pāri labojumam.
---

## §51 — Jauns ēnas modelis no nulles pēc lietotāja noraidījuma; Attempt 3 checker 4/4 PASS, gaida pogu (2026-10-24)

### Lietotāja lēmums un izpēte
- Attempt 2 kolāžai lietotājs neatbildēja ar apstiprinājumu, bet deva
  labojumu: ēnas modelis, kas krīt uz pelēkā fona, jāizveido no 0, jāmeklē
  internetā profesionāli piemēri un tie jāpielieto jaunajā modelī.
- Profesionālie principi, kas ņemti par pamatu: PCSS/contact-hardening —
  ēna asāka kontaktā un mīkstāka tālāk, penumbras platums atkarīgs no
  gaismas izmēra un blocker/receiver attālumiem
  (https://developer.download.nvidia.com/shaderlibrary/docs/shadow_PCSS.pdf);
  e-komercijā viena konsekventa gaismas virziena ēna (augšā-kreisi ->
  apakšā-labi), mīkstas malas, īsa/uz pamatnes tuva ēna un tumšākais
  punkts kontaktā
  (https://www.pixel-prep.com/blog/product-photography-shadows-drop-natural-reflection-guide-ecommerce);
  kontakta un metēnā ēna jābūvē kā atsevišķas komponentes
  (https://it-s.com/how-to-create-natural-product-shadows-for-ecommerce-images,
  https://pikes.ai/blog/product-photo-drop-shadows). Kalibrācija veikta
  nevis pēc rakstu gaumes, bet pret diviem iesniegtajiem Slam Jam pilniem
  kadriem ar sektoru×attāluma mērījumu.

### Mērķis skaitļos (Slam Jam pilno kadru vidējais; vidējais Δ joslās 2-4 / 4-8 / 8-14 / 14-22 / 22-35 / 35-60 px)
- E: 79.65 / 66.65 / 42.95 / 18.50 / 2.90 / 0
- S: 78.70 / 65.80 / 42.85 / 19.35 / 3.45 / 0
- W: 2.00 / 1.35 / 0.85 / 0.40 / 0.05 / 0
- N: 3.55 / 1.00 / 0.05 / 0 / 0 / 0
- Attempt 2 SE/NW agregāta RMSE pret šo mērķi bija 24.38; galvenais
  defekts nebija SE stiprums, bet W/N ambient atlikums (vidēji Δ~15
  <=40 px joslā pret parauga ~1-2).

### Jaunais modelis `studio_v1_contact_pcss`
- `loop.studio_shadow_bg`: transmisija =
  `(1 - contactAO(d)) * (1 - peak * V^gamma)`. Kontakta AO ir šaurs
  (peak 0.10, lambda 1.4 px). V ir laukuma gaismas redzamība: siluets
  projicēts 43° virzienā par 16 audekla px un izpludināts ar penumbru
  sigma(d)=0.9+0.28*d (līmeņi 0.8/1.8/3.2/5.0/7.5, log-interpolācija,
  aprēķins pusizšķirtspējā). peak=0.32, gamma=0.80; logs 42->58 px,
  pēc kura ēna ir tieši 0 (tālais fons 243; GATE_B sākas pie 90 px).
- Kalibrācija: pirmais ekstrūzijas prototips NW likvidēja, bet SE palika
  vājš (RMSE 14.68) un tika atmests. Redzamības modelis režģa meklēšanā
  deva kardinālo RMSE 1.69; izvēlētie parametri ir augstāk minētie.
- Integrēts visos ražošanas ceļos: workflow MASTER, `render_paraugs`,
  v1 master, `rebuild_master.py`, `closeup.py`. MASTER mērogā parametri
  tiek pārrēķināti ar `canvas_scale=para_scale`, lai MASTER un PARAUGS
  ēna būtu viens fiziskais lielums un GATE_R paliktu godīgs. Avotā
  mērītais leņķis renderī vairs netiek lietots (viena studijas gaisma
  katalogam); tas paliek atskaitē kā mērījums, jaunais modelis atskaitē
  ierakstīts kā `shadow_model=studio_v1_contact_pcss`, 43°, nobīde 16 px.
- Koda sha256(16) pēc integrācijas: `loop.py fe7bc60d892ca0d5`,
  `workflow_v2.py d2c84350ffcc40a8`, `rebuild_master.py a5339e97f63edc2e`,
  `closeup.py c96f11a89ccdad07`. Dūmu tests sintētiskai maskai:
  0.26 s (2000x2500), E/W=137.7x, S/N=128.7x, fons >90 px precīzi 243.
- Procesa piezīme (mana kļūda, fiksēta pirms palaišanas): paralēli
  labojumi vienā failā sacentās un daļa izmaiņu sākumā pazuda; tas tika
  noķerts ar grep/hash kontroli, labojumi atkārtoti secīgi un pārbaudīti.

### Attempt 3 — izolēta ēnas iterācija
- Pirms palaišanas A2 atskaites/hash saglabāti `output/audits/attempt2_*`.
  Palaists `--attempt 3 --rerender-saved` ar `--no-decontam` abiem
  tuvplāniem. Rezultāts: visas 12 maskas/ALPHA/PARAUGS_MASK bitiski SAME
  pret A2; mainījās tikai MASTER/PARAUGS fona ēna. Profila LUT pret A2
  arhīvu ir identisks (maks. starpība 0; atšķiras tikai paraugu
  statistikas lauki), tāpēc auduma gradācija nemainījās.
- Maker 4/4: vidēji 12.237 s/bilde, maks. 14.604 s. Checker **4/4 PASS**:
  A2 max_diff=0; B 100.0%; H 100%/100%, bad_partial=0; R fore_p99
  6/7/17/18 un bg_p99=0 visiem; T 9.741-14.604 s (<25).
- Faktiskais ēnas audits gala JPEG (pilno kadru agregāts, vidējais Δ):
  E 78.1/72.0/46.9/19.0/4.0/0; S 75.0/69.0/43.7/17.2/3.5/0;
  W 2.5/1.1/0.2/0.1/0/0; N 1.7/0.6/0/0/0/0. Kardinālais RMSE pret
  parauga agregātu = **1.85** (prototipa prognoze 1.69). Tālais fons
  (>90 px) Δ=0 ir 100.0000% visām 4 bildēm. Tuvplānos atklātās E malas
  profils 161944 ir 72.3/52.5/21.2/6.9/1.3/0; 161959 atklātās ir galvenokārt
  N/W malas, tāpēc tur apzināti paliek gandrīz tikai kontakta AO
  (N 2.4/1.2/0.2/0.1/0/0) — metēnā ēna krīt zem apģērba uz SE.
- Aģents vizuāli apskatīja A3 kolāžu, priekšpusi un 161959 pilnā izmērā:
  ēna krīt leju-labi, W/N puse ir tīra bez vecā rimhulo, neēnota gaiša
  līnija pie kontakta nav redzama, priekšmeti/oreols nav parādījušies.
  Gala E lēmums joprojām ir lietotājam ar pogām.

### Gala faili Attempt 3 (vēl nav apstiprināti; ZIP nav)
| Fails | baiti | sha256 (16) |
|---|---:|---|
| `output/paraugs/MVIMG_20261020_161746_PARAUGS_2000x2500.jpg` | 578 930 | `f14e6b0d8860261f` |
| `output/paraugs/IMG_20261020_201332_PARAUGS_2000x2500.jpg` | 620 714 | `0ff166f4b01251a3` |
| `output/paraugs/MVIMG_20261020_161944_PARAUGS_2000x2500.jpg` | 1 748 721 | `96798940b7aab798` |
| `output/paraugs/MVIMG_20261020_161959_PARAUGS_2000x2500.jpg` | 2 217 108 | `9d32fce6c0f16707` |
| `output/master/MVIMG_20261020_161746_MASTER_1to1.png` | 7 591 100 | `0789679f8054bf07` |
| `output/master/IMG_20261020_201332_MASTER_1to1.png` | 7 206 818 | `cf40e2cb4f1dba79` |
| `output/master/MVIMG_20261020_161944_MASTER_1to1.png` | 12 860 558 | `8174f21a908beca0` |
| `output/master/MVIMG_20261020_161959_MASTER_1to1.png` | 15 613 509 | `de588c5879041dc9` |
| `output/V2_KOLAZA.jpg` | 405 395 | `45ad4cafe9abfe9e` |

- Krātuve pirms šī ieraksta: `/home/user` 93M (du -sh), 96 814 978 B.
  ZIP drīkst veidot tikai pēc pogas `Apstiprināt`. Pēc apstiprināšanas:
  notīrīt `__pycache__`/diagnostiku, izmērīt du, veidot ZIP; atjaunināt
  `00_SAKU_SHEIT.md` §8 (jaunais modelis aizstāj S2 kanoniskajām izvadēm)
  un pārģenerēt handoff pakotnes, jo kods atšķiras no `01_DZINEJS.md`.
---

## §52 — Vans grupa apstiprināta; ZIP izveidots; gaida lejupielādes pogu (2026-10-24)

- Lietotājs ar pogu **Apstiprināt** pieņēma Attempt 3 kolāžu
  (`V2_KOLAZA.jpg`, sha256(16) `45ad4cafe9abfe9e`). Checker pirms ZIP:
  4/4 PASS (Attempt 3), tāpēc ZIP drīkstēja veidot.
- Pirms ZIP notīrīts `__pycache__`: krātuve 96 825 839 B -> 96 603 723 B
  (`du -sh` abos gadījumos 93M).
- `workflow_v2.py --make-zip --zip-name GALA_BILDES.zip` exit 0.
  Fails: `output/GALA_BILDES.zip`, 5 013 044 B, sha256
  `2072608b28a6ef179efc08e4cc3f2aeeb945f2fae348d77f33e0b4590c60ad74`.
  Saturs: tikai 4 gala JPG ar A3 hashiem (`0ff166f4b01251a3`,
  `f14e6b0d8860261f`, `96798940b7aab798`, `9d32fce6c0f16707`).
  Neatkarīgs `ZipFile.testzip()` = OK; ierakstu baiti atbilst failiem.
- Krātuve pēc ZIP: `du -sh /home/user` = 98M; precīzi 101 679 113 B
  (pirms šī ieraksta). Grupu vēl nedzēšam: nākamais solis ir lietotāja
  pogas `Lejupielādēju — dzēst grupu` / `Vēl nedzēst`.
- Pēc grupas noslēgšanas vēl atlicis uzturēšanas solis: atjaunināt
  `00_SAKU_SHEIT.md` §8 uz `studio_v1_contact_pcss` (apstiprināts šajā
  piegādē) un pārģenerēt `01_DZINEJS.md`/`02_ATMINA.md`, jo kods tagad
  atšķiras no vecās pakotnes (asināšana 25% + jaunais ēnas modelis).
---

## §53 — Vans grupa slēgta pēc lejupielādes apstiprinājuma (2026-10-24)

- Lietotājs ar pogu **Lejupielādēju — dzēst grupu** apstiprināja ZIP
  lejupielādi. Tikai pēc tam palaista grupas dzēšana.
- Pirms dzēšanas atrasts un izlabots `close_group.py` trūkums: tas zināja
  tikai veco kolāžas vārdu `_KOMPLEKTS_vinted_henley.jpg` un nebūtu
  izdzēsis `output/V2_KOLAZA.jpg`. Tagad sarakstā ir abi vārdi
  (`close_group.py` sha256(16) `d7bc4636af04620b`, py_compile OK).
- Dry-run uzrādīja precīzi 30 failus / 97.57 MB. Ar `--yes` izdzēsti visi
  30: 4 `uploads/` oriģināli, 4 MASTER, 4 PARAUGS, 12 maskas/ALPHA,
  4 per-stem profili, `GALA_BILDES.zip` un `V2_KOLAZA.jpg`.
  Pēcpārbaude: katra grupas stema atbilstību skaits uploads+output = 0;
  ZIP skaits output = 0.
- Neskarti paliek: kods un dokumenti, `output/report_v2*.json`,
  `output/delivery_v2.json`, `output/grade_profile_v2.json`,
  `output/audits/attempt*` tekstuālās atskaites/hash saraksti un visas
  4 Slam Jam parauga atsauces (sha256(16) `bb0e436bff3ebb42`,
  `cdbca1dd3cdd11b3`, `49fa45698c4ee120`, `669263eb8388f3a3` — tādi paši
  kā §48 inventarizācijā).
- Krātuve pēc dzēšanas (pirms šī ieraksta): `/home/user` 4.0M /
  4 015 423 B; `loop_bildes/` 916K; `uploads/` 3.1M.
- STĀVOKLIS: Vans grupa piegādāta un slēgta. Darba telpa gatava vienai
  jaunai grupai pēc §3.1 protokola. Atlikušais uzturēšanas darbs (nav
  šīs piegādes daļa): atjaunināt `00_SAKU_SHEIT.md` §8 uz apstiprināto
  `studio_v1_contact_pcss` un pārģenerēt `01_DZINEJS.md`/`02_ATMINA.md`;
  līdz tam vecās pakotnes `uploads/` ir novecojušas attiecībā pret kodu
  (asināšana 25%, jaunais ēnas modelis, close_group labojums) un tās
  nedrīkst atjaunot pāri pašreizējam kodam.

---

## §54 — Produkcijas refaktors, solis 1: git + arhīvs (2026-10-24)

- Lietotājs apstiprināja mērķi: produkcijas programmatūra; strādājam soli pa
  solim, pa vienam uzlabojumam. Pilns ceļš: `PRODUKCIJAS_PLANS.md`
  (6 soļi + ātrie labojumi; katrs solis = komits + šis reģistrs + pogas).
- Audita izejas skaitļi (solim 1 pamats): 22 `.py` / 7 116 rindas;
  `workflow_v2.py` 2 085 rindas ar `main()` 552 rindas; 1 534 rindas ārpus
  ražošanas importa grafu; `test_workflow_v2.py` nav; git nebija;
  checker importē `apply_lut` no `workflow_v2`.
- Izveidots git repozitorijs `loop_bildes/` saknē. Bāzes komits `77e9ac2`
  (tags `v2.1.0`, 38 faili, 13 375 rindas) = stāvoklis pirms jebkuras
  kustības. `.gitignore`: `__pycache__/`, `output/`, `PROGRESS.md.bak-*`,
  `*.zip`.
- Uz `archive/` pārvietoti 10 moduļi / 1 441 rinda, kurus neviens ražošanas
  fails neimportē (pārbaudīts ar grep, arī dinamiskais imports workflow ir
  tikai `find_spec`): `loop_engine.py`, `checker.py`, `cast_shadow.py`,
  `directional_shadow.py`, `real_shadow.py`, `restyle_shadow.py`,
  `shadow_studio_v2.py`, `fix_mask_holes.py`, `make_collage_vinted.py`,
  `make_zip_vinted.py`. `measure_shadow.py` apzināti paliek saknē kā
  diagnostika. Atsauces dokumentos uz arhivētajiem ir tikai vēsturiskajos
  reģistros; aktuālie komandu dokumenti (`LOOP_KOMANDAS.md`,
  `WORKFLOW_V2.md`) tos nesauc.
- Pierādījums, ka kods nav mainījies: pirms/pēc sha256 saraksti visiem 22
  `.py` — **22/22 identiski** (mainījies tikai ceļš); `py_compile` 22/22 OK.
  Ražošanas algoritmi, 00 §3.2 un §5 sliekšņi: nemainīgi.
- Blakus atradums: `python3 setup_v2.py --check` → `ready:false`
  (`/var/tmp` vide starp sesijām nav izdzīvojusi). Šim solim apstrāde nav
  vajadzīga; pirms nākamās apstrādes/testu palaišanas jāpalaiž
  `python3 setup_v2.py`.
- STĀVOKLIS: solis 1 izdarīts, gaida lietotāja apstiprinājumu solim 2
  (testi). Soļa 1 komits satur šo ierakstu; tā hash skatīt `git log`.

---

## §55 — Ātrais labojums: ISNet modeļa sha256 piespraude (2026-10-24)

- Lietotājs ar pogām izvēlējās pirms soļa 2 izdarīt ātro labojumu.
  Problēma: `setup_v2.py` modeli uzskatīja par derīgu, ja fails eksistē un
  ir >100 MB. Pretpiemērs izmērīts: līdz 104 857 600 B saīsināts modeļa
  fails veco kritēriju **izietu** (104,9 MB > 100 MB), tāpat jebkurš bojāts
  pilna izmēra fails.
- Vide pirms labojuma: `ready:false` (trūka `onnxruntime`, `rembg`, modeļa).
  Palaists `python3 setup_v2.py` (54 s, tikai `/var/tmp`): visi moduļi OK,
  modelis lejupielādēts, izmērs 178 648 008 B — identisks iepriekšējā
  sesijā validētā modeļa izmēram.
- Hash krustojums pirms piespraušanas (nevis aklu uzticība lejupielādei):
  faila MD5 `fc16ebd8b0c10d971d3513d564d01e29` == rembg 2.0.85 avota
  konstante `rembg/sessions/dis_general_use.py` 67. rindā
  (`"md5:fc16ebd8..."`). Tikai pēc tam piesprausts SHA-256
  `60920e99c45464f2ba57bee2ad08c919a52bbf852739e96947fbb4358c0d964a`.
- Izmaiņa tikai `setup_v2.py` (+42/−8 rindas): konstantes `MODEL_BYTES`,
  `MODEL_SHA256`; `_model_status()` (hashē tikai, ja izmērs sakrīt);
  `download_model()` pēc lejupielādes validē un pie neatbilstības krīt ar
  `RuntimeError`; `--check` JSON pievienoti lauki `expected_bytes`,
  `sha256`, `expected_sha256` (iepriekšējie lauki saglabāti).
- Pierādījums: `py_compile` OK; `--check` → `ready:true`, modeļa sha256 ==
  piespraude, viss pārbaudes laiks 2,48 s. Negatīvie testi ar pagaidu
  kopijām `/tmp` (pēc tam izdzēstas): saīsināts fails → `ok=False`;
  pilna izmēra kopija ar 1 apgrieztu byte (pozīcija 90 000 000) →
  sha256(16) `df616ab2e70caa91`, `ok=False`.
- Nemainīgi: visi pārējie faili (`git diff` tikai `setup_v2.py`, šis
  reģistrs un plāna atzīme); pakotņu piespraudes, algoritmi, §5 sliekšņi.
- STĀVOKLIS: ātrais labojums izdarīts; vide atkal `ready:true`. Nākamais
  plānā: solis 2 (testi) — gaida lietotāja apstiprinājumu.

---

## §56 — Testu atrastas kļūdas labojums setup_v2.py (2026-10-24)

- Rakstot soļa 2 testus, `test_missing_file` atklāja defektu §55 kodā:
  `_model_status()` hashēja failu, kad `size == MODEL_BYTES`. Trūkstošam
  failam `size=0`; ar `MODEL_BYTES=0` tā mēģināja atvērt neeksistējošu
  failu un krita ar `FileNotFoundError` (testa iznākums ERROR), nevis
  atgrieza `ok=False`.
- Smagums godīgi: ražošanas konstantē `MODEL_BYTES=178_648_008` ceļš nav
  sasniedzams; defekts ir latenta trausluma vieta (fails pazūd starp
  `stat()` un `open()` → izņēmums pārbaudes vietā).
- Labojums 1 rinda: `if exists and size == MODEL_BYTES`. Lietotājs ar
  pogām izvēlējās labot tūlīt, atsevišķā komitā pirms soļa 2 komita.
- Pierādījums pēc labojuma: pilns komplekts 46 testi → `OK (expected
  failures=1)`, 1,37 s; `setup_v2.py --check` joprojām exit 0
  (`ready:true`, īstais modelis atbilst piespraudei).

---

## §57 — Produkcijas refaktors, solis 2: testi (2026-10-24)

- Lietotājs ar pogām apstiprināja pilnu tvērumu (A vienību + B regresijas +
  C golden). Izveidots `test_workflow_v2.py` (438 rindas, stdlib `unittest`,
  0 jaunu atkarību; sandbox `pytest` versija nav piesprausta, tāpēc uz to
  nepaļaujamies). Palaišana: `python3 -m unittest test_workflow_v2`.
- Sastāvs: 46 gadījumi 13 klasēs. A: `fit_size`, rotāciju
  parsings/`apply_quarter_turn` (bezzaudējumu Pierādījums), LUT/sRGB,
  masku QA, `refine_alpha` bands invariants, `studio_shadow_bg`
  (243 tālu, asimetrija, dilšana), I/O palīgi, modeļa statusa pārbaude.
  B: asināšanas 25% + GATE_R sliekšņa 24 konstanšu sargi; decontam
  idempotence kā `expectedFailure`. C: golden `render_paraugs`
  (2000×2500, stūri 243, kodola krāsa, ēna tikai austrumos, byte-identisks
  determinisms) — bez rakstīšanas ražošanas `output/` mapēs.
- Characterization pirms testiem (izmērīts, nevis pieņemts): LUT zem ceļa
  (blend=0) bitiska identitāte 0–219, `LUT[255]=242` (noklusējumā 244);
  ēna uz sintētiska taisnstūra E kontakta Δ=80,3 pret W Δ=3,67
  (attiecība 21,9); `refine_alpha` daļējie tikai |signed|≤6,5 (band_px);
  sRGB apļceļa kļūda 2,8e-14. Mans sākotnējais plāna formulējums "neitrāla
  LUT = identitāte" kodā izrādījās nepilnīgs (filma plecs + līkne strādā
  vienmēr) — testi piesprauž patieso, dokumentēto kontraktu.
- `expectedFailure` pamats: decontam defekts reproducēts sintētiski —
  1. palaišana noņem 17 498 px (projektētais 14 px rims, pareizi),
  2. palaišana tai pašai maskai vēl 6 611 px. Defekts tagad redzams katrā
  testu palaišanā; labojums ir soļa 3 darbs.
- Blakus atradums atsevišķā komitā jau salabots (§56). Komplekta laiks
  1,37 s (mērķis bija <60 s). Fixtūras ģenerē kods ar fiksētu sēklu;
  bināru failu repo nepievieno.
- Nemainīgi: no 23 izsekotajiem `.py` hash salīdzinājums pirms/pēc rāda
  mainītu tikai `setup_v2.py` (§56 apstiprinātais labojums). Algoritmi,
  §3.2, §5 sliekšņi neskarti. ISNet maskas kvalitāte apzināti netestējas —
  tā paliek attempt/checker procedūrā.
- STĀVOKLIS: solis 2 pabeigts. Nākamais plānā: solis 3 (idempotenti posmi,
  provenance) — gaida lietotāja apstiprinājumu.

---

## §58 — Produkcijas refaktors, solis 3: masku provenance, idempotents decontam (2026-10-24)

- Lietotājs ar pogām apstiprināja variantu A: sidecars pie maskas +
  hash aizsargs; nezināmai vēsturei uzvedība kā līdz šim.
- Izmaiņa `workflow_v2.py` (+96/−2 rindas): `WORKFLOW_VERSION` 2.1→2.2;
  palīgfunkcijas `mask_provenance_path`, `read_mask_provenance`,
  `start_mask_provenance`, `append_mask_stage`, `decontam_needed`
  (tīrs lēmums); konstante `DECONTAM_PARAMS={max_px:30, tex_ratio:0.45}`,
  ko tagad padod funkcijai eksplicīti (vērtības = iepriekšējie
  noklusējumi). Āķi abās kanoniskās maskas rakstīšanas vietās (masku
  fāze + render pārrakstīšana). Posma ierakstu raksta tikai `applied`
  gadījumā: ne-pielietots decontam atkarīgs no graded attēla, tāpēc
  konservatīvi to pārrēķina, nevis piesprauž.
- Sidecars `{stem}_MASK.json`: avota sha256, faila sha256 pēc katras
  rakstīšanas, posmu ķēde ar ieejas/izejas hash. Hash nesakritība
  (masku mainījis cits rīks, piem. `closeup.py`) vēsturi anulē droši.
  `close_group.py` nemainīts: `{stem}*` šablons sidecar jau savāc.
- Testi: +6 gadījumi (`TestMaskProvenance`), bijušais `expectedFailure`
  pārrakstīts par raksturojumu (jēlā funkcija 2. reizē nogriež vēl —
  tieši tāpēc aizsargs eksistē). Komplekts: **52 testi, OK, 0 gaidāmo
  neveiksmju, 1,57 s**.
- E2E Pierādījums caur īsto CLI uz sintētiska kadra `TESTSINT_1`
  (avota sha256(16) `85cf02836efabd10`, ģenerēts, pēc mērījumiem
  izdzēsts — 9 faili / 2,80 MB ar `close_group.py`): Attempt 1 decontam
  `applied=true`, −38 887 px (projektētais 14 px rims). Attempt 2 ar
  `--rerender-saved` **bez** `--no-decontam`: decontam `skipped`
  (provenance), un 5/5 artefakti bitiski identiski Attempt 1 —
  MASK `821e472087039c8a`, ALPHA `1e3295d2754b1a1e`, MASTER
  `10bfff4349951e25`, PARAUGS `bf7ec343bb39602c`, grade profils
  `d277985272df0adf`. Pirms šā soļa Attempt 2 maska atšķirtos (§57).
- Blakus efekts godīgi: e2e pārrakstīja birstošās
  `output/report_v2_maker.json` un `output/grade_profile_v2.json`
  (tagad apraksta sintētisko verifikāciju). Vans gala skaitļi nav
  zaudēti — tie ir fiksēti §51–§53.
- Nemainīgi: `loop.py` decontam algoritms un parametri (hash
  salīdzinājums 24 izsekotajiem `.py`: mainījušies tikai
  `workflow_v2.py` un `test_workflow_v2.py`); §3.2, §5 sliekšņi;
  `--no-decontam` nozīme sākotnējai izlaišanai. Kosmētika: daži konsoles
  teksti vēl saka "v2.1"; atskaitē versija ir 2.2.
- Atlikts: grade profila provenance/config hash (solis 4). STĀVOKLIS:
  solis 3 pabeigts; nākamais plānā — solis 4 (viena konfigurācija),
  gaida lietotāja apstiprinājumu.

---

## §59 — Produkcijas refaktors, solis 4: config.toml (šaurais tvērums) (2026-10-24)

- Lietotājs ar pogām apstiprināja šauro tvērumu: parametri uz failu,
  specifikācija (audekļa izmērs, fons 243, visi §5 vārti checker pusē)
  paliek kodā un testu sardzē. Ēnas `STUDIO_*` konstantes `loop.py`
  šoreiz nepārvietotas (kandidāti solim 6).
- Jauns `config.toml`: 39 vērtības 5 sekcijās (`run` 6, `mask` 11,
  `plate` 5, `decontam` 2, `grade` 15) — visas 1:1 no iepriekšējām koda
  konstantēm/CLI noklusējumiem/inline skaitļiem (`PAD_*`, `PLATE_*`,
  `ai_mask_qa` robežas, grade līkne un asināšana 25%).
- `workflow_v2.py` (+258 pārrēķinātas rindas): `load_config()` ar stingru
  shēmas validāciju (nezināma/trūkstoša atslēga, tips, izvēles — kļūda
  ar vārdu; lasa stdlib `tomllib`, 0 atkarību); 6 CLI parametru karogu
  noklusējumi → `None`, izšķir `_resolve_args` (CLI > config);
  `WORKFLOW_VERSION` 2.2→2.3. Atskaite tagad nes `code_commit`
  (git HEAD, ar `-dirty` pie neiekomitētām izmaiņām), `config_sha256`
  un pilnu efektīvo konfigurāciju — "Attempt N" kļūst viennozīmīgs.
- Testi: +7 (migrācijas sargs: visa CFG == pirms-migrācijas literāļi;
  typo/tips/izvēle/trūkstošs fails noraidīti; CLI prioritāte; hash
  stabilitāte/jūtība) → **59 testi, OK, 1,58 s**.
- Bitiskais Pierādījums: pārģenerēts §58 sintētiskais avots (sha256(16)
  `85cf02836efabd10` — sakrīt), Attempt 1 → MASK `821e472087039c8a`,
  MASTER `10bfff4349951e25`, PARAUGS `bf7ec343bb39602c` — **visi trīs
  identiski §58 vērtībām** (kods pirms config refaktora). Mainījies tikai
  atskaites JSON (versija 2.3, `config_sha256=151c9de63ed32e82`,
  `code_commit` ar `-dirty`, jo palaišanas brīdī izmaiņas vēl nebija
  komitā — godīgs marķējums strādā). Sintētika pēc mērījumiem izdzēsta
  (9 faili / 2,80 MB; paliek 4 Slam Jam paraugi).
- Nemainīgi: `loop.py`, `checker_v2.py` un pārējie (hash salīdzinājums:
  mainījušies tikai `workflow_v2.py`, `test_workflow_v2.py`; pievienots
  `config.toml`); algoritmi, §3.2, §5 sliekšņi.
- STĀVOKLIS: solis 4 pabeigts. Nākamais plānā: solis 5 (neatkarīgs
  checker) — gaida lietotāja apstiprinājumu.

---

## §60 — Produkcijas refaktors, solis 5: neatkarīgs checker (2026-10-24)

- Lietotājs ar pogām apstiprināja pilno tvērumu. Pirms soļa checker
  importēja no maker: `apply_lut` (A2 vārtu kodols), `apply_quarter_turn`,
  un no `loop`: `BG_GRAY`, `GARMENT_FILL_W/H`, `OUT`, `SRC_DIR` — kopīga
  kļūda vai konstanšu drifts būtu izmainījis abas puses vienādi un vārti
  paliku zaļi.
- Izmaiņa tikai `checker_v2.py` (+55/−9 neto): lokāls `_apply_lut`
  (tīra NumPy indeksēšana; LUT rindas paliek DATI no grade profila,
  ar formas validāciju), lokāls `_quarter_turn_cw` ar savu virzienu
  tabulu un to pašu validāciju, spec konstantes `SPEC_BG=243`,
  `SPEC_FILL_W/H=0.74/0.78`, ceļi no repo izkārtojuma. Importa Pierādījums:
  svaigā interpreterī pēc `import checker_v2` — `workflow_v2` un `loop`
  NAV ielādēti (`paper_leak` ir; tas maker moduļus nevelk).
- Nemainīguma Pierādījums divos līmeņos: (1) testi — LUT un pagriezieni
  bitiski ekvivalenti maker realizācijām uz nejaušiem datiem (paliek
  komplektā kā krustsargs), spec konstantes == maker pašreizējās, AST
  tests aizliedz maker importus checker failā; (2) e2e — vecais un
  jaunais checker uz tiem pašiem sintētiskajiem (`TESTSINT_1`, avots
  `85cf02836efabd10`) Attempt 1 failiem: ALL_PASS abiem; rekursīvs
  atskaišu salīdzinājums **136 lapu laukos: 0 atšķirību** (izslēgts tikai
  checker mērītais `seconds`). Sintētika pēc tam izdzēsta (9 faili /
  2,80 MB).
- Testi: +5 → **64 testi, OK, 1,67 s**. Sliekšņi un vārtu loģika nav
  mainīti ne par vērtību (hash audits: mainījušies tikai `checker_v2.py`
  un testi). Kosmētika nemainīta: konsoles teksti vecajā stilā "V2.1".
- Paliekošs, apzināts izņēmums: `paper_leak` imports informatīvajiem
  L vārtiem (pass=None) — tas nav maker atkarība lēmumu ceļā.
  Nākamais plānā: solis 6 (monolīta dalīšana) — gaida apstiprinājumu.

---

## §61 — Solis 6.1: `engine/config.py` (2026-10-24)

- Lietotājs apstiprināja visus soļa 6 apakšsoļus secīgi, katru savā
  komitā ar pilnu Pierādījums komplektu. Izveidota pakotne `engine/`;
  `workflow_v2.py` paliek CLI ieeja un fasāde (re-eksportē vārdus).
- Pārvietots nemainot ķermeņus: config shēma/ielāde (`load_config`,
  `CFG`, `CONFIG_PATH` — modulis tagad `engine/`, tāpēc ceļš
  `parents[1]`; vērtība nemainīga), `_resolve_args`,
  `_effective_config`, `_config_sha256`.
- Pierādījums: AST hash visām 55 funkcijām pirms/pēc — 0 atšķirību;
  64 testi OK; `--help` izvade identiska; TESTSINT e2e
  MASK/MASTER/PARAUGS == §58 hash. STĀVOKLIS: turpinu ar 6.2.

---

## §62 — Solis 6.2: `engine/infra.py` + `engine/provenance.py` (2026-10-24)

- Pārvietots: infra 16 funkcijas + rotāciju globāli; provenance 6
  funkcijas + `MASK_PROVENANCE_VERSION`/`DECONTAM_PARAMS`;
  `WORKFLOW_VERSION` pārcelts uz `engine/config.py`, lai `preflight`
  varētu dzīvot infra bez riņķa importa. Ķermeņi nemainīti.
- Vienīgā testa korekcija (plānā paredzēta): `rotation_for` tests vairs
  nepārsien `ROTATIONS_CW` atsauci, bet mutē vārdnīcu — tā, kā to dara
  visi ražošanas ceļi (`update()`); testa apgalvojumi identiski.
- Pierādījums: AST hash 55/55 bez atšķirībām; 64 testi OK; `--help`
  identiska; e2e == §58 hash. STĀVOKLIS: turpinu ar 6.3.

---

## §63 — Solis 6.3: `engine/grade.py` (2026-10-24)

- Pārvietotas 6 funkcijas (sRGB pārveides, `build_lut`,
  `compute_grade_profile`, `apply_lut` u.c.), ķermeņi nemainīti.
- Pierādījums: AST hash 55/55 bez atšķirībām; 64 testi OK; `--help`
  identiska; e2e == §58 hash. STĀVOKLIS: turpinu ar 6.4.

---

## §64 — Solis 6.4: `engine/masks.py` (2026-10-24)

- Pārvietotas 14 funkcijas (ISNet workeri, QA, pad/plate/closeup) +
  `TMP_SOFT`. Vienīgās ķermeņa izmaiņas visā solī 6 līdz šim: divās
  vietās workera pašizsaukumā `__file__` → `str(ENTRY_SCRIPT)`
  (fasādes fails), jo modulis vairs nav CLI ieeja.
- Pierādījums: AST hash — atšķiras tieši `{run_isnet, run_isnet_auto}`
  (plānotais izņēmums), pārējās 53 identiskas; 64 testi OK; `--help`
  identiska; e2e == §58 hash (īstais ISNet workers gāja caur jauno
  ENTRY_SCRIPT ceļu). STĀVOKLIS: turpinu ar 6.5.

---

## §65 — Solis 6.5: `engine/render.py` + `engine/report.py`; solis 6 pabeigts (2026-10-24)

- Pārvietots: render (`render_one`, `write_collage`, `NO_DECONTAM`) un
  report/deliver (`_persist_report`, `make_zip`, meta, ceļu
  konstantes). `_selected_files` apzināti palika fasādē pie `main`
  (CLI atlases loģika). Trešais un pēdējais plānotais AST izņēmums:
  `_code_commit` repo ceļš `parents[1]`.
- Pierādījums: AST hash — atšķiras tikai `_code_commit`; 64 testi OK;
  `--help` identiska oriģinālam no soļa 6 sākuma; e2e == §58 hash;
  visi saknes moduļi importējas (`closeup`, `rebuild_master`,
  `checker_v2` ieskaitot).
- Soļa 6 kopbilde: `workflow_v2.py` 2 327 → 741 rinda (CLI + fasādes
  re-eksporti + `main`); `engine/` 8 faili / 1 759 rindas. Visos 5
  apakšsoļos: funkciju ķermeņi identiski (3 dokumentēti izņēmumi:
  2× ENTRY_SCRIPT, 1× repo ceļš), e2e izvade bitiski nemainīga.
- STĀVOKLIS: produkcijas refaktora plāna soļi 1–6 pabeigti. Atlikuši
  ātrie labojumi (00 §8, atjaunot.py dublikāts, lēmums par .md
  pakotnēm) un atliktais `main()` fāžu dalījums.

---

## §66 — Ātrais labojums: 00 dokumenta sinhronizācija ar kodu (2026-10-24)

- Lietotājs ar pogām izvēlējās 00 §8 atjaunināšanu. Mainīta tikai
  kanoniskā `HANDOFF/00_SAKU_SHEIT.md` (+129/−106 rindas diff);
  `uploads/00_SAKU_SHEIT.md` apzināti nemainīta (lietotāja fails;
  abas pirms tam bija identiskas, sha256(16) `5d914b64b8a17159`).
- §8 pārrakstīta uz `studio_v1_contact_pcss` (formula, 43°/16 px,
  σ(d), 42→58 px logs; kalibrācija 2 paraugi, RMSE 1,85; **holdout
  validācija vēl nav** — ierakstīts godīgi). Vecie modeļi markēti kā
  arhīvs; `measure_shadow` "kodola Δ" brīdinājums pārnests.
- Sinhronizētas arī vietas, kuras §8 maiņa padarīja klaji nepatiesas
  vai bīstamas: versijas rinda; §2 (vairs neliek atjaunot vecās
  pakotnes pāri kodam); §6.1 failu tabula (`engine/`, `config.toml`,
  testi, `archive/`); §6.2 testu komanda (64, ne 8); §7 stāvoklis
  (aktīvas grupas nav; Vans pabeigts; refaktors pabeigts); §12 karte;
  §14 pakotņu statuss + konstatējums, ka `izveidot_pakotni.py` darba
  telpā nav; §15 ēnas rinda; Pielikuma B pašpārbaude (tagad git +
  unittest + setup, izpildīta: visi punkti zaļi).
- Nemainīti: §3 dzelzs noteikumi un §5 vārti (sinhronizācija tos
  neskāra — pārbaudīts ar diff tvērumu: tikai dokumentācijas fails,
  šis reģistrs un plāna atzīme). Kods: 0 izmaiņu; 64 testi pirms
  komita OK.
- Atlikuši ātrie labojumi: `atjaunot.py` dublikāts; lēmums par `.md`
  pakotņu likteni; atliktais `main()` fāžu dalījums.

## §67 — Jauna grupa fiksēta: Uniqlo balts vafeļu Henley, L (2026-10-24)
- §3.1 starta protokols ievērots: vispirms tikai inventārs + poga
  "Vai šīs ir visas šīs grupas bildes?" → lietotājs: "Jā, šīs ir visas".
- Avoti (5 faili, 16 417 263 B kopā; EXIF orientācija visiem = 1;
  sha256(16) iekavās):
  - `PXL_20261022_124309570.PORTRAIT.ORIGINAL.jpg` — priekšpuse,
    3072×4080, 2 837 394 B (`87c48307c90020be`)
  - `PXL_20261022_124322251.PORTRAIT.ORIGINAL.jpg` — kakla izgriezuma
    un pogu tuvplāns, 4080×3072, 3 900 325 B (`55871f43852ab782`)
  - `PXL_20261022_124339475.PORTRAIT.ORIGINAL.jpg` — apakšmalas un
    aproču tuvplāns, 4080×3072, 3 842 887 B (`bca8fd008986640a`)
  - `PXL_20261022_124406358.PORTRAIT.ORIGINAL.jpg` — birkas tuvplāns
    (UNIQLO, L, MADE IN India), 4080×3072, 2 424 361 B (`378ca503ba0b5b34`)
  - `PXL_20261022_124651636.PORTRAIT.ORIGINAL.jpg` — mugura, 3072×4080,
    3 412 296 B (`ed31840d18ef966c`)
- Rotācijas — lietotāja lēmums ar pogām: kakla tuvplāns CW 270°
  (izgriezums augšā); birka BEZ pagriešanas (noraidīts ieteiktais
  CW 90° — teksts paliek vertikāls); apakšmala/aproces CW 90°.
- Preflight notvēra kļūdu PIRMS apstrādes: īsā atslēga `322251:270`
  neatbilst, jo stems beidzas ar `.PORTRAIT.ORIGINAL`, tādēļ
  `stem[-6:]` = "IGINAL" (veco grupu stemi beidzās ar cipariem un
  īsais ceļš strādāja). Ar pilniem stemiem: `rotation_cw` 270/90
  reģistrēti, izmēri pēc pagriešanas 3072×4080; `ready:true`,
  0 problēmu. Atlikums (nav labots): `--rotate` klusi ignorē
  neatbilstošu atslēgu — kandidāts vēlākam mazam labojumam ar
  brīdinājumu/validāciju.
- Vide pirms starta: `setup_v2.py --check` `ready:true`, modeļa
  SHA-256 sakrīt; `python3 -m unittest test_workflow_v2` 64 OK (1.59 s).
- Krātuve: 5 434 991 → 22 515 898 B (pēc augšupielādes un id lapas;
  limits 100 MB).

## §68 — Henley Attempt 1: 4/5 gatavas, birkas kadrs STOP (2026-10-24)
- Maker (60.3 s siena; vidēji 12.28 s/bilde pabeigtajām, maks. 15.23 s):
  - priekšpuse `124309570`: isnet, segums 0.4674, slamjam — done
  - mugura `124651636`: isnet, segums 0.5141, slamjam — done
  - kakla tuvplāns `124322251` (CW 270): isnet_pad_retry, segums
    0.7679, original — done
  - apakšmala/aproces `124339475` (CW 90): isnet_pad_retry, segums
    0.7062, original — done
  - birka `124406358`: ISNet segums 0.0501 (fragments) → pad retry
    0.0462 (noraidīts) → plāksne segums 0.022 (noraidīts) →
    `needs_review`, `refused_no_trusted_mask`. Auto-sēklu GrabCut ceļa
    ražotnē nav (dzēsts 2026-10-22) — STOP ir apzināts dizains.
- Neatkarīgais checker: **4/4 PASS** (11 pass-lauki katram, 0 FAIL);
  birka skaitās kā nepabeigta meta (checker exit 2).
- Diagnoze (mērīta, kods nemainīts): tekstūras signāls birkas kadrā
  PASTĀV — lokālā L* std medianas papīrs/audums = 2.07/7.06 (3.4x)
  ražotnes iestatījumā (pusizmērs, logs 25); mēroga slaucīšana
  0.25–0.5 × logi 15/25/41 dod 2.9–5.4x. Kritiens ir `plate_segment`
  Otsu slieksnī: tas izvēlējās 13.73 — VIRs auduma medianas (7.06),
  jo E sadalījumu izkropļo retie ļoti augstie maksimumi (birkas melnā
  druka, vīļu ēnas) un vafeļu šūnu plaknes ir zemas enerģijas. Maska
  paturēja tikai 2.2 % augstākās enerģijas kores (fg_med 21.5).
  L* krāsa gandrīz neatdala (papīrs 58.3, audums 63.9) — tekstūra ir
  vienīgais signāls, bet pietiekams.
- Krātuve pēc Attempt 1: 80 760 141 B (MASTER PNG 9.0–15.4 MB gab.).
- Blakus atradums: `code = stem[-6:]` sēklu bibliotēkas atslēga šīs
  grupas stemiem ir "IGINAL" (tas pats `.PORTRAIT.ORIGINAL` gals,
  kas §67 lauza `--rotate` īsās atslēgas) — šai grupai nekaitē
  (sēklu nav), bet jāfiksē kopējā mazā labojumā.

## §69 — Plate ceļa divi mērīti labojumi birkas kadram (2026-10-24)
- Lietotājs ar pogām apstiprināja: (a) labot plate slieksni ražotnē,
  (b) pielikt QA `bg_inside` papīra krāsas nosacījumu. Neviens
  skaitliskais vārtu slieksnis nav mainīts.
- Labojums 1 (`plate_segment._detect`): ja Otsu maskas segums
  < `DETECT_COVER_FLOOR=0.25` (tā pati grīda, ko QA tāpat prasītu),
  slieksni pārrēķina no enkuriem — ģeometriskais vidējais starp
  papīra E (malas gredzena gludā daļa) un auduma E (p90). Uz birkas:
  2.24 un 9.38 -> 4.58; segums 0.0219 -> 0.8696 (Otsu 13.73 bija virs
  auduma mediānas 7.06; sadalījuma asti nosaka birkas melnā druka un
  vīļu ēnas, E maks. 31.3). Info vārdnīcai pievienoti `thr` un
  `thr_method` (`otsu`|`anchored_fallback`); vecais `otsu` saglabāts.
- Regresija = 0: kalibrācijas kadriem fallback neieslēdzas un
  `plate_mask` binārās maskas ir bitiski identiskas pirms/pēc —
  apakšmala `f51f9f8941232a33`, kakls `81f504ab9524c0f8`.
- Pēc 1. labojuma QA birku joprojām noraidīja: `bg_inside`
  0.0284 > 0.02. Karte + komponentu mērījums pierādīja: karogotie
  66 383 px ir vafeļu rindu ēnu līnijas un vīle — tūkstošiem sīku
  plankumiņu (lielākais 3 965 px), L* mediāna 66.8, kamēr īstais
  papīrs ārpus maskas ir L* 49-61. "Gluds + plakans" bez krāsas
  makro kadrā audumu sauc par fonu.
- Labojums 2 (`engine/masks.plate_mask`): `bg_like` papildus prasa
  papīra L* logu `L_TOL` (-14..+8) ap izmērīto papīra līmeni (tas
  pats logs, ko `_keep_garment` jau lieto papīra/krokas dalījumam);
  ja papīra līmenis nav izmērāms, paliek vecais skaitījums. Birka:
  0.0284 -> 0.0145, accept False -> True. Kontroles: apakšmala
  0.0067 -> 0.0053, kakls 0.0024 -> 0.0007 (abi paliek accept=True,
  binārās nemainītas). QA vārdnīcai pievienots `paper_L` (birkā 59.0).
- Sintētiskās kontroles (tagad unit testi): vāja tekstūra +
  ekstrēms bloks reproducē Otsu kritienu (20.8) un fallback atgūst
  segumu 0.8275 (patiesais 0.8125); papīra krāsas pleķis auduma vidū
  joprojām tiek noraidīts (`bg_inside` 0.1719), gaiša gluda "birka"
  netiek karogota (0.0, accept=True). Testi: 64 -> **69 OK** (2.60 s).

## §70 — Attempt 2 + GATE_P precizējums; checker 5/5 PASS (2026-10-24)
- Attempt 2 (`--resume`, 30.5 s): 4 gatavās maskas atpazītas pēc
  SHA-256; tikai birka segmentēta no jauna — `plate_texture`,
  segums 0.8693 (iekšmala 0.69, ārējā 0.533, bg_inside 0.0145).
  5/5 pabeigtas, 11.08 s/bilde. Krāsu profils nedaudz nobīdījās
  (fons [131.0, 128.5, 127.5] -> [132.0, 129.0, 128.0], WB R
  0.974457 -> 0.969584), jo kopīgais LUT tagad rēķināts no visām
  piecām bildēm, kā §3.2 prasa; tāpēc 4 iepriekšējie kadri ar jauno
  LUT pārrenderēti (hashi mainīti, maskas nē).
- Pirmais checker piegājiens: 4/5. Birka krita `GATE_P_paper_at_border`
  (3 reģioni, 30 537 px). Lokalizācija pierādīja viltus trauksmi:
  visi reģioni ir vafeļu rindu gludie ieloki un aproces josla pie
  kadra malām, `enclosed_by_fg=True`, dE pret papīru 9.6-13.9
  (īstam papīram ~0-3); detektora `garment_fpr=0.196`, atdalāmība
  0.52 (paša veerdikts "marginal", tāpēc GATE_L ir tikai advisory).
  Pilnkadra makro kadram "pieskaras malai" nav informācijas.
- Lietotājs ar pogām apstiprināja GATE_P precizējumu. Diskriminators
  PIRMS koda maiņas pierādīts uz sintētikas: īsts ķīlis (maska
  pārskrien papīrā līdz malai) -> `enclosed=False`, dE 0.46; gluda
  auduma josla līdz malai -> `enclosed=True`, dE 12.89.
- Izmaiņa (`checker_v2.gate_p_verdict`): bloķē tikai malas reģionus,
  kas NAV audumā ieslēgti; ieslēgtie tiek ziņoti
  (`enclosed_border_regions`/`_px`). Pārējiem 4 kadriem spriedumi
  nemainās (tiem malas reģionu nebija). 5 jauni testi (3 vienību +
  2 integrācijas caur `leak_probe`) -> **74 OK**.
- Checker otrais piegājiens: **5/5 PASS**, exit 0; birkas GATE_P ziņo
  3 ieslēgtos reģionus / 30 537 px. Gala PARAUGS sha256(16):
  priekšpuse `76ff012e1750c2d3`, kakls `c4e67398867278e5`,
  apakšmala `202452de832866e6`, birka `cde7d9d6131e46aa`,
  mugura `e317d70c804d2882`; grade profils `771e8e148a2a8e68`.
- Krātuve pirms piegādes: 96 765 843 B (jāatbrīvo vieta ZIP dublikātam;
  kandidāti: tmp_id diagnostika, output/audits saturu pārbaudīt).

## §71 — Henley piegāde: lietotājs apstiprināja, ZIP izveidots (2026-10-24)
- §3.4 plūsma: kolāža parādīta -> poga "Apstiprināt" (checker 5/5 PASS
  jau bija pirms rādīšanas).
- Vietas jautājums: ZIP prasīja +8.1 MB pie 97.4 MB. Lietotājs
  precizēja: Arena vienas sarunas krātuves griesti ir 128 MB;
  rīcība kā iepriekš — pēc lejupielādes dzēšam ZIP (close_group).
  MASTER pārspiešana/dzēšana NAV darīta. Pīķis ar ZIP: 104 341 065 B
  (virs 00 §3.5 iekšējā 100 MB darba limita, zem 128 MB griestiem;
  pēc grupas slēgšanas gaidāms atkal ~5-6 MB). Apsvērumam citreiz:
  00 §3.5 limita saskaņošana ar 128 MB (lietotāja lēmums).
- `output/GALA_BILDES.zip`: 7 997 787 B, sha256
  `bebe8337e23203890ff015bb83b6cc91e18ae8cf072f53eb0b11746f87ab0b27`.
  Saturs = 5 PARAUGS; katra faila SHA-256 ZIP iekšienē salīdzināts
  ar §70 checker apstiprinātajiem — 5/5 atbilst.
- tmp_id diagnostika (id lapa, kartes, hasu saraksti, 1 012 177 B)
  pēc apstiprinājuma izdzēsta; tās skaitļi saglabāti §67-§70.
- Gaida pogu "Lejupielādēju — dzēst grupu" -> tad close_group par
  visiem 5 stemiem (oriģināli, maskas/alpha/provenance, MASTER,
  PARAUGS, kolāža, ZIP) un beigu mērījums.

## §72 — Henley grupa slēgta un iztīrīta (2026-10-24)
- Lietotājs: "Lejupielādēju — dzēst grupu". `close_group.py` vispirms
  dry-run (42 faili, saraksts pārbaudīts acīm: tikai 5 grupas stemi
  + ZIP + kolāža), tad `--yes`: izdzēsti visi 42, atbrīvoti
  98.21 MB. `V2_KOLAZA.jpg` dzēšana iekļauta (labojums no Vans
  slēgšanas strādā).
- Krātuve: 104 341 065 -> **6 250 491 B**. Palikušie `output/`
  artefakti: maker+checker atskaites, `delivery_v2.json` (ZIP
  manifests ar failu SHA-256), grade profils, `audits/` (attempt 1/2
  atskaišu kopijas un hasu saraksti); master/paraugs/masks tukšas.
- `uploads/`: tikai `00_SAKU_SHEIT.md`, sasaldētās `01_DZINEJS.md`,
  `02_ATMINA.md` un 4 Slam Jam paraugi (hashi nemainīti:
  `bb0e436b…`, `cdbca1dd…`, `49fa4569…`, `669263eb…`). Git tīrs;
  grupas komiti: `5f0b0e0` (§67-§68), `89a0c87` (§69), `21953ee`
  (§70), `d1e4e1f` (§71), `ae0545a` (QA §50).
- Ražotne pēc grupas ir stiprāka nekā pirms tās: 74 testi (bija 64);
  plate ceļš vairs nekrīt uz ekstrēmas E astes; `bg_inside` atpazīst
  papīru pēc krāsas, ne tikai gluduma; GATE_P izšķir ķīli no audumā
  ieslēgtiem ielokiem. Sekojošie numuri: PROGRESS §73, QA §51.
- Zināmie sīkie atlikumi (nebloķē nākamo grupu): `--rotate` un
  sēklu bibliotēkas īsās atslēgas klusām nesakrīt stemiem ar
  `.PORTRAIT.ORIGINAL` galu (§67); 00 §3.5 100 MB limits pret
  128 MB griestiem (§71) — abi gaida lietotāja vārdu.

## §73 — Studiju žurnāls STUDIJAS.md izveidots (2026-10-24)
- Pēc lietotāja lūguma uzsākta sistemātiska pašizglītošanās darba
  jomā. Godīga atruna, kas pasniegta arī lietotājam: zināšanas
  saglabājas tikai kā pieraksts (`STUDIJAS.md`), tāpēc tas ir
  pastāvīgs projekta dokuments, ne sarunas piezīme.
- Saturs: izmērāmi "absolvēšanas" kritēriji (galvenais: 3 grupas
  pēc kārtas bez koda labojumiem), moduļi M1-M7 (Otsu sadalījumi,
  COD/tekstūras mērogi, matting/dekontaminācija, malas mērīšana
  Boundary IoU+Grad, krāsu konstante/ΔE2000, ēnas/harmonizācija,
  pārizlase/asināšana) ar literatūras atsaucēm, 7 kandidāt-
  eksperimenti E1-E7 (neviens nav atļauja mainīt kodu bez pogas)
  un KPI tabula no divām piegādātajām grupām.
- Asākais secinājums: mūsu vārti mēra maskas īpašības, bet ne
  malas precizitāti pret patiesību; lētākais nākamais zināšanu
  solis ir sintētisks zināmas-patstiesības etalons (E4) bez
  ražošanas izmaiņām. Kods šajā solī: 0 izmaiņu.

## §74 — Jauna grupa fiksēta: zila metāliska pufjaka uz koka grīdas (2026-10-24)
- §3.1 protokols: inventārs + poga -> "Jā, šīs ir visas — sāc darbu".
- Avoti (4 faili, 49 434 216 B; visi 3072×4096, EXIF orientācijas nav):
  - `IMG_20261015_121349.jpg` — priekšpuse (apakšā kadrā pēda),
    12 988 550 B (`a2c830f71e9daa1f`)
  - `IMG_20261015_121740.jpg` — mugura, 14 537 778 B (`3880993a4a0ceca4`)
  - `IMG_20261015_122109.jpg` — atvērta jaka: odere + birka (Mohito),
    slīps kadrs ar sienu/mēbeli, 10 601 088 B (`7bed43a6559cbb0a`)
  - `IMG_20261015_122248.jpg` — slīps kadrs: kabata/piedurkne,
    11 306 800 B (`18fef3be56ef7a2f`)
- ATKĀPE NO PARASTĀ UZSTĀDĪJUMA: fons ir koka grīda ar spēcīgām
  krītošām ēnām, ne balts papīrs. Pirms Attempt 1 pārbaudīts kodā:
  `compute_grade_profile` fona paraugu filtrē (sat <= 38, attālums
  no maskas > 18) un mēra hromu; pie `bg_chroma > wb_chroma_max
  (0.18)` WB kļūst neitrāla automātiski (koda komentārs šo gadījumu
  — "koka grīda, zilā audumā -4.9 b*" — apraksta no agrākas
  pieredzes). Prognoze ielīmēta pirms palaišanas: profils ziņos
  `wb_trusted: false`. Citi riski: apmales retry polsterē ar fona
  krāsu; plate pieņem gludu fonu (koks ir teksturēts); metālisks
  spīdums malās.
- Vide: sesijas sākumā `setup --check` atkal `ready:false`
  (/var/tmp zudums starp sesijām, kā iepriekš); `setup_v2.py`
  58 s, pēc tam ready:true, modeļa SHA-256 sakrīt; 74 testi OK.
  Preflight ready:true, 0 problēmu.
- Krātuve: 6 389 384 -> 56 134 214 B (ar tmp_id lapu). Pīķis pēc
  Attempt 1 jāvēro: avoti vien ir 49.4 MB.

## §75 — Pufjakas Attempt 1: pilnie kadri PASS, slīpie kadri ārpus instrumentārija (2026-10-24)
- Maker 4/4 (10.77 s/bilde). Profila prognoze no §74 piepildījās:
  fons [180, 173, 159], `wb_trusted: false`, WB=[1,1,1],
  ekspozīcija 1.059829 — krāsa no koka nav vilkta.
- Checker 2/4 PASS: priekšpuse `121349` un mugura `121740` abi
  ALL_PASS (arī vizuāli kolāžā tīri; pēda kadrā pazudusi līdzi fonam).
- `122109` (odere, slīps): GATE_C silhouette_fill 0.4058 < 0.55.
  Pārklājums parāda īstu defektu, ne vārtu kaprīzi: retry maska
  (segums 0.2841) satur tikai jakas fragmentus; lieli paneļi
  (apakšējais centrs, kreisā puse ar spiedpogām) ārpus tās.
- `122248` (kabata, slīps): GATE_C iekšējs caurums 576 px. Pārklājums:
  maska zaudē rāvējslēdzēja kreiso joslu un kabatas kreisos paneļus,
  un apakšmalā pārskrien uz grīdas. Abi GATE_E (vizuāli) arī krīt.
- Offline mērījumi (kods nemainīts), kāpēc esošie glābšanas ceļi te
  nestrādā: papīra krāsas novērtējums uz koka dod (52,59,51) un
  (37,34,41) — pad-retry polsterē ar šo krāsu un tā sargi
  (overflow/uncovered ~0) zaudē nozīmi. Pad slaucīšana: 0.35 ->
  segums 1.0 (viss kadrs), 0.9 -> 0.277/0.828, 1.6 -> 0.040/0.001.
  Plate: segums 0.998/0.997 — koka dzīslojums tekstūras E kartē ir
  "audums" (pareizi noraidīts). Secinājums: papīram būvētais
  instrumentārijs (ISNet konteksts, papīra polsterējums, tekstūras
  slieksnis) slīpos kadrus uz koka segmentēt nevar; pilnie kadri
  iziet, jo siluets ir slēgts un ISNet to redz kā objektu.
- Krātuve pēc Attempt 1: 108 364 926 B.
- STUDIJAS KPI rindai: Attempt 1 checker 2/4; koda labojumu pagaidām
  0 (lēmums lietotājam: piegādāt 2 / pārfotografēt uz papīra /
  būvēt krāsu-attāluma ceļu kā atsevišķu soli).

## §76 — Chroma rezerves ceļš uzbūvēts (engine/chroma.py, workflow 2.4) (2026-10-24)
- Lietotāja lēmums (§75 poga): būvēt krāsu-attāluma ceļu kā atsevišķu
  soli. Prototips #1 izgāzās izmērāmi: malas gredzena (2%) k-means
  paletē nonāca pats apģērbs (centrs b*=-32.5), jo slīpos kadros jaka
  pieskaras kadra malām -> segums 0.0/0.0005. Prototips #3 (sēklas no
  ISNet: kodols = FG palete; malas gredzens MINUS FG-līdzīgie = BG
  palete; tuvākā palete + plūdu princips) uz abiem slīpajiem kadriem:
  min. savstarpējais palešu dE 24.0/23.0; sēklu pašu/citā mediānas
  5.4-6.2 pret 35-42; pēc clean segums 0.7837/0.7777, fill
  0.9184/0.8238, 0 caurumu >=400 px; pārklājumi `tmp_id/chroma3_*.jpg`
  vizuāli seko kontūrai.
- Ražotne: jauns `engine/chroma.py` (deterministiska mediān-griezuma
  palete, bez RNG; dE76 kartes gabalos; QA iekšā: palešu atstarpe,
  sēklu robežas, divdomīgo pikseļu daļa, strukturālais veselums) +
  `structural_qa` (tās pašas 4 īpašības, ko checker GATE_C). Parametri
  `config.toml [chroma]` (12 gab.), workflow 2.3 -> 2.4.
- Integrācija (`workflow_v2.py`): chroma ir PĒDĒJAIS ceļš divās
  vietās — (a) pēc plate noraidījuma pirms STOP-eskalācijas;
  (b) strukturāls trigeris: jebkura ceļa kandidāts, kas pirms
  saglabāšanas neiztur `structural_qa`, mēģina chroma; ja chroma
  sevi noraida, kandidāds paliek un checker lemj (nekas netiek
  atvieglināts). Atskaitē: `chroma_qa`, `pre_chroma_structural`,
  metode `chroma_seeded`.
- Testi: +5 sintētiski (atgūst ISNet zaudētu paneli, IoU >= 0.93;
  noraida pārplūdes joslas iekšpusi; noraida, ja apģērbs==fons krāsā;
  noraida bez sēklām; palete deterministiska; structural_qa caurums/
  fragmenti). Kopā 79 OK; TESTSINT zelta hashi nemainījās (ceļš
  neiedarbojas, kur vecā ķēde strādā).
- Nākamais: Attempt 2 visai grupai + checker. Prognoze: pilnie kadri
  paliek `isnet`; abi slīpie pārslēdzas uz `chroma_seeded`.

## §77 — Attempt 2: checker 4/4, bet acs atrod defektu (2026-10-24)
- Maker 4/4 (12.64 s/bilde, maks. 17.03 s). Prognoze no §76
  piepildījās precīzi: pilnie kadri palika `isnet` ar identisku
  segumu (0.4746/0.5404); abi slīpie caur strukturālo trigeri
  pārslēdzās uz `chroma_seeded` (122109: pirms fill 0.4058 ->
  segums 0.7851, min_cross_dE 24.13; 122248: pirms caurums 576 px
  -> segums 0.7777, min_cross_dE 22.97). Profils nemainīgs:
  [180,173,159], WB [1,1,1], ekspozīcija 1.06.
- Checker: 4/4 ALL_PASS.
- BET vizuālā pārbaude (GATE_E) atrod to, ko vārti neredz: 122248
  zem piedurknes gala maskā palicis grīdas pleķis ēnā
  (~240x140 px PARAUGS mērogā). Izmērīts: pleķa Lab mediāna
  [6.5, 3.2, 2.6]; tuvākais FG centrs (auduma tumšākā kroka
  [5.7, 0.8, -4.1]) 7.2, tuvākais BG centrs 16.7 — dziļā ēnā koks
  un audums abi ir gandrīz melni neitrāli; krāsa viena pati šo
  līci neatšķir. 122109 vizuāli tīrs.
- Akls ceļš fiksēts: "sēklu pretrunas" likums (sēklu nepiespiež, ja
  paletes to sauc par otru klasi) uz īstajām bildēm deva d0 px, un
  sintētikā mehānismu apiet paletes piesārņojums (pārplūde nozog
  FG centru [28, 6, 15.3]) — labojums un tests atcelti kā
  nepierādīti. Krātuve 125 965 537 B (masteri 59.4 MB) — tuvu
  128 MB griestiem, pēc grupas slēgšanas atbrīvosies.
- STUDIJAS KPI: grupa sākta ar A1 2/4; koda labojums §76 bija
  vajadzīgs (sērija "3 grupas bez labojuma" paliek 0), bet tas ir
  vispārīgs ceļš + trigeris, ne ielāps vienai bildei; 79 testi OK.
- Lēmums lietotājam par pleķi: pieņemt / operatora griezums /
  piegādāt 3 bildes / tekstūras izšķīrējs kā atsevišķs solis.

## §78 — Tumšās zonas izšķīrējs chroma ceļā (workflow 2.5) (2026-10-24)
- Lietotāja lēmums (§77 poga): algoritmisks risinājums, ne rokudarbss.
  Mērījumi pirms koda: lokālā std tekstūra līci NEatdala (pleķis E7
  med 0.91 pret tumšu audumu 2.38, bet p25 0.93 — sadalījumi
  pārklājas); hroma tumšajā zonā atdala labāk (b* med: pleķis +1.9,
  audums -9.4, grīda +9.9), bet BG paletē dziļās ēnas parauga nav —
  sēklu atlase (dF>=18) to bija izslēgusi. Tāpēc mehānisms nav tīra
  tekstūra, bet trīs signālu summa: tumšās paletes + tekstūras vārti
  + topoloģija (plūdi caur nedrošo zonu sasniedz tikai līčus).
- Ražotne: `engine/chroma.py._dark_uncertain` — tumšās (L*<=25)
  paletes no tumšajām sēklām (fona puse: zema alfa + nokrāsa tuvāk
  BG paletei), centru savstarpēja attīrīšana (sakrīt < 8 dE = ārā),
  nedrošs = tumšs & lauks < 5 & E7 < 1.5x fona ēnas mediānas.
  Plūdi iet caur nedrošo zonu; drošinātājs: izgrebums no galvenās
  komponentes <= 5%, citādi piegājiens sevi izslēdz. 7 jauni
  parametri `config.toml [chroma]`; workflow 2.4 -> 2.5.
- Pierādījumi: prototips uz īstajām bildēm izgrebj tieši līci +
  vecās pārplūdes mēli (pārklājums `tmp_id/dark2_122248.jpg`),
  kontrolē 122109 tikai 19 px. Ražotnes kods offline: 122248
  d-108 624 px / +0 (carve_garment 28 525 puspx), 122109 d0 px.
- Testi: +1 vienības tests `_dark_uncertain` (līcis nedrošs >=0.8,
  teksturēta kroka <=0.1). Pilnas ainas sintētiskais līča tests
  izmests ar iemeslu: diskrētas krāsas mediān-griezumā izolējas
  citādi nekā foto nepārtrauktais ēnojums (3 mēģinājumi); integrāciju
  pierāda Attempt 3 mērījumi. Kopā 80 testi OK.
- Zināms ierobežojums: ja tumšajās FG sēklās ir diskrēta, krāsā
  attāla fona mode (>=~10%), tā var nozagt paletes centru; tad
  līcis paliek (kļūdas virziens = drošais: maska kā 1. piegājienā).

## §79 — Attempt 3: checker 4/4, līcis izgrebts (2026-10-24)
- Maker 4/4 (14.11 s/bilde; maks. 20.70 s — 122109 ar tumšo
  piegājienu nedaudz pāri ~20 s orientierim; checker GATE_T iztur).
  Pilnie kadri nemainīgi `isnet` (segums 0.4746/0.5404 kā A1/A2).
  122109: dark_pass carve_garment 19 puspx, maska pret A2 d0 px.
  122248: carve_garment 28 525 puspx (d-108 624 px pilnā mērogā,
  +0), segums 0.7777 -> 0.7691.
- Checker: 4/4 ALL_PASS.
- Vizuāli: koka pleķis zem piedurknes pazudis (zoom
  `tmp_id/zoom_a3_122248.jpg` pret `zoom_paraugs_122248.jpg`).
  Atlikušās tumšās daivas izgrebuma malā ir gludas, bez koka
  dzīslojuma — pēc tekstūras tās ir audums (jakas apakšpuse ēnā),
  bet robeža tur ir raupjāka nekā pārējā siluetā. Papildu
  morfoloģiskais gludinājums offline (atvēršana / attāluma lauka
  gludināšana) daivas tikai noapaļo — tās nav troksnis, tāpēc
  ražotnē nelikts. GATE_E galavārds lietotājam: apstiprināt A3 /
  122248 atpakaļ uz A2 variantu / piegādāt 3 bildes.
- Krātuve: ~126 MB; pēc apstiprināšanas un slēgšanas atbrīvosies.

## §80 — 122248 līča robeža: ROI GrabCut (lietotāja izvēle), Attempt 4 (2026-10-24)
- Lietotājs A3 vizuāli noraidīja ("izskatās ļoti slikti") un jautāja,
  vai vietu var AI reģenerēt. Atbilde fiksēta: audumu ģenerēt
  nedrīkst (00 §3.2); drīkst tikai masku. Pierādījums ar kontūru uz
  oriģināla (`tmp_id/evidence_122248.jpg`): A3 atlikušās daivas guļ
  uz grīdas (dzīslojums iekšā). Lauka sadalījumi pārklājas (daivas
  med 8.1 pret piedurkni 13.0) — globāls slieksnis neder.
- Lietotāja izvēle: algoritmiski precizēt robežu tikai zonā.
  ROI atvasināts no nedrošās zonas lielākās komponentes (ne ar
  roku); GrabCut 5 iter., sēklas: sureFG = maska & dist>=25 &
  (tumšais lauks>12 | L>25), sureBG = ~maska & dist>=15; rezultāts
  pieņemts tikai dilatētā nedrošajā zonā (ROI mala citādi ielika
  šuvi — izmērīts prototipā). Pielietots maskas failam ar
  provenance posmu `roi_grabcut` (ķēde mask -> roi_grabcut,
  history_known true): d-46 199 / +2 919 px pret A3 masku.
  Skripts: `tmp_id/roi_fix_122248.py`.
- Attempt 4 (`--rerender-saved`): maker 4/4, profils nemainīgs
  ([180,173,159], [1,1,1], 1.06), checker 4/4 ALL_PASS. Zoom
  `tmp_id/zoom_a4_122248.jpg`: līcis tīrs, robeža pa aproci un
  ķermeņa malu; savienojumā daži 2-4 px pakāpieni (GrabCut pilnā
  izšķirtspējā). Gala lēmums (GATE_E) lietotājam ar kolāžu.

## §81 — Piegāde: 3 bildes (lietotājs kabatas kadru izslēdza) (2026-10-24)
- `make_zip` ieguva `only_stems` (CLI: `--make-zip --files ...`):
  lietotāja izslēgšana neko neatvieglo (atlasītajām vajag checker
  PASS; nezināms/tukšs saraksts = kļūda) un tiek ierakstīta
  delivery atskaitē kā `excluded_by_user`. +1 tests; kopā 81 OK.
- ZIP: `output/V2_GALA_BILDES.zip`, 4 161 694 B, sha256
  `285d4a9e602a21ed...`, workflow 2.5, attempt 4. Iekšā:
  `121349` (1 072 452 B, `3f960a3c...`), `121740` (1 188 039 B,
  `22fc74f6...`), `122109` (2 011 354 B, `1642e005...`).
  Izslēgts pēc lietotāja lēmuma: `122248` (kabata) — tā A4
  artefakti paliek output/, līdz grupa tiks slēgta.
- Nākamais: lietotāja poga "Lejupielādēju — dzēst grupu" ->
  `close_group.py` dry-run, tad `--yes`.
- STUDIJAS KPI kopsavilkums šai grupai: A1 checker 2/4; vajadzēja
  2 ražotnes soļus (§76 chroma ceļš, §78 tumšās zonas piegājiens)
  + 1 ROI labojumu (§80) + piegādes rīka paplašinājumu (§81).
  Sērija "3 grupas bez koda labojuma" paliek 0 — grupa bija ārpus
  papīra uzstādījuma, ko rīki sākotnēji sedza.

## §82 — Grupa slēgta (2026-10-24)
- Lietotājs ar pogu apstiprināja lejupielādi. `close_group.py`
  dry-run: 34 faili / 120.50 MB (tikai grupas faili: 4 avoti,
  MASTER/PARAUGS/maskas/profili, kolāža, ZIP). `--yes`:
  izdzēsti 34 faili; krātuve 131 684 447 -> 11 181 758 B.
  `uploads/` atkal tikai handoff .md + 4 Slam Jam paraugi.
- Piegādāts: 3 bildes (priekšpuse, mugura, odere/birka). Kabatas
  kadrs `122248` izslēgts pēc lietotāja lēmuma — ēnas līča robeža
  netika līdz galam izšķirta bez ģenerēšanas (§77-§80).
- Ilgstošais ieguvums no grupas: chroma rezerves ceļš (§76) +
  tumšās zonas piegājiens (§78) + piegādes apakškopa (§81);
  workflow 2.5; 81 tests. Nākamā grupa uz ne-papīra fona sāksies
  ar šiem rīkiem jau iekšā; studiju sērija joprojām 0.

### §83 Studiju 2. kārta (M8): padziļināta izpēte pirms nākamajām bildēm — 2026-10-24
- Pēc lietotāja uzdevuma: internets + YouTube + Telegram apskats pufjakas grupas
  atklātajām vājajām vietām. **Kods netika mainīts**; 15 web meklējumi + 2 lapas
  (Vinted catalog-rules, t.me/s/AI_DeepLearning priekšskatījums).
- `STUDIJAS.md` papildināts ar M8 (N1–N9) un kandidāteksperimentiem E8–E13:
  OKLab (E8), guided joint-upsampling malām (E9), SLIC superpikseļi (E10),
  ēnas invariante (E11), dihromatiskais spīduma modelis (E12), matting
  caurspīdīgiem audumiem + specifikācijas jautājums (E13). Prioritāšu secība:
  E9 > E8 > E11 > E10 > E12 > E13.
- Modeļu karte: rembg noklusējums tagad bria-rmbg (~1.02 GB; komerciālai
  lietošanai vajag licenci) — mums neder; ISNet lēmums nemainīgs.
- **Biznesa atradums (N9)**: Vinted noteikumi burtiski aizliedz attēlu
  rediģēšanu, bet Vinted preses pozīcija (2026-10-23) atļauj vizuālu uzlabojumu
  (piem., fona noņemšanu), ja bilde paliek precīza un neslēpj stāvokli.
  Ieteikums lietotājam: vismaz viena neapstrādāta bilde sludinājumā + godīga
  deklarācija. ES AI akta marķēšana no 2026-08-02 (mūsu pikseļi ir oriģināli).
- KPI žurnālā pielikta pufjakas rinda (A1 checker 2/4; 10.77 s/bilde).
  Video avoti apskatīti aprakstu/metadatu līmenī (godīgi atzīmēts dokumentā);
  Telegram kanāli lasāmi caur t.me/s priekšskatījumiem.
- Nākamie soļi pēc lietotāja izvēles: kāds no E8–E13 eksperimenta prototipiem
  (§3 kārtība: mērījums -> poga -> solis) vai nākamā bilžu grupa pēc §3.1.

### §84 E8 eksperiments: OKLab pret CIE Lab tumšajai zonai — NAV pierādīts (2026-10-24)
- Lietotāja izvēle (poga): E8. Skripts `tmp_id/e8_oklab.py` (gitignored),
  rezultāti `tmp_id/e8_oklab.json`. Ražošanas kods nemainīts.
- Metode: īstie tumšie centri no `report_v2_maker.json` (122248, 122109) +
  2 sintētiski pāri; ap centriem fizikāli mākoņi (ēnojums lineārā sRGB ->
  8 bitu troksnis/kvantizācija); abas telpas apstrādā TOS PAŠUS pikseļus
  ar ražošanas `_median_cut_palette` (k=4, attīrīšana >=8.0). Konversiju
  apaļā ceļa pārbaude: max 0.70 dE. 2 grūtības līmeņi.
- Mērījumi (bāzes līmenis): 122248 — Lab M2 9.45/8.02, M3(testa kļūda)
  0.0000, M5 līcis 0.668; OKLab M2 4.56/3.81, M3 0.0002, M5 0.906.
  122109 — Lab M3 0.0036; OKLab M3 0.0003, bet M2 1.40/2.87 pret Lab
  4.97/7.34. S1: OKLab attīrīšanā zaudē visus centrus; S2: abas telpas
  sevi izslēdz (krāsas tiešām neatdalāmas).
- **Spriedums pēc iepriekš fiksētā kritērija: OKLab NAV pierādīts**
  (M3 uz 122248 nav mazāka: 0.0002 > 0.0000; M2 visos gadījumos sliktāka).
  Kritēriju pēc fakta nemaina.
- **Metodoloģiska pašpiezīme (kļūda manā dizainā):** vieni un tie paši
  krāsu pāri Lab76 dod ~2.5x lielākus attālumus nekā OKLab x100
  (M1 pirms attīrīšanas: 15.59 pret 6.19; 10.21 pret 4.06) — Lab tumšās
  atšķirības "izstiepj". Tāpēc ražošanas absolūtie sliekšņi (attīrīšana
  8.0, lauks 5.0) OKLab telpā ir nesamērojami bargāki: attīrīšana nogāza
  2 no 4 FG centriem (122248) un visus (S1), kas piesārņo M2/M4 un daļēji
  M3. M4 (|lauks|<5) vispār nav salīdzināms starp dažādi skalātām telpām.
- **Vienīgais no skalas neatkarīgais signāls par labu OKLab:** izmērītais
  līča pikselis [6.5,3.2,2.6] Lab telpā ir tuvāk apģērbam (attiecība
  0.67/0.71 — tieši ražošanas kļūme), OKLab — 0.91 (bāze) un 1.13
  (grūts; faktiski tuvāk fonam). Ierobežojums: sintētiskie mākoņi ir
  tīrāki par īstajām sēklām (sintētika M2 9.45 pret īsto 3.90), tāpēc
  der tikai relatīvais salīdzinājums.
- Godīgs turpinājums būtu E8b ar sliekšņu kalibrēšanu katrai telpai
  (piem., attīrīšanas slieksni piesiet klases iekšējiem attālumiem vai
  skalas koeficientam ~2.5) un TĀDIEM PAŠIEM uzvaras kritērijiem —
  tikai ar lietotāja lēmumu. Bez tā OKLab ražošanā neieliek.

### §85 E8b: OKLab ar kalibrētiem sliekšņiem — tēma SLĒGTA, Lab labāks (2026-10-24)
- Lietotāja izvēle (poga): E8b. Skripts `tmp_id/e8b_oklab.py`, rezultāti
  `tmp_id/e8b_oklab.json`. Ražošanas kods nemainīts.
- Kalibrēšana pēc iepriekš fiksēta noteikuma: s = centru savstarpējo
  attālumu mediānu attiecība pret Lab (no train paletēm); sliekšņi
  8.0*s un 5.0*s. Izmērītais s = 0.30-0.40 visos gadījumos; pēc
  kalibrēšanas centri saglabājas 4/4 (E8 artefakts novērsts; S2 abas
  telpas sevi izslēdz kā iepriekš). Kalibrācijas noteikumu apstiprina
  M4 sakritība (122109 bāze: 0.0751 pret 0.0752). 3 sēklas, vidējie.
- Rezultāts (bāze, 122248): M2 OKLab 5.99/6.24 pret Lab 9.44/8.01;
  M3 0.0027 pret 0.0000 (grūts līmenis: 0.0113 pret 0.0006); M5 līcis
  0.440 pret 0.669. M2 sliktāka 12 no 14 salīdzinājumiem (izņēmums:
  S2 "grūts", kur Lab 2/3 sēklās sevi izslēdza — tur abas telpas ir
  nederīgas, un pareizā ražošanas uzvedība ir tieši izslēgties).
- **Spriedums pēc tā paša kritērija: NAV pierādīts (0/3).** E8 vienīgais
  OKLab plus-signāls (M5 = 0.906) izrādījās paša E8 sliekšņu artefakts:
  attīrīšana bija izdzēsusi FG centrus līča tuvumā; ar pilnu paleti
  līcis OKLab telpā apģērbam ir VĒL tuvāks nekā Lab (0.44 pret 0.67).
- **Secinājums (pierakstīt kā zināšanu):** uztveres vienmērība nav tas
  pats, kas klašu atdalāmība. Lab "izstiepums" tumšajā zonā, ko kritizē
  kā uztveres kļūdu, mūsu klasifikatoram darbojas kā pazīmju
  pastiprinātājs: klašu attālumi aug straujāk nekā ēnojuma izkliede
  klases iekšienē (M2 to mēra bez skalas ietekmes). OKLab tika
  testēts godīgi divos eksperimentos — **tēma slēgta, paliek CIE Lab.**
  OKLab vēl var noderēt uztveres metrikām (piem., ēnas kļūdai), ne
  klasifikācijai.
- Abu eksperimentu cena: ~sekundes CPU pret ražošanas refaktoru —
  tieši šim studiju sistēma domāta.

### §86 E9 etalons: guided upsampling pret ražošanas LANCZOS — NAV pierādīts (2026-10-24)
- Lietotāja izvēle (poga): E9. Skripts `tmp_id/e9_guided.py`, rezultāti
  `tmp_id/e9_guided.json`, vizuālais pierādījums `tmp_id/e9_evidence.png`.
  Ražošanas kods nemainīts.
- Etalons: 4 sintētiskas ainas ar analītiskām patiesām malām (A kontrasts
  ar līci, B vāja mala, C viltus tumša līnija 3-6 px ārpus malas, D 4/8 px
  siksnas + cilpa) x 2 režīmi (R1 bināra 2x ievade kā chroma/plate;
  R2 mīksta 4x kā ISNet) x 6 metodes; visām beigās ražošanas
  `clean_mask(128, erode 1)`. Iekšējā pārbaude: PROD ainās A/B/C dod
  identiskus skaitļus - pareizi, ievade tajās ir viena un tā pati maska.
- **R1 (binārā ievade): guided zaudē visur.** BIoU5 0.79-0.81 pret PROD
  0.8353; chamfer 1.01-1.68 pret 0.844. Blakus atklājums: BILIN pēc
  sliekšņa + clean_mask ir identisks LANCZOS (0.8353) - interpolācijas
  veids binārai maskai pēc binarizācijas vairs neko nemaina.
- **R2 (mīkstā ievade): tuvākais ir COL-P1** (krāsu guided, r=4,
  eps=1e-3): kritērijs (a) krīt par 0.005 (vid. BIoU5 0.7729 pret
  0.7775; velk lejā vājas malas aina B: 0.7723 pret 0.7917), (b) un
  (c) izpildās. Lielākais reālais ieguvums: D siksnas pie 4x - chamfer
  1.43 pret PROD 8.23 (Lanczos plānu struktūru izsmērē zem sliekšņa,
  guided to atgūst no foto). Pelēktoņu guided ainā C ielēca viltus šuvē
  (chamfer 3.49) - pelēktoņu variants mūsu jomā aizliegts; krāsu
  variants slazdu izturēja (0.7937 pret 0.7917).
- **Spriedums pēc iepriekš fiksētā kritērija (abi režīmi obligāti):
  NAV pierādīts - neviens no 4 variantiem neizpilda visus (a)(b)(c).**
  Ražošanas LANCZOS paliek. Skaidrojums: ar ideālu zemas izšķirtspējas
  ievadi Lanczos+slieksnis jau ir tuvu informācijas robežai; guided
  koeficientu izlīdzināšana malu nobīda (~+0.25 px). Guided vērtība
  parādās tikai tur, kur ievade struktūru jau ZAUDĒJUSI (siksnas 4x).
  Ātrums nav šķērslis (COL 0.82 s/12 MP pret PROD 0.06 s). Kopējais IoU
  visiem ~0.99 - literatūras brīdinājums apstiprināts: IoU malu neredz.
- Ierobežojumi: ievades ideālas (no patiesās alfas); īstās ISNet mīkstās
  maskas nes semantiskas kļūdas; apģērba iekšējās malas (apdruka/šuves
  pie robežas) netestētas. Atlikušais kandidāts tikai ar jaunu lēmumu:
  E9b = COL-P1 A/B tests TIKAI uz ISNet mīksto masku ceļa ar īstu grupu;
  chroma/plate bināro ceļu neaiztikt (pierādīti sliktāk). Mans
  ieteikums: slēgt; atgriezties tikai, ja īsta grupa uzrāda siksnveida
  struktūru zudumu maskas posmā.

### §87 E11: ēnas invariante (Finlayson) — NAV pierādīta, tēma slēgta (2026-10-24)
- Lietotāja izvēle (poga): E11. Skripti `tmp_id/e11_invariant.py` +
  autopsija `tmp_id/e11_autopsy.py`; JSON blakus. Ražošana nemainīta.
  (Sākumā paštaisīta attālumu kļūda deva 0 sēklas - izlabota pirms
  jebkādiem rezultātiem.)
- **Reģistrētais E11** (entropijas theta, kā būtu ražošanā): F1 (tikai
  invariante) sajaukšanas kļūda 0.43/0.41 (tīrs/JPEG) pret F0 (Lab
  tumšās paletes) 0.0000/0.0104; F2 (F0+F1) JPEG līmenī 0.0297 -
  invariantes pievienošana Lab pat KAITĒJA. Visi kritēriji krita.
- **Autopsija (theta slaucīšana) atklāj trīs mehānismus:**
  1. Entropijas kalibrēšana izgāzās: atrada 45.7/45.0°, kas nav ne
     invariante, ne diskriminante (kļūda 0.40-0.44). Uz divu virsmu
     foto (apģērbs+fons = mūsu joma) entropijas minimums ir deģenerēts.
  2. Ar teorētiski pareizo theta=35° invariance fizikāli strādā
     (korelācija ar ēnu 0.024 tīrā ainā), BET klasifikācija tik un tā
     zaudē: kļūda 0.12/0.105 pret F0 0.0/0.01. Projekcija ortogonāli
     apgaismojumam izmet tieši to virzienu, kurā zilais apģērbs no
     siltās grīdas atšķiras visvairāk.
  3. JPEG invariance lauž: korelācija 0.024 -> 0.46 (4:2:0 hromas
     izsmērēšana + log attiecību trokšņa pastiprināšanās tumšajos
     pikseļos - tieši tur, kur tumšais piegājiens dzīvo).
  "Oracle" theta (78/104°) dod kļūdu ~0, bet ar korelāciju 0.938 - tā
  ir labākā diskriminantes ass, nevis invariante, un Lab to jau panāk.
- **Spriedums: NAV pierādīts; tēma slēgta** (nevis "vēl jātestē"): trīs
  neatkarīgi mehānismi strādā pret metodi tieši mūsu apstākļos.
  Blakus secinājums par labu esošajai ražotnei: kad ēna ir sēklās
  paraugota (§78 dizains), Lab tumšais piegājiens sintētikā dod 0 kļūdu.
  Ierobežojums: sintētiskā aptumšošana saglabā nokrāsu proporcionāli;
  telefona melnā līmeņa/hromas NR apstrāde F0 reālo rezervi samazina -
  bet mehānismi (2)(3) invarianti tur degradē vismaz tikpat strauji.

### §88 E10: SLIC superpikseļi — kritērijs krita, bet V1 precizitāte pārsteidz (2026-10-24)
- Lietotāja izvēle (poga): E10. Skripts `tmp_id/e10_slic.py`, rezultāti
  `tmp_id/e10_slic.json`. Ražošanas kods nemainīts.
- **Replikas validācija perfekta:** BASE (chroma replika pusmērogā ar
  ražošanas palīgfunkcijām) pret īsto `chroma_mask`: IoU = 1.00000 abos
  līmeņos, visas metrikas identiskas. Etalons tik tiešām mēra ražošanu.
- **Kritērijs (a) izrādījās tukšs (mana dizaina kļūda):** BASE perimetra
  attiecība ir 0.9916 - robeža jau ir GLUDĀKA par patieso (lauka Gauss
  sigma=2 + morfoloģija + Lanczos visu izlīdzina; sintētiskās tekstūras
  ir pārāk gludas). Uzlabojums par 0.05 matemātiski neiespējams, tāpēc
  (a) krita visiem un formālais spriedums ir NAV PIERĀDĪTS. §79 robainība
  uz īstas bildes šajā ainā neatveidojās - šis jautājums paliek atklāts.
- **Taču V1 (SLIC mediāna galvenā lauka |lauks|<5 zonā) precizitātē
  uzvarēja pārliecinoši abos līmeņos:** kļūdu pikseļi 14225->9511 (tīrs,
  -33%) un 14423->10447 (JPEG, -28%); Boundary IoU(5) 0.591->0.734 /
  0.586->0.712; chamfer 2.18->1.43 / 2.22->1.59 (labākais: 20 px
  segmenti). Mehānisms: segmenti nepārkāpj foto malas, tāpēc mediānas
  lēmums robežu noliek uz segmentu robežām, kas piekļaujas īstajai
  malai labāk nekā nobīdītais lauka nulles šķērsojums. Cena: +418-567
  FP pikseļi ēnas zonā (BASE: 0). V2 (SLIC tumšajā nedrošajā zonā)
  nedaudz sliktāks; V3 identisks V1.
- **Godīgs statuss: V1 = daudzsološs, bet NEpierādīts.** Sintētiskā
  mala ir tīrāka par īstu foto malu - ieguvuma lielums, visticamāk,
  pārspīlēts; SLIC maksā ~4.5 s/bilde pusmērogā (budžets 20 s).
  Kritēriju pēc fakta nepārraksta. Kandidāts **E10b**: V1 kā config
  slēdzis chroma ceļā, A/B uz nākamās ĪSTĀS ne-papīra grupas (checker +
  acs + tie paši malu mērījumi pret rokām vērtētu robežu nav iespējami
  bez patiesības - vērtējam ar GATE_H zonu un vizuālo kolāžu).
  Lēmums lietotājam; bez tā kodu neaiztiek.

### §89 E12: dihromatiskās līnijas paletes — NAV pierādīts, tēma slēgta (2026-10-24)
- Lietotāja izvēle (poga): E12. Skripts `tmp_id/e12_dichromatic.py`,
  rezultāti `tmp_id/e12_dichromatic.json`. Ražošanas kods nemainīts.
- **Modelis fizikāli pareizs, novērtēšana to nogalina.** Ar PATIESO
  gaismas krāsu S (oracle) segmenti ir teju perfekti: L2 kļūda 0.0000 /
  0.0041 pret P8 0.0003 / 0.0042, spīduma apakškopā pat labāki (0.0108
  pret 0.0168) ar 2 segmentiem pret 8 punktiem. Bet ar S, kas novērtēts
  no datiem (spilgtāko 0.5% mediāna), L2 spīduma kļūda ir 0.039 / 0.159
  pret P8 0.002 / 0.017 - par kārtu sliktāk. Visi kritēriji krita.
- Mehānisms: spilgtākie pikseļi ir APGRIEZTI baltā (uint8 griesti) -
  novērtētais S = [100,0,0] pret patieso [98.8,0.3,3.3]. Tikai 3.6 dE
  virziena kļūda segmenta tālajā galā izaug proporcionāli spīdumam un
  visu svītru noliek garām datiem. Punktveida centri ir robusti, jo
  sēž uz faktiskā (apgrieztā, izliektā) datu mākoņa, lai kur tas būtu.
  Telefona HDR/tonu līknes šo novērtēšanu padarītu vēl sliktāku.
- Strukturāls šķērslis ražošanai: abu klašu segmenti beidzas vienā S
  punktā, tāpēc palešu savstarpējais attālums ir 0 pēc konstrukcijas -
  esošais QA slieksnis (min_cross >= 15) uz segmentiem nepārnesas;
  vajadzētu jaunu QA teoriju. Punktu paletēm P8 kļūda jau ir 0.0003-
  0.0042 - uzlabojumam gandrīz nav vietas.
- **Spriedums: NAV pierādīts; tēma slēgta.** Novērojums malā (nav
  kandidāts bez jauna lēmuma): datu vadītas iegarenas kopas (katra
  centra lokālais virziens no pašiem datiem) apietu S novērtēšanu,
  bet tas ir cits eksperiments un cita sarežģītība; P8 rezervju te
  tikpat kā nav.
- Ierobežojums: sintētika ir modeļa labākais gadījums (viens
  apgaismotājs, precīza dihromatiska fizika) - oracle pilnība tāpēc
  gaidāma; pārnesamais atradums ir novērtēšanas trauslums.

### §90 E13: caurspīdīgie audumi izmērīti — vajadzīgs specifikācijas lēmums (2026-10-24)
- Lietotāja izvēle (poga): E13. Skripts `tmp_id/e13_tulle.py`, rezultāti
  `tmp_id/e13_tulle.json`, pierādījums `tmp_id/e13_evidence.png`
  (foto | efektīvais ražošanas iznākums | patiesais uz #F3F3F3 | dE karte).
  Ražošanas kods nemainīts; mērījumi ar īsto ISNet un `chroma_mask`.
- **M1 - ISNet alfa caurspīdīgumu neredz:** melnā tilla zonā alfa
  0.97/0.90 (patiesā 0.38/0.46), baltā 0.15/0.10 (patiesā 0.56/0.66);
  MAE 0.47-0.60. ISNet mīkstā maska NEDER kā matte alfa.
- **M2 - trīs dažādi ražotnes likteņi:** (A, melns tills) chroma ceļš
  sevi NORAIDA - FG palete saindēta caur tīklu: 56% tās masas ir koks,
  kas redzams caur caurumiem (centri [23.6,11,15] u.tml.), gredzena
  d_fg mediāna 5.7 < 18 -> 0 fona sēklu. Noraidījums ir DROŠA uzvedība
  (rezerves ķēde/STOP, nevis miskastes maska). ISNet binārā A: IoU
  0.9953. (B, balts tills) chroma pieņem (ambiguous 0.002, IoU 0.9947),
  bet ISNet binārā svārkus zaudē PILNĪBĀ (atgūstamība 0.0).
- **M3 - pašreizējās (necaurspīdīgās) specifikācijas rendera kļūda**
  pret patieso preces izskatu uz #F3F3F3: A tīkla zonās dE mediāna
  56.2/49.9 (>10 veseliem 99.8% pikseļu) - caur melnu tillu izvadā
  spīd VECĀ koka grīda uz pelēkā fona; B 15.9/9.6 (>10: 82%/48%).
  Necaurspīdīgā kontrole: mediāna 0.5-0.9 (mērījums valīds).
- Secinājums: ar bināro specifikāciju tills/siets/mežģīnes izvadā
  maldina pircēju (vecā fona spoks nav preces izskats; sal. N9 Vinted
  precizitātes prasību) vai pazūd. Īsts labojums = alfa novērtēšana +
  alfu zinošs renders un checker (liela specifikācijas maiņa; ISNet
  alfa tam neder - vajadzīgs E13b PyMatting prototipa mērījums vispirms).
  Alternatīva: šādus apģērbu STOP-eskalēt lietotājam. **Lēmums tiek
  prasīts lietotājam ar pogu; līdz tam ražošana nemainās.**
- Ierobežojumi: regulārs sintētisks tīkls (īstas mežģīnes
  neregulārākas), viens fona veids, renders mērīts bez ēnas un krāsu
  profila (izolēts tikai caurspīdīguma efekts).

### §91 Lietotāja lēmums: caurspīdīgo audumu specifikācija atlikta (2026-10-24)
- Poga pēc §90 mērījumiem: **"Atlikt lēmumu"** - izlemjam, kad pienāks
  pirmais tills/siets/mežģīnes apģērbs. Ražošana nemainās.
- Operatīvā sekas man (§3.1 papildinājums praksē): pie katras jaunas
  grupas inventarizācijas PĀRBAUDĪT, vai apģērbam ir caurspīdīgas
  daļas; ja ir - pirms apstrādes atgādināt §90 skaitļus un prasīt
  specifikācijas lēmumu ar pogu. Klusi laist cauri binārajam ceļam
  NEDRĪKST (maldinošs izvads, §90/N9).
- Studiju 2. kārtas (M8) bilance uz šo brīdi: E8/E8b (OKLab) slēgts;
  E11 (invariante) slēgts; E12 (dihromatiskās līnijas) slēgts;
  E9 (guided) nepierādīts, atlikums E9b; E10 (SLIC) formāli
  nepierādīts, bet V1 precizitāte +28-33% -> kandidāts E10b uz īstas
  grupas; E13 izmērīts, lēmums atlikts. Ražošanas kods visā 2. kārtā
  NAV mainīts (workflow 2.5, 81 tests). Visi eksperimenti kopā:
  ~2 min CPU pret piecām atmestām ražošanas izmaiņām.

### §92 YouTube video pēc lietotāja saites: Karpathy metode (2026-10-24)
- Lietotājs atsūtīja youtu.be/7zZy1QTvokM ("Stop Prompting Claude. Use
  Karpathy's Method Instead.", Austin Marchese, 13:18) un uzdeva 5
  jautājumus (par ko video; vai saprotu; vai pielietosim; vai tas
  padara mani zinošāku; piebildes). Noskatījos pilnībā: yt-dlp
  transkripts (3336 vārdi) + 27 kadri (720p, ik pēc 30 s); atbildes
  sniegts sarunā. Godīgais kodols: video mani "zinošāku" padara tikai
  caur dokumentāciju - tieši tāpēc šis ieraksts.
- Ar lietotāja pogas apstiprinājumu video esence ierakstīta
  `STUDIJAS.md` Video avotu sadaļā (3 slāņi: spec / verifier /
  environment) ar sasaisti uz mūsu sistēmu un vienu kandidātidēju:
  augstas kļūdas cenas "never do" noteikumus (piem., §91) kādreiz
  pārnest no prozas koda līmenī. Ražošanas kods nemainīts.
- Lejupielādes paliek /var/tmp/yt (video 59 MB, kadri, transkripts) -
  ārpus darba mapes krātuves.

### §93 Jauna grupa: Uniqlo Henley (balts vafeļadījums) — inventārs (2026-10-24)
- Pēc §3.1: inventarizētas 5 bildes `uploads/MVIMG_20261020_*.jpg`,
  visas 3072x4096: `160538` (pilns priekšskats) sha256 `dd04e56e...`,
  `160550` (apkakle/pogas) `43065fda...`, `160601` (pogu aile slīpi)
  `fa66e706...`, `160608` (izmēra birka L) `d0b4809f...`, `160645`
  (kopšanas birka 60/40 kokvilna/poliesters) `c548a367...`.
- Fons: gaiši pelēks papīrs (ražotnes mājas gadījums). Apģērbs:
  balts/krēmkrāsas termālais vafeļadījums - §91 caurspīdīguma
  pārbaude: NAV tilla/sieta paneļu, neattiecas.
- Lietotāja poga: "Jā, šīs ir visas - sākt apstrādi."
- Krātuve pirms: uploads 47 225 059 B; kopā ~60.1 MB.

### §94 Uniqlo Henley Attempt 1: maker 3/5, checker 0/3 (2026-10-24)
- Vide: setup ready (ISNet SHA-256 sakrīt), 81 tests OK, preflight tīrs
  (visiem rotation_cw=0). Attempt 1: 78 s kopā; krātuve pēc: 102.2 MB
  (iekšējais 100 MB griesti pārsniegti, Arena 128 MB vēl nav; sekot!).
- **Kopīgais atteikums visām 3 pabeigtajām: GATE_K** (krāsu godīgums):
  auduma b* nobīde -3.31/-3.24/-3.21 pret limitu 2.5. Cēlonis: profils
  no siltā pelēkā papīra (fons [146,145,137]) paceļ zilo kanālu par
  1.0798 un krēmkrāsas audumu "izbalina" vēsāku, nekā tas ir.
  Kandidāts bez koda maiņas: `--wb-mode identity` (CLI jau eksistē).
- `160538` (pilns): maska isnet, visi pārējie vārti iziet; bloķē tikai K.
- `160550` (apkakle): maska isnet_pad_retry; K + GATE_L DUBIOUS
  (noplūde 45 511 px = 1.03%). Kolāžā REDZAMS defekts: baltas
  vertikālas svītras kreisajā pusē un balts pleķis apakšējā labajā
  daļā - dekontaminācija noņēmusi 120 040 px (vafeļribu tekstūru
  acīmredzot lasa kā malas piesārņojumu). Kandidāts: `--no-decontam`.
- `160601` (slīpais tuvplāns): K + GATE_C: 1 iekšējs caurums 619 px;
  izmērīts alfā: 610 px šķēlums (31..45, 1078..1133) pie kreisās malas.
- `160608` un `160645` (birku makro): STOP needs_review - ISNet dod
  fragmentus (0.0135/0.2449 segums), pad retry un plate noraidīti
  (plate: "ārpusē audums 0.833" / "fons iekšpusē 0.036"), chroma bez
  fona sēklām. Baltā makro problēmas ģimene (sal. Henley §67).
- Godīgs kopsavilkums: šobrīd piegādājama nav neviena no 5. Nākamais
  solis tikai pēc lietotāja pogas: (A) Attempt 2 ar identity WB
  (pārrenderēšana no saglabātajām maskām) + 160550 bez dekontaminācijas
  + makro un cauruma diagnostika ar mērījumiem pirms jebkāda koda
  soļa; vai (B) šaurāks apjoms pēc lietotāja izvēles.

### §95 Uniqlo Henley Attempt 2 (identity WB): checker 1/3 + diagnostika (2026-10-24)

- Komanda (poga `attempt2_full`): `--attempt 2 --wb-mode identity
  --no-decontam MVIMG_20261020_160550`, 3 pabeigtie faili. Maker 3/3
  (46.6 s); profils WB [1,1,1], ekspozīcija 1.06.
- Checker **1/3 PASS**: `160538` ALL_PASS. GATE_K izlabots visām trim
  (identity WB strādā — siltais papīrs vairs neizvēdina krēmkrāsu).
- `160550` GATE_C: 2 caurumi, 54 569 px. Lielākais 53 877 px,
  bbox (2851,1922) 158x1936 — pad_retry maska labajā malā fragmentējas
  pa vafeļadījuma ielejām un ieslēdz auduma joslu kā "caurumu"; kolāžā
  baltais pleķis apakšā pa labi ir šī cauruma renderis. Dekontaminā-
  cijas svītras pazudušas (salīdzinot ar §94), pleķis palicis. GATE_L
  DUBIOUS 0.527% (bija 1.03%).
- `160601` GATE_C: tas pats 1 caurums 619 px (alfā 610 px, 14x55 pie
  kreisās malas (31,1078)) — nemainīgs, kā gaidīts: WB to nevar labot.
- Diagnostika (tikai mērījumi, kods nemainīts):
  - `plate_mask` offline `160550`: accept=True, segums 0.646
    (pad_retry 0.666); labā mala tīra, apkakles iekšpusē nelieli robi.
    Ražošanas ķēde strukturāli sliktam pad_retry mēģina tikai chroma,
    plate netiek mēģināta. CLI plate piespiešanas karoga nav.
  - **Korekcija §93/§94 aprakstam:** `160608` = kopšanas birka,
    `160645` = izmēra birka "L" (bija samainīti).
  - `160608` plate: segums 0.6145, noraidīta "ārpusē audums 0.833 >
    0.6"; pārklājumā ārējā kontūra pareiza (~90%), iekšpuse caurumaina
    pa noēnotajām vafeļielejām (QA mēra pirms caurumu aizpildīšanas).
    bg_med_E = NaN (drošu fona sēklu nav — papīrs tikai stūrī).
  - `160645` plate: segums 0.8906, noraidīta "fons iekšpusē 0.036 >
    0.02" — baltā izmēra birka + gaišās ribu virsotnes skaitās papīrs
    (tā pati §69/§70 klase: makro gluds+gaišs nav papīrs). ISNet makro
    neder (segumi 0.0135 / 0.2449).
  - Pārklājumi: `tmp_id/diag_plate_{160550,160608,160645}.jpg`,
    `diag_160550_right.jpg`, `diag_160601_left.jpg`.
- Krātuve pēc Attempt 2: `/home/user` 102 483 214 B (iekšējais 100 MB
  pārsniegts, Arena 128 MB vēl nav), `loop_bildes` 55 221 255 B.
- Nemainīgs: ražošanas kods (2.5), vārtu sliekšņi, oriģināli.
  Piegādājams šobrīd: 1/5 (`160538`). Nākamais solis — tikai pēc
  lietotāja pogas (sk. ziņu: `--pad` tests bez koda / plate ķēdē /
  plate QA makro precizējums / kadru izslēgšana).

### §96 Uniqlo pad tests (poga `pad_test`): 160550 PASS caur plate, 160601 pie 0.70 STOP (2026-10-24)

- Kritērijs pirms mērījuma (fiksēts ziņā): caurumi ≤ 2000 px kopā katrai
  bildei un segums ±0.03 no A2. **Kopā kritērijs nav izpildīts** (160601),
  bet 160550 iznākums ir labākais iespējamais — sk. zemāk.
- Komanda: `--attempt 3 --wb-mode identity --pad 0.70 --no-decontam
  MVIMG_20261020_160550 --files 160550.jpg 160601.jpg`.
  `--pad` = daļa no 768 audekla (config `pad_retry=0.90`); mazāka
  vērtība = vairāk papīra konteksta.
- **Korekcija §95:** apgalvojums "plate netiek mēģināta" bija nepareizs.
  Ķēde ir ISNet → pad_retry → plate → chroma → STOP; A1/A2 plate līdz
  mēģinājumam netika, jo pad_retry tika pieņemta. Bez tam eksistē
  `--overrides` JSON ar pad katram stem atsevišķi.
- `160550` pie pad 0.70: pad_retry noraidīta → **plate pieņemta**
  (metode `plate_texture`, segums 0.6460, kā offline mērījums §95).
  ALPHA caurumi ≥100 px: **0** (A2: 53 877 + 121 px). Checker:
  **ALL_PASS**, GATE_L PASS 0.161% (bija DUBIOUS 0.527%).
- `160601` pie pad 0.70: **STOP** — pad_retry segums 1.000 noraidīts,
  plate 0.999 noraidīta, chroma: fona sēklas 261 px par maz. Pie
  pad 0.90 (A2) tai bija pad_retry ar 610 px caurumu. Starpvērtības
  0.80/0.85 nav mērītas.
- Stāvoklis: checker **2/2 PASS** (`160538` A2 + `160550` A3; abiem
  identity WB, ekspozīcija 1.06 — profilu vērtības sakrīt). Atklāts:
  `160601` caurums un 2 makro STOP (§95 diagnostika). Pirms piegādes
  tāpat vajadzēs vienu apvienotu mēģinājumu visam komplektam ar
  per-stem iestatījumiem (`--overrides`).
- Krātuve: `/home/user` 101513979 B; `loop_bildes` 51.74 MiB (maker
  atskaite). Kods un sliekšņi nemainīgi. Nākamais — pēc pogas.

### §97 Koda solis 2.6: caurumu klasificēšana pēc satura — ieviests, reālos kadros daļēji (2026-10-24)

- Poga code_holes. Jauns repair_interior_holes (engine/masks.py),
  izsaukts pirms strukturālā trigera visiem kandidātiem; 7 jauni
  parametri config [mask] hole_* (vecās vērtības nemainītas; migrācijas
  sarga tabula papildināta apzināti ar šo ierakstu); WORKFLOW_VERSION
  2.6. Testi **88/88 OK** (7 jauni TestHoleRepair; zelta e2e hashes
  nemainīgi). Darbības tiek ierakstītas maker atskaitē (hole_repair).
- Validācija Attempt 4 (pad 0.90, identity WB, 160550+160601):
  - 160550: mazais caurums 610 px filled_fabric (d_fg 2.46, d_bg 14.76)
    — pareizi. Lielā josla 53 829 px -> opened_bg (d_fg 22.35,
    d_bg 5.75, tex 2.68 pret fonu 2.61, izgriezti tikai 4 px).
    Pilnizšķirtspējas griezums (tmp_id/diag_gt_160550.jpg) rāda: josla
    ir **auduma ielejas**, klasifikācija kļūdīga. Cēlonis izmērīts:
    cauruma mediāna ir ieļeju L~67 pret gredzena ribu virsotnēm, un
    win=5 tekstūra pie ribu perioda ~30 px audumu mēra kā gludu.
    Sekas: renderis kā A2 (baltais pleķis paliek), bet GATE_C iziet —
    skaitlisks PASS ar vizuālu defektu; A3 plate variants paliek
    labākais šim kadram. GATE_E pēc acs šo noķer, vārti ne.
  - 160601: left "neskaidrs saturs" (d_fg 2.24, d_bg 3.55, tex 0.91
    pret 0.72) — defokusēta mala; arī pēc acs griezumā neatdalāms.
  - Checker pēc A4: 2/3 PASS (160538, 160550); 160601 GATE_C.
- Repair laiks 2.9/2.2 s kadros ar caurumiem (kopā 16.7/22.9 s/bilde).
- Mācība precizējumam: tekstūra jāmēra samazinātā mērogā (plate ceļš
  strādā pusizmērā tieši tāpēc) un Lab mediāna pret mediānu ribu
  audumiem ir sistemātiski šķība — vajadzīgs sadalījuma pārklājums
  (gredzena L percentīļu diapazons), nevis mediāna.
- Krātuve: /home/user 102709580 B. Nemainīts: checker, vārtu sliekšņi,
  oriģināli. Nākamais — pēc pogas (klasifikatora precizējums /
  paturēt + plate maršruts / atcelt 2.6 / piegādāt 2/5).

### §98 Klasifikatora precizējums (2.7): mērogs + E-enkurētas atsauces — checker 3/3 (2026-10-24)

- Poga refine_classifier. Kritēriji pirms darba: (1) sintētisks ribu
  tests; (2) visi testi iziet; (3) 160550 josla filled_fabric un pleķis
  kolāžā pazudis. Iznākums: (1) un (2) izpildīti (90 testi OK);
  (3) daļēji — sk. zemāk par pleķa diviem cēloņiem.
- Trīs iterācijas, katra ar mērījumu (godīgi, nevis sliekšņu grozīšana):
  1. A5: tekstūra mērogā 1:4 (josla 7.38, gredzens 8.26) tomēr
     opened_bg: lokālā fona atsauce piesārņota ar audumu (tex_bg_s
     6.97), gredzena L p5=58.6 pret cauruma 49.5.
  2. Atsauču mērījumi: E<8 pret papīra krāsu globāli dod tex 0.75/0.78;
     auduma L sadalījums paplašinātā apkārtnē p5=45.6 iekļauj ielejas.
  3. A6: asimetrisks pierādījums (aizpildīšanai struktūras
     nepārtrauktība cauruma vietā joslā [0.5, 2.5]x pret gredzenu;
     atvēršanai gludums tikai erodētā kodolā), E-enkurēta fona
     tekstūras atsauce, L sargs no auduma apkārtnes.
- A6 rezultāts (pad 0.90): visi 3 caurumi filled_fabric via texture
  (160550 josla: ts 7.38/8.26/0.76; 160601 šķēlums: 2.72/2.82/0.78).
  Checker **3/3 PASS** (160538+160550+160601). Strukturālais trigeris
  chroma vairs nepalaiž; masku laiki 14.1/12.4 s.
- **Pleķis 160550 kolāžā paliek**: izmērīts, ka bijusī josla tagad
  88.1% FG, bet apakšējā labajā stūrī ir 4 ar kadra malu savienoti
  fona līči (5.4-11.0 tūkst. px) — pad_retry ĀRĒJĀ robeža fragmentējas
  pa ielejām. Tie nav caurumi; šis solis ārējo robežu pēc definīcijas
  nelabo. 160550 gala maršruts paliek plate (pad 0.70, A3 PASS ar tīru
  siluetu). Kritērija (3) otrā puse tātad nav izpildīta un ar šo rīku
  nav izpildāma.
- Jauni parametri: hole_tex_scale=4, hole_tex_fg_ratio=0.5,
  hole_tex_fg_ratio_max=2.5, hole_tex_bg_ratio=2.0, hole_tex_min=1.2,
  hole_L_slack=4.0, hole_bg_E=8.0 (kopā ar §97 septiņiem = 14 hole_*).
  WORKFLOW_VERSION 2.7. Krātuve: /home/user 102875656 B.
- Atklāts: 2 birku makro STOP (§95 diagnostika: plate QA). Pirms
  piegādes vajadzīgs apvienots mēģinājums (160550 ar pad 0.70 caur
  --overrides, pārējie noklusēti, identity WB). Nākamais — pēc pogas.

### §99 Audits pēc lietotāja aizrādījuma: checker PASS ar redzamu caurumu — akls punkts izmērīts (2026-10-24)

- Lietotājs pamatoti aizrādīja: A6 checker 3/3 PASS, bet 160550 kadrā
  acīmredzams balts pleķis/svītras; Photoroom to pašu kadru apstrādā
  bez caurumiem sekundēs. Uzdevums: pārbaudīt aprēķinus vai atrast
  citu pieeju. Audits = tikai mērījumi, kods nemainīts.
- Posmu izsekošana 160550: MASK -> ALPHA zaudē tikai 1707 px
  (atšķirības kopā 2999 px): renderis pleķi NERADA. Aritmētiskas
  kļūdas starp posmiem nav; kļūda ir maskā un vērtējuma definīcijā.
- Salīdzinājums ar plate masku (accept=True): plate-only = 704 292 px
  ar tekstūru mērogā 7.27 (auduma atsauce 6.76, papīra 0.66) — gatavā
  maska pazaudē ~0.70 Mpx auduma, no tiem 263 536 px apakšējā labajā
  kvadrantā. Pārklājums: tmp_id/audit_160550_lost.jpg (sarkans =
  zaudētais audums: ieleju svītras + pleķis).
- 4 līči pie labās/apakšējās malas (5.4-11.0 tūkst. px): tex_s
  6.2-7.4, E pret papīru 7.0-11.5 — pēc satura audums, bet savienoti
  ar kadra malu, tāpēc GATE_C tos pēc definīcijas neskaita.
- **Secinājums (korekcija §98 optimistam):** checker ir akls pret
  audumu, kas palicis ĀRPUS maskas gar robežu (līči un ieleju kanāli).
  GATE_C soda tikai ieslēgtus caurumus; "3/3 PASS" bija paties pēc
  definīcijas, nevis vizuāli. Cēlonis ķēdē: pie pad 0.90 pad_retry QA
  masku pieņēma, plate netika mēģināta; strukturālajam trigerim nav
  signāla "teksturēts fons silueta iekšienē".
- Novēršami ceļi (izvēle ar pogu): (a) maker trigeris/kandidātu
  salīdzinājums ar plate, mērot zaudēto teksturēto audumu;
  (b) līču/kanālu atgūšana pēc satura (caurumu labotāja vispārinājums);
  (c) jauns checker vārts šim aklajam punktam; (d) modeļa benchmarks
  (Photoroom līmenis ir servera modelis; lokāli ISNet 768px proxy
  ielejas zaudē). Krātuve: /home/user 103258788 B.

### §100 Modeļa benchmarks (poga model_benchmark): lokāls modelis Photoroom līmeni nesasniedz (2026-10-24)

- Kritērijs pirms mērījuma: IoU >= 0.95 un zaudētais audums <= 50 000 px
  pret plate uz 160550, RAM <= 1800 MB, <= 60 s/kadrs. Tikai mērījumi
  tmp_id/bench (metrics.json, diff pārklājumi); ražošana nemainīta.
  Vide bija jāatjauno (setup_v2; /var/tmp starp sesijām notīrīts).
- Neiespējami pie 1982 MB RAM (exit 137, OOM): bria-rmbg (RMBG-2.0,
  fails 1.02 GB; turklāt komerclicence), birefnet-general-lite
  (214 MB; OOM arī ar 1024px proxy ievadi), u2net_cloth_seg (169 MB;
  fiksēta 768x768 ievade, OOM arī tiešā onnxruntime skrējienā).
  BiRefNet pārējie varianti lielāki — nemērīti kā bezcerīgi.
- Izmērītie (viens piegājiens, slieksnis 0.5, bez pēcapstrādes):
  ISNet plain: 160550 IoU 0.186 (zaud. 6.50 Mpx), 160601 IoU 0.037
  (segums 0.032), 160538 IoU 0.974 bet +134 038 px lieki; 3.6-4.0 s,
  1215-1228 MB. u2net: 0.249 / 0.659 / 0.869 (160538 zaud. 572 975 px);
  1.5-2.0 s, ~900 MB. Ražošanas A6 (pad_retry+labojumi) pret plate:
  IoU 0.812, zaud. 704 292 px — labākais lokālais rezultāts uz 160550
  pēc pašas plate.
- **Secinājums:** modeļa maiņa rembg/2 GB ietvaros problēmu neatrisina;
  Photoroom ir servera klases modelis, kam lokālas atbildes šajā
  atmiņas budžetā nav. Reālistiskie ceļi paliek no §99: (a) maker
  trigeris + checker vārts aklajam punktam; (b) līču/kanālu atgūšana
  pēc satura; (c) flīzēta (tiled) ISNet inference dzimtajā izšķirtspējā
  (jauna, nemērīta ideja); (d) ārējs serviss kā maskas avots
  (lietotāja lēmums par mākoņi/maksu). Krātuve: /home/user 107778026 B.

### §101 Eksperments: flīzēts ISNet — hipotēze noraidīta ar mērījumu (2026-10-24)

- Poga tiled_isnet. Kritērijs tas pats (IoU >= 0.95, zaudētais
  audums <= 50 000 px pret plate uz 160550). Tikai tmp_id/bench.
- Metode: ražošanas isnet_native (arēna izslēgta; rembg sesija flīzēs
  mira ar OOM — tas pats 1215 MB arēnas efekts, ko ražošana jau bija
  izmērījusi), flīzes 1024x1024 solis 768, jēlā izvade bez flīžu
  min-max, spalvu vidējošana + max variants; V1 pa oriģinālu
  (20 flīzes, 64.6 s, 1114 MB), V2 ar 512 px papīra apmali
  (35 flīzes, 115.6 s, 1231 MB).
- Rezultāts: IoU 0.043-0.069, segums 0.03-0.09, zaudētais audums
  7.55-7.78 Mpx — sliktāk par vienpiegājiena ISNet (0.186).
  Kontrole pret inversiju: vidējā soft vērtība audumā 0.059, fonā
  0.082 — modelis flīžu mērogā uz papīra graudu reaģē pat vairāk
  nekā uz audumu.
- **Secinājums:** ISNet tuvplānu neveiksme nav izšķirtspējas, bet
  semantikas jautājums: bez visa objekta skata modelis auduma
  tekstūru par objektu neatzīst nevienā mērogā. Flīzēšana to nelabo
  un maksā 65-116 s/kadrs. Tēma slēgta. Paliek §99 ceļi:
  (a) maker trigeris + checker vārts; (b) līču/kanālu atgūšana;
  (d) ārējs serviss kā maskas avots (lietotāja lēmums).
  Krātuve: /home/user 117285010 B.

### §102 GATE_Q: checker vārts zaudētajam audumam ārpus maskas (A solis) (2026-10-24)

- Poga start_gate (ieteikums apstiprināts). Kritēriji pirms darba:
  A6 160550 krīt, 160538/160601 iziet; sabotāžas testi; visi testi
  iziet; esošie sliekšņi nemainās. Visi izpildīti.
- Jauns bloķējošs vārts GATE_Q_lost_fabric (checker_v2.py, lokāla
  matemātika — neatkarības princips saglabāts): 1:4 mērogā zona
  aizvērts(siluets, elipse R=10 ds px) − siluets; aizdomīgs pikselis,
  ja tekstūra >= max(2.5x fona, fona+2.0, 0.5x auduma kodola).
  Slieksnis 1.0% no FG (GATE_Q_LIMIT_PCT, piesprausts testā).
  Pirmais prototips ar bbox kritēriju izmests: plate ("labais")
  deva 5.48% kakla izgriezuma paneļa dēļ — aizvēršanas ģeometrija
  logus pēc konstrukcijas izslēdz. Kalibrācija (4 kadri): sliktais
  4.27%, labie 0.031/0.065/0.101% — robeža apzināti četru paraugu,
  pārskatīt ar vairāk grupām.
- Testi: 94/94 OK (4 jauni TestGateQ: tīrs iziet, kanāla sabotāža
  krīt, papīra logs iziet, slieksnis piesprausts).
- Reālā validācija: checker **2/3 PASS** — 160550 ALL_PASS=False
  tikai Q dēļ (4.266%); 160538 0.101%, 160601 0.065%. PASS-ar-pleķi
  no šī brīža nav iespējams: tiesnesis defektu redz.
- Nemainīts: maker (2.7), visi esošie vārtu sliekšņi, oriģināli.
  Krātuve: /home/user 118255591 B. Nākamais pēc pogas: B solis (maker
  trigeris ar Q metriku -> plate/chroma) vai Uniqlo pabeigt ar zināmo
  plate maršrutu bez vispārīgā trigera.

### §103 B solis: GATE_Q trigeris makerī (2.8) — checker 3/3, bet plate apēd apkakli (2026-10-24)

- Poga step_b_trigger. Kritēriji pirms darba visi izpildīti:
  160550 pie noklusētā pad 0.90 trigeris pats nonāk līdz plate;
  checker 3/3 ieskaitot Q; 160538/160601 bez izmaiņām; testi
  98/98 OK, zelta e2e nemainīgs.
- lost_fabric_metric (engine/masks.py) = GATE_Q spogulis; parametri
  config [mask] q_* piesprausti pret checker konstantēm krustsarga
  testā. Trigeris strukturālajā blokā: kandidāts neuzticas, ja
  strukturāli slikts VAI zaudētais audums > 1.0%; Q gadījumā vispirms
  plate (pieņem, ja tās Q mazāks), tad chroma kā līdz šim.
  WORKFLOW_VERSION 2.8.
- Attempt 7: 160550 pad_retry Q=4.253% -> plate pieņemta caur
  trigeri (Q=0.031%, metode plate_texture, segums 0.6460). Checker
  3/3 PASS (Q: 0.101/0.031/0.065%).
- **Vizuālais atradums (GATE_E):** plate renderī apkakles josla
  vietām apēsta (balti robi augšā pa kreisi un vidū) — gaišās
  apkakles ribu virsotnes plate lasa kā papīru (redzēts jau §95
  pārklājumā, kolāžā tagad acīmredzams). Pad_retry apkakli turēja
  tīru, bet zaudēja apakšas ielejas; plate otrādi. Q vārti robus
  neredz pēc konstrukcijas (plati logi, ne šauri kanāli), tāpēc
  "3/3 PASS" šim kadram joprojām nav "gatavs" — lēmums lietotājam:
  (a) līču/kanālu atgūšana uz pad_retry bāzes (§99 b); (b) kandidātu
  apvienošanas mērījums (union) offline; (c) pieņemt plate robus;
  (d) 160550 izslēgt. Makro joprojām STOP. Krātuve: 117619511 B.

### §104 Prototips: līču/ieleju atgūšana uz pad_retry — kriteriji izpildīti mērījumā (2026-10-24)

- Poga inlet_reclaim. Tikai mērījumi tmp_id/reclaim_proto.py;
  ražošana nemainīta. Kritēriji pirms darba: zaudētais pret plate
  <= 100k, Q <= 1.0%, apkakle (y<1000) nemainās.
- Bāzes atruna: A6 masku A7 pārrakstīja, tāpēc pad_retry atjaunota
  offline (isnet_padded_mask+clean+hole repair): segums 0.6965,
  Q 2.922%, zaud. 375 446 (ražošanas A6 bija 0.6703 / 4.253% /
  704 292; ceļš atšķiras ar JPEG audekla soli). Virziens derīgs,
  gala skaitļi jāvalidē ražošanas mēģinājumā.
- Variants close R=10 ds (aizvēršanas zona kā GATE_Q, tekstūra
  L* mērogā 1:4, slieksnis max(2x fona E-atsauces, +1.0, 0.5x auduma
  kodola), komponentes >= 8 ds px pie FG): atgūts 342 495 px,
  zaudētais 375k -> **33 086**, liekie pret plate mainās par
  **+135 px** (papīrs netiek ievilkts), apkakle Δ=0, Q -> 0.001%.
  R=20/40 gandrīz identiski; bbox+distance variants sliktāks
  (apkakle Δ=4995).
- Divas godīgas piezīmes: (1) mans pirms-fiksētais "viltus E<6 ~ 0"
  kritērijs izrādījās nederīgs (130 784 px) — ieleju krāsa pret
  papīru E ziņā neatdalās, to zinām kopš §97; izšķirošais ir
  plate-atsauces liekie (+135 px). (2) Q -> 0.001% daļēji cirkulāri
  (atgūšanas zona = Q zona); neatkarīgie pierādījumi ir plate
  salīdzinājums un acs: kompozīts tmp_id/bench/reclaim_comp_160550.jpg
  (apkakle vesela, apakša aizpildīta; paliek sīki balti punktiņi
  atsevišķās ielejās pie apakšējās malas).
- Nākamais pēc pogas: ieviest ražošanā kā posmu pirms Q trigera
  (config reclaim_*, testi, Attempt 8 validācija ar īsto ķēdi).
  Krātuve: /home/user 130644607 B.

### §105 Prototips v2-v4: audzēšana ar histerēzi — svītras izmērītas un aizvērtas (2026-10-24)

- Lietotājs ar ekrānšāviņu (uploads/IMG_20261025_063556.jpg) iezīmēja
  §104 kompozītā palikušās svītras, kurās spīd fons (kreisā apakša +
  apakšmala). Atlikuma (33 086 px pret plate) atribūcija izmērīta:
  58% nav aizvēršanas zonā (maskas robeža iet caur audumu — nav
  "līča"), 40% zonā, bet tekstūra zem sliekšņa (mediāna 3.10 pret
  3.19), komponentu filtrs nebūtisks.
- v2 audzēšana (ģeodēziska dilatācija no FG caur tex>=lo, L*
  tekstūra 1:4): zaudētais 375k -> 11 825, bet kontroles kadrā
  160538 noplūde +361 534 px (7.3%) — apģērba ēnas maliņa uz papīra
  gar visu siluetu (pārklājums tmp_id/bench/reclaim2_diff_160538.jpg).
- v3 virzienu sargs (FG >=2 virzienos 15 ds px): 160538 -> 143 580,
  160550 zaud. 21 162. Diagonālas malas sargu daļēji apiet.
- v4 divu līmeņu zona (aizvēršanas zonā vājais slieksnis, ārpus tās
  stiprais 0.5x auduma + virzienu sargs): **160550 zaud. 21 483,
  liekie pret plate tikai +7 565, Q=0.029%, noplūde virs apģērba 0**;
  kompozīts reclaim2_comp_160550.jpg — lietotāja svītras aizvērtas,
  apkakle vesela. Kontroles: 160601 +0.28%, 160538 +2.0% (joprojām
  augtu) — tāpēc ražošanas vieta ir TIKAI Q trigera iekšienē kā
  pirmais līdzeklis (pirms plate), ar pieņemšanu tikai ja
  Q pēc <= trigeris; labiem kadriem nekad nepalaižas.
- Atlikušais risks (godīgi): Q-sliktam pilnkadra kadram maliņas
  noplūde iespējama; to ierobežo Q pieņemšanas pārbaude un GATE_E.
  Prototipa bāze joprojām atjaunota (§104 atruna). Krātuve: 131734771 B.

### §106 Atlikušo svītru atribūcija + silueta iekšpuses aizvēršana; E13 konteksts (2026-10-24)

- Lietotājs §105 kompozītā iezīmēja atlikušās svītras, kurās spīd
  fons (uploads/IMG_20261025_063556.jpg), un prasīja produkcijas
  iznākumu. Tikai mērījumi (tmp_id/residual2.py).
- Atlikums pēc v4 (21 483 px pret plate): 1801 komponente, 64.9%
  komponentēs <400 px, VISS <= 20 px no jaunās robežas — ieleju
  dibenu mikrosegmenti (tumši/gludi, tekstūra logā zema) + robežas
  domstarpības ar plate pie kadra malām. Karte
  tmp_id/bench/residual_map.jpg sakrīt ar lietotāja atzīmēm.
- Aizvēršana pilnā izšķirtspējā (elipse) uz v4 rezultāta: R=6 ->
  8104 px, **R=10 -> 3783 px** (liekie tikai +1174), R=14 -> 2608,
  R=20 -> 2599. Kompozīts reclaim3_comp_160550.jpg: svītras
  pazudušas, apkakle vesela. Ražošanas vieta (ja ievieš): tikai uz
  atgūtā kandidāta Q trigerī, nevis globāli visām maskām.
- E13 saikne (lietotāja jautājums): Henley ir necaurspīdīgs (§93
  pārbaude) — tā adījuma poras/ieleju dibeni NAV E13 gadījums;
  produkcijas foto silueta iekšpusei jābūt cietai. Īstam tillam/
  sietam aizvēršana būtu kļūda (§90: caurspīdīgums ir preces
  izskats, vajadzīga alfa); §91 lēmums "atlikt" un karoga pienākums
  inventarizācijā paliek spēkā nemainīti.
- Krātuve: /home/user 132374626 B. Nākamais — pogas lēmums par ieviešanu.

### §107 Malas joslas aizpildīšana: pēdējās svītriņas izmērītas un aizvērtas prototipā (2026-10-24)

- Lietotājs §106 kompozītā iezīmēja vēl 3 mazas svītriņas
  (uploads/IMG_20261025_065854.jpg: labā mala x2, apakšmala).
  Izmērītas precīzi: komponentes 515 px (x3060..3071, y3396..3443),
  309 px (x3061..3071, y2358..2390), 215 px (apakšā) — 11 px platas
  auduma šķēles pie pašas kadra malas (tex 5.4-8.4), kur apģērbs
  iziet no kadra. Aizvēršana tās pēc konstrukcijas neņem: kanāls
  iet GAR malu (dilatācija/erozija tur viena otru atceļ).
- Malas josla (prototips): BG pikseļi <=16 px no kadra malas,
  attālums līdz FG <=16 px un tekstūra >= 0.5x auduma kodola ->
  aizpilda līdz malai. Rezultāts: +1133 px, atlikums pret plate
  3783 -> **2650 px**, liekie nemainās (**+0** pret plate).
  Kontroles: 160538 (malām nepieskaras) 0 px; 160601 4615 px
  (audums iziet no kadra — tās pašas klases šķēles).
- Pilna ķēde prototipā (pad_retry atjaunota bāze): zaudētais
  375 446 -> 2650 px (99.3% atgūts), Q 2.922% -> 0.0%, apkakle
  vesela, lietotāja svītras pazudušas (reclaim4_comp_160550.jpg).
  Atlikuma kodols ir 1813 px pleca robežas domstarpība ar plate
  (y~1307) — nevis iekšpuses caurumi.
- Ražošanas pakete lēmumam: audzēšana v4 + aizvēršana R=10 +
  malas josla 16, Q trigera iekšienē pirms plate, pieņemšana tikai
  ja Q pēc <= trigeris. Krātuve: /home/user 133120337 B.

### §108 2.9 ieviests: līču atgūšana Q trigerī — svītras pazuda, platais līcis palika (2026-10-24)

- Poga impl_pkg. reclaim_inlets (engine/masks.py) = §105 v4 +
  aizvēršana R=10 (§106) + malas josla 16 ar rindas/kolonnas
  atbalstu (§107; stūra pāršaušana 256 px sintētikā noķerta testā
  un sašaurināta). Q trigerī kā pirmais līdzeklis pirms plate;
  pieņem tikai ja Q pēc <= 1.0%. Config reclaim_* (14), testi
  102/102 OK (4 jauni TestReclaimInlets), versija 2.9.
- Attempt 8: 160550 atgūšana pieņemta (+556 006 px, Q 4.253% ->
  0.042%, metode paliek isnet_pad_retry), checker **3/3 PASS**,
  GATE_L šim kadram pirmo reizi PASS 0.0 (bija DUBIOUS 0.52).
- **BET kolāžā apakšā pa labi joprojām balts pleķis** (acs noķēra,
  skaitļi ne): viena komponente 154 314 px (x2392..2883,
  y3575..4095, tex 6.23 = audums), maks. attālums līdz FG 131 px.
  Audzēšanas virzienu sargs (FG 60 px rādiusā) tās iekšieni
  nesasniedz, un GATE_Q zona (80 px) to neredz — otrais aklais
  punkts: PLATI zaudējumi. "3/3 PASS" šim kadram atkal nav "gatavs".
- Atmesti ar mērījumu: dziļā audzēšana (dir 64/dist 160 pleķi
  aizpilda -> 22.9k, bet kontrole 160538 izaug 172 698 px = ēnas
  maliņa), piekļaušanās filtrs (līcis 0.209 pret maliņu 0.19-0.29 —
  neatdala).
- **Apvienojums izmērīts tīrs:** A8 ∪ plate: zaudētais pret plate 0,
  Q 0.0%, pievienotais (zils diff attēlā) = tikai pleķa vieta +
  2 punktiņi; apkakle no pad_retry vesela, apakša no plate vesela
  (tmp_id/bench/union_comp_160550.jpg). Kandidāts nākamajam solim:
  trigerī vērtēt arī union(kandidāts, plate), kad plate pieņemta.
  Krātuve: /home/user 135067523 B.

### §109 2.10: union kandidāts Q trigerī — 160550 tīrs visos mērījumos (2026-10-24)

- Poga impl_union. choose_candidate (workflow_v2.py): strukturāli
  pieņemto starpā mazākais Q, neizšķirtā union > current > plate.
  Plate zarā tagad vērtē arī union(kandidāts, plate) — arī tad, ja
  atgūšana jau pieņemta (Q plata līča dēļ var būt zems maldinoši).
  Testi 106/106 OK (4 jauni TestChooseCandidate), versija 2.10.
- Attempt 9: 160550 atgūšana +556 006 px (Q 0.042%), tad union ar
  plate pieņemts (Q 0.042% -> 0.0%, metode
  isnet_pad_retry+plate_union, segums 0.7270). Checker **3/3 PASS**
  (Q 0.101 / 0.0 / 0.065; GATE_L 0.0 uz 160550). Kolāža: apkakle
  vesela, pleķa un svītru nav — pirmo reizi šis kadrs iztur gan
  visus vārtus, gan aci. Laiki 11.3/23.3/18.8 s (maks. kopā 23.3 <
  GATE_T 25 s).
- Atvērts: 2 birku makro STOP (§95 plate QA diagnostika).
  Komplekts piegādei gatavs kā 3/5 ar lietotāja Apstiprināt, vai
  makro solis mērķim 5/5. Krātuve: /home/user 135416393 B.
  UZMANĪBU: uploads/ ir lietotāja 2 anotētie ekrānšāviņi (IMG_20261025_*)
  — palaišanām bez --files tie iekļūtu grupā; lietot precīzus --files.

### §110 160601 augšas robeža defokusā: kodumi izmērīti, ROI GrabCut prototips (2026-10-24)

- Lietotājs A9 kolāžā iezīmēja 160601 augšējo kreiso malu
  (uploads/IMG_20261025_073111.jpg): robota silueta mala un
  iecirtums pie apkakles. Tikai mērījumi.
- Reģions ir defokusēts (sekla asuma dziļuma zona): papīra->auduma
  gradients mediānā 18 px plats. Robežas nobīde no gradienta vidus
  (101 kolonna): mediāna 3 px, bet 27% kolonnu iekož >10 px,
  10% >20 px, maks. 94 px (iecirtums). Q metrika defokusā klusē
  (tekstūra zema), GATE_H mēra alfai profilu, ne novietojumu —
  defekta klase atšķiras no §99 (daudzums) — šī ir robežas
  LOKALIZĀCIJA izplūdušā malā. Offline atgūšana te pievienoja
  tikai 15 050 px un malu neiztaisnoja.
- ROI GrabCut prototips (§80 precedents; ROI 1400x1500, sēklas no
  pašreizējās maskas erodēta/dilatēta, ielīmē tikai dilatētā
  nedrošajā joslā): +39 006 / -690 px, kodumu statistika
  maks. 94 -> **6 px**, p90 20 -> 0; kontūra seko īstajai malai
  (tmp_id/bench/a9_160601_grabcut.jpg). GrabCut 6.6 s.
- Lēmums pēc pogas: (a) vienreizējs ROI GrabCut šim kadram §80
  stilā (provenance roi_grabcut -> rerender -> checker);
  (b) vispārīgs robežas pārlokalizēšanas posms (lielāks darbs);
  (c) pieņemt kā ir; (d) 160601 izslēgt. Krātuve: 149012606 B.

### §111 Git anomālija labota: 2.9/2.10 kods bija darba kokā bez komitiem (2026-10-24)

- Atklāts §110 laikā: komiti, kurus ziņoju kā 8d14de0 (§108) un
  b9ebd90 (§109), repozitorijā NEPASTĀV — starp sesijām atjaunots
  agrāks .git stāvoklis (§107), kamēr darba koka faili (kods 2.10,
  PROGRESS §108/§109 teksti, A8/A9 artefakti) saglabājās. Tāpēc
  §110 komits (f863c90) satur arī §108/§109 PROGRESS tekstus.
- Verificēts: darba koka kods = 2.10, testi atkārtoti **106/106 OK**
  uz šī paša stāvokļa; tas ir tas pats kods, kas ražoja A8/A9.
  Šis komits beidzot ieraksta 2.9+2.10 kodu vēsturē (config,
  engine/config, engine/masks, workflow_v2, testi).
- Mācība: pēc katra komita pārbaudīt "git log --oneline -1" un
  "git status" (darīju §103, pārtraucu §108/§109 — tur arī pazuda).
  Krātuve: /home/user 149412674 B.

### §112 Krātuves tīrīšana un makro izslēgšana (lietotāja lēmums) (2026-10-24)

- Krātuve bija sasniegusi 149 564 138 B (pāri Arena 128 MB griestiem;
  lietotājs nevarēja atvērt attēlu priekšskatījumu). Sadalījums:
  tmp_id 51.1 MB (benchmarka maskas), uploads 48.7 MB, output 41.4 MB.
- Dzēsts: tmp_id/bench *.png/*.npy/logi un tmp_id/diag_*.jpg
  (~39 MB paša pagaidu failu; JSON mērījumi un skripti saglabāti,
  skaitļi jau fiksēti §100-§110).
- **Pēc lietotāja tieša norādījuma dzēsti makro oriģināli**
  uploads/MVIMG_20261020_160608.jpg un _160645.jpg (18.4 MB).
  Sekas: birku makro no grupas IZSLĒGTI galīgi (atjaunot var tikai
  no telefona atkārtoti augšupielādējot). Grupa = 3 kadri (A9).
- Pēc tīrīšanas: /home/user 91904554 B (zem 100 MB iekšējā un 128 MB
  Arena limita). Mācība: benchmarka pilnizmēra maskas tmp_id
  jādzēš uzreiz pēc mērījuma, nevis jākrāj.

### §113 160601 atzīmētā mala: GrabCut nav pietiekams; vajadzīgi robežas pierādījuma vārti (2026-10-25)

- Lietotājs GrabCut kompozītā ar sarkanu iezīmēja tās pašas vietas
  (uploads/IMG_20261025_074636.jpg, 768x1024 = 1:4): kreisā mala
  x2..17/y200..267, plecs x18..262/y145..191, apkakles slīpums
  x294..385/y165..205. Izmērīts tieši tur. A9 maska ņemta 1:4;
  GrabCut siluets no kompozīta atgūts kā |RGB-243|>8 (fons tur ir
  precīzi 243; augšpuses IoU pret A9 0.988 kā saprāta kontrole).
  Nelīdzenums = robežas atlikums pret 21 px (SS mērogā) slīdošo
  mediānu, pārrēķināts pilnā izšķirtspējā.
- Plecs: A9 RMS 6.6 / p95 8 / maks. 40 px -> GrabCut 3.0 / 4 / 16 px
  (uzlabo, bet neizzūd). Apkakles slīpums: A9 4.8 / 14 / 24 px ->
  GrabCut 5.1 / 14 / 20 px (uzlabojuma nav). Kreisā mala
  (y720..1120): A9 joslas mediāna 72, maks. 108 px, laukums
  26 416 px²; GrabCut atstāj iecirtumu SS y201..252, maks. 56 px,
  7 968 px². Secinājums: prototips novērš rupjo kodumu (§110), bet
  lietotāja vizuālo kritēriju neiztur — ražošanā to neliek.
- Sistēmas secinājums: šis nav "nelabojams pēc definīcijas", bet
  trūkstoša pārbaude. §110 pārejas platums defokusā ir mediānā
  18 px; GATE_Q tur klusē (tekstūra zema), GATE_H vērtē alfas
  profilu, ne robežas novietojumu pret avota gradientu. Globāls
  kontūras nelīdzenums viens pats arī nešķir droši: sliktākā
  100 punktu segmenta RMS A9 6.81 pret kontrolēm 3.71 (160538) un
  1.33 (160550), bet GrabCut 3.02 pārklājas ar kontroli. Vārtiem
  jābūt kombinētiem: lokāls nelīdzenums + avota pārejas platums /
  robežas nobīde no gradienta + kadra malas iecirtums.
- Lietotājs: šī kadra kvalitāte ir nepieņemama, to pārfotografēs.
  Tāpēc 160601 no šī avota nepiegādā un vienreizējo GrabCut
  nelieto; kadrs gaida jaunu oriģinālu. 160538/160550 nemainīti.
  Princips nākotnei: nenoteikta/defokusēta robeža = STOP ar
  iemeslu (pārfotografēt vai labot ar pierādījumu), nevis PASS.
- Nākamais solis tikai pēc pogas: offline kalibrēt robežas
  pierādījuma metriku uz šī sliktā gadījuma + kontrolēm; ja ir
  skaidra atdalīšana, ieviest checker vārtus un maker STOP/
  trigeri ar sabotāžas testiem. Krātuve: /home/user 91808135 B.

### §114 Robežas pierādījuma kalibrācija: v1 noraidīts, v2 atdala ar rezervi (2026-10-25)

- Poga calibrate_gate. Kritērijs pirms mērījuma: metrika der tikai
  tad, ja iezīmē gan A9 160601, gan GrabCut atlikumu, bet ne
  160538/160550 kontroles. Skripti tmp_id/boundary_calib{,2}.py,
  v2 skaitļi tmp_id/boundary_calib2.json. Ražošanas kods NAV mainīts.
- v1 (profils ±48 px katram paraugam; platums/nobīde) **noraidīts**:
  pārejas platuma mediāna kontrolēm 24-28 px un sliktajam 32 px,
  maksimums kontrolei 76 px pret sliktā 56 px; nobīde piesātinās
  pie meklēšanas robežas 32 px visiem. Profils mēra apģērba
  ēnojumu/ribas, nevis malas pierādījumu.
- v2 (tā pati 1:4 skala): kontūras paraugam nelīdzenums pret
  21 parauga slīdošo mediānu; normāles profils ±8 ds px; segmentam
  (32 paraugi, solis 8) ņem mediāno profilu un tā maksimālo
  gradientu. Aizdomīgs logs = vismaz 20% paraugu ar nelīdzenumu
  >=1 ds px **un** segmenta gradients <=5 (vāja malas liecība
  avotā). Kandidāta lēmums: >=4 aizdomīgi logi jebkurā 160 paraugu
  kontūras posmā.
- Rezultāts (sliktākais 160 posms): kontroles **1** (160538) un
  **0** (160550); A9 160601 **12**; GrabCut prototips **14**.
  Karogi krīt tieši lietotāja joslā (centri y170..256 ds). Plato
  apgabals stabils: arī pie 25%/grad<=6 kontroles 0, sliktie
  10-11. Slieksnis 4 ir ~ģeometriskais vidus starp 1 un 12.
  Kadra malas iecirtums viens pats neder (GrabCut 56 px/7968 px²,
  bet A9 alfai tikai 112 px²) — paliek kā diagnostika.
- Godīgi ierobežojumi: tikai 2 kontroles no tās pašas sesijas;
  sliekšņi kalibrēti uz šiem pašiem gadījumiem; metrika sedz
  "nelīdzena kontūra tur, kur avota mala ir vāja/defokusēta",
  nevis gludi nobīdītu robežu. Tāpēc ieviešanai obligāti
  sabotāžas testi un validācija uz nākamajām grupām; pie
  neskaidra rezultāta vēlamā uzvedība ir STOP, nevis PASS.
  Krātuve: /home/user 92081291 B.

### §115 GATE_S ieviests checkerī: 160601 vairs neiziet ar viltus PASS (2026-10-25)

- Poga checker_first. `boundary_evidence_gate` (checker_v2.py,
  lokāla matemātika, bez maker importa) + `GATE_S_*` konstantes
  tieši no §114 kalibrācijas. Maker un workflow 2.10 NAV mainīti.
- Testi **111/111 OK** (5 jauni TestGateS). Sabotāža šķir cēloni:
  izplūdusi mala + viļņota kontūra krīt; izplūdusi+gluda iziet;
  asa+viļņota iziet. Konstantes piespraustas testā.
- Checker uz esošā A9: **2/3 PASS (exit 2)** agrākā 3/3 vietā.
  160601 krīt TIKAI GATE_S: sliktākais posms 12 logi pret limitu 4
  (aizdomīgi 20 no 97 vērtētiem; centrs [151,751] — lietotāja
  atzīmētā augšējā kreisā mala). Kontrolēm S = 1 (160538) un 0
  (160550), pārējie vārti nemainīgi PASS. Tieši tas bija mērķis:
  defekta klasi tagad bloķē skaitlis, nevis tikai acs.
- Atvērts apzināti: vārti ir tikai checkerī — maker joprojām
  izrenderē kadru un checker to aptur pēc fakta. Maker spoguļ-
  metrika ar STOP pirms rendera ir atsevišķs solis pēc pogas.
  160601 gaida pārfotografēšanu; grupa kā 3 kadri nepiegādājama.
  Krātuve: /home/user 92716187 B.

### §116 2.11: maker STOP pirms rendera (boundary_uncertain) (2026-10-25)

- Poga maker_stop. Pirms koda pārbaudīts pieņēmums, ka checker
  metrika (kalibrēta uz alfas) strādā arī uz maker binārās maskas:
  160601 worst=12, kontroles 1/0 — tas pats lēmums.
- `boundary_evidence_metric` (engine/masks.py) + config `s_*`
  (krustsargs pret GATE_S_*) + centrāls STOP pēc 1. fāzes, pirms
  profila/rendera — sedz arī --resume/--rerender-saved maskas.
  Statuss `boundary_uncertain` ar iemeslu un centra koordināti;
  kopsavilkumā jauns skaitītājs. Testi **115/115 OK**.
- Attempt 10 (rerender-saved, identity, no-decontam 160550):
  maker **2/3 completed, exit 2** — 160601 apstājās PIRMS rendera
  (maker worst 9 pret limitu 4, centrs [89,792]; binārās maskas
  mēroga noapaļošana pret checker alfas 12, lēmums tas pats),
  kontroles completed (maker worst 1/1). Checker: 2/2 completed
  PASS, meta 1 boundary_uncertain, exit 2. Kolāža tagad satur
  tikai 2 pabeigtos kadrus (nav apstiprināta, nav piegāde).
- Stāvoklis: sistēma šo klasi vairs nevar klusi izlaist nevienā
  posmā. Grupa gaida pārfotografēto 160601; pēc jaunā oriģināla —
  jauns attempt ar precīziem --files. Krātuve: 92793951 B.

### §117 Jauna eksperimenta paraugi: Kiko Kostadinov Tomelilla (2026-10-25)

- Lietotājs norādīja jaunu eksperimentu un lūdza no Slam Jam
  produkta `kiko-kostadinov-clothing-tomelilla-top-white-j359802`
  izvilkt visas 4 bildes kā papildus paraugus, pēc tam gaidīt.
  Lapa ir Shopify: attēlu saraksts ņemts no produkta JSON
  (`...j359802.js`), nevis no JS-renderētās galerijas.
- Saglabāts `uploads/` pilnā izmērā 2000x2500:
  `slamjam_kiko_tomelilla_1.jpg` (priekša, sha256 77507e8af7d2…),
  `_2.jpg` (aizmugure, b67bca2ca4cb…), `_3.jpg` (kakla/birkas
  detaļa, 7b0db03861d8…), `_4.jpg` (piedurknes/apakšmalas detaļa,
  34ea2d2ea4dd…). Kopā +1 998 235 B.
- Dzēšanas tvērums ("visas bildes, tikai priekša/aizmugure") bija
  neskaidrs, tāpēc jautāts ar pogu pēc inventāra (uploads 15,
  output 16, tmp_id 50 attēli). Lietotājs izvēlējās
  **pagaidām neko nedzēst**. Nekas nav dzēsts; aktīvā Uniqlo
  grupa un A10 stāvoklis nemainīti. Gaida nākamos norādījumus.
  Krātuve: /home/user 94409738 B.

### §118 M9 sākts: Slam Jam tuvplānu leņķis un mērogs izmērīti (2026-10-25)

- Lietotāja uzdevums: iemācīties kameras leņķi/attālumu Slam Jam
  tuvplāniem. Metode: detaļa pret atbilstošo kopskatu (SIFT
  homogrāfija; Kiko gludajam audumam tā deģenerējas — noraidīta,
  birka mērīta manuāli). Pilna tabula un brīdinājumi STUDIJAS M9.
- Rezultāts (3 izmērītas detaļas): palielinājums pret kopskatu
  **4.4–6.6x**; optiskā ass **34–41° no plaknes normāles**
  (kamera ~49–56° virs auduma plaknes); rotācija kadrā −14..+5°
  (drīzāk apģērba pagrieziens, ne kameras rullis); fons detaļās
  tikai 6.9–16.7% (kopskatos 55.9–64.5%). Lauka augstums plaknē
  pēc pogas šķērspārbaudes ~22–26 cm. Absolūts attālums/fokuss
  no JPEG nav pierādāms (EXIF bez fokusa).
- Kods nemainīts. Skripts tmp_id/study_slamjam_angles.py;
  palielinājuma rūtiņu kropi pēc mērījuma dzēsti.
  Krātuve: /home/user 94510090 B.

### §119 M9 paplašināts: 6 komplekti, leņķa koridors precizēts (2026-10-25)

- Lietotājs ar pogu izvēlējās vairāk paraugu. No Slam Jam
  publiskā Shopify JSON deterministiski atlasīti 4 apģērbu
  komplekti pa kategorijām (bikses/krekls/jaka/tops), katram
  priekša+aizmugure+2 detaļas; pilna izmēra 2000x2500 bildes
  saglabātas `uploads/slamjam_{junya_denim_pants,
  patagonia_flannel,wrangler_11mjz,jilsander_longsleeve}_*.jpg`
  (+13.5 MB). Visiem 24 Slam Jam failiem EXIF vienādi 6 lauki
  bez fokusa — absolūts attālums joprojām nav pierādāms.
- Metode nemainīga: SIFT homogrāfija detaļa→kopskats ar
  sakarīguma pārbaudi (projektētie stūri + pāru mērogu
  izkliede); deģenerētās noraidītas. Wrangler tumšajam denimam
  SIFT sabrūk vienā punktā arī ar CLAHE/ROI — tā vietā zilās
  birkas taisnstūris (64x30 px kopskatā -> 357x123 px detaļā)
  un pogas platums (5.55x); rāvējslēdzēja detaļai tikai kniežu
  attālums, leņķis nav pierādīts (mēlīte ārpus plaknes).
- Rezultāts (kopā 9 detaļas ar leņķi, 10 ar mērogu): novirze
  no normāles **24–43° (mediāna 34°)**, t.i. kamera
  **47–66° virs plaknes (mediāna ~56°)**; palielinājums
  **3.9–6.6x (mediāna ~4.8x)**; rotācija −15..+5°. Fons
  kopskatos 54.6–66.3%, detaļās 0.0–16.7% (diagonālai
  piedurknei 25.7%). Darba mērķis mūsu uzņemšanai: ~55° virs
  plaknes, koridors 50–60°, rullis 0, apģērbu pagriež
  0 līdz −15°, lauka augstums ~20–30 cm. Pilna tabula
  STUDIJAS M9. Homogrāfija mēra lokālo auduma plakni — daļa
  izkliedes ir apģērba pārlikšana detaļai, ne kamera.
- Kods nemainīts. Pagaidu kandidātu lapa un Wrangler rūtiņu
  attēli pēc mērījuma dzēsti; skripts papildināts ar jaunajiem
  pāriem un puses izšķirtspējas SIFT. Krātuve: /home/user
  107681774 B.

### §120 M9 POC: detaļu simulācija no kopskatiem (2026-10-25)

- Lietotājs precizēja uzdevumu un ar pogām apstiprināja
  simulācijas testu: turpmāk no **2 kadriem (priekša+aizmugure)
  jāizveido 2 tuvplāni Slam Jam ģeometrijā**; zonas izvēlas
  katram apģērbam atsevišķi. Tests ir izņēmums §3.2 (perspektīvas
  transformācija), ražošanā vēl nav ieviests.
- Neredzamā simulācija mfpen komplektam
  (`tmp_id/poc_simulate_details.py`): no kopskatiem vien
  izvēlētas zonas (jostas priekša 1000,560; aizmugures kabata
  1150,560), recepte 56°/M4.8x/−7°/perspektīva 1.22, izeja
  2000x2500 bez asināšanas. Salīdzinājums ar īstajām detaļām:
  `tmp_id/poc_mfpen_compare.jpg` un `poc_mfpen_compare_100.jpg`.
- Mērījumi: avota reģions ~219 tūkst. px = 4.4% no izejas;
  Tenengrad SIM/ĪSTA 67% (josta) un 53% (kabata); Laplacian
  dispersija 4%/2%. Vizuāli: kompozīcija un leņķis atbilst,
  bet birkas/pogas teksts nav salasāms un mikrostruktūras nav.
  POC avots bija jau 2000x2500 web kadrs (sliktākais gadījums);
  no telefona oriģināla avota pikseļu būtu vairāk — jāpārbauda
  uz mūsu grupas materiāla pirms lēmuma par ražošanu.
- Ražošanas kods nemainīts. Rūtiņu attēli zonu izvēlei dzēsti;
  simulētie kadri un salīdzinājuma lapas saglabātas lietotāja
  spriedumam. Krātuve: /home/user 111195334 B.

### §121 M9 POC-2: simulācija no telefona oriģināla (2026-10-25)

- Lietotājs ar pogu izvēlējās testu no pilnas izšķirtspējas
  oriģināla. Avots: Uniqlo Henley kopskats 160538
  (3072x4096); zonas no kopskata vien: kakls/Henley (1430,1600)
  un apakšmala/audums (1450,3150). Etalons: īstā telefona
  detaļa 160550 tai pašai kakla zonai, pārveidota uz 2000x2500.
  Skripts `tmp_id/poc_simulate_uniqlo.py`; salīdzinājumi
  `tmp_id/poc_uniqlo_compare.jpg`, `poc_uniqlo_compare_100.jpg`.
- Mērījumi: avota reģions 0.60 Mpx = 12.0% no izejas (POC-1:
  0.22 Mpx, 4.4%); efektīvais palielinājums 2.89x (POC-1: 4.8x).
  Asums centra ROI pret īsto detaļu: Tenengrad 62%, Laplacian
  dispersija 6% (pret POC-1 uzlabojums 1.9x/5.0x). Vizuāli
  parastā skatā kadrs ir Slam Jam līdzīgs, 100% mērogā adījuma
  mikrostruktūra un birkas teksts joprojām zaudē īstajai detaļai.
- Ieviešanas secinājums: ražošanā simulēt no maskēta
  maksimālās izšķirtspējas avota (MASTER/#F3), ne no papīra
  oriģināla. Ražošanas kods nemainīts; rūtiņu attēli dzēsti.
  Krātuve: /home/user 116845717 B.

### §122 M9 POC-3: simulācijas uzlabojumu varianti (2026-10-25)

- Lietotājs izvēlējās vispirms uzlabot kvalitāti. Fiksēti 6
  varianti kakla zonai (`tmp_id/poc_improve_variants.py`):
  interpolācija CUBIC/LANCZOS4, USM r2/a0.6 vai r3/a1.0,
  lauka augstums avotā 950/1200/1400 px. Lapas:
  `poc_variants_sheet.jpg`, `poc_variants_100.jpg`; pilnā
  izmērā saglabāti C un D varianti.
- Mērījumi (avota daļa no izejas / Laplacian dispersija pogas
  ROI; īstā detaļa 7171): A bāze 12.0%/515; B LANCZOS 497
  (~bez izmaiņām); C +USM0.6 968; D lauks 1200 19.1%/2349;
  E lauks 1400 26.0%/4033; F USM1.0 1697. Pēc acs 100%
  mērogā: C tīrs bez halo, F kraukšķina bez jaunas
  detalizācijas, D/E dabiskāks adījums, bet E vairs nav
  tuvplāns. Ieteiktā recepte: efektīvais palielinājums
  ≤~2.3x (avots ≥~19%), LANCZOS4, USM r2/a0.6. Īsta detaļa
  joprojām asāka. Gaida lietotāja lēmumu par ražošanu.
- Ražošanas kods nemainīts. Krātuve: /home/user 121765193 B
  (POC materiāli tmp_id — pēc lēmuma jāiztīra).

### §123 D recepte ieviesta: closeup.py Slam Jam režīms (2026-10-25)

- Lietotājs ar pogu apstiprināja D receptes ieviešanu. Solis =
  specifikācija + ģenerators + vārti + testi (maker attempt
  integrācija vēl priekšā). WORKFLOW_V2 papildināts ar sadaļu
  "Atvasinātās detaļas" un sarkano līniju izņēmumu tikai šiem
  kadriem: deterministiska perspektīva no MASTER pikseļiem,
  bez ģeneratīvas pārzīmēšanas; galvenie kadri nemainīti.
- `closeup.py` jauns `--mode slamjam` (noklusētais `crop`
  nemainīgs; regresijas skrējiens deva tos pašus logus
  941x1176/1556x1945): ģeometrija 34°/−7°/1.22, LANCZOS4,
  USM 2/60/3, LUT no profila, ēna no jauna izejas mērogā.
  Zonas: `--zones-file` JSON vai automātisks priekšlikums.
  Vārti: palielinājums ≤2.3x, avots ≥19%, segums ≥0.80;
  neizejot fails netiek rakstīts un novecojusi tāda paša
  nosaukuma versija tiek noņemta. Atskaite ar izcelsmi
  `output/tuvplani/_TUVPLANI.json`, faili `*_DETALA_*_ATVASINATA.jpg`.
- Validācija uz Uniqlo 160538 MASTER (zonas
  `tmp_id/zones_uniqlo_s123.json`): kakls un apakšmala ar
  lauku h=1197 px, palielinājums 2.294x, avots 0.190, segums
  0.924/0.844 — abi written. Vārtu atteikums pārbaudīts ar
  src_h=600 (4.58x, 0.048): faili nav rakstīti, vecie noņemti,
  pēc tam labie atjaunoti.
- Testi: +4 (ģeometrija, vārtu robežas, sintētisks renders),
  kopā **119/119 OK**. POC pilna izmēra simulācijas dzēstas
  (lapas un skripti paliek tmp_id); bāzes crop testa faili
  dzēsti. Krātuve: /home/user 117006359 B.
- Atliek pēc apstiprinājuma: iebūvēt maker attempt plūsmā
  (zonu priekšlikums kolāžā, checker atpazīšana, ZIP piegāde
  ar atvasinātajiem kadriem).

### §124 Zonu priekšlikums pēc apģērba tipa (2026-10-25)

- Lietotājs izvēlējās vispirms uzlabot zonu izvēli. Kritērijs
  pirms koda: uz Uniqlo 160538 pirmajai zonai jātrāpa augšējā
  centrā ap kaklu/Henley (manuālais mērķis [1430,1600]),
  otrajai — aprocē vai apakšmalā (manuāli [1450,3050]), ar
  vārtu segumu ≥0.80.
- Bāze pirms izmaiņas: vecais akcentu meklētājs deva
  "detaļa" [1060,1688] (380 px no kakla mērķa, kadrs ar plecu/
  piedurkni) un "zīmols" [1654,2612] (torsa vidus).
- Jauns `pick_slamjam_centers` tikai Slam Jam režīmā (`crop`
  režīms nemainīgs): tips no bbox malu attiecības; augšdaļai
  kakls (centra + hromas/birkas priors, vērtēšana mazākā
  centrālā logā) + aproce no maskas piedurkņu galu klasteriem
  vai apakšmala ar vertikālo prioritāti; apakšdaļai josta +
  kabata vai apakšmala. Ja kandidātu nav — kritiens atpakaļ
  uz veco meklētāju. Zonu fails joprojām pārraksta auto izvēli.
- Pēc izmaiņas uz tā paša MASTER: **kakls [1573,1627]**
  (146 px no mērķa) un **apaksmala [1426,2950]** (103 px no
  mērķa); automātiski ģenerētie kadri iziet vārtus (segums
  0.947/0.943, palielinājums 2.294x; lapa
  `tmp_id/s124_auto_sheet.jpg`). Aproce šim apģērbam netika
  izvēlēta izmērīta iemesla dēļ: aproču kadru segums būtu
  tikai 0.48/0.42 (< 0.80), tāpēc priekšlikums godīgi dod
  apakšmalu.
- Testi: +2 sintētiskie tipu testi; kopā **121/121 OK**.
  Maker/checker/ZIP integrācija joprojām nākamais solis.
  Krātuve: /home/user 117884996 B.
- **Pauze pēc lietotāja lēmuma:** turpināt vēlāk. Atsākot darbu,
  vispirms ar pogām uzdot tos pašus trīs variantus: (1) iebūvēt
  attempt plūsmā, (2) testēt zonu priekšlikumu uz citiem apģērbu
  tipiem, (3) pauze M9 līnijā / atgriezties pie grupām.

### §125 Zonu priekšlikums pārbaudīts uz citiem tipiem; 3 kļūdas atrastas un labotas (2026-10-25)

- Lietotājs izvēlējās testēt uz citiem apģērbu tipiem. Materiāls:
  Slam Jam kopskati (bikses Junya, jaka Wrangler, flanela Patagonia;
  maska ar fona slieksni — tikai šim testam, ne ražošanas ceļš;
  LUT identitāte). Etaloni: Slam Jam īstās detaļas.
- **Atradās 3 reālas kļūdas** (tests bija vajadzīgs):
  1. Bikšu zaru nogalināja attāluma sargs `0.5xsrc_h` — kabatu
     kandidāti (10 logi ar segumu līdz 0.96) ir tuvu jostas centram,
     visi izslēgti → kritiens uz veco meklētāju → divas gandrīz
     vienādas jostas zonas 66 px attālumā. Labojums: biksēm
     `0.15xfw`; kritiens tagad patur labo zonu un pievieno otru
     tikai ar attālumu (bez dublētiem; `pick_centers` izņēmums
     apstrādāts).
  2. Jostas loga mērķis v=0.16 lika logam sniegties virs jostas
     malas (aizmugures renderis 0.787 < 0.80). Labojums: mērķis
     `max(0.16, 0.5*fh/bh)` — logs balstās uz apģērba augšmalu.
  3. `_warp_coverage` bool masku pārvērta par 0/1 bez *255 — visiem
     kandidātiem segums 0.000, verifikācija neko neizslēdza un kods
     atgrieza nesošo augstāko. Labojums: *255 + verifikācija iet
     cauri visam kandidātu sarakstam; regresijas tests pievienots.
- Rezultāts pēc labojumiem (zonas normālkoordinātas u,v):
  bikses priekša josta (0.52,0.31) + kabata (0.35,0.39); aizmugure
  josta (0.52,0.29) + kabata (0.35,0.31 — trāpa īstās _4 aizmugures
  kabatas reģionu); jaka kakls (0.54,0.26) + apakšmala (0.54,0.71);
  flanela kakls (0.48,0.26) + apakšmala (0.45,0.71); Uniqlo tops
  nemainīgs [1573,1627]/[1426,2950]. Visi 3 renderi iziet vārtus
  (0.938/0.926/0.827, 2.29x). Lapa
  `tmp_id/t125_zone_test_sheet.jpg`.
- Asums godīgi: priekšas jostas SIM Tenengrad 154.7 pret īstās 174.9,
  bet lauki atšķiras (mūsu 2.29x pret īstajiem 4.7–6.6x), tāpēc
  skaitļi nav tieši salīdzināmi — tas ir satura, ne asuma spriedums.
- Testi: **122/122 OK** (+1 regresijas). Renderi pēc mērījuma
  dzēsti (atkārtoti ģenerējami ar tmp_id/test_zones_other_types.py).
  Maker/checker/ZIP integrācija joprojām nākamais solis.
- Lietotāja lēmums ar pogu: nākamais tests **uz īstās telefona
  grupas** — gaida jaunos kadrus (ieskaitot pārfotografēto 160601);
  tajā testēs gan zonu priekšlikumu, gan visu plūsmu reālā
  materiālā. Pirms jebkāda maker attempt: inventārs + §91
  caurspīdīgums + `setup_v2.py --check`.

### §126 Uniqlo krekla grupa pilnībā iztīrīta; nākamā grupa — bikses (2026-10-25)

- Lietotājs: krekls tiks pārbildēts viss no jauna; tagad būs
  bikses īstajam testam. Dzēšanas tvērums apstiprināts ar pogu
  (pilna grupas tīrīšana) PIRMS dzēšanas.
- Dzēsts: uploads 3 oriģināli MVIMG_20261020_{160538,160550,
  160601} (25.6 MB) + 4 SS IMG_20261025_* (1.8 MB); output:
  3 MASTER (36.2 MB), 3 PARAUGS (4.1 MB), 12 masku faili,
  3 profili, kolāža, delivery/report/grade JSON, tuvplani
  (2 DETALA + _TUVPLANI.json), audits attempt9/attempt10.
- Pārbaudīts un **paturēts**: audits attempt1/attempt2 — to
  stumbri ir 161746/161944/161959 (vecākas grupas ēnas iterācijas
  laiks), tie nav Uniqlo faili. tmp_id studiju materiāli
  (lapas, skripti) paliek kā M9 pierādījumi.
- Krātuve: 119 654 112 -> **46 810 303 B**. uploads paliek
  24 Slam Jam paraugi + 3 md dokumenti.
- Uniqlo grupas stāvoklis: atiestatīts uz nulli (nav oriģinālu,
  masku, attempt). Sērija "3 neredzētas grupas bez koda labojuma"
  joprojām 0/3 — nākamā (bikšu) grupa skaitīsies tajā.
  Gaida kadru augšupielādi; pēc tās: inventārs + §91 + setup.

### §127 Bikšu grupa sākta: inventārs, §91, orientācija, vide (2026-10-25)

- Augšupielādētas 2 bildes: MVIMG_20261020_160811.jpg (10.08 MB) un
  MVIMG_20261020_161031.jpg (10.37 MB); abas 4096x3072 ainava,
  POCO F7, uzņemtas 2026-10-20 16:08/16:10 (vecās sesijas kadri,
  ne jaunā loga uzstādīšana). Krātuve 46.9 -> 66.8 MB.
  Inventāra lapa ar mērījumiem: tmp_id/bikses_inventars.jpg.
- Pogas: abas bildes = viens apģērbs, priekša+aizmugure, visas;
  virsma = papīrs + redzama grīda stūrosos; §91 caurspīdīgu daļu nav.
- Skaitļi: stūri pelēki [150-170] std 3-4 (tumši izpakavēts
  papīrs), katrā bildē viens tumši brūns izkliedes stūris (koka
  grīda); spilgtais reģions 13-14% RGB [218,218,212]; ekspozīcija
  p50 ~165. Audums (tumši neitrāls, lum<130, |R-B|<=18) 28.6% /
  22.8%; centrā ass (Laplacian var līdz 44 000), apakšējās joslas
  gludas (78-376) — defokuss vēl nav pierādīts, izšķirs maskas
  kvalitāte un GATE_S.
- Orientācija: mani skaitliskie mēģinājumi (galu spraugas,
  erozijas kodols, biezuma profils) deva pretrunīgus rezultātus
  (161031 biezuma maksimums kreisajā pusē pretdāz vecajai piezīmei
  "josta labajā"). Lēmums pēc lietotāja acs: **jostasvieta labajā
  pusē abām bildēm** -> --rotate STEM:270 (90° pret pulksteņrādītāju,
  labā mala uz augšu) abiem. 160811 saskan ar biezuma maksimumu
  85% no kreisās; 161031 saskan ar vēsturisko piezīmi.
- setup_v2.py: vide atjaunota (piespraudes OK, ISNet sha256 OK).
  Nākamais: attempt 1 ar rotācijām, tad kolāža lietotājam.

### §128 Bikšu grupa: attempt 1-2, detaļas, checker 2/2 PASS (2026-10-25)

- Attempt 1 (rotācijas 270 abām): 160811 maska isnet (segums
  0.383), 161031 AI QA noraidīja sadrumstalotu silueti (0.584<0.6),
  apmales retry pieņēma (0.367, overflow 0.0). Checker: **GATE_K
  krāsu godīgums FAIL abām** — auto WB (zilais +7.3% siltā papīra
  [183,180,172] dēļ) pavirzīja auduma b* par −2.72/−2.52 (limits
  2.5). Pārējie vārti zaļi (C/Q/S/P/H/A2/B/D/R/T), defokusa nav
  (GATE_S 0 aizdomīgu logu abās).
- Attempt 2 `--rerender-saved --wb-mode identity` (maske pārmantota;
  §116 precedents): **checker 2/2 PASS**. Audums paliek
  nofotografētajā krāsā, fons aizvietots ar #F3F3F3.
- Atvasinātās detaļas no jaunā profila: aizmugure (161031)
  automātiski josta (segums 0.847) + kabata (0.834), palielinājums
  1.77x; priekša (160811) tipa loģika jostas zonu neatrada —
  staras izpletstas, jostas joslā nav neviena kandidāta ar segumu
  >=0.70 (sprauga starp starām iekrīt laukā). Vārtus nemīkstināju;
  mērīta apakšmalas zona caur zones-file: segums 0.960, 1.73x.
  Kopā 3 detaļas, visas `_ATVASINATA`, izcelsme _TUVPLANI.json.
- Krātuve: 66.8 -> 99.0 MB. Rezultātu lapa
  tmp_id/bikses_rezultats.jpg; kolāža output/V2_KOLAZA.jpg.
  Gaida lietotāja apstiprinājumu (§3.4): kolāža -> Apstiprināt/
  Noraidīt -> ZIP -> dzēst pēc "Lejupielādēju".
