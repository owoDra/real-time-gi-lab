#!/usr/bin/env python3
"""Score retained corpus captures without modifying original capture evidence."""
import argparse
import json
from pathlib import Path
from acquire_rc_pilot import ROOT, sha
from readiness_preflight import replay
from score_hdr import score

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--captures', type=Path, required=True)
    parser.add_argument('--cells', nargs='+', required=True)
    parser.add_argument('--vertices', type=int, nargs='+', choices=(2,8), default=[2,8])
    parser.add_argument('--references', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.work.exists() or args.output.exists():
        raise ValueError('refuse existing scoring acquisition')
    original = json.loads(args.captures.read_text())
    if not original['complete']:
        raise ValueError('original acquisition not complete')
    selected = [row for row in original['rows'] if row['cell'] in args.cells]
    if {row['cell'] for row in selected} != set(args.cells):
        raise ValueError('missing requested cell')
    args.work.mkdir(parents=True)
    result = {'schema':'n010-retained-corpus-scoring/1', 'complete':False,
              'capture_evidence_sha256':sha(args.captures),
              'scoring_script_sha256':sha(Path(__file__)),
              'scoring_exclusions':[], 'rows':[]}
    for row in selected:
        capture = ROOT / row['capture_directory']
        if row['returncode']:
            raise ValueError('failed original capture')
        for name, digest in row['payload_sha256'].items():
            if sha(capture/name) != digest:
                raise ValueError('original evidence changed: '+name)
        refcell = row['cell'] if row['target'] else ('C1' if row['cell'] in ('C2','C3','C4','C5','C6') else 'C7')
        scored = []
        for vertices in args.vertices:
            ref = args.references/f'{refcell}_T_B{vertices}'
            qualification = ref/'qualification.json'
            target = args.work/(row['cell']+'-'+row['backend']+'-'+('target' if row['target'] else 'source'))
            target.mkdir(parents=True, exist_ok=True)
            path = target/f'quality-B{vertices}.json'
            value = score(capture, json.loads(qualification.read_text()), ref, path)
            value['qualification_sha256'] = sha(qualification)
            path.write_text(json.dumps(value,indent=2)+'\n')
            scored.append(value)
        memory = json.loads((capture/'allocation-ledger.json').read_text())
        passed = replay(memory)
        result['rows'].append({'cell':row['cell'], 'backend':row['backend'], 'target':row['target'],
                               'capture_directory':row['capture_directory'], 'scores':scored,
                               'memory_independent_replay':'PASS' if passed else 'FAIL',
                               'ledger_sha256':sha(capture/'allocation-ledger.json'),
                               'owned_peak_bytes':memory['true_peak_owned_bytes']})
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        if not passed:
            raise ValueError('memory replay failed; record retained')
    result.update(complete=True, score_payload_sha256={
        str(path.relative_to(args.work)):sha(path) for path in sorted(args.work.rglob('*')) if path.is_file()})
    args.output.write_text(json.dumps(result,indent=2)+'\n')
