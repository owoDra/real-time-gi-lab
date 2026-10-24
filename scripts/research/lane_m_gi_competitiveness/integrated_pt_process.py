"""022 freeze and execute exactly one new GPU-resident physical image."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import build_integrated_pt as B
import surface_quadratic_gpu_process as T
R,C,F,G,P=T.R,T.C,T.F,T.G,T.P
ROOT,BASE,RESULTS=T.ROOT,T.BASE,T.RESULTS
TARGETS=T.TARGETS
BUILD=BASE/'m001-integrated022-cpu-build-v1/result.json'
CPU=BASE/'m001-integrated022-cpu-contracts-v1/result.json'
TESTS=BASE/'m001-integrated022-process-cpu-contracts-v1/result.json'
GPU_PUBLICATION=RESULTS/'126-surface-quadratic-repaired-device-six-gpu-targets-raw-replay.json'
OWN=[Path(__file__).resolve(),Path(__file__).with_name('integrated_pt_audit.py'),Path(__file__).with_name('test_integrated_pt_process.py')]+B.OWN


def committed():
    for p in OWN:R.require(subprocess.check_output(['git','show',G.head()+':'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes(),'Commit022process/audit/contracts before execution')


def tag(cell,depth):
    R.require((cell,depth) in TARGETS,'022 unregistered target');return f'm001-integrated022-gpu-{cell.lower()}-b{depth}'


def sequence():
    return [('producer',0,p,128) for p in range(0,57600,128)]+[('geometry',0,0,57600)]+[('fit',s,p,128) for s in range(3) for p in range(0,57600,128)]+[('filter',s,0,57600) for s in range(3)]+[('composite',0,0,57600)]


def previous_gate(cell,depth,base=BASE):
    tag(cell,depth);inputs={}
    for c,d in TARGETS[:TARGETS.index((cell,depth))]:
        path=base/(tag(c,d)+'-terminal-audit-v1/result.json');r=T.pin_inventory(path,inputs)
        R.require(r['complete'] is True and r['valid'] is True and r['gpu_executed'] is True and r['source_commit']==G.head() and (r['cell'],r['depth'])==(c,d) and r['classification']=='INTEGRATED_TARGET_PASS' and r['decision']==dict(selected_image_pass=True,reference_bias_pass=True,pass_=True),'022 prior terminal audit absent/failed/source/order; stop')
        n=T.pin_inventory(Path(r['native_receipt']),inputs,r['native_receipt_sha256']);R.require(n['complete'] is True and n['valid'] is True and n['gpu_executed'] is True,'022 prior native invalid')
    return inputs


def prepare_inputs(cell,depth):
    inputs,proof=T.prepare_inputs(cell,depth)
    P.pin(GPU_PUBLICATION,inputs);pub=R.read(GPU_PUBLICATION);R.require(pub['complete'] and pub['valid'] and len(pub['records'])==6,'022 prior six GPU receipts unavailable')
    for target,row in zip(TARGETS,pub['records']):
        R.require((row['cell'],row['depth'])==target,'022 prior GPU order differs');a=T.pin_inventory(Path(row['audit_receipt']),inputs,row['audit_receipt_sha256'])
        R.require(a==row['audit'] and a['complete'] and a['valid'] and a['classification']=='GPU_TARGET_PASS' and a['decision']['pass_'],'022 prior GPU audit differs')
        n=T.pin_inventory(Path(a['native_receipt']),inputs,a['native_receipt_sha256']);R.require(n['complete'] and n['valid'] and n['gpu_executed'],'022 prior GPU native invalid')
    build=T.pin_inventory(BUILD,inputs);cpu=T.pin_inventory(CPU,inputs);tests=T.pin_inventory(TESTS,inputs)
    R.require(all(x['complete'] and x['all_pass'] and x['gpu_executed'] is False for x in (build,cpu,tests)),'022 build/new CPU contracts incomplete')
    R.require(cpu['total_python_contracts']==102 and cpu['new_native_scalar_safety_contracts']==9,'022 actual native contract count differs')
    for source in (build['input_sha256'],build['compiled_dependency_sha256'],cpu['input_sha256'],tests['input_sha256']):F.rehash(source);inputs.update(source)
    proof.update(integrated_executable=build['executable'],integrated_shader_directory=build['shader_directory'])
    for p in OWN:P.pin(p,inputs)
    F.rehash(inputs);return inputs,proof


def command(proof,out,depth):
    return [proof['integrated_executable'],'--gpu','--state',proof['primary_capture'],'--out',str(out/'capture'),'--spp',str(proof['selected_spp']),'--vertices',str(depth),'--seed','305419896','--shaders',proof['integrated_shader_directory']]


def quiet():
    R.quiet()
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name)==os.getpid():continue
        try:name=(p/'exe').readlink().name
        except (FileNotFoundError,PermissionError,ProcessLookupError):continue
        R.require(name not in ('integrated-pt','surface-quadratic-device','phos-n010-pixel-pt','m001-ddgi-scene','closest-primary'),'022 another research native process active')


def new_plan(cell,depth,out):
    committed();R.require(out==BASE/(tag(cell,depth)+'-v1'),'022 fixed canonical exclusive output required');prior=previous_gate(cell,depth);inputs,proof=prepare_inputs(cell,depth);inputs.update(prior)
    quiet();R.require(shutil.disk_usage(BASE).free>=16*1024**3,'022 requires16GiB free');out=P.new_root(out)
    plan=dict(schema='m001-integrated022-one-gpu-plan/1',cell=cell,depth=depth,source_commit=G.head(),input_sha256=inputs,proof=proof,command=command(proof,out,depth),gpu_processes_authorized=1,accepted_timing=False)
    G.write(out/'plan.json',plan);return out/'plan.json'


def launch_inventory(root):
    R.require({str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}=={'plan.json'} and {p.name for p in root.iterdir()}=={'plan.json'},'022 launched/partial/extra inventory; no retry')


def validate_plan(path):
    committed();root=path.parent.resolve();R.require(path.name=='plan.json' and root.is_relative_to(BASE),'022 plan location');launch_inventory(root);plan=R.read(path)
    R.require(plan['schema']=='m001-integrated022-one-gpu-plan/1' and plan['source_commit']==G.head() and plan['gpu_processes_authorized']==1 and plan['accepted_timing'] is False and root==BASE/(tag(plan['cell'],plan['depth'])+'-v1'),'022 plan identity/authority differs')
    inputs,proof=prepare_inputs(plan['cell'],plan['depth']);inputs.update(previous_gate(plan['cell'],plan['depth']));R.require(inputs==plan['input_sha256'] and proof==plan['proof'] and command(proof,root,plan['depth'])==plan['command'],'022 reconstructed plan differs');F.rehash(inputs);return plan


def journal_report(events,device,envelope):
    bits=device['timestamp_valid_bits'];period=device['timestamp_period_ns'];R.require(type(bits) is int and 1<=bits<=64 and type(period) in (int,float) and math.isfinite(period) and period>0,'022 invalid timestamp facts')
    def duration(e):
        for k in ('timestamp_begin','timestamp_end'):R.require(type(e[k]) is int and 0<=e[k]<2**64,'022 timestamp word')
        return ((e['timestamp_end']-e['timestamp_begin'])&((1<<bits)-1))*period/1000.
    units=sequence();R.require(len(events)==2*len(units),'022 partial/extra dispatch log');maximum=0.;total=0.
    for j,((kind,stage,start,count),begin,end) in enumerate(zip(units,events[::2],events[1::2])):
        R.require(begin==dict(event='begin',unit=j,kind=kind,stage=stage,start=start,count=count),'022 unit ordering/range differs')
        R.require(set(end)=={'event','unit','timestamp_begin','timestamp_end','gpu_us_diagnostic'} and end['event']=='complete' and end['unit']==j,'022 unit incomplete/unknown')
        us=duration(end);R.require(math.isfinite(end['gpu_us_diagnostic']) and 0<=us<=250000 and math.isclose(us,end['gpu_us_diagnostic'],rel_tol=1e-12,abs_tol=1e-12),'022 unit timestamp/guard');total+=us;maximum=max(maximum,us)
    whole=duration(envelope);R.require(envelope['accepted_timing'] is False and math.isfinite(whole) and total<=whole<=180e6 and math.isclose(whole,envelope['gpu_us_including_pauses'],rel_tol=1e-12,abs_tol=1e-12) and math.isclose(total,envelope['active_unit_sum_us'],rel_tol=1e-12,abs_tol=1e-9),'022 frame envelope/active sum differs')
    return dict(completed_units=len(units),maximum_gpu_unit_us_diagnostic=maximum,active_gpu_unit_sum_us_diagnostic=total,gpu_frame_envelope_including_pauses_us_diagnostic=whole,accepted_timing=False)


def ledger_report(ledger,complete):
    R.require(ledger['schema']=='n010-allocation-lifetimes/1' and ledger['device_contexts']==1 and ledger['teardown_zero'] is True and ledger['live_bytes_at_teardown']==0,'022 ownership scope/teardown')
    live={};allocated=[];livebytes=0;peak=0
    for j,e in enumerate(ledger['events']):
        R.require(e['sequence']==j and e['device_context']==1 and type(e['bytes']) is int and 0<e['bytes']<=8*1024**3 and type(e['buffer_usage']) is int and type(e['requested_properties']) is int,'022 owned event identity/range')
        key=e['allocation_id']
        if e['action']=='allocate':R.require(key not in live and key==len(allocated)+1,'022 duplicate/unordered allocation');live[key]=e;allocated.append(e);livebytes+=e['bytes']
        else:
            R.require(e['action']=='free' and key in live,'022 unmatched/duplicate free');old=live.pop(key);R.require(all(e[k]==old[k] for k in ('bytes','memory_type','requested_properties','buffer_usage','device_context')),'022 free identity differs');livebytes-=e['bytes']
        R.require(e['live_bytes']==livebytes,'022 aggregate accounting differs');peak=max(peak,livebytes)
    R.require(not live and livebytes==0 and 0<peak<=8*1024**3 and peak==ledger['true_peak_owned_bytes']==complete['aggregate_reserved_peak'] and complete['aggregate_reserved_at_teardown']==0,'022 true peak/aggregate counter/teardown')
    # Eleven mapped pipeline allocations plus original AS/vertices/metadata/
    # instance/scratch and staging are all recorded through the same allocator.
    pipeline=[e for e in allocated if e['requested_properties']==6 and e['buffer_usage'] in (16,32)]
    logical=[57600*8*4,80,57600*8*4,57600*75*4,57600*6*4,57600*4,57600*3*4,57600*3*4,57600*4*4,57600*4*4,128]
    R.require(len(pipeline)>=11 and [e['buffer_usage'] for e in pipeline[-11:]]==[32]*10+[16] and all(e['bytes']>=size for e,size in zip(pipeline[-11:],logical)),'022 complete pipeline allocations absent/small')
    R.require(any(e['buffer_usage']&0x100000 for e in allocated) and any(e['buffer_usage']&0x20000 for e in allocated) and len(allocated)>11,'022 AS/scratch/vertex/staging ownership absent')
    R.require(all(0<=p['live_bytes_at_end']<=p['peak_bytes']<=peak for p in ledger['phases']),'022 phase ownership invalid')
    return dict(true_peak_owned_bytes=peak,live_bytes_at_teardown=0,teardown_zero=True,allocation_events=len(ledger['events']),allocation_pairs=len(allocated),all_owned_as_scratch_staging_pipeline=True,driver_private_and_cpu_memory_excluded=True)


def validate_native(capture,plan):
    binary_sizes={'hits.u32':57600*8*4,'camera.f32':80,'geometry.f32':57600*8*4,'coefficients.f32':57600*75*4,'maps.u32':57600*6*4,'sources.f32':57600*4,'stages.f32':57600*3*4,'unclipped.f32':57600*3*4,'raw-pt.f32':57600*4*4,'final.f32':57600*4*4}
    expected=set(binary_sizes)|{'geometry-state.bin','frame-state.bin','complete.json','device.json','dispatches.jsonl','allocation-ledger.json','envelope.json','setup.json'}|{prefix+name+'.pfm' for prefix in ('','raw-') for name in ('direct','indirect','total')}
    R.require({str(p.relative_to(capture)) for p in capture.rglob('*') if p.is_file()}==expected,'022 native missing/extra capture');R.require(all((capture/name).stat().st_size==size for name,size in binary_sizes.items()),'022 native binary shape')
    for name in ('geometry-state.bin','frame-state.bin'):R.require((capture/name).read_bytes()==(Path(plan['proof']['primary_capture'])/name).read_bytes(),'022 original physical state changed')
    c=R.read(capture/'complete.json');spp=plan['proof']['selected_spp'];R.require(c['schema']=='m001-integrated022-native-gpu/1' and c['complete'] is True and c['gpu_initialized'] is True and c['units']==1805 and (c['spp'],c['vertices'],c['seed'])==(spp,plan['depth'],305419896) and c['new_primary_paths']==57600 and c['new_indirect_paths']==57600*spp and all(c[k]==0 for k in ('input_images_uploaded','input_hits_uploaded','cpu_coefficients_uploaded','intermediate_readbacks')) and c['quality_admitted'] is False and c['accepted_timing'] is False,'022 native complete/input/residency claims differ')
    d=R.read(capture/'device.json');R.require(d['name']==T.DEVICE and d['vendor_id']==4098 and d['api_version']>=(1<<22)+(3<<12) and d['driver_name'] and d['driver_info'],'022 device differs')
    setup=R.read(capture/'setup.json');R.require(setup['accepted_timing'] is False and setup['initial_allocation_upload_as_pipeline_costs_separate'] is True and all(math.isfinite(setup[k]) and setup[k]>=0 for k in ('setup_wall_us','vertex_upload_wall_us','metadata_upload_wall_us','blas_build_gpu_us','tlas_build_gpu_us')),'022 setup costs missing/invalid')
    return dict(device=d,dispatches=journal_report([json.loads(s) for s in (capture/'dispatches.jsonl').read_text().splitlines()],d,R.read(capture/'envelope.json')),ownership=ledger_report(R.read(capture/'allocation-ledger.json'),c),setup=setup)


def run_plan(path):
    path=path.resolve();plan=validate_plan(path);root=path.parent;quiet();R.require(shutil.disk_usage(root).free>=16*1024**3,'022 disk gate');G.write(root/'started.json',dict(plan_sha256=C.sha(path),gpu_processes_authorized=1))
    r=dict(schema='m001-integrated022-one-native-gpu/1',cell=plan['cell'],depth=plan['depth'],complete=False,valid=False,gpu_executed=True,source_commit=G.head(),classification='STOP_NO_RETRY',accepted_timing=False)
    try:
        launch=root/'launch';launch.mkdir();native=G.guarded(plan['command'],launch,120,180);G.write(launch/'result.json',native);R.require(native['returncode']==0 and not native['timed_out'],'022 native failure/timeout; stop/no retry');report=validate_native(root/'capture',plan);F.rehash(plan['input_sha256']);r.update(complete=True,valid=True,classification='GPU_EXECUTED_AUDIT_REQUIRED',native_device_report=report,plan_sha256=C.sha(path))
    except Exception as e:r['error']=repr(e)
    finally:r['payload_sha256']={str(p.relative_to(root)):C.sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'result.json'};G.write(root/'result.json',r)
    return r

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True);p=sub.add_parser('prepare');p.add_argument('--cell',choices=('H01','H02','H03'),required=True);p.add_argument('--depth',choices=(2,8),type=int,required=True);p.add_argument('--out',type=Path,required=True);p=sub.add_parser('run');p.add_argument('--plan',type=Path,required=True);a=ap.parse_args()
    if a.mode=='prepare':print(new_plan(a.cell,a.depth,a.out.resolve()))
    else:
        r=run_plan(a.plan);print(json.dumps({k:r[k] for k in ('cell','depth','complete','valid','classification','error') if k in r},indent=2));raise SystemExit(0 if r['complete'] else 1)
