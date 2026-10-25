"""041 full local physical audit, with ONE fixed64 SDK radiance unit."""
import numpy as np
import restir_gi_device_model as D

F=np.float32;U=np.uint32;PI=F(np.pi)
WITNESS=np.dtype([(k,'<f4',4) for k in ('origin_t','direction_direct','position_primitive','normal_kind','spawn_front')])
CANDIDATE=np.dtype([(k,'<f4',4) for k in ('origin_pdf','normal_status','endpoint_primitive','endpoint_normal','radiance_trial','direction_cosine','primary_direct')]+[('flags','<u4',4)])
SEEDS=tuple((s&0xffffffff)^0xa040a040 for s in (305419896,2596069104,81985529216486895,18364758544493064720))
TARGETS=tuple((c,b) for c in ('H01','H02','H03') for b in (2,8))


def need(ok,why):
    if not ok:raise ValueError('037 '+why)


def near(a,b,rtol=3e-4,atol=3e-6):return np.isclose(a,b,rtol=rtol,atol=atol)
def bits(a):return np.ascontiguousarray(a).view(U)
def norm(a):return a/np.linalg.norm(a,axis=-1)[...,None]


def spawn(position,normal):
    p=np.array(position,F);n=np.asarray(normal,F);delta=(F(4)*n).astype(np.int32)
    shifted=(p.view(np.int32)+np.where(p<0,-delta,delta)).astype(np.int32).view(F)
    return np.where(np.abs(p)<F(1/32),p+n*F(1e-7),shifted)


def mix32(value):
    x=np.array(value,U)
    with np.errstate(over='ignore'):
        x^=x>>16;x*=U(0x7feb352d);x^=x>>15;x*=U(0x846ca68b);x^=x>>16
    return x


def direction(normal,rng):
    with np.errstate(over='ignore'):
        rng=rng+U(0x9e3779b9);u=((mix32(rng)>>8).astype(F)+F(.5))/F(16777216)
        rng=rng+U(0x9e3779b9);angle=F(2)*PI*((mix32(rng)>>8).astype(F)+F(.5))/F(16777216)
    helper=np.where((np.abs(normal[:,2])<F(.999))[:,None],np.array([0,0,1],F),np.array([0,1,0],F))
    tangent=norm(np.cross(helper,normal));bitangent=np.cross(normal,tangent)
    wi=norm(np.sqrt(u)[:,None]*(np.cos(angle)[:,None]*tangent+np.sin(angle)[:,None]*bitangent)+np.sqrt(F(1)-u)[:,None]*normal)
    return wi,rng


def decode_normal(code):
    code=np.asarray(code,U);lo=(code&65535).astype(np.int16).astype(F);hi=(code>>16).astype(np.int16).astype(F)
    xy=np.maximum(np.stack((lo,hi),axis=-1)/F(32767),F(-1));z=F(1)-np.abs(xy).sum(axis=-1)
    folded=(F(1)-np.abs(xy[:,::-1]))*np.where(xy>=0,F(1),F(-1))
    return norm(np.concatenate((np.where((z<0)[:,None],folded,xy),z[:,None]),axis=-1))


def audit(original,observed,original_hits,observed_hits,original_source,observed_source,w,c,packed,output,triangles,params,seed,metadata,local_endpoint):
    n=len(original);depth=w.shape[1]
    need(w.dtype==WITNESS and c.dtype==CANDIDATE and packed.dtype==D.PACKED,'binary ABI')
    need(original.shape==observed.shape==(n,4) and original_hits.shape==observed_hits.shape==(n,8) and original_source.shape==observed_source.shape==(n,) and c.shape==packed.shape==(n,) and output.shape==(n,6,4),'full array shapes')
    for a,b in ((original,observed),(original_hits,observed_hits),(original_source,observed_source)):need(a.tobytes()==b.tobytes(),'bit-exact paired PT/primary/source')
    need(np.isfinite(original).all() and (original>=0).all() and (original[:,3]==1).all() and np.array_equal(original[:,1],original_source),'finite original image/source')
    need(np.array_equal(original[:,2],original[:,0]+original[:,1]),'primary direct exactly once')
    kind=bits(w['normal_kind'][...,3]);hit=kind==2;visited=kind!=0;miss=kind==1
    need(np.isin(kind,[0,1,2]).all() and visited[:,0].all() and np.array_equal(visited[:,1:],hit[:,:-1]),'complete finite path prefix')
    need(w[~visited].tobytes()==bytes(int((~visited).sum())*WITNESS.itemsize),'all unvisited bytes zero')
    for field in ('origin_t','direction_direct','normal_kind','spawn_front'):need(np.isfinite(w[field]).all(),'finite witness '+field)
    need(np.isfinite(w['position_primitive'][...,:3]).all(),'finite endpoints')
    need((w['origin_t'][...,3]>=0).all() and (w['direction_direct'][...,3]>=0).all(),'nonnegative distance/direct')
    for field in ('origin_t','direction_direct'):need((w[field][miss,3]==0).all(),'MISS scalar zero')
    need((w['position_primitive'][miss,:3]==0).all() and (bits(w['position_primitive'][...,3])[miss]==0xffffffff).all(),'MISS no fake endpoint')
    need((w['normal_kind'][miss,:3]==0).all() and (w['spawn_front'][miss]==0).all(),'MISS normal/spawn zero')
    rays=w['direction_direct'][...,:3];origins=w['origin_t'][...,:3];positions=w['position_primitive'][...,:3];normals=w['normal_kind'][...,:3];spawns=w['spawn_front'][...,:3]
    need(near(np.linalg.norm(rays[visited],axis=1),1).all(),'unit query directions')
    need(np.array_equal(origins[:,1:][visited[:,1:]],spawns[:,:-1][visited[:,1:]]),'actual ray chain spawn')
    endpoint_error=np.zeros((n,depth,3));endpoint_error[hit]=positions[hit].astype(float)-(origins.astype(float)+rays.astype(float)*w['origin_t'][...,3,None])[hit]
    need(near(positions[hit],(origins.astype(float)+rays.astype(float)*w['origin_t'][...,3,None])[hit]).all(),'float32 hit endpoint/ray consistency')
    primitive=bits(w['position_primitive'][...,3])[hit];need((primitive<len(triangles)).all(),'actual primitive indices')
    tri=triangles[primitive].astype(float);a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0];geometric=norm(np.cross(a,b))
    front=(geometric*rays[hit]).sum(axis=1)<=0
    need(np.array_equal(bits(w['spawn_front'][...,3])[hit],front.astype(U)) and near(normals[hit],np.where(front[:,None],geometric,-geometric)).all(),'two-sided geometric normal/front')
    delta=positions[hit].astype(float)-tri[:,0];aa=(a*a).sum(axis=1);bb=(b*b).sum(axis=1);ab=(a*b).sum(axis=1);da=(delta*a).sum(axis=1);db=(delta*b).sum(axis=1)
    denominator=aa*bb-ab*ab;u=(da*bb-db*ab)/denominator;v=(db*aa-da*ab)/denominator
    need((u>=-3e-4).all() and (v>=-3e-4).all() and (u+v<=1+3e-4).all() and near(positions[hit],tri[:,0]+u[:,None]*a+v[:,None]*b).all(),'all hits belong to actual triangle')
    need(np.array_equal(spawns[hit],spawn(positions[hit],normals[hit])),'exact four-step float32 spawn')
    # Reconstruct original center camera rays and every actual RNG continuation.
    pf=np.frombuffer(params,F,count=24).reshape(6,4);pu=np.frombuffer(params,U,count=8,offset=96).reshape(2,4)
    width=int(pu[0,1]);height=int(pu[0,2]);need(width*height==n,'viewport')
    y,x=np.divmod(np.arange(n),width);nx=F(2)*(x.astype(F)+F(.5))/F(width)-F(1);ny=F(1)-F(2)*(y.astype(F)+F(.5))/F(height)
    view=norm(pf[3,:3]+nx[:,None]*pf[1,3]*pf[1,:3]+ny[:,None]*pf[2,3]*pf[2,:3])
    need(near(rays[:,0],view).all() and np.array_equal(origins[:,0],np.broadcast_to(pf[0,:3],(n,3))),'original camera center rays')
    rng=mix32(U(seed)^mix32(np.arange(n,dtype=U)));rng=np.where(hit[:,0],rng,U(0))
    for vertex in range(1,depth):
        mask=visited[:,vertex];expected,next_rng=direction(normals[:,vertex-1][mask],rng[mask]);rng[mask]=next_rng
        need(near(rays[:,vertex][mask],expected).all(),'actual original continuation RNG/direction')
    need(np.array_equal(c['flags'][:,0],rng) and (c['flags'][:,1:]==0).all(),'complete RNG state/zero flags')
    lv=pf[5,:3].astype(float)-spawns[hit].astype(float);d2=(lv*lv).sum(axis=1);cos=np.maximum(0,(normals[hit]*norm(lv)).sum(axis=1));s=float(pf[5,3]);upper=cos*s*s/(np.pi*(s*s+d2));direct=w['direction_direct'][...,3]
    need(((direct[hit]==0)|near(direct[hit],upper)).all(),'all reflected direct values have original NEE physical scale (visibility not independently retraced)')
    suffix=np.zeros(n,F)
    for vertex in range(1,depth):suffix=suffix+direct[:,vertex]
    need(np.array_equal(suffix,original[:,1]) and np.array_equal(direct[:,0],original[:,0]),'all finite suffixes and separate primary direct')
    primary=hit[:,0];secondary=hit[:,1];status=np.where(~primary,0,np.where(secondary,2,1)).astype(U)
    need(np.array_equal(original_hits[:,7],primary.astype(U)) and np.array_equal(original_hits[primary,:3],bits(normals[:,0])[primary]) and np.array_equal(original_hits[primary,3],bits(w['origin_t'][:,0,3])[primary]),'exact original primary presence/normal/depth')
    primary_ids=bits(w['position_primitive'][:,0,3])[primary]
    need(np.array_equal(original_hits[primary,4:7],metadata[primary_ids,:3]),'all primary primitive/material/instance identities')
    need(np.array_equal(bits(c['normal_status'][:,3]),status) and (c['radiance_trial'][:,3]==1).all(),'physical status and separate raw trial denominator')
    for field in ('origin_pdf','normal_status','radiance_trial','direction_cosine','primary_direct'):need(np.isfinite(c[field]).all(),'finite candidate '+field)
    need((c['radiance_trial'][:,:3]>=0).all() and np.array_equal(c['radiance_trial'][:,:3],np.broadcast_to(suffix[:,None],(n,3))),'actual GPU suffix RGB')
    for field,actual in (('origin_pdf',np.where(primary[:,None],spawns[:,0],0)),('normal_status',np.where(primary[:,None],normals[:,0],0)),('endpoint_primitive',np.where(secondary[:,None],positions[:,1],0)),('endpoint_normal',np.where(secondary[:,None],normals[:,1],0)),('primary_direct',np.where(primary[:,None],positions[:,0],0))):need(np.array_equal(c[field][:,:3],actual),'actual original packet '+field)
    need(np.array_equal(c['primary_direct'][:,3],direct[:,0]),'separate packet primary direct')
    empty=np.zeros(int((~primary).sum()),CANDIDATE);empty['radiance_trial'][:,3]=1
    need(c[~primary].tobytes()==empty.tobytes(),'all current-invalid packet bytes explicit empty/trial1')
    need((c['endpoint_primitive'][~secondary]==0).all() and (c['endpoint_normal'][~secondary,:3]==0).all(),'no finite MISS endpoint')
    need((bits(c['endpoint_normal'][:,3])[primary]==bits(w['position_primitive'][:,0,3])[primary]).all() and (bits(c['endpoint_primitive'][:,3])[secondary]==bits(w['position_primitive'][:,1,3])[secondary]).all(),'packet start/end primitive identity')
    source_cos=np.maximum(F(0),(normals[:,0]*rays[:,1]).sum(axis=1));pdf=np.where(primary,source_cos/PI,F(0))
    need(near(c['origin_pdf'][:,3],pdf).all() and (c['origin_pdf'][primary,3]>0).all() and near(c['direction_cosine'][:,:3],rays[:,1]).all() and near(c['direction_cosine'][:,3],source_cos).all(),'actual sampled solid-angle PDF/direction')
    need(local_endpoint.shape==(n,4) and local_endpoint.dtype==np.dtype('<f4') and np.isfinite(local_endpoint).all(),'complete local endpoint ABI')
    need((local_endpoint[~secondary]==0).all(),'no local fake MISS endpoint')
    need(np.array_equal(local_endpoint[secondary,3],w['origin_t'][secondary,1,3]),'local endpoint actual intersection t')
    parametric=rays[:,1]*w['origin_t'][:,1,3,None]
    need(near(local_endpoint[secondary,:3],parametric[secondary]).all(),'local endpoint comes from actual sampled ray times t')
    represented=c['origin_pdf'][secondary,:3].astype(float)+local_endpoint[secondary,:3].astype(float)
    need(near(represented,c['endpoint_primitive'][secondary,:3]).all(),'local and original barycentric world endpoint agree geometrically')
    need(near(represented,(origins.astype(float)+rays.astype(float)*w['origin_t'][...,3,None])[:,1][secondary]).all(),'local world endpoint agrees with actual query ray')
    st=triangles[bits(w['position_primitive'][:,1,3])[secondary]].astype(float);sa=st[:,1]-st[:,0];sb=st[:,2]-st[:,0];sd=represented-st[:,0]
    saa=(sa*sa).sum(axis=1);sbb=(sb*sb).sum(axis=1);sab=(sa*sb).sum(axis=1);sda=(sd*sa).sum(axis=1);sdb=(sd*sb).sum(axis=1);den=saa*sbb-sab*sab
    su=(sda*sbb-sdb*sab)/den;sv=(sdb*saa-sda*sab)/den
    need((su>=-3e-4).all() and (sv>=-3e-4).all() and (su+sv<=1+3e-4).all() and near(represented,st[:,0]+su[:,None]*sa+sv[:,None]*sb).all(),'represented local endpoint belongs to same actual triangle')
    absolute_direction=np.zeros((n,3));absolute_direction[secondary]=norm(c['endpoint_primitive'][secondary,:3].astype(float)-c['origin_pdf'][secondary,:3].astype(float))
    absolute_direction_error=absolute_direction-np.where(secondary[:,None],rays[:,1],0)
    absolute_direction_failed=np.zeros((n,3),bool);absolute_direction_failed[secondary]=~near(absolute_direction[secondary],rays[:,1][secondary])
    endpoint_direction=np.zeros((n,3));endpoint_direction[secondary]=norm(local_endpoint[secondary,:3].astype(float))
    direction_error=endpoint_direction-np.where(secondary[:,None],rays[:,1],0)
    need(near(endpoint_direction[secondary],rays[:,1][secondary]).all(),'endpoint versus originally generated direction')
    geometric_cos=np.maximum(0,(endpoint_direction*c['normal_status'][:,:3]).sum(axis=1));recovery=np.zeros((n,3))
    recovery[secondary]=c['radiance_trial'][secondary,:3]*geometric_cos[secondary,None]/(np.pi*c['origin_pdf'][secondary,3,None])
    need(near(recovery,original[:,1,None]).all(),'no-resampling original PT recovery')
    hemisphere=np.zeros(n,bool);hemisphere[secondary]=(c['endpoint_normal'][secondary,:3]*(-local_endpoint[secondary,:3])).sum(axis=1)>0
    need(hemisphere[secondary].all(),'physical oriented endpoint hemisphere')
    need((packed['misc']==secondary.astype(U)).all() and (packed['unused']==0).all(),'exact packed M/age/reserved')
    need(np.array_equal(packed['position'],local_endpoint[:,:3]),'packed endpoint exact')
    weight=np.zeros(n);weight[secondary]=1/c['origin_pdf'][secondary,3].astype(float)
    need(near(packed['weight'],weight,2e-5,2e-6).all(),'actual packed inverse solid-angle PDF')
    decoded=D.decode(packed['radiance'])/F(64);decoded_n=decode_normal(packed['normal'])
    need(near(decoded_n[secondary],c['endpoint_normal'][secondary,:3]).all(),'packed octahedral normal')
    need((packed['radiance'][~secondary]==0).all() and (packed['normal'][~secondary]==0).all(),'empty packed encoding')
    radiance_error=np.abs(decoded.astype(float)-c['radiance_trial'][:,:3]);need((radiance_error<=.02*np.maximum(c['radiance_trial'][:,:3],1e-6)).all(),'packed RGB error at most2percent')
    expected_packed=np.zeros((n,3));expected_packed[secondary]=decoded[secondary]*geometric_cos[secondary,None]/np.pi*weight[secondary,None]
    need(np.isfinite(output).all() and (output>=0).all(),'finite nonnegative actual SDK outputs')
    for base,expected in ((0,recovery),(3,expected_packed)):
        need(np.array_equal(output[:,base,3],secondary.astype(F)) and near(output[:,base,:3],expected,2e-5,2e-6).all(),'full actual SDK RGB/M recovery')
        need(near(output[:,base+1,0],weight,2e-5,2e-6).all() and near(output[:,base+1,1],geometric_cos).all(),'full actual SDK weight/cosine')
        need(np.array_equal(output[:,base+1,2],secondary.astype(F)) and np.array_equal(output[:,base+1,3],secondary.astype(F)),'actual SDK oriented hemisphere AND real-BVH visibility must hold')
        need(near(output[:,base+2,:3],original[:,0,None]+output[:,base,:3],2e-5,2e-6).all() and (output[:,base+2,3]==1).all(),'actual SDK composition counts primary once')
    need(near(output[:,0,:3],original[:,1,None]).all(),'actual uncompressed SDK recovery versus original PT')
    packing_error=np.abs(output[:,3,:3].astype(float)-original[:,1,None]);need((packing_error<=.02*np.maximum(original[:,1,None],1e-6)+3e-6).all(),'packed final PT recovery error at most2percent plus3e-6')
    arrays=dict(local_endpoint=local_endpoint,absolute_direction_error=absolute_direction_error,absolute_direction_failed=absolute_direction_failed,status=status,visited=visited,endpoint_error=endpoint_error,direction_error=direction_error,suffix=suffix,source_pdf=pdf,recovered=recovery,unpacked_error=output[:,0,:3]-original[:,1,None],packed_error=packing_error,radiance_error=radiance_error)
    summary=dict(absolute_world_direction_failed_pixels=int(absolute_direction_failed.any(axis=1).sum()),paths=n,visited_vertices=int(visited.sum()),hit_vertices=int(hit.sum()),primary_invalid=int((~primary).sum()),secondary_misses=int((primary&~secondary).sum()),secondary_hits=int(secondary.sum()),black_secondary_hits=int((secondary&(suffix==0)).sum()),backfacing_hits=int((~front).sum()),max_unpacked_absolute_error=float(np.max(np.abs(arrays['unpacked_error']))),max_packed_absolute_error=float(packing_error.max()))
    return arrays,summary
