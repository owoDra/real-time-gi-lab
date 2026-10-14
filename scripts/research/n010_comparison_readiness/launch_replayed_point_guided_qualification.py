#!/usr/bin/env python3
"""One fresh, proof-gated queue after the explicit physical-analysis replay."""
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt, identities

original, source = adapt('launch_point_guided_qualification.py',
    'f5688489d9138ae9ba04ed613eae9817dc7be940b7c3c08f9e6ef5b71e91fb3d', [
        ('113-point-guided-physical-controls.json', '125-point-guided-physical-analysis-replay.json', 1),
        ('115-point-guided-all-state-and-prefix.json', '126-replayed-point-guided-all-state-and-prefix.json', 1),
        ('qualify_point_guided_references.py', 'qualify_point_guided_replayed_references.py', 2),
        ('point_guided_reference_provenance.py', 'point_guided_replayed_provenance.py', 1),
        ('validate_point_guided_prefix.py', 'validate_replayed_point_guided_prefix.py', 1)])
source = once(source, '    inputs = {',
    '    paths += [Path(p) for p in '+repr(list(identities(__file__, original)))+']\n    inputs = {')
exec(compile(source, str(original)+'#plan036', 'exec'), {'__name__': __name__, '__file__': __file__})
