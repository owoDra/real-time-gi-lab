#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, os, subprocess
from pathlib import Path
import j002_contract as contract
import j002_geometry as geometry
import run_j002_prepare as prepare

ROOT=Path(__file__).resolve().parents[3]
EXPECTED_BRANCH="research-lane-j-topology-backend-alternatives"
CONFIG=ROOT/"research/lanes/lane-j-topology-backend-alternatives/experiments/002-deterministic-topology-contract.json"

def git(*args):
    p=subprocess.run(["git",*args],cwd=ROOT,text=True,capture_output=True,check=False)
    if p.returncode: raise RuntimeError(p.stderr.strip())
    return p.stdout.strip()

def discover_accepted_producer_stream(root: Path, cfg: dict) -> Path:
    source=cfg["producer_source"]
    candidates=sorted(root.glob(str(source["artifact_glob"])))
    accepted=[]
    for stream in candidates:
        meta=stream.with_name("stream-v1.json")
        if not meta.exists():
            continue
        try:
            record=json.loads(meta.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError):
            continue
        if (
            record.get("case")==source["case"]
            and record.get("git_commit")==source["accepted_git_commit"]
        ):
            accepted.append(stream)
    if len(accepted)!=1:
        raise RuntimeError(
            "expected exactly one accepted A001 producer stream; "
            f"found {len(accepted)} matching {source['case']} @ "
            f"{source['accepted_git_commit']}"
        )
    return accepted[0]

def main():
    ap=argparse.ArgumentParser(description="Materialize frozen J002 topology snapshots")
    ap.add_argument(
        "--scene",
        type=Path,
        default=Path("assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"),
    )
    ap.add_argument("--producer-stream",type=Path)
    ap.add_argument("--artifact-dir",type=Path)
    ap.add_argument("--allow-dirty",action="store_true")
    args=ap.parse_args()
    if git("branch","--show-current")!=EXPECTED_BRANCH: raise RuntimeError(f"must run on {EXPECTED_BRANCH}")
    if not args.allow_dirty and git("status","--porcelain"): raise RuntimeError("retained J002 preparation requires clean worktree")
    cfg=json.loads(CONFIG.read_text())
    producer_path=args.producer_stream or discover_accepted_producer_stream(ROOT,cfg)
    producer=producer_path.read_bytes()
    manifest=prepare.build_manifest(cfg,producer)
    scene=geometry.load_b002_compatible_gltf(args.scene)
    representative=geometry.select_representative_object(scene,796)
    selected_instance=representative[0].instance_id
    global_next=max(t.primitive_id for t in scene)+1
    env_root=os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    root=args.artifact_dir or (Path(env_root) if env_root else None)
    if root is None:
        root=ROOT/"out/research/lane-j-topology-backend-alternatives/002-deterministic-topology-contract/materialize"
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    result_profiles=[]
    for profile_index,p in enumerate(cfg["profiles"]):
        seed=contract.profile_seed(int(cfg["master_topology_seed"]),profile_index)
        steps=contract.topology_sequence(int(p["base_primitive_count"]),[float(x) for x in cfg["primitive_count_factors"]],seed,float(p["replacement_fraction"]),str(p["locality"]))
        digest=contract.topology_digest(str(p["name"]),steps)
        if digest!=p["expected_topology_digest"]: raise RuntimeError(f"topology digest drift for {p['name']}")
        base=geometry.derive_profile_base(representative,int(steps[0].primitive_count),seed,global_next)
        snaps=geometry.materialize_profile(base,steps,global_next+max(0,len(base)-len(representative)))
        identity=[{"primitive_count":s.primitive_count,"snapshot_digest":s.snapshot_digest} for s in snaps]
        contract.validate_transition_identity(identity)
        profile_dir=root/str(p["name"]); profile_dir.mkdir(parents=True,exist_ok=True)
        rows=[]
        for snap in snaps:
            filename=f"step-{snap.index:02d}.bin"; geometry.write_snapshot(profile_dir/filename,snap)
            rows.append({
                "index":snap.index,"primitive_count":snap.primitive_count,"topology_seed":snap.topology_seed,
                "replacement_count":snap.replacement_count,"locality":snap.locality,"snapshot_digest":snap.snapshot_digest,
                "inserted_ids":list(snap.inserted_ids),"removed_ids":list(snap.removed_ids),
                "replaced_old_ids":list(snap.replaced_old_ids),"replaced_new_ids":list(snap.replaced_new_ids),
                "file":f"{p['name']}/{filename}"
            })
        result_profiles.append({"name":p["name"],"topology_digest":digest,"steps":rows})
    output={
        **manifest,
        "scene":str(args.scene),
        "producer_stream_path":str(producer_path),
        "producer_stream_file_sha256":hashlib.sha256(producer).hexdigest(),
        "scene_sha256":hashlib.sha256(args.scene.read_bytes()).hexdigest(),
        "scene_triangle_count":len(scene),
        "representative_instance_id":selected_instance,
        "representative_primitive_count":len(representative),
        "representative_primitive_ids":[t.primitive_id for t in representative],
        "profiles":result_profiles,
        "gpu_required":False
    }
    (root/"j002-materialized-manifest.json").write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print(f"J002 materialized: {root}")
    print(f"representative instance={selected_instance} triangles={len(representative)}")
    for p in result_profiles: print(f"{p['name']}: {len(p['steps'])} snapshots")
    return 0

if __name__=="__main__": raise SystemExit(main())
