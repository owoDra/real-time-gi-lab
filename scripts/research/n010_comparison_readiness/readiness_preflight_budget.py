#!/usr/bin/env python3
"""Retain all six readiness gates and add explicit operational receipt checks."""
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt


def program():
    original, source = adapt('readiness_preflight_replayed.py',
        '8387513530a32db29b60848b44b31cfe98832c881f1f4fbeaae81405077850b1', [
            ('from point_guided_replayed_provenance import verify_reference',
             'from budget_reference_provenance import verify_reference', 1),
            ("'plan':'037'", "'plan':'039'", 1),
            ('Reference provenance dispatch only; original six gates and thresholds unchanged',
             'Reference provenance dispatch and operational receipts; original six gates and thresholds unchanged', 1)])
    source = once(source, '    identities = {str(p):sha(p) for p in paths}',
        "    paths += [Path("+repr(str(original))+"),ROOT/'research/lanes/n010-comparison-readiness/experiments/039-operational-cpu-budget-continuation.md']\n"
        '    identities = {str(p):sha(p) for p in paths}')
    return original, source


if __name__ == '__main__':
    original, source = program()
    exec(compile(source, str(original)+'#plan039', 'exec'), {'__name__': '__main__', '__file__': __file__})
