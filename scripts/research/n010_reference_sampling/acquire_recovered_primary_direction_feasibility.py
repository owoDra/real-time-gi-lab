#!/usr/bin/env python3
"""Plan 047: original two-level feasibility after complete recovered controls."""
import sys
from primary_direction_recovery_programs import HERE, identities, require_paths, feasibility_program

sys.path.insert(0, str(HERE.parent/'n010_comparison_readiness'))
from run_primary_direction_sequence import require_no_other_research_worker

original, source = feasibility_program()
_program_inputs = identities(__file__, original)
_require_quiet = require_no_other_research_worker
_require_paths = require_paths
exec(compile(source, str(original)+'#plan047-recovery', 'exec'), globals())
