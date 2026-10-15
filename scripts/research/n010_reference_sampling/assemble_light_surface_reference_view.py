#!/usr/bin/env python3
"""Fix the full plan-041 map; pending targets do not admit comparisons."""
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt


def program():
    original, source = adapt('assemble_replayed_reference_view.py',
        '0e5e442268eea1ab8f6a6cfb61ee4208355dc56da8aea209ff1b9310c8270fa5', [
            ('from point_guided_replayed_provenance import SELECTED, VARIANT',
             'from light_surface_reference_provenance import SELECTED, VARIANT', 1),
            ("('036-replayed-point-guided-proof-chain.md', '037-replayed-reference-comparison-transition.md')",
             "('041-prospective-light-surface-corpus-admission.md',)", 1),
            ('--point-guided', '--light-surface', 1),
            ('a.point_guided', 'a.light_surface', 1),
            ("'plan': '037'", "'plan': '041'", 1),
            ('plan-037', 'plan-041', 1),
            ('nine fixed plan-036 targets', 'nine fixed plan-041 light-surface targets', 1)])
    source = once(source, '    inputs = {str(Path(__file__).resolve()): sha(Path(__file__))}',
        '    inputs = {'+repr(str(original))+': '+repr('0e5e442268eea1ab8f6a6cfb61ee4208355dc56da8aea209ff1b9310c8270fa5')+
        ', str(Path(__file__).resolve()): sha(Path(__file__))}')
    return original, source


if __name__ == '__main__':
    original, source = program()
    exec(compile(source, str(original)+'#plan041', 'exec'), {'__name__': '__main__', '__file__': __file__})
