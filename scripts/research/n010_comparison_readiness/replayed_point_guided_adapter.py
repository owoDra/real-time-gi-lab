"""Guarded source substitutions for the separately identified 125/126 chain."""
from pathlib import Path
from reference_provenance import ROOT, sha

PLAN = ROOT/'research/lanes/n010-comparison-readiness/experiments/036-replayed-point-guided-proof-chain.md'


def adapt(name, digest, replacements):
    path = Path(__file__).with_name(name).resolve()
    if sha(path) != digest:
        raise ValueError('pinned original adapter source changed: '+name)
    source = path.read_text()
    for old, new, count in replacements:
        if source.count(old) != count:
            raise ValueError('source substitution count differs: '+old)
        source = source.replace(old, new)
    return path, source


def identities(adapter, original):
    return {str(p.resolve()): sha(p) for p in (Path(adapter), original, Path(__file__), PLAN)}
