"""032 real CPU inheritance/signal/timeout/native-exec contracts; no M001 data."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import unittest
import numpy as np
import anchor_process_limits as C
import anchor_path_difference_corrected as R


class ProcessContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = R.PREPARATION.parent/'fixtures'; cls.root.mkdir()

    def test_actual_parent_and_1200_child_after_exec(self):
        parent = C.limits()
        self.assertEqual(parent, dict(cpu=[360, 1200], address=[C.ADDRESS, C.ADDRESS], core=[0, 0], sigxcpu_default=True, sigxcpu_unblocked=True))
        folder = self.root/'effective'; folder.mkdir()
        command = [sys.executable, '-c', 'import json,resource,signal; print(json.dumps(dict(cpu=resource.getrlimit(resource.RLIMIT_CPU),address=resource.getrlimit(resource.RLIMIT_AS),core=resource.getrlimit(resource.RLIMIT_CORE),default=signal.getsignal(signal.SIGXCPU)==signal.SIG_DFL,unblocked=signal.SIGXCPU not in signal.pthread_sigmask(signal.SIG_BLOCK,set()))))']
        result = C.guarded(command, folder, 'native-budget', cpu=1200, wall=10)
        actual = json.loads((folder/'native-budget.stdout').read_text())
        self.assertEqual(actual, dict(cpu=[1200, 1200], address=[C.ADDRESS, C.ADDRESS], core=[0, 0], default=True, unblocked=True))
        self.assertEqual(json.loads((folder/'native-budget.child-limits.json').read_text())['cpu'], [1200, 1200])
        self.assertTrue(result['reaped']); self.assertEqual(result['returncode'], 0)

    def test_qualified_native_geometry_and_paths_registered_limits(self):
        folder = self.root/'native-integration'; folder.mkdir()
        # A tiny two-sided square covers exactly one actual center-primary pixel.
        x, y, e = .003125, 1-2*89.5/180, .0001
        scene = folder/'synthetic.n008'
        scene.write_text('n008scene 1\nresolution 320 180\ncamera 0 0 1 0 0 -1 0 1 0 1 1 0 10\nsampling center\nmax_bounces 2\nfalloff n001_soft 1\nsecondary_far inf\nmaterial s 1 1 1 0 0 0 1\npoint 0 0 1 1 1 1\n'+
                         f'tri s {x-e:.17g} {y-e:.17g} 0 {x+e:.17g} {y-e:.17g} 0 {x+e:.17g} {y+e:.17g} 0\n'+
                         f'tri s {x-e:.17g} {y-e:.17g} 0 {x+e:.17g} {y+e:.17g} 0 {x-e:.17g} {y+e:.17g} 0\n')
        exe = str(R.BUILD/'anchor_path_difference_cpu'); geometry = folder/'geometry'
        C.guarded([exe, 'geometry', '--scene', str(scene), '--out', str(geometry)], folder, 'geometry', cpu=120, wall=180)
        primary = np.fromfile(geometry/'primary.bin', R.PRIMARY); active = primary['tri'] != 0xffffffff
        self.assertEqual(int(active.sum()), 1)
        groups = np.full(57600, -1, dtype='<i8'); groups[active] = 0; groups.tofile(geometry/'groups.i64')
        anchors = np.flatnonzero(active).astype('<u4'); anchors.tofile(geometry/'anchors.u32')
        paths = folder/'paths'
        C.guarded([exe, 'paths', '--scene', str(scene), '--geometry', str(geometry), '--out', str(paths)], folder, 'paths', cpu=1200, wall=1800)
        n = json.loads((paths/'paths.json').read_text())
        self.assertTrue(n['complete']); self.assertFalse(n['gpu_executed']); self.assertEqual(n['active_pixels'], 1)
        self.assertEqual(n['groups'], 1); self.assertEqual(n['pairs'], 16); self.assertEqual(n['absolute'], 1024)
        self.assertEqual([x['seed'] for x in n['rows']], list(R.SEEDS))
        for row in n['rows']:
            for name in ('local_closest', 'paired_closest', 'extra_closest'): self.assertEqual(row[name], 32)
            self.assertEqual(row['bank_closest'], 2048)
        self.assertEqual(json.loads((folder/'geometry.child-limits.json').read_text())['cpu'], [120, 120])
        self.assertEqual(json.loads((folder/'paths.child-limits.json').read_text())['cpu'], [1200, 1200])
        self.assertTrue(json.loads((folder/'paths.process.json').read_text())['reaped'])

    def test_soft_cpu_guard_default_signal_scaled_probe(self):
        folder = self.root/'soft-cpu'; folder.mkdir()
        code = 'import json,resource,signal; resource.setrlimit(resource.RLIMIT_CPU,(1,3)); print(json.dumps(dict(cpu=resource.getrlimit(resource.RLIMIT_CPU),default=signal.getsignal(signal.SIGXCPU)==signal.SIG_DFL)),flush=True)\nwhile True: pass\n'
        with self.assertRaises(ValueError): C.guarded([sys.executable, '-c', code], folder, 'soft-probe', cpu=1200, wall=15)
        actual = json.loads((folder/'soft-probe.stdout').read_text()); self.assertEqual(actual, dict(cpu=[1, 3], default=True))
        terminal = json.loads((folder/'soft-probe.process.json').read_text())
        self.assertEqual(terminal['returncode'], -signal.SIGXCPU); self.assertFalse(terminal['timed_out']); self.assertTrue(terminal['reaped'])

    def test_wall_timeout_kills_and_reaps_exact_child(self):
        folder = self.root/'wall'; folder.mkdir()
        with self.assertRaises(ValueError): C.guarded([sys.executable, '-c', 'import time; time.sleep(10)'], folder, 'wall-probe', cpu=1200, wall=.1)
        terminal = json.loads((folder/'wall-probe.process.json').read_text()); pid = json.loads((folder/'wall-probe.pid.json').read_text())['pid']
        self.assertEqual(terminal['pid'], pid); self.assertEqual(terminal['returncode'], -signal.SIGKILL)
        self.assertTrue(terminal['timed_out'] and terminal['reaped'])
        with self.assertRaises(ProcessLookupError): os.kill(pid, 0)

    def test_failure_and_exclusive_receipts_preserve_actual_limits(self):
        folder = self.root/'failure'; folder.mkdir()
        with self.assertRaises(ValueError): C.guarded([sys.executable, '-c', 'raise SystemExit(19)'], folder, 'failure', cpu=1200, wall=10)
        self.assertEqual(json.loads((folder/'failure.process.json').read_text())['returncode'], 19)
        self.assertEqual(json.loads((folder/'failure.command.json').read_text())['parent_effective']['cpu'], [360, 1200])
        self.assertEqual(json.loads((folder/'failure.child-limits.json').read_text())['cpu'], [1200, 1200])
        with self.assertRaises(FileExistsError): C.guarded([sys.executable, '-c', 'pass'], folder, 'failure', cpu=1200, wall=10)

    def test_new_output_order_and_no_gpu_cli(self):
        folder = self.root/'canonical'; R.reserve(folder, folder)
        with self.assertRaises(ValueError): R.reserve(folder, folder)
        with self.assertRaises(ValueError): R.reserve(self.root/'different', folder)
        order = self.root/'order'; order.mkdir(); self.assertEqual(R.previous('H01', 2, order), {})
        with self.assertRaises(FileNotFoundError): R.previous('H01', 8, order)
        a = order/(R.tag('H01', 2)+'-audit-v1'); a.mkdir()
        (a/'result.json').write_text(json.dumps(dict(complete=False, valid=False, all_pass=False)))
        with self.assertRaises(ValueError): R.previous('H01', 8, order)
        with self.assertRaises(SystemExit): R.parser().parse_args(['gpu'])


if __name__ == '__main__': unittest.main()
