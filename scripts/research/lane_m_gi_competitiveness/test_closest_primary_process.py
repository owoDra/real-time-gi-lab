"""013 actual CPU process, ordered stop, retained proof and independent map replay."""
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import closest_primary_step as F
import closest_primary_audit as A


class ProcessContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = F.K.Case('C1', 'hwrt')
        self.paths = SimpleNamespace(work=self.root/'work', capture=self.root/'work/capture',
                                     scores=self.root/'scores', plan=self.root/'plan.json', archive=self.root/'proof.tar')
        self.plan = dict(schema='m001-closest-primary-plan/1', scope=dict(cell='C1', backend='hwrt'),
                         command=['unused-native'], input_sha256={}, reference_verification={}, previous_audits={},
                         contract=str(F.K.CONTRACT), gpu_executed=False, accepted_timing=False,
                         source_commit='0'*40)
        F.R.write_new(self.paths.plan, self.plan)

    def test_exact_order_first_to_all_eight_passes(self):
        reports = {}
        for pair in F.K.TARGETS:
            case = F.K.Case(*pair)
            self.assertEqual(F.next_case(reports), case)
            reports[case.name] = dict(correctness_evidence_valid=True, classification='PASS')
        self.assertIsNone(F.next_case(reports))

    def test_any_invalid_operational_or_correctness_loss_stops(self):
        for valid, decision in [(True, 'CORRECTNESS_FAIL'), (False, 'OPERATIONAL_FAILURE_RETAINED_STOP'),
                                (False, 'PASS'), (True, 'QUALITY_FAIL')]:
            with self.assertRaisesRegex(ValueError, 'STOP'):
                F.next_case({'c1-hwrt': dict(correctness_evidence_valid=valid, classification=decision)})

    def test_missing_or_unregistered_history_does_not_advance(self):
        for name in ['c1-software', 'h03-software', 'unregistered']:
            with self.assertRaisesRegex(ValueError, 'missing|Unregistered'):
                F.next_case({name: dict(correctness_evidence_valid=True, classification='PASS')})

    def test_missing_terminal_independent_audit_blocks_history(self):
        self.paths.work.mkdir()
        with patch.object(F, 'Paths', return_value=self.paths):
            with self.assertRaisesRegex(ValueError, 'terminal independent audit'):
                F.history()

    def test_existing_partial_output_is_never_overwritten(self):
        self.paths.work.mkdir()
        with patch.object(F, 'Paths', return_value=self.paths), patch.object(F, 'history') as history:
            with self.assertRaisesRegex(ValueError, 'Existing013'):
                F.prepare(self.case)
            history.assert_not_called()

    def test_process_gate_missing_or_failed_cannot_admit(self):
        gate = self.root/'gate.json'
        with patch.object(F, 'PROCESS_GATE', gate):
            with self.assertRaisesRegex(ValueError, 'not yet admitted'):
                F.process_gate({})
            F.R.write_new(gate, dict(all_pass=False, gpu_executed=False))
            with self.assertRaisesRegex(ValueError, 'failed'):
                F.process_gate({})

    def test_source_or_reference_file_drift_is_rejected(self):
        path = self.root/'reference.bin'
        path.write_bytes(b'accepted')
        inputs = {str(path): F.C.sha(path)}
        F.rehash(inputs)
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'input drift'):
            F.rehash(inputs)

    def test_plan_drift_rejects_before_process_or_output_creation(self):
        for key in ['scope', 'command', 'input_sha256', 'reference_verification', 'previous_audits', 'contract']:
            current = copy.deepcopy(self.plan)
            current[key] = 'changed'
            with patch.object(F, 'Paths', return_value=self.paths), patch.object(F, 'prepare', return_value=current), patch.object(F, 'run_native') as native:
                with self.assertRaisesRegex(ValueError, 'plan drift'):
                    F.execute(self.case)
                native.assert_not_called()
                self.assertFalse(self.paths.work.exists())

    def test_one_raw_process_creates_archive_but_no_quality_decision(self):
        def raw(command, env, stdout, stderr):
            stdout.write_text('CPU fixture only')
            stderr.write_text('')
            return dict(returncode=0, timed_out=False)
        with patch.object(F, 'Paths', return_value=self.paths), patch.object(F, 'prepare', return_value=self.plan), patch.object(F, 'run_native', side_effect=raw) as native:
            result = F.execute(self.case)
        native.assert_called_once()
        self.assertTrue(result['complete'])
        self.assertEqual(result['classification'], 'RAW_CAPTURE_RETAINED_INDEPENDENT_AUDIT_REQUIRED')
        self.assertFalse(self.paths.scores.exists())
        self.assertEqual(set(A.A.archive_members(self.paths.archive)), {'plan.json', 'result.json'})
        A.A.validate_inventory(self.paths.work, F.R.read(self.paths.work/'result.json')['payload_sha256'])

    def test_operational_failure_retains_partial_and_stops_without_retry(self):
        def failed(command, env, stdout, stderr):
            stdout.write_text('partial CPU fixture')
            stderr.write_text('expected fixture failure')
            return dict(returncode=7, timed_out=False)
        with patch.object(F, 'Paths', return_value=self.paths), patch.object(F, 'prepare', return_value=self.plan), patch.object(F, 'run_native', side_effect=failed) as native:
            result = F.execute(self.case)
        native.assert_called_once()
        self.assertFalse(result['complete'])
        self.assertTrue(self.paths.archive.is_file())
        self.assertEqual((self.paths.work/'native.stdout.txt').read_text(), 'partial CPU fixture')
        with patch.object(F, 'Paths', return_value=self.paths):
            audit = A.audit(self.case, save=True)
            self.assertFalse(audit['correctness_evidence_valid'])
            self.assertEqual(audit, A.audit(self.case))
        with self.assertRaisesRegex(ValueError, 'STOP'):
            F.next_case({'c1-hwrt': audit})

    def test_real_cpu_subprocess_exit_and_stdout_are_retained(self):
        out, err = self.root/'stdout.txt', self.root/'stderr.txt'
        result = F.run_native([sys.executable, '-c', "import sys; print('CPU only'); sys.stderr.write('diagnostic'); sys.exit(7)"], dict(os.environ), out, err)
        self.assertEqual(result, dict(returncode=7, timed_out=False))
        self.assertEqual(out.read_text().strip(), 'CPU only')
        self.assertEqual(err.read_text(), 'diagnostic')

    def test_real_cpu_timeout_kills_process_and_preserves_partial_output(self):
        out, err = self.root/'stdout.txt', self.root/'stderr.txt'
        result = F.run_native([sys.executable, '-c', "import time; print('before timeout',flush=True); time.sleep(5)"], dict(os.environ), out, err, timeout=.2)
        self.assertTrue(result['timed_out'])
        self.assertNotEqual(result['returncode'], 0)
        self.assertIn('before timeout', out.read_text())

    def test_missing_terminal_or_changed_archive_rejects_independent_intake(self):
        with patch.object(F, 'Paths', return_value=self.paths):
            with self.assertRaisesRegex(ValueError, 'terminal proof incomplete'):
                A.audit(self.case)
        self.paths.work.mkdir()
        F.R.write_new(self.paths.work/'result.json', {})
        with self.paths.archive.open('xb') as handle:
            with tarfile.open(fileobj=handle, mode='w') as tar:
                tar.add(self.paths.plan, arcname='plan.json')
                tar.add(self.paths.plan, arcname='result.json')
        with patch.object(F, 'Paths', return_value=self.paths):
            with self.assertRaisesRegex(ValueError, 'archive/local'):
                A.audit(self.case)


class FullMapReplay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.p = SimpleNamespace(scores=Path(self.temp.name)/'scores')
        self.report = dict(classification='PASS', correctness_evidence_valid=True)
        self.arrays = {'quality-b2.direct.error.npy': np.zeros((180,320), dtype=np.float64),
                       'primary-b2.npz': {'gpu_hit': np.zeros(57600, dtype=bool), 'depth_error': np.zeros(57600, dtype=np.float64)}}
        A.save_or_replay(self.p, copy.deepcopy(self.report), self.arrays, True)

    def rehash_saved_file(self, name):
        path = self.p.scores/'result.json'
        r = F.R.read(path)
        r['derived_sha256'][name] = F.C.sha(self.p.scores/name)
        path.write_text(json.dumps(r))

    def test_full_array_replay_and_overwrite_refusal(self):
        result = A.save_or_replay(self.p, copy.deepcopy(self.report), self.arrays, False)
        self.assertTrue(result['correctness_evidence_valid'])
        with self.assertRaisesRegex(ValueError, 'no overwrite'):
            A.save_or_replay(self.p, copy.deepcopy(self.report), self.arrays, True)

    def test_missing_or_extra_full_map_is_rejected(self):
        (self.p.scores/'unregistered.bin').write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError, 'missing/extra'):
            A.save_or_replay(self.p, copy.deepcopy(self.report), self.arrays, False)

    def test_changed_error_even_with_updated_hash_is_rejected(self):
        name = 'quality-b2.direct.error.npy'
        changed = np.ones((180,320), dtype=np.float64)
        with (self.p.scores/name).open('wb') as handle: np.save(handle, changed)
        self.rehash_saved_file(name)
        with self.assertRaisesRegex(ValueError, 'error-map replay'):
            A.save_or_replay(self.p, copy.deepcopy(self.report), self.arrays, False)

    def test_identical_values_in_f32_do_not_substitute_for_f64_errors(self):
        name = 'quality-b2.direct.error.npy'
        with (self.p.scores/name).open('wb') as handle: np.save(handle, np.zeros((180,320), dtype=np.float32))
        self.rehash_saved_file(name)
        with self.assertRaisesRegex(ValueError, 'f64 error-map'):
            A.save_or_replay(self.p, copy.deepcopy(self.report), self.arrays, False)

    def test_changed_primary_even_with_updated_hash_is_rejected(self):
        name = 'primary-b2.npz'
        changed = copy.deepcopy(self.arrays[name])
        changed['gpu_hit'][12] = True
        with (self.p.scores/name).open('wb') as handle: np.savez(handle, **changed)
        self.rehash_saved_file(name)
        with self.assertRaisesRegex(ValueError, 'primary comparison'):
            A.save_or_replay(self.p, copy.deepcopy(self.report), self.arrays, False)


if __name__ == '__main__':
    unittest.main()
