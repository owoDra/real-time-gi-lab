#!/usr/bin/env python3
"""Revalidate six M001 references and retained RC scores; write compact CPU evidence."""
import argparse
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import reference_step as R
from score_retained import reference


def collect():
    rows = []
    for cell in R.CAPTURE_SHA:
        for bounce in (2, 8):
            state, state_audit, inputs = R.preflight(cell, bounce)
            ref = reference(cell, bounce)
            spec = {'state_directory': str((R.LANE / f'capture/M001-{cell}-hwrt').relative_to(R.ROOT)),
                    'state_sha256': state['sha256']}
            verification = R.P.verify_reference(ref, cell, bounce, spec, inputs)
            q = R.read(ref / 'qualification.json')
            if (cell, bounce) == ('H01', 2):
                entries = [(8192, R.ROOT / 'out/research/lane-m-gi-competitiveness/m001-h01-b2-rqmc-first-level-v1'),
                           (16384, R.ROOT / 'out/research/lane-m-gi-competitiveness/m001-h01-b2-rqmc-second-level-v1')]
            else:
                entries, _ = R.prior_levels(cell, bounce)
            originals = []
            for spp, work in entries:
                receipt = R.read(work / 'result.json')
                R.require(receipt['complete'] and receipt['returncode'] == 0
                          and receipt['spp'] == spp and set(receipt['payload_sha256']) == R.RAW_NAMES,
                          'original acquisition incomplete')
                for name, digest in receipt['payload_sha256'].items():
                    R.require(R.sha(work / name) == digest, 'original raw input changed: ' + name)
                    if name not in ('oracle.stdout.txt', 'oracle.stderr.txt'):
                        dest = ref / f'o.n{spp}.{name.removeprefix("oracle.")}'
                        R.require(R.sha(dest) == digest, 'canonical view differs from original native bytes')
                originals.append({'spp': spp, 'directory': str(work.relative_to(R.ROOT)),
                                  'source_commit': receipt['source_commit'],
                                  'receipt_sha256': R.sha(work / 'result.json'),
                                  'payload_sha256': receipt['payload_sha256']})
            score_path = R.BASE / f'{cell}_T_B{bounce}/retained-incumbent-hwrt-quality/quality.json'
            scored = R.read(score_path)
            R.require(scored['reference_qualification_sha256'] == R.sha(ref / 'qualification.json'),
                      'scoring reference changed')
            quality = scored['quality']
            R.require(quality['scoring_exclusions'] == 0 and quality['state_bytes_equal']
                      and quality['complete_physical_scene_bytes_equal'], 'quality state/exclusion differs')
            # Recompute score metrics without creating or changing any prior error maps.
            import score_hdr as S
            capture = R.LANE / f'capture/M001-{cell}-hwrt/gpu'
            spp = q['levels'][-1]['spp']
            sidecars = [R.Q.L.read_sidecar(ref / f'o.n{spp}.s{i}.f64')['mean'] for i in range(4)]
            means = np.mean(sidecars, axis=0)
            for component in ('direct', 'indirect', 'total'):
                raw = capture / f'{component}.pfm'
                R.require(R.sha(raw) == quality['capture_payload_sha256'][component + '.pfm'],
                          'scored native capture changed')
                g = R.Q.L.read_pfm(raw) @ S.LUMA
                r = means[..., R.Q.L.COMPONENTS.index(component), :] @ S.LUMA
                R.require(S.metrics(g, r) == quality['components'][component],
                          'independent metrics replay differs')
            rows.append({'cell': cell, 'transport': f'T_B{bounce}',
                         'reference_eligible': True, 'accepted_spp': q['levels'][-1]['spp'],
                         'physical_source_sha256': q['scene_sha256'],
                         'state_sha256': q['state_sha256'], 'verification': verification,
                         'original_native_levels': originals,
                         'original_N007_screens': [l['screen'] for l in q['levels']],
                         'canonical_raw_payload_sha256': {str(l['spp']): l['all_payload_sha256'] for l in q['levels']},
                         'state_audit': state_audit, 'verified_inputs_sha256': inputs,
                         'retained_incumbent': {'result_sha256': R.sha(score_path),
                                                'classification': scored['classification'],
                                                'quality': quality}})
    return {'schema': 'lane-m-m001-six-reference-and-retained-rc-checkpoint/1',
            'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=R.ROOT, text=True).strip(),
            'collector_sha256': R.sha(Path(__file__)),
            'environment': {'python': platform.python_version(), 'numpy': np.__version__},
            'classification': 'SIX_ORIGINAL_REFERENCES_ADMITTED_RETAINED_FIXED_RC_SCORED',
            'reference_qualified_slot_count': len(rows), 'reference_total_slot_count': 6,
            'original_native_payload_hashes_replayed': sum(len(l['payload_sha256']) for r in rows for l in r['original_native_levels']),
            'canonical_reference_payload_hashes_replayed': sum(len(h) for r in rows for h in r['canonical_raw_payload_sha256'].values()),
            'physical_proof_009_sha256': R.sha(R.VALIDATION), 'rows': rows,
            'gpu_executed': False, 'accepted_timing': False, 'architecture_promoted': False,
            'limitations': ['Reference physical admission uses the original N010 sampler companion proof; statistical-only N007 physical_correctness_proven remains false.',
                            'All six native state captures were human-operated historical M001 runs; this checkpoint acquired no GPU images.',
                            'RC is the unchanged fixed-budget incumbent on static controlled heldouts; no equal-quality speed or PT budget equivalence is claimed.',
                            'PT ladder, software/vanilla/dense captures, DDGI scene integration and matched-quality timing remain NOT RUN.']}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    R.require(not args.output.exists(), 'refuse prior checkpoint overwrite')
    report = collect()
    R.write_new(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('rows', 'limitations')}, indent=2))
