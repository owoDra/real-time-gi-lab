#!/usr/bin/env python3
"""One explicitly named DDGI semantic control. No quality scoring or GPU queue."""
import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import tarfile

import reference_step as R
from score_retained import reference

CASES=('direct','black','unit','hdr','scene-one','scene-seven')
BUILD=R.ROOT/'out/research/lane-m-gi-competitiveness/m001-ddgi-host-build-v1'
TESTS=BUILD.with_name('m001-ddgi-host-cpu-tests-v2')
ADAPTER=BUILD.with_name('m001-ddgi-scene-compile-v1')
SDK=R.ROOT/'out/research/n010-comparison-readiness/ddgi-shaders-v2'
REDUCTION=SDK.with_name('ddgi-reduction-shaders-v1')
PROTOCOL=R.ROOT/'research/lanes/lane-m-gi-competitiveness/experiments/008-ddgi-bounded-semantic-controls.md'


def paths(name):
    R.require(name in CASES,'unregistered DDGI control')
    return (R.ROOT/f'out/m001-ddgi-control-{name}-plan.json',
            BUILD.with_name('m001-ddgi-controls-v1')/name,
            R.ROOT/f'out/m001-ddgi-control-{name}.tar')


def command(name):
    _,work,_=paths(name)
    modes={'direct':'direct','black':'constant0','unit':'constant1','hdr':'constant8','scene-one':'scene','scene-seven':'scene'}
    return ['bash',str(R.ROOT/'scripts/run_with_vulkan.sh'),str(BUILD/'m001-ddgi-scene'),
        '--state',str(R.LANE/'capture/M001-H01-hwrt'),'--out',str(work/'capture'),
        '--sdk-shaders',str(SDK),'--reduction-shaders',str(REDUCTION),'--adapter-shaders',str(ADAPTER),
        '--grid-side','4','--rays','128','--vertices','1' if name=='direct' else '8' if name=='scene-seven' else '2',
        '--mode',modes[name]]


def prepare(name):
    plan,work,archive=paths(name)
    R.require(not work.exists() and not archive.exists(),'existing control/partial/proof; no retry')
    state,physical,inputs=R.preflight('H01',2)
    spec={'state_directory':str((R.LANE/'capture/M001-H01-hwrt').relative_to(R.ROOT)),'state_sha256':state['sha256']}
    verification=R.P.verify_reference(reference('H01',2),'H01',2,spec,inputs)
    import ddgi_control_audit as A
    previous=None
    if CASES.index(name):
        prior=CASES[CASES.index(name)-1];audit=A.audit(prior)
        R.require(audit['semantic_pass'],'previous control not independently admitted')
        previous={'name':prior,'result_sha256':audit['result_sha256']}
    build=R.read(BUILD/'result.json');tests=R.read(TESTS/'result.json')
    R.require(build['all_pass'] and tests['all_pass'] and build['gpu_executed'] is False and tests['gpu_executed'] is False,'CPU host build/tests missing')
    for field in ('input_sha256','compiled_dependency_sha256'):
        for p,h in build[field].items():R.require(R.sha(Path(p))==h,'CPU build input/dependency drift: '+p)
    for p,h in tests['input_sha256'].items():R.require(R.sha(Path(p))==h,'CPU test binary/source drift')
    for p,h in build['payload_sha256'].items():R.require(R.sha(BUILD/p)==h,'private build payload drift')
    historical=R.ROOT/'research/lanes/n010-comparison-readiness/results/057-ddgi-volume-runtime-bringup.json'
    for p,h in R.read(historical)['input_sha256'].items():
        path=Path(p);path=path if path.is_absolute() else R.ROOT/path
        if path.suffix=='.spv':R.require(R.sha(path)==h,'pinned SDK SPIR-V changed');inputs[str(path)]=h
    shader_receipt=R.read(ADAPTER/'result.json')
    R.require(shader_receipt['all_pass'] and shader_receipt['gpu_executed'] is False,'adapter CPU compile missing')
    for row in shader_receipt['rows']:
        path=ADAPTER/(row['entry']+'.spv');R.require(R.sha(path)==row['shader_sha256'],'adapter SPIR-V drift');inputs[str(path)]=row['shader_sha256']
    sources=[Path(__file__).resolve(),Path(A.__file__).resolve(),PROTOCOL,R.ROOT/'scripts/run_with_vulkan.sh',
        BUILD/'result.json',TESTS/'result.json',ADAPTER/'result.json',historical,BUILD/'m001-ddgi-scene']
    for p in sources:inputs[str(p)]=R.sha(p)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R.ROOT,text=True).strip()
    for p in sources[:3]:R.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(R.ROOT))],cwd=R.ROOT)==p.read_bytes(),'commit control source/protocol first')
    return {'schema':'m001-ddgi-control-plan/1','name':name,'command':command(name),'source_commit':commit,
        'input_sha256':inputs,'previous_control_audit':previous,'reference_verification':verification,'physical_state_audit':physical,
        'gpu_executed':False,'accepted_timing':False,'heldout_quality_scoring':False}


def execute(name):
    plan,work,archive=paths(name);R.require(plan.is_file(),'prepare exact CPU plan first')
    frozen=R.read(plan);current=prepare(name)
    for key in ('name','command','input_sha256','previous_control_audit','reference_verification'):
        R.require(frozen[key]==current[key],'prepared control plan drift: '+key)
    work.mkdir(parents=True);R.write_new(work/'started.json',{'plan_sha256':R.sha(plan),'plan':frozen})
    result={'schema':'m001-ddgi-control-result/1','name':name,'command':command(name),'plan_sha256':R.sha(plan),
        'complete':False,'gpu_executed':True,'accepted_timing':False,'semantic_admission':False,'quality_admission':False,
        'classification':'OPERATIONAL_FAILURE_RETAIN_PARTIAL_NO_RETRY'}
    def limits():resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    native=None
    try:
        native=subprocess.Popen(command(name),cwd=R.ROOT,env=dict(os.environ),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                start_new_session=True,preexec_fn=limits,text=True)
        try:stdout,stderr=native.communicate(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(native.pid,signal.SIGTERM)
            try:stdout,stderr=native.communicate(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(native.pid,signal.SIGKILL);stdout,stderr=native.communicate()
            (work/'native.stdout.txt').write_text(stdout);(work/'native.stderr.txt').write_text(stderr)
            raise ValueError('180 second control timeout; retain partial, no retry')
        (work/'native.stdout.txt').write_text(stdout);(work/'native.stderr.txt').write_text(stderr)
        result['returncode']=native.returncode
        R.require(native.returncode==0 and R.read(work/'capture/complete.json')['capture_complete'],'native control incomplete')
        result.update(complete=True,classification='RAW_CONTROL_RETAINED_INDEPENDENT_AUDIT_REQUIRED')
    except Exception as error:result['error']=str(error)
    result['payload_sha256']={str(p.relative_to(work)):R.sha(p) for p in sorted(work.rglob('*')) if p.is_file()}
    R.write_new(work/'result.json',result)
    with archive.open('xb') as f:
        with tarfile.open(fileobj=f,mode='w') as t:
            t.add(plan,arcname='plan.json');t.add(work/'result.json',arcname='result.json')
    return {'name':name,'classification':result['classification'],'complete':result['complete'],
            'archive':str(archive.relative_to(R.ROOT)),'next':'STOP and independently audit; no next GPU process'}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('prepare','execute','audit'));ap.add_argument('--name',choices=CASES,required=True);args=ap.parse_args()
    if args.action=='prepare':
        d=prepare(args.name);R.write_new(paths(args.name)[0],d);print(json.dumps({'command':d['command'],'plan':str(paths(args.name)[0]),'gpu_executed':False},indent=2))
    elif args.action=='execute':print(json.dumps(execute(args.name),indent=2))
    else:
        import ddgi_control_audit as A
        print(json.dumps(A.audit(args.name),indent=2))
