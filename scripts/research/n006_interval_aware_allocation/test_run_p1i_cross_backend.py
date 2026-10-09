from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from run_p1i_cross_backend import MATRIX, SCENARIOS, VARIANTS, validate


def fixture(variant: str = "lane-e-final-hwrt",
            scenario: str = "static") -> dict:
    owners = 100
    original_outputs = owners * 4
    keys = [80, 50, 30, 20]
    unique = sum(keys)
    def frame(index: int, canonical: bool) -> dict:
        outputs = unique if canonical else original_outputs
        return {
            "index": index, "motion_fraction": 1, "owner_budget": 0,
            "internal_correctness": True,
            "image": f"frames/candidate-{index:03d}.pfm",
            "hit_diagnostics": {"substantive_mismatches": 0},
            "stats": {
                "visible_owners": owners, "work_items": outputs * 8,
                "outputs": outputs, "storage_updates": outputs,
                "overflow": 0, "storage_failures": 0,
            },
            "timing_us": {"complete_gi_gpu": 1200.0 - 200*index},
            "extra": {
                "base_prefix_correct": True, "extra_work_correct": True,
                "extra_rays_traced": 0,
                "gpu_hash_probe": {"executed": False},
                "canonical": (
                    {"executed": True,
                     "original_work_items": original_outputs*8,
                     "original_outputs": original_outputs,
                     "canonical_work_items": unique*8,
                     "canonical_outputs": unique, "duplicates": original_outputs-unique,
                     "unique_by_cascade": list(keys),
                     "invalid_keys": 0, "failed_inserts": 0,
                     "index_overflows": 0, "owner_weight_errors": 0,
                     "weighted_owner_total": original_outputs,
                     "scratch_bytes": 8421464,
                     "total_canonical_gpu_us": 50.0,
                     "owner_weight_storage_gpu_us": 5.0}
                    if canonical else {"executed": False}
                ),
            },
        }
    return {
        "protocol_version": "n006-p1-intervention-v1",
        "variant": variant, "scenario": scenario, "mode": "current",
        "reference_generation": "skipped", "source_warmup_frames": 32,
        "device": {"name": "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"},
        "source": {"internal_correctness": True},
        "frames": [frame(0, False), frame(1, True)],
    }


class TestN006P1iMatrix(unittest.TestCase):
    GPU = "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"

    def _audit(self, raw):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "frames").mkdir()
            for idx in range(2):
                (dest / f"frames/candidate-{idx:03d}.pfm").write_bytes(b"same HDR bytes")
            return validate(raw, dest, self.GPU,
                            raw["variant"], raw["scenario"])

    def test_frozen_matrix(self):
        self.assertEqual(len(MATRIX), 10)
        self.assertEqual(VARIANTS, ("lane-e-final-hwrt", "lane-e-final-software"))
        self.assertEqual(SCENARIOS,
                         ("static", "camera-motion", "light-motion",
                          "moving-rigid", "deforming-control"))

    def test_all_scenarios_all_backends_accept_variable_cardinality(self):
        for variant, scenario in MATRIX:
            with self.subTest(variant=variant, scenario=scenario):
                out = self._audit(fixture(variant, scenario))
                self.assertEqual(out["canonical_ray_work_items"], 180 * 8)
                self.assertEqual(out["baseline_ray_work_items"], 100 * 4 * 8)
                self.assertEqual(out["duplicate_owner_outputs"], 220)

    def test_reject_wrong_owner_weight(self):
        raw = fixture()
        raw["frames"][1]["extra"]["canonical"]["weighted_owner_total"] -= 1
        with self.assertRaisesRegex(ValueError, "canonical GPU"):
            self._audit(raw)

    def test_reject_still_full_ray_count(self):
        raw = fixture()
        raw["frames"][1]["stats"]["work_items"] = 3200
        with self.assertRaisesRegex(ValueError, "canonical GPU"):
            self._audit(raw)

    def test_reject_wrong_variant_identity(self):
        raw = fixture()
        raw["variant"] = "unexpected-variant"
        with self.assertRaisesRegex(ValueError, "matrix"):
            self._audit(raw)

    def test_reject_probe_overflow(self):
        raw = fixture()
        raw["frames"][1]["extra"]["canonical"]["index_overflows"] = 1
        with self.assertRaisesRegex(ValueError, "canonical GPU"):
            self._audit(raw)

    def test_reject_image_mismatch_without_discarding(self):
        raw = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            (dest / "frames").mkdir()
            (dest / "frames/candidate-000.pfm").write_bytes(b"A")
            (dest / "frames/candidate-001.pfm").write_bytes(b"B")
            with self.assertRaisesRegex(ValueError, "PFM mismatch"):
                validate(raw, dest, self.GPU, raw["variant"], raw["scenario"])

    def test_reject_inconsistent_owner_count(self):
        raw = fixture()
        raw["frames"][1]["stats"]["visible_owners"] += 1
        with self.assertRaisesRegex(ValueError, "visible-owner"):
            self._audit(raw)


if __name__ == "__main__":
    unittest.main()
