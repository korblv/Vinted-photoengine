#!/usr/bin/env python3
"""Sintētisko ainu ģenerators pašmācībām (P-sērija, PROGRESS §133).

Deterministisks: katrai ainai fiksēta sēkla. Mērķis nav fotoreālisms,
bet ceļu provocēšana: maskas QA, kadrējuma izvēle, WB profila reakcija,
lut_only verifikācija. Ainas un gaidītie ceļi: sk. P0_PLANS.md.

Lietošana: python3 pasmacibas/gen_scenes.py --out /tmp/pdrill/uploads
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1888, 4096          # tāds pats portreta krops kā reālajiem kadriem


def _paper(w, h, rng, rgb=(165, 165, 163), vign=0.06):
    """Gluds papīrs: viegla vinete + troksnis sigma 2 (reālam papīram
    stūru std ir 3-4)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w / 2, h / 2
    d = np.sqrt(((xx - cx) / (w / 2)) ** 2 + ((yy - cy) / (h / 2)) ** 2)
    fall = 1.0 - vign * np.clip(d - 0.55, 0, 1)
    img = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        img[..., c] = rgb[c] * fall + rng.normal(0, 2.0, (h, w))
    return img


def _floor_corner(paper, rng, rgb=(106, 98, 82), corner="br", frac=0.30):
    """Koka grīdas stūris (reālajos kopskatos bija redzams)."""
    h, w = paper.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if corner == "br":
        d = np.sqrt(((w - xx) / (w * frac)) ** 2 + ((h - yy) / (h * frac)) ** 2)
    else:
        d = np.sqrt((xx / (w * frac)) ** 2 + (yy / (h * frac)) ** 2)
    m = np.clip(1.0 - d, 0, 1)[..., None]
    tex = rng.normal(0, 6, paper.shape)
    return paper * (1 - m) + (np.asarray(rgb, np.float32) + tex) * m


def _fabric(h, w, rng, base=(201, 201, 203), sigma=14, folds=5):
    """Audums: troksnis + zemas frekvences krokas (bez tām tas ir balts
    troksnis, ko rīki atpazīst kā 'nav audums')."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cro = np.zeros((h, w), np.float32)
    for _ in range(folds):
        fx, fy = rng.uniform(0.008, 0.035), rng.uniform(0.008, 0.035)
        cro += np.sin(xx * fx + yy * fy + rng.uniform(0, 6.28))
    cro /= folds
    img = np.zeros((h, w, 3), np.float32)
    for c in range(3):
        img[..., c] = base[c] + rng.normal(0, sigma, (h, w)) + 14 * cro
    return np.clip(img, 0, 255)


def _shirt_mask(w, h, touch_right=False, cy_frac=0.44, scale=1.0):
    """Krekla siluets: ķermenis + 2 piedurknes (vienveidīgs, bez caurumiem)."""
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    bw, bh = int(0.52 * w * scale), int(0.40 * h * scale)
    cx, cy = w // 2, int(h * cy_frac)
    body = (cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2)
    d.ellipse(body, fill=255)
    sw, sh = int(0.26 * w * scale), int(0.13 * h * scale)
    for sx, ang in ((cx - bw // 2 - sw // 3, -38), (cx + bw // 2 + sw // 3, 38)):
        sleeve = Image.new("L", (sw * 2, sh * 2), 0)
        ImageDraw.Draw(sleeve).ellipse((0, 0, sw * 2 - 1, sh * 2 - 1), fill=255)
        sleeve = sleeve.rotate(ang, expand=True, resample=Image.BILINEAR)
        m.paste(sleeve, (sx - sleeve.width // 2, cy - sleeve.height // 2), sleeve)
    if touch_right:
        # resna, slīpa "piedurkne" (elipse ~20 grādi) no ķermeņa pāri labajai
        # malai — kontakta josla >= 50% malas, bet forma NATURĀLA (ne
        # taisnstūris: v2 taisnstūra joslu ISNet noraidīja)
        arr = np.asarray(m).astype(np.uint8).copy()
        sleeve = Image.new("L", (w, h), 0)
        sd = ImageDraw.Draw(sleeve)
        sw2, sh2 = int(0.62 * w), int(0.58 * h)
        sx, sy = cx + bw // 4, cy
        sd.ellipse((sx - sw2 // 2, sy - sh2 // 2,
                    sx + sw2 // 2, sy + sh2 // 2), fill=255)
        sleeve = sleeve.rotate(20, expand=False, resample=Image.BILINEAR,
                               center=(sx, sy))
        arr = np.maximum(arr, np.asarray(sleeve))
        m = Image.fromarray(arr)
    return np.asarray(m) > 127


def _drop_shadow(scene, mask, rng, strength=0.35, dx=26, dy=34):
    """Kontakta ēna: silueta nobīde + izpludināšana; tikai uz papīra."""
    sh = Image.fromarray((mask * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(18))
    a = np.asarray(sh).astype(np.float32) / 255.0 * strength
    a = np.roll(np.roll(a, dy, axis=0), dx, axis=1)
    out = scene.copy()
    paper_only = ~mask
    for c in range(3):
        out[..., c][paper_only] *= (1.0 - 0.45 * a[paper_only])
    return out


def _save(img, path):
    Image.fromarray(np.clip(img + 0.5, 0, 255).astype(np.uint8)).save(
        path, quality=95)
    print(f"  {Path(path).name}: {img.shape[1]}x{img.shape[0]}")


def scene_kopskats(out, name, seed, paper_rgb=(165, 165, 163), garment=(201, 201, 203),
                   floor=True, touch_right=False, shadow=0.35, shadow_split=False,
                   scale=1.0):
    rng = np.random.default_rng(seed)
    scene = _paper(W, H, rng, paper_rgb)
    if floor:
        scene = _floor_corner(scene, rng)
    mask = _shirt_mask(W, H, touch_right=touch_right, scale=scale)
    fab = _fabric(H, W, rng, garment)
    if shadow_split:
        # krekla augšdaļa dziļā ēnā (reālais 145345 gadījums: p10 16-31)
        yy = np.mgrid[0:H, 0:W][0].astype(np.float32)
        ramp = np.clip(1.0 - 0.68 * np.exp(-((yy - H * 0.28) / (H * 0.10)) ** 2), 0.32, 1.0)
        fab *= ramp[..., None]
        scene = scene * 0.92                 # aina kopumā tumšāka
    scene = np.where(mask[..., None], fab, scene)
    scene = _drop_shadow(scene, mask, rng, strength=shadow)
    _save(scene, Path(out) / f"PDR_{name}.jpg")


def scene_haoss(out):
    rng = np.random.default_rng(404)
    scene = _paper(W, H, rng)
    m = np.zeros((H, W), bool)
    for i, (cx, cy, r) in enumerate([(0.3, 0.2, 0.10), (0.7, 0.24, 0.08),
                                     (0.45, 0.5, 0.13), (0.62, 0.7, 0.09),
                                     (0.3, 0.85, 0.07)]):
        yy, xx = np.mgrid[0:H, 0:W]
        m |= ((xx - W * cx) ** 2 + (yy - H * cy) ** 2) < (min(W, H) * r) ** 2
    fab = _fabric(H, W, rng, (150, 150, 152))
    scene = np.where(m[..., None], fab, scene)
    _save(scene, Path(out) / "PDR_D_haoss.jpg")


def scene_makro(out):
    rng = np.random.default_rng(505)
    fab = _fabric(H, W, rng, (201, 201, 203), sigma=16, folds=7)
    _save(fab, Path(out) / "PDR_F_makro.jpg")


def scene_extra(out):
    """2. kārtas ainas (P_REZULTATI §5):
    - G_plats: milzīgs krekls, ķermenis pāri pilnam platumam -> kontakts
      >= 50% abās vertikālajās malās -> auto KADRĒJUMAM jāizvēlas original
      (vienīgais līdz šim neizprovocētais auto atzars).
    - C2_zemkontrasts: zemas kontrasta krekls [178] uz [156] papīra ar
      cietu ēnas joslu -> mēģinājums izsaukt isnet_pad_retry ceļu."""
    # G: scale 1.95 -> body 1.01xW plats, 0.78H augsts
    scene_kopskats(out, "G_plats", seed=707, floor=False, scale=1.95)
    rng = np.random.default_rng(808)
    scene = _paper(W, H, rng)
    mask = _shirt_mask(W, H)
    fab = _fabric(H, W, rng, (178, 178, 178))
    yy = np.mgrid[0:H, 0:W][0].astype(np.float32)
    ramp = np.clip(1.0 - 0.80 * np.exp(-((yy - H * 0.30) / (H * 0.09)) ** 2), 0.20, 1.0)
    fab *= ramp[..., None]
    scene = np.where(mask[..., None], fab, scene)
    scene = _drop_shadow(scene, mask, rng, strength=0.30)
    _save(scene, Path(out) / "PDR_C2_zemkontrasts.jpg")


def scene_round4(out, gt_dir=None):
    """3. un 4. kārtas ainas (P_REZULTATI §8–§14):
    - E2_siltpapirs: silts kraftpapīrs (b* ~+14, chroma <= 0.15 robeža / pelēks krekls)
    - H_salocits: salocīts krekls pāri abām vertikālajām malām (2 bleed + 2 margin)
    - I_dividots: divi atsevišķi objekti (krekls + bikses) -> GATE_C STOP tests
    - J_henley_bleed: zema kontrasta vafeļadījuma henley pāri 3 malām uz gludas
      pelēkas plāksnes (145704 klase: plate_texture + open silhouette para_scale + GATE_Q/F)
    - K_exif6_portrets: asimetrisks divkrāsu apģērbs ar EXIF Orientation=6 (sensora 4096x1888)
    - L_makro_pilnkadrs: tīrs auduma makro visā kadrā (--lut-only pozītīvais tests)
    """
    gt_p = Path(gt_dir) if gt_dir else None
    if gt_p:
        gt_p.mkdir(parents=True, exist_ok=True)

    def _save_gt(mask_bool, name):
        if gt_p is not None:
            Image.fromarray((mask_bool.astype(np.uint8) * 255)).save(gt_p / f"PDR_{name}_GT.png")

    # E2: silts papīrs ar pelēku kreklu
    scene_kopskats(out, "E2_siltpapirs", seed=616, floor=False,
                   paper_rgb=(216, 206, 188), garment=(196, 196, 198))

    import gc
    # H: salocīts horizontāls krekls pāri pilnam platumam (58% kontakta -> original: 2 bleed + 2 margin)
    rng = np.random.default_rng(909)
    sc_h = _paper(W, H, rng, rgb=(172, 172, 172))
    yy, xx = np.mgrid[0:H, 0:W]
    top_wave = int(H * 0.23) + (14 * np.sin(xx[0] * 0.004)).astype(int)
    bot_wave = int(H * 0.77) + (14 * np.cos(xx[0] * 0.0035)).astype(int)
    m_h = (yy >= top_wave[None, :]) & (yy <= bot_wave[None, :])
    fab_h = _fabric(H, W, rng, base=(96, 108, 128), sigma=13, folds=6)
    sc_h = np.where(m_h[..., None], fab_h, sc_h)
    sc_h = _drop_shadow(sc_h, m_h, rng, strength=0.28)
    _save(sc_h, Path(out) / "PDR_H_salocits.jpg")
    _save_gt(m_h, "H_salocits")
    del sc_h, fab_h, m_h; gc.collect()

    # H2: slēgts siluets līdz pat sensora malai (44% < 50% kontakta -> slamjam + GATE_R ēnas malas tests)
    rng = np.random.default_rng(910)
    sc_h2 = _paper(W, H, rng, rgb=(172, 172, 172))
    top_w2 = int(H * 0.28) + (14 * np.sin(xx[0] * 0.004)).astype(int)
    bot_w2 = int(H * 0.72) + (14 * np.cos(xx[0] * 0.0035)).astype(int)
    m_h2 = (yy >= top_w2[None, :]) & (yy <= bot_w2[None, :])
    fab_h2 = _fabric(H, W, rng, base=(92, 104, 124), sigma=13, folds=6)
    sc_h2 = np.where(m_h2[..., None], fab_h2, sc_h2)
    sc_h2 = _drop_shadow(sc_h2, m_h2, rng, strength=0.28)
    _save(sc_h2, Path(out) / "PDR_H2_slamjam_mala.jpg")
    _save_gt(m_h2, "H2_slamjam_mala")
    del sc_h2, fab_h2, m_h2; gc.collect()

    # I: divdaļīgs komplekts (divas nesavienotas daļas -> largest_component < 0.95 -> STOP)
    rng = np.random.default_rng(919)
    sc_i = _paper(W, H, rng, rgb=(168, 168, 166))
    m_i1 = _shirt_mask(W, H, cy_frac=0.28, scale=0.68)
    m_i2 = _shirt_mask(W, H, cy_frac=0.73, scale=0.62)
    m_i = m_i1 | m_i2
    del m_i1, m_i2
    fab_i = _fabric(H, W, rng, base=(86, 92, 104), sigma=12, folds=5)
    sc_i = np.where(m_i[..., None], fab_i, sc_i)
    sc_i = _drop_shadow(sc_i, m_i, rng, strength=0.30)
    _save(sc_i, Path(out) / "PDR_I_dividots.jpg")
    _save_gt(m_i, "I_dividots")
    del sc_i, fab_i, m_i; gc.collect()

    # J: 145704 klases gaišs vafeļadījuma henley pāri 3 kadra malām (isnet_pad_retry + original)
    rng = np.random.default_rng(145704)
    sc_j = _paper(W, H, rng, rgb=(168, 168, 169), vign=0.03)
    m_j_im = Image.new("L", (W, H), 0)
    dj = ImageDraw.Draw(m_j_im)
    dj.polygon([
        (0, int(H * 0.30)),
        (int(W * 0.30), int(H * 0.245)),
        (int(W * 0.50), int(H * 0.235)),
        (int(W * 0.70), int(H * 0.245)),
        (W, int(H * 0.31)),
        (W, H),
        (0, H),
    ], fill=255)
    m_j = np.asarray(m_j_im) > 127
    del m_j_im
    waffle = ((((xx // 6) + (yy // 6)) % 2) * 34 - 17).astype(np.float32)
    rib = (8.0 * np.sin(xx * 0.42) + 6.0 * np.cos(yy * 0.37)).astype(np.float32)
    fab_j = _fabric(H, W, rng, base=(204, 202, 198), sigma=7, folds=6) + waffle[..., None] + rib[..., None]
    placket = (np.abs(xx - W // 2) < 42) & (yy > int(H * 0.24)) & (yy < int(H * 0.48))
    fab_j[placket] -= 24.0
    del placket
    fab_j = np.clip(fab_j, 0, 255)
    sc_j = np.where(m_j[..., None], fab_j, sc_j)
    del fab_j
    sc_j = _drop_shadow(sc_j, m_j, rng, strength=0.22, dx=16, dy=-18)
    _save(sc_j, Path(out) / "PDR_J_henley_bleed.jpg")
    _save_gt(m_j, "J_henley_bleed")
    del sc_j; gc.collect()

    # M: izo-luminances vafeļadījums + tumša pogu plakete uz gludas plāksnes -> plate_texture ceļš!
    del waffle, rib
    rng = np.random.default_rng(145706)
    sc_m = np.full((H, W, 3), 172.0, np.float32) + rng.normal(0, 1.1, (H, W, 3)).astype(np.float32)
    m_m_im = Image.new("L", (W, H), 0)
    dm = ImageDraw.Draw(m_m_im)
    dm.polygon([
        (0, int(H * 0.30)), (int(W * 0.32), int(H * 0.245)),
        (int(W * 0.50), int(H * 0.235)), (int(W * 0.68), int(H * 0.245)),
        (W, int(H * 0.31)), (W, H), (0, H),
    ], fill=255)
    m_m = np.asarray(m_m_im) > 127
    del m_m_im
    fine = ((((xx // 7) + (yy // 7)) % 2) * 22.0 - 11.0).astype(np.float32)
    fab_m = np.empty((H, W, 3), np.float32)
    for c, bv in enumerate((173.0, 173.0, 172.0)):
        fab_m[..., c] = bv + fine + rng.normal(0, 2.0, (H, W)).astype(np.float32)
    del fine
    placket_m = (np.abs(xx - W // 2) < 38) & (yy > int(H * 0.24)) & (yy < int(H * 0.50))
    collar_m = ((np.hypot((xx - W // 2) / 260.0, (yy - H * 0.25) / 110.0) < 1.08) &
                (np.hypot((xx - W // 2) / 260.0, (yy - H * 0.25) / 110.0) > 0.85) & (yy >= H * 0.235))
    fab_m[placket_m | collar_m] = 58.0
    del placket_m, collar_m
    sc_m = np.where(m_m[..., None], np.clip(fab_m, 0, 255), sc_m)
    del fab_m
    _save(sc_m, Path(out) / "PDR_M_plate_only.jpg")
    _save_gt(m_m, "M_plate_only")
    del sc_m, m_m, m_j; gc.collect()

    # K: asimetrisks divkrāsu apģērbs ar EXIF Orientation=6 (sensora orientācijā 4096x1888)
    rng = np.random.default_rng(6060)
    sc_k = _paper(W, H, rng, rgb=(172, 172, 172))
    m_k = _shirt_mask(W, H, scale=1.02)
    fab_k_left = _fabric(H, W, rng, base=(98, 110, 128), sigma=11, folds=5)
    fab_k_right = _fabric(H, W, rng, base=(134, 124, 104), sigma=11, folds=5)
    fab_k = np.where((xx < int(W * 0.65))[..., None], fab_k_left, fab_k_right)
    del fab_k_left, fab_k_right
    sc_k = np.where(m_k[..., None], fab_k, sc_k)
    del fab_k
    sc_k = _drop_shadow(sc_k, m_k, rng, strength=0.25)
    raw_im = Image.fromarray(np.clip(sc_k + 0.5, 0, 255).astype(np.uint8)).transpose(Image.ROTATE_90)
    del sc_k
    exif = Image.Exif()
    exif[274] = 6
    kp = Path(out) / "PDR_K_exif6_portrets.jpg"
    raw_im.save(kp, quality=95, exif=exif.tobytes())
    print(f"  {kp.name}: raw {raw_im.size[0]}x{raw_im.size[1]} (EXIF=6 -> {W}x{H})")
    _save_gt(m_k, "K_exif6_portrets")
    del raw_im, m_k; gc.collect()

    # L: bagātīgas tekstūras tumšāks auduma makro (--lut-only pozitīvais tests)
    rng = np.random.default_rng(7171)
    weave = ((((xx // 5) + (yy // 7)) % 2) * 28 - 14).astype(np.float32)
    del xx, yy
    fab_l = np.clip(_fabric(H, W, rng, base=(88, 96, 114), sigma=15, folds=8) + weave[..., None], 0, 255)
    del weave
    _save(fab_l, Path(out) / "PDR_L_makro_pilnkadrs.jpg")
    del fab_l; gc.collect()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--extra", action="store_true", help="iekļaut 2. kārtas ainas")
    ap.add_argument("--round4", action="store_true", help="iekļaut 3./4. kārtas ainas (E2, H, I, J, K, L)")
    ap.add_argument("--gt-dir", default="", help="kur saglabāt GT maskas (pēc izvēles)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"Ģenerēju ainas -> {out}")
    scene_kopskats(out, "A_kopskats", seed=101)                      # gaidāms: isnet + slamjam
    scene_kopskats(out, "A2_kopskats", seed=107)                     # P4 profila avotam
    scene_kopskats(out, "B_mala", seed=202, floor=False, touch_right=True)   # gaidāms: original
    scene_kopskats(out, "C_enskaelis", seed=303, shadow_split=True)  # gaidāms: pad retry vai STOP
    scene_kopskats(out, "E_siltpapirs", seed=606, floor=False,
                   paper_rgb=(232, 214, 186))                         # gaidāms: GATE K auto FAIL
    scene_haoss(out)                                                 # gaidāms: STOP
    scene_makro(out)                                                 # gaidāms: lut_only refused
    if a.extra or a.round4:
        scene_extra(out)
    if a.round4:
        scene_round4(out, gt_dir=a.gt_dir or None)
    print("Gatavs.")


if __name__ == "__main__":
    main()
