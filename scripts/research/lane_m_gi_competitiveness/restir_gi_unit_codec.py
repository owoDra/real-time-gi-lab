"""041 independent neutral/Rec709 SDK codec reference and fixed physical units."""
import numpy as np
import restir_gi_local_overlay as L
import restir_gi_device_model as D
F=np.float32;U=np.uint32
UNIT=F(64);BLACK_BOUND=2.0**(-20+1/409.6);UPPER=7/np.pi


def shader(raw):
    return L.apply(L.shader(raw).decode(),[
        ('localEndpoints[pixel].xyz,c.endpoint_normal.xyz,c.radiance_trial.xyz,c.origin_pdf.w','localEndpoints[pixel].xyz,c.endpoint_normal.xyz,c.radiance_trial.xyz*64.0,c.origin_pdf.w'),
        ('rgb=r.radiance*(cosine/RTXDI_PI)*r.weightSum;','rgb=(r.radiance*(cosine/RTXDI_PI)*r.weightSum)/64.0;')]).encode()


def encode(rgb):
    rgb=np.asarray(rgb,F)
    matrix=np.array([[.4123907992659595,.357584339383878,.1804807884018343],[.2126390058715104,.7151686787677559,.0721923153607337],[.0193308187155918,.1191947797946259,.9505321522496608]],F)
    xyz=rgb@matrix.T
    with np.errstate(divide='ignore'):
        le=np.clip(F(409.6)*(np.log2(xyz[...,1])+F(20)),0,16383).astype(U)
    active=le!=0;uv=np.zeros((*le.shape,2),F)
    a=xyz[active];den=-F(2)*a[:,0]+F(12)*a[:,1]+F(3)*(a[:,0]+a[:,1]+a[:,2])
    uv[active]=a[:,:2]*np.array([4,9],F)/den[:,None]
    code=np.clip(F(820)*uv,0,511).astype(U)
    return np.where(active,(le<<18)|(code[...,0]<<9)|code[...,1],U(0))


def decode(code):return D.decode(code)/UNIT
def budget(rgb):return .02*np.maximum(np.asarray(rgb,float),1e-6)


def critical_grid():
    boundaries=(np.exp2(np.arange(1,16384,dtype=float)/409.6-20)/float(UNIT)).astype(F)
    boundaries=boundaries[(boundaries>=0)&(boundaries<=F(UPPER))]
    return np.unique(np.concatenate((boundaries,np.nextafter(boundaries,F(0)),np.nextafter(boundaries,F(np.inf)),np.array([0,np.nextafter(F(0),F(1)),1e-6,F(UPPER),np.nextafter(F(UPPER),F(np.inf))],F))))


def underflow_failures(rgb,packed):
    rgb=np.asarray(rgb,F);decoded=D.decode(packed)
    bad=(np.abs(decoded.astype(float)-rgb)>budget(rgb)).any(axis=-1)
    explained=(np.asarray(packed,U)==0)&(rgb.max(axis=-1)<=BLACK_BOUND*(1+3e-6))
    return bad,explained
