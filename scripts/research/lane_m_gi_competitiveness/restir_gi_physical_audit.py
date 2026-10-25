#!/usr/bin/env python3
"""035 full-record independent extraction audit; no new rays or HDR quality scoring."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import restir_gi_physical_process as P
import restir_gi_physical_model as M
import anchor_process_limits as C

B=P.B


def run(path):
    path=path.resolve();native=B.read(path);root=P.canonical(native['cell'],native['depth']);out=Path(str(root)+'-audit')
    M.need(path==root/'result.json' and not out.exists(),'canonical exclusive independent audit');head=P.committed()
    out.mkdir();pins={str(path):B.SHA(path)};C.write(out/'inputs-before.json',dict(native_receipt=str(path),native_receipt_sha256=B.SHA(path)))
    r=dict(schema='m001-restir035-full-record-audit/1',source_commit=head,cell=native['cell'],depth=native['depth'],complete=False,all_pass=False,
           classification='INVALID_STOP_NO_RETRY',input_sha256=pins,native_receipt=str(path),native_receipt_sha256=B.SHA(path),gpu_executed=False,
           independent_full_ray_retracing=False,hdr_quality_scored=False,accepted_timing=False,rows=[])
    try:
        r['effective_parent_limits']=C.limits();M.need(native['complete'] and native['all_pass'] and native['source_commit']==head,'complete same-source acquisition')
        B.rehash(native['input_sha256']);pins.update(native['input_sha256'])
        M.need(B.inventory(root)==native['payload_sha256'],'complete unchanged native inventory')
        payload={str(root/k):v for k,v in native['payload_sha256'].items()};B.rehash(payload);pins.update(payload)
        geometry=Path(native['info']['geometry']);vertices=np.fromfile(geometry/'vertices.f64','<f8').reshape(-1,3,3);primary=np.fromfile(geometry/'primary.bin',M.PRIMARY)
        M.need(len(primary)==57600 and native['native']['vertex_stride']==192 and native['native']['packet_stride']==144 and native['native']['result_stride']==152,'exact frozen/full ABI')
        depth=native['depth'];offset=native['native']['offset']
        for seed in range(4):
            folder=root/'paths'/f'seed-{seed}';original=np.fromfile(folder/'original.bin',M.RESULT);observed=np.fromfile(folder/'observed.bin',M.RESULT)
            records=np.fromfile(folder/'vertices.bin',M.VERTEX).reshape(57600,depth);packets=np.fromfile(folder/'packets.bin',M.PACKET)
            M.need(original.shape==observed.shape==packets.shape==(57600,),'complete per-pixel records')
            arrays,summary=M.audit_records(original,observed,records,packets,vertices,offset,primary)
            with (out/f'seed-{seed}-full-recovery.npz').open('xb') as f:np.savez_compressed(f,**arrays)
            r['rows'].append(dict(seed=M.SEEDS[seed],all_pass=True,**summary));print('035 seed',seed,'FULL_RECORD_PASS',flush=True)
        B.rehash(pins);r.update(complete=True,all_pass=True,classification='CPU_PHYSICAL_CANDIDATE_CASE_PASS',paths_per_role=230400,allocated_vertex_slots=230400*depth)
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    r['payload_sha256']=B.inventory(out);C.write(out/'result.json',r)
    print(json.dumps({k:r.get(k) for k in ('complete','all_pass','classification','error')}),flush=True);return 0 if r['all_pass'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',type=Path,required=True);args=parser.parse_args();sys.exit(run(args.receipt))
