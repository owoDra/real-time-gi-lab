#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path


def add_quad(positions, indices, a, b, c, d):
    base = len(positions)
    positions.extend((a, b, c, d))
    indices.extend((base, base + 1, base + 2, base, base + 2, base + 3))


def add_box(positions, indices, center, half):
    cx, cy, cz = center
    hx, hy, hz = half
    x0, x1 = cx - hx, cx + hx
    y0, y1 = cy - hy, cy + hy
    z0, z1 = cz - hz, cz + hz
    add_quad(positions, indices, (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1))
    add_quad(positions, indices, (x1,y0,z0),(x0,y0,z0),(x0,y1,z0),(x1,y1,z0))
    add_quad(positions, indices, (x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0))
    add_quad(positions, indices, (x1,y0,z1),(x1,y0,z0),(x1,y1,z0),(x1,y1,z1))
    add_quad(positions, indices, (x0,y1,z1),(x1,y1,z1),(x1,y1,z0),(x0,y1,z0))
    add_quad(positions, indices, (x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1))


def add_grid_floor(positions, indices, size=8.0, cells=24):
    step = size / cells
    origin = -size * 0.5
    for z in range(cells):
        for x in range(cells):
            x0 = origin + x * step
            x1 = x0 + step
            z0 = origin + z * step
            z1 = z0 + step
            add_quad(positions, indices, (x0,0.0,z0),(x1,0.0,z0),(x1,0.0,z1),(x0,0.0,z1))


def control_group(center):
    positions, indices = [], []
    cx, cy, cz = center
    # Three boxes = 36 triangles. The accepted Lane-E-final stable path keeps
    # one idle dynamic object; making this mesh first ensures the large workload
    # geometry remains static ownership rather than becoming the control object.
    for offset in (-0.36, 0.0, 0.36):
        add_box(positions, indices, (cx + offset, cy, cz), (0.12, 0.12, 0.12))
    return positions, indices


def leak_scene(thickness: float):
    floor_p, floor_i = [], []
    add_grid_floor(floor_p, floor_i, 8.0, 24)

    wall_p, wall_i = [], []
    add_box(wall_p, wall_i, (0.0, 1.35, 0.0), (thickness * 0.5, 1.35, 2.25))
    add_box(wall_p, wall_i, (0.0, 0.75, -2.75), (0.35, 0.75, 0.35))
    add_box(wall_p, wall_i, (0.0, 0.75,  2.75), (0.35, 0.75, 0.35))

    return [
        control_group((-3.35, 0.18, -3.35)),
        (floor_p, floor_i),
        (wall_p, wall_i),
    ]


def world_scene(kind: str):
    positions, indices = [], []
    if kind == "sparse":
        nx, ny, nz = 8, 1, 8
        spacing = (5.0, 1.0, 5.0)
        half = (0.35, 0.35, 0.35)
    elif kind == "dense":
        nx, ny, nz = 16, 2, 16
        spacing = (0.65, 0.8, 0.65)
        half = (0.28, 0.28, 0.28)
    elif kind == "large-horizontal":
        nx, ny, nz = 32, 1, 4
        spacing = (2.0, 1.0, 1.5)
        half = (0.45, 0.45, 0.45)
    elif kind == "vertical-tall":
        nx, ny, nz = 4, 32, 4
        spacing = (1.5, 1.6, 1.5)
        half = (0.42, 0.42, 0.42)
    else:
        raise ValueError(f"unknown world scene: {kind}")

    ox = -0.5 * (nx - 1) * spacing[0]
    oy = 0.5
    oz = -0.5 * (nz - 1) * spacing[2]
    for y in range(ny):
        for z in range(nz):
            for x in range(nx):
                jitter = 0.07 * math.sin((x + 1) * 1.7 + (z + 1) * 0.9 + y * 0.4)
                add_box(
                    positions,
                    indices,
                    (ox + x * spacing[0], oy + y * spacing[1] + jitter, oz + z * spacing[2]),
                    half,
                )

    control_center = (ox + 0.2, oy + 0.15, oz + 0.2)
    return [control_group(control_center), (positions, indices)]


def write_gltf(root: Path, name: str, groups):
    root.mkdir(parents=True, exist_ok=True)
    binary = bytearray()
    buffer_views = []
    accessors = []
    meshes = []
    nodes = []

    for mesh_index, (positions, indices) in enumerate(groups):
        while len(binary) % 4:
            binary.append(0)
        position_offset = len(binary)
        for p in positions:
            binary.extend(struct.pack("<3f", *p))
        position_view = len(buffer_views)
        buffer_views.append({
            "buffer": 0, "byteOffset": position_offset,
            "byteLength": len(positions) * 12, "target": 34962,
        })
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        zs = [p[2] for p in positions]
        position_accessor = len(accessors)
        accessors.append({
            "bufferView": position_view, "byteOffset": 0, "componentType": 5126,
            "count": len(positions), "type": "VEC3",
            "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)],
        })

        while len(binary) % 4:
            binary.append(0)
        index_offset = len(binary)
        for i in indices:
            binary.extend(struct.pack("<I", i))
        index_view = len(buffer_views)
        buffer_views.append({
            "buffer": 0, "byteOffset": index_offset,
            "byteLength": len(indices) * 4, "target": 34963,
        })
        index_accessor = len(accessors)
        accessors.append({
            "bufferView": index_view, "byteOffset": 0, "componentType": 5125,
            "count": len(indices), "type": "SCALAR",
            "min": [min(indices)], "max": [max(indices)],
        })
        meshes.append({"primitives": [{"attributes": {"POSITION": position_accessor}, "indices": index_accessor}]})
        nodes.append({"mesh": mesh_index})

    bin_name = f"{name}.bin"
    gltf = {
        "asset": {"version": "2.0", "generator": "phos-n004-scene-factory-v2"},
        "buffers": [{"uri": bin_name, "byteLength": len(binary)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
        "meshes": meshes,
        "nodes": nodes,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "scene": 0,
    }
    (root / bin_name).write_bytes(binary)
    path = root / f"{name}.gltf"
    path.write_text(json.dumps(gltf, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def triangle_count(groups):
    return sum(len(indices) // 3 for _, indices in groups)


def generate_all(root: Path):
    manifest = {"schema_version": 1, "generator": "phos-n004-scene-factory-v2", "scenes": {}}
    for label, thickness in (("thin", 0.02), ("medium", 0.10), ("thick", 0.40)):
        groups = leak_scene(thickness)
        path = write_gltf(root, f"leak-{label}", groups)
        manifest["scenes"][f"leak-{label}"] = {
            "path": path.name, "kind": "leak", "wall_thickness_world": thickness,
            "triangles": triangle_count(groups), "mesh_count": len(groups),
            "idle_dynamic_control_triangles": 36,
        }
    for kind in ("sparse", "dense", "large-horizontal", "vertical-tall"):
        groups = world_scene(kind)
        path = write_gltf(root, f"world-{kind}", groups)
        manifest["scenes"][f"world-{kind}"] = {
            "path": path.name, "kind": "world-shape", "layout": kind,
            "triangles": triangle_count(groups), "mesh_count": len(groups),
            "idle_dynamic_control_triangles": 36,
        }
    (root / "n004-scenes.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Generate deterministic N004 synthetic glTF workloads")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = generate_all(args.output_dir.resolve())
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
