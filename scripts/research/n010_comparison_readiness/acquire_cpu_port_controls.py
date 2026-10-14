#!/usr/bin/env python3
"""Retain original CPU low-dose controls for every locked state/transport."""
import argparse
import ctypes
import json
from pathlib import Path
import resource
import subprocess
import numpy as np
import qualify_references as Q
from reference_provenance import ROOT,RESULTS,sha,physical_proof

def limits():
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(900,900))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.work.exists() or args.output.exists():raise ValueError('refuse existing CPU control acquisition')
    ctypes.CDLL(None).prctl(15,b'n010_cpu_check',0,0,0)
    lock_path=RESULTS/'016-corpus-state-lock.json';lock=json.loads(lock_path.read_text())
    if set(lock['cells'])!={f'C{i}' for i in range(1,13)}:raise ValueError('complete corpus required')
    inputs={};physical_proof(inputs)
    paths=[Q.BINARY,Q.NET,lock_path,Path(__file__),Path(Q.__file__),Path(Q.L.__file__),
        RESULTS.parent/'experiments/020-gpu-reference-all-state-and-prefix-plan.md']
    inputs.update({str(p.resolve()):sha(p) for p in paths})
    args.work.mkdir(parents=True)
    result={'schema':'n010-all-state-cpu-port-controls/1','complete':False,'all_pass':False,
        'gpu_run':False,'eligible_for_references':False,'spp':16,'threads':4,
        'seeds':list(Q.L.N007_SEEDS),'input_sha256':inputs,'rows':[],
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'limits':{'address_space_bytes':4*1024**3,'cpu_seconds':900,'elapsed_seconds':900},
        'scope':'Whole locked 24-state/transport original CPU numerical controls. No statistical reference qualification or GPU performance claim.'}
    def save():args.output.write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        for cell in sorted(lock['cells'],key=lambda c:int(c[1:])):
            state=Q.L.read_state(ROOT/lock['cells'][cell]['state_directory'])
            if state['sha256']!=lock['cells'][cell]['state_sha256']:raise ValueError('locked state changed')
            for vertices in (2,8):
                if any(sha(Path(p))!=digest for p,digest in inputs.items()):raise ValueError('original numerical control dependency changed')
                name=f'{cell}_T_B{vertices}';out=args.work/name;out.mkdir();scene=Q.scene_for_state(state,vertices)
                path=out/'scene.n008';path.write_text(scene.text())
                command=[str(Q.BINARY),'--net',str(Q.NET),'--scene',str(path.resolve()),'--out',str((out/'o').resolve()),
                    '--seeds',','.join(map(str,Q.L.N007_SEEDS)),'--spp','16','--threads','4']
                row={'cell':cell,'vertices':vertices,'directory':str(out.resolve()),'state_sha256':state['sha256'],
                    'scene_sha256':sha(path),'command':command,'pass':False};result['rows'].append(row);save()
                try:
                    proc=subprocess.run(command,text=True,capture_output=True,timeout=900,preexec_fn=limits)
                    (out/'stdout.json').write_text(proc.stdout);(out/'stderr.log').write_text(proc.stderr);row['returncode']=proc.returncode
                except subprocess.TimeoutExpired:
                    row['failure']='bounded elapsed guard';raise ValueError('original CPU control timed out')
                if proc.returncode:raise ValueError('original CPU control failed')
                meta=json.loads(proc.stdout)
                if (meta['spp'],meta['seeds'],meta['scene_sha256'],meta['geometry_sha256'])!=(16,list(Q.L.N007_SEEDS),sha(path),scene.geometry_sha256()):raise ValueError('CPU output scene/geometry/schedule mismatch')
                meta.update(binary_sha256=sha(Q.BINARY),net_sha256=sha(Q.NET),source_commit=result['source_commit'])
                (out/'meta.json').write_text(json.dumps(meta,indent=2)+'\n')
                finite=True
                for i,seed in enumerate(Q.L.N007_SEEDS):
                    data=Q.L.read_sidecar(out/f'o.s{i}.f64')
                    if (data['width'],data['height'],data['spp'],data['seed'])!=(state['width'],state['height'],16,seed):raise ValueError('CPU sidecar header mismatch')
                    finite=finite and bool(np.isfinite(data['mean']).all() and np.isfinite(data['m2']).all())
                row.update(all_finite=finite,pass_=finite,payload_sha256={p.name:sha(p) for p in out.iterdir() if p.is_file()})
                row['pass']=finite;save();print(name,'PASS' if finite else 'FAIL',flush=True)
                if not finite:raise ValueError('CPU numerical control nonfinite')
        result['all_pass']=len(result['rows'])==24 and all(r['pass'] for r in result['rows'])
        if any(sha(Path(p))!=digest for p,digest in inputs.items()):raise ValueError('frozen control input changed')
    except (ValueError,OSError,KeyError,AssertionError) as error:
        result['failure']=str(error);result['all_pass']=False
    result['complete']=True;save();print('ALL-STATE CPU CONTROL PASS' if result['all_pass'] else 'ALL-STATE CPU CONTROL FAIL',flush=True)
    raise SystemExit(0 if result['all_pass'] else 2)
