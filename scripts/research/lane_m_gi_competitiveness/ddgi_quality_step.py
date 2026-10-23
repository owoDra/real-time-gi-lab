#!/usr/bin/env python3
"""One explicitly named010 DDGI quality unit; CPU prepare, single GPU, CPU audit."""
import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import tarfile

import ddgi_dynamic_step as D
from score_retained import reference
import score_hdr as S

R=D.R
PROTOCOL=R.ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/010-ddgi-static-quality-budget-ladder.md'
ROOT=D.BUILD.with_name('m001-ddgi-quality-v1')
CPU=ROOT.with_name('m001-ddgi-quality-cpu-v1')
TESTS=ROOT.with_name('m001-ddgi-quality-process-tests-v1')
TARGETS=tuple((c,b) for c in ('H01','H02','H03') for b in (2,8))
BUDGETS=((8,128),(16,256),(24,512))


@dataclass(frozen=True)
class Case:
    cell:str
    depth:int
    rung:int

    def __post_init__(self):
        R.require((self.cell,self.depth) in TARGETS and type(self.rung) is int and 0<=self.rung<3,'unregistered010 case')

    @property
    def name(self):return f'{self.cell.lower()}-b{self.depth}-q{self.rung}'
    @property
    def budget(self):return BUDGETS[self.rung]
    @property
    def scope(self):return {'cell':self.cell,'vertices':self.depth,'rung':self.rung,'grid_side':self.budget[0],'rays':self.budget[1]}
    @property
    def plan(self):return R.ROOT/f'out/m001-ddgi-quality-{self.name}-plan.json'
    @property
    def work(self):return ROOT/self.name
    @property
    def archive(self):return R.ROOT/f'out/m001-ddgi-quality-{self.name}.tar'


def next_case(reports):
    """Pure frozen first-PASS selection; invalid/operational results never escalate."""
    consumed=set()
    for cell,depth in TARGETS:
        for rung in range(3):
            case=Case(cell,depth,rung)
            if case.name not in reports:
                R.require(set(reports)==consumed,'out-of-order/extra010 acquisition')
                return case
            row=reports[case.name];consumed.add(case.name)
            R.require(row.get('quality_evidence_valid') is True and row.get('classification') in ('PASS','QUALITY_FAIL'),
                      'operational/invalid010 result stops cohort; no budget escalation')
            if row['classification']=='PASS':break
    R.require(set(reports)==consumed,'acquisition after first PASS or exhausted cohort')
    return None


def history(case):
    import ddgi_quality_audit as A
    reports={}
    for cell,depth in TARGETS:
        for rung in range(3):
            prior=Case(cell,depth,rung)
            if prior.work.exists() or prior.archive.exists():reports[prior.name]=A.audit(prior)
    R.require(next_case(reports)==case,'name exactly next010 case; stop after PASS/exhaustion/operational failure')
    return {n:{k:r[k] for k in ('classification','quality_evidence_valid','result_sha256')} for n,r in reports.items()}


def command(case,out=None,cpu=False):
    side,rays=case.budget
    cmd=['bash',str(R.ROOT/'scripts/run_with_vulkan.sh'),str(D.BUILD/'m001-ddgi-transition'),
        '--state',str(R.LANE/f'capture/M001-{case.cell}-hwrt'),'--out',str(out or case.work/'capture'),
        '--sdk-shaders',str(D.S.SDK),'--reduction-shaders',str(D.S.REDUCTION),'--adapter-shaders',str(D.S.ADAPTER),
        '--grid-side',str(side),'--rays',str(rays),'--vertices',str(case.depth),'--mode','scene']
    return cmd+(['--cpu-check'] if cpu else [])


def verify_references(inputs):
    reports={}
    for cell,depth in TARGETS:
        state,audit,proof=R.preflight(cell,depth);inputs.update(proof)
        spec={'state_directory':str((R.LANE/f'capture/M001-{cell}-hwrt').relative_to(R.ROOT)),'state_sha256':state['sha256']}
        reports[f'{cell}_T_B{depth}']=R.P.verify_reference(reference(cell,depth),cell,depth,spec,inputs)
    return reports


def cpu_contract(case):
    """Run actual native CPU branch once, then only rehash its immutable receipt."""
    root=CPU/case.name;receipt=root/'result.json';binary=D.BUILD/'m001-ddgi-transition'
    inputs={str(p):R.sha(p) for p in (binary,R.LANE/f'capture/M001-{case.cell}-hwrt/geometry-state.bin',R.LANE/f'capture/M001-{case.cell}-hwrt/frame-state.bin')}
    cmd=command(case,root/'capture',True)
    if root.exists():
        from audit_quality_step import validate_inventory
        d=R.read(receipt);R.require(d['all_pass'] and d['command']==cmd and d['input_sha256']==inputs,'failed/drifted CPU contract; preserve, no retry')
        validate_inventory(root,d['payload_sha256']);return {'path':str(receipt),'sha256':R.sha(receipt),'contract':d['contract']}
    root.mkdir(parents=True);R.write_new(root/'started.json',{'command':cmd,'input_sha256':inputs,'gpu_executed':False})
    env=dict(os.environ,VK_DRIVER_FILES='/nonexistent/m001-no-icd.json',VK_ICD_FILENAMES='/nonexistent/m001-no-icd.json')
    p=subprocess.run(cmd,cwd=R.ROOT,capture_output=True,text=True,timeout=30,env=env)
    (root/'stdout.txt').write_text(p.stdout);(root/'stderr.txt').write_text(p.stderr)
    d={'command':cmd,'input_sha256':inputs,'gpu_executed':False,'returncode':p.returncode,'all_pass':False}
    if p.returncode==0:
        d['contract']=R.read(root/'capture/cpu-contract.json');s,r=case.budget
        d['all_pass']=d['contract']=={'gpu_initialized':False,'stage_count':case.depth-1,'tile_count_per_stage':s**3*r//4096,
            'total_rays_per_stage':s**3*r,'frame_bytes':128,'triangle_stride':64,'push_bytes':16}
    d['payload_sha256']={str(p.relative_to(root)):R.sha(p) for p in sorted(root.rglob('*')) if p.is_file()};R.write_new(receipt,d)
    R.require(d['all_pass'],'native CPU contract failed; preserve, no retry')
    return {'path':str(receipt),'sha256':R.sha(receipt),'contract':d['contract']}


def prepare(case):
    R.require(not case.work.exists() and not case.archive.exists(),'existing010 work/partial/tar; no retry')
    R.require(shutil.disk_usage(R.ROOT).free>=16*1024**3,'less than16GiB free disk')
    previous=history(case);inputs={};refs=verify_references(inputs)
    import ddgi_dynamic_audit as A
    import ddgi_control_audit as Static
    controls=[Static.audit(n) for n in D.S.CASES]+[A.audit(n) for n in D.CASES]
    R.require(all(c['semantic_pass'] for c in controls),'008/009 prerequisite controls failed')
    evidence=[D.BUILD/'result.json',D.TESTS/'result.json',D.PROCESS_TESTS/'result.json',TESTS/'result.json']
    for path in evidence:
        d=R.read(path);R.require(d['all_pass'] and d['gpu_executed'] is False,'CPU build/test evidence failed')
        inputs[str(path)]=R.sha(path)
        for field in ('input_sha256','compiled_dependency_sha256'):
            for p,h in d.get(field,{}).items():R.require(R.sha(Path(p))==h,'CPU dependency drift: '+p);inputs[p]=h
    for p,h in R.read(D.BUILD/'result.json')['payload_sha256'].items():R.require(R.sha(D.BUILD/p)==h,'dynamic private build drift')
    for p,h in R.read(D.S.paths('direct')[0])['input_sha256'].items():R.require(R.sha(Path(p))==h,'static dependency drift');inputs[p]=h
    # Includes all128/256/512 official blend modules, not just the control ray count.
    for directory in (D.S.SDK,D.S.REDUCTION,D.S.ADAPTER):
        for p in sorted(directory.glob('*.spv')):inputs[str(p)]=R.sha(p)
    import ddgi_quality_audit as Q
    sources=[Path(__file__).resolve(),Path(Q.__file__).resolve(),PROTOCOL,Path(__file__).with_name('test_ddgi_quality_step.py')]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R.ROOT,text=True).strip()
    for p in sources:
        R.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(R.ROOT))],cwd=R.ROOT)==p.read_bytes(),'commit010 runner/auditor/protocol/tests before GPU')
        inputs[str(p)]=R.sha(p)
    contract=cpu_contract(case);inputs[contract['path']]=contract['sha256']
    return {'schema':'m001-ddgi-quality-plan/1','scope':case.scope,'source_commit':commit,'command':command(case),
        'input_sha256':inputs,'reference_verification':refs,'previous_quality_audits':previous,'native_cpu_contract':contract,
        'control_result_sha256':{c['name']:c['result_sha256'] for c in controls},'gpu_executed':False,'accepted_timing':False}


def execute(case):
    R.require(case.plan.is_file(),'prepare exact010 plan first');plan=R.read(case.plan);now=prepare(case)
    for key in ('scope','command','input_sha256','reference_verification','previous_quality_audits','native_cpu_contract','control_result_sha256'):
        R.require(plan[key]==now[key],'prepared010 plan drift: '+key)
    case.work.mkdir(parents=True);R.write_new(case.work/'started.json',{'plan_sha256':R.sha(case.plan),'plan':plan})
    result={'schema':'m001-ddgi-quality-result/1','scope':case.scope,'command':command(case),'plan_sha256':R.sha(case.plan),
        'complete':False,'gpu_executed':True,'accepted_timing':False,'quality_admission':False,'classification':'OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY'}
    def limits():resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    try:
        p=subprocess.Popen(command(case),cwd=R.ROOT,env=dict(os.environ),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            start_new_session=True,preexec_fn=limits,text=True)
        try:stdout,stderr=p.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGTERM)
            try:stdout,stderr=p.communicate(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate()
            (case.work/'native.stdout.txt').write_text(stdout);(case.work/'native.stderr.txt').write_text(stderr)
            raise ValueError('010180s timeout; preserve partial, no retry/escalation')
        (case.work/'native.stdout.txt').write_text(stdout);(case.work/'native.stderr.txt').write_text(stderr);result['returncode']=p.returncode
        R.require(p.returncode==0 and R.read(case.work/'capture/complete.json')['capture_complete'],'native incomplete')
        for p,h in plan['input_sha256'].items():R.require(R.sha(Path(p))==h,'input drift during010 execution')
        # A raw capture is not a quality decision. The independent CPU auditor is authoritative.
        result.update(complete=True,classification='RAW_QUALITY_CAPTURE_RETAINED_AUDIT_REQUIRED')
    except Exception as error:result['error']=str(error)
    result['payload_sha256']={str(p.relative_to(case.work)):R.sha(p) for p in sorted(case.work.rglob('*')) if p.is_file()};R.write_new(case.work/'result.json',result)
    with case.archive.open('xb') as f:
        with tarfile.open(fileobj=f,mode='w') as t:t.add(case.plan,arcname='plan.json');t.add(case.work/'result.json',arcname='result.json')
    return {'scope':case.scope,'complete':result['complete'],'classification':result['classification'],'archive':str(case.archive),
        'next':'STOP and independently CPU-audit terminal evidence before choosing any next GPU unit'}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('prepare','execute','audit'))
    ap.add_argument('--cell',choices=('H01','H02','H03'),required=True);ap.add_argument('--depth',choices=(2,8),type=int,required=True)
    ap.add_argument('--rung',choices=(0,1,2),type=int,required=True);args=ap.parse_args();case=Case(args.cell,args.depth,args.rung)
    if args.action=='prepare':
        R.require(not case.plan.exists(),'refuse existing010 CPU plan');d=prepare(case);R.write_new(case.plan,d)
        print(json.dumps({'scope':case.scope,'plan':str(case.plan),'command':d['command'],'gpu_executed':False},indent=2))
    elif args.action=='execute':print(json.dumps(execute(case),indent=2))
    else:
        import ddgi_quality_audit as A
        # Scores/error maps are CPU-only derived products, outside the immutable native inventory.
        report=A.audit(case,save=True);print(json.dumps(report,indent=2))
