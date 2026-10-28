# ZIP saturs un izmantošana (aģentam, kas saņem šo arhīvu)

**Konteksts:** šis ZIP nonāca GitHub repozitorijā ar tīmekļa augšupielādi
(lietotājs no telefona). GitHub ZIPus automātiski NEizpakojā — to dari Tu.

**Kas iekšā:**
1. **Repo darba koks** (visi sekotie faili, 66+ faili) pie komita, kas
   norādīts `git log` pēdējā ierakstā bundlī — bez `.git` mapes.
2. **`loop_bildes_git.bundle`** — pilna git vēsture (~145 darba ieraksti).
   Nav obligāts, bet ļauj atjaunot vēsturi: `git clone
   loop_bildes_git.bundle vesture` un pēc tam strādāt tur.

**Ko darīt (parastā plūsma — repo jau piesaistīts Arena sesijai):**
```bash
# no repo saknes, kur guļ arena-vinted-dzinejs.zip:
unzip -q arena-vinted-dzinejs.zip -d /tmp/zip_izpakots
# pārcel failus uz repo sakni (bez paša zip un bundļa dublējuma, ja nav vajadzīgs):
rsync -a --exclude='arena-vinted-dzinejs.zip' /tmp/zip_izpakots/ ./
git add -A && git commit -m "izpakots arena-vinted-dzinejs.zip (darba koks)"
git rm --cached arena-vinted-dzinejs.zip 2>/dev/null; rm -f arena-vinted-dzinejs.zip
git commit -m "zip aizvākts" --allow-empty
```
(Vai vienkāršāk: izpakot, aizvākt zip, komitēt vienā reizā.)

**Tad turpini:** `README.md` → `HANDOFF/00_SAKU_SHEIT.md` (īpaši §2.0,
§3, §7) → `sesijas_atskanoshana/ATJAUNOT_SESIJU.md` (aktīvās grupas
145704 stāvoklis + gaidāmais GATE_C lēmums).

**Dzelzs likumi joprojām spēkā:** pogas apstiprinājumiem; ražošnes
izmaiņām poga PIRMS koda; NEKAD nepalaid `atjaunot.py` / nesējus
`01_DZINEJS.md` un `02_ATMINA.md` (novecojušas §47 kopijas).
