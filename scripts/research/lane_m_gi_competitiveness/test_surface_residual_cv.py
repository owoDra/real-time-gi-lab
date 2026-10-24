"""029 executed-kernel contracts; synthetic mathematics, no physical paths/GPU."""
import unittest
import numpy as np
import surface_residual_cv as K


class Kernel(unittest.TestCase):
    def test_cosine_moments_by_independent_quadrature(self):
        z, weights = np.polynomial.legendre.leggauss(24)
        z = (z+1)/2; weights = weights/2
        phi = 2*np.pi*(np.arange(96)+.5)/96
        for normal in np.array([[0, 0, 1], [1, 0, 0], [0, 0, -1], [1, 2, 3], [-3, 2, -1]], float):
            normal /= np.linalg.norm(normal)
            helper = np.eye(3)[np.argmin(np.abs(normal))]
            tangent = np.cross(helper, normal); tangent /= np.linalg.norm(tangent)
            bitangent = np.cross(normal, tangent)
            w = z[:, None, None]*normal+np.sqrt(1-z*z)[:, None, None]*(
                np.cos(phi)[None, :, None]*tangent+np.sin(phi)[None, :, None]*bitangent)
            f = K.basis(w)
            observed = (f*(2*z*weights)[:, None, None]).sum(axis=(0, 1))/len(phi)
            np.testing.assert_allclose(observed, K.moments(normal[None])[0], rtol=0, atol=2e-14)

    def test_constant_cancels_exactly(self):
        w = np.tile([0., 0., 1.], (56, 3, 1)); c = np.zeros((1, 9)); c[0, 0] = 123.
        self.assertTrue(np.array_equal(K.correction(K.basis(w), K.moments(w[0]), c, np.zeros(3, int)), np.zeros((56, 3))))

    def test_signed_polynomial_residual_is_retained(self):
        rng = np.random.default_rng(2901); w = K.unit_vectors(rng.normal(size=(56, 5, 3)))
        mu = K.moments(np.tile([0., 0., 1.], (5, 1)))
        c = np.array([[2., -3., 4., -1., 1., 2., -1., .5, -.25]])
        f = np.einsum('fpk,k->fp', K.basis(w), c[0])
        corrected = f+K.correction(K.basis(w), mu, c, np.zeros(5, int))
        np.testing.assert_allclose(corrected, np.broadcast_to(mu@c[0], corrected.shape), rtol=0, atol=2e-14)
        self.assertTrue((f < 0).any())

    def test_ridge_matches_augmented_svd(self):
        rng = np.random.default_rng(2902); x = K.basis(rng.normal(size=(8, 12, 3)))
        y = rng.uniform(size=(8, 12)); groups = np.arange(12) % 3
        fit = K.train(x, y, groups, 3)
        for g in range(3):
            a = x[:, groups == g].reshape(-1, 9)
            expected = np.linalg.lstsq(np.vstack((a, np.sqrt(fit['lambdas'][g])*np.eye(9))),
                                     np.r_[y[:, groups == g].ravel(), np.zeros(9)], rcond=None)[0]
            np.testing.assert_allclose(fit['coefficients'][g], expected, rtol=1e-10, atol=1e-12)

    def test_zero_and_singular_fields(self):
        x = K.basis(np.tile([0., 0., 1.], (8, 1, 1)))
        fit = K.train(x, np.zeros((8, 1)), np.array([0]), 1)
        self.assertTrue(np.array_equal(fit['coefficients'], np.zeros((1, 9))))
        self.assertTrue(np.isfinite(K.train(x, np.ones((8, 1)), np.array([0]), 1)['coefficients']).all())

    def test_sky_correction_zero(self):
        x = np.ones((56, 2, 9)); mu = np.zeros((2, 9))
        self.assertEqual(float(K.correction(x, mu, np.ones((1, 9)), np.array([-1, 0]))[:, 0].sum()), 0)

    def test_geometry_owner_material_partition(self):
        vertices = np.array([[[0., 0., 0.], [1., 0., 0.], [0., 1., 0.]]])
        meta = np.array([[8, 0xffffffff, 7, 0]], dtype=np.uint32)
        origin = np.array([[.1, .1, 0.], [.1, .1, 0.], [0., 0., 0.]])
        normal = np.tile([0., 0., 1.], (3, 1)); active = np.array([True, True, False])
        owner = np.array([7, 7, 0xffffffff], dtype=np.uint32)
        material = np.array([0xffffffff, 2, 0xffffffff], dtype=np.uint32)
        a = K.partition(origin, normal, active, owner, material, vertices, meta)
        self.assertEqual(len(a['keys']), 2); self.assertEqual(a['groups'][2], -1)
        self.assertIn(0xffffffff, a['keys'][:, 1])
        b = K.partition(origin+3, normal, active, owner, material, vertices+3, meta)
        np.testing.assert_array_equal(a['keys'], b['keys'])

    def test_training_not_corrected_and_negatives_not_clipped(self):
        raw = np.tile(np.arange(64, dtype=float)[:, None]+1, (1, 2))
        corrected = -raw[8:]
        images, _ = K.aggregate(raw, corrected)
        np.testing.assert_array_equal(images['signed'], (raw[:8].sum(axis=0)-raw[8:].sum(axis=0))/64)
        self.assertTrue((images['signed'] < 0).all()); self.assertTrue((images['clipped'] == 0).all())

    def test_bad_vectors(self):
        for bad in (np.zeros((2, 3)), np.full((2, 3), np.nan), np.ones((2, 4))):
            with self.assertRaises(ValueError): K.basis(bad)

    def test_wrong_split_and_nonfinite_rejected(self):
        for raw, corrected in ((np.ones((63, 2)), np.ones((56, 2))),
                               (np.full((64, 2), np.inf), np.ones((56, 2))),
                               (np.ones((64, 2)), np.ones((56, 2)))):
            with self.assertRaises(ValueError): K.aggregate(raw, corrected)

    def test_missing_group_and_invalid_correction_rejected(self):
        with self.assertRaises(ValueError): K.train(np.ones((8, 1, 9)), np.ones((8, 1)), np.array([0]), 2)
        with self.assertRaises(ValueError): K.correction(np.ones((56, 1, 9)), np.ones((1, 9)), np.ones((1, 9)), np.array([1]))

    def test_full64_cannot_train(self):
        with self.assertRaises(ValueError): K.train(np.ones((64, 1, 9)), np.ones((64, 1)), np.array([0]), 1)


class Process(unittest.TestCase):
    def test_cli_has_no_gpu_mode(self):
        import contextlib, io
        import surface_residual_replay as R
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            R.parser().parse_args(['--gpu'])

    def test_order_rejects_missing_and_invalid_previous(self):
        import tempfile
        from pathlib import Path
        import surface_residual_replay as R
        base = Path(tempfile.mkdtemp(prefix='m001-residual029-order-fixture-', dir=R.BASE))
        self.assertEqual(R.previous('H01', 2, base), {})
        with self.assertRaises(FileNotFoundError): R.previous('H01', 8, base)
        p = base/(R.tag('H01', 2)+'-audit-v1'); p.mkdir()
        R.write(p/'result.json', dict(complete=False, valid=False, all_pass=False))
        with self.assertRaises(ValueError): R.previous('H01', 8, base)

    def test_overwrite_and_noncanonical_output_rejected(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import surface_residual_replay as R
        base = Path(tempfile.mkdtemp(prefix='m001-residual029-output-fixture-', dir=R.BASE))
        with patch.object(R, 'BASE', base):
            existing = base/'existing'; existing.mkdir(); (existing/'sentinel').write_text('keep')
            with self.assertRaises(ValueError): R.reserve(existing, existing)
            with self.assertRaises(ValueError): R.reserve(base/'other', base/'expected')
            self.assertEqual((existing/'sentinel').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
