#!/usr/bin/env python3
"""Workflow v2.1 regresijas un vienību testi (produkcijas refaktors, solis 2).

Palaišana:  python3 -m unittest test_workflow_v2 -v

Principi (PRODUKCIJAS_PLANS.md):
- tikai sintētiski, deterministiski ģenerēti dati — repo nav bināru fixtūru;
- testi piesprauž pašreizējo paredzamo uzvedību (characterization), nevis
  vēlamo; zināmi defekti netiek slēpti — vai nu raksturo, vai aizsargā
  posma līmenī ar testu, kas aizsargu pierāda;
- ISNet maskas kvalitāte šeit NETIEK testēta (vajadzīgi reāli foto) — tā
  paliek katras grupas attempt/checker procedūrā;
- testi neko neraksta ražošanas ``output/`` mapēs (tikai pagaidu mapes).
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np
from PIL import Image

import checker_v2 as ck
import loop
import setup_v2
import workflow_v2 as wf

SEED = 12345


# ---------------------------------------------------------------------------
# Mērogošana un rotāciju parsings
# ---------------------------------------------------------------------------
class TestFitSize(unittest.TestCase):
    def test_downscale_keeps_aspect(self):
        self.assertEqual(wf.fit_size(4000, 3000, 768, 1024), (768, 576))

    def test_never_enlarges(self):
        self.assertEqual(wf.fit_size(100, 50), (100, 50))

    def test_extreme_aspect_at_least_1px(self):
        self.assertEqual(wf.fit_size(1, 10000), (1, 1024))

    def test_invalid_size_raises(self):
        with self.assertRaises(ValueError):
            wf.fit_size(0, 100)


class TestRotationParsing(unittest.TestCase):
    def test_aliases_and_case(self):
        self.assertEqual(wf.normalize_rotation("cw"), 90)
        self.assertEqual(wf.normalize_rotation(" RIGHT "), 90)
        self.assertEqual(wf.normalize_rotation("Ccw"), 270)
        self.assertEqual(wf.normalize_rotation("left"), 270)

    def test_modulo(self):
        self.assertEqual(wf.normalize_rotation(450), 90)
        self.assertEqual(wf.normalize_rotation(-90), 270)
        self.assertEqual(wf.normalize_rotation(0), 0)

    def test_invalid_raises(self):
        for bad in (45, "abc", "91"):
            with self.assertRaises(ValueError):
                wf.normalize_rotation(bad)

    def test_parse_list_and_extension_strip(self):
        out = wf.parse_rotations(["IMG_1:270,IMG_2.jpg:cw", "A.B.ORIGINAL.png:180"])
        self.assertEqual(out, {"IMG_1": 270, "IMG_2": 90, "A.B.ORIGINAL": 180})

    def test_parse_without_colon_raises(self):
        with self.assertRaises(ValueError):
            wf.parse_rotations(["IMG_1-270"])

    def test_rotation_for_global_and_fallback(self):
        saved = wf.ROTATIONS_CW
        try:
            wf.ROTATIONS_CW = {"ABC123": 90, "201332": 270}
            self.assertEqual(wf.rotation_for("ABC123.jpg"), 90)
            self.assertEqual(wf.rotation_for("IMG_201332.jpg"), 270)  # pēdējo 6 zīmju atslēga
            self.assertEqual(wf.rotation_for("NEZINAMA.jpg"), 0)
        finally:
            wf.ROTATIONS_CW = saved


class TestQuarterTurn(unittest.TestCase):
    """§3.2 vienīgais atļautais pagrieziens — jābūt bezzaudējumu permutācijai."""

    def setUp(self):
        rng = np.random.default_rng(SEED)
        self.arr = rng.integers(0, 256, (4, 6, 3), dtype=np.uint8)
        self.img = Image.fromarray(self.arr)

    def test_anchor_top_left_goes_top_right_on_90cw(self):
        a = np.zeros((2, 3, 3), np.uint8)
        a[0, 0] = [255, 0, 0]
        r = np.asarray(wf.apply_quarter_turn(Image.fromarray(a), 90))
        self.assertEqual(r.shape, (3, 2, 3))
        self.assertEqual(tuple(np.argwhere(r[:, :, 0] > 0)[0]), (0, 1))

    def test_four_quarter_turns_identity(self):
        out = self.img
        for _ in range(4):
            out = wf.apply_quarter_turn(out, 90)
        self.assertEqual(out.tobytes(), self.img.tobytes())

    def test_90_then_270_identity(self):
        out = wf.apply_quarter_turn(wf.apply_quarter_turn(self.img, 90), 270)
        self.assertEqual(out.tobytes(), self.img.tobytes())

    def test_lossless_pixel_multiset_all_angles(self):
        ref = sorted(self.arr.tobytes())
        for deg in (0, 90, 180, 270):
            out = np.asarray(wf.apply_quarter_turn(self.img, deg))
            self.assertEqual(sorted(out.tobytes()), ref, f"grādi={deg}")


# ---------------------------------------------------------------------------
# Krāsu LUT
# ---------------------------------------------------------------------------
class TestLut(unittest.TestCase):
    def test_apply_identity_lut_exact(self):
        rgb = np.random.default_rng(SEED).integers(0, 256, (8, 8, 3), dtype=np.uint8)
        ident = [np.arange(256, dtype=np.uint8)] * 3
        np.testing.assert_array_equal(wf.apply_lut(rgb, ident), rgb)

    def test_apply_invert_lut_exact(self):
        rgb = np.arange(4 * 4 * 3, dtype=np.uint8).reshape(4, 4, 3) * 5
        inv = [np.arange(255, -1, -1, dtype=np.uint8)] * 3
        np.testing.assert_array_equal(wf.apply_lut(rgb, inv), 255 - rgb)

    def test_build_lut_identity_below_knee_without_blend(self):
        # gains=1, exposure=1, bez līknes: zem gaišo toņu ceļa (0.86*255=219)
        # LUT ir bitiska identitāte; virs tā plecs saspiež (filmiskais roll-off).
        lut = wf.build_lut(np.ones(3), 1.0, curve_blend=0.0)[0].astype(int)
        np.testing.assert_array_equal(lut[:220], np.arange(220))
        self.assertEqual(lut[255], 242)  # izmērīts characterization solī

    def test_build_lut_default_monotone_and_endpoints(self):
        for row in wf.build_lut(np.ones(3), 1.0):
            r = row.astype(int)
            self.assertTrue(np.all(np.diff(r) >= 0))
            self.assertEqual(r[0], 0)
            self.assertEqual(r[255], 244)

    def test_gain_raises_midtone(self):
        base = wf.build_lut(np.ones(3), 1.0)[0].astype(int)
        hot = wf.build_lut(np.array([1.14, 1.0, 1.0]), 1.0)[0].astype(int)
        self.assertGreater(hot[128], base[128])

    def test_srgb_roundtrip(self):
        x = np.arange(256, dtype=np.float64)
        err = np.abs(wf.linear_to_srgb(wf.srgb_to_linear(x)) - x).max()
        self.assertLess(err, 1e-9)


class TestGradeProfileGuard(unittest.TestCase):
    """Regresijas sargs: GATE_R krita ar asināšanu 42% (p99 26/28 > 24);
    labojums uz 25% nedrīkst klusi atgriezties (PROGRESS §50)."""

    def test_output_sharpen_pinned_25(self):
        with tempfile.TemporaryDirectory() as td:
            src = np.full((240, 240, 3), 200, np.uint8)
            src[50:190, 50:190] = 90
            msk = np.zeros((240, 240), np.uint8)
            msk[50:190, 50:190] = 255
            sp, mp = Path(td) / "sint.png", Path(td) / "sint_MASK.png"
            Image.fromarray(src).save(sp)
            Image.fromarray(msk).save(mp)
            rec = {"source": str(sp), "mask_path": str(mp), "stem": "sint"}
            prof = wf.compute_grade_profile([rec], wb_mode="identity")
        self.assertEqual(prof["output_sharpen"],
                         {"radius": 1.4, "percent": 25, "threshold": 3})
        self.assertEqual(prof["wb_gains_linear_rgb"], [1.0, 1.0, 1.0])
        self.assertEqual([len(r) for r in prof["lut_rgb"]], [256, 256, 256])
        self.assertTrue(0.99 <= prof["exposure_factor"] <= 1.06)


# ---------------------------------------------------------------------------
# Masku QA un malas alfa
# ---------------------------------------------------------------------------
class TestMaskQa(unittest.TestCase):
    def _rect_soft(self):
        s = np.zeros((200, 200), np.uint8)
        s[30:170, 30:170] = 255
        return s

    def test_mask_stats_exact(self):
        q = wf._mask_stats((self._rect_soft() > 0).astype(np.uint8))
        self.assertEqual(q["coverage"], 0.49)
        self.assertEqual(q["largest_component_ratio"], 1.0)
        self.assertEqual(q["bbox_fraction"], [0.7, 0.7])
        self.assertEqual(q["silhouette_fill"], 1.0)

    def test_ai_mask_qa_accepts_whole_silhouette(self):
        self.assertTrue(wf.ai_mask_qa(self._rect_soft())["accept"])

    def test_ai_mask_qa_rejects_empty_full_fragmented(self):
        self.assertFalse(wf.ai_mask_qa(np.zeros((200, 200), np.uint8))["accept"])
        self.assertFalse(wf.ai_mask_qa(np.full((200, 200), 255, np.uint8))["accept"])
        frag = np.zeros((200, 200), np.uint8)
        frag[20:110, 20:120] = 255      # 9000 px
        frag[150:170, 150:200] = 255    # 1000 px -> lielākā 0.90 < 0.95
        self.assertFalse(wf.ai_mask_qa(frag)["accept"])


class TestRefineAlpha(unittest.TestCase):
    def test_forced_beyond_band_with_production_defaults(self):
        b = np.zeros((200, 200), np.uint8)
        b[40:160, 40:160] = 1
        alpha = loop.refine_alpha(b)  # ražošanas noklusējumi, band_px=6.5
        din = cv2.distanceTransform(b, cv2.DIST_L2, 5)
        dout = cv2.distanceTransform(1 - b, cv2.DIST_L2, 5)
        signed = din - dout
        self.assertTrue(np.all(alpha[signed >= 6.5] == 255))
        self.assertTrue(np.all(alpha[signed <= -6.5] == 0))
        partial = (alpha > 0) & (alpha < 255)
        self.assertTrue(partial.any())  # pāreja vispār eksistē
        self.assertLessEqual(float(np.abs(signed[partial]).max()), 6.5)


# ---------------------------------------------------------------------------
# Studijas ēna (studio_v1_contact_pcss)
# ---------------------------------------------------------------------------
class TestStudioShadow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = np.zeros((500, 400), np.uint8)
        cls.binary[150:350, 120:280] = 1
        cls.bg = loop.studio_shadow_bg((500, 400), cls.binary, canvas_scale=1.0)
        cls.delta = 243 - cls.bg.astype(int)

    def test_empty_and_full_mask_give_plain_bg(self):
        z = loop.studio_shadow_bg((50, 40), np.zeros((50, 40), np.uint8))
        o = loop.studio_shadow_bg((50, 40), np.ones((50, 40), np.uint8))
        self.assertTrue(np.all(z == 243))
        self.assertTrue(np.all(o == 243))

    def test_far_background_exactly_243(self):
        for y, x in [(0, 0), (0, -1), (-1, 0), (-1, -1)]:
            self.assertEqual(int(self.bg[y, x]), 243)
        # austrums aiz ēnas loga beigām (58 px) — tieši 243
        self.assertTrue(np.all(self.bg[200:300, 280 + 60:] == 243))

    def test_one_directional_asymmetry(self):
        e = self.delta[200:300, 281:284].mean()   # kontakts austrumos (d=1..3)
        w = self.delta[200:300, 116:119].mean()   # kontakts rietumos
        self.assertTrue(60.0 <= e <= 95.0, f"E Δ={e:.1f}")   # kalibrācijas zona
        self.assertLess(w, 8.0, f"W Δ={w:.2f}")              # tikai kontakta AO
        self.assertGreater(e / max(w, 0.01), 15.0)

    def test_delta_decays_with_distance_east(self):
        bands = [self.delta[200:300, 280 + lo:280 + hi].mean()
                 for lo, hi in [(1, 5), (10, 20), (30, 45), (60, 80)]]
        self.assertTrue(all(a > b for a, b in zip(bands, bands[1:])), str(bands))
        self.assertEqual(bands[-1], 0.0)


# ---------------------------------------------------------------------------
# decontaminate_rim: jēlā funkcija NAV idempotenta; posms IR (provenance)
# ---------------------------------------------------------------------------
def _decontam_fixture():
    rng = np.random.default_rng(SEED)
    mask = np.zeros((480, 480), np.uint8)
    mask[60:420, 60:420] = 1
    din = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    base = (100 + rng.integers(-30, 30, (480, 480))).astype(np.int16)
    base[(din > 0) & (din <= 14)] = 45   # gluda tumšā josla = papīra ēnas rims
    base[mask == 0] = 210
    rgb = np.repeat(np.clip(base, 0, 255).astype(np.uint8)[:, :, None], 3, axis=2)
    return rgb, mask


class TestDecontam(unittest.TestCase):
    def test_first_run_removes_rim(self):
        rgb, mask = _decontam_fixture()
        out, info = loop.decontaminate_rim(rgb, mask.copy())
        self.assertTrue(info.get("applied"))
        self.assertLess(int((out > 0).sum()), int(mask.sum()))

    def test_raw_second_run_cuts_more_characterization(self):
        """Kāpēc vajadzīgs provenance aizsargs: jēlā funkcija ir novērtētājs,
        nevis idempotenta operācija — tai pašai maskai otrais piegājiens
        nogriež vēl (sintētikā: 1. reizē −17 498 px, 2. reizē vēl −6 611 px).
        Ražošanā to nedrīkst izsaukt divreiz: TestMaskProvenance pierāda,
        ka posms to aizsargā. Ja funkcija kādreiz kļūst patiesi idempotenta,
        šis tests apzināti kritīs un liks pārskatīt aizsarga vajadzību."""
        rgb, mask = _decontam_fixture()
        once, _ = loop.decontaminate_rim(rgb, mask.copy())
        twice, _ = loop.decontaminate_rim(rgb, once.copy())
        self.assertLess(int((twice > 0).sum()), int((once > 0).sum()))


# ---------------------------------------------------------------------------
# Masku provenance un posma idempotence (solis 3)
# ---------------------------------------------------------------------------
class TestMaskProvenance(unittest.TestCase):
    def _mask_file(self, td, stem="STEM", val=255):
        p = Path(td) / f"{stem}_MASK.png"
        arr = np.zeros((60, 80), np.uint8)
        arr[10:50, 10:70] = val
        Image.fromarray(arr).save(p)
        return p

    def test_start_and_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._mask_file(td)
            prov = wf.start_mask_provenance(p, "STEM", "srcsha", "isnet")
            self.assertEqual(prov["mask_sha256"], wf.sha256_file(p))
            self.assertTrue(prov["history_known"])
            self.assertEqual(prov["stages"][0]["stage"], "mask")
            self.assertEqual(wf.read_mask_provenance(p), prov)
            self.assertTrue(wf.mask_provenance_path(p).name.endswith("_MASK.json"))

    def test_read_missing_or_broken_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._mask_file(td)
            self.assertIsNone(wf.read_mask_provenance(p))
            wf.mask_provenance_path(p).write_text("{bojāts json", encoding="utf-8")
            self.assertIsNone(wf.read_mask_provenance(p))

    def test_decontam_needed_matrix(self):
        sha = "a" * 64
        done = {"mask_sha256": sha,
                "stages": [{"stage": "decontam", "params": wf.DECONTAM_PARAMS}]}
        self.assertTrue(wf.decontam_needed(None, wf.DECONTAM_PARAMS, sha))
        self.assertTrue(wf.decontam_needed(done, wf.DECONTAM_PARAMS, "b" * 64))
        self.assertFalse(wf.decontam_needed(done, wf.DECONTAM_PARAMS, sha))
        self.assertTrue(wf.decontam_needed(
            done, {"max_px": 99, "tex_ratio": 0.45}, sha))
        self.assertTrue(wf.decontam_needed(
            {"mask_sha256": sha, "stages": [{"stage": "mask"}]},
            wf.DECONTAM_PARAMS, sha))

    def test_append_chain_and_reset_on_external_change(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._mask_file(td)
            wf.start_mask_provenance(p, "STEM", "srcsha", "isnet")
            sha_in = wf.sha256_file(p)
            self._mask_file(td, val=200)  # posms pārraksta masku
            prov = wf.append_mask_stage(p, "STEM", "srcsha", {
                "stage": "decontam", "params": dict(wf.DECONTAM_PARAMS),
                "input_mask_sha256": sha_in})
            self.assertEqual([s["stage"] for s in prov["stages"]], ["mask", "decontam"])
            self.assertEqual(prov["mask_sha256"], wf.sha256_file(p))
            # Ārēja izmaiņa: failu maina bez sidecar atjaunināšanas ->
            # nākamais posms ar novecojušu ieeju sāk jaunu, nezināmu ķēdi.
            self._mask_file(td, val=128)
            prov2 = wf.append_mask_stage(p, "STEM", "srcsha", {
                "stage": "decontam", "params": dict(wf.DECONTAM_PARAMS),
                "input_mask_sha256": sha_in})
            self.assertEqual(len(prov2["stages"]), 1)
            self.assertFalse(prov2["history_known"])

    def test_stage_level_idempotence_on_real_decontam(self):
        """Atkārto render_one lēmuma ceļu ar īsto funkciju uz pagaidu
        failiem: otrais piegājiens ir skipped un maska bitiski identiska.
        (Pats render_one raksta fiksētās output/ mapēs, tāpēc šeit tiek
        testēts tā lēmuma kodols — tās pašas funkcijas, tā pati secība.)"""
        rgb, mask = _decontam_fixture()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "STEM_MASK.png"
            wf.save_gray_png(mask * 255, p, 1)
            wf.start_mask_provenance(p, "STEM", "srcsha", "synthetic")

            def decontam_stage():
                binary = (np.asarray(Image.open(p).convert("L")) > 128).astype(np.uint8)
                cur = wf.sha256_file(p)
                if not wf.decontam_needed(wf.read_mask_provenance(p),
                                           wf.DECONTAM_PARAMS, cur):
                    return {"applied": False, "skipped": True}
                binary, info = loop.decontaminate_rim(rgb, binary, **wf.DECONTAM_PARAMS)
                if info.get("applied"):
                    wf.save_gray_png(binary.astype(np.uint8) * 255, p, 1)
                    wf.append_mask_stage(p, "STEM", "srcsha", {
                        "stage": "decontam", "params": dict(wf.DECONTAM_PARAMS),
                        "input_mask_sha256": cur,
                        "removed_px": info.get("removed_px")})
                return info

            info1 = decontam_stage()
            self.assertTrue(info1.get("applied"))
            sha1, arr1 = wf.sha256_file(p), np.asarray(Image.open(p))
            info2 = decontam_stage()
            self.assertTrue(info2.get("skipped"))
            self.assertEqual(wf.sha256_file(p), sha1)
            np.testing.assert_array_equal(np.asarray(Image.open(p)), arr1)

    def test_workflow_version_bumped_for_new_rerender_semantics(self):
        self.assertEqual(wf.WORKFLOW_VERSION, "2.2")


# ---------------------------------------------------------------------------
# Golden: render_paraugs pilna izmēra izvadē (bez diska rakstīšanas)
# ---------------------------------------------------------------------------
class TestGoldenRenderParaugs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cut = np.zeros((600, 500, 4), np.uint8)
        cut[100:500, 80:420, :3] = (120, 30, 200)
        cut[100:500, 80:420, 3] = 255
        binary = (cut[:, :, 3] > 0).astype(np.uint8)
        cls.cut_pil = Image.fromarray(cut, "RGBA")
        cls.binary = binary
        cls.img, cls.placed, cls.full = loop.render_paraugs(cls.cut_pil, binary)
        cls.arr = np.asarray(cls.img)

    def test_canvas_geometry_and_corners(self):
        self.assertEqual(self.img.size, (2000, 2500))
        self.assertTrue(self.full)
        for y, x in [(0, 0), (0, -1), (-1, 0), (-1, -1)]:
            np.testing.assert_array_equal(self.arr[y, x], [243, 243, 243])

    def test_garment_core_colour_unchanged(self):
        np.testing.assert_array_equal(self.arr[1250, 1000], [120, 30, 200])

    def test_shadow_only_on_studio_side(self):
        pm = np.asarray(self.placed) > 0
        _, xs = np.nonzero(pm)
        x1, x0 = int(xs.max()), int(xs.min())
        east = int(self.arr[1250, x1 + 6, 0])   # metēnā ēna: izmērīts 166
        west = int(self.arr[1250, x0 - 6, 0])
        self.assertLess(east, 233)
        self.assertGreaterEqual(west, 240)

    def test_deterministic_bytes(self):
        again, _, _ = loop.render_paraugs(self.cut_pil, self.binary)
        self.assertEqual(hashlib.sha256(again.tobytes()).hexdigest(),
                         hashlib.sha256(self.img.tobytes()).hexdigest())


# ---------------------------------------------------------------------------
# Checker palīgfunkcijas un vārtu konstantes
# ---------------------------------------------------------------------------
class TestCheckerHelpers(unittest.TestCase):
    def test_largest_stats_ratio(self):
        m = np.zeros((30, 40), np.uint8)
        m[0:10, 0:30] = 1     # 300 px
        m[15:25, 30:40] = 1   # 100 px
        ratio, lab, idx = ck.largest_stats(m)
        self.assertAlmostEqual(ratio, 0.75, places=6)
        self.assertEqual(int((lab == idx).sum()), 300)

    def test_largest_stats_empty(self):
        ratio, _, idx = ck.largest_stats(np.zeros((10, 10), np.uint8))
        self.assertEqual((ratio, idx), (0.0, -1))

    def test_reconcile_metrics_identical(self):
        rng = np.random.default_rng(SEED)
        ref = rng.integers(0, 256, (32, 32, 3), dtype=np.uint8)
        fore = np.zeros((32, 32), bool)
        fore[:, :16] = True
        m = ck.reconcile_metrics(ref, ref.copy(), fore, ~fore)
        self.assertEqual((m["fore_p99"], m["bg_p99"], m["edge_ratio"]), (0.0, 0.0, 1.0))

    def test_reconcile_metrics_detects_change(self):
        ref = np.full((16, 16, 3), 100, np.uint8)
        par = ref.copy()
        par[:, :8] = 130
        fore = np.zeros((16, 16), bool)
        fore[:, :8] = True
        m = ck.reconcile_metrics(ref, par, fore, ~fore)
        self.assertEqual(m["fore_p99"], 30.0)
        self.assertEqual(m["bg_p99"], 0.0)

    def test_gate_r_thresholds_pinned(self):
        # §3.6/§5: sliekšņus nedrīkst klusi pārvietot, lai "izietu".
        self.assertEqual(ck.GATE_R_P99_MAX, 24.0)
        self.assertEqual(ck.GATE_R_BG_P99_MAX, 4.0)


# ---------------------------------------------------------------------------
# Infrastruktūra: faili un modeļa integritāte
# ---------------------------------------------------------------------------
class TestIoHelpers(unittest.TestCase):
    def test_sha256_file_known_value(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a.bin"
            p.write_bytes(b"abc")
            self.assertEqual(wf.sha256_file(p),
                             "ba7816bf8f01cfea414140de5dae2223"
                             "b00361a396177a9cb410ff61f20015ad")

    def test_atomic_write_json_roundtrip_no_tmp_left(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sub" / "x.json"
            wf.atomic_write_json(p, {"a": [1, 2], "b": "ē"})
            self.assertEqual(json.loads(p.read_text(encoding="utf-8")),
                             {"a": [1, 2], "b": "ē"})
            self.assertEqual([f.name for f in p.parent.iterdir()], ["x.json"])


class TestSetupModelStatus(unittest.TestCase):
    def _status_with(self, td, content: bytes | None, flip: bool = False):
        p = Path(td) / "model.onnx"
        if content is not None:
            body = bytearray(content)
            if flip:
                body[3] ^= 0xFF
            p.write_bytes(bytes(body))
        with mock.patch.object(setup_v2, "MODEL_PATH", p), \
             mock.patch.object(setup_v2, "MODEL_BYTES", len(content or b"")), \
             mock.patch.object(setup_v2, "MODEL_SHA256",
                               hashlib.sha256(content or b"").hexdigest()):
            return setup_v2._model_status()

    def test_ok_for_intact_model(self):
        with tempfile.TemporaryDirectory() as td:
            s = self._status_with(td, b"fake-model" * 16)
            self.assertTrue(s["ok"])

    def test_rejects_one_flipped_byte(self):
        with tempfile.TemporaryDirectory() as td:
            s = self._status_with(td, b"fake-model" * 16, flip=True)
            self.assertFalse(s["ok"])
            self.assertNotEqual(s["sha256"], s["expected_sha256"])

    def test_rejects_truncated(self):
        with tempfile.TemporaryDirectory() as td:
            full = b"fake-model" * 16
            with mock.patch.object(setup_v2, "MODEL_PATH", Path(td) / "m"), \
                 mock.patch.object(setup_v2, "MODEL_BYTES", len(full)), \
                 mock.patch.object(setup_v2, "MODEL_SHA256",
                                   hashlib.sha256(full).hexdigest()):
                (Path(td) / "m").write_bytes(full[:40])
                self.assertFalse(setup_v2._model_status()["ok"])

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            s = self._status_with(td, None)
            self.assertFalse(s["ok"])
            self.assertFalse(s["exists"])


if __name__ == "__main__":
    unittest.main()
