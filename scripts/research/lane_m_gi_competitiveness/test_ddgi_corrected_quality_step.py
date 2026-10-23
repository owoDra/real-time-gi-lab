"""012 CPU fixtures/mocks for stop gates, retained failures and copy corruption.

The native fixture is a retained grid4 correctness control, never a new quality
acquisition or an indirect reference score. All process launches are mocked.
"""
from contextlib import contextmanager
import copy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import ddgi_corrected_quality_step as F
import ddgi_corrected_quality_audit as A


class AdmissionAndOrder(unittest.TestCase):
    def test_all_losses_exact_eighteen_and_exhaustion(self):
        reports = {}
        for cell, depth in F.TARGETS:
            for rung in range(3):
                c = F.Case(cell, depth, rung)
                self.assertEqual(F.next_case(reports), c)
                reports[c.name] = dict(quality_evidence_valid=True, classification='QUALITY_FAIL')
        self.assertIsNone(F.next_case(reports))
        self.assertEqual(len(reports), 18)

    def test_first_pass_skips_remaining_rungs_and_rejects_extra(self):
        reports = {}
        for cell, depth in F.TARGETS:
            c = F.Case(cell, depth, 0)
            self.assertEqual(F.next_case(reports), c)
            reports[c.name] = dict(quality_evidence_valid=True, classification='PASS')
        self.assertIsNone(F.next_case(reports))
        reports['h01-b2-q1'] = dict(quality_evidence_valid=True, classification='QUALITY_FAIL')
        with self.assertRaises(ValueError):
            F.next_case(reports)

    def test_invalid_partial_missing_or_skipped_results_cannot_escalate(self):
        for row in ({}, dict(quality_evidence_valid=False, classification='QUALITY_FAIL'),
                    dict(quality_evidence_valid=True, classification='OPERATIONAL_FAILURE_RETAINED')):
            with self.assertRaises(ValueError):
                F.next_case({'h01-b2-q0': row})
        with self.assertRaises(ValueError):
            F.next_case({'h01-b8-q0': dict(quality_evidence_valid=True, classification='PASS')})

    def test_qualification_requires_exact_twenty_passes(self):
        proof = dict(registered_requalification_complete=True, all_existing_evidence_valid=True,
                     controls_pass=20, native_acquisitions=20, controls_required=20,
                     rows=[dict(name=c.name, audit=dict(semantic_pass=True, classification='BORDER_CONTROL_PASS'))
                           for c in F.B.CASES])
        F.validate_qualification_proof(proof)
        for key in ('registered_requalification_complete', 'all_existing_evidence_valid', 'controls_pass', 'native_acquisitions'):
            bad = copy.deepcopy(proof)
            bad[key] = False if type(bad[key]) is bool else 19
            with self.assertRaises(ValueError):
                F.validate_qualification_proof(bad)
        for change in ('missing', 'order', 'failed'):
            bad = copy.deepcopy(proof)
            if change == 'missing':
                bad['rows'].pop()
            elif change == 'order':
                bad['rows'].reverse()
            else:
                bad['rows'][19]['audit']['semantic_pass'] = False
            with self.assertRaises(ValueError):
                F.validate_qualification_proof(bad)

    def test_withdrawn_runtime_gate_stops_before_any_process(self):
        with patch.object(F.R, 'read', return_value={'experiments': [dict(ddgi_border_runtime_requalified=False)]}), \
                patch.object(F.subprocess, 'Popen') as native:
            with self.assertRaisesRegex(ValueError, 'not admitted'):
                F.requalification({})
            native.assert_not_called()

    def test_inclusive_quality_gates_and_invalid_metrics(self):
        d = dict(total=dict(nrmse=.05), indirect=dict(nrmse=.10, signed_sum_bias=-.05))
        self.assertEqual(A.classify(d), 'PASS')
        for component, field, value in [('total', 'nrmse', np.nextafter(.05, 1)),
                                        ('indirect', 'nrmse', np.nextafter(.10, 1)),
                                        ('indirect', 'signed_sum_bias', np.nextafter(-.05, -1))]:
            bad = copy.deepcopy(d)
            bad[component][field] = value
            self.assertEqual(A.classify(bad), 'QUALITY_FAIL')
        for component, field in [('total', 'nrmse'), ('indirect', 'nrmse'), ('indirect', 'signed_sum_bias')]:
            for value in (None, float('nan'), float('inf'), -float('inf')):
                bad = copy.deepcopy(d)
                bad[component][field] = value
                with self.assertRaises(ValueError):
                    A.classify(bad)

    def test_copy_units_before_current_readback_all_budgets(self):
        for side, rays in F.BUDGETS:
            for depth in (2, 8):
                labels = A.unit_labels(side, rays, depth)
                self.assertEqual(len(labels), 2 + (depth - 1) * (13 + side**3 * rays // 4096))
                for k in range(depth - 1):
                    p = f'stage-{k}'
                    self.assertLess(labels.index(p + '-sdk-blend'), labels.index('readback-' + p + '-pre-border-1'))
                    self.assertLess(labels.index('readback-' + p + '-pre-border-2'), labels.index(p + '-border-irradiance'))
                    self.assertLess(labels.index(p + '-border-distance'), labels.index('readback-' + p + '-current-0'))


@contextmanager
def isolated():
    with tempfile.TemporaryDirectory(dir=F.R.ROOT / 'out') as t:
        root = Path(t)
        with patch.object(F.R, 'ROOT', root), patch.object(F.C, 'ROOT', root / 'work'):
            (root / 'out').mkdir()
            yield F.Case('H01', 2, 0)


def plan(case):
    return dict(schema='m001-ddgi-corrected-quality-plan/1', scope=case.scope, command=F.command(case),
                input_sha256={}, source_commit='synthetic-cpu-process-test', reference_verification={},
                previous_quality_audits={}, native_cpu_contract={}, requalification={},
                unblinded_cohort=True, gpu_executed=False, accepted_timing=False)


class SingleProcess(unittest.TestCase):
    def test_missing_plan_never_launches(self):
        with isolated() as c, patch.object(F.subprocess, 'Popen') as native:
            with self.assertRaises(ValueError):
                F.execute(c)
            native.assert_not_called()

    def test_plan_scope_source_reference_contract_history_drift_stops_before_launch(self):
        for key in ('scope', 'command', 'input_sha256', 'reference_verification', 'previous_quality_audits', 'native_cpu_contract', 'requalification'):
            with isolated() as c:
                p = plan(c)
                F.R.write_new(c.plan, p)
                changed = dict(p)
                changed[key] = 'changed'
                with patch.object(F, 'prepare', return_value=changed), patch.object(F.subprocess, 'Popen') as native:
                    with self.assertRaises(ValueError):
                        F.execute(c)
                    native.assert_not_called()
                    self.assertFalse(c.work.exists())

    def test_existing_work_or_tar_refused(self):
        for kind in ('work', 'archive'):
            with isolated() as c, patch.object(F.subprocess, 'Popen') as native:
                c.work.mkdir(parents=True) if kind == 'work' else c.archive.write_bytes(b'retained')
                with self.assertRaises(ValueError):
                    F.prepare(c)
                native.assert_not_called()

    def run_mock(self, kind):
        with isolated() as c:
            p = plan(c)
            F.R.write_new(c.plan, p)
            process = Mock(returncode=5, pid=123456)
            process.communicate.side_effect = ([subprocess.TimeoutExpired('native', 180), ('partial', 'timeout')]
                                              if kind == 'timeout' else [('partial', 'failed')])
            with patch.object(F, 'prepare', return_value=p), patch.object(F.subprocess, 'Popen') as launch, patch.object(F.os, 'killpg') as kill:
                if kind == 'launch':
                    launch.side_effect = OSError('CPU mock launch failure')
                else:
                    launch.return_value = process
                r = F.execute(c)
                self.assertFalse(r['complete'])
                self.assertEqual(launch.call_count, 1)
                self.assertEqual(kill.call_count, int(kind == 'timeout'))
                terminal = F.R.read(c.work / 'result.json')
                self.assertEqual(terminal['gpu_executed'], kind != 'launch')
                self.assertFalse(terminal['quality_admission'])
                self.assertEqual(A.audit(c)['classification'], 'OPERATIONAL_FAILURE_RETAINED')
                self.assertEqual(launch.call_count, 1)
            with patch.object(F.subprocess, 'Popen') as no_retry:
                with self.assertRaises(ValueError):
                    F.execute(c)
                no_retry.assert_not_called()

    def test_native_failure_preserved_without_escalation(self):
        self.run_mock('native')

    def test_timeout_terminates_and_preserves_partial(self):
        self.run_mock('timeout')

    def test_failed_launch_does_not_claim_gpu_execution(self):
        self.run_mock('launch')


class NativeCopyAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=F.R.ROOT / 'out')
        self.root = Path(self.temp.name)
        old = F.B.get_case('static-scene-one').work / 'capture'
        shutil.copytree(old, self.root / 'capture')
        F.R.write_new(self.root / 'contract.json', dict(contract=F.R.read(self.root / 'capture/cpu-contract.json')))
        F.R.write_new(self.root / 'plan.json', dict(native_cpu_contract=dict(path=str(self.root / 'contract.json'))))
        self.case = SimpleNamespace(work=self.root, plan=self.root / 'plan.json', budget=(4, 128), depth=2, cell='H01')

    def tearDown(self):
        self.temp.cleanup()

    def test_retained_correctness_fixture_passes_all_native_predicates_without_quality_scoring(self):
        r = A.native_report(self.case)
        self.assertEqual(len(r['copies']), 2)
        self.assertTrue(r['full_copy_exact'])
        self.assertTrue(r['owned_memory']['teardown_zero'])

    def test_missing_pre_copy_capture_rejected(self):
        (self.root / 'capture/stage-0-pre-border-2.f32').unlink()
        with self.assertRaises(FileNotFoundError):
            A.native_report(self.case)

    def test_post_copy_corrupt_border_rejected(self):
        p = self.root / 'capture/stage-0-current-2.f32'
        a = np.fromfile(p, dtype='<f4')
        a[0] += 1
        a.tofile(p)
        with self.assertRaises(ValueError):
            A.native_report(self.case)

    def test_post_copy_changed_interior_rejected(self):
        p = self.root / 'capture/stage-0-current-1.f32'
        a = np.fromfile(p, dtype='<f4').reshape(4, 32, 32, 4)
        a[0, 3, 3, 0] += 1
        a.tofile(p)
        with self.assertRaises(ValueError):
            A.native_report(self.case)

    def test_nonfinite_pre_copy_rejected(self):
        p = self.root / 'capture/stage-0-pre-border-2.f32'
        a = np.fromfile(p, dtype='<f4')
        a[34] = float('nan')
        a.tofile(p)
        with self.assertRaises(ValueError):
            A.native_report(self.case)

    def test_missing_gpu_unit_rejected(self):
        p = self.root / 'capture/dispatches.jsonl'
        p.write_text('\n'.join(p.read_text().splitlines()[:-2]) + '\n')
        with self.assertRaises(ValueError):
            A.native_report(self.case)

    def test_contaminated_initial_history_rejected(self):
        p = self.root / 'capture/stage-0-previous-1.f32'
        a = np.fromfile(p, dtype='<f4')
        a[0] = -0.0
        a.tofile(p)
        with self.assertRaises(ValueError):
            A.native_report(self.case)


if __name__ == '__main__':
    unittest.main()
