#!/usr/bin/env python3
"""Plan121: separate pilot integrity from timing precision in the six-gate audit."""
import hashlib
import os
from pathlib import Path

from deferred_readiness_dispatch import assemble
from reportable_timing_provenance import PILOT, PLAN, RESULTS, verify_timing_pilot

AUDIT = RESULTS / '387-reportable-timing-readiness-preflight.json'


def require_output(path):
    if path.resolve() != AUDIT or path.exists():
        raise ValueError('require fresh registered387 audit; never overwrite a retained decision')


def program():
    """Assemble without dispatching a worker or running the final auditor."""
    parent, scope, dispatch_proof = assemble('audit', Path(__file__).resolve())
    # The assembled module only defines the source adapter when imported.
    scope['__name__'] = 'n010_reportable_parent_source_adapter'
    exec(compile(parent, __file__ + '#parent-source-only', 'exec'), scope)
    original = scope['program']()
    source, edits = original, []

    def change(before, after):
        nonlocal source
        if source.count(before) != 1 or after in source:
            raise ValueError('reportable preflight overlay shape differs: ' + before[:80])
        source = source.replace(before, after, 1)
        edits.append((before, after))

    start = source.index(' def calibration():\n')
    end = source.index(" gate('demonstrated_full_renderer_timing_capability',calibration)", start)
    change(source[start:end], ''' def calibration():
  if a.calibration.resolve()!=_reportable_pilot:
   raise ValueError('requires actual registered reportable pilot386')
  return _verify_reportable_pilot(a.lock,result['inputs'])
''')
    change(" gate('demonstrated_full_renderer_timing_capability',calibration)",
           " gate('valid_full_renderer_timing_pilot',calibration)")
    change("'schema':'n010-readiness-preflight/1'", "'schema':'n010-readiness-preflight/2'")
    # This bridge covers the registered legacy pilot cohort, not the still
    # missing selected-quality/history-frame manifest and all-split intake.
    # Even complete future386 evidence cannot silently grant final readiness.
    change("if all(g['pass'] for g in result['gates']):result['classification']='READY_FOR_LANE_M_FIRST_COHORT'",
           "if all(g['pass'] for g in result['gates']):result['classification']='PILOT_EVIDENCE_VALID_HANDOFF_INCOMPLETE'")
    import reportable_timing_provenance as P
    paths = (Path(__file__).resolve(), Path(P.__file__).resolve(), PLAN,
             PLAN.with_name('120-reportable-comparison-readiness-amendment.md'))
    identity = dict(plan='121', parent_dispatch=dispatch_proof,
                    timing_claims_accepted=False, timing_precision='NOT_DEMONSTRATED',
                    whole_parent_inverse_exact=True,
                    other_five_gate_bodies_unchanged=True,
                    reference_dispatch='Existing plan055 recovered/reference proof dispatch; '
                        'no automatic all-split reference admission')
    inputs = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    change(' def gate(name,work):',
           ' result["reportable_timing_amendment"] = ' + repr(identity) + '\n'
           ' result["inputs"].update(' + repr(inputs) + ')\n def gate(name,work):')
    restored = source
    for before, after in reversed(edits):
        if restored.count(after) != 1:
            raise ValueError('reportable preflight inverse count differs')
        restored = restored.replace(after, before, 1)
    if restored != original:
        raise ValueError('change outside the registered timing overlay')
    return source, dict(parent_dispatch=dispatch_proof, whole_parent_inverse_exact=True,
                        generated_source_sha256=hashlib.sha256(source.encode()).hexdigest())


if __name__ == '__main__':
    source, _ = program()
    from run_primary_direction_sequence import require_no_other_research_worker
    if 31 not in os.sched_getaffinity(0):
        raise ValueError('registered audit CPU31 unavailable')
    os.sched_setaffinity(0, {31})
    priority = os.getpriority(os.PRIO_PROCESS, 0)
    if priority < 15:
        os.nice(15 - priority)
    exec(compile(source, __file__ + '#plan121', 'exec'), dict(
        __name__='__main__', __file__=__file__, _require_output=require_output,
        _require_quiet=require_no_other_research_worker,
        _reportable_pilot=PILOT, _verify_reportable_pilot=verify_timing_pilot))
