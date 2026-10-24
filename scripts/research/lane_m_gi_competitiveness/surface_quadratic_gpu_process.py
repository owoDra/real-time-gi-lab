"""021 freeze/launch exactly one repaired-host Vulkan replay, never queue targets."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import surface_quadratic_material_replay as Q

M=Q.M
R,C,F,G=Q.R,Q.C,Q.F,Q.G
ROOT,BASE,RESULTS=Q.ROOT,Q.BASE,Q.RESULTS
PROTOCOL=RESULTS.parent/'experiments/021-surface-quadratic-repaired-device-correctness.md'
CPU_PUBLICATION=RESULTS/'122-surface-quadratic-material-abi-six-cpu-targets-raw-replay.json'
TEST_RECEIPT=BASE/'m001-q021-process-cpu-contracts-v1/result.json'
OWN=[Path(__file__).resolve(),Path(__file__).with_name('surface_quadratic_gpu_audit.py'),Path(__file__).with_name('test_surface_quadratic_gpu_process.py'),PROTOCOL]
TARGETS,NAMES=Q.TARGETS,Q.NAMES
P=Q.P
selected_spp,decision,pin_inventory,images,input_arrays=Q.selected_spp,Q.decision,Q.pin_inventory,Q.images,Q.input_arrays
EXPECTED_BINARY='a5077400039cdc77396b25e9c99cbf529bd0e65fe7caacd346efbb7b2f322932'
EXPECTED_SHADER='fc29a8d59cb4f1a57c304e1265f36a1f3ff8f1f28d295bf4172d9d5a7d944827'
DEVICE='AMD Radeon 8060S Graphics (RADV STRIX_HALO)'
LOGICAL_BYTES=(57600*8*4,80,57600*8*4,57600*75*4,57600*6*4,57600*5*4,57600*15*4,57600*15*4)


def committed():
    M.committed()
    for p in OWN:R.require(subprocess.check_output(['git','show',G.head()+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'Commit021process/audit/tests before execution')


def tag(cell,depth):
    R.require((cell,depth) in TARGETS,'021 unregistered target')
    return f'm001-q021-gpu-{cell.lower()}-b{depth}'


def previous_gate(cell,depth,base=BASE):
    tag(cell,depth);inputs={}
    for c,d in TARGETS[:TARGETS.index((cell,depth))]:
        path=base/(tag(c,d)+'-terminal-audit-v1/result.json');r=pin_inventory(path,inputs)
        R.require(r['complete'] is True and r['valid'] is True and r['gpu_executed'] is True and r['source_commit']==G.head() and (r['cell'],r['depth'])==(c,d) and r['decision']==decision(c,d,r['rows']) and r['decision']['pass_'] is True and r['classification']=='GPU_TARGET_PASS','021 prior GPU audit absent/failed/reordered')
        native=pin_inventory(Path(r['native_receipt']),inputs,r['native_receipt_sha256'])
        R.require(native['complete'] is True and native['valid'] is True and native['gpu_executed'] is True,'021 prior native invalid')
    return inputs


def cpu_gate(inputs):
    P.pin(CPU_PUBLICATION,inputs);pub=R.read(CPU_PUBLICATION);P.pin(Path(pub['raw_receipt']),inputs,pub['raw_receipt_sha256'])
    R.require(pub['complete'] and pub['valid'] and pub['classification']=='REPAIRED_HOST_CPU_COHORT_PASS' and len(pub['records'])==6,'021 six CPU gate unavailable')
    for target,row in zip(TARGETS,pub['records']):
        R.require((row['cell'],row['depth'])==target,'021 CPU order differs');a=pin_inventory(Path(row['audit_receipt']),inputs,row['audit_receipt_sha256'])
        R.require(a==row['audit'] and a['complete'] and a['valid'] and a['decision']==decision(*target,a['rows']) and a['decision']['pass_'],'021 CPU audit differs/failed')
        n=pin_inventory(Path(a['native_receipt']),inputs,a['native_receipt_sha256']);R.require(n['complete'] and n['valid'] and n['gpu_executed'] is False,'021 CPU native invalid')
        F.rehash(R.read(Path(a['native_receipt']).parent/'plan.json')['input_sha256'])
    return pub


def prepare_inputs(cell,depth):
    inputs,proof=Q.prepare_inputs(cell,depth);cpu_gate(inputs)
    R.require(C.sha(Path(proof['executable']))==EXPECTED_BINARY and C.sha(Path(proof['shader']))==EXPECTED_SHADER,'021 frozen binary/shader differs')
    tests=pin_inventory(TEST_RECEIPT,inputs)
    R.require(tests['complete'] and tests['all_pass'] and tests['gpu_executed'] is False,'021 process CPU contracts unavailable');F.rehash(tests['source_input_sha256']);inputs.update(tests['source_input_sha256'])
    inputs.update({str(p):C.sha(p) for p in OWN});F.rehash(inputs)
    return inputs,proof


def new_plan(cell,depth,out):
    committed();prior=previous_gate(cell,depth);inputs,proof=prepare_inputs(cell,depth);inputs.update(prior)
    R.quiet();R.require(shutil.disk_usage(BASE).free>=16*1024**3,'021 requires16GiB free');out=P.new_root(out);inputdir=out/'input';inputdir.mkdir()
    arrays=input_arrays(proof);old=BASE/(Q.tag(cell,depth)+'-v1/input')
    for name,key in (('camera.f32','camera'),('hits.u32','hits'),('sources.f32','sources')):
        R.require((old/name).read_bytes()==arrays[key].tobytes(),'021 original CPU upload differs');os.link(old/name,inputdir/name);P.pin(inputdir/name,inputs)
    command=[proof['executable'],'--gpu','--input',str(inputdir),'--out',str(out/'capture'),'--shader',proof['shader']]
    plan=dict(schema='m001-q021-one-gpu-plan/1',cell=cell,depth=depth,source_commit=G.head(),input_sha256=inputs,proof=proof,command=command,names=list(NAMES),gpu_processes_authorized=1,accepted_timing=False)
    G.write(out/'plan.json',plan);return out/'plan.json'


def launch_inventory(root):
    R.require({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}=={'plan.json','input/camera.f32','input/hits.u32','input/sources.f32'},'021 launched/partial/extra inventory or overwrite')
    R.require({p.name for p in root.iterdir()}=={'input','plan.json'},'021 unexpected output/capture/start directory')


def validate_plan(planpath):
    committed();root=planpath.parent.resolve();R.require(root.is_relative_to(BASE) and planpath.name=='plan.json','021 invalid plan location');launch_inventory(root)
    plan=R.read(planpath);R.require(plan['schema']=='m001-q021-one-gpu-plan/1' and plan['source_commit']==G.head() and plan['gpu_processes_authorized']==1 and plan['accepted_timing'] is False,'021 plan identity/authority differs')
    inputs,proof=prepare_inputs(plan['cell'],plan['depth']);inputs.update(previous_gate(plan['cell'],plan['depth']));arrays=input_arrays(proof)
    for name,key in (('camera.f32','camera'),('hits.u32','hits'),('sources.f32','sources')):
        R.require((root/'input'/name).read_bytes()==arrays[key].tobytes(),'021 uploaded input differs');P.pin(root/'input'/name,inputs)
    command=[proof['executable'],'--gpu','--input',str(root/'input'),'--out',str(root/'capture'),'--shader',proof['shader']]
    R.require(inputs==plan['input_sha256'] and proof==plan['proof'] and command==plan['command'] and plan['names']==list(NAMES),'021 reconstructed plan differs');F.rehash(inputs);return plan


def run_plan(planpath):
    planpath=planpath.resolve();plan=validate_plan(planpath);root=planpath.parent
    R.quiet();R.require(shutil.disk_usage(root).free>=16*1024**3,'021 disk gate');G.write(root/'started.json',dict(plan_sha256=C.sha(planpath),gpu_processes_authorized=1))
    r=dict(schema='m001-q021-one-native-gpu/1',cell=plan['cell'],depth=plan['depth'],complete=False,valid=False,gpu_executed=True,source_commit=G.head(),classification='STOP_NO_RETRY',new_render_paths=0,new_reference_paths=0)
    try:
        launch=root/'launch';launch.mkdir();native=G.guarded(plan['command'],launch,120,180);G.write(launch/'result.json',native)
        R.require(native['returncode']==0 and not native['timed_out'],'021 native failure/timeout; stop/no retry');validate_native(root/'capture');F.rehash(plan['input_sha256'])
        r.update(complete=True,valid=True,classification='GPU_EXECUTED_AUDIT_REQUIRED',plan_sha256=C.sha(planpath),native_returncode=native['returncode'],native_timed_out=native['timed_out'])
    except Exception as error:r['error']=repr(error)
    finally:
        r['payload_sha256']={str(p.relative_to(root)):C.sha(p) for p in sorted(root.rglob('*')) if p.is_file()};G.write(root/'result.json',r)
    return r


def journal_report(events,device):
    bits=device['timestamp_valid_bits'];period=device['timestamp_period_ns'];R.require(type(bits) is int and 1<=bits<=64 and type(period) in (int,float) and math.isfinite(period) and period>0,'021 timestamp device facts invalid')
    units=[(0,0,0,57600)]+[(1,s,p,128) for s in range(3) for p in range(0,57600,128)]+[(2,s,0,57600) for s in range(3)]
    R.require(len(events)==2*len(units),'021 journal size/partial differs');maximum=0.;total=0.
    for i,((mode,stage,start,count),begin,end) in enumerate(zip(units,events[::2],events[1::2])):
        label=('geometry' if mode==0 else 'fit' if mode==1 else 'filter')+f'-s{stage}-p{start}'
        R.require(begin==dict(event='begin',unit=i,label=label,mode=mode,stage=stage,start=start,count=count),'021 dispatch sequence differs')
        R.require(set(end)=={'event','unit','timestamp_begin','timestamp_end','gpu_us_diagnostic'} and end['event']=='complete' and end['unit']==i,'021 dispatch incomplete/unknown')
        for key in ('timestamp_begin','timestamp_end'):R.require(type(end[key]) is int and 0<=end[key]<=2**64-1,'021 timestamp word invalid')
        actual=end['gpu_us_diagnostic'];us=((end['timestamp_end']-end['timestamp_begin'])&((1<<bits)-1))*period/1000.
        R.require(type(actual) in (int,float) and math.isfinite(actual) and 0<=actual<=250000 and math.isclose(actual,us,rel_tol=1e-12,abs_tol=1e-12),'021 diagnostic timestamp inconsistent/guard')
        maximum=max(maximum,us);total+=us
    return dict(completed_units=len(units),maximum_gpu_unit_us_diagnostic=maximum,sum_gpu_units_us_diagnostic=total,accepted_timing=False)


def ledger_report(ledger,device):
    R.require(ledger['schema']=='n010-allocation-lifetimes/1' and ledger['device_contexts']==1 and ledger['teardown_zero'] is True and ledger['live_bytes_at_teardown']==0,'021 ownership scope/teardown invalid')
    events=ledger['events'];R.require(len(events)==16,'021 expected eight allocation/free pairs');live={};livebytes=0;peak=0;allocations=[]
    for sequence,e in enumerate(events):
        R.require(e['sequence']==sequence and e['device_context']==1 and type(e['bytes']) is int and e['bytes']>0 and e['requested_properties']==6 and e['buffer_usage']==32,'021 allocation event invalid')
        key=e['allocation_id']
        if e['action']=='allocate':
            R.require(key not in live and key==len(allocations)+1 and len(allocations)<8 and e['bytes']>=LOGICAL_BYTES[len(allocations)],'021 duplicate/small allocation');live[key]=e;livebytes+=e['bytes'];allocations.append(e)
        else:
            R.require(e['action']=='free' and key in live,'021 untracked free');old=live.pop(key);R.require(all(e[k]==old[k] for k in ('bytes','memory_type','requested_properties','buffer_usage','device_context')),'021 free identity differs');livebytes-=e['bytes']
        R.require(e['live_bytes']==livebytes,'021 live accounting differs');peak=max(peak,livebytes)
    R.require(not live and livebytes==0 and len(allocations)==8 and 0<peak<=8*1024**3 and ledger['true_peak_owned_bytes']==peak==device['owned_bytes']==sum(e['bytes'] for e in allocations),'021 ownership peak/teardown differs')
    phases=ledger['phases'];R.require(phases and all(type(x['peak_bytes']) is int and type(x['live_bytes_at_end']) is int and 0<=x['live_bytes_at_end']<=x['peak_bytes']<=peak for x in phases),'021 phase ownership invalid')
    return dict(true_peak_owned_bytes=peak,live_bytes_at_teardown=0,teardown_zero=True,allocation_events=16,logical_buffer_bytes=sum(LOGICAL_BYTES),driver_private_and_cpu_memory_excluded=True)


def validate_native(capture):
    expected={'geometry.f32','coefficients.f32','maps.u32','stages.f32','unclipped.f32','complete.json','device.json','dispatches.jsonl','allocation-ledger.json'}
    R.require({str(p.relative_to(capture)) for p in capture.rglob('*') if p.is_file()}==expected,'021 native capture missing/extra')
    complete=R.read(capture/'complete.json');R.require(complete==dict(schema='m001-q019-native-gpu/1',complete=True,units=1354,new_primary_paths=0,new_pt_paths=0,quality_admitted=False,accepted_timing=False),'021 native completion ABI invalid')
    device=R.read(capture/'device.json');R.require(device['name']==DEVICE and device['vendor_id']==4098 and type(device['queue_family']) is int and device['queue_family']>=0 and device['api_version']>=(1<<22)+(3<<12) and isinstance(device['driver_name'],str) and device['driver_name'] and isinstance(device['driver_info'],str) and device['driver_info'],'021 native device differs')
    events=[json.loads(x) for x in (capture/'dispatches.jsonl').read_text().splitlines()]
    return dict(device=device,dispatches=journal_report(events,device),ownership=ledger_report(R.read(capture/'allocation-ledger.json'),device))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True);p=sub.add_parser('prepare');p.add_argument('--cell',choices=('H01','H02','H03'),required=True);p.add_argument('--depth',choices=(2,8),type=int,required=True);p.add_argument('--out',type=Path,required=True);p=sub.add_parser('run');p.add_argument('--plan',type=Path,required=True);a=ap.parse_args()
    if a.mode=='prepare':print(new_plan(a.cell,a.depth,a.out.resolve()))
    else:
        r=run_plan(a.plan);print(json.dumps({k:r[k] for k in ('cell','depth','complete','valid','classification','error') if k in r},indent=2));raise SystemExit(0 if r['complete'] else 1)
