#!/usr/bin/env python3
"""028 ordered one-process cold/warm HDR acquisition; no automatic queue/retry."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import nrd_no_prepass_build as B
import nrd_sky_process as S
import nrd_no_prepass_overlay as O
import reference_step as R
import score_retained as F
import guided_transport_cpu as G

TARGETS=[(c,d) for c in ('H01','H02','H03') for d in (2,8)]
LADDER=(1,4,16,64)
BUILD=B.BASE/'m001-nrd028-cpu-build-v3/result.json'
CPU=B.BASE/'m001-nrd028-cpu-contracts-v2/result.json'

def tag(cell,depth,spp):return f'm001-nrd028-gpu-{cell.lower()}-b{depth}-n{spp}'

def pin(path,pins,payloads=True):
    r=B.read(path);pins[str(path)]=B.SHA(path)
    if payloads:pins.update({str(path.parent/name):h for name,h in r.get('payload_sha256',{}).items()})
    return r

def previous(cell,depth,spp,base=None):
    base=base or B.BASE;B.need((cell,depth) in TARGETS and spp in LADDER,'028 unregistered target/budget');pins={}
    def audit(c,d,n):
        p=base/(tag(c,d,n)+'-audit-v1/result.json');r=pin(p,pins)
        B.need(r['complete'] and r['valid'] and (r['cell'],r['depth'],r['spp'])==(c,d,n) and r['classification']==('JOINT_QUALITY_PASS' if r['joint_pass'] else 'QUALITY_FAIL') and r['joint_pass']==(r['cold_pass'] and r['warm_pass']),'028 previous operational/quality audit not terminal-valid')
        native=pin(Path(r['native_receipt']),pins,False);B.need(native['complete'] and native['valid'] and B.SHA(r['native_receipt'])==r['native_receipt_sha256'],'028 previous native identity')
        return r
    for c,d in TARGETS[:TARGETS.index((cell,depth))]:
        for n in LADDER:
            r=audit(c,d,n)
            if r['joint_pass']:break
        else:B.need(r['spp']==64 and not r['joint_pass'],'028 preceding target not exhausted')
    for n in LADDER[:LADDER.index(spp)]:B.need(not audit(cell,depth,n)['joint_pass'],'028 stop ladder after first joint PASS')
    B.rehash(pins);return pins

def parent(cell,depth,spp,pins):
    import subprocess
    published=B.ROOT/'research/lanes/lane-m-gi-competitiveness/results/163-nrd-cold-warm-six-targets-summary.json'
    B.need(subprocess.check_output(['git','show','892708b3:'+str(published.relative_to(B.ROOT))])==published.read_bytes(),'028 immutable026 published index')
    index=B.read(published);pins[str(published)]=B.SHA(published)
    native=B.BASE/f'm001-nrd026-gpu-{cell.lower()}-b{depth}-n{spp}-v1/result.json'
    audit=B.BASE/f'm001-nrd026-gpu-{cell.lower()}-b{depth}-n{spp}-audit-v1/result.json'
    for path in (native,audit):B.need(B.SHA(path)==index['input_sha256'][str(path)],'028026 saved receipt identity')
    n=pin(native,pins,False);r=pin(audit,pins)
    B.need(n['complete'] and n['valid'] and r['complete'] and r['valid'] and (r['cell'],r['depth'],r['spp'])==(cell,depth,spp),'028026 reuse operational validity')
    B.need(r['native_receipt']==str(native) and r['native_receipt_sha256']==B.SHA(native),'028026 audit native identity')
    B.need(r['full_secondary_intersection_frames']==[0,1,63] and len(r['all_frame_field_checks'])==64,'028026 reuse coverage')
    cold=Path(index['supplemental_cold_pt_bitword_receipt']);B.need(B.SHA(cold)==index['supplemental_cold_pt_bitword_receipt_sha256'],'028026 certified cold bit proof')
    c=pin(cold,pins,False);B.need(c['complete'] and c['all_pass'] and c['raw_capture_cases']==24,'02802624 certified cold cases')
    # Each actual new producer/guide field is compared to the anchored native
    # payload hash by the independent028 audit, never inferred from source.
    return dict(native_receipt=str(native),audit_receipt=str(audit),cold_bitword_receipt=str(cold))

def original(cell,depth,spp,pins):
    import nrd_quality_process as Q
    proof=Q.original(cell,depth,spp,pins);proof['reused026']=parent(cell,depth,spp,pins)
    directory=CPU.parent/cell.lower()
    for p in directory.rglob('*'):
        if p.is_file():pins[str(p)]=B.SHA(p)
    B.need((directory/'complete.json').is_file(),'028 new SDK CPU capture required')
    proof['sdk_cpu_capture']=str(directory)
    return proof

def prepared(cell,depth,spp):
    head=B.committed();pins=previous(cell,depth,spp);b=pin(BUILD,pins);cpu=pin(CPU,pins)
    B.need(b['all_pass'] and cpu['all_pass'] and not b['gpu_executed'] and not cpu['gpu_executed'],'028 actual CPU readiness')
    for r in (b,cpu):
        for field in ('input_sha256','compiled_dependency_sha256'):B.rehash(r.get(field,{}));pins.update(r.get(field,{}))
    proof=original(cell,depth,spp,pins);proof.update(executable=b['executable'],shaders=b['shader_directory'])
    for p in B.OWN:pins[str(p)]=B.SHA(p)
    B.rehash(pins);return head,pins,proof

def command(proof,out,depth):return [proof['executable'],'--gpu','--state',proof['primary_capture'],'--out',str(out/'capture'),'--spp',str(proof['spp']),'--vertices',str(depth),'--shaders',proof['shaders']]

def prepare(cell,depth,spp,out):
    head,pins,proof=prepared(cell,depth,spp);B.need(out==B.BASE/(tag(cell,depth,spp)+'-v1') and not out.exists(),'028 exclusive canonical output');S.quiet();B.need(shutil.disk_usage(B.BASE).free>=32*1024**3,'02832GiB disk gate');out.mkdir()
    plan=dict(schema='m001-nrd028-one-quality-plan/1',cell=cell,depth=depth,spp=spp,source_commit=head,input_sha256=pins,proof=proof,command=command(proof,out,depth),seeds=[O.seed(i) for i in range(64)],frames=64,gpu_processes_authorized=1,accepted_timing=False);B.write(out/'plan.json',plan);return out/'plan.json'

def run(path):
    out=path.parent;S.launch_inventory(out);p=B.read(path);head,pins,proof=prepared(p['cell'],p['depth'],p['spp'])
    B.need(p==dict(schema='m001-nrd028-one-quality-plan/1',cell=p['cell'],depth=p['depth'],spp=p['spp'],source_commit=head,input_sha256=pins,proof=proof,command=command(proof,out,p['depth']),seeds=[O.seed(i) for i in range(64)],frames=64,gpu_processes_authorized=1,accepted_timing=False) and out==B.BASE/(tag(p['cell'],p['depth'],p['spp'])+'-v1'),'028 exact plan/proof/command');S.quiet();B.need(shutil.disk_usage(out).free>=32*1024**3,'028 disk gate');B.write(out/'started.json',dict(plan_sha256=B.SHA(path),gpu_processes_authorized=1))
    r=dict(schema='m001-nrd028-one-native-quality-runtime/1',cell=p['cell'],depth=p['depth'],spp=p['spp'],source_commit=head,complete=False,valid=False,gpu_executed=True,classification='STOP_NO_RETRY',accepted_timing=False,plan_sha256=B.SHA(path))
    try:
        launch=out/'launch';launch.mkdir();native=G.guarded(p['command'],launch,120,180);B.write(launch/'result.json',native);B.need(native['returncode']==0 and not native['timed_out'],'028 native failure/timeout')
        c=B.read(out/'capture/complete.json');B.need(c['complete'] and c['frames']==64 and c['units']==30540 and c['aggregate_reserved_at_teardown']==0,'028 incomplete native/ownership');B.rehash(pins);r.update(complete=True,valid=True,classification='GPU_EXECUTED_AUDIT_REQUIRED')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    r['payload_sha256']=B.inventory(out);B.write(out/'result.json',r);return r

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True)
    p=sub.add_parser('prepare');p.add_argument('--cell',choices=('H01','H02','H03'),required=True);p.add_argument('--depth',type=int,choices=(2,8),required=True);p.add_argument('--spp',type=int,choices=LADDER,required=True);p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('run');p.add_argument('--plan',type=Path,required=True)
    p=sub.add_parser('audit');p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.mode=='prepare':print(prepare(a.cell,a.depth,a.spp,a.out.resolve()))
    elif a.mode=='run':
        r=run(a.plan.resolve());print(json.dumps({k:r.get(k) for k in ('complete','valid','classification','error')}));sys.exit(0 if r['complete'] else 2)
    else:
        import nrd_no_prepass_audit as A
        r=A.run(a.native.resolve(),a.out.resolve());print(json.dumps({k:r.get(k) for k in ('complete','valid','classification','cold_pass','warm_pass','joint_pass','error')}));sys.exit(0 if r['valid'] else 2)
