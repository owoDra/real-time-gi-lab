"""Plan 054 strict intake of actual 184/185/186; no acquisition or inferred PASS."""
import hashlib
import json
from pathlib import Path

from deferred_image_calibration_program import HERE, ROOT, RESULTS, PLAN, program

ORIGINAL = HERE/'bulk_pfm_timing_provenance.py'
ORIGINAL_SHA = '49ac6660fe17e8895be2a0d600771a8e844358867fe57014f0066105b247b9a8'
BUILD_SHA = '6eca016a61ca7ba3b072f05ef7f22221a2d402a9ff778d10b56feb0261f96ebf'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value,message):
    if not value:raise ValueError('deferred image timing proof: '+message)


def verify_plan(proof,mode,inputs):
    from qualify_hybrid_references import check_files
    _,_,assembly = program(HERE/'calibrate_deferred_image_capture.py')
    require(proof['plan054_source_inverse_proof']==assembly,'whole acquisition inverse differs')
    env = proof['execution_environment']
    require(env['vendor']=='0x1002' and env['device']=='0x1586'
        and env['driver']=='/sys/bus/pci/drivers/amdgpu'
        and env['pci_device'].endswith('/0000:c5:00.0') and env['boot_id'] and env['kernel'],
        'registered AMD environment provenance differs')
    for p in (PLAN,HERE/'calibrate_deferred_image_capture.py',HERE/'deferred_image_calibration_program.py',
              HERE/'deferred_image_capture_programs.py',HERE/'hidden_ide_bulk_pfm_program.py'):
        require(proof['fixture_input_sha256'].get(str(p))==sha(p),'mandatory source/plan identity omitted')
        inputs[str(p)] = sha(p)
    check_files(inputs,{})


def verify_spool(block,directory,doses,inputs):
    from reference_provenance import read
    path = directory/'deferred-image-serialization.json'
    receipt = read(path,inputs)
    frame = directory/'frames'/'0'
    if (frame/'gpu').is_dir():frame = frame/'gpu'
    with (frame/'direct.pfm').open('rb') as f:
        require(f.readline().strip()==b'PF','image header')
        width,height = map(int,f.readline().split())
    require(receipt==block.get('deferred_image_serialization')
        and sha(path)==block.get('deferred_image_serialization_sha256')
        and receipt['schema']=='n010-deferred-image-serialization/1' and receipt['complete']
        and receipt['retained_frames']==len(doses)==receipt['written_frames']
        and receipt['rgba_capacity_limit_bytes']==256*1024**2
        and len(doses)*width*height*16<=receipt['rgba_capacity_peak_bytes']<=256*1024**2
        and receipt['rgba_capacity_bytes_after_flush']==0,
        'actual bounded CPU image-spool completeness/release differs')


def verifier_program():
    require(sha(ORIGINAL)==ORIGINAL_SHA,'original strict verifier changed')
    original = ORIGINAL.read_text(); source = original; edits = []
    def replace(old,new):
        nonlocal source
        count = source.count(old)
        require(count>0 and new not in source,'strict source dispatch guard: '+old)
        source = source.replace(old,new); edits.append((old,new,count))
    for old,new in (
        ('167-bulk-pfm-calibration-fixture-build.json','184-deferred-image-calibration-fixture-build.json'),
        ('168-bulk-pfm-calibration-quiet-sizing.json','185-deferred-image-calibration-sizing.json'),
        ('169-bulk-pfm-calibration-full-renderer.json','186-deferred-image-calibration-full-renderer.json'),
        ('minimal-calibration-build-v3','deferred-image-calibration-build-v1'),
        ('bulk-pfm-calibration-sizing-v1','deferred-image-calibration-sizing-v1'),
        ('bulk-pfm-calibration-accepted-v1','deferred-image-calibration-accepted-v1'),
        ('n010-minimal-calibration-fixture-build/3','n010-minimal-calibration-fixture-build/4'),
        ('n010-bulk-pfm-renderer-calibration/1','n010-deferred-image-renderer-calibration/1'),
        ('71b94470b465f0d16afaec9bec60b42e63c39e6be8ed781f6d5b1802ca99b88a',BUILD_SHA),
        ('(167, 168, 169)','(184, 185, 186)'),
        ("(167, '184-deferred", "(184, '184-deferred"),
        ("(168, '185-deferred", "(185, '185-deferred"),
        ("(169, '186-deferred", "(186, '186-deferred"),
        ('167/168/169','184/185/186'),('paths[167]','paths[184]'),('paths[168]','paths[185]'),('paths[169]','paths[186]')):
        replace(old,new)
    replace("    for mode, proof in (('sizing', sizing), ('accepted', accepted)):\n",
        "    require(sizing['execution_environment']==accepted['execution_environment'], 'sizing/accepted execution environment differs')\n"
        "    require(build.get('whole_inverse_to_167') and build.get('runtime_file_and_pt_timed_bodies_unchanged'), 'parent source inverse/timed-body proof')\n"
        "    for mode, proof in (('sizing', sizing), ('accepted', accepted)):\n        _verify_plan(proof,mode,inputs)\n")
    replace("        require(samples==block['samples'] and len(samples)==len(dose_values)\n",
        "        _verify_spool(block,directory,dose_values,inputs)\n"
        "        require(samples==block['samples'] and len(samples)==len(dose_values)\n")
    restored = source
    for old,new,count in reversed(edits):
        require(restored.count(new)==count,'strict inverse dispatch count differs')
        restored = restored.replace(new,old)
    require(restored==original,'whole original strict verifier inverse differs')
    return source,{'whole_original_strict_verifier_inverse_exact':True,
        'original_source_sha256':ORIGINAL_SHA,'restored_source_sha256':hashlib.sha256(restored.encode()).hexdigest(),
        'generated_source_sha256':hashlib.sha256(source.encode()).hexdigest()}


def verify_calibration(lock_path,inputs):
    source,inverse = verifier_program()
    scope = {'__name__':'n010_deferred_image_timing_intake','__file__':str(ORIGINAL),
        '_verify_plan':verify_plan,'_verify_spool':verify_spool}
    exec(compile(source,str(ORIGINAL)+'#plan054','exec'),scope)
    result = scope['verify_calibration'](lock_path,inputs)
    result['strict_verifier_inverse_proof'] = inverse
    result['cpu_spool_scope'] = 'Bounded CPU RGBA storage separately verified; original all-owned-Vulkan ledger scope unchanged'
    for p in (Path(__file__).resolve(),HERE/'deferred_image_calibration_program.py',PLAN):inputs[str(p)] = sha(p)
    return result
