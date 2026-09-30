from __future__ import annotations
from dataclasses import dataclass
import math
from j002_geometry import centroid

@dataclass
class Cluster:
    cluster_id:int
    primitive_ids:list[int]

@dataclass
class UpdateStats:
    dirty_cluster_count:int=0
    rebuilt_triangle_count:int=0
    unaffected_cluster_rebuild_count:int=0
    split_count:int=0
    merge_count:int=0
    cluster_set_changed:bool=False

class ClusterModel:
    def __init__(self,triangles,target=48,maximum=64,merge_below=24):
        if not (0<merge_below<target<=maximum): raise ValueError("invalid thresholds")
        self.target=target; self.maximum=maximum; self.merge_below=merge_below
        self.triangles={t.primitive_id:t for t in triangles}; self.next_cluster_id=0
        ordered=self._morton_order(list(self.triangles))
        self.clusters=[Cluster(self._new_id(),ordered[i:i+target]) for i in range(0,len(ordered),target)]
        self._validate()
    def _new_id(self): v=self.next_cluster_id; self.next_cluster_id+=1; return v
    def _bounds(self,ids):
        pts=[p for pid in ids for p in (self.triangles[pid].v0,self.triangles[pid].v1,self.triangles[pid].v2)]
        return tuple(min(p[a] for p in pts) for a in range(3)),tuple(max(p[a] for p in pts) for a in range(3))
    def _area(self,ids):
        if not ids:return 0.0
        mn,mx=self._bounds(ids); e=[max(0.0,mx[i]-mn[i]) for i in range(3)]
        return 2*(e[0]*e[1]+e[1]*e[2]+e[2]*e[0])
    def _morton_order(self,ids):
        if not ids:return []
        cs={i:centroid(self.triangles[i]) for i in ids}; mn=tuple(min(p[a] for p in cs.values()) for a in range(3)); mx=tuple(max(p[a] for p in cs.values()) for a in range(3))
        def code(pid):
            p=cs[pid]; q=[]
            for a in range(3): q.append(max(0,min(1023,int((p[a]-mn[a])/max(mx[a]-mn[a],1e-9)*1023+0.5))))
            def spread(v):
                r=0
                for bit in range(10): r|=((v>>bit)&1)<<(3*bit)
                return r
            return spread(q[0])|(spread(q[1])<<1)|(spread(q[2])<<2)
        return sorted(ids,key=lambda pid:(code(pid),pid))
    def _nearest(self,t):
        best=None
        for c in self.clusters:
            key=(self._area(c.primitive_ids+[t.primitive_id])-self._area(c.primitive_ids),c.cluster_id)
            if best is None or key<best[0]: best=(key,c)
        return best[1] if best else None
    def _split(self,c):
        queue=[self._morton_order(c.primitive_ids)]; pieces=[]
        while queue:
            ids=queue.pop(0)
            if len(ids)<=self.maximum: pieces.append(ids); continue
            cut=len(ids)//2; queue.extend([ids[:cut],ids[cut:]])
        out=[Cluster(c.cluster_id,pieces[0])]
        out.extend(Cluster(self._new_id(),ids) for ids in pieces[1:])
        return out
    def update(self,triangles):
        new={t.primitive_id:t for t in triangles}; old=set(self.triangles); now=set(new); deleted=old-now; inserted=now-old; changed={pid for pid in old&now if self.triangles[pid]!=new[pid]}
        original={c.cluster_id:tuple(c.primitive_ids) for c in self.clusters}; dirty=set()
        for c in self.clusters:
            before=list(c.primitive_ids); c.primitive_ids=[pid for pid in c.primitive_ids if pid not in deleted and pid not in changed]
            if c.primitive_ids!=before: dirty.add(c.cluster_id)
        self.triangles=new
        for pid in sorted(inserted|changed):
            c=self._nearest(new[pid])
            if c is None: c=Cluster(self._new_id(),[]); self.clusters.append(c)
            c.primitive_ids.append(pid); dirty.add(c.cluster_id)
        split_count=0; rebuilt=[]
        for c in sorted(self.clusters,key=lambda x:x.cluster_id):
            if c.cluster_id in dirty and len(c.primitive_ids)>self.maximum:
                parts=self._split(c); rebuilt.extend(parts); split_count+=len(parts)-1
            else: rebuilt.append(c)
        self.clusters=rebuilt
        if split_count: dirty.update(c.cluster_id for c in self.clusters if c.cluster_id not in original)
        merge_count=0; changed_loop=True
        while changed_loop:
            changed_loop=False
            for c in sorted(self.clusters,key=lambda x:x.cluster_id):
                if c.cluster_id not in dirty or len(c.primitive_ids)>=self.merge_below: continue
                candidates=[x for x in self.clusters if x.cluster_id!=c.cluster_id and len(x.primitive_ids)+len(c.primitive_ids)<=self.target]
                if not candidates: continue
                cc=(0,0,0) if not c.primitive_ids else tuple(sum(x)/2 for x in zip(*self._bounds(c.primitive_ids)))
                def dist(x):
                    center=tuple(sum(v)/2 for v in zip(*self._bounds(x.primitive_ids))); return (math.dist(cc,center),x.cluster_id)
                target=min(candidates,key=dist); target.primitive_ids=self._morton_order(target.primitive_ids+c.primitive_ids); dirty.add(target.cluster_id)
                self.clusters=[x for x in self.clusters if x.cluster_id!=c.cluster_id]; merge_count+=1; changed_loop=True; break
        self._validate()
        final_dirty={c.cluster_id for c in self.clusters if c.cluster_id in dirty}
        unaffected=sum(1 for c in self.clusters if c.cluster_id not in dirty and original.get(c.cluster_id)!=tuple(c.primitive_ids))
        return UpdateStats(len(final_dirty),sum(len(c.primitive_ids) for c in self.clusters if c.cluster_id in final_dirty),unaffected,split_count,merge_count,split_count>0 or merge_count>0)
    def _validate(self):
        ids=[pid for c in self.clusters for pid in c.primitive_ids]
        if len(ids)!=len(set(ids)) or set(ids)!=set(self.triangles): raise AssertionError("cluster ownership invalid")
        if any(len(c.primitive_ids)>self.maximum for c in self.clusters): raise AssertionError("cluster maximum exceeded")
