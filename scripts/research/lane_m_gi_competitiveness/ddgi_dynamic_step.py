#!/usr/bin/env python3
"""One explicit009 DDGI changed-state GPU unit; CPU preparation/audit separate."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import tarfile

import ddgi_dynamic_inputs as D
import ddgi_control_step as S

R=D.R
BUILD=S.BUILD.with_name('m001-ddgi-transition-host-build-v1')
TESTS=BUILD.with_name('m001-ddgi-transition-cpu-tests-v1')
PROCESS_TESTS=BUILD.with_name('m001-ddgi-dynamic-process-tests-v1')
PROTOCOL=R.ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/009-ddgi-dynamic-reset-qualification.md'
CASES=tuple(f'{kind}-{mode}-b{depth}' for kind in D.KINDS for mode in ('fresh','transition') for depth in (2,8))


def split(name):
    R.require(name in CASES,'unregistered DDGI dynamic unit');kind,mode,depth=name.split('-');return kind,mode,int(depth[1:])


def paths(name):
    split(name)
    return (R.ROOT/f'out/m001-ddgi-dynamic-{name}-plan.json',BUILD.with_name('m001-ddgi-dynamic-controls-v1')/name,
            R.ROOT/f'out/m001-ddgi-dynamic-{name}.tar')


def command(name):
    kind,mode,depth=split(name);_,work,_=paths(name)
    cmd=['bash',str(R.ROOT/'scripts/run_with_vulkan.sh'),str(BUILD/'m001-ddgi-transition'),'--state',
        str(D.WORK/kind if mode=='fresh' else R.LANE/'capture/M001-H01-hwrt'),'--out',str(work/'capture'),
        '--sdk-shaders',str(S.SDK),'--reduction-shaders',str(S.REDUCTION),'--adapter-shaders',str(S.ADAPTER),
        '--grid-side','4','--rays','128','--vertices',str(depth),'--mode','scene']
    if mode=='transition':cmd+=['--target-state',str(D.WORK/kind),'--history-policy','reset-all']
    return cmd


def prepare(name):
    kind,mode,depth=split(name);_,work,archive=paths(name)
    R.require(not work.exists() and not archive.exists(),'existing dynamic work/partial/tar; no retry')
    _,physical,inputs=R.preflight('H01',2);states=D.audit_states();direct=D.audit_oracle(kind)
    import ddgi_dynamic_audit as A
    import ddgi_control_audit as Static
    static=[Static.audit(n) for n in S.CASES];R.require(all(x['semantic_pass'] for x in static),'static qualification missing')
    previous=None
    if CASES.index(name):
        prior=CASES[CASES.index(name)-1];p=A.audit(prior);R.require(p['semantic_pass'],'previous dynamic unit failed/incomplete')
        previous={'name':prior,'result_sha256':p['result_sha256']}
    build=R.read(BUILD/'result.json');tests=R.read(TESTS/'result.json');process=R.read(PROCESS_TESTS/'result.json')
    R.require(build['all_pass'] and tests['all_pass'] and process['all_pass'],'CPU build/contract/process tests failed')
    for d in (build,tests,process):
        R.require(d['gpu_executed'] is False,'CPU evidence falsely runs GPU')
        for field in ('input_sha256','compiled_dependency_sha256'):
            for p,h in d.get(field,{}).items():R.require(R.sha(Path(p))==h,'CPU dependency drift: '+p);inputs[p]=h
    for name_,h in build['payload_sha256'].items():R.require(R.sha(BUILD/name_)==h,'private dynamic build drift')
    # Reuse the immutable static plan's SDK/adapter/reference proof input identities.
    for p,h in R.read(S.paths('direct')[0])['input_sha256'].items():R.require(R.sha(Path(p))==h,'static SDK/physical input drift');inputs[p]=h
    paths_to_pin=[Path(__file__).resolve(),Path(A.__file__).resolve(),PROTOCOL,Path(D.__file__).resolve(),BUILD/'result.json',TESTS/'result.json',PROCESS_TESTS/'result.json',BUILD/'m001-ddgi-transition',
        D.WORK/'manifest.json',D.WORK/kind/'cpu-direct-v1/result.json']
    paths_to_pin += [p for p in sorted((D.WORK/kind).glob('*')) if p.is_file()]
    for p in paths_to_pin:inputs[str(p)]=R.sha(p)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R.ROOT,text=True).strip()
    for p in paths_to_pin[:4]:R.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(R.ROOT))],cwd=R.ROOT)==p.read_bytes(),'commit dynamic runner/auditor/protocol')
    return {'schema':'m001-ddgi-dynamic-plan/1','name':name,'source_commit':commit,'command':command(name),'input_sha256':inputs,
        'previous_unit_audit':previous,'state_lock':states,'deterministic_direct':direct,'source_physical_audit':physical,
        'static_control_result_sha256':{x['name']:x['result_sha256'] for x in static},'gpu_executed':False,'accepted_timing':False,'quality_admission':False}


def execute(name):
    plan,work,archive=paths(name);R.require(plan.is_file(),'prepare exact named dynamic CPU plan first')
    frozen=R.read(plan);current=prepare(name)
    for key in ('name','command','input_sha256','previous_unit_audit','state_lock','deterministic_direct'):
        R.require(frozen[key]==current[key],'prepared dynamic plan drift: '+key)
    work.mkdir(parents=True);R.write_new(work/'started.json',{'plan_sha256':R.sha(plan),'plan':frozen})
    result={'schema':'m001-ddgi-dynamic-result/1','name':name,'command':command(name),'plan_sha256':R.sha(plan),'complete':False,
        'gpu_executed':True,'accepted_timing':False,'semantic_admission':False,'quality_admission':False,'classification':'OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY'}
    def limits():resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    try:
        native=subprocess.Popen(command(name),cwd=R.ROOT,env=dict(os.environ),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                start_new_session=True,preexec_fn=limits,text=True)
        try:stdout,stderr=native.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(native.pid,signal.SIGTERM)
            try:stdout,stderr=native.communicate(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(native.pid,signal.SIGKILL);stdout,stderr=native.communicate()
            (work/'native.stdout.txt').write_text(stdout);(work/'native.stderr.txt').write_text(stderr);raise ValueError('dynamic180s timeout; retain partial, no retry')
        (work/'native.stdout.txt').write_text(stdout);(work/'native.stderr.txt').write_text(stderr);result['returncode']=native.returncode
        R.require(native.returncode==0 and R.read(work/'capture/complete.json')['capture_complete'],'dynamic native incomplete')
        result.update(complete=True,classification='RAW_DYNAMIC_CONTROL_RETAINED_AUDIT_REQUIRED')
    except Exception as error:result['error']=str(error)
    result['payload_sha256']={str(p.relative_to(work)):R.sha(p) for p in sorted(work.rglob('*')) if p.is_file()};R.write_new(work/'result.json',result)
    with archive.open('xb') as f:
        with tarfile.open(fileobj=f,mode='w') as t:t.add(plan,arcname='plan.json');t.add(work/'result.json',arcname='result.json')
    return {'name':name,'complete':result['complete'],'classification':result['classification'],'archive':str(archive.relative_to(R.ROOT)),
            'next':'STOP and independently audit before preparing another GPU unit'}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('prepare','execute','audit'));ap.add_argument('--name',choices=CASES,required=True);args=ap.parse_args()
    if args.action=='prepare':d=prepare(args.name);R.write_new(paths(args.name)[0],d);print(json.dumps({'command':d['command'],'plan':str(paths(args.name)[0]),'gpu_executed':False},indent=2))
    elif args.action=='execute':print(json.dumps(execute(args.name),indent=2))
    else:
        import ddgi_dynamic_audit as A
        print(json.dumps(A.audit(args.name),indent=2))
