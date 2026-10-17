#!/usr/bin/env python3
"""Plans 063/064: one contiguous C7 sizing and eight-block diagnosis only."""
import argparse
import hashlib
import inspect
import json
import math
import os
import resource
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
FIXTURE=WORK/'contiguous-c7-build-v3'
INPUTS={}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path,expected=None):
    path=Path(path);raw=path.read_bytes();h=hashlib.sha256(raw).hexdigest()
    if expected is not None and h!=expected:raise ValueError('input identity differs: '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)]!=h:raise ValueError('input changed: '+str(path))
    INPUTS[str(path)]=h
    return raw



class BatchBoundedSubprocess(BoundedSubprocess):
    def run(self,command,**kwargs):
        if len(command)>2 and command[:2]==['bash','scripts/run_with_vulkan.sh']:
            require_no_other_research_worker()
            out=Path(command[command.index('--out')+1]);receipt=out.parent/(out.name+'.resource-limits.json')
            record={'receipt_path':str(receipt),'command':command};self.receipts.append(record)
            def limits():
                resource.setrlimit(resource.RLIMIT_CPU,(30,30))
                receipt.write_text(json.dumps(dict(pid=os.getpid(),start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                    cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
                    affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),elapsed_limit_seconds=30,command=command))+'\n')
            kwargs.update(timeout=30,preexec_fn=limits)
            try:
                proc=subprocess.run(command,**kwargs);raw=receipt.read_bytes();actual=json.loads(raw)
                if actual['cpu']!=[30,30] or len(actual['affinity'])!=1 or actual['nice']!=15 or actual['command']!=command:
                    raise ValueError('actual batch native limits differ')
                record.update(receipt_sha256=hashlib.sha256(raw).hexdigest(),actual=actual,returncode=proc.returncode)
                return proc
            except subprocess.TimeoutExpired as e:
                (out.parent/(out.name+'.timeout.stdout')).write_bytes(e.stdout or b'')
                (out.parent/(out.name+'.timeout.stderr')).write_bytes(e.stderr or b'')
                record['failure']='ELAPSED_GUARD_PARTIALS_RETAINED';raise
        return subprocess.run(command,**kwargs)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('sizing','diagnostic'),required=True)
    mode=parser.parse_args().mode
    stem='207-contiguous-c7-sizing' if mode=='sizing' else '208-contiguous-c7-precision-diagnostic'
    work=WORK/('contiguous-c7-sizing-v3' if mode=='sizing' else 'contiguous-c7-diagnostic-v3')
    output=RESULTS/(stem+'.json')
    if work.exists() or output.exists():raise ValueError('refuse existing acquisition')
    require_no_other_research_worker()
    os.sched_setaffinity(0,{max(os.sched_getaffinity(0))});os.nice(15)
    for p in (Path(__file__),HERE/'build_contiguous_c7_capture_v3.py',HERE/'build_contiguous_c7_capture_v2.py',HERE/'build_contiguous_c7_capture.py',
        RESULTS.parent/'experiments/063-contiguous-c7-command-batch-diagnosis.md',RESULTS.parent/'experiments/064-contiguous-decoder-build-repair.md',RESULTS.parent/'experiments/065-contiguous-import-header-repair.md',
        Path(sys.modules['readiness_preflight'].__file__),
        Path(sys.modules['diagnose_deferred_c7_precision'].__file__),
        Path(sys.modules['deferred_image_calibration_program'].__file__),
        Path(sys.modules['run_primary_direction_sequence'].__file__),ROOT/'scripts/run_with_vulkan.sh',
        ROOT/'build/n009/n010-neutral-work-verify'):
        read(p)
    read(C.__file__,'64deb4d3995eb40498ca2b454dacf6d97d5909115ef32a36e3c80c3a7683cb8d')
    build_path=RESULTS/'206-contiguous-c7-import-repair-build.json'
    build=json.loads(read(build_path))
    if (build['schema']!='n010-contiguous-c7-fixture-build/1' or
        not all(build.get(k) for k in ('complete','all_pass','whole_parent_source_inverses_exact',
            'timed_gpu_recording_through_stamp15_byte_identical','timing_expressions_byte_identical','active_inputs_byte_unchanged')) or
        len(build['steps'])!=4 or any(s['returncode']!=0 for s in build['steps'])):
        raise ValueError('complete exact contiguous build required')
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
    sizing_path=RESULTS/'207-contiguous-c7-sizing.json'
    if mode=='diagnostic':
        sizing=json.loads(read(sizing_path))
        if (not sizing['complete'] or not sizing['all_pass'] or len(sizing['rows'])!=1 or
            sizing['lock_sha256']!=sha(lock_path) or sizing['build_sha256']!=sha(build_path) or
            sizing['execution_environment']!=observation):
            raise ValueError('complete same-environment contiguous C7 sizing required')
        frozen=sizing['rows'][0]['frozen_dose']
    bounded=BatchBoundedSubprocess()
    original=inspect.getsource(C.execute);source=original
    edits=[("ROOT/'build/n009/phos-n010-capture'",repr(FIXTURE/'phos-n010-capture').replace('PosixPath','Path')),
        (' env=os.environ.copy();cell=',
         ' env=os.environ.copy();env["PHOS_N010_MINIMAL_CALIBRATION_READBACK"]="1";env["PHOS_N010_PACKED_CALIBRATION_READBACK"]="1";env["PHOS_N010_CONTIGUOUS_C7"]="1";cell=')]
    for old,new in edits:
        if source.count(old)!=1:raise ValueError('original execute anchor differs')
        source=source.replace(old,new)
    restored=source
    for old,new in reversed(edits):restored=restored.replace(new,old)
    if restored!=original:raise ValueError('whole execute inverse differs')
    scope=dict(C.__dict__);scope['subprocess']=bounded
    exec(compile(source,str(Path(__file__))+'#execute-overlay','exec'),scope)
    result=dict(schema='n010-contiguous-c7-diagnostic/1',mode=mode,complete=False,all_pass=False,
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
            raise ValueError('contiguous image differs from original 046')
        for name,limit in (('deferred-image-serialization.json',256*1024**2),('packed-scratch-spool.json',16*1024**2)):
            spool=json.loads((directory/name).read_bytes())
            peak='rgba_capacity_peak_bytes' if name.startswith('deferred') else 'capacity_peak_bytes'
            cap='rgba_capacity_limit_bytes' if name.startswith('deferred') else 'capacity_limit_bytes'
            end='rgba_capacity_bytes_after_flush' if name.startswith('deferred') else 'capacity_bytes_after_flush'
            if (not spool['complete'] or spool['retained_frames']!=len(doses) or
                spool['written_frames']!=len(doses) or spool[cap]!=limit or spool[peak]>limit or spool[end]!=0):
                raise ValueError('contiguous CPU spool bound/completeness/release differs')
            block[name]=spool
        batch=json.loads((directory/'contiguous-batch.json').read_bytes())
        if (not batch['complete'] or batch['recorded_frames']!=len(doses) or batch['consumed_frames']!=len(doses) or
            batch['queue_submit_calls']!=1 or batch['fence_wait_calls']!=1 or batch['uniform_stride']!=4096 or
            not batch['uniform_alignment'] or 4096%batch['uniform_alignment'] or not 0<batch['uniform_range']<=4096):
            raise ValueError('batch count/limits receipt differs')
        expected=[dict(index=i,frame_id=i+1,uniform_offset=4096*i,query_first=24*i,query_written_count=18) for i in range(len(doses))]
        if batch['frames']!=expected:raise ValueError('batch per-frame identities differ')
        block.update(images_byte_equal_to_original_046=True,allocation_ledger_replay_pass=True,contiguous_batch=batch)
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
