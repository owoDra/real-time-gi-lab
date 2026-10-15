#!/usr/bin/env python3
"""Plan 047 Amendment 1: fixed eight ladders after full recovered proof."""
from pathlib import Path
import sys
from primary_direction_recovery_programs import HERE, sha, once

sys.path.insert(0, str(HERE.parent/'n010_comparison_readiness'))
from run_primary_direction_sequence import require_no_other_research_worker as _recovery_require_quiet

_BASE = HERE/'qualify_primary_direction_references.py'
if sha(_BASE) != '99bbde9b594dd5e1d9b3363210f225b7f177690ebfbdfa8ac2c86d56b36e784a':
    raise ValueError('frozen plan-046 qualifier changed')
_source = _BASE.read_text()
_name = 'primary_direction_reference_provenance'
if _source.count(_name) != 2:
    raise ValueError('reference API dispatch count differs')
_source = _source.replace(_name, 'recovered_primary_direction_reference_provenance')
_source = once(_source, '"    a = ap.parse_args()\\n"',
    '"    a = ap.parse_args()\\n"\n        "    _require_quiet()\\n"\n'
    '        "    if not a.prerequisites_only and a.output.resolve() != RESULTS/\\\"166-recovered-primary-direction-reference-qualification.json\\\":\\n"\n'
    '        "        raise ValueError(\\\"recovered intake must use registered result 166\\\")\\n"')
_source = once(_source, "'__file__': __file__, '_import_feasibility': import_feasibility}",
    "'__file__': __file__, '_import_feasibility': import_feasibility, '_require_quiet': _recovery_require_quiet}")
exec(compile(_source, str(_BASE)+'#plan047-recovered-proof-dispatch', 'exec'), globals())
