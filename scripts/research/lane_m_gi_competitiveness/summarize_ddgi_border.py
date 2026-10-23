#!/usr/bin/env python3
"""Read-only011 prefix replay. Never launches, queues or retries a GPU process."""
import argparse
import json
from pathlib import Path
import subprocess

import ddgi_border_cases as F
import ddgi_border_requalification_audit as A


def collect():
    rows = []
    stopped = False
    for case in F.CASES:
        exists = case.work.exists() or case.archive.exists()
        if stopped:
            F.R.require(not exists, '011 evidence after missing/failed predecessor')
            continue
        if not exists:
            stopped = True
            continue
        report = A.audit(case)
        saved = F.BASE / 'm001-ddgi-border-audits-v1' / case.name / 'result.json'
        F.R.require(F.R.read(saved) == report, '011 saved terminal audit differs from independent replay')
        rows.append(dict(name=case.name, family=case.family, audit_sha256=F.R.sha(saved), audit=report))
        if not report['semantic_pass']:
            stopped = True
    passed = [x for x in rows if x['audit']['semantic_pass']]
    frames = [f for r in passed for f in r['audit']['frames']]
    copies = [c for f in frames for c in f['copies']]
    return dict(schema='m001-ddgi-separated-border-controls-raw-replay/1',
                source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=F.R.ROOT, text=True).strip(),
                collector_sha256=F.R.sha(Path(__file__).resolve()), gpu_executed_by_collector=False,
                native_acquisitions=len(rows), controls_pass=len(passed), controls_required=20,
                all_existing_evidence_valid=len(rows) == len(passed),
                registered_requalification_complete=len(passed) == 20,
                next_named_case=F.CASES[len(rows)].name if len(rows) == len(passed) < 20 else None,
                raw_payloads_rehashed=sum(x['audit']['raw_payloads_rehashed'] for x in rows),
                captured_frames=len(frames), full_copy_atlases=len(copies),
                full_copy_components=sum(c['complete_components'] for c in copies),
                exact_border_components=sum(c['border_components'] for c in copies),
                completed_gpu_units=sum(f['timing']['completed_gpu_units'] for f in frames),
                max_true_peak_owned_bytes=max((r['audit']['owned_memory']['true_peak_owned_bytes'] for r in passed), default=0),
                rows=rows, indirect_quality_scoring=False, quality_admission=False, accepted_timing=False,
                scope='Existing ordered011correctness captures only; partial prefix is not runtime requalification or HDR quality admission')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    F.R.require(not args.output.exists(), 'Existing011replay; never overwrite')
    result = collect()
    F.R.write_new(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}, indent=2))
