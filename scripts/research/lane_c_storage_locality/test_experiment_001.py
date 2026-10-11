#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

path = Path(__file__).with_name("experiment_001.py")
spec = importlib.util.spec_from_file_location("lane_c_experiment_001", path)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class C001Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.probes = m.generate(1, (2, 2, 1), 4, 4)

    def test_semantics_for_all_variants(self) -> None:
        variants = [
            m.ProbeHashModel(len(self.probes)),
            m.HashedBrickPoolModel(4, 4),
            m.VirtualClipmapModel(1, 4, (4, 4, 2)),
        ]
        for storage in variants:
            with self.subTest(type=type(storage).__name__):
                self.assertTrue(m.verify(storage, self.probes))

    def test_sparse_bricks_are_not_assumed_to_win(self) -> None:
        probes = m.generate(1, (4, 4, 2), 4, 4)
        h = m.ProbeHashModel(len(probes))
        b = m.HashedBrickPoolModel(32, 4)
        for p in probes:
            h.upsert(p, m.payload(p))
            b.upsert(p, m.payload(p))
        self.assertGreater(b.persistent_bytes, h.persistent_bytes)

    def test_dense_occupancy_can_make_bricks_memory_plausible(self) -> None:
        probes = m.generate(1, (4, 4, 2), 4, 48)
        h = m.ProbeHashModel(len(probes))
        b = m.HashedBrickPoolModel(32, 4)
        for p in probes:
            h.upsert(p, m.payload(p))
            b.upsert(p, m.payload(p))
        self.assertLess(b.persistent_bytes, h.persistent_bytes)


if __name__ == "__main__":
    unittest.main()
