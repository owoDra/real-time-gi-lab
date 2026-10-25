"""031 reversible private query counters; never modifies the N008 source."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = ROOT/'src/research/n008_hdr_oracle/n008_oracle.hpp'


def overlay(raw):
    changes = [
        ('namespace phos::gi::research::n008 {', 'namespace phos::gi::research::m001anchor_physical {'),
        ('struct RenderCounters {', 'struct RenderCounters {\n    std::uint64_t closest_queries{};'),
        ('            const Hit hit = bvh_.closest(ray, tmin, tmax, ignore);',
         '            ++cnt.closest_queries;\n            const Hit hit = bvh_.closest(ray, tmin, tmax, ignore);')]
    result = raw.decode()
    for old, new in changes:
        if result.count(old) != 1: raise ValueError('031 nonunique physical counter anchor')
        result = result.replace(old, new)
    restored = result
    for old, new in reversed(changes):
        if restored.count(new) != 1: raise ValueError('031 nonunique inverse counter anchor')
        restored = restored.replace(new, old)
    if restored.encode() != raw: raise ValueError('031 counter inverse not exact')
    return result.encode(), dict(original_sha256=hashlib.sha256(raw).hexdigest(),
                                 generated_sha256=hashlib.sha256(result.encode()).hexdigest(),
                                 exact_inverse=True, semantic_changes='namespace and closest-query counters only')
