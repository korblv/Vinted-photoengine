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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
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
    print("Gatavs.")


if __name__ == "__main__":
    main()
