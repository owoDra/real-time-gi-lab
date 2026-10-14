#!/usr/bin/env python3
"""Fail-closed N010 handoff: actual eligible corpus, complete pilots and calibration."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from calibrate_renderer import boundaries,shader_hashes
ROOT=Path(__file__).resolve().parents[3]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def replay(memory):
 live={};peak=0
 for event in memory['events']:
  key=(event['device_context'],event['allocation_id'])
  if event['action']=='allocate':
   if key in live:raise ValueError('duplicate owned allocation')
   live[key]=event['bytes']
  elif event['action']=='free':
   if live.pop(key)!=event['bytes']:raise ValueError('owned allocation free size')
  else:raise ValueError('unknown allocation action')
  current=sum(live.values());peak=max(peak,current)
  if current!=event['live_bytes']:raise ValueError('ledger live sum mismatch')
 return not live and peak==memory['true_peak_owned_bytes'] and memory['teardown_zero'] and peak<=8*1024**3
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--lock',type=Path,required=True);ap.add_argument('--references',type=Path,required=True);ap.add_argument('--calibration',type=Path,required=True);ap.add_argument('--dynamic-pilots',type=Path,nargs='+',required=True);ap.add_argument('--static-pilots',type=Path,nargs='+',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 result={'schema':'n010-readiness-preflight/1','classification':'NOT_READY','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'gates':[],'inputs':{}}
 def gate(name,work):
  try:
   detail=work();passed=bool(detail)
   result['gates'].append({'name':name,'pass':passed,'detail':detail})
  except (ValueError,KeyError,OSError,AssertionError,StopIteration) as e:result['gates'].append({'name':name,'pass':False,'reason':str(e)})
 def read(p):
  d=json.loads(p.read_text());result['inputs'][str(p)]=sha(p);return d
 lock=read(a.lock)
 def refs():
  if set(lock['cells'])!={f'C{i}' for i in range(1,13)}:raise ValueError('full locked corpus required')
  for cell in lock['cells']:
   for v in (2,8):
    directory=a.references/f'{cell}_T_B{v}';q=read(directory/'qualification.json')
    if q['classification']!='STATISTICALLY_ELIGIBLE' or q['state_sha256']!=lock['cells'][cell]['state_sha256']:raise ValueError('reference not eligible/locked: '+cell)
    if len(q['levels'])<2 or not q['levels'][-1]['screen']['status']=='statistical-screen-pass':raise ValueError('missing consecutive qualification')
    for level in q['levels']:
     for name,digest in level['all_payload_sha256'].items():
      if sha(directory/name)!=digest:raise ValueError('reference payload changed')
  validation=read(ROOT/'research/lanes/n010-comparison-readiness/results/009-iid-precision-confirmation.json')
  if not(validation['complete'] and validation['all_pass']):raise ValueError('physical validation missing')
  return '24 eligible cell/transport references; payload, locked-state and physical-validation identities checked'
 gate('eligible_locked_physical_references',refs)
 def correctness():
  base=ROOT/'research/lanes/n010-comparison-readiness/results'
  replay_data=read(base/'002-gpu-key-replay.json')
  if {r['capture'] for r in replay_data['rows']}!={cell+'-'+backend for cell in ('C1','C2','C4','C5','C7') for backend in ('hwrt','software')}:raise ValueError('missing actual GPU-key replay')
  for row in replay_data['rows']:
   if not row['V1'] or row['max_absolute_error']>1e-6 or row['positivity_disagreements'] or row['scoring_exclusions']:raise ValueError('GPU-key replay gate failure')
  models=read(base/'007-c7-probe-replay-validation.json')
  if {r['backend'] for r in models['rows']}!={'hwrt','software'}:raise ValueError('missing BF-P probe model')
  for row in models['rows']:
   if not all(row['gates'][v] for v in ('V1','V2','V3','V4')) or row['V1_scoring_exclusions'] or row['scoring_mask_pixels']!=57600:raise ValueError('probe-model gate failure/exclusions')
  measured=read(base/'017-comparison-pilot-summary.json')
  if measured['historical_outcomes_revised'] or measured['comparison_exclusions']:raise ValueError('historical outcome revised/exclusion')
  for row in measured['direct_rows']:
   if row['direct']['scoring_exclusions']:raise ValueError('excluded direct pixels')
   if row['direct']['gpu_zero_reference_positive'] and row.get('remaining_disagreements')!='UNRESOLVED':raise ValueError('unreported remaining correctness disagreement')
  return 'All-pixel key/BF-P validations pass; measured direct discrepancies remain explicit and included. N009 unresolved max-relative-error-1.0 outcome is unchanged.'
 gate('correctness_validations_and_explicit_remaining_discrepancies',correctness)
 def verify_payloads(row):
  command=row['command'];directory=Path(command[command.index('--out')+1])
  if not directory.is_absolute():directory=ROOT/directory
  for name,digest in row['payload_sha256'].items():
   if sha(directory/name)!=digest:raise ValueError('pilot payload changed: '+name)
 def dynamic():
  corpus=[]
  for path in a.dynamic_pilots:
   pilot=read(path)
   if not pilot['complete']:raise ValueError('partial dynamic pilot')
   corpus+=pilot['rows']
  expected={f'C{i}' for i in (2,3,4,5,6,8,9,10,11,12)}
  if {r['cell'] for r in corpus}!=expected:raise ValueError('missing required dynamic cell')
  for cell in expected:
   roles={r['role']:r for r in corpus if r['cell']==cell}
   required={'incumbent-hwrt','incumbent-software','vanilla-traversal','pixel-pt-B2','pixel-pt-B8','dense-rc'}
   if set(roles)!=required:raise ValueError('missing dynamic comparator: '+cell)
   for role,row in roles.items():
    if row.get('classification')=='UNSUPPORTED_IN_CAPTURE_API':
     if role!='incumbent-software' or cell not in ('C6','C12'):raise ValueError('unexpected missing regime')
     continue
    verify_payloads(row)
    if row['returncode'] or not replay(row['memory']):raise ValueError('dynamic execution/memory failure')
    scores=row['scores'];frames={s['frame_index'] for s in scores}
    required_transports=[2] if role=='pixel-pt-B2' else ([8] if role=='pixel-pt-B8' else [2,8])
    if {(s['frame_index'],s['transport']) for s in scores}!={(f,'T_B'+str(v)) for f in range(5) for v in required_transports}:raise ValueError('missing source/change/recovery transport score')
    if frames!=set(range(5)):raise ValueError('missing source/change/recovery frame')
    for s in scores:
     if s['scoring_exclusions'] not in (0,[]) or not s['complete_physical_scene_bytes_equal']:raise ValueError('scoring excluded/unmatched physical state')
     if s['pilot_quality_target'] not in ('PASS','FAIL'):raise ValueError('unknown quality classification')
  return 'Complete executed cohort and every frame classified; quality failures retained as losses'
 gate('whole_corpus_dynamic_quality_memory_pilot',dynamic)
 def static():
  cells=set()
  for path in a.static_pilots:
   pilot=read(path)
   if not pilot['complete']:raise ValueError('partial static pilot')
   cell=pilot['cell'];cells.add(cell)
   levels={(r['vertices'],r['spp']) for r in pilot['rows']}
   if len(pilot['rows'])!=12:raise ValueError('duplicate/extra ladder rows')
   if levels!={(v,n) for v in (2,8) for n in (1,4,16,64,256,1024)}:raise ValueError('budget ladder incomplete')
   if cell in ('C7','C8','C9') and any(not any(r['vertices']==v and r['quality']['pilot_quality_target']=='PASS' for r in pilot['rows']) for v in (2,8)):raise ValueError('no demonstrated matching budget in tuning pilot')
   for r in pilot['rows']:
    verify_payloads(r)
    if r['returncode'] or not replay(r['allocation_ledger']):raise ValueError('static execution/memory failure')
    if r['quality']['scoring_exclusions'] not in (0,[]):raise ValueError('excluded static pixels')
  if not {'C1','C7','C8','C9'}<=cells:raise ValueError('missing declared static budget selection pilot')
  return 'All fixed budget levels retained; passing budgets selected with original quality thresholds'
 gate('fixed_ladders_and_quality_selection',static)
 def calibration():
  data=read(a.calibration)
  if data['mode']!='accepted' or not data['complete'] or not data['all_pass']:raise ValueError('accepted timing capability not demonstrated')
  if data['lock_sha256']!=sha(a.lock):raise ValueError('calibration locked corpus mismatch')
  rows={r['boundary']['id']:r for r in data['rows']}
  if set(rows)!={b['id'] for b in boundaries(lock)}:raise ValueError('missing actual Renderer boundary')
  for row in rows.values():
   if len(row['blocks'])!=8 or not row['analysis']['all_pass']:raise ValueError('block count/gate failure')
   for block in row['blocks']:
    if len(block['tagged_samples'])!=64 or not block['images_byte_equal'] or not block['known_work_probe_validation'] or not replay(block['allocation_ledger']):raise ValueError('invalid calibrated sample block')
    role=row['boundary']['role'];binary=ROOT/('build/n009/phos-n010-capture' if role in ('hwrt','software') else 'build/n009/phos-n010-pixel-pt')
    if block['binary_sha256']!=sha(binary) or block['shader_sha256']!=shader_hashes():raise ValueError('current comparator differs from calibrated binary')
  return 'Actual complete boundaries pass unchanged eight-process control/effect gates'
 gate('demonstrated_full_renderer_timing_capability',calibration)
 def provenance():
  data=read(ROOT/'research/lanes/n010-comparison-readiness/results/021-ddgi-source-provenance.json')
  sdk=ROOT/'out/research/n010-comparison-readiness/external/RTXGI-DDGI'
  for name,digest in data['source_files'].items():
   if sha(sdk/name)!=digest:raise ValueError('external comparator source changed')
  if data['cuda_required'] or data['backend']!='Vulkan':raise ValueError('unsupported AMD comparator')
  return 'DDGI source and Vulkan integration boundary specified; actual DDGI qualification required before its Lane M campaign'
 gate('additional_family_source_and_supported_device_boundary',provenance)
 if all(g['pass'] for g in result['gates']):result['classification']='READY_FOR_LANE_M_FIRST_COHORT'
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['classification'])
 raise SystemExit(0 if result['classification']=='READY_FOR_LANE_M_FIRST_COHORT' else 2)
