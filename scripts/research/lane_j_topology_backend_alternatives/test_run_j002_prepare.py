from __future__ import annotations

import copy
import unittest

import run_j002_prepare as prepare


class J002PrepareTests(unittest.TestCase):
    def config(self) -> dict[str, object]:
        return {
            "plan_version": "test",
            "master_topology_seed": 0x4A303032,
            "primitive_count_factors": [1.0, 1.25, 0.75],
            "producer_contract": "A001",
            "producer_source": {
                "case": "static",
                "frame_id": 0,
                "accepted_git_commit": "test-commit",
                "artifact_glob": "out/test/**/stream-v1.bin",
            },
            "hit_contract": "B001",
            "storage_contract": "C001",
            "changed_object_id": "topology-object-0",
            "immutable_owner_ids": [
                "static-world",
                "unrelated-object-0",
            ],
            "profiles": [{
                "name": "medium",
                "base_primitive_count": 100,
                "replacement_fraction": 0.25,
                "locality": "global",
            }],
            "candidate_set": ["candidate"],
            "required_boundary_fields": [
                "upload_us",
                "true_peak_resident_bytes",
            ],
            "required_correctness_zero_fields": [
                "hit_mismatch_count",
                "immutable_owner_mutation_count",
            ],
        }

    def test_manifest_is_deterministic(self) -> None:
        first = prepare.build_manifest(self.config())
        second = prepare.build_manifest(self.config())
        self.assertEqual(first, second)
        self.assertFalse(first["producer_stream_ready"])
        self.assertEqual(first["producer_source"], self.config()["producer_source"])
        self.assertEqual(
            [
                step["primitive_count"]
                for step in first["profiles"][0]["steps"]
            ],
            [100, 125, 75],
        )

    def test_expected_digest_detects_drift(self) -> None:
        cfg = self.config()
        cfg["profiles"][0]["expected_topology_digest"] = "wrong"
        with self.assertRaises(ValueError):
            prepare.build_manifest(cfg)

    def test_candidate_record_gate(self) -> None:
        manifest = prepare.build_manifest(self.config())
        profile = manifest["profiles"][0]
        record = {
            "manifest_digest": manifest["manifest_digest"],
            "producer_contract": "A001",
            "hit_contract": "B001",
            "storage_contract": "C001",
            "profile": "medium",
            "topology_digest": profile["topology_digest"],
            "snapshots": [
                {
                    "primitive_count": 100,
                    "snapshot_digest": "a",
                },
                {
                    "primitive_count": 125,
                    "snapshot_digest": "b",
                },
                {
                    "primitive_count": 75,
                    "snapshot_digest": "c",
                },
            ],
            "upload_us": 0.0,
            "true_peak_resident_bytes": 30,
            "correctness": {
                "passed": True,
                "hit_mismatch_count": 0,
                "immutable_owner_mutation_count": 0,
            },
            "mutation_events": [{
                "owner_id": "topology-object-0",
                "operation": "rebuild",
            }],
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
        prepare.validate_candidate_record(
            record,
            manifest,
        )

        stale = copy.deepcopy(record)
        stale["snapshots"][1]["snapshot_digest"] = "a"
        with self.assertRaises(ValueError):
            prepare.validate_candidate_record(
                stale,
                manifest,
            )


if __name__ == "__main__":
    unittest.main()
