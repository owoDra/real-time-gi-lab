#!/usr/bin/env python3
"""Retire only redundant hybrid work after complete selected-reference proof."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import point_guided_replayed_provenance as P
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files, BINARY

BASE = ROOT/'out/research/n010-comparison-readiness'
QUEUE = BASE/'hybrid-qualification-queue-v1'
HYBRID = BASE/'hybrid-reference-ladders-v1'
POINT_RESULT = RESULTS/'128-replayed-point-guided-reference-qualification.json'
HYBRID_RESULT = RESULTS/'121-hybrid-reference-qualification.json'
VIEW = RESULTS/'127-replayed-point-guided-reference-view.json'
LOCK = RESULTS/'026-dynamic-execution-state-lock.json'


def process(pid):
    try:
        directory = Path('/proc')/str(pid)
        stat = (directory/'stat').read_text().rsplit(')',1)[1].split()
        return {'pid':pid,'ppid':int(stat[1]),'state':stat[0],'start_ticks':stat[19],
            'uid':directory.stat().st_uid,'command':[s.decode(errors='replace') for s in
                (directory/'cmdline').read_bytes().split(b'\0') if s]}
    except (FileNotFoundError,ProcessLookupError):
        return None


def same(original):
    current = process(original['pid'])
    return current is not None and current['start_ticks'] == original['start_ticks']


def terminal(original):
    current = process(original['pid'])
    return not same(original) or current['state'] == 'Z'


def argument(command,flag):
    return Path(command[command.index(flag)+1]).resolve()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing scoped-retirement attempt')
    ctypes.CDLL(None).prctl(15,b'n010_hyb_retire',0,0,0)
    proof = json.loads((RESULTS/'131-replayed-point-guided-proof-chain-audit.json').read_text())
    if not proof['complete'] or not proof['all_pass']:
        raise ValueError('selected-reference method proof incomplete')
    inputs = dict(proof['input_sha256'])
    for path in (Path(__file__),RESULTS.parent/'experiments/038-qualified-reference-quiescence-transition.md',
                 RESULTS/'131-replayed-point-guided-proof-chain-audit.json',VIEW,LOCK):
        inputs[str(path.resolve())] = sha(path)
    check_files(inputs,{})
    queue_status = json.loads((QUEUE/'status.json').read_text())
    check_files(queue_status['input_sha256'],inputs)
    source_inputs = {p:h for p,h in inputs.items() if Path(p).suffix in ('.py','.md')}
    original = process(queue_status['pid'])
    if original:
        cmd = original['command']
        if (original['uid'] != os.getuid() or not any(Path(s).name == 'launch_hybrid_qualification.py' for s in cmd)
                or argument(cmd,'--queue') != QUEUE or argument(cmd,'--work') != HYBRID):
            raise ValueError('original hybrid queue identity differs')
    elif not queue_status.get('complete'):
        raise ValueError('hybrid queue missing without terminal status; inspect before retirement')
    a.work.mkdir(parents=True)
    record = {'schema':'n010-qualified-redundant-acquisition-retirement/1','complete':False,
        'phase':'WAITING_FOR_COMPLETE_SELECTED_QUALIFICATION','gpu_run':False,
        'pid':os.getpid(),'input_sha256':inputs,'source_commit':subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'original_hybrid_queue':original,'signal_targets':[],
        'scope':'Workflow retirement only after complete 24-reference proof; all scientific thresholds and on-disk evidence retained',
        'cap_failure_claimed':False,'hybrid_acquisition_completed_by_retirement':False}
    def save():
        record['updated_utc'] = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
        (a.work/'status.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    stopped = []
    try:
        while True:
            check_files(source_inputs,{})
            try:
                point = json.loads(POINT_RESULT.read_text())
            except (FileNotFoundError,json.JSONDecodeError):
                point = {}
            if point.get('complete'):
                if not point.get('all_pass'):
                    raise ValueError('selected qualification failed; hybrid not retired')
                break
            time.sleep(30)
        check_files(inputs,{})
        view,lock = read(VIEW,inputs),read(LOCK,inputs)
        if view.get('plan') != '037' or len(view['rows']) != 24:
            raise ValueError('fixed full view missing')
        read(POINT_RESULT,inputs)
        record['phase'] = 'VERIFYING_ALL_SELECTED_REFERENCES';save()
        rows = []
        for row in view['rows']:
            path = Path(view['work'])/row['name']
            if not path.is_symlink() or str(path.resolve()) != row['target']:
                raise ValueError('scheduled reference target changed')
            q = read(path/'qualification.json',inputs)
            if q.get('computational_variant','original-full-prefix') != row['computational_variant']:
                raise ValueError('scheduled computational variant differs')
            rows.append(P.verify_reference(path,row['cell'],int(row['transport'][3:]),
                                          lock['cells'][row['cell']],inputs))
        if {r['cell']+'_'+r['transport'] for r in rows} != {f'C{i}_T_B{v}' for i in range(1,13) for v in (2,8)}:
            raise ValueError('full selected reference proof coverage differs')
        record['selected_reference_proof'] = rows
        check_files(inputs,{})
        if original and not terminal(original):
            if not same(original) or process(original['pid'])['command'] != original['command']:
                raise ValueError('hybrid PID/start identity changed')
            os.kill(original['pid'],signal.SIGSTOP);stopped.append(original)
            time.sleep(.15)
            children = [process(int(p.name)) for p in Path('/proc').iterdir() if p.name.isdigit()]
            children = [p for p in children if p and p['ppid'] == original['pid'] and p['state'] != 'Z']
            if len(children) != 1:
                raise ValueError('expected exactly one hybrid qualifier')
            qualifier = children[0];cmd = qualifier['command']
            if (qualifier['uid'] != os.getuid() or not any(Path(s).name == 'qualify_hybrid_references.py' for s in cmd)
                    or argument(cmd,'--work') != HYBRID or argument(cmd,'--output') != HYBRID_RESULT):
                raise ValueError('hybrid qualifier identity differs')
            os.kill(qualifier['pid'],signal.SIGSTOP);stopped.append(qualifier)
            time.sleep(.15)
            procs = {int(p.name):process(int(p.name)) for p in Path('/proc').iterdir() if p.name.isdigit()}
            descendants = {qualifier['pid']}
            while True:
                more = {pid for pid,p in procs.items() if p and p['ppid'] in descendants}
                if more <= descendants:break
                descendants |= more
            native = []
            for pid in sorted(descendants-{qualifier['pid']}):
                p = procs[pid];cmd = p['command']
                if p['state'] == 'Z':continue
                if (p['uid'] != os.getuid() or str(BINARY) not in cmd
                        or not any(Path(s).is_absolute() and Path(s).is_relative_to(HYBRID) for s in cmd)):
                    raise ValueError('unexpected hybrid descendant identity')
                if Path(cmd[0]).resolve() != BINARY and not (cmd[0]=='bash' and cmd[1]=='scripts/run_with_vulkan.sh'):
                    raise ValueError('unexpected hybrid native/wrapper')
                native.append(p)
            for path in (QUEUE/'status.json',HYBRID_RESULT):
                target = a.work/('retained-'+path.parent.name+'-'+path.name)
                target.write_bytes(path.read_bytes())
                record.setdefault('retained_status_bytes',[]).append({'source':str(path),'path':str(target.resolve()),'sha256':sha(target)})
            record['signal_targets'] = native+[qualifier,original]
            record['phase'] = 'VERIFIED_REDUNDANT_HYBRID_ONLY';save()
            for p in record['signal_targets']:
                current = process(p['pid'])
                if current is None or current['state'] == 'Z':continue
                if not same(p):raise ValueError('verified target identity changed before TERM')
                try:os.kill(p['pid'],signal.SIGTERM)
                except ProcessLookupError:pass
        elif original and same(original) and process(original['pid'])['state'] != 'Z':
            raise ValueError('unexpected hybrid terminal identity')
        else:
            current_status = json.loads((QUEUE/'status.json').read_text())
            if not current_status.get('complete'):
                raise ValueError('hybrid parent vanished without terminal queue status; inspect possible orphans')
            for directory in Path('/proc').iterdir():
                if not directory.name.isdigit():continue
                p = process(int(directory.name))
                if p and p['state'] != 'Z' and any(str(HYBRID) in arg for arg in p['command']):
                    raise ValueError('hybrid parent terminal but matching work process remains; no no-op claim')
            record['natural_hybrid_termination_before_retirement'] = True
    except (ValueError,OSError,KeyError,AssertionError) as error:
        record['failure'] = str(error)
    finally:
        for p in stopped:
            if same(p):
                try:os.kill(p['pid'],signal.SIGCONT)
                except ProcessLookupError:pass
    if record.get('signal_targets') and not record.get('failure'):
        deadline = time.monotonic()+10
        while any(not terminal(p) for p in record['signal_targets']) and time.monotonic()<deadline:
            time.sleep(.1)
        if any(not terminal(p) for p in record['signal_targets']):
            record['failure'] = 'verified hybrid targets not yet terminal; inspect without retry'
    if not record.get('failure'):
        record['retained_hybrid_files'] = [{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
            for p in sorted(HYBRID.rglob('*')) if p.is_file()]
        record['phase'] = ('RETIRED_REDUNDANT_HYBRID_PARTIALS_RETAINED' if record['signal_targets']
                           else 'FULL_REFERENCE_PROOF_HYBRID_ALREADY_TERMINAL_NO_SIGNALS')
        record['all_selected_references_verified'] = True
    else:
        record['phase'] = 'RETAINED_RETIREMENT_REFUSAL_OR_FAILURE'
    record['complete'] = True;save()
    a.output.write_text(json.dumps(record,indent=2)+'\n')
    print(record['phase'],flush=True)
    raise SystemExit(2 if record.get('failure') else 0)
