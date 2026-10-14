#!/usr/bin/env python3
"""Amendment 6 exact 8192->16384 prefix continuation against original outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3]
RESULTS=ROOT/'research/lanes/n010-comparison-readiness/results'
KEYS=('primary_hits','shadow_tests','shadow_blocked','backface_absorbed')
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--threads',type=int,default=8)
    parser.add_argument('--wait-for-cache-proof',action='store_true')
    args=parser.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing equivalence acquisition')
    proof_path=RESULTS/'022-cached-oracle-equivalence.json'
    while True:
        try:
            proof=json.loads(proof_path.read_text())
        except (FileNotFoundError,json.JSONDecodeError):
            proof={}
        if proof.get('complete'):
            if not proof['all_pass']:
                raise ValueError('cached oracle proof failed')
            break
        if not args.wait_for_cache_proof:
            raise ValueError('cached oracle proof incomplete')
        # Waiting for an independently running acquisition is not a passing proof.
        active=False
        for path in Path('/proc').iterdir():
            if path.name.isdigit():
                try:
                    active=active or (path/'comm').read_text().strip().startswith('n010_cached_')
                    words=(path/'cmdline').read_bytes().split(b'\0')
                    active=active or any(Path(word.decode(errors='replace')).name=='validate_cached_oracle.py' for word in words if word)
                except OSError:
                    pass
        if not active:
            raise ValueError('cached proof incomplete and its acquisition is not running')
        time.sleep(30)
    original=ROOT/'build/n010-cpu/n010_rqmc_oracle'
    cached=ROOT/'build/n010-cpu/n010_cached_oracle'
    binary=ROOT/'build/n010-cpu/n010_incremental_oracle'
    net=ROOT/'out/research/n010-comparison-readiness/sobol16x262144.bin'
    if proof['original_binary_sha256']!=sha(original) or proof['cached_binary_sha256']!=sha(cached) or proof['sobol_table_sha256']!=sha(net):
        raise ValueError('cached proof executable/sampler identity mismatch')
    physical_path=RESULTS/'009-iid-precision-confirmation.json'
    physical=json.loads(physical_path.read_text())
    if not physical['complete'] or not physical['all_pass'] or physical['binary_sha256']!=sha(original) or physical['sobol_table_sha256']!=sha(net):
        raise ValueError('original physical validation mismatch')
    old_source=ROOT/'out/research/n010-comparison-readiness/cached-oracle-source'
    new_source=ROOT/'out/research/n010-comparison-readiness/incremental-oracle-source-v1'
    for name,digest in proof['generated_source_sha256'].items():
        if sha(old_source/name)!=digest:
            raise ValueError('cached proof generated source changed')
    old=(old_source/'n010_rqmc_oracle.hpp').read_text()
    new=(new_source/'n010_rqmc_oracle.hpp').read_text()
    if old.split('    std::vector<PixelStats> render(')[0]!=new.split('    std::vector<PixelStats> render(')[0] or old[old.index('    const Bvh& bvh()'): ]!=new[new.index('    const Bvh& bvh()'): ]:
        raise ValueError('physical transport/intersection/RNG changed outside render continuation')
    args.work.mkdir(parents=True)
    binary_sha=sha(binary)
    result={'schema':'n010-incremental-oracle-equivalence/1','amendment':'6',
            'complete':False,'all_pass':False,'cached_equivalence_sha256':sha(proof_path),
            'physical_validation_sha256':sha(physical_path),
            'original_binary_sha256':sha(original),'incremental_binary_sha256':binary_sha,
            'net_sha256':sha(net),'physical_transport_source_bytes_equal':True,
            'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'generated_source_sha256':{path.name:sha(path) for path in sorted(new_source.glob('*')) if path.is_file()},
            'script_sha256':sha(Path(__file__)),'rows':[]}
    refs=ROOT/'out/research/n010-comparison-readiness/references-v1'
    for cell in ('C1_T_B2','C7_T_B2','C7_T_B8'):
        directory=refs/cell
        previous_path=directory/'n8192.meta.json'
        target_path=directory/'n16384.meta.json'
        previous=json.loads(previous_path.read_text())
        target=json.loads(target_path.read_text())
        scene=directory/'scene.n008'
        if previous['scene_sha256']!=sha(scene) or target['scene_sha256']!=sha(scene) or previous['binary_sha256']!=sha(original) or target['binary_sha256']!=sha(original):
            raise ValueError('original reference metadata identity mismatch')
        if previous['spp']!=8192 or target['spp']!=16384 or previous['seeds']!=target['seeds']:
            raise ValueError('original prefix seed/level mismatch')
        counter_text=';'.join(','.join(str(run[key]) for key in KEYS) for run in previous['runs'])
        out=args.work/cell
        command=[str(binary),'--net',str(net),'--scene',str(scene),'--out',str(out),
                 '--seeds',','.join(map(str,target['seeds'])),'--spp','16384','--threads',str(args.threads),
                 '--resume-prefix',str(directory/'o.n8192'),'--resume-spp','8192',
                 '--resume-counters',counter_text]
        prefix_hashes={path.name:sha(path) for path in sorted(directory.glob('o.n8192.*'))}
        started=time.monotonic()
        process=subprocess.run(command,text=True,capture_output=True)
        (args.work/(cell+'.stdout.json')).write_text(process.stdout)
        (args.work/(cell+'.stderr.log')).write_text(process.stderr)
        row={'cell':cell,'command':command,'returncode':process.returncode,
             'previous_metadata_sha256':sha(previous_path),'target_metadata_sha256':sha(target_path),
             'prefix_payload_sha256':prefix_hashes,'wall_seconds_diagnostic':time.monotonic()-started,
             'all_pass':False}
        if process.returncode==0:
            fresh=json.loads(process.stdout)
            payloads=[]
            for i in range(4):
                for suffix in ('f64','emission.pfm','direct.pfm','indirect.pfm','total.pfm'):
                    left=Path(str(directory/'o.n16384')+f'.s{i}.{suffix}')
                    right=Path(str(out)+f'.s{i}.{suffix}')
                    payloads.append({'payload':f'.s{i}.{suffix}','expected_sha256':sha(left),
                                     'actual_sha256':sha(right),'byte_equal':left.read_bytes()==right.read_bytes()})
            left=directory/'o.n16384.hits';right=Path(str(out)+'.hits')
            payloads.append({'payload':'.hits','expected_sha256':sha(left),'actual_sha256':sha(right),
                             'byte_equal':left.read_bytes()==right.read_bytes()})
            counters=all(all(a[key]==b[key] for key in ('seed',)+KEYS) for a,b in zip(target['runs'],fresh['runs']))
            row.update(payloads=payloads,counters_equal=counters,
                       all_pass=counters and len(fresh['runs'])==4 and all(value['byte_equal'] for value in payloads))
        if prefix_hashes!={path.name:sha(path) for path in sorted(directory.glob('o.n8192.*'))} or sha(binary)!=binary_sha:
            raise ValueError('input or binary changed during prefix validation')
        result['rows'].append(row)
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        print(cell,'PASS' if row['all_pass'] else 'FAIL',flush=True)
        if not row['all_pass']:
            raise SystemExit('prefix equivalence failed; variant remains ineligible')
    result.update(complete=True,all_pass=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
