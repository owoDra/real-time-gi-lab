#!/usr/bin/env python3
"""Plan 047: unchanged full state/prefix proof after complete recovered controls."""
import sys
from primary_direction_recovery_programs import HERE, identities, require_paths, prefix_program

sys.path.insert(0, str(HERE.parent/'n010_comparison_readiness'))
from run_primary_direction_sequence import require_no_other_research_worker

if __name__ == '__main__':
    original, source = prefix_program()
    exec(compile(source, str(original)+'#plan047-recovery', 'exec'), {
        '__name__': '__main__', '__file__': __file__,
        '_program_inputs': identities(__file__, original),
        '_require_quiet': require_no_other_research_worker,
        '_require_paths': require_paths,
    })
