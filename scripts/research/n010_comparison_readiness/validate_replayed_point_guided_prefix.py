#!/usr/bin/env python3
"""Plan-036 exact state/prefix runner, using retained physical replay 125."""
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt, identities

original, source = adapt('validate_point_guided_prefix.py',
    '243c9f74570b168568bb5b2a775f33ba14b411a672bfcc032f8ffb4f2af33695', [
        ('113-point-guided-physical-controls.json', '125-point-guided-physical-analysis-replay.json', 3)])
source = once(source, '    inputs = {}', '    inputs = '+repr(identities(__file__, original)))
exec(compile(source, str(original)+'#plan036', 'exec'), {'__name__': __name__, '__file__': __file__})
