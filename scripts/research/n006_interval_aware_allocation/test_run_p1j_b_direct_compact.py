from __future__ import annotations

import unittest
from pathlib import Path

from run_p1j_b_direct_compact import validate_direct_case
from run_p1j_lean_hash import (
    LEAN_HASH_SLOTS, LEAN_SCRATCH_BYTES,
)


def example():
    parity = {"status": "pass",
              "additional_scratch_bytes": LEAN_SCRATCH_BYTES,
              "byte_identical_pfm_sha256": "same"}
    raw = {"frames": [
        {"extra": {"canonical": {"executed": False}}},
        {"extra": {"canonical": {
            "executed": True,
            "copyback_executed": False,
            "hash_slots": LEAN_HASH_SLOTS,
            "scratch_bytes": LEAN_SCRATCH_BYTES,
            "collision_steps": 504,
        }}},
    ]}
    return parity, raw


class TestP1jBDirectCompact(unittest.TestCase):
    def test_accept_explicitly_zero_copy(self):
        parity, raw = example()
        result = validate_direct_case(parity, raw)
        self.assertTrue(result["direct_compact_work"])
        self.assertFalse(result["copyback_executed"])
        self.assertEqual(result["lean_scratch_bytes"], LEAN_SCRATCH_BYTES)
        self.assertEqual(result["hash_collision_steps"], 504)

    def test_copyback_candidate_rejected(self):
        parity, raw = example()
        raw["frames"][1]["extra"]["canonical"]["copyback_executed"] = True
        with self.assertRaisesRegex(ValueError, "copied back"):
            validate_direct_case(parity, raw)

    def test_missing_copyback_flag_rejected(self):
        parity, raw = example()
        del raw["frames"][1]["extra"]["canonical"]["copyback_executed"]
        with self.assertRaisesRegex(ValueError, "copied back"):
            validate_direct_case(parity, raw)

    def test_wrong_memory_not_waved(self):
        parity, raw = example()
        raw["frames"][1]["extra"]["canonical"]["scratch_bytes"] += 1024
        with self.assertRaisesRegex(ValueError, "slot/scratch"):
            validate_direct_case(parity, raw)

    def test_source_wiring_has_all_five_compact_work_consumers(self):
        root = Path(__file__).resolve().parents[3]
        source = (root / "src/research/n006_interval_aware_allocation"
                  / "n006_runtime.cpp").read_text(encoding="utf-8")
        for stage in (
            "direct_ray_stage", "direct_radiance_stage",
            "direct_storage_update_stage", "direct_resolve_stage",
            "direct_weight_stage",
        ):
            with self.subTest(stage=stage):
                self.assertIn(f"state_->" + stage, source)
        self.assertIn("if (!direct_canonical) {\n            state_->canonical_copy_stage",
                      source)
        self.assertIn("direct_canonical ? state_->canonical_work : impl.work",
                      source)

    def test_constructor_flag_requires_lean_hash(self):
        root = Path(__file__).resolve().parents[3]
        source = (root / "src/research/n006_interval_aware_allocation"
                  / "n006_runtime.cpp").read_text(encoding="utf-8")
        self.assertIn(
            "if (p1j_direct_compact && !p1j_lean_hash)", source)


if __name__ == "__main__":
    unittest.main()
