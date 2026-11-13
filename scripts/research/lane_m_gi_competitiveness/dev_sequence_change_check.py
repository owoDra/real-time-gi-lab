import numpy as np, sys, math
from pathlib import Path
R=Path('out/research/lane-m-gi-competitiveness/rtcv-dev-runs')
N=57600
def img(o,f): return np.fromfile(o/f'frame-{f:04d}.f32','<f4').reshape(N,2).astype(float)
def ref(seq,f):
    return np.mean([img(R/f'ref-{seq}-b8-s{s}',f) for s in range(4)],axis=0)
def nrm(a,b): 
    e=a-b; return math.sqrt(np.mean(e*e))/max(math.sqrt(np.mean(b*b)),1e-30)
for seq in sys.argv[1:]:
    fs=sorted(int(p.name[6:10]) for p in (R/f'ref-{seq}-b8-s0').glob('frame-*.f32'))
    r0=ref(seq,fs[0])
    # reference noise estimate: half-difference of seed pairs
    a=np.mean([img(R/f'ref-{seq}-b8-s{s}',fs[-1]) for s in (0,1)],axis=0);b=np.mean([img(R/f'ref-{seq}-b8-s{s}',fs[-1]) for s in (2,3)],axis=0)
    out=[]
    for f in fs[1:]:
        r=ref(seq,f)
        out.append(f"{f}: ind {nrm(r[:,1],r0[:,1]):.4f} tot {nrm(r.sum(1),r0.sum(1)):.4f}")
    cov=(r0.sum(1)>0).mean()
    print(f"{seq:14s} cov={cov:.3f} ind/total_rms={math.sqrt(np.mean(r0[:,1]**2))/math.sqrt(np.mean(r0.sum(1)**2)):.3f} refnoise_ind={nrm(a[:,1],b[:,1])/2:.4f} | change vs frame0: "+' ; '.join(out))
