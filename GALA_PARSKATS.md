# GALA PĀRSKATS — Uniqlo henley komplekts pēc parauga

Parauga nosacījumi (izmērīti): audekls 2000×2500, fons #F3F3F3 (243,243,243),
apģērbs centrēts plakani, mīksta ēna, bez cilvēka/grīdas/priekšmetiem.
Sarkanā līnija: apģērba pikseļi netika ģenerēti — MASTER (PNG) ir 1:1 ar oriģinālu,
PARAUGS (JPG 2000×2500) ir tikai deterministiski samazināts no MASTER.

## Rezultāti pa bildēm

| Bilde | Saturs | Stratēģija | Maska | A pikseļi (max diff, kodols) | B fons | D 2000×2500 | E vizuāli | F pilns kadrs | H malas |
|---|---|---|---|---|---|---|---|---|---|---|
| 160538 | Pilnais kadrs no priekšas | isnet-general-use (iter.2), malu alfa (iter.7) | 0.403 | 0 uz 4,995,502 px | 100.0% #F3 | PASS | PASS (aģents) + apstiprināts (lietotājs) | — (silueta kadrs) | PASS |
| 160550 | Tuvplāns: izgriezums + birka | GrabCut + sēklas (iter.3), cover (iter.4), maskas labojums (iter.5), malu alfa (iter.7) | 0.724 | 0 uz 9,090,528 px | 100.0% #F3 | PASS | PASS (aģents, G/H audits) | PASS (3/4 malas ≥50%) | PASS |
| 160601 | Tuvplāns šķērsām: pogas | GrabCut + sēklas (iter.3), cover (iter.4), malu alfa (iter.7) | 0.804 | 0 uz 10,099,475 px | 100.0% #F3 | PASS | PASS (aģents, H audits) | PASS (3/4) | PASS |
| 160608 | Tuvplāns: izmēra birka L | GrabCut, bez tex sēklām + top_edge_snap (iter.3c), cover (iter.4), malu alfa (iter.7) | 0.639 | 0 uz 8,017,976 px | 100.0% #F3 | PASS | PASS (aģents, H audits) | PASS (3/4) | PASS |
| 160645 | Tuvplāns: sastāva birka | GrabCut + sēklas (iter.3), cover (iter.4), maskas labojumi (iter.5–6), malu alfa (iter.7) | 0.882 | 0 uz 11,078,083 px | 100.0% #F3 | PASS | PASS (aģents, G/H audits) | PASS (3/4) | PASS |

**Kopā: 5/5 bildes iziet visus piemērojamos vārtus A–H** (G = fona atlieku
audits, H = malu alfa audits; skat. MASKU_AUDITS.md un MALU_AUDITS_ITER7.md).

Iterācija 7 (pēc lietotāja novērojuma par vietām robainām maliņām): attēlu
pašu neblurēja. Visām bildēm no nemainītajām binārajām maskām izveidoja jaunu
malas alfa — attāluma pāreju izlīdzināja un tai atjaunoja kontrastu; pievienoja
priekšplāna krāsas paplašināšanu un premultiplicētu RGBA samazināšanu.
Pikseļu salīdzinājumā diagonālās/izliektās malas ir tīrākas bez plata oreola,
bet dabiskā adījuma nevienmērība saglabāta. H vārti apstiprina, ka daļējā
alfa atrodas ne tālāk kā 2,0 px no robežas un kodola pikseļi joprojām ir
identiski oriģinālam.

Iterācija 6 (pēc lietotāja norādes par melniem pikseļiem 160645 apakšā):
atkārtots pikseļu mēroga audits atrada, ka zem baltās apakšmalas vēl bija
palicis ēnā esoša galda/spraugas bloks. Izlabota gan apakšējās spraugas sēkla,
gan vispārīgā caurumu aizpildīšana (tā vairs nedrīkst atjaunot komponenti ar
drošā fona sēklu). Tumšo (<60) pikseļu skaits pēdējās 50 rindās kritās no
5 625 līdz 407; atlikušā šaurā tumšā josla ir īstā apakšējā auduma slāņa sānu
mala. Pārējās 4 bildes šajā iterācijā nav mainītas.

Iterācija 5 (pēc lietotāja atrasta papīra pleķa 160550 bildē): veikts pilns
masku audits visām 5 bildēm piezūmētās robežās. 160550 noņemts papīra/ēnas
ķīlis aiz apkakles; 160645 papildus atrasta un noņemta lielākā galda plaknes
daļa tās ēnā. Pārējās 3 bildes auditā tīras, bez izmaiņām.

Iterācija 4 (pēc lietotāja atgriezeniskās saites): tuvplāni pārkadrēti no
contain (1875×2500 + sānu joslas — audums izskatījās nogriezts pirms malas)
uz full-bleed cover 2000×2500 kā parauga detaļu kadros. Sānu malas tagad
netiek grieztas nemaz; 3:4→4:5 dēļ centrāli apgriezti tikai ~6.25% augstuma
(augša+apakša). MASTER faili joprojām saglabā pilnu neapgriezto kadru 1:1.
Vecie contain varianti pēc iterācijas noslēguma dzēsti saskaņā ar krātuves
higiēnas noteikumu; aktuālie MASTER joprojām saglabā pilnu kadru.

## Faili
- `output/Uniqlo_Polo_20261020_GALA_BILDES.zip` — pēc kolāžas apstiprināšanas
  izveidots gala arhīvs ar visām 5 publicēšanai gatavajām bildēm
- `output/paraugs/*_PARAUGS_2000x2500.jpg` — publicēšanai gatavās bildes pēc parauga
- `output/master/*_MASTER_1to1.png` — 1:1 meistari (apģērbs pikselis-pikselī = oriģināls)
- `output/masks/` — binārās maskas un `*_ALPHA.png` auditam; `output/report.json` — skaitliskie checker rezultāti
- `MALU_AUDITS_ITER7.md` — malu variantu testi, izvēlētie parametri un H rezultāti
- `output/PARSKATS_5_bildes.jpg` — visu 5 PARAUGS bilžu pārskata lapa vienam skatienam
- Diagnostikas un veco iterāciju attēli pēc secinājumu fiksēšanas dokumentos
  ir dzēsti, lai darba krātuve paliktu pēc iespējas brīva

## Atkāpes (apzinātas, saskaņā ar LOOP.md sarkanajām līnijām)
- Apģērbs nav rotēts/iztaisnots un apgaismojums UZ apģērba nav labots — krokas un
  mājas gaisma paliek kā oriģinālā, jo citādi tiktu pārkāpta pikseļu prasība.
- Krekls ar izplestām piedurknēm dabiski aizņem platāku kadru nekā parauga bikses;
  ievērots parauga fons/audekls/centrējums/ēna, nevis bikšu silueta proporcijas.
- Mugurpuses kadra avotā nav — loops to neizdomāja.

## Nākamais solis (tavs lēmums — ārējā cilpa)
Kolāža ir lietotāja apstiprināta, gala `.zip` izveidots un lejupielāde
apstiprināta ar izvēles pogu. Saskaņā ar `LOOP.md` 8. sadaļu šīs grupas
attēlu faili pēc piegādes no darba telpas ir dzēsti; šis pārskats paliek
kā tekstuāla vēsture.
Jaunam komplektam: ieliec bildes uploads/, loops atkārtos LOOP.md; jauniem
tuvplāniem būs vajadzīgs sēklu kartējums (to izdaru es pēc bilžu apskates).
