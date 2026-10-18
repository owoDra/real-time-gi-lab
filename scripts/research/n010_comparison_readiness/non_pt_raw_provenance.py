"""Plan152: independent full non-PT raw/native/state/memory/quality intake."""
import json
import math
from pathlib import Path
import struct
import subprocess

import numpy as np
import continuation_quality_provenance as C
from continuation_quality_provenance import P, R, S
import hybrid_reference_provenance as H

PLAN = R.RESULTS.parent/'experiments/152-full-non-pt-raw-evidence-intake.md'
LOCK = R.RESULTS/'026-dynamic-execution-state-lock.json'
BUILD = R.RESULTS/'506-raw-query-pilot-build.json'
CONTRACT = R.BASE/'light-selection-v1/sponza-local-motion.n009contract'
SCOPE = ('static-C1-hwrt','static-C1-software','static-C1-dense-rc',
         'static-C7-hwrt','static-C7-software','static-C7-dense-rc',
         'dynamic-C6-hwrt','dynamic-C12-hwrt')


def identity(boundary):
    C.require(boundary in SCOPE, 'undeclared non-PT boundary')
    mode, cell, role = boundary.split('-', 2)
    return cell, role, mode == 'dynamic'


def command(boundary, capture, build, lock):
    cell, role, dynamic = identity(boundary)
    spec = lock['cells'][cell]
    cmd = ['bash', str(R.ROOT/'scripts/run_with_vulkan.sh'),
           build['binaries']['dense' if role == 'dense-rc' else 'rc']]
    if role == 'dense-rc':
        return cmd+['--state',str((R.ROOT/spec['state_directory']).resolve()),
            '--out',str(capture),'--family','dense-rc','--spp','1','--vertices','2',
            '--seed','305419896','--frames','1']
    scene = R.ROOT/('assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf'
        if cell in ('C1','C6') else
        'out/research/n008-hdr-oracle/phase-b-states/n004-scenes/leak-medium.gltf')
    cmd += ['--scene',str(scene),'--scenario',spec['scenario'] if dynamic else 'static',
        '--backend',role,'--direct-profile','ulp4','--out',str(capture)]
    if dynamic:cmd += ['--target-state','--recovery-frames','3','--topology-churn']
    return cmd


def interval(query, first, last, native_float=False):
    bits, period = query['timestamp_valid_bits'], query['timestamp_period_ns']
    C.require(1 <= bits <= 64 and R.positive(period)
        and math.ldexp(period,bits)/1e9 > 180, 'invalid timestamp wrap domain')
    # Source-native uint64 subtraction and valid-bit wrap are distinct evidence.
    delta = (query['ticks'][last]-query['ticks'][first]) & ((1 << (64 if native_float else bits))-1)
    if native_float:
        def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]
        return f32(f32(delta)*f32(period))/1000.
    return delta*period/1000.


def raw_trace(path, role, dynamic):
    records = [json.loads(line) for line in R.checked(path).splitlines()]
    contexts, phases, queries, fences = {}, [], [], []
    active = (-1,'setup')
    for index, row in enumerate(records):
        C.require(row['sequence'] == index, 'raw observer sequence gap')
        kind = row['kind']
        if kind == 'context':
            key = row['context']
            C.require(type(key) is int and key > 0 and key not in contexts
                and type(row['queue_family']) is int and row['queue_family'] >= 0
                and type(row['timestamp_valid_bits']) is int
                and 1 <= row['timestamp_valid_bits'] <= 64
                and R.positive(row['timestamp_period_ns']), 'invalid raw context')
            contexts[key] = row
        elif kind == 'phase':
            active = (row['frame'],row['phase']);phases.append(active)
        else:
            C.require(row['context'] in contexts and (row['frame'],row['phase']) == active
                and row['result'] == 0, 'unknown context/phase or failed Vulkan call')
            if kind == 'fence':
                C.require(type(row['count']) is int and row['count'] > 0
                    and row['wait_all'] in (0,1) and 0 <= row['bounded_timeout_ns'] <= 500000000
                    and row['bounded_timeout_ns'] == min(row['requested_timeout_ns'],500000000),
                    'fence guard or shape differs')
                fences.append(row)
            elif kind == 'query':
                ctx = contexts[row['context']]
                C.require((row['timestamp_period_ns'],row['timestamp_valid_bits']) ==
                    (ctx['timestamp_period_ns'],ctx['timestamp_valid_bits'])
                    and (row['first'],row['stride'],row['flags']) == (0,8,3)
                    and row['count'] in (2,4,18) and row['count'] == len(row['ticks'])
                    and row['data_size'] >= row['count']*8
                    and all(type(t) is int and 0 <= t < 2**64 for t in row['ticks']),
                    'raw timestamp payload layout differs')
                queries.append(row)
            else:raise ValueError('unknown raw observer event')
    count = 5 if dynamic else 1
    labels = [('source' if dynamic or role != 'dense-rc' else 'static') if i == 0
              else ('first-target' if i == 1 else 'recovery') for i in range(count)]
    expected = [entry for i,label in enumerate(labels) for entry in ((i,label),(i,'readback'))]
    if role != 'dense-rc':expected.append((-2,'final-readback'))
    expected.append((-3,'teardown'))
    C.require(phases == expected and contexts and queries and fences, 'incomplete raw trajectory')
    # All contexts are separate VkDevices on this frozen single-GPU fixture.
    domains = {(c['queue_family'],c['timestamp_valid_bits'],c['timestamp_period_ns']) for c in contexts.values()}
    C.require(len(domains) == 1, 'cross-context timestamp domain is not established')
    frames = []
    frame_queries = []
    for i,label in enumerate(labels):
        selected = [q for q in queries if (q['frame'],q['phase']) == (i,label)]
        size = 4 if role == 'dense-rc' else 18
        images = [q for q in selected if q['count'] == size]
        C.require(len(images) == 1 and all(q['count'] in (2,size) for q in selected),
            'missing/extra full image query')
        image = images[0]
        before = [q for q in selected if q['sequence'] < image['sequence']]
        after = [q for q in selected if q['sequence'] > image['sequence']]
        C.require(all(q['count'] == 2 for q in before+after), 'unclassified image-phase query')
        start, end = (0,1) if role == 'dense-rc' else (12,15)
        order = [0,2,3,1] if role == 'dense-rc' else [12,13,*range(12),14,16,17,15]
        C.require(all(0 <= interval(image,a,b) <= 500000 for a,b in zip(order,order[1:])),
            'image timestamp source order differs')
        image_us = interval(image,start,end)
        C.require(R.positive(image_us) and image_us <= (250000 if role == 'dense-rc' else 500000),
            'source-specific image/fence operational guard exceeded')
        maintenance = sum(interval(q,0,1) for q in before)
        image_begin = image['ticks'][start]
        bits, period = image['timestamp_valid_bits'], image['timestamp_period_ns']
        mask = (1<<bits)-1
        previous = None
        for q in before:
            C.require(0 <= interval(q,0,1) <= 500000, 'maintenance operational guard exceeded')
            if previous is not None:
                C.require(((q['ticks'][0]-previous)&mask)*period/1000 < 180e6,
                    'maintenance sequence differs')
            previous = q['ticks'][1]
        if previous is not None:
            C.require(((image_begin-previous)&mask)*period/1000 < 180e6,
                'maintenance/image order differs')
        first = before[0]['ticks'][0] if before else image_begin
        envelope = ((image['ticks'][end]-first)&mask)*period/1000
        C.require(0 < image_us+maintenance <= envelope < 180e6, 'complete GPU envelope differs')
        if role == 'dense-rc':
            native_image = interval(image,0,1,True)
            optional = interval(image,2,3,True)
            primary, composite = None, None
        else:
            primary, composite = interval(image,12,13),interval(image,14,15)
            native_image = primary+interval(image,0,11)+composite
            optional = interval(image,16,17)
        frames.append(dict(index=i,state=label,image_envelope_gpu_us=image_us,
            raw_maintenance_gpu_us=maintenance,full_renderer_envelope_gpu_us=envelope,
            native_image_gpu_us=native_image,native_renderer_gpu_us=native_image+maintenance,
            primary_visibility_us=primary,composite_us=composite,empty_optional_interval_gpu_us=optional,
            maintenance_query_sequences=[q['sequence'] for q in before],
            post_image_auxiliary_sequences=[q['sequence'] for q in after],
            post_image_auxiliary_gpu_us=sum(interval(q,0,1) for q in after)))
        frame_queries += selected
    for q in queries:
        if q not in frame_queries:
            C.require(q['count'] == 2 and (q['phase'] in ('setup','readback','final-readback','teardown'))
                and 0 <= interval(q,0,1) <= 500000, 'unclassified auxiliary GPU query')
    return dict(frames=frames,context_count=len(contexts),query_count=len(queries),
        fence_count=len(fences),all_query_sequences=[q['sequence'] for q in queries],
        separate_auxiliary_queries=[q for q in queries if q not in frame_queries],
        timing_precision='TIMING_INCONCLUSIVE',accepted_timing=False)


def memory(path, context_count):
    peak = R.ledger_replay(path)
    ledger = C.read(path)
    C.require(ledger['device_contexts'] == context_count, 'raw/owned context counts differ')
    events, live, position, phases = ledger['events'],0,0,[]
    names = [p['name'] for p in ledger['phases']]
    C.require(len(names) == len(set(names)), 'ambiguous repeated ledger phase names')
    for phase in ledger['phases']:
        high = live
        while position < len(events) and events[position]['phase'] == phase['name']:
            event = events[position]
            live += event['bytes'] if event['action'] == 'allocate' else -event['bytes']
            high = max(high,live);position += 1
        C.require(high == phase['peak_bytes'] and live == phase['live_bytes_at_end'],
            'owned phase peak/end-live differs')
        phases.append(dict(phase))
    C.require(position == len(events) and live == 0, 'unclassified owned memory events')
    return dict(owned_true_peak_bytes=peak,owned_teardown_zero=True,phases=phases,
        persistent_live_bytes_at_phase_end={p['name']:p['live_bytes_at_end'] for p in phases},
        scope='All owned Vulkan allocations; CPU and driver-private excluded')


def state(directory, expected, index, rc):
    C.require(R.checked(directory/'geometry-state.bin') == R.checked(expected/'geometry-state.bin'),
        'full captured geometry differs')
    actual, locked = R.checked(directory/'frame-state.bin'),R.checked(expected/'frame-state.bin')
    if rc:
        C.require(len(actual) == len(locked) == 148 and actual[:144] == locked[:144]
            and struct.unpack_from('<I',actual,144)[0] == index+1
            and struct.unpack_from('<I',locked,144)[0] == (1 if index == 0 else 2),
            'RC state differs beyond registered frame-counter progression')
    else:C.require(actual == locked, 'complete dense frame state differs')


def verify_capture(path, boundary, references=None, score_work=None, reference_verifier=H.verify_reference):
    record = C.read(path)
    cell, role, dynamic = identity(boundary)
    C.require(record['complete'] and record['native_returncode'] == 0
        and record['boundary_id'] == boundary, 'nonterminal/failed/wrong native')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in record[group].items():R.checked(name,digest)
    build, lock = C.read(BUILD),C.read(LOCK)
    C.require(build['complete'] and build['build_valid']
        and record['input_sha256'].get(str(BUILD)) == P.sha(BUILD), 'actual506 build not bound')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in build[group].items():R.checked(name,digest)
    commit = record['source_commit']
    C.require(type(commit) is str and len(commit) == 40 and all(c in '0123456789abcdef' for c in commit),
        'full native source commit required')
    for ancestor,descendant in ((build['source_commit'],commit),(commit,'HEAD')):
        subprocess.run(['git','merge-base','--is-ancestor',ancestor,descendant],cwd=R.ROOT,
            check=True,capture_output=True)
    for name in ('prepare_raw_query_pilots.py','build_raw_query_pilots.py'):
        source = Path(__file__).with_name(name)
        C.require(subprocess.check_output(['git','show',commit+':'+str(source.relative_to(R.ROOT))],cwd=R.ROOT)
            == R.checked(source), 'native build source missing/different at recorded commit')
    directory = Path(record['command'][record['command'].index('--out')+1])
    C.require(directory.is_absolute() and record['command'] == command(boundary,directory,build,lock),
        'full physical/budget command differs')
    work = directory.parent
    required = {str(p) for p in directory.rglob('*') if p.is_file()}
    required |= {str(work/name) for name in ('raw-queries.jsonl','native.resources.json','native.stdout','native.stderr')}
    # Original507 includes no quality maps; future score files are outside capture.
    C.require(set(record['payload_sha256']) == required, 'full native payload inventory differs')
    receipt = C.read(work/'native.resources.json')
    C.require(receipt['pid'] == receipt['pgid'] == record['native_pid']
        and type(receipt['start_ticks']) is int and receipt['start_ticks'] > 0
        and bool(receipt['boot_id']) and receipt['boot_id'] == record['environment']['boot_id']
        and receipt['command'] == record['command'] and receipt['affinity'] == [31]
        and receipt['nice'] == 15 and receipt['cpu'] == [120,120]
        and receipt['address_space'] == [-1,-1] and receipt['elapsed_limit_seconds'] == 180
        and 0 < record['elapsed_seconds'] < 180 and 0 <= record['child_cpu_seconds'] <= 120,
        'actual native PID/start/boot/limits differ')
    proc = Path(f'/proc/{receipt["pid"]}/stat')
    if proc.exists() and Path('/proc/sys/kernel/random/boot_id').read_text().strip() == receipt['boot_id']:
        fields = proc.read_text().rsplit(')',1)[1].split()
        C.require(int(fields[19]) != receipt['start_ticks'] or fields[0] == 'Z',
            'same recorded native is still live')
    raw = raw_trace(work/'raw-queries.jsonl',role,dynamic)
    mem = memory(directory/'allocation-ledger.json',raw['context_count'])
    spec = lock['cells'][cell]
    target = R.ROOT/spec['state_directory']
    source = R.ROOT/spec['source_directory'] if dynamic else target
    for name,key in (('geometry-state.bin','geometry'),('frame-state.bin','frame')):
        R.checked(target/name,spec['state_sha256'][key])
    count, rc = (5 if dynamic else 1),role != 'dense-rc'
    metadata = C.read(directory/'capture.json') if rc else C.read(directory/'frames.json')
    C.require((metadata['width'],metadata['height'],metadata['spp']) == (320,180,512 if rc else 1),
        'full image shape/native budget differs')
    if rc:
        C.require(metadata['backend'] == role and metadata['target_state'] == dynamic
            and metadata['work_overflow'] == 0, 'RC role/overflow differs')
        timings = [json.loads(line) for line in R.checked(directory/'renderer-timings.jsonl').splitlines()]
    else:
        C.require((metadata['family'],metadata['vertices'],metadata['seed']) == ('dense-rc',2,305419896),
            'dense family/transport/seed differs')
        timings = metadata['frames']
    C.require(len(timings) == count, 'missing native history timing')
    if references is not None:
        C.require(score_work is not None and not Path(score_work).exists(), 'fresh full score output required')
        Path(score_work).mkdir(parents=True)
    scores, walls = [],0.0
    for index,(timing,frame) in enumerate(zip(timings,raw['frames'])):
        frame_dir = directory/'frames'/str(index)
        state(frame_dir,source if index == 0 else target,index,rc)
        C.require(timing['state'] == frame['state'] and R.positive(timing['wall_us']),
            'native frame label/wall differs')
        walls += timing['wall_us']
        if rc:
            C.require(timing['classification'] == 'DIAGNOSTIC_UNCALIBRATED' and timing['overflow'] == 0,
                'RC frame overflow/classification differs')
            for native,recomputed in (('complete_renderer_gpu_us','native_renderer_gpu_us'),
                    ('maintenance_gpu_us','raw_maintenance_gpu_us'),
                    ('primary_visibility_us','primary_visibility_us'),('composite_us','composite_us')):
                C.require(R.close(timing[native],frame[recomputed]), 'RC raw/native field differs: '+native)
        else:
            C.require((timing['index'],timing['seed'],timing['dose'],timing['changed_slots']) ==
                (index,305419896,0,0), 'dense frame identity differs')
            for native,recomputed in (('image_gpu_us','native_image_gpu_us'),
                    ('gpu_us','native_renderer_gpu_us'),('maintenance_gpu_us','raw_maintenance_gpu_us'),
                    ('known_work_gpu_us','empty_optional_interval_gpu_us')):
                C.require(R.close(timing[native],frame[recomputed]), 'dense source-exact field differs: '+native)
        image_dir = frame_dir/'gpu' if rc else frame_dir
        for component in ('direct','indirect','total'):
            image = P.Q.L.read_pfm(image_dir/(component+'.pfm'))
            C.require(image.shape == (180,320,3) and np.isfinite(image).all() and (image >= 0).all(),
                'nonfinite/negative/incomplete full image')
            if index == count-1:
                top = directory/'gpu' if rc else directory
                C.require(R.checked(top/(component+'.pfm')) == R.checked(image_dir/(component+'.pfm')),
                    'top image differs from final frame')
        if references is not None:
            ref_cell = ('C1' if cell == 'C6' else 'C7') if dynamic and index == 0 else cell
            for vertices in (2,8):
                reference = Path(references)/f'{ref_cell}_T_B{vertices}'
                proof = reference_verifier(reference,ref_cell,vertices,lock['cells'][ref_cell],R.INPUTS)
                qualification = C.read(reference/'qualification.json')
                output = Path(score_work)/f'frame{index}-B{vertices}.json'
                score = S.score(frame_dir,qualification,reference,output)
                C.require(score['scoring_exclusions'] == 0 and all(m['pixels'] == 57600
                    and m['scoring_exclusions'] == 0 for m in score['components'].values()),
                    'incomplete full pixel scoring')
                with output.open('x') as stream:stream.write(json.dumps(score,indent=2,allow_nan=False)+'\n')
                scores.append(dict(frame_index=index,vertices=vertices,reference_proof=proof,quality=score))
    C.require(walls < record['elapsed_seconds']*1e6, 'frame wall exceeds whole native')
    state(directory,target,count-1,rc)
    if not rc:
        old = next(row for row in C.read(R.RESULTS/'015-dense-rc-pilot.json')['rows'] if row['cell'] == cell)
        prior = Path(old['command'][old['command'].index('--out')+1])
        for name,digest in old['payload_sha256'].items():R.checked(prior/name,digest)
        for component in ('direct','indirect','total'):
            C.require(R.checked(prior/(component+'.pfm')) == R.checked(directory/(component+'.pfm')),
                'full original015 dense image bytes differ')
    R.unchanged()
    return dict(boundary_id=boundary,execution_evidence_valid=True,quality_evidence_valid=references is not None,
        source_commit=commit,raw=raw,memory=mem,scores=scores,accepted_timing=False,
        reference_admission=False,timing_precision='TIMING_INCONCLUSIVE',
        full_handoff_cost_accounting_valid=False,
        remaining_host_cost_accounting='Independent setup/readback/submit/wait receipts not provided by506')
