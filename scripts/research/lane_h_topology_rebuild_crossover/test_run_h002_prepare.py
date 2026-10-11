from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
PATH = SCRIPT_DIR / "run_h002_prepare.py"
spec = importlib.util.spec_from_file_location("run_h002_prepare", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class H002PrepareTests(unittest.TestCase):
    def config(self) -> dict[str, object]:
        return {
            "plan_version": "test",
            "base_primitive_count": 100,
            "primitive_count_factors": [1.0, 1.25, 0.75],
            "topology_seed": 0x48303032,
            "replacement_fraction": 0.25,
            "producer_contract": "A001",
            "hit_contract": "exact-hit",
            "storage_contract": "C001",
            "changed_object_id": "topology-object-0",
            "immutable_owner_ids": ["static-world", "unrelated-object-0"],
            "candidate_set": ["candidate", "control"],
            "required_boundary_fields": [
                "upload_us", "build_us", "true_peak_resident_bytes"
            ],
        }

    def test_manifest_is_deterministic(self) -> None:
        first = mod.build_manifest(self.config())
        second = mod.build_manifest(self.config())
        self.assertEqual(first, second)
        self.assertEqual(
            [step["primitive_count"] for step in first["steps"]],
            [100, 125, 75],
        )

    def test_manifest_rejects_frozen_digest_drift(self) -> None:
        cfg = self.config()
        cfg["expected_workload_digest"] = "not-the-real-digest"
        with self.assertRaises(ValueError):
            mod.build_manifest(cfg)

    def test_evidence_gate_accepts_complete_local_record(self) -> None:
        manifest = mod.build_manifest(self.config())
        record = {
            "workload_digest": manifest["workload_digest"],
            "producer_contract": "A001",
            "hit_contract": "exact-hit",
            "storage_contract": "C001",
            "upload_us": 1.0,
            "build_us": 2.0,
            "true_peak_resident_bytes": 30,
            "correctness": {
                "passed": True,
                "visibility_mismatches": 0,
                "producer_semantic_errors": 0,
                "hit_mismatches": 0,
                "traversal_runtime_errors": 0,
                "storage_failures": 0,
            },
            "mutation_events": [
                {"owner_id": "static-world", "operation": "read"},
                {"owner_id": "topology-object-0", "operation": "rebuild"},
            ],
            "allocations": [
                {
                    "name": "old",
                    "owner_id": "topology-object-0",
                    "bytes": 10,
                    "birth_phase": 0,
                    "death_phase": 3,
                },
                {
                    "name": "new",
                    "owner_id": "topology-object-0",
                    "bytes": 20,
                    "birth_phase": 2,
                    "death_phase": 5,
                },
            ],
        }
        mod.validate_evidence_record(record, manifest=manifest)

    def test_evidence_gate_rejects_workload_drift(self) -> None:
        manifest = mod.build_manifest(self.config())
        record = {
            "workload_digest": "wrong",
            "producer_contract": "A001",
            "hit_contract": "exact-hit",
            "storage_contract": "C001",
            "upload_us": 1.0,
            "build_us": 2.0,
            "true_peak_resident_bytes": 0,
            "correctness": {
                "passed": True,
                "visibility_mismatches": 0,
                "producer_semantic_errors": 0,
                "hit_mismatches": 0,
                "traversal_runtime_errors": 0,
                "storage_failures": 0,
            },
            "mutation_events": [],
            "allocations": [],
        }
        with self.assertRaises(ValueError):
            mod.validate_evidence_record(record, manifest=manifest)


if __name__ == "__main__":
    unittest.main()
