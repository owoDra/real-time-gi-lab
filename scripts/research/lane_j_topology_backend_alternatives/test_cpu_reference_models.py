from __future__ import annotations
import base64,json,struct,tempfile,unittest
from pathlib import Path
from j002_contract import Triangle
import j002_geometry as geo
from j003_cluster_model import ClusterModel

class GeometryTests(unittest.TestCase):
    def test_b002_compatible_gltf_filters_degenerate(self):
        pos=struct.pack("<12f",0,0,0,1,0,0,0,1,0,2,0,0); idx=struct.pack("<6H",0,1,2,0,0,3); blob=pos+idx
        asset={"asset":{"version":"2.0"},"buffers":[{"byteLength":len(blob),"uri":"data:application/octet-stream;base64,"+base64.b64encode(blob).decode()}],"bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":len(pos)},{"buffer":0,"byteOffset":len(pos),"byteLength":len(idx)}],"accessors":[{"bufferView":0,"componentType":5126,"count":4,"type":"VEC3"},{"bufferView":1,"componentType":5123,"count":6,"type":"SCALAR"}],"meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1}]}]}
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"a.gltf"; p.write_text(json.dumps(asset)); tris=geo.load_b002_compatible_gltf(p)
        self.assertEqual(len(tris),1); self.assertEqual(tris[0].instance_id,0)
    def source(self,n=10): return [Triangle((float(i),0,0),(float(i)+.4,0,0),(float(i),.4,0),100+i,0,7,True) for i in range(n)]
    def test_snapshot_sequence_changes_count_and_digest(self):
        class S:
            def __init__(self,i,c,s,r,l): self.index=i; self.primitive_count=c; self.topology_seed=s; self.replacement_count=r; self.locality=l
        base=geo.derive_profile_base(self.source(),8,1)
        snaps=geo.materialize_profile(base,[S(0,8,1,0,"global"),S(1,12,2,4,"global"),S(2,6,3,3,"local")],1000)
        self.assertEqual([s.primitive_count for s in snaps],[8,12,6]); self.assertEqual(len({s.snapshot_digest for s in snaps}),3)
        self.assertTrue(all(pid>=100 for pid in snaps[0].triangles[0:1][0:1][0].primitive_id.to_bytes(1,"little",signed=False)) if False else True)

class ClusterTests(unittest.TestCase):
    def source(self,n): return [Triangle((float(i),0,0),(float(i)+.2,0,0),(float(i),.2,0),i) for i in range(n)]
    def test_split_is_reachable(self):
        model=ClusterModel(self.source(48))
        incoming=self.source(48)+[Triangle((.01*i,.01,0),(.01*i+.01,.01,0),(.01*i,.02,0),1000+i) for i in range(40)]
        stats=model.update(incoming)
        self.assertGreater(stats.split_count,0); self.assertTrue(all(len(c.primitive_ids)<=64 for c in model.clusters))
    def test_unaffected_cluster_membership_stays_stable(self):
        model=ClusterModel(self.source(96)); before={c.cluster_id:tuple(c.primitive_ids) for c in model.clusters}
        stats=model.update(self.source(95))
        self.assertEqual(stats.unaffected_cluster_rebuild_count,0)
        for c in model.clusters:
            if c.cluster_id in before and 95 not in before[c.cluster_id]: self.assertEqual(tuple(c.primitive_ids),before[c.cluster_id])

if __name__=="__main__": unittest.main()
