from __future__ import annotations

import unittest
import subprocess
from run_p1_pilot import BINARY

from run_p1_pilot import check_evidence, deterministic_tiles

GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"


def evidence(mode: str, rays: int, selected: int) -> dict:
    return {
        "protocol_version": "n006-p1-intervention-v1",
        "mode": mode,
        "scenario": "deforming-control",
        "device": {"name": GPU},
        "source": {"internal_correctness": True},
        "frames": [{
            "internal_correctness": True,
            "extra": {
                "base_prefix_correct": True,
                "extra_work_correct": True,
                "extra_rays_traced": rays,
                "selected_owner_count": selected,
            },
            "hit_diagnostics": {"substantive_mismatches": 0},
            "stats": {"overflow": 0, "storage_failures": 0},
        }],
    }


class TestN006Pilot(unittest.TestCase):
    def test_deterministic_spatial_quantiles(self) -> None:
        self.assertEqual(deterministic_tiles([100, 0, 30, 90], 2), [30, 100])

    def test_invalid_tiles(self) -> None:
        with self.assertRaises(ValueError):
            deterministic_tiles([1, 1, 2], 2)
        with self.assertRaises(ValueError):
            deterministic_tiles([1], 2)

    def test_current(self) -> None:
        self.assertTrue(check_evidence(evidence("current", 0, 0), "current", 0, GPU))

    def test_targeted(self) -> None:
        data = evidence("targeted-extra-rays", 4, 1)
        self.assertTrue(check_evidence(data, "targeted-extra-rays", 4, GPU))

    def test_compiled_cli_accepts_tile_and_cascade_flags(self) -> None:
        # Runs before any GPU initialization. The original regression returned
        # exit 2 + usage because these two flags were not parsed.
        if not BINARY.is_file():
            self.fail("build phos-n006-intervention before running unit tests")
        result = subprocess.run(
            [str(BINARY), "--selected-tile-id", "22890",
             "--selected-cascade", "2"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("invalid N006 candidate arguments", result.stderr)

    def test_targeted_missing_rays_fails(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "extra work"):
            check_evidence(evidence("targeted-extra-rays", 0, 0), "targeted-extra-rays", 4, GPU)

    def test_traversal_mismatch_fails(self) -> None:
        data = evidence("targeted-extra-rays", 4, 1)
        data["frames"][0]["hit_diagnostics"]["substantive_mismatches"] = 1
        with self.assertRaisesRegex(RuntimeError, "correctness"):
            check_evidence(data, "targeted-extra-rays", 4, GPU)

    def test_reference_protocol_mismatch_fails(self) -> None:
        data = evidence("current", 0, 0)
        data["protocol_version"] = "n005-p2-candidate-evidence-v1"
        with self.assertRaisesRegex(RuntimeError, "protocol"):
            check_evidence(data, "current", 0, GPU)


if __name__ == "__main__":
    unittest.main()
