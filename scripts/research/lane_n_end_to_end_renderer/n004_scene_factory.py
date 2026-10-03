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
    for offset in (-0.36, 0.0, 0.36):
        add_box(positions, indices, (cx + offset, cy, cz), (0.12, 0.12, 0.12))
    return positions, indices


def base_floor():
    p, i = [], []
    add_grid_floor(p, i, 8.0, 24)
    return p, i


def wall_box(thickness: float):
    p, i = [], []
    add_box(p, i, (0.0, 1.35, 0.0), (thickness * 0.5, 1.35, 2.25))
    add_box(p, i, (0.0, 0.75, -2.75), (0.35, 0.75, 0.35))
    add_box(p, i, (0.0, 0.75,  2.75), (0.35, 0.75, 0.35))
    return p, i


def rotate_y(group, radians: float):
    positions, indices = group
    c, s = math.cos(radians), math.sin(radians)
    rotated = [(x*c + z*s, y, -x*s + z*c) for x, y, z in positions]
    return rotated, list(indices)


def leak_scene(case: str, thickness: float = 0.10):
    floor = base_floor()
    if case in {"thin", "medium", "thick"}:
        geometry = wall_box(thickness)
    elif case == "grazing":
        geometry = rotate_y(wall_box(thickness), math.radians(68.0))
    elif case == "one-sided":
        p, i = [], []
        add_quad(p, i, (0.0,0.0,-2.25),(0.0,0.0,2.25),(0.0,2.7,2.25),(0.0,2.7,-2.25))
        geometry = (p, i)
    elif case == "enclosed":
        p, i = [], []
        add_box(p, i, (0.0, 1.35, 0.0), (thickness * 0.5, 1.35, 2.25))
        # A dark-side enclosure behind the wall: rear, side caps and roof.
        add_box(p, i, (1.55, 1.35, 0.0), (0.08, 1.35, 2.25))
        add_box(p, i, (0.78, 1.35, -2.25), (0.78, 1.35, 0.08))
        add_box(p, i, (0.78, 1.35,  2.25), (0.78, 1.35, 0.08))
        add_box(p, i, (0.78, 2.70, 0.0), (0.78, 0.08, 2.25))
        geometry = (p, i)
    else:
        raise ValueError(f"unknown leak case: {case}")
    return [control_group((-3.35, 0.18, -3.35)), floor, geometry]


def world_scene(kind: str):
    positions, indices = [], []
    if kind == "sparse":
        nx, ny, nz, spacing, half = 8, 1, 8, (5.0, 1.0, 5.0), (0.35, 0.35, 0.35)
    elif kind == "dense":
        nx, ny, nz, spacing, half = 16, 2, 16, (0.65, 0.8, 0.65), (0.28, 0.28, 0.28)
    elif kind == "large-horizontal":
        nx, ny, nz, spacing, half = 32, 1, 4, (2.0, 1.0, 1.5), (0.45, 0.45, 0.45)
    elif kind == "vertical-tall":
        nx, ny, nz, spacing, half = 4, 32, 4, (1.5, 1.6, 1.5), (0.42, 0.42, 0.42)
    else:
        raise ValueError(f"unknown world scene: {kind}")
    ox = -0.5 * (nx - 1) * spacing[0]
    oy = 0.5
    oz = -0.5 * (nz - 1) * spacing[2]
    for y in range(ny):
        for z in range(nz):
            for x in range(nx):
                jitter = 0.07 * math.sin((x + 1) * 1.7 + (z + 1) * 0.9 + y * 0.4)
                add_box(positions, indices, (ox+x*spacing[0], oy+y*spacing[1]+jitter, oz+z*spacing[2]), half)
    return [control_group((ox + 0.2, oy + 0.15, oz + 0.2)), (positions, indices)]


def write_gltf(root: Path, name: str, groups):
    root.mkdir(parents=True, exist_ok=True)
    binary = bytearray(); buffer_views = []; accessors = []; meshes = []; nodes = []
    for mesh_index, (positions, indices) in enumerate(groups):
        while len(binary) % 4: binary.append(0)
        position_offset = len(binary)
        for p in positions: binary.extend(struct.pack("<3f", *p))
        position_view = len(buffer_views)
        buffer_views.append({"buffer":0,"byteOffset":position_offset,"byteLength":len(positions)*12,"target":34962})
        xs=[p[0] for p in positions]; ys=[p[1] for p in positions]; zs=[p[2] for p in positions]
        position_accessor=len(accessors)
        accessors.append({"bufferView":position_view,"byteOffset":0,"componentType":5126,"count":len(positions),"type":"VEC3","min":[min(xs),min(ys),min(zs)],"max":[max(xs),max(ys),max(zs)]})
        while len(binary) % 4: binary.append(0)
        index_offset=len(binary)
        for value in indices: binary.extend(struct.pack("<I", value))
        index_view=len(buffer_views)
        buffer_views.append({"buffer":0,"byteOffset":index_offset,"byteLength":len(indices)*4,"target":34963})
        index_accessor=len(accessors)
        accessors.append({"bufferView":index_view,"byteOffset":0,"componentType":5125,"count":len(indices),"type":"SCALAR","min":[min(indices)],"max":[max(indices)]})
        meshes.append({"primitives":[{"attributes":{"POSITION":position_accessor},"indices":index_accessor}]})
        nodes.append({"mesh":mesh_index})
    bin_name=f"{name}.bin"
    gltf={"asset":{"version":"2.0","generator":"phos-n004-scene-factory-v3"},"buffers":[{"uri":bin_name,"byteLength":len(binary)}],"bufferViews":buffer_views,"accessors":accessors,"meshes":meshes,"nodes":nodes,"scenes":[{"nodes":list(range(len(nodes)))}],"scene":0}
    (root/bin_name).write_bytes(binary)
    path=root/f"{name}.gltf"; path.write_text(json.dumps(gltf,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return path


def triangle_count(groups):
    return sum(len(indices)//3 for _,indices in groups)


def generate_all(root: Path):
    manifest={"schema_version":1,"generator":"phos-n004-scene-factory-v3","scenes":{}}
    leak_specs=(("thin",0.02),("medium",0.10),("thick",0.40),("grazing",0.10),("one-sided",0.0),("enclosed",0.10))
    for case, thickness in leak_specs:
        groups=leak_scene(case, max(thickness,0.10) if case=="one-sided" else thickness)
        name=f"leak-{case}"; path=write_gltf(root,name,groups)
        manifest["scenes"][name]={"path":path.name,"kind":"leak","geometry_case":case,"wall_thickness_world":thickness,"triangles":triangle_count(groups),"mesh_count":len(groups),"idle_dynamic_control_triangles":36}
    for kind in ("sparse","dense","large-horizontal","vertical-tall"):
        groups=world_scene(kind); name=f"world-{kind}"; path=write_gltf(root,name,groups)
        manifest["scenes"][name]={"path":path.name,"kind":"world-shape","layout":kind,"triangles":triangle_count(groups),"mesh_count":len(groups),"idle_dynamic_control_triangles":36}
    (root/"n004-scenes.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return manifest


def main():
    parser=argparse.ArgumentParser(description="Generate deterministic N004 synthetic glTF workloads")
    parser.add_argument("--output-dir",type=Path,required=True)
    args=parser.parse_args(); print(json.dumps(generate_all(args.output_dir.resolve()),indent=2,sort_keys=True))


if __name__ == "__main__":
    main()
