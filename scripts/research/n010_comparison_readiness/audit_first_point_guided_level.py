#!/usr/bin/env python3
"""Post-hoc first-level provenance and fixed-screen precision diagnosis."""
import argparse
import json
from pathlib import Path
import subprocess
import point_guided_replayed_provenance as P
import qualify_references as Q
from reference_provenance import ROOT, RESULTS, read, sha
from qualify_hybrid_references import check_files

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing first-level audit')
    directory = ROOT/'out/research/n010-comparison-readiness/point-guided-replayed-reference-ladders-v1/C1_T_B8'
    original = ROOT/'out/research/n010-comparison-readiness/references-recovery-sponza-v1/C1_T_B8'
    qpath = directory/'qualification.json'
    raw = qpath.read_bytes()
    q = json.loads(raw)
    if [l['spp'] for l in q['levels']] != [8192]:
        raise ValueError('expected exactly the retained first completed level')
    a.work.mkdir(parents=True)
    archive = a.work/'retained-first-qualification.json'
    archive.write_bytes(raw)
    inputs = {str(Path(__file__).resolve()):sha(Path(__file__)),str(archive.resolve()):sha(archive)}
    result = {'schema':'n010-first-point-guided-level-audit/1','complete':False,
        'all_pass':False,'gpu_run':False,'native_acquisition_run':False,
        'classification':'POST_HOC_PREFIX_PROVENANCE_AND_PRECISION_DIAGNOSIS_NOT_ELIGIBILITY',
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'inputs':inputs,'scoring_exclusions':0,'eligible_for_references':False,
        'scope':'One complete four-seed 8192 C1 B8 level; original gates unchanged; no cap or full-corpus conclusion',
        'mutable_source_read':{'source':str(qpath),'sha256':sha(archive),'archive':str(archive.resolve())}}
    try:
        lock = read(RESULTS/'026-dynamic-execution-state-lock.json',inputs)
        result['new_variant_provenance'] = P.verify_reference(directory,'C1',8,lock['cells']['C1'],inputs,require_eligible=False)
        if qpath.read_bytes() != raw:
            raise ValueError('producer advanced qualification during audit; retain and inspect')
        old_q = read(original/'qualification.json',inputs)
        if (old_q['state_sha256'] != q['state_sha256'] or old_q['scene_sha256'] != q['scene_sha256']
                or (original/'scene.n008').read_bytes() != (directory/'scene.n008').read_bytes()):
            raise ValueError('original/new first-level physical states differ')
        inputs[str(original/'scene.n008')] = sha(original/'scene.n008')
        manifest = original/'screen-n8192.json'
        m = read(manifest,inputs)
        for level in m['levels']:
            for ref in level['references']:
                p = original/ref['path']
                if sha(p) != ref['sha256']:
                    raise ValueError('original first-level screen payload changed')
                inputs[str(p)] = sha(p)
        old_screen = Q.assess(manifest)
        if old_screen != old_q['levels'][0]['screen']:
            raise ValueError('original first-level screen differs from unchanged assessor')
        new_screen = q['levels'][0]['screen']
        result['screens'] = {'original':old_screen,'point_guided':new_screen}
        old = old_screen['rows'][0];new = new_screen['rows'][0]
        result['first_level_precision_ratios'] = {
            'active_abs_p99_new_over_original':new['max_active_abs_p99']/old['max_active_abs_p99'],
            'active_rel_p99_new_over_original':new['max_active_rel_p99']/old['max_active_rel_p99']}
        meta = read(directory/'n8192.meta.json',inputs)
        paths = 320*180*8192
        result['guided_null_diagnostics'] = [{'seed':r['seed'],
            'total_paths':paths,'null_paths':r['proposal_null_samples'],
            'null_path_fraction':r['proposal_null_samples']/paths,
            'shadow_tests':r['shadow_tests'],'primary_hits':r['primary_hits']}
            for r in meta['runs']]
        result['implementation_bound_diagnostic'] = {
            'cosine_branch_probability':0.75,
            'maximum_single_continuation_importance_correction':1/0.75,
            'seven_continuation_product_upper_bound':(1/0.75)**7,
            'interpretation':'Bound from nonnegative mixture PDF; not measured variance, bias or proof of cap failure'}
        result['qualification_classification'] = q['classification']
        result['statistical_screen_status'] = new_screen['status']
        result['thresholds'] = {'active_abs_p99_max':1e-5,'active_rel_p99_max':0.05,
            'required_replicates':4,'required_consecutive_levels':2,'cap_spp':262144}
        # The producer will advance qualification.json; preserve the exact read
        # bytes and make the audit's hash map refer to the immutable archive.
        qdigest = inputs.pop(str(qpath.resolve()))
        if qdigest != sha(archive):
            raise ValueError('qualification archive differs from audited bytes')
        check_files(inputs,{})
        result['inputs_unchanged_after_audit'] = True
        result['all_pass'] = True
    except (ValueError,OSError,KeyError,AssertionError) as error:
        result['failure'] = str(error)
    result['complete'] = True
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'audit_pass':result['all_pass'],'failure':result.get('failure'),
        'qualification':result.get('qualification_classification'),
        'ratios':result.get('first_level_precision_ratios'),
        'null_fractions':[r['null_path_fraction'] for r in result.get('guided_null_diagnostics',[])],
        'input_count':len(inputs)}))
    raise SystemExit(0 if result['all_pass'] else 2)
