"""011 synthetic CPU fixtures/process mocks; never GPU evidence or admission."""
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import ddgi_border_cases as F
import ddgi_border_step as Step
import ddgi_border_requalification_audit as A
import ddgi_border_audit as Border


class ProcessOrder(unittest.TestCase):
    def test_exact_twenty_progression_requires_every_pass(self):
        reports = {}
        for c in F.CASES:
            Step.validate_previous(c, reports)
            reports[c.name] = dict(semantic_pass=True, classification='BORDER_CONTROL_PASS')

    def test_missing_failure_or_quality_loss_cannot_advance(self):
        for row in ({}, dict(semantic_pass=False, classification='BORDER_CONTROL_PASS'),
                    dict(semantic_pass=True, classification='QUALITY_FAIL'),
                    dict(semantic_pass=False, classification='OPERATIONAL_FAILURE_RETAINED')):
            with self.assertRaises(ValueError):
                Step.validate_previous(F.CASES[1], {F.CASES[0].name: row})
        with self.assertRaises(ValueError):
            Step.validate_previous(F.CASES[1], {})

    def test_extra_or_reordered_predecessors_rejected(self):
        row = dict(semantic_pass=True, classification='BORDER_CONTROL_PASS')
        with self.assertRaises(ValueError):
            Step.validate_previous(F.CASES[0], {F.CASES[0].name: row})
        with self.assertRaises(ValueError):
            Step.validate_previous(F.CASES[2], {F.CASES[1].name: row, F.CASES[0].name: row})

    def test_fixed_gpu_units_and_copy_before_current_capture(self):
        for c in F.CASES:
            labels = A.unit_labels(c)
            per_stage = 13 + c.side**3 * c.rays // 4096 if c.mode == 'scene' else 14
            self.assertEqual(len(labels), 2 + (c.depth - 1) * per_stage)
            self.assertEqual(len(labels), len(set(labels)))
            for k in range(c.depth - 1):
                p = f'stage-{k}'
                self.assertLess(labels.index(p + '-sdk-blend'), labels.index('readback-' + p + '-pre-border-1'))
                self.assertLess(labels.index('readback-' + p + '-pre-border-2'), labels.index(p + '-border-irradiance'))
                self.assertLess(labels.index(p + '-border-distance'), labels.index('readback-' + p + '-current-0'))
        self.assertEqual(len(A.unit_labels(F.CASES[0])), 2)

    def test_missing_reordered_extra_or_over_guard_unit_rejected(self):
        labels = A.unit_labels(F.CASES[4])
        events = [x for label in labels for x in (dict(event='begin', unit=label), dict(event='complete', unit=label, gpu_us_diagnostic=1.0))]
        self.assertEqual(A.Q.check_units(events, labels)['completed_gpu_units'], len(labels))
        for changed in (events[:-1], events + events[:2], events[2:4] + events[:2] + events[4:]):
            with self.assertRaises(ValueError):
                A.Q.check_units(changed, labels)
        for value in (-1, 250000.1, float('nan'), float('inf')):
            changed = [dict(x) for x in events]
            changed[1]['gpu_us_diagnostic'] = value
            with self.assertRaises(ValueError):
                A.Q.check_units(changed, labels)


@contextmanager
def isolated_case():
    with tempfile.TemporaryDirectory(dir=F.R.ROOT / 'out') as t:
        root = Path(t)
        with patch.object(F.R, 'ROOT', root), patch.object(F, 'WORK', root / 'work'):
            (root / 'out').mkdir()
            yield F.CASES[0]


def plan_for(case):
    return dict(name=case.name, case=asdict(case), command=F.command(case), input_sha256={}, source_commit='synthetic-cpu-process-test',
                reference_verification={}, dynamic_states={}, dynamic_direct_controls={}, previous_control_audits={},
                quality_scoring=False, accepted_timing=False, gpu_executed=False)


class SingleProcess(unittest.TestCase):
    def test_missing_plan_never_starts_process(self):
        with isolated_case() as c, patch.object(Step.subprocess, 'Popen') as native:
            with self.assertRaises(ValueError):
                Step.execute(c)
            native.assert_not_called()
            self.assertFalse(c.work.exists())

    def test_plan_drift_never_starts_or_creates_work(self):
        with isolated_case() as c:
            plan = plan_for(c)
            F.R.write_new(c.plan, plan)
            with patch.object(Step, 'prepare', return_value=dict(plan, input_sha256={'changed': 'hash'})), patch.object(Step.subprocess, 'Popen') as native:
                with self.assertRaises(ValueError):
                    Step.execute(c)
                native.assert_not_called()
                self.assertFalse(c.work.exists())

    def test_existing_work_or_tar_or_later_work_refused(self):
        for mode in ('work', 'archive', 'later'):
            with isolated_case() as c, patch.object(Step.subprocess, 'Popen') as native:
                if mode == 'work':
                    c.work.mkdir(parents=True)
                elif mode == 'archive':
                    c.archive.write_bytes(b'retain')
                else:
                    F.CASES[1].work.mkdir(parents=True)
                with self.assertRaises(ValueError):
                    Step.prepare(c)
                native.assert_not_called()

    def failed_attempt(self, timeout=False, launch_failure=False):
        with isolated_case() as c:
            plan = plan_for(c)
            F.R.write_new(c.plan, plan)
            process = Mock(returncode=-6, pid=123456)
            process.communicate.side_effect = [subprocess.TimeoutExpired('native', 180), ('partial', 'timeout')] if timeout else [('partial', 'failed')]
            with patch.object(Step, 'prepare', return_value=plan), patch.object(Step.subprocess, 'Popen', side_effect=OSError('synthetic launch failure') if launch_failure else None, return_value=process) as native, patch.object(Step.os, 'killpg') as kill:
                result = Step.execute(c)
                self.assertFalse(result['complete'])
                self.assertEqual(native.call_count, 1)
                self.assertEqual(kill.call_count, int(timeout))
                stored = F.R.read(c.work / 'result.json')
                self.assertEqual(stored['gpu_executed'], not launch_failure)
                self.assertFalse(stored['quality_admission'])
                audit = A.audit(c)
                self.assertEqual(audit['classification'], 'OPERATIONAL_FAILURE_RETAINED')
                self.assertFalse(audit['semantic_pass'])
                self.assertEqual(set(A.archive_members(c.archive)), {'plan.json', 'result.json'})
                if not launch_failure:
                    self.assertEqual((c.work / 'native.stdout.txt').read_text(), 'partial')
                return True

    def test_native_failure_retains_partial_and_no_admission(self):
        self.assertTrue(self.failed_attempt())

    def test_timeout_terminates_named_process_and_retains_partial(self):
        self.assertTrue(self.failed_attempt(timeout=True))

    def test_launch_failure_does_not_claim_gpu_execution(self):
        self.assertTrue(self.failed_attempt(launch_failure=True))

    def test_success_launches_only_once_and_requires_independent_audit(self):
        with isolated_case() as c:
            plan = plan_for(c)
            F.R.write_new(c.plan, plan)
            process = Mock(returncode=0)
            def complete(timeout):
                (c.work / 'capture').mkdir()
                F.R.write_new(c.work / 'capture/complete.json', dict(capture_complete=True))
                return 'synthetic complete', ''
            process.communicate.side_effect = complete
            with patch.object(Step, 'prepare', return_value=plan), patch.object(Step.subprocess, 'Popen', return_value=process) as native:
                report = Step.execute(c)
                self.assertTrue(report['complete'])
                self.assertEqual(native.call_count, 1)
                native.assert_called_once()
                stored = F.R.read(c.work / 'result.json')
                self.assertEqual(stored['classification'], 'RAW_BORDER_CONTROL_RETAINED_AUDIT_REQUIRED')
                self.assertFalse(stored['semantic_admission'])
                self.assertFalse(stored['quality_admission'])

    def test_changed_partial_inventory_is_rejected(self):
        with isolated_case() as c:
            plan = plan_for(c)
            F.R.write_new(c.plan, plan)
            process = Mock(returncode=2)
            process.communicate.return_value = 'partial', 'failed'
            with patch.object(Step, 'prepare', return_value=plan), patch.object(Step.subprocess, 'Popen', return_value=process):
                Step.execute(c)
            (c.work / 'native.stderr.txt').write_text('changed')
            with self.assertRaises(ValueError):
                A.audit(c)


class SyntheticNativeFrame(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=F.R.ROOT / 'out')
        self.path = Path(self.temp.name) / 'synthetic-frame'
        self.case = F.get_case('static-scene-one')
        self.old = A.old_work(self.case) / 'capture'
        shutil.copytree(self.old, self.path)
        cfg = F.R.read(self.path / 'configuration.json')
        for j, tile in ((1, 8), (2, 16)):
            a = A.atlas(self.path / f'stage-0-current-{j}.f32', cfg['images'][j])
            for y, x, _, _ in Border.border_map(tile):
                a[:, y::tile, x::tile, :] = 0
            a.tofile(self.path / f'stage-0-pre-border-{j}.f32')
        # Explicit synthetic completion journal. This fixture is never a GPU record.
        events = [x for label in A.unit_labels(self.case) for x in (dict(event='begin', unit=label), dict(event='complete', unit=label, gpu_us_diagnostic=1))]
        (self.path / 'dispatches.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in events))

    def tearDown(self):
        self.temp.cleanup()

    def check(self):
        return A.frame_report(self.case, self.path, F.SOURCE, self.old)

    def test_explicit_synthetic_frame_exercises_physical_and_full_copy_predicates(self):
        r = self.check()
        self.assertEqual(len(r['copies']), 2)
        self.assertTrue(all(x['full_copy_exact'] for x in r['copies']))
        self.assertFalse(r['quality_scoring'])

    def test_missing_pre_copy_capture_is_rejected(self):
        (self.path / 'stage-0-pre-border-2.f32').unlink()
        with self.assertRaises(FileNotFoundError):
            self.check()

    def test_corrupt_post_copy_border_is_rejected(self):
        p = self.path / 'stage-0-current-2.f32'
        a = np.fromfile(p, dtype='<f4')
        a[0] += 1
        a.tofile(p)
        with self.assertRaises(ValueError):
            self.check()

    def test_changed_post_copy_interior_is_rejected(self):
        p = self.path / 'stage-0-current-1.f32'
        a = np.fromfile(p, dtype='<f4').reshape(4, 32, 32, 4)
        a[0, 3, 3, 0] += 1
        a.tofile(p)
        with self.assertRaises(ValueError):
            self.check()


if __name__ == '__main__':
    unittest.main()
