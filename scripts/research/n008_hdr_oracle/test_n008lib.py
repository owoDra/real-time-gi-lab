#!/usr/bin/env python3
"""Unit tests for the independent expected-value code (needs numpy; the hash
parity test also needs the built oracle)."""
from __future__ import annotations

import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import n008lib as L  # noqa: E402


class FormFactor(unittest.TestCase):
    def test_rectangle_formula_matches_brute_quadrature(self):
        h = 2.0
        for px, pz in ((0.0, 0.0), (0.3, -0.2), (1.7, 0.9), (-2.5, 2.0)):
            X, Z, W = L.gauss_legendre_square(-0.5, 0.5, -0.5, 0.5, 16, 8)
            r2 = (X - px) ** 2 + h * h + (Z - pz) ** 2
            brute = float(np.sum(W * h * h / r2 ** 2)) / math.pi
            closed = float(L.rect_point_form_factor(np.array(px), np.array(pz), h, -0.5, 0.5, -0.5, 0.5))
            self.assertAlmostEqual(closed, brute, delta=1e-12 + 1e-10 * brute)

    def test_infinite_plane_limit_is_one(self):
        self.assertAlmostEqual(float(L.rect_point_form_factor(np.array(0.0), np.array(0.0), 1.0, -1e6, 1e6, -1e6, 1e6)), 1.0, places=5)


class Geometry(unittest.TestCase):
    def test_camera_centre_ray_and_handedness(self):
        cam = L.Camera((0, 0, 0), (0, 0, -1), tan_x=0.5, tan_y=0.375)
        o, d = L.camera_rays(cam, 128, 96)
        self.assertGreater(d[48, 127, 0], 0)  # right column looks +x
        self.assertGreater(d[0, 64, 1], 0)    # top row looks +y
        np.testing.assert_allclose(np.linalg.norm(d, axis=-1), 1.0, rtol=1e-15)

    def test_icosphere_bounds(self):
        v, f = L.icosphere(3)
        self.assertEqual(len(f), 20 * 4 ** 3)
        np.testing.assert_allclose(np.linalg.norm(v, axis=1), 1.0, rtol=1e-15)
        dev, sag = L.sphere_mesh_bounds(v, f)
        self.assertGreater(dev, 0); self.assertGreater(sag, 0); self.assertLess(sag, 0.01)

    def test_obb_slab(self):
        o = np.array([0.0, 0.0, 5.0]); d = np.array([[[0.0, 0.0, -1.0]]])
        t0, t1 = L.ray_obb(o, d, (0, 0, 0), np.eye(3), (1, 1, 1))
        self.assertAlmostEqual(float(t0.item()), 4.0); self.assertAlmostEqual(float(t1.item()), 6.0)

    def test_box_triangles_outward(self):
        sc = L.Scene(L.Camera((0, 0, 5), (0, 0, 0)))
        sc.material("m", (0.5, 0.5, 0.5))
        L.box_triangles(sc, "m", (1, 2, 3), np.eye(3), (0.5, 1, 2))
        for _, a, b, c in sc.triangles:
            a, b, c = map(np.array, (a, b, c))
            n = np.cross(b - a, c - a)
            self.assertGreater(np.dot(n, (a + b + c) / 3 - np.array((1, 2, 3))), 0)


class OracleParity(unittest.TestCase):
    def test_geometry_hash_and_sidecar_roundtrip(self):
        try:
            L.oracle_binary()
        except SystemExit:
            self.skipTest("oracle not built")
        sc = L.Scene(L.Camera((0, 0, 3), (0, 0, 0)), width=8, height=6)
        sc.material("m", (0.25, 0.5, 0.75))
        sc.quad("m", (-1, -1, 0), (2, 0, 0), (0, 2, 0))
        sc.tri("m", (0.1, 0.2, -1.0 / 3.0), (1.0 / 7.0, 0.5, -1), (0.3, math.pi, -1))
        sc.point((0, 0, 2), (1, 1, 1))
        with tempfile.TemporaryDirectory() as tmp:
            meta = L.run_oracle(sc, Path(tmp), "t", seeds=(1, 2), spp=3)
            self.assertTrue(meta["geometry_hash_match"])
            self.assertEqual(meta["scene_sha256"], meta["scene_file_sha256_python"])
            pooled = L.pooled(meta)
            pfm = L.read_pfm(Path(meta["runs"][0]["prefix"] + ".total.pfm"))
            np.testing.assert_allclose(pfm, pooled["per_seed"][0]["mean"][..., 3, :], rtol=1e-6)
            self.assertEqual(pooled["n"], 6)


if __name__ == "__main__":
    unittest.main()
