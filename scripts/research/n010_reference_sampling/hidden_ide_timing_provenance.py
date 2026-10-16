"""Plan 052 strict proof intake; preserve the original 049 verifier unchanged."""
import json
from pathlib import Path
import sys

from hidden_ide_bulk_pfm_program import HERE, ROOT, RESULTS, digest, program
import diagnose_ide_visibility_accounting as D

ORIGINAL = HERE/'bulk_pfm_timing_provenance.py'
ORIGINAL_SHA = '49ac6660fe17e8895be2a0d600771a8e844358867fe57014f0066105b247b9a8'
PLAN = RESULTS.parent/'experiments/052-prospective-hidden-ide-full-calibration.md'
sys.path.insert(0,str(HERE.parent/'n010_comparison_readiness'))


def verify_environment(proof, mode, inputs):
    from reference_provenance import read
    from qualify_hybrid_references import check_files
    work = ROOT/'out/research/n010-comparison-readiness'/(
        'hidden-ide-bulk-pfm-sizing-v1' if mode=='sizing' else 'hidden-ide-bulk-pfm-accepted-v1')
    _, _, assembly = program()
    D.require(proof.get('plan052_source_inverse_proof')==assembly,
              'actual whole source inverse proof differs')
    policy_path, snapshots_path = work/'visibility-policy.json', work/'visibility-snapshots.jsonl'
    D.require(proof.get('visibility_policy_path')==str(policy_path)
        and proof.get('visibility_snapshots_path')==str(snapshots_path)
        and D.sha(policy_path)==proof.get('visibility_policy_sha256')
        and D.sha(snapshots_path)==proof.get('visibility_snapshots_sha256'),
        'actual registered visibility sidecars differ')
    policy = read(policy_path,inputs)
    D.require(policy==proof.get('visibility_policy')
        and policy['schema']=='n010-hidden-ide-calibration-policy/1'
        and all(policy.get(k) for k in ('complete','all_pass','restoration_verified',
                                      'pre_gpu_hidden_intervals_pass','input_identities_unchanged'))
        and proof.get('numerical_all_pass') is True
        and policy['maximum_accounted_gfx_ns_per_elapsed_second']==1000000
        and policy['requested_observer_interval_seconds']==5
        and policy.get('application_stopped') is False and policy.get('power_settings_changed') is False
        and not any(policy.get(k) for k in ('acquisition_failure','observer_failure',
                                          'restoration_failure','input_failure')),
        'complete source-verified environment/restoration PASS required')
    # Restoration is a producer observation bound to the frozen source and
    # sidecar, not a retrospective query of historical desktop state.
    original = policy['original_window']
    diagnostic = read(RESULTS/'174-ide-visibility-accounting-diagnostic.json',inputs)
    D.require(original['address']==diagnostic['original_window']['address']
        and original['pid']==D.PARENT_PID and original['class']=='orca'
        and original['workspace']['id']>0
        and original['mapped'] and not any(original[k] for k in (
            'hidden','floating','fullscreen','fullscreenClient','pinned','grouped'))
        and policy['desktop_version']['commit']==D.VERSION,
        'registered original IDE/compositor boundary differs')
    values = [json.loads(line) for line in snapshots_path.read_text().splitlines()]
    D.require(len(values)==policy['snapshot_count'] and len(values)>=6,
              'full sampled visibility/accounting evidence absent')
    for index, value in enumerate(values):
        window = value['window']
        D.require(value['client']==list(D.CLIENT) and value['pid']==D.GPU_PID
            and value['start_ticks']==D.GPU_START and isinstance(value['first_matching_fd'],int)
            and value['scan_end_monotonic_ns']>=value['scan_start_monotonic_ns']
            and value['sampled_visibility_identity_pass']
            and window['address']==original['address'] and window['workspace']['name']==D.SPECIAL
            and value['monitors']==policy['original_monitors']
            and all(window[k]==original[k] for k in (
                'pid','class','mapped','floating','fullscreen','fullscreenClient','pinned','grouped')),
            'sampled client/window/monitor identity differs')
        if index:
            before = values[index-1]
            elapsed = value['scan_start_monotonic_ns']-before['scan_start_monotonic_ns']
            delta = value['engine_ns']['gfx']-before['engine_ns']['gfx']
            D.require(value.get('elapsed_ns')==elapsed and value.get('gfx_delta_ns')==delta
                and elapsed>0 and delta>=0 and delta*1000000000<=1000000*elapsed,
                'every original sampled hidden interval must pass without exclusions')
            if index<=3:
                D.require(elapsed>=5000000000,'registered pre-GPU interval shortened')
    inputs[str(snapshots_path)] = D.sha(snapshots_path)
    for p in (Path(__file__).resolve(),HERE/'hidden_ide_bulk_pfm_program.py',
              HERE/'hidden_ide_calibration_policy.py',HERE/'calibrate_hidden_ide_bulk_pfm.py',
              Path(D.__file__).resolve(),PLAN,RESULTS/'176-user-requested-post-stop-feasibility-stop.json'):
        D.require(proof['fixture_input_sha256'].get(str(p))==D.sha(p) or p==Path(__file__).resolve(),
                  'mandatory prospective environment source/input missing')
        inputs[str(p)] = D.sha(p)
    check_files(inputs,{})


def verifier_program():
    D.require(D.sha(ORIGINAL)==ORIGINAL_SHA,'original strict 049 verifier changed')
    original = ORIGINAL.read_text()
    source = original
    changes = []
    for old,new in (
        ('168-bulk-pfm-calibration-quiet-sizing.json','177-hidden-ide-bulk-pfm-calibration-sizing.json'),
        ('169-bulk-pfm-calibration-full-renderer.json','178-hidden-ide-bulk-pfm-calibration-full-renderer.json'),
        ('bulk-pfm-calibration-sizing-v1','hidden-ide-bulk-pfm-sizing-v1'),
        ('bulk-pfm-calibration-accepted-v1','hidden-ide-bulk-pfm-accepted-v1'),
        ('n010-bulk-pfm-renderer-calibration/1','n010-hidden-ide-bulk-pfm-renderer-calibration/1')):
        count = source.count(old)
        D.require(count>0 and new not in source,'strict proof dispatch anchor differs')
        source = source.replace(old,new)
        changes.append((old,new,count))
    for old,new in (('(168,','(177,'),('(169,','(178,'),
                    ('(167, 168, 169)','(167, 177, 178)'),
                    ('167/168/169','167/177/178'),
                    ('paths[168]','paths[177]'),('paths[169]','paths[178]')):
        count = source.count(old)
        D.require(count>0 and new not in source,'strict proof numeric identity anchor differs')
        source = source.replace(old,new)
        changes.append((old,new,count))
    old = "    for mode, proof in (('sizing', sizing), ('accepted', accepted)):\n"
    new = old+"        _verify_environment(proof,mode,inputs)\n"
    D.require(source.count(old)==1,'strict environment proof hook differs')
    source = source.replace(old,new)
    restored = source.replace(new,old)
    for old,new,count in reversed(changes):
        D.require(restored.count(new)==count,'strict dispatch inverse differs')
        restored = restored.replace(new,old)
    D.require(restored==original,'entire original strict verifier inverse differs')
    proof = {'whole_original_strict_verifier_inverse_exact':True,
             'original_source_sha256':digest(original),'restored_source_sha256':digest(restored),
             'generated_source_sha256':digest(source)}
    return source,proof


def verify_calibration(lock_path,inputs):
    source,inverse = verifier_program()
    namespace = {'__name__':'n010_hidden_ide_timing_intake','__file__':str(ORIGINAL),
                 '_verify_environment':verify_environment}
    exec(compile(source,str(ORIGINAL)+'#plan052','exec'),namespace)
    result = namespace['verify_calibration'](lock_path,inputs)
    result['environment']='Plan 052: registered IDE undisplayed; sampled accounting guard and source-bound restoration'
    result['strict_verifier_inverse_proof'] = inverse
    result['restoration_verification_scope']='Frozen producer observations; no retrospective desktop query'
    return result
