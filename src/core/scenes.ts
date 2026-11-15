// S2 scenes: Sponza, Sponza made wider (phase 32: copies of its building in a row, as instances) or 10x denser (every
// triangle split into ten with the same surface), and enclosed leak rooms after N004 (legacy/scenes/n004_scene_factory.py).
// S3: Sponza with toon objects (saturated, untextured, toon style) standing on the atrium floor in the sun.
import { s0Camera } from './bench.ts';
import type { Camera } from './frame.ts';
import type { MaterialDesc, SceneData } from './gltf.ts';
import { add3, cross, normalize, scale3, type Vec3 } from './math.ts';
import { withBuilding, type BuildingSpec } from './building.ts';
import type { World } from './world.ts';

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
  /** Full-dynamic lane: the building itself changes every frame (building.ts). */
  building?: BuildingSpec;
  /** Phase 32: the static part is placed at these offsets (instance 0 at the origin); loadScene builds `world` from it. */
  instances?: Vec3[];
  world?: World;
  /** Phase 32 (D4): the moving camera flies along +x at this speed (m per frame), looking along the row. */
  fly?: number;
}

/** Full-dynamic lane: suffix -bwave (every building vertex moves every frame) or -bcut (parts of the building appear
 * and vanish every CUT_PERIOD frames), see building.ts. */
export function withBuildingMotion(s: SceneSpec, kind: 'wave' | 'cut'): SceneSpec {
  const firstVertex = s.dynamic ? s.dynamic.objects[0].firstVertex : s.scene.positions.length / 3;
  const r = withBuilding(s.scene, kind, firstVertex, s.dynamic?.firstTriangle ?? s.scene.triangleCount);
  return { ...s, name: `${s.name}-b${kind}`, scene: r.scene, building: r.building };
}

/** height: rest height above the pivot (top of the object), used by the bend deformation. */
export interface DynamicObject { firstVertex: number; vertexCount: number; pivot: Vec3; height: number; }
/** Deformation of an object's rest mesh at time t (frames), applied before the rigid pose; the topology never
 * changes. wave: every vertex moves along its rest normal by a smooth field of its rest position (two travelling
 * waves, 0.9 m long, +-8 cm), so vertices shared by a seam stay together; the normal is tilted by the field's
 * tangential gradient. bend: the object bends sideways (+-0.4 m at the top, quadratic in height, period 120). */
export interface Deform { kind: 'wave' | 'bend'; t: number; }
export interface DynamicPose { sunDir: Vec3; sunScale: number; poses: { rotY: number; offset: Vec3; deform?: Deform }[]; }
export interface DynamicSpec {
  firstTriangle: number;
  objects: DynamicObject[];
  /** Pose of every object (rotation about the vertical axis through its pivot, then a translation) and the sun. */
  at(frame: number): DynamicPose;
}

const WAVE_A = 0.08, WAVE_K = 2 * Math.PI / 0.9, BEND_B = 0.4;
/** Deformed local position and normal (x, y, z relative to the pivot) into p[0..2], n[0..2]. */
function deformVertex(df: Deform, height: number, p: number[], n: number[]) {
  const [x, y, z] = p;
  if (df.kind === 'wave') {
    const a1 = WAVE_K * (0.8 * x + 0.6 * y) + 2 * Math.PI * df.t / 70, a2 = WAVE_K * (0.8 * z - 0.6 * y) + 2 * Math.PI * df.t / 90;
    const h = WAVE_A * 0.5 * (Math.sin(a1) + Math.sin(a2));
    const c1 = WAVE_A * 0.5 * WAVE_K * Math.cos(a1), c2 = WAVE_A * 0.5 * WAVE_K * Math.cos(a2);
    const g = [0.8 * c1, 0.6 * c1 - 0.6 * c2, 0.8 * c2];
    const gn = g[0] * n[0] + g[1] * n[1] + g[2] * n[2];
    for (let a = 0; a < 3; a++) p[a] += n[a] * h;
    const m = [n[0] - (g[0] - gn * n[0]), n[1] - (g[1] - gn * n[1]), n[2] - (g[2] - gn * n[2])];
    const l = Math.hypot(m[0], m[1], m[2]);
    for (let a = 0; a < 3; a++) n[a] = m[a] / l;
  } else {
    // z += b(y), b = B (y / H)^2 sin(2 pi t / 120); normals by the inverse transpose: n_y -= b'(y) n_z.
    const s = Math.sin(2 * Math.PI * df.t / 120), u = Math.max(y, 0) / height;
    p[2] = z + BEND_B * u * u * s;
    n[1] -= 2 * BEND_B * u / height * s * n[2];
    const l = Math.hypot(n[0], n[1], n[2]);
    for (let a = 0; a < 3; a++) n[a] /= l;
  }
}

/** Positions and normals of the dynamic vertices at a pose (rest data from `scene`), packed for the vertex buffers. */
export function posedVertices(scene: SceneData, d: DynamicSpec, pose: DynamicPose) {
  const first = d.objects[0].firstVertex;
  const last = d.objects[d.objects.length - 1].firstVertex + d.objects[d.objects.length - 1].vertexCount;
  const pos = new Float32Array((last - first) * 3), nrm = new Float32Array((last - first) * 3);
  const lp = [0, 0, 0], ln = [0, 0, 0];
  d.objects.forEach((o, i) => {
    const { rotY, offset, deform } = pose.poses[i];
    const c = Math.cos(rotY), s = Math.sin(rotY);
    for (let v = o.firstVertex; v < o.firstVertex + o.vertexCount; v++) {
      let x = scene.positions[v * 3] - o.pivot[0], y = scene.positions[v * 3 + 1] - o.pivot[1], z = scene.positions[v * 3 + 2] - o.pivot[2];
      let nx = scene.normals[v * 3], ny = scene.normals[v * 3 + 1], nz = scene.normals[v * 3 + 2];
      if (deform) {
        lp[0] = x; lp[1] = y; lp[2] = z; ln[0] = nx; ln[1] = ny; ln[2] = nz;
        deformVertex(deform, o.height, lp, ln);
        [x, y, z] = lp; [nx, ny, nz] = ln;
      }
      const q = (v - first) * 3;
      pos[q] = o.pivot[0] + c * x + s * z + offset[0]; pos[q + 1] = o.pivot[1] + y + offset[1]; pos[q + 2] = o.pivot[2] - s * x + c * z + offset[2];
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

/** Phase 32: the building of `s` copied n times along +x, 2 m apart (instances of its static part, not new geometry).
 * The camera, the sun and the dynamic objects stay in the first copy; the camera looks along -x, the copies lie behind it. */
export function widen(s: SceneSpec, n: number): SceneSpec {
  const b = s.scene, V = s.dynamic ? s.dynamic.objects[0].firstVertex : b.positions.length / 3;
  let x0 = Infinity, x1 = -Infinity;
  for (let v = 0; v < V; v++) { x0 = Math.min(x0, b.positions[v * 3]); x1 = Math.max(x1, b.positions[v * 3]); }
  const dx = x1 - x0 + 2;
  return { ...s, name: s.name.replace(/^sponza/, `sponza-wide${n}`), instances: Array.from({ length: n }, (_, k): Vec3 => [k * dx, 0, 0]) };
}

/** Every triangle split into 10 with the same surface: the 9 of a degree-3 barycentric grid, the middle one halved. */
export function densify(base: SceneData): SceneSpec {
  const T = base.triangleCount;
  const positions = new Float32Array(T * 11 * 3), normals = new Float32Array(T * 11 * 3), uvs = new Float32Array(T * 11 * 2);
  const tangents = new Float32Array(T * 11 * 4), indices = new Uint32Array(T * 30);
  const primitives: SceneData['primitives'] = [];
  // Barycentric grid of degree 3: point (i, j), i + j <= 3.
  // Point 10 is the midpoint of the middle triangle's edge (1,2)-(1,1) (it lies on (i, j) = (1, 1.5)).
  const pts: [number, number][] = [];
  for (let j = 0; j <= 3; j++) for (let i = 0; i <= 3 - j; i++) pts.push([i, j]);
  const at = (i: number, j: number) => pts.findIndex(([a, b]) => a === i && b === j);
  pts.push([1, 1.5]);
  const local: number[] = [];
  for (let j = 0; j < 3; j++)
    for (let i = 0; i < 3 - j; i++) {
      local.push(at(i, j), at(i + 1, j), at(i, j + 1));
      if (i + j < 2) {
        // The upside-down triangle (i+1, j), (i+1, j+1), (i, j+1); the one at (0, 1) is split at point 10.
        if (i === 0 && j === 1) local.push(at(1, 1), 10, at(0, 2), 10, at(1, 2), at(0, 2));
        else local.push(at(i + 1, j), at(i + 1, j + 1), at(i, j + 1));
      }
    }
  if (local.length !== 30) throw new Error('densify: 10 triangles per triangle');
  let t = 0;
  for (const p of base.primitives) {
    const firstIndex = t * 30;
    for (let k = p.firstIndex; k < p.firstIndex + p.indexCount; k += 3, t++) {
      const v = [0, 1, 2].map((q) => base.indices[k + q] + p.baseVertex);
      pts.forEach(([i, j], n) => {
        const w = [1 - (i + j) / 3, i / 3, j / 3];
        const o = t * 11 + n;
        for (let a = 0; a < 3; a++) {
          positions[o * 3 + a] = w[0] * base.positions[v[0] * 3 + a] + w[1] * base.positions[v[1] * 3 + a] + w[2] * base.positions[v[2] * 3 + a];
          normals[o * 3 + a] = w[0] * base.normals[v[0] * 3 + a] + w[1] * base.normals[v[1] * 3 + a] + w[2] * base.normals[v[2] * 3 + a];
        }
        for (let a = 0; a < 2; a++) uvs[o * 2 + a] = w[0] * base.uvs[v[0] * 2 + a] + w[1] * base.uvs[v[1] * 2 + a] + w[2] * base.uvs[v[2] * 2 + a];
        for (let a = 0; a < 4; a++) tangents[o * 4 + a] = w[0] * base.tangents[v[0] * 4 + a] + w[1] * base.tangents[v[1] * 4 + a] + w[2] * base.tangents[v[2] * 4 + a];
      });
      local.forEach((l, q) => { indices[t * 30 + q] = t * 11 + l; });
    }
    primitives.push({ firstIndex, indexCount: t * 30 - firstIndex, baseVertex: 0, material: p.material });
  }
  const scene: SceneData = { ...base, positions, normals, uvs, tangents, indices, primitives, triangleCount: T * 10 };
  return { name: 'sponza-dense10', scene, camera: s0Camera(base), moving: true, sunDir: SPONZA_SUN, enclosed: false };
}

const GREY: MaterialDesc = { name: 'grey', baseColorFactor: [0.7, 0.7, 0.7, 1], baseColorImage: -1, normalImage: -1, metallicRoughnessImage: -1,
  metallicFactor: 0, roughnessFactor: 1, alphaMask: false, alphaCutoff: 0.5, doubleSided: false };

class Builder {
  pos: number[] = []; nrm: number[] = []; idx: number[][] = [[]];
  /** Material of the quads added next (index into materials). */
  mat = 0;
  /** Added to every position. */
  offset: Vec3 = [0, 0, 0];
  constructor(readonly materials: MaterialDesc[] = [GREY]) { this.idx = materials.map(() => []); }
  quad(a: Vec3, b: Vec3, c: Vec3, d: Vec3) {
    const e1 = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], e2 = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    const n = normalize([e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]);
    const base = this.pos.length / 3;
    for (const p of [a, b, c, d]) { this.pos.push(p[0] + this.offset[0], p[1] + this.offset[1], p[2] + this.offset[2]); this.nrm.push(...n); }
    this.idx[this.mat].push(base, base + 1, base + 2, base, base + 2, base + 3);
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
    const primitives: SceneData['primitives'] = [];
    let firstIndex = 0;
    this.idx.forEach((l, material) => { if (l.length) primitives.push({ firstIndex, indexCount: l.length, baseVertex: 0, material }); firstIndex += l.length; });
    const indices = new Uint32Array(this.idx.flat());
    return { positions, normals: new Float32Array(this.nrm), uvs: new Float32Array(V * 2), tangents: new Float32Array(V * 4),
      indices, primitives, materials: this.materials, imageUris: [], boundsMin, boundsMax, triangleCount: indices.length / 3 };
  }
}

const plain = (name: string, rgb: [number, number, number]): MaterialDesc => ({ ...GREY, name, baseColorFactor: [...rgb, 1] });
export const TOWN_SUN: Vec3 = [-0.5, 1, 0.7];

/** W2 (phase 25): a scene that is not Sponza, with inside and outside, thin shapes and wide surfaces. A house
 * (8 x 6 m, 3 m high, 0.2 m walls; a door and a window in the front wall, a red partition and a green panel inside)
 * with a porch on two thin columns, a pergola of thin slats (6 x 20 cm, 33 cm apart), a fence of thin pickets, a tower,
 * a long wall behind and a low wall on the right, on a 40 x 34 m ground of 1 m cells. The camera stands 11 m in front
 * of the door; the sun is low in front, so light enters the house through the door and the window.
 * The whole scene is moved by a few centimetres off the 0.2 m voxel grid (TOWN_OFFSET): with grid = true it is not,
 * and the ground and the house's faces lie on level-0 voxel faces (town-grid, phase 25 finding). */
export const TOWN_OFFSET: Vec3 = [0.031, 0.037, 0.043];
export function townSpec(grid = false): SceneSpec {
  const b = new Builder([plain('ground', [0.5, 0.47, 0.4]), plain('plaster', [0.8, 0.77, 0.7]), plain('red', [0.65, 0.15, 0.1]),
    plain('green', [0.2, 0.5, 0.2]), plain('slate', [0.35, 0.4, 0.5]), plain('wood', [0.45, 0.3, 0.18]), plain('ochre', [0.8, 0.65, 0.3])]);
  if (!grid) b.offset = TOWN_OFFSET;
  b.mat = 0;
  for (let z = -14; z < 20; z++) for (let x = -20; x < 20; x++) b.quad([x, 0, z + 1], [x + 1, 0, z + 1], [x + 1, 0, z], [x, 0, z]);
  b.mat = 1; // house
  b.box([0, 1.5, -3.1], [4.2, 1.5, 0.1]);
  b.box([-4.1, 1.5, 0], [0.1, 1.5, 3]);
  b.box([4.1, 1.5, 0], [0.1, 1.5, 3]);
  b.box([-2.6, 1.5, 3.1], [1.6, 1.5, 0.1]);   // front wall: left of the door (x -1..1, 2.4 m high)
  b.box([0, 2.7, 3.1], [1, 0.3, 0.1]);         // above the door
  b.box([1.5, 1.5, 3.1], [0.5, 1.5, 0.1]);     // between the door and the window (x 2..3.2, y 1..2)
  b.box([3.7, 1.5, 3.1], [0.5, 1.5, 0.1]);
  b.box([2.6, 0.5, 3.1], [0.6, 0.5, 0.1]);
  b.box([2.6, 2.5, 3.1], [0.6, 0.5, 0.1]);
  b.box([0, 3.1, 0], [4.4, 0.1, 3.4]);         // roof
  b.box([11, 0.6, 2], [0.15, 0.6, 6]);         // low wall on the right
  b.mat = 2; b.box([0.5, 1.5, -1.25], [0.08, 1.5, 1.75]);   // partition, open towards the door
  b.mat = 3; b.box([-2, 1.4, -2.97], [1.8, 1.2, 0.03]);     // panel on the back wall
  b.mat = 4; b.box([0, 2, -9], [14, 2, 0.25]);             // long wall behind
  b.mat = 6; b.box([-9, 4.5, -3], [2.5, 4.5, 2.5]);        // tower
  b.mat = 5; // wood: porch, pergola, fence
  b.box([0, 2.85, 4.45], [2.2, 0.06, 1.25]);
  for (const x of [-2, 2]) b.box([x, 1.4, 5.55], [0.06, 1.4, 0.06]);
  for (const x of [5, 9]) for (const z of [-2, 4]) b.box([x, 1.3, z], [0.05, 1.3, 0.05]);
  for (let k = 0; k < 13; k++) b.box([5 + k / 3, 2.7, 1], [0.03, 0.1, 3.2]);
  b.box([7, 0.25, 1], [1.2, 0.25, 0.3]);                   // bench under the pergola
  for (let k = 0; k < 29; k++) b.box([-12 + k / 4, 0.6, 6], [0.025, 0.6, 0.025]);
  b.box([-8.5, 1.0, 6.04], [3.6, 0.04, 0.015]);
  return { name: grid ? 'town-grid' : 'town', scene: b.scene(), camera: { eye: [1.2, 1.6, 11], target: [-0.3, 1.2, 0], fovYDeg: 60, near: 0.05 },
    moving: true, sunDir: TOWN_SUN, enclosed: false };
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
export function toonSponza(base: SceneData, photoreal = false, withDynamic = false, groups = 1, grid = 0, place?: SceneSpec): SceneSpec {
  const cam = place?.camera ?? s0Camera(base);
  const f = normalize([cam.target[0] - cam.eye[0], 0, cam.target[2] - cam.eye[2]]);
  const side = normalize(cross(f, [0, 1, 0]));
  const at = (ahead: number, aside: number, y: number): Vec3 => {
    const p = add3(add3(cam.eye, scale3(f, ahead)), scale3(side, aside));
    return [p[0], groundAt(base, p[0], p[2], cam.eye[1]) + y, p[2]];
  };
  const kinds = [
    (ahead: number, aside: number) => ({ mat: toonMaterial('toon-orange', [0.75, 0.28, 0.06]), mesh: [sphere(at(ahead, aside, 0.7), 0.7)] }),
    (ahead: number, aside: number) => ({ mat: toonMaterial('toon-blue', [0.12, 0.25, 0.8]), mesh: [torus(at(ahead, aside, 0.95), f, 0.7, 0.25)] }),
    (ahead: number, aside: number) => ({ mat: toonMaterial('toon-green', [0.15, 0.65, 0.18]), mesh: [capsule(at(ahead, aside, 0), 0.35, 1.4), sphere(at(ahead, aside, 1.73), 0.33)] }),
  ];
  const objects: { mat: MaterialDesc; mesh: ReturnType<typeof surface>[] }[] = [];
  if (grid > 0) {
    // Grid (stress scenes sponza-dynobj-n<N>): object k is kind k mod 3 (sphere, ring, figure), in lane k mod 4 (the
    // two side corridors and two lanes of the atrium) and row floor(k / 4), rows 1.1 m apart from 5 m ahead (16 rows
    // end at 21.5 m, inside the floor, which ends about 22 m ahead).
    const lanes = [-3.4, -0.9, 0.9, 3.4];
    for (let k = 0; k < grid; k++) objects.push(kinds[k % 3](5 + 1.1 * Math.floor(k / 4), lanes[k % 4]));
  } else {
    // Groups (stress scenes): group g is moved g * 16 / groups m along the view, odd groups mirrored sideways.
    for (let g = 0; g < groups; g++) {
      const a = g * 16 / groups, m = g % 2 ? -1 : 1;
      objects.push(kinds[0](5 + a, 1.0 * m), kinds[1](7 + a, -1.0 * m), kinds[2](9.5 + a, 0.3 * m));
    }
  }
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
    let cx = 0, cz = 0, ymin = Infinity, ymax = -Infinity;
    for (let v = firstVertex; v < firstVertex + vertexCount; v++) {
      cx += pos[v * 3]; cz += pos[v * 3 + 2]; ymin = Math.min(ymin, pos[v * 3 + 1]); ymax = Math.max(ymax, pos[v * 3 + 1]);
    }
    dynObjects.push({ firstVertex, vertexCount, pivot: [cx / vertexCount, ymin, cz / vertexCount], height: ymax - ymin });
  }
  const positions = new Float32Array(pos), V = positions.length / 3;
  const uvs = new Float32Array(V * 2), tangents = new Float32Array(V * 4);
  uvs.set(base.uvs); tangents.set(base.tangents);
  const [boundsMin, boundsMax] = bounds(positions);
  const scene: SceneData = { ...base, positions, normals: new Float32Array(nrm), uvs, tangents, indices: new Uint32Array(idx), primitives, materials,
    boundsMin, boundsMax, triangleCount: idx.length / 3 };
  const prefix = place?.name ?? 'sponza';
  return { name: photoreal ? `${prefix}-objects` : `${prefix}-toon`, scene, camera: cam, moving: true, sunDir: place?.sunDir ?? SPONZA_SUN, enclosed: false,
    dynamic: !withDynamic ? undefined : { firstTriangle, objects: dynObjects, at: () => ({ sunDir: place?.sunDir ?? SPONZA_SUN, sunScale: 1, poses: dynObjects.map(() => ({ rotY: 0, offset: [0, 0, 0] as Vec3 })) }) } };
}

/** M1: fully dynamic Sponza. The S3 objects (toon, or photoreal with photoreal = true) move on the atrium floor and
 * the sun swings, all with the frame number t (periods of 160-400 frames, so a 240-frame run sees all of it):
 * the sphere rolls sideways by +-1.6 m, the ring turns about the vertical, the figure walks +-1.5 m along the view
 * and the sun swings by about +-20 degrees along the atrium and a little across it (its lit patches move over the
 * floor and the walls in view; a larger swing across the narrow atrium puts the whole visible floor in shadow).
 * Optional light switch for R1: from frame switchAt the sun jumps to another direction. only: 'sun' or 'objects' moves
 * just those; 'sphere' moves the sphere alone (the ring and the figure stay at rest, still dynamic triangles).
 * groups > 1 (stress scenes sponza-dynobj-many<N>): N copies of the three objects, see toonSponza.
 * grid > 0 (stress scenes sponza-dynobj-n<N>): N objects on a grid (see toonSponza) with smaller moves so that
 * neighbours seldom touch: spheres roll +-0.35 m sideways, rings turn, figures walk +-0.4 m, object k 13 k frames ahead.
 * deform (suffix -deform): every object also deforms (Deform: spheres and rings wave, figures bend). */
export function dynamicSponza(base: SceneData, photoreal = false, switchAt = -1, only: 'all' | 'sun' | 'objects' | 'sphere' = 'all', groups = 1,
  grid = 0, deform = false, place?: SceneSpec): SceneSpec {
  const s = toonSponza(base, photoreal, true, groups, grid, place);
  const sun0 = place?.sunDir ?? SPONZA_SUN;
  const cam = s.camera;
  const f = normalize([cam.target[0] - cam.eye[0], 0, cam.target[2] - cam.eye[2]]);
  const side = normalize(cross(f, [0, 1, 0]));
  const d = s.dynamic!;
  const sun = (t: number): Vec3 => {
    if (switchAt >= 0) return t < switchAt ? sun0 : [0.45, 1, -0.25];
    if (only === 'objects' || only === 'sphere') t = 0;
    const a = 2 * Math.PI * t / 400;
    return [sun0[0] + 0.4 * Math.sin(a), sun0[1], sun0[2] + 0.08 * Math.sin(2 * a + 0.5)];
  };
  const rigid = (t: number) => switchAt >= 0 || only === 'sun' ? d.objects.map(() => ({ rotY: 0, offset: [0, 0, 0] as Vec3 }))
    : grid > 0 ? d.objects.map((_, k) => {
      const tk = t + 13 * k;
      return [
        { rotY: 0, offset: scale3(side, -0.35 * Math.sin(2 * Math.PI * tk / 240)) },
        { rotY: 2 * Math.PI * tk / 320, offset: [0, 0, 0] as Vec3 },
        { rotY: 0, offset: scale3(f, 0.4 * Math.sin(2 * Math.PI * tk / 160)) },
      ][k % 3];
    })
    // Group g runs 37 g frames ahead, mirrored sideways when odd.
    : Array.from({ length: groups }, (_, g) => {
      const tg = t + 37 * g, m = g % 2 ? -1 : 1;
      return [
        { rotY: 0, offset: scale3(side, -1.6 * m * Math.sin(2 * Math.PI * tg / 240)) },
        { rotY: only === 'sphere' ? 0 : 2 * Math.PI * tg / 320, offset: [0, 0, 0] as Vec3 },
        { rotY: 0, offset: only === 'sphere' ? [0, 0, 0] as Vec3 : scale3(f, 1.5 * Math.sin(2 * Math.PI * tg / 160)) },
      ];
    }).flat();
  d.at = (t: number) => ({
    sunDir: sun(t), sunScale: 1,
    // Object k (kind k mod 3: sphere, ring, figure) deforms 11 k frames ahead.
    poses: rigid(t).map((p, k) => deform ? { ...p, deform: { kind: k % 3 === 2 ? 'bend' as const : 'wave' as const, t: t + 11 * k } } : p),
  });
  const name = (place?.name ?? 'sponza') + (photoreal ? '-dynobj' : '-dyn') + (switchAt >= 0 ? `-switch${switchAt}` : '') + (only !== 'all' ? `-${only}only` : '')
    + (groups > 1 ? `-many${groups}` : '') + (grid > 0 ? `-n${grid}` : '') + (deform ? '-deform' : '');
  return { ...s, name, sunDir: sun(0), dynamic: d };
}

/** W2 scenes by name: town, town-grid (on the voxel grid), town-toon, town-objects (objects at rest), town-dyn (toon objects and the sun move),
 * town-dynobj (photoreal objects). The objects stand where they stand in Sponza, relative to the camera. */
export function townScene(name: string): SceneSpec {
  if (name === 'town-grid') return townSpec(true);
  const t = townSpec();
  if (name === 'town') return t;
  if (name === 'town-toon' || name === 'town-objects') return toonSponza(t.scene, name === 'town-objects', false, 1, 0, t);
  if (name === 'town-dyn' || name === 'town-dynobj') return dynamicSponza(t.scene, name === 'town-dynobj', -1, 'all', 1, 0, false, t);
  throw new Error(`unknown scene ${name}`);
}

/** Sponza scenes by name (docs/spec/10-evaluation.md). Stress scenes: sponza-dynobj-many<G> (G groups of the three
 * objects), -n<N> (N objects on a grid), -deform. Phase 32: sponza-wide<N>[-...] is any Sponza scene with its building
 * copied N times in a row (widen); sponza-wide<N>-fly flies the moving camera along the row at 0.5 m per frame (D4). */
export function sponzaScene(name: string, base: SceneData): SceneSpec {
  const wide = /^sponza-wide(\d+)(-fly)?(.*)$/.exec(name);
  if (wide) return { ...widen(sponzaScene('sponza' + wide[3], base), Number(wide[1])), name, ...(wide[2] ? { fly: 0.5 } : {}) };
  const stress = /^sponza-dynobj(?:-many(\d+)|-n(\d+))?(-deform)?$/.exec(name);
  return name === 'sponza' ? sponzaSpec(base)
    : name === 'sponza-dense10' ? densify(base) : name === 'sponza-toon' ? toonSponza(base)
    : name === 'sponza-objects' ? toonSponza(base, true)
    : name === 'sponza-dyn' ? dynamicSponza(base) : name === 'sponza-dynobj' ? dynamicSponza(base, true)
    : name === 'sponza-dyn-sunonly' ? dynamicSponza(base, false, -1, 'sun') : name === 'sponza-dyn-objectsonly' ? dynamicSponza(base, false, -1, 'objects')
    : name === 'sponza-dynobj-sunonly' ? dynamicSponza(base, true, -1, 'sun') : name === 'sponza-dynobj-objectsonly' ? dynamicSponza(base, true, -1, 'objects')
    : name === 'sponza-dynobj-sphereonly' ? dynamicSponza(base, true, -1, 'sphere')
    : stress ? dynamicSponza(base, true, -1, 'all', Number(stress[1] ?? 1), Number(stress[2] ?? 0), !!stress[3])
    : name.startsWith('sponza-dyn-switch') ? dynamicSponza(base, false, Number(name.slice('sponza-dyn-switch'.length)))
    : (() => { throw new Error(`unknown scene ${name}`); })();
}
