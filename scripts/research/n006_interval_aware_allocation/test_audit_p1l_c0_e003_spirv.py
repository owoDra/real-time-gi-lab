from __future__ import annotations
import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path
import struct

import audit_p1l_c0_e003_spirv as c0

class TestN006E003StaticAudit(unittest.TestCase):
    def test_baseline_shader_has_expected_traversal_structure(self):
        source = (c0.ROOT / c0.VARIANTS["accepted_e003_rebuilt"][0]).read_text()
        checks = c0.source_contract(source)
        self.assertEqual(set(checks.values()), {True})

    def test_missing_division_is_detected_as_source_change(self):
        source = (c0.ROOT / c0.VARIANTS["accepted_e003_rebuilt"][0]).read_text()
        self.assertFalse(c0.source_contract(source.replace(
            "float a = (mn - o) / d;", "float a = 0.0;"))["per_axis_division_source"])

    def test_spirv_instruction_count_not_dynamic_cost(self):
        # Header + one OpFDiv + one OpReturn. Synthetic valid SPIR-V words;
        # the parser counts opcodes but never claims hardware execution counts.
        words=[0x07230203,0x00010600,0,20,0,0x00010088,0x000100fd]
        result=c0.parse_spirv(struct.pack("<"+("I"*len(words)),*words))
        self.assertEqual(result["opcode_counts"].get("136"),1)
        self.assertEqual(result["instruction_count"],2)

    def test_runtime_binary_provenance_is_required(self):
        script = (c0.ROOT / "scripts/research/n006_interval_aware_allocation"
                  / "audit_p1l_c0_e003_spirv.py").read_text()
        self.assertIn("matches_fresh_source_rebuild", script)
        cmake = (c0.ROOT / "src/research/lane_n_end_to_end_renderer"
                 / "CMakeLists.txt").read_text()
        self.assertIn("n006_p1l_c0_e003_source_rebuild", cmake)

    def test_missing_compiled_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                c0.audit(Path(tmp))

if __name__ == "__main__":
    unittest.main()
