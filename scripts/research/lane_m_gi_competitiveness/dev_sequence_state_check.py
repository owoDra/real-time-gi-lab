import numpy as np, sys, struct
from pathlib import Path
for seq in sys.argv[1:]:
    d=Path(seq); subs=sorted(p for p in d.iterdir() if p.is_dir())
    def load(p):
        f=(p/'frame-state.bin').read_bytes(); g=(p/'geometry-state.bin').read_bytes()
        par=np.frombuffer(f,dtype='<f4',count=24,offset=20).reshape(6,4)
        rec=np.frombuffer(g,dtype=np.dtype([('v','<f4',(9,)),('meta','<u4',(4,))]),offset=8)
        return par,rec
    p0,r0=load(subs[0]); p1,r1=load(subs[-1])
    inst,cnt=np.unique(r0['meta'][:,2],return_counts=True)
    v=r0['v'].reshape(-1,3); lo,hi=v.min(0),v.max(0)
    moved=np.abs(r0['v']-r1['v']).max(1)>0
    print(seq,'frames',len(subs),'tris',len(r0),'instances',dict(zip(inst.tolist(),cnt.tolist())) if len(inst)<12 else f'{len(inst)} instances, top {sorted(cnt.tolist())[-3:]}')
    print('  bbox',lo.round(2),hi.round(2),'center',((lo+hi)/2).round(2))
    print('  params f0:\n',p0.round(3)); print('  params changed rows:',np.where(np.abs(p0-p1).max(1)>0)[0], 'light f0',p0[5],'light fN',p1[5])
    print('  moved tris',int(moved.sum()),'instances moved',np.unique(r0['meta'][moved,2]).tolist(), 'max disp',float(np.abs(r0['v']-r1['v']).max()))
