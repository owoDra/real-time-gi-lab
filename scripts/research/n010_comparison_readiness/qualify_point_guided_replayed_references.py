#!/usr/bin/env python3
"""Unchanged plan-032 acquisition using the explicit replayed proof chain."""
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt, identities

original, source = adapt('qualify_point_guided_references.py',
    'cb9ce1e58a612cd66e6f2af1492e575b49e8ff3f003b6bef38d6e2112d77cc2e', [
        ('import point_guided_reference_provenance as P', 'import point_guided_replayed_provenance as P', 1)])
source = once(source, '    result = {',
    '    inputs.update('+repr(identities(__file__, original))+')\n    result = {')
exec(compile(source, str(original)+'#plan036', 'exec'), {'__name__': __name__, '__file__': __file__})
