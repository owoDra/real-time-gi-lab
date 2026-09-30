#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
import j002_geometry as geometry
from j003_cluster_model import ClusterModel

def main():
    ap=argparse.ArgumentParser(description="Replay J002 snapshots through the J003 CPU cluster model")
    ap.add_argument("--j002-artifact-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    manifest=json.loads((args.j002_artifact_dir/"j002-materialized-manifest.json").read_text())
    profiles=[]
    for profile in manifest["profiles"]:
        steps=profile["steps"]
        first=geometry.read_snapshot(args.j002_artifact_dir/steps[0]["file"])
        model=ClusterModel(first,target=48,maximum=64,merge_below=24)
        rows=[{
            "index":0,"cluster_count":len(model.clusters),
            "occupancy_min":min(len(c.primitive_ids) for c in model.clusters),
            "occupancy_max":max(len(c.primitive_ids) for c in model.clusters),
            "dirty_cluster_count":0,"rebuilt_triangle_count":0,"split_count":0,"merge_count":0,
            "unaffected_cluster_rebuild_count":0
        }]
        for step in steps[1:]:
            triangles=geometry.read_snapshot(args.j002_artifact_dir/step["file"])
            stats=model.update(triangles)
            occupancy=[len(c.primitive_ids) for c in model.clusters]
            if stats.unaffected_cluster_rebuild_count!=0: raise RuntimeError("unaffected cluster mutation detected")
            if max(occupancy)>64: raise RuntimeError("cluster maximum violated")
            rows.append({
                "index":step["index"],"cluster_count":len(model.clusters),
                "occupancy_min":min(occupancy),"occupancy_max":max(occupancy),
                "dirty_cluster_count":stats.dirty_cluster_count,
                "rebuilt_triangle_count":stats.rebuilt_triangle_count,
                "split_count":stats.split_count,"merge_count":stats.merge_count,
                "unaffected_cluster_rebuild_count":stats.unaffected_cluster_rebuild_count
            })
        profiles.append({"name":profile["name"],"rows":rows})
    result={
        "schema_version":1,
        "experiment":"J003-cpu-structural-gates",
        "correctness_scope":"cluster ownership/split/merge/locality invariants only",
        "formal_timing_decision":False,
        "gpu_validation_required":True,
        "profiles":profiles
    }
    output=args.output or args.j002_artifact_dir/"j003-cpu-structural.json"
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(f"J003 CPU structural gates PASS: {output}")
    print("Next gate requires the target GPU implementation and exact end-to-end validation.")
    return 0

if __name__=="__main__": raise SystemExit(main())
