#!/usr/bin/env python3
"""One explicitly named M001 CPU reference level, audit, or admission; never GPU.

Uses the unchanged N010 executable, physical proof, canonical scene constructor,
N007 assessor and reference_provenance verifier. No automatic level/cell loop.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

from run_h01_b2_reference_stage1 import (
    ROOT, LANE, SOURCES, BINARY, NET, VALIDATION, SEEDS, BINARY_SHA, NET_SHA,
    quiet, sha, require,
)
from prepare_m001_n010_physical_inputs import (
    CAPTURE_SHA, CORRECTED_SHA, F64_GEOMETRY_SHA,
    audit_h01, audit_h02, audit_h03,
)
from run_h01_b8_reference_stage1 import VALIDATION_SHA, SOURCES_MANIFEST_SHA

sys.path[:0] = [str(ROOT / 'scripts/research/n010_comparison_readiness'),
               str(ROOT / 'scripts/research/n008_hdr_oracle'),
               str(ROOT / 'scripts/research/n007_reference_validity')]
import qualify_references as Q
import reference_provenance as P

BASE = ROOT / 'out/research/lane-m-gi-competitiveness/m001-original-cpu-v2'
SCHEDULE = (8192, 16384, 32768, 65536, 131072, 262144)
SUFFIXES = ('f64', 'emission.pfm', 'direct.pfm', 'indirect.pfm', 'total.pfm')
RAW_NAMES = {'oracle.hits', 'oracle.stdout.txt', 'oracle.stderr.txt'} | {
    f'oracle.s{i}.{s}' for i in range(4) for s in SUFFIXES}


def read(path):
    return json.loads(path.read_text())


def write_new(path, data):
    with path.open('x', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n')


def target(cell, bounce):
    require(cell in CAPTURE_SHA and bounce in (2, 8), 'unregistered cell/transport')
    return BASE / f'{cell}_T_B{bounce}'


def preflight(cell, bounce):
    require(subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT,
                                   text=True).strip() == 'research-lane-m-gi-competitiveness',
            'wrong research branch')
    require(not subprocess.check_output(['git', 'diff', 'HEAD', '--', 'scripts',
                                         'src', 'shaders', 'CMakeLists.txt'], cwd=ROOT),
            'commit executable source before acquisition/admission')
    quiet()
    for path, expected in ((BINARY, BINARY_SHA), (NET, NET_SHA),
                           (VALIDATION, VALIDATION_SHA),
                           (SOURCES / 'manifest.json', SOURCES_MANIFEST_SHA),
                           (SOURCES / f'M001-{cell}-T_B{bounce}.n008', CORRECTED_SHA[cell][bounce])):
        require(path.is_file() and sha(path) == expected, 'frozen input changed: ' + str(path))
    proof_inputs = {}
    proof = P.physical_proof(proof_inputs)
    require(proof['complete'] and proof['all_pass'], 'physical proof failed')
    auditor = {'H01': audit_h01, 'H02': audit_h02, 'H03': audit_h03}[cell]
    state_audit = auditor(LANE, metadata_only=False)
    state_dir = LANE / f'capture/M001-{cell}-hwrt'
    state = Q.L.read_state(state_dir)
    require(state['sha256'] == CAPTURE_SHA[cell], 'captured state changed')
    scene = Q.scene_for_state(state, bounce)
    require(scene.text().encode() == (SOURCES / f'M001-{cell}-T_B{bounce}.n008').read_bytes()
            and scene.geometry_sha256() == F64_GEOMETRY_SHA[cell], 'physical scene changed')
    require(Q.LEVELS == SCHEDULE and tuple(Q.L.N007_SEEDS) == SEEDS,
            'original scientific schedule/seeds changed')
    return state, state_audit, proof_inputs


def audit_level(work, cell, bounce, spp):
    """Replay complete native inventory, original screen, physical and seed identity."""
    r = read(work / 'result.json')
    require(r.get('complete') is True and r.get('returncode') == 0
            and r.get('reference_eligible') is False and r.get('spp') == spp
            and r.get('scene') == cell and r.get('transport') == f'T_B{bounce}'
            and r.get('seeds') == list(map(str, SEEDS)), 'incomplete/wrong level receipt')
    require(r.get('binary_sha256') == BINARY_SHA and r.get('net_sha256') == NET_SHA
            and r.get('source_sha256', r.get('physical_source_sha256')) == CORRECTED_SHA[cell][bounce]
            and r.get('n010_validation_sha256', r.get('validation_sha256')) == VALIDATION_SHA,
            'recorded executable/physical proof identity differs')
    commit = r.get('source_commit', '')
    require(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit)
            and subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'],
                               cwd=ROOT, capture_output=True).returncode == 0,
            'receipt source is not a reachable ancestor')
    files = r['payload_sha256']
    require(set(files) == RAW_NAMES, 'incomplete or extra native payload inventory')
    for name, digest in files.items():
        path = (work / name).resolve()
        require(path.is_relative_to(work.resolve()) and path.is_file() and sha(path) == digest,
                'retained raw payload changed: ' + name)
    native = read(work / 'oracle.stdout.txt')
    require(native.get('oracle') == 'n010-rqmc-digital-shift'
            and native.get('scene_sha256') == CORRECTED_SHA[cell][bounce]
            and native.get('geometry_sha256') == F64_GEOMETRY_SHA[cell]
            and native.get('spp') == spp and native.get('seeds') == list(SEEDS)
            and (native.get('width'), native.get('height'), native.get('triangles')) ==
                (320, 180, 1248 if cell == 'H03' else 1224)
            and [x['seed'] for x in native.get('runs', [])] == list(SEEDS),
            'native physical/replicate identity differs')
    for i, seed in enumerate(SEEDS):
        d = Q.L.read_sidecar(work / f'oracle.s{i}.f64')
        require((d['seed'], d['spp'], d['width'], d['height']) == (seed, spp, 320, 180),
                'F64 replicate identity differs')
    legacy = (work / 'level1-input-manifest.json').exists()
    manifest_path = work / ('level1-input-manifest.json' if legacy else 'screen-input.json')
    manifest = read(manifest_path)
    require(manifest['levels'][-1]['spp'] == spp
            and all(x['seed'] == seed and x['sha256'] == files[f'oracle.s{i}.total.pfm']
                    for i, (seed, x) in enumerate(zip(SEEDS, manifest['levels'][-1]['references']))),
            'screen references do not match native output inventory')
    screen = Q.assess(manifest_path)
    require(screen == read(work / ('level1-screen.json' if legacy else 'screen.json')),
            'original N007 raw-PFM replay differs')
    require(screen['scene_sha256'] == CORRECTED_SHA[cell][bounce]
            and screen['frame_state_sha256'] == CAPTURE_SHA[cell]['frame'],
            'screen physical identity differs')
    return {'work': str(work.relative_to(ROOT)), 'result_sha256': sha(work / 'result.json'),
            'raw_payloads_verified': len(files), 'screen': screen}


def prior_levels(cell, bounce):
    entries = []
    if (cell, bounce) == ('H01', 8):
        legacy = ROOT / 'out/research/lane-m-gi-competitiveness/m001-h01-b8-rqmc-first-level-v1'
        # Original owner evidence is imported by audit only, never sampled again.
        entries.append((8192, legacy))
    root = target(cell, bounce)
    for spp in SCHEDULE:
        work = root / f'n{spp}'
        if work.exists():
            entries.append((spp, work))
    require([s for s, _ in entries] == list(SCHEDULE[:len(entries)]),
            'missing/duplicate/out-of-order retained levels')
    reports = [audit_level(w, cell, bounce, s) for s, w in entries]
    for j, (_, work) in enumerate(entries):
        manifest = read(work / ('level1-input-manifest.json' if
                                (work / 'level1-input-manifest.json').exists() else 'screen-input.json'))
        require(len(manifest['levels']) == j + 1, 'screen omitted prior levels')
        for level, (_, original) in zip(manifest['levels'], entries):
            for i, row in enumerate(level['references']):
                require(row['sha256'] == sha(original / f'oracle.s{i}.total.pfm'),
                        'prior screen PFM differs from original retained level')
    return entries, reports


def acquire(cell, bounce, spp):
    target(cell, bounce)
    require((cell, bounce) != ('H01', 2), 'H01/B2 already admitted; no new sampling')
    state, state_audit, inputs = preflight(cell, bounce)
    entries, audits = prior_levels(cell, bounce)
    require(len(entries) < len(SCHEDULE) and spp == SCHEDULE[len(entries)],
            'must name exactly the next frozen level; no retries')
    require(not audits or audits[-1]['screen']['status'] == 'incomplete',
            'sampling must stop after original statistical decision')
    work = target(cell, bounce) / f'n{spp}'
    require(not work.exists(), 'refuse existing output including partial failures')
    require(shutil.disk_usage(ROOT).free >= 8 * 1024**3, 'less than 8GiB free disk')
    work.mkdir(parents=True)
    cmd = [str(BINARY), '--net', str(NET), '--scene',
           str(SOURCES / f'M001-{cell}-T_B{bounce}.n008'), '--out', str(work / 'oracle'),
           '--seeds', ','.join(map(str, SEEDS)), '--spp', str(spp)]
    r = {'schema': 'lane-m-m001-original-cpu-level/2', 'complete': False,
         'scene': cell, 'transport': f'T_B{bounce}', 'spp': spp,
         'seeds': list(map(str, SEEDS)), 'command': cmd,
         'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
         'runner_sha256': sha(Path(__file__)), 'binary_sha256': sha(BINARY),
         'net_sha256': sha(NET), 'validation_sha256': sha(VALIDATION),
         'physical_source_sha256': CORRECTED_SHA[cell][bounce],
         'state_sha256': state['sha256'], 'prior_level_audits': audits,
         'state_audit': state_audit, 'reference_eligible': False,
         'gpu_executed': False, 'quality_scored': False, 'accepted_timing': False}
    write_new(work / 'started.json', r)
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        (work / 'oracle.stdout.txt').write_text(p.stdout)
        (work / 'oracle.stderr.txt').write_text(p.stderr)
        r['returncode'] = p.returncode
        r['payload_sha256'] = {p.name: sha(p) for p in sorted(work.glob('oracle.*')) if p.is_file()}
        require(p.returncode == 0 and set(r['payload_sha256']) == RAW_NAMES,
                'native CPU process failed/missing outputs; retain partial and stop')
        manifests = []
        for old_spp, old_work in entries + [(spp, work)]:
            refs = []
            for i, seed in enumerate(SEEDS):
                src = old_work / f'oracle.s{i}.total.pfm'
                name = f'level-{old_spp}-s{i}.total.pfm'
                shutil.copyfile(src, work / name)
                require(sha(work / name) == sha(src), 'screen copy differs')
                refs.append({'seed': seed, 'path': name, 'sha256': sha(src)})
            manifests.append({'spp': old_spp, 'references': refs})
        write_new(work / 'screen-input.json', {
            'schema_version': 1, 'source_commit': r['source_commit'],
            'scene_sha256': CORRECTED_SHA[cell][bounce],
            'frame_state_sha256': state['sha256']['frame'], 'levels': manifests})
        screen = Q.assess(work / 'screen-input.json')
        write_new(work / 'screen.json', screen)
        r['complete'] = True
        r['classification'] = screen['status']
    except Exception as e:
        r['complete'] = False
        r['classification'] = 'FAILED_RETAIN_PARTIAL_NO_RETRY'
        r['error'] = str(e)
        write_new(work / 'result.json', r)
        raise
    write_new(work / 'result.json', r)
    audit = audit_level(work, cell, bounce, spp)
    write_new(work / 'audit.json', audit)
    return audit


def admit(cell, bounce):
    state, state_audit, inputs = preflight(cell, bounce)
    entries, audits = prior_levels(cell, bounce)
    require(audits and audits[-1]['screen']['status'] == 'statistical-screen-pass',
            'original full-prefix statistical screen did not pass')
    dest = target(cell, bounce) / 'admitted'
    require(not dest.exists(), 'refuse existing admission including partial')
    dest.mkdir(parents=True)
    (dest / 'scene.n008').write_bytes((SOURCES / f'M001-{cell}-T_B{bounce}.n008').read_bytes())
    levels, manifests = [], []
    for (spp, work), audited in zip(entries, audits):
        hashes = {}
        for suffix in ['hits'] + [f's{i}.{s}' for i in range(4) for s in SUFFIXES]:
            src, name = work / f'oracle.{suffix}', f'o.n{spp}.{suffix}'
            shutil.copyfile(src, dest / name)
            require(sha(dest / name) == sha(src), 'admission copy differs')
            hashes[name] = sha(src)
        meta = read(work / 'oracle.stdout.txt')
        meta.update(binary_sha256=BINARY_SHA, net_sha256=NET_SHA,
                    source_commit=read(work / 'result.json')['source_commit'],
                    original_raw_receipt_sha256=sha(work / 'result.json'))
        write_new(dest / f'n{spp}.meta.json', meta)
        manifests.append({'spp': spp, 'references': [
            {'seed': seed, 'path': f'o.n{spp}.s{i}.total.pfm',
             'sha256': hashes[f'o.n{spp}.s{i}.total.pfm']} for i, seed in enumerate(SEEDS)]})
        write_new(dest / f'screen-n{spp}.json', {
            'schema_version': 1, 'source_commit': meta['source_commit'],
            'scene_sha256': CORRECTED_SHA[cell][bounce],
            'frame_state_sha256': state['sha256']['frame'], 'levels': list(manifests)})
        screen = Q.assess(dest / f'screen-n{spp}.json')
        require(screen['rows'] == audited['screen']['rows']
                and screen['status'] == audited['screen']['status'], 'admission screen differs')
        levels.append({'spp': spp, 'screen': screen, 'geometry_hash_match': True,
                       'all_payload_sha256': hashes})
    write_new(dest / 'qualification.json', {
        'cell': cell, 'transport': f'T_B{bounce}', 'state_sha256': state['sha256'],
        'scene_sha256': CORRECTED_SHA[cell][bounce], 'levels': levels,
        'classification': 'STATISTICALLY_ELIGIBLE', 'computational_variant': 'original-full-prefix'})
    spec = {'state_directory': str((LANE / f'capture/M001-{cell}-hwrt').relative_to(ROOT)),
            'state_sha256': state['sha256']}
    verification = P.verify_reference(dest, cell, bounce, spec, inputs)
    report = {'schema': 'lane-m-m001-original-cpu-admission/2', 'complete': True,
              'reference_eligible': verification['pass'], 'verification': verification,
              'physical_proof_009_sha256': sha(VALIDATION), 'state_audit': state_audit,
              'original_level_audits': audits, 'inputs_sha256': inputs,
              'gpu_executed': False, 'quality_scored': False, 'accepted_timing': False}
    write_new(dest / 'admission.json', report)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=('audit', 'acquire', 'admit'))
    ap.add_argument('--cell', required=True, choices=tuple(CAPTURE_SHA))
    ap.add_argument('--bounce', required=True, type=int, choices=(2, 8))
    ap.add_argument('--spp', type=int, choices=SCHEDULE)
    args = ap.parse_args()
    target(args.cell, args.bounce)
    if args.action == 'acquire':
        require(args.spp is not None, 'explicit spp required')
        report = acquire(args.cell, args.bounce, args.spp)
    elif args.action == 'admit':
        report = admit(args.cell, args.bounce)
    else:
        _, state_audit, inputs = preflight(args.cell, args.bounce)
        _, audits = prior_levels(args.cell, args.bounce)
        report = {'state_audit': state_audit, 'level_audits': audits, 'inputs': inputs}
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == '__main__':
    main()
