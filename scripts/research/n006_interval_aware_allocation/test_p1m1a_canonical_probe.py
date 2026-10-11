"""P1m1a static/fail-closed contracts; no GPU execution or signed quality."""
import re
import struct
import tempfile
import unittest
from pathlib import Path

import run_p1m1a_canonical_probe_pilot as m1

ROOT = Path(__file__).resolve().parents[3]
SHADER = ROOT / "shaders/research/n006_interval_aware_allocation/n006_p1m1_canonical_key_extra.comp.glsl"
LEGACY = ROOT / "shaders/research/n006_interval_aware_allocation/n006_extra_producer.comp.glsl"
RUNTIME = ROOT / "src/research/n006_interval_aware_allocation/n006_runtime.cpp"
HEADER = ROOT / "src/research/n006_interval_aware_allocation/n006_runtime.hpp"
CLI = ROOT / "src/research/n006_interval_aware_allocation/n006_intervention_main.cpp"
CMAKE = ROOT / "src/research/lane_n_end_to_end_renderer/CMakeLists.txt"


class TestCanonicalM1Mechanism(unittest.TestCase):
    def test_exact_p1a_deterministic_direction_rule(self):
        expression = r"vec3 extra_direction\(WorkItem item, uint ordinal\) \{.*?\n\}"
        original = re.search(expression, LEGACY.read_text(), flags=re.S)
        candidate = re.search(expression, SHADER.read_text(), flags=re.S)
        self.assertIsNotNone(original)
        self.assertIsNotNone(candidate)
        compact = lambda v: re.sub(r"\s+", "", v)
        self.assertEqual(compact(original.group()), compact(candidate.group()))

    def test_single_canonical_key_append_no_base_rewrite(self):
        shader = SHADER.read_text()
        for phrase in (
            "layout(local_size_x = 1)", "output_id * pc.rays_per_probe",
            "base_count != outputs * pc.rays_per_probe",
            "pc.extra_rays != 4u", "base_count + pc.extra_rays > p.limits.y",
            "if (stats.data[1] != 1u)", "item.ray_index = pc.rays_per_probe + extra",
            "work.items[base_count + extra] = item",
            "counters.data[0] = base_count + pc.extra_rays",
            "counters.data[4] = counters.data[0]",
            "stats.data[5] = 5u",
        ):
            self.assertIn(phrase, shader)
        self.assertNotIn("work.items[output_id * pc.rays_per_probe] =", shader)
        self.assertNotIn("counters.data[1] =", shader)
        self.assertNotIn("counters.data[5] =", shader)

    def test_placement_parity_and_buffer_lifetime(self):
        runtime = RUNTIME.read_text()
        header = HEADER.read_text()
        main = CLI.read_text()
        build = CMAKE.read_text()
        start = runtime.index("state_->canonical_compact_stage->record_indirect(")
        # Both P1m1a and P1m2a use this one placement; M2a merely
        # selects a separate shader at the same pre-secondary boundary.
        dispatch = re.search(
            r"\(request\.p1m2_tetra_octant_directions\s*"
            r"\?\s*state_->p1m2_tetra_octant_stage\.get\(\)\s*"
            r":\s*state_->p1m1_extra_stage\.get\(\)\)->record\(",
            runtime,
        )
        self.assertIsNotNone(dispatch)
        intervention = dispatch.start()
        tracing = runtime.index(
            "(direct_canonical ? state_->direct_ray_stage.get() : impl.ray_stage.get())")
        self.assertLess(start, intervention)
        self.assertLess(intervention, tracing)
        for phrase in (
            "state_->p1m1_extra_stage.reset()",
            "destroy_buffer(state_->p1m1_stats)",
            "request.p1m1_canonical_key_intervention ? 4U : 0U",
            "request.p1m1_canonical_key_intervention ? 22U",
            "trace.merged_sample_count != 12U",
            "n006_same_base_identity(base, item)",
            "data.weighted_owner_total != data.original_outputs",
        ):
            # Timestamp count line can wrap across two lines; special-case it.
            if phrase == "request.p1m1_canonical_key_intervention ? 22U":
                self.assertIn("request.p1m1_canonical_key_intervention) ? 22U", runtime)
            else:
                self.assertIn(phrase, runtime)
        self.assertIn("N006CanonicalM1Trace", header)
        self.assertIn("--p1m1-canonical-token", main)
        self.assertIn("3223322625U", main)
        self.assertIn("3223324678U", main)
        self.assertIn("3221225474U", main)
        self.assertIn('"canonical_m1"', main.replace('\\\"', '"'))
        self.assertIn("n006_p1m1_canonical_key_extra.spv", build)

    def test_m1_validates_immutable_eight_ray_prefix_plus_exact_tail(self):
        runtime = RUNTIME.read_text()
        self.assertIn(
            "const std::uint32_t expected_tail =\n"
            "            request.p1m1_canonical_key_intervention ? 4U : 0U;",
            runtime)
        self.assertIn(
            "result.stats.outputs * impl.settings.rays_per_probe +\n"
            "            expected_tail", runtime)
        self.assertIn(
            "extra.base_traced_rays ==\n"
            "                result.stats.outputs * impl.settings.rays_per_probe",
            runtime)
        self.assertIn("extra.extra_work_items == expected_tail", runtime)
        self.assertIn("unique.size() == result.stats.outputs", runtime)
        self.assertIn(
            "extra.base_prefix_correct && extra.extra_work_correct", runtime)
        self.assertIn(
            "if (!state_->last_canonical_frame || !impl.have_last ||", runtime)
        self.assertEqual(3008 * 8, 24064)
        self.assertEqual(3008 * 8 + 4, 24068)
        self.assertNotEqual(3008 * 8 + 4, 3008 * 8)

    def test_p1m1c_gpu_hit_vs_zero_radiance_is_fail_closed(self):
        runtime = RUNTIME.read_text()
        header = HEADER.read_text()
        main = CLI.read_text()
        runner = (
            ROOT / "scripts/research/n006_interval_aware_allocation"
            / "run_p1m1a_canonical_probe_pilot.py"
        ).read_text()
        audit_script = (
            ROOT / "scripts/research/n006_interval_aware_allocation"
            / "run_p1m1c_ray_fate.py"
        ).read_text()
        self.assertIn("std::vector<GpuHit> gpu_hits(total_work)", runtime)
        self.assertIn("impl.hits, gpu_hits.data()", runtime)
        self.assertIn("hit.metadata[3] > 1U", runtime)
        self.assertIn("!std::isfinite(hit.normal_t[3])", runtime)
        self.assertIn(
            "trace.extra_hit_count + trace.extra_miss_count != 4U", runtime)
        self.assertIn(
            "trace.extra_positive_radiance_rays +", runtime)
        self.assertIn(
            "trace.base_positive_radiance_rays > trace.base_hit_count", runtime)
        self.assertIn("count_ray_fate(index, c[1], false)", runtime)
        self.assertIn("count_ray_fate(index, c[1], true)", runtime)
        for key in (
            "base_hit_count", "extra_hit_count", "extra_miss_count",
            "base_positive_radiance_rays", "extra_positive_radiance_rays",
            "extra_hit_zero_radiance_rays",
        ):
            self.assertIn(key, header)
            self.assertIn("m1." + key, main)
            self.assertIn('"' + key + '"', runner)
        self.assertIn("trace[\"extra_radiance_sum16\"] != 0", runner)
        self.assertIn("require_ray_fate=True", audit_script)
        self.assertIn("n006-p1m1c-ray-fate-static-c3-v1", audit_script)
        self.assertIn("ray-fate-audit-complete", runner)

    def test_image_delta_detects_pixel_and_channels_without_signed_gain(self):
        zeros = struct.pack("<f", 0.0) * (320 * 180 * 3)
        changed = bytearray(zeros)
        struct.pack_into("<f", changed, 3 * 4, 0.125)
        info = m1.image_delta(zeros, bytes(changed))
        self.assertEqual(info["changed_rgb_pixels"], 1)
        self.assertEqual(info["changed_channel_values"], 1)
        self.assertEqual(info["max_abs_rgb_delta"], 0.125)
        self.assertEqual(m1.image_delta(zeros, zeros)["changed_rgb_pixels"], 0)

    def test_pfm_header_and_float_payload(self):
        with tempfile.TemporaryDirectory() as name:
            file = Path(name) / "test.pfm"
            pixels = struct.pack("<f", 0.0) * (320 * 180 * 3)
            file.write_bytes(b"PF\n320 180\n-1.0\n" + pixels)
            self.assertEqual(m1.read_pfm_payload(file), pixels)
            file.write_bytes(b"Pf\n320 180\n-1.0\n" + pixels)
            with self.assertRaises(ValueError):
                m1.read_pfm_payload(file)

    def test_selected_keys_are_frozen_m0_static_cascade_3_only(self):
        self.assertEqual(m1.CALIBRATION_C3,
                         {"zero": (3221225474, 0, 3),
                          "low_positive": (3223322625, 93, 3),
                          "high_positive": (3223324678, 875, 125)})
        self.assertEqual(m1.CASES,
                         ("control", "zero", "low_positive", "high_positive"))


if __name__ == "__main__":
    unittest.main()
