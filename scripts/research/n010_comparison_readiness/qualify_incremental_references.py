#!/usr/bin/env python3
"""Qualify every frozen level using an exact, proved prefix continuation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
import qualify_references as Q

ROOT=Q.ROOT
RESULTS=ROOT/'research/lanes/n010-comparison-readiness/results'
BINARY=ROOT/'build/n010-cpu/n010_incremental_oracle'
KEYS=('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def dependencies():
    names=('009-iid-precision-confirmation.json','022-cached-oracle-equivalence.json','050-incremental-oracle-equivalence.json')
    values=[json.loads((RESULTS/name).read_text()) for name in names]
    if any(not value.get('complete') or not value.get('all_pass') for value in values):
        raise ValueError('physical/cache/incremental proof is not complete/PASS')
    physical,cached,incremental=values
    if physical['binary_sha256']!=sha(Q.BINARY) or physical['sobol_table_sha256']!=sha(Q.NET):
        raise ValueError('physical sampler validation identity mismatch')
    if cached['original_binary_sha256']!=sha(Q.BINARY) or cached['sobol_table_sha256']!=sha(Q.NET):
        raise ValueError('cached proof original/sampler identity mismatch')
    if cached['cached_binary_sha256']!=sha(ROOT/'build/n010-cpu/n010_cached_oracle'):
        raise ValueError('cached proof binary changed')
    if incremental['incremental_binary_sha256']!=sha(BINARY) or incremental['net_sha256']!=sha(Q.NET):
        raise ValueError('incremental proof binary/sampler identity mismatch')
    if incremental['cached_equivalence_sha256']!=sha(RESULTS/names[1]) or incremental['physical_validation_sha256']!=sha(RESULTS/names[0]):
        raise ValueError('incremental proof dependency mismatch')
    return {name:sha(RESULTS/name) for name in names}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock',type=Path,required=True)
    parser.add_argument('--cells',nargs='+',required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--threads',type=int,default=32)
    args=parser.parse_args()
    proofs=dependencies()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing incremental acquisition')
    if args.threads<1:
        raise ValueError('threads must be positive')
    lock=json.loads(args.lock.read_text())
    if len(set(args.cells))!=len(args.cells) or not set(args.cells)<=set(lock['cells']):
        raise ValueError('duplicate or unknown cell')
    args.work.mkdir(parents=True)
    identities={'binary':sha(BINARY),'net':sha(Q.NET),'lock':sha(args.lock),
                'script':sha(Path(__file__)),'qualification_helpers':sha(Path(Q.__file__))}
    result={'schema':'n010-incremental-reference-qualification/1','amendment':'6',
            'complete':False,'proof_sha256':proofs,'input_sha256':identities,'cells':[]}
    def frozen():
        if proofs!=dependencies() or identities!={'binary':sha(BINARY),'net':sha(Q.NET),'lock':sha(args.lock),
                'script':sha(Path(__file__)),'qualification_helpers':sha(Path(Q.__file__))}:
            raise ValueError('acquisition dependencies changed')
    for cell in args.cells:
        state=Q.L.read_state(ROOT/lock['cells'][cell]['state_directory'])
        if state['sha256']!=lock['cells'][cell]['state_sha256']:
            raise ValueError('locked state mismatch: '+cell)
        for transport,vertices in (('T_B2',2),('T_B8',8)):
            out=args.work/f'{cell}_{transport}'
            out.mkdir()
            scene=Q.scene_for_state(state,vertices)
            scene_path=out/'scene.n008'
            scene_path.write_text(scene.text())
            levels,manifests=[],[]
            previous=None
            for spp in Q.LEVELS:
                frozen()
                prefix=out/f'o.n{spp}'
                command=[str(BINARY),'--net',str(Q.NET),'--scene',str(scene_path),'--out',str(prefix),
                         '--seeds',','.join(map(str,Q.L.N007_SEEDS)),'--spp',str(spp),'--threads',str(args.threads)]
                old_payloads={}
                if previous:
                    old_spp=previous['spp']
                    old_payloads={path.name:sha(path) for path in sorted(out.glob(f'o.n{old_spp}.*'))}
                    if previous['all_payload_sha256']!=old_payloads:
                        raise ValueError('previous prefix payload changed')
                    counters=';'.join(','.join(str(run[key]) for key in KEYS) for run in previous['runs'])
                    command+=['--resume-prefix',str(out/f'o.n{old_spp}'),'--resume-spp',str(old_spp),'--resume-counters',counters]
                attempt={'command':command,'input_sha256':identities,'proof_sha256':proofs,
                         'sample_interval':[previous['spp'] if previous else 0,spp],
                         'previous_payload_sha256':old_payloads}
                (out/f'n{spp}.attempt.json').write_text(json.dumps(attempt,indent=2)+'\n')
                start=time.monotonic()
                process=subprocess.run(command,text=True,capture_output=True)
                (out/f'n{spp}.stdout.json').write_text(process.stdout)
                (out/f'n{spp}.stderr.log').write_text(process.stderr)
                if process.returncode:
                    raise ValueError('incremental acquisition failed; retained without retry')
                fresh=json.loads(process.stdout)
                if fresh['spp']!=spp or fresh['seeds']!=list(Q.L.N007_SEEDS) or fresh['scene_sha256']!=sha(scene_path) or fresh['geometry_sha256']!=scene.geometry_sha256():
                    raise ValueError('incremental output scene/level/seed identity mismatch')
                fresh.update(binary_sha256=sha(BINARY),net_sha256=sha(Q.NET),
                             computational_variant='exact-prefix-continuation',proof_sha256=proofs,
                             source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                             wall_seconds_diagnostic=time.monotonic()-start,
                             all_payload_sha256={path.name:sha(path) for path in sorted(out.glob(f'o.n{spp}.*'))},
                             sample_interval=attempt['sample_interval'],previous_payload_sha256=old_payloads)
                if previous:
                    fresh['previous_metadata_sha256']=sha(out/f'n{previous["spp"]}.meta.json')
                    if old_payloads!={path.name:sha(path) for path in sorted(out.glob(f'o.n{previous["spp"]}.*'))}:
                        raise ValueError('previous prefix changed during continuation')
                (out/f'n{spp}.meta.json').write_text(json.dumps(fresh,indent=2)+'\n')
                manifests.append({'spp':spp,'references':[{'seed':seed,
                    'path':Path(str(prefix)+f'.s{i}.total.pfm').name,
                    'sha256':sha(Path(str(prefix)+f'.s{i}.total.pfm'))} for i,seed in enumerate(Q.L.N007_SEEDS)]})
                manifest={'schema_version':1,'source_commit':fresh['source_commit'],
                          'scene_sha256':sha(scene_path),'frame_state_sha256':state['sha256']['frame'],'levels':manifests}
                manifest_path=out/f'screen-n{spp}.json'
                manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
                screen=Q.assess(manifest_path)
                runs=[Q.L.read_sidecar(Path(str(prefix)+f'.s{i}.f64')) for i in range(4)]
                if any(run['seed']!=seed or run['spp']!=spp for run,seed in zip(runs,Q.L.N007_SEEDS)):
                    raise ValueError('f64 replicate seed/level mismatch')
                means=np.stack([run['mean'] for run in runs])
                levels.append({'spp':spp,'screen':screen,'geometry_hash_match':True,
                    'components_union_positive':{key:int((means[...,j,:].max(-1)>0).any(0).sum()) for j,key in enumerate(Q.L.COMPONENTS)},
                    'replicate_means_se_max':float((means.std(0,ddof=1)/2).max()),
                    'all_payload_sha256':fresh['all_payload_sha256'],
                    'metadata_sha256':sha(out/f'n{spp}.meta.json')})
                row={'cell':cell,'transport':transport,'state_sha256':state['sha256'],
                     'scene_sha256':sha(scene_path),'levels':levels,'proof_sha256':proofs,
                     'computational_variant':'exact-prefix-continuation',
                     'classification':'STATISTICALLY_ELIGIBLE' if screen['status']=='statistical-screen-pass' else 'INELIGIBLE'}
                (out/'qualification.json').write_text(json.dumps(row,indent=2,allow_nan=False)+'\n')
                print(cell,transport,spp,screen['status'],flush=True)
                previous=fresh
                if row['classification']=='STATISTICALLY_ELIGIBLE':
                    break
            result['cells'].append(row)
            args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    frozen()
    result['complete']=True
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
