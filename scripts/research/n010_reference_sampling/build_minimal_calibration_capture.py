#!/usr/bin/env python3
"""Plan 044: isolated image/scratch calibration fixture; no GPU dispatch."""
import argparse
import json
from pathlib import Path
import resource
import shlex
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parents[1]/'n010_comparison_readiness'
sys.path.insert(0,str(SCRIPTS))
from generate_rqmc_oracle import once
from reference_provenance import ROOT, RESULTS, sha
from qualify_hybrid_references import check_files

BUILD = ROOT/'build/n009'
PLAN = RESULTS.parent/'experiments/044-prospective-minimal-calibration-capture.md'
SWITCH = 'PHOS_N010_MINIMAL_CALIBRATION_READBACK'

def guards():
    resource.setrlimit(resource.RLIMIT_AS,(8*1024**3,8*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(21600,21600))

def overlay(source,pairs):
    result = source
    for old,new in pairs:
        result = once(result,old,new)
    restored = result
    for old,new in reversed(pairs):
        restored = once(restored,new,old)
    if restored != source:
        raise ValueError('inverse source proof failed')
    return result

def commands(target):
    proc = subprocess.run(['ninja','-C',str(BUILD),'-t','commands',target],
        check=True,capture_output=True,text=True)
    result = []
    for line in proc.stdout.splitlines():
        args = shlex.split(line)
        if args[:2] == [':','&&'] and args[-2:] == ['&&',':']:
            args = args[2:-2]
        if '-c' in args or ('-o' in args and args[args.index('-o')+1] == target):
            if any(a in ('&&',';','|',':') for a in args):
                raise ValueError('unexpected shell operation in compiler/link command')
            result.append(args)
    return result

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a = ap.parse_args()
    if a.work.exists() or a.output.exists():
        raise ValueError('refuse existing fixture build; no retry')
    inputs = {str(p.resolve()):sha(p) for p in (Path(__file__),PLAN,BUILD/'build.ninja',
        SCRIPTS/'generate_calibration.py',SCRIPTS/'generate_capture.py',
        SCRIPTS/'generate_rqmc_oracle.py')}
    active_hashes = {'phos-n010-capture':'cc6d7802a45d68d5074a13bbdd5c2cc94310d2f7fa5c303ee890508dae7535ab',
                     'phos-n010-pixel-pt':'b96880ba40c8466b4210d9e5af0dad80855c96416496a6c47ad9dc7670d60ea0'}
    for name,digest in active_hashes.items():
        if sha(BUILD/name) != digest:
            raise ValueError('active executable identity changed')
        inputs[str(BUILD/name)] = digest
    original_paths = {
        'runtime':BUILD/'src/research/n010_comparison_readiness/generated/n010_runtime.cpp',
        'capture':BUILD/'src/research/n010_comparison_readiness/generated/n010_capture_main.cpp',
        'pt':ROOT/'src/research/n010_comparison_readiness/pixel_pt_main.cpp'}
    inputs.update({str(p):sha(p) for p in original_paths.values()})
    originals = {k:p.read_text() for k,p in original_paths.items()}
    runtime_pairs = [
        ('    out.surfaces = impl_->a_scene.samples;\n    out.triangles = impl_->b_scene.triangles;',
         '    const bool n010_minimal=impl_->n010_neutral && std::getenv("'+SWITCH+'");\n'
         '    if(!n010_minimal) {\n'
         '        out.surfaces = impl_->a_scene.samples;\n        out.triangles = impl_->b_scene.triangles;\n    }'),
        ('    // Diagnostic SSBO export: existing primary traversal remains unchanged.',
         '    if(n010_minimal) {\n'
         '        const char* directory=std::getenv("PHOS_N007_PROBE_DIR");\n'
         '        if(!directory || !*directory)fail("minimal calibration scratch directory missing");\n'
         '        impl_->n010_neutral->save(std::filesystem::path(directory)/"neutral-work.bin");\n'
         '        return out;\n    }\n'
         '    // Diagnostic SSBO export: existing primary traversal remains unchanged.')]
    capture_pairs = [
        ('                const auto image=runtime.renderer_readback();capture_state(directory,image);',
         '                const auto image=runtime.renderer_readback();\n'
         '                if(!std::getenv("'+SWITCH+'"))capture_state(directory,image);')]
    pt_pairs = [
        ('            copy_state(target&&(f>0||!doses.empty()) ? target_path : state,frame_out);',
         '            if(doses.empty())copy_state(target&&(f>0||!doses.empty()) ? target_path : state,frame_out);')]
    generated = {key:overlay(originals[key],pairs) for key,pairs in (
        ('runtime',runtime_pairs),('capture',capture_pairs),('pt',pt_pairs))}
    # These entire methods/loops must remain byte-identical, not only their shaders.
    for begin in ('    [[nodiscard]] I001FrameResult run_frame(bool target_state) {',):
        # The inverse proof is the authoritative full-file check. Explicitly
        # retain a fingerprint of the actual timed method through its return.
        start = originals['runtime'].index(begin)
        stop = originals['runtime'].index('\n    }',start)+6
        if originals['runtime'][start:stop] != generated['runtime'][start:stop]:
            raise ValueError('timed Renderer method changed')
    for path in (BUILD/'shaders').glob('*.spv'):
        inputs[str(path)] = sha(path)
    a.work = a.work.resolve();a.work.mkdir(parents=True)
    generated_paths = {}
    for key,text in generated.items():
        path = a.work/('minimal_'+key+'.cpp');path.write_text(text);generated_paths[key] = path
    result = {'schema':'n010-minimal-calibration-fixture-build/1','complete':False,'all_pass':False,
        'gpu_run':False,'input_sha256':inputs,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'source_inverse_proof':True,'timed_renderer_method_unchanged':True,'steps':[],
        'scope':'CPU fixture compilation only; no GPU image equivalence, calibration capability, regression validation or readiness',
        'limits':{'address_space_bytes':8*1024**3,'cpu_seconds':21600,'elapsed_seconds_per_invocation':3600},
        'environment_switch':SWITCH}
    def save():
        a.output.write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        for target,keys in (('phos-n010-capture',('runtime','capture')),('phos-n010-pixel-pt',('pt',))):
            rows = commands(target)
            replacements = {}
            selected = []
            for key in keys:
                matches = [args for args in rows if '-c' in args and Path(args[args.index('-c')+1]) == original_paths[key]]
                if len(matches) != 1:
                    raise ValueError('native compile command is not unique')
                old_args = matches[0]
                old_object = old_args[old_args.index('-o')+1]
                dep = subprocess.run(['ninja','-C',str(BUILD),'-t','deps',old_object],check=True,capture_output=True,text=True)
                dependencies = [Path(line.strip()) for line in dep.stdout.splitlines() if line.startswith('    ')]
                if not dependencies:
                    raise ValueError('actual compile dependencies unavailable')
                for path in dependencies:
                    path = path if path.is_absolute() else BUILD/path
                    inputs[str(path.resolve())] = sha(path)
                args = list(old_args);obj = a.work/(key+'.o')
                for option,value in (('-o',str(obj)),('-MT',str(obj)),('-MF',str(obj)+'.d'),('-c',str(generated_paths[key]))):
                    args[args.index(option)+1] = value
                replacements[old_object] = str(obj);selected.append(args)
            links = [args for args in rows if '-c' not in args and '-o' in args and args[args.index('-o')+1] == target]
            if len(links) != 1:
                raise ValueError('native link command is not unique')
            link = []
            for arg in links[0]:
                if arg in replacements:
                    arg = replacements[arg]
                elif arg.startswith('-Wl,--dependency-file='):
                    arg = '-Wl,--dependency-file='+str(a.work/(target+'.link.d'))
                elif arg.endswith(('.o','.a')):
                    path = Path(arg) if Path(arg).is_absolute() else BUILD/arg
                    inputs[str(path.resolve())] = sha(path)
                link.append(arg)
            link[link.index('-o')+1] = str(a.work/target)
            for args in selected+[link]:
                compiler = Path(args[0]).resolve()
                inputs[str(compiler)] = sha(compiler)
                check_files(inputs,{})
                proc = subprocess.run(args,cwd=BUILD,text=True,capture_output=True,timeout=3600,preexec_fn=guards)
                result['steps'].append({'command':args,'cwd':str(BUILD),'returncode':proc.returncode,
                    'stdout':proc.stdout,'stderr':proc.stderr});save()
                if proc.returncode:
                    raise ValueError('fixture compile/link failure; no retry')
                check_files(inputs,{})
        result['generated_sha256'] = {p.name:sha(p) for p in a.work.iterdir() if p.is_file()}
        check_files(inputs,{})
        result['active_inputs_byte_unchanged'] = True
        result['all_pass'] = True
    except (ValueError,OSError,KeyError,AssertionError,subprocess.SubprocessError) as error:
        result['failure'] = str(error)
    result['complete'] = True;save()
    print(json.dumps({'all_pass':result['all_pass'],'failure':result.get('failure')}))
    raise SystemExit(0 if result['all_pass'] else 2)
