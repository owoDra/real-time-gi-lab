"""Mock-only GPU handoff safety checks; no Vulkan/native execution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import first_pt_quality as F


class FirstPTSafety(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(dir=F.R.ROOT / 'out')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for name, value in [('PLAN', root / 'plan.json'), ('WORK', root / 'case'),
                            ('ARCHIVE', root / 'result.tar')]:
            p = patch.object(F, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_missing_plan_never_dispatches(self):
        with patch.object(F.subprocess, 'Popen') as native:
            with self.assertRaisesRegex(ValueError, 'prepare and review'):
                F.execute()
            native.assert_not_called()

    def test_plan_drift_never_dispatches(self):
        F.R.write_new(F.PLAN, {'command': ['original'], 'input_sha256': {'old': 'sha'}})
        with patch.object(F, 'prepare', return_value={'command': ['changed'], 'input_sha256': {}}), \
             patch.object(F.subprocess, 'Popen') as native:
            with self.assertRaisesRegex(ValueError, 'plan drifted'):
                F.execute()
            native.assert_not_called()
            self.assertFalse(F.WORK.exists())

    def test_failed_native_keeps_evidence_and_refuses_retry(self):
        plan = {'command': F.command(), 'input_sha256': {}}
        F.R.write_new(F.PLAN, plan)
        process = Mock(returncode=-6)
        process.communicate.return_value = ('partial stdout', 'failure stderr')
        with patch.object(F, 'prepare', return_value=plan), \
             patch.object(F.subprocess, 'Popen', return_value=process) as native:
            result = F.execute()
            self.assertFalse(result['complete'])
            self.assertEqual(json.loads((F.WORK / 'result.json').read_text())['returncode'], -6)
            self.assertEqual((F.WORK / 'native.stderr.txt').read_text(), 'failure stderr')
            self.assertTrue(F.ARCHIVE.is_file())
            with self.assertRaises(FileExistsError):
                F.execute()
            self.assertEqual(native.call_count, 1)


if __name__ == '__main__':
    unittest.main()
