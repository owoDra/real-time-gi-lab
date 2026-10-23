"""010 stop/order/guard, independent native-data corruption tests; no GPU dispatch."""
import copy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import tempfile
import subprocess
import unittest
from unittest.mock import Mock,patch

import ddgi_quality_step as F
import ddgi_quality_audit as A


class QualityOrder(unittest.TestCase):
    def test_unregistered_cases_refused(self):
        for args in [('H04',2,0),('H01',3,0),('H01',2,3),('H01',2,-1),('H01',2,True)]:
            with self.assertRaises(ValueError):F.Case(*args)

    def test_all_losses_exact18_order_and_exhaustion(self):
        reports={}
        for cell,depth in F.TARGETS:
            for rung in range(3):
                case=F.Case(cell,depth,rung);self.assertEqual(F.next_case(reports),case)
                reports[case.name]={'quality_evidence_valid':True,'classification':'QUALITY_FAIL'}
        self.assertIsNone(F.next_case(reports));self.assertEqual(len(reports),18)

    def test_first_pass_skips_remaining_budgets(self):
        reports={}
        for cell,depth in F.TARGETS:
            case=F.Case(cell,depth,0);self.assertEqual(F.next_case(reports),case)
            reports[case.name]={'quality_evidence_valid':True,'classification':'PASS'}
        self.assertIsNone(F.next_case(reports))
        reports['h01-b2-q1']={'quality_evidence_valid':True,'classification':'QUALITY_FAIL'}
        with self.assertRaises(ValueError):F.next_case(reports)

    def test_partial_invalid_or_skip_cannot_escalate(self):
        for row in [{'quality_evidence_valid':False,'classification':'QUALITY_FAIL'},
                    {'quality_evidence_valid':True,'classification':'OPERATIONAL_FAILURE'},{}]:
            with self.assertRaises(ValueError):F.next_case({'h01-b2-q0':row})
        with self.assertRaises(ValueError):F.next_case({'h01-b8-q0':{'quality_evidence_valid':True,'classification':'PASS'}})

    def test_commands_are_single_fresh_registered_budget(self):
        for rung,(side,rays) in enumerate(F.BUDGETS):
            c=F.Case('H03',8,rung);cmd=F.command(c)
            self.assertEqual(cmd[cmd.index('--grid-side')+1],str(side));self.assertEqual(cmd[cmd.index('--rays')+1],str(rays))
            self.assertNotIn('--target-state',cmd);self.assertNotIn('--cpu-check',cmd)
            self.assertEqual(len(A.unit_labels(side,rays,8)),2+7*(9+side**3*rays//4096))

    def test_frozen_quality_boundaries(self):
        components={'total':{'nrmse':.05},'indirect':{'nrmse':.1,'signed_sum_bias':-.05}}
        self.assertTrue(A.quality_pass(components))
        for c,k,v in [('total','nrmse',.05000000001),('indirect','nrmse',.10000000001),('indirect','signed_sum_bias',-.05000000001),('indirect','nrmse',None)]:
            d=copy.deepcopy(components);d[c][k]=v;self.assertFalse(A.quality_pass(d))


class QualityProcess(unittest.TestCase):
    def test_missing_plan_no_gpu(self):
        with tempfile.TemporaryDirectory(dir=F.R.ROOT/'out') as t,patch.object(F.R,'ROOT',Path(t)),patch.object(F.subprocess,'Popen') as native:
            with self.assertRaises(ValueError):F.execute(F.Case('H01',2,0))
            native.assert_not_called()

    def test_plan_drift_no_gpu_or_work(self):
        with tempfile.TemporaryDirectory(dir=F.R.ROOT/'out') as t,patch.object(F.R,'ROOT',Path(t)),patch.object(F,'ROOT',Path(t)/'work'):
            c=F.Case('H01',2,0);c.plan.parent.mkdir();plan={'scope':c.scope,'command':F.command(c),'input_sha256':{},'reference_verification':{},'previous_quality_audits':{},'native_cpu_contract':{},'control_result_sha256':{}}
            F.R.write_new(c.plan,plan)
            with patch.object(F,'prepare',return_value=dict(plan,input_sha256={'changed':'digest'})),patch.object(F.subprocess,'Popen') as native:
                with self.assertRaises(ValueError):F.execute(c)
                native.assert_not_called();self.assertFalse(c.work.exists())

    def failure(self,timeout):
        with tempfile.TemporaryDirectory(dir=F.R.ROOT/'out') as t,patch.object(F.R,'ROOT',Path(t)),patch.object(F,'ROOT',Path(t)/'work'):
            c=F.Case('H01',2,0);c.plan.parent.mkdir();plan={'scope':c.scope,'command':F.command(c),'input_sha256':{},'reference_verification':{},'previous_quality_audits':{},'native_cpu_contract':{},'control_result_sha256':{}}
            F.R.write_new(c.plan,plan);process=Mock(returncode=-6,pid=123456)
            process.communicate.side_effect=[subprocess.TimeoutExpired('native',180),('partial','timeout')] if timeout else [('partial','failed')]
            with patch.object(F,'prepare',return_value=plan),patch.object(F.subprocess,'Popen',return_value=process) as native,patch.object(F.os,'killpg') as kill:
                self.assertFalse(F.execute(c)['complete']);self.assertEqual(native.call_count,1);self.assertEqual(kill.call_count,int(timeout))
                self.assertEqual(A.audit(c)['classification'],'OPERATIONAL_FAILURE_RETAINED')
                self.assertEqual((c.work/'native.stdout.txt').read_text(),'partial')
                with self.assertRaises(FileExistsError):F.execute(c)
                self.assertEqual(native.call_count,1)

    def test_failed_process_evidence_retained(self):self.failure(False)
    def test_timeout_evidence_retained(self):self.failure(True)


class IndependentNativeAudit(unittest.TestCase):
    """Retained4^3 control is a CPU-only fixture, never an010 budget acquisition."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=F.R.ROOT/'out');self.root=Path(self.temp.name)
        shutil.copytree(F.D.S.paths('scene-one')[1]/'capture',self.root/'capture')
        F.R.write_new(self.root/'contract-receipt.json',{'contract':F.R.read(self.root/'capture/cpu-contract.json')})
        F.R.write_new(self.root/'plan.json',{'native_cpu_contract':{'path':str(self.root/'contract-receipt.json')}})
        self.case=SimpleNamespace(work=self.root,plan=self.root/'plan.json',budget=(4,128),depth=2,cell='H01')

    def tearDown(self):self.temp.cleanup()

    def change_json(self,name,change):
        p=self.root/'capture'/name;d=F.R.read(p);change(d);p.write_text(json.dumps(d))

    def test_original_fixture_all_native_contracts_pass(self):
        r=A.native_report(self.case);self.assertEqual(r['timing']['completed_gpu_units'],13);self.assertTrue(r['owned_memory']['teardown_zero'])

    def test_changed_sdk_layout_rejected(self):
        self.change_json('configuration.json',lambda d:d['images'][0].update(w=256))
        with self.assertRaisesRegex(ValueError,'dimensions'):A.native_report(self.case)

    def test_incomplete_tile_journal_rejected(self):
        p=self.root/'capture/dispatches.jsonl';p.write_text('\n'.join(p.read_text().splitlines()[:-2])+'\n')
        with self.assertRaisesRegex(ValueError,'GPU units'):A.native_report(self.case)

    def test_nonfinite_gpu_unit_rejected(self):
        p=self.root/'capture/dispatches.jsonl';rows=[json.loads(x) for x in p.read_text().splitlines()];rows[1]['gpu_us_diagnostic']=float('nan');p.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
        with self.assertRaisesRegex(ValueError,'guard failed'):A.native_report(self.case)

    def test_previous_history_contamination_rejected(self):
        import struct
        p=self.root/'capture/stage-0-previous-1.f32';b=bytearray(p.read_bytes());struct.pack_into('<f',b,0,1);p.write_bytes(b)
        with self.assertRaisesRegex(ValueError,'history not black'):A.native_report(self.case)

    def test_packed_ray_count_rejected_even_with_matching_pair(self):
        import struct
        for name in ('constants-0.bin','constants-1.bin'):
            p=self.root/'capture'/name;b=bytearray(p.read_bytes());struct.pack_into('<I',b,100,256|(6<<16)|(14<<24));p.write_bytes(b)
        with self.assertRaisesRegex(ValueError,'rotation/count'):A.native_report(self.case)

    def test_nonzero_teardown_rejected(self):
        self.change_json('allocation-ledger.json',lambda d:d.update(teardown_zero=False))
        with self.assertRaises(ValueError):A.native_report(self.case)


if __name__=='__main__':unittest.main()
