#!/usr/bin/env python3
"""Plan 058: low-priority fixed-grid diagnosis using the exact 193 binary."""
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

import numpy as np

import diagnose_readiness_bottlenecks as D
from run_primary_direction_sequence import require_no_other_research_worker

WORK=D.OUT/'fixed-grid-scramble-diagnosis-v1'
TARGET=D.RESULTS/'195-fixed-grid-scramble-diagnosis.json'
PLAN=D.RESULTS.parent/'experiments/058-fixed-grid-and-short-boundary-diagnostics.md'


def main():
    if WORK.exists() or TARGET.exists():raise ValueError('refuse existing grid diagnostic')
    require_no_other_research_worker()
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    for p in (Path(__file__).resolve(),PLAN,Path(D.__file__).resolve(),
              D.ROOT/'scripts/research/n010_reference_sampling/run_primary_direction_sequence.py'):
        D.read_bytes(p)
    proof=D.read_json(D.RESULTS/'193-selected-bounce-path-diagnosis.json')
    if not proof['complete']:raise ValueError('completed original instrumentation proof required')
    if not all(v['selected_retained_mean_second_bit_exact'] for v in proof['variants'] if v['variant'] in ('original','guided')):
        raise ValueError('bit-exact retained reconstruction required')
    nested=next(r for r in proof['variants'] if r['variant']=='nested')
    if not nested['whole_header_instrumentation_inverse_exact']:raise ValueError('instrumentation proof absent')
    for name,h in nested['payload_sha256'].items():D.read_bytes(Path(name),h)
    binary=next(Path(p) for p in nested['payload_sha256'] if p.endswith('/n010_bounce_diagnostic'))
    D.read_bytes(D.RESULTS/'194-posthoc-depth-weight-and-rqmc-interpretation.json')
    net=D.OUT/'sobol16x262144.bin'
    original_dir=D.OUT/'references-recovery-sponza-v1/C1_T_B8'
    scene=original_dir/'scene.n008'
    D.read_bytes(net);D.read_bytes(scene)
    qualification=D.read_json(original_dir/'qualification.json')
    original,original_second=D.load_level(original_dir,qualification,8192)
    failed=D.read_json(D.RESULTS/'180-primary-direction-second-stop-bounded-feasibility.json')
    if not failed['complete'] or failed['all_pass']:raise ValueError('terminal failed 180 required')
    guided=[];guided_second=[]
    for i,seed in enumerate(D.SEEDS):
        p=D.OUT/f'primary-direction-feasibility-recovery-v3/o.n8192.s{i}.f64'
        m,s=D.sidecar(p,failed['levels'][0]['payload_sha256'][f'.s{i}.f64'],8192,seed)
        guided.append(m);guided_second.append(s)
    grid=[(int((i+.5)*320/16),int((j+.5)*180/16)) for j in range(16) for i in range(16)]
    WORK.mkdir();pixels=WORK/'pixels.txt'
    pixels.write_text(''.join(f'{x} {y}\n' for x,y in grid))
    result={'schema':'n010-fixed-grid-scramble-diagnosis/1','complete':False,
        'classification':'DIAGNOSTIC_ACQUIRING_NO_ADMISSION','gpu_run':False,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'input_sha256':D.INPUTS,'pixels':grid,'spp':8192,'seeds':list(D.SEEDS),
        'reference_admission':False,'attempt':{},'variants':[]}
    def save():TARGET.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save();data_path=WORK/'data.json';receipt=WORK/'native-resource-limits.json'
    command=[str(binary),str(net),str(scene),str(pixels),str(data_path)]
    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(220,220))
        resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,)*2)
        receipt.write_text(json.dumps({'pid':os.getpid(),
            'start_ticks':int((Path('/proc')/str(os.getpid())/'stat').read_text().rsplit(')',1)[1].split()[19]),
            'cpu':list(resource.getrlimit(resource.RLIMIT_CPU)),
            'address_space':list(resource.getrlimit(resource.RLIMIT_AS)),
            'cpu_affinity':sorted(os.sched_getaffinity(0)),
            'nice':os.getpriority(os.PRIO_PROCESS,0),'command':command})+'\n')
    try:
        started=time.monotonic()
        result['attempt']={'command':command,'elapsed_limit_seconds':300};save()
        try:
            proc=subprocess.run(command,capture_output=True,text=True,timeout=300,preexec_fn=limits)
        except subprocess.TimeoutExpired as error:
            (WORK/'native.stdout').write_bytes(error.stdout or b'')
            (WORK/'native.stderr').write_bytes(error.stderr or b'')
            raise ValueError('elapsed guard; retained partials, no retry') from error
        (WORK/'native.stdout').write_text(proc.stdout);(WORK/'native.stderr').write_text(proc.stderr)
        result['attempt'].update(returncode=proc.returncode,elapsed=time.monotonic()-started,
            resource_receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest())
        save()
        if proc.returncode:raise ValueError('native diagnostic failed; no retry')
        actual=json.loads(D.read_bytes(receipt))
        if actual['cpu']!=[220]*2 or actual['address_space']!=[4*1024**3]*2 or len(actual['cpu_affinity'])!=1 or actual['nice']!=15:
            raise ValueError('actual low-load resource receipt differs')
        rows=json.loads(D.read_bytes(data_path))
        if len(rows)!=len(grid)*4 or {(r['x'],r['y'],r['seed']) for r in rows}!={(x,y,seed) for x,y in grid for seed in D.SEEDS}:
            raise ValueError('grid/seeds scope differs')
        mean=np.array([[next(r['mean'] for r in rows if (r['x'],r['y'])==p and r['seed']==seed)
                        for p in grid] for seed in D.SEEDS]).reshape(4,256,4,3)
        second=np.array([[next(r['second'] for r in rows if (r['x'],r['y'])==p and r['seed']==seed)
                          for p in grid] for seed in D.SEEDS]).reshape(4,256,4,3)
        coords=tuple(np.array(a) for a in zip(*[(y,x) for x,y in grid]))
        for name,m,s in (('original',original[:,coords[0],coords[1]],original_second[:,coords[0],coords[1]]),
                         ('guided',np.stack(guided)[:,coords[0],coords[1]],np.stack(guided_second)[:,coords[0],coords[1]]),
                         ('nested',mean,second)):
            if not np.isfinite(m).all() or not np.isfinite(s).all() or (m<0).any() or (s<0).any():raise ValueError('invalid grid moments')
            luminance=m[...,2,:]@D.LUMA
            result['variants'].append({'variant':name,
                'indirect_replicate_variance_sum':float(np.var(luminance,axis=0,ddof=1).sum()),
                'max_pairwise_indirect_p99':D.pairwise_p99(luminance),
                'mean_path_variance_sum':float(np.maximum(s[...,2,0]-m[...,2,0]**2,0).mean(0).sum())})
        for p,h in list(D.INPUTS.items()):D.read_bytes(Path(p),h)
        result.update(complete=True,classification='DIAGNOSTIC_COMPLETE_NO_ADMISSION',
            warning='Fixed 256-pixel C1 grid at one level only; no whole-image or other-state feasibility, '
                    'reference qualification, powered superiority claim or timing acceptance',
            tests='NOT_RUN; scientific diagnostic only')
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        result.update(complete=False,classification='OPERATIONAL_FAILURE_PARTIALS_RETAINED',failure=str(error))
    save()
    print(json.dumps({k:result[k] for k in ('complete','classification','attempt','variants')},indent=2))
    raise SystemExit(0 if result['complete'] else 2)


if __name__=='__main__':main()
