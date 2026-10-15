"""Plan 049: strict actual-proof intake; never acquire or infer timing capability."""
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = ROOT/'research/lanes/n010-comparison-readiness/results'
sys.path.insert(0, str(HERE.parent/'n010_comparison_readiness'))
from reference_provenance import read, sha
from qualify_hybrid_references import check_files
from readiness_preflight import replay
import calibrate_renderer as C

FIXTURE = ROOT/'out/research/n010-comparison-readiness/minimal-calibration-build-v3'
CORE_SHA = '64deb4d3995eb40498ca2b454dacf6d97d5909115ef32a36e3c80c3a7683cb8d'
BUILD_SHA = '71b94470b465f0d16afaec9bec60b42e63c39e6be8ed781f6d5b1802ca99b88a'
BASELINE_SHA = '2ab654662ffdef9b873179d95a9142eea7e18ad0635cec37601c51f0f828d36d'


def require(condition, message):
    if not condition:
        raise ValueError('bulk PFM timing proof: '+message)


def expected_command(boundary, lock, directory, doses):
    b = boundary
    binary = FIXTURE/('phos-n010-capture' if b['role'] in ('hwrt', 'software') else 'phos-n010-pixel-pt')
    command = ['bash', 'scripts/run_with_vulkan.sh', str(binary)]
    if b['role'] in ('hwrt', 'software'):
        scene = ROOT/('assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf' if b['base']=='C1'
            else 'out/research/n008-hdr-oracle/phase-b-states/n004-scenes/leak-medium.gltf')
        command += ['--scene', str(scene), '--scenario', 'deforming-control' if b['dynamic'] else 'static',
                    '--backend', b['role'], '--direct-profile', 'ulp4',
                    '--calibration-doses', str(doses), '--out', str(directory)]
        if b['dynamic']:
            command += ['--target-state', '--topology-churn']
    else:
        command += ['--state', str(ROOT/lock['cells'][b['base']]['state_directory']),
                    '--spp', '1' if b['role']=='dense-rc' else '1024',
                    '--vertices', '8' if b['role']=='pt-B8' else '2',
                    '--family', 'dense-rc' if b['role']=='dense-rc' else 'pixel-pt',
                    '--seed', '305419896', '--calibration-doses', str(doses), '--out', str(directory)]
        if b['dynamic']:
            command += ['--target-state', str(ROOT/lock['cells'][b['cell']]['state_directory'])]
    return command, binary


def verify_calibration(lock_path, inputs):
    """Return actual fixture identities only after all original full gates replay."""
    core = Path(C.__file__).resolve()
    require(sha(core)==CORE_SHA, 'original schedule/analysis source changed')
    lock_path = Path(lock_path).resolve()
    require(lock_path==RESULTS/'026-dynamic-execution-state-lock.json', 'different lock')
    lock = read(lock_path, inputs)
    paths = {n:RESULTS/name for n, name in (
        (167, '167-bulk-pfm-calibration-fixture-build.json'),
        (168, '168-bulk-pfm-calibration-quiet-sizing.json'),
        (169, '169-bulk-pfm-calibration-full-renderer.json'))}
    # Refuse incomplete/failed evidence before expensive payload verification.
    build, sizing, accepted = (read(paths[n], inputs) for n in (167, 168, 169))
    require(all(d['complete'] and d['all_pass'] for d in (build, sizing, accepted)),
            'complete full PASS 167/168/169 required')
    require(sha(paths[167])==BUILD_SHA, 'different registered build proof')
    require(build['schema']=='n010-minimal-calibration-fixture-build/3'
        and all(build[k] for k in ('source_inverse_proof', 'timed_renderer_method_unchanged',
                                  'active_inputs_byte_unchanged'))
        and len(build['steps'])==5 and all(s['returncode']==0 for s in build['steps']), 'build scope')
    check_files(build['input_sha256'], inputs)
    check_files({str(FIXTURE/name):h for name,h in build['generated_sha256'].items()}, inputs)
    baseline_path = RESULTS/'046-calibration-quiet-sizing.json'
    require(sha(baseline_path)==BASELINE_SHA, 'original image baseline changed')
    baseline = read(baseline_path, inputs)
    cohort = C.boundaries(lock)
    require(len(cohort)==16 and baseline['complete'] and baseline['all_pass']
            and baseline['lock_sha256']==sha(lock_path), 'original full image baseline')
    require(accepted['plan_sha256']==sha(paths[168]), 'accepted sizing identity')
    for mode, proof in (('sizing', sizing), ('accepted', accepted)):
        require(proof['schema']=='n010-bulk-pfm-renderer-calibration/1'
                and proof['mode']==mode and proof['lock_sha256']==sha(lock_path), 'GPU proof identity')
        require([r['boundary'] for r in proof['rows']]==cohort, 'full ordered sixteen-boundary scope')
        mandatory = {str(core):CORE_SHA, str(paths[167]):BUILD_SHA,
                     str(baseline_path):BASELINE_SHA}
        for p in (HERE/'calibrate_bulk_pfm_capture.py', HERE/'calibrate_minimal_capture.py',
                  RESULTS.parent/'experiments/048-prospective-bulk-pfm-calibration-output.md'):
            mandatory[str(p)] = sha(p)
        require(all(proof['fixture_input_sha256'].get(p)==h for p,h in mandatory.items()),
                'mandatory fixture provenance omitted or changed')
        check_files(proof['fixture_input_sha256'], inputs)
    witnesses = {}
    shaders = C.shader_hashes()

    def evidence(block, boundary, directory, dose_values):
        native = block['command']
        require(native.count('--out')==1, 'native output argument')
        actual_out = Path(native[native.index('--out')+1])
        require((ROOT/actual_out).resolve()==directory, 'registered native output directory')
        actual_doses = actual_out.with_suffix('.doses.txt')
        dose_file = ROOT/actual_doses
        command, binary = expected_command(boundary, lock, actual_out, actual_doses)
        require(block['boundary']==boundary and block['command']==command
                and block['returncode']==0 and block['binary_sha256']==sha(binary)
                and block['shader_sha256']==shaders, 'native command/binary/shader identity')
        require(dose_file.read_text()==''.join(str(v)+'\n' for v in dose_values)
                and block['doses_file_sha256']==sha(dose_file), 'native dose schedule')
        inputs[str(dose_file)] = sha(dose_file)
        actual_files = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()}
        require(actual_files==set(block['payload_sha256']), 'full native payload manifest')
        check_files({str(directory/name):h for name,h in block['payload_sha256'].items()}, inputs)
        if (directory/'frames.json').exists():
            samples = json.loads((directory/'frames.json').read_text())['frames']
        else:
            samples = [json.loads(line) for line in (directory/'calibration-timings.jsonl').read_text().splitlines()]
        require(samples==block['samples'] and len(samples)==len(dose_values)
                and [s['dose'] for s in samples]==dose_values, 'native sample file/scope')
        ledger = json.loads((directory/'allocation-ledger.json').read_text())
        require(ledger==block['allocation_ledger'] and replay(ledger)
                and block['allocation_ledger_replay_pass'], 'owned-memory replay')
        expected_images = next(r['evidence']['payloads'][0]['images'] for r in baseline['rows']
                               if r['boundary']==boundary)
        require(len(block['payloads'])==len(samples) and block['known_work_probe_validation']
                and block['images_byte_equal'] and block['images_byte_equal_to_original_046'], 'image/witness scope')
        for index, dose in enumerate(dose_values):
            frame = directory/'frames'/str(index)
            if (frame/'gpu').is_dir():
                frame = frame/'gpu'
            payload = block['payloads'][index]
            images = {n:sha(frame/(n+'.pfm')) for n in ('direct', 'indirect', 'total')}
            scratch = frame/'neutral-work.bin'
            require(images==payload['images']==expected_images and scratch.stat().st_size==65536
                    and sha(scratch)==payload['scratch'], 'actual image/scratch bytes')
            if dose not in witnesses:
                verifier = ROOT/'build/n009/n010-neutral-work-verify'
                subprocess.run([str(verifier), str(dose), str(scratch)], check=True,
                               capture_output=True, text=True)
                witnesses[dose] = sha(scratch)
            require(witnesses[dose]==sha(scratch), 'known-work witness consistency')

    for srow, arow, boundary in zip(sizing['rows'], accepted['rows'], cohort):
        directory = ROOT/'out/research/n010-comparison-readiness/bulk-pfm-calibration-sizing-v1'/boundary['id']/'sizing'
        evidence(srow['evidence'], boundary, directory, [0,65536,262144]*3)
        samples = srow['evidence']['samples']
        med = {d:statistics.median(s['gpu_us'] for s in samples if s['dose']==d) for d in (0,65536,262144)}
        inner = {d:statistics.median(s['known_work_gpu_us'] for s in samples if s['dose']==d) for d in (0,65536,262144)}
        slopes = [(inner[d]-inner[0])/d for d in (65536,262144)]
        require(min(slopes)>0, 'positive known-work sizing slopes')
        dose = math.ceil(.2*med[0]/statistics.median(slopes))
        require(srow['amendment']=='5' and srow['sizing_pass'] and dose<=100000000
                and srow['frozen_dose']==dose
                and srow['medians_us']=={str(k):v for k,v in med.items()}
                and srow['known_work_medians_us']=={str(k):v for k,v in inner.items()}, 'original sizing replay')
        require(len(arow['blocks'])==8, 'eight fresh-process blocks')
        for index, block in enumerate(arow['blocks']):
            records = C.schedule(dose, index)
            directory = ROOT/'out/research/n010-comparison-readiness/bulk-pfm-calibration-accepted-v1'/boundary['id']/f'block-{index}'
            evidence(block, boundary, directory, [r['dose'] for r in records])
            expected = [dict(s, **{k:v for k,v in r.items() if k not in s})
                        for s,r in zip(block['samples'], records)]
            require(len(expected)==64 and block['tagged_samples']==expected, 'original AB/BA schedule')
        recalculated = C.analysis(arow['blocks'])
        require(arow['analysis']==recalculated and recalculated['all_pass'], 'original numerical gates')
    for p in (Path(__file__).resolve(), core, RESULTS.parent/'experiments/049-prospective-bulk-pfm-timing-proof-intake.md'):
        inputs[str(p)] = sha(p)
    check_files(inputs, {})
    return {'scope':'Actual complete isolated-fixture calibration; no historical timing transfer',
            'boundaries':16, 'blocks_per_boundary':8, 'samples_per_block':64,
            'calibration_sha256':sha(paths[169]), 'sizing_sha256':sha(paths[168]),
            'build_sha256':BUILD_SHA,
            'binary_sha256':{n:sha(FIXTURE/n) for n in ('phos-n010-capture','phos-n010-pixel-pt')},
            'shader_sha256':shaders, 'historical_pilot_timing_accepted':False}
