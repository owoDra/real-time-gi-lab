// S2: voxel StrataBrick. Multi-level voxel bricks rebuilt from triangles on the GPU.
//
// Level L has voxels of v0 * 2^L. A brick is 8^3 voxels (16 words of occupancy bits) plus the index of its
// first voxel attribute. Each level is a camera-relative clipmap of G^3 brick pointers (dense, so memory is
// bounded by G and the number of occupied bricks, not by the size of the world); only occupied bricks are
// allocated. Occupied voxels carry an albedo (alpha: toon flag, S3) and a normal (8 bytes), addressed by the rank of their bit in the
// brick, taken from one representative triangle (the highest index overlapping the voxel, so the choice does
// not depend on scheduling) at the voxel centre projected onto it. Voxelisation is conservative (triangle /
// box overlap); alpha-masked materials are tested at the projected voxel centre. The build is deterministic.
//
// Header words: 0 bricks, 1 voxels, 2-4 overflows, 8-15 bricks per level, 16-31 big-triangle lists.
// P2: only the static triangles (the head of the triangle table) are voxelised. Dynamic triangles go to the
// dynamic layer (dynlayer.ts), never into these binary bricks. With a fixed window (anchor 'scene', local) the
// static bricks are built once.
// Build: clear -> markBricks (per triangle and level, brick granularity) -> allocBricks -> clearKeys ->
// voxBits (per triangle and level: bit + representative) -> allocVoxels -> resolveAttr (per occupied voxel).
// In both triangle passes, triangles that cover more than 8 cells of a level go to a list processed one
// workgroup each: a few large triangles otherwise hold whole waves (markBricks went from 0.7 to 0.05 ms).
import type { SceneData } from './gltf.ts';
import type { SceneGpu } from './scene_gpu.ts';

export interface VoxParams {
  v0: number;        // finest voxel size (m)
  levels: number;    // <= 8
  G: number;         // bricks per axis per level (clipmap)
  maxBricks: number; // brick pool, all levels
  maxVoxels: number; // voxel attribute pool, all levels
  // M1: clipmap windows centred on the camera (S2) or fixed on the scene's centre (the window then never scrolls;
  // scrolling updates are M2's streaming). local: the static triangles are voxelised once (needs anchor 'scene');
  // otherwise they are rebuilt every frame.
  anchor: 'camera' | 'scene';
  local: boolean;
}
export const DEFAULT_VOX: VoxParams = { v0: 0.1, levels: 5, G: 64, maxBricks: 1 << 15, maxVoxels: 4 << 20, anchor: 'camera', local: false };

const HDR = 64;        // counter words at the start of the vox buffer
export const BRICK_WORDS = 18; // 16 occupancy words, first attribute, level and brick coordinates

/** Uniform shared by the builder and the tracer. */
export const VOX_STRUCT_WGSL = /* wgsl */ `
struct VoxU {
  a: vec4f,   // v0, levels, G, brick words
  b: vec4u,   // ptrOff, brickOff, attrOff, maxBricks
  c: vec4u,   // maxVoxels, end of the triangles to voxelise (the static ones), 0, 0
  origin: array<vec4i, 8>, // per level: first brick of the clipmap (world brick coordinates), w unused
}
const VOX_EMPTY = 0xffffffffu;
const VOX_MARK = 0xfffffffeu;
fn voxSize(L: u32) -> f32 { return VX.a.x * exp2(f32(L)); }
fn voxG() -> i32 { return i32(VX.a.z); }
fn voxPtrIndex(L: u32, b: vec3i) -> u32 {
  let G = u32(VX.a.z);
  return VX.b.x + L * G * G * G + (u32(b.z) * G + u32(b.y)) * G + u32(b.x);
}
`;

/** Tracer: hierarchical DDA (empty bricks are skipped whole) over one level. Needs VX, vox (array<u32>) and
 * a hit-shading function voxShade(entry, n, albedo (a: toon flag), dir, v, attribute index, level, voxel centre) -> vec3f,
 * where entry is the point where the ray enters the voxel (the side the ray comes from). Occupied voxels entered
 * before tSkip are ignored. Returns (radiance, T), T = 0 on a hit. */
export const VOX_TRACE_WGSL = /* wgsl */ `
${VOX_STRUCT_WGSL}
fn voxRank(brick: u32, bit: u32) -> u32 {
  let base = VX.b.y + brick * ${BRICK_WORDS}u;
  let w = bit >> 5u;
  var r = countOneBits(vox[base + w] & ((1u << (bit & 31u)) - 1u));
  for (var i = 0u; i < w; i++) { r += countOneBits(vox[base + i]); }
  return vox[base + 16u] + r;
}
fn voxInside(L: u32, p: vec3f) -> bool {
  let bs = voxSize(L) * 8.0;
  let lo = vec3f(VX.origin[L].xyz) * bs;
  return all(p > lo) && all(p < lo + f32(voxG()) * bs);
}
// Smallest level >= L whose clipmap contains the end of the segment.
fn voxLevelFor(L: u32, e: vec3f) -> u32 {
  var l = L;
  let n = u32(VX.a.y);
  while (l + 1u < n && !voxInside(l, e)) { l++; }
  return l;
}
var<private> voxSteps: u32;
fn traceVox(o: vec3f, d: vec3f, t0: f32, t1: f32, tSkip: f32, L: u32) -> vec4f {
  let v = voxSize(L);
  let G = voxG();
  let lo = vec3f(VX.origin[L].xyz) * v * 8.0;
  let hi = lo + f32(G) * v * 8.0;
  // Exact zero components occur (octahedral texel centres with |x| + |y| = 1): give them a tiny positive
  // value so that the step sign and the boundary times agree.
  let dd = select(d, vec3f(1e-9), abs(d) < vec3f(1e-9));
  let inv = 1.0 / dd;
  let ta = (lo - o) * inv; let tb = (hi - o) * inv;
  let tn = min(ta, tb); let tf = max(ta, tb);
  var t = max(max(max(tn.x, tn.y), tn.z), t0);
  let tEnd = min(min(min(tf.x, tf.y), tf.z), t1);
  if (t >= tEnd) { return vec4f(0.0, 0.0, 0.0, 1.0); }
  let st = vec3i(sign(dd));
  let stepPos = vec3f(st > vec3i(0));
  let nVox = G * 8;
  var c = clamp(vec3i(floor((o + d * t - lo) / v)), vec3i(0), vec3i(nVox - 1));
  var tMax = ((vec3f(c) + stepPos) * v + lo - o) * inv;
  let tDelta = abs(v * inv);
  var tIn = t;
  for (var it = 0u; it < 1024u; it++) {
    voxSteps++;
    let b = c >> vec3u(3u);
    let ptr = vox[voxPtrIndex(L, b)];
    if (ptr >= VOX_MARK) {
      // Empty brick: jump to its exit.
      let bt = ((vec3f(b * 8) + stepPos * 8.0) * v + lo - o) * inv;
      let te = min(min(bt.x, bt.y), bt.z);
      if (te >= tEnd) { break; }
      var nb = b;
      if (bt.x <= bt.y && bt.x <= bt.z) { nb.x += st.x; } else if (bt.y <= bt.z) { nb.y += st.y; } else { nb.z += st.z; }
      if (any(nb < vec3i(0)) || any(nb >= vec3i(G))) { break; }
      t = te; tIn = te;
      c = clamp(vec3i(floor((o + d * t - lo) / v)), nb * 8, nb * 8 + 7);
      tMax = ((vec3f(c) + stepPos) * v + lo - o) * inv;
      continue;
    }
    let l = c & vec3i(7);
    let bit = u32(l.x + 8 * l.y + 64 * l.z);
    let occ = vox[VX.b.y + ptr * ${BRICK_WORDS}u + (bit >> 5u)];
    let tExit = min(min(tMax.x, tMax.y), tMax.z);
    if ((occ & (1u << (bit & 31u))) != 0u && tIn >= tSkip) {
      let ai = voxRank(ptr, bit);
      let alb = unpack4x8unorm(vox[VX.b.z + ai * 2u]);
      let nn = unpack2x16snorm(vox[VX.b.z + ai * 2u + 1u]);
      var n = vec3f(nn.x, nn.y, 1.0 - abs(nn.x) - abs(nn.y));
      let q = max(-n.z, 0.0);
      n.x += select(q, -q, n.x >= 0.0); n.y += select(q, -q, n.y >= 0.0);
      return vec4f(voxShade(o + d * tIn, n, alb, d, v, ai, L, lo + (vec3f(c) + 0.5) * v), 0.0);
    }
    if (tExit >= tEnd) { break; }
    tIn = tExit;
    if (tMax.x <= tMax.y && tMax.x <= tMax.z) { c.x += st.x; tMax.x += tDelta.x; }
    else if (tMax.y <= tMax.z) { c.y += st.y; tMax.y += tDelta.y; }
    else { c.z += st.z; tMax.z += tDelta.z; }
    if (any(c < vec3i(0)) || any(c >= vec3i(nVox))) { break; }
  }
  return vec4f(0.0, 0.0, 0.0, 1.0);
}
`;

const BUILD_WGSL = /* wgsl */ `
${VOX_STRUCT_WGSL}
struct Material { baseColorFactor: vec4f, layers: vec4u, params: vec4f }
@group(0) @binding(0) var<uniform> VX: VoxU;
@group(0) @binding(1) var<storage, read_write> vox: array<atomic<u32>>;
@group(0) @binding(2) var<storage, read_write> rep: array<atomic<u32>>;    // 512 per brick: representative triangle + 1
@group(0) @binding(3) var<storage, read_write> big: array<u32>;      // 8 unused words, then BIG_CAP triangles per segment:
                                                                     // segments 0-7 voxBits per level, 8-15 markBricks per level
@group(0) @binding(5) var<storage, read> positions: array<f32>;
@group(0) @binding(6) var<storage, read> normals: array<f32>;
@group(0) @binding(7) var<storage, read> uvs: array<f32>;
@group(0) @binding(8) var<storage, read> tri: array<vec4u>;          // absolute indices + material
@group(0) @binding(9) var<storage, read> materials: array<Material>;
@group(0) @binding(10) var baseColorTex: texture_2d_array<f32>;
@group(0) @binding(11) var samp: sampler;

const BIG = 8u;
const BIG_CAP = 1u << 18u;
fn lin(wid: vec3u, nwg: vec3u, li: u32) -> u32 { return (wid.y * nwg.x + wid.x) * 64u + li; }
fn P(i: u32) -> vec3f { return vec3f(positions[i * 3u], positions[i * 3u + 1u], positions[i * 3u + 2u]); }
fn N(i: u32) -> vec3f { return vec3f(normals[i * 3u], normals[i * 3u + 1u], normals[i * 3u + 2u]); }
fn UV(i: u32) -> vec2f { return vec2f(uvs[i * 2u], uvs[i * 2u + 1u]); }

// Akenine-Moller triangle / box overlap (box at origin with half size h, triangle already relative).
fn axisTest(a: vec3f, v0: vec3f, v1: vec3f, v2: vec3f, h: vec3f) -> bool {
  let p0 = dot(v0, a); let p1 = dot(v1, a); let p2 = dot(v2, a);
  let r = dot(h, abs(a));
  return !(min(min(p0, p1), p2) > r || max(max(p0, p1), p2) < -r);
}
fn triBox(c: vec3f, h: vec3f, a: vec3f, b: vec3f, cc: vec3f) -> bool {
  let v0 = a - c; let v1 = b - c; let v2 = cc - c;
  if (any(min(min(v0, v1), v2) > h) || any(max(max(v0, v1), v2) < -h)) { return false; }
  let e0 = v1 - v0; let e1 = v2 - v1; let e2 = v0 - v2;
  let n = cross(e0, e1);
  if (abs(dot(n, v0)) > dot(h, abs(n))) { return false; }
  // The nine edge axes, unrolled (dynamically indexed local arrays can spill to scratch memory).
  return axisTest(vec3f(0.0, -e0.z, e0.y), v0, v1, v2, h) && axisTest(vec3f(0.0, -e1.z, e1.y), v0, v1, v2, h)
    && axisTest(vec3f(0.0, -e2.z, e2.y), v0, v1, v2, h) && axisTest(vec3f(e0.z, 0.0, -e0.x), v0, v1, v2, h)
    && axisTest(vec3f(e1.z, 0.0, -e1.x), v0, v1, v2, h) && axisTest(vec3f(e2.z, 0.0, -e2.x), v0, v1, v2, h)
    && axisTest(vec3f(-e0.y, e0.x, 0.0), v0, v1, v2, h) && axisTest(vec3f(-e1.y, e1.x, 0.0), v0, v1, v2, h)
    && axisTest(vec3f(-e2.y, e2.x, 0.0), v0, v1, v2, h);
}
// Barycentrics of the point of the triangle closest to p (Ericson, Real-Time Collision Detection 5.1.5).
fn closestBary(p: vec3f, a: vec3f, b: vec3f, c: vec3f) -> vec3f {
  let ab = b - a; let ac = c - a; let ap = p - a;
  let d1 = dot(ab, ap); let d2 = dot(ac, ap);
  if (d1 <= 0.0 && d2 <= 0.0) { return vec3f(1.0, 0.0, 0.0); }
  let bp = p - b; let d3 = dot(ab, bp); let d4 = dot(ac, bp);
  if (d3 >= 0.0 && d4 <= d3) { return vec3f(0.0, 1.0, 0.0); }
  let vc = d1 * d4 - d3 * d2;
  if (vc <= 0.0 && d1 >= 0.0 && d3 <= 0.0) { let w = d1 / (d1 - d3); return vec3f(1.0 - w, w, 0.0); }
  let cp = p - c; let d5 = dot(ab, cp); let d6 = dot(ac, cp);
  if (d6 >= 0.0 && d5 <= d6) { return vec3f(0.0, 0.0, 1.0); }
  let vb = d5 * d2 - d1 * d6;
  if (vb <= 0.0 && d2 >= 0.0 && d6 <= 0.0) { let w = d2 / (d2 - d6); return vec3f(1.0 - w, 0.0, w); }
  let va = d3 * d6 - d5 * d4;
  if (va <= 0.0 && (d4 - d3) >= 0.0 && (d5 - d6) >= 0.0) { let w = (d4 - d3) / ((d4 - d3) + (d5 - d6)); return vec3f(0.0, 1.0 - w, w); }
  let dn = 1.0 / (va + vb + vc);
  let v = vb * dn; let w = vc * dn;
  return vec3f(1.0 - v - w, v, w);
}

struct Tri { a: vec3f, b: vec3f, c: vec3f, idx: vec4u }
fn loadTri(t: u32) -> Tri { let i = tri[t]; return Tri(P(i.x), P(i.y), P(i.z), i); }
fn regionLo(L: u32) -> vec3f { return vec3f(VX.origin[L].xyz) * voxSize(L) * 8.0; }

// Voxel range of a triangle at level L, clipped to the clipmap. Returns (lo, count) with count 0 if outside.
struct Range { lo: vec3i, n: vec3i }
fn voxRange(T: Tri, L: u32, cell: f32) -> Range {
  let lo = regionLo(L);
  let mn = min(min(T.a, T.b), T.c); let mx = max(max(T.a, T.b), T.c);
  let lim = i32(f32(voxG()) * voxSize(L) * 8.0 / cell);
  let a = clamp(vec3i(floor((mn - lo) / cell)), vec3i(0), vec3i(lim));
  let b = clamp(vec3i(floor((mx - lo) / cell)) + 1, vec3i(0), vec3i(lim));
  return Range(a, max(b - a, vec3i(0)));
}

// Alpha test at the voxel centre projected onto the triangle; also returns the attributes there.
struct Surf { ok: bool, albedo: vec3f, n: vec3f, toon: f32 }
fn surfaceAt(T: Tri, p: vec3f, L: u32, wantAttr: bool) -> Surf {
  let m = materials[T.idx.w];
  let masked = (m.layers.w & 1u) != 0u;
  if (!masked && !wantAttr) { return Surf(true, vec3f(0.0), vec3f(0.0), 0.0); }
  let w = closestBary(p, T.a, T.b, T.c);
  let uv = UV(T.idx.x) * w.x + UV(T.idx.y) * w.y + UV(T.idx.z) * w.z;
  let tex = textureSampleLevel(baseColorTex, samp, uv, m.layers.x, f32(3u + L)) * m.baseColorFactor;
  if (masked && tex.a < m.params.z) { return Surf(false, vec3f(0.0), vec3f(0.0), 0.0); }
  var n = N(T.idx.x) * w.x + N(T.idx.y) * w.y + N(T.idx.z) * w.z;
  n = select(cross(T.b - T.a, T.c - T.a), n, dot(n, n) > 1e-12);
  return Surf(true, tex.rgb, normalize(n), select(0.0, 1.0, (m.layers.w & 4u) != 0u));
}

@compute @workgroup_size(64) fn clear(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  let G = u32(VX.a.z);
  if (i < ${HDR}u) { atomicStore(&vox[i], 0u); }
  if (i < 4u) { big[i] = 0u; }
  if (i < u32(VX.a.y) * G * G * G) { atomicStore(&vox[VX.b.x + i], VOX_EMPTY); }
}

// Read before the atomic: many triangles hit the same brick (made no measurable difference on Sponza).
fn markBrick(i: u32) { if (atomicLoad(&vox[i]) == VOX_EMPTY) { atomicMin(&vox[i], VOX_MARK); } }
fn markRange(T: Tri, L: u32, r: Range, start: u32, stride: u32) {
  let bs = voxSize(L) * 8.0;
  let lo = regionLo(L);
  let n = u32(r.n.x * r.n.y * r.n.z);
  for (var j = start; j < n; j += stride) {
    let q = i32(j);
    let b = r.lo + vec3i(q % r.n.x, (q / r.n.x) % r.n.y, q / (r.n.x * r.n.y));
    if (n == 1u || triBox(lo + (vec3f(b) + 0.5) * bs, vec3f(0.5 * bs * 1.0001), T.a, T.b, T.c)) { markBrick(voxPtrIndex(L, b)); }
  }
}
@compute @workgroup_size(64) fn markBricks(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let t = lin(wid, nwg, li);
  if (t >= VX.c.y) { return; }
  let T = loadTri(t);
  for (var L = 0u; L < u32(VX.a.y); L++) {
    let r = voxRange(T, L, voxSize(L) * 8.0);
    let n = r.n.x * r.n.y * r.n.z;
    if (n > 8) {
      let k = atomicAdd(&vox[24u + L], 1u);
      if (k < BIG_CAP) { big[8u + (8u + L) * BIG_CAP + k] = t; } else { atomicAdd(&vox[3], 1u); }
      continue;
    }
    markRange(T, L, r, 0u, 1u);
  }
}
@compute @workgroup_size(64) fn markBricksBig(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  var L = 0u; var k = wid.y * nwg.x + wid.x;
  loop {
    let n = min(atomicLoad(&vox[24u + L]), BIG_CAP);
    if (k < n || L + 1u >= u32(VX.a.y)) { break; }
    k -= n; L++;
  }
  if (k >= min(atomicLoad(&vox[24u + L]), BIG_CAP)) { return; }
  let T = loadTri(big[8u + (8u + L) * BIG_CAP + k]);
  markRange(T, L, voxRange(T, L, voxSize(L) * 8.0), li, 64u);
}

@compute @workgroup_size(64) fn allocBricks(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  let G = u32(VX.a.z); let per = G * G * G;
  if (i >= u32(VX.a.y) * per) { return; }
  if (atomicLoad(&vox[VX.b.x + i]) != VOX_MARK) { return; }
  let idx = atomicAdd(&vox[0], 1u);
  if (idx >= VX.b.w) { atomicStore(&vox[VX.b.x + i], VOX_EMPTY); atomicAdd(&vox[2], 1u); return; }
  atomicAdd(&vox[8u + i / per], 1u);
  atomicStore(&vox[VX.b.x + i], idx);
  for (var w = 0u; w < 17u; w++) { atomicStore(&vox[VX.b.y + idx * ${BRICK_WORDS}u + w], 0u); }
  let L = i / per; let r = i % per;
  atomicStore(&vox[VX.b.y + idx * ${BRICK_WORDS}u + 17u], (L << 27u) | ((r % G) << 18u) | (((r / G) % G) << 9u) | (r / (G * G)));
}
@compute @workgroup_size(64) fn clearKeys(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  if (i < min(atomicLoad(&vox[0]), VX.b.w) * 512u) { atomicStore(&rep[i], 0u); }
}

fn voxelizeOne(T: Tri, t: u32, L: u32, c: vec3i, single: bool) {
  let v = voxSize(L);
  let p = regionLo(L) + (vec3f(c) + 0.5) * v;
  if (!single && !triBox(p, vec3f(0.5 * v * 1.0001), T.a, T.b, T.c)) { return; }
  let ptr = atomicLoad(&vox[voxPtrIndex(L, c >> vec3u(3u))]);
  if (ptr >= VOX_MARK) { return; }
  let l = c & vec3i(7);
  let bit = u32(l.x + 8 * l.y + 64 * l.z);
  if (!surfaceAt(T, p, L, false).ok) { return; }
  let wi = VX.b.y + ptr * ${BRICK_WORDS}u + (bit >> 5u);
  let m = 1u << (bit & 31u);
  if ((atomicLoad(&vox[wi]) & m) == 0u) { atomicOr(&vox[wi], m); }
  if (atomicLoad(&rep[ptr * 512u + bit]) < t + 1u) { atomicMax(&rep[ptr * 512u + bit], t + 1u); }
}

fn voxelizeSmall(t: u32) {
  if (t >= VX.c.y) { return; }
  let T = loadTri(t);
  for (var L = 0u; L < u32(VX.a.y); L++) {
    let r = voxRange(T, L, voxSize(L));
    let n = r.n.x * r.n.y * r.n.z;
    if (n == 0) { continue; }
    if (u32(n) > BIG) {
      let k = atomicAdd(&vox[16u + L], 1u);
      if (k < BIG_CAP) { big[8u + L * BIG_CAP + k] = t; } else { atomicAdd(&vox[3], 1u); }
      continue;
    }
    for (var k = 0; k < n; k++) {
      voxelizeOne(T, t, L, r.lo + vec3i(k % r.n.x, (k / r.n.x) % r.n.y, k / (r.n.x * r.n.y)), n == 1);
    }
  }
}
@compute @workgroup_size(64) fn voxBits(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  voxelizeSmall(lin(wid, nwg, li));
}
// One workgroup per large (triangle, level); the level is in big's segment.
fn voxelizeBig(wi: u32, li: u32) {
  var L = 0u; var k = wi;
  loop {
    let n = min(atomicLoad(&vox[16u + L]), BIG_CAP);
    if (k < n || L + 1u >= u32(VX.a.y)) { break; }
    k -= n; L++;
  }
  if (k >= min(atomicLoad(&vox[16u + L]), BIG_CAP)) { return; }
  let t = big[8u + L * BIG_CAP + k];
  let T = loadTri(t);
  let r = voxRange(T, L, voxSize(L));
  let n = u32(r.n.x * r.n.y * r.n.z);
  for (var j = li; j < n; j += 64u) {
    let q = i32(j);
    voxelizeOne(T, t, L, r.lo + vec3i(q % r.n.x, (q / r.n.x) % r.n.y, q / (r.n.x * r.n.y)), false);
  }
}
@compute @workgroup_size(64) fn voxBitsBig(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  voxelizeBig(wid.y * nwg.x + wid.x, li);
}

@compute @workgroup_size(64) fn allocVoxels(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let b = lin(wid, nwg, li);
  if (b >= min(atomicLoad(&vox[0]), VX.b.w)) { return; }
  let base = VX.b.y + b * ${BRICK_WORDS}u;
  var n = 0u;
  for (var w = 0u; w < 16u; w++) { n += countOneBits(atomicLoad(&vox[base + w])); }
  let first = atomicAdd(&vox[1], n);
  if (first + n > VX.c.x) { atomicStore(&vox[base + 16u], VOX_EMPTY); atomicAdd(&vox[4], 1u); return; }
  atomicStore(&vox[base + 16u], first);
}

fn octEnc(n: vec3f) -> vec2f {
  var p = n.xy / (abs(n.x) + abs(n.y) + abs(n.z));
  if (n.z < 0.0) { p = (1.0 - abs(p.yx)) * select(vec2f(-1.0), vec2f(1.0), p >= vec2f(0.0)); }
  return p;
}
// One thread per (brick, voxel slot): occupied voxels take albedo and normal from their representative.
@compute @workgroup_size(64) fn resolveAttr(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  let ptr = i >> 9u; let bit = i & 511u;
  if (ptr >= min(atomicLoad(&vox[0]), VX.b.w)) { return; }
  let base = VX.b.y + ptr * ${BRICK_WORDS}u;
  let w = bit >> 5u;
  let word = atomicLoad(&vox[base + w]);
  if ((word & (1u << (bit & 31u))) == 0u) { return; }
  let first = atomicLoad(&vox[base + 16u]);
  if (first == VOX_EMPTY) { return; }
  var r = countOneBits(word & ((1u << (bit & 31u)) - 1u));
  for (var j = 0u; j < w; j++) { r += countOneBits(atomicLoad(&vox[base + j])); }
  let ai = first + r;
  let code = atomicLoad(&vox[base + 17u]);
  let L = code >> 27u;
  let b = vec3i(i32((code >> 18u) & 511u), i32((code >> 9u) & 511u), i32(code & 511u));
  let c = b * 8 + vec3i(i32(bit & 7u), i32((bit >> 3u) & 7u), i32(bit >> 6u));
  let p = regionLo(L) + (vec3f(c) + 0.5) * voxSize(L);
  let t = atomicLoad(&rep[ptr * 512u + bit]) - 1u;
  let s = surfaceAt(loadTri(t), p, L, true);
  atomicStore(&vox[VX.b.z + ai * 2u], pack4x8unorm(vec4f(s.albedo, s.toon)));
  atomicStore(&vox[VX.b.z + ai * 2u + 1u], pack2x16snorm(octEnc(s.n)));
}

`;

const ARGS_WGSL = /* wgsl */ `
${VOX_STRUCT_WGSL}
@group(0) @binding(0) var<uniform> VX: VoxU;
@group(0) @binding(1) var<storage, read> vox: array<u32>;
@group(0) @binding(2) var<storage, read_write> args: array<u32>;
const BIG_CAP = 1u << 18u;
@compute @workgroup_size(1) fn writeArgs() {
  var nb = 0u;
  for (var L = 0u; L < u32(VX.a.y); L++) { nb += min(vox[16u + L], BIG_CAP); }
  let x = min(nb, 65535u);
  args[0] = x; args[1] = select(0u, (nb + x - 1u) / max(x, 1u), x > 0u); args[2] = 1u;
  let nb0 = min(vox[0], VX.b.w);
  let nv = (nb0 * 512u + 63u) / 64u;
  let y = min(nv, 65535u);
  args[4] = y; args[5] = select(0u, (nv + y - 1u) / max(y, 1u), y > 0u); args[6] = 1u;
  let nr = (nb0 * 512u + 63u) / 64u;
  let z = min(nr, 65535u);
  args[8] = z; args[9] = select(0u, (nr + z - 1u) / max(z, 1u), z > 0u); args[10] = 1u;
  let na = (nb0 + 63u) / 64u;
  let w = min(na, 65535u);
  args[12] = w; args[13] = select(0u, (na + w - 1u) / max(w, 1u), w > 0u); args[14] = 1u;
  var nm = 0u;
  for (var L = 0u; L < u32(VX.a.y); L++) { nm += min(vox[24u + L], BIG_CAP); }
  let m = min(nm, 65535u);
  args[16] = m; args[17] = select(0u, (nm + m - 1u) / max(m, 1u), m > 0u); args[18] = 1u;
}

`;

export const VOX_STAGES = ['clear', 'markBricks', 'allocBricks', 'voxBits', 'allocVoxels', 'resolve'] as const;

export interface VoxWorld {
  params: VoxParams;
  vox: GPUBuffer;
  uniform: GPUBuffer;
  bytes: number;           // allocated
  update(eye: [number, number, number]): void;
  /** Local: voxelises the static triangles once (call after the first update, before encoding frames). */
  buildStatic(): Promise<number>;
  /** This frame's work inside the caller's pass (nothing when the static bricks are built once). */
  encode(pass: GPUComputePassEncoder): void;
  /** Same work, one pass per stage with timestamps at slots [base, base + 2 * VOX_STAGES.length). */
  encodeStaged(enc: GPUCommandEncoder, querySet: GPUQuerySet, base: number): void;
  readCounters(): Promise<{ bricks: number; voxels: number; brickOverflow: number; bigOverflow: number; voxelOverflow: number; bricksPerLevel: number[]; bigPerLevel: number[] }>;
  usedBytes(c: { bricks: number; voxels: number }): { persistent: number; buildTemp: number };
  destroy(): void;
}

/** Absolute triangle indices + material, shared by the voxel builder and the triangle BVH. */
export function triangleTable(scene: SceneData): Uint32Array {
  const t = new Uint32Array(scene.triangleCount * 4);
  for (const p of scene.primitives)
    for (let i = p.firstIndex; i < p.firstIndex + p.indexCount; i += 3) {
      const k = i / 3;
      t[k * 4] = scene.indices[i] + p.baseVertex; t[k * 4 + 1] = scene.indices[i + 1] + p.baseVertex;
      t[k * 4 + 2] = scene.indices[i + 2] + p.baseVertex; t[k * 4 + 3] = p.material;
    }
  return t;
}

export function createVoxWorld(device: GPUDevice, scene: SceneData, gpu: SceneGpu, tri: GPUBuffer, params: VoxParams, firstDynamicTri = scene.triangleCount): VoxWorld {
  const { v0, levels: NL, G, maxBricks, maxVoxels } = params;
  if (NL > 8) throw new Error('at most 8 levels');
  if (params.local && params.anchor !== 'scene') throw new Error('static bricks built once need a fixed window (anchor scene)');
  const ptrOff = HDR, brickOff = ptrOff + NL * G ** 3, attrOff = brickOff + maxBricks * BRICK_WORDS;
  const words = attrOff + maxVoxels * 2;
  const S = GPUBufferUsage.STORAGE;
  const vox = device.createBuffer({ label: 'vox', size: words * 4, usage: S | GPUBufferUsage.COPY_SRC });
  const repBuf = device.createBuffer({ label: 'vox.rep', size: maxBricks * 512 * 4, usage: S });
  const BIG_CAP = 1 << 18;
  const big = device.createBuffer({ label: 'vox.big', size: (8 + 16 * BIG_CAP) * 4, usage: S });
  const args = device.createBuffer({ label: 'vox.args', size: 24 * 4, usage: S | GPUBufferUsage.INDIRECT });
  const uniform = device.createBuffer({ label: 'vox.u', size: 48 + 8 * 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  const C = GPUShaderStage.COMPUTE;
  const st = (type: GPUBufferBindingType) => ({ visibility: C, buffer: { type } });
  const bgl = device.createBindGroupLayout({ entries: [
    { binding: 0, ...st('uniform') }, { binding: 1, ...st('storage') }, { binding: 2, ...st('storage') }, { binding: 3, ...st('storage') },
    { binding: 5, ...st('read-only-storage') }, { binding: 6, ...st('read-only-storage') }, { binding: 7, ...st('read-only-storage') },
    { binding: 8, ...st('read-only-storage') }, { binding: 9, ...st('read-only-storage') },
    { binding: 10, visibility: C, texture: { viewDimension: '2d-array' } }, { binding: 11, visibility: C, sampler: {} },
  ] });
  const module = device.createShaderModule({ code: BUILD_WGSL, label: 'vox.build' });
  const layout = device.createPipelineLayout({ bindGroupLayouts: [bgl] });
  const pipes: Record<string, GPUComputePipeline> = Object.fromEntries(['clear', 'markBricks', 'markBricksBig', 'allocBricks', 'clearKeys', 'voxBits', 'voxBitsBig',
    'allocVoxels', 'resolveAttr'].map((e) => [e, device.createComputePipeline({ label: `vox.${e}`, layout, compute: { module, entryPoint: e } })]));
  const sampler = device.createSampler({ minFilter: 'linear', magFilter: 'linear', mipmapFilter: 'linear', addressModeU: 'repeat', addressModeV: 'repeat' });
  const bg = device.createBindGroup({ layout: bgl, entries: [
    { binding: 0, resource: { buffer: uniform } }, { binding: 1, resource: { buffer: vox } }, { binding: 2, resource: { buffer: repBuf } },
    { binding: 3, resource: { buffer: big } }, { binding: 5, resource: { buffer: gpu.positions } },
    { binding: 6, resource: { buffer: gpu.normals } }, { binding: 7, resource: { buffer: gpu.uvs } }, { binding: 8, resource: { buffer: tri } },
    { binding: 9, resource: { buffer: gpu.materials } }, { binding: 10, resource: gpu.baseColor.createView({ dimension: '2d-array' }) },
    { binding: 11, resource: sampler },
  ] });
  const argsModule = device.createShaderModule({ code: ARGS_WGSL, label: 'vox.args' });
  pipes.writeArgs = device.createComputePipeline({ label: 'vox.writeArgs', layout: 'auto', compute: { module: argsModule, entryPoint: 'writeArgs' } });
  const bgs: Record<string, GPUBindGroup> = Object.fromEntries(Object.keys(pipes).map((n) => [n, bg]));
  bgs.writeArgs = device.createBindGroup({ layout: pipes.writeArgs.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: uniform } }, { binding: 1, resource: { buffer: vox } }, { binding: 2, resource: { buffer: args } },
  ] });
  const T = firstDynamicTri; // static triangles only
  const lin = (pass: GPUComputePassEncoder, n: number) => {
    const g = Math.ceil(n / 64), x = Math.min(g, 65535);
    if (g > 0) pass.dispatchWorkgroups(x, Math.ceil(g / x));
  };
  const use = (pass: GPUComputePassEncoder, name: string) => { pass.setPipeline(pipes[name]); pass.setBindGroup(0, bgs[name]); };
  const bytes = vox.size + repBuf.size + big.size + args.size + uniform.size;
  const stage = (pass: GPUComputePassEncoder, st: typeof VOX_STAGES[number], tris = T) => {
    switch (st) {
      case 'clear': use(pass, 'clear'); lin(pass, Math.max(NL * G ** 3, HDR)); break;
      case 'markBricks':
        use(pass, 'markBricks'); lin(pass, tris);
        use(pass, 'writeArgs'); pass.dispatchWorkgroups(1);
        use(pass, 'markBricksBig'); pass.dispatchWorkgroupsIndirect(args, 64);
        break;
      case 'allocBricks':
        use(pass, 'allocBricks'); lin(pass, NL * G ** 3);
        use(pass, 'writeArgs'); pass.dispatchWorkgroups(1);
        use(pass, 'clearKeys'); pass.dispatchWorkgroupsIndirect(args, 16);
        break;
      case 'voxBits':
        use(pass, 'voxBits'); lin(pass, tris);
        use(pass, 'writeArgs'); pass.dispatchWorkgroups(1);
        use(pass, 'voxBitsBig'); pass.dispatchWorkgroupsIndirect(args, 0);
        break;
      case 'allocVoxels':
        use(pass, 'writeArgs'); pass.dispatchWorkgroups(1);
        use(pass, 'allocVoxels'); pass.dispatchWorkgroupsIndirect(args, 48);
        break;
      case 'resolve': use(pass, 'resolveAttr'); pass.dispatchWorkgroupsIndirect(args, 32); break;
    }
  };

  const centre = [0, 1, 2].map((a) => (scene.boundsMin[a] + scene.boundsMax[a]) / 2) as [number, number, number];
  let lastEye: [number, number, number] = centre;
  const writeUniform = (eye: [number, number, number], end: number) => {
    const buf = new ArrayBuffer(48 + 8 * 16);
    const f = new Float32Array(buf), u = new Uint32Array(buf), i = new Int32Array(buf);
    f.set([v0, NL, G, BRICK_WORDS], 0);
    u.set([ptrOff, brickOff, attrOff, maxBricks], 4);
    u.set([maxVoxels, end, 0, 0], 8);
    for (let L = 0; L < NL; L++) {
      const bs = v0 * 2 ** L * 8;
      i.set([0, 1, 2].map((a) => Math.floor(eye[a] / bs) - G / 2).concat([0]), 12 + L * 4);
    }
    device.queue.writeBuffer(uniform, 0, buf);
  };
  const stages = params.local ? [] : VOX_STAGES;

  return {
    params, vox, uniform, bytes,
    update(eye) {
      lastEye = params.anchor === 'scene' ? centre : eye;
      writeUniform(lastEye, T);
    },
    async buildStatic() {
      if (!params.local) return 0;
      writeUniform(lastEye, T);
      const qs = device.createQuerySet({ type: 'timestamp', count: 2 });
      const enc = device.createCommandEncoder();
      const pass = enc.beginComputePass({ label: 'vox.static', timestampWrites: { querySet: qs, beginningOfPassWriteIndex: 0, endOfPassWriteIndex: 1 } });
      for (const st of VOX_STAGES) stage(pass, st);
      pass.end();
      const rb = device.createBuffer({ size: 16, usage: GPUBufferUsage.QUERY_RESOLVE | GPUBufferUsage.COPY_SRC });
      const rd = device.createBuffer({ size: 16, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
      enc.resolveQuerySet(qs, 0, 2, rb, 0); enc.copyBufferToBuffer(rb, 0, rd, 0, 16);
      device.queue.submit([enc.finish()]);
      await rd.mapAsync(GPUMapMode.READ);
      const ts = new BigUint64Array(rd.getMappedRange().slice(0));
      rd.unmap(); rd.destroy(); rb.destroy(); qs.destroy();
      return Number(ts[1] - ts[0]) / 1e6;
    },
    encode(pass) {
      for (const st of stages) stage(pass, st);
    },
    encodeStaged(enc, querySet, base) {
      VOX_STAGES.forEach((st, i) => {
        const pass = enc.beginComputePass({ label: `vox.${st}`, timestampWrites: { querySet, beginningOfPassWriteIndex: base + 2 * i, endOfPassWriteIndex: base + 2 * i + 1 } });
        stage(pass, st);
        pass.end();
      });
    },
    async readCounters() {
      const read = device.createBuffer({ size: HDR * 4, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
      const enc = device.createCommandEncoder();
      enc.copyBufferToBuffer(vox, 0, read, 0, HDR * 4);
      device.queue.submit([enc.finish()]);
      await read.mapAsync(GPUMapMode.READ);
      const c = new Uint32Array(read.getMappedRange().slice(0));
      read.unmap(); read.destroy();
      return { bricks: Math.min(c[0], maxBricks), voxels: c[1], brickOverflow: c[2], bigOverflow: c[3], voxelOverflow: c[4],
        bricksPerLevel: Array.from(c.slice(8, 8 + NL)), bigPerLevel: Array.from(c.slice(16, 16 + NL)) };
    },
    usedBytes(c) {
      return { persistent: (HDR + NL * G ** 3 + c.bricks * BRICK_WORDS + Math.min(c.voxels, maxVoxels) * 2) * 4 + uniform.size,
        buildTemp: c.bricks * 512 * 4 };
    },
    destroy() { for (const b of [vox, repBuf, big, args, uniform]) b.destroy(); },
  };
}

