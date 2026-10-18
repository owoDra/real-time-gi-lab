#!/usr/bin/env python3
"""Plan127: add separate readback accounting to immutable400 source only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

from prepare_tiled_pixel_pt import overlay

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
BASE = ROOT/'out/research/n010-comparison-readiness'
PLAN = RESULTS.parent/'experiments/127-continuation-readback-accounting.md'
WORK = BASE/'continuation-pixel-pt-accounted-source-v1'
OUTPUT = RESULTS/'405-continuation-readback-source-prepare.json'


def main():
    if WORK.exists() or OUTPUT.exists():
        raise ValueError('refuse existing405/source')
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:
        os.nice(15-priority)
    inputs = {}
    def checked(path, expected=None):
        path = Path(path).resolve()
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if expected is not None and digest != expected:
            raise ValueError('input identity differs: '+str(path))
        if str(path) in inputs and inputs[str(path)]!=digest:
            raise ValueError('input changed')
        inputs[str(path)] = digest
        return raw
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),PLAN,Path(__file__).with_name('prepare_tiled_pixel_pt.py')):
        if checked(path) != subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))]):
            raise ValueError('commit exact source/plan first')
    parent = json.loads(checked(RESULTS/'400-continuation-pixel-pt-source-prepare.json'))
    if not parent['complete'] or not parent['source_preparation_valid'] or parent['compiled']:
        raise ValueError('valid source400 required')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in parent[group].items():
            checked(name,digest)
    source = BASE/'continuation-pixel-pt-source-v1'
    host = checked(source/'continuation_pixel_pt.cpp').decode()
    shader = checked(source/'continuation_pixel_pt.comp.glsl')
    edits = [
        ('        std::ofstream times(out/"frames.json");times<<std::setprecision(17);',
         '        std::ofstream times(out/"frames.json");times<<std::setprecision(17);\n'
         '        std::ofstream readback_times(out/"readback-timings.jsonl");readback_times<<std::setprecision(17);',1),
        ('            n::AllocationLedger::instance().phase("diagnostic-readback-"+std::to_string(f));',
         '            const auto readback_started=Clock::now();\n'
         '            n::AllocationLedger::instance().phase("diagnostic-readback-"+std::to_string(f));',1),
        ('            }\n        }\n        times<<',
         '            }\n'
         '            const double readback_wall=std::chrono::duration<double,std::micro>(Clock::now()-readback_started).count();\n'
         '            readback_times<<"{\\\"index\\\":"<<f<<",\\\"wall_us\\\":"<<readback_wall<<"}"<<std::endl;\n'
         '            if(!readback_times)throw std::runtime_error("readback timing output failed");\n'
         '        }\n        times<<',1)]
    revised = overlay(host,edits)
    WORK.mkdir(parents=True)
    (WORK/'continuation_pixel_pt.cpp').write_text(revised)
    (WORK/'continuation_pixel_pt.comp.glsl').write_bytes(shader)
    (WORK/'source-edits.json').write_text(json.dumps(edits,indent=2)+'\n')
    result = dict(schema='n010-continuation-readback-source/1',complete=True,
        source_preparation_valid=True,all_pass=False,compiled=False,gpu_run=False,
        accepted_timing=False,reference_admission=False,source_commit=commit,input_sha256=inputs,
        payload_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in WORK.iterdir()},
        whole_host_inverse_exact=True,whole_shader_inverse_exact=True,
        per_sample_transport_scalar_sum_body_byte_identical=True,shader_byte_identical_to400=True,
        classification='READBACK_ACCOUNTED_CONTINUATION_SOURCE_UNCOMPILED_NO_ADMISSION',
        tests='NOT_RUN; source preparation only')
    for name,digest in list(inputs.items()):
        checked(name,digest)
    with OUTPUT.open('x') as out:
        out.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(result['classification'])


if __name__ == '__main__':
    main()
