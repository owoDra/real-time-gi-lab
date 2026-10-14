#!/usr/bin/env python3
"""Unchanged point-guided provenance gates with explicit 125/126 proofs."""
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt, identities

original, source = adapt('point_guided_reference_provenance.py',
    'e22bb5b1e28e3c8463f5ecbb1049305ae6e4b566b9f81c9e6c21a891eba95e91', [
        ('113-point-guided-physical-controls.json', '125-point-guided-physical-analysis-replay.json', 1),
        ('115-point-guided-all-state-and-prefix.json', '126-replayed-point-guided-all-state-and-prefix.json', 1),
        ('qualify_point_guided_references.py', 'qualify_point_guided_replayed_references.py', 1)])
source = once(source, 'def prerequisites(inputs):',
    'def prerequisites(inputs):\n    inputs.update('+repr(identities(__file__, original))+')')
exec(compile(source, str(original)+'#plan036', 'exec'), globals())
