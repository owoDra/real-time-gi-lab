#!/usr/bin/env python3
"""N007 CPU-only prospective fixed-seed reference screen from ONE captured frame.

No GPU rerender, parameter search, changed scene/camera, or new seeds.
Pre-registered early stop is two consecutive eligible SPP levels, otherwise
exhaust precisely 512,1024,2048,4096,8192. Existing PFMs are never rewritten.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from check_convergence import assess, SPP, SEEDS
from component_contract import analyze

def sha(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()

def campaign(root: Path, reference_binary: Path) -> dict:
    root=root.resolve()
    source=json.loads((root/'component-manifest.json').read_text())
    diagnostic=analyze(root/'component-manifest.json')
    if source['frame']['backend']!='software' or not diagnostic['primary']['match']:
        raise ValueError('N007 statistical screen requires matched software primary')
    if not diagnostic['primary_geometry_attestation']['match']:
        raise ValueError('N007 GPU primary geometry state mismatch')
    frame=source['frame']
    if frame['spp']!=512 or frame['seeds']!=list(SEEDS):
        raise ValueError('frozen 512-SPP starting sample or seeds missing')
    for key in ('scene_asset_sha256','frame_state_sha256','source_commit'):
        if not frame.get(key):
            raise ValueError('missing frame provenance '+key)
    manifest={
        'schema_version':1,'source_commit':frame['source_commit'],
        'scene_sha256':frame['scene_asset_sha256'],
        'frame_state_sha256':frame['frame_state_sha256'],
        'levels':[]}
    manifest_path=root/'eligibility-manifest.json'
    final_path=root/'eligibility-summary.json'
    if final_path.exists():
        done=json.loads(final_path.read_text())
        if done.get('source_commit')!=frame['source_commit'] or (
            done.get('frame_state_sha256')!=frame['frame_state_sha256']):
            raise ValueError('existing eligibility result belongs to a different source state')
        # Pure read-only rerun of the frozen SHA-checked manifest.
        result=assess(manifest_path)
        result['classification']='statistical-eligibility-screen-only'
        return result
    if manifest_path.exists():
        earlier=json.loads(manifest_path.read_text())
        if (earlier.get('source_commit')!=manifest['source_commit'] or
            earlier.get('scene_sha256')!=manifest['scene_sha256'] or
            earlier.get('frame_state_sha256')!=manifest['frame_state_sha256']):
            raise ValueError('existing SPP campaign provenance differs from immutable capture')
        validated=assess(manifest_path)
        if validated['status']=='statistical-screen-pass':
            validated['classification']='statistical-eligibility-screen-only'
            final_path.write_text(json.dumps(validated,sort_keys=True,indent=2,
                                             allow_nan=False)+'\n')
            return validated
        manifest['levels']=earlier['levels']
    if not reference_binary.is_file():
        raise ValueError('CPU-only reference binary missing')
    for spp in SPP[len(manifest['levels']):]:
        if spp==512:
            paths=[root/'cpu'/f'seed-{i}'/'total.pfm' for i in range(4)]
        else:
            dest=root/'cpu'/'ladder'/f'spp-{spp}'
            if not dest.exists():
                subprocess.run([str(reference_binary.resolve()),'--capture',str(root),
                                '--spp',str(spp),'--out',str(dest)],check=True)
            paths=[dest/f'seed-{i}'/'total.pfm' for i in range(4)]
        if any(not p.is_file() for p in paths):
            raise ValueError(f'one or more {spp}-SPP seed PFMs missing')
        manifest['levels'].append({
            'spp':spp,'references':[
                {'seed':seed,'path':str(path.relative_to(root)),
                 'sha256':sha(path)}
                for seed,path in zip(SEEDS,paths)]})
        manifest_path.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        # check_convergence verifies source SHA, every seed/PFM hash,
        # screened signal/noise, and freezes the two-level stop.
        summary=assess(manifest_path)
        if summary['status']=='statistical-screen-pass':
            break
    summary=assess(manifest_path)
    if summary['status']=='incomplete':
        raise ValueError('N007 frozen ladder ended without PASS or five-level FAIL')
    summary['classification']='statistical-eligibility-screen-only'
    summary['physical_correctness_proven']=False
    summary['historical_causation_proven']=False
    final_path.write_text(json.dumps(summary,sort_keys=True,indent=2,
                                     allow_nan=False)+'\n')
    return summary

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture',required=True,type=Path)
    ap.add_argument('--reference-binary',required=True,type=Path)
    args=ap.parse_args()
    result=campaign(args.capture,args.reference_binary)
    print(json.dumps({
        'classification':result['classification'],
        'status':result['status'],'eligible_at_spp':result['eligible_at_spp'],
        'tested_spp':[x['spp'] for x in result['rows']],
        'per_level_positive_signal':[x['active_fraction'] for x in result['rows']],
        'physical_correctness_proven':False,
        'historical_causation_proven':False},indent=2,allow_nan=False))

if __name__=='__main__':main()
