import copy
import unittest

from run_p1c_multiplicity import validate


def sample():
    evidence = {
        "protocol_version": "n006-p1-intervention-v1",
        "mode": "current", "scenario": "deforming-control",
        "device": {"name": "AMD Radeon 8060S Graphics (RADV STRIX_HALO)"},
        "source": {"internal_correctness": True},
        "frames": [{
            "internal_correctness": True,
            "extra": {"base_prefix_correct": True, "extra_work_correct": True,
                      "extra_rays_traced": 0},
            "hit_diagnostics": {"substantive_mismatches": 0},
            "stats": {"overflow": 0, "storage_failures": 0,
                      "work_items": 320, "visible_owners": 10, "outputs": 40},
        }],
    }
    counts = {
        "protocol_version": "n006-probe-multiplicity-v1",
        "base_work_items": 320, "visible_owners": 10,
        "cascade_count": 4, "rays_per_probe": 8,
        "cascades": [
            {"cascade": i, "owner_outputs": 10,
             "unique_probe_keys": 10 - i,
             "duplicated_ray_inputs": 8 * i,
             "same_probe_ray_inputs_identical": True}
            for i in range(4)],
    }
    return counts, evidence


class TestN006Multiplicity(unittest.TestCase):
    def test_valid(self):
        counts, evidence = sample()
        result = validate(counts, evidence)
        self.assertEqual(result["repeat_base_ray_inputs"], 48)
        self.assertAlmostEqual(result["repeat_fraction"], 48 / 320)

    def test_wrong_duplicate_count(self):
        counts, evidence = sample()
        counts["cascades"][2]["duplicated_ray_inputs"] = 7
        with self.assertRaisesRegex(ValueError, "repeated-ray"):
            validate(counts, evidence)

    def test_changed_ray_inputs(self):
        counts, evidence = sample()
        counts["cascades"][3]["same_probe_ray_inputs_identical"] = False
        with self.assertRaisesRegex(ValueError, "repeated-ray"):
            validate(counts, evidence)

    def test_wrong_base_work_count(self):
        counts, evidence = sample()
        counts["base_work_items"] = 319
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            validate(counts, evidence)


if __name__ == "__main__":
    unittest.main()
