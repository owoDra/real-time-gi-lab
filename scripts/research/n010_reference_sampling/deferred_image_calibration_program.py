"""Plan 054 acquisition assembly and CPU-spool proof; no dispatch at import."""
import hashlib
import json
import platform
from pathlib import Path

from deferred_image_capture_programs import HERE, ROOT, RESULTS, PLAN, FIXTURE
from hidden_ide_bulk_pfm_program import original_program


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def environment():
    device = Path('/sys/class/drm/renderD128/device')
    if not Path('/dev/dri/renderD128').exists() or (device/'vendor').read_text().strip()!='0x1002':
        raise ValueError('actual AMD Vulkan render node required')
    return {'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'kernel':platform.release(),'pci_device':str(device.resolve()),
        'driver':str((device/'driver').resolve()),
        'vendor':(device/'vendor').read_text().strip(),'device':(device/'device').read_text().strip(),
        'scope':'Read-only OS identity. No hidden-window policy, display/power/clock changes or global-quiescence claim.'}


class Acquisition:
    def __init__(self,result,args,inputs,proof):
        self.result,self.args,self.inputs = result,args,inputs
        self.environment = environment()
        if args.mode=='accepted' and json.loads(args.plan.read_bytes())['execution_environment']!=self.environment:
            raise ValueError('full calibration requires the actual sizing boot/device/driver environment')
        result['execution_environment'] = self.environment
        result['plan054_source_inverse_proof'] = proof

    def wrap(self,execute):
        def checked(boundary,lock,doses,out):
            if environment()!=self.environment:
                raise ValueError('registered execution environment changed')
            result = execute(boundary,lock,doses,out)
            receipt = json.loads((out/'deferred-image-serialization.json').read_bytes())
            directory = out/'frames'/'0'
            if (directory/'gpu').is_dir(): directory = directory/'gpu'
            with (directory/'direct.pfm').open('rb') as f:
                if f.readline().strip()!=b'PF':raise ValueError('spooled image header differs')
                width,height = map(int,f.readline().split())
            if (receipt['schema']!='n010-deferred-image-serialization/1' or not receipt['complete']
                or receipt['retained_frames']!=len(doses) or receipt['written_frames']!=len(doses)
                or receipt['rgba_capacity_limit_bytes']!=256*1024**2
                or not len(doses)*width*height*16<=receipt['rgba_capacity_peak_bytes']<=256*1024**2
                or receipt['rgba_capacity_bytes_after_flush']!=0):
                raise ValueError('CPU image-spool bound, completeness or release differs')
            result['deferred_image_serialization'] = receipt
            result['deferred_image_serialization_sha256'] = sha(out/'deferred-image-serialization.json')
            if environment()!=self.environment:
                raise ValueError('execution environment changed during native work')
            return result
        return checked

    def __enter__(self): return self

    def __exit__(self,kind,error,traceback):
        if kind is not None:
            self.result.update(complete=False,all_pass=False,
                classification='OPERATIONAL_FAILURE_PARTIALS_RETAINED_NOT_ACCEPTED',failure=str(error))
            self.args.output.write_text(json.dumps(self.result,indent=2)+'\n')
        return False


def program(entry):
    original,scope = original_program()
    if hashlib.sha256(original.encode()).hexdigest()!='18f906fee96fc1cbb43f9f225c4c6ea35224cac01e6d9736647308e56436b55c':
        raise ValueError('whole frozen plan-048 generated program changed')
    source,edits = original,[]
    def replace(old,new):
        nonlocal source
        count = source.count(old)
        if count<1 or new in source:raise ValueError('deferred acquisition dispatch guard differs: '+old)
        source = source.replace(old,new); edits.append((old,new,count))
    for old,new in (
        ('167-bulk-pfm-calibration-fixture-build.json','184-deferred-image-calibration-fixture-build.json'),
        ('n010-minimal-calibration-fixture-build/3','n010-minimal-calibration-fixture-build/4'),
        ('minimal-calibration-build-v3','deferred-image-calibration-build-v1'),
        ('168-bulk-pfm-calibration-quiet-sizing.json','185-deferred-image-calibration-sizing.json'),
        ('169-bulk-pfm-calibration-full-renderer.json','186-deferred-image-calibration-full-renderer.json'),
        ('bulk-pfm-calibration-sizing-v1','deferred-image-calibration-sizing-v1'),
        ('bulk-pfm-calibration-accepted-v1','deferred-image-calibration-accepted-v1'),
        ('n010-bulk-pfm-renderer-calibration/1','n010-deferred-image-renderer-calibration/1'),
        ('actual sizing 168','actual sizing 185'),('full PASS 168 required','full PASS 185 required')):
        replace(old,new)
    replace(' _inputs={}',
        " _inputs={}\n for _path in _extra_inputs: _inputs[str(_path)]=sha(_path)")
    replace(" _check_files(_build['input_sha256'],_inputs)",
        " if not _build.get('whole_inverse_to_167') or not _build.get('runtime_file_and_pt_timed_bodies_unchanged'):\n"
        "  raise ValueError('full parent source inverse/timed-body proof missing')\n"
        " _check_files(_build['input_sha256'],_inputs)")
    anchor = ' for boundary in cohort:\n'
    if source.count(anchor)!=1:raise ValueError('complete acquisition loop differs')
    head,tail = source.split(anchor)
    hook = (' _acquisition=_Acquisition(result,a,_inputs,_assembly_proof)\n'
            ' execute=_acquisition.wrap(execute)\n with _acquisition:\n')
    unwrapped = anchor+tail
    source = head+hook+''.join(' '+line if line.strip() else line for line in unwrapped.splitlines(keepends=True))
    restored = head+unwrapped
    for old,new,count in reversed(edits):
        if restored.count(new)!=count:raise ValueError('inverse acquisition dispatch count differs')
        restored = restored.replace(new,old)
    definitions = source.split("if __name__=='__main__':")[0]
    for old,new,count in reversed(edits):
        definitions = definitions.replace(new,old)
    if (restored!=original or definitions!=original.split("if __name__=='__main__':")[0]
        or source.split('def schedule(')[1].split("if __name__")[0]
            !=original.split('def schedule(')[1].split("if __name__")[0]):
        raise ValueError('whole inverse or original scientific schedule/analysis changed')
    proof = {'whole_generated_program_inverse_exact':True,
        'function_definitions_inverse_exact_after_declared_fixture_dispatch':True,
        'original_schedule_analysis_byte_identical':True,
        'original_generated_source_sha256':hashlib.sha256(original.encode()).hexdigest(),
        'restored_generated_source_sha256':hashlib.sha256(restored.encode()).hexdigest(),
        'generated_source_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'dispatch_changes':[{'old':old,'new':new,'count':count} for old,new,count in edits]}
    scope.update(_wrapper=str(Path(entry).resolve()),_Acquisition=Acquisition,_assembly_proof=proof,
        _extra_inputs=[Path(entry).resolve(),Path(__file__).resolve(),PLAN,
            HERE/'hidden_ide_bulk_pfm_program.py',HERE/'bulk_pfm_capture_programs.py',
            HERE/'calibrate_bulk_pfm_capture.py',HERE/'deferred_image_capture_programs.py'])
    return source,scope,proof
