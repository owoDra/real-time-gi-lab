#!/usr/bin/env python3
"""Plan173: exact-rational re-evaluation of the742 guard witnesses (CPU only, no native)."""
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path

import diagnose_737_guard_witness as D

ANALYSIS=D.RESULTS/'742-737-guard-failure-witness-analysis.json'
EPS=F(2)**-52


def triangles(scene):
    rows=[]
    for line in scene.read_text().splitlines():
        line=line.split('#',1)[0].split()
        if line and line[0]=='tri':
            v=[F(float(x)) for x in line[2:11]]
            rows.append((v[0:3],v[3:6],v[6:9]))
    return rows


def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def norm(a):return math.sqrt(float(dot(a,a)))


def barycentric(v0,v1,v2,p):
    n=cross(sub(v1,v0),sub(v2,v0));nn=dot(n,n)
    return [dot(cross(sub(v2,v1),sub(p,v1)),n)/nn,dot(cross(sub(v0,v2),sub(p,v2)),n)/nn,
            dot(cross(sub(v1,v0),sub(p,v0)),n)/nn]


def analyze(row,tris):
    v0,v1,v2=tris[row['target_triangle']]
    o=[F(row[k]) for k in ('ox','oy','oz')];p=[F(row[k]) for k in ('px','py','pz')]
    low=[F(row[k]) for k in ('lx','ly','lz')];w=[F(row[k]) for k in ('wx','wy','wz')]
    n=cross(sub(v1,v0),sub(v2,v0));nlen=norm(n)
    exact_hit=[oi+wi*(dot(n,sub(v0,o))/dot(n,w)) for oi,wi in zip(o,w)]
    actual=[oi+wi*F(row['t']) for oi,wi in zip(o,w)]
    cosine=abs(float(dot(n,w)))/(nlen*norm(w))
    e1,e2=norm(sub(v1,v0)),norm(sub(v2,v0))
    bound=float(row['bound'])
    return dict(kind=row['kind'],pixel=[row['x'],row['y']],sample=row['s'],light_first=row['light_first'],
        index=row['index'],target_triangle=row['target_triangle'],hit_triangle=row['hit_triangle'],
        coincident=row['coincident'],same_triangle=row['target_triangle']==row['hit_triangle'],
        triangle_condition=e1*e2/nlen,abs_cosine=cosine,distance=float(row['distance']),
        recorded_fraction=dict(target_plane=row['target_plane']/bound,actual_plane=row['actual_plane']/bound,
                               conditioned=row['conditioned']/bound),
        exact_target_plane_fraction=abs(float(dot(n,sub(p,v0))))/nlen/bound,
        exact_precise_target_plane_fraction=abs(float(dot(n,sub([a+b for a,b in zip(p,low)],v0))))/nlen/bound,
        exact_actual_plane_fraction=abs(float(dot(n,sub(actual,v0))))/nlen/bound,
        exact_line_plane_to_target_conditioned_fraction=norm(sub(exact_hit,p))*cosine/bound,
        exact_line_plane_to_actual_conditioned_fraction=norm(sub(exact_hit,actual))*cosine/bound,
        target_barycentric=[float(x) for x in barycentric(v0,v1,v2,p)],
        bound_over_eps_scale=bound/float(EPS))


def main():
    if ANALYSIS.exists():raise ValueError('refuse existing742 analysis')
    result=json.loads(D.OUTPUT.read_bytes())
    if not result['complete']:raise ValueError('terminal742 required')
    tris=triangles(D.SCENE)
    near=[]
    for line in (D.WORK/'stderr.log').read_text(errors='replace').splitlines():
        if line.startswith('GUARD_WITNESS '):
            row=json.loads(line[len('GUARD_WITNESS '):])
            for k,_ in D.WITNESS_FIELDS:row[k]=float.fromhex(row[k])
            near.append(row)
    rows=[analyze(r,tris) for r in near]
    out=dict(schema='n010-737-guard-failure-witness-analysis/1',posthoc=True,gpu_run=False,
        reference_admission=False,witness_sha256=D.sha(D.OUTPUT),stderr_sha256=D.sha(D.WORK/'stderr.log'),
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        rows=rows,tests='NOT_RUN')
    ANALYSIS.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    for r in rows:
        if r['kind']=='fail':print(json.dumps(r,indent=1))
    print('near',sum(r['kind']=='near' for r in rows),'fail',sum(r['kind']=='fail' for r in rows))


if __name__=='__main__':main()
