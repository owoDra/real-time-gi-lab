#!/usr/bin/env python3
"""N010 preregistered full Renderer known-work sizing and eight-block calibration."""
import argparse,hashlib,json,math,os,statistics,struct,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
LANE=ROOT/'research/lanes/n010-comparison-readiness'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def quiescent():
 running=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:name=(p/'comm').read_text().strip()
  except (OSError,PermissionError):continue
  if name.startswith(('n010_rqmc','n010_cached','n008_oracle','phos-n0')):running.append(name)
 if running:raise ValueError('accepted calibration requires completed reference/GPU work: '+','.join(running))
def boundaries(lock):
 result=[]
 for cell in ('C1','C7','C6','C12'):
  dynamic=cell in ('C6','C12');base='C1' if cell in ('C1','C6') else 'C7'
  roles=['hwrt','pt-B2','pt-B8'] if dynamic else ['hwrt','software','pt-B2','pt-B8','dense-rc']
  for role in roles:result.append({'id':cell+'-'+role,'cell':cell,'base':base,'dynamic':dynamic,'role':role})
 return result
def execute(b,lock,doses,out):
 out.parent.mkdir(parents=True,exist_ok=True)
 dosefile=out.with_suffix('.doses.txt');dosefile.write_text(''.join(str(d)+'\n' for d in doses))
 env=os.environ.copy();cell=b['cell'];base=b['base'];spec=lock['cells'][cell]
 if b['role'] in ('hwrt','software'):
  binary=ROOT/'build/n009/phos-n010-capture'
  scene=ROOT/('assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf' if base=='C1' else 'out/research/n008-hdr-oracle/phase-b-states/n004-scenes/leak-medium.gltf')
  cmd=['bash','scripts/run_with_vulkan.sh',str(binary),'--scene',str(scene),'--scenario','deforming-control' if b['dynamic'] else 'static','--backend',b['role'],'--direct-profile','ulp4','--calibration-doses',str(dosefile),'--out',str(out)]
  if b['dynamic']:cmd+=['--target-state','--topology-churn']
  env['PHOS_N010_MEMORY_LEDGER']=str(out/'allocation-ledger.json')
  env['PHOS_N009_CONTRACT']=str(ROOT/'out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract')
 else:
  binary=ROOT/'build/n009/phos-n010-pixel-pt'
  cmd=['bash','scripts/run_with_vulkan.sh',str(binary),'--state',str(ROOT/lock['cells'][base]['state_directory']),
       '--spp','1' if b['role']=='dense-rc' else '1024','--vertices','8' if b['role']=='pt-B8' else '2',
       '--family','dense-rc' if b['role']=='dense-rc' else 'pixel-pt','--seed','305419896',
       '--calibration-doses',str(dosefile),'--out',str(out)]
  if b['dynamic']:cmd+=['--target-state',str(ROOT/spec['state_directory'])]
 proc=subprocess.run(cmd,env=env,text=True,capture_output=True)
 result={'boundary':b,'command':cmd,'binary_sha256':sha(binary),'returncode':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'doses_file_sha256':sha(dosefile)}
 if proc.returncode:
  (out.parent/(out.name+'.failure.json')).write_text(json.dumps(result,indent=2)+'\n');raise ValueError('failed calibration process retained')
 if (out/'frames.json').exists():samples=json.loads((out/'frames.json').read_text())['frames']
 else:samples=[json.loads(line) for line in (out/'calibration-timings.jsonl').read_text().splitlines()]
 if len(samples)!=len(doses) or any(s['dose']!=d for s,d in zip(samples,doses)):raise ValueError('sample schedule mismatch')
 payloads=[]
 for index,dose in enumerate(doses):
  directory=out/'frames'/str(index);directory=directory/'gpu' if (directory/'gpu').exists() else directory
  scratch=directory/'neutral-work.bin';data=scratch.read_bytes()
  if len(data)!=65536:raise ValueError('known-work payload shape')
  for item in (0,1,64,127,8191,16383):
   expected=item^0x4e303130
   for _ in range(dose):
    expected=(expected*1664525+1013904223)&0xffffffff;expected^=expected>>13
   if struct.unpack_from('<I',data,item*4)[0]!=expected:raise ValueError('known-work result mismatch')
  payloads.append({'image':sha(directory/'total.pfm'),'scratch':sha(scratch)})
 # Exact image identity required; retain any image divergence as a failure.
 identical=len({p['image'] for p in payloads})==1
 result.update(samples=samples,known_work_probe_validation=True,images_byte_equal=identical,payloads=payloads,
               allocation_ledger=json.loads((out/'allocation-ledger.json').read_text()),
               payload_sha256={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
 if not identical:raise ValueError('known work calibration changed image; retained output')
 return result
def schedule(dose,block):
 records=[]
 for pair in range(16):
  order='AB' if (pair+block)%2==0 else 'BA'
  for kind in (['control','effect'] if (pair+block)%2==0 else ['effect','control']):
   for arm in order:records.append({'index':len(records),'pair':pair,'warmup':pair<4,'kind':kind,'arm':arm,'order':order,'dose':dose if kind=='effect' and arm=='B' else 0})
 return records
def analysis(blocks):
 processes=[]
 for block in blocks:
  kinds={}
  for kind in ('control','effect'):
   logs=[];ab=[];ba=[]
   for pair in range(4,16):
    group=[s for s in block['tagged_samples'] if s['pair']==pair and s['kind']==kind]
    a=next(s['gpu_us'] for s in group if s['arm']=='A');b=next(s['gpu_us'] for s in group if s['arm']=='B')
    if a<=0 or b<=0:raise ValueError('nonpositive timestamp')
    value=math.log(b/a);logs.append(value);(ab if group[0]['order']=='AB' else ba).append(value)
   med=statistics.median(logs)
   kinds[kind]={'median_log_ratio':med,'ratio':math.exp(med),'order_bias_ratio':math.exp(abs(statistics.median(ab)-statistics.median(ba))),'positive_pair_fraction':sum(v>0 for v in logs)/12}
  processes.append(kinds)
 control=[p['control'] for p in processes];effect=[p['effect'] for p in processes]
 envelope=max(math.exp(abs(p['median_log_ratio'])) for p in control)
 cspan=max(p['ratio'] for p in control)/min(p['ratio'] for p in control)
 espan=max(p['ratio'] for p in effect)/min(p['ratio'] for p in effect)
 cbias=max(p['order_bias_ratio'] for p in control);ebias=max(p['order_bias_ratio'] for p in effect)
 fraction=min(p['positive_pair_fraction'] for p in effect);minimum=min(p['ratio'] for p in effect)
 gates={'control_max_absolute_ratio':envelope<=1.02,'control_span':cspan<=1.03,'control_order_bias':cbias<=1.02,'effect_span':espan<=1.05,'effect_order_bias':ebias<=1.03,'effect_positive_fraction':fraction>=.75,'effect_exceeds_control_envelope':minimum>envelope}
 return {'processes':processes,'control_envelope':envelope,'control_span':cspan,'effect_span':espan,'control_order_bias':cbias,'effect_order_bias':ebias,'minimum_positive_fraction':fraction,'minimum_effect':minimum,'gates':gates,'all_pass':all(gates.values())}
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--mode',choices=('sizing','accepted'),required=True);ap.add_argument('--lock',type=Path,required=True);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--plan',type=Path);ap.add_argument('--boundaries',nargs='+');a=ap.parse_args()
 lock=json.loads(a.lock.read_text());cohort=boundaries(lock)
 if a.boundaries:
  requested=set(a.boundaries);cohort=[b for b in cohort if b['id'] in requested]
  if {b['id'] for b in cohort}!=requested:raise ValueError('unknown calibration boundary')
 if a.work.exists():raise ValueError('refuse existing work directory')
 if a.mode=='accepted':
  if not a.plan:raise ValueError('accepted acquisition requires hashed sizing plan')
  quiescent();plan=json.loads(a.plan.read_text())
  if not plan['complete'] or any(not r['sizing_pass'] for r in plan['rows']):raise ValueError('incomplete/failed sizing plan')
  if plan['lock_sha256']!=sha(a.lock):raise ValueError('sizing lock mismatch')
 result={'schema':'n010-renderer-calibration/1','mode':a.mode,'complete':False,'all_pass':False,'lock_sha256':sha(a.lock),'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'rows':[]}
 if a.plan:result['plan_sha256']=sha(a.plan)
 for boundary in cohort:
  row={'boundary':boundary}
  if a.mode=='sizing':
   evidence=execute(boundary,lock,[0,256,1024]*3,a.work/boundary['id']/'sizing');samples=evidence['samples']
   med={dose:statistics.median(s['gpu_us'] for s in samples if s['dose']==dose) for dose in (0,256,1024)}
   inner={dose:statistics.median(s['known_work_gpu_us'] for s in samples if s['dose']==dose) for dose in (0,256,1024)}
   slopes=[(inner[d]-inner[0])/d for d in (256,1024)]
   valid=min(slopes)>0;dose=math.ceil(.2*med[0]/statistics.median(slopes)) if valid else None
   row.update(evidence=evidence,medians_us=med,known_work_medians_us=inner,amendment='4',sizing_pass=valid and dose<=10000000,frozen_dose=dose)
  else:
   sizing=next(r for r in plan['rows'] if r['boundary']['id']==boundary['id']);blocks=[]
   for block in range(8):
    quiescent();time.sleep(1);records=schedule(sizing['frozen_dose'],block)
    evidence=execute(boundary,lock,[r['dose'] for r in records],a.work/boundary['id']/f'block-{block}')
    if evidence['binary_sha256']!=sizing['evidence']['binary_sha256']:raise ValueError('sized binary changed')
    evidence['tagged_samples']=[dict(s,**{k:v for k,v in r.items() if k not in s}) for s,r in zip(evidence['samples'],records)]
    blocks.append(evidence);row.update(blocks=blocks)
    result['rows'].append(row) if block==0 else None
    a.output.write_text(json.dumps(result,indent=2)+'\n')
   row['analysis']=analysis(blocks)
  if a.mode=='sizing':result['rows'].append(row)
  a.output.write_text(json.dumps(result,indent=2)+'\n');print(boundary['id'],'done',flush=True)
 result.update(complete=True,all_pass=all(r['sizing_pass'] if a.mode=='sizing' else r['analysis']['all_pass'] for r in result['rows']))
 a.output.write_text(json.dumps(result,indent=2)+'\n')
