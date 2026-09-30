from __future__ import annotations

import math
import unittest

import j002_contract as contract


class J002ContractTests(unittest.TestCase):
    def test_profile_seeds_are_deterministic_and_distinct(self) -> None:
        seeds = [
            contract.profile_seed(0x4A303032, index)
            for index in range(5)
        ]
        self.assertEqual(
            seeds,
            [
                contract.profile_seed(0x4A303032, index)
                for index in range(5)
            ],
        )
        self.assertEqual(len(set(seeds)), 5)

    def test_topology_sequence_changes_count_and_replaces(self) -> None:
        steps = contract.topology_sequence(
            796,
            [1.0, 1.25, 0.75, 1.1, 0.9],
            123,
            0.25,
            "global",
        )
        self.assertTrue(all(
            left.primitive_count != right.primitive_count
            for left, right in zip(steps, steps[1:], strict=False)
        ))
        self.assertTrue(all(
            step.replacement_count > 0
            for step in steps[1:]
        ))
        self.assertEqual(
            contract.topology_digest("x", steps),
            contract.topology_digest("x", steps),
        )

    def test_transition_identity_rejects_stale_transition(self) -> None:
        contract.validate_transition_identity([
            {"primitive_count": 10, "snapshot_digest": "a"},
            {"primitive_count": 12, "snapshot_digest": "b"},
        ])
        with self.assertRaises(ValueError):
            contract.validate_transition_identity([
                {"primitive_count": 10, "snapshot_digest": "a"},
                {"primitive_count": 10, "snapshot_digest": "b"},
            ])
        with self.assertRaises(ValueError):
            contract.validate_transition_identity([
                {"primitive_count": 10, "snapshot_digest": "a"},
                {"primitive_count": 12, "snapshot_digest": "a"},
            ])

    def test_object_local_mutation_gate(self) -> None:
        contract.validate_object_local_mutations(
            [
                contract.MutationEvent("static-world", "read"),
                contract.MutationEvent(
                    "topology-object-0",
                    "rebuild",
                ),
            ],
            changed_object_id="topology-object-0",
            immutable_owner_ids=["static-world"],
        )
        with self.assertRaises(ValueError):
            contract.validate_object_local_mutations(
                [
                    contract.MutationEvent(
                        "static-world",
                        "release",
                    ),
                ],
                changed_object_id="topology-object-0",
                immutable_owner_ids=["static-world"],
            )

    def test_boundary_requires_explicit_finite_values(self) -> None:
        contract.validate_boundary_record(
            {"a": 0.0, "b": 2.0},
            ["a", "b"],
        )
        with self.assertRaises(ValueError):
            contract.validate_boundary_record(
                {"a": 0.0},
                ["a", "b"],
            )
        with self.assertRaises(ValueError):
            contract.validate_boundary_record(
                {"a": math.inf},
                ["a"],
            )

    def test_true_peak_counts_reallocation_overlap(self) -> None:
        allocations = [
            contract.AllocationLifetime(
                "old",
                "topology-object-0",
                100,
                0,
                3,
            ),
            contract.AllocationLifetime(
                "new",
                "topology-object-0",
                160,
                2,
                5,
            ),
            contract.AllocationLifetime(
                "scratch",
                "topology-object-0",
                40,
                1,
                4,
                "scratch",
            ),
        ]
        self.assertEqual(
            contract.true_peak_resident_bytes(allocations),
            300,
        )
        self.assertEqual(
            contract.allocation_class_bytes(allocations)["scratch"],
            40,
        )

    def test_lane_a_stream_validates_exact_workload_id(self) -> None:
        item = contract.A001_ITEM.pack(
            0, 0, 0,
            0, 0, 0, 0, 0,
            0.1, 10.0,
            0.0, 0.0, 1.0,
            0.0, 0.0, 0.0,
        )
        workload = contract.lane_a_workload_id(item)
        header = contract.A001_HEADER.pack(
            contract.A001_MAGIC,
            1,
            64,
            64,
            0,
            1,
            1,
            1,
            1,
            1,
            1,
            0,
            workload,
        )
        parsed = contract.parse_lane_a_stream(header + item)
        self.assertEqual(parsed["item_count"], 1)
        with self.assertRaises(ValueError):
            contract.parse_lane_a_stream(
                header
                + item[:-1]
                + bytes([item[-1] ^ 1])
            )

    def test_reference_hit_matches_lane_b_tie_rule(self) -> None:
        ray = contract.Ray(
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 2.0),
            10.0,
        )
        high_id = contract.Triangle(
            (-1.0, -1.0, 2.0),
            (1.0, -1.0, 2.0),
            (0.0, 1.0, 2.0),
            9,
        )
        low_id = contract.Triangle(
            (-1.0, -1.0, 2.0),
            (1.0, -1.0, 2.0),
            (0.0, 1.0, 2.0),
            3,
        )
        hit = contract.trace_reference(
            [high_id, low_id],
            ray,
        )
        self.assertTrue(hit.hit)
        self.assertEqual(hit.primitive_id, 3)
        self.assertAlmostEqual(hit.t, 2.0, places=5)
        self.assertTrue(
            contract.equivalent_hit(hit, hit)
        )


if __name__ == "__main__":
    unittest.main()
