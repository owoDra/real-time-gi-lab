"""Plan 055 guarded whole-file dispatch overlays; no acquisition at assembly."""
import hashlib
from pathlib import Path

from primary_direction_recovery_programs import HERE, RESULTS, sha, once

PLAN = RESULTS.parent/'experiments/055-prospective-deferred-calibration-handoff.md'
PARENTS = {
    'pilots':('finish_recovered_primary_direction_readiness.py',
              '7a7cff2449d528762e6b864a09a8ab6ca3aea2d27c1909d817f8b80eebe098cf'),
    'audit':('readiness_preflight_recovered_primary_direction.py',
             'c485165c1ec811abd4d83210357c54a0f72e01e779dbda961a9636f77827b061'),
}


def assemble(kind,entry):
    name,digest = PARENTS[kind]
    parent = HERE/name
    if sha(parent)!=digest:raise ValueError('whole parent readiness adapter changed')
    original = parent.read_text(); source = original; edits = []
    def change(old,new):
        nonlocal source
        source = once(source,old,new); edits.append((old,new))
    change('from bulk_pfm_timing_provenance import verify_calibration',
           'from deferred_image_timing_provenance import verify_calibration')
    change("experiments/049-prospective-bulk-pfm-timing-proof-intake.md",'experiments/'+PLAN.name)
    change("HERE/'bulk_pfm_timing_provenance.py'","HERE/'deferred_image_timing_provenance.py'")
    if kind=='pilots':
        change('Plan 049 Amendment 1: unchanged remaining pilots after full proof admission.',
               'Plan 055: unchanged remaining pilots after actual deferred calibration admission.')
        change('final-comparison-pilots-recovered-v1','final-comparison-pilots-deferred-image-v1')
        change('for p in (Path(__file__).resolve(), ORIGINAL, PLAN,',
               'for p in (Path(__file__).resolve(), ORIGINAL, PLAN, Path(_parent_adapter), Path(_dispatch_helper),')
        change("'calibrated_fixture':timing, 'scoring_exclusions':0,",
               "'calibrated_fixture':timing, 'scoring_exclusions':0,\n"
               "            'dispatch_inverse_proof':_dispatch_inverse_proof,")
    else:
        change('Plan 049: original six readiness gates with recovered references and fixture proof.',
               'Plan 055: original six readiness gates with actual deferred calibration proof.')
        change('actual registered calibration 169','actual registered calibration 186')
        change("169-bulk-pfm-calibration-full-renderer.json","186-deferred-image-calibration-full-renderer.json")
        change('files = [ORIGINAL, Path(__file__).resolve(), PLAN,',
               'files = [ORIGINAL, Path(__file__).resolve(), PLAN, Path(_parent_adapter), Path(_dispatch_helper),')
        change("identity = {'plan':'049',", "identity = {'plan':'055', 'dispatch_inverse_proof':_dispatch_inverse_proof,")
        change('strict actual 167/168/169 timing intake','strict actual 184/185/186 timing intake')
    restored = source
    for old,new in reversed(edits):restored = once(restored,new,old)
    if restored!=original:raise ValueError('whole readiness adapter inverse differs')
    proof = {'plan':'055','whole_parent_adapter_inverse_exact':True,
        'parent_path':str(parent),'parent_source_sha256':digest,
        'restored_source_sha256':hashlib.sha256(restored.encode()).hexdigest(),
        'generated_adapter_module_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'dispatch_kind':kind,'historical_pilot_timing_accepted':False}
    namespace = {'__name__':'n010_deferred_readiness_'+kind,'__file__':str(Path(entry).resolve()),
        '_parent_adapter':str(parent),'_dispatch_helper':str(Path(__file__).resolve()),
        '_dispatch_inverse_proof':proof}
    return source,namespace,proof
