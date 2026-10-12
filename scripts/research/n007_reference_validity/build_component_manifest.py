#!/usr/bin/env python3
"""Build private N007 capture manifest from real, hash-verified GPU/CPU payloads.

The scene asset and raw post-motion camera/triangle snapshots remain local.
Same manifest fingerprints alone do NOT attest to actual GPU buffer contents.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from component_contract import analyze, SEEDS

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(root: Path, scene: Path, repo: Path, source_commit: str) -> dict:
    root=root.resolve()
    scene=scene.resolve()
    repo=repo.resolve()
    if not scene.is_file():
        raise ValueError('source GLTF is missing')
    head=subprocess.check_output(
        ['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if head!=source_commit:
        raise ValueError('source commit differs from Git HEAD')
    dirty=subprocess.check_output(
        ['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],
        text=True)
    if dirty:
        raise ValueError('tracked source is dirty; provenance invalid')
    capture=json.loads((root/'capture.json').read_text())
    if capture['schema_version']!=1 or (capture['width'],capture['height'])!=(320,180):
        raise ValueError('capture is not N007 320x180')
    if capture['backend'] not in ('software','hwrt') or capture['spp'] not in (
            512,1024,2048,4096,8192):
        raise ValueError('backend or sample count violates frozen protocol')
    if capture['frame_id']!=(2 if capture['target_state'] else 1):
        raise ValueError('inconsistent renderer frame ID')
    def file(path: Path) -> dict:
        if not path.is_file():
            raise ValueError(f'missing capture file: {path}')
        return {'path':str(path.relative_to(root)),'sha256':sha(path)}
    manifest={
        'schema_version':1,
        'frame':{
            'source_commit':source_commit,
            'scene_asset_sha256':sha(scene),
            'frame_state_sha256':sha(root/'frame-state.bin'),
            'geometry_state_sha256':sha(root/'geometry-state.bin'),
            'frame_id':capture['frame_id'],
            'width':capture['width'],'height':capture['height'],
            'seeds':SEEDS,'spp':capture['spp'],'backend':capture['backend'],
        },
        'state_files':{
            'frame':file(root/'frame-state.bin'),
            'geometry':file(root/'geometry-state.bin'),
        },
        'cpu_counts':json.loads((root/'cpu/counts.json').read_text()),
    }
    for side in ('cpu','gpu'):
        manifest[side]={
            part:file(root/side/('hits.bin' if part=='hits' else part+'.pfm'))
            for part in ('hits','direct','indirect','total')
        }
    for i in range(4):
        for part in ('direct','indirect','total'):
            file(root/'cpu'/f'seed-{i}'/(part+'.pfm'))
    return manifest

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture',type=Path,required=True)
    ap.add_argument('--scene',type=Path,required=True)
    ap.add_argument('--repo',type=Path,default=Path('.'))
    ap.add_argument('--source-commit',required=True)
    args=ap.parse_args()
    manifest=build(args.capture,args.scene,args.repo,args.source_commit)
    result_file=args.capture/'component-manifest.json'
    result_file.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    summary=analyze(result_file)
    (args.capture/'component-diagnostic.json').write_text(
        json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps({
        'classification':'diagnostic-only',
        'primary_match':summary['primary']['match'],
        'gpu_reconstruction_passed':summary['reconstruction']['gpu']['passed'],
        'historical_causation_proven':False
    },indent=2))
if __name__=='__main__':
    main()
