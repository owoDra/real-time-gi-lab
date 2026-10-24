"""019 actual new host CLI routes/replay/rejection, never a Vulkan acquisition."""
import argparse
import json
import os
from pathlib import Path
import numpy as np
import surface_quadratic_cpu as P


def run(binary,kernel,out):
    out=P.P.new_root(out);record=dict(schema='m001-q019-host-cpu-contracts/1',complete=False,gpu_executed=False,rows=[])
    saved_icd=os.environ.get('VK_ICD_FILENAMES');os.environ['VK_ICD_FILENAMES']='/nonexistent/q019-host-no-vulkan.json'
    try:
        base=kernel/'independent-tests/native-input';one=kernel/'independent-tests/valid-one-hit-cpu/input';shader=kernel/'surface_quadratic_device.spv'
        def case(name,mode='--gpu',input=base,changes=None,shaderpath=shader,arguments=None,existing=None,valid=False,error=None):
            work=out/name;work.mkdir();inputs=work/'input';inputs.mkdir();changes=changes or {}
            for filename in ('camera.f32','hits.u32','sources.f32','geometry.f32'):
                if filename in changes:
                    if changes[filename] is not None:(inputs/filename).write_bytes(changes[filename])
                elif (input/filename).exists():os.link(input/filename,inputs/filename)
            target=existing or work/'capture'
            args=arguments if arguments is not None else [mode,'--input',str(inputs),'--out',str(target),*(['--shader',str(shaderpath)] if mode=='--gpu' else [])]
            hashes={str(p):P.C.sha(p) for p in target.iterdir()} if target.exists() else None
            row=P.G.guarded([str(binary),*args],work,120,180)
            assert row['returncode']==(0 if valid else 2) and not row['timed_out'],name+': '+row['stderr']
            if error is not None:assert error in row['stderr'],name+' rejected at unexpected boundary'
            if valid:assert P.R.read(target/'complete.json')['gpu_initialized'] is False
            elif existing is None:assert not target.exists(),name+' wrote before invalid-input rejection'
            if hashes is not None:
                P.F.rehash(hashes);assert {str(p) for p in target.iterdir()}==set(hashes),name+' changed existing inventory'
            P.G.write(work/'result.json',dict(row,name=name,expected_gpu_initialization=False));record['rows'].append(dict(name=name,receipt=str(work/'result.json'),sha256=P.C.sha(work/'result.json')))
            return target
        allmiss=case('cpu-route-all-miss',mode='--cpu-check',valid=True)
        onehit=case('cpu-route-one-hit',mode='--cpu-check',input=one,valid=True)
        geometry=(onehit/'geometry.f32').read_bytes()
        replay=case('device-geometry-cpu-replay',mode='--cpu-replay-geometry',input=one,changes={'geometry.f32':geometry},valid=True)
        for filename in ('geometry.f32','coefficients.f32','maps.u32','stages.f32','unclipped.f32'):assert (replay/filename).read_bytes()==(onehit/filename).read_bytes(),'new geometry replay differs'
        case('missing-mode',arguments=[],error='usage:');case('unknown-mode',arguments=['--unknown'],error='usage:')
        case('missing-gpu-input',changes={'camera.f32':None},error='input shape/size')
        case('missing-gpu-shader',shaderpath=out/'absent.spv',error='invalid SPIR-V size/path')
        small=out/'wrong-size.spv';small.write_bytes(b'bad');case('gpu-shader-byte-size',shaderpath=small,error='invalid SPIR-V size/path')
        wrong=out/'wrong-magic.spv';wrong.write_bytes(bytes(20));case('gpu-shader-magic',shaderpath=wrong,error='invalid SPIR-V magic')
        case('gpu-existing-output-refused',existing=allmiss,error='output exists')
        case('geometry-missing',mode='--cpu-replay-geometry',input=one,error='input shape/size')
        case('geometry-byte-size',mode='--cpu-replay-geometry',input=one,changes={'geometry.f32':b'bad'},error='input shape/size')
        for name,index,value,reason in [('nonfinite-geometry',0,np.nan,'geometry nonfinite'),('nonunit-geometry-normal',6,0,'geometry normal not unit'),('nonzero-miss-geometry',8,1,'nonzero miss geometry')]:
            data=np.frombuffer(geometry,dtype='<f4').copy();data[index]=value
            case(name,mode='--cpu-replay-geometry',input=one,changes={'geometry.f32':data.tobytes()},error=reason)
        record.update(complete=True,actual_new_host_contract_tests=len(record['rows']),new_geometry_replay_byte_exact=True,prior_kernel_tests_rerun=False)
    except Exception as error:record['error']=repr(error)
    finally:
        if saved_icd is None:os.environ.pop('VK_ICD_FILENAMES',None)
        else:os.environ['VK_ICD_FILENAMES']=saved_icd
        P.G.write(out/'result.json',record)
    return record


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--binary',type=Path,required=True);ap.add_argument('--kernel-build',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    r=run(a.binary,a.kernel_build,a.out);print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));raise SystemExit(0 if r['complete'] else 1)
