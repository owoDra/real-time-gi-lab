#!/usr/bin/env python3
"""Continue the frozen N010 pilot once existing references qualify; no retries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from calibrate_renderer import quiescent, shader_hashes

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT/'scripts/research/n010_comparison_readiness'
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--references', type=Path, required=True)
    parser.add_argument('--lock', type=Path, required=True)
    args = parser.parse_args()
    args.work = args.work.resolve()
    if args.work.exists():
        raise ValueError('refuse existing continuation; inspect retained attempt before resuming')
    # Every output has a single acquisition. Failed/partial calibration is never retried here.
    outputs = {number:RESULTS/name for number,name in {
        29:'029-full-renderer-calibration.json',
        43:'043-c1-b8-pt-quality-ladder.json',
        44:'044-c1-complete-pt-quality-ladder.json',
        46:'046-calibration-quiet-sizing.json',
        47:'047-readiness-preflight.json',
        48:'048-sponza-dynamic-cohort.json',
    }.items()}
    if any(path.exists() for path in outputs.values()):
        raise ValueError('continuation result already exists; refuse overwrite')
    args.work.mkdir(parents=True)
    lock = json.loads(args.lock.read_text())
    paths = [ROOT/'build/n009/phos-n010-capture', ROOT/'build/n009/phos-n010-pixel-pt',
             ROOT/'build/n009/n010-neutral-work-verify', args.lock,
             ROOT/'build/n010-cpu/n010_rqmc_oracle',
             ROOT/'out/research/n010-comparison-readiness/sobol16x262144.bin',
             RESULTS/'009-iid-precision-confirmation.json', RESULTS/'031-c1-b2-pt-quality-ladder.json',
             RESULTS/'013-c7-pt-cohort-pilot.json', RESULTS/'019-controlled-dynamic-cohort.json',
             RESULTS/'037-controlled-dynamic-pt1024.json',
             RESULTS/'024-c8-pt-quality-ladder.json', RESULTS/'025-c9-pt-quality-ladder.json']
    paths += list(SCRIPTS.glob('*.py'))
    identities = {str(path):sha(path) for path in paths}
    shaders = shader_hashes()
    status = {'schema':'n010-continuation/1', 'phase':'STARTING', 'complete':False,
              'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
              'input_sha256':identities, 'shader_sha256':shaders, 'jobs':[],
              'scope':'Existing original CPU oracle only; one GPU acquisition at a time; no accepted retries'}
    def save(phase):
        status['phase'] = phase
        status['updated_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        # Status is mutable execution state; scientific child results retain their own identities.
        (args.work/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    def frozen():
        if any(sha(Path(path)) != digest for path,digest in identities.items()) or shader_hashes()!=shaders:
            raise ValueError('frozen executable/input changed; stop before further acquisition')
    def eligible(cell, vertices):
        path = args.references/f'{cell}_T_B{vertices}'/'qualification.json'
        try:
            value = json.loads(path.read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return False
        if value['state_sha256'] != lock['cells'][cell]['state_sha256']:
            raise ValueError('reference state differs from lock: '+cell)
        return value['classification']=='STATISTICALLY_ELIGIBLE'
    def cpu_or_gpu_active():
        try:
            quiescent()
            return False
        except ValueError:
            return True
    def run(name, command):
        frozen()
        # CPU references may coexist with diagnostic pilots; another image
        # producer must not overlap. Calibration additionally requires quiescence.
        for process in Path('/proc').iterdir():
            if not process.name.isdigit():
                continue
            try:
                comm = (process/'comm').read_text().strip()
            except OSError:
                continue
            if comm.startswith('phos-'):
                raise ValueError('another GPU image producer is active; stop without overlapping acquisition')
        attempt = {'name':name, 'command':command, 'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
        status['jobs'].append(attempt)
        save('RUNNING_'+name)
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = ':'.join(filter(None,[env.get('NIX_LD_LIBRARY_PATH'),env.get('LD_LIBRARY_PATH')]))
        with (args.work/(name+'.stdout.log')).open('w') as stdout, (args.work/(name+'.stderr.log')).open('w') as stderr:
            result = subprocess.run(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
        attempt['returncode'] = result.returncode
        attempt['stdout_sha256'] = sha(args.work/(name+'.stdout.log'))
        attempt['stderr_sha256'] = sha(args.work/(name+'.stderr.log'))
        save('FINISHED_'+name)
        print(name,result.returncode,flush=True)
        frozen()
        if result.returncode:
            raise ValueError('acquisition/check failed; no automatic retry: '+name)
    python = str(ROOT/'out/research/n010-comparison-readiness/venv/bin/python')
    cells = ('C2','C3','C4','C5','C6')
    completed = {}
    b8_done = False
    try:
        while not b8_done or len(completed)!=len(cells):
            frozen()
            if not b8_done and eligible('C1',8):
                run('C1-B8-ladder',[python,str(SCRIPTS/'acquire_pt_pilot.py'),
                    '--cell','C1','--vertices','8','--state',lock['cells']['C1']['state_directory'],
                    '--references',str(args.references),'--work',str(args.work/'C1-B8-ladder'),
                    '--output',str(outputs[43])])
                b8_done = True
            for cell in cells:
                if cell in completed or not all(eligible(c,v) for c in ('C1',cell) for v in (2,8)):
                    continue
                path = args.work/(cell+'-dynamic.json')
                run(cell+'-dynamic',[python,str(SCRIPTS/'acquire_dynamic_pilot.py'),
                    '--cells',cell,'--lock',str(args.lock),'--references',str(args.references),
                    '--work',str(args.work/(cell+'-dynamic')),'--output',str(path)])
                completed[cell] = json.loads(path.read_text())
            if not b8_done or len(completed)!=len(cells):
                if not cpu_or_gpu_active():
                    raise ValueError('required references still ineligible/missing after generators stopped')
                save('WAITING_FOR_ELIGIBLE_REFERENCES')
                time.sleep(30)
        b2 = json.loads((RESULTS/'031-c1-b2-pt-quality-ladder.json').read_text())
        b8 = json.loads(outputs[43].read_text())
        combined = {'schema':'n010-pt-cohort-pilot/1','complete':True,'cell':'C1',
                    'selected_vertices':[2,8],'full_two_transport_ladder':True,
                    'source_evidence_sha256':{str(RESULTS/'031-c1-b2-pt-quality-ladder.json'):sha(RESULTS/'031-c1-b2-pt-quality-ladder.json'),str(outputs[43]):sha(outputs[43])},
                    'rows':b2['rows']+b8['rows']}
        outputs[44].write_text(json.dumps(combined,indent=2)+'\n')
        cohort = {'schema':'n010-dynamic-cohort-pilot/1','complete':True,'lock_sha256':sha(args.lock),
                  'source_evidence_sha256':{cell:sha(args.work/(cell+'-dynamic.json')) for cell in cells},
                  'rows':[row for cell in cells for row in completed[cell]['rows']]}
        outputs[48].write_text(json.dumps(cohort,indent=2)+'\n')
        while cpu_or_gpu_active():
            frozen()
            save('WAITING_FOR_QUIET_CALIBRATION')
            time.sleep(30)
        if not all(eligible(cell,v) for cell in lock['cells'] for v in (2,8)):
            raise ValueError('full corpus references are not eligible')
        run('quiet-sizing',[python,str(SCRIPTS/'calibrate_renderer.py'),'--mode','sizing',
            '--lock',str(args.lock),'--work',str(args.work/'quiet-sizing'),'--output',str(outputs[46])])
        plan = json.loads(outputs[46].read_text())
        if not plan['complete'] or not plan['all_pass']:
            raise ValueError('quiet sizing failed; retained; no accepted acquisition')
        run('accepted-calibration',[python,str(SCRIPTS/'calibrate_renderer.py'),'--mode','accepted',
            '--lock',str(args.lock),'--work',str(args.work/'accepted-calibration'),
            '--plan',str(outputs[46]),'--output',str(outputs[29])])
        run('readiness-preflight',[python,str(SCRIPTS/'readiness_preflight.py'),
            '--lock',str(args.lock),'--references',str(args.references),'--calibration',str(outputs[29]),
            '--dynamic-pilots',str(RESULTS/'019-controlled-dynamic-cohort.json'),
            str(RESULTS/'037-controlled-dynamic-pt1024.json'),str(outputs[48]),
            '--static-pilots',str(outputs[44]),str(RESULTS/'013-c7-pt-cohort-pilot.json'),
            str(RESULTS/'024-c8-pt-quality-ladder.json'),str(RESULTS/'025-c9-pt-quality-ladder.json'),
            '--output',str(outputs[47])])
        status['complete'] = True
        save('READY_EVIDENCE_PENDING_REVIEW')
    except Exception as error:
        status['failure'] = str(error)
        save('STOPPED_RETAINED_FAILURE')
        print(str(error),file=sys.stderr,flush=True)
        raise
