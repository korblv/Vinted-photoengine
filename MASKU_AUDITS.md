# MASKU AUDITS — G vārti (fona atlieku audits), iterācijas 5–7

Metode: katrai bildei no MASTER izveidotas piezūmētas audita lapas
(`output/audits/audits_<kods>.jpg`: pilnajam kadram 4 kvadranti, tuvplāniem
augšas+apakšas joslas pilnā platumā), aizdomīgās vietas papildus pārbaudītas
ar koordinātu režģi oriģināls-vs-MASTER un 2× tuvplānu.
Kritērijs: nav neviena redzama vecās virsmas (papīra/galda) vai uz tās mestās
ēnas pleķa maskā; nav apģērba "iekodienu"; ≤2px antialias pāreja uz fiziskās
auduma malas ir pieļaujama. Skaitliskie vārti A–F: `output/report.json` (5/5 PASS).

| Bilde | Kas pārbaudīts | Atradums | Statuss pēc iter.5 |
|---|---|---|---|
| 160538 (priekšpuse) | Viss siluets 4 kvadrantos: apkakle, piedurknes, paduses, apakšmala | Nav fona atlieku; lietotājs jau bija apstiprinājis | ✅ Bez izmaiņām |
| 160550 | Augša pilnā platumā; labais plecs ar režģi (x 0.62–1.0, y 0.16–0.38); kreisais plecs ar režģi; vīle 2× zūmā | **Defekts (atrada lietotājs):** papīra/ēnas ķīlis aiz apkakles x~0.82–0.92, y~0.285–0.315 + mazs atlikums zem tā. Kreisā puse tīra (brūnais = apkakles iekšpuses audums) | ✅ Izlabots: 2 BG sēklas ķīlī (CLOSEUP_SEEDS). Ķīļa zonā "auduma" īpatsvars kritās 0.36→0.05 (atlikums = īstā vīles auduma strēmele, pārbaudīta 2× zūmā — redzams adījums un vīle) |
| 160601 | Augša ar režģi pilnā platumā (y 0.06–0.34); apakša = audums | Robeža precīzi seko apkaklei/pleciem; līmlente un priekšmets augšā pilnībā noņemti | ✅ Bez izmaiņām |
| 160608 | Augšmala (snap robeža) pilnā platumā; apakša = audums | Robeža iet pa auduma augšējo vīli, papīra pleķa vairs nav (sal. iter.3) | ✅ Bez izmaiņām |
| 160645 | Apakša ar režģi (kreisā puse + labā puse atsevišķi); augša/labā mala = audums | **Papildu defekts (atrada audits):** galda plakne savā ēnā — diagonālā ēnas josla zem augšējās ieloces un sprauga zem apakšējās malas — bija klasificēta kā audums (~4.4% kadra) | ⚠️ Iter.5 daļēji izlabots (segums 0.929→0.886), bet secinājums par apakšmalu bija nepilnīgs; galīgā korekcija veikta iter.6 zemāk |

Secinājums pēc iterācijas 5: 160538, 160550, 160601 un 160608 audita lapās
vecā fona atlieku vairs nebija. 160645 secinājums izrādījās priekšlaicīgs un
tika pārskatīts iterācijā 6.
Vecās (pirms labojuma) 160550/160645 versijas: `output/archive_iter4_pirms_masku_labojuma/`.

## Iterācijas 6 papildinājums — 160645 apakšmala

Lietotājs pēc iter.5 norādīja uz melniem pikseļiem 160645 apakšā. Atkārtotā
pārbaude apstiprināja defektu: PARAUGS pēdējās 50 rindās bija 5 625 pikseļi
ar vidējo luminanci <60, galvenokārt zem baltās apakšmalas izvirzītā tumšā
blokā. Salīdzinājums ar oriģinālu parādīja, ka tas pārsvarā bija galds/sprauga
dziļā ēnā starp auduma slāņiem, nevis apģērbs.

Cēlonis bija divkāršs:
1. apakšējās spraugas drošā fona sēkla vēl nesniedzās pietiekami tālu gar
   vīles slīpumu un līdz apakšējā ribotā slāņa fiziskajai malai;
2. vispārīgā mazo “caurumu” aizpildīšana varēja atjaunot jau ar sēklu apzināti
   izslēgtu ārējo spraugu kā apģērbu.

Labojums `loop.py`: caurumu aizpildīšana tagad izlaiž katru fona komponenti,
kurā ir `GC_BGD` sēkla, un 160645 apakšējās spraugas poligons seko vīles
slīpumam līdz kadra apakšai un x≈0,690. Pēc pārpalaišanas segums ir 0.8819,
A kodols 11 078 083 px ar max diff 0, un pēdējās 50 rindās pikseļu ar
luminanci <60 skaits kritās no 5 625 līdz 407. Atlikušie ir lokalizēti
x=1275–1994; pikseļu mēroga salīdzinājums
(`output/audits/zoom_160645_apaksa_iter6_pikseki.jpg`) apstiprina, ka šaurā
tumšā josla pie x≈0,685–0,700 ir ēnā esošā apakšējā auduma slāņa sānu mala,
kas savienojas ar riboto priekšpusi, bet gluda galda sprauga pa kreisi ir
ārpus maskas. Atjaunotas arī `audits_160645.jpg` un `PARSKATS_5_bildes.jpg`.
Iter.5 160645 PARAUGS saglabāts `output/archive_iter5_pirms_apaksas_labojuma/`.

Piezīme par procesa kļūdu: pirmajā iter.5 palaišanā 160550 sēkla netika
pielietota (paralēli labojumi loop.py pārrakstīja viens otru) — to noķēra
failu hash salīdzinājums ar arhīvu (identisks = labojums nav noticis),
pēc kā sēkla pielikta atsevišķi un pārbaude atkārtota. Tāpēc kopš šīs
iterācijas pēc katras pārpalaišanas salīdzina arī failu hash pret arhīvu.

## Iterācijas 7 papildinājums — malu kvalitāte visām bildēm

Pēc lietotāja novērojuma par vietām robainām drēbju maliņām binārās maskas
saturu nemainīja, bet visām piecām bildēm no jauna izveidoja malas alfa:
parakstītā attāluma pāreja ±1,6 px, kontūras izlīdzināšana σ=1,6 un
kontrasta atjaunošana 1,65. Tieši ārpus maskas krāsu paplašināja ar tuvāko
apģērba krāsu, bet PARAUGS samazināšanu pārcēla uz premultiplicētu alfa.
Checker H vārti visām bildēm PASS: kodola alfa minimums 255, tālu ārpus
maskas maksimums 0, daļējā alfa ne tālāk par 2,0 px no robežas un alfa
laukuma delta pret bināro masku ≤0,000001. Detalizēts protokols un testa
variantu izvēles pamatojums: `MALU_AUDITS_ITER7.md`.

Krātuves piezīme: šajā protokolā minētās pagaidu audita lapas, režģi un veco
iterāciju arhīvi pēc auditu noslēgšanas un skaitļu fiksēšanas ir dzēsti pēc
lietotāja noteikuma par maksimāli brīvu darba krātuvi. Aktuālie MASTER,
PARAUGS, maskas/ALPHA un checker JSON ir saglabāti.
