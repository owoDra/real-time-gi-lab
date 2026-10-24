#!/usr/bin/env python3
"""027 supplemental static pointer/read relevance; no image or metric rerun."""
import argparse
import json
import struct
import subprocess
import unittest
from pathlib import Path
import numpy as np
import nrd_semantics_audit as A
B=A.B
OWN=[Path(__file__).resolve(),A.PROTOCOL]

def reads(instructions,root,target,constants):
    """Conservative member-pointer traversal; whole-block reads count as live."""
    paths={root:None};loads=[];target_accesses=0
    for op,a in instructions:
        if op in (65,66):
            if a[2] in paths:
                path=paths[a[2]]
                if path is None:
                    A.need(len(a)>=4 and a[3] in constants,'dynamic/unknown uniform member index')
                    path=constants[a[3]]
                paths[a[1]]=path
                target_accesses+=path==target
        elif op==83 and a[2] in paths:paths[a[1]]=paths[a[2]]
        elif op==61 and a[2] in paths:loads.append(paths[a[2]])
        elif op in (62,63,64):
            A.need(not any(k in paths for k in a[:2]),'unexpected write/copy uniform pointer')
        elif op in (57,67,70,121,122,123,124,169,245):
            A.need(not any(k in paths for k in a[2:]),'unsupported escaped uniform pointer')
    return dict(target_member_accesses=target_accesses,target_member_loads=sum(x==target for x in loads),whole_block_loads=sum(x is None for x in loads),total_member_loads=len(loads),no_target_reads=not any(x is None or x==target for x in loads))

def analyze(raw,target='gLuminanceEdgeStoppingRelaxation'):
    A.need(len(raw)>=20 and len(raw)%4==0,'SPIR-V size');w=struct.unpack('<'+'I'*(len(raw)//4),raw);A.need(w[0]==0x07230203,'SPIR-V magic')
    at=5;instructions=[];decs={};vars={};pointers={};member_names={};constants={}
    while at<len(w):
        n=w[at]>>16;op=w[at]&65535;A.need(n>0 and at+n<=len(w),'SPIR-V instruction bounds');a=list(w[at+1:at+n]);instructions.append((op,a))
        if op==71:decs.setdefault(a[0],{})[a[1]]=a[2:]
        elif op==59:vars[a[1]]=(a[0],a[2])
        elif op==32:pointers[a[0]]=(a[1],a[2])
        elif op==6:member_names[(a[0],a[1])]=struct.pack('<'+'I'*len(a[2:]),*a[2:]).split(b'\0')[0].decode()
        elif op==43 and len(a)==3:constants[a[1]]=a[2]
        at+=n
    for op,a in instructions:
        if len(a)>=2 and a[0] in pointers:
            A.need(op in (59,65,66,83),'unsupported pointer-producing opcode '+str(op))
    candidates=[k for k in vars if decs.get(k,{}).get(34)==[1] and decs.get(k,{}).get(33)==[2]];A.need(len(candidates)==1,'one constant root')
    root=candidates[0];A.need(vars[root][1]==2,'uniform storage');block=pointers[vars[root][0]][1]
    matches=[i for (b,i),name in member_names.items() if b==block and name==target]
    if not matches:return dict(declared=False,target_member_accesses=0,target_member_loads=0,whole_block_loads=0,total_member_loads=0,no_target_reads=True)
    A.need(len(matches)==1,'one named constant member')
    return dict(declared=True,member_index=matches[0],**reads(instructions,root,matches[0],constants))

class Controls(unittest.TestCase):
    def test_declared_without_load(self):self.assertTrue(reads([],10,3,{20:3})['no_target_reads'])
    def test_direct_field_load_detected(self):
        r=reads([(65,[1,30,10,20]),(61,[2,40,30])],10,3,{20:3});self.assertEqual(r['target_member_loads'],1);self.assertFalse(r['no_target_reads'])
    def test_other_field_is_not_target(self):self.assertTrue(reads([(65,[1,30,10,20]),(61,[2,40,30])],10,3,{20:4})['no_target_reads'])
    def test_whole_block_is_conservatively_live(self):self.assertFalse(reads([(61,[2,40,10])],10,3,{})['no_target_reads'])
    def test_pointer_copy_followed(self):self.assertFalse(reads([(83,[1,11,10]),(65,[1,30,11,20]),(61,[2,40,30])],10,3,{20:3})['no_target_reads'])
    def test_dynamic_member_rejected(self):
        with self.assertRaises(ValueError):reads([(65,[1,30,10,99])],10,3,{20:3})
    def test_pointer_escape_rejected(self):
        with self.assertRaises(ValueError):reads([(57,[1,30,50,10])],10,3,{})
    def test_invalid_binary_rejected(self):
        with self.assertRaises(ValueError):analyze(bytes(24))

def execute(out,contracts,parent):
    head=A.committed()
    for p in OWN:A.need(subprocess.check_output(['git','show',head+':'+str(p.relative_to(A.ROOT))],cwd=A.ROOT)==p.read_bytes(),'commit027 relevance source before execution')
    out=A.bounds(out);out.mkdir();r=dict(schema='m001-nrd027-supplemental-static-relevance/1',source_commit=head,complete=False,all_pass=False,gpu_executed=False,quality_impact_experiment_run=False,original_metric_or_geometry_audit_rerun=False,input_sha256={str(p):B.SHA(p) for p in OWN})
    try:
        if not contracts:
            suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
            with (out/'contracts.log').open('x') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
            r.update(complete=True,all_pass=result.wasSuccessful(),actual_python_tests=suite.countTestCases())
        else:
            c=B.read(contracts);A.need(c['complete'] and c['all_pass'] and c['source_commit']==head,'027 relevance qualified source');B.rehash(c['input_sha256'])
            parent=parent.resolve();p=B.read(parent);A.need(p['complete'] and p['valid'] and p['all_pass'] and len(p['rows'])==24,'027 complete parent semantic audit');B.rehash(p['input_sha256'])
            r['input_sha256'][str(contracts)]=B.SHA(contracts);r['input_sha256'][str(parent)]=B.SHA(parent)
            first=A.BASE/'m001-nrd026-gpu-h01-b2-n1-v1/capture';rows=[]
            for j in range(15):
                path=first/f'pipelines/{j}.spv';A.need(B.SHA(path)==p['pipeline_reflections']['pipeline_sha256'][j],'027 canonical binary identity');r['input_sha256'][str(path)]=B.SHA(path)
                target=analyze(path.read_bytes());positive=analyze(path.read_bytes(),'gDiffPhiLuminance');rows.append(dict(pipeline=j,target=target,diffuse_phi_positive_control=positive))
            A.need(all(x['target']['no_target_reads'] for x in rows),'027 disputed field is actually read; do not infer irrelevance')
            A.need(sum(x['diffuse_phi_positive_control']['target_member_loads'] for x in rows)>0,'027 actual positive scalar-read control')
            maps=[]
            for g in p['geometry']:
                path=parent.parent/(g['cell'].lower()+'-full-geometry-errors.npz');A.need(B.SHA(path)==p['payload_sha256'][path.name],'027 full geometry map identity');r['input_sha256'][str(path)]=B.SHA(path)
                with np.load(path) as arrays:
                    active=arrays['active_primary'];fields={}
                    for name in arrays.files:
                        v=arrays[name]
                        if v.dtype.kind=='f':
                            bad=~np.isfinite(v);A.need(not bad[active].any(),'027 nonfinite actual-hit geometry map');fields[name]=int(bad.sum())
                maps.append(dict(cell=g['cell'],all_hit_domain_values_finite=True,nonfinite_entries_by_field=fields,nonfinite_entries_outside_primary_hit_domain_only=True))
            r.update(complete=True,all_pass=True,selected_pipelines=15,pipeline_identity_coverage_captures=24,declared_common_field_pipelines=sum(x['target']['declared'] for x in rows),actual_disputed_field_loads=sum(x['target']['target_member_loads']+x['target']['whole_block_loads'] for x in rows),actual_diffuse_phi_loads=sum(x['diffuse_phi_positive_control']['target_member_loads'] for x in rows),disputed_field_irrelevant_to_selected_diffuse_binaries=True,does_not_explain026_quality_losses=True,rows=rows,geometry_map_domain_checks=maps,geometry_warnings_explanation='Original primary-miss t is nonfinite. Full maps retain nonfinite camera-relative/projection diagnostics only outside explicit primary-hit domain; all actual-hit values are finite. Original HDR scoring still includes every pixel.')
    except Exception as e:r['error']=type(e).__name__+': '+str(e)
    B.rehash(r['input_sha256']);r['payload_sha256']=B.inventory(out);B.write(out/'result.json',r);print(json.dumps({k:r.get(k) for k in ('complete','all_pass','error','actual_python_tests','actual_disputed_field_loads','actual_diffuse_phi_loads')}));return r

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--contracts',type=Path);ap.add_argument('--parent',type=Path);args=ap.parse_args()
    result=execute(args.out,args.contracts,args.parent);raise SystemExit(0 if result['all_pass'] else 2)
