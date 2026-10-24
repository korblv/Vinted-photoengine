# ATMIŅAS UN ĀTRUMA TESTI — swap side-by-side

Datums: 2026-10-21. Testa bilde: MVIMG_20261020_160645 (3072×4096).
Testa skripti atradās `/tmp`, tāpēc darba krātuvē jauni testa faili nepalika.

## Sandbox inventārs

- KVM Linux 6.1, 2 vCPU (Intel Xeon 2,60 GHz)
- RAM: 2 030 404 KB; cgroup `user/memory.max`: 1 944 915 968 baiti
- Sākumā swap: 0; `sudo`, `mkswap`, `swapon` un `zramctl` ir pieejami
- GPU/OpenCL: nav redzami
- Saknes disks: 26 GB, brīvi aptuveni 20 GB; `/tmp` ir 992 MB tmpfs
- Python 3.13, NumPy 2.3.5, OpenCV 4.11 (2 pavedieni), Pillow 12.3,
  SciPy 1.17.1, ONNX Runtime 1.31; pyvips/libvips nav uzstādīts

Fizisko RAM no iekšpuses palielināt nevar: cgroup robežas pacelšana nerada
papildu fizisko atmiņu. Papildu kapacitāti var dot tikai swap/zram vai
lielāka platforma/VM no pakalpojuma puses.

## Swap side-by-side

Īstais 160645 renderings no saglabātās maskas, bez failu saglabāšanas:

| Variants | Kopā | Peak RSS | Secinājums |
|---|---:|---:|---|
| Bez swap | 2,025 s | 473 MB | RAM pietiek |
| 2 GB faila swap uz saknes diska | 2,046 s | 473 MB | +0,021 s; ātruma ieguvuma nav |

Kontrolēts 2400 MB atmiņas stresa tests:

| Variants | Rezultāts |
|---|---|
| Bez swap | OOM; process nogalināts pēc >1024 MB piešķiršanas (exit 137) |
| 2 GB swap | Pabeigts 11,26 s; piešķiršana 4,37 s, divas darba pārejas 6,88 s; `VmSwap` 989 852 KB, peak RSS 1417 MB |

Pēc testa swap izslēdza un `/var/tmp/arena_swap_test` dzēsa.
Secinājums: swap ir noderīga **OOM drošība** modeļiem/eksperimentiem, bet
nav ātruma optimizācija. Ja darba kopa regulāri pārsniedz RAM, paging padara
procesu lēnāku.

## Kur pazūd laiks īstajā procesā

160645 posmi atsevišķos procesos:

- `refine_alpha`: 0,386 s, peak 307 MB
- `extend_foreground_colors`: 0,247 s, peak 460 MB
- MASTER kompozīcija: pašreizējā float 0,174 s; uint16 0,158 s; PIL
  `Image.composite` 0,186 s; Numba 0,321 s pēc iesildīšanas — šis posms nav
  vērts sarežģīt
- Korekta premultiplicēta RGBA samazināšana: 0,808 s; tieša RGBA resize:
  0,291 s, bet ar vecā fona krāsas noplūdes risku, tāpēc to neizvēlas
- Viss saved-mask renderings bez saglabāšanas: 2,025 s, peak 473 MB
- JPG q95 saglabāšana: 0,048 s

GrabCut mērogs:

| Platums | Laiks | Peak RSS | Atšķirība no 960 px maskas |
|---:|---:|---:|---:|
| 768 px | 1,900 s | 285 MB | 0,00029 |
| 960 px | 3,216 s | 409 MB | atsauce |
| 1280 px | 5,806 s | 590 MB | 0,00032 |

MASTER PNG bezzuduma saglabāšana:

| Līmenis | Laiks | Izmērs |
|---:|---:|---:|
| 1 | 0,944 s | 13,84 MB |
| 3 | 1,421 s | 13,11 MB |
| 6 | 3,248 s | 12,66 MB |
| 9 | 12,365 s | 12,23 MB |

## Profesionālais lēmums

1. **PNG noklusējumu mainīt no 9 uz 6** — izdarīts (`--png-level`, noklusēti
   6). Vienai bildei tas ietaupa aptuveni 9,1 s, maksājot aptuveni 0,43 MB.
2. Renderēšanas iterācijās izmantot `--saved-mask`, nevis atkārtot
   segmentāciju vai modeļa ielādi.
3. Saglabāt chunkoto, zemas atmiņas cauruļvadu; pašreizējais saved-mask
   renderings ar 473 MB peak nav RAM ierobežots.
4. Swap ieslēgt tikai īslaicīgi kā OOM drošību jauna modeļa vai augstākas
   izšķirtspējas eksperimentiem; pēc darba to izslēgt un failu dzēst.
5. Ja platforma ļautu izvēlēties resursus, šim procesam vispirms ņemtu
   vairāk vCPU; 4 GB RAM būtu pietiekama drošība un divu renderu
   paralēlisms. 8 GB vai GPU būtu pamatoti galvenokārt modeļu/paralēlu
   partiju dēļ, nevis pašreizējam vienbildes renderingam.
6. Ātriem melnrakstiem var lietot GrabCut 768 px (aptuveni 41% ātrāk nekā
   960 px), bet gala kvalitātei paturēt 960 px.
