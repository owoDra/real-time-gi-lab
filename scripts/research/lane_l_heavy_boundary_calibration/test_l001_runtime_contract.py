from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = (
    ROOT
    / "src/research/lane_l_heavy_boundary_calibration/l001_formal_process.cpp"
)


class L001RuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_reuses_j004_runtime_source_directly(self) -> None:
        self.assertIn(
            '#include "../lane_j_topology_backend_alternatives/formal_runtime/'
            'j004_formal_process.cpp"',
            self.source,
        )

    def test_only_required_measurement_environments_exist(self) -> None:
        self.assertIn('"dual-context"', self.source)
        self.assertIn('"single-context-independent-runtime"', self.source)
        self.assertNotIn("single-runtime repeated-baseline", self.source)

    def test_single_context_keeps_two_independent_runtimes(self) -> None:
        marker = "B002VulkanContext context("
        self.assertIn(marker, self.source)
        self.assertIn(
            "FormalRuntime runtime_a(context, options, kind);",
            self.source,
        )
        self.assertIn(
            "FormalRuntime runtime_b(context, options, kind);",
            self.source,
        )

    def test_timing_is_control_control_only(self) -> None:
        self.assertIn(
            'if (options.comparison != "control")',
            self.source,
        )
        self.assertIn(
            'fail("L001 timing permits same-variant control only")',
            self.source,
        )

    def test_validation_requires_resolved_identity_and_lifetime(self) -> None:
        self.assertIn(
            "a.resolved_digest == b.resolved_digest",
            self.source,
        )
        self.assertIn(
            "allocation_lifetime_consistent",
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
