#!/usr/bin/env python3
"""Exact-source adapter: new reference provenance, unchanged six readiness gates."""
import argparse
from pathlib import Path
import sys
from generate_rqmc_oracle import once
from reference_provenance import ROOT, sha

ORIGINAL_SHA256 = '87985c62edd7ad9a7a8e931e0f36264d939a4e4774507fe0653ac9d483857e2c'


if __name__ == '__main__':
    original = Path(__file__).with_name('readiness_preflight.py').resolve()
    adapter = Path(__file__).resolve()
    plan = ROOT/'research/lanes/n010-comparison-readiness/experiments/033-point-guided-readiness-adapter.md'
    if sha(original) != ORIGINAL_SHA256:
        raise ValueError('original full-gate preflight source changed; refuse undocumented adapter')
    if not any(arg in ('--help', '-h') for arg in sys.argv[1:]):
        guard = argparse.ArgumentParser(add_help=False)
        guard.add_argument('--output', type=Path, required=True)
        args, _ = guard.parse_known_args()
        if args.output.exists():
            raise ValueError('refuse overwriting a retained readiness audit')
    identity = {'original_source_path': str(original), 'original_source_sha256': ORIGINAL_SHA256,
        'adapter_path': str(adapter), 'adapter_sha256': sha(adapter),
        'plan_path': str(plan), 'plan_sha256': sha(plan),
        'change': 'Reference provenance dispatch only; all six gates/thresholds/classifiers retained'}
    source = original.read_text()
    source = once(source, 'from reference_provenance import physical_proof,verify_reference',
        'from reference_provenance import physical_proof\nfrom point_guided_reference_provenance import verify_reference')
    source = once(source,
        '24 eligible canonical scene/seed references; every payload/header and original convergence screen verified; incremental metadata and 009/022/050 proof chains checked when used',
        '24 eligible canonical scene/seed references; every payload/header and unchanged convergence screen verified; applicable original/exact-prefix, hybrid or point-guided physical/state/prefix proof chains checked')
    source = once(source, ' def gate(name,work):',
        ' result["adapter_provenance"] = '+repr(identity)+'\n'
        ' result["inputs"].update('+repr({str(p): sha(p) for p in (original, adapter, plan)})+')\n'
        ' def gate(name,work):')
    # Execute an exact, guarded source adaptation in a private namespace.
    # No mutation of imported legacy modules, active driver or source files.
    exec(compile(source, str(original), 'exec'), {'__name__': '__main__', '__file__': str(original)})
