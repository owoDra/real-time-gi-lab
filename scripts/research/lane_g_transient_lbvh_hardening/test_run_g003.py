from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATH = Path(__file__).with_name("run_g003.py")
spec = importlib.util.spec_from_file_location("run_g003", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

BASELINE = (
    ROOT / "src/research/lane_g_transient_lbvh_hardening"
    / "baseline/lane_b_traversal"
)
IMMUTABLE_CPP = (
    ROOT / "src/research/lane_g_transient_lbvh_hardening"
    / "g003_immutable_hwrt.cpp"
)
RUNTIME_CPP = (
    ROOT / "src/research/lane_g_transient_lbvh_hardening"
    / "i001_runtime.cpp"
)


def git_blob_sha(path: Path) -> str:
    payload = path.read_bytes()
    header = f"blob {len(payload)}\0".encode()
    return hashlib.sha1(header + payload).hexdigest()


class G003RunnerTests(unittest.TestCase):
    def test_frozen_variants(self) -> None:
        self.assertEqual(
            mod.VARIANTS,
            ("transient-lbvh", "hardened-transient-lbvh", "vanilla-software"),
        )

    def test_release_set_is_only_g001_setup_only_hwrt(self) -> None:
        self.assertEqual(
            mod.RELEASED_NAMES,
            {
                "static-hwrt.vertices",
                "static-hwrt.instance",
                "static-hwrt.scratch",
            },
        )

    def test_g001_sparse_anchors_are_frozen(self) -> None:
        self.assertEqual(
            mod.G001_SPARSE_ANCHORS["sparse-stress"],
            {
                "baseline_peak_bytes": 119_078_592,
                "vanilla_peak_bytes": 38_616_288,
                "released_setup_only_bytes": 46_202_400,
                "expected_hardened_runtime_resident_bytes": 72_876_192,
                "expected_hardened_setup_peak_bytes": 104_595_424,
                "expected_hardened_peak_bytes": 104_595_424,
            },
        )
        self.assertEqual(
            mod.G001_SPARSE_ANCHORS["sparse-moving"],
            {
                "baseline_peak_bytes": 123_668_160,
                "vanilla_peak_bytes": 38_616_288,
                "released_setup_only_bytes": 46_017_696,
                "expected_hardened_runtime_resident_bytes": 77_650_464,
                "expected_hardened_setup_peak_bytes": 104_233_440,
                "expected_hardened_peak_bytes": 104_233_440,
            },
        )

    def test_f007_hwrt_baseline_snapshot_is_byte_exact(self) -> None:
        self.assertEqual(
            git_blob_sha(BASELINE / "b002_hwrt.hpp"),
            "8177fd7e1cec09df8674b8e47e8d5e5f4e2d0d5a",
        )
        self.assertEqual(
            git_blob_sha(BASELINE / "b002_hwrt.cpp"),
            "8bec912c01579fe8515ad0a90aec7a22966e3c90",
        )

    def test_immutable_owner_has_no_update_path(self) -> None:
        source = IMMUTABLE_CPP.read_text(encoding="utf-8")
        self.assertNotIn("update_geometry(", source)
        self.assertIn("setup_stats_.tlas_build_us = build_tlas();", source)
        self.assertIn("context_.destroy_buffer(scratch_);", source)
        self.assertIn("context_.destroy_buffer(instance_buffer_);", source)
        self.assertIn("context_.destroy_buffer(vertex_buffer_);", source)

    def test_hardened_variant_only_opts_into_lane_owned_owner(self) -> None:
        source = RUNTIME_CPP.read_text(encoding="utf-8")
        self.assertIn(
            "if (uses_hardened_transient_lbvh(options.variant))",
            source,
        )
        self.assertIn(
            "std::make_unique<lane_g::G003ImmutableHwrtTraversal>",
            source,
        )
        self.assertNotIn("HwrtBuildInputRetention", source)

    def test_immutable_setup_precedes_shared_allocations(self) -> None:
        source = RUNTIME_CPP.read_text(encoding="utf-8")
        early = source.index(
            "if (uses_hardened_transient_lbvh(options.variant))"
        )
        shared = source.index("surfaces = context.upload_device_buffer(")
        self.assertLess(early, shared)
        self.assertIn(
            "peak_resident_bytes =\n            std::max(",
            source,
        )

    def test_g003_does_not_require_power_state_manipulation(self) -> None:
        runner = PATH.with_name("run_g003.py").read_text(encoding="utf-8")
        self.assertNotIn("profile_peak", runner)
        self.assertNotIn("power_dpm_force_performance_level", runner)


if __name__ == "__main__":
    unittest.main()
