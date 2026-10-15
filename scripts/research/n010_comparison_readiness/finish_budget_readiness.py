#!/usr/bin/env python3
"""Keep the full fixed comparison sequence with operational receipt admission."""
from pathlib import Path
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt
from reference_provenance import ROOT


def program():
    original, source = adapt('finish_replayed_readiness.py',
        '4591d6d4e4c8af20af12dc1fc55fcc64d2399137b502c65a539358a0a3e4c9c1', [
            ('from point_guided_replayed_provenance import verify_reference',
             'from budget_reference_provenance import verify_reference', 1),
            ('readiness_preflight_replayed.py', 'readiness_preflight_budget.py', 1)])
    source = once(source, '    source = once(source,\'    shaders = shader_hashes()\',',
        "    paths += [Path("+repr(str(original))+"),ROOT/'research/lanes/n010-comparison-readiness/experiments/039-operational-cpu-budget-continuation.md']\n"
        "    source = once(source,'    shaders = shader_hashes()',")
    return original, source


if __name__ == '__main__':
    original, source = program()
    exec(compile(source, str(original)+'#plan039', 'exec'), {'__name__': '__main__', '__file__': __file__})
