# LOOP — Mājas bilžu pārtaisīšana pēc parauga

> Izveidots pēc loop engineering principa: cilvēks (tu) definē mērķi un pieņem
> galalēmumu, sistēma (šis loops) pati dara → pārbauda → labo → atkārto,
> līdz izpildās PĀRBAUDĀMS "gatavs" nosacījums vai nostrādā STOP noteikums.

> **Pašreizējais ražošanas dzinējs ir Workflow v2.1** (`WORKFLOW_V2.md`,
> `workflow_v2.py`, `checker_v2.py`). Šajā dokumentā zemāk aprakstītie v1
> modeļi un Gate A pikseļu identitāte ir vēsturiskā atsauce un v1
> palīgfunkciju specifikācija. Starta pogu protokols, vienas aktīvās
> grupas princips, kolāža pirms ZIP un dzēšana tikai pēc lejupielādes
> apstiprinājuma joprojām ir saistoši arī v2.1. Tāpat saistošs ir
> orientācijas noteikums: šķērsām nofotografētu apģērbu pirms apstrādes
> ar bezzaudējumu 90° pagriezienu novieto vertikāli dabiskā pozīcijā
> (detalizēti `WORKFLOW_V2.md` orientācijas sadaļā).

## 1. TRIGERIS UN STARTA PROTOKOLS
Lietotājs iesniedz jaunu mājas bilžu komplektu mapē `uploads/` un norāda
parauga komplektu (slamjam_*.jpg), ja paraugs mainās.

Pēc **katras jaunas produktu foto augšupielādes** vai lietotāja paziņojuma
par jaunu bilžu grupu loops pirms jebkādas apstrādes:
1. tikai inventarizē jaunās produktu bildes un izmēra krātuvi;
2. ar saskarnes izvēles pogām jautā: **“Vai šīs ir visas šīs grupas
   bildes?”** Pogas: `Jā, šīs ir visas — sāc darbu` /
   `Nē, vēl pievienošu`;
3. ja izvēlēts `Nē, vēl pievienošu`, loops apstājas, gaida nākamo
   augšupielādi un pēc tās jautājumu uzdod atkārtoti;
4. tikai pēc `Jā, šīs ir visas — sāc darbu` loops fiksē pilno komplekta
   sarakstu `PROGRESS.md` un sāk segmentāciju/renderēšanu.

Pirms šī apstiprinājuma nedrīkst sākt jaunas grupas segmentāciju,
renderēšanu vai iterāciju. Lietotāja komandu īsais ceļvedis ir
`LOOP_KOMANDAS.md`.

Pašreizējā v2.1 vide (ja sandbox iztīrīts):
`python3 setup_v2.py`, pēc tam `python3 setup_v2.py --check`.
Jaunas grupas pamatplūsma ir `workflow_v2.py --preflight --files ...`,
`workflow_v2.py --attempt 1 --files ...` un `checker_v2.py` (skat.
`WORKFLOW_V2.md`). `loop.py` un `checker.py` paliek kā v1 atsauce un
koplietojamo deterministisko renderēšanas/malas palīgfunkciju avots.

## 2. MĒRĶIS (izmērīts no parauga, nevis izdomāts)
Paraugs = Slam Jam produkta fotogrāfijas (mfpen bikses), 2000×2500 px:
- Audekls 2000×2500 (malu attiecība 4:5)
- Fons: vienmērīgs **#F3F3F3** (RGB 243,243,243) — izmērīts parauga stūros
- Pilnais kadrs: apģērbs plakani no augšas, centrēts, augstums ~79% no kadra,
  augšējā mala ~11%, apakšējā ~10% (bikšu bbox: x 20.7–80.7%, y 11.2–89.9%)
- Tuvplāni: apģērbs aizpilda ~90% kadra, fons redzams tikai šaurās joslās
- Mīksta, izkliedēta ēna apģērba labajā/apakšējā pusē
- Nekādu cilvēku, grīdas, mēbeļu vai citu priekšmetu

## 3. SARKANĀS LĪNIJAS (nedrīkst pārkāpt nekad)
1. **Apģērba pikseļi = oriģināls.** Aizliegta ģeneratīva AI pār-zīmēšana
   (generate_image u.tml.) uz apģērba: nedrīkst mainīt tekstūru, krāsu,
   krokas, birkas, pogas, defektus vai "izdomāt" neredzamas daļas
   (piem., mugurpusi, ja tā nav nobildēta).
2. Mainīt drīkst tikai to, kas NAV apģērbs: fonu, ēnu fonā, audekla izmēru,
   kadrējumu (apgriešanu). Apģērbu nedrīkst rotēt/deformēt (tas pār-interpolētu
   pikseļus un mainītu proporcijas) — MASTER versijā nedrīkst arī mērogot.
3. Ja nosacījuma "tieši kā paraugā" dēļ būtu jāpārkāpj 1. vai 2. punkts,
   priekšroka ir pikseļu saglabāšanai, un atkāpe tiek ierakstīta PROGRESS.md.

### Pretrunas atrisinājums: divas izejas versijas
"Tieši 2000×2500" + "oriģinālie pikseļi" vienā failā burtiski nesanāk, jo
mērogošana uz 2000×2500 pār-interpolē pikseļus. Tāpēc katrai bildei top:
- **MASTER_1to1 (PNG, bezzudumu):** apģērbs 1:1 oriģinālmērogā un pozīcijā,
  pikseļi 100% identiski avotam (pārbauda checker.py skaitliski),
  nomainīts tikai fons → #F3F3F3 + mīksta ēna fonā.
- **PARAUGS_2000x2500 (JPG q95):** veikalam gatavais kadrs pēc parauga
  (2000×2500, #F3F3F3, centrēts, parauga malas, ēna). Apģērbs iegūts no
  MASTER tikai ar deterministisku samazināšanu (Lanczos) — bez ģenerēšanas.

## 4. IZPILDE (maker: loop.py)
Katrai bildei:
1. Segmentē apģērbu pēc kadra tipa, kas fiksēts PROGRESS.md kartējumā:
   - **Pilnais kadrs** (`--mode full`, primāri rembg
     `birefnet-general-lite` caur ONNX Runtime): silueta maska, atstāj
     tikai LIELĀKO komponenti (automātiski izmet kājas/apavus u.c.
     atsevišķus objektus), aizpilda maskas "caurumus". Vispirms veic
     pilota pārbaudi uz vienas bildes; ja Lite neiziet vārtus, nākamais
     mēģinājums ir pārbaudītais `isnet-general-use`.
     (`u2net` izmēģināts iterācijā 1 — nogrieza piedurkni, noraidīts.)
   - **Tuvplāns** (`--mode closeup`, GrabCut): audums te nav "objekts uz fona",
     tāpēc silueta modeļi kļūdās (iterācijā 2 tie izvēlējās birku/pogas).
     Tā vietā: kodu vārdnīcā `CLOSEUP_SEEDS` (loop.py) pēc vizuālas kartēšanas
     norādīti tikai DROŠIE fona un auduma apgabali + drošs audums = izteikta
     vafeļu tekstūra; precīzo robežu atrod GrabCut gar reālajām malām.
     Jaunam tuvplānam bez sēklām → STOP-eskalācija, nedrīkst minēt.
     Sēklu opcijas: `use_tex_fg=False` (ja fona virsmai pašai ir tekstūra, piem.
     papīra šķiedras) un `top_edge_snap=(y0,y1)` (gandrīz horizontālai auduma
     augšmalai robežu pievelk spēcīgākajai gaišuma pārejai papīrs→audums,
     jo GrabCut mēdz vilkt robežu pa vecās ēnas ārmalu).
     **Caurumu aizpildīšanas aizliegums (iter.6):** pēcapstrāde nedrīkst
     aizpildīt nevienu fona komponenti, kurā atrodas drošā fona (`GC_BGD`)
     sēkla. Šāda komponente var būt apzināta ārējā sprauga starp auduma
     slāņiem, nevis caurums audumā; tās aizpildīšana atjauno jau izslēgtu
     galda/ēnas laukumu kā melnu bloku.
2. Kompozīcija: kur maska → oriģinālais pikselis; kur nav → #F3F3F3.
   Ēna = nobīdīta (+x,+y), izpludināta maska, zīmēta TIKAI fonā.
   **Malu alfa apstrāde (iter.7):** bināro audita masku nemaina. No tās
   parakstītā attāluma lauka veido alfa pāreju (pusplatums 1,6 avota px),
   kontūru izlīdzina ar Gaussian σ=1,6 un pārejai atjauno kontrastu 1,65.
   Alfa ir piespiedu kārtā 255 vismaz 5 px apģērba iekšienē un 0 vismaz
   5 px ārpusē; tieši ārpus maskas RGB paplašina ar tuvāko apģērba krāsu,
   lai vecā fona krāsa neieplūstu pārejā. Attēlu pašu neblurē.
3. Saglabā MASTER (PNG), bināro masku un mīkstināto alfa (audits), PARAUGS (JPG).
   RGBA samazināšanu veic premultiplicētā alfa telpā, lai caurspīdīgo pikseļu
   paslēptā vecā fona krāsa neradītu oreolu:
   - Pilnais kadrs (apģērba laukums <70% kadra): apģērba bbox proporcionāli
     (bez deformācijas) ievieto centrālajā zonā x 6–94%, y 10–90%, centrē.
   - Tuvplāns (≥70%): visu kadru proporcionāli mērogo ar cover uz 2000×2500
     (full-bleed līdz audekla malām, bez sānu joslām); 3:4→4:5 dēļ centrāli
     apgriež tikai augstuma pārpalikumu. MASTER saglabā pilnu kadru 1:1.
4. Ieraksta rezultātu report.json un PROGRESS.md (atmiņa ārpus sarunas).

## 5. PĀRBAUDE (checker: checker.py — neatkarīgi no maker)
"Gatavs" tikai ja VISI vārti iziet:
- **A. Pikseļi:** maskas iekšienē (erodēta par 5px) MASTER == oriģināls
  pikselis-pikselī: max|diff| = 0, vienādo pikseļu īpatsvars = 100%.
- **B. Fons:** fonā ārpus apģērba un ēnas zonas visi paraugpunkti == (243,243,243).
- **C. Maska vesela:** apģērba segums 15–98% kadra; lielākā komponente ≥95% maskas.
- **D. Parauga formāts:** PARAUGS ir tieši 2000×2500; stūri (kur nav apģērba)
  = 243±3 (JPEG tolerance).
- **E. Vizuāla pārbaude (aģents apskatās katru rezultātu):** nav oreola
  (vecā fona apmales), nav nogrieztu piedurkņu/malu, nav palikušu kāju/
  priekšmetu, ēna izskatās kā paraugā (mīksta, nevis melna kontūra),
  tuvplānos cover kadrējums nav nogriezis birku/pogas (subjektu).
- **F. Pilns kadrs (tuvplāniem, no iterācijas 4):** PARAUGS maska sasniedz
  kadra ārējo rindu/kolonnu vismaz 3 no 4 malās ≥50% apmērā — t.i., audums
  iziet no kadra pie pašas malas kā oriģinālā un paraugā, bez joslām.
- **G. Fona atlieku audits (no iterācijas 5, pēc lietotāja atrasta defekta):**
  katrai bildei piezūmēti (audita lapas output/audits/) apskata VISAS maskas
  robežas pret oriģinālu. "Ideāla maska" šeit nozīmē: nav neviena redzama
  vecās virsmas (papīra/galda) vai uz tās mestās ēnas pleķa maskas iekšienē
  un nav apģērba "iekodienu"; pieļaujama tikai ≤2px antialias pāreja uz
  fiziskās auduma malas. Strīdīgās tumšās zonās papildus salīdzina oriģinālu,
  MASTER un maskas pārklājumu pikseļu mērogā un skaitliski lokalizē tumšos
  pikseļus; ēnā esošu īstu audumu nedrīkst sajaukt ar gludu galda spraugu.
  Atrasts defekts → sēklas/poligona korekcija CLOSEUP_SEEDS un atkārtots
  audits; rezultātu fiksē MASKU_AUDITS.md.
- **H. Malas alfa kvalitāte (no iterācijas 7):** checker no saglabātās
  `*_ALPHA.png` pārbauda, ka 5 px kodolā alfa visur ir 255, >5 px ārpus
  binārās maskas alfa visur ir 0, daļēji caurspīdīgie pikseļi atrodas ne
  tālāk kā 5,1 px no robežas un alfa laukuma segums no binārās maskas
  atšķiras ne vairāk kā par 0,0025. Papildus veco/jauno variantu salīdzina
  pikseļu palielinājumā: nedrīkst būt plata oreola, "ziepjainas" malas vai
  pazudušu auduma šķiedru; dabiska adījuma nevienmērība nav defekts.

## 6. ATKĀRTOŠANA UN STOP NOTEIKUMI
- Maks. **3 mēģinājumi** vienai bildei. Katrs nākamais mēģinājums MAIN stratēģiju:
  1) u2net maska, slieksnis 128, erozija 1px pret oreolu;
  2) isnet-general-use maska (cits modelis);
  3) cits slieksnis/erozija pēc checker/vizuālas kļūdas iemesla.
- STOP-uzvara: visi piemērojamie A–H vārti iziet → bilde atzīmēta DONE.
- STOP-eskalācija: pēc 3 mēģinājumiem vārti neiziet → loops apstājas,
  ieraksta iemeslu PROGRESS.md un prasa lēmumu cilvēkam (ārējā cilpa = tu).
  Loops NEKAD pats nepāriet uz ģeneratīvu pār-zīmēšanu, lai "izietu vārtus".

## 7. ATMIŅA / STĀVOKLIS
- `PROGRESS.md` — kas gatavs, kas neizdevās, ar kādu stratēģiju, atkāpes.
- `output/report.json` — skaitlie checker rezultāti katrai bildei/mēģinājumam.
- `output/masks/` — binārās maskas un `*_ALPHA.png` auditam (var redzēt gan
  to, kas tika uzskatīts par apģērbu, gan faktisko malas caurspīdīgumu).

### Krātuves higiēna (pastāvīgs lietotāja noteikums)
- Pirms un pēc katras iterācijas izmēra `/home/user` un `loop_bildes`
  (`du -sh`); mērķis ir darba krātuvi turēt pēc iespējas mazāku un zem
  100 MB, ja vien aktuālie gala faili to atļauj.
- Pastāvīgi glabā tikai aktuālos `MASTER`, `PARAUGS`, binārās/ALPHA/
  PARAUGS maskas, `report*.json`, kopskatu, kodu un dokumentus.
- Arhīvus A/B salīdzinājumiem drīkst turēt tikai notiekošās iterācijas
  laikā. Tiklīdz checker un vizuālais audits ir iziets un skaitļi/secinājumi
  ierakstīti dokumentos, dzēš vecos arhīvus, diagnostikas/testa/audita
  attēlus, SOFTMASK dublikātus un `__pycache__`.
- Lietotāja oriģinālus un paraugus `uploads/` bez atsevišķa lietotāja
  lēmuma nedzēš. 8. sadaļā noteiktais lejupielādes apstiprinājums ir šāds
  lēmums par piegādāto produktu grupu; atkārtoti izmantojamās parauga
  atsauces bez atsevišķas norādes saglabā.
- MASTER/maskas PNG saglabā ar `optimize=True` un noklusēto
  `compress_level=6` (bezzudumā; pikseļi nemainās). 9. līmeni lieto tikai
  tad, ja vieta ir kritiskāka par laiku: tas ir ~4× lēnāks par 6. līmeni,
  bet dod tikai ~3,5% mazāku failu. Maker beigās izdrukā `KRĀTUVE:` izmēru.

## 8. CILVĒKA LOMA (outer loop) UN PIEGĀDES PROTOKOLS
Pirms komplekts tiek pasludināts par gala rezultātu, loops no **visām**
aktuālajām `PARAUGS_2000x2500` bildēm izveido vienu kopīgu kolāžu un
parāda to lietotājam. Šajā posmā `.zip` arhīvu vēl neveido.

Apstiprinājumus lietotājam vienmēr prasa ar saskarnes izvēles pogām, lai
viņam nebūtu jāraksta apstiprinājuma teksts: kolāžai —
`Apstiprināt` / `Noraidīt`, lejupielādei —
`Lejupielādēju — dzēst grupu` / `Vēl nedzēst`. Brīvs teksts vajadzīgs
tikai tad, ja lietotājs noraida un vēlas aprakstīt vajadzīgo labojumu.

Tu kolāžu apstiprini vai noraidi. Noraidījums ar iemeslu (piem., "ēna par
stipru") = jauna loopa iterācija ar mainītu parametru; pēc labojumiem
kolāža tiek izveidota un parādīta atkārtoti.

Tikai pēc skaidra lietotāja apstiprinājuma loops izveido vienu `.zip`
arhīvu ar visām apstiprinātajām gala `PARAUGS_2000x2500` bildēm un
pasniedz to kā gala piegādi. Bez šī apstiprinājuma komplekts nav gala
rezultāts.

Darba telpā vienlaikus tur tikai vienu aktīvu produktu bilžu grupu. Kad
lietotājs ar izvēles pogu `Lejupielādēju — dzēst grupu` apstiprina, ka
`.zip` ir lejupielādēts, šīs grupas attēlu failus — grupas avotus
`uploads/`, `MASTER`, `PARAUGS`, maskas, kolāžu un `.zip` — no darba
telpas dzēš. Saglabā loopa kodu, dokumentāciju, īsu tekstuālu progresa
vēsturi un atkārtoti izmantojamās parauga atsauces. Bez lejupielādes
apstiprinājuma grupu nedzēš. Soli izpilda `close_group.py STEM…`
(bez `--yes` tikai parāda sarakstu un atbrīvotos baitus; `.zip` ir
sarakstā obligāti — 2026-10-23 tas tika aizmirsts un palika darba telpā).
