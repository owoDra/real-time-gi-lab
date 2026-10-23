"""Dynamic GPU process controls, mocked only; no Vulkan initialization."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock,patch
import ddgi_dynamic_step as F


class DynamicProcess(unittest.TestCase):
    def test_fixed_family_and_transition_command(self):
        self.assertEqual(len(F.CASES),8)
        with self.assertRaises(ValueError):F.paths('light-reuse-b8')
        for name in F.CASES:
            kind,mode,depth=F.split(name);command=F.command(name)
            self.assertEqual(command[command.index('--vertices')+1],str(depth))
            self.assertEqual('--target-state' in command,mode=='transition')
            if mode=='transition':self.assertEqual(command[command.index('--history-policy')+1],'reset-all')

    def test_missing_plan_cannot_dispatch(self):
        with tempfile.TemporaryDirectory() as t,patch.object(F,'paths',return_value=(Path(t)/'plan',Path(t)/'work',Path(t)/'proof')),patch.object(F.subprocess,'Popen') as native:
            with self.assertRaises(ValueError):F.execute(F.CASES[0])
        native.assert_not_called()

    def test_drift_stops_before_dispatch(self):
        with tempfile.TemporaryDirectory() as t,patch.object(F,'paths',return_value=(Path(t)/'plan',Path(t)/'work',Path(t)/'proof')):
            old={'name':F.CASES[0],'command':[],'input_sha256':{},'previous_unit_audit':None,'state_lock':{},'deterministic_direct':{}}
            F.R.write_new(Path(t)/'plan',old)
            with patch.object(F,'prepare',return_value=dict(old,input_sha256={'changed':'digest'})),patch.object(F.subprocess,'Popen') as native:
                with self.assertRaises(ValueError):F.execute(F.CASES[0])
            native.assert_not_called();self.assertFalse((Path(t)/'work').exists())

    def failed(self,timeout=False):
        with tempfile.TemporaryDirectory(dir=F.R.ROOT/'out') as t,patch.object(F,'paths',return_value=(Path(t)/'plan',Path(t)/'work',Path(t)/'proof.tar')):
            name=F.CASES[0];plan={'name':name,'command':F.command(name),'input_sha256':{},'previous_unit_audit':None,'state_lock':{},'deterministic_direct':{}}
            F.R.write_new(Path(t)/'plan',plan);process=Mock(returncode=-6,pid=123456)
            process.communicate.side_effect=[subprocess.TimeoutExpired('native',180),('partial','timeout')] if timeout else [('partial','failed')]
            with patch.object(F,'prepare',return_value=plan),patch.object(F.subprocess,'Popen',return_value=process) as native,patch.object(F.os,'killpg') as kill:
                r=F.execute(name);self.assertFalse(r['complete']);self.assertTrue((Path(t)/'proof.tar').is_file())
                self.assertEqual((Path(t)/'work/native.stdout.txt').read_text(),'partial')
                self.assertEqual(F.R.read(Path(t)/'work/result.json')['classification'],'OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY')
                with self.assertRaises(FileExistsError):F.execute(name)
                self.assertEqual(native.call_count,1);self.assertEqual(kill.call_count,int(timeout))

    def test_failed_native_retained_no_retry(self):self.failed()
    def test_timeout_retained_no_retry(self):self.failed(True)

if __name__=='__main__':unittest.main()
