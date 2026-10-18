"""Plan129: raw continuation PT capture/physical-quality intake; no acquisition."""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
import reference_provenance as P
import score_hdr as S

ROOT = P.ROOT
sys.path.insert(0, str(ROOT/'scripts/research/n010_reference_sampling'))
import replay_continuation_pixel_pt as R

BUDGETS = (1, 4, 16, 64, 256, 1024)
DYNAMIC = {f'C{i}' for i in (2,3,4,5,6,8,9,10,11,12)}


def require(value, message):
    if not value:
        raise ValueError('continuation quality proof: '+message)


def read(path):
    return json.loads(R.checked(path))


def nonnegative(value):
    return type(value) in (int,float) and math.isfinite(value) and value >= 0


def require_state(directory, expected):
    for name in ('geometry-state.bin','frame-state.bin'):
        require(R.checked(directory/name) == R.checked(expected/name),
                'complete captured physical state changed: '+str(directory))
    return P.Q.L.read_state(directory)


def command_scope(command, spec, directory, vertices, spp, dynamic):
    require(command[:3] == ['bash',str(ROOT/'scripts/run_with_vulkan.sh'),
            str(R.BUILD/'phos-n010-continuation-pixel-pt')], 'wrong native executable')
    flags = command[3:]
    require(len(flags)%2 == 0, 'invalid command pairs')
    options = dict(zip(flags[::2],flags[1::2]))
    require(len(options)*2 == len(flags), 'duplicate command flag')
    expected = {'--state':str((ROOT/spec['source_directory' if dynamic else 'state_directory']).resolve()),
        '--out':str(directory),'--family':'pixel-pt','--vertices':str(vertices),'--spp':str(spp),
        '--seed':'305419896','--frames':'5' if dynamic else '1',
        '--tile-pixels':'4096','--sample-chunk':'16','--pause-us':'2000'}
    if dynamic:
        expected['--target-state'] = str((ROOT/spec['state_directory']).resolve())
    require(options == expected, 'native physical/budget/frame command differs')


def verify_native(record, directory):
    receipt = read(directory.parent/'native.resources.json')
    require(record['native_returncode'] == 0 and record['pid'] == receipt['pid']
            and type(receipt['pid']) is int and receipt['pid'] > 0
            and receipt['pgid'] == receipt['pid'] and type(receipt['start_ticks']) is int
            and receipt['start_ticks'] > 0 and bool(receipt['boot_id'])
            and receipt['boot_id'] == record['environment']['boot_id']
            and receipt['command'] == record['command'], 'native identity/returncode differs')
    require(receipt['affinity'] == [31] and receipt['nice'] == 15
            and receipt['cpu'] == [120,120] and receipt['address_space'] == [-1,-1]
            and receipt['elapsed_limit_seconds'] == 180
            and R.positive(record['elapsed_seconds']) and record['elapsed_seconds'] < 180
            and nonnegative(record['child_cpu_seconds']) and record['child_cpu_seconds'] <= 120,
            'native registered operational resources differ')


def dispatches(rows, frame, spp, pixels, period):
    expected_count = ((spp+15)//16)*((pixels+4095)//4096)
    require(len(rows) == expected_count, 'missing/extra dispatches')
    bits = rows[0]['timestamp_valid_bits']
    require(type(bits) is int and 1 <= bits <= 64 and R.positive(period)
            and math.ldexp(period,bits)/1e9 > 180, 'unsupported timestamp range')
    mask, active, maximum, previous, index = (1<<bits)-1, 0.0, 0.0, None, 0
    for begin in range(0,spp,16):
        end = min(begin+16,spp)
        for pixel in range(0,pixels,4096):
            row = rows[index]
            require((row['image_index'],row['seed'],row['sample_begin'],row['sample_end'],
                    row['pixel_begin'],row['pixel_count']) == (frame,305419896+frame,begin,end,
                    pixel,min(4096,pixels-pixel)) and row['timestamp_valid_bits'] == bits
                    and row['timestamp_period_ns'] == period, 'sample/pixel/seed coverage differs')
            first,last = row['begin_tick'],row['end_tick']
            require(all(type(x) is int and 0 <= x < 2**64 for x in (first,last)), 'invalid raw ticks')
            duration = ((last-first)&mask)*period/1000
            require(R.positive(duration) and duration <= 250000 and R.close(duration,row['gpu_us']),
                    'raw duration differs or operational dispatch guard exceeded')
            require(previous is None or ((first-previous)&mask)*period/1e9 < 180,
                    'dispatch order/wrap differs')
            previous,active,maximum,index = last,active+duration,max(maximum,duration),index+1
    envelope = ((rows[-1]['end_tick']-rows[0]['begin_tick'])&mask)*period/1000
    require(R.positive(envelope) and active <= envelope < 180e6, 'invalid full image envelope')
    return dict(dispatch_count=len(rows),pixel_samples=pixels*spp,
                active_gpu_us=active,image_envelope_gpu_us=envelope,max_dispatch_gpu_us=maximum)


def final_state(directory, width, height, spp):
    raw = R.checked(directory/'sample-state.bin')
    require(len(raw) == width*height*16, 'missing final per-pixel state')
    words = np.frombuffer(raw,dtype='<u4').reshape(height,width,4)
    sums = words[:,:,1].copy().view('<f4')
    require(np.all(words[:,:,2] == spp) and not np.any(words[:,:,3])
            and np.isfinite(sums).all() and np.all(sums >= 0), 'final continuation progress/error/sum differs')
    expected = np.repeat((sums/np.float32(spp))[:,:,None],3,axis=2)
    image = P.Q.L.read_pfm(directory/'indirect.pfm')
    require(np.array_equal(image,expected), 'full final state does not generate indirect image')
    for component in ('direct','indirect','total'):
        R.checked(directory/(component+'.pfm'))
        image = P.Q.L.read_pfm(directory/(component+'.pfm'))
        require(image.shape == (height,width,3) and np.isfinite(image).all()
                and np.all(image >= 0), 'image dimensions/finiteness/radiance differ')
    return hashlib.sha256(raw).hexdigest()


def verify_capture(part_path, lock_path, cell, vertices, spp, dynamic=False,
                   references=None, score_work=None, reference_verifier=P.verify_reference):
    """Replay one real native; optional physical scoring, never timing admission.

    No all-split fallback exists. A future alternate reference verifier must
    itself replay its complete physical/state/prefix chain before returning.
    """
    require(vertices in (2,8) and spp in BUDGETS, 'outside frozen static budget family')
    require(not dynamic or cell in DYNAMIC, 'outside frozen transition family')
    record = read(Path(part_path).resolve())
    require(record['complete'] and record['cell'] == cell, 'partial or wrong cell capture')
    for group in ('input_sha256','payload_sha256'):
        for name,digest in record[group].items():
            R.checked(name,digest)
    # This re-reads401 and every pinned source/library/shader/binary input.
    R.inputs('C7')
    build = read(R.RESULTS/'401-continuation-pixel-pt-build.json')
    commit = record['source_commit']
    require(type(commit) is str and len(commit) == 40
            and all(c in '0123456789abcdef' for c in commit), 'full capture source commit required')
    subprocess.run(['git','merge-base','--is-ancestor',commit,'HEAD'],cwd=ROOT,
                   check=True,capture_output=True)
    build_path = R.RESULTS/'401-continuation-pixel-pt-build.json'
    require(record['input_sha256'].get(str(build_path)) == P.sha(build_path),
            'actual build result not pinned in capture inputs')
    subprocess.run(['git','merge-base','--is-ancestor',build['source_commit'],commit],cwd=ROOT,
                   check=True,capture_output=True)
    # A generated build result can be published after acquisition. Its actual
    # bytes must match the capture's immutable input digest, while executable
    # source/registration bytes must already exist in the recorded Git commits.
    tracked_sources = (ROOT/'scripts/research/n010_reference_sampling/build_continuation_pixel_pt.py',
                 ROOT/'scripts/research/n010_reference_sampling/prepare_continuation_pixel_pt.py',
                 ROOT/'scripts/research/n010_reference_sampling/prepare_continuation_readback.py',
                 R.RESULTS.parent/'experiments/126-exact-sample-continuation-pixel-pt.md',
                 R.RESULTS.parent/'experiments/127-continuation-readback-accounting.md')
    for path in tracked_sources:
        for source_commit in (build['source_commit'],commit):
            require(subprocess.check_output(['git','show',source_commit+':'+str(path.relative_to(ROOT))],cwd=ROOT)
                    == R.checked(path), 'executable source/recipe absent or different at build/capture commit')
    lock = read(Path(lock_path).resolve())
    require(set(lock['cells']) == {f'C{i}' for i in range(1,13)}, 'full026 corpus required')
    spec = lock['cells'][cell]
    command = record['command']
    directory = Path(command[command.index('--out')+1]).resolve()
    command_scope(command,spec,directory,vertices,spp,dynamic)
    require(R.checked(directory.parent/'record.json') == R.checked(part_path),
            'published/native-local record bytes differ')
    expected_payloads = {str(p.resolve()) for p in directory.rglob('*') if p.is_file()}
    expected_payloads.update(str(directory.parent/name) for name in
                             ('native.resources.json','native.stdout','native.stderr'))
    require(set(record['payload_sha256']) == expected_payloads,
            'missing/extra original capture payload identities')
    verify_native(record,directory)
    metadata = read(directory/'frames.json')
    source = ROOT/spec['source_directory' if dynamic else 'state_directory']
    target = ROOT/spec['state_directory']
    target_state = P.Q.L.read_state(target)
    require(target_state['sha256'] == spec['state_sha256'], 'canonical target state differs from026')
    width,height = target_state['width'],target_state['height']
    require_state(directory,target)
    source_state = P.Q.L.read_state(source)
    require((source_state['width'],source_state['height']) == (width,height)
            and len(source_state['verts']) == len(target_state['verts'])
            and np.all(source_state['meta'][:,3] == 1)
            and np.all(target_state['meta'][:,3] == 1), 'source/target dimensions or BF-P parity differ')
    # Pinned to_gpu_triangle preserves these 52 input bytes, inserting only
    # zero float padding; with two_sided==1 its memcmp changed set is exact.
    layout = ROOT/'src/research/lane_n_end_to_end_renderer/imported/lane_b_traversal/b002_gpu_layout.hpp'
    require(str(layout) in R.INPUTS, 'GPU triangle conversion missing from pinned build inputs')
    old_geometry = np.frombuffer(R.checked(source/'geometry-state.bin'),dtype='u1',offset=8).reshape(-1,52)
    new_geometry = np.frombuffer(R.checked(target/'geometry-state.bin'),dtype='u1',offset=8).reshape(-1,52)
    changed_slots = int(np.any(old_geometry != new_geometry,axis=1).sum())
    count = 5 if dynamic else 1
    require((metadata['schema'],metadata['timing_classification'],metadata['family'],metadata['vertices'],
            metadata['spp'],metadata['seed'],metadata['width'],metadata['height']) ==
            ('n010-continuation-pixel-pt/1','DIAGNOSTIC_UNCALIBRATED','pixel-pt',vertices,spp,
            305419896,width,height) and len(metadata['frames']) == count, 'native frame scope differs')
    tiles = [json.loads(line) for line in R.checked(directory/'tile-timings.jsonl').splitlines()]
    readbacks = [json.loads(line) for line in R.checked(directory/'readback-timings.jsonl').splitlines()]
    require(len(readbacks) == count and all(type(r['image_index']) is int
            and 0 <= r['image_index'] < count for r in tiles), 'unknown frame or readback count')
    require(R.positive(metadata['setup_wall_us']), 'setup observation missing')
    if references is not None:
        require(score_work is not None and not Path(score_work).exists(), 'fresh score output required')
        Path(score_work).mkdir(parents=True)
        physical = P.physical_proof(R.INPUTS)
        R.checked(P.Q.BINARY,physical['binary_sha256'])
        R.checked(P.Q.NET,physical['sobol_table_sha256'])
    rows, walls = [], metadata['setup_wall_us']
    for index,frame in enumerate(metadata['frames']):
        label = 'static' if not dynamic else ('source' if index==0 else ('first-target' if index==1 else 'recovery'))
        require((frame['index'],frame['state'],frame['seed'],frame['dose'],frame['known_work_gpu_us'],
                frame['tile_pixels'],frame['sample_chunk'],frame['pause_us'],frame['sample_state_bytes'])
                == (index,label,305419896+index,0,0,4096,16,2000,width*height*16), 'frame identity differs')
        frame_dir = directory/'frames'/str(index)
        state = require_state(frame_dir,source if index==0 else target)
        replay = dispatches([r for r in tiles if r['image_index']==index],index,spp,width*height,
                            metadata['timestamp_period_ns'])
        fields = ('uniform_upload_gpu_us','geometry_upload_gpu_us','blas_update_us','tlas_update_us')
        require(all(nonnegative(frame[k]) for k in fields)
                and R.close(sum(frame[k] for k in fields),frame['maintenance_gpu_us']), 'maintenance costs differ')
        require(type(frame['changed_slots']) is int and 0 <= frame['changed_slots'] <= len(state['verts']),
                'invalid changed-slot count')
        if not dynamic or index != 1:
            require(frame['changed_slots'] == 0 and frame['maintenance_gpu_us'] == 0,
                    'unexpected static/recovery maintenance')
        else:
            require(frame['changed_slots'] == changed_slots, 'first-target geometry update set differs')
        for key,value in [('image_gpu_us',replay['image_envelope_gpu_us']),
                ('image_envelope_gpu_us',replay['image_envelope_gpu_us']),
                ('image_active_gpu_us',replay['active_gpu_us']),
                ('active_gpu_us',replay['active_gpu_us']+frame['maintenance_gpu_us']),
                ('gpu_us',replay['image_envelope_gpu_us']+frame['maintenance_gpu_us']),
                ('max_tile_gpu_us',replay['max_dispatch_gpu_us'])]:
            require(R.close(frame[key],value), 'complete frame cost differs: '+key)
        require(R.positive(frame['wall_us']) and readbacks[index]['index'] == index
                and R.positive(readbacks[index]['wall_us']), 'missing frame/readback wall')
        walls += frame['wall_us']+readbacks[index]['wall_us']
        replay.update(frame_index=index,label=label,seed=305419896+index,
            cpu_frame_wall_us=frame['wall_us'],readback_wall_us=readbacks[index]['wall_us'],
            renderer_gpu_us=frame['gpu_us'],maintenance_gpu_us=frame['maintenance_gpu_us'],
            changed_slots=frame['changed_slots'],final_state_sha256=final_state(frame_dir,width,height,spp))
        if references is not None:
            ref_cell = ('C1' if cell in {'C2','C3','C4','C5','C6'} else 'C7') if dynamic and index==0 else cell
            ref = Path(references)/f'{ref_cell}_T_B{vertices}'
            replay['reference_proof'] = reference_verifier(ref,ref_cell,vertices,lock['cells'][ref_cell],R.INPUTS)
            qualification = P.read(ref/'qualification.json',R.INPUTS)
            score_path = Path(score_work)/f'frame{index}.json'
            quality = S.score(frame_dir,qualification,ref,score_path)
            require(quality['scoring_exclusions'] == 0 and all(
                    m['pixels'] == width*height and m['scoring_exclusions'] == 0
                    for m in quality['components'].values()), 'incomplete pixel scoring')
            quality.update(frame_index=index,role=f'pixel-pt-B{vertices}',qualification_sha256=P.sha(ref/'qualification.json'))
            with score_path.open('x') as output:
                output.write(json.dumps(quality,indent=2,allow_nan=False)+'\n')
            replay['quality'] = quality
        rows.append(replay)
    require(walls <= record['elapsed_seconds']*1e6, 'setup/frame/readback costs exceed native wall')
    for name in ('sample-state.bin','direct.pfm','indirect.pfm','total.pfm'):
        require(R.checked(directory/name) == R.checked(directory/'frames'/str(count-1)/name),
                'top-level payload differs from final frame')
    peak = R.ledger_replay(directory/'allocation-ledger.json')
    require(any('sample-state.bin' in name for name in record['payload_sha256']),
            'capture final-state payload identity absent')
    R.unchanged()
    return dict(cell=cell,vertices=vertices,spp=spp,frames=rows,execution_evidence_valid=True,
        quality_evidence_valid=references is not None,source_commit=commit,
        build_source_commit=build['source_commit'],setup_wall_us=metadata['setup_wall_us'],
        native_elapsed_seconds=record['elapsed_seconds'],owned_peak_bytes=peak,owned_teardown_zero=True,
        persistent_sample_state_bytes=width*height*16,accepted_timing=False,reference_admission=False)
