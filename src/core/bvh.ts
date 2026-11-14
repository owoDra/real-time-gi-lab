// S2: triangle BVH, the ground truth that the voxel tracer is compared against (same interface, same hit
// shading). Built once on the CPU (binned SAH, up to 4 triangles per leaf), refitted on the CPU each frame for
// moving triangles (refitBvh), traversed with a stack in WGSL.
// Alpha-masked materials are tested at the hit, as in the G-buffer.
import type { SceneData } from './gltf.ts';

export interface Bvh { nodes: Float32Array; tris: Float32Array; buildMs: number; nodeCount: number; order: Uint32Array; }

/** nodes: 8 words per node (min xyz, leftFirst | max xyz, count); count 0 = inner node with children
 * leftFirst and leftFirst + 1. tris: 16 words per triangle in BVH order:
 * (p0, mat) (e1, uv0.x) (e2, uv0.y) (uv1, uv2). */
export function buildBvh(scene: SceneData, triTable: Uint32Array): Bvh {
  const t0 = performance.now();
  const T = scene.triangleCount, P = scene.positions;
  const cen = new Float32Array(T * 3), bmin = new Float32Array(T * 3), bmax = new Float32Array(T * 3);
  for (let t = 0; t < T; t++)
    for (let a = 0; a < 3; a++) {
      const x = P[triTable[t * 4] * 3 + a], y = P[triTable[t * 4 + 1] * 3 + a], z = P[triTable[t * 4 + 2] * 3 + a];
      bmin[t * 3 + a] = Math.min(x, y, z); bmax[t * 3 + a] = Math.max(x, y, z); cen[t * 3 + a] = (x + y + z) / 3;
    }
  const order = new Uint32Array(T); for (let i = 0; i < T; i++) order[i] = i;
  const maxNodes = 2 * T;
  const nodes = new Float32Array(maxNodes * 8), nu = new Uint32Array(nodes.buffer);
  let used = 1;
  const BINS = 16;
  const stack: [number, number, number][] = [[0, 0, T]]; // node, first, count
  const bounds = (first: number, count: number) => {
    const mn = [Infinity, Infinity, Infinity], mx = [-Infinity, -Infinity, -Infinity];
    for (let i = first; i < first + count; i++) {
      const t = order[i];
      for (let a = 0; a < 3; a++) { mn[a] = Math.min(mn[a], bmin[t * 3 + a]); mx[a] = Math.max(mx[a], bmax[t * 3 + a]); }
    }
    return [mn, mx];
  };
  const area = (mn: number[], mx: number[]) => {
    const d = [mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]];
    return d[0] < 0 ? 0 : 2 * (d[0] * d[1] + d[1] * d[2] + d[2] * d[0]);
  };
  while (stack.length) {
    const [ni, first, count] = stack.pop()!;
    const [mn, mx] = bounds(first, count);
    nodes.set(mn, ni * 8); nodes.set(mx, ni * 8 + 4);
    const leaf = () => { nu[ni * 8 + 3] = first; nu[ni * 8 + 7] = count; };
    if (count <= 4) { leaf(); continue; }
    // Centroid bounds and binned SAH over all three axes.
    const cmn = [Infinity, Infinity, Infinity], cmx = [-Infinity, -Infinity, -Infinity];
    for (let i = first; i < first + count; i++) for (let a = 0; a < 3; a++) { const c = cen[order[i] * 3 + a]; cmn[a] = Math.min(cmn[a], c); cmx[a] = Math.max(cmx[a], c); }
    let best = Infinity, bestAxis = -1, bestSplit = 0;
    for (let a = 0; a < 3; a++) {
      const ext = cmx[a] - cmn[a];
      if (ext <= 1e-9) continue;
      const cnt = new Array(BINS).fill(0), bl = Array.from({ length: BINS }, () => [Infinity, Infinity, Infinity, -Infinity, -Infinity, -Infinity]);
      for (let i = first; i < first + count; i++) {
        const t = order[i];
        const b = Math.min(BINS - 1, Math.floor((cen[t * 3 + a] - cmn[a]) / ext * BINS));
        cnt[b]++;
        for (let k = 0; k < 3; k++) { bl[b][k] = Math.min(bl[b][k], bmin[t * 3 + k]); bl[b][3 + k] = Math.max(bl[b][3 + k], bmax[t * 3 + k]); }
      }
      const leftA = new Array(BINS).fill(0), leftN = new Array(BINS).fill(0);
      let acc = [Infinity, Infinity, Infinity, -Infinity, -Infinity, -Infinity], n = 0;
      for (let b = 0; b < BINS - 1; b++) {
        n += cnt[b];
        acc = acc.map((v, k) => k < 3 ? Math.min(v, bl[b][k]) : Math.max(v, bl[b][k]));
        leftA[b] = area(acc.slice(0, 3), acc.slice(3)); leftN[b] = n;
      }
      acc = [Infinity, Infinity, Infinity, -Infinity, -Infinity, -Infinity]; n = 0;
      for (let b = BINS - 1; b > 0; b--) {
        n += cnt[b];
        acc = acc.map((v, k) => k < 3 ? Math.min(v, bl[b][k]) : Math.max(v, bl[b][k]));
        const cost = leftA[b - 1] * leftN[b - 1] + area(acc.slice(0, 3), acc.slice(3)) * n;
        if (leftN[b - 1] > 0 && n > 0 && cost < best) { best = cost; bestAxis = a; bestSplit = b; }
      }
    }
    // No useful split: a leaf if small, otherwise a median split (bestAxis < 0) or the SAH split anyway.
    if ((bestAxis < 0 || best >= area(mn, mx) * count) && count <= 16) { leaf(); continue; }
    let mid: number;
    if (bestAxis < 0) {
      // Identical centroids: split by index.
      mid = first + (count >> 1);
    } else {
      const ext = cmx[bestAxis] - cmn[bestAxis];
      let i = first, j = first + count - 1;
      while (i <= j) {
        const t = order[i];
        const b = Math.min(BINS - 1, Math.floor((cen[t * 3 + bestAxis] - cmn[bestAxis]) / ext * BINS));
        if (b < bestSplit) i++; else { order[i] = order[j]; order[j] = t; j--; }
      }
      mid = i;
    }
    if (mid === first || mid === first + count) mid = first + (count >> 1);
    const l = used; used += 2;
    nu[ni * 8 + 3] = l; nu[ni * 8 + 7] = 0;
    stack.push([l, first, mid - first], [l + 1, mid, first + count - mid]);
  }
  const tris = new Float32Array(T * 16), tu = new Uint32Array(tris.buffer);
  const U = scene.uvs;
  for (let i = 0; i < T; i++) {
    const t = order[i];
    const [a, b, c, m] = [triTable[t * 4], triTable[t * 4 + 1], triTable[t * 4 + 2], triTable[t * 4 + 3]];
    const p0 = [P[a * 3], P[a * 3 + 1], P[a * 3 + 2]];
    tris.set(p0, i * 16); tu[i * 16 + 3] = m;
    tris.set([P[b * 3] - p0[0], P[b * 3 + 1] - p0[1], P[b * 3 + 2] - p0[2], U[a * 2]], i * 16 + 4);
    tris.set([P[c * 3] - p0[0], P[c * 3 + 1] - p0[1], P[c * 3 + 2] - p0[2], U[a * 2 + 1]], i * 16 + 8);
    tris.set([U[b * 2], U[b * 2 + 1], U[c * 2], U[c * 2 + 1]], i * 16 + 12);
  }
  return { nodes: nodes.slice(0, used * 8), tris, buildMs: performance.now() - t0, nodeCount: used, order };
}

/** Dynamic scenes: rewrites the triangles from firstTri on with the current positions and refits every node's
 * bounds (same topology; exact hits, slower traversal as the moved triangles spread their nodes). Children are
 * allocated after their parent, so a reverse sweep is bottom-up. Returns the first changed triangle slot range. */
export function refitBvh(b: Bvh, P: Float32Array, triTable: Uint32Array, firstTri: number) {
  const { nodes, tris, order } = b;
  const nu = new Uint32Array(nodes.buffer, nodes.byteOffset, nodes.length);
  for (let i = 0; i < order.length; i++) {
    const t = order[i];
    if (t < firstTri) continue;
    const [a, bb, c] = [triTable[t * 4], triTable[t * 4 + 1], triTable[t * 4 + 2]];
    for (let k = 0; k < 3; k++) {
      tris[i * 16 + k] = P[a * 3 + k];
      tris[i * 16 + 4 + k] = P[bb * 3 + k] - P[a * 3 + k];
      tris[i * 16 + 8 + k] = P[c * 3 + k] - P[a * 3 + k];
    }
  }
  for (let ni = b.nodeCount - 1; ni >= 0; ni--) {
    const o = ni * 8, first = nu[o + 3], count = nu[o + 7];
    const mn = [Infinity, Infinity, Infinity], mx = [-Infinity, -Infinity, -Infinity];
    if (count > 0) {
      for (let i = first; i < first + count; i++)
        for (let k = 0; k < 3; k++) {
          const p0 = tris[i * 16 + k], e1 = tris[i * 16 + 4 + k], e2 = tris[i * 16 + 8 + k];
          mn[k] = Math.min(mn[k], p0, p0 + e1, p0 + e2); mx[k] = Math.max(mx[k], p0, p0 + e1, p0 + e2);
        }
    } else {
      for (const ch of [first, first + 1])
        for (let k = 0; k < 3; k++) { mn[k] = Math.min(mn[k], nodes[ch * 8 + k]); mx[k] = Math.max(mx[k], nodes[ch * 8 + 4 + k]); }
    }
    nodes.set(mn, o); nodes.set(mx, o + 4);
  }
}

/** Needs bvhNodes, bvhTris (array<vec4f>), materials, baseColorTex, linSamp and voxShade-like triShade. */
export const BVH_TRACE_WGSL = /* wgsl */ `
struct BvhNode { mn: vec3f, a: u32, mx: vec3f, n: u32 }
fn boxHit(mn: vec3f, mx: vec3f, o: vec3f, inv: vec3f, tMax: f32) -> f32 {
  let ta = (mn - o) * inv; let tb = (mx - o) * inv;
  let tn = max(max(min(ta.x, tb.x), min(ta.y, tb.y)), min(ta.z, tb.z));
  let tf = min(min(max(ta.x, tb.x), max(ta.y, tb.y)), max(ta.z, tb.z));
  return select(1e30, max(tn, 0.0), tf >= max(tn, 0.0) && tn < tMax);
}
fn traceTri(o: vec3f, d: vec3f, t0: f32, t1: f32) -> vec4f {
  let inv = 1.0 / select(d, vec3f(1e-12), abs(d) < vec3f(1e-12));
  var best = t1; var hit = 0xffffffffu; var hb = vec2f(0.0);
  var stack: array<u32, 40>; var sp = 0u;
  var ni = 0u;
  for (var it = 0u; it < 4096u; it++) {
    let nd = bvhNodes[ni];
    if (nd.n > 0u) {
      for (var k = nd.a; k < nd.a + nd.n; k++) {
        let q0 = bvhTris[k * 4u]; let q1 = bvhTris[k * 4u + 1u]; let q2 = bvhTris[k * 4u + 2u];
        let e1 = q1.xyz; let e2 = q2.xyz;
        let pv = cross(d, e2);
        let det = dot(e1, pv);
        if (abs(det) < 1e-12) { continue; }
        let id = 1.0 / det;
        let tv = o - q0.xyz;
        let u = dot(tv, pv) * id;
        if (u < 0.0 || u > 1.0) { continue; }
        let qv = cross(tv, e1);
        let v = dot(d, qv) * id;
        if (v < 0.0 || u + v > 1.0) { continue; }
        let t = dot(e2, qv) * id;
        if (t <= t0 || t >= best) { continue; }
        let m = materials[bitcast<u32>(q0.w)];
        if ((m.layers.w & 1u) != 0u) {
          let q3 = bvhTris[k * 4u + 3u];
          let uv = vec2f(q1.w, q2.w) * (1.0 - u - v) + q3.xy * u + q3.zw * v;
          let a = textureSampleLevel(baseColorTex, linSamp, uv, m.layers.x, 3.0).a * m.baseColorFactor.a;
          if (a < m.params.z) { continue; }
        }
        best = t; hit = k; hb = vec2f(u, v);
      }
      if (sp == 0u) { break; }
      sp--; ni = stack[sp];
      continue;
    }
    let l = bvhNodes[nd.a]; let r = bvhNodes[nd.a + 1u];
    let tl = boxHit(l.mn, l.mx, o, inv, best); let tr = boxHit(r.mn, r.mx, o, inv, best);
    if (tl > 1e29 && tr > 1e29) {
      if (sp == 0u) { break; }
      sp--; ni = stack[sp];
      continue;
    }
    var near = nd.a; var far = nd.a + 1u; var tfar = tr;
    if (tr < tl) { near = nd.a + 1u; far = nd.a; tfar = tl; }
    if (tfar < 1e29 && sp < 40u) { stack[sp] = far; sp++; }
    ni = near;
  }
  if (hit == 0xffffffffu) { return vec4f(0.0, 0.0, 0.0, 1.0); }
  let q0 = bvhTris[hit * 4u]; let q1 = bvhTris[hit * 4u + 1u]; let q2 = bvhTris[hit * 4u + 2u]; let q3 = bvhTris[hit * 4u + 3u];
  let m = materials[bitcast<u32>(q0.w)];
  let uv = vec2f(q1.w, q2.w) * (1.0 - hb.x - hb.y) + q3.xy * hb.x + q3.zw * hb.y;
  let alb = vec4f((textureSampleLevel(baseColorTex, linSamp, uv, m.layers.x, 3.0) * m.baseColorFactor).rgb, select(0.0, 1.0, (m.layers.w & 4u) != 0u));
  let n = normalize(cross(q1.xyz, q2.xyz));
  return vec4f(triShade(o + d * best, n, alb, d), 0.0);
}
`;
