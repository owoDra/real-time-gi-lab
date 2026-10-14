#!/usr/bin/env python3
"""Run the unchanged final pilot/calibration sequence after full new admission."""
from pathlib import Path
from generate_rqmc_oracle import once
from reference_provenance import ROOT, sha

if __name__ == '__main__':
    original = Path(__file__).with_name('finish_readiness.py').resolve()
    if sha(original) != '53b173bfe9cb214442f869334426c281059f3162ac26596d44f2f614bea7dff5':
        raise ValueError('original comparison continuation changed')
    source = original.read_text()
    paths = [original,Path(__file__).resolve(),ROOT/'research/lanes/n010-comparison-readiness/experiments/037-replayed-reference-comparison-transition.md']
    source = once(source,'    shaders = shader_hashes()',
        '    identities.update('+repr({str(p):sha(p) for p in paths})+')\n    shaders = shader_hashes()')
    source = once(source,"'scope':'Full locked corpus with physically proved original/exact-prefix references; one GPU acquisition at a time; no accepted retries'",
        "'scope':'Full 24-slot plan-037 corpus; complete 125/126 reference admission and quiescence before unchanged pilots/calibration; no accepted retries'")
    source = once(source,"str(SCRIPTS/'readiness_preflight.py')", "str(SCRIPTS/'readiness_preflight_replayed.py')")
    barrier = '''    try:
        from point_guided_replayed_provenance import verify_reference
        if not view_record or view.get('plan') != '037':
            raise ValueError('explicit plan-037 scheduling map required')
        while True:
            frozen()
            ready = all(eligible(cell,v) for cell in lock['cells'] for v in (2,8))
            busy = cpu_or_gpu_active()
            if ready and not busy:
                break
            if not ready and not busy:
                raise ValueError('reference work stopped without full eligible corpus; no comparison dispatch')
            save('WAITING_FOR_FULL_REFERENCES' if not ready else 'WAITING_FOR_REFERENCE_QUIESCENCE')
            time.sleep(30)
        save('AUDITING_FULL_REFERENCE_ADMISSION')
        admission = {'schema':'n010-comparison-reference-admission/1','complete':False,
            'all_pass':False,'gpu_run':False,'inputs':{},'rows':[],
            'reference_view_sha256':sha(view_record),'scoring_exclusions':0}
        admission_path = args.work/'reference-admission.json'
        try:
            if len(view['rows']) != 24 or {r['name'] for r in view['rows']} != {f'C{i}_T_B{v}' for i in range(1,13) for v in (2,8)}:
                raise ValueError('scheduled view coverage differs')
            for row in view['rows']:
                path = args.references/row['name']
                if not path.is_symlink() or str(path.resolve()) != row['target']:
                    raise ValueError('scheduled reference target changed')
                q = json.loads((path/'qualification.json').read_text())
                if q.get('computational_variant','original-full-prefix') != row['computational_variant']:
                    raise ValueError('scheduled computational variant differs')
                admission['rows'].append(verify_reference(path,row['cell'],int(row['transport'][3:]),lock['cells'][row['cell']],admission['inputs']))
            if any(sha(Path(p)) != digest for p,digest in admission['inputs'].items()):
                raise ValueError('reference input changed during admission')
            admission['all_pass'] = len(admission['rows']) == 24 and all(r['pass'] for r in admission['rows'])
        except Exception as error:
            admission['failure'] = str(error)
            raise
        finally:
            admission['complete'] = True
            admission_path.write_text(json.dumps(admission,indent=2)+'\\n')
        if not admission['all_pass']:
            raise ValueError('full reference admission failed')
        identities.update(admission['inputs'])
        identities[str(admission_path)] = sha(admission_path)
        status['reference_admission_sha256'] = sha(admission_path)
        save('FULL_REFERENCE_ADMISSION_PASS')
        while not b8_done or len(completed)!=len(cells):'''
    source = once(source,'    try:\n        while not b8_done or len(completed)!=len(cells):',barrier)
    exec(compile(source,str(original)+'#plan037','exec'),{'__name__':'__main__','__file__':str(original)})
