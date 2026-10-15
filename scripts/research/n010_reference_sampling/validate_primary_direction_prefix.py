#!/usr/bin/env python3
"""Apply every original state/prefix gate to the plan-043 proposal."""
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from generate_rqmc_oracle import once
from reference_provenance import sha


if __name__ == '__main__':
    original = SCRIPTS/'validate_point_guided_prefix.py'
    digest = '243c9f74570b168568bb5b2a775f33ba14b411a672bfcc032f8ffb4f2af33695'
    if sha(original) != digest:
        raise ValueError('original state/prefix runner changed')
    source = original.read_text()
    old_physical = '113-point-guided-physical-controls.json'
    if source.count(old_physical) != 3:
        raise ValueError('physical proof references changed')
    source = source.replace(old_physical, '152-primary-direction-physical-controls.json')
    source = once(source,
        "        '112-point-guided-oracle-build.json', '152-primary-direction-physical-controls.json',\n"
        "        '114-point-guided-prefix-build.json', '078-all-state-cpu-port-controls.json')}",
        "        '151-primary-direction-proposal-build.json', '152-primary-direction-physical-controls.json',\n"
        "        '078-all-state-cpu-port-controls.json')}")
    start = source.index('    builds = {}\n')
    end = source.index('    for path in (Path(__file__)', start)
    source = source[:start]+'''    builds = {}
    build = proofs['151-primary-direction-proposal-build.json']
    if (not build['geometry_light_transport_source_unchanged']
        or not build['sampling_physical_source_bytes_equal']):
        raise ValueError('sampling-only source proof failed')
    for number, directory, binary, generated in (
        ('112', 'standalone', 'n010_primary_direction_oracle', build['generated_sha256']),
        ('114', 'prefix', 'n010_primary_direction_prefix', build['prefix_generated_sha256'])):
        base = ROOT/'out/research/n010-comparison-readiness/primary-direction-build-v1'/directory
        check_files({str(base/name): h for name, h in generated.items()}, inputs)
        builds[number] = base/binary
'''+source[end:]
    for old, new in (
        ('n010-point-guided-all-state-and-prefix/1', 'n010-primary-direction-all-state-and-prefix/1'),
        ('031-point-guided-state-and-prefix-validation.md', '043-prospective-primary-direction-reference-sampling.md'),
        ("b'n010_guide_pfx'", "b'n010_dir_pfx'"),
        ('POINT-GUIDED STATE/PREFIX', 'PRIMARY-DIRECTION STATE/PREFIX'),
        ('    inputs = {}', '    inputs = {'+repr(str(original))+': '+repr(digest)+'}')):
        source = once(source, old, new)
    exec(compile(source, str(original)+'#plan043', 'exec'),
         {'__name__': '__main__', '__file__': __file__})
