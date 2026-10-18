#!/usr/bin/env python3
"""Plans126/127: acquire one complete continuation image or replay both for404."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import struct
import subprocess
import time

from build_tiled_pixel_pt import quiet

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
BASE = ROOT/'out/research/n010-comparison-readiness'
WORK = BASE/'continuation-pixel-pt-numerical-v1'
BUILD = BASE/'continuation-pixel-pt-build-v1'
OUTPUT = RESULTS/'404-continuation-pixel-pt-numerical.json'
POLICY = RESULTS.parent/'experiments/126-exact-sample-continuation-pixel-pt.md'
INPUTS = {}


def checked(path, expected=None):
    path = Path(path).resolve()
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError('identity differs: '+str(path))
    if str(path) in INPUTS and INPUTS[str(path)] != digest:
        raise ValueError('input changed: '+str(path))
    INPUTS[str(path)] = digest
    return raw


def unchanged():
    for name, digest in list(INPUTS.items()):
        checked(name, digest)


def positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def close(a, b):
    return math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-8)


def inputs(cell):
    for path in (Path(__file__), POLICY, Path(__file__).with_name('build_tiled_pixel_pt.py')):
        checked(path)
    build = json.loads(checked(RESULTS/'401-continuation-pixel-pt-build.json'))
    if not (build['complete'] and build['build_valid'] and build['all_pass']
            and not build['gpu_run'] and not build['accepted_timing'] and not build['reference_admission']):
        raise ValueError('valid private401 build required')
    for group in ('input_sha256', 'payload_sha256'):
        for name, digest in build[group].items():
            checked(name, digest)
    original = json.loads(checked(RESULTS/'046-calibration-quiet-sizing.json',
        '2ab654662ffdef9b873179d95a9142eea7e18ad0635cec37601c51f0f828d36d'))
    row = next(r['evidence'] for r in original['rows'] if r['boundary']['id'] == cell+'-pt-B8')
    command = row['command']
    state = Path(command[command.index('--state')+1])
    archive = Path(command[command.index('--out')+1])
    for name in ('geometry-state.bin', 'frame-state.bin'):
        digest = row['payload_sha256']['frames/0/'+name]
        if checked(state/name, digest) != checked(archive/'frames/0'/name, digest):
            raise ValueError('archived state differs')
    for component in ('direct', 'indirect', 'total'):
        name = component+'.pfm'
        checked(archive/'frames/0'/name, row['payloads'][0]['images'][component])
    checked(ROOT/'scripts/run_with_vulkan.sh')
    return state, archive


def ledger_replay(path):
    ledger = json.loads(checked(path))
    live, peak, devices = {}, 0, set()
    for sequence, event in enumerate(ledger['events']):
        if (event['sequence'] != sequence or type(event['bytes']) is not int or event['bytes'] <= 0
                or type(event['device_context']) is not int or event['device_context'] <= 0
                or type(event['allocation_id']) is not int or event['allocation_id'] <= 0):
            raise ValueError('invalid owned allocation event')
        key = event['device_context'], event['allocation_id']
        devices.add(key[0])
        if event['action'] == 'allocate' and key not in live:
            live[key] = event['bytes']
        elif event['action'] == 'free' and key in live and live[key] == event['bytes']:
            del live[key]
        else:
            raise ValueError('owned allocation lifetime differs')
        current = sum(live.values())
        peak = max(peak, current)
        if current != event['live_bytes']:
            raise ValueError('owned live bytes differ')
    if (live or not 0 < peak <= 8*1024**3 or peak != ledger['true_peak_owned_bytes']
            or ledger['live_bytes_at_teardown'] != 0 or ledger['teardown_zero'] is not True
            or len(devices) != ledger['device_contexts']):
        raise ValueError('owned peak/teardown differs')
    return peak


def replay(cell, state, archive, native_elapsed_seconds):
    directory = WORK/cell/'capture'
    metadata = json.loads(checked(directory/'frames.json'))
    state_raw = checked(state/'frame-state.bin')
    width, height = struct.unpack_from('<II', state_raw, 12)
    pixels = width*height
    if (metadata['schema'] != 'n010-continuation-pixel-pt/1'
            or metadata['timing_classification'] != 'DIAGNOSTIC_UNCALIBRATED'
            or (metadata['family'],metadata['spp'],metadata['vertices'],metadata['seed'],metadata['width'],metadata['height'])
            != ('pixel-pt',1024,8,305419896,width,height) or len(metadata['frames']) != 1):
        raise ValueError('whole image identity differs')
    frame = metadata['frames'][0]
    if ((frame['index'],frame['state'],frame['seed'],frame['tile_pixels'],frame['pause_us'],
         frame['sample_chunk'],frame['sample_state_bytes']) != (0,'static',305419896,4096,2000,16,pixels*16)):
        raise ValueError('static continuation frame scope differs')
    for key in ('dose','known_work_gpu_us','maintenance_gpu_us','uniform_upload_gpu_us',
                'geometry_upload_gpu_us','blas_update_us','tlas_update_us','changed_slots'):
        if frame[key] != 0:
            raise ValueError('unexpected static maintenance or known work')
    for name in ('frame-state.bin','geometry-state.bin'):
        raw = checked(state/name)
        if checked(directory/name) != raw or checked(directory/'frames/0'/name) != raw:
            raise ValueError('captured state differs')
    images = {}
    image_bytes = {}
    for component in ('direct','indirect','total'):
        name = component+'.pfm'
        expected = checked(archive/'frames/0'/name)
        actual = checked(directory/name)
        if actual != expected or checked(directory/'frames/0'/name) != expected:
            raise ValueError('whole-image byte mismatch: '+cell+'/'+name)
        images[component] = hashlib.sha256(expected).hexdigest()
        image_bytes[component] = actual
    raw_state = checked(directory/'sample-state.bin')
    if len(raw_state) != pixels*16 or checked(directory/'frames/0/sample-state.bin') != raw_state:
        raise ValueError('full final state stream differs')
    pfm_header = f'PF\n{width} {height}\n-1.0\n'.encode()
    if not image_bytes['indirect'].startswith(pfm_header):
        raise ValueError('original PFM layout differs')
    for pixel,words in enumerate(struct.iter_unpack('<4I',raw_state)):
        total = struct.unpack('<f',struct.pack('<I',words[1]))[0]
        if words[2:] != (1024,0) or not math.isfinite(total) or total < 0:
            raise ValueError('final sample progress/error/float sum differs')
        y,x = divmod(pixel,width)
        offset = len(pfm_header)+((height-1-y)*width+x)*12
        expected = struct.pack('<f',total/1024)*3
        if image_bytes['indirect'][offset:offset+12] != expected:
            raise ValueError('final state sum does not produce final image')
    rows = [json.loads(line) for line in checked(directory/'tile-timings.jsonl').splitlines()]
    expected_count = 64*((pixels+4095)//4096)
    if len(rows) != expected_count:
        raise ValueError('missing/extra sample/pixel dispatches')
    active,maximum,previous_end = 0.0,0.0,None
    bits,period = rows[0]['timestamp_valid_bits'],rows[0]['timestamp_period_ns']
    if type(bits) is not int or not 1 <= bits <= 64 or not positive(period) or math.ldexp(period,bits)/1e9 <= 180:
        raise ValueError('unsupported timestamp range')
    mask = (1<<bits)-1
    index,scored_pixel_samples = 0,0
    for sample_begin in range(0,1024,16):
        sample_end = min(1024,sample_begin+16)
        for pixel_begin in range(0,pixels,4096):
            row = rows[index]
            count = min(4096,pixels-pixel_begin)
            if ((row['image_index'],row['seed'],row['sample_begin'],row['sample_end'],row['pixel_begin'],row['pixel_count'])
                    != (0,305419896,sample_begin,sample_end,pixel_begin,count)
                    or row['timestamp_valid_bits'] != bits or row['timestamp_period_ns'] != period):
                raise ValueError('sample/pixel coverage or identity differs')
            begin,end = row['begin_tick'],row['end_tick']
            if any(type(x) is not int or not 0 <= x < 2**64 for x in (begin,end)):
                raise ValueError('invalid raw timestamps')
            duration = ((end-begin)&mask)*period/1000
            if not positive(duration) or duration > 250000 or not close(duration,row['gpu_us']):
                raise ValueError('bounded dispatch GPU duration differs')
            if previous_end is not None and ((begin-previous_end)&mask)*period/1e9 >= 180:
                raise ValueError('dispatch timestamp order differs')
            previous_end = end
            active += duration
            maximum = max(maximum,duration)
            scored_pixel_samples += count*(sample_end-sample_begin)
            index += 1
    envelope = ((rows[-1]['end_tick']-rows[0]['begin_tick'])&mask)*period/1000
    if (scored_pixel_samples != pixels*1024 or not positive(envelope) or envelope >= 180e6 or envelope < active
            or not all(close(frame[k],v) for k,v in (
                ('image_active_gpu_us',active),('active_gpu_us',active),('max_tile_gpu_us',maximum),
                ('image_gpu_us',envelope),('image_envelope_gpu_us',envelope),('gpu_us',envelope)))
            or not positive(frame['wall_us']) or frame['wall_us'] >= 180e6):
        raise ValueError('complete frame cost replay differs')
    readbacks = [json.loads(line) for line in checked(directory/'readback-timings.jsonl').splitlines()]
    if len(readbacks)!=1 or readbacks[0]['index']!=0 or not positive(readbacks[0]['wall_us']):
        raise ValueError('missing separate readback duration')
    if frame['wall_us']+readbacks[0]['wall_us'] > native_elapsed_seconds*1e6:
        raise ValueError('component wall costs exceed end-to-end native cost')
    return dict(images_byte_exact=images,pixels=pixels,pixel_samples=scored_pixel_samples,
        dispatch_count=len(rows),active_gpu_us=active,image_envelope_gpu_us=envelope,
        cpu_frame_wall_us=frame['wall_us'],readback_wall_us=readbacks[0]['wall_us'],
        native_elapsed_seconds=native_elapsed_seconds,max_dispatch_gpu_us=maximum,
        final_state_count=pixels,final_state_progress_exact=True,final_state_errors_zero=True,
        final_state_sum_image_exact=True,final_rng_and_sum_state_sha256=hashlib.sha256(raw_state).hexdigest(),
        persistent_sample_state_bytes=pixels*16,
        owned_peak_bytes=ledger_replay(directory/'allocation-ledger.json'),owned_teardown_zero=True,
        accepted_timing=False,reference_admission=False)


def part_result(cell):
    return RESULTS/('402-continuation-pixel-pt-c1.json' if cell=='C1' else '403-continuation-pixel-pt-c7.json')


def command_for(state, cell):
    return ['bash',str(ROOT/'scripts/run_with_vulkan.sh'),str(BUILD/'phos-n010-continuation-pixel-pt'),
        '--state',str(state),'--out',str(WORK/cell/'capture'),'--family','pixel-pt',
        '--spp','1024','--vertices','8','--seed','305419896','--frames','1',
        '--tile-pixels','4096','--sample-chunk','16','--pause-us','2000']


def native_receipt(cell, record, command):
    actual = json.loads(checked(WORK/cell/'native.resources.json'))
    if (record['native_returncode'] != 0 or record['pid'] != actual['pid']
            or actual['pid'] != actual['pgid'] or type(actual['start_ticks']) is not int
            or actual['start_ticks'] <= 0 or actual['boot_id'] != record['environment']['boot_id']
            or actual['cpu'] != [120,120] or actual['address_space'] != [-1,-1]
            or actual['affinity'] != [31] or actual['nice'] != 15
            or actual['elapsed_limit_seconds'] != 180 or actual['command'] != command
            or not positive(record['elapsed_seconds']) or record['elapsed_seconds'] > 180
            or not 0 <= record['child_cpu_seconds'] <= 120):
        raise ValueError('native terminal/resource receipt differs')
    return actual


def retained_part(cell):
    raw = checked(WORK/cell/'record.json')
    if checked(part_result(cell)) != raw:
        raise ValueError('published/local part identity differs')
    record = json.loads(raw)
    if not record['complete'] or not record['numerical_replay_valid']:
        raise ValueError('prior part incomplete/failed; no next capture')
    for name,digest in record['input_sha256'].items():
        checked(name,digest)
    for name,digest in record['payload_sha256'].items():
        checked(name,digest)
    state,archive = inputs(cell)
    native_receipt(cell,record,command_for(state,cell))
    return replay(cell,state,archive,record['elapsed_seconds'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--cell', choices=('C1','C7'))
    mode.add_argument('--summarize', action='store_true')
    args = parser.parse_args()
    os.sched_setaffinity(0,{31})
    priority = os.getpriority(os.PRIO_PROCESS,0)
    if priority < 15:
        os.nice(15-priority)
    if args.summarize:
        if OUTPUT.exists():
            raise ValueError('refuse existing404; no overwrite')
        rows = {cell:retained_part(cell) for cell in ('C1','C7')}
        unchanged()
        result = dict(schema='n010-continuation-pixel-pt-numerical/1',complete=True,
            numerical_replay_valid=True,all_pass=False,accepted_timing=False,reference_admission=False,
            classification='TWO_STATIC_WHOLE_IMAGES_BYTE_EXACT_NO_ADMISSION',rows=rows,
            input_sha256=INPUTS,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            tests='NOT_RUN; archived-image implementation-equivalence scientific replay only')
        with OUTPUT.open('x') as out:
            out.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        print(result['classification'])
        return 0
    quiet()
    for number,step in ((381,'build'),(382,'old'),(383,'guarded')):
        diagnostic = json.loads(checked(RESULTS/f'{number}-early-density-route-{step}.json'))
        if not diagnostic['complete'] or not diagnostic['step_valid']:
            raise ValueError('review119 failure before new GPU work; no dispatch')
    if args.cell == 'C7':
        retained_part('C1')
    part = WORK/args.cell
    if part.exists() or part_result(args.cell).exists() or OUTPUT.exists():
        raise ValueError('refuse existing part or404; no retry')
    state,archive = inputs(args.cell)
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    for path in (Path(__file__).resolve(),POLICY):
        frozen = subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))])
        if frozen != checked(path):
            raise ValueError('commit exact driver/policy before capture')
    import shutil
    if shutil.disk_usage(BASE).free < 2*1024**3:
        raise ValueError('2GiB disk guard; no GPU')
    part.mkdir(parents=True)
    command = command_for(state,args.cell)
    environment = dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        kernel=os.uname().release,opengl_driver_root=str(Path('/run/opengl-driver').resolve()),variables={k:os.environ.get(k) for k in
            ('VK_ICD_FILENAMES','VK_DRIVER_FILES','AMD_VULKAN_ICD','RADV_PERFTEST','RADV_DEBUG')},
        drm_devices={})
    for device in Path('/sys/class/drm').glob('renderD*/device'):
        environment['drm_devices'][str(device)] = dict(pci=str(device.resolve()),
            **{key:(device/key).read_text().strip() for key in ('vendor','device','revision')})
    record = dict(schema='n010-continuation-pixel-pt-numerical-part/1',cell=args.cell,
        complete=False,numerical_replay_valid=False,all_pass=False,accepted_timing=False,
        reference_admission=False,gpu_run=True,source_commit=commit,input_sha256=INPUTS,
        environment=environment,command=command,classification='NUMERICAL_CAPTURE_IN_PROGRESS',
        tests='NOT_RUN; whole-image implementation-equivalence scientific capture only')

    def save():
        serialized = json.dumps(record,indent=2,allow_nan=False)+'\n'
        (part/'record.json').write_text(serialized)
        part_result(args.cell).write_text(serialized)

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU,(120,120))
        resource.setrlimit(resource.RLIMIT_AS,(resource.RLIM_INFINITY,resource.RLIM_INFINITY))
        (part/'native.resources.json').write_text(json.dumps(dict(pid=os.getpid(),pgid=os.getpgrp(),
            boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
            cpu=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space=list(resource.getrlimit(resource.RLIMIT_AS)),
            affinity=sorted(os.sched_getaffinity(0)),nice=os.getpriority(os.PRIO_PROCESS,0),
            elapsed_limit_seconds=180,command=command))+'\n')

    save()
    try:
        quiet()
        unchanged()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        started = time.monotonic()
        with (part/'native.stdout').open('wb') as out,(part/'native.stderr').open('wb') as err:
            native = subprocess.Popen(command,cwd=ROOT,stdout=out,stderr=err,
                                      start_new_session=True,preexec_fn=limits)
            record['pid'] = native.pid
            save()
            try:
                code = native.wait(timeout=180)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(native.pid,signal.SIGKILL)
                except ProcessLookupError:
                    pass
                native.wait(timeout=5)
                code = 'TIMEOUT_PARTIALS_RETAINED'
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        record.update(native_returncode=code,elapsed_seconds=time.monotonic()-started,
            child_cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            child_peak_rss_kib=after.ru_maxrss)
        save()
        native_receipt(args.cell,record,command)
        record['validation'] = replay(args.cell,state,archive,record['elapsed_seconds'])
        unchanged()
        record.update(numerical_replay_valid=True,classification='WHOLE_IMAGE_BYTE_EXACT_NO_ADMISSION')
    except (OSError,ValueError,KeyError,IndexError,subprocess.SubprocessError) as error:
        record.update(failure=str(error),classification='NUMERICAL_FAILURE_PARTIALS_RETAINED')
    record['payload_sha256'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in part.rglob('*') if p.is_file() and p.name != 'record.json'}
    record['complete'] = True
    save()
    print(record['classification'])
    return 0 if record['numerical_replay_valid'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
