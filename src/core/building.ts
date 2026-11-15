// Full-dynamic lane (phase 20): the building itself (the "static" triangles, the head of the triangle table) changes
// every frame. Scene suffixes (src/native/rc.ts): -bwave (every building vertex moves every frame) and -bcut (parts
// of the building appear and vanish: topology changes). Measurement scaffolding: the work done here is not GI and is
// outside the GPU timing of the GI passes. Needs the static bricks rebuilt every frame (--vox without local).
//
// wave: a smooth displacement field of the rest position, d_i(p) = A_i sin(k w_i . p + 2 pi t / T_i + phi_i)
// (wavelength 4 m, +-12 cm sideways, +-6 cm vertically), applied on the GPU to all building vertices from a copy of the
// rest mesh. Vertices shared by a seam stay together. Normals to first order: n' = normalize(n - D^T n), D = grad d.
// cut: the building triangles (except the floor, centroid below 0.5 m above the scene's bottom) are grouped into
// 2 m cells by their centroid; every CUT_PERIOD frames a new set of cells (hash < CUT_SHARE) is removed. A removed
// triangle points at one extra vertex far below the scene (the clipmaps never reach it, the rasteriser drops it
// as degenerate). The index buffer (raster) and the triangle table (voxels) are rewritten when the set changes.
import type { SceneData } from './gltf.ts';
import type { SceneGpu } from './scene_gpu.ts';
import type { World } from './world.ts';

export const CUT_PERIOD = 30, CUT_SHARE = 0.2, CUT_CELL = 2;
const FAR_Y = -1e4;

export interface BuildingSpec {
  kind: 'wave' | 'cut';
  /** Building vertices [0, vertexCount) and triangles [0, triangleCount) (the dynamic objects follow). */
  vertexCount: number;
  triangleCount: number;
  /** cut: index of the far vertex appended to the scene. */
  farVertex?: number;
}

/** Adds building motion to a scene (cut appends the far vertex; the bounds stay those of the real scene). */
export function withBuilding(scene: SceneData, kind: 'wave' | 'cut', firstDynamicVertex: number, firstDynamicTri: number): { scene: SceneData; building: BuildingSpec } {
  if (kind === 'wave') return { scene, building: { kind, vertexCount: firstDynamicVertex, triangleCount: firstDynamicTri } };
  const V = scene.positions.length / 3;
  const grow = (a: Float32Array, n: number, v: number[]) => { const b = new Float32Array((V + 1) * n); b.set(a); b.set(v, V * n); return b; };
  return {
    scene: { ...scene, positions: grow(scene.positions, 3, [0, FAR_Y, 0]), normals: grow(scene.normals, 3, [0, 1, 0]), uvs: grow(scene.uvs, 2, [0, 0]),
      tangents: grow(scene.tangents, 4, [1, 0, 0, 1]) },
    building: { kind, vertexCount: firstDynamicVertex, triangleCount: firstDynamicTri, farVertex: V },
  };
}

const WAVE_WGSL = /* wgsl */ `
struct U { t: f32, n: u32, lodFirst: u32, lodN: u32 } // phase 32: then the clustered copies' vertices (world.ts)
@group(0) @binding(0) var<uniform> u: U;
@group(0) @binding(1) var<storage, read> restP: array<f32>;
@group(0) @binding(2) var<storage, read> restN: array<f32>;
@group(0) @binding(3) var<storage, read_write> outP: array<f32>;
@group(0) @binding(4) var<storage, read_write> outN: array<f32>;
const K = 6.283185 / 4.0;
const A = vec3f(0.12, 0.06, 0.12);
const W0 = vec3f(0.0, 0.8, 0.6);
const W1 = vec3f(0.6, 0.0, 0.8);
const W2 = vec3f(0.8, 0.6, 0.0);
@compute @workgroup_size(64) fn wave(@builtin(global_invocation_id) gid: vec3u, @builtin(num_workgroups) nwg: vec3u) {
  let k = gid.y * nwg.x * 64u + gid.x;
  if (k >= u.n + u.lodN) { return; }
  let v = select(u.lodFirst + k - u.n, k, k < u.n);
  let p = vec3f(restP[k * 3u], restP[k * 3u + 1u], restP[k * 3u + 2u]);
  let n = vec3f(restN[k * 3u], restN[k * 3u + 1u], restN[k * 3u + 2u]);
  let a = vec3f(K * dot(W0, p) + 6.283185 * u.t / 90.0, K * dot(W1, p) + 6.283185 * u.t / 110.0 + 1.3, K * dot(W2, p) + 6.283185 * u.t / 130.0 + 2.6);
  let d = A * sin(a);
  let c = A * K * cos(a);  // D_ij = c_i W_i[j]
  let dtn = W0 * (c.x * n.x) + W1 * (c.y * n.y) + W2 * (c.z * n.z);
  var m = n - dtn;
  m = select(n, normalize(m), dot(m, m) > 1e-12);
  let q = p + d;
  outP[v * 3u] = q.x; outP[v * 3u + 1u] = q.y; outP[v * 3u + 2u] = q.z;
  outN[v * 3u] = m.x; outN[v * 3u + 1u] = m.y; outN[v * 3u + 2u] = m.z;
}
`;

export interface Building {
  spec: BuildingSpec;
  /** Poses the building at frame t (queue writes and a compute submission, ordered before the next frame). */
  apply(t: number): void;
  /** Share of the building triangles present at frame t (cut), 1 for wave. */
  present(t: number): number;
  destroy(): void;
}

function hash3(x: number, y: number, z: number, e: number) {
  let h = Math.imul(x, 73856093) ^ Math.imul(y, 19349663) ^ Math.imul(z, 83492791) ^ Math.imul(e + 1, 2654435761);
  h ^= h >>> 13; h = Math.imul(h, 0x5bd1e995); h ^= h >>> 15;
  return (h >>> 0) / 4294967296;
}

export function createBuilding(device: GPUDevice, scene: SceneData, gpu: SceneGpu, tri: GPUBuffer, table: Uint32Array, spec: BuildingSpec,
  world: World | null = null): Building {
  if (world && spec.kind !== 'wave') throw new Error('instanced worlds support the wave only');
  if (spec.kind === 'wave') {
    const n = spec.vertexCount, lodFirst = world?.lodFirstVertex ?? 0, lodN = world?.lodVertexCount ?? 0;
    const S = GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST;
    const restP = device.createBuffer({ label: 'building.restP', size: (n + lodN) * 12, usage: S });
    const restN = device.createBuffer({ label: 'building.restN', size: (n + lodN) * 12, usage: S });
    device.queue.writeBuffer(restP, 0, scene.positions, 0, n * 3);
    device.queue.writeBuffer(restN, 0, scene.normals, 0, n * 3);
    if (lodN) {
      device.queue.writeBuffer(restP, n * 12, scene.positions, lodFirst * 3, lodN * 3);
      device.queue.writeBuffer(restN, n * 12, scene.normals, lodFirst * 3, lodN * 3);
    }
    const uni = device.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    const pipe = device.createComputePipeline({ layout: 'auto', compute: { module: device.createShaderModule({ code: WAVE_WGSL, label: 'building.wave' }), entryPoint: 'wave' } });
    // Writes only the building's vertices (and the clustered copies'); the dynamic objects' range is written by the runner.
    const bg = device.createBindGroup({ layout: pipe.getBindGroupLayout(0), entries: [
      { binding: 0, resource: { buffer: uni } }, { binding: 1, resource: { buffer: restP } }, { binding: 2, resource: { buffer: restN } },
      { binding: 3, resource: { buffer: gpu.positions } }, { binding: 4, resource: { buffer: gpu.normals } },
    ] });
    const g = Math.ceil((n + lodN) / 64), x = Math.min(g, 65535);
    return {
      spec,
      apply(t) {
        const b = new ArrayBuffer(16);
        new Float32Array(b, 0, 1)[0] = t; new Uint32Array(b, 4, 3).set([n, lodFirst, lodN]);
        device.queue.writeBuffer(uni, 0, b);
        const enc = device.createCommandEncoder();
        const pass = enc.beginComputePass({ label: 'building.wave' });
        pass.setPipeline(pipe); pass.setBindGroup(0, bg); pass.dispatchWorkgroups(x, Math.ceil(g / x));
        pass.end();
        device.queue.submit([enc.finish()]);
      },
      present: () => 1,
      destroy() { restP.destroy(); restN.destroy(); uni.destroy(); },
    };
  }
  // cut
  const T = spec.triangleCount, far = spec.farVertex!;
  const cell = new Int32Array(T * 3), floor = new Uint8Array(T);
  const yFloor = scene.boundsMin[1] + 0.5;
  for (let t = 0; t < T; t++) {
    const c = [0, 0, 0];
    for (let q = 0; q < 3; q++) for (let a = 0; a < 3; a++) c[a] += scene.positions[table[t * 4 + q] * 3 + a] / 3;
    for (let a = 0; a < 3; a++) cell[t * 3 + a] = Math.floor(c[a] / CUT_CELL);
    floor[t] = c[1] < yFloor ? 1 : 0;
  }
  // Primitive of each triangle (index buffer entries are relative to the primitive's base vertex).
  const base = new Uint32Array(T);
  for (const p of scene.primitives) for (let i = p.firstIndex; i < p.firstIndex + p.indexCount && i / 3 < T; i += 3) base[i / 3] = p.baseVertex;
  const cache = new Map<number, { idx: Uint32Array; tab: Uint32Array; present: number }>();
  const epochData = (e: number) => {
    let d = cache.get(e);
    if (d) return d;
    const idx = scene.indices.slice(0, T * 3), tab = table.slice(0, T * 4);
    let kept = 0;
    for (let t = 0; t < T; t++) {
      if (!floor[t] && hash3(cell[t * 3], cell[t * 3 + 1], cell[t * 3 + 2], e) < CUT_SHARE) {
        idx.fill(far - base[t], t * 3, t * 3 + 3);
        tab.fill(far, t * 4, t * 4 + 3);
      } else kept++;
    }
    d = { idx, tab, present: kept / T };
    cache.set(e, d);
    return d;
  };
  let current = -1;
  return {
    spec,
    apply(t) {
      const e = Math.floor(t / CUT_PERIOD);
      if (e === current) return;
      current = e;
      const d = epochData(e);
      device.queue.writeBuffer(gpu.indices, 0, d.idx);
      device.queue.writeBuffer(tri, 0, d.tab);
    },
    present: (t) => epochData(Math.floor(t / CUT_PERIOD)).present,
    destroy() {},
  };
}
