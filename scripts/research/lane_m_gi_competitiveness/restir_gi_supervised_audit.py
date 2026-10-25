#!/usr/bin/env python3
"""036 real outer supervisor for immutable035 CPU physical extraction audits."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import anchor_process_limits as C
import restir_gi_physical_process as P
import restir_gi_physical_model as M

ROOT,BASE,B=P.ROOT,P.BASE,P.B
PROTOCOL=ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/036-physical-candidate-audit-supervisor-correction.md'
OWN=[PROTOCOL,Path(__file__).resolve()]
PREP=BASE/'m001-restir036-supervisor-probe-v1'


def committed():
    head=P.committed();subprocess.run(['git','merge-base','--is-ancestor','70374817',head],check=True)
    for p in OWN:M.need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(ROOT))])==p.read_bytes(),'commit036 supervisor/contract before use')
    for p in P.OWN:M.need(subprocess.check_output(['git','show','9c22bc21:'+str(p.relative_to(ROOT))])==p.read_bytes(),'immutable035 model/source')
    return head


def imports():
    pins={str(p):B.SHA(p) for p in [*OWN,*P.OWN,Path(C.__file__),P.O.ORIGINAL,Path(sys.executable)]}
    for number in (219,221):
        p=next((ROOT/'research/lanes/lane-m-gi-competitiveness/results').glob(str(number)+'-*.json'))
        M.need(subprocess.check_output(['git','show','6d1c9aac:'+str(p.relative_to(ROOT))])==p.read_bytes(),'035 withdrawal identity');pins[str(p)]=B.SHA(p)
    prep=P.D.pin_inventory(P.BUILD,pins);M.need(prep['all_pass'] and not prep['old_successful_tests_reexecuted'],'reuse successful035 native build/tests')
    return pins


def case_root(cell,depth):
    M.need((cell,depth) in M.TARGETS,'fixed036 target');return BASE/f'm001-restir036-{cell.lower()}-b{depth}-v1'


def old_input(native_path):
    native_path=native_path.resolve();native=B.read(native_path);M.need(native_path==P.canonical(native['cell'],native['depth'])/'result.json','exact original035 native root')
    supersession=B.read(ROOT/'research/lanes/lane-m-gi-competitiveness/results/219-restir-gi-physical-audit-envelope-supersession.json')
    row=next(r for r in supersession['records'] if (r['cell'],r['depth'])==(native['cell'],native['depth']))
    M.need(B.SHA(native_path)==row['native_receipt_sha256'] and native['complete'] and native['all_pass'] and native['source_commit'].startswith('9c22bc21'),'actual immutable035 acquisition')
    M.need(B.inventory(native_path.parent)==native['payload_sha256'],'035 full native inventory')
    pins=dict(native['input_sha256']);pins[str(native_path)]=B.SHA(native_path)
    pins.update({str(native_path.parent/k):v for k,v in native['payload_sha256'].items()})
    oldaudit=Path(row['numerical_audit_receipt']);M.need(B.SHA(oldaudit)==row['numerical_audit_sha256'],'old unqualified numeric identity');a=B.read(oldaudit)
    pins[str(oldaudit)]=B.SHA(oldaudit);pins.update({str(oldaudit.parent/k):v for k,v in a['payload_sha256'].items()})
    command=B.read(native_path.parent/'paths.command.json');terminal=B.read(native_path.parent/'paths.process.json')
    M.need(command['cpu_limit']==1200 and command['wall_limit']==1800 and terminal['reaped'] and not terminal['timed_out'] and terminal['returncode']==0,'guarded original native acquisition')
    B.rehash(pins);return native,oldaudit,pins


def worker(out,native_path=None):
    # Numeric worker intentionally DOES NOT call C.limits: the outer supervisor
    # sets the registered actual child profile, rather than the parent profile.
    state=C.state();wanted=dict(cpu=[1200,1200],address=[C.ADDRESS,C.ADDRESS],core=[0,0],sigxcpu_default=True,sigxcpu_unblocked=True)
    M.need(state==wanted,'actual numeric worker profile');M.need(not out.exists(),'exclusive worker root');out.mkdir()
    C.write(out/'effective-worker-before.json',dict(pid=os.getpid(),effective=state))
    r=dict(schema='m001-restir036-supervised-worker/1',source_commit=committed(),complete=False,all_pass=False,pid=os.getpid(),effective_worker=state,
           probe=native_path is None,gpu_executed=False,new_paths=0,hdr_quality_scored=False,rows=[])
    try:
        if native_path is not None:
            native,old_audit,pins=old_input(native_path);r.update(native_receipt=str(native_path),native_receipt_sha256=B.SHA(native_path),original_native_source_commit=native['source_commit'],input_sha256=pins)
            geometry=Path(native['info']['geometry']);vertices=np.fromfile(geometry/'vertices.f64','<f8').reshape(-1,3,3);primary=np.fromfile(geometry/'primary.bin',M.PRIMARY)
            depth=native['depth']
            for seed in range(4):
                folder=native_path.parent/'paths'/f'seed-{seed}';original=np.fromfile(folder/'original.bin',M.RESULT);observed=np.fromfile(folder/'observed.bin',M.RESULT)
                records=np.fromfile(folder/'vertices.bin',M.VERTEX).reshape(57600,depth);packets=np.fromfile(folder/'packets.bin',M.PACKET)
                M.need(original.shape==observed.shape==packets.shape==(57600,),'all035 pixels')
                arrays,summary=M.audit_records(original,observed,records,packets,vertices,native['native']['offset'],primary)
                with np.load(old_audit.parent/f'seed-{seed}-full-recovery.npz',allow_pickle=False) as old:
                    M.need(set(old.files)==set(arrays) and all(np.array_equal(old[k],v) for k,v in arrays.items()),'every old/new semantic array agrees')
                with (out/f'seed-{seed}-full-recovery.npz').open('xb') as f:np.savez_compressed(f,**arrays)
                r['rows'].append(dict(seed=M.SEEDS[seed],all_pass=True,old_new_semantic_arrays_exact=True,**summary));print('036 seed',seed,'GUARDED_FULL_RECORD_PASS',flush=True)
            B.rehash(pins)
        M.need(C.state()==wanted,'worker profile unchanged through numeric work');r.update(complete=True,all_pass=True)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    r['payload_sha256']=B.inventory(out);C.write(out/'result.json',r);return 0 if r['all_pass'] else 1


def supervise(root,native_path=None):
    args=[sys.executable,str(Path(__file__).resolve()),'worker','--out',str(root/'worker')]
    if native_path is not None:args+=['--native',str(native_path)]
    row=C.guarded(args,root,'numeric',cpu=1200,wall=1800)
    command=B.read(root/'numeric.command.json');child=B.read(root/'numeric.child-limits.json');terminal=B.read(root/'numeric.process.json');pid=B.read(root/'numeric.pid.json')['pid'];w=B.read(root/'worker/result.json')
    M.need(command['command']==args and command['cpu_limit']==1200 and command['wall_limit']==1800 and command['address_limit']==C.ADDRESS,'actual registered outer deadline command')
    M.need(child==w['effective_worker'] and child['cpu']==[1200,1200] and pid==row['pid']==terminal['pid']==w['pid'],'actual worker PID and effective profile')
    M.need(terminal['reaped'] and not terminal['timed_out'] and terminal['returncode']==0 and w['complete'] and w['all_pass'],'actual successful reaped numeric worker')
    return row,w


def prepare():
    head=committed();M.need(not PREP.exists(),'one036 probe only');pins=imports();PREP.mkdir();C.write(PREP/'inputs-before.json',dict(source_commit=head,input_sha256=pins))
    r=dict(schema='m001-restir036-supervisor-preparation/1',source_commit=head,complete=False,all_pass=False,input_sha256=pins,gpu_executed=False,old_tests_reexecuted=False,new_native_compilations=0,new_paths=0)
    try:
        r['effective_parent_limits']=C.limits();r['process'],w=supervise(PREP);M.need(w['probe'] and not w['rows'],'probe touches no physical data');B.rehash(pins)
        r.update(complete=True,all_pass=True,classification='CPU_AUDIT_SUPERVISOR_PROBE_PASS',actual_integration_probes=1)
    except Exception as e:r.update(error=type(e).__name__+': '+str(e),classification='INVALID_STOP_NO_RETRY')
    r['payload_sha256']=B.inventory(PREP);C.write(PREP/'result.json',r);print(json.dumps({k:r.get(k) for k in ('complete','all_pass','classification','error')}),flush=True);return 0 if r['all_pass'] else 1


def case(cell,depth):
    head=committed();root=case_root(cell,depth);M.need(not root.exists(),'exclusive036 audit');pins=imports();P.D.pin_inventory(PREP,pins)
    for c,d in M.TARGETS[:M.TARGETS.index((cell,depth))]:
        p=case_root(c,d)/'result.json';old=B.read(p);M.need(old['complete'] and old['all_pass'] and old['classification']=='CPU_PHYSICAL_EXTRACTION_SUPERVISED_CASE_PASS','previous actual supervised audit PASS required');pins[str(p)]=B.SHA(p)
    native_path=P.canonical(cell,depth)/'result.json';native,oldaudit,oldpins=old_input(native_path);pins.update(oldpins)
    M.need(shutil.disk_usage(BASE).free>=16*1024**3,'16GiB free disk');root.mkdir();C.write(root/'inputs-before.json',dict(source_commit=head,input_sha256=pins))
    r=dict(schema='m001-restir036-supervised-case/1',source_commit=head,original_native_source_commit=native['source_commit'],cell=cell,depth=depth,
           complete=False,all_pass=False,classification='INVALID_STOP_NO_RETRY',input_sha256=pins,gpu_executed=False,new_native_path_acquisitions=0,
           native_receipt=str(native_path),native_receipt_sha256=B.SHA(native_path))
    try:
        r['effective_parent_limits']=C.limits();r['process'],w=supervise(root,native_path);M.need(not w['probe'] and len(w['rows'])==4,'complete fresh supervised numeric work')
        B.rehash(pins);r.update(complete=True,all_pass=True,classification='CPU_PHYSICAL_EXTRACTION_SUPERVISED_CASE_PASS',rows=w['rows'],outer_wall_deadline_enforced=True,
                              actual_numeric_workers=1,paths_per_imported_role=230400,allocated_imported_vertex_slots=230400*depth)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    r['payload_sha256']=B.inventory(root);C.write(root/'result.json',r);print(json.dumps({k:r.get(k) for k in ('complete','all_pass','classification','error')}),flush=True);return 0 if r['all_pass'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='operation',required=True);sub.add_parser('prepare')
    p=sub.add_parser('case');p.add_argument('--cell',choices=['H01','H02','H03'],required=True);p.add_argument('--depth',type=int,choices=[2,8],required=True)
    p=sub.add_parser('worker');p.add_argument('--out',type=Path,required=True);p.add_argument('--native',type=Path)
    args=parser.parse_args()
    if args.operation=='prepare':sys.exit(prepare())
    elif args.operation=='case':sys.exit(case(args.cell,args.depth))
    else:sys.exit(worker(args.out,args.native))
