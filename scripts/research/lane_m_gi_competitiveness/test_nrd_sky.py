#!/usr/bin/env python3
"""025 adversarial intervention/stop contracts and actual patched SDK inspection."""
import argparse
import json
from pathlib import Path
import tempfile
import numpy as np
import nrd_sky_build as B
import nrd_sky_audit as A
import nrd_sky_process as P
import test_nrd_cpu as T

def run(work,build_path):
    head=B.committed();work=work.resolve();B.need(work.is_relative_to(B.BASE) and not work.exists(),'025 exclusive CPU contracts output')
    build=B.read(build_path);B.need(build['all_pass'] and not build['gpu_executed'],'025 passing actual private build required')
    B.rehash(build['input_sha256']);B.rehash(build['compiled_dependency_sha256']);B.rehash({str(build_path.parent/p):h for p,h in build['payload_sha256'].items()})
    work.mkdir();r=dict(schema='m001-nrd025-sky-intervention-cpu-contracts/1',source_commit=head,complete=False,all_pass=False,gpu_executed=False,build_receipt=str(build_path),build_receipt_sha256=B.SHA(build_path),input_sha256={str(p):B.SHA(p) for p in B.OWN},checks=[],commands=[],probes=[])
    def check(name,fn):
        fn();r['checks'].append(dict(name=name,pass_=True))
    def rejects(fn):
        try:fn()
        except (ValueError,FileNotFoundError):return
        raise AssertionError('025 expected rejection')
    try:
        check('source intervention matches one pinned occurrence',lambda:B.need(B.patch(B.OLD.encode())==B.NEW.encode(),'patch'))
        for name,data in [('absent patch site',b''),('multiple patch sites',(B.OLD*2).encode()),('already patched source',B.NEW.encode())]:
            check('reject '+name,lambda data=data:rejects(lambda:B.patch(data)))
        old=np.array([[77,0],[0,0]],dtype='u1');sky=np.array([[True,True],[False,False]]);zero=np.zeros((2,2),dtype='u1')
        check('accept sky initialization with unchanged active zeros',lambda:B.need(A.intervention_arrays(old,zero,sky)['changed_bytes']==1,'material proof'))
        changed=zero.copy();changed[1,1]=1
        check('reject changed active material despite identical sky',lambda:rejects(lambda:A.intervention_arrays(old,changed,sky)))
        changed_sky=zero.copy();changed_sky[0,0]=1
        check('reject noncanonical sky material',lambda:rejects(lambda:A.intervention_arrays(old,changed_sky,sky)))
        check('reject truncated material capture',lambda:rejects(lambda:A.intervention_arrays(old,zero[:1],sky)))
        check('reject untyped sky classification',lambda:rejects(lambda:A.intervention_arrays(old,zero,sky.astype('u1'))))
        check('previous unexecuted control blocks H02 preparation',lambda:rejects(lambda:P.previous('H02',8)))
        with tempfile.TemporaryDirectory(dir=work) as folder:
            p=Path(folder);(p/'plan.json').write_text('{}')
            check('unlaunched one-plan intake accepted',lambda:P.launch_inventory(p))
            (p/'started.json').write_text('{}')
            check('launched or partial intake rejected without GPU',lambda:rejects(lambda:P.launch_inventory(p)))
        check('original target order and budgets unchanged',lambda:B.need(P.TARGETS==[('H01',2,16),('H02',8,64),('H03',2,64)],'target order'))
        # Independent actual SDK inspection and comparison of every saved
        # dispatch, resource, setting and constant byte, with no GPU ICD.
        first_pipeline=None
        for cell,depth,spp in P.TARGETS:
            pins={};proof=P.original(cell,depth,pins);old=B.BASE/('m001-nrd023-cpu-contracts-v1' if cell=='H01' else 'm001-nrd023-cpu-contracts-v3')/cell.lower()
            state=Path(proof['primary_capture']);out=work/cell.lower()
            # P.original points to this experiment's not-yet-created SDK
            # output. The original state/camera/oracle are already pinned.
            command=[build['api_executable'],'--cpu-inspect','--state',str(state),'--out',str(out)]
            row=B.execute('api-'+cell.lower(),command,work);r['commands'].append(row);B.need(row['pass_'],'025 actual API process failed')
            audit=T.audit_probe(out,state,Path(proof['original_camera']))
            oldfiles=sorted(p.relative_to(old) for p in old.rglob('*') if p.is_file());newfiles=sorted(p.relative_to(out) for p in out.rglob('*') if p.is_file())
            B.need(oldfiles==newfiles,'025 SDK output coverage changed')
            changed=[str(name) for name in oldfiles if (old/name).read_bytes()!=(out/name).read_bytes()]
            B.need(changed==['pipelines/9.spv'],'025 unregistered SDK/API/pipeline difference')
            a=T.spirv(old/'pipelines/9.spv');b=T.spirv(out/'pipelines/9.spv')
            B.need(all(a[k]==b[k] for k in ('capabilities','extensions','local_size','descriptors')) and a['entry']['name']==b['entry']['name'] and a['entry']['model']==b['entry']['model'],'025 modified SPIR-V interface changed')
            pipeline=(out/'pipelines/9.spv').read_bytes()
            if first_pipeline is None:
                row=B.execute('changed-pipeline-validate',[str(B.V.B.VAL),'--target-env','vulkan1.2',str(out/'pipelines/9.spv')],work);r['commands'].append(row);B.need(row['pass_'],'025 patched SPIR-V invalid');first_pipeline=pipeline
            else:B.need(pipeline==first_pipeline,'025 patched shader differs across cameras')
            r['probes'].append(dict(cell=cell,source=str(old),actual_api_frames=65,changed_files=changed,unchanged_files=len(oldfiles)-1,audit=audit,patched_pipeline_sha256=B.SHA(out/'pipelines/9.spv')))
            r['input_sha256'].update(pins)
            for p in old.rglob('*'):
                if p.is_file():r['input_sha256'][str(p)]=B.SHA(p)
        old=B.ROOT/'research/lanes/lane-m-gi-competitiveness/results/138-nrd-native-vulkan-cpu-preparation.json';r['reused024contracts_receipt']=str(old);r['reused024contracts_receipt_sha256']=B.SHA(old);r['prior024contracts_rerun']=False
        B.rehash(r['input_sha256']);r.update(all_pass=True,actual_sdk_api_frames=195,changed_selected_pipeline_index=9,new_gpu_acquisitions=0)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    r.update(complete=True,python_checks=len(r['checks']),payload_sha256=B.inventory(work))
    with (work/'result.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    return r

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--build',type=Path,required=True);a=ap.parse_args();r=run(a.work,a.build.resolve());print(json.dumps({k:r.get(k) for k in ('all_pass','python_checks','actual_sdk_api_frames','error')}));raise SystemExit(0 if r['all_pass'] else 2)
