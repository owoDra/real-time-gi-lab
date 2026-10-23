"""013 prospective all-pixel gates, corruption rejection and inclusive boundaries."""
import copy
import json
import unittest
import numpy as np

import closest_primary_metrics as M


def components():
    return {name: dict(pixels=57600, scoring_exclusions=0, nrmse=0.0,
                       signed_sum_bias=0.0, whole_image_max_absolute=0.0,
                       gpu_zero_reference_positive=0)
            for name in ('direct', 'indirect', 'total')}


class PrimaryMetrics(unittest.TestCase):
    def setUp(self):
        self.gpu = np.zeros(57600, dtype=M.GPU_DTYPE)
        self.gpu['prim'] = self.gpu['mat'] = self.gpu['inst'] = M.INVALID
        self.gpu['t'] = np.inf
        self.oracle = np.zeros(57600, dtype=M.ORACLE_DTYPE)
        self.oracle['tri'] = M.INVALID
        self.oracle['t'] = np.inf
        self.meta = np.array([[7, 8, 9, 1]], dtype=np.uint32)
        self.verts = np.array([[[0, 0, 0], [1, 0, 0], [0, 1, 0]]], dtype=float)
        self.gpu[0] = ([0, 0, 1], 1.0, 7, 8, 9, 1)
        self.oracle[0] = (1.0, 0, 1)

    def assess(self, far=200000):
        return M.primary(self.gpu, self.oracle, self.meta, self.verts, far)

    def test_complete_all_pixel_arrays_and_serializable_report(self):
        report, arrays = self.assess()
        self.assertTrue(report['pass_'])
        self.assertEqual(report['pixels'], 57600)
        self.assertEqual(report['scoring_exclusions'], 0)
        self.assertEqual(report['gpu_hit_pixels'], 1)
        self.assertTrue(all(a.shape[0] == 57600 for a in arrays.values()))
        json.dumps(report, allow_nan=False)

    def test_hit_presence_mismatch_is_correctness_failure(self):
        self.oracle[1] = (1.0, 0, 1)
        report, _ = self.assess()
        self.assertFalse(report['pass_'])
        self.assertEqual(report['hit_presence_mismatches'], 1)

    def test_inclusive_depth_bound_then_next_float_fails(self):
        self.oracle[0]['t'] = 100000
        self.gpu[0]['t'] = 100001
        self.assertTrue(self.assess()[0]['pass_'])
        self.gpu[0]['t'] = np.nextafter(np.float32(100001), np.float32(np.inf))
        report, _ = self.assess()
        self.assertFalse(report['pass_'])
        self.assertEqual(report['depth_bound_failures'], 1)

    def test_unknown_primitive_or_inconsistent_metadata_is_invalid(self):
        for field, value in [('prim', 100), ('prim', 6), ('mat', 100), ('inst', 100)]:
            original = self.gpu[0].copy()
            self.gpu[0][field] = value
            with self.assertRaisesRegex(ValueError, 'primitive|metadata'):
                self.assess()
            self.gpu[0] = original

    def test_nonfinite_hit_or_nonunit_normal_is_invalid(self):
        for normal in [[np.nan, 0, 1], [0, 0, 0], [0, 0, 1.01]]:
            self.gpu[0]['n'] = normal
            with self.assertRaisesRegex(ValueError, 'Nonfinite|normal'):
                self.assess()
        self.gpu[0]['n'] = [0, 0, 1]
        self.gpu[0]['t'] = np.inf
        with self.assertRaisesRegex(ValueError, 'Nonfinite'):
            self.assess()

    def test_invalid_flags_miss_clear_and_reference_triangle_are_rejected(self):
        self.gpu[0]['flag'] = 2
        with self.assertRaisesRegex(ValueError, 'flag'):
            self.assess()
        self.gpu[0]['flag'] = 1
        self.gpu[1]['n'] = [1, 0, 0]
        with self.assertRaisesRegex(ValueError, 'miss clear'):
            self.assess()
        self.gpu[1]['n'] = 0
        self.oracle[0]['tri'] = 1
        with self.assertRaisesRegex(ValueError, 'outside geometry'):
            self.assess()

    def test_incomplete_coverage_and_wrong_abi_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'coverage'):
            M.primary(self.gpu[:-1], self.oracle[:-1], self.meta, self.verts, 10)
        with self.assertRaisesRegex(ValueError, 'ABI'):
            M.primary(np.zeros(57600), self.oracle, self.meta, self.verts, 10)

    def test_nonfinite_geometry_and_duplicate_identity_are_rejected(self):
        self.verts[0, 0, 0] = np.inf
        with self.assertRaisesRegex(ValueError, 'geometry'):
            self.assess()
        self.verts[0, 0, 0] = 0
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            M.primary(self.gpu, self.oracle, np.repeat(self.meta, 2, axis=0),
                      np.repeat(self.verts, 2, axis=0), 10)

    def test_normal_difference_is_reported_without_pixel_exclusion(self):
        self.gpu[0]['n'] = [1, 0, 0]
        report, arrays = self.assess()
        self.assertTrue(report['pass_'])
        self.assertEqual(report['normal_vector_mismatch_pixels'], 1)
        self.assertGreater(arrays['normal_vector_error'][0], 1)
        self.assertEqual(report['scoring_exclusions'], 0)


class DecisionMetrics(unittest.TestCase):
    def setUp(self):
        self.primary = dict(pass_=True, pixels=57600, scoring_exclusions=0)
        self.components = components()

    def decide(self, named=()):
        return M.classify(self.primary, self.components, named)

    def test_inclusive_direct_physical_bounds(self):
        self.components['direct'].update(nrmse=1e-4, whole_image_max_absolute=1e-5)
        self.assertEqual(self.decide()['classification'], 'PASS')
        self.components['direct']['nrmse'] = np.nextafter(1e-4, np.inf)
        self.assertEqual(self.decide()['classification'], 'CORRECTNESS_FAIL')

    def test_zero_positive_direct_is_not_ignored(self):
        self.components['direct']['gpu_zero_reference_positive'] = 1
        self.assertEqual(self.decide()['classification'], 'CORRECTNESS_FAIL')

    def test_indirect_quality_loss_does_not_become_direct_correctness_loss(self):
        self.components['indirect']['nrmse'] = .9
        result = self.decide()
        self.assertEqual(result['classification'], 'PASS')
        self.assertEqual(result['quality_classification'], 'QUALITY_FAIL')
        self.assertFalse(result['accepted_timing'])

    def test_inclusive_quality_bounds_and_both_bias_signs(self):
        self.components['total']['nrmse'] = .05
        self.components['indirect']['nrmse'] = .1
        for bias in [.05, -.05]:
            self.components['indirect']['signed_sum_bias'] = bias
            self.assertEqual(self.decide()['quality_classification'], 'PASS')
        self.components['indirect']['signed_sum_bias'] = np.nextafter(.05, np.inf)
        self.assertEqual(self.decide()['quality_classification'], 'QUALITY_FAIL')

    def test_undefined_nonfinite_and_excluded_pixels_invalidate(self):
        for name in ['direct', 'indirect', 'total']:
            for key in ['nrmse', 'signed_sum_bias', 'whole_image_max_absolute']:
                for value in [None, np.nan, np.inf]:
                    data = copy.deepcopy(self.components)
                    data[name][key] = value
                    with self.assertRaisesRegex(ValueError, 'Undefined/nonfinite'):
                        M.classify(self.primary, data, [])
        for changes in [dict(pixels=57599), dict(scoring_exclusions=1)]:
            data = copy.deepcopy(self.components)
            data['direct'].update(changes)
            with self.assertRaisesRegex(ValueError, 'all-pixel'):
                M.classify(self.primary, data, [])

    def test_named_wrong_surface_zero_or_relative_error_one_fails(self):
        row = dict(gpu_primitive=7, reference_primitive=7, gpu_direct=1.0, reference_direct=1.0)
        self.assertEqual(self.decide([row])['classification'], 'PASS')
        for changes in [dict(gpu_primitive=6), dict(gpu_direct=0.0), dict(gpu_direct=2.0)]:
            self.assertEqual(self.decide([dict(row, **changes)])['classification'], 'CORRECTNESS_FAIL')
        self.assertEqual(self.decide([dict(row, gpu_direct=np.nextafter(2.0, 0.0))])['classification'], 'PASS')

    def test_invalid_primary_report_cannot_authorize_next_process(self):
        self.primary['scoring_exclusions'] = 1
        with self.assertRaisesRegex(ValueError, 'primary decision boundary'):
            self.decide()


if __name__ == '__main__':
    unittest.main()
