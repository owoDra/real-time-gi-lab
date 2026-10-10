"""Offline B1c packing + SPIR-V parser contracts; no GPU hardware required."""
from __future__ import annotations
import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import audit_p1l_b1c_spirv as spirv

class B1cStaticTests(unittest.TestCase):
    def test_parse_spirv_valid_opcode_count(self):
        blob = struct.pack("<8I", 0x07230203, 0x10600, 0, 20, 0,
                           0x0002003d, 4, 0x000100fd)
        parsed = spirv.parse_spirv(blob)
        self.assertEqual(parsed["instruction_count"], 2)
        self.assertEqual(parsed["selected_opcode_counts"]["OpLoad"], 1)
        self.assertEqual(parsed["selected_opcode_counts"]["OpReturn"], 1)

    def test_parse_spirv_rejects_truncation_and_zero_words(self):
        with self.assertRaises(ValueError):
            spirv.parse_spirv(struct.pack("<6I", 0x07230203, 0, 0, 0, 0, 0))
        with self.assertRaises(ValueError):
            spirv.parse_spirv(b"\x03\x02\x23")

    def test_b1c_source_and_compilation_contract(self):
        project = spirv.ROOT
        helper = (project / "src/research/n006_interval_aware_allocation/"
                  "n006_primary_axis_proxy.hpp").read_text()
        shader = (project / spirv.VARIANTS["candidate_b1c"][0]).read_text()
        baseline = (project / spirv.VARIANTS["accepted_original"][0]).read_text()
        self.assertIn("node.data[2] = delta[axis]", helper)
        self.assertIn("node.data.z", shader)
        self.assertNotIn("nodes[node.data.x]", shader)
        self.assertNotIn("nodes[node.data.y]", shader)
        self.assertEqual("bool intersect_triangle(" in shader,
                         "bool intersect_triangle(" in baseline)
        self.assertIn("n006_p1l_b1c_primary_axis_proxy", (
            project / "src/research/lane_n_end_to_end_renderer/CMakeLists.txt").read_text())

if __name__ == "__main__":
    unittest.main()
