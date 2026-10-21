#!/usr/bin/env python3
"""CPU-only contract tests; mock N004 geometry adapter, no GPU."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_heldout_geometry import generate, verify


FACTORY = """
import json
from pathlib import Path
def leak_scene(kind, thickness):
    return [([(thickness, 0., 0.), (1., 0., 0.), (0., 1., 0.)], [0, 1, 2])]
def triangle_count(groups):
    return sum(len(i)//3 for _, i in groups)
def write_gltf(root, name, groups):
    target = root / (name + '.gltf')
    target.write_text(json.dumps(groups))
    (root / (name + '.bin')).write_bytes(name.encode())
    return target
"""


class HeldoutManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.factory = self.dir / "frozen_factory.py"
        self.factory.write_text(FACTORY)
        self.out = self.dir / "heldout"

    def run_generate(self):
        manifest = generate(self.out, self.factory)
        self.assertEqual(len(manifest["scenes"]), 3)
        self.assertTrue(manifest["complete"])
        return self.out / "manifest.json"

    def test_generator_and_integrity_verifier(self):
        p = self.run_generate()
        verdict = verify(p, self.factory)
        self.assertEqual(verdict["scenes"], 3)
        self.assertEqual(verdict["classification"], "M001_GEOMETRY_MANIFEST_INTEGRITY_PASS_NOT_GPU_READY")

    def test_reject_existing_output(self):
        self.run_generate()
        with self.assertRaises(ValueError):
            generate(self.out, self.factory)

    def test_reject_modified_binary(self):
        p = self.run_generate()
        (self.out / "M001-H02.bin").write_bytes(b"mutated")
        with self.assertRaisesRegex(ValueError, "asset changed"):
            verify(p, self.factory)

    def test_reject_modified_factory(self):
        p = self.run_generate()
        self.factory.write_text(FACTORY + "\n# altered\n")
        with self.assertRaisesRegex(ValueError, "factory changed"):
            verify(p, self.factory)

    def test_no_false_gpu_or_reference_admission(self):
        p = self.run_generate()
        d = json.loads(p.read_text())
        self.assertTrue(all(not r["eligible_reference"] and not r["gpu_state_frozen"] for r in d["scenes"]))
        d["scenes"][0]["eligible_reference"] = True
        p.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError, "may not declare"):
            verify(p, self.factory)


if __name__ == "__main__":
    unittest.main()
