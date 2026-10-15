#!/usr/bin/env python3
"""Plan 043: run one fresh physical/state/feasibility sequence, without retry."""
import argparse
import ctypes
import datetime
import json
import os
from pathlib import Path
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from reference_provenance import ROOT, RESULTS, sha
from qualify_hybrid_references import check_files

def require_no_other_research_worker():
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            name = (p/'comm').read_text().strip()
            words = (p/'cmdline').read_bytes().split(b'\0')
        except OSError:
            continue
        if name.startswith(('n010_','n008_oracle','phos-','gi_')) or any(
            w.startswith((b'scripts/research/',str(ROOT/'scripts/research').encode()+b'/')) for w in words):
            raise ValueError('another research worker remains: '+p.name+' '+name)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    a = ap.parse_args()
    require_no_other_research_worker()
    ctypes.CDLL(None).prctl(15, b'n010_dir_queue', 0, 0, 0)
    base = ROOT/'scripts/research/n010_reference_sampling'
    jobs = [
        ('validate_primary_direction.py','primary-direction-physical-v1','152-primary-direction-physical-controls.json'),
        ('validate_primary_direction_prefix.py','primary-direction-prefix-proof-v1','153-primary-direction-all-state-and-prefix.json'),
        ('acquire_primary_direction_feasibility.py','primary-direction-feasibility-v1','154-primary-direction-bounded-feasibility.json')]
    if a.work.exists() or any((RESULTS/name).exists() or (ROOT/'out/research/n010-comparison-readiness'/work).exists()
                              for _, work, name in jobs):
        raise ValueError('refuse existing sequence/results/work; no restart')
    build_path = RESULTS/'151-primary-direction-proposal-build.json'
    build = json.loads(build_path.read_text())
    if not build['complete'] or not build['all_pass']:
        raise ValueError('build has not passed')
    inputs = dict(build['input_sha256'])
    for p in [Path(__file__), build_path]+[base/script for script, _, _ in jobs]:
        inputs[str(p.resolve())] = sha(p)
    for folder, key in (('standalone','generated_sha256'),('prefix','prefix_generated_sha256')):
        for name, digest in build[key].items():
            inputs[str(ROOT/'out/research/n010-comparison-readiness/primary-direction-build-v1'/folder/name)] = digest
    check_files(inputs, {})
    a.work = a.work.resolve(); a.work.mkdir(parents=True)
    status = {'schema':'n010-primary-direction-sequence/1','complete':False,'all_pass':False,
        'classification':'RUNNING','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'input_sha256':inputs,'steps':[],'scope':'CPU proposal controls and bounded feasibility only; no corpus admission'}
    def save():
        (a.work/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    save()
    try:
        for script, work, name in jobs:
            require_no_other_research_worker()
            check_files(inputs,{})
            command = [sys.executable,str(base/script),'--work',str(ROOT/'out/research/n010-comparison-readiness'/work),
                '--output',str(RESULTS/name)]
            with (a.work/(name[:3]+'.stdout')).open('w') as stdout, (a.work/(name[:3]+'.stderr')).open('w') as stderr:
                child = subprocess.Popen(command,cwd=ROOT,stdout=stdout,stderr=stderr,start_new_session=True)
                step = {'command':command,'pid':child.pid,
                    'start_ticks':(Path('/proc')/str(child.pid)/'stat').read_text().rsplit(')',1)[1].split()[19],
                    'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
                status['steps'].append(step);save()
                step['returncode'] = child.wait()
                step['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat();save()
            if step['returncode']:
                raise ValueError('child failed or candidate stopped; no retry')
            proof = json.loads((RESULTS/name).read_text())
            if not proof['complete'] or not proof['all_pass']:
                raise ValueError('required complete PASS absent; no later dispatch')
            check_files(inputs,{})
            inputs[str(RESULTS/name)] = sha(RESULTS/name);save()
        status['all_pass'] = True
        status['classification'] = 'BOUNDED_SEQUENCE_PASS_NO_REFERENCE_ADMISSION'
    except (ValueError,OSError,KeyError,AssertionError) as error:
        status['classification'] = 'STOPPED_NO_RETRY'
        status['failure'] = str(error)
    status['complete'] = True;save()
    raise SystemExit(0 if status['all_pass'] else 2)
