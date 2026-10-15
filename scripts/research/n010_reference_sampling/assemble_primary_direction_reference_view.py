#!/usr/bin/env python3
"""Plan 046: verify sixteen existing references and fix all 24 view targets."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0,str(SCRIPTS))
import primary_direction_reference_provenance as P
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lock',type=Path,required=True)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists() or P.REFERENCE_WORK.exists():
        raise ValueError('refuse existing view, result or pending acquisition root')
    inputs = {str(p.resolve()):sha(p) for p in (Path(__file__),Path(P.__file__),P.PLAN,
        Path(__file__).with_name('qualify_primary_direction_references.py'))}
    lock = read(a.lock,inputs)
    if set(lock['cells']) != {f'C{i}' for i in range(1,13)}:
        raise ValueError('full canonical corpus required')
    old_view = read(RESULTS/'127-replayed-point-guided-reference-view.json',inputs)
    cpu = read(RESULTS/'109-existing-eligible-cpu-provenance-audit.json',inputs)
    hybrid = read(RESULTS/'123-first-qualified-hybrid-provenance-audit.json',inputs)
    expected_cpu = {f'C{i}_T_B{v}' for i in range(7,13) for v in (2,8)} | {'C1_T_B2','C2_T_B2','C3_T_B2'}
    if (not cpu['complete'] or not cpu['all_pass'] or len(cpu['rows'])!=15
        or {r['cell']+'_'+r['transport'] for r in cpu['rows']} != expected_cpu
        or not hybrid['complete'] or not hybrid['all_pass'] or len(hybrid['rows'])!=1
        or (hybrid['rows'][0]['cell'],hybrid['rows'][0]['transport']) != ('C4','T_B2')
        or hybrid['scoring_exclusions']):
        raise ValueError('retained eligible reference proof scope differs')
    retained = {r['cell']+'_'+r['transport']:r for r in cpu['rows']+hybrid['rows']}
    if set(P.SELECTED) != {f'C{i}_T_B{v}' for i in range(1,13) for v in (2,8)}-set(retained):
        raise ValueError('prospective selection does not cover exactly all 24 slots')
    result = {'schema':'n010-primary-direction-fixed-reference-view/1','complete':False,'all_pass':False,
        'gpu_run':False,'classification':'VERIFYING_RETAINED_REFERENCES','eligible_for_comparison':False,
        'plan':'046','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'work':str(a.work.resolve()),'input_sha256':inputs,'rows':[],'retained_provenance':[],
        'scope':'Sixteen existing eligible references reverified; eight fixed future targets pending. Full 24-slot scheduling only, no new sampler or comparison admission.',
        'selection_basis':'Fifteen already eligible CPU references plus already eligible hybrid C4 B2, all predating plan 043; no incumbent-quality or new-sampler score selection.'}
    def save():
        a.output.write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        for i in range(1,13):
            cell = f'C{i}'
            for vertices in (2,8):
                name = f'{cell}_T_B{vertices}'
                if name in retained:
                    before = retained[name]
                    target = Path(before['directory']).resolve()
                    actual = P.verify_reference(target,cell,vertices,lock['cells'][cell],inputs)
                    if (not actual['pass'] or actual['levels'] != before['levels']
                        or actual['qualification_sha256'] != before['qualification_sha256']
                        or actual['computational_variant'] != before['computational_variant']):
                        raise ValueError('retained reference provenance changed: '+name)
                    if name in expected_cpu:
                        previous = next(r for r in old_view['rows'] if r['name']==name)
                        if previous['target'] != str(target) or previous['computational_variant'] != before['computational_variant']:
                            raise ValueError('retained original target changed: '+name)
                    result['retained_provenance'].append(actual)
                    variant = before['computational_variant']; state = 'EXISTING_ELIGIBLE_REVERIFIED'
                else:
                    target = P.REFERENCE_WORK/name
                    variant = P.VARIANT;state = 'PENDING_NOT_ADMITTED'
                result['rows'].append({'cell':cell,'transport':f'T_B{vertices}','name':name,'target':str(target),
                    'computational_variant':variant,'state_sha256':lock['cells'][cell]['state_sha256'],
                    'reference_state':state})
                save()
                print(name,state,flush=True)
        check_files(inputs,{})
        a.work = a.work.resolve();a.work.mkdir(parents=True)
        for row in result['rows']:
            (a.work/row['name']).symlink_to(row['target'],target_is_directory=True)
        result.update(all_pass=True,classification='FIXED_24_SLOT_MAP_16_REVERIFIED_8_PENDING',
            retained_eligible_count=16,pending_count=8,full_corpus_eligible=False)
    except (ValueError,OSError,KeyError,AssertionError) as error:
        result['failure'] = str(error)
        result['classification'] = 'FAILED_NO_ADMISSION'
    result['complete'] = True;save()
    raise SystemExit(0 if result['all_pass'] else 2)
