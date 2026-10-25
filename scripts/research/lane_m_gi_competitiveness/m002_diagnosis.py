#!/usr/bin/env python3
"""048 CPU diagnosis of the M002 PTR failures from saved images/references only."""
import json
import math
from pathlib import Path
import sys
import numpy as np
import m002_bridge as MB
import m002_states as M
import closest_primary_metrics as CM
import geometry_barrier_filter as B
import surface_quadratic_filter as S

T=MB.T;Q=T.Q
sys.path.insert(0,str(MB.ROOT/"scripts/research/n008_hdr_oracle"));import n008lib as L
ROOT,BASE=MB.ROOT,MB.BASE
OUT=ROOT/'research/lanes/lane-m-gi-competitiveness/results/266-m002-ptr-failure-diagnosis.json'
FAILING={('S4',2),('S4',8),('S1L',2),('S1L',8),('S3L',2),('S3L',8)}


def need(ok,why):
    if not ok:raise ValueError('048 '+why)


def oracle_hits(path,state):
    raw=Path(path).read_bytes();need(raw[:8]==b'N008HIT\0','oracle primary ABI')
    oracle=np.frombuffer(raw,dtype=CM.ORACLE_DTYPE,offset=16);need(oracle.shape==(57600,),'oracle primary size')
    gpu=np.zeros(57600,dtype=CM.GPU_DTYPE);hit=oracle['tri']!=CM.INVALID
    gpu['t']=np.inf;gpu['prim']=gpu['mat']=gpu['inst']=CM.INVALID
    tri=oracle['tri'][hit];v=state['verts'][tri].astype(np.float32)
    n=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);n/=np.linalg.norm(n,axis=1,keepdims=True)
    gpu['n'][hit]=n;gpu['t'][hit]=oracle['t'][hit].astype(np.float32)
    meta=state['meta'];gpu['prim'][hit]=meta[tri,0];gpu['mat'][hit]=meta[tri,1];gpu['inst'][hit]=meta[tri,2];gpu['flag'][hit]=1
    return gpu,oracle


def geometry(gpu,state):
    """geometry_filter_cpu.geometry on an in-memory 022 hit record."""
    hit=gpu['flag']==1
    x,y=np.meshgrid(np.arange(320,dtype=np.float32),np.arange(180,dtype=np.float32))
    nx=np.float32(2)*((x+np.float32(.5))/np.float32(320))-np.float32(1)
    ny=np.float32(1)-np.float32(2)*((y+np.float32(.5))/np.float32(180))
    direction=(state['camera_forward_far'][:3]+state['camera_right_tan_x'][:3]*(nx*state['camera_right_tan_x'][3])[...,None]
               +state['camera_up_tan_y'][:3]*(ny*state['camera_up_tan_y'][3])[...,None])
    direction/=np.linalg.norm(direction,axis=2,keepdims=True);direction=direction.reshape(-1,3)
    position=np.zeros((57600,3));position[hit]=(state['camera_pos_near'][:3]+direction[hit]*gpu['t'][hit,None]).astype(np.float64)
    normal=np.zeros_like(position);normal[hit]=gpu['n'][hit].astype(float);normal[hit]/=np.linalg.norm(normal[hit],axis=1,keepdims=True)
    flip=hit&((normal*direction).sum(axis=1)>0);normal[flip]*=-1
    diagonal=float(np.linalg.norm(state['verts'].max(axis=(0,1))-state['verts'].min(axis=(0,1))));epsilon=1e-5*max(1.,diagonal)
    return position.reshape(180,320,3),normal.reshape(180,320,3),hit.reshape(180,320),gpu['mat'].reshape(180,320),epsilon


def operator(gpu,state):
    pos,normal,hit,material,eps=geometry(gpu,state);masks=B.geometry_masks(pos,normal,hit,material,eps)
    coefficients,maps=S.fit(pos,normal,hit,masks);return coefficients,maps,masks,hit


def linear(image,coefficients):
    x=np.asarray(image,float).reshape(180,320)
    for stride,c in zip(B.STRIDES,coefficients):
        y=np.zeros_like(x)
        for cj,(dy,dx,_) in zip(c,B.OFFSETS):y+=cj*B.shifted(x,dy*stride,dx*stride)
        x=y
    return x


def clipped(image,coefficients):return S.reconstruct(np.asarray(image,float).reshape(180,320),coefficients)[0][-1]


def nrmse(img,ref):
    e=np.asarray(img,float).ravel()-ref.ravel();return math.sqrt(float(np.mean(e*e)))/math.sqrt(float(np.mean(ref*ref)))


def gain(coefficients):
    """Exact per-pixel sum of squared composed weights via spaced impulses (support < 32 px)."""
    g=np.zeros((180,320))
    for oy in range(32):
        for ox in range(32):
            d=np.zeros((180,320));d[oy::32,ox::32]=1.;r=linear(d,coefficients)
            # each output pixel sees at most one impulse within its support: accumulate r^2 from each grid
            g+=r*r
    return g


def control():
    rows=[]
    for cell in ('H01','H02','H03'):
        for depth in (2,8):
            root=BASE/f'm001-integrated022-gpu-{cell.lower()}-b{depth}-v1';plan=json.loads((root/'plan.json').read_text());proof=plan['proof']
            state=L.read_state(Path(proof['primary_capture']))
            archived=np.fromfile(root/'capture/hits.u32','<u4').reshape(57600,8).copy().view(CM.GPU_DTYPE).reshape(-1)
            built,oracle=oracle_hits(Path(proof['reference']['directory'])/'o.n16384.hits',state)
            prim,_=CM.primary(archived,oracle,state['meta'],state['verts'],float(state['camera_forward_far'][3]))
            coefficients,_,_,_=operator(built,state)
            sources=np.fromfile(root/'capture/sources.f32','<f4').reshape(180,320);stages=np.fromfile(root/'capture/stages.f32','<f4').reshape(3,180,320)
            out=clipped(sources,coefficients);final=stages[-1].astype(float)
            rel=math.sqrt(float(np.mean((out-final)**2)))/math.sqrt(float(np.mean(final*final)))
            rows.append(dict(cell=cell,depth=depth,primitive_mismatches=int(prim['primitive_mismatches']),final_stage_relative_nrmse=rel,
                             pass_=prim['primitive_mismatches']==0 and rel<=1e-3))
            print('control',cell,depth,rows[-1],flush=True)
    return dict(rows=rows,pass_=all(r['pass_'] for r in rows))


def light_distance(state):
    light=state['light_pos_interval'][:3].astype(float);v=state['verts']
    # point-triangle distance (exact, vectorized Ericson closest point)
    a,b,c=v[:,0],v[:,1],v[:,2];p=light[None]
    ab,ac,ap=b-a,c-a,p-a;d1=(ab*ap).sum(1);d2=(ac*ap).sum(1)
    n=np.cross(ab,ac);nn=(n*n).sum(1);t=((ap*n).sum(1))/nn;proj=p-t[:,None]*n
    # barycentric test of projection; fall back to edge distances
    def seg(p0,p1):
        d=p1-p0;s=np.clip(((p-p0)*d).sum(1)/np.maximum((d*d).sum(1),1e-30),0,1);q=p0+s[:,None]*d;return np.linalg.norm(p-q,axis=1)
    w=proj-a;d00=(ab*ab).sum(1);d01=(ab*ac).sum(1);d11=(ac*ac).sum(1);d20=(w*ab).sum(1);d21=(w*ac).sum(1);den=d00*d11-d01*d01
    bv=(d11*d20-d01*d21)/den;bw=(d00*d21-d01*d20)/den;inside=(bv>=0)&(bw>=0)&(bv+bw<=1)
    dist=np.minimum(np.minimum(seg(a,b),seg(b,c)),seg(c,a));dist[inside]=np.abs(t[inside])*np.sqrt(nn[inside])
    return float(dist.min())


def target(cell,depth):
    ref,directory,q=MB.reference(cell,depth);state=L.read_state(M.OUT/cell);level=q['levels'][-1]['spp']
    gpu,_=oracle_hits(directory/f'o.n{level}.hits',state);coefficients,maps,masks,hit=operator(gpu,state)
    r_ind,r_tot=ref['indirect'].reshape(180,320).astype(float),ref['total'].reshape(180,320).astype(float)
    row=dict(cell=cell,depth=depth,failing=(cell,depth) in FAILING,reference_spp=level)
    ob=clipped(r_ind,coefficients);row['operator_bias']=dict(indirect_nrmse=nrmse(ob,r_ind),signed_bias=float((ob-r_ind).sum()/r_ind.sum()))
    g=gain(coefficients);row['noise_gain']=dict(mean=float(g[hit].mean()),fraction_ge_1=float((g[hit]>=1).mean()),median=float(np.median(g[hit])))
    caps=MB.CAPTURES/f'{cell.lower()}-b{depth}';images={}
    for d in sorted(caps.iterdir()):
        role,spp=d.name.rsplit('-',1);images[(role,int(spp))]=np.fromfile(d/'capture/image.f32','<f4').reshape(180,320,2)[...,1].astype(float)
    pt=sorted(s for r,s in images if r=='PT_REF');row['pt_rungs']=pt;row['ratio']={};row['clip_bias']={};row['replica_ptr']={}
    for n in pt:
        e=images[('PT_REF',n)]-r_ind;row['ratio'][n]=float((linear(e,coefficients)**2).sum()/(e*e).sum())
        lin=linear(images[('PT_REF',n)],coefficients);op=clipped(images[('PT_REF',n)],coefficients)
        row['clip_bias'][n]=float((op-lin).sum()/r_ind.sum());row['replica_ptr'][n]=dict(indirect_nrmse=nrmse(op,r_ind),signed_bias=float((op-r_ind).sum()/r_ind.sum()),
                                                                                       raw_pt_indirect_nrmse=nrmse(images[('PT_REF',n)],r_ind))
    saved={s:dict(nrmse=nrmse(images[('PTR',s)],r_ind),signed_sum_bias=float((images[('PTR',s)]-r_ind).sum()/r_ind.sum())) for r,s in images if r=='PTR'}
    row['saved_ptr_indirect']=saved
    n64=max(s for s in pt if s<=64);op=clipped(images[('PT_REF',n64)],coefficients);err=(op-r_ind)**2;total=float(err.sum())
    model=maps['model'][0];taps=masks[2].sum(axis=0)
    row['attribution']=dict(rung=n64,by_model={name:dict(error_share=float(err[model==k].sum()/total),pixel_share=float((model==k).mean())) for k,name in ((0,'quadratic'),(1,'affine'),(2,'constant'),(255,'miss'))},
                           by_stage2_taps={name:dict(error_share=float(err[hit&m].sum()/total),pixel_share=float((hit&m).mean())) for name,m in (('le8',taps<=8),('9to16',(taps>=9)&(taps<=16)),('ge17',taps>=17))})
    if 1024 in pt:
        e=((images[('PT_REF',1024)]-r_ind)**2).ravel();k=max(1,int(round(.001*e.size)));row['heavy_tail_top0p1_share']=float(np.sort(e)[-k:].sum()/e.sum())
    x=np.log([n for n in pt]);y=np.log([row['replica_ptr'][n]['raw_pt_indirect_nrmse'] for n in pt]);row['pt_loglog_slope']=float(np.polyfit(x,y,1)[0])
    row['descriptors']=dict(indirect_over_total_rms=math.sqrt(float(np.mean(r_ind**2)))/math.sqrt(float(np.mean(r_tot**2))),light_nearest_triangle_distance=light_distance(state),
                            light_soft_radius=float(state['light_pos_interval'][3]),hit_fraction=float(hit.mean()))
    ab=row['operator_bias'];r64=row['ratio'][n64];cb=row['clip_bias'].get(64,row['clip_bias'][n64])
    row['labels']=[name for name,ok in (('BIAS_FLOOR',ab['indirect_nrmse']>.05 or abs(ab['signed_bias'])>.025),('NO_VARIANCE_REDUCTION',r64>.25),
                                        ('CLIP_BIAS',cb>.025),('HEAVY_TAIL',row.get('heavy_tail_top0p1_share',0)>.25)) if ok]
    print(cell,depth,row['labels'],json.dumps(dict(ob=ab,r=row['ratio'],clip=row['clip_bias'],g=row['noise_gain'])),flush=True)
    return row


def main():
    need(not OUT.exists(),'one diagnosis record');head=Q.git('rev-parse','HEAD')
    rec=dict(schema='m002-ptr-diagnosis/1',source_commit=head,registration='048',complete=False)
    rec['control']=control()
    if not rec['control']['pass_']:rec.update(classification='CONTROL_FAIL',complete=True)
    else:
        rec['targets']=[target(c,d) for c,d in MB.targets() if MB.reference(c,d)[0] is not None];rec.update(classification='DIAGNOSIS_COMPLETE',complete=True)
    OUT.write_text(json.dumps(rec,indent=1)+'\n');print(rec['classification'])


if __name__=='__main__':main()
