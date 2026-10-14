#!/usr/bin/env python3
"""Amendment 3: exact existing control/reference payload and counter equality."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 a.work.mkdir(parents=True,exist_ok=False)
 old=ROOT/'build/n010-cpu/n010_rqmc_oracle';new=ROOT/'build/n010-cpu/n010_cached_oracle';net=ROOT/'out/research/n010-comparison-readiness/sobol16x262144.bin'
 result={'schema':'n010-cached-oracle-equivalence/1','complete':False,'all_pass':False,'original_binary_sha256':sha(old),'cached_binary_sha256':sha(new),'sobol_table_sha256':sha(net),'amendment':'3','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'generated_source_sha256':{p.name:sha(p) for p in (ROOT/'out/research/n010-comparison-readiness/cached-oracle-source').glob('*') if p.is_file()},'rows':[]}
 controls=ROOT/'out/research/n010-comparison-readiness/sampler-validation-v1/rqmc'
 jobs=[(p.stem.replace('.meta',''),p,p.with_name(p.name.replace('.meta.json','.n008')),controls/p.name.replace('.meta.json','')) for p in sorted(controls.glob('*.meta.json'))]
 refs=ROOT/'out/research/n010-comparison-readiness/references-v1'
 for cell in ('C1_T_B2','C7_T_B2','C7_T_B8'):
  d=refs/cell;jobs.append((cell,d/'n8192.meta.json',d/'scene.n008',d/'o.n8192'))
 for name,meta_path,scene,prefix in jobs:
  m=json.loads(meta_path.read_text());out=a.work/name
  cmd=[str(new),'--net',str(net),'--scene',str(scene),'--out',str(out),'--seeds',','.join(map(str,m['seeds'])),'--spp',str(m['spp']),'--threads','8']
  start=time.monotonic();proc=subprocess.run(cmd,text=True,capture_output=True,check=True);fresh=json.loads(proc.stdout)
  (a.work/(name+'.meta.json')).write_text(json.dumps(fresh,indent=2)+'\n')
  payloads=[]
  for seed_index in range(4):
   for ext in ('f64','emission.pfm','direct.pfm','indirect.pfm','total.pfm'):
    left=Path(str(prefix)+f'.s{seed_index}.{ext}');right=Path(str(out)+f'.s{seed_index}.{ext}')
    payloads.append({'payload':f'.s{seed_index}.{ext}','old_sha256':sha(left),'new_sha256':sha(right),'byte_equal':left.read_bytes()==right.read_bytes()})
  keys=('seed','primary_hits','shadow_tests','shadow_blocked','backface_absorbed')
  counters=all(all(x[k]==y[k] for k in keys) for x,y in zip(m['runs'],fresh['runs']))
  passed=counters and all(p['byte_equal'] for p in payloads)
  result['rows'].append({'name':name,'original_metadata_sha256':sha(meta_path),'scene_sha256':sha(scene),'command':cmd,'wall_seconds_diagnostic':time.monotonic()-start,'counters_equal':counters,'all_pass':passed,'payloads':payloads})
  a.output.write_text(json.dumps(result,indent=2)+'\n');print(name,'PASS' if passed else 'FAIL',flush=True)
  if not passed:raise SystemExit('equivalence failure retained; cached oracle ineligible')
 result.update(complete=True,all_pass=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
