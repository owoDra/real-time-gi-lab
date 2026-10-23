"""Control process retention/refusal tests use mocked processes; never launch GPU."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock,patch

import ddgi_control_step as F


class Controls(unittest.TestCase):
    def test_unregistered_and_exact_bounded_commands(self):
        with self.assertRaises(ValueError):F.paths('quality-auto')
        for name in F.CASES:
            cmd=F.command(name)
            self.assertEqual(cmd[cmd.index('--grid-side')+1],'4');self.assertEqual(cmd[cmd.index('--rays')+1],'128')
            self.assertEqual(cmd[cmd.index('--vertices')+1],'1' if name=='direct' else '8' if name=='scene-seven' else '2')

    def test_missing_plan_cannot_launch(self):
        with tempfile.TemporaryDirectory() as t,patch.object(F.R,'ROOT',Path(t)),patch.object(F.subprocess,'Popen') as native:
            with self.assertRaises(ValueError):F.execute('direct')
        native.assert_not_called()

    def test_prepared_drift_cannot_launch(self):
        with tempfile.TemporaryDirectory() as t,patch.object(F,'paths',return_value=(Path(t)/'plan',Path(t)/'work',Path(t)/'proof.tar')):
            plan=dict(name='direct',command=['old'],input_sha256={},previous_control_audit=None,reference_verification={})
            F.R.write_new(Path(t)/'plan',plan)
            with patch.object(F,'prepare',return_value=dict(plan,command=['changed'])),patch.object(F.subprocess,'Popen') as native:
                with self.assertRaises(ValueError):F.execute('direct')
            native.assert_not_called();self.assertFalse((Path(t)/'work').exists())

    def fake_run(self,timeout=False):
        with tempfile.TemporaryDirectory() as t,patch.object(F,'paths',return_value=(Path(t)/'plan',Path(t)/'work',Path(t)/'proof.tar')):
            plan=dict(name='direct',command=F.command('direct'),input_sha256={},previous_control_audit=None,reference_verification={})
            F.R.write_new(Path(t)/'plan',plan);native=Mock(returncode=-6,pid=123456)
            native.communicate.side_effect=[subprocess.TimeoutExpired('native',180),('partial','timeout')] if timeout else [('partial','failed')]
            with patch.object(F,'prepare',return_value=plan),patch.object(F.subprocess,'Popen',return_value=native) as launch,patch.object(F.os,'killpg') as kill:
                result=F.execute('direct');self.assertFalse(result['complete']);self.assertTrue((Path(t)/'proof.tar').is_file())
                self.assertEqual((Path(t)/'work/native.stdout.txt').read_text(),'partial')
                self.assertEqual(F.R.read(Path(t)/'work/result.json')['classification'],'OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY')
                with self.assertRaises(FileExistsError):F.execute('direct')
                self.assertEqual(launch.call_count,1)
                self.assertEqual(kill.call_count,int(timeout))

    def test_failed_process_preserved_no_retry(self):self.fake_run()
    def test_timed_out_process_preserved_no_retry(self):self.fake_run(True)

    def test_ineligible_previous_control_stops_preparation(self):
        import ddgi_control_audit as A
        with tempfile.TemporaryDirectory() as t,patch.object(F,'paths',return_value=(Path(t)/'plan',Path(t)/'work',Path(t)/'proof.tar')), \
             patch.object(F.R,'preflight',return_value=({'sha256':{}},{},{})),patch.object(F.R.P,'verify_reference',return_value={}), \
             patch.object(A,'audit',return_value={'semantic_pass':False}),patch.object(F.subprocess,'Popen') as native:
            with self.assertRaisesRegex(ValueError,'previous control'):F.prepare('black')
        native.assert_not_called()

if __name__=='__main__':unittest.main()
