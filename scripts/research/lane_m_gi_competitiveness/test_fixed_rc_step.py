"""RC acquisition guards, exact budget, and failure retention; mocked GPU process."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import fixed_rc_step as F

class FixedRCTests(unittest.TestCase):
    def test_named_command(self):
        c=F.Case('H02','software');cmd=F.command(c)
        for flag,value in [('--backend','software'),('--spp','512'),('--scenario','static'),('--direct-profile','ulp4')]:
            self.assertEqual(cmd[cmd.index(flag)+1],value)
        self.assertNotIn('--target-state',cmd)
    def test_unregistered_role(self):
        with self.assertRaises(ValueError):F.Case('H01','hwrt')
    def test_absent_plan_no_native(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(F.R,'ROOT',Path(tmp)), \
             patch.object(F.subprocess,'Popen') as native, self.assertRaises(ValueError):
            F.execute(F.Case('H01','vanilla'))
        native.assert_not_called()
    def test_drift_no_native(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(F.R,'ROOT',Path(tmp)):
            c=F.Case('H01','vanilla');c.plan.parent.mkdir(parents=True)
            plan={'scope':{'role':'vanilla'},'command':[],'references':{},'input_sha256':{}}
            F.R.write_new(c.plan,plan)
            with patch.object(F,'prepare',return_value={**plan,'command':['changed']}), \
                 patch.object(F.subprocess,'Popen') as native,self.assertRaises(ValueError):F.execute(c)
            native.assert_not_called()
    def test_native_failure_and_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(F.R,'ROOT',Path(tmp)), \
             patch.object(F.R,'BASE',Path(tmp)/'cases'):
            c=F.Case('H01','software');c.plan.parent.mkdir(parents=True)
            plan={'scope':{'cell':c.cell,'role':c.role},'command':F.command(c),'references':{},'input_sha256':{}}
            F.R.write_new(c.plan,plan);p=Mock(returncode=2);p.communicate.return_value=('partial','failure')
            with patch.object(F,'prepare',return_value=plan),patch.object(F.subprocess,'Popen',return_value=p) as native:
                self.assertFalse(F.execute(c)['complete']);self.assertTrue(c.archive.is_file())
                self.assertEqual((c.work/'native.stderr.txt').read_text(),'failure')
                with self.assertRaises(FileExistsError):F.execute(c)
                self.assertEqual(native.call_count,1)
                self.assertFalse(F.audit(c)['quality_evidence_valid'])

if __name__=='__main__':unittest.main()
