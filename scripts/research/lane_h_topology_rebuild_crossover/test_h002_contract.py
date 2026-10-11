from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PATH = Path(__file__).with_name("h002_contract.py")
spec = importlib.util.spec_from_file_location("h002_contract", PATH)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class H002ContractTests(unittest.TestCase):
    def test_sequence_is_deterministic_and_count_changing(self) -> None:
        args = (796, [1.0, 1.25, 0.75, 1.10], 0x48303032, 0.25)
        first = mod.topology_sequence(*args)
        second = mod.topology_sequence(*args)
        self.assertEqual(first, second)
        self.assertTrue(
            all(
                a.primitive_count != b.primitive_count
                for a, b in zip(first, first[1:], strict=False)
            )
        )
        self.assertTrue(all(step.replacement_count > 0 for step in first[1:]))

    def test_digest_changes_with_seed(self) -> None:
        common = dict(
            base_primitive_count=796,
            factors=[1.0, 1.25, 0.75],
            replacement_fraction=0.25,
        )
        a = mod.topology_sequence(seed=1, **common)
        b = mod.topology_sequence(seed=2, **common)
        kwargs = dict(
            producer_contract="A001",
            hit_contract="exact",
            storage_contract="C001",
        )
        self.assertNotEqual(
            mod.workload_digest(a, **kwargs),
            mod.workload_digest(b, **kwargs),
        )

    def test_object_local_mutation_rejects_static_or_unrelated_writes(self) -> None:
        mod.validate_object_local_mutations(
            [
                mod.MutationEvent("static-world", "read"),
                mod.MutationEvent("topology-object-0", "rebuild"),
            ],
            changed_object_id="topology-object-0",
            immutable_owner_ids=["static-world", "unrelated-object-0"],
        )
        with self.assertRaises(ValueError):
            mod.validate_object_local_mutations(
                [mod.MutationEvent("static-world", "rebuild")],
                changed_object_id="topology-object-0",
                immutable_owner_ids=["static-world"],
            )

    def test_boundary_record_requires_explicit_zero_fields(self) -> None:
        required = ["upload_us", "build_us", "tlas_us"]
        mod.validate_boundary_record(
            {"upload_us": 0.0, "build_us": 2.0, "tlas_us": 0.0},
            required,
        )
        with self.assertRaises(ValueError):
            mod.validate_boundary_record(
                {"upload_us": 0.0, "build_us": 2.0},
                required,
            )

    def test_true_peak_counts_reallocation_overlap(self) -> None:
        allocations = [
            mod.AllocationLifetime("old", "topology-object-0", 100, 0, 3),
            mod.AllocationLifetime("new", "topology-object-0", 160, 2, 5),
            mod.AllocationLifetime("scratch", "topology-object-0", 40, 1, 4),
        ]
        self.assertEqual(mod.true_peak_resident_bytes(allocations), 300)

    def test_invalid_lifetime_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            mod.true_peak_resident_bytes([
                mod.AllocationLifetime("bad", "topology-object-0", 1, 2, 2)
            ])


if __name__ == "__main__":
    unittest.main()
