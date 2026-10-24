#!/usr/bin/env python3
"""026 ordered one-process cold/warm HDR acquisition; no automatic queue/retry."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import nrd_quality_build as B
import nrd_sky_process as S
import nrd_quality_overlay as O
import reference_step as R
import score_retained as F
import guided_transport_cpu as G

TARGETS=[(c,d) for c in ('H01','H02','H03') for d in (2,8)]
LADDER=(1,4,16,64)
BUILD=B.BASE/'m001-nrd026-cpu-build-v1/result.json'
CPU=B.BASE/'m001-nrd026-cpu-contracts-v1/result.json'

def tag(cell,depth,spp):return f'm001-nrd026-gpu-{cell.lower()}-b{depth}-n{spp}'

def pin(path,pins,payloads=True):
    r=B.read(path);pins[str(path)]=B.SHA(path)
    if payloads:pins.update({str(path.parent/name):h for name,h in r.get('payload_sha256',{}).items()})
    return r

def previous(cell,depth,spp,base=None):
    base=base or B.BASE;B.need((cell,depth) in TARGETS and spp in LADDER,'026 unregistered target/budget');pins={}
    def audit(c,d,n):
        p=base/(tag(c,d,n)+'-audit-v1/result.json');r=pin(p,pins)
        B.need(r['complete'] and r['valid'] and (r['cell'],r['depth'],r['spp'])==(c,d,n) and r['classification']==('JOINT_QUALITY_PASS' if r['joint_pass'] else 'QUALITY_FAIL') and r['joint_pass']==(r['cold_pass'] and r['warm_pass']),'026 previous operational/quality audit not terminal-valid')
        native=pin(Path(r['native_receipt']),pins,False);B.need(native['complete'] and native['valid'] and B.SHA(r['native_receipt'])==r['native_receipt_sha256'],'026 previous native identity')
        return r
    for c,d in TARGETS[:TARGETS.index((cell,depth))]:
        for n in LADDER:
            r=audit(c,d,n)
            if r['joint_pass']:break
        else:B.need(r['spp']==64 and not r['joint_pass'],'026 preceding target not exhausted')
    for n in LADDER[:LADDER.index(spp)]:B.need(not audit(cell,depth,n)['joint_pass'],'026 stop ladder after first joint PASS')
    B.rehash(pins);return pins

def original(cell,depth,spp,pins):
    B.need((cell,depth) in TARGETS and spp in LADDER,'026 target/budget')
    proof=S.original(cell,depth,pins);oldplan=B.read(B.BASE/f'm001-integrated022-gpu-{cell.lower()}-b{depth}-v1/plan.json')['proof']
    level=next(x for x in oldplan['levels'] if x['spp']==spp);pt=Path(level['work'])/'capture'
    for name in ('direct.pfm','indirect.pfm','total.pfm'):pins[str(pt/name)]=B.SHA(pt/name)
    state,audit,extra=R.preflight(cell,depth);pins.update(extra);ref=F.reference(cell,depth);spec=dict(state_directory=str((R.LANE/f'capture/M001-{cell}-hwrt').relative_to(B.ROOT)),state_sha256=R.CAPTURE_SHA[cell]);verification=R.P.verify_reference(ref,cell,depth,spec,pins)
    B.need(verification['qualification_sha256']==oldplan['reference']['qualification_sha256'],'026 admitted reference differs from022')
    proof.update(spp=spp,original_pt_directory=str(pt),reference_directory=str(ref),reference_verification=verification,original_state_audit=audit)
    return proof

def prepared(cell,depth,spp):
    head=B.committed();pins=previous(cell,depth,spp);b=pin(BUILD,pins);cpu=pin(CPU,pins)
    B.need(b['all_pass'] and cpu['all_pass'] and not b['gpu_executed'] and not cpu['gpu_executed'],'026 actual CPU readiness')
    for r in (b,cpu):
        for field in ('input_sha256','compiled_dependency_sha256'):B.rehash(r.get(field,{}));pins.update(r.get(field,{}))
    proof=original(cell,depth,spp,pins);proof.update(executable=b['executable'],shaders=b['shader_directory'])
    for p in B.OWN:pins[str(p)]=B.SHA(p)
    B.rehash(pins);return head,pins,proof

def command(proof,out,depth):return [proof['executable'],'--gpu','--state',proof['primary_capture'],'--out',str(out/'capture'),'--spp',str(proof['spp']),'--vertices',str(depth),'--shaders',proof['shaders']]

def prepare(cell,depth,spp,out):
    head,pins,proof=prepared(cell,depth,spp);B.need(out==B.BASE/(tag(cell,depth,spp)+'-v1') and not out.exists(),'026 exclusive canonical output');S.quiet();B.need(shutil.disk_usage(B.BASE).free>=32*1024**3,'02632GiB disk gate');out.mkdir()
    plan=dict(schema='m001-nrd026-one-quality-plan/1',cell=cell,depth=depth,spp=spp,source_commit=head,input_sha256=pins,proof=proof,command=command(proof,out,depth),seeds=[O.seed(i) for i in range(64)],frames=64,gpu_processes_authorized=1,accepted_timing=False);B.write(out/'plan.json',plan);return out/'plan.json'

def run(path):
    out=path.parent;S.launch_inventory(out);p=B.read(path);head,pins,proof=prepared(p['cell'],p['depth'],p['spp'])
    B.need(p==dict(schema='m001-nrd026-one-quality-plan/1',cell=p['cell'],depth=p['depth'],spp=p['spp'],source_commit=head,input_sha256=pins,proof=proof,command=command(proof,out,p['depth']),seeds=[O.seed(i) for i in range(64)],frames=64,gpu_processes_authorized=1,accepted_timing=False) and out==B.BASE/(tag(p['cell'],p['depth'],p['spp'])+'-v1'),'026 exact plan/proof/command');S.quiet();B.need(shutil.disk_usage(out).free>=32*1024**3,'026 disk gate');B.write(out/'started.json',dict(plan_sha256=B.SHA(path),gpu_processes_authorized=1))
    r=dict(schema='m001-nrd026-one-native-quality-runtime/1',cell=p['cell'],depth=p['depth'],spp=p['spp'],source_commit=head,complete=False,valid=False,gpu_executed=True,classification='STOP_NO_RETRY',accepted_timing=False,plan_sha256=B.SHA(path))
    try:
        launch=out/'launch';launch.mkdir();native=G.guarded(p['command'],launch,120,180);B.write(launch/'result.json',native);B.need(native['returncode']==0 and not native['timed_out'],'026 native failure/timeout')
        c=B.read(out/'capture/complete.json');B.need(c['complete'] and c['frames']==64 and c['units']==30540 and c['aggregate_reserved_at_teardown']==0,'026 incomplete native/ownership');B.rehash(pins);r.update(complete=True,valid=True,classification='GPU_EXECUTED_AUDIT_REQUIRED')
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
        import nrd_quality_audit as A
        r=A.run(a.native.resolve(),a.out.resolve());print(json.dumps({k:r.get(k) for k in ('complete','valid','classification','cold_pass','warm_pass','joint_pass','error')}));sys.exit(0 if r['valid'] else 2)
