from __future__ import annotations

import copy
import unittest

from run_p0_smoke import validate_evidence

GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"


def valid_evidence() -> dict:
    return {
        "protocol_version": "n005-p2-candidate-evidence-v1",
        "mode": "current",
        "scenario": "static",
        "device": {"name": GPU, "driver_name": "RADV"},
        "source": {"internal_correctness": True},
        "frames": [{
            "internal_correctness": True,
            "owner_budget": 0,
            "extra": {"extra_rays_traced": 0},
            "stats": {
                "overflow": 0,
                "storage_failures": 0,
                "visible_owners": 40,
                "work_items": 1280,
            },
            "hit_diagnostics": {"substantive_mismatches": 0},
            "timing_us": {"complete_gi_gpu": 1200.0},
        }],
    }


class TestP0Smoke(unittest.TestCase):
    def test_valid_current_smoke(self) -> None:
        summary = validate_evidence(valid_evidence(), GPU)
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["extra_rays"], 0)
        self.assertEqual(summary["visible_owners"], 40)

    def test_wrong_gpu_fails(self) -> None:
        data = valid_evidence()
        data["device"]["name"] = "different GPU"
        with self.assertRaisesRegex(RuntimeError, "wrong GPU"):
            validate_evidence(data, GPU)

    def test_storage_failure_fails(self) -> None:
        data = valid_evidence()
        data["frames"][0]["stats"]["storage_failures"] = 1
        with self.assertRaisesRegex(RuntimeError, "overflow/storage"):
            validate_evidence(data, GPU)

    def test_failed_frame_fails(self) -> None:
        data = valid_evidence()
        data["frames"][0]["internal_correctness"] = False
        with self.assertRaisesRegex(RuntimeError, "frame correctness"):
            validate_evidence(data, GPU)

    def test_unexpected_extra_rays_fails(self) -> None:
        data = valid_evidence()
        data["frames"][0]["extra"]["extra_rays_traced"] = 4
        with self.assertRaisesRegex(RuntimeError, "extra rays"):
            validate_evidence(data, GPU)

    def test_unexpected_schema_fails(self) -> None:
        data = valid_evidence()
        data["protocol_version"] = "unexpected"
        with self.assertRaisesRegex(RuntimeError, "schema"):
            validate_evidence(data, GPU)


if __name__ == "__main__":
    unittest.main()
