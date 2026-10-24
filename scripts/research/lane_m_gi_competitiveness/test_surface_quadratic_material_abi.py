"""020 actual host material ABI/negative contracts with an unusable Vulkan ICD."""
import argparse
import json
import os
from pathlib import Path
import numpy as np
import surface_quadratic_material_abi as M


def run(binary,kernel,out):
    out=M.OLD.P.new_root(out);r=dict(schema='m001-q020-material-abi-contracts/1',complete=False,gpu_executed=False,rows=[])
    saved=os.environ.get('VK_ICD_FILENAMES');os.environ['VK_ICD_FILENAMES']='/nonexistent/q020-no-vulkan.json'
    try:
        base=kernel/'independent-tests/valid-one-hit-cpu/input';raw=np.fromfile(base/'hits.u32',dtype='<u4').reshape(-1,8);camera=np.fromfile(base/'camera.f32',dtype='<f4');sources=np.fromfile(base/'sources.f32',dtype='<f4')
        def case(name,hits=raw,cam=camera,source=sources,valid=False,error=None,existing=None,mode='--cpu-check'):
            work=out/name;work.mkdir();inp=work/'input';inp.mkdir();hits.tofile(inp/'hits.u32');cam.tofile(inp/'camera.f32');source.tofile(inp/'sources.f32');target=existing or work/'capture'
            before={str(p.relative_to(target)):M.C.sha(p) for p in target.rglob('*') if p.is_file()} if target.exists() else None
            command=[str(binary),mode,'--input',str(inp),'--out',str(target)]
            if mode=='--gpu':command+=['--shader',str(kernel/'surface_quadratic_device.spv')]
            row=M.G.guarded(command,work,120,180);M.R.require(row['returncode']==(0 if valid else 2) and not row['timed_out'],name+': '+row['stderr'])
            if error:M.R.require(error in row['stderr'],name+' wrong rejection boundary')
            if valid:M.R.require(M.R.read(target/'complete.json')['gpu_initialized'] is False,name+' initialized GPU')
            elif existing is None:M.R.require(not target.exists(),name+' created output before rejection')
            if before is not None:M.R.require(before=={str(p.relative_to(target)):M.C.sha(p) for p in target.rglob('*') if p.is_file()},name+' changed accepted output')
            M.G.write(work/'result.json',row);r['rows'].append(dict(name=name,receipt=str(work/'result.json'),sha256=M.C.sha(work/'result.json')));return target
        accepted=[]
        for token in (0,0xffffffff,0x80000001):
            h=raw.copy();h[0,5]=token;accepted.append(case('valid-material-'+str(token),hits=h,valid=True))
        for name in ('geometry.f32','coefficients.f32','maps.u32','stages.f32','unclipped.f32'):
            M.R.require(len({M.C.sha(p/name) for p in accepted})==1,'020 opaque token changed single-hit math')
        for name,word,value,error in [('primitive-sentinel',4,0xffffffff,'hit primitive/instance'),('instance-sentinel',6,0xffffffff,'hit primitive/instance'),('flag-invalid',7,2,'primary flag'),('normal-invalid',2,0,'primary normal/depth'),('depth-negative',3,np.float32(-1).view('<u4'),'primary normal/depth')]:
            h=raw.copy();h[0,word]=value;case(name,hits=h,error=error)
        for word in (4,5,6):
            h=raw.copy();h[1,word]=0;case('miss-metadata-'+str(word),hits=h,error='miss metadata')
        for name,value in [('source-negative',-1),('source-nonfinite',np.nan)]:
            s=sources.copy();s[0]=value;case(name,source=s,error='source nonfinite/negative')
        cam=camera.copy();cam[0]=np.inf;case('camera-nonfinite',cam=cam,error='nonfinite camera')
        case('source-byte-size',source=sources[:-1],error='input shape/size')
        case('overwrite-cpu-refused',existing=accepted[1],error='output exists')
        case('overwrite-gpu-refused',existing=accepted[1],mode='--gpu',error='output exists')
        for word in (4,6):
            h=raw.copy();h[0,word]=0xffffffff;case('gpu-invalid-id-'+str(word),hits=h,mode='--gpu',error='hit primitive/instance')
        checks=0
        text=(M.SOURCE/'surface_quadratic_scalar.cpp').read_text();M.R.require(M.repaired(text).replace(M.AFTER,M.BEFORE)==text,'inverse overlay failed');checks+=1
        try:M.repaired(text.replace(M.BEFORE,M.AFTER))
        except ValueError:checks+=1
        else:raise AssertionError('modified source allowed')
        meta=np.array([[0,0xffffffff,0]],dtype=np.uint32);h=raw.copy();h[0,5]=0xffffffff;M.canonical_metadata(h,meta);checks+=1
        for word in (4,5,6,7):
            bad=h.copy();bad[0,word]=1 if word!=7 else 2
            try:M.canonical_metadata(bad,meta)
            except ValueError:checks+=1
            else:raise AssertionError('canonical mismatch allowed: '+str(word))
        folder=Path(__file__).parent
        old=(folder/'surface_quadratic_replay_audit.py').read_text().replace('019','020').replace('import surface_quadratic_replay as T','import surface_quadratic_material_replay as T')
        M.R.require(old==(folder/'surface_quadratic_material_audit.py').read_text(),'020 independent numerical auditor changed beyond labels/import');checks+=1
        import ast
        oldtree=ast.parse((folder/'surface_quadratic_replay.py').read_text().replace('019','020'))
        newtree=ast.parse((folder/'surface_quadratic_material_replay.py').read_text())
        oldfunctions={f.name:ast.dump(f,include_attributes=False) for f in oldtree.body if isinstance(f,ast.FunctionDef)}
        newfunctions={f.name:ast.dump(f,include_attributes=False) for f in newtree.body if isinstance(f,ast.FunctionDef)}
        for name in ('selected_spp','decision','tag','previous_gate','pin_inventory','images','input_arrays','run_cpu'):
            M.R.require(oldfunctions[name]==newfunctions[name],'020 protected runner function changed: '+name);checks+=1
        r.update(complete=True,native_cli_contracts=len(r['rows']),canonical_overlay_contracts=checks,opaque_material_outputs_byte_exact=True,existing_outputs_and_inventory_preserved=True,obsolete019material_negative_test_carried_forward=False)
    except Exception as e:r['error']=repr(e)
    finally:
        if saved is None:os.environ.pop('VK_ICD_FILENAMES',None)
        else:os.environ['VK_ICD_FILENAMES']=saved
        M.G.write(out/'result.json',r)
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--kernel-build',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=run(a.binary,a.kernel_build,a.out);print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2));raise SystemExit(0 if r['complete'] else 1)
