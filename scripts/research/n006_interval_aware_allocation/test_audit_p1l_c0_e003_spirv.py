from __future__ import annotations
import unittest
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

    @staticmethod
    def _fake_build(folder: Path, *, active: bytes | None) -> None:
        shader_dir = folder / "shaders"
        shader_dir.mkdir()
        (folder / "CMakeCache.txt").write_text(
            "GLSLANG_VALIDATOR:FILEPATH=glslangValidator\n")
        words = [0x07230203, 0x00010600, 0, 20, 0, 0x00010088, 0x000100fd]
        rebuilt = struct.pack("<" + ("I" * len(words)), *words)
        (shader_dir / "n006_p1l_c0_e003_source_rebuild.spv").write_bytes(rebuilt)
        (shader_dir / "n006_p1l_e003_count.spv").write_bytes(rebuilt)
        if active is not None:
            (shader_dir / "e003_instance_quantized.spv").write_bytes(active)

    def test_missing_active_binary_is_blocked_but_retains_static_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_build(root, active=None)
            result = c0.audit(root)
            self.assertEqual(result["provenance_status"],
                             "BLOCKED_ACTIVE_BINARY_MISSING")
            self.assertEqual(result["status"], "blocked")
            self.assertIn("OpFDiv",
                          result["variants"]["accepted_e003_rebuilt"]["opcode_families"])

    def test_mismatched_active_binary_is_blocked_with_hash_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_build(root, active=struct.pack(
                "<7I", 0x07230203, 0x00010600, 0, 20, 0,
                0x000100fd, 0x000100fd))
            result = c0.audit(root)
            self.assertEqual(result["provenance_status"],
                             "BLOCKED_BINARY_MISMATCH")
            self.assertFalse(result["runtime_e003_binary"]["matches_fresh_source_rebuild"])
            self.assertIsNotNone(result["runtime_e003_binary"]["sha256"])

    def test_matched_active_binary_is_static_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fake_build(root, active=b"")
            spv_path = root / "shaders" / "n006_p1l_c0_e003_source_rebuild.spv"
            (root / "shaders" / "e003_instance_quantized.spv").write_bytes(
                spv_path.read_bytes())
            result = c0.audit(root)
            self.assertEqual(result["provenance_status"], "MATCHED")
            self.assertEqual(result["status"], "ready_static_only")
            self.assertEqual(result["variants"]["accepted_e003_rebuilt"]["opcode_families"]["OpFDiv"],1)

    def test_missing_compiled_artifact_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                c0.audit(Path(tmp))

if __name__ == "__main__":
    unittest.main()
