#!/usr/bin/env python3
"""Generate or verify the M001 frozen, geometry-only held-out glTF fixtures.

No Renderer, GPU, reference scoring, state capture or timing is invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FACTORY = ROOT / "scripts/research/lane_n_end_to_end_renderer/n004_scene_factory.py"
SCENES = (
    ("M001-H01", "medium", 0.137),
    ("M001-H02", "grazing", 0.163),
    ("M001-H03", "enclosed", 0.127),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(output_dir: Path, factory_path: Path = FACTORY) -> dict:
    output_dir = output_dir.resolve()
    factory_path = factory_path.resolve()
    if output_dir.exists():
        raise ValueError(f"refuse to overwrite or reuse existing root: {output_dir}")
    if not factory_path.is_file():
        raise FileNotFoundError(factory_path)
    spec = importlib.util.spec_from_file_location("lane_m_n004_factory", factory_path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot import frozen N004 geometry factory")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factory_sha = digest(factory_path)
    output_dir.mkdir(parents=True)
    manifest = {
        "schema": "lane-m-m001-heldout-geometry/1",
        "complete": False,
        "classification": "GEOMETRY_ONLY_NOT_STATE_OR_REFERENCE_ELIGIBLE",
        "factory_path": str(factory_path.relative_to(ROOT)) if factory_path.is_relative_to(ROOT) else str(factory_path),
        "factory_sha256": factory_sha,
        "recipes_fixed_in": "research/lanes/lane-m-gi-competitiveness/experiments/001-first-cohort-preregistration.md",
        "scenes": [],
    }
    path = output_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for name, kind, thickness in SCENES:
        groups = module.leak_scene(kind, thickness)
        gltf = module.write_gltf(output_dir, name, groups)
        binary = output_dir / (name + ".bin")
        if not gltf.is_file() or not binary.is_file():
            raise ValueError("factory did not emit complete paired glTF/BIN")
        manifest["scenes"].append({
            "name": name, "kind": kind, "wall_thickness_world": thickness,
            "gltf": gltf.name, "gltf_sha256": digest(gltf),
            "bin": binary.name, "bin_sha256": digest(binary),
            "triangle_count": module.triangle_count(groups),
            "eligible_reference": False, "gpu_state_frozen": False,
        })
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["complete"] = True
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify(manifest_path: Path, factory_path: Path = FACTORY) -> dict:
    manifest_path = manifest_path.resolve()
    d = json.loads(manifest_path.read_text(encoding="utf-8"))
    if d.get("schema") != "lane-m-m001-heldout-geometry/1" or d.get("complete") is not True:
        raise ValueError("incomplete or unknown geometry manifest")
    if digest(factory_path.resolve()) != d.get("factory_sha256"):
        raise ValueError("N004 factory changed")
    if len(d.get("scenes", [])) != len(SCENES):
        raise ValueError("wrong held-out count")
    for row, (name, kind, thickness) in zip(d["scenes"], SCENES):
        if (row.get("name"), row.get("kind"), row.get("wall_thickness_world")) != (name, kind, thickness):
            raise ValueError("held-out recipe changed")
        if row.get("eligible_reference") is not False or row.get("gpu_state_frozen") is not False:
            raise ValueError("geometry manifest may not declare GPU or reference eligibility")
        for filename, key in ((name + ".gltf", "gltf_sha256"), (name + ".bin", "bin_sha256")):
            if row.get("gltf" if filename.endswith(".gltf") else "bin") != filename:
                raise ValueError("asset path changed")
            if digest(manifest_path.parent / filename) != row.get(key):
                raise ValueError(f"asset changed: {filename}")
        if type(row.get("triangle_count")) is not int or row["triangle_count"] <= 0:
            raise ValueError("invalid geometry triangle count")
    return {"classification": "M001_GEOMETRY_MANIFEST_INTEGRITY_PASS_NOT_GPU_READY",
            "scenes": len(SCENES), "factory_sha256": d["factory_sha256"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output-dir", type=Path)
    group.add_argument("--verify-manifest", type=Path)
    args = parser.parse_args()
    result = generate(args.output_dir) if args.output_dir else verify(args.verify_manifest)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
