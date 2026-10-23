#!/usr/bin/env python3
"""CPU-only full re-audit and fixed-prefix selection of six retained PT ladders."""
import argparse
import json
from pathlib import Path
import subprocess

import audit_first_pt_quality as A
import audit_quality_step as G
import frozen_quality_step as F

R = F.R


def validate_ladder(rows):
    R.require(bool(rows) and [x['spp'] for x in rows] == list(F.LADDER[:len(rows)]),
              'missing/duplicate/out-of-order frozen PT prefix')
    R.require(all(x['audit']['quality_evidence_valid'] for x in rows), 'invalid/incomplete PT evidence')
    R.require(all(x['audit']['classification'] == 'QUALITY_FAIL' for x in rows[:-1]),
              'sampling continued after first PASS')
    R.require(rows[-1]['audit']['classification'] == 'PASS'
              or (len(rows) == len(F.LADDER) and rows[-1]['audit']['classification'] == 'QUALITY_FAIL'),
              'ladder is not terminal')
    return rows[-1]['spp'] if rows[-1]['audit']['classification'] == 'PASS' else None


def collect():
    report = {'schema': 'lane-m-m001-six-pt-ladders/1',
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip(),
              'gpu_execution': 'assistant on explicitly user-authorized workstation; no power/clock changes',
              'accepted_timing': False, 'superiority_claim': False, 'rows': []}
    for cell in ('H01', 'H02', 'H03'):
        for bounce in (2, 8):
            rows = []
            for spp in F.LADDER:
                if (cell, bounce, spp) == ('H01', 2, 1):
                    work, plan, archive, audit = A.F.WORK, A.F.PLAN, A.F.ARCHIVE, A.audit
                    intake = R.ROOT / 'out/m001-h01-b2-pt-n1-independent-audit.json'
                else:
                    c = F.Case(cell, bounce, spp)
                    work, plan, archive = c.WORK, c.PLAN, c.ARCHIVE
                    audit = lambda c=c: G.audit(c)
                    intake = R.ROOT / f'out/{c.tag}-independent-audit.json'
                if not work.exists():
                    R.require(not archive.exists() and not plan.exists() and not intake.exists(),
                              'orphan prepared/archived PT evidence')
                    continue
                actual = audit()
                R.require(actual == R.read(intake), 'retained original intake differs from current full replay')
                result = R.read(work / 'result.json')
                rows.append({'spp': spp, 'work': str(work.relative_to(R.ROOT)),
                             'plan_sha256': R.sha(plan), 'result_sha256': R.sha(work / 'result.json'),
                             'archive_sha256': R.sha(archive), 'intake_sha256': R.sha(intake),
                             'native_timing_diagnostic_only': result['timing']['native'], 'audit': actual})
                print(cell, bounce, spp, actual['classification'], flush=True)
            selected = validate_ladder(rows)
            report['rows'].append({'cell': cell, 'transport': f'T_B{bounce}', 'selected_spp': selected,
                                   'classification': 'PASS' if selected is not None else 'QUALITY_FAIL',
                                   'levels': rows})
    all_rows = [r for cell in report['rows'] for r in cell['levels']]
    report.update(native_cases=len(all_rows), quality_pass=sum(r['audit']['classification'] == 'PASS' for r in all_rows),
                  quality_fail=sum(r['audit']['classification'] == 'QUALITY_FAIL' for r in all_rows),
                  native_raw_hashes_replayed=sum(r['audit']['raw_payloads_rehashed'] for r in all_rows),
                  complete=True, classification='SIX_FROZEN_PT_LADDERS_COMPLETE_NO_ACCEPTED_TIMING')
    env = R.ROOT / 'out/m001-authorized-workstation-vulkan-summary-2026-10-23.txt'
    report['workstation_inventory'] = {'path': str(env.relative_to(R.ROOT)), 'sha256': R.sha(env),
                                      'text': env.read_text(), 'scope': 'read-only environment observation; native enforces exact target device; not per-process timing provenance'}
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    R.require(not args.output.exists(), 'refuse existing summary')
    report = collect()
    R.write_new(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('rows', 'workstation_inventory')}, indent=2))
