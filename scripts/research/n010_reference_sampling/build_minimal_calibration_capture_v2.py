#!/usr/bin/env python3
"""Plan 045: preserve 156 and build its isolated output-directory repair."""
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0,str(SCRIPTS))
from generate_rqmc_oracle import once
from reference_provenance import sha

if __name__ == '__main__':
    original = Path(__file__).with_name('build_minimal_calibration_capture.py')
    if sha(original) != '65bd2a5ede54240e957219b706d6beb518576b61cbd7467fd1c800741c650826':
        raise ValueError('frozen 156 builder changed')
    source = original.read_text()
    source = once(source,'044-prospective-minimal-calibration-capture.md',
        '045-minimal-capture-output-directory-repair.md')
    source = once(source,'Path(__file__),PLAN,BUILD/\'build.ninja\',',
        "Path(__file__),Path(_original_builder),RESULTS/'156-minimal-calibration-fixture-build.json',PLAN,BUILD/'build.ninja',")
    old = "'            if(doses.empty())copy_state(target&&(f>0||!doses.empty()) ? target_path : state,frame_out);'"
    new = "'            if(doses.empty())copy_state(target&&(f>0||!doses.empty()) ? target_path : state,frame_out);\\n            else fs::create_directories(frame_out);'"
    source = once(source,old,new)
    source = once(source,'n010-minimal-calibration-fixture-build/1','n010-minimal-calibration-fixture-build/2')
    exec(compile(source,str(original)+'#plan045','exec'),
        {'__name__':'__main__','__file__':__file__,'_original_builder':str(original.resolve())})
