"""019 compile a new Vulkan replay host; only CPU CLI is executed here."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
import surface_quadratic_cpu as P
import build_surface_quadratic_device as K

ROOT=P.ROOT
HOST=K.SOURCE/'surface_quadratic_device.cpp'
TEST=Path(__file__).with_name('test_surface_quadratic_host.py')
OWN=[HOST,TEST,Path(__file__).resolve()]
HEADERS=ROOT/'build/n007/_deps/vulkan-headers-for-vk-bootstrap-src/include'
LOADER=Path('/run/current-system/sw/share/nix-ld/lib/libvulkan.so')
LEDGER=ROOT/'src/research/n010_comparison_readiness/allocation_ledger.hpp'


def build(kernel,work):
    commit=P.G.head()
    for path in OWN:
        if subprocess.check_output(['git','show',commit+':'+str(path.relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit019host/CPU tests/builder before compilation')
    work=P.P.new_root(work);r=dict(schema='m001-q019-host-cpu-build/1',complete=False,all_pass=False,gpu_executed=False,source_commit=commit,rows=[],m001_float32_replays_run=0,gpu_process_ready=False)
    try:
        old=P.R.read(kernel/'result.json');P.R.require(old['complete'] and old['all_pass'],'019kernel gate incomplete')
        P.F.rehash(old['input_sha256']);P.F.rehash(old['compiled_dependency_sha256']);P.F.rehash({str(kernel/name):digest for name,digest in old['payload_sha256'].items()})
        inputs=P.inputs_now();inputs.update({str(p):P.C.sha(p) for p in [*OWN,*K.OWN,LEDGER,LOADER,kernel/'result.json']})
        inputs.update(old['input_sha256']);r.update(input_sha256=inputs,kernel_build=str(kernel/'result.json'),kernel_build_sha256=P.C.sha(kernel/'result.json'))
        compiler=old['rows'][0]['command'][0];binary=work/'surface-quadratic-device'
        flags=['-std=c++20','-O2','-g','-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(K.SOURCE),'-I'+str(K.SHADERS),'-I'+str(HEADERS),'-I'+str(LEDGER.parent)]
        def execute(label,command,cpu=120,wall=180):
            folder=work/label;folder.mkdir();row=P.G.guarded(command,folder,cpu,wall);row.update(label=label);r['rows'].append(row)
            P.R.require(row['returncode']==0 and not row['timed_out'],'019host CPU command failed: '+label);return row
        execute('compile-link-host',[compiler,*flags,'-MD','-MF',str(work/'host.d'),str(HOST),str(LOADER),'-pthread','-o',str(binary)])
        execute('new-host-cpu-contracts',[sys.executable,str(TEST),'--binary',str(binary),'--kernel-build',str(kernel),'--out',str(work/'native-cpu-tests')],300,600)
        tests=P.R.read(work/'native-cpu-tests/result.json');P.R.require(tests['complete'],'019host tests incomplete')
        dependencies={Path(name).resolve() for name in shlex.split((work/'host.d').read_text().replace('\\\n',' ').split(':',1)[1])}
        P.F.rehash(inputs)
        r.update(complete=True,all_pass=True,actual_new_host_contract_tests=tests['actual_new_host_contract_tests'],compiled_dependency_sha256={str(p):P.C.sha(p) for p in sorted(dependencies)},executable=str(binary),executable_sha256=P.C.sha(binary),shader=old['shader'],shader_sha256=old['shader_sha256'],
                 prior_kernel_contract_tests_reused_not_rerun=19,prior_independent_svd_vectors_reused_not_rerun=old['independent_contracts']['independent_svd_coefficient_vectors'],prior_scalar_cli_tests_reused_not_rerun=24,prior_cpu_gate_sha256=P.C.sha(kernel/'result.json'),new_geometry_replay_byte_exact=tests['new_geometry_replay_byte_exact'],default_build_graph_changed=False)
    except Exception as error:r['error']=repr(error)
    finally:
        r['payload_sha256']={str(p.relative_to(work)):P.C.sha(p) for p in sorted(work.rglob('*')) if p.is_file()};P.G.write(work/'result.json',r)
    print(json.dumps({k:r[k] for k in ('complete','all_pass','actual_new_host_contract_tests','prior_kernel_contract_tests_reused_not_rerun','error') if k in r},indent=2));return r


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--kernel-build',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();r=build(a.kernel_build.resolve(),a.out);raise SystemExit(0 if r['all_pass'] else 1)
