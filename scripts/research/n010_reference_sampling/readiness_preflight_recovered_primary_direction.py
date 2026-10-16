#!/usr/bin/env python3
"""Plan 049: original six readiness gates with recovered references and fixture proof."""
from pathlib import Path
import sys

from primary_direction_recovery_programs import HERE, ROOT, RESULTS, sha, once
from bulk_pfm_timing_provenance import verify_calibration

SCRIPTS = HERE.parent/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from run_primary_direction_sequence import require_no_other_research_worker

ORIGINAL = SCRIPTS/'readiness_preflight.py'
ORIGINAL_SHA = '87985c62edd7ad9a7a8e931e0f36264d939a4e4774507fe0653ac9d483857e2c'
PLAN = RESULTS.parent/'experiments/049-prospective-bulk-pfm-timing-proof-intake.md'


def require_output(path):
    if path.resolve()!=RESULTS/'047-readiness-preflight.json':
        raise ValueError('final recovered preflight requires registered result 047')
    if path.exists():
        raise ValueError('refuse overwriting retained final readiness result')


def program():
    if sha(ORIGINAL)!=ORIGINAL_SHA:
        raise ValueError('original six-gate preflight source changed')
    original = ORIGINAL.read_text()
    source = original
    edits = []

    def change(before, after):
        nonlocal source
        source = once(source, before, after)
        edits.append((before, after))

    change('from reference_provenance import physical_proof,verify_reference',
           'from reference_provenance import physical_proof\n'
           'from recovered_primary_direction_reference_provenance import verify_reference')
    change('a=ap.parse_args()\n',
           'a=ap.parse_args()\n _require_output(a.output)\n _require_quiet()\n')
    start = source.index(' def calibration():\n')
    end = source.index(" gate('demonstrated_full_renderer_timing_capability',calibration)", start)
    old = source[start:end]
    change(old, ''' def calibration():
  if a.calibration.resolve()!=_calibration_path:
   raise ValueError('final preflight requires actual registered calibration 169')
  return _verify_calibration(a.lock,result['inputs'])
''')
    files = [ORIGINAL, Path(__file__).resolve(), PLAN,
             HERE/'bulk_pfm_timing_provenance.py',
             HERE/'recovered_primary_direction_reference_provenance.py']
    identities = {str(p):sha(p) for p in files}
    identity = {'plan':'049', 'original_path':str(ORIGINAL), 'original_sha256':ORIGINAL_SHA,
                'adapter_path':str(Path(__file__).resolve()),
                'adapter_sha256':sha(Path(__file__).resolve()),
                'change':'Recovered reference proof dispatch and strict actual 167/168/169 timing intake; original gate names and other five gate bodies unchanged',
                'historical_pilot_timing_accepted':False}
    change(' def gate(name,work):',
           ' result["adapter_provenance"] = '+repr(identity)+'\n'
           ' result["inputs"].update('+repr(identities)+')\n def gate(name,work):')
    restored = source
    for before, after in reversed(edits):
        restored = once(restored, after, before)
    if restored!=original:
        raise ValueError('unexpected change outside registered preflight dispatch')
    return source


if __name__=='__main__':
    source = program()
    exec(compile(source, str(ORIGINAL)+'#plan049', 'exec'), {
        '__name__':'__main__', '__file__':__file__,
        '_require_output':require_output, '_require_quiet':require_no_other_research_worker,
        '_verify_calibration':verify_calibration,
        '_calibration_path':RESULTS/'169-bulk-pfm-calibration-full-renderer.json',
    })
