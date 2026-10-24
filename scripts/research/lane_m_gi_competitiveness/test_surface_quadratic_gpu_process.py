"""021 CPU process/ordered-stop/full native intake contracts; no Vulkan call."""
import argparse
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import surface_quadratic_gpu_process as T

OUT=None


def journal():
    result=[];units=[(0,0,0,57600)]+[(1,s,p,128) for s in range(3) for p in range(0,57600,128)]+[(2,s,0,57600) for s in range(3)]
    for i,(mode,s,p,count) in enumerate(units):
        label=('geometry' if mode==0 else 'fit' if mode==1 else 'filter')+f'-s{s}-p{p}'
        result.extend([dict(event='begin',unit=i,label=label,mode=mode,stage=s,start=p,count=count),dict(event='complete',unit=i,timestamp_begin=i*2000,timestamp_end=i*2000+1000,gpu_us_diagnostic=1.)])
    return result


def device():return dict(name=T.DEVICE,vendor_id=4098,queue_family=0,api_version=(1<<22)+(3<<12),driver_name='synthetic-contract',driver_info='not actual GPU evidence',timestamp_valid_bits=64,timestamp_period_ns=1.,owned_bytes=sum(T.LOGICAL_BYTES))


def ledger():
    events=[];live=0
    for i,size in enumerate(T.LOGICAL_BYTES):
        live+=size;events.append(dict(sequence=len(events),allocation_id=i+1,device_context=1,action='allocate',bytes=size,live_bytes=live,memory_type=0,requested_properties=6,buffer_usage=32,phase='synthetic'))
    peak=live
    for i,size in enumerate(T.LOGICAL_BYTES):
        live-=size;events.append(dict(sequence=len(events),allocation_id=i+1,device_context=1,action='free',bytes=size,live_bytes=live,memory_type=0,requested_properties=6,buffer_usage=32,phase='synthetic'))
    return dict(schema='n010-allocation-lifetimes/1',device_contexts=1,teardown_zero=True,live_bytes_at_teardown=0,true_peak_owned_bytes=peak,events=events,phases=[dict(name='synthetic',peak_bytes=peak,live_bytes_at_end=0)])


def good_capture(root):
    root.mkdir()
    for name in ('geometry.f32','coefficients.f32','maps.u32','stages.f32','unclipped.f32'):(root/name).write_bytes(b'not numerical data: intake fixture only')
    for name,data in [('complete.json',dict(schema='m001-q019-native-gpu/1',complete=True,units=1354,new_primary_paths=0,new_pt_paths=0,quality_admitted=False,accepted_timing=False)),('device.json',device()),('allocation-ledger.json',ledger())]:T.G.write(root/name,data)
    (root/'dispatches.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in journal()));return root


class Contracts(unittest.TestCase):
    def test_valid_journal(self):self.assertEqual(T.journal_report(journal(),device())['completed_units'],1354)
    def test_timestamp_wrap(self):
        j=journal();d=device();d['timestamp_valid_bits']=32;j[1].update(timestamp_begin=2**32-500,timestamp_end=500);T.journal_report(j,d)
    def test_missing_incomplete_unit(self):
        with self.assertRaises(ValueError):T.journal_report(journal()[:-1],device())
    def test_reordered_unit(self):
        j=journal();j[2],j[4]=j[4],j[2]
        with self.assertRaises(ValueError):T.journal_report(j,device())
    def test_unbounded_fit_unit(self):
        j=journal();j[2]['count']=256
        with self.assertRaises(ValueError):T.journal_report(j,device())
    def test_bad_complete_event(self):
        j=journal();j[1]['event']='incomplete'
        with self.assertRaises(ValueError):T.journal_report(j,device())
    def test_nan_timestamp(self):
        j=journal();j[1]['gpu_us_diagnostic']=float('nan')
        with self.assertRaises(ValueError):T.journal_report(j,device())
    def test_timestamp_mismatch(self):
        j=journal();j[1]['gpu_us_diagnostic']=2.
        with self.assertRaises(ValueError):T.journal_report(j,device())
    def test_duration_guard(self):
        j=journal();j[1].update(timestamp_end=250001000,gpu_us_diagnostic=250001.)
        with self.assertRaises(ValueError):T.journal_report(j,device())
    def test_timestamp_device_invalid(self):
        d=device();d['timestamp_valid_bits']=0
        with self.assertRaises(ValueError):T.journal_report(journal(),d)
    def test_valid_owned_ledger(self):self.assertEqual(T.ledger_report(ledger(),device())['true_peak_owned_bytes'],sum(T.LOGICAL_BYTES))
    def test_leaked_ledger(self):
        l=ledger();l['events']=l['events'][:-1]
        with self.assertRaises(ValueError):T.ledger_report(l,device())
    def test_forged_teardown(self):
        l=ledger();l['teardown_zero']=False
        with self.assertRaises(ValueError):T.ledger_report(l,device())
    def test_live_accounting(self):
        l=ledger();l['events'][0]['live_bytes']+=1
        with self.assertRaises(ValueError):T.ledger_report(l,device())
    def test_duplicate_allocation(self):
        l=ledger();l['events'][1]['allocation_id']=1
        with self.assertRaises(ValueError):T.ledger_report(l,device())
    def test_small_owned_buffer(self):
        l=ledger();l['events'][3]['bytes']-=4
        with self.assertRaises(ValueError):T.ledger_report(l,device())
    def test_wrong_free_identity(self):
        l=ledger();l['events'][8]['memory_type']=1
        with self.assertRaises(ValueError):T.ledger_report(l,device())
    def test_device_owned_total(self):
        d=device();d['owned_bytes']+=4
        with self.assertRaises(ValueError):T.ledger_report(ledger(),d)
    def test_over_budget(self):
        l=ledger();l['true_peak_owned_bytes']=8*1024**3+1
        with self.assertRaises(ValueError):T.ledger_report(l,device())
    def test_valid_native_intake(self):T.validate_native(good_capture(OUT/'valid-native'))
    def test_missing_completion(self):
        p=good_capture(OUT/'missing-completion');(p/'complete.json').unlink()
        with self.assertRaises(ValueError):T.validate_native(p)
    def test_extra_capture_file(self):
        p=good_capture(OUT/'extra-capture');(p/'extra').write_text('bad')
        with self.assertRaises(ValueError):T.validate_native(p)
    def test_wrong_device(self):
        p=good_capture(OUT/'wrong-device');d=device();d['name']='other';(p/'device.json').write_text(json.dumps(d))
        with self.assertRaises(ValueError):T.validate_native(p)
    def test_wrong_complete_abi(self):
        p=good_capture(OUT/'wrong-complete');d=T.R.read(p/'complete.json');d['units']=1;(p/'complete.json').write_text(json.dumps(d))
        with self.assertRaises(ValueError):T.validate_native(p)
    def test_first_target_no_prior(self):self.assertEqual(T.previous_gate('H01',2,OUT/'absent'),{})
    def test_skip_prior_missing(self):
        with self.assertRaises(FileNotFoundError):T.previous_gate('H01',8,OUT/'absent')
    def test_prior_loss_stops(self):
        root=OUT/'prior-fail';p=root/(T.tag('H01',2)+'-terminal-audit-v1');p.mkdir(parents=True);rows=[dict(name=n,pass_=True) for n in T.NAMES];rows[2]['pass_']=False;rows[3]['pass_']=False
        T.G.write(p/'result.json',dict(complete=True,valid=True,gpu_executed=True,source_commit=T.G.head(),cell='H01',depth=2,rows=rows,decision=T.decision('H01',2,rows),classification='GPU_TARGET_FAIL',payload_sha256={}))
        with self.assertRaises(ValueError):T.previous_gate('H01',8,root)
    def test_inventory_hash_drift(self):
        p=OUT/'hash-drift';p.mkdir();(p/'payload').write_text('altered');T.G.write(p/'result.json',dict(payload_sha256={'payload':'0'*64}))
        with self.assertRaises(ValueError):T.pin_inventory(p/'result.json',{})
    def test_extra_inventory(self):
        p=OUT/'extra-inventory';p.mkdir();(p/'unexpected').write_text('extra');T.G.write(p/'result.json',dict(payload_sha256={}))
        with self.assertRaises(ValueError):T.pin_inventory(p/'result.json',{})
    def test_duplicate_launch(self):
        p=OUT/'duplicate';p.mkdir();(p/'input').mkdir();(p/'plan.json').write_text('{}')
        for n in ('camera.f32','hits.u32','sources.f32'):(p/'input'/n).write_text('fixture')
        T.launch_inventory(p);(p/'started.json').write_text('{}')
        with self.assertRaises(ValueError):T.launch_inventory(p)
    def test_unexpected_upload(self):
        p=OUT/'extra-upload';p.mkdir();(p/'input').mkdir();(p/'plan.json').write_text('{}')
        for n in ('camera.f32','hits.u32','sources.f32','coefficients.f32'):(p/'input'/n).write_text('fixture')
        with self.assertRaises(ValueError):T.launch_inventory(p)
    def plan_fixture(self,name):
        p=OUT/name;p.mkdir();(p/'input').mkdir();arrays={key:T.Q.np.zeros(1,dtype=T.Q.np.float32) for key in ('camera','hits','sources')};inputs={};proof=dict(executable='/frozen/binary',shader='/frozen/shader')
        for filename,key in (('camera.f32','camera'),('hits.u32','hits'),('sources.f32','sources')):
            (p/'input'/filename).write_bytes(arrays[key].tobytes());inputs[str(p/'input'/filename)]=T.C.sha(p/'input'/filename)
        command=[proof['executable'],'--gpu','--input',str(p/'input'),'--out',str(p/'capture'),'--shader',proof['shader']]
        plan=dict(schema='m001-q021-one-gpu-plan/1',cell='H01',depth=2,source_commit=T.G.head(),gpu_processes_authorized=1,accepted_timing=False,input_sha256=inputs,proof=proof,command=command,names=list(T.NAMES));T.G.write(p/'plan.json',plan)
        return p,arrays,plan
    def check_plan_fixture(self,p,arrays,plan):
        with patch.object(T,'prepare_inputs',return_value=({},plan['proof'])),patch.object(T,'previous_gate',return_value={}),patch.object(T,'input_arrays',return_value=arrays):return T.validate_plan(p/'plan.json')
    def test_valid_reconstructed_plan(self):
        p,a,r=self.plan_fixture('valid-plan');self.check_plan_fixture(p,a,r)
    def test_changed_plan_source(self):
        p,a,r=self.plan_fixture('changed-source');r['source_commit']='0'*40;(p/'plan.json').write_text(json.dumps(r))
        with self.assertRaises(ValueError):self.check_plan_fixture(p,a,r)
    def test_changed_uploaded_input(self):
        p,a,r=self.plan_fixture('changed-input');(p/'input/sources.f32').write_bytes(b'evil')
        with self.assertRaises(ValueError):self.check_plan_fixture(p,a,r)
    def test_changed_plan_command(self):
        p,a,r=self.plan_fixture('changed-command');r['command'][0]='/unregistered/binary';(p/'plan.json').write_text(json.dumps(r))
        with self.assertRaises(ValueError):self.check_plan_fixture(p,a,r)
    def test_changed_plan_build_digest(self):
        p,a,r=self.plan_fixture('changed-build');r['input_sha256']['/frozen/build']='0'*64;(p/'plan.json').write_text(json.dumps(r))
        with self.assertRaises(ValueError):self.check_plan_fixture(p,a,r)
    def test_multiple_process_authority_refused(self):
        p,a,r=self.plan_fixture('multiple-launch');r['gpu_processes_authorized']=2;(p/'plan.json').write_text(json.dumps(r))
        with self.assertRaises(ValueError):self.check_plan_fixture(p,a,r)
    def test_selected_rung_and_bias_conjunction(self):
        for name in ('reference-bias','n16'):
            rows=[dict(name=n,pass_=n!=name) for n in T.NAMES];self.assertFalse(T.decision('H01',2,rows)['pass_'])
    def test_frozen_numerical_auditor(self):
        p=Path(__file__).parent;s=(p/'surface_quadratic_material_audit.py').read_text().replace('020','021').replace('import surface_quadratic_material_replay as T','import surface_quadratic_gpu_process as T').replace('def audit_cpu(','def audit_gpu(').replace('r=audit_cpu(','r=audit_gpu(').replace('valid=False,gpu_executed=False,source_commit=G.head()','valid=False,gpu_executed=True,source_commit=G.head()')
        a=s.index("        R.require({p.name for p in (root/'capture').iterdir()}");b=s.index('        data=capture_arrays',a);s=s[:a]+"        native_device_report=T.validate_native(root/'capture')\n"+s[b:];s=s.replace("classification='CPU_TARGET_PASS' if decision['pass_'] else 'STOP_NO_RETRY'","classification='GPU_TARGET_PASS' if decision['pass_'] else 'GPU_TARGET_FAIL',native_device_report=native_device_report")
        self.assertEqual(s,(p/'surface_quadratic_gpu_audit.py').read_text())


def run(out):
    global OUT
    T.committed();OUT=T.P.new_root(out);r=dict(schema='m001-q021-process-cpu-contracts/1',complete=False,all_pass=False,gpu_executed=False,source_commit=T.G.head(),source_input_sha256={str(p):T.C.sha(p) for p in T.OWN})
    try:
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(Contracts)
        with (OUT/'unittest.txt').open('x') as f:result=unittest.TextTestRunner(stream=f,verbosity=2).run(suite)
        r.update(complete=result.wasSuccessful(),all_pass=result.wasSuccessful(),actual_cpu_contract_tests=result.testsRun,failures=len(result.failures),errors=len(result.errors))
    finally:
        r['payload_sha256']={str(p.relative_to(OUT)):T.C.sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()};T.G.write(OUT/'result.json',r)
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_input_sha256','payload_sha256')},indent=2));return r


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=run(a.out.resolve());raise SystemExit(0 if r['all_pass'] else 1)
