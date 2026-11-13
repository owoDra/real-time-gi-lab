// S2 scenes: Sponza, Sponza made 10x wider (ten copies in a row) or 10x denser (every triangle split into
// nine with the same surface), and enclosed leak rooms after N004 (legacy/scenes/n004_scene_factory.py).
import { s0Camera } from './bench.ts';
import type { Camera } from './frame.ts';
import type { MaterialDesc, SceneData } from './gltf.ts';
import { normalize, type Vec3 } from './math.ts';

export interface SceneSpec {
  name: string;
  scene: SceneData;
  camera: Camera;
  /** Moving camera, or null when only the static camera is measured. */
  moving: boolean;
  sunDir: Vec3;
  /** Leak scenes: every visible point is enclosed, so all indirect irradiance is leakage. */
  enclosed: boolean;
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
