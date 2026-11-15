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
// dynamic layer (dynlayer.ts), never into these binary bricks.
// Full-dynamic lane (phase 21): everything is rebuilt every frame (the building may change every frame), in clipmap
// windows centred on the camera; there is no build-once path.
// Coarse levels from the finer one: a cell of level L >= 1 that lies inside level L-1's window is the OR of its 8
// children, and its representative is the highest of theirs (the same rule as from the triangles, except that an
// alpha-masked material is tested at the finest voxel only). Only cells outside the finer window are voxelised from
// the triangles (none on Sponza, all of which fits level 0's window).
// Build: clear -> markBricks (per triangle, level 0 and the coarse cells outside the finer window, brick granularity)
// -> markParents (every marked brick marks its ancestors) -> allocBricks -> clearKeys -> voxBits (per triangle:
// bit + representative) -> reduce (levels 1.., fine to coarse) -> allocVoxels -> resolveAttr (per occupied voxel).
// In both triangle passes, triangles that cover more than 8 cells of a level go to a list processed one
// workgroup each: a few large triangles otherwise hold whole waves (markBricks went from 0.7 to 0.05 ms).
import { FRAME_WGSL, SHADOW_TAP_WGSL } from './frame.ts';
import type { SceneData } from './gltf.ts';
import type { Vec3 } from './math.ts';
import type { SceneGpu } from './scene_gpu.ts';
import { selectItems, type World, type WorkItem } from './world.ts';

export interface VoxParams {
  v0: number;        // finest voxel size (m)
  levels: number;    // <= 8
  G: number;         // bricks per axis per level (clipmap)
  maxBricks: number; // brick pool, all levels
  maxVoxels: number; // voxel attribute pool, all levels
  dynBricks: number; // P2: brick pool of the dynamic layer (dynlayer.ts), all levels
}
// Level 0 of 0.2 m (phase 20 decision: the only measured form that fits all geometry rebuilt every frame in 4 ms).
// Phase 32: windows of G = 32 bricks per axis (level 0 spans 51 m, level 4 819 m; 64 changed Sponza's indirect light by
// 0.06 8-bit levels on average and doubled the building inside level 0 on wide worlds). Pools sized for the wide world's
// fast flight (sponza-wide100-fly: at most 4151 bricks, 450k voxels; Sponza uses 1941 / 206k) and 64 moving objects (324
// dynamic bricks), so that GI memory stays within 128 MB including the build temporaries (budget, user 2026-11-14). A full
// brick pool drops the finest bricks deterministically and reads them at a coarser level (allocBricks); the overflow
// counters tell.
export const DEFAULT_VOX: VoxParams = { v0: 0.2, levels: 5, G: 32, maxBricks: 4608, maxVoxels: 524288, dynBricks: 512 };
export function voxParams(o: Record<string, unknown>): VoxParams {
  for (const k of Object.keys(o)) if (!(k in DEFAULT_VOX)) throw new Error(`unknown voxel parameter ${k}`);
  return { ...DEFAULT_VOX, ...o } as VoxParams;
}

const HDR = 64;        // counter words at the start of the vox buffer
export const BRICK_WORDS = 18; // 16 occupancy words, first attribute, level and brick coordinates

/** Uniform shared by the builder and the tracer. */
export const VOX_STRUCT_WGSL = /* wgsl */ `
struct VoxU {
  a: vec4f,   // v0, levels, G, brick words
  b: vec4u,   // ptrOff, brickOff, attrOff, maxBricks
  c: vec4u,   // maxVoxels, threads of the triangle passes (this frame's work items), bounce words (phase 23), plane words (phase 29)
  d: vec4u,   // phase 32: key stride (table rows), items (word offset in big), item count, instance offsets (word offset in big)
  origin: array<vec4i, 8>, // per level: first brick of the clipmap (world brick coordinates), w unused
}
const VOX_EMPTY = 0xffffffffu;
const VOX_DROP = 0xfffffffeu; // phase 32: a brick the full pool dropped (finest first); read at the next coarser level
const VOX_MARK = 0xfffffffdu; // pointers >= VOX_MARK hold no brick
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
// The occupied voxel at cell c of level L: (brick, bit, level), or VOX_EMPTY. A dropped brick is read at the next coarser
// level that holds the cell (the build voxelised its region there from the triangles).
fn voxAt(L: u32, c: vec3i) -> vec3u {
  var l = L; var cc = c;
  loop {
    let ptr = vox[voxPtrIndex(l, cc >> vec3u(3u))];
    if (ptr != VOX_DROP) {
      if (ptr >= VOX_MARK) { return vec3u(VOX_EMPTY, 0u, l); }
      let q = cc & vec3i(7);
      let bit = u32(q.x + 8 * q.y + 64 * q.z);
      if ((vox[VX.b.y + ptr * ${BRICK_WORDS}u + (bit >> 5u)] & (1u << (bit & 31u))) == 0u) { return vec3u(VOX_EMPTY, 0u, l); }
      return vec3u(ptr, bit, l);
    }
    if (l + 1u >= u32(VX.a.y)) { return vec3u(VOX_EMPTY, 0u, l); }
    let w = (VX.origin[l].xyz * 8 + cc) >> vec3u(1u);
    l++;
    cc = w - VX.origin[l].xyz * 8;
    if (any(cc < vec3i(0)) || any(cc >= vec3i(voxG() * 8))) { return vec3u(VOX_EMPTY, 0u, l); }
  }
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
    if (ptr == VOX_DROP) {
      // Dropped brick: voxel by voxel, each read at the coarser level that holds it.
      let r = voxAt(L, c);
      if (r.x != VOX_EMPTY && tIn >= tSkip) {
        let vl = voxSize(r.z);
        let ai = voxRank(r.x, r.y);
        let alb = unpack4x8unorm(vox[VX.b.z + ai * 2u]);
        let nn = unpack2x16snorm(vox[VX.b.z + ai * 2u + 1u]);
        var n = vec3f(nn.x, nn.y, 1.0 - abs(nn.x) - abs(nn.y));
        let q = max(-n.z, 0.0);
        n.x += select(q, -q, n.x >= 0.0); n.y += select(q, -q, n.y >= 0.0);
        return vec4f(voxShade(o + d * tIn, n, alb, d, vl, ai, r.z, (floor((lo + (vec3f(c) + 0.5) * v) / vl) + 0.5) * vl), 0.0);
      }
      let tx = min(min(tMax.x, tMax.y), tMax.z);
      if (tx >= tEnd) { break; }
      tIn = tx;
      if (tMax.x <= tMax.y && tMax.x <= tMax.z) { c.x += st.x; tMax.x += tDelta.x; }
      else if (tMax.y <= tMax.z) { c.y += st.y; tMax.y += tDelta.y; }
      else { c.z += st.z; tMax.z += tDelta.z; }
      if (any(c < vec3i(0)) || any(c >= vec3i(nVox))) { break; }
      continue;
    }
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
@group(0) @binding(3) var<storage, read_write> big: array<u32>;      // 8 unused words, then BIG_CAP triangle keys per segment:
                                                                     // segments 0-7 voxBits per level, 8-15 markBricks per level,
                                                                     // then (phase 32) chunk lists, instance offsets, work items
@group(0) @binding(4) var<uniform> RL: vec4u;                        // reduce: the level built
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
// Phase 32: a triangle is a key, instance * key stride + table row; the instance's offset moves it (0 for instance 0).
fn loadTri(key: u32) -> Tri {
  let inst = key / VX.d.x;
  let i = tri[key - inst * VX.d.x];
  let ob = VX.d.w + inst * 4u;
  let o = vec3f(bitcast<f32>(big[ob]), bitcast<f32>(big[ob + 1u]), bitcast<f32>(big[ob + 2u]));
  return Tri(P(i.x) + o, P(i.y) + o, P(i.z) + o, i);
}
// Thread i of a triangle pass -> (key, first level). Items: (first thread, source, instance, first level); the source is a
// list of table rows in big, or (high bit set) the first row of a contiguous range.
fn workAt(i: u32) -> vec2u {
  var lo = 0u; var hi = VX.d.z;
  while (hi - lo > 1u) { let m = (lo + hi) / 2u; if (big[VX.d.y + m * 4u] <= i) { lo = m; } else { hi = m; } }
  let b = VX.d.y + lo * 4u;
  let j = i - big[b];
  let src = big[b + 1u];
  let row = select(big[src + j], (src & 0x7fffffffu) + j, (src & 0x80000000u) != 0u);
  return vec2u(big[b + 2u] * VX.d.x + row, big[b + 3u]);
}
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

// Cell c of level L >= 1 lies inside level L-1's window: it is built from its children (reduce), not from triangles.
fn finerHolds(L: u32, c: vec3i) -> bool {
  if (L == 0u) { return false; }
  let f = (VX.origin[L].xyz * 8 + c) * 2 - VX.origin[L - 1u].xyz * 8;
  return all(f >= vec3i(0)) && all(f < vec3i(voxG() * 8));
}
// All cells of a non-empty range (of cells of size cell = voxSize(L) * s, s = 1 or 8) inside the finer window.
fn finerHoldsRange(L: u32, r: Range, s: i32) -> bool {
  return finerHolds(L, r.lo * s) && finerHolds(L, (r.lo + r.n) * s - 1);
}
// Phase 32 (after the bricks are allocated): the finer level holds cell c unless its brick there was dropped (pool full);
// then the cell is voxelised from the triangles at this level, and no range test may skip a level.
fn finerBuilt(L: u32, c: vec3i) -> bool {
  if (!finerHolds(L, c)) { return false; }
  if (atomicLoad(&vox[2]) == 0u) { return true; }
  let f = (VX.origin[L].xyz * 8 + c) * 2 - VX.origin[L - 1u].xyz * 8;
  return atomicLoad(&vox[voxPtrIndex(L - 1u, f >> vec3u(3u))]) != VOX_DROP;
}
fn finerBuiltRange(L: u32, r: Range) -> bool { return atomicLoad(&vox[2]) == 0u && finerHoldsRange(L, r, 1); }

// Alpha test at the voxel centre projected onto the triangle (when wantAttr is false); also returns the attributes
// there (when wantAttr is true: no alpha test, the voxel is occupied already) and the projected point q.
struct Surf { ok: bool, albedo: vec3f, n: vec3f, toon: f32, q: vec3f }
fn surfaceAt(T: Tri, p: vec3f, L: u32, wantAttr: bool) -> Surf {
  let m = materials[T.idx.w];
  let masked = (m.layers.w & 1u) != 0u && !wantAttr;
  if (!masked && !wantAttr) { return Surf(true, vec3f(0.0), vec3f(0.0), 0.0, p); }
  let w = closestBary(p, T.a, T.b, T.c);
  let uv = UV(T.idx.x) * w.x + UV(T.idx.y) * w.y + UV(T.idx.z) * w.z;
  let tex = textureSampleLevel(baseColorTex, samp, uv, m.layers.x, f32(3u + L)) * m.baseColorFactor;
  if (masked && tex.a < m.params.z) { return Surf(false, vec3f(0.0), vec3f(0.0), 0.0, p); }
  var n = N(T.idx.x) * w.x + N(T.idx.y) * w.y + N(T.idx.z) * w.z;
  n = select(cross(T.b - T.a, T.c - T.a), n, dot(n, n) > 1e-12);
  return Surf(true, tex.rgb, normalize(n), select(0.0, 1.0, (m.layers.w & 4u) != 0u), T.a * w.x + T.b * w.y + T.c * w.z);
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
    if (finerHolds(L, b * 8) && finerHolds(L, b * 8 + 7)) { continue; }
    if (n == 1u || triBox(lo + (vec3f(b) + 0.5) * bs, vec3f(0.5 * bs * 1.0001), T.a, T.b, T.c)) { markBrick(voxPtrIndex(L, b)); }
  }
}
@compute @workgroup_size(64) fn markBricks(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  if (i >= VX.c.y) { return; }
  let w = workAt(i);
  let t = w.x;
  let T = loadTri(t);
  for (var L = w.y; L < u32(VX.a.y); L++) {
    let r = voxRange(T, L, voxSize(L) * 8.0);
    let n = r.n.x * r.n.y * r.n.z;
    if (n == 0 || finerHoldsRange(L, r, 8)) { continue; }
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

// Every marked brick of levels 0..levels-2 marks its ancestors (their windows contain it).
@compute @workgroup_size(64) fn markParents(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  let G = u32(VX.a.z); let per = G * G * G; let NL = u32(VX.a.y);
  if (i >= (NL - 1u) * per) { return; }
  if (atomicLoad(&vox[VX.b.x + i]) != VOX_MARK) { return; }
  var L = i / per; let r = i % per;
  var w = VX.origin[L].xyz + vec3i(i32(r % G), i32((r / G) % G), i32(r / (G * G))); // world brick coordinates
  for (L++; L < NL; L++) {
    w = w >> vec3u(1u);
    let b = w - VX.origin[L].xyz;
    if (any(b < vec3i(0)) || any(b >= vec3i(i32(G)))) { return; }
    markBrick(voxPtrIndex(L, b));
  }
}

// Phase 32: when the pool cannot hold every marked brick, bricks are allocated in a fixed order, coarse levels first and by
// pointer index within a level, so the full pool drops the finest bricks, and the same ones every time (before, the order
// of an atomic counter decided, and a dropped brick was simply empty). When they all fit, the order does not change the
// result and the atomic counter allocates them (the ordered allocation cost 0.27 ms at G = 64). countMarks: marked
// pointers per group of 64 (rep is scratch until clearKeys) and their total (header word 5); scanMarks (only when they do
// not fit): the groups' prefix in that order; allocBricks: rank = prefix + rank in the group.
var<workgroup> wsum: array<u32, 64>;
// Inclusive prefix sum of wsum over the workgroup (log steps; every thread calls it).
fn wsumScan(li: u32) {
  for (var o = 1u; o < 64u; o <<= 1u) {
    workgroupBarrier();
    let x = select(0u, wsum[li - o], li >= o);
    workgroupBarrier();
    wsum[li] += x;
  }
  workgroupBarrier();
}
@compute @workgroup_size(64) fn countMarks(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  let G = u32(VX.a.z);
  wsum[li] = select(0u, 1u, i < u32(VX.a.y) * G * G * G && atomicLoad(&vox[VX.b.x + i]) == VOX_MARK);
  wsumScan(li);
  if (li == 63u) { atomicStore(&rep[wid.y * nwg.x + wid.x], wsum[63]); if (wsum[63] > 0u) { atomicAdd(&vox[5], wsum[63]); } }
}
var<workgroup> wTotal: u32;
@compute @workgroup_size(64) fn scanMarks(@builtin(local_invocation_index) li: u32) {
  if (li == 0u) { wTotal = atomicLoad(&vox[5]); }
  if (workgroupUniformLoad(&wTotal) <= VX.b.w) { return; }
  let G = u32(VX.a.z); let gl = G * G * G / 64u; let NL = u32(VX.a.y); let ng = NL * gl;
  let per = (ng + 63u) / 64u;
  // Order o: level NL - 1 first. Thread li sums orders [li * per, (li + 1) * per).
  var s = 0u;
  for (var o = li * per; o < min((li + 1u) * per, ng); o++) { s += atomicLoad(&rep[(NL - 1u - o / gl) * gl + o % gl]); }
  wsum[li] = s;
  workgroupBarrier();
  if (li == 0u) { var a = 0u; for (var k = 0u; k < 64u; k++) { let x = wsum[k]; wsum[k] = a; a += x; } atomicStore(&vox[0], a); }
  workgroupBarrier();
  var a = wsum[li];
  for (var o = li * per; o < min((li + 1u) * per, ng); o++) {
    let g = (NL - 1u - o / gl) * gl + o % gl;
    let x = atomicLoad(&rep[g]);
    atomicStore(&rep[ng + g], a);
    a += x;
  }
}
@compute @workgroup_size(64) fn allocBricks(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  let G = u32(VX.a.z); let per = G * G * G;
  let marked = i < u32(VX.a.y) * per && atomicLoad(&vox[VX.b.x + i]) == VOX_MARK;
  wsum[li] = select(0u, 1u, marked);
  wsumScan(li);
  if (!marked) { return; }
  let fits = atomicLoad(&vox[5]) <= VX.b.w;
  var idx = 0u;
  if (fits) { idx = atomicAdd(&vox[0], 1u); }
  else {
    let ng = u32(VX.a.y) * per / 64u;
    idx = atomicLoad(&rep[ng + wid.y * nwg.x + wid.x]) + wsum[li] - 1u;
    if (idx >= VX.b.w) { atomicStore(&vox[VX.b.x + i], VOX_DROP); atomicAdd(&vox[2], 1u); return; }
  }
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
  if (finerBuilt(L, c)) { return; }
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

fn voxelizeSmall(i: u32) {
  if (i >= VX.c.y) { return; }
  let w = workAt(i);
  let t = w.x;
  let T = loadTri(t);
  for (var L = w.y; L < u32(VX.a.y); L++) {
    let r = voxRange(T, L, voxSize(L));
    let n = r.n.x * r.n.y * r.n.z;
    if (n == 0 || finerBuiltRange(L, r)) { continue; }
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

// Level RL.x from level RL.x - 1: one thread per word of occupancy of a brick of the finer level. A word is 8 x 4
// voxels of one z row; their parents are 4 x 2 voxels of one word of one parent brick (the windows start at even
// cells), so the thread sets that word's bits with one atomic and raises each parent's representative to the
// highest of its children in the word.
@compute @workgroup_size(64) fn reduce(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  let ptr = i >> 4u; let w = i & 15u;
  if (ptr >= min(atomicLoad(&vox[0]), VX.b.w)) { return; }
  let base = VX.b.y + ptr * ${BRICK_WORDS}u;
  let code = atomicLoad(&vox[base + 17u]);
  let Lc = code >> 27u; let L = RL.x;
  if (Lc + 1u != L) { return; }
  var word = atomicLoad(&vox[base + w]);
  if (word == 0u) { return; }
  let b = vec3i(i32((code >> 18u) & 511u), i32((code >> 9u) & 511u), i32(code & 511u));
  let c0 = b * 8 + vec3i(0, i32((w & 1u) * 4u), i32(w >> 1u));
  let pc0 = ((VX.origin[Lc].xyz * 8 + c0) >> vec3u(1u)) - VX.origin[L].xyz * 8;
  let pptr = atomicLoad(&vox[voxPtrIndex(L, pc0 >> vec3u(3u))]);
  if (pptr >= VOX_MARK) { return; } // brick pool overflow (counted by allocBricks)
  let l0 = pc0 & vec3i(7);
  let pbit0 = u32(l0.x + 8 * l0.y + 64 * l0.z);
  var mask = 0u;
  var lo = vec4u(0u); var hi = vec4u(0u); // highest representative per parent (x 0..3; y 0 in lo, 1 in hi)
  while (word != 0u) {
    let k = firstTrailingBit(word);
    word &= word - 1u;
    let px = (k & 7u) >> 1u; let py = k >> 4u;
    mask |= 1u << ((pbit0 + px + 8u * py) & 31u);
    let rv = atomicLoad(&rep[ptr * 512u + w * 32u + k]);
    if (py == 0u) { lo[px] = max(lo[px], rv); } else { hi[px] = max(hi[px], rv); }
  }
  let wi = VX.b.y + pptr * ${BRICK_WORDS}u + (pbit0 >> 5u);
  if ((atomicLoad(&vox[wi]) & mask) != mask) { atomicOr(&vox[wi], mask); }
  for (var px = 0u; px < 4u; px++) {
    for (var py = 0u; py < 2u; py++) {
      let rv = select(hi[px], lo[px], py == 0u);
      if (rv == 0u) { continue; }
      let ri = pptr * 512u + pbit0 + px + 8u * py;
      if (atomicLoad(&rep[ri]) < rv) { atomicMax(&rep[ri], rv); }
    }
  }
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
  // Phase 29: the representative's plane, the stored normal through the projected point: its offset from the centre (voxSun).
  atomicStore(&vox[VX.c.w + ai], bitcast<u32>(dot(s.n, s.q - p)));
}

`;

// Phase 29: the sun visibility of every occupied voxel, once per frame after the shadow map and resolveAttr: the mean of
// 2 x 2 points on the representative's plane, a quarter voxel from the centre's projection along two tangents and
// (0.25 voxel + 3 cm) off the plane on its sunward side, each a hardware 2 x 2 comparison of the shadow map. The tracers'
// voxel hits read it (voxShade in rc.ts: RC cascades, the bounce volume and DDGI) instead of the shadow map at one point of
// the hit: under a moving sun the shadow map's grid moves, and one point on the edge of a shadow flipped between lit and
// shadowed (phase 28: 89 % of the jump of the cut scene; this took 14 %, phase 29). It replaces the point by a mean over
// the voxel's face, with fewer shadow-map reads than one per hit.
const SUN_WGSL = /* wgsl */ `
${FRAME_WGSL}
${VOX_STRUCT_WGSL}
@group(0) @binding(0) var<uniform> VX: VoxU;
@group(0) @binding(1) var<storage, read_write> vox: array<u32>;
@group(0) @binding(2) var<uniform> F: Frame;
@group(0) @binding(3) var shadowTex: texture_depth_2d_array;
@group(0) @binding(4) var shadowCmp: sampler_comparison;
${SHADOW_TAP_WGSL}
fn sunVisAt(x: vec3f) -> f32 { return shadowTap(x); }
@compute @workgroup_size(64) fn voxSun(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = (wid.y * nwg.x + wid.x) * 64u + li;
  let ptr = i >> 9u; let bit = i & 511u;
  if (ptr >= min(vox[0], VX.b.w)) { return; }
  let base = VX.b.y + ptr * ${BRICK_WORDS}u;
  let w = bit >> 5u;
  let word = vox[base + w];
  if ((word & (1u << (bit & 31u))) == 0u) { return; }
  let first = vox[base + 16u];
  if (first >= VOX_MARK) { return; }
  var r = countOneBits(word & ((1u << (bit & 31u)) - 1u));
  for (var j = 0u; j < w; j++) { r += countOneBits(vox[base + j]); }
  let ai = first + r;
  let code = vox[base + 17u];
  let L = code >> 27u;
  let b = vec3i(i32((code >> 18u) & 511u), i32((code >> 9u) & 511u), i32(code & 511u));
  let c = b * 8 + vec3i(i32(bit & 7u), i32((bit >> 3u) & 7u), i32(bit >> 6u));
  let v = voxSize(L);
  let pc = vec3f(VX.origin[L].xyz) * v * 8.0 + (vec3f(c) + 0.5) * v;
  let e = unpack2x16snorm(vox[VX.b.z + ai * 2u + 1u]);
  var n = vec3f(e.x, e.y, 1.0 - abs(e.x) - abs(e.y));
  let q0 = max(-n.z, 0.0);
  n.x += select(q0, -q0, n.x >= 0.0); n.y += select(q0, -q0, n.y >= 0.0);
  var q = pc;
  if (dot(n, n) > 1e-4) { n = normalize(n); q = pc + n * bitcast<f32>(vox[VX.c.w + ai]); } else { n = vec3f(0.0, 1.0, 0.0); }
  let ns = select(n, -n, dot(n, F.sunDir.xyz) < 0.0);
  let t1 = normalize(cross(ns, select(vec3f(0.0, 1.0, 0.0), vec3f(1.0, 0.0, 0.0), abs(ns.y) > 0.9)));
  let t2 = cross(ns, t1);
  let h = 0.25 * v;
  let o = q + ns * (0.25 * v + 0.03);
  let vis = 0.25 * (sunVisAt(o + h * (t1 + t2)) + sunVisAt(o + h * (t1 - t2)) + sunVisAt(o - h * (t1 + t2)) + sunVisAt(o - h * (t1 - t2)));
  vox[VX.c.w + VX.c.x + ai] = bitcast<u32>(vis);
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
  let nw = (nb0 * 16u + 63u) / 64u;
  let q = min(nw, 65535u);
  args[20] = q; args[21] = select(0u, (nw + q - 1u) / max(q, 1u), q > 0u); args[22] = 1u;
}

`;

export const VOX_STAGES = ['clear', 'markBricks', 'allocBricks', 'voxBits', 'reduce', 'allocVoxels', 'resolve', 'sun'] as const;

export interface VoxWorld {
  params: VoxParams;
  vox: GPUBuffer;
  uniform: GPUBuffer;
  bytes: number;           // allocated, the build temporaries included (they are used every frame)
  /** Triangles voxelised this frame (the static ones of the work items inside the windows; no path skips unchanged geometry). */
  staticTriangles(): number;
  /** This frame's work items (phase 32). */
  items(): WorkItem[];
  update(eye: [number, number, number]): void;
  /** This frame's work inside the caller's pass. */
  encode(pass: GPUComputePassEncoder): void;
  /** Same work, one pass per stage with timestamps at slots [base, base + 2 * VOX_STAGES.length) when querySet is given. */
  encodeStaged(enc: GPUCommandEncoder, querySet: GPUQuerySet | null, base: number): void;
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

export const VOX_UNIFORM_BYTES = 64 + 8 * 16;
const MAX_INSTANCES = 1024, MAX_ITEMS = 16384;

/** sun: the frame uniform and the shadow map (drawn before encode) for the voxels' sun visibility.
 * rows: rows of the triangle table (the key stride). world (phase 32): instances, chunks and clustered copies. */
export function createVoxWorld(device: GPUDevice, scene: SceneData, gpu: SceneGpu, tri: GPUBuffer, rows: number, params: VoxParams, sun: { frame: GPUBuffer; shadow: GPUTexture },
  firstDynamicTri = scene.triangleCount, world: World | null = null): VoxWorld {
  const { v0, levels: NL, G, maxBricks, maxVoxels } = params;
  if (NL > 8) throw new Error('at most 8 levels');
  if (world && (world.v0 !== v0 || world.levels !== NL)) throw new Error(`the world's clustered copies were made for v0 ${world.v0}, ${world.levels} levels`);
  if (world && world.instances.length > MAX_INSTANCES) throw new Error('too many instances');
  if (world && rows * world.instances.length >= 2 ** 32) throw new Error('triangle keys overflow');
  const ptrOff = HDR, brickOff = ptrOff + NL * G ** 3, attrOff = brickOff + maxBricks * BRICK_WORDS;
  // Phase 23: 4 words per voxel attribute after the attributes, the indirect irradiance on the two sides of the voxel
  // (along its normal, then against it; rg, b as half floats), written every frame by bounce.ts (bnInject).
  const bnOff = attrOff + maxVoxels * 2;
  // Phase 29: then 1 word per voxel attribute, the representative's plane offset from the voxel centre along the stored normal
  // (f32, m), and 1 word, the sun visibility of the voxel's face (voxSun).
  const plOff = bnOff + maxVoxels * 4;
  const words = plOff + maxVoxels * 2;
  const S = GPUBufferUsage.STORAGE;
  const vox = device.createBuffer({ label: 'vox', size: words * 4, usage: S | GPUBufferUsage.COPY_SRC });
  const repBuf = device.createBuffer({ label: 'vox.rep', size: maxBricks * 512 * 4, usage: S });
  const BIG_CAP = 1 << 18;
  // Phase 32: after the big-triangle segments, the chunk lists (world), the instance offsets and this frame's work items.
  const LIST_OFF = 8 + 16 * BIG_CAP;
  const listOff: number[][] = [];
  let listWords = 0;
  if (world) for (const ch of world.chunks) { listOff.push(ch.lod.map((l) => { const o = LIST_OFF + listWords; listWords += l.length; return o; })); }
  const INST_OFF = LIST_OFF + listWords, ITEM_OFF = INST_OFF + MAX_INSTANCES * 4;
  const big = device.createBuffer({ label: 'vox.big', size: (ITEM_OFF + MAX_ITEMS * 4) * 4, usage: S | GPUBufferUsage.COPY_DST });
  if (world) {
    world.chunks.forEach((ch, c) => ch.lod.forEach((l, s) => device.queue.writeBuffer(big, listOff[c][s] * 4, l)));
    const inst = new Float32Array(world.instances.length * 4);
    world.instances.forEach((o, i) => inst.set(o, i * 4));
    device.queue.writeBuffer(big, INST_OFF * 4, inst);
  } else device.queue.writeBuffer(big, INST_OFF * 4, new Float32Array(4));
  const args = device.createBuffer({ label: 'vox.args', size: 24 * 4, usage: S | GPUBufferUsage.INDIRECT });
  const uniform = device.createBuffer({ label: 'vox.u', size: VOX_UNIFORM_BYTES, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  const C = GPUShaderStage.COMPUTE;
  const st = (type: GPUBufferBindingType) => ({ visibility: C, buffer: { type } });
  const bgl = device.createBindGroupLayout({ entries: [
    { binding: 0, ...st('uniform') }, { binding: 1, ...st('storage') }, { binding: 2, ...st('storage') }, { binding: 3, ...st('storage') },
    { binding: 4, ...st('uniform') },
    { binding: 5, ...st('read-only-storage') }, { binding: 6, ...st('read-only-storage') }, { binding: 7, ...st('read-only-storage') },
    { binding: 8, ...st('read-only-storage') }, { binding: 9, ...st('read-only-storage') },
    { binding: 10, visibility: C, texture: { viewDimension: '2d-array' } }, { binding: 11, visibility: C, sampler: {} },
  ] });
  const module = device.createShaderModule({ code: BUILD_WGSL, label: 'vox.build' });
  const layout = device.createPipelineLayout({ bindGroupLayouts: [bgl] });
  const pipes: Record<string, GPUComputePipeline> = Object.fromEntries(['clear', 'markBricks', 'markBricksBig', 'markParents', 'countMarks', 'scanMarks', 'allocBricks', 'clearKeys', 'voxBits', 'voxBitsBig',
    'reduce', 'allocVoxels', 'resolveAttr'].map((e) => [e, device.createComputePipeline({ label: `vox.${e}`, layout, compute: { module, entryPoint: e } })]));
  const sampler = device.createSampler({ minFilter: 'linear', magFilter: 'linear', mipmapFilter: 'linear', addressModeU: 'repeat', addressModeV: 'repeat' });
  // reduce builds level L with the bind group of index L (its RL); the other entry points use index 0.
  const levelU = Array.from({ length: NL }, (_, L) => {
    const u = device.createBuffer({ label: `vox.level${L}`, size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    device.queue.writeBuffer(u, 0, new Uint32Array([L, 0, 0, 0]));
    return u;
  });
  const baseColorView = gpu.baseColor.createView({ dimension: '2d-array' });
  const levelBg = levelU.map((u) => device.createBindGroup({ layout: bgl, entries: [
    { binding: 0, resource: { buffer: uniform } }, { binding: 1, resource: { buffer: vox } }, { binding: 2, resource: { buffer: repBuf } },
    { binding: 3, resource: { buffer: big } }, { binding: 4, resource: { buffer: u } }, { binding: 5, resource: { buffer: gpu.positions } },
    { binding: 6, resource: { buffer: gpu.normals } }, { binding: 7, resource: { buffer: gpu.uvs } }, { binding: 8, resource: { buffer: tri } },
    { binding: 9, resource: { buffer: gpu.materials } }, { binding: 10, resource: baseColorView },
    { binding: 11, resource: sampler },
  ] }));
  const bg = levelBg[0];
  const argsModule = device.createShaderModule({ code: ARGS_WGSL, label: 'vox.args' });
  pipes.writeArgs = device.createComputePipeline({ label: 'vox.writeArgs', layout: 'auto', compute: { module: argsModule, entryPoint: 'writeArgs' } });
  const sunModule = device.createShaderModule({ code: SUN_WGSL, label: 'vox.sun' });
  pipes.voxSun = device.createComputePipeline({ label: 'vox.voxSun', layout: 'auto', compute: { module: sunModule, entryPoint: 'voxSun' } });
  const bgs: Record<string, GPUBindGroup> = Object.fromEntries(Object.keys(pipes).map((n) => [n, bg]));
  bgs.voxSun = device.createBindGroup({ layout: pipes.voxSun.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: uniform } }, { binding: 1, resource: { buffer: vox } }, { binding: 2, resource: { buffer: sun.frame } },
    { binding: 3, resource: sun.shadow.createView({ dimension: '2d-array' }) },
    { binding: 4, resource: device.createSampler({ compare: 'less-equal', minFilter: 'linear', magFilter: 'linear' }) },
  ] });
  bgs.writeArgs = device.createBindGroup({ layout: pipes.writeArgs.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: uniform } }, { binding: 1, resource: { buffer: vox } }, { binding: 2, resource: { buffer: args } },
  ] });
  const T = firstDynamicTri; // static triangles only
  let items: WorkItem[] = [{ inst: 0, start: 0, list: -1, first: 0, count: T }];
  let threads = T;
  const lin = (pass: GPUComputePassEncoder, n: number) => {
    const g = Math.ceil(n / 64), x = Math.min(g, 65535);
    if (g > 0) pass.dispatchWorkgroups(x, Math.ceil(g / x));
  };
  const use = (pass: GPUComputePassEncoder, name: string) => { pass.setPipeline(pipes[name]); pass.setBindGroup(0, bgs[name]); };
  const bytes = vox.size + repBuf.size + big.size + args.size + uniform.size + NL * 16;
  const stage = (pass: GPUComputePassEncoder, st: typeof VOX_STAGES[number]) => {
    const tris = threads;
    switch (st) {
      case 'clear': use(pass, 'clear'); lin(pass, Math.max(NL * G ** 3, HDR)); break;
      case 'markBricks':
        use(pass, 'markBricks'); lin(pass, tris);
        use(pass, 'writeArgs'); pass.dispatchWorkgroups(1);
        use(pass, 'markBricksBig'); pass.dispatchWorkgroupsIndirect(args, 64);
        use(pass, 'markParents'); lin(pass, (NL - 1) * G ** 3);
        break;
      case 'allocBricks':
        use(pass, 'countMarks'); lin(pass, NL * G ** 3);
        use(pass, 'scanMarks'); pass.dispatchWorkgroups(1);
        use(pass, 'allocBricks'); lin(pass, NL * G ** 3);
        use(pass, 'writeArgs'); pass.dispatchWorkgroups(1);
        use(pass, 'clearKeys'); pass.dispatchWorkgroupsIndirect(args, 16);
        break;
      case 'voxBits':
        use(pass, 'voxBits'); lin(pass, tris);
        use(pass, 'writeArgs'); pass.dispatchWorkgroups(1);
        use(pass, 'voxBitsBig'); pass.dispatchWorkgroupsIndirect(args, 0);
        break;
      case 'reduce':
        // args (slot 20: one thread per word of every brick) were written after allocBricks by the voxBits stage.
        for (let L = 1; L < NL; L++) {
          pass.setPipeline(pipes.reduce); pass.setBindGroup(0, levelBg[L]); pass.dispatchWorkgroupsIndirect(args, 80);
        }
        break;
      case 'allocVoxels':
        use(pass, 'writeArgs'); pass.dispatchWorkgroups(1);
        use(pass, 'allocVoxels'); pass.dispatchWorkgroupsIndirect(args, 48);
        break;
      case 'resolve': use(pass, 'resolveAttr'); pass.dispatchWorkgroupsIndirect(args, 32); break;
      case 'sun': use(pass, 'voxSun'); pass.dispatchWorkgroupsIndirect(args, 32); break;
    }
  };

  const writeUniform = (eye: [number, number, number]) => {
    const buf = new ArrayBuffer(VOX_UNIFORM_BYTES);
    const f = new Float32Array(buf), u = new Uint32Array(buf), i = new Int32Array(buf);
    const windows: { lo: Vec3; hi: Vec3 }[] = [];
    for (let L = 0; L < NL; L++) {
      const bs = v0 * 2 ** L * 8;
      const o = [0, 1, 2].map((a) => Math.floor(eye[a] / bs) - G / 2);
      i.set(o.concat([0]), 16 + L * 4);
      windows.push({ lo: o.map((x) => x * bs) as Vec3, hi: o.map((x) => (x + G) * bs) as Vec3 });
    }
    // This frame's work items (phase 32): the chunks of the instances inside the windows, from their finest window on.
    if (world) {
      items = selectItems(world, (c, s) => listOff[c][s], windows);
      if (items.length > MAX_ITEMS) throw new Error(`too many work items: ${items.length}`);
    }
    const rec = new Uint32Array(items.length * 4);
    threads = 0;
    items.forEach((it, k) => { rec.set([threads, it.list < 0 ? 0x80000000 | it.first : it.list, it.inst, it.start], k * 4); threads += it.count; });
    device.queue.writeBuffer(big, ITEM_OFF * 4, rec);
    f.set([v0, NL, G, BRICK_WORDS], 0);
    u.set([ptrOff, brickOff, attrOff, maxBricks], 4);
    u.set([maxVoxels, threads, bnOff, plOff], 8);
    u.set([rows, ITEM_OFF, items.length, INST_OFF], 12);
    device.queue.writeBuffer(uniform, 0, buf);
  };

  return {
    params, vox, uniform, bytes, staticTriangles: () => threads, items: () => items,
    update(eye) { writeUniform(eye); },
    encode(pass) {
      for (const st of VOX_STAGES) stage(pass, st);
    },
    encodeStaged(enc, querySet, base) {
      VOX_STAGES.forEach((st, i) => {
        const pass = enc.beginComputePass({ label: `vox.${st}`,
          timestampWrites: querySet ? { querySet, beginningOfPassWriteIndex: base + 2 * i, endOfPassWriteIndex: base + 2 * i + 1 } : undefined });
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
      return { persistent: (HDR + NL * G ** 3 + c.bricks * BRICK_WORDS + Math.min(c.voxels, maxVoxels) * 8) * 4 + uniform.size,
        buildTemp: c.bricks * 512 * 4 };
    },
    destroy() { for (const b of [vox, repBuf, big, args, uniform, ...levelU]) b.destroy(); },
  };
}

