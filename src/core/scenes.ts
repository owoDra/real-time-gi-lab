// S2 scenes: Sponza, Sponza made 10x wider (ten copies in a row) or 10x denser (every triangle split into
// nine with the same surface), and enclosed leak rooms after N004 (legacy/scenes/n004_scene_factory.py).
// S3: Sponza with toon objects (saturated, untextured, toon style) standing on the atrium floor in the sun.
import { s0Camera } from './bench.ts';
import type { Camera } from './frame.ts';
import type { MaterialDesc, SceneData } from './gltf.ts';
import { add3, cross, normalize, scale3, type Vec3 } from './math.ts';

export interface SceneSpec {
  name: string;
  scene: SceneData;
  camera: Camera;
  /** Moving camera, or null when only the static camera is measured. */
  moving: boolean;
  sunDir: Vec3;
  /** Leak scenes: every visible point is enclosed, so all indirect irradiance is leakage. */
  enclosed: boolean;
  /** M1: fully dynamic scenes. Rigid objects (vertex ranges at the end of the vertex buffer; their triangles are
   * the last ones of the triangle table, from firstTriangle on) and the sun move with the frame number. */
  dynamic?: DynamicSpec;
}

export interface DynamicObject { firstVertex: number; vertexCount: number; pivot: Vec3; }
export interface DynamicPose { sunDir: Vec3; sunScale: number; poses: { rotY: number; offset: Vec3 }[]; }
export interface DynamicSpec {
  firstTriangle: number;
  objects: DynamicObject[];
  /** Pose of every object (rotation about the vertical axis through its pivot, then a translation) and the sun. */
  at(frame: number): DynamicPose;
}

/** Positions and normals of the dynamic vertices at a pose (rest data from `scene`), packed for the vertex buffers. */
export function posedVertices(scene: SceneData, d: DynamicSpec, pose: DynamicPose) {
  const first = d.objects[0].firstVertex;
  const last = d.objects[d.objects.length - 1].firstVertex + d.objects[d.objects.length - 1].vertexCount;
  const pos = new Float32Array((last - first) * 3), nrm = new Float32Array((last - first) * 3);
  d.objects.forEach((o, i) => {
    const { rotY, offset } = pose.poses[i];
    const c = Math.cos(rotY), s = Math.sin(rotY);
    for (let v = o.firstVertex; v < o.firstVertex + o.vertexCount; v++) {
      const x = scene.positions[v * 3] - o.pivot[0], y = scene.positions[v * 3 + 1] - o.pivot[1], z = scene.positions[v * 3 + 2] - o.pivot[2];
      const q = (v - first) * 3;
      pos[q] = o.pivot[0] + c * x + s * z + offset[0]; pos[q + 1] = o.pivot[1] + y + offset[1]; pos[q + 2] = o.pivot[2] - s * x + c * z + offset[2];
      const nx = scene.normals[v * 3], ny = scene.normals[v * 3 + 1], nz = scene.normals[v * 3 + 2];
      nrm[q] = c * nx + s * nz; nrm[q + 1] = ny; nrm[q + 2] = -s * nx + c * nz;
    }
  });
  return { first, pos, nrm };
}

export const SPONZA_SUN: Vec3 = [-0.15, 1, 0.1];

function bounds(pos: Float32Array): [Vec3, Vec3] {
  const mn: Vec3 = [Infinity, Infinity, Infinity], mx: Vec3 = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < pos.length; i += 3)
    for (let a = 0; a < 3; a++) { mn[a] = Math.min(mn[a], pos[i + a]); mx[a] = Math.max(mx[a], pos[i + a]); }
  return [mn, mx];
}

export function sponzaSpec(scene: SceneData): SceneSpec {
  return { name: 'sponza', scene, camera: s0Camera(scene), moving: true, sunDir: SPONZA_SUN, enclosed: false };
}

/** n copies along +x, 2 m apart. The camera stays in the first copy. */
export function widen(base: SceneData, n: number): SceneSpec {
  const V = base.positions.length / 3, I = base.indices.length;
  const dx = base.boundsMax[0] - base.boundsMin[0] + 2;
  const positions = new Float32Array(V * 3 * n), normals = new Float32Array(V * 3 * n), uvs = new Float32Array(V * 2 * n);
  const tangents = new Float32Array(V * 4 * n), indices = new Uint32Array(I * n);
  const primitives: SceneData['primitives'] = [];
  for (let k = 0; k < n; k++) {
    for (let i = 0; i < V; i++) {
      positions[(k * V + i) * 3] = base.positions[i * 3] + k * dx;
      positions[(k * V + i) * 3 + 1] = base.positions[i * 3 + 1];
      positions[(k * V + i) * 3 + 2] = base.positions[i * 3 + 2];
    }
    normals.set(base.normals, k * V * 3); uvs.set(base.uvs, k * V * 2); tangents.set(base.tangents, k * V * 4);
    indices.set(base.indices, k * I);
    for (const p of base.primitives) primitives.push({ ...p, firstIndex: p.firstIndex + k * I, baseVertex: p.baseVertex + k * V });
  }
  const [boundsMin, boundsMax] = bounds(positions);
  const scene: SceneData = { ...base, positions, normals, uvs, tangents, indices, primitives, boundsMin, boundsMax, triangleCount: base.triangleCount * n };
  return { name: `sponza-wide${n}`, scene, camera: s0Camera(base), moving: true, sunDir: SPONZA_SUN, enclosed: false };
}

/** Every triangle split into 9 (edges in thirds): same surface, 9x the triangles. */
export function densify(base: SceneData): SceneSpec {
  const T = base.triangleCount;
  const positions = new Float32Array(T * 10 * 3), normals = new Float32Array(T * 10 * 3), uvs = new Float32Array(T * 10 * 2);
  const tangents = new Float32Array(T * 10 * 4), indices = new Uint32Array(T * 27);
  const primitives: SceneData['primitives'] = [];
  // Barycentric grid of degree 3: point (i, j), i + j <= 3.
  const pts: [number, number][] = [];
  for (let j = 0; j <= 3; j++) for (let i = 0; i <= 3 - j; i++) pts.push([i, j]);
  const at = (i: number, j: number) => pts.findIndex(([a, b]) => a === i && b === j);
  const local: number[] = [];
  for (let j = 0; j < 3; j++)
    for (let i = 0; i < 3 - j; i++) {
      local.push(at(i, j), at(i + 1, j), at(i, j + 1));
      if (i + j < 2) local.push(at(i + 1, j), at(i + 1, j + 1), at(i, j + 1));
    }
  let t = 0;
  for (const p of base.primitives) {
    const firstIndex = t * 27;
    for (let k = p.firstIndex; k < p.firstIndex + p.indexCount; k += 3, t++) {
      const v = [0, 1, 2].map((q) => base.indices[k + q] + p.baseVertex);
      pts.forEach(([i, j], n) => {
        const w = [1 - (i + j) / 3, i / 3, j / 3];
        const o = t * 10 + n;
        for (let a = 0; a < 3; a++) {
          positions[o * 3 + a] = w[0] * base.positions[v[0] * 3 + a] + w[1] * base.positions[v[1] * 3 + a] + w[2] * base.positions[v[2] * 3 + a];
          normals[o * 3 + a] = w[0] * base.normals[v[0] * 3 + a] + w[1] * base.normals[v[1] * 3 + a] + w[2] * base.normals[v[2] * 3 + a];
        }
        for (let a = 0; a < 2; a++) uvs[o * 2 + a] = w[0] * base.uvs[v[0] * 2 + a] + w[1] * base.uvs[v[1] * 2 + a] + w[2] * base.uvs[v[2] * 2 + a];
        for (let a = 0; a < 4; a++) tangents[o * 4 + a] = w[0] * base.tangents[v[0] * 4 + a] + w[1] * base.tangents[v[1] * 4 + a] + w[2] * base.tangents[v[2] * 4 + a];
      });
      local.forEach((l, q) => { indices[t * 27 + q] = t * 10 + l; });
    }
    primitives.push({ firstIndex, indexCount: t * 27 - firstIndex, baseVertex: 0, material: p.material });
  }
  const scene: SceneData = { ...base, positions, normals, uvs, tangents, indices, primitives, triangleCount: T * 9 };
  return { name: 'sponza-dense9', scene, camera: s0Camera(base), moving: true, sunDir: SPONZA_SUN, enclosed: false };
}

const GREY: MaterialDesc = { name: 'grey', baseColorFactor: [0.7, 0.7, 0.7, 1], baseColorImage: -1, normalImage: -1, metallicRoughnessImage: -1,
  metallicFactor: 0, roughnessFactor: 1, alphaMask: false, alphaCutoff: 0.5, doubleSided: false };

class Builder {
  pos: number[] = []; nrm: number[] = []; idx: number[] = [];
  quad(a: Vec3, b: Vec3, c: Vec3, d: Vec3) {
    const e1 = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], e2 = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    const n = normalize([e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]);
    const base = this.pos.length / 3;
    for (const p of [a, b, c, d]) { this.pos.push(...p); this.nrm.push(...n); }
    this.idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
  /** Axis-aligned box with outward faces. */
  box(c: Vec3, h: Vec3) {
    const [x0, y0, z0] = [c[0] - h[0], c[1] - h[1], c[2] - h[2]], [x1, y1, z1] = [c[0] + h[0], c[1] + h[1], c[2] + h[2]];
    this.quad([x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]);
    this.quad([x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0]);
    this.quad([x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]);
    this.quad([x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1]);
    this.quad([x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0]);
    this.quad([x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]);
  }
  scene(): SceneData {
    const positions = new Float32Array(this.pos);
    const [boundsMin, boundsMax] = bounds(positions);
    const V = positions.length / 3;
    return { positions, normals: new Float32Array(this.nrm), uvs: new Float32Array(V * 2), tangents: new Float32Array(V * 4),
      indices: new Uint32Array(this.idx), primitives: [{ firstIndex: 0, indexCount: this.idx.length, baseVertex: 0, material: 0 }],
      materials: [GREY], imageUris: [], boundsMin, boundsMax, triangleCount: this.idx.length / 3 };
  }
}

/** A closed room (inside x 0..3, y 0..2.7, z -2.25..2.25) whose walls and roof are `t` thick, on an 8 m floor
 * made of 24 x 24 cells. The sun is low on the -x side, so the -x wall and the roof are lit from outside.
 * Nothing inside can be lit: every bit of indirect light seen by the camera is leakage. */
export function leakRoom(t: number): SceneSpec {
  const b = new Builder();
  const cells = 24, size = 8, step = size / cells;
  for (let z = 0; z < cells; z++)
    for (let x = 0; x < cells; x++) {
      const x0 = -size / 2 + 1.5 + x * step, z0 = -size / 2 + z * step;
      b.quad([x0, 0, z0 + step], [x0 + step, 0, z0 + step], [x0 + step, 0, z0], [x0, 0, z0]);
    }
  const W = 3, H = 2.7, D = 2.25;
  b.box([-t / 2, H / 2, 0], [t / 2, H / 2, D + t]);           // -x wall (sun side)
  b.box([W + t / 2, H / 2, 0], [t / 2, H / 2, D + t]);        // +x wall
  b.box([W / 2, H / 2, -D - t / 2], [W / 2, H / 2, t / 2]);   // -z wall
  b.box([W / 2, H / 2, D + t / 2], [W / 2, H / 2, t / 2]);    // +z wall
  b.box([W / 2, H + t / 2, 0], [W / 2 + t, t / 2, D + t]);    // roof
  const scene = b.scene();
  return { name: `leak-${t}`, scene, camera: { eye: [2.6, 1.6, 1.8], target: [0.2, 1.0, -1.4], fovYDeg: 75, near: 0.05 },
    moving: false, sunDir: [-1, 1.1, 0.35], enclosed: true };
}

/** Smooth closed surface over a (u, v) grid, u wrapping; f returns position and outward normal. Each triangle is
 * wound counter-clockwise seen from outside (the G-buffer flips the normal of back faces, double-sided or not). */
function surface(nu: number, nv: number, f: (u: number, v: number) => [Vec3, Vec3]) {
  const pos: number[] = [], nrm: number[] = [], idx: number[] = [];
  for (let j = 0; j <= nv; j++)
    for (let i = 0; i <= nu; i++) { const [p, n] = f(i / nu, j / nv); pos.push(...p); nrm.push(...normalize(n)); }
  const at = (i: number, j: number) => j * (nu + 1) + i;
  const tri = (a: number, b: number, c: number) => {
    const P = (k: number): Vec3 => [pos[k * 3], pos[k * 3 + 1], pos[k * 3 + 2]];
    const [pa, pb, pc] = [P(a), P(b), P(c)];
    const g = cross([pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]], [pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2]]);
    const n = [0, 1, 2].map((q) => nrm[a * 3 + q] + nrm[b * 3 + q] + nrm[c * 3 + q]);
    if (g[0] * n[0] + g[1] * n[1] + g[2] * n[2] >= 0) idx.push(a, b, c); else idx.push(a, c, b);
  };
  for (let j = 0; j < nv; j++)
    for (let i = 0; i < nu; i++) { tri(at(i, j), at(i, j + 1), at(i + 1, j + 1)); tri(at(i, j), at(i + 1, j + 1), at(i + 1, j)); }
  return { pos, nrm, idx };
}
/** Surface of revolution about the y axis through c. profile(v) -> [radius, height, normal radial, normal y]. */
function revolve(c: Vec3, profile: (v: number) => [number, number, number, number], nv: number) {
  return surface(64, nv, (u, v) => {
    const [r, y, nr, ny] = profile(v), a = 2 * Math.PI * u;
    return [[c[0] + r * Math.cos(a), c[1] + y, c[2] + r * Math.sin(a)], [nr * Math.cos(a), ny, nr * Math.sin(a)]];
  });
}
const sphere = (c: Vec3, r: number) => revolve(c, (v) => { const t = Math.PI * v; return [r * Math.sin(t), -r * Math.cos(t), Math.sin(t), -Math.cos(t)]; }, 32);
/** Vertical capsule standing on c (radius r, total height h). */
const capsule = (c: Vec3, r: number, h: number) => revolve(c, (v) => {
  const L = h - 2 * r, total = Math.PI * r + L, s = v * total;
  if (s < Math.PI * r / 2) { const t = s / r; return [r * Math.sin(t), r - r * Math.cos(t), Math.sin(t), -Math.cos(t)]; }
  if (s < Math.PI * r / 2 + L) return [r, r + s - Math.PI * r / 2, 1, 0];
  const t = (s - L) / r; return [r * Math.sin(t), r + L - r * Math.cos(t), Math.sin(t), -Math.cos(t)];
}, 48);
/** Torus around the unit axis a through c. */
function torus(c: Vec3, a: Vec3, R: number, r: number) {
  const e1 = normalize(cross(a, Math.abs(a[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0])), e2 = cross(a, e1);
  return surface(96, 32, (u, v) => {
    const p = 2 * Math.PI * u, q = 2 * Math.PI * v;
    const radial = add3(scale3(e1, Math.cos(p)), scale3(e2, Math.sin(p)));
    const n = add3(scale3(radial, Math.cos(q)), scale3(a, Math.sin(q)));
    return [add3(c, add3(scale3(radial, R), scale3(n, r))), n];
  });
}

const toonMaterial = (name: string, rgb: [number, number, number]): MaterialDesc => ({ name, baseColorFactor: [...rgb, 1], baseColorImage: -1,
  normalImage: -1, metallicRoughnessImage: -1, metallicFactor: 0, roughnessFactor: 1, alphaMask: false, alphaCutoff: 0.5, doubleSided: true, style: 1 });

/** Height of the highest surface below `top` on the vertical line through (x, z). */
function groundAt(s: SceneData, x: number, z: number, top: number) {
  let best = -Infinity;
  for (const p of s.primitives)
    for (let k = p.firstIndex; k < p.firstIndex + p.indexCount; k += 3) {
      const v = [0, 1, 2].map((q) => (s.indices[k + q] + p.baseVertex) * 3);
      const [ax, az, bx, bz, cx, cz] = [s.positions[v[0]], s.positions[v[0] + 2], s.positions[v[1]], s.positions[v[1] + 2], s.positions[v[2]], s.positions[v[2] + 2]];
      const d = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz);
      if (Math.abs(d) < 1e-12) continue;
      const w0 = ((bz - cz) * (x - cx) + (cx - bx) * (z - cz)) / d, w1 = ((cz - az) * (x - cx) + (ax - cx) * (z - cz)) / d, w2 = 1 - w0 - w1;
      if (w0 < 0 || w1 < 0 || w2 < 0) continue;
      const y = w0 * s.positions[v[0] + 1] + w1 * s.positions[v[1] + 1] + w2 * s.positions[v[2] + 1];
      if (y < top && y > best) best = y;
    }
  return best;
}

/** Sponza with toon objects on the atrium floor ahead of the camera, along the moving camera's path (which walks
 * 6 m forward): an orange sphere, a blue ring facing the camera and a green capsule figure with a head. With
 * photoreal = true the same objects get photoreal materials (style 0). */
export function toonSponza(base: SceneData, photoreal = false, withDynamic = false): SceneSpec {
  const cam = s0Camera(base);
  const f = normalize([cam.target[0] - cam.eye[0], 0, cam.target[2] - cam.eye[2]]);
  const side = normalize(cross(f, [0, 1, 0]));
  const at = (ahead: number, aside: number, y: number): Vec3 => {
    const p = add3(add3(cam.eye, scale3(f, ahead)), scale3(side, aside));
    return [p[0], groundAt(base, p[0], p[2], cam.eye[1]) + y, p[2]];
  };
  const objects: { mat: MaterialDesc; mesh: ReturnType<typeof surface>[]; pivot?: Vec3 }[] = [
    { mat: toonMaterial('toon-orange', [0.75, 0.28, 0.06]), mesh: [sphere(at(5, 1.0, 0.7), 0.7)] },
    { mat: toonMaterial('toon-blue', [0.12, 0.25, 0.8]), mesh: [torus(at(7, -1.0, 0.95), f, 0.7, 0.25)] },
    { mat: toonMaterial('toon-green', [0.15, 0.65, 0.18]), mesh: [capsule(at(9.5, 0.3, 0), 0.35, 1.4), sphere(at(9.5, 0.3, 1.73), 0.33)] },
  ];
  const pos = Array.from(base.positions), nrm = Array.from(base.normals), idx = Array.from(base.indices);
  const materials = base.materials.slice(), primitives = base.primitives.slice();
  const dynObjects: DynamicObject[] = [];
  const firstTriangle = base.triangleCount;
  for (const o of objects) {
    const material = materials.length;
    const firstVertex = pos.length / 3;
    materials.push(photoreal ? { ...o.mat, name: o.mat.name.replace('toon', 'plain'), style: 0, object: true } : o.mat);
    for (const m of o.mesh) {
      const baseVertex = pos.length / 3, firstIndex = idx.length;
      pos.push(...m.pos); nrm.push(...m.nrm); idx.push(...m.idx);
      primitives.push({ firstIndex, indexCount: m.idx.length, baseVertex, material });
    }
    const vertexCount = pos.length / 3 - firstVertex;
    let cx = 0, cz = 0, ymin = Infinity;
    for (let v = firstVertex; v < firstVertex + vertexCount; v++) { cx += pos[v * 3]; cz += pos[v * 3 + 2]; ymin = Math.min(ymin, pos[v * 3 + 1]); }
    dynObjects.push({ firstVertex, vertexCount, pivot: [cx / vertexCount, ymin, cz / vertexCount] });
  }
  const positions = new Float32Array(pos), V = positions.length / 3;
  const uvs = new Float32Array(V * 2), tangents = new Float32Array(V * 4);
  uvs.set(base.uvs); tangents.set(base.tangents);
  const [boundsMin, boundsMax] = bounds(positions);
  const scene: SceneData = { ...base, positions, normals: new Float32Array(nrm), uvs, tangents, indices: new Uint32Array(idx), primitives, materials,
    boundsMin, boundsMax, triangleCount: idx.length / 3 };
  return { name: photoreal ? 'sponza-objects' : 'sponza-toon', scene, camera: cam, moving: true, sunDir: SPONZA_SUN, enclosed: false,
    dynamic: !withDynamic ? undefined : { firstTriangle, objects: dynObjects, at: () => ({ sunDir: SPONZA_SUN, sunScale: 1, poses: dynObjects.map(() => ({ rotY: 0, offset: [0, 0, 0] as Vec3 })) }) } };
}

/** M1: fully dynamic Sponza. The S3 objects (toon, or photoreal with photoreal = true) move on the atrium floor and
 * the sun swings, all with the frame number t (periods of 160-400 frames, so a 240-frame run sees all of it):
 * the sphere rolls sideways by +-1.6 m, the ring turns about the vertical, the figure walks +-1.5 m along the view
 * and the sun swings by about +-20 degrees along the atrium and a little across it (its lit patches move over the
 * floor and the walls in view; a larger swing across the narrow atrium puts the whole visible floor in shadow).
 * Optional light switch for R1: from frame switchAt the sun jumps to another direction. */
export function dynamicSponza(base: SceneData, photoreal = false, switchAt = -1, only: 'all' | 'sun' | 'objects' = 'all'): SceneSpec {
  const s = toonSponza(base, photoreal, true);
  const cam = s.camera;
  const f = normalize([cam.target[0] - cam.eye[0], 0, cam.target[2] - cam.eye[2]]);
  const side = normalize(cross(f, [0, 1, 0]));
  const d = s.dynamic!;
  const sun = (t: number): Vec3 => {
    if (switchAt >= 0) return t < switchAt ? SPONZA_SUN : [0.45, 1, -0.25];
    if (only === 'objects') t = 0;
    const a = 2 * Math.PI * t / 400;
    return [-0.15 + 0.4 * Math.sin(a), 1, 0.1 + 0.08 * Math.sin(2 * a + 0.5)];
  };
  d.at = (t: number) => ({
    sunDir: sun(t), sunScale: 1,
    poses: switchAt >= 0 || only === 'sun' ? d.objects.map(() => ({ rotY: 0, offset: [0, 0, 0] as Vec3 })) : [
      { rotY: 0, offset: scale3(side, -1.6 * Math.sin(2 * Math.PI * t / 240)) },
      { rotY: 2 * Math.PI * t / 320, offset: [0, 0, 0] },
      { rotY: 0, offset: scale3(f, 1.5 * Math.sin(2 * Math.PI * t / 160)) },
    ],
  });
  const name = (photoreal ? 'sponza-dynobj' : 'sponza-dyn') + (switchAt >= 0 ? `-switch${switchAt}` : '') + (only !== 'all' ? `-${only}only` : '');
  return { ...s, name, sunDir: sun(0), dynamic: d };
}
