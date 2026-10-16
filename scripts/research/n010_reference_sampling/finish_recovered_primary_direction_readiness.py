#!/usr/bin/env python3
"""Plan 049 Amendment 1: unchanged remaining pilots after full proof admission."""
import json
from pathlib import Path
import sys

from primary_direction_recovery_programs import HERE, ROOT, RESULTS, sha, once
from bulk_pfm_timing_provenance import verify_calibration

SCRIPTS = HERE.parent/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from run_primary_direction_sequence import require_no_other_research_worker
from qualify_hybrid_references import check_files
from reference_provenance import read

ORIGINAL = SCRIPTS/'finish_readiness.py'
ORIGINAL_SHA = '53b173bfe9cb214442f869334426c281059f3162ac26596d44f2f614bea7dff5'
PLAN = RESULTS.parent/'experiments/049-prospective-bulk-pfm-timing-proof-intake.md'
VIEW = RESULTS/'160-primary-direction-reference-view.json'
WORK = ROOT/'out/research/n010-comparison-readiness/final-comparison-pilots-recovered-v1'


def admit(args):
    require_no_other_research_worker()
    if (args.work.resolve()!=WORK or args.work.exists()
        or args.lock.resolve()!=RESULTS/'026-dynamic-execution-state-lock.json'
        or not args.reference_view_record or args.reference_view_record.resolve()!=VIEW):
        raise ValueError('remaining pilots require registered fresh work, lock and view')
    inputs = {}
    timing = verify_calibration(args.lock, inputs)
    import recovered_primary_direction_reference_provenance as P
    qualifier = read(RESULTS/'166-recovered-primary-direction-reference-qualification.json', inputs)
    selected = {f'C{i}_T_B{v}' for i in range(1,13) for v in (2,8)}
    if (not qualifier['complete'] or not qualifier['all_pass']
        or qualifier['schema']!='n010-primary-direction-reference-qualification/1'
        or len(qualifier['cells'])!=8
        or {q['cell']+'_'+q['transport'] for q in qualifier['cells']}!=set(P.SELECTED)
        or any(q['classification']!='STATISTICALLY_ELIGIBLE' for q in qualifier['cells'])):
        raise ValueError('actual complete eight-slot qualification 166 required')
    check_files(qualifier['input_sha256'], inputs)
    view = read(VIEW, inputs)
    lock = read(args.lock, inputs)
    if (view['plan']!='046' or not view['complete'] or not view['all_pass']
        or view['work']!=str(args.references.resolve()) or len(view['rows'])!=24
        or {r['name'] for r in view['rows']}!=selected):
        raise ValueError('actual fixed full 24-slot scheduling map required')
    check_files(view['input_sha256'], inputs)
    rows = []
    for row in view['rows']:
        path = args.references/row['name']
        if not path.is_symlink() or str(path.resolve())!=row['target']:
            raise ValueError('fixed reference target changed')
        q = read(path/'qualification.json', inputs)
        if q.get('computational_variant', 'original-full-prefix')!=row['computational_variant']:
            raise ValueError('fixed reference computational variant changed')
        rows.append(P.verify_reference(path, row['cell'], int(row['transport'][3:]),
                                       lock['cells'][row['cell']], inputs))
    if len(rows)!=24 or not all(r['pass'] for r in rows):
        raise ValueError('independent full reference admission failed')
    for p in (Path(__file__).resolve(), ORIGINAL, PLAN,
              HERE/'bulk_pfm_timing_provenance.py', HERE/'recovered_primary_direction_reference_provenance.py'):
        inputs[str(p)] = sha(p)
    check_files(inputs, {})
    require_no_other_research_worker()
    return {'schema':'n010-recovered-final-pilot-admission/1', 'complete':True,
            'all_pass':True, 'gpu_run':False, 'rows':rows, 'input_sha256':inputs,
            'calibrated_fixture':timing, 'scoring_exclusions':0,
            'historical_pilot_timing_accepted':False}


def program():
    if sha(ORIGINAL)!=ORIGINAL_SHA:
        raise ValueError('original full pilot continuation source changed')
    original = ORIGINAL.read_text()
    source = original
    edits = []

    def change(before, after):
        nonlocal source
        position = source.index(before)
        source = once(source, before, after)
        edits.append((position, before, after))

    change('    args = parser.parse_args()',
           '    args = parser.parse_args()\n    _admission = _admit(args)')
    change("        29:'029-full-renderer-calibration.json',\n", '')
    change("        46:'046-calibration-quiet-sizing.json',\n", '')
    change('    shaders = shader_hashes()',
           "    identities.update(_admission['input_sha256'])\n"
           "    _admission_path=args.work/'reference-admission.json'\n"
           "    _admission_path.write_text(json.dumps(_admission,indent=2)+'\\n')\n"
           "    identities[str(_admission_path)]=sha(_admission_path)\n"
           '    shaders = shader_hashes()')
    change("'scope':'Full locked corpus with physically proved original/exact-prefix references; one GPU acquisition at a time; no accepted retries'",
           "'scope':'Full admitted plan-046/047 references; original remaining quality/memory pilots; imported actual fixture calibration; pilot timing diagnostic only'")
    waiting = '''            if not b8_done or len(completed)!=len(cells):
                if not cpu_or_gpu_active():
                    raise ValueError('required references still ineligible/missing after generators stopped')
                save('WAITING_FOR_ELIGIBLE_REFERENCES')
                time.sleep(30)'''
    change(waiting, '''            if not b8_done or len(completed)!=len(cells):
                raise ValueError('full admitted references changed; no waiting worker or retry')''')
    start = source.index('        while cpu_or_gpu_active():\n')
    end = source.index("        status['complete'] = True", start)
    change(source[start:end], '''        frozen()
        _require_quiet()
        status['calibrated_fixture'] = _admission['calibrated_fixture']
        status['final_audit'] = '047 must run separately after this driver terminates'
''')
    change("save('READY_EVIDENCE_PENDING_REVIEW')", "save('FULL_PILOTS_COMPLETE_FINAL_AUDIT_NOT_RUN')")
    # Positional inversion also handles deleted old calibration commands.
    restored = source
    for position, before, after in reversed(edits):
        if restored[position:position+len(after)]!=after:
            raise ValueError('pilot control-flow inverse position differs')
        restored = restored[:position]+before+restored[position+len(after):]
    if restored!=original:
        raise ValueError('unexpected change outside registered pilot dispatch')
    # Check the scientific acquisition and merge bodies explicitly too.
    for begin, end in (
        ('    def eligible(', '    def cpu_or_gpu_active('),
        ('    def run(', '    python = '),
        ("            if not b8_done and eligible('C1',8):", '            if not b8_done or len(completed)'),
        ('        b2 = json.loads(', '        cohort = '),
        ('        cohort = ', '        outputs[48].write_text')):
        old = original[original.index(begin):original.index(end, original.index(begin))]
        new = source[source.index(begin):source.index(end, source.index(begin))]
        if new!=old:
            raise ValueError('original pilot acquisition/scoring/merge body changed')
    return source


if __name__=='__main__':
    source = program()
    exec(compile(source, str(ORIGINAL)+'#plan049-final-pilots', 'exec'), {
        '__name__':'__main__', '__file__':__file__, '_admit':admit,
        '_require_quiet':require_no_other_research_worker,
    })
