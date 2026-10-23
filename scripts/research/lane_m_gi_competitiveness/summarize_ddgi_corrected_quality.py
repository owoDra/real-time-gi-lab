#!/usr/bin/env python3
"""Read-only012 acquisition/score replay. Never execute, retry or queue GPU work."""
import argparse
import json
from pathlib import Path
import subprocess

import ddgi_corrected_quality_step as F
import ddgi_corrected_quality_audit as A


def collect():
    reports = {}
    rows = []
    expected = F.next_case(reports)
    stopped = False
    invalid = False
    for cell, depth in F.TARGETS:
        for rung in range(3):
            case = F.Case(cell, depth, rung)
            exists = case.work.exists() or case.archive.exists()
            if exists:
                F.R.require(not stopped and case == expected, '012 evidence after missing/failed unit or first PASS')
                report = A.audit(case)
                reports[case.name] = report
                rows.append(report)
                if report['quality_evidence_valid']:
                    expected = F.next_case(reports)
                else:
                    stopped = invalid = True
            elif case == expected:
                stopped = True
    valid = [r for r in rows if r['quality_evidence_valid']]
    passes = []
    losses = []
    for cell, depth in F.TARGETS:
        cases = [r for r in valid if r['scope']['cell'] == cell and r['scope']['vertices'] == depth]
        if any(r['classification'] == 'PASS' for r in cases):
            passes.append(f'{cell}_T_B{depth}')
        elif any(r['scope']['rung'] == 2 and r['classification'] == 'QUALITY_FAIL' for r in cases):
            losses.append(f'{cell}_T_B{depth}')
    copies = [c for row in valid for c in row['native']['copies']]
    return dict(schema='m001-ddgi-corrected-quality-raw-replay/1',
                source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=F.R.ROOT, text=True).strip(),
                collector_sha256=F.R.sha(Path(__file__).resolve()), gpu_executed_by_collector=False,
                native_acquisitions=len(rows), all_existing_evidence_valid=not invalid,
                cohort_complete=not invalid and expected is None,
                next_named_case=expected.name if expected and not invalid else None,
                operational_failure_stops_cohort=invalid, quality_pass_targets=passes, exhausted_quality_fail_targets=losses,
                unresolved_target_count=6-len(passes)-len(losses),
                raw_payloads_rehashed=sum(r['raw_payloads_rehashed'] for r in rows),
                full_error_maps=3*len(valid), full_copy_atlases=len(copies),
                full_copy_components=sum(c['complete_components'] for c in copies),
                exact_border_components=sum(c['border_components'] for c in copies),
                completed_gpu_units=sum(r['native']['timing']['completed_gpu_units'] for r in valid),
                max_true_peak_owned_bytes=max((r['native']['owned_memory']['true_peak_owned_bytes'] for r in valid), default=0),
                rows=rows, unblinded_cohort=True, accepted_timing=False, superiority_claim=False,
                scope='012 corrected finite-stage static cohort only; old010evidence remains separate; no calibrated speed, general dynamics/device or architecture promotion')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    F.R.require(not args.output.exists(), 'Existing012 replay; never overwrite')
    report = collect()
    F.R.write_new(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))
