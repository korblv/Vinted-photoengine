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
