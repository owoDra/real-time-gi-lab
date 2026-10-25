"""035 physical raw candidate layouts and independent double extraction audit."""
import math
import numpy as np

PRIMARY=np.dtype([('t','<f8'),('tri','<u4'),('front','<u4')])
RESULT=np.dtype([('components','<f8',(3,3)),('primary',PRIMARY),('counts','<u8',4),('rng','<u8',4)])
VERTEX=np.dtype([(n,'<f8',3) for n in ('ray_origin','direction','hit_position','nudged','spawn','normal','reflected')]+[('t','<f8')]+[(n,'<u4') for n in ('triangle','kind','front','padding')])
PACKET=np.dtype([(n,'<f8',3) for n in ('receiver','normal','endpoint','endpoint_normal','radiance')]+[('pdf','<f8')]+[(n,'<u4') for n in ('status','sdk_m','trials','padding')])
SEEDS=tuple(x^0xa035a035a035a035 for x in (305419896,2596069104,81985529216486895,18364758544493064720))
TARGETS=tuple((c,d) for c in ('H01','H02','H03') for d in (2,8))


def need(ok,why):
    if not ok:raise ValueError('035 '+why)


def near(a,b):return np.isclose(a,b,rtol=1e-10,atol=1e-12)


def audit_records(original,observed,records,packets,vertices,offset,primary):
    n=len(original);depth=records.shape[1]
    need(original.dtype==observed.dtype==RESULT and packets.dtype==PACKET and records.dtype==VERTEX,'actual binary ABI')
    need(observed.tobytes()==original.tobytes(),'all components/primary/counters/RNG bit parity')
    need(original['primary'].tobytes()==primary.tobytes(),'unchanged frozen original primary records')
    components=original['components'];need(np.isfinite(components).all() and (components>=0).all() and (components[:,0]==0).all(),'finite unit-grey nonemissive components')
    kind=records['kind'];hit=kind==2;visited=kind!=0
    need(np.isin(kind,[0,1,2]).all() and (visited[:,0]).all(),'explicit camera query/slot status')
    need(np.array_equal(visited[:,1:],hit[:,:-1]),'complete unit-albedo path prefix stops exactly at miss/depth')
    need(records[~visited].tobytes()==bytes(int((~visited).sum())*192),'all unvisited slots exactly zero')
    need((records['padding']==0).all() and (packets['padding']==0).all(),'zero reserved fields')
    for field in ('ray_origin','direction','hit_position','nudged','spawn','normal','reflected','t'):need(np.isfinite(records[field]).all(),'finite full '+field)
    need((records['reflected']>=0).all() and (records['t']>=0).all(),'nonnegative reflected/t')
    miss=kind==1
    for field in ('hit_position','nudged','spawn','normal','reflected','t','triangle','front'):need((records[field][miss]==0).all(),'explicit miss zero fields '+field)
    need(near(np.linalg.norm(records['direction'][visited],axis=1),1).all(),'all visited ray directions unit')
    need(near(records['ray_origin'][:,1:][visited[:,1:]],records['spawn'][:,:-1][visited[:,1:]]).all(),'actual next ray starts at previous spawn')
    need(near(records['hit_position'][hit],(records['ray_origin']+records['direction']*records['t'][...,None])[hit]).all(),'actual unnudged ray endpoints')
    ids=records['triangle'][hit];need((ids<len(vertices)).all(),'all hit triangle identities')
    tris=vertices[ids];normal=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);normal/=np.linalg.norm(normal,axis=1)[:,None]
    front=(normal*records['direction'][hit]).sum(axis=1)<0;normal=np.where(front[:,None],normal,-normal)
    need(np.array_equal(records['front'][hit],front.astype(np.uint32)) and near(records['normal'][hit],normal).all(),'two-sided oriented normals/fronts')
    p=records['hit_position'][hit];minimum=np.full(len(p),np.inf);maximum=np.zeros(len(p))
    for i in range(3):
        a=tris[:,(i+1)%3];b=tris[:,(i+2)%3];edge=b-a;length=np.linalg.norm(edge,axis=1)
        minimum=np.minimum(minimum,np.linalg.norm(np.cross(edge,p-a),axis=1)/length);maximum=np.maximum(maximum,length)
    diagonal=np.linalg.norm(vertices.max(axis=(0,1))-vertices.min(axis=(0,1)));inset=1e-11*max(diagonal,1e-12)
    height=np.linalg.norm(np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]),axis=1)/maximum
    alpha=np.minimum(.5,3*inset/height);nudged=p+np.where((minimum<inset)[:,None],alpha[:,None]*(tris.mean(axis=1)-p),0)
    need(near(records['nudged'][hit],nudged).all() and near(records['spawn'][hit],nudged+normal*offset).all(),'independent nudge/spawn relationship')
    active=hit[:,0];secondary=hit[:,1];expected_status=np.where(~active,0,np.where(secondary,2,1)).astype(np.uint32)
    need(np.array_equal(packets['status'],expected_status) and (packets['sdk_m']==secondary).all() and (packets['trials']==1).all(),'official MISS M0 versus independent trial count')
    need(near(packets['receiver'],np.where(active[:,None],records['spawn'][:,0],0)).all() and near(packets['normal'],np.where(active[:,None],records['normal'][:,0],0)).all(),'proposal receiver is actual spawn')
    for packet,vertex in [('endpoint','hit_position'),('endpoint_normal','normal')]:need(near(packets[packet],np.where(secondary[:,None],records[vertex][:,1],0)).all(),'no fake miss endpoint/oriented hit '+packet)
    suffix=np.array([[math.fsum(map(float,records['reflected'][i,1:,c])) for c in range(3)] for i in range(n)])
    need(near(suffix,components[:,2]).all() and near(packets['radiance'],suffix).all(),'all finite-depth RGB suffixes equal original indirect')
    need(near(records['reflected'][:,0],components[:,1]).all(),'primary direct never included in suffix')
    cosine=(records['normal'][:,0]*records['direction'][:,1]).sum(axis=1)
    pdf=np.where(secondary,cosine/math.pi,0.)
    need(near(packets['pdf'],pdf).all() and (packets['pdf'][secondary]>0).all(),'actual source solid-angle PDF')
    recovered=np.zeros((n,3));scale=np.zeros(n);endpoint_cosine=np.zeros(n)
    delta=packets['endpoint'][secondary]-packets['receiver'][secondary];distance=np.linalg.norm(delta,axis=1);need((distance>0).all(),'finite positive secondary endpoint distance')
    direction=delta/distance[:,None];endpoint_cosine[secondary]=(direction*packets['normal'][secondary]).sum(axis=1)
    need(near(direction,records['direction'][:,1][secondary]).all(),'recorded ray and geometric receiver direction')
    scale[secondary]=endpoint_cosine[secondary]/(math.pi*packets['pdf'][secondary]);recovered[secondary]=packets['radiance'][secondary]*scale[secondary,None]
    need(near(scale[secondary],1).all() and near(recovered,components[:,2]).all(),'original sample BRDF/PDF cancellation')
    need(((packets['endpoint_normal'][secondary]*(-delta)).sum(axis=1)>0).all(),'secondary oriented hemisphere support')
    black=secondary&(suffix==0).all(axis=1);need((packets['sdk_m'][black]==1).all(),'black HIT retains M1')
    arrays=dict(status=expected_status,trial_count=packets['trials'],sdk_m=packets['sdk_m'],suffix=suffix,recovered=recovered,
                absolute_error=np.abs(recovered-components[:,2]),source_pdf=pdf,geometric_cosine=endpoint_cosine,recovery_scale=scale,visited=visited,hit=hit)
    summary=dict(paths=n,visited_slots=int(visited.sum()),hit_slots=int(hit.sum()),primary_invalid=int((~active).sum()),
                 secondary_misses=int((active&~secondary).sum()),secondary_hits=int(secondary.sum()),black_secondary_hits=int(black.sum()),
                 backfacing_hits=int((records['front'][hit]==0).sum()),max_absolute_recovery_error=float(np.max(arrays['absolute_error'])),
                 shadow_tests_original=int(original['counts'][:,1].sum()),shadow_tests_observed=int(observed['counts'][:,1].sum()))
    return arrays,summary
