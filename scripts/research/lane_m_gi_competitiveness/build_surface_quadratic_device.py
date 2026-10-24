"""019 CPU-only scalar-kernel compilation/tests and actual SPIR-V qualification.

No Vulkan host execution, no M001 float32 dry replay and no GPU in this builder.
The complete GPU host/process preparation remains a separate required gate.
"""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import surface_quadratic_cpu as P

ROOT=P.ROOT
SOURCE=ROOT/'src/research/lane_m_gi_competitiveness'
SHADERS=ROOT/'shaders/research/lane_m_gi_competitiveness'
PROTOCOL=P.RESULTS.parent/'experiments/019-surface-quadratic-device-correctness.md'
COMPILER=ROOT/'build/n009/_deps/glslang-build/StandAlone/glslang'
SPIRV=Path('/nix/store/z5hs3p3inrq3w8cv71jycz7l4y3ny5xk-spirv-tools-1.4.363.0/bin')
OWN=[SOURCE/name for name in ('surface_quadratic_scalar.hpp','surface_quadratic_scalar.cpp','test_surface_quadratic_scalar.cpp')]
OWN += [SHADERS/name for name in ('surface_quadratic_shared.glslinc','surface_quadratic_device.comp.glsl')]
OWN += [Path(__file__).resolve(),Path(__file__).with_name('test_surface_quadratic_device.py'),PROTOCOL]


def build(work):
    commit=P.G.head()
    for path in OWN:
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit019kernel/test/builder before compiling')
    work=P.P.new_root(work)
    record=dict(schema='m001-q019-kernel-only-cpu-build/1',source_commit=commit,complete=False,all_pass=False,gpu_executed=False,
                m001_float32_replays_run=0,gpu_host_implemented=False,gpu_process_ready=False,rows=[])
    try:
        compiler=Path(shutil.which('c++')).resolve()
        inputs=P.inputs_now();inputs.update({str(p):P.C.sha(p) for p in [*OWN,compiler,COMPILER,SPIRV/'spirv-val',SPIRV/'spirv-dis']})
        for gate in (P.PREPARATION,P.P.PREPARATION):
            old=P.R.read(gate);P.P.pin(gate,inputs);P.P.pin(Path(old['raw_test_receipt']),inputs,old['raw_test_receipt_sha256'])
        record['input_sha256']=inputs
        def run(label,command,cpu=120,wall=180):
            folder=work/label;folder.mkdir();row=P.G.guarded(command,folder,cpu,wall);row.update(label=label)
            record['rows'].append(row);P.R.require(row['returncode']==0 and not row['timed_out'],'019CPU command failed: '+label);return row
        record['compiler_version']=run('compiler-version',[str(compiler),'--version'])['stdout']
        flags=['-std=c++20','-O2','-g','-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(SOURCE),'-I'+str(SHADERS)]
        for name in ('test_surface_quadratic_scalar','surface_quadratic_scalar'):
            run('compile-'+name,[str(compiler),*flags,'-MD','-MF',str(work/(name+'.d')),str(SOURCE/(name+'.cpp')),'-o',str(work/name)])
        target=work/'surface_quadratic_device.spv'
        run('compile-shader',[str(COMPILER),'-V','--target-env','vulkan1.3','-S','comp','-I'+str(SHADERS),str(SHADERS/'surface_quadratic_device.comp.glsl'),'-o',str(target)])
        run('validate-shader',[str(SPIRV/'spirv-val'),'--target-env','vulkan1.3',str(target)])
        dis=run('disassemble-shader',[str(SPIRV/'spirv-dis'),str(target)])['stdout']
        no_contraction=dis.count(' NoContraction');P.R.require(no_contraction>=20,'019ordered arithmetic missing NoContraction evidence')
        actual=run('actual-shared-scalar-tests',[str(work/'test_surface_quadratic_scalar'),str(work/'fixtures')])
        contracts=json.loads(actual['stdout']);P.R.require(contracts['pass_'] and contracts['actual_shared_float32_contract_tests']==19,'019actual scalar contracts unavailable')
        run('independent-svd-and-native-contracts',[sys.executable,str(OWN[-2]),'--fixtures',str(work/'fixtures'),'--binary',str(work/'surface_quadratic_scalar'),'--out',str(work/'independent-tests')],300,600)
        independent=P.R.read(work/'independent-tests/result.json');P.R.require(independent['complete'],'019independent contracts incomplete')
        dependencies=set()
        for path in work.glob('*.d'):
            for name in shlex.split(path.read_text().replace('\\\n',' ').split(':',1)[1]):dependencies.add(Path(name).resolve())
        record.update(compiled_dependency_sha256={str(p):P.C.sha(p) for p in sorted(dependencies)},actual_shared_kernel_contracts=contracts,
                      independent_contracts=independent,native_cli_contract_tests=len(independent['native_contracts']),shader_no_contraction_decorations=no_contraction,
                      scalar_executable=str(work/'surface_quadratic_scalar'),scalar_executable_sha256=P.C.sha(work/'surface_quadratic_scalar'),shader=str(target),shader_sha256=P.C.sha(target),
                      complete=True,all_pass=True,default_build_graph_changed=False,old_test_suites_rerun=False)
        P.F.rehash(inputs)
    except Exception as error:record['error']=repr(error)
    finally:
        record['payload_sha256']={str(p.relative_to(work)):P.C.sha(p) for p in sorted(work.rglob('*')) if p.is_file()}
        P.G.write(work/'result.json',record)
    print(json.dumps({k:record[k] for k in ('complete','all_pass','actual_shared_kernel_contracts','native_cli_contract_tests','shader_no_contraction_decorations','error') if k in record},indent=2))
    return record


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();r=build(args.out);sys.exit(0 if r['all_pass'] else 1)
