"""031 actual aggregation, geometry, counter-overlay and durable-phase fixtures."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from unittest.mock import patch
import numpy as np
import anchor_path_difference as R
import anchor_difference_overlay as O


class AnchorContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = R.BUILD/'fixtures'; cls.root.mkdir()

    def test_reversible_namespace_and_counter_overlay(self):
        raw = O.ORIGINAL.read_bytes(); generated, proof = O.overlay(raw)
        self.assertTrue(proof['exact_inverse']); self.assertEqual(generated.count(b'++cnt.closest_queries;'), 1)
        self.assertIn(b'namespace phos::gi::research::m001anchor_physical {', generated)
        self.assertEqual(raw, O.ORIGINAL.read_bytes())
        with self.assertRaises(ValueError): O.overlay(raw+ b'\nstruct RenderCounters {\n')

    def test_actual_aggregate_signed_mean_control_reuse_and_full_bank_queries(self):
        folder = self.root/'aggregate'; folder.mkdir(); groups = np.full(57600, -1, dtype=np.int64); groups[:2] = 0
        for i in range(4):
            p = folder/f'seed-{i}'; p.mkdir()
            absolute = np.full((1, 1024), .01*(i+1)); local = np.zeros((57600, 16)); local[:2] = 1+i
            paired = np.zeros_like(local); paired[:2] = 3+i; extra = local.copy()
            direct = np.zeros(57600); direct[:2] = 1
            queries = np.zeros((57600, 6), dtype='<u8'); queries[:2] = [32, 16, 32, 16, 32, 16]
            for name, data in [('anchor-absolute.f64', absolute), ('local.f64', local), ('paired-anchor.f64', paired), ('extra-local.f64', extra), ('direct.f64', direct),
                               ('query-counts.u64', queries), ('bank-query-counts.u64', np.array([[2048, 1024]], dtype='<u8'))]: data.tofile(p/name)
        images, cost, variances, rows = R.aggregate(folder, groups)
        np.testing.assert_allclose(images['signed'][:, 0], np.arange(1, 5)*.01-2, rtol=0, atol=1e-15)
        np.testing.assert_array_equal(images['clipped'], 0)
        np.testing.assert_array_equal(images['baseline'][:, 0], np.arange(1, 5))
        self.assertEqual(cost['baseline_complete_queries'], 58368)
        self.assertEqual(cost['candidate_complete_queries'], 70656)
        self.assertEqual(cost['geometry_scan_queries_per_role'], 57600)
        self.assertTrue((variances['baseline'][2:] == 0).all()); self.assertEqual(len(rows), 4)
        # The executed loader rejects a corrupt physical value, rather than
        # obtaining a seemingly better signed estimate from a negative path.
        file = folder/'seed-0/local.f64'; a = np.memmap(file, dtype='<f8', mode='r+', shape=(57600, 16)); a[0, 0] = -1; a.flush(); del a
        with self.assertRaises(ValueError): R.raw_seed(folder, 0, groups)

    def test_geometry_only_opaque_owners_and_median_anchor(self):
        folder = self.root/'geometry'; folder.mkdir()
        primary = np.zeros(57600, dtype=R.PRIMARY); primary['t'] = -1; primary['tri'] = 0xffffffff
        primary['tri'][[2, 5, 9]] = 0; primary['t'][[2, 5, 9]] = 1; primary['front'][[2, 5, 9]] = 1
        primary.tofile(folder/'primary.bin')
        origin = np.zeros((57600, 3)); origin[[2, 5, 9], 2] = 1e-12
        normal = np.zeros((57600, 3)); normal[:, 2] = 1
        vertices = np.array([[[-1., -1., 0.], [1., -1., 0.], [1., 1., 0.]]])
        origin.tofile(folder/'origins.f64'); normal.tofile(folder/'normals.f64'); vertices.tofile(folder/'vertices.f64')
        ref = folder/'original.hits'; ref.write_bytes(b'N008HIT\0'+struct.pack('<II', 320, 180)+primary.tobytes())
        info = dict(primary_path=ref, vertices=vertices, metadata=np.array([[0, 0xdeadbeef, 0xffffffff, 0]], dtype='<u4'))
        with patch.object(R.S, 'score', side_effect=AssertionError('radiance in geometry')):
            geo = R.geometry_data(info, folder)
        self.assertEqual(geo['anchors'].tolist(), [5]); self.assertEqual(int(geo['keys'][0, 0]), 0xffffffff)
        self.assertEqual(int(geo['keys'][0, 1]), 0xdeadbeef)
        self.assertTrue((geo['groups'][[2, 5, 9]] == 0).all()); self.assertEqual(int(geo['active'].sum()), 3)

    def test_durable_command_and_phase_survive_expected_failure(self):
        folder = self.root/'failure'; folder.mkdir(); pins = {'fixed': 'a'*64}
        R.phase(folder, 'before', pins, radiance_sampled=False)
        with self.assertRaises(ValueError): R.guarded([sys.executable, '-c', 'raise SystemExit(17)'], folder, 'injected', cpu=3, wall=5)
        self.assertEqual(json.loads((folder/'before.json').read_text())['input_sha256'], pins)
        command = json.loads((folder/'injected.command.json').read_text()); self.assertEqual(command['cpu_limit'], 3)
        self.assertEqual(command['command'][-1], 'raise SystemExit(17)')
        with self.assertRaises(FileExistsError): R.phase(folder, 'before', pins)

    def test_exclusive_output_and_order_rejection(self):
        folder = self.root/'reserved'; R.reserve(folder, folder)
        with self.assertRaises(ValueError): R.reserve(folder, folder)
        with self.assertRaises(ValueError): R.reserve(self.root/'other', folder)
        order = self.root/'order'; order.mkdir(); self.assertEqual(R.previous('H01', 2, order), {})
        with self.assertRaises(FileNotFoundError): R.previous('H01', 8, order)
        p = order/(R.tag('H01', 2)+'-audit-v1'); p.mkdir()
        (p/'result.json').write_text(json.dumps(dict(complete=False, valid=False, all_pass=False)))
        with self.assertRaises(ValueError): R.previous('H01', 8, order)

    def test_python_and_native_no_gpu_malformed_overwrite(self):
        with self.assertRaises(SystemExit): R.parser().parse_args(['gpu'])
        native = str(R.BUILD/'anchor_path_difference_cpu')
        run = subprocess.run([native, 'gpu'], capture_output=True, text=True); self.assertNotEqual(run.returncode, 0)
        folder = self.root/'native-existing'; folder.mkdir(); sentinel = folder/'sentinel'; sentinel.write_text('preserved')
        run = subprocess.run([native, 'geometry', '--scene', '/031-no-scene', '--out', str(folder)], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0); self.assertIn('output exists', run.stderr); self.assertEqual(sentinel.read_text(), 'preserved')


if __name__ == '__main__': unittest.main()
