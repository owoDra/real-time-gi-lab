"""030 signed scoring and provenance boundary fixtures; no real cohort fit."""
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import surface_residual_corrected_replay as R
import surface_residual_corrected_audit as A
import surface_residual_signed_metrics as S


class CorrectedContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = R.PREPARATION.parent/'fixtures'
        cls.fixture.mkdir()

    def test_analytic_signed_error_bias_and_nonpositive_support(self):
        a, r = np.array([-1., 1., 4.]), np.array([1., 2., 3.])
        for method in (S.metric, A.metric):
            m = method(a, r, signed=True)
            self.assertAlmostEqual(m['nrmse'], math.sqrt(6/14))
            self.assertAlmostEqual(m['signed_sum_bias'], -2/6)
            self.assertEqual(m['gpu_zero_reference_positive'], 1)
            self.assertEqual(m['whole_image_max_absolute'], 2)
            self.assertEqual(m['pixels'], 3)
            self.assertEqual(m['scoring_exclusions'], 0)

    def test_clip_changes_signed_estimate_and_bias(self):
        a, r = np.array([-2., 0., 3.]), np.ones(3)
        signed, clipped = S.metric(a, r, signed=True), S.metric(np.maximum(a, 0), r)
        self.assertAlmostEqual(signed['signed_sum_bias'], -2/3)
        self.assertEqual(clipped['signed_sum_bias'], 0)
        self.assertEqual(signed['gpu_zero_reference_positive'], 2)
        self.assertGreater(signed['nrmse'], clipped['nrmse'])

    def test_nonnegative_adapter_matches_historical_physical_scorer(self):
        a = np.array([0., .4, .8, 0., 1.2]); r = np.array([.2, .3, .9, 0., 0.])
        old = R.R.N.Q.P.S.metrics(a, r)
        self.assertEqual(S.metric(a, r), old)
        for key, value in A.metric(a, r).items():
            self.assertAlmostEqual(value, old[key], places=13)

    def test_negative_physical_candidate_or_reference_rejected(self):
        for method in (S.metric, A.metric):
            with self.assertRaises(ValueError): method([-1.], [1.])
            with self.assertRaises(ValueError): method([1.], [-1.], signed=True)

    def test_nonfinite_shape_empty_and_zero_reference_rejected(self):
        for method in (S.metric, A.metric):
            for candidate, ref in [([math.nan], [1.]), ([math.inf], [1.]), ([1.], [math.nan]),
                                   ([1., 2.], [1.]), ([], []), ([1.], [0.])]:
                with self.subTest(method=method.__module__, candidate=candidate):
                    with self.assertRaises(ValueError): method(candidate, ref, signed=True)

    def test_full_roles_signed_permission_and_error_maps(self):
        r = {k: np.ones((180, 320)) for k in ('direct', 'indirect')}; r['total'] = r['direct']+r['indirect']
        signed = np.ones(57600); signed[0] = -3
        images = dict(baseline=np.ones(57600), signed=signed, clipped=np.maximum(signed, 0))
        scores, errors = S.score(images, np.ones(57600), r)
        self.assertEqual(scores['signed']['components']['indirect']['gpu_zero_reference_positive'], 1)
        self.assertEqual(errors['signed_indirect'][0, 0], -4)
        self.assertEqual(len(errors), 9)
        with self.assertRaises(ValueError): S.score(images, -np.ones(57600), r)
        for role in ('baseline', 'clipped'):
            invalid = dict(images); invalid[role] = signed
            with self.assertRaises(ValueError): S.score(invalid, np.ones(57600), r)

    def test_original_joint_quality_thresholds(self):
        ref = dict(direct=np.ones((180, 320)), indirect=np.ones((180, 320)), total=np.full((180, 320), 2.))
        for amplitude, passed in ((.099, True), (.101, False)):
            indirect = np.tile([1+amplitude, 1-amplitude], 28800)
            images = {k: indirect for k in ('baseline', 'signed', 'clipped')}
            scores, _ = S.score(images, np.ones(57600), ref)
            self.assertEqual(scores['signed']['pass_'], passed)
            for c in ('direct', 'indirect', 'total'):
                image = np.ones(57600) if c == 'direct' else indirect if c == 'indirect' else 1+indirect
                for key, value in A.metric(image, ref[c].ravel(), signed=c != 'direct').items():
                    self.assertAlmostEqual(value, scores['signed']['components'][c][key], places=10)

    def test_signed_energy_bias_and_direct_support_gates(self):
        r = dict(direct=np.ones((180, 320)), indirect=np.ones((180, 320)), total=np.full((180, 320), 2.))
        images = {k: np.full(57600, 1.051) for k in ('baseline', 'signed', 'clipped')}
        scores, _ = S.score(images, np.ones(57600), r)
        self.assertFalse(scores['signed']['pass_'])
        images = {k: np.ones(57600) for k in images}; d = np.ones(57600); d[0] = 0
        scores, _ = S.score(images, d, r)
        self.assertFalse(scores['signed']['pass_'])
        self.assertEqual(scores['signed']['components']['direct']['gpu_zero_reference_positive'], 1)

    def test_independent_percentile_and_near_zero_support(self):
        a = np.array([-1e-30, 0., 1e-30, 2.]); ref = np.array([1., 1., 1., 0.])
        for key, value in A.metric(a, ref, signed=True).items():
            self.assertAlmostEqual(value, S.metric(a, ref, signed=True)[key], places=13)
        self.assertEqual(A.metric(a, ref, signed=True)['gpu_zero_reference_positive'], 2)

    def test_durable_expected_input_survives_injected_frame_failure(self):
        out = self.fixture/'frame-failure'; out.mkdir(); capture = out/'source'
        expected = {f'capture/frame-0/{name}': 'a'*64 for name in
                    ('raw-pt.f32', 'secondary-rays.f32', 'hits.u32', 'secondary-origins.f32')}
        info = dict(capture=capture, native=dict(payload_sha256=expected))
        with patch.object(R.R, 'frame', side_effect=ValueError('injected before numerical work')):
            with self.assertRaisesRegex(ValueError, 'injected'): R.read_frame(info, 0, out)
        receipt = json.loads((out/'frame-0-before.json').read_text())
        self.assertTrue(receipt['expected_identities']); self.assertEqual(len(receipt['input_sha256']), 4)
        self.assertTrue(all(x == 'a'*64 for x in receipt['input_sha256'].values()))

    def test_phase_receipt_is_snapshot_and_exclusive(self):
        out = self.fixture/'phase'; out.mkdir(); pins = {'source': 'b'*64}
        R.phase(out, 'before', pins, reference_radiance_decoded=False); pins['later'] = 'c'*64
        self.assertEqual(json.loads((out/'before.json').read_text())['input_sha256'], {'source': 'b'*64})
        with self.assertRaises(FileExistsError): R.phase(out, 'before', pins)

    def test_reference_manifest_uses_anchored_plan_before_decode(self):
        out = self.fixture/'reference'; out.mkdir(); source = out/'source'; source.mkdir()
        q = source/'qualification.json'; q.write_text(json.dumps({'levels': [{'all_payload_sha256': {}}]}))
        info = dict(native={}, plan=dict(proof=dict(reference_directory=str(source)), input_sha256={str(q): R.B.SHA(q)}), pins={})
        def decode(argument):
            self.assertTrue((out/'reference-before.json').exists())
            self.assertEqual(argument['pins'][str(q)], R.B.SHA(q)); return 'fixture'
        with patch.object(R.R, 'references', side_effect=decode): self.assertEqual(R.reference(info, out), 'fixture')

    def test_exclusive_canonical_output(self):
        target = self.fixture/'reserved'; R.reserve(target, target)
        with self.assertRaises(ValueError): R.reserve(target, target)
        with self.assertRaises(ValueError): R.reserve(self.fixture/'different', target)

    def test_fixed_order_rejects_missing_and_invalid_prior(self):
        base = self.fixture/'order'; base.mkdir()
        self.assertEqual(R.previous('H01', 2, base), {})
        with self.assertRaises(FileNotFoundError): R.previous('H01', 8, base)
        p = base/(R.tag('H01', 2)+'-audit-v1'); p.mkdir()
        (p/'result.json').write_text(json.dumps(dict(complete=False, valid=False, all_pass=False)))
        with self.assertRaises(ValueError): R.previous('H01', 8, base)
        with self.assertRaises(ValueError): R.previous('H04', 2, base)

    def test_no_gpu_or_unregistered_cli(self):
        for args in (['gpu'], ['replay', '--cell', 'H04', '--depth', '2', '--out', 'x'],
                     ['replay', '--cell', 'H01', '--depth', '4', '--out', 'x']):
            with self.assertRaises(SystemExit): R.parser().parse_args(args)


if __name__ == '__main__': unittest.main()
