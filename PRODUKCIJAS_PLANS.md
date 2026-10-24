# Produkcijas refaktora plāns

Lēmums (lietotājs, 2026-10-24): mērķis ir **produkcijas programmatūra**, nevis
operatora darbagalds. Strādājam soli pa solim, pa vienam uzlabojumam.

## Noteikumi katram solim

1. Viens solis = viens komits + ieraksts `PROGRESS.md` ar skaitļiem un hash.
2. Pirms/pēc mēra: `du -sh /home/user` un skartos failus (sha256).
3. 00 dokumenta §3.2 (pikseļi = oriģināls) un §5 vārtu sliekšņi refaktora laikā
   **nemainās**.
4. Pēc katra soļa ražošanas izvadei jābūt bitiski identiskai ar stāvokli pirms
   soļa, vai atšķirība ir apzināta un pierakstīta ar skaitli.
5. Nākamo soli sāk tikai pēc lietotāja apstiprinājuma ar pogām.
6. Krātuve zem 100 MB; `uploads/` bez lietotāja lēmuma nedzēš.

## Soļi

- [x] **1. Git + arhīvs** (PROGRESS §54): bāzes komits `77e9ac2` (tags `v2.1.0`);
      10 novecojuši moduļi (1 441 rinda) pārvietoti uz `archive/`; saknē paliek
      12 ražošanas `.py`. Saturs nemainīgs: 22/22 sha256 identiski.
- [ ] **2. Testi no nulles**: `test_workflow_v2.py` — vienību testi tīrajām
      funkcijām (LUT, rotācija, ēna uz sintētiskas maskas) + golden regresijas
      tests ar deterministiski ģenerētiem sintētiskiem attēliem. Katra
      vēsturiskā kļūda (PROGRESS/QA) kļūst par testu. Mērķis: pilna palaišana
      < 2 min.
- [ ] **3. Idempotenti posmi**: katrs starpprodukts (maska, profils) iegūst
      blakus JSON ar provenanci (avota sha256, posms, parametri). Rerender
      nedrīkst atkārtot jau izdarītu posmu — novērš `--no-decontam` klases
      kļūdas (Attempt 2: −102 868/−44 627 px).
- [ ] **4. Viena konfigurācija**: visi sliekšņi/parametri vienā versijotā
      TOML failā; atskaitē ieraksta koda komita hash + konfigurācijas hash.
      CLI karogi tikai ignorētām vērtībām.
- [ ] **5. Neatkarīgs checker**: checker pārstāj importēt `workflow_v2`
      funkcijas; LUT izmanto kā datus (JSON) ar savu pielietojumu.
- [ ] **6. Monolīta dalīšana**: `workflow_v2.py` (2 085 rindas, `main()` 552)
      pa posmiem: sagatavošana / maska / krāsa / renderēšana / piegāde.
      Sāk tikai, kad soļa 2 testi zaļi.

## Ātrie labojumi (jebkurā brīdī, katrs savā komitā)

- [x] ISNet modeļa sha256 pārbaude `setup_v2.py` (PROGRESS §55; piespraude
      krustota ar rembg 2.0.85 avota MD5 konstanti).
- [ ] `00_SAKU_SHEIT.md` §8 atjaunināšana uz `studio_v1_contact_pcss`
      (atlikts no Vans piegādes).
- [ ] `atjaunot.py` dublikāts saknē un `HANDOFF/` — atstāt vienu.
- [ ] Lēmums par `uploads/01_DZINEJS.md` / `02_ATMINA.md`: ar git tie vairs
      nav vajadzīgi; līdz lietotāja lēmumam paliek kā sasalusi v2.1 kopija.

## Vides piezīmes

- `.git/config` Arena snapshot neietver: jaunā sesijā pirms komita atkārtot
  `git config user.name "loop_bildes"` un `git config user.email
  "loop_bildes@localhost"`. Komiti, tagi un objekti saglabājas.
- `/var/tmp/pylibs` + modelis starp sesijām var pazust (2026-10-24:
  `setup_v2.py --check` → `ready:false`). Pirms apstrādes: `python3
  setup_v2.py`.
- `archive/` kods ir sasalusi vēsture: netiek importēts, palaižams tikai ar
  `PYTHONPATH=.` no repozitorija saknes. `measure_shadow.py` apzināti
  atstāts saknē kā diagnostikas rīks (tā "kodola Δ" trūkums dokumentēts QA).
