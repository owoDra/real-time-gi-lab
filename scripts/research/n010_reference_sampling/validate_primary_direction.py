#!/usr/bin/env python3
"""Run unchanged complete physical/iid controls on the separate proposal."""
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0, str(SCRIPTS))
from generate_rqmc_oracle import once
from reference_provenance import ROOT, sha


if __name__ == '__main__':
    original = SCRIPTS/'validate_point_guided_oracle.py'
    digest = '50991fb0fc8aef8cc132f20a73667ffc58ba94f752b449bb7b13245beb4d38a0'
    if sha(original) != digest:
        raise ValueError('original physical runner changed')
    source = original.read_text()
    for old, new in (
        ('112-point-guided-oracle-build.json','151-primary-direction-proposal-build.json'),
        ('point-guided-oracle-build-v1','primary-direction-build-v1/standalone'),
        ('n010_point_guided_oracle','n010_primary_direction_oracle'),
        ('n010-point-guided-physical-controls/1','n010-primary-direction-physical-controls/1'),
        ("meta = dict(data['meta'])", "meta = dict(data['meta'])\n            meta.update(name=name, geometry_hash_match=meta['geometry_sha256'] == scene.geometry_sha256())")):
        source = once(source, old, new)
    source = once(source, '    inputs = {}',
        "    inputs = {"+repr(str(original))+': '+repr(digest)+',\n'
        "        str(RESULTS.parent/'experiments/043-prospective-primary-direction-reference-sampling.md'):sha(RESULTS.parent/'experiments/043-prospective-primary-direction-reference-sampling.md')}")
    source = once(source, "    if not build['complete'] or not build['all_pass']:",
        "    if (not build['complete'] or not build['all_pass']\n"
        "        or not build['geometry_light_transport_source_unchanged']\n"
        "        or not build['sampling_physical_source_bytes_equal']):")
    exec(compile(source,str(original)+'#plan043','exec'), {'__name__':'__main__','__file__':__file__})
