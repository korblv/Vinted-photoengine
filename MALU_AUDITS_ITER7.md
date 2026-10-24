# MALU AUDITS — iterācija 7

Mērķis: samazināt vietām redzamo kontūras robainumu, neblurējot pašu apģērba
attēlu un nemainot jau apstiprināto bināro masku saturu.

## Testētie varianti

Pirms ražošanas 160538, 160550 un 160645 malās pikseļu palielinājumā
salīdzināja:

1. pašreizējo alfa (`GaussianBlur 5×5, σ=1,0` uz binārās maskas);
2. tikai parakstītā attāluma pāreju ±1,6 px;
3. guided-filter alfa variantus;
4. kontūras izlīdzināšanu + alfa kontrasta atjaunošanu;
5. guided/smooth kombinācijas.

Guided varianti diagonāles izlīdzināja, bet vietām atstāja platāku pelēku
oreolu un pārāk mīkstu pāreju, tāpēc ražošanā tos neizmantoja. Testa lapas
tika apskatītas parametru izvēlei un pēc secinājumu ierakstīšanas dzēstas
saskaņā ar krātuves higiēnas noteikumu.

## Ražošanas metode

`loop.py:refine_alpha` visām piecām bildēm no saglabātās binārās maskas:

- parakstītā attāluma alfa ar pusplatumu 1,6 avota px;
- kontūras izlīdzināšana ar Gaussian σ=1,6;
- alfa kontrasta atjaunošana ar koeficientu 1,65;
- alfa piespiedu kārtā 255 vismaz 5 px apģērba iekšienē un 0 vismaz 5 px
  ārpusē;
- tieši ārpus maskas oriģināla RGB paplašina ar tuvāko apģērba krāsu, lai
  vecā fona krāsa neieplūstu daļēji caurspīdīgajos malas pikseļos;
- PARAUGS RGBA samazināšana notiek premultiplicētā alfa telpā.

Iter.6 PARAUGS un maskas pirms pārrakstīšanas īslaicīgi arhivēja A/B
salīdzinājumam un hash kontrolei; pēc iter.7 apstiprināšanas arhīvs dzēsts.

## Rezultātu pārbaude

Checker pievienoti H vārti (`H_edge_alpha`). Visām bildēm:

| Bilde | A max diff | Kodola alfa min | Tālu ārpusē alfa max | Daļējās alfas max attālums | Alfa/binārā seguma delta | Daļējās alfas px |
|---|---:|---:|---:|---:|---:|---:|
| 160538 | 0 | 255 | 0 | 2,0 px | 0,000001 | 32 280 |
| 160550 | 0 | 255 | 0 | 2,0 px | <0,000001 | 7 943 |
| 160601 | 0 | 255 | 0 | 2,0 px | <0,000001 | 7 715 |
| 160608 | 0 | 255 | 0 | 2,0 px | <0,000001 | 6 779 |
| 160645 | 0 | 255 | 0 | 2,0 px | <0,000001 | 7 297 |

Gala salīdzinājumus vecā/jaunā PARAUGS kopskatā un pikseļu palielinājumā
apskatīja visām piecām bildēm; pēc audita salīdzinājuma lapas dzēstas.
Vizuālais secinājums: diagonālās un izliektās malas ir tīrākas, plata oreola
nav, bet dabiskā adījuma šķiedru nevienmērība nav mākslīgi izlīdzināta.
