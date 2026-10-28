# Kā atjaunot sesiju no GitHub repo (jaunam aģentam)

**Kad lietot:** jaunā Arena Agent Mode sesijā, kas startēta ar klonētu vai
piesaistītu GitHub repo `https://github.com/korblv/Vinted-photoengine`.

**Pirms visam:** izlasi `HANDOFF/00_SAKU_SHEIT.md` (visa projekta atmiņa).

## 0. NEIZMANTOT `atjaunot.py`

`HANDOFF/atjaunot.py` un `archive/atjaunot.py` ir vēsturiski §47 atjaunošanas
skripti no sasaldētajiem `01_DZINEJS.md` / `02_ATMINA.md` nesējiem. Tie ir
**novecojuši** — GitHub repozitorijs ir vienīgais patiesais avots.

## 1. Aktīvo grupu stāvoklis (PROGRESS §145)

- Grupa `145704` ir piegādāta (`GALA_145704.zip`), lietotājs apstiprināja
  lejupielādi, un visi grupas attēli un atjaunošanas faili ir **pilnībā
  izdzēsti** gan no darba telpas, gan no GitHub repozitorija vēstures.
- Šobrīd aktīvu produktu bilžu grupu **nav** (`uploads/` un `output/` ir
  tīri un gatavi nākamajai bilžu grupai).

## 2. Vides sagatavošana jaunā smilškastē

Jaunā smilškastē `/var/tmp` ir tukšs — pirms apstrādes vienmēr:

```bash
cd /home/user/loop_bildes && python3 setup_v2.py   # ~1 min; /var/tmp/pylibs + ISNet
python3 -m pytest test_workflow_v2.py -q            # jābūt 150 passed
```

## 3. Pēc jebkuras nākamās grupas noslēguma

Piegāde tikai ar pogām (`HANDOFF §3.4`): `V2_KOLAZA.jpg` → `Apstiprināt` →
`--make-zip` → pēc `Lejupielādēju` pilna grupas dzēšana ar:

```bash
python3 close_group.py --yes <STEM_VAI_6_CIPARI>
```

## 4. Ko publiskais repo NESATUR

- Nevienu lietotāja apģērba fotogrāfiju, ne apstrādātās bildes (`PARAUGS`,
  `MASTER`, `V2_KOLAZA.jpg`, `.zip`), ne ekrānšāviņus.
