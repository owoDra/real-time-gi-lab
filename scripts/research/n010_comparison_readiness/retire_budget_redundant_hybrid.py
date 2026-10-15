#!/usr/bin/env python3
"""Retire redundant hybrid work only after full budget-aware reference proof."""
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt


def program():
    original, source = adapt('retire_qualified_redundant_hybrid.py',
        '85f4350d1f7472a01ac81f0f332b71723e58e1686ae0d02bc4a569a8c7fe7592', [
            ('import point_guided_replayed_provenance as P', 'import budget_reference_provenance as P', 1),
            ('128-replayed-point-guided-reference-qualification.json', '140-budget-point-guided-reference-qualification.json', 1),
            ('038-qualified-reference-quiescence-transition.md', '039-operational-cpu-budget-continuation.md', 1)])
    source = once(source, '    for path in (Path(__file__),RESULTS.parent/',
        '    for path in (Path('+repr(str(original))+'),Path(__file__),RESULTS.parent/')
    return original, source


if __name__ == '__main__':
    original, source = program()
    exec(compile(source, str(original)+'#plan039', 'exec'), {'__name__': '__main__', '__file__': __file__})
