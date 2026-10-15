#!/usr/bin/env python3
"""Keep all six original readiness gates with plan-041 reference dispatch."""
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt


def program():
    original, source = adapt('readiness_preflight_replayed.py',
        '8387513530a32db29b60848b44b31cfe98832c881f1f4fbeaae81405077850b1', [
            ("Path(__file__).with_name('readiness_preflight.py').resolve()",
             'Path('+repr(str(SCRIPTS/'readiness_preflight.py'))+')', 1),
            ('point_guided_replayed_provenance', 'light_surface_reference_provenance', 1),
            ("'033-point-guided-readiness-adapter.md', '036-replayed-point-guided-proof-chain.md',\n        '037-replayed-reference-comparison-transition.md'",
             "'041-prospective-light-surface-corpus-admission.md',", 1),
            ("'plan':'037'", "'plan':'041'", 1),
            ('#plan037', '#plan041', 1),
            ('applicable original, hybrid or replayed point-guided proof chains checked',
             'applicable original, hybrid or light-surface proof chains and explicit imports checked', 1)])
    source = once(source, '    identities = {str(p):sha(p) for p in paths}',
        '    paths += [Path('+repr(str(original))+')] + list(Path('+repr(str(Path(__file__).resolve().parent))+').glob("*.py"))\n'
        '    identities = {str(p):sha(p) for p in paths}')
    return original, source


if __name__ == '__main__':
    original, source = program()
    exec(compile(source, str(original)+'#plan041', 'exec'), {'__name__': '__main__', '__file__': __file__})
