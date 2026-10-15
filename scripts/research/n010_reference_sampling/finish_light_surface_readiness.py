#!/usr/bin/env python3
"""Full original pilots/calibration after all 24 plan-041 references admit."""
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from generate_rqmc_oracle import once
from replayed_point_guided_adapter import adapt


def program():
    original, source = adapt('finish_replayed_readiness.py',
        '4591d6d4e4c8af20af12dc1fc55fcc64d2399137b502c65a539358a0a3e4c9c1', [
            ("Path(__file__).with_name('finish_readiness.py').resolve()",
             'Path('+repr(str(SCRIPTS/'finish_readiness.py'))+')', 1),
            ('037-replayed-reference-comparison-transition.md', '041-prospective-light-surface-corpus-admission.md', 1),
            ('point_guided_replayed_provenance', 'light_surface_reference_provenance', 1),
            ("str(SCRIPTS/'readiness_preflight_replayed.py')",
             "str(ROOT/'scripts/research/n010_reference_sampling/readiness_preflight_light_surface.py')", 1),
            ("view.get('plan') != '037'", "view.get('plan') != '041'", 1),
            ('plan-037', 'plan-041', 2),
            ('complete 125/126 reference admission', 'complete light-surface reference admission', 1),
            ('#plan037', '#plan041', 1)])
    source = once(source, "    source = once(source,'    shaders = shader_hashes()',",
        '    paths += [Path('+repr(str(original))+')] + list(Path('+repr(str(Path(__file__).resolve().parent))+').glob("*.py"))\n'
        "    source = once(source,'    shaders = shader_hashes()',")
    return original, source


if __name__ == '__main__':
    original, source = program()
    exec(compile(source, str(original)+'#plan041', 'exec'), {'__name__': '__main__', '__file__': __file__})
