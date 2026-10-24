"""020 build exactly one private material-token loader overlay; CPU tests only."""
import argparse
import json
from pathlib import Path
import shlex
import sys
import surface_quadratic_material_abi as M
import build_surface_quadratic_host as H


def build(out):
    M.committed();out=M.OLD.P.new_root(out)
    r=dict(schema='m001-q020-private-host-build/1',complete=False,all_pass=False,gpu_executed=False,source_commit=M.G.head(),rows=[])
    try:
        gate=M.R.read(M.OLD.PREPARATION);inputs={str(p):M.C.sha(p) for p in M.OWN}
        M.F.rehash(gate['source_input_sha256']);inputs.update(gate['source_input_sha256'])
        for name in ('kernel_build','host_build'):
            b=gate[name];old=M.OLD.pin_inventory(Path(b['raw_receipt']),inputs,b['raw_receipt_sha256']);M.F.rehash(old['input_sha256']);M.F.rehash(old['compiled_dependency_sha256']);inputs.update(old['input_sha256']);inputs.update(old['compiled_dependency_sha256'])
            if name=='kernel_build':kernel=Path(b['raw_receipt']).parent;compiler=old['rows'][0]['command'][0]
        overlay=out/'source';overlay.mkdir()
        for name in ('surface_quadratic_device.cpp','surface_quadratic_scalar.cpp','surface_quadratic_scalar.hpp'):
            original=M.SOURCE/name;M.OLD.P.pin(original,inputs);data=original.read_text();(overlay/name).write_text(M.repaired(data) if name.endswith('scalar.cpp') else data)
        binary=out/'surface-quadratic-device';flags=['-std=c++20','-O2','-g','-fno-fast-math','-ffp-contract=off','-fsanitize=undefined','-fno-sanitize-recover=all','-I'+str(overlay),'-I'+str(H.K.SHADERS),'-I'+str(H.HEADERS),'-I'+str(H.LEDGER.parent)]
        def execute(label,command,cpu=120,wall=180):
            folder=out/label;folder.mkdir();row=M.G.guarded(command,folder,cpu,wall);row['label']=label;r['rows'].append(row);M.R.require(row['returncode']==0 and not row['timed_out'],'020 CPU command failed: '+label)
        execute('compile-link-host',[compiler,*flags,'-MD','-MF',str(out/'host.d'),str(overlay/'surface_quadratic_device.cpp'),str(H.LOADER),'-pthread','-o',str(binary)])
        execute('material-abi-contracts',[sys.executable,str(Path(__file__).with_name('test_surface_quadratic_material_abi.py')),'--binary',str(binary),'--kernel-build',str(kernel),'--out',str(out/'contracts')],120,180)
        tests=M.R.read(out/'contracts/result.json');M.R.require(tests['complete'],'020 native tests incomplete')
        dependencies={Path(n).resolve() for n in shlex.split((out/'host.d').read_text().replace('\\\n',' ').split(':',1)[1])};M.F.rehash(inputs)
        r.update(complete=True,all_pass=True,input_sha256=inputs,compiled_dependency_sha256={str(p):M.C.sha(p) for p in sorted(dependencies)},executable=str(binary),executable_sha256=M.C.sha(binary),shader=gate['shader'],shader_sha256=gate['shader_sha256'],actual_native_cli_contracts=tests['native_cli_contracts'],canonical_overlay_contracts=tests['canonical_overlay_contracts'],overlay_exactly_reversible=True,unchanged_shared_kernel_tests_reused_not_rerun=19,obsolete_material_negative_test_carried_forward=False,shader_recompiled=False,m001_rehearsals_run=0,gpu_process_ready=False)
    except Exception as e:r['error']=repr(e)
    finally:
        r['payload_sha256']={str(p.relative_to(out)):M.C.sha(p) for p in sorted(out.rglob('*')) if p.is_file()};M.G.write(out/'result.json',r)
    print(json.dumps({k:r[k] for k in ('complete','all_pass','actual_native_cli_contracts','canonical_overlay_contracts','error') if k in r},indent=2));return r


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=build(a.out.resolve());raise SystemExit(0 if r['all_pass'] else 1)
