#!/usr/bin/env python3
"""Freeze diagnostic changed states and acquire one named deterministic CPU direct control."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import struct
import subprocess

import numpy as np
import reference_step as R

WORK=R.ROOT/'out/research/lane-m-gi-competitiveness/m001-ddgi-dynamic-inputs-v1'
KINDS=('light','geometry')


def derive(geometry,frame,kind):
    R.require(kind in KINDS,'unregistered dynamic state')
    g,f=bytearray(geometry),bytearray(frame)
    R.require(len(f)==148 and f[:12]==b'N007-STATE1\0','frame contract')
    version,count=struct.unpack_from('<II',g)
    R.require(version==1 and count==1224 and len(g)==8+52*count,'original H01 geometry required')
    def shift(raw,offset,delta):struct.pack_into('<f',raw,offset,struct.unpack_from('<f',raw,offset)[0]+delta)
    if kind=='light':shift(f,20+80,.137)
    else:
        for j in range(count):
            for v in range(3):shift(g,8+j*52+v*12,.127)
    return bytes(g),bytes(f)


def committed():
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R.ROOT,text=True).strip();p=Path(__file__).resolve()
    R.require(subprocess.check_output(['git','show',commit+':'+str(p.relative_to(R.ROOT))],cwd=R.ROOT)==p.read_bytes(),'commit dynamic factory first')
    return commit


def prepare():
    R.require(not WORK.exists(),'existing diagnostic state work; never overwrite')
    state,audit,inputs=R.preflight('H01',2);commit=committed()
    source=R.LANE/'capture/M001-H01-hwrt';g=(source/'geometry-state.bin').read_bytes();f=(source/'frame-state.bin').read_bytes()
    WORK.mkdir(parents=True)
    rows=[]
    for kind in KINDS:
        directory=WORK/kind;directory.mkdir();geometry,frame=derive(g,f,kind)
        (directory/'geometry-state.bin').write_bytes(geometry);(directory/'frame-state.bin').write_bytes(frame)
        derived=R.Q.L.read_state(directory);scenes=[]
        for depth in (2,8):
            scene=R.Q.scene_for_state(derived,depth);path=directory/f'T_B{depth}.n008';path.write_text(scene.text())
            scenes.append({'vertices':depth,'path':path.name,'sha256':R.sha(path),'f64_geometry_sha256':scene.geometry_sha256()})
        rows.append({'kind':kind,'state_sha256':derived['sha256'],'physical_scenes':scenes,'holdout':False,'indirect_reference_eligible':False})
    inputs.update({str(p):R.sha(p) for p in (Path(__file__).resolve(),R.BINARY,R.NET)})
    d={'schema':'m001-ddgi-dynamic-state-lock/1','source_commit':commit,'source_state_sha256':state['sha256'],
       'input_sha256':inputs,'source_physical_audit':audit,'rows':rows,'gpu_executed':False,'oracle_executed':False,
       'scope':'Derived009 tuning/diagnostic state bytes only; never new heldouts or indirect physical references'}
    R.write_new(WORK/'manifest.json',d);return audit_states()


def audit_states():
    manifest=R.read(WORK/'manifest.json');source=R.LANE/'capture/M001-H01-hwrt'
    R.require(manifest['source_state_sha256']==R.CAPTURE_SHA['H01'],'source state differs')
    for p,h in manifest['input_sha256'].items():R.require(R.sha(Path(p))==h,'dynamic factory/physical proof input drift')
    g=(source/'geometry-state.bin').read_bytes();f=(source/'frame-state.bin').read_bytes()
    for row in manifest['rows']:
        kind=row['kind'];directory=WORK/kind;geometry,frame=derive(g,f,kind)
        R.require((directory/'geometry-state.bin').read_bytes()==geometry and (directory/'frame-state.bin').read_bytes()==frame,'derived state differs from exact registered byte transform')
        state=R.Q.L.read_state(directory);R.require(state['sha256']==row['state_sha256'],'target state hashes differ')
        for record in row['physical_scenes']:
            scene=R.Q.scene_for_state(state,record['vertices']);p=directory/record['path']
            R.require(p.read_text()==scene.text() and R.sha(p)==record['sha256'] and scene.geometry_sha256()==record['f64_geometry_sha256'],'derived physical camera/geometry differs')
    return {'state_lock_sha256':R.sha(WORK/'manifest.json'),'all_pass':True,'gpu_executed':False,'rows':manifest['rows']}


def oracle(kind):
    R.require(kind in KINDS,'unregistered CPU direct control');R.preflight('H01',2);states=audit_states();commit=committed()
    work=WORK/kind/'cpu-direct-v1';R.require(not work.exists(),'existing deterministic direct output/partial; no retry');work.mkdir()
    scene=WORK/kind/'T_B2.n008'
    cmd=[str(R.BINARY),'--net',str(R.NET),'--scene',str(scene),'--out',str(work/'oracle'),'--seeds','305419896','--spp','1','--threads','1']
    d={'schema':'m001-ddgi-deterministic-direct-control/1','source_commit':commit,'command':cmd,'kind':kind,'complete':False,
       'gpu_executed':False,'indirect_reference_eligible':False,'quality_admission':False,'input_sha256':{str(p):R.sha(p) for p in (R.BINARY,R.NET,scene,WORK/'manifest.json',Path(__file__).resolve())},'physical_proof':states}
    R.write_new(work/'started.json',d)
    def limits():resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    try:
        p=subprocess.run(cmd,cwd=R.ROOT,capture_output=True,text=True,timeout=180,preexec_fn=limits)
        (work/'oracle.stdout.txt').write_text(p.stdout);(work/'oracle.stderr.txt').write_text(p.stderr);d['returncode']=p.returncode
        R.require(p.returncode==0,'CPU direct control failed; retain partial')
        meta=json.loads(p.stdout);R.require(meta['spp']==1 and meta['seeds']==[305419896] and meta['scene_sha256']==R.sha(scene),'CPU direct identity differs')
        values=R.Q.L.read_sidecar(work/'oracle.s0.f64')['mean'];direct=values[...,R.Q.L.COMPONENTS.index('direct'),:]
        R.require(np.isfinite(direct).all() and float(np.max(direct))>0,'nonfinite/zero deterministic direct control')
        d.update(complete=True,classification='DETERMINISTIC_DIRECT_CONTROL_ONLY_INDIRECT_INELIGIBLE',metadata=meta)
    except subprocess.TimeoutExpired as error:
        for key,raw in [('stdout',error.stdout),('stderr',error.stderr)]:
            (work/('oracle.'+key+'.txt')).write_bytes(raw if isinstance(raw,bytes) else (raw or '').encode())
        d['error']='CPU180s timeout; no retry'
    except Exception as error:d['error']=str(error)
    d['payload_sha256']={p.name:R.sha(p) for p in sorted(work.iterdir()) if p.is_file()}
    R.write_new(work/'result.json',d);return audit_oracle(kind)


def audit_oracle(kind):
    audit_states();work=WORK/kind/'cpu-direct-v1';d=R.read(work/'result.json')
    R.require(d['complete'] and d['returncode']==0 and d['indirect_reference_eligible'] is False,'CPU direct incomplete or falsely admitted')
    for p,h in d['input_sha256'].items():R.require(R.sha(Path(p))==h,'CPU direct input drift')
    for name,h in d['payload_sha256'].items():R.require(R.sha(work/name)==h,'CPU direct raw drift')
    expected={'started.json','oracle.stdout.txt','oracle.stderr.txt','oracle.hits'}|{'oracle.s0.'+s for s in R.SUFFIXES}
    R.require(set(d['payload_sha256'])==expected,'CPU direct incomplete inventory')
    values=R.Q.L.read_sidecar(work/'oracle.s0.f64')['mean'];image=R.Q.L.read_pfm(work/'oracle.s0.direct.pfm')
    direct=values[...,R.Q.L.COMPONENTS.index('direct'),:]
    R.require(np.isfinite(values).all() and np.array_equal(image,direct.astype(np.float32)),'CPU deterministic direct PFM/f64 mismatch')
    return {'kind':kind,'complete':True,'all_pass':True,'result_sha256':R.sha(work/'result.json'),
            'raw_payloads_rehashed':len(d['payload_sha256']),'direct_nonzero_pixels':int(np.count_nonzero(direct[...,0])),
            'direct_max':float(direct.max()),'indirect_reference_eligible':False,'gpu_executed':False}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('action',choices=('prepare','audit','oracle','audit-oracle'));ap.add_argument('--kind',choices=KINDS);args=ap.parse_args()
    if args.action in ('oracle','audit-oracle'):R.require(args.kind is not None,'name one CPU target')
    print(json.dumps(prepare() if args.action=='prepare' else audit_states() if args.action=='audit' else oracle(args.kind) if args.action=='oracle' else audit_oracle(args.kind),indent=2))
