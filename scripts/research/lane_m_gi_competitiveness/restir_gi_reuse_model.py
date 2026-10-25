"""042 independent CPU replay of receiver-frame SDK ReSTIR GI reuse.

Integer RNG, z-curve, offsets, addresses and frame transforms are replayed
exactly in uint32/float32; continuous values in float64. Near-boundary
decisions (042a) may be flipped only to explain an observed GPU divergence.
"""
import itertools
import json
from pathlib import Path
import subprocess
import numpy as np
import restir_gi_device_model as D
import restir_gi_unit_model as M

F=np.float32;U32=np.uint32
W,H=320,180;N=W*H;ROW=((W+15)//16)*256;PITCH=ROW*((H+15)//16)
SURFACE=np.dtype([('origin','<f4',3),('depth','<f4'),('normal','<f4',3),('primitive','<u4'),('valid','<u4'),('pad','<u4',3)])
CANDIDATE=M.CANDIDATE;PACKED=D.PACKED
QUERY=np.dtype([('origin','<f8',3),('direction','<f8',3),('tmax','<f8'),('ignore','<u4'),('pad','<u4')])
LUMA=np.array([.2126,.7152,.0722]);MARGIN=1e-5;UNIT=64.0
VARIANTS=('null','m0');RECORD=(0,1,63);STREAMS=4;FRAMES=64
TEMPORAL_PASS,SPATIAL_PASS=12,13


def need(ok,why):
    if not ok:raise ValueError('042 '+why)


def bits(a):return np.ascontiguousarray(a).view(U32)
def pointer(x,y,array=0):
    x=np.asarray(x,np.int64);y=np.asarray(y,np.int64)
    return array*PITCH+(y//16)*ROW+(x//16)*256+(y%16)*16+x%16
def jenkins(a):
    with np.errstate(over='ignore'):return D.jenkins(np.asarray(a,U32))
def producer_seed(stream,frame):return (((0x0a420000+64*stream+frame)*0x9e3779b1)&0xffffffff)^0xa042a042


class Rng:
    """RTXDI_InitRandomSampler / murmur3 / GetNextRandom."""
    def __init__(self,x,y,frame,pass_):
        z=D.spread(np.asarray(x,U32))|(D.spread(np.asarray(y,U32))<<U32(1))
        with np.errstate(over='ignore'):self.seed=(jenkins(z)+U32(frame&0xffffffff)+U32(pass_*31)).astype(U32)
        self.index=np.ones(len(z),U32)
    def next(self,mask=None):
        with np.errstate(over='ignore'):
            k=self.index*U32(0xcc9e2d51);k=((k<<U32(15))|(k>>U32(17)))*U32(0x1b873593);h=self.seed^k
            h=((h<<U32(13))|(h>>U32(19)))*U32(5)+U32(0xe6546b64);h=h^U32(4);h=h^(h>>U32(16));h=h*U32(0x85ebca6b);h=h^(h>>U32(13));h=h*U32(0xc2b2ae35);h=h^(h>>U32(16))
        self.index=self.index+(U32(1) if mask is None else np.asarray(mask,U32))
        return ((h&U32(0x7fffff)).astype(F)/F(8388608)).astype(F)


def temporal_offset(i,radius):
    i=np.asarray(i,np.int64)&7;m2=(i>>1)&1;m4=1-((i>>2)&1);t0=-1+2*(i&1);t1=1-2*m2;t2=m4|m2;t3=m4|(1-m2)
    return t0*t2*radius,t0*t1*t3*radius
def permute(x,y,u):
    ox,oy=int(u)&3,(int(u)>>2)&3
    return ((x+ox)^3)-ox,((y+oy)^3)-oy
def mirror(x,y):
    out=[]
    for p,s in ((np.asarray(x,np.int64),W),(np.asarray(y,np.int64),H)):
        period=2*s;p=np.fmod(np.fmod(p,period)+period,period);out.append(np.minimum(p,period-1-p))
    return out


def encode_normal(n):
    n=np.asarray(n,F).reshape(-1,3)
    with np.errstate(divide='ignore',invalid='ignore'):p=n[:,:2]*(F(1)/np.abs(n).sum(axis=1,dtype=F))[:,None]
    folded=np.stack(((F(1)-np.abs(p[:,1]))*np.where(p[:,0]>=0,F(1),F(-1)),(F(1)-np.abs(p[:,0]))*np.where(p[:,1]>=0,F(1),F(-1))),axis=1)
    p=np.where((n[:,2]<0)[:,None],folded,p);p=np.where(np.isnan(p).any(axis=1)[:,None],F(0),np.clip(p,F(-1),F(1)))
    iv=np.rint(p*F(32767)).astype(np.int64)
    return ((iv[:,0]&0xffff)|((iv[:,1]&0xffff)<<16)).astype(U32)
def snorm_close(a,b):
    a=np.asarray(a,U32);b=np.asarray(b,U32);lo=lambda c:(c&0xffff).astype(np.uint16).astype(np.int16).astype(np.int64);hi=lambda c:(c>>16).astype(np.uint16).astype(np.int16).astype(np.int64)
    return (np.abs(lo(a)-lo(b))<=1)&(np.abs(hi(a)-hi(b))<=1)


class Bank:
    """One reservoir array and its owner records; loads convert owner->receiver frame."""
    def __init__(self,reservoirs,owners):
        need(reservoirs.dtype==PACKED and reservoirs.shape==(PITCH,) and owners.shape==(PITCH,4),'reservoir bank ABI');self.r=reservoirs;self.o=owners
    def load(self,ptr,receiver):
        raw=self.r[ptr];shift=(self.o[ptr,:3]-receiver).astype(F);position=(shift+raw['position']).astype(F)
        rgb=D.decode(raw['radiance']);misc=raw['misc']
        return dict(pos=position,M=(misc&0xff).astype(np.int64),age=((misc>>8)&0xff).astype(np.int64),w=raw['weight'].astype(float),
                    lum=rgb.astype(float)@LUMA,nrm=M.decode_normal(raw['normal']),code=raw['radiance'],ncode=raw['normal'],
                    zero=(raw['weight']==0)|((raw['radiance']>>U32(18))==0))


def take(r,mask,other):
    return {k:np.where(mask.reshape(mask.shape+(1,)*(np.ndim(v)-1)),v,other[k]) for k,v in r.items()}


def neighbor_ok(n0,n1,d0,d1,normal=.6,depth=.1):
    dot=(n0.astype(float)*n1).sum(axis=-1);diff=np.abs(d0.astype(float)-d1);limit=depth*np.maximum(d0,d1).astype(float)
    ok=(dot>=normal)&(diff<=limit);near=(np.abs(dot-normal)<=MARGIN*normal)|(np.abs(diff-limit)<=MARGIN*np.maximum(limit,1e-30))
    return ok,near


def target(pos,lum,nrm,receiver,normal,valid=True):
    d=(pos-receiver).astype(F).astype(float);d2=(d*d).sum(axis=-1);facing=(nrm.astype(float)*(-d)).sum(axis=-1)
    ok=valid&(lum>0)&(d2>0)&(facing>0)
    with np.errstate(divide='ignore',invalid='ignore'):cos=np.maximum(0,(normal.astype(float)*d).sum(axis=-1)/np.sqrt(d2))
    return np.where(ok,lum*np.nan_to_num(cos)/np.pi,0.)


def jacobian(receiver,other,pos,nrm):
    def part(r):
        v=r.astype(float)-pos.astype(float);d2=(v*v).sum(axis=-1)
        with np.errstate(divide='ignore',invalid='ignore'):c=np.clip((nrm.astype(float)*v).sum(axis=-1)/np.sqrt(d2),0,1)
        return d2,c
    nd,nc=part(receiver);od,oc=part(other)
    with np.errstate(divide='ignore',invalid='ignore'):j=(nc*od)/(oc*nd)
    return np.where(np.isfinite(j),j,0.)


def validate(j,zero):
    ok=zero|((j<=10)&(j>=.1));near=~zero&((np.abs(j-10)<=MARGIN*10)|(np.abs(j-.1)<=MARGIN*.1))
    return ok,np.where(zero,1.,np.clip(j,1/3,3)),near


def forced(decision,force,name):
    if force is None or name not in force:return decision
    f=force[name];return np.where(f<0,decision,f==1)


class Visibility:
    """Memoized independent brute-force visibility; unknown queries are collected and traced in batches."""
    def __init__(self,tool,geometry,work,epsilon,triangles):
        self.tool,self.geometry,self.work,self.epsilon,self.triangles=tool,geometry,Path(work),float(epsilon),triangles
        self.memo={};self.pending={};self.batches=[];self.queries=0
    def __call__(self,viewer,receiver,point,mask):
        """viewer: surface records (world origin, primitive); point in receiver frame. Returns (visible, unstable, known)."""
        n=len(mask);visible=np.ones(n,bool);unstable=np.zeros(n,bool);known=np.ones(n,bool)
        rel=(viewer['origin']-receiver).astype(F);d=(point-rel).astype(F);dd=d.astype(float);dist=np.sqrt((dd*dd).sum(axis=-1))
        tmax=dist*(1-1e-3)-self.epsilon;trace=mask&(dist>0)&(tmax>0)
        keys=[(tuple(bits(viewer['origin'][j]).tolist()),int(viewer['primitive'][j]),tuple(bits(d[j]).tolist())) for j in np.flatnonzero(trace)]
        for j,key in zip(np.flatnonzero(trace),keys):
            if key in self.memo:visible[j],unstable[j]=self.memo[key]
            else:
                known[j]=False
                if key not in self.pending:self.pending[key]=(viewer['origin'][j].astype(float),dd[j]/dist[j],tmax[j],int(viewer['primitive'][j]))
        return visible,unstable,known
    def flush(self):
        if not self.pending:return 0
        keys=list(self.pending);q=np.zeros(len(keys),QUERY)
        for j,k in enumerate(keys):o,d,t,i=self.pending[k];q['origin'][j]=o;q['direction'][j]=d;q['tmax'][j]=t;q['ignore'][j]=i
        index=len(self.batches);qp=self.work/f'visibility-{index}.queries';rp=self.work/f'visibility-{index}.result'
        with qp.open('xb') as f:f.write(q.tobytes())
        run=subprocess.run([str(self.tool),'--triangles',str(self.geometry),'--queries',str(qp),'--out',str(rp)],capture_output=True,text=True)
        need(run.returncode==0 and json.loads(run.stdout)=={'queries':len(keys),'triangles':self.triangles},'independent visibility tool')
        r=np.fromfile(rp,np.uint8);need(len(r)==len(keys),'visibility result ABI')
        for k,v in zip(keys,r):self.memo[k]=(not bool(v&4),bool(v&1)!=bool(v&2))
        self.batches.append(dict(queries=len(keys),occluded=int(((r&4)!=0).sum()),unstable=int(((r&1)!=((r>>1)&1)).sum())));self.queries+=len(keys);self.pending={}
        return len(keys)


class Frame:
    """All saved arrays of one full-record frame."""
    def __init__(self,folder,controls,frame_index,uniform):
        f=Path(folder);self.folder=f;self.frame_index=frame_index;self.uniform=uniform;self.controls=controls
        load=lambda name,dtype,shape:np.fromfile(f/name,dtype).reshape(shape)
        self.cand=load('candidates.bin',CANDIDATE,(N,));self.local=load('local-endpoints.f32','<f4',(N,4));self.hits=load('hits.u32','<u4',(N,8))
        self.image=load('producer-image.f32','<f4',(N,4));self.frame=load('frame-image.f32','<f4',(N,4))
        self.reservoirs=load('reservoirs.bin',PACKED,(6,PITCH));self.owners=load('owners.f32','<f4',(6,PITCH,4))
        surfaces=load('surfaces.bin',SURFACE,(2*N,));self.cur=surfaces[:N];self.after=surfaces[N:]
        self.prev=load('previous-surfaces.bin',SURFACE,(N,));self.shading=load('shading.f32','<f4',(2,N,2,4))
        self.diagnostics=load('diagnostics.u32','<u4',(3,2,N));self.counters=load('counters.u32','<u4',(8,))
        self.history={v:Bank(load(f'history-reservoirs-{v}.bin',PACKED,(PITCH,)),load(f'history-owners-{v}.bin','<f4',(PITCH,4))) for v in VARIANTS}
    def bank(self,variant,stage):
        if stage=='history':return self.history[VARIANTS[variant]]
        a=variant*3+{'initial':0,'temporal':1,'spatial':2}[stage];return Bank(self.reservoirs[a],self.owners[a])


def check_initial(fr):
    """Exact surfaces, initial reservoirs/owners and image inputs for both variants."""
    c=fr.cand;status=bits(c['normal_status'][:,3]);valid=status!=0;hit=status==2;miss=status==1
    need(np.isin(status,[0,1,2]).all(),'candidate status')
    s=fr.cur;need((s['valid']==valid.astype(U32)).all() and (s['pad']==0).all(),'surface validity')
    need(np.array_equal(bits(s['origin'][valid]),bits(c['origin_pdf'][valid,:3])) and np.array_equal(bits(s['normal'][valid]),bits(c['normal_status'][valid,:3])),'exact surface origin/normal')
    need(np.array_equal(s['primitive'][valid],bits(c['endpoint_normal'][valid,3])),'surface primitive')
    k=fr.controls;depth=((c['primary_direct'][:,:3].astype(float)-k['camera'])*k['forward']).sum(axis=1)
    need(np.allclose(s['depth'][valid],depth[valid],rtol=1e-6,atol=1e-6),'surface linear depth')
    need(s[~valid].tobytes()==bytes(int((~valid).sum())*SURFACE.itemsize),'invalid surface bytes zero')
    need(np.array_equal(bits(fr.frame[:,0]),bits(c['primary_direct'][:,3])) and np.array_equal(bits(fr.frame[:,1]),bits(fr.image[:,1])),'frame direct/PT inputs')
    need(np.array_equal(fr.after.tobytes(),fr.cur.tobytes()),'previous-surface copy')
    x,y=np.arange(N)%W,np.arange(N)//W;rows=[]
    for v in range(2):
        r=fr.reservoirs[v*3][pointer(x,y)];o=fr.owners[v*3][pointer(x,y)]
        need(np.array_equal(bits(o[valid,:3]),bits(s['origin'][valid])) and (o[valid,3]==0).all() and (o[~valid]==0).all(),'initial owner records')
        need(np.array_equal(bits(r['position'][hit]),bits(fr.local[hit,:3])) and (r['misc'][hit]==1).all(),'HIT position/M/age')
        need(np.allclose(r['weight'][hit],1/c['origin_pdf'][hit,3].astype(float),rtol=1e-6,atol=0),'HIT inverse PDF')
        li=c['radiance_trial'][hit,:3].astype(float);dec=D.decode(r['radiance'][hit]).astype(float)/UNIT
        need((np.abs(dec-li)<=.02*np.maximum(li,1e-6)).all(),'HIT radiance within041 decoded gate')
        need(snorm_close(r['normal'][hit],encode_normal(c['endpoint_normal'][hit,:3])).all(),'HIT normal code')
        nul=miss if v==0 else np.zeros(N,bool)
        need(np.array_equal(bits(r['position'][nul]),bits(c['normal_status'][nul,:3])) and (r['misc'][nul]==0x10001).all() and (r['weight'][nul]==0).all() and (r['radiance'][nul]==0).all(),'V1 explicit null trial')
        need(snorm_close(r['normal'][nul],encode_normal(-c['normal_status'][nul,:3])).all(),'null placeholder normal')
        empty=~hit&~nul;need(r[empty].tobytes()==bytes(int(empty.sum())*PACKED.itemsize) and (r['unused']==0).all(),'empty reservoirs')
        rows.append(dict(variant=VARIANTS[v],hits=int(hit.sum()),null_trials=int(nul.sum()),empty=int(empty.sum())))
    need((fr.diagnostics&0xff).max()==0 and fr.counters[0]==0,'no shader error flags')
    return rows,valid


def temporal(fr,v,P,vis,force=None):
    x,y=P%W,P//W;s=fr.cur[P];recv=s['origin'];zero=np.zeros_like(recv);n=len(P);near={}
    inp=fr.bank(v,'initial').load(pointer(x,y),recv);hist=fr.bank(v,'history');rng=Rng(x,y,fr.frame_index,TEMPORAL_PASS)
    start=(rng.next()*F(8)).astype(np.int64);search=np.ones(n,bool);found=np.zeros(n,bool);tx=np.zeros(n,np.int64);ty=np.zeros(n,np.int64)
    for i in range(6):
        fallback=i==5
        if i==0:qx,qy=x,y
        elif fallback:qx,qy=permute(x,y,fr.uniform)
        else:ox,oy=temporal_offset(start+i,1);qx,qy=x+ox,y+oy
        inside=(qx>=0)&(qx<W)&(qy>=0)&(qy<H);cx,cy=np.clip(qx,0,W-1),np.clip(qy,0,H-1)
        ts=fr.prev[cy*W+cx];ok=search&inside&(ts['valid']!=0)
        if not fallback:
            nb,nn=neighbor_ok(s['normal'],ts['normal'],s['depth'],ts['depth'],.6,.1);name=f't-neighbor-{i}';near[name]=ok&nn;ok=ok&forced(nb,force,name)
        ok=ok&((hist.r['misc'][pointer(cx,cy)]&0xff)!=0)
        found|=ok;tx=np.where(ok,cx,tx);ty=np.where(ok,cy,ty);search&=~ok
    valid_input=inp['M']!=0;tp_in=target(inp['pos'],inp['lum'],inp['nrm'],zero,s['normal'])
    count=np.where(valid_input,inp['M'],0);wsum=np.where(valid_input,tp_in*inp['w']*inp['M'],0.);selected_target=np.where(valid_input,tp_in,0.)
    ts=fr.prev[ty*W+tx];tr=hist.load(pointer(tx,ty),recv);trel=(ts['origin']-recv).astype(F)
    ok,jc,jn=validate(jacobian(zero,trel,tr['pos'],tr['nrm']),tr['zero']);near['t-validate']=found&jn;found=found&forced(ok,force,'t-validate')
    tm=np.minimum(tr['M'],8);tage=tr['age']+1;found&=tage<=30
    tp=target(tr['pos'],tr['lum'],tr['nrm'],zero,s['normal']);risk=tp*tr['w']*jc*tm
    wsum=np.where(found,wsum+risk,wsum);count=np.where(found,count+tm,count)
    r=rng.next(found).astype(float);lhs=r*wsum;pick=found&(lhs<=risk);near['t-select']=found&(np.abs(lhs-risk)<=MARGIN*np.maximum(lhs,risk))
    pick=found&forced(pick,force,'t-select');selected_target=np.where(pick,tp,selected_target)
    chosen=take(dict(tr,age=tage),pick,inp)
    pi=selected_target.copy();pisum=selected_target*inp['M'];active=(count!=0)&found
    tq=target(chosen['pos'],chosen['lum'],chosen['nrm'],trel,ts['normal'],ts['valid']!=0);trace=active&(tq>0)
    visible,unstable,known=vis(ts,recv,chosen['pos'],trace);near['t-visibility']=trace&unstable;visible=forced(visible,force,'t-visibility')
    tq=np.where(trace&~visible,0.,tq);pi=np.where(active&pick,tq,pi);pisum=np.where(active,pisum+tq*tm,pisum)
    den=pisum*selected_target;weight=np.where(den==0,0.,wsum*pi/np.where(den==0,1,den))
    return dict(M=count,age=np.where(count!=0,chosen['age'],0),pos=np.where((count!=0)[:,None],chosen['pos'],F(0)),W=weight,code=np.where(count!=0,chosen['code'],0),
                ncode=np.where(count!=0,chosen['ncode'],0),known=known,near=near,source=np.where(pick,1,np.where(valid_input,0,-1)))


def spatial(fr,v,P,vis,offsets,force=None):
    x,y=P%W,P//W;s=fr.cur[P];recv=s['origin'];zero=np.zeros_like(recv);n=len(P);near={}
    bank=fr.bank(v,'temporal');inp=bank.load(pointer(x,y),recv);rng=Rng(x,y,fr.frame_index,SPATIAL_PASS)
    valid_input=inp['M']!=0;tp_in=target(inp['pos'],inp['lum'],inp['nrm'],zero,s['normal'])
    count=np.where(valid_input,inp['M'],0);wsum=np.where(valid_input,tp_in*inp['w']*inp['M'],0.);selected_target=np.where(valid_input,tp_in,0.)
    chosen=dict(inp);source=np.where(valid_input,0,-1);start=(rng.next()*F(8191)).astype(np.int64);used=[]
    for i in range(2):
        o=offsets[(start+i)&8191];dx=(o[:,0]*F(32)).astype(np.int64);dy=(o[:,1]*F(32)).astype(np.int64);qx,qy=mirror(x+dx,y+dy)
        ns=fr.cur[qy*W+qx];nb,nn=neighbor_ok(s['normal'],ns['normal'],s['depth'],ns['depth'],.6,.1);near[f's-neighbor-{i}']=nn;ok=forced(nb,force,f's-neighbor-{i}')
        nr=bank.load(pointer(qx,qy),recv);ok&=nr['M']!=0;nrel=(ns['origin']-recv).astype(F)
        j=jacobian(zero,nrel,nr['pos'],nr['nrm']);tp=target(nr['pos'],nr['lum'],nr['nrm'],zero,s['normal'])
        vok,jc,jn=validate(j,nr['zero']);near[f's-validate-{i}']=ok&jn;ok=ok&forced(vok,force,f's-validate-{i}')
        risk=tp*jc*nr['w']*nr['M'];count=np.where(ok,count+nr['M'],count);wsum=np.where(ok,wsum+risk,wsum)
        r=rng.next(ok).astype(float);lhs=r*wsum;pick=ok&(lhs<=risk);near[f's-select-{i}']=ok&(np.abs(lhs-risk)<=MARGIN*np.maximum(lhs,risk))
        pick=ok&forced(pick,force,f's-select-{i}');selected_target=np.where(pick,tp,selected_target);chosen=take(nr,pick,chosen);source=np.where(pick,i+1,source)
        used.append((ok,ns,nrel,nr['M']))
    pi=selected_target.copy();pisum=selected_target*inp['M'];known=np.ones(n,bool)
    for i,(ok,ns,nrel,nm) in enumerate(used):
        ps=target(chosen['pos'],chosen['lum'],chosen['nrm'],nrel,ns['normal'],ns['valid']!=0);trace=ok&(ps>0)
        visible,unstable,k=vis(ns,recv,chosen['pos'],trace);known&=k;near[f's-visibility-{i}']=trace&unstable;visible=forced(visible,force,f's-visibility-{i}')
        ps=np.where(trace&~visible,0.,ps);pi=np.where(ok&(source==i+1),ps,pi);pisum=np.where(ok,pisum+ps*nm,pisum)
    den=selected_target*pisum;weight=np.where(den==0,0.,wsum*pi/np.where(den==0,1,den))
    return dict(M=count,age=np.where(count!=0,chosen['age'],0),pos=np.where((count!=0)[:,None],chosen['pos'],F(0)),W=weight,code=np.where(count!=0,chosen['code'],0),
                ncode=np.where(count!=0,chosen['ncode'],0),known=known,near=near,source=source)


def agree(expected,raw):
    """Per-pixel agreement of a replayed reservoir with the GPU-stored packed reservoir."""
    m=(raw['misc']&0xff).astype(np.int64);age=((raw['misc']>>8)&0xff).astype(np.int64)
    position=(bits(raw['position'])==bits(expected['pos'])).all(axis=1);count=m==np.minimum(expected['M'],255);ages=age==np.minimum(expected['age'],255)
    weight=np.isclose(raw['weight'].astype(float),expected['W'],rtol=1e-4,atol=1e-6)
    gpu=D.decode(raw['radiance']).astype(float)/UNIT;ref=D.decode(np.asarray(expected['code'],U32)).astype(float)/UNIT
    radiance=(np.abs(gpu-ref)<=.02*np.maximum(ref,1e-6)).all(axis=1)
    normal=np.where(expected['M']!=0,snorm_close(raw['normal'],encode_normal(M.decode_normal(np.asarray(expected['ncode'],U32)))),raw['normal']==0)
    reserved=((raw['misc']>>16)==0)&(raw['unused']==0)
    fields=dict(position=position,M=count,age=ages,weight=weight,radiance=radiance,normal=normal,reserved=reserved)
    return np.logical_and.reduce(list(fields.values())),fields


def resolve(stage,args,vis,P,raw):
    """Replay with CPU decisions; explain each disagreement only by flipping its near-boundary decisions."""
    for _ in range(3):
        e=stage(*args,P,vis)
        if e['known'].all():break
        vis.flush()
    need(e['known'].all(),'visibility memo complete')
    ok,fields=agree(e,raw);bad=np.flatnonzero(~ok);explained=[];unexplained=[]
    for j in bad:
        names=[k for k,m in e['near'].items() if m[j]]
        hit=None
        if names and len(names)<=8:
            combos=[c for c in itertools.product((0,1),repeat=len(names))]
            Q=np.repeat(P[j:j+1],len(combos));force={k:np.array([c[a] for c in combos],np.int8) for a,k in enumerate(names)}
            for _ in range(3):
                t=stage(*args,Q,vis,force=force)
                if t['known'].all():break
                vis.flush()
            if t['known'].all():
                rr=np.repeat(raw[j:j+1],len(combos));good,_=agree(t,rr)
                if good.any():hit=dict(pixel=int(P[j]),near=names,forced=dict(zip(names,map(int,combos[int(np.flatnonzero(good)[0])]))),matching_combinations=int(good.sum()))
        (explained if hit else unexplained).append(hit or dict(pixel=int(P[j]),near=names,failed=[k for k,v in fields.items() if not v[j]]))
    return e,ok,explained,unexplained


def shade(fr,v,P,vis):
    x,y=P%W,P//W;s=fr.cur[P];recv=s['origin'];r=fr.bank(v,'spatial').load(pointer(x,y),recv)
    d=r['pos'].astype(float);d2=(d*d).sum(axis=1);active=(r['M']!=0)&(d2>0)
    with np.errstate(divide='ignore',invalid='ignore'):cos=np.where(active,np.maximum(0,(s['normal'].astype(float)*d).sum(axis=1)/np.sqrt(d2)),0.)
    hemi=active&((r['nrm'].astype(float)*(-d)).sum(axis=1)>0)
    for _ in range(2):
        visible,unstable,known=vis(s,recv,r['pos'],active)
        if known.all():break
        vis.flush()
    need(known.all(),'shading visibility memo')
    base=r['lum']/UNIT*(cos/np.pi)*r['w'];indirect=np.where(hemi&visible,base,0.)
    return dict(base=base,indirect=indirect,M=r['M'],W=r['w'],cos=cos,hemi=hemi,visible=np.where(active,visible,False),unstable=active&unstable,age=r['age'],active=active)


def check_shading(fr,v,P,e):
    g=fr.shading[v][P];ind=g[:,0,0].astype(float)
    need((g[:,0,1]==e['M']).all() and (g[:,1,2]==e['age']).all() and np.array_equal(g[:,0,2].astype(float),e['W']) and (g[:,1,3]==0).all(),'shading M/W/age records')
    need(np.allclose(g[:,0,3],e['cos'],rtol=1e-4,atol=1e-6) and np.array_equal(g[:,1,0]==1,e['hemi']),'shading cosine/hemisphere')
    gv=g[:,1,1]==1;mismatch=(gv!=e['visible'])&e['active'];need(not (mismatch&~e['unstable']).any(),'stable final visibility verdict')
    need(np.array_equal(gv&~e['active'],np.zeros(len(P),bool)),'no traced visibility for inactive reservoirs')
    verdict=np.where(mismatch,gv,e['visible']);expected=np.where(e['hemi']&verdict,e['base'],0.)
    need(np.allclose(ind,expected,rtol=1e-4,atol=1e-7),'final indirect')
    need(np.array_equal(bits(fr.frame[P,2+v]),bits(g[:,0,0])),'frame image carries shaded indirect')
    return dict(active=int(e['active'].sum()),visible=int((gv&e['active']).sum()),unstable=int(e['unstable'].sum()),explained_visibility=int(mismatch.sum()))


def audit_frame(fr,tool,geometry,triangles,work,offsets):
    """Complete replay of one full-record frame, both variants; returns summary and complete arrays."""
    rows,valid=check_initial(fr);P=np.flatnonzero(valid);vis=Visibility(tool,geometry,work,fr.controls['epsilon'],triangles);summary=dict(initial=rows,valid_pixels=len(P),variants=[]);arrays={}
    need(fr.frame_index%4096!=0 or fr.prev.tobytes()==bytes(N*SURFACE.itemsize),'frame0 previous surfaces empty')
    need(fr.frame_index%4096==0 or fr.prev.tobytes()==fr.cur.tobytes(),'static previous surfaces exact')
    for v in range(2):
        row=dict(variant=VARIANTS[v])
        for name,stage,args,array in (('temporal',temporal,(fr,v),1),('spatial',spatial,(fr,v),2)):
            raw=fr.reservoirs[v*3+array][pointer(P%W,P//W)];e,ok,explained,unexplained=resolve(stage if name=='temporal' else (lambda f,vv,Q,vi,force=None:spatial(f,vv,Q,vi,offsets,force)),args,vis,P,raw)
            owners=fr.owners[v*3+array][pointer(P%W,P//W)];need(np.array_equal(bits(owners[:,:3]),bits(fr.cur['origin'][P])) and (owners[:,3]==0).all(),name+' owner records')
            rest=np.setdiff1d(np.arange(N),P);need(fr.reservoirs[v*3+array][pointer(rest%W,rest//W)].tobytes()==bytes(len(rest)*PACKED.itemsize),name+' invalid pixels empty')
            need((fr.diagnostics[array-1,v]&0xff).max()==0,name+' error flags')
            limit=.001*len(P);row[name]=dict(pixels=len(P),agree=int(ok.sum()),explained=len(explained),unexplained=len(unexplained),explained_records=explained,unexplained_records=unexplained[:64],
                sources=dict(zip(*map(lambda a:a.tolist(),np.unique(e['source'],return_counts=True)))),visibility_queries=vis.queries)
            need(not unexplained,f'{name} unexplained replay divergence');need(len(explained)<=limit,f'{name} explained divergences above0.1%')
            arrays[f'{VARIANTS[v]}-{name}-agree']=ok;arrays[f'{VARIANTS[v]}-{name}-weight']=e['W'];arrays[f'{VARIANTS[v]}-{name}-source']=e['source']
        e=shade(fr,v,P,vis);row['shading']=check_shading(fr,v,P,e);need((fr.diagnostics[2,v]&0xff).max()==0,'shading error flags')
        need(row['shading']['explained_visibility']<=.001*len(P),'shading visibility divergences above0.1%')
        rest=np.setdiff1d(np.arange(N),P);need((fr.shading[v][rest]==0).all() and (fr.frame[rest,2+v]==0).all(),'invalid pixels unshaded')
        arrays[f'{VARIANTS[v]}-indirect']=e['indirect'];summary['variants'].append(row)
    summary['visibility_batches']=vis.batches;summary['visibility_queries']=vis.queries
    return summary,arrays
