"""N008 shared helpers: scene authoring, canonical geometry hash, oracle I/O and
independent analytic geometry (numpy). Nothing here is derived from oracle code
paths; expected values use closed forms on analytic primitives."""
from __future__ import annotations

import hashlib
import json
import math
import struct
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
N007_SEEDS = (305419896, 2596069104, 81985529216486895, 18364758544493064720)
COMPONENTS = ("emission", "direct", "indirect", "total")


# --------------------------------------------------------------------------- scene
@dataclass
class Camera:
    origin: tuple
    target: tuple
    up: tuple = (0.0, 1.0, 0.0)
    tan_x: float = 0.8
    tan_y: float = 0.6
    near: float = 0.0
    far: float = math.inf

    @property
    def forward(self):
        f = np.subtract(self.target, self.origin).astype(float)
        return f / np.linalg.norm(f)


@dataclass
class Scene:
    camera: Camera
    width: int = 128
    height: int = 96
    sampling: str = "center"
    max_bounces: int = 1
    falloff: str = "inverse_square"
    soft_scale: float = 0.0
    secondary_far: str = "inf"
    materials: dict = field(default_factory=dict)  # name -> (rho, emit, two_sided)
    triangles: list = field(default_factory=list)  # (mat, v0, v1, v2)
    points: list = field(default_factory=list)  # (pos, intensity)

    def material(self, name, rho, emit=(0.0, 0.0, 0.0), two_sided=True):
        self.materials[name] = (tuple(map(float, rho)), tuple(map(float, emit)), bool(two_sided))
        return name

    def tri(self, mat, v0, v1, v2):
        self.triangles.append((mat, tuple(map(float, v0)), tuple(map(float, v1)), tuple(map(float, v2))))

    def quad(self, mat, p0, eu, ev):
        """Parallelogram p0, p0+eu, p0+eu+ev, p0+ev; front normal = eu x ev."""
        p0 = np.asarray(p0, float); eu = np.asarray(eu, float); ev = np.asarray(ev, float)
        a, b, c, d = p0, p0 + eu, p0 + eu + ev, p0 + ev
        self.tri(mat, a, b, c)
        self.tri(mat, a, c, d)

    def point(self, pos, intensity):
        self.points.append((tuple(map(float, pos)), tuple(map(float, intensity))))

    def text(self) -> str:
        c = self.camera
        f = c.forward
        far = "inf" if math.isinf(c.far) else repr(float(c.far))
        lines = [
            "n008scene 1",
            f"resolution {self.width} {self.height}",
            "camera " + " ".join(repr(float(v)) for v in (*c.origin, *f, *c.up, c.tan_x, c.tan_y, c.near)) + f" {far}",
            f"sampling {self.sampling}",
            f"max_bounces {self.max_bounces}",
            "falloff inverse_square" if self.falloff == "inverse_square" else f"falloff n001_soft {self.soft_scale!r}",
            f"secondary_far {self.secondary_far}",
        ]
        for name, (rho, emit, two) in self.materials.items():
            lines.append(f"material {name} " + " ".join(repr(v) for v in (*rho, *emit)) + f" {int(two)}")
        for pos, inten in self.points:
            lines.append("point " + " ".join(repr(v) for v in (*pos, *inten)))
        for mat, v0, v1, v2 in self.triangles:
            lines.append(f"tri {mat} " + " ".join(repr(v) for v in (*v0, *v1, *v2)))
        return "\n".join(lines) + "\n"

    def geometry_sha256(self) -> str:
        """Same canonical bytes as the oracle: 9 float64 LE + uint32 material index."""
        index = {name: i for i, name in enumerate(self.materials)}
        h = hashlib.sha256()
        for mat, v0, v1, v2 in self.triangles:
            h.update(struct.pack("<9dI", *v0, *v1, *v2, index[mat]))
        return h.hexdigest()


# --------------------------------------------------------------------------- oracle I/O
def oracle_binary() -> Path:
    for cand in (ROOT / "build/n008/n008_oracle", ROOT / "build/release/src/research/n008_hdr_oracle/n008_oracle"):
        if cand.exists():
            return cand
    raise SystemExit("n008_oracle not built: cmake -S src/research/n008_hdr_oracle -B build/n008 && cmake --build build/n008")


def run_oracle(scene: Scene, out_dir: Path, name: str, seeds=N007_SEEDS, spp=1) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    scene_path = out_dir / f"{name}.n008"
    scene_path.write_text(scene.text())
    proc = subprocess.run(
        [str(oracle_binary()), "--scene", str(scene_path), "--out", str(out_dir / name),
         "--seeds", ",".join(map(str, seeds)), "--spp", str(spp)],
        check=True, capture_output=True, text=True)
    meta = json.loads(proc.stdout)
    meta["expected_geometry_sha256"] = scene.geometry_sha256()
    meta["geometry_hash_match"] = meta["geometry_sha256"] == meta["expected_geometry_sha256"]
    meta["scene_file_sha256_python"] = hashlib.sha256(scene_path.read_bytes()).hexdigest()
    return meta


def read_sidecar(path: Path):
    raw = path.read_bytes()
    if raw[:8] != b"N008F64\0":
        raise ValueError(f"{path}: bad sidecar magic")
    w, h, spp = struct.unpack_from("<3I", raw, 8)
    (seed,) = struct.unpack_from("<Q", raw, 20)
    data = np.frombuffer(raw, dtype="<f8", offset=28).reshape(h, w, 24)
    mean = data[..., :12].reshape(h, w, 4, 3)
    m2 = data[..., 12:].reshape(h, w, 4, 3)
    return {"width": w, "height": h, "spp": spp, "seed": seed, "mean": mean, "m2": m2}


def pooled(meta: dict) -> dict:
    """Pool per-seed moments (equal spp): mean, per-sample variance, SE of mean."""
    runs = [read_sidecar(Path(r["prefix"] + ".f64")) for r in meta["runs"]]
    n = sum(r["spp"] for r in runs)
    mean = sum(r["mean"] for r in runs) / len(runs)
    m2 = sum(r["m2"] for r in runs) / len(runs)
    var = np.maximum(m2 - mean * mean, 0.0)
    return {"mean": mean, "se": np.sqrt(var / n), "n": n, "per_seed": runs}


def read_pfm(path: Path) -> np.ndarray:
    raw = path.read_bytes()
    parts = raw.split(b"\n", 3)
    assert parts[0].strip() == b"PF"
    w, h = map(int, parts[1].split())
    scale = float(parts[2])
    data = np.frombuffer(parts[3], dtype="<f4" if scale < 0 else ">f4").reshape(h, w, 3)
    return data[::-1].astype(np.float64)  # top-down


# --------------------------------------------------------------------------- analytic geometry
def camera_rays(cam: Camera, width: int, height: int):
    """Pixel-centre directions per the specification (independent of oracle code)."""
    f = cam.forward
    r = np.cross(f, cam.up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    xs = (np.arange(width) + 0.5) * 2.0 / width - 1.0
    ys = 1.0 - (np.arange(height) + 0.5) * 2.0 / height
    nx, ny = np.meshgrid(xs, ys)
    d = f[None, None, :] + r[None, None, :] * (nx * cam.tan_x)[..., None] + u[None, None, :] * (ny * cam.tan_y)[..., None]
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    return np.asarray(cam.origin, float), d


def ray_parallelogram(o, d, p0, eu, ev):
    """Returns t (inf on miss) and boundary margin in world units (>=0 inside)."""
    p0 = np.asarray(p0, float); eu = np.asarray(eu, float); ev = np.asarray(ev, float)
    n = np.cross(eu, ev)
    denom = d @ n
    with np.errstate(divide="ignore", invalid="ignore"):
        t = ((p0 - o) @ n) / denom if o.ndim == 1 else np.einsum("...k,k->...", p0 - o, n) / denom
    p = o + d * t[..., None]
    q = p - p0
    # Solve q = a*eu + b*ev in the plane.
    g = np.array([[eu @ eu, eu @ ev], [eu @ ev, ev @ ev]])
    gi = np.linalg.inv(g)
    qa = q @ eu; qb = q @ ev
    a = gi[0, 0] * qa + gi[0, 1] * qb
    b = gi[1, 0] * qa + gi[1, 1] * qb
    margin = np.minimum.reduce([a * np.linalg.norm(eu), (1 - a) * np.linalg.norm(eu), b * np.linalg.norm(ev), (1 - b) * np.linalg.norm(ev)])
    ok = np.isfinite(t) & (t > 0) & (margin >= 0)
    return np.where(ok, t, np.inf), np.where(np.isfinite(t) & (t > 0), margin, np.inf), n / np.linalg.norm(n)


def ray_obb(o, d, center, axes, half):
    """Slab test against oriented box. Returns (t_enter, t_exit) arrays; miss if t_enter > t_exit."""
    center = np.asarray(center, float)
    t0 = np.full(d.shape[:-1], -np.inf); t1 = np.full(d.shape[:-1], np.inf)
    rel = center - o
    for ax, h in zip(axes, half):
        ax = np.asarray(ax, float)
        e = rel @ ax if rel.ndim == 1 else np.einsum("...k,k->...", rel, ax)
        f = d @ ax
        with np.errstate(divide="ignore", invalid="ignore"):
            ta = (e - h) / f
            tb = (e + h) / f
        lo = np.minimum(ta, tb); hi = np.maximum(ta, tb)
        par = f == 0
        inside = np.abs(e) <= h
        lo = np.where(par, np.where(inside, -np.inf, np.inf), lo)
        hi = np.where(par, np.where(inside, np.inf, -np.inf), hi)
        t0 = np.maximum(t0, lo); t1 = np.minimum(t1, hi)
    return t0, t1


def segment_blocked_obb(p, light, center, axes, half):
    """Visibility of segment p->light against an OBB; returns (blocked, margin)."""
    v = np.asarray(light, float) - p
    dist = np.linalg.norm(v, axis=-1)
    d = v / dist[..., None]
    t0, t1 = ray_obb(p, d, center, axes, half)
    lo = np.maximum(t0, 0.0); hi = np.minimum(t1, dist)
    overlap = hi - lo  # >0 penetrates, <0 clear
    return overlap > 0, np.abs(overlap)


def box_triangles(scene: Scene, mat, center, axes, half):
    """12 outward-wound triangles for an oriented box."""
    c = np.asarray(center, float)
    ax = [np.asarray(a, float) * h for a, h in zip(axes, half)]
    for i in range(3):
        j, k = (i + 1) % 3, (i + 2) % 3
        for s in (1.0, -1.0):
            fc = c + s * ax[i]
            eu, ev = (ax[j] * 2, ax[k] * 2) if s > 0 else (ax[k] * 2, ax[j] * 2)
            scene.quad(mat, fc - eu / 2 - ev / 2, eu, ev)


def icosphere(level: int, radius: float = 1.0):
    t = (1.0 + 5 ** 0.5) / 2.0
    verts = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
             (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    verts = [np.array(v, float) / np.linalg.norm(v) for v in verts]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
             (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
             (8, 6, 7), (9, 8, 1)]
    for _ in range(level):
        cache = {}
        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                m = verts[a] + verts[b]
                verts.append(m / np.linalg.norm(m))
                cache[key] = len(verts) - 1
            return cache[key]
        nf = []
        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = nf
    v = np.array(verts) * radius
    return v, np.array(faces)


def sphere_mesh_bounds(v, f, radius=1.0):
    """Max facet-normal deviation (rad) and max sagitta of a sphere-inscribed mesh."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.cross(b - a, c - a); n /= np.linalg.norm(n, axis=1, keepdims=True)
    dev = 0.0
    for p in (a, b, c):
        cosang = np.abs(np.sum(n * p / radius, axis=1))
        dev = max(dev, float(np.max(np.arccos(np.clip(cosang, -1, 1)))))
    plane_dist = np.abs(np.sum(n * a, axis=1))
    return dev, float(radius - plane_dist.min())


def rect_point_form_factor(px, pz, h, x1, x2, z1, z2):
    """Point-to-parallel-rectangle form factor (rectangle at height h over the receiver
    point, both normals facing each other), by signed corner superposition."""
    def corner(a, b):
        A = np.abs(a) / h; B = np.abs(b) / h
        sa = np.sqrt(1 + A * A); sb = np.sqrt(1 + B * B)
        val = (A / sa * np.arctan(B / sa) + B / sb * np.arctan(A / sb)) / (2 * np.pi)
        return np.sign(a) * np.sign(b) * val
    return corner(x2 - px, z2 - pz) - corner(x1 - px, z2 - pz) - corner(x2 - px, z1 - pz) + corner(x1 - px, z1 - pz)


def gauss_legendre_square(x0, x1, z0, z1, panels, order):
    g, w = np.polynomial.legendre.leggauss(order)
    edges_x = np.linspace(x0, x1, panels + 1); edges_z = np.linspace(z0, z1, panels + 1)
    xs, wx = [], []
    for a, b in zip(edges_x[:-1], edges_x[1:]):
        xs.append((b - a) / 2 * g + (a + b) / 2); wx.append((b - a) / 2 * w)
    zs, wz = [], []
    for a, b in zip(edges_z[:-1], edges_z[1:]):
        zs.append((b - a) / 2 * g + (a + b) / 2); wz.append((b - a) / 2 * w)
    xs = np.concatenate(xs); wx = np.concatenate(wx); zs = np.concatenate(zs); wz = np.concatenate(wz)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    W = np.outer(wx, wz)
    return X.ravel(), Z.ravel(), W.ravel()
