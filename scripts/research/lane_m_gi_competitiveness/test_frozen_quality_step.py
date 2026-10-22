"""Frozen budget order and evidence retention tests; mocked native process only."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import frozen_quality_step as F

class FrozenSteps(unittest.TestCase):
    def test_reject_unregistered_budget_depth_and_repeat(self):
        for args in [('H02', 2, 8), ('H02', 3, 1), ('H04', 2, 1),
                     ('H01', 2, 1), ('H02', 2, 4, 'dense-rc')]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                F.Case(*args)

    def test_exact_named_command(self):
        c = F.Case('H02', 8, 64)
        cmd = F.command(c)
        self.assertEqual(cmd[cmd.index('--vertices') + 1], '8')
        self.assertEqual(cmd[cmd.index('--spp') + 1], '64')
        self.assertIn('M001-H02-hwrt', str(cmd))

    def test_first_failure_required_for_next(self):
        c = F.Case('H01', 2, 4)
        for outcome, valid in [('PASS', True), ('QUALITY_FAIL', False), ('OPERATIONAL_FAILURE', False)]:
            with patch.object(F.A, 'audit', return_value={'quality_evidence_valid': valid, 'classification': outcome}), \
                 self.assertRaises(ValueError):
                F.previous_audit(c)
        with patch.object(F.A, 'audit', return_value={'quality_evidence_valid': True,
                          'classification': 'QUALITY_FAIL', 'result_sha256': 'digest'}):
            self.assertEqual(F.previous_audit(c)['spp'], 1)

    def test_missing_prior_cannot_skip_ladder(self):
        import audit_quality_step as A
        with patch.object(A, 'audit', side_effect=ValueError('missing previous')) as audit, \
             self.assertRaisesRegex(ValueError, 'missing previous'):
            F.previous_audit(F.Case('H03', 8, 256))
        self.assertEqual(audit.call_args.args[0].spp, 64)

    def test_missing_plan_never_launches(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(F.R, 'ROOT', Path(tmp)), \
             patch.object(F.subprocess, 'Popen') as native, self.assertRaises(ValueError):
            F.execute(F.Case('H02', 2, 1))
        native.assert_not_called()

    def test_failed_native_retained_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(F.R, 'ROOT', Path(tmp)), \
             patch.object(F.R, 'BASE', Path(tmp) / 'cases'):
            c = F.Case('H02', 2, 1)
            c.PLAN.parent.mkdir(parents=True)
            plan = {'command': F.command(c), 'input_sha256': {}, 'scope': {}, 'previous_budget_audit': None}
            F.R.write_new(c.PLAN, plan)
            process = Mock(returncode=-6)
            process.communicate.return_value = ('partial', 'error')
            with patch.object(F, 'prepare', return_value=plan), \
                 patch.object(F.subprocess, 'Popen', return_value=process) as native:
                self.assertFalse(F.execute(c)['complete'])
                self.assertTrue(c.ARCHIVE.is_file())
                self.assertEqual((c.WORK / 'native.stderr.txt').read_text(), 'error')
                with self.assertRaises(FileExistsError):
                    F.execute(c)
                self.assertEqual(native.call_count, 1)

if __name__ == '__main__':
    unittest.main()
