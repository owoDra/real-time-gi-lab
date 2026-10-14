#!/usr/bin/env python3
"""Retain the original six gates with explicit 125/126 provenance dispatch."""
import argparse
from pathlib import Path
import sys
from generate_rqmc_oracle import once
from reference_provenance import ROOT, sha

ORIGINAL_SHA = '87985c62edd7ad9a7a8e931e0f36264d939a4e4774507fe0653ac9d483857e2c'

if __name__ == '__main__':
    original = Path(__file__).with_name('readiness_preflight.py').resolve()
    adapter = Path(__file__).resolve()
    if sha(original) != ORIGINAL_SHA:
        raise ValueError('original full-gate preflight source changed')
    if not any(arg in ('--help','-h') for arg in sys.argv[1:]):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument('--output',type=Path,required=True)
        a,_ = parser.parse_known_args()
        if a.output.exists():
            raise ValueError('refuse overwriting a retained readiness audit')
    paths = [original,adapter] + [ROOT/'research/lanes/n010-comparison-readiness/experiments'/n for n in (
        '033-point-guided-readiness-adapter.md', '036-replayed-point-guided-proof-chain.md',
        '037-replayed-reference-comparison-transition.md')]
    identities = {str(p):sha(p) for p in paths}
    identity = {'original_source_path':str(original),'original_source_sha256':ORIGINAL_SHA,
        'adapter_path':str(adapter),'adapter_sha256':sha(adapter),'plan':'037',
        'change':'Reference provenance dispatch only; original six gates and thresholds unchanged'}
    source = original.read_text()
    source = once(source,'from reference_provenance import physical_proof,verify_reference',
        'from reference_provenance import physical_proof\nfrom point_guided_replayed_provenance import verify_reference')
    source = once(source,
        '24 eligible canonical scene/seed references; every payload/header and original convergence screen verified; incremental metadata and 009/022/050 proof chains checked when used',
        '24 eligible canonical scene/seed references; every payload/header and unchanged convergence screen verified; applicable original, hybrid or replayed point-guided proof chains checked')
    source = once(source,' def gate(name,work):',
        ' result["adapter_provenance"] = '+repr(identity)+'\n'
        ' result["inputs"].update('+repr(identities)+')\n def gate(name,work):')
    exec(compile(source,str(original)+'#plan037','exec'),{'__name__':'__main__','__file__':str(original)})
