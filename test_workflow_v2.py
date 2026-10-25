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
import paper_leak
import plate_segment as ps
import setup_v2
import workflow_v2 as wf
from engine.chroma import (_dark_uncertain, _median_cut_palette,
                           chroma_mask, structural_qa)
from engine.masks import (boundary_evidence_metric, lost_fabric_metric,
                          plate_mask, reclaim_inlets,
                          repair_interior_holes)

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
        # Solis 6.2: ROTATIONS_CW dzīvo engine.infra; ražošana to visos
        # ceļos MUTĒ ar update(), tāpēc arī tests mutē, nevis pārsien
        # atsauci (pārsiešana mainītu tikai fasādes atributu).
        saved = dict(wf.ROTATIONS_CW)
        try:
            wf.ROTATIONS_CW.clear()
            wf.ROTATIONS_CW.update({"ABC123": 90, "201332": 270})
            self.assertEqual(wf.rotation_for("ABC123.jpg"), 90)
            self.assertEqual(wf.rotation_for("IMG_201332.jpg"), 270)  # pēdējo 6 zīmju atslēga
            self.assertEqual(wf.rotation_for("NEZINAMA.jpg"), 0)
        finally:
            wf.ROTATIONS_CW.clear()
            wf.ROTATIONS_CW.update(saved)


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
        # 2.2 = provenance/idempotence (solis 3); 2.3 = config.toml (solis 4);
        # 2.4 = chroma rezerves ceļš (§76); 2.5 = tumšās zonas piegājiens (§78);
        # 2.6 = iekšējo caurumu klasificēšana pēc satura (§97);
        # 2.7 = klasifikatora tekstūras pierādījums mērogā (§98);
        # 2.8 = zaudētā auduma (GATE_Q) trigeris kandidātu izvēlē (§103);
        # 2.9 = līču atgūšana Q trigerī pirms plate (§108);
        # 2.10 = union kandidāts Q trigerī (§109).
        # 2.11 = robežas pierādījuma STOP pirms rendera (§116).
        self.assertEqual(wf.WORKFLOW_VERSION, "2.11")


# ---------------------------------------------------------------------------
# Konfigurācija (solis 4): migrācijas sargs + stingrā ielāde + prioritāte
# ---------------------------------------------------------------------------
class TestConfig(unittest.TestCase):
    def test_values_equal_pre_migration_literals(self):
        """MIGRĀCIJAS SARGS: katra vērtība config.toml ir tieši tā pati, kas
        pirms soļa 4 bija nokoda kodā. Ja šis tests krīt mainot config —
        tā ir apzināta uzvedības maiņa: atjaunini tabulu TIKAI ar jaunu
        PROGRESS ierakstu un mērījumu."""
        self.assertEqual(wf.CFG, {
            "config_version": 1,
            "run": {"closeup_proc_w": 768, "png_level": 1, "framing": "auto",
                    "wb_mode": "auto", "auto_closeup": True,
                    "auto_grabcut_iters": 5},
            "mask": {"silhouette_fill_min": 0.60, "pad_retry": 0.90,
                     "pad_overflow_limit": 0.02, "pad_uncovered_limit": 0.05,
                     "pad_tex_relaxed": 2.5, "ai_qa_coverage_min": 0.15,
                     "ai_qa_coverage_max": 0.65, "ai_qa_largest_min": 0.95,
                     "ai_qa_bbox_area_min": 0.35, "ai_qa_bbox_w_min": 0.45,
                     "ai_qa_bbox_h_min": 0.35,
                     # caurumu klasificēšana (§97) — jauni parametri,
                     # neviena vecā vērtība nav mainīta
                     "hole_min_px": 400, "hole_margin_de": 3.0,
                     "hole_tex_ratio": 1.8, "hole_tex_abs": 1.0,
                     "hole_border_px": 96, "hole_max_cut_px": 250,
                     "hole_max_fill_frac": 0.02,
                     # tekstūras pierādījums mērogā (§98)
                     "hole_tex_scale": 4, "hole_tex_fg_ratio": 0.5,
                     "hole_tex_bg_ratio": 2.0, "hole_tex_min": 1.2,
                     "hole_L_slack": 4.0, "hole_tex_fg_ratio_max": 2.5,
                     "hole_bg_E": 8.0,
                     # GATE_Q trigeris (§103) — jāsakrīt ar checker konstantēm
                     "q_scale": 0.25, "q_close_r_ds": 10,
                     "q_tex_bg_ratio": 2.5, "q_tex_bg_abs": 2.0,
                     "q_tex_fg_ratio": 0.5, "q_trigger_pct": 1.0,
                     # robežas pierādījuma STOP (§116) — jāsakrīt ar
                     # checker GATE_S konstantēm
                     "s_scale": 0.25, "s_win_samples": 32,
                     "s_step_samples": 8, "s_rough_ds": 1.0,
                     "s_rough_frac_min": 0.20, "s_grad_max": 5.0,
                     "s_span_samples": 160, "s_limit_windows": 4,
                     "s_min_windows": 4,
                     # līču atgūšana (§108)
                     "reclaim_ds": 4, "reclaim_max_dist_ds": 60,
                     "reclaim_tex_bg_ratio": 2.5, "reclaim_tex_bg_abs": 1.0,
                     "reclaim_tex_lo_fg_ratio": 0.25, "reclaim_tex_min": 1.2,
                     "reclaim_tex_hi_ratio": 0.5, "reclaim_close_r_ds": 10,
                     "reclaim_dir_dist_ds": 15, "reclaim_min_comp_ds": 8,
                     "reclaim_solidify_r_px": 10, "reclaim_band_px": 16,
                     "reclaim_bg_E": 8.0, "reclaim_max_frac": 0.10},
            "plate": {"inner_min": 0.50, "outer_max": 0.60,
                      "bg_inside_max": 0.02, "cover_min": 0.25,
                      "cover_max": 0.95},
            "chroma": {"scale": 2, "palette_k": 8, "fg_alpha": 0.90,
                       "fg_core_alpha": 0.80, "fg_core_dist_px": 10.0,
                       "border_alpha_max": 0.50, "seed_margin_dE": 18.0,
                       "bg_refine_dE": 25.0, "margin_sigma": 2.0,
                       "min_cross_dE": 15.0, "seed_margin_ratio_min": 2.0,
                       "max_ambiguous_fraction": 0.08, "dark_L": 25.0,
                       "dark_palette_k": 4, "dark_min_cross_dE": 8.0,
                       "dark_uncertain_field": 5.0, "dark_tex_ratio": 1.5,
                       "dark_seed_min_frac": 0.0005,
                       "dark_carve_max_frac": 0.05},
            "decontam": {"max_px": 30, "tex_ratio": 0.45},
            "grade": {"curve_blend": 0.18, "highlight_knee": 0.86,
                      "exposure_target": 248.0, "exposure_min": 0.99,
                      "exposure_max": 1.06, "exposure_step": 0.01,
                      "exposure_max_adjustments": 6, "wb_chroma_max": 0.18,
                      "wb_shrink": 0.62, "gain_clip_min": 0.88,
                      "gain_clip_max": 1.14, "clipping_limit_pct": 1.5,
                      "sharpen_radius": 1.4, "sharpen_percent": 25,
                      "sharpen_threshold": 3},
        })

    def _variant(self, td, old, new):
        src = wf.CONFIG_PATH.read_text(encoding="utf-8")
        self.assertIn(old, src)
        p = Path(td) / "config.toml"
        p.write_text(src.replace(old, new, 1), encoding="utf-8")
        return p

    def test_unknown_key_typo_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._variant(td, "png_level = 1", "png_levl = 1")
            with self.assertRaises(ValueError):
                wf.load_config(p)

    def test_wrong_type_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._variant(td, "png_level = 1", 'png_level = "viens"')
            with self.assertRaises(ValueError):
                wf.load_config(p)

    def test_bad_choice_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._variant(td, 'framing = "auto"', 'framing = "zigzag"')
            with self.assertRaises(ValueError):
                wf.load_config(p)

    def test_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileNotFoundError):
                wf.load_config(Path(td) / "nav.toml")

    def _ns(self, **over):
        import argparse
        ns = argparse.Namespace(closeup_proc_w=None, png_level=None,
                                framing=None, wb_mode=None, auto_closeup=None,
                                auto_grabcut_iters=None)
        for k, v in over.items():
            setattr(ns, k, v)
        return ns

    def test_resolve_fills_from_config_and_cli_wins(self):
        ns = wf._resolve_args(self._ns())
        self.assertEqual((ns.png_level, ns.framing, ns.wb_mode, ns.auto_closeup),
                         (1, "auto", "auto", True))
        ns2 = wf._resolve_args(self._ns(png_level=3, wb_mode="identity",
                                        auto_closeup=False))
        self.assertEqual((ns2.png_level, ns2.wb_mode, ns2.auto_closeup),
                         (3, "identity", False))

    def test_effective_config_hash_stable_and_sensitive(self):
        ns = wf._resolve_args(self._ns())
        sha1 = wf._config_sha256(wf._effective_config(ns))
        sha2 = wf._config_sha256(wf._effective_config(ns))
        self.assertEqual(sha1, sha2)
        ns3 = wf._resolve_args(self._ns(png_level=2))
        eff3 = wf._effective_config(ns3)
        self.assertEqual(eff3["run"]["png_level"], 2)
        self.assertNotEqual(wf._config_sha256(eff3), sha1)


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
# Checker neatkarība (solis 5): nav importa no maker; realizācijas ekvivalentas
# ---------------------------------------------------------------------------
class TestCheckerIndependence(unittest.TestCase):
    def test_checker_source_does_not_import_maker(self):
        import ast
        tree = ast.parse(Path(ck.__file__).read_text(encoding="utf-8"))
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                mods.add(node.module)
        bad = {m for m in mods if m == "loop" or m.startswith("workflow_v2")}
        self.assertEqual(bad, set(), f"checker importē maker moduļus: {bad}")

    def test_apply_lut_bitwise_equivalent_to_maker(self):
        rng = np.random.default_rng(SEED)
        cases = [
            [np.arange(256, dtype=np.uint8)] * 3,
            [np.arange(255, -1, -1, dtype=np.uint8)] * 3,
            list(rng.integers(0, 256, (3, 256), dtype=np.uint8)),
        ]
        for shape in [(1, 1, 3), (17, 29, 3)]:
            rgb = rng.integers(0, 256, shape, dtype=np.uint8)
            for lut in cases:
                np.testing.assert_array_equal(
                    ck._apply_lut(rgb, lut), wf.apply_lut(rgb, lut))

    def test_apply_lut_rejects_bad_table(self):
        rgb = np.zeros((2, 2, 3), np.uint8)
        with self.assertRaises(ValueError):
            ck._apply_lut(rgb, [np.arange(255, dtype=np.uint8)] * 3)
        with self.assertRaises(ValueError):
            ck._apply_lut(rgb, [np.arange(256, dtype=np.uint8)] * 2)

    def test_quarter_turn_equivalent_to_maker(self):
        rng = np.random.default_rng(SEED)
        img = Image.fromarray(rng.integers(0, 256, (5, 7, 3), dtype=np.uint8))
        for deg in (0, 90, 180, 270, 360, -90):
            self.assertEqual(ck._quarter_turn_cw(img, deg).tobytes(),
                             wf.apply_quarter_turn(img, deg).tobytes(), f"deg={deg}")
        with self.assertRaises(ValueError):
            ck._quarter_turn_cw(img, 45)

    def test_gate_q_constants_equal_maker_trigger(self):
        """KRUSTSARGS (§103): maker trigera q_* parametriem jāsakrīt ar
        checker GATE_Q konstantēm — citādi trigeris klusi novirzās no
        vārtiem, kuriem tas mēģina palīdzēt iziet."""
        q = wf.CFG["mask"]
        self.assertEqual(q["q_trigger_pct"], ck.GATE_Q_LIMIT_PCT)
        self.assertEqual(q["q_scale"], ck.GATE_Q_SCALE)
        self.assertEqual(q["q_close_r_ds"], ck.GATE_Q_CLOSE_R_DS)
        self.assertEqual(q["q_tex_bg_ratio"], ck.GATE_Q_TEX_BG_RATIO)
        self.assertEqual(q["q_tex_bg_abs"], ck.GATE_Q_TEX_BG_ABS)
        self.assertEqual(q["q_tex_fg_ratio"], ck.GATE_Q_TEX_FG_RATIO)

    def test_gate_s_constants_equal_maker_mirror(self):
        """KRUSTSARGS (§116): maker STOP s_* parametriem jāsakrīt ar
        checker GATE_S konstantēm — citādi maker apturētu citus
        kadrus nekā checker soda (vai nepamanītu tos pašus)."""
        m = wf.CFG["mask"]
        self.assertEqual(m["s_scale"], ck.GATE_S_SCALE)
        self.assertEqual(m["s_win_samples"], ck.GATE_S_WIN_SAMPLES)
        self.assertEqual(m["s_step_samples"], ck.GATE_S_STEP_SAMPLES)
        self.assertEqual(m["s_rough_ds"], ck.GATE_S_ROUGH_DS)
        self.assertEqual(m["s_rough_frac_min"], ck.GATE_S_ROUGH_FRAC_MIN)
        self.assertEqual(m["s_grad_max"], ck.GATE_S_GRAD_MAX)
        self.assertEqual(m["s_span_samples"], ck.GATE_S_SPAN_SAMPLES)
        self.assertEqual(m["s_limit_windows"], ck.GATE_S_LIMIT_WINDOWS)
        self.assertEqual(m["s_min_windows"], ck.GATE_S_MIN_WINDOWS)

    def test_spec_constants_equal_current_maker_values(self):
        """KRUSTSARGS: checker specifikācija šodien sakrīt ar maker
        konstantēm. Ja kāda puse mainīsies viena pati, šis tests kritīs
        PIRMS klusa drifta ražošanā — izmaiņa jāveic apzināti abās ar
        PROGRESS ierakstu."""
        self.assertEqual(ck.SPEC_BG, loop.BG_GRAY)
        self.assertEqual(ck.SPEC_BG, 243)
        self.assertEqual(ck.SPEC_FILL_W, loop.GARMENT_FILL_W)
        self.assertEqual(ck.SPEC_FILL_H, loop.GARMENT_FILL_H)
        self.assertEqual(Path(ck.OUT), Path(loop.OUT))
        self.assertEqual(Path(ck.SRC_DIR), Path(loop.SRC_DIR))


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


class TestPlateThresholdFallback(unittest.TestCase):
    """PROGRESS §69: Otsu kritiens uz birkas makro `124406358`.

    Sintētika atveido izmērīto sadalījumu: vāja auduma tekstūra
    (E med ~3) + neliels ekstrēmas enerģijas bloks (E 45), kas Otsu
    aizvelk uz 20.8 — virs auduma. Fallback slieksnis no enkuriem
    atgūst patieso segumu 0.8125; veselīgs sadalījums paliek pie Otsu.
    """

    def _plane(self, amp, checker):
        rng = np.random.default_rng(42)
        h, w = 600, 800
        L = np.full((h, w), 59.0, np.float32)
        L += rng.normal(0, 0.6, (h, w)).astype(np.float32)
        yy, xx = np.mgrid[0:h, 0:w]
        L[:, :650] = (64.0 + amp * np.sin(yy[:, :650] * 2 * np.pi / 14)
                      + amp * np.sin(xx[:, :650] * 2 * np.pi / 14)
                      + rng.normal(0, 0.6, (h, 650)))
        if checker:
            chk = ((yy // 3 + xx // 3) % 2) * 90.0 - 45.0
            L[200:310, 250:360] = 60.0 + chk[200:310, 250:360]
        return L.astype(np.float32)

    def test_anchored_fallback_recovers_coverage(self):
        m, info = ps._detect(self._plane(amp=3.0, checker=True), 25)
        self.assertEqual(info["thr_method"], "anchored_fallback")
        self.assertAlmostEqual(float(m.mean()), 0.8125, delta=0.05)

    def test_healthy_distribution_stays_on_otsu(self):
        m, info = ps._detect(self._plane(amp=7.0, checker=False), 25)
        self.assertEqual(info["thr_method"], "otsu")
        self.assertAlmostEqual(float(m.mean()), 0.8125, delta=0.05)

    def test_anchored_threshold_is_geometric_mean(self):
        E = np.full((400, 400), 10.0, np.float32)
        E[:4, :] = E[-4:, :] = 2.0
        E[:, :4] = E[:, -4:] = 2.0
        thr = ps._anchored_threshold(E)
        self.assertIsNotNone(thr)
        self.assertAlmostEqual(thr, float(np.sqrt(2.0 * 10.0)), places=4)


class TestPlateBgInsideColor(unittest.TestCase):
    """PROGRESS §69: bg_inside skaita tikai papīra krāsas plakano daļu.

    Negatīvā kontrole: papīra krāsas pleķis auduma vidū QA joprojām
    noraida (bg_inside 0.17 > 0.02). Pozitīvā: gaiša gluda "birka"
    netiek karogota (0.0) un maska tiek pieņemta.
    """

    def _rgb(self, patch_gray):
        rng = np.random.default_rng(42)
        hf, wf_ = 1200, 1600
        img = np.full((hf, wf_), 190.0) + rng.normal(0, 2, (hf, wf_))
        yy, xx = np.mgrid[0:hf, 0:wf_]
        tex = (200 + 26 * np.sin(yy * 2 * np.pi / 16)
               + 26 * np.sin(xx * 2 * np.pi / 16) + rng.normal(0, 2, (hf, wf_)))
        img[100:1100, 100:1500] = tex[100:1100, 100:1500]
        img[400:800, 600:1000] = patch_gray + rng.normal(0, 2, (400, 400))
        return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGB")

    def test_paper_colored_patch_inside_still_rejected(self):
        _, qa = plate_mask(self._rgb(190))
        self.assertGreater(qa["bg_inside"], 0.02)
        self.assertFalse(qa["accept"])

    def test_bright_smooth_label_not_counted_as_paper(self):
        _, qa = plate_mask(self._rgb(245))
        self.assertLess(qa["bg_inside"], 0.005)
        self.assertTrue(qa["accept"])


class TestGatePVerdict(unittest.TestCase):
    """PROGRESS §70: GATE_P dalījums ķīlis pret ieslēgtiem ielokiem."""

    @staticmethod
    def _region(border, enclosed, area=1000):
        return {"touches_photo_border": border, "enclosed_by_fg": enclosed,
                "area_px": area, "max_depth_px": 10.0}

    def test_wedge_blocks(self):
        v = ck.gate_p_verdict([self._region(border=True, enclosed=False)])
        self.assertFalse(v["pass"])
        self.assertEqual(v["regions"], 1)
        self.assertEqual(v["enclosed_border_regions"], 0)

    def test_enclosed_border_only_reports(self):
        v = ck.gate_p_verdict([self._region(border=True, enclosed=True, area=3000)])
        self.assertTrue(v["pass"])
        self.assertEqual(v["regions"], 0)
        self.assertEqual(v["enclosed_border_regions"], 1)
        self.assertEqual(v["enclosed_border_px"], 3000)

    def test_interior_regions_ignored(self):
        v = ck.gate_p_verdict([self._region(border=False, enclosed=False)])
        self.assertTrue(v["pass"])
        self.assertEqual(v["regions"], 0)
        self.assertEqual(v["enclosed_border_regions"], 0)


class TestGatePIntegration(unittest.TestCase):
    """End-to-end caur `paper_leak.leak_probe` uz sintētikas (§70).

    Īsts ķīlis (maska pārskrien papīrā līdz kadra malai): reģions nav
    ieslēgts, dE 0.46. Gluda auduma josla līdz malai (birkas makro
    analogs): ieslēgts, dE 12.9. GATE_P izšķir abus.
    """

    def _scene(self, wedge):
        rng = np.random.default_rng(7)
        h, w = 1200, 1600
        yy, xx = np.mgrid[0:h, 0:w]
        tex = (205 + 26 * np.sin(yy * 2 * np.pi / 16)
               + 26 * np.sin(xx * 2 * np.pi / 16) + rng.normal(0, 1.5, (h, w)))
        paper = 150 + rng.normal(0, 1.5, (h, w))
        alpha = np.zeros((h, w), np.float32)
        if wedge:
            img = np.where(xx < 1280, tex, paper)
            alpha[:, :1280] = 1.0
            cv2.fillPoly(alpha, [np.array(
                [[1280, 520], [1600, 600], [1600, 700], [1280, 760]])], 1.0)
        else:
            img = np.where(xx < 1408, tex, paper)
            img[:170, :1408] = 185 + rng.normal(0, 1.5, (170, 1408))
            alpha[:, :1408] = 1.0
        rgb = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGB")
        return rgb, alpha

    def test_real_wedge_fails_gate_p(self):
        rgb, alpha = self._scene(wedge=True)
        res = paper_leak.leak_probe(rgb, alpha)
        self.assertFalse(ck.gate_p_verdict(res["regions"])["pass"])

    def test_smooth_fabric_band_at_border_passes(self):
        rgb, alpha = self._scene(wedge=False)
        res = paper_leak.leak_probe(rgb, alpha)
        v = ck.gate_p_verdict(res["regions"])
        self.assertEqual(v["enclosed_border_regions"], 1)
        self.assertTrue(v["pass"])


class TestChromaPath(unittest.TestCase):
    """PROGRESS §76: krāsu-attāluma rezerves ceļš ne-papīra fonam.

    Sintētika atdarina izmērīto gadījumu (zila pufjaka uz koka, §75):
    ISNet mīkstā maska zaudē veselu paneli un plānu joslu pārplūst uz
    grīdas; apģērbs pieskaras kadra malām, tāpēc tīra gredzena palete
    neder (prototips #1 deva segumu 0.0).
    """

    def _scene(self, garment_rgb=(60, 90, 190), bg_rgb=(170, 130, 85)):
        rng = np.random.default_rng(11)
        h, w = 1200, 1600
        yy, xx = np.mgrid[0:h, 0:w]
        img = np.zeros((h, w, 3))
        for c, base in enumerate(bg_rgb):
            img[..., c] = (base + 18 * np.sin(yy * 2 * np.pi / 90 + c)
                           + rng.normal(0, 4, (h, w)))
        truth = np.zeros((h, w), bool)
        truth[250:h, 0:1150] = True          # apģērbs pāri kreisai+apakš malai
        shade = 0.75 + 0.45 * (xx / w)        # ēnojums pāri audumam
        for c, base in enumerate(garment_rgb):
            img[..., c] = np.where(truth, base * shade
                                   + rng.normal(0, 4, (h, w)), img[..., c])
        rgb = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        soft = np.where(truth, 245, 5).astype(np.uint8)
        soft[800:h, 700:1150] = 10            # ISNet zaudē paneli
        soft[250:400, 1150:1180] = 240        # plāna pārplūde uz fona
        return rgb, soft, truth

    def test_recovers_missed_panel_and_rejects_spill(self):
        rgb, soft, truth = self._scene()
        binary, qa = chroma_mask(rgb, [soft])
        self.assertTrue(qa["accept"], qa.get("reason"))
        m = binary > 0
        iou = float((m & truth).sum() / (m | truth).sum())
        self.assertGreaterEqual(iou, 0.93)
        self.assertGreaterEqual(float(m[800:, 700:1150].mean()), 0.95)
        # joslas iekšpuse (bez ~10 px robežas zonas, ko pusmērogs izpludina)
        self.assertLessEqual(float(m[250:400, 1162:1180].mean()), 0.05)

    def test_same_color_garment_and_background_rejected(self):
        rgb, soft, _ = self._scene(garment_rgb=(170, 130, 85))
        _, qa = chroma_mask(rgb, [soft])
        self.assertFalse(qa["accept"])

    def test_no_foreground_seeds_rejected(self):
        rgb, _, _ = self._scene()
        _, qa = chroma_mask(rgb, [np.zeros((1200, 1600), np.uint8)])
        self.assertFalse(qa["accept"])

    def test_dark_uncertain_marks_shadow_bay_not_fabric(self):
        # §78 mehānisms Lab līmenī: dziļās ēnas līcis (gandrīz melns
        # neitrāls) ir nedrošs; tumša auduma kroka ar tekstūru nav.
        rng = np.random.default_rng(5)
        h, w = 400, 500
        lab = np.zeros((h, w, 3), np.float32)
        lab[:] = (60, 12, 25)                       # apgaismots fons
        lab[0:60, :] = (13, 6, 8)                   # fona ēnas josla
        lab[100:400, 0:350] = (45, 5, -35)          # apģērbs
        # tumša kroka kā nepārtraukts ēnojuma gradients (kā īstā foto,
        # kur līcis 5% sēklu robežās savu centru neizolē, §78)
        grad = np.linspace(0.0, 1.0, 200, dtype=np.float32)[None, :]
        lab[100:400, 0:200, 0] = 9.0 + 14.0 * grad
        lab[100:400, 0:200, 1] = 1.0
        lab[100:400, 0:200, 2] = -5.0 - 9.0 * grad
        bay = np.zeros((h, w), bool)
        bay[280:400, 220:280] = True
        lab[bay] = (8, 3, 3)                        # ēnas līcis
        yy, xx = np.mgrid[0:h, 0:w]
        garment = np.zeros((h, w), bool)
        garment[100:400, 0:350] = True
        lab[..., 0] += np.where(garment & ~bay,
                                2.5 * np.sin(xx * 2 * np.pi / 12), 0.0)
        lab += rng.normal(0, 0.4, lab.shape).astype(np.float32)
        a_bg = np.where(garment, 0.97, 0.02).astype(np.float32)
        fg_seed = np.zeros((h, w), bool)
        fg_seed[115:400, 15:335] = True             # arī līcī (pārplūde)
        uncertain, info = _dark_uncertain(
            lab, a_bg, fg_seed,
            np.array([[45, 5, -35], [12, 1, -8]], np.float32),
            np.array([[60, 12, 25], [13, 6, 8]], np.float32),
            wf.CFG["chroma"])
        self.assertIsNotNone(uncertain, info)
        self.assertGreaterEqual(float(uncertain[290:400, 230:270].mean()), 0.8)
        self.assertLessEqual(float(uncertain[150:350, 20:180].mean()), 0.1)

    def test_palette_is_deterministic(self):
        rng = np.random.default_rng(3)
        s = rng.normal(50, 15, (5000, 3)).astype(np.float32)
        c1, sup1 = _median_cut_palette(s, 6)
        c2, sup2 = _median_cut_palette(s, 6)
        np.testing.assert_array_equal(c1, c2)
        self.assertEqual(sup1, sup2)

    def test_structural_qa(self):
        ok = np.zeros((600, 800), np.uint8)
        ok[100:500, 100:700] = 1
        self.assertTrue(structural_qa(ok)["accept"])
        hole = ok.copy()
        hole[250:350, 350:450] = 0            # 10 000 px ieslēgts caurums
        q = structural_qa(hole)
        self.assertFalse(q["accept"])
        self.assertEqual(q["interior_holes_ge400"], 1)
        frag = np.zeros((600, 800), np.uint8)
        frag[::3, ::3] = 1                    # fragmenti, ne siluets
        self.assertFalse(structural_qa(frag)["accept"])


class TestMakeZipSubset(unittest.TestCase):
    """PROGRESS §81: lietotājs drīkst izslēgt kadru no piegādes; ZIP
    satur tikai atlasītās, izslēgtā tiek ierakstīta delivery atskaitē,
    un nezināms stems ir kļūda (ne klusa ignorēšana)."""

    def test_subset_excludes_and_records(self):
        import zipfile as zf

        import engine.report as rep
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            (out / "paraugs").mkdir()
            stems = ["STEM_A", "STEM_B", "STEM_C"]
            for s in stems:
                (out / "paraugs" / f"{s}_PARAUGS_2000x2500.jpg").write_bytes(
                    s.encode() * 10)
            (out / "report_v2_maker.json").write_text(json.dumps(
                {"attempt": 4,
                 "images": {s: {"status": "completed"} for s in stems}}))
            (out / "report_v2.json").write_text(json.dumps(
                {s: {"ALL_PASS": True} for s in stems}))
            with mock.patch.object(rep, "OUT", str(out)), \
                    mock.patch.object(rep, "REPORT_PATH", out / "report_v2_maker.json"), \
                    mock.patch.object(rep, "CHECKER_REPORT_PATH", out / "report_v2.json"), \
                    mock.patch.object(rep, "DELIVERY_REPORT_PATH", out / "delivery_v2.json"):
                rep.make_zip(only_stems={"STEM_A", "STEM_C"})
                with zf.ZipFile(out / "V2_GALA_BILDES.zip") as z:
                    names = sorted(z.namelist())
                delivery = json.loads((out / "delivery_v2.json").read_text())
                with self.assertRaises(RuntimeError):
                    rep.make_zip(only_stems={"STEM_X"})
            self.assertEqual(names, ["STEM_A_PARAUGS_2000x2500.jpg",
                                     "STEM_C_PARAUGS_2000x2500.jpg"])
            self.assertEqual(delivery["excluded_by_user"], ["STEM_B"])


# ---------------------------------------------------------------------------
# Iekšējo caurumu klasificēšana pēc satura (PROGRESS §97)
# ---------------------------------------------------------------------------
class TestHoleRepair(unittest.TestCase):
    BG = (150, 148, 140)
    FG = (225, 222, 215)

    def _scene(self, size=240, garment=(40, 40, 200, 200), hole=None,
               hole_fill=None):
        """Sintētiska aina: gluds pelēks fons, teksturēts gaišs apģērba
        taisnstūris, bināra maska ar ieslēgtu caurumu `hole`=(x0,y0,x1,y1),
        kura SATURS oriģinālā ir `hole_fill` (krāsa vai "fabric")."""
        rgb = np.tile(np.array(self.BG, np.uint8), (size, size, 1))
        gx0, gy0, gx1, gy1 = garment
        yy, xx = np.indices((size, size))
        tex = (((xx // 4) + (yy // 4)) % 2) * 36 - 18
        fabric = np.clip(np.array(self.FG, np.int16) + tex[..., None],
                         0, 255).astype(np.uint8)
        rgb[gy0:gy1, gx0:gx1] = fabric[gy0:gy1, gx0:gx1]
        binary = np.zeros((size, size), np.uint8)
        binary[gy0:gy1, gx0:gx1] = 1
        if hole is not None:
            hx0, hy0, hx1, hy1 = hole
            binary[hy0:hy1, hx0:hx1] = 0
            if hole_fill == "fabric":
                pass  # saturs jau ir audums (maska to pazaudējusi)
            elif hole_fill is not None:
                rgb[hy0:hy1, hx0:hx1] = np.array(hole_fill, np.uint8)
        return rgb, binary

    def test_fabric_hole_is_filled(self):
        rgb, binary = self._scene(hole=(90, 90, 120, 110),
                                  hole_fill="fabric")
        out, info = repair_interior_holes(binary, Image.fromarray(rgb))
        self.assertTrue(bool((out[90:110, 90:120] > 0).all()))
        self.assertEqual(info["actions"][0]["action"], "filled_fabric")

    def test_bg_hole_near_border_is_opened(self):
        from scipy import ndimage
        rgb, binary = self._scene(garment=(10, 40, 200, 200),
                                  hole=(20, 90, 45, 110), hole_fill=self.BG)
        out, info = repair_interior_holes(binary, Image.fromarray(rgb))
        self.assertEqual(info["actions"][0]["action"], "opened_bg")
        self.assertLessEqual(info["actions"][0]["cut_px"], 250)
        largest = (out > 0)
        holes_left = ndimage.binary_fill_holes(largest) & ~largest
        self.assertEqual(int(holes_left[90:110, 20:45].sum()), 0)

    def test_bg_hole_far_from_border_left(self):
        rgb, binary = self._scene(size=400, garment=(100, 30, 370, 370),
                                  hole=(150, 185, 176, 211),
                                  hole_fill=self.BG)
        out, info = repair_interior_holes(binary, Image.fromarray(rgb))
        self.assertTrue(np.array_equal(out, binary))
        self.assertEqual(info["actions"][0]["action"], "left")

    def test_ambiguous_hole_left(self):
        rgb, binary = self._scene(hole=(90, 90, 120, 110),
                                  hole_fill=(188, 185, 178))
        out, info = repair_interior_holes(binary, Image.fromarray(rgb))
        self.assertTrue(np.array_equal(out, binary))
        self.assertEqual(info["actions"][0]["action"], "left")

    def test_small_hole_ignored(self):
        rgb, binary = self._scene(garment=(10, 40, 200, 200),
                                  hole=(20, 90, 30, 100), hole_fill=self.BG)
        out, info = repair_interior_holes(binary, Image.fromarray(rgb))
        self.assertTrue(np.array_equal(out, binary))
        self.assertEqual(info["holes_ge_min"], 0)

    def test_too_large_fabric_hole_left(self):
        # 40x40 = 1600 px > 2% no 240x240 (1152 px) -> eskalācija, nelabo
        rgb, binary = self._scene(hole=(90, 90, 130, 130),
                                  hole_fill="fabric")
        out, info = repair_interior_holes(binary, Image.fromarray(rgb))
        self.assertTrue(np.array_equal(out, binary))
        self.assertEqual(info["actions"][0]["action"], "left")

    def test_ribbed_valley_strip_filled_via_texture(self):
        """§97 reālā kadra (160550) sintētiska replika: ribu audums,
        kura ielejas krāsā sakrīt ar fonu. Maska pazaudējusi vienu
        ieleju joslu: Lab mediāna saka "fons", bet tekstūra mērogā
        (ribu periods 24 px >> win=5) saka "audums" -> jāaizpilda."""
        size = 320
        rgb = np.tile(np.array(self.BG, np.uint8), (size, size, 1))
        xx = np.indices((size, size))[1]
        bright = (xx % 24) < 12
        fabric = np.where(bright[..., None],
                          np.array([232, 230, 224], np.uint8),
                          np.array(self.BG, np.uint8)).astype(np.uint8)
        rgb[40:280, 16:280] = fabric[40:280, 16:280]
        binary = np.zeros((size, size), np.uint8)
        binary[40:280, 16:280] = 1
        binary[90:150, 36:48] = 0  # viena ieleja (x%24 = 12..23)
        out, info = repair_interior_holes(binary, Image.fromarray(rgb))
        self.assertTrue(bool((out[90:150, 36:48] > 0).all()))
        self.assertEqual(info["actions"][0]["action"], "filled_fabric")
        self.assertEqual(info["actions"][0]["via"], "texture")

    def test_narrow_bg_sliver_opened_via_fullres_fallback(self):
        """12 px plats fona šķēlums: mēroga tekstūras logs caurumā
        neietilpst (tex_hole_core_s = None), tāpēc gludumu vērtē
        pilnizšķirtspējas tekstūra -> atver pie malas. Auduma
        pierādījumu bloķē L diapazona sargs (papīra L ārpus gredzena)."""
        rgb, binary = self._scene(garment=(10, 40, 200, 200),
                                  hole=(20, 90, 32, 140), hole_fill=self.BG)
        out, info = repair_interior_holes(binary, Image.fromarray(rgb))
        self.assertEqual(info["actions"][0]["action"], "opened_bg")
        self.assertIsNone(info["actions"][0]["tex_hole_core_s"])

    def test_no_holes_identity(self):
        rgb, binary = self._scene()
        out, info = repair_interior_holes(binary, Image.fromarray(rgb))
        self.assertTrue(np.array_equal(out, binary))
        self.assertEqual(info["holes_total"], 0)


# ---------------------------------------------------------------------------
# Zaudētā auduma metrika maker pusē (GATE_Q trigeris, PROGRESS §103)
# ---------------------------------------------------------------------------
class TestLostFabricMetric(unittest.TestCase):
    def _scene(self, channel=False):
        H, W = 1000, 800
        rgb = np.tile(np.array([170, 168, 160], np.uint8), (H, W, 1))
        yy, xx = np.indices((H, W))
        tex = (((xx // 6) + (yy // 6)) % 2) * 44 - 22
        fabric = np.clip(np.array([210, 206, 198], np.int16) + tex[..., None],
                         0, 255).astype(np.uint8)
        rgb[80:920, 100:700] = fabric[80:920, 100:700]
        binary = np.zeros((H, W), np.uint8)
        binary[80:920, 100:700] = 1
        if channel:
            binary[80:920, 380:420] = 0
        return rgb, binary

    def test_clean_candidate_below_trigger(self):
        rgb, binary = self._scene()
        m = lost_fabric_metric(binary, Image.fromarray(rgb))
        self.assertLess(m["lost_fabric_pct"],
                        wf.CFG["mask"]["q_trigger_pct"], m)

    def test_channel_candidate_above_trigger(self):
        rgb, binary = self._scene(channel=True)
        m = lost_fabric_metric(binary, Image.fromarray(rgb))
        self.assertGreater(m["lost_fabric_pct"],
                           wf.CFG["mask"]["q_trigger_pct"], m)

    def test_agrees_with_checker_gate_direction(self):
        """Maker metrika un checker GATE_Q uz tiem pašiem sintētiskajiem
        kadriem dod saskaņotu spriedumu (trigeris redz to, ko vārti)."""
        for channel, expect_bad in ((False, False), (True, True)):
            rgb, binary = self._scene(channel=channel)
            m = lost_fabric_metric(binary, Image.fromarray(rgb))
            g = ck.lost_fabric_gate(rgb, (binary * 255).astype(np.uint8))
            self.assertEqual(m["lost_fabric_pct"] > 1.0, expect_bad)
            self.assertEqual(g["pass"], not expect_bad)


# ---------------------------------------------------------------------------
# Kandidātu izvēle Q trigerī (PROGRESS §109)
# ---------------------------------------------------------------------------
class TestChooseCandidate(unittest.TestCase):
    def test_tie_prefers_union(self):
        self.assertEqual(wf.choose_candidate(
            [("current", 0.04, True), ("plate", 0.03, True),
             ("union", 0.03, True)]), "union")

    def test_lowest_q_wins(self):
        self.assertEqual(wf.choose_candidate(
            [("current", 0.5, True), ("plate", 0.2, True),
             ("union", 0.4, True)]), "plate")

    def test_structural_reject_excluded(self):
        self.assertEqual(wf.choose_candidate(
            [("current", 0.9, True), ("plate", 0.1, False),
             ("union", 0.1, False)]), "current")

    def test_none_q_excluded_and_empty_fallback(self):
        self.assertEqual(wf.choose_candidate(
            [("current", None, True), ("plate", None, True),
             ("union", None, True)]), "current")
        self.assertEqual(wf.choose_candidate([]), "current")


# ---------------------------------------------------------------------------
# Līču atgūšana ražošanā (PROGRESS §108)
# ---------------------------------------------------------------------------
class TestReclaimInlets(unittest.TestCase):
    def _scene(self):
        H, W = 1000, 800
        rgb = np.tile(np.array([170, 168, 160], np.uint8), (H, W, 1))
        yy, xx = np.indices((H, W))
        tex = (((xx // 6) + (yy // 6)) % 2) * 44 - 22
        fabric = np.clip(np.array([210, 206, 198], np.int16) + tex[..., None],
                         0, 255).astype(np.uint8)
        rgb[80:920, 100:800] = fabric[80:920, 100:800]  # audums līdz labai malai
        binary = np.zeros((H, W), np.uint8)
        binary[80:920, 100:800] = 1
        return rgb, binary

    def test_channel_reclaimed(self):
        """40 px auduma kanāls maskā iztrūkst -> atgūšana to aizpilda
        un Q metrika nokrīt zem trigera."""
        rgb, binary = self._scene()
        binary[80:920, 380:420] = 0
        out, info = reclaim_inlets(binary, Image.fromarray(rgb))
        self.assertGreater(info["reclaimed_px"], 0, info)
        self.assertTrue(bool((out[80:920, 392:408] > 0).mean() > 0.9))
        q = lost_fabric_metric(out, Image.fromarray(rgb))
        self.assertLessEqual(q["lost_fabric_pct"], 1.0)

    def test_edge_sliver_reclaimed(self):
        """11 px auduma šķēle pie kadra labās malas iztrūkst (lietotāja
        atzīmju replika §107) -> malas josla to aizpilda līdz malai."""
        rgb, binary = self._scene()
        binary[300:600, 789:800] = 0
        out, info = reclaim_inlets(binary, Image.fromarray(rgb))
        self.assertTrue(bool((out[300:600, 795:800] > 0).all()))

    def test_paper_window_not_reclaimed(self):
        """240 px gluds fona logs auduma vidū nedrīkst tikt aizpildīts."""
        rgb, binary = self._scene()
        rgb[380:620, 280:520] = np.array([170, 168, 160], np.uint8)
        binary[380:620, 280:520] = 0
        out, info = reclaim_inlets(binary, Image.fromarray(rgb))
        self.assertTrue(bool((out[480:520, 380:420] == 0).all()))

    def test_clean_mask_unchanged(self):
        rgb, binary = self._scene()
        out, info = reclaim_inlets(binary, Image.fromarray(rgb))
        self.assertEqual(info["reclaimed_px"], 0, info)
        self.assertTrue(np.array_equal(out, binary))


# ---------------------------------------------------------------------------
# GATE_Q: zaudētais audums ārpus maskas (PROGRESS §102)
# ---------------------------------------------------------------------------
class TestGateQ(unittest.TestCase):
    def _scene(self):
        """Teksturēts apģērba taisnstūris uz gluda fona; alfa = audums."""
        H, W = 1000, 800
        rgb = np.tile(np.array([170, 168, 160], np.uint8), (H, W, 1))
        yy, xx = np.indices((H, W))
        tex = (((xx // 6) + (yy // 6)) % 2) * 44 - 22
        fabric = np.clip(np.array([210, 206, 198], np.int16) + tex[..., None],
                         0, 255).astype(np.uint8)
        rgb[80:920, 100:700] = fabric[80:920, 100:700]
        alpha = np.zeros((H, W), np.uint8)
        alpha[80:920, 100:700] = 255
        return rgb, alpha

    def test_clean_garment_passes(self):
        rgb, alpha = self._scene()
        res = ck.lost_fabric_gate(rgb, alpha)
        self.assertTrue(res["pass"], res)
        self.assertLess(res["lost_fabric_pct"], ck.GATE_Q_LIMIT_PCT)

    def test_fabric_channel_sabotage_fails(self):
        """Maska pa vidu audumam izmet 40 px kanālu (ieleju svītras
        replika 160550): saturs ir audums, kanāls šaurs -> jākrīt."""
        rgb, alpha = self._scene()
        alpha[80:920, 380:420] = 0
        res = ck.lost_fabric_gate(rgb, alpha)
        self.assertFalse(res["pass"], res)
        self.assertGreater(res["lost_fabric_pct"], ck.GATE_Q_LIMIT_PCT)

    def test_paper_window_passes(self):
        """240 px gluda papīra logs auduma vidū (izgriezuma replika):
        plats un gluds -> nav zaudētais audums, jāiziet."""
        rgb, alpha = self._scene()
        rgb[380:620, 280:520] = np.array([170, 168, 160], np.uint8)
        alpha[380:620, 280:520] = 0
        res = ck.lost_fabric_gate(rgb, alpha)
        self.assertTrue(res["pass"], res)

    def test_limit_pinned(self):
        # §3.6/§5: slieksni nedrīkst klusi pārvietot, lai "izietu".
        # Kalibrācija §102: labie <= 0.101%, sliktais 4.27%.
        self.assertEqual(ck.GATE_Q_LIMIT_PCT, 1.0)


# ---------------------------------------------------------------------------
# GATE_S: robežas pierādījums (PROGRESS §113-§115)
# ---------------------------------------------------------------------------
class TestGateS(unittest.TestCase):
    def _scene(self, blur_sigma=0.0, jagged=False):
        """Gluds apģērba taisnstūris (kontrasts 40) uz gluda fona.

        blur_sigma izpludina AVOTA malu (defokusa replika); jagged
        padara ALFAS augšējo malu par +/-6 px kvadrātvilni garā posmā.
        """
        H, W = 1000, 800
        gray = np.full((H, W), 155.0, np.float32)
        gray[120:920, 100:700] = 195.0
        if blur_sigma:
            gray = cv2.GaussianBlur(gray, (0, 0), blur_sigma)
        rgb = np.clip(np.repeat(gray[..., None], 3, axis=2),
                      0, 255).astype(np.uint8)
        alpha = np.zeros((H, W), np.uint8)
        alpha[120:920, 100:700] = 255
        if jagged:
            alpha[100:140, 160:640] = 0
            for x in range(160, 640):
                top = 114 if ((x - 160) // 8) % 2 == 0 else 126
                alpha[top:920, x] = 255
        return rgb, alpha

    def test_sharp_smooth_passes(self):
        rgb, alpha = self._scene()
        res = ck.boundary_evidence_gate(rgb, alpha)
        self.assertTrue(res["pass"], res)

    def test_defocused_smooth_passes(self):
        """Defokuss viens pats nav defekts: gluda kontūra cauri
        izplūdušai malai ir pierādāma tikpat labi kā asa."""
        rgb, alpha = self._scene(blur_sigma=14.0)
        res = ck.boundary_evidence_gate(rgb, alpha)
        self.assertTrue(res["pass"], res)

    def test_sharp_jagged_passes(self):
        """Nelīdzena kontūra viena pati nav defekts: asā malā
        viļņojumam ir pikseļu liecība (stūri/krokas drīkst būt asi)."""
        rgb, alpha = self._scene(jagged=True)
        res = ck.boundary_evidence_gate(rgb, alpha)
        self.assertTrue(res["pass"], res)

    def test_defocused_jagged_sabotage_fails(self):
        """160601 klase: kontūra viļņojas tur, kur avota mala ir
        izplūdusi — robeža nav pierādāma, jākrīt."""
        rgb, alpha = self._scene(blur_sigma=14.0, jagged=True)
        res = ck.boundary_evidence_gate(rgb, alpha)
        self.assertFalse(res["pass"], res)
        self.assertGreaterEqual(res["worst_span_windows"],
                                ck.GATE_S_LIMIT_WINDOWS)

    def test_constants_pinned(self):
        # Kalibrācija §114: kontroles 0-1 logs, sliktie 12-14.
        # Sliekšņus maina tikai ar jaunu kalibrāciju un pogu.
        self.assertEqual(ck.GATE_S_LIMIT_WINDOWS, 4)
        self.assertEqual(ck.GATE_S_GRAD_MAX, 5.0)
        self.assertEqual(ck.GATE_S_ROUGH_FRAC_MIN, 0.20)
        self.assertEqual(ck.GATE_S_SCALE, 0.25)


# ---------------------------------------------------------------------------
# Maker robežas pierādījuma STOP metrika (PROGRESS §116)
# ---------------------------------------------------------------------------
class TestBoundaryEvidenceMetric(unittest.TestCase):
    """Tā pati sintētiskā aina kā TestGateS (TestGateS._scene):
    maker spogulim uz binārās maskas jāsakrīt virzienā ar checker."""

    def _metric(self, **kw):
        rgb, alpha = TestGateS()._scene(**kw)
        binary = (alpha > 127).astype(np.uint8)
        return boundary_evidence_metric(binary, Image.fromarray(rgb))

    def test_clean_mask_not_uncertain(self):
        m = self._metric()
        self.assertFalse(m["uncertain"], m)
        self.assertLess(m["worst_span_windows"], m["limit_windows"])

    def test_defocused_jagged_uncertain(self):
        m = self._metric(blur_sigma=14.0, jagged=True)
        self.assertTrue(m["uncertain"], m)
        self.assertGreaterEqual(m["worst_span_windows"],
                                m["limit_windows"])
        self.assertIsNotNone(m["worst_center_xy_fullres"])

    def test_agrees_with_checker_gate_direction(self):
        for kw, expect_bad in [({}, False),
                               ({"blur_sigma": 14.0, "jagged": True}, True)]:
            rgb, alpha = TestGateS()._scene(**kw)
            m = boundary_evidence_metric((alpha > 127).astype(np.uint8),
                                         Image.fromarray(rgb))
            g = ck.boundary_evidence_gate(rgb, alpha)
            self.assertEqual(m["uncertain"], expect_bad, (kw, m))
            self.assertEqual(not g["pass"], expect_bad, (kw, g))


# ---------------------------------------------------------------------------
# Atvasinātās Slam Jam detaļas (PROGRESS §123)
# ---------------------------------------------------------------------------
class TestSlamjamDetails(unittest.TestCase):
    """D receptes ģeometrija un vārti closeup.py slamjam režīmā."""

    def test_min_src_h_satisfies_both_gates(self):
        import closeup as cu
        src_h = cu.min_src_h_for_upscale()
        m = cu.slamjam_metrics(src_h)
        self.assertLessEqual(m["upscale_geom"], cu.SLAMJAM_MAX_UPSCALE + 1e-9)
        self.assertGreaterEqual(m["source_fraction"],
                                cu.SLAMJAM_MIN_SOURCE_FRAC - 1e-9)
        passed, reasons = cu.slamjam_gate(m, coverage=0.95)
        self.assertTrue(passed, reasons)

    def test_gate_rejects_small_field_and_low_coverage(self):
        import closeup as cu
        m = cu.slamjam_metrics(600)  # pārāk tuvu: palielinājums ~4.6x
        passed, reasons = cu.slamjam_gate(m, coverage=0.95)
        self.assertFalse(passed)
        self.assertTrue(any("upscale_geom" in r for r in reasons), reasons)
        m2 = cu.slamjam_metrics(cu.min_src_h_for_upscale())
        passed2, reasons2 = cu.slamjam_gate(m2, coverage=0.50)
        self.assertFalse(passed2)
        self.assertTrue(any("coverage" in r for r in reasons2), reasons2)

    def test_quad_has_perspective_trapezoid(self):
        import closeup as cu
        quad = cu.slamjam_quad((1600, 1430), 1200)
        top = float(np.linalg.norm(quad[1] - quad[0]))
        bottom = float(np.linalg.norm(quad[2] - quad[3]))
        self.assertGreater(top, bottom)  # tālākā mala aptver vairāk auduma
        self.assertAlmostEqual(float(quad[:, 0].mean()), 1430, delta=2.0)
        self.assertAlmostEqual(float(quad[:, 1].mean()), 1600, delta=2.0)

    def test_render_slamjam_synthetic(self):
        import closeup as cu
        master = np.zeros((500, 400, 3), np.uint8)
        master[:] = (200, 180, 160)
        master[200:260, 150:250] = (40, 60, 200)  # "poga"
        mask = np.zeros((500, 400), bool)
        mask[60:440, 40:360] = True
        profile = {"lut_rgb": [list(range(256))] * 3}
        img, _quad, metrics, coverage = cu.render_slamjam(
            master, mask, profile, (250, 200), 180, canvas=(200, 250),
            usm_percent=0)
        self.assertEqual(img.shape, (250, 200, 3))
        self.assertGreater(coverage, 0.80)
        self.assertGreater(metrics["upscale_geom"], 1.0)
        # zilā "poga" pēc warp joprojām atrodama izējē
        button_px = int(((img[:, :, 2] > 150) & (img[:, :, 0] < 100)).sum())
        self.assertGreater(button_px, 50)


if __name__ == "__main__":
    unittest.main()
