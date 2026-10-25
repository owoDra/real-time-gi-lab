#!/usr/bin/env python3
"""042 publication: summarize committed receipts, rehash every payload and check Lane M index/links."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'out/research/lane-m-gi-competitiveness'
LANE=ROOT/'research/lanes/lane-m-gi-competitiveness'
TARGETS=(('H01',2),('H01',8),('H02',2),('H02',8),('H03',2),('H03',8))
DEV=('m001-restir042-dev-build-1','m001-restir042-dev-smoke-1','m001-restir042-dev-build-2','m001-restir042-dev-smoke-2')


def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def need(ok,why):
    if not ok:raise ValueError('042 publication '+why)
def inventory(root):return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'result.json'}


def rehash(root):
    r=read(root/'result.json');need(inventory(root)==r['payload_sha256'],'complete payload inventory '+str(root));return r,len(r['payload_sha256'])


def envelopes(root,labels):
    rows=[]
    for label in labels:
        c=read(root/f'{label}.command.json');t=read(root/f'{label}.process.json');l=read(root/f'{label}.child-limits.json')
        need(t['returncode']==0 and t['reaped'] and not t['timed_out'] and l['cpu'][0]==c['cpu_limit'],'qualified envelope '+label)
        rows.append(dict(label=label,pid=t['pid'],cpu_seconds=c['cpu_limit'],outer_wall_seconds=c['wall_limit'],returncode=0,reaped=True,timed_out=False))
    return rows


def warm(frames,method):
    w=[x['metrics']['indirect']['nrmse'] for x in frames if x['method']==method and x['frame']>=48]
    t=[x['metrics']['total']['nrmse'] for x in frames if x['method']==method and x['frame']>=48]
    c=[x['metrics']['indirect']['nrmse'] for x in frames if x['method']==method and x['frame']==0]
    return dict(cold_indirect_nrmse_mean=sum(c)/len(c),warm_indirect_nrmse_mean=sum(w)/len(w),warm_total_nrmse_mean=sum(t)/len(t),warm_frames_passing=sum(x['quality_pass'] for x in frames if x['method']==method and x['frame']>=48))


def summaries(out):
    prep=BASE/'m001-restir042-cpu-build-v1';p,count=rehash(prep);need(p['all_pass'] and not p['gpu_executed'],'preparation')
    labels=[x['label'] for x in p['rows']];prep_env=envelopes(prep,labels)
    contracts=(prep/'new-python-contracts.stderr').read_text();need('Ran 12 tests' in contracts and contracts.rstrip().endswith('OK') and 'skipped' not in contracts,'12 executed contracts')
    j246=dict(schema='m001-restir042-cpu-preparation-summary/1',complete=True,all_pass=True,source_commit=p['source_commit'],classification=p['classification'],new_python_contracts=12,
              new_native_compilations=['restir_gi_reuse_gpu.cpp host compile+link','restir_gi_reuse_visibility.cpp UBSan -Werror'],new_hlsl_stage_compilations=5,native_cpu_input_checks_unusable_icd=6,
              exact041_producer_spirv_reused=True,qualified033_neighbor_offsets_reused=True,camera_epsilon=p['epsilon'],pinned_inputs=len(p['input_sha256']),actual_cpu_envelopes=prep_env,
              old_successful_tests_reexecuted=False,raw_receipt=str(prep/'result.json'),raw_receipt_sha256=sha(prep/'result.json'),payload_files=count)
    rows=[];payloads=count;processes=len(prep_env)
    for cell,depth in TARGETS:
        root=BASE/f'm001-restir042-{cell.lower()}-b{depth}-v1';r,n=rehash(root);payloads+=n;a,an=rehash(root/'audit');payloads+=an
        need(r['all_pass'] and r['classification']=='REUSE_CASE_AUDIT_PASS' and a['all_pass'] and a['pid']==r['numeric_process']['pid'],'case '+cell+str(depth))
        env=envelopes(root,['native','numeric']);processes+=2;q=a['quality'];frames=read(root/'audit/quality-frames.json');need(len(frames)==768,'complete per-frame metrics')
        replay=dict(record_frames=len(a['frames']),valid_pixels=a['frames'][0]['valid_pixels'],visibility_queries=a['visibility_queries'],explained_divergences=a['explained_divergences'],
                    unexplained_divergences=sum(v[s]['unexplained'] for x in a['frames'] for v in x['variants'] for s in ('temporal','spatial')),
                    shading_unstable_visibility=sum(v['shading']['unstable'] for x in a['frames'] for v in x['variants']),
                    replayed_reservoirs=sum(2*x['valid_pixels']*2 for x in a['frames']))
        need(replay['unexplained_divergences']==0,'no unexplained divergence')
        n=r['native_audit']
        rows.append(dict(cell=cell,depth=depth,classification=r['classification'],raw_receipt=str(root/'result.json'),raw_receipt_sha256=sha(root/'result.json'),audit_receipt_sha256=sha(root/'audit/result.json'),
            processes=env,true_peak_owned_bytes=n['true_peak_owned_bytes'],allocation_pairs=n['allocation_pairs'],teardown_zero=True,frames=n['frames'],dispatches=n['dispatches'],
            frame_gpu_us_mean_diagnostic=n['frame_gpu_us_mean_diagnostic'],pass_gpu_us_mean_diagnostic=n['pass_gpu_us_mean_diagnostic'],replay=replay,
            q1=dict(target_pass=q['q1_target_pass'],streams_passing=q['q1_streams_passing'],streams=[{k:s[k] for k in ('stream','q1_cold_pass','q1_warm_pass','q1_joint_pass')} for s in q['streams']]),
            q2=dict(streams_passing=q['q2_streams_passing'],nrmse_ratio_pt_over_v1=q['q2_nrmse_ratio_pt_over_v1'],streams=[{m:s[f'q2_{m}'] for m in ('pt','v1_null_trial','v0_miss_m0')}|dict(stream=s['stream']) for s in q['streams']]),
            b1=q['b1'],b2=q['b2'],per_frame_descriptive={m:warm(frames,m) for m in ('pt','v1_null_trial','v0_miss_m0')}))
    dev=[]
    for name in DEV:
        root=BASE/name;files=inventory(root)|({'result.json':sha(root/'result.json')} if (root/'result.json').exists() else {})
        dev.append(dict(directory=str(root),files=len(files),inventory_sha256=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),quality_scored=False))
    j247=dict(schema='m001-restir042-six-target-summary/1',complete=True,all_pass=True,study='042',preregistration_commits=dict(protocol='d576bc75',replay_addendum='7e9dbef3',development_disclosure='7c41269a'),
              implementation_commit=p['source_commit'],classification='RECEIVER_FRAME_REUSE_IMPLEMENTATION_PASS_6_6_NULL_TRIAL_BIAS_CONFIRMED_6_6_QUALITY_0_6',
              targets=rows,null_trial_hypothesis_holds=sum(r['b1']['h_null_holds'] for r in rows),v1_bias_within_5_percent=sum(r['b2']['v1_within_5_percent'] for r in rows),
              q1_target_passes=sum(r['q1']['target_pass'] for r in rows),q2_v1_stream_passes=sum(r['q2']['streams_passing']['v1_null_trial'] for r in rows),q2_pt_stream_passes=sum(r['q2']['streams_passing']['pt'] for r in rows),
              development_smoke=dict(gpu_processes=2,directories=dev,fixes=[dict(after='m001-restir042-dev-smoke-1',defect='host wrote RTXDI bias-correction enum 2 (PAIRWISE, unsupported for GI, behaves as BASIC) instead of registered RAY_TRACED=3',
                  detection='CPU replay W mismatch on 7/7325 stream-16 frame-0 spatial pixels with stable occluded independent visibility',fix='enum 3 for temporal and spatial; verified in registered controls audit')]),
              new_gpu_acquisitions_registered=6,new_gpu_acquisitions_development=2,total_assistant_gpu_acquisitions=204,accepted_timing=False,memory_advantage=False,architecture_promoted=False,lane_m_complete=False,
              limitations=['single AMD Radeon 8060S/RADV','static M001 heldouts only','boiling filter, sample-app final MIS and checkerboard NOT_RUN','timings are uncalibrated diagnostics','driver-private and CPU memory excluded','RAY_TRACED bias correction keeps SDK realization-dependent Jacobian domain exclusion'])
    return j246,j247,processes,payloads


def links():
    files=[ROOT/'research/status.md',ROOT/'research/roadmap.md',LANE/'README.md',*sorted((LANE/'results').glob('24[4-9]-*.md')),*sorted((LANE/'experiments').glob('042*.md'))];count=0
    for f in files:
        for target in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)',f.read_text()):
            if target.startswith('http'):continue
            need((f.parent/target).resolve().exists(),f'link {f.name}->{target}');count+=1
    index=read(LANE/'results/index.json');paths=0
    def walk(x):
        nonlocal paths
        if isinstance(x,dict):[walk(v) for v in x.values()]
        elif isinstance(x,list):[walk(v) for v in x]
        elif isinstance(x,str) and re.match(r'^(experiments|results)/',x):need((LANE/x).exists(),'index path '+x);paths+=1
    walk(index);return count,paths


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['summaries','verify']);args=parser.parse_args()
    j246,j247,processes,payloads=summaries(LANE/'results')
    if args.mode=='summaries':
        for name,value in (('246-restir-gi-reuse-cpu-preparation.json',j246),('247-restir-gi-reuse-six-targets.json',j247)):
            (LANE/'results'/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    else:
        for name,value in (('246-restir-gi-reuse-cpu-preparation.json',j246),('247-restir-gi-reuse-six-targets.json',j247)):need(read(LANE/'results'/name)==json.loads(json.dumps(value)),'published summary regenerates exactly '+name)
        count,paths=links();check=subprocess.run(['python3','scripts/research/verify.py'],cwd=ROOT,capture_output=True,text=True);need(check.returncode==0,'research check')
        diff=subprocess.run(['git','diff','--name-only','6d8b4438','HEAD','--','CMakeLists.txt','cmake','src/CMakeLists.txt'],cwd=ROOT,capture_output=True,text=True).stdout.strip()
        v=dict(schema='m001-restir042-verification/1',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),complete=True,all_pass=True,study_complete=True,
               classification=j247['classification'],lane_m_complete=False,new_gpu_acquisitions=8,registered_gpu_acquisitions=6,development_gpu_acquisitions=2,total_assistant_gpu_acquisitions=204,
               new_reference_samples=0,hdr_quality_scored=True,accepted_timing=False,architecture_promoted=False,rehashed_payloads=payloads,actual_supervised_processes=processes,actual_envelopes_qualified=processes,
               all_lane_m_index_paths=paths,markdown_links_checked=count,research_check_output=check.stdout,default_build_graph_unchanged=diff=='',default_renderer_build_and_runtime='NOT_RERUN',validation_layers='NOT_RUN',
               helper_sha256=sha(Path(__file__)))
        (LANE/'results/249-restir-gi-reuse-verification.json').write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v[k] for k in ('rehashed_payloads','actual_supervised_processes','all_lane_m_index_paths','markdown_links_checked','default_build_graph_unchanged')}))
