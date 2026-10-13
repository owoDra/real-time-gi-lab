#!/usr/bin/env python3
"""N009 preregistered, geometry/direct-only selection of the C1 contract values
(experiments/001 §C1). No GPU image, no indirect/total image and no quality metric
is read. Steps:
  1. authored camera = first camera node of the glTF default scene (asset-defined);
  2. light candidates L1..L7 (fractions of the C1 world vertex bounds), in order;
     gate G-L1 free space: min distance light->any triangle >= 2 s (s = light scale);
     gate G-L2 direct support (oracle, direct only, pixel centre, deterministic):
       >= 64 px, >= 1 % of pixels, peak Y >= 1e-4;
     base light = first passing candidate; light-motion light = next passing
     candidate at distance >= 0.1 * diag from the base light;
  3. camera-motion offsets +right, -right, +forward, -forward with |offset| =
     0.02 * diag; gate G-C1 free space: min distance moved eye->triangle >= 2 s;
     first passing offset is used.
Writes the contract file and a JSON selection record."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "n008_hdr_oracle"))
import n008lib as L  # noqa: E402

LUMA = np.array((0.2126, 0.7152, 0.0722))
LIGHT_FRACTIONS = [  # (x, y, z) fractions of the world vertex bounds, preregistered order
    ("L1", 0.50, 0.50, 0.50), ("L2", 0.50, 0.35, 0.50), ("L3", 0.75, 0.50, 0.50), ("L4", 0.25, 0.50, 0.50),
    ("L5", 0.50, 0.65, 0.50), ("L6", 0.75, 0.35, 0.50), ("L7", 0.25, 0.35, 0.50),
]
CAMERA_OFFSETS = [("+right", 0, 1.0), ("-right", 0, -1.0), ("+forward", 2, 1.0), ("-forward", 2, -1.0)]


def f32(v):
    return [float(np.float32(x)) for x in v]


def write_contract(path: Path, eye, offset, base, motion):
    lines = ["n009contract 1"]
    for key, v in (("authored_eye", eye), ("camera_motion_offset", offset), ("light_base", base), ("light_motion", motion)):
        lines.append(key + " " + " ".join(f"{np.float32(x):.9g}" for x in v))
    path.write_text("\n".join(lines) + "\n")


def point_triangle_distance(p, a, b, c):
    """Vectorised Ericson closest-point distance from point p to triangles (a,b,c)."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = np.einsum("ij,ij->i", ab, ap), np.einsum("ij,ij->i", ac, ap)
    bp = p - b
    d3, d4 = np.einsum("ij,ij->i", ab, bp), np.einsum("ij,ij->i", ac, bp)
    cp = p - c
    d5, d6 = np.einsum("ij,ij->i", ab, cp), np.einsum("ij,ij->i", ac, cp)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    denom = va + vb + vc
    with np.errstate(divide="ignore", invalid="ignore"):
        v = vb / denom
        w = vc / denom
    q = a + ab * v[:, None] + ac * w[:, None]  # interior
    def put(mask, val):
        q[mask] = val[mask]
    with np.errstate(divide="ignore", invalid="ignore"):
        put((vc <= 0) & (d1 >= 0) & (d3 <= 0), a + ab * (d1 / (d1 - d3))[:, None])
        put((vb <= 0) & (d2 >= 0) & (d6 <= 0), a + ac * (d2 / (d2 - d6))[:, None])
        put((va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0), b + (c - b) * ((d4 - d3) / ((d4 - d3) + (d5 - d6)))[:, None])
    put((d1 <= 0) & (d2 <= 0), a)
    put((d3 >= 0) & (d4 <= d3), b)
    put((d6 >= 0) & (d5 <= d6), c)
    return float(np.min(np.linalg.norm(q - p, axis=1)))


def authored_eye(gltf: Path):
    g = json.loads(gltf.read_text())
    scene = g["scenes"][g.get("scene", 0)]
    for i in scene["nodes"]:  # Sponza nodes are roots; nested cameras are rejected here.
        n = g["nodes"][i]
        if "camera" in n:
            if "children" in n or "matrix" in n or "scale" in n:
                raise SystemExit("unsupported authored camera node layout")
            return f32(n.get("translation", (0.0, 0.0, 0.0)))
    raise SystemExit("no authored camera")


def export(exporter: Path, scene: Path, contract: Path, regime: str, out: Path) -> dict:
    proc = subprocess.run([str(exporter), "--scene", str(scene), "--out", str(out), "--regime", regime],
                          check=True, capture_output=True, text=True, env={"PHOS_N009_CONTRACT": str(contract)})
    return json.loads(proc.stdout)


def direct_support(state_dir: Path, work: Path) -> dict:
    st = L.read_state(state_dir)
    sc = L.state_scene(st, max_bounces=1)
    meta = L.run_oracle(sc, work, "direct", seeds=(L.N007_SEEDS[0],), spp=1)
    y = L.read_sidecar(Path(meta["runs"][0]["prefix"] + ".f64"))["mean"][..., 1, :] @ LUMA
    n = y.size
    pos = int((y > 0).sum())
    return {"positive": pos, "fraction": pos / n, "peak_y": float(y.max()),
            "passes": pos >= 64 and pos / n >= 0.01 and float(y.max()) >= 1e-4}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scene", type=Path, default=L.ROOT / "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf")
    ap.add_argument("--exporter", type=Path, default=L.ROOT / "build/n009/src/research/n009_scene_contract/n009_state_export")
    ap.add_argument("--work", type=Path, default=L.ROOT / "out/research/n009-scene-contract/selection")
    ap.add_argument("--contract", type=Path, required=True)
    ap.add_argument("--record", type=Path, required=True)
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    eye = authored_eye(a.scene)
    zero = [0.0, 0.0, 0.0]
    probe_contract = a.work / "probe.n009contract"
    write_contract(probe_contract, eye, zero, eye, eye)
    base_info = export(a.exporter, a.scene, probe_contract, "static", a.work / "geometry")
    st = L.read_state(a.work / "geometry")
    tri = st["verts"]
    lo, hi = tri.reshape(-1, 3).min(0), tri.reshape(-1, 3).max(0)
    diag = float(np.linalg.norm(hi - lo))
    s = float(st["light_pos_interval"][3])
    A, B, C = tri[:, 0], tri[:, 1], tri[:, 2]
    record = {"schema": "n009-contract-selection/1", "scene_sha256": L.hashlib.sha256(a.scene.read_bytes()).hexdigest(),
              "authored_eye": eye, "world_vertex_bounds": [lo.tolist(), hi.tolist()], "diag": diag, "light_scale_s": s,
              "authored_eye_min_distance": point_triangle_distance(np.array(eye, float), A, B, C),
              "exporter": base_info, "lights": [], "camera_offsets": []}
    passing = []
    for name, fx, fy, fz in LIGHT_FRACTIONS:
        pos = f32(lo + (hi - lo) * np.array((fx, fy, fz)))
        dist = point_triangle_distance(np.array(pos, float), A, B, C)
        row = {"name": name, "position": pos, "min_distance": dist, "free_space": dist >= 2 * s}
        if row["free_space"]:
            c = a.work / f"{name}.n009contract"
            write_contract(c, eye, zero, pos, pos)
            export(a.exporter, a.scene, c, "static", a.work / f"state-{name}")
            row["direct"] = direct_support(a.work / f"state-{name}", a.work / f"oracle-{name}")
            if row["direct"]["passes"]:
                passing.append(row)
        record["lights"].append(row)
    if not passing:
        record["outcome"] = "NO_LIGHT_PASSES_GATES"
        a.record.write_text(json.dumps(record, indent=1) + "\n")
        raise SystemExit("no light candidate passes the preregistered gates")
    base = passing[0]
    motion = next((r for r in passing[1:] if math.dist(r["position"], base["position"]) >= 0.1 * diag), None)
    right = st["camera_right_tan_x"][:3].astype(float)
    fwd = st["camera_forward_far"][:3].astype(float)
    chosen = None
    for name, axis, sign in CAMERA_OFFSETS:
        vec = (right if axis == 0 else fwd) * sign * 0.02 * diag
        off = f32(vec)
        moved = np.array(eye, float) + np.array(off, float)
        dist = point_triangle_distance(moved, A, B, C)
        record["camera_offsets"].append({"name": name, "offset": off, "min_distance": dist, "free_space": dist >= 2 * s})
        if chosen is None and dist >= 2 * s:
            chosen = off
    record["selected"] = {"light_base": base["name"], "light_motion": motion["name"] if motion else None,
                          "camera_motion_offset": chosen}
    if motion is None or chosen is None:
        record["outcome"] = "INCOMPLETE_CONTRACT"
        a.record.write_text(json.dumps(record, indent=1) + "\n")
        raise SystemExit("light-motion or camera-motion selection failed the preregistered gates")
    write_contract(a.contract, eye, chosen, base["position"], motion["position"])
    record["outcome"] = "CONTRACT_SELECTED"
    record["contract_text"] = a.contract.read_text()
    a.record.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record["selected"]))


if __name__ == "__main__":
    main()
