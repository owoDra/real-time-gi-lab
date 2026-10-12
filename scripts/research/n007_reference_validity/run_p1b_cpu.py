#!/usr/bin/env python3
"""N007 P1-B one-command CPU-only postprocess, from a private existing capture.

Run only on the machine holding the raw ignored capture; NO GPU dispatch.
Preserve historical N001-N006 files, source code and classifications.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from component_contract import analyze
from replay_probe_image import replay_capture
from run_reference_ladder import campaign

def resolve_native_binary(build_dir: Path, name: str) -> Path:
    """Resolve the N007 CMake subdirectory layout or explicit flat bin dir.

    CMake currently puts CPU-only add_executable targets in its declaring
    binary subdirectory, unlike phos-n007-capture which sets root RUNTIME_OUTPUT_DIRECTORY.
    Prefer that current target location so an old executable at build root
    can never silently shadow it.
    """
    if Path(name).name != name or not name.startswith('phos-n007-'):
        raise ValueError('invalid N007 native binary name')
    paths = (
        build_dir / 'src/research/n007_reference_validity' / name,
        build_dir / name,
    )
    for path in paths:
        if path.is_file():
            return path.resolve()
    raise ValueError(
        'CPU-only native tool not built: ' + name +
        ' (checked: ' + ', '.join(str(path) for path in paths) + ')')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture',type=Path,required=True)
    ap.add_argument('--bin-dir',type=Path,required=True,
                    help='CMake output dir with CPU-only N007 targets')
    args=ap.parse_args()
    root=args.capture.resolve()
    native=args.bin_dir.resolve()
    manifest=root/'component-manifest.json'
    if not manifest.is_file():
        raise ValueError('N007 previously captured component-manifest.json is required')
    diagnostic=analyze(manifest)
    if (not diagnostic['primary']['match'] or
        not diagnostic['primary_geometry_attestation'] or
        not diagnostic['primary_geometry_attestation']['match']):
        raise ValueError('N007 primary-world-state mismatch blocks prospective study')
    if not diagnostic['probe_shadow_replay_testable']:
        raise ValueError('GPU probe ray/hit/fixed contribution replay invalid')
    def run(binary: str,*opts: str):
        subprocess.run([str(resolve_native_binary(native,binary)),*opts],check=True)
    for test in ('phos-n007-cpu-test','phos-n007-probe-test'):
        run(test)
    flags=root/'gpu/probe-shadow-flags.bin'
    if not flags.exists():
        run('phos-n007-probe-offline','--capture',str(root))
    # Read-only baseline replay, then independently shadow-filtered replay.
    try:
        image=replay_capture(root,flags)
    except ValueError as error:
        # A numerically failed baseline reconstruction does not invalidate
        # the separate CPU statistical reference screen. Other malformed
        # source/provenance failures still fail closed.
        if 'baseline probe-to-image replay failed' not in str(error):
            raise
        image={'baseline_reconstruction_passed':False,
               'shadow_counterfactual_eligible':False,
               'diagnostic_blocker':str(error)}
    image_path=root/'probe-image-replay.json'
    if image_path.exists():
        old=json.loads(image_path.read_text())
        if old!=image:
            raise ValueError('previous pixel replay differs from current provenance')
    else:
        image_path.write_text(json.dumps(image,indent=2,sort_keys=True,
                                        allow_nan=False)+'\n')
    # Statistical eligibility is INDEPENDENT of the GPU estimator's leakage.
    # It is still measured if the original GPU image replay failed; that
    # separate mismatch remains a recorded fail-closed causal blocker.
    eligibility=campaign(root,resolve_native_binary(native,'phos-n007-cpu-reference'))
    summary={
        'classification':'diagnostic-only',
        'source_commit':diagnostic['frame']['source_commit'],
        'frame_state_sha256':diagnostic['frame']['frame_state_sha256'],
        'gpu_indirect_baseline_reconstruction_passed':
            image['baseline_reconstruction_passed'],
        'gpu_probe_shadow_counterfactual':
            image.get('counterfactual'),
        'statistical_eligibility_status':eligibility['status'],
        'statistical_eligible_at_spp':eligibility['eligible_at_spp'],
        'tested_spp':[x['spp'] for x in eligibility['rows']],
        'per_level_active_fraction':[x['active_fraction'] for x in eligibility['rows']],
        'physical_correctness_proven':False,
        'historical_causation_proven':False,
        'lane_closed':False,
        'remaining_lane_scope':[
            'preregistered camera/disocclusion and positive light-motion controls',
            'independent known-lit/shadow GPU physical control',
            'remaining preregistered dynamic classes or explicit unmeasurable decision',
            'GPU camera/secondary provenance attestation']}
    print(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False))

if __name__=='__main__':
    main()
