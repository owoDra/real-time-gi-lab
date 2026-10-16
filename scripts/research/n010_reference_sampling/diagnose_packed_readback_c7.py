#!/usr/bin/env python3
"""Plan 060: one C7 sizing and one original eight-block diagnostic, no admission."""
import argparse
import hashlib
import inspect
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE.parent/'n010_comparison_readiness'))
import calibrate_renderer as C
from readiness_preflight import replay
from deferred_image_calibration_program import environment
from diagnose_deferred_c7_precision import BoundedSubprocess
from run_primary_direction_sequence import require_no_other_research_worker

RESULTS=ROOT/'research/lanes/n010-comparison-readiness/results'
WORK=ROOT/'out/research/n010-comparison-readiness'
FIXTURE=WORK/'packed-readback-build-v1'
INPUTS={}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path,expected=None):
    path=Path(path);raw=path.read_bytes();h=hashlib.sha256(raw).hexdigest()
    if expected is not None and h!=expected:raise ValueError('input identity differs: '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)]!=h:raise ValueError('input changed: '+str(path))
    INPUTS[str(path)]=h
    return raw


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('sizing','diagnostic'),required=True)
    mode=parser.parse_args().mode
    stem='200-packed-readback-c7-sizing' if mode=='sizing' else '201-packed-readback-c7-precision-diagnostic'
    work=WORK/('packed-readback-c7-sizing-v1' if mode=='sizing' else 'packed-readback-c7-diagnostic-v1')
    output=RESULTS/(stem+'.json')
    if work.exists() or output.exists():raise ValueError('refuse existing acquisition')
    require_no_other_research_worker()
    for p in (Path(__file__),HERE/'build_packed_readback_capture.py',
        RESULTS.parent/'experiments/060-packed-readback-cadence-diagnosis.md',
        Path(sys.modules['readiness_preflight'].__file__),
        Path(sys.modules['diagnose_deferred_c7_precision'].__file__),
        Path(sys.modules['deferred_image_calibration_program'].__file__),
        Path(sys.modules['run_primary_direction_sequence'].__file__),ROOT/'scripts/run_with_vulkan.sh',
        ROOT/'build/n009/n010-neutral-work-verify'):
        read(p)
    read(C.__file__,'64deb4d3995eb40498ca2b454dacf6d97d5909115ef32a36e3c80c3a7683cb8d')
    build_path=RESULTS/'199-packed-readback-fixture-build.json'
    build=json.loads(read(build_path))
    if (build['schema']!='n010-packed-readback-fixture-build/1' or
        not all(build.get(k) for k in ('complete','all_pass','whole_parent_source_inverses_exact',
            'timed_gpu_recording_through_stamp15_byte_identical','timing_expressions_byte_identical','active_inputs_byte_unchanged')) or
        len(build['steps'])!=3 or any(s['returncode']!=0 for s in build['steps'])):
        raise ValueError('complete exact packed build required')
    for p,h in build['input_sha256'].items():read(p,h)
    for p,h in build['generated_sha256'].items():read(FIXTURE/p,h)
    lock_path=RESULTS/'026-dynamic-execution-state-lock.json';lock=json.loads(read(lock_path))
    baseline=json.loads(read(RESULTS/'046-calibration-quiet-sizing.json',
        '2ab654662ffdef9b873179d95a9142eea7e18ad0635cec37601c51f0f828d36d'))
    if not baseline['complete'] or not baseline['all_pass'] or baseline['lock_sha256']!=sha(lock_path):
        raise ValueError('original image baseline differs')
    boundary=next(b for b in C.boundaries(lock) if b['id']=='C7-hwrt')
    expected_images=next(r['evidence']['payloads'][0]['images'] for r in baseline['rows'] if r['boundary']['id']=='C7-hwrt')
    for p in (ROOT/'out/research/n008-hdr-oracle/phase-b-states/n004-scenes').rglob('*'):
        if p.is_file():read(p)
    read(ROOT/'out/research/n010-comparison-readiness/light-selection-v1/sponza-local-motion.n009contract')
    for p in (ROOT/'build/n009/shaders').glob('*.spv'):read(p)
    observation=environment()
    frozen=None
    sizing_path=RESULTS/'200-packed-readback-c7-sizing.json'
    if mode=='diagnostic':
        sizing=json.loads(read(sizing_path))
        if (not sizing['complete'] or not sizing['all_pass'] or len(sizing['rows'])!=1 or
            sizing['lock_sha256']!=sha(lock_path) or sizing['build_sha256']!=sha(build_path) or
            sizing['execution_environment']!=observation):
            raise ValueError('complete same-environment packed C7 sizing required')
        frozen=sizing['rows'][0]['frozen_dose']
    bounded=BoundedSubprocess()
    original=inspect.getsource(C.execute);source=original
    edits=[("ROOT/'build/n009/phos-n010-capture'",repr(FIXTURE/'phos-n010-capture').replace('PosixPath','Path')),
        (' env=os.environ.copy();cell=',
         ' env=os.environ.copy();env["PHOS_N010_MINIMAL_CALIBRATION_READBACK"]="1";env["PHOS_N010_PACKED_CALIBRATION_READBACK"]="1";cell=')]
    for old,new in edits:
        if source.count(old)!=1:raise ValueError('original execute anchor differs')
        source=source.replace(old,new)
    restored=source
    for old,new in reversed(edits):restored=restored.replace(new,old)
    if restored!=original:raise ValueError('whole execute inverse differs')
    scope=dict(C.__dict__);scope['subprocess']=bounded
    exec(compile(source,str(Path(__file__))+'#execute-overlay','exec'),scope)
    result=dict(schema='n010-packed-readback-c7-diagnostic/1',mode=mode,complete=False,all_pass=False,
        diagnostic_only=True,accepted_timing=False,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        build_sha256=sha(build_path),lock_sha256=sha(lock_path),execution_environment=observation,
        fixture_input_sha256=INPUTS,rows=[],diagnostic_native_resources=bounded.receipts,
        execute_dispatch_proof=dict(whole_original_execute_inverse_exact=True,
            original_execute_sha256=hashlib.sha256(original.encode()).hexdigest(),
            generated_execute_sha256=hashlib.sha256(source.encode()).hexdigest(),
            schedule_analysis_source_sha256=sha(C.__file__),
            edits=[dict(old=a,new=b) for a,b in edits]),
        tests='NOT_RUN; isolated scientific acquisition, not regression validation')
    if mode=='diagnostic':result['plan_sha256']=sha(sizing_path)
    def save():output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    save()

    def execute(doses,directory):
        if environment()!=observation:raise ValueError('execution environment changed')
        block=scope['execute'](boundary,lock,doses,directory)
        if not replay(block['allocation_ledger']):raise ValueError('owned ledger failed')
        if any(p['images']!=expected_images for p in block['payloads']):
            raise ValueError('packed image differs from original 046')
        for name,limit in (('deferred-image-serialization.json',256*1024**2),('packed-scratch-spool.json',16*1024**2)):
            spool=json.loads((directory/name).read_bytes())
            peak='rgba_capacity_peak_bytes' if name.startswith('deferred') else 'capacity_peak_bytes'
            cap='rgba_capacity_limit_bytes' if name.startswith('deferred') else 'capacity_limit_bytes'
            end='rgba_capacity_bytes_after_flush' if name.startswith('deferred') else 'capacity_bytes_after_flush'
            if (not spool['complete'] or spool['retained_frames']!=len(doses) or
                spool['written_frames']!=len(doses) or spool[cap]!=limit or spool[peak]>limit or spool[end]!=0):
                raise ValueError('packed CPU spool bound/completeness/release differs')
            block[name]=spool
        block.update(images_byte_equal_to_original_046=True,allocation_ledger_replay_pass=True)
        if environment()!=observation:raise ValueError('environment changed during native work')
        return block

    try:
        row=dict(boundary=boundary);result['rows'].append(row)
        if mode=='sizing':
            block=execute([0,65536,262144]*3,work/boundary['id']/'sizing');samples=block['samples']
            med={dose:statistics.median(s['gpu_us'] for s in samples if s['dose']==dose) for dose in (0,65536,262144)}
            inner={dose:statistics.median(s['known_work_gpu_us'] for s in samples if s['dose']==dose) for dose in (0,65536,262144)}
            slopes=[(inner[d]-inner[0])/d for d in (65536,262144)]
            dose=math.ceil(.2*med[0]/statistics.median(slopes)) if min(slopes)>0 else None
            row.update(evidence=block,medians_us=med,known_work_medians_us=inner,
                frozen_dose=dose,sizing_pass=dose is not None and dose<=100000000)
            result['all_pass']=row['sizing_pass']
        else:
            row['blocks']=[]
            for i in range(8):
                require_no_other_research_worker();time.sleep(1)
                records=C.schedule(frozen,i)
                block=execute([r['dose'] for r in records],work/boundary['id']/f'block-{i}')
                if (block['binary_sha256']!=sizing['rows'][0]['evidence']['binary_sha256'] or
                    block['shader_sha256']!=sizing['rows'][0]['evidence']['shader_sha256']):
                    raise ValueError('sized binary/shaders changed')
                block['tagged_samples']=[dict(s,**{k:v for k,v in r.items() if k not in s}) for s,r in zip(block['samples'],records)]
                row['blocks'].append(block);save()
            row['analysis']=C.analysis(row['blocks']);result['all_pass']=row['analysis']['all_pass']
        for p,h in list(INPUTS.items()):read(p,h)
        require_no_other_research_worker()
        result.update(complete=True,classification='DIAGNOSTIC_COMPLETE_NO_ADMISSION')
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        result.update(classification='OPERATIONAL_FAILURE_PARTIALS_RETAINED',failure=str(e))
    save()
    print(json.dumps(dict(complete=result['complete'],all_pass=result['all_pass'],failure=result.get('failure'))))
    raise SystemExit(0 if result['complete'] else 2)


if __name__=='__main__':main()
