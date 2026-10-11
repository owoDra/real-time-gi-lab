"""P1m0 exact-source pretrace coverage diagnostic static contracts.

No GPU execution or input PFM oracle in this test module.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
SHADER = ROOT / "shaders/research/n006_interval_aware_allocation/n006_p1m0_consumer_coverage.comp.glsl"
COMPOSITE = ROOT / "shaders/research/lane_n_end_to_end_renderer/n001_composite.comp.glsl"
CANONICAL = ROOT / "shaders/research/n006_interval_aware_allocation/n006_canonical_index.comp.glsl"
CMAKE = ROOT / "src/research/lane_n_end_to_end_renderer/CMakeLists.txt"

class TestP1m0CoverageStaticContracts(unittest.TestCase):
    def test_source_pixel_to_key_arithmetic_exactly_mirrors_composite(self):
        import re
        def compact(value: str) -> str:
            return re.sub(r"\s+", "", value)
        diagnostic = compact(SHADER.read_text())
        for relative in (
            "shaders/research/lane_n_end_to_end_renderer/n001_composite.comp.glsl",
            "shaders/research/lane_n_end_to_end_renderer/n003_composite_software.comp.glsl",
        ):
            composite = compact((ROOT / relative).read_text())
            steps = [
                "float nx = (2.0 * (float(pixel.x) + 0.5) / float(p.counts.y)) - 1.0;",
                "float ny = 1.0 - (2.0 * (float(pixel.y) + 0.5) / float(p.counts.z));",
                "vec3 view_direction = normalize(p.camera_forward_far.xyz + p.camera_right_tan_x.xyz * (nx * p.camera_right_tan_x.w) + p.camera_up_tan_y.xyz * (ny * p.camera_up_tan_y.w));",
                "vec3 position = p.camera_pos_near.xyz + view_direction * hit.normal_t.w;",
                "float spacing = p.scene_origin_spacing.w * float(1u << cascade);",
                "ivec3 probe = ivec3(floor((position - p.scene_origin_spacing.xyz) / spacing));",
            ]
            for expr in steps:
                with self.subTest(shader=relative, expression=expr):
                    self.assertIn(compact(expr), composite)
                    self.assertIn(compact(expr), diagnostic)
            self.assertIn(compact(
                "hit.metadata.w != 1u || isnan(hit.normal_t.w) || isinf(hit.normal_t.w)"),
                diagnostic)

    def test_diagnostic_checks_postframe_byte_equality(self):
        runtime = (ROOT / "src/research/n006_interval_aware_allocation"
                   / "n006_runtime.cpp").read_text()
        self.assertIn("hits_before != hits_after || image_before != image_after", runtime)
        self.assertIn("state_->last_canonical_frame", runtime)
        cli = (ROOT / "src/research/n006_interval_aware_allocation"
               / "n006_intervention_main.cpp").read_text()
        self.assertIn('--p1m0-consumer-coverage', cli)
        self.assertIn('runtime.p1m0_consumer_coverage()', cli)
        # The legacy software-variant/lean-hash/target-warmup gates have
        # three independent discriminators; M0 is narrowly opted in.
        self.assertGreaterEqual(cli.count("!p1m0_coverage"), 2)
        # The third gate is a positive allowlist, rather than a negation.
        self.assertIn("!three_arm_pattern.empty() || p1l_stage_any ||", cli)
        self.assertIn("p1m0_coverage))", cli)
        self.assertIn("p1l_stage_any || p1m0_coverage", cli)

    def test_warmup_gates_allow_five_p1m0_scenarios_without_relaxing_legacy(self):
        cli = (ROOT / "src/research/n006_interval_aware_allocation"
               / "n006_intervention_main.cpp").read_text()
        # Regression: previous P1h-only count contract demanded precisely 4172
        # owners, rejecting the accepted STATIC scenario (4167 owners).
        self.assertIn(
            "const bool scenario_counted_target = p1l_stage_any || p1m0_coverage;",
            cli)
        self.assertIn("const bool expected_counts = scenario_counted_target", cli)
        self.assertIn("(scenario_counted_target\n", cli)
        self.assertIn("stats.outputs == first_target_warmup_outputs", cli)
        # The historical P1h hardcoded deforming-control check stays intact
        # for its original protocol: only P1m0/P1l opt in to dynamic counts.
        self.assertIn("stats.visible_owners == 4172U", cli)
        self.assertIn("last_target_warmup_owners != 4172U", cli)
        self.assertIn("source_warmup_frames != 32U", cli)
        self.assertIn("target_state_warmup_frames != 8U", cli)

    def test_m0_performs_n004_oracle_once_not_eight_warmups(self):
        cli = (ROOT / "src/research/n006_interval_aware_allocation"
               / "n006_intervention_main.cpp").read_text()
        self.assertIn(
            "p1l_stage_fast || p1l_b0_counts || p1l_b1 || p1l_b1b_counts ||",
            cli)
        self.assertIn("p1m0_coverage;\n", cli)
        self.assertIn("const auto warm_hits = p1l_sampled_hit", cli)
        self.assertIn("? frame_core_correct(warm_frame)", cli)
        self.assertIn("p1l_b1 ? index == 1U : (!p1l_sampled_hit || index == 0U)", cli)
        self.assertIn("runtime.n004_hit_diagnostics()", cli)
        self.assertIn('trace_p1m0("target N004 sampled hit oracle begin")', cli)
        self.assertIn('trace_p1m0("target N004 sampled hit oracle complete")', cli)
        runtime = (ROOT / "src/research/n006_interval_aware_allocation"
                   / "n006_runtime.cpp").read_text()
        for mark in ("pre-diagnostic primary/image readback begin",
                     "compute pipeline constructed",
                     "diagnostic GPU fence wait begin",
                     "diagnostic GPU fence signaled",
                     "consumer count invariants verified"):
            self.assertIn(mark, runtime)

    def test_post_failure_log_diagnostic_is_discoverable(self):
        runner = (ROOT / "scripts/research/n006_interval_aware_allocation"
                  / "run_p1m0_consumer_coverage.py").read_text()
        self.assertIn("evidence root: {dest.resolve()}", runner)
        self.assertIn("stderr={folder.resolve() / 'stderr.log'}", runner)
        self.assertIn("Stream both child logs directly to durable files", runner)
        self.assertIn("last stage / stderr:", runner)
        self.assertIn("stderr tail:", runner)
        self.assertIn("timeout=TIMEOUT_SECONDS", runner)
        self.assertIn("p1m0_coverage;", (ROOT / "src/research/n006_interval_aware_allocation" / "n006_intervention_main.cpp").read_text())
        self.assertIn("failure report: {summary_file.resolve()}", runner)

    def test_pretrace_runs_after_primary_and_hash_before_secondary(self):
        runtime = (ROOT / "src/research/n006_interval_aware_allocation"
                   / "n006_runtime.cpp").read_text()
        header = (ROOT / "src/research/n006_interval_aware_allocation"
                  / "n006_runtime.hpp").read_text()
        cli = (ROOT / "src/research/n006_interval_aware_allocation"
               / "n006_intervention_main.cpp").read_text()
        self.assertIn("bool p1m0_pretrace_coverage{}", header)
        self.assertIn("--p1m0-pretrace-coverage", cli)
        self.assertIn("p1m0_pretrace_coverage && index == 0U", cli)
        self.assertIn("p1m0_pretrace_coverage && !p1m0_coverage", cli)
        self.assertIn("pretrace_slot_byte_equal", cli)
        self.assertIn("pretrace_stats_byte_equal", cli)
        self.assertIn("pretrace_clear_and_count_gpu_us", cli)
        self.assertIn("pretrace_scratch_bytes", cli)
        canonical = runtime.index("state_->canonical_compact_stage->record_indirect(")
        pretrace = runtime.index("state_->p1m0_pretrace_stage->record(")
        secondary = runtime.index(
            "(direct_canonical ? state_->direct_ray_stage.get() : impl.ray_stage.get())")
        self.assertLess(canonical, pretrace)
        self.assertLess(pretrace, secondary)
        self.assertIn("stamp(20);", runtime)
        self.assertIn("stamp(21);", runtime)
        self.assertIn("request.p1m0_pretrace_coverage ? 22U", runtime)
        self.assertIn("pretrace_counts == raw_counts", runtime)
        self.assertIn("pretrace_stats == raw_stats", runtime)
        self.assertIn("state_->p1m0_pretrace_counts.size, 0U", runtime)
        self.assertIn("state_->p1m0_pretrace_stats.size, 0U", runtime)
        self.assertIn("i001_transfer_to_compute_barrier(impl.context, command);", runtime)
        self.assertIn("last_p1m0_pretrace_frame = false", runtime)
        self.assertIn("p1m0_pretrace_stage.reset()", runtime)

    def test_diagnostic_uses_existing_key_packing_and_bounded_slots(self):
        diagnostic = SHADER.read_text()
        canonical = CANONICAL.read_text()
        for key in ("0x7feb352du", "0x846ca68bu", "0xfffffffeu",
                    "0xffffffffu"):
            self.assertIn(key, diagnostic)
            self.assertIn(key, canonical)
        for invariant in (
            "pc.max_probe > pc.hash_capacity",
            "pc.consumer_capacity < pc.hash_capacity",
            "atomicAdd(consumers.values[slot], 1u)",
            "if (key == 0u)",
            "if (key == token)",
            "atomicAdd(stats.data[5], 1u)",
            "atomicAdd(stats.data[6], 1u)",
            "atomicAdd(stats.data[7], 1u)",
        ):
            self.assertIn(invariant, diagnostic)
        # No output storage, original GI ray/work buffer or input mutations.
        self.assertNotIn("writeonly buffer Image", diagnostic)
        self.assertNotIn("buffer WorkItem", diagnostic)
        self.assertIn("readonly buffer PrimaryHits", diagnostic)
        self.assertIn("readonly buffer KeyTokens", diagnostic)

    def test_new_target_is_n006_only(self):
        self.assertIn("n006_p1m0_consumer_coverage", CMAKE.read_text())
        self.assertTrue(SHADER.is_file())

if __name__ == "__main__":
    unittest.main()
