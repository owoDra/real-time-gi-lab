// P2: the dynamic layer. Dynamic triangles (the tail of the triangle table) are not in the binary voxel bricks;
// every frame they are written into this separate layer of coverage and mean radiance, prefiltered from fine to
// coarse levels, and the interval tracers read it at the level that matches the width of the direction bin's cone.
//
// Build (every frame, after the shadow map):
//  mark     per dynamic triangle: its splat level (the finest level whose clipmap holds it) and every brick its box,
//           grown by one voxel, touches at that level, as bits of this frame's bitset; the bounds of the workgroup's
//           triangles
//  parents  every wanted brick wants its ancestors on all coarser levels (they hold its prefiltered values)
//  count    per block of 256 bitset words: the wanted bricks
//  alloc    every wanted brick gets the slot of its rank in bit order (coarse levels first, then by brick index):
//           deterministic, and when the pool is too small the finest bricks with the highest index are dropped
//           (marked so that the read falls back to the coarser level). Bricks wanted last frame and not now are
//           emptied. Each level's bricks are one contiguous range of slots.
//  finalize counts per level and the indirect dispatch sizes of clear and resolve; publishes the bounds and flips
//           which of the two brick bitsets is the next frame's
//  clear    the allocated bricks' accumulators and their bits of non-zero voxels
//  splat    per dynamic triangle: m^2 equal sub-triangles (m from the edge length, about one voxel of the splat
//           level), each a sample at its centroid with its area, shaded there like a voxel hit (albedo, outward
//           normal, sun, shadow map, toon operator). Each sample adds, with trilinear weights over the 8 nearest
//           voxel centres (fixed point), its area projected on the 6 axis directions (front and back separately),
//           its area and its area x radiance. Trilinear splats of samples that move with the object make every
//           voxel value continuous in the object's pose: no voxel switches on or off. A workgroup's 64 triangles
//           (neighbours: the dynamic triangles are sorted by a Morton code of their rest centroids) add into a window
//           of voxels (their box, up to WIN voxels) in workgroup memory and the window is added to the layer once; corners outside the window go
//           straight to the layer. Fixed point sums are exact, so the result does not depend on the order.
//  resolve  levels 1.. from fine to coarse: a voxel's value (float, in units of its own voxel face v^2) is its
//           own splats plus the sum of its 8 children (one brick), reading only the non-zero ones; voxels with nothing
//           stay zero. Level 0 stays fixed point (read as such).
// Read (traceDyn): the segment is marched with steps of half the cone width w = t * sqrt(4 pi / res^2); at each
// step the layer is read at the two levels around v = w (nearest voxel) and interpolated between them. A voxel's
// coverage for direction d is front / v^2 with front = sum_a |d_a| P(faces against d), so a closed object inside
// one voxel covers its projected area and a surface crossing a fine voxel covers it whole; it is scaled by the step
// length / v. Faces along d (seen from inside a closed object) do not cover: probes that end up inside a dynamic
// object (the relocation sees only the static voxels) look out through it instead of at its inner shell. Coverage is accumulated additively front to back and clamped at 1
// (a wall split between two voxels then still covers the ray fully); the covered part carries the voxels' mean
// radiance (area-weighted mean of the samples).
import { FRAME_WGSL, SHADOW_TAP_WGSL } from './frame.ts';
import type { SceneGpu } from './scene_gpu.ts';
import { STYLE_WGSL } from './style.ts';
import { DEFAULT_VOX, VOX_STRUCT_WGSL, type VoxParams } from './voxel.ts';

/** Default brick pool of the dynamic layer (VoxParams.dynBricks; the shaders take it as the override constant
 * DYN_MAX_BRICKS): 64 moving objects in Sponza need up to 1241 bricks. */
export const DYN_MAX_BRICKS = DEFAULT_VOX.dynBricks;
/** Pipeline constants for a pool other than the default (none for the default). */
export const dynConstants = (n: number): Record<string, number> | undefined => n === DYN_MAX_BRICKS ? undefined : { DYN_MAX_BRICKS: n };
// Header words: 0 wanted bricks, 1 dropped bricks, 2..7 bounds, 8 allocated bricks, 9 triangles outside every
// clipmap, 10 frame counter (bitset parity), 16 + L first slot of level L, 24 + L bricks of level L, 32..37 bounds and
// 38 outside count being marked (published by finalize).
const HDR = 64;
const WORDS = 13; // per voxel: P+x P-x P+y P-y P+z P-z, area, area x radiance (rgb), area x albedo (rgb; phase 31)
const FIX = 65536;
const WIN = 144; // voxels of the splat window in workgroup memory (WIN * WORDS words, 7.3 of the 16 KiB; phase 31: 192 with 13 words cost 0.03 ms more)
const SWG = 64; // splat workgroup size
/** Words before the voxel data: header, pointer table, two bitsets, block counts, slot -> brick, and per slot
 * 16 words of bits of its non-zero voxels (build only). */
function layout(levels: number, G: number, cap: number) {
  const ptrCount = levels * G ** 3, nw = ptrCount / 32, nblk = Math.ceil(nw / 256);
  return { ptrCount, nw, nblk, data: HDR + ptrCount + 2 * nw + nblk + cap * 17 };
}
// Same in WGSL (VX.a: v0, levels, G).
const LAYOUT_WGSL = /* wgsl */ `
const DYN_EMPTY = 0xffffffffu;
const DYN_DROPPED = 0xfffffffdu;
fn dynPtrCount() -> u32 { let G = u32(VX.a.z); return u32(VX.a.y) * G * G * G; }
fn dynNW() -> u32 { return dynPtrCount() / 32u; }
fn dynBitsOff() -> u32 { return ${HDR}u + dynPtrCount(); }
fn dynBlkOff() -> u32 { return dynBitsOff() + 2u * dynNW(); }
fn dynMetaOff() -> u32 { return dynBlkOff() + (dynNW() + 255u) / 256u; }
fn dynMaskOff() -> u32 { return dynMetaOff() + DYN_MAX_BRICKS; }
fn dynDataOff() -> u32 { return dynMaskOff() + DYN_MAX_BRICKS * 16u; }
`;

/** Read side, shared by the RC and DDGI tracers. Needs VX (VoxU), voxSize, voxG, voxLevelFor, dyn (array<u32>). */
export const DYN_READ_WGSL = /* wgsl */ `
override DYN_MAX_BRICKS: u32 = ${DYN_MAX_BRICKS}u;
${LAYOUT_WGSL}
// (data base of the voxel at p, level read): the voxel of level L, or of the first coarser level whose brick was
// not dropped (pool too small); base 0xffffffff when the brick is empty.
fn dynFind(L: u32, p: vec3f) -> vec2u {
  let G = voxG();
  let ug = u32(G);
  let nl = u32(VX.a.y);
  var l = L;
  loop {
    let v = voxSize(l);
    let c = vec3i(floor((p - vec3f(VX.origin[l].xyz) * v * 8.0) / v));
    if (any(c < vec3i(0)) || any(c >= vec3i(G * 8))) { return vec2u(0xffffffffu, l); }
    let b = vec3u(c >> vec3u(3u));
    let ptr = dyn[${HDR}u + l * ug * ug * ug + (b.z * ug + b.y) * ug + b.x];
    if (ptr == DYN_DROPPED && l + 1u < nl) { l++; continue; }
    if (ptr >= DYN_MAX_BRICKS) { return vec2u(0xffffffffu, l); }
    let lc = c & vec3i(7);
    return vec2u(dynDataOff() + (ptr * 512u + u32(lc.x + 8 * lc.y + 64 * lc.z)) * ${WORDS}u, l);
  }
}
// Word k of a voxel of level L (level 0 stays fixed point).
fn dynWord(base: u32, k: u32, L: u32) -> f32 {
  let u = dyn[base + k];
  if (L == 0u) { return f32(u) / ${FIX}.0; }
  return bitcast<f32>(u);
}
// (mean radiance, coverage per voxel length) of the voxel at base (level L) for direction d.
fn dynRead(base: u32, L: u32, d: vec3f) -> vec4f {
  if (base == 0xffffffffu) { return vec4f(0.0); }
  let a = dynWord(base, 6u, L);
  if (a <= 0.0) { return vec4f(0.0); }
  // Only the three faces against d (P+x P-x P+y P-y P+z P-z: the + face is read for d > 0).
  let ad = abs(d);
  let sx = select(0u, 1u, d.x > 0.0); let sy = select(0u, 1u, d.y > 0.0); let sz = select(0u, 1u, d.z > 0.0);
  let front = ad.x * dynWord(base, sx, L) + ad.y * dynWord(base, 2u + sy, L) + ad.z * dynWord(base, 4u + sz, L);
  let r = vec3f(dynWord(base, 7u, L), dynWord(base, 8u, L), dynWord(base, 9u, L)) / a;
  return vec4f(r, min(front, 1.0));
}
// Covered radiance and coverage of [t0, t1] along d from o, for a cone of width k * t (k = sqrt(solid angle)).
// The step positions depend only on t0 and k, not on where the dynamic objects are.
fn traceDyn(o: vec3f, d: vec3f, t0: f32, t1: f32, k: f32) -> vec4f {
  if (dyn[0] == 0u || t1 <= t0) { return vec4f(0.0); }
  // Bounds in cm, offset by 2^30 (unsigned atomics).
  let bmin = (vec3f(vec3u(dyn[2], dyn[3], dyn[4])) - 1073741824.0) * 0.01;
  let bmax = (vec3f(vec3u(dyn[5], dyn[6], dyn[7])) - 1073741824.0) * 0.01;
  let dd = select(d, vec3f(1e-9), abs(d) < vec3f(1e-9));
  let ta = (bmin - o) / dd; let tb = (bmax - o) / dd;
  let tn = min(ta, tb); let tf = max(ta, tb);
  let ba = max(max(max(tn.x, tn.y), tn.z), t0);
  let bb = min(min(min(tf.x, tf.y), tf.z), t1);
  if (ba >= bb) { return vec4f(0.0); }
  let v0 = VX.a.x;
  let nl = u32(VX.a.y);
  var rad = vec3f(0.0); var cov = 0.0;
  var t = t0;
  for (var i = 0u; i < 128u; i++) {
    if (t >= bb || cov >= 1.0) { break; }
    let w = max(k * t, v0);
    let te = min(t + 0.5 * w, t1);
    if (te > ba) {
      let len = te - t;
      let p = o + d * (0.5 * (t + te));
      let lf = clamp(log2(w / v0), 0.0, f32(nl - 1u));
      var L0 = u32(floor(lf)); var f = lf - f32(L0);
      let Lw = voxLevelFor(L0, p);
      if (Lw != L0) { L0 = Lw; f = 0.0; }
      let fa = dynFind(L0, p);
      let sa = dynRead(fa.x, fa.y, d);
      var aa = sa.a * len / voxSize(fa.y);
      var ra = sa.rgb * aa;
      if (f > 0.0 && L0 + 1u < nl) {
        let fb = dynFind(L0 + 1u, p);
        let sb = dynRead(fb.x, fb.y, d);
        let ab = sb.a * len / voxSize(fb.y);
        ra = mix(ra, sb.rgb * ab, f); aa = mix(aa, ab, f);
      }
      if (aa > 0.0) {
        let a = min(aa, 1.0 - cov);
        rad += ra * (a / aa); cov += a;
      }
    }
    t = te;
  }
  return vec4f(rad, cov);
}
`;

/** Phase 31: the dynamic objects receive the indirect light. After the build, one thread per voxel of the allocated
 * bricks (every level; dispatched with DynLayer.args, as clear) adds albedo / pi x irradiance to the voxel's radiance:
 * area x albedo (words 10..12) / pi x E, with E the irradiance of the GI method that includes it (RC: the bounce
 * volume, DDGI: its probes; both as the previous frame left them), weighted over the six axis faces by the voxel's
 * projected areas: E = sum_a P_a E_a / sum_a P_a. A toon object reflects it as Lambert (the emission-side operator acts
 * on the sun term only, as at the voxel hits). The includer binds dyn as read_write array<u32>, includes DYN_READ_WGSL
 * and VX, defines PI and dynE(p, P, v, L) -> E (p the voxel centre, P the six projected areas, v the voxel size). */
export const DYN_INJECT_WGSL = /* wgsl */ `
@compute @workgroup_size(64) fn dynInject(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = (wid.y * nwg.x + wid.x) * 64u + li;
  let slot = i / 512u; let bit = i % 512u;
  if (slot >= dyn[8]) { return; }
  let G = u32(VX.a.z); let G3 = G * G * G;
  let pi = dyn[dynMetaOff() + slot];
  let L = pi / G3; let r = pi % G3;
  let base = dynDataOff() + (slot * 512u + bit) * ${WORDS}u;
  if (dynWord(base, 6u, L) <= 0.0) { return; }
  var P: array<f32, 6>;
  for (var k = 0u; k < 6u; k++) { P[k] = dynWord(base, k, L); }
  let c = vec3i(i32(r % G), i32((r / G) % G), i32(r / (G * G))) * 8 + vec3i(i32(bit & 7u), i32((bit >> 3u) & 7u), i32(bit >> 6u));
  let v = voxSize(L);
  let p = vec3f(VX.origin[L].xyz) * v * 8.0 + (vec3f(c) + 0.5) * v;
  let add = vec3f(dynWord(base, 10u, L), dynWord(base, 11u, L), dynWord(base, 12u, L)) / PI * dynE(p, P, v, L);
  for (var k = 0u; k < 3u; k++) {
    if (L == 0u) { dyn[base + 7u + k] += u32(round(add[k] * ${FIX}.0)); }
    else { dyn[base + 7u + k] = bitcast<u32>(bitcast<f32>(dyn[base + 7u + k]) + add[k]); }
  }
}
`;

const BUILD_WGSL = /* wgsl */ `
${FRAME_WGSL}
${STYLE_WGSL}
${VOX_STRUCT_WGSL}
const PI = 3.14159265;
struct Material { baseColorFactor: vec4f, layers: vec4u, params: vec4f }
@group(0) @binding(0) var<uniform> VX: VoxU;
@group(0) @binding(1) var<storage, read_write> dyn: array<atomic<u32>>;
@group(0) @binding(2) var<uniform> F: Frame;
@group(0) @binding(3) var<uniform> DL: vec4u; // first dynamic triangle, end of the triangles, level (resolve), 0
@group(0) @binding(5) var<storage, read> positions: array<f32>;
@group(0) @binding(6) var<storage, read> normals: array<f32>;
@group(0) @binding(7) var<storage, read> uvs: array<f32>;
@group(0) @binding(8) var<storage, read> tri: array<vec4u>;
@group(0) @binding(9) var<storage, read> materials: array<Material>;
@group(0) @binding(10) var baseColorTex: texture_2d_array<f32>;
@group(0) @binding(11) var samp: sampler;
@group(0) @binding(12) var shadowTex: texture_depth_2d_array;
@group(0) @binding(13) var shadowCmp: sampler_comparison;
// Indirect dispatch sizes (finalize only): clear, then resolve of each level.
@group(1) @binding(0) var<storage, read_write> args: array<u32>;

override DYN_MAX_BRICKS: u32 = ${DYN_MAX_BRICKS}u;
${LAYOUT_WGSL}
const W = ${WORDS}u;
const FIX = ${FIX}.0;
const NONE = 0xffffffffu;
fn lin(wid: vec3u, nwg: vec3u, li: u32) -> u32 { return (wid.y * nwg.x + wid.x) * 64u + li; }
fn P(i: u32) -> vec3f { return vec3f(positions[i * 3u], positions[i * 3u + 1u], positions[i * 3u + 2u]); }
fn N(i: u32) -> vec3f { return vec3f(normals[i * 3u], normals[i * 3u + 1u], normals[i * 3u + 2u]); }
fn UV(i: u32) -> vec2f { return vec2f(uvs[i * 2u], uvs[i * 2u + 1u]); }
fn regionLo(L: u32) -> vec3f { return vec3f(VX.origin[L].xyz) * voxSize(L) * 8.0; }
fn ptrIndex(L: u32, b: vec3i) -> u32 { let G = u32(VX.a.z); return L * G * G * G + (u32(b.z) * G + u32(b.y)) * G + u32(b.x); }
fn curBits() -> u32 { return dynBitsOff() + (atomicLoad(&dyn[10]) & 1u) * dynNW(); }
fn prevBits() -> u32 { return dynBitsOff() + (1u - (atomicLoad(&dyn[10]) & 1u)) * dynNW(); }
// Splat level of a triangle: the finest level whose clipmap holds its box grown by two voxels.
fn splatLevel(mn: vec3f, mx: vec3f) -> u32 {
  let n = u32(VX.a.y);
  for (var L = 0u; L < n; L++) {
    let v = voxSize(L); let lo = regionLo(L); let hi = lo + f32(voxG()) * v * 8.0;
    if (all(mn - 2.0 * v > lo) && all(mx + 2.0 * v < hi)) { return L; }
  }
  return NONE;
}
${SHADOW_TAP_WGSL}
fn sunVis(x: vec3f) -> f32 { return shadowTap(x); }


// Brick b of level L is wanted this frame (bit order: coarse levels first).
fn want(L: u32, b: vec3i) {
  let G = i32(VX.a.z);
  if (any(b < vec3i(0)) || any(b >= vec3i(G))) { return; }
  let ug = u32(G);
  let g = (u32(VX.a.y) - 1u - L) * ug * ug * ug + (u32(b.z) * ug + u32(b.y)) * ug + u32(b.x);
  let w = curBits() + (g >> 5u); let m = 1u << (g & 31u);
  if ((atomicLoad(&dyn[w]) & m) == 0u) { atomicOr(&dyn[w], m); }
}
var<workgroup> wbmin: array<atomic<u32>, 3>;
var<workgroup> wbmax: array<atomic<u32>, 3>;
@compute @workgroup_size(64) fn mark(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  if (li < 3u) { atomicStore(&wbmin[li], 0xffffffffu); atomicStore(&wbmax[li], 0u); }
  workgroupBarrier();
  let t = lin(wid, nwg, li) + DL.x;
  if (t < DL.y) {
    let i = tri[t];
    let a = P(i.x); let b = P(i.y); let c = P(i.z);
    let mn = min(min(a, b), c); let mx = max(max(a, b), c);
    let Ls = splatLevel(mn, mx);
    if (Ls == NONE) { atomicAdd(&dyn[38], 1u); }
    else {
      let n = u32(VX.a.y);
      let bs = voxSize(Ls) * 8.0; let lo = regionLo(Ls);
      let g0 = vec3i(floor((mn - voxSize(Ls) - lo) / bs)); let g1 = vec3i(floor((mx + voxSize(Ls) - lo) / bs));
      for (var z = g0.z; z <= g1.z; z++) { for (var y = g0.y; y <= g1.y; y++) { for (var x = g0.x; x <= g1.x; x++) {
        want(Ls, vec3i(x, y, z));
      } } }
      // Bounds of everything a read can see: the box grown by the coarsest voxel (cm, offset by 2^30).
      let gv = voxSize(n - 1u);
      let blo = vec3u(vec3i(floor((mn - gv) * 100.0)) + 1073741824); let bhi = vec3u(vec3i(ceil((mx + gv) * 100.0)) + 1073741824);
      atomicMin(&wbmin[0], blo.x); atomicMin(&wbmin[1], blo.y); atomicMin(&wbmin[2], blo.z);
      atomicMax(&wbmax[0], bhi.x); atomicMax(&wbmax[1], bhi.y); atomicMax(&wbmax[2], bhi.z);
    }
  }
  workgroupBarrier();
  if (li < 3u) { atomicMin(&dyn[32u + li], atomicLoad(&wbmin[li])); atomicMax(&dyn[35u + li], atomicLoad(&wbmax[li])); }
}

// One thread per bitset word of the levels below the coarsest: each wanted brick wants its ancestors. A brick's
// 8 voxels map to 4 voxels of the next level, which lie in one brick (origins are whole bricks).
@compute @workgroup_size(64) fn parents(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let G = u32(VX.a.z); let G3 = G * G * G; let n = u32(VX.a.y);
  let w = lin(wid, nwg, li) + G3 / 32u; // skip the coarsest level (first in bit order)
  if (w >= dynNW()) { return; }
  var m = atomicLoad(&dyn[curBits() + w]);
  loop {
    if (m == 0u) { break; }
    let bit = firstTrailingBit(m);
    m &= ~(1u << bit);
    let g = w * 32u + bit;
    let lr = g / G3;
    var L = n - 1u - lr;
    let r = g - lr * G3;
    var b = vec3i(i32(r % G), i32((r / G) % G), i32(r / (G * G)));
    loop {
      if (L + 1u >= n) { break; }
      b = ((VX.origin[L].xyz + b) * 8 / 2 - VX.origin[L + 1u].xyz * 8) >> vec3u(3u);
      L++;
      want(L, b);
    }
  }
}

var<workgroup> sc: array<u32, 256>;
// Sum of sc over the workgroup, returned to every thread (sc is free again after it).
fn wgSum(li: u32, x: u32) -> u32 {
  sc[li] = x;
  workgroupBarrier();
  for (var s = 128u; s > 0u; s >>= 1u) {
    if (li < s) { sc[li] += sc[li + s]; }
    workgroupBarrier();
  }
  let r = sc[0];
  workgroupBarrier();
  return r;
}
@compute @workgroup_size(256) fn count(@builtin(workgroup_id) wid: vec3u, @builtin(local_invocation_index) li: u32) {
  let w = wid.x * 256u + li;
  var c = 0u;
  if (w < dynNW()) { c = countOneBits(atomicLoad(&dyn[curBits() + w])); }
  let s = wgSum(li, c);
  if (li == 0u) { atomicStore(&dyn[dynBlkOff() + wid.x], s); }
}
@compute @workgroup_size(256) fn alloc(@builtin(workgroup_id) wid: vec3u, @builtin(local_invocation_index) li: u32) {
  let blk = wid.x;
  var s = 0u;
  for (var j = li; j < blk; j += 256u) { s += atomicLoad(&dyn[dynBlkOff() + j]); }
  let base = wgSum(li, s);
  let w = blk * 256u + li;
  let nw = dynNW();
  var cur = 0u; var old = 0u;
  if (w < nw) { cur = atomicLoad(&dyn[curBits() + w]); old = atomicLoad(&dyn[prevBits() + w]); }
  let c = countOneBits(cur);
  // Inclusive scan of c over the workgroup.
  sc[li] = c;
  workgroupBarrier();
  for (var off = 1u; off < 256u; off <<= 1u) {
    var v = 0u;
    if (li >= off) { v = sc[li - off]; }
    workgroupBarrier();
    sc[li] += v;
    workgroupBarrier();
  }
  let excl = base + sc[li] - c;
  if (w < nw) {
    let G = u32(VX.a.z); let G3 = G * G * G; let n = u32(VX.a.y);
    if ((w * 32u) % G3 == 0u) { atomicStore(&dyn[16u + n - 1u - w * 32u / G3], excl); }
    if (w == nw - 1u) { atomicStore(&dyn[0], excl + c); }
    var m = cur | old;
    loop {
      if (m == 0u) { break; }
      let bit = firstTrailingBit(m);
      m &= ~(1u << bit);
      let g = w * 32u + bit;
      let lr = g / G3;
      let pi = (n - 1u - lr) * G3 + g - lr * G3;
      if (((cur >> bit) & 1u) != 0u) {
        let rank = excl + countOneBits(cur & ((1u << bit) - 1u));
        if (rank < DYN_MAX_BRICKS) { atomicStore(&dyn[${HDR}u + pi], rank); atomicStore(&dyn[dynMetaOff() + rank], pi); }
        else { atomicStore(&dyn[${HDR}u + pi], DYN_DROPPED); }
      } else { atomicStore(&dyn[${HDR}u + pi], DYN_EMPTY); }
    }
    atomicStore(&dyn[prevBits() + w], 0u);
  }
}
fn dims(o: u32, g: u32) { let x = min(g, 65535u); args[o] = x; args[o + 1u] = select(1u, (g + x - 1u) / max(x, 1u), x > 0u); args[o + 2u] = 1u; }
@compute @workgroup_size(1) fn finalize() {
  let total = atomicLoad(&dyn[0]);
  let al = min(total, DYN_MAX_BRICKS);
  atomicStore(&dyn[8], al); atomicStore(&dyn[1], total - al);
  dims(0u, al * 8u);
  let n = u32(VX.a.y);
  for (var L = 0u; L < n; L++) {
    var e = total;
    if (L > 0u) { e = atomicLoad(&dyn[16u + L - 1u]); }
    let s0 = min(atomicLoad(&dyn[16u + L]), DYN_MAX_BRICKS);
    let c = min(e, DYN_MAX_BRICKS) - s0;
    atomicStore(&dyn[16u + L], s0); atomicStore(&dyn[24u + L], c);
    dims(3u + 3u * L, c * 8u);
  }
  // Publish the bounds and the outside count marked this frame, reset them for the next frame, flip the bitsets.
  for (var k = 0u; k < 3u; k++) {
    atomicStore(&dyn[2u + k], atomicExchange(&dyn[32u + k], 0xffffffffu));
    atomicStore(&dyn[5u + k], atomicExchange(&dyn[35u + k], 0u));
  }
  atomicStore(&dyn[9], atomicExchange(&dyn[38], 0u));
  atomicAdd(&dyn[10], 1u);
}
@compute @workgroup_size(64) fn clear(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  if (i / 512u >= atomicLoad(&dyn[8])) { return; }
  for (var k = 0u; k < W; k++) { atomicStore(&dyn[dynDataOff() + i * W + k], 0u); }
  if (i % 512u < 16u) { atomicStore(&dyn[dynMaskOff() + i / 512u * 16u + i % 512u], 0u); }
}

// Splat window in workgroup memory: voxels o .. o + d - 1 of level L.
var<workgroup> wacc: array<atomic<u32>, ${WIN * WORDS}>;
var<workgroup> wL: atomic<u32>;
var<workgroup> wlo: array<atomic<i32>, 3>;
var<workgroup> whi: array<atomic<i32>, 3>;
var<private> winL: u32;
var<private> winO: vec3i;
var<private> winD: vec3i;
fn setMask(ptr: u32, v: u32) { atomicOr(&dyn[dynMaskOff() + ptr * 16u + (v >> 5u)], 1u << (v & 31u)); }
fn addFix(base: u32, k: u32, x: f32) { let q = u32(round(x * FIX)); if (q > 0u) { atomicAdd(&dyn[base + k], q); } }
fn addWin(j: u32, k: u32, x: f32) { let q = u32(round(x * FIX)); if (q > 0u) { atomicAdd(&wacc[j * W + k], q); } }
fn splatSample(L: u32, p: vec3f, n: vec3f, area: f32, rad: vec3f, alb: vec3f) {
  let v = voxSize(L);
  let g = (p - regionLo(L)) / v - 0.5;
  let c0 = vec3i(floor(g)); let f = g - vec3f(c0);
  let s = area / (v * v);
  let pn = max(n, vec3f(0.0)); let nn = max(-n, vec3f(0.0));
  let G = voxG() * 8;
  for (var k = 0u; k < 8u; k++) {
    let o = vec3i(i32(k & 1u), i32((k >> 1u) & 1u), i32(k >> 2u));
    let c = c0 + o;
    if (any(c < vec3i(0)) || any(c >= vec3i(G))) { continue; }
    let tw = select(1.0 - f, f, o == vec3i(1));
    let w = tw.x * tw.y * tw.z * s;
    if (w <= 0.0) { continue; }
    let r = c - winO;
    if (L == winL && all(r >= vec3i(0)) && all(r < winD)) {
      let j = u32(r.x + winD.x * (r.y + winD.y * r.z));
      addWin(j, 0u, w * pn.x); addWin(j, 1u, w * nn.x);
      addWin(j, 2u, w * pn.y); addWin(j, 3u, w * nn.y);
      addWin(j, 4u, w * pn.z); addWin(j, 5u, w * nn.z);
      addWin(j, 6u, w);
      addWin(j, 7u, w * rad.x); addWin(j, 8u, w * rad.y); addWin(j, 9u, w * rad.z);
      if (DYN_ALB) { addWin(j, 10u, w * alb.x); addWin(j, 11u, w * alb.y); addWin(j, 12u, w * alb.z); }
      continue;
    }
    let ptr = atomicLoad(&dyn[${HDR}u + ptrIndex(L, c >> vec3u(3u))]);
    if (ptr >= DYN_MAX_BRICKS) { continue; }
    let l = c & vec3i(7);
    let vi = u32(l.x + 8 * l.y + 64 * l.z);
    setMask(ptr, vi);
    let base = dynDataOff() + (ptr * 512u + vi) * W;
    addFix(base, 0u, w * pn.x); addFix(base, 1u, w * nn.x);
    addFix(base, 2u, w * pn.y); addFix(base, 3u, w * nn.y);
    addFix(base, 4u, w * pn.z); addFix(base, 5u, w * nn.z);
    addFix(base, 6u, w);
    addFix(base, 7u, w * rad.x); addFix(base, 8u, w * rad.y); addFix(base, 9u, w * rad.z);
    if (DYN_ALB) { addFix(base, 10u, w * alb.x); addFix(base, 11u, w * alb.y); addFix(base, 12u, w * alb.z); }
  }
}
override DYN_ALB: bool = true; // phase 31: splat the albedo (only runs whose objects receive light, DynLayer.setAlbedo)
var<private> sampleAlb: vec3f; // albedo of the last shaded sample (phase 31: dynInject adds the received light)
fn shadeSample(m: Material, p: vec3f, n: vec3f, uv: vec2f, L: u32) -> vec4f {
  let tex = textureSampleLevel(baseColorTex, samp, uv, m.layers.x, f32(3u + L)) * m.baseColorFactor;
  if ((m.layers.w & 1u) != 0u && tex.a < m.params.z) { return vec4f(0.0, 0.0, 0.0, -1.0); }
  sampleAlb = tex.rgb;
  let ndl = max(dot(n, F.sunDir.xyz), 0.0);
  if (ndl <= 0.0) { return vec4f(0.0); }
  let vis = sunVis(p + n * 0.03);
  if ((m.layers.w & 4u) != 0u && F.style.x > 0.5) { return vec4f(toonSun(tex.rgb, ndl, vis, F.sunE.rgb), 0.0); }
  return vec4f(tex.rgb / PI * F.sunE.rgb * ndl * vis, 0.0);
}
// This thread's triangle (loaded once): indices and material, corners, splat level (NONE: no triangle).
var<private> ti: vec4u;
var<private> ta: vec3f;
var<private> tb: vec3f;
var<private> tc: vec3f;
var<private> tL: u32;
// Splat of this thread's triangle into the window or the layer.
fn splatTri() {
  let L = tL; let i = ti; let a = ta; let b = tb; let c = tc;
  if (L == NONE) { return; }
  let area = 0.5 * length(cross(b - a, c - a));
  if (area <= 0.0) { return; }
  let e = max(max(length(b - a), length(c - b)), length(a - c));
  let m = u32(clamp(ceil(e / voxSize(L)), 1.0, 16.0));
  let fm = f32(m);
  let sa = area / (fm * fm);
  let mat = materials[i.w];
  for (var u = 0u; u < m; u++) {
    for (var v = 0u; v + u < m; v++) {
      for (var flip = 0u; flip < 2u; flip++) {
        if (flip == 1u && u + v + 1u >= m) { continue; }
        let off = select(1.0 / 3.0, 2.0 / 3.0, flip == 1u);
        let wb = (f32(u) + off) / fm; let wc = (f32(v) + off) / fm; let wa = 1.0 - wb - wc;
        let p = a * wa + b * wb + c * wc;
        var n = N(i.x) * wa + N(i.y) * wb + N(i.z) * wc;
        n = normalize(select(cross(b - a, c - a), n, dot(n, n) > 1e-12));
        let uv = UV(i.x) * wa + UV(i.y) * wb + UV(i.z) * wc;
        let s = shadeSample(mat, p, n, uv, L);
        if (s.a < 0.0) { continue; }
        splatSample(L, p, n, sa, s.rgb, sampleAlb);
      }
    }
  }
}
// The workgroup's 64 consecutive triangles go into one window: the box of those at the finest splat level among
// them (others add straight to the layer).
@compute @workgroup_size(${SWG}) fn splat(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  if (li == 0u) {
    atomicStore(&wL, NONE);
    for (var k = 0u; k < 3u; k++) { atomicStore(&wlo[k], 0x7fffffff); atomicStore(&whi[k], -0x7fffffff); }
  }
  let t = (wid.y * nwg.x + wid.x) * ${SWG}u + li + DL.x;
  tL = NONE;
  if (t < DL.y) {
    ti = tri[t];
    ta = P(ti.x); tb = P(ti.y); tc = P(ti.z);
    tL = splatLevel(min(min(ta, tb), tc), max(max(ta, tb), tc));
  }
  workgroupBarrier();
  if (tL != NONE) { atomicMin(&wL, tL); }
  workgroupBarrier();
  winL = atomicLoad(&wL);
  if (tL != NONE && tL == winL) {
    // Voxels the samples' trilinear corners can reach: floor(x / v - 0.5) .. + 1 over the triangle's box.
    let v = voxSize(winL); let lo = regionLo(winL);
    let c0 = vec3i(floor((min(min(ta, tb), tc) - lo) / v - 0.5)); let c1 = vec3i(floor((max(max(ta, tb), tc) - lo) / v - 0.5)) + 1;
    for (var k = 0u; k < 3u; k++) { atomicMin(&wlo[k], c0[k]); atomicMax(&whi[k], c1[k]); }
  }
  workgroupBarrier();
  winO = vec3i(atomicLoad(&wlo[0]), atomicLoad(&wlo[1]), atomicLoad(&wlo[2]));
  let d = vec3i(atomicLoad(&whi[0]), atomicLoad(&whi[1]), atomicLoad(&whi[2])) - winO + 1;
  winD = vec3i(0);
  if (winL != NONE && d.x * d.y <= ${WIN}) { winD = vec3i(d.x, d.y, min(d.z, ${WIN} / (d.x * d.y))); }
  let vol = u32(winD.x * winD.y * winD.z);
  for (var j = li; j < vol * W; j += ${SWG}u) { atomicStore(&wacc[j], 0u); }
  workgroupBarrier();
  splatTri();
  workgroupBarrier();
  // Add the window to the layer (voxels of dropped or unclaimed bricks are skipped, as the direct adds do).
  let G = voxG() * 8;
  for (var j = li; j < vol; j += ${SWG}u) {
    let cj = winO + vec3i(i32(j) % winD.x, (i32(j) / winD.x) % winD.y, i32(j) / (winD.x * winD.y));
    if (any(cj < vec3i(0)) || any(cj >= vec3i(G))) { continue; }
    var sum = 0u;
    for (var k = 0u; k < W; k++) { sum |= atomicLoad(&wacc[j * W + k]); }
    if (sum == 0u) { continue; }
    let ptr = atomicLoad(&dyn[${HDR}u + ptrIndex(winL, cj >> vec3u(3u))]);
    if (ptr >= DYN_MAX_BRICKS) { continue; }
    let l = cj & vec3i(7);
    let vi = u32(l.x + 8 * l.y + 64 * l.z);
    setMask(ptr, vi);
    let base = dynDataOff() + (ptr * 512u + vi) * W;
    for (var k = 0u; k < W; k++) { let q = atomicLoad(&wacc[j * W + k]); if (q != 0u) { atomicAdd(&dyn[base + k], q); } }
  }
}
// Level DL.z >= 1, fine to coarse: own splats (fixed point) + the 8 children (fixed point on level 0, floats above),
// in units of v^2. The children of a voxel are 2 x 2 x 2 voxels of one brick (even coordinates).
@compute @workgroup_size(64) fn resolve(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let L = DL.z;
  let i = lin(wid, nwg, li);
  if (i / 512u >= atomicLoad(&dyn[24u + L])) { return; }
  let slot = atomicLoad(&dyn[16u + L]) + i / 512u;
  let G = u32(VX.a.z);
  let pi = atomicLoad(&dyn[dynMetaOff() + slot]);
  let r = pi % (G * G * G);
  let bit = i % 512u;
  let c = vec3i(i32(r % G), i32((r / G) % G), i32(r / (G * G))) * 8 + vec3i(i32(bit & 7u), i32((bit >> 3u) & 7u), i32(bit >> 6u));
  let own = (atomicLoad(&dyn[dynMaskOff() + slot * 16u + (bit >> 5u)]) >> (bit & 31u)) & 1u;
  let gc = (VX.origin[L].xyz * 8 + c) * 2 - VX.origin[L - 1u].xyz * 8;
  var cptr = DYN_MAX_BRICKS;
  if (all(gc >= vec3i(0)) && all(gc < vec3i(i32(G) * 8))) { cptr = atomicLoad(&dyn[${HDR}u + ptrIndex(L - 1u, gc >> vec3u(3u))]); }
  var kids = 0u;
  if (cptr < DYN_MAX_BRICKS) {
    for (var q = 0u; q < 8u; q++) {
      let l = (gc & vec3i(7)) + vec3i(i32(q & 1u), i32((q >> 1u) & 1u), i32(q >> 2u));
      let v = u32(l.x + 8 * l.y + 64 * l.z);
      if (((atomicLoad(&dyn[dynMaskOff() + cptr * 16u + (v >> 5u)]) >> (v & 31u)) & 1u) != 0u) { kids |= 1u << q; }
    }
  }
  if (own == 0u && kids == 0u) { return; }
  var acc: array<f32, ${WORDS}>;
  let base = dynDataOff() + (slot * 512u + bit) * W;
  for (var k = 0u; k < W; k++) { acc[k] = f32(atomicLoad(&dyn[base + k])) / FIX; }
  for (var q = 0u; q < 8u; q++) {
    if (((kids >> q) & 1u) == 0u) { continue; }
    let l = (gc & vec3i(7)) + vec3i(i32(q & 1u), i32((q >> 1u) & 1u), i32(q >> 2u));
    let cb = dynDataOff() + (cptr * 512u + u32(l.x + 8 * l.y + 64 * l.z)) * W;
    for (var k = 0u; k < W; k++) {
      let u = atomicLoad(&dyn[cb + k]);
      var x = bitcast<f32>(u);
      if (L == 1u) { x = f32(u) / FIX; }
      acc[k] += 0.25 * x;
    }
  }
  for (var k = 0u; k < W; k++) { atomicStore(&dyn[base + k], bitcast<u32>(acc[k])); }
  if (own == 0u) { atomicOr(&dyn[dynMaskOff() + slot * 16u + (bit >> 5u)], 1u << (bit & 31u)); }
}
`;

/** Passes of the build, in order (resolve covers levels 1..). */
const DYN_PASSES = ['mark', 'parents', 'count', 'alloc', 'finalize', 'clear', 'splat', 'resolve'] as const;
/** Stages timed by encodeStaged: alloc = parents + count + alloc + finalize. */
export const DYN_STAGES = ['mark', 'alloc', 'clear', 'splat', 'resolve'] as const;
const STAGE_PASSES: Record<typeof DYN_STAGES[number], typeof DYN_PASSES[number][]> = {
  mark: ['mark'], alloc: ['parents', 'count', 'alloc', 'finalize'], clear: ['clear'], splat: ['splat'], resolve: ['resolve'] };

/** CPU count of the build's work at one pose, mirroring the shaders (splatLevel, mark, parents, the splat
 * subdivision): dynamic triangles, splat samples (sub-triangles), mark claims (brick visits at the splat level) and
 * distinct bricks wanted per level (with the ancestors, without a pool limit). tri is the triangle table
 * (triangleTable), pos the positions of all vertices, origin[L] the clipmap origin of level L in bricks (as in the
 * voxel uniform). */
export function dynWork(tri: Uint32Array, first: number, end: number, pos: Float32Array, vp: { v0: number; levels: number; G: number }, origin: number[][]) {
  const vs = (L: number) => vp.v0 * 2 ** L;
  const lo = (L: number, a: number) => origin[L][a] * vs(L) * 8;
  let samples = 0, claims = 0, outside = 0;
  const bricks = Array.from({ length: vp.levels }, () => new Set<number>());
  const key = (b: number[]) => (b[2] * vp.G + b[1]) * vp.G + b[0];
  const want = (L: number, b: number[]) => { if (b.every((x) => x >= 0 && x < vp.G)) bricks[L].add(key(b)); };
  const mn = [0, 0, 0], mx = [0, 0, 0];
  for (let t = first; t < end; t++) {
    const ia = tri[t * 4] * 3, ib = tri[t * 4 + 1] * 3, ic = tri[t * 4 + 2] * 3;
    for (let a = 0; a < 3; a++) { mn[a] = Math.min(pos[ia + a], pos[ib + a], pos[ic + a]); mx[a] = Math.max(pos[ia + a], pos[ib + a], pos[ic + a]); }
    let Ls = -1;
    for (let L = 0; L < vp.levels && Ls < 0; L++) {
      const v = vs(L), hi = (a: number) => lo(L, a) + vp.G * v * 8;
      if ([0, 1, 2].every((a) => mn[a] - 2 * v > lo(L, a) && mx[a] + 2 * v < hi(a))) Ls = L;
    }
    if (Ls < 0) { outside++; continue; }
    const v = vs(Ls), bs = v * 8;
    const g0 = [0, 1, 2].map((a) => Math.floor((mn[a] - v - lo(Ls, a)) / bs)), g1 = [0, 1, 2].map((a) => Math.floor((mx[a] + v - lo(Ls, a)) / bs));
    for (let z = g0[2]; z <= g1[2]; z++) for (let y = g0[1]; y <= g1[1]; y++) for (let x = g0[0]; x <= g1[0]; x++) { claims++; want(Ls, [x, y, z]); }
    const e = Math.max(...[[ia, ib], [ib, ic], [ic, ia]].map(([p, q]) => Math.hypot(pos[q] - pos[p], pos[q + 1] - pos[p + 1], pos[q + 2] - pos[p + 2])));
    const m = Math.min(Math.max(Math.ceil(e / vs(Ls)), 1), 16);
    samples += m * m;
  }
  // Parents, fine to coarse (a level's set is complete before its own parents are added).
  for (let L = 0; L + 1 < vp.levels; L++) for (const k of bricks[L]) {
    const b = [k % vp.G, Math.floor(k / vp.G) % vp.G, Math.floor(k / vp.G ** 2)];
    want(L + 1, b.map((x, a) => Math.floor(((origin[L][a] + x) * 4 - origin[L + 1][a] * 8) / 8)));
  }
  const perLevel = bricks.map((s) => s.size);
  return { triangles: end - first, samples, claims, outside, bricks: perLevel.reduce((a, b) => a + b, 0), bricksPerLevel: perLevel };
}

/** Sorts the dynamic tail of the triangle table (4 words per triangle) by a Morton code of the rest centroids on a
 * 4 cm grid, so that a workgroup's 64 consecutive triangles are neighbours (the splat window). The layer's values
 * do not depend on the order (fixed point sums). */
export function mortonSortDynamic(table: Uint32Array, first: number, pos: Float32Array) {
  const n = table.length / 4 - first;
  if (n <= 1) return;
  const cen = new Float32Array(n * 3), mn = [Infinity, Infinity, Infinity];
  for (let t = 0; t < n; t++) for (let a = 0; a < 3; a++) {
    const o = (first + t) * 4;
    const c = (pos[table[o] * 3 + a] + pos[table[o + 1] * 3 + a] + pos[table[o + 2] * 3 + a]) / 3;
    cen[t * 3 + a] = c; mn[a] = Math.min(mn[a], c);
  }
  const spread = (x: number) => { let r = 0; for (let b = 0; b < 10; b++) r += ((x >> b) & 1) * 2 ** (3 * b); return r; };
  const key = new Float64Array(n);
  for (let t = 0; t < n; t++) {
    const q = [0, 1, 2].map((a) => Math.min(1023, Math.max(0, Math.floor((cen[t * 3 + a] - mn[a]) / 0.04))));
    key[t] = spread(q[0]) + 2 * spread(q[1]) + 4 * spread(q[2]);
  }
  const order = Array.from({ length: n }, (_, t) => t).sort((x, y) => key[x] - key[y] || x - y);
  const tail = table.slice(first * 4);
  order.forEach((t, k) => table.set(tail.subarray(t * 4, t * 4 + 4), (first + k) * 4));
}

export interface DynLayer {
  buffer: GPUBuffer;
  /** Indirect dispatch size of one thread per voxel of the allocated bricks (clear; DYN_INJECT_WGSL). */
  args: GPUBuffer;
  bytes: number;
  /** Builds this frame's layer (after the shadow map, inside the caller's compute pass). */
  encode(pass: GPUComputePassEncoder): void;
  /** Same work, one compute pass per stage (DYN_STAGES), with timestamps at slots [base, base + 2 * DYN_STAGES.length)
   * when querySet is given. */
  encodeStaged(enc: GPUCommandEncoder, querySet: GPUQuerySet | null, base: number): void;
  /** Phase 31: whether the splat writes the albedo words (configs with objects receiving light); otherwise they stay 0. */
  setAlbedo(on: boolean): void;
  /** Allocated bricks, dropped bricks (pool too small) and triangles outside every clipmap (last frame). */
  readCounters(): Promise<{ bricks: number; brickOverflow: number; outside: number }>;
  destroy(): void;
}

export function createDynLayer(device: GPUDevice, gpu: SceneGpu, tri: GPUBuffer, voxUniform: GPUBuffer, frame: GPUBuffer, shadow: GPUTexture,
  vp: VoxParams, firstDynamicTri: number, triangleCount: number): DynLayer {
  const NB = vp.dynBricks;
  const lay = layout(vp.levels, vp.G, NB);
  if (vp.G ** 3 % 32) throw new Error('dynamic layer: G^3 must be a multiple of 32');
  const words = lay.data + NB * 512 * WORDS;
  const buffer = device.createBuffer({ label: 'dyn', size: words * 4, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC });
  const init = new Uint32Array(HDR + lay.ptrCount);
  init.fill(0xffffffff, HDR);
  init.fill(0xffffffff, 32, 35);
  device.queue.writeBuffer(buffer, 0, init);
  const args = device.createBuffer({ label: 'dyn.args', size: 4 * 3 * (1 + vp.levels), usage: GPUBufferUsage.STORAGE | GPUBufferUsage.INDIRECT });
  const C = GPUShaderStage.COMPUTE;
  const st = (binding: number, type: GPUBufferBindingType) => ({ binding, visibility: C, buffer: { type } });
  const bgl = device.createBindGroupLayout({ entries: [
    st(0, 'uniform'), st(1, 'storage'), st(2, 'uniform'), st(3, 'uniform'),
    st(5, 'read-only-storage'), st(6, 'read-only-storage'), st(7, 'read-only-storage'), st(8, 'read-only-storage'), st(9, 'read-only-storage'),
    { binding: 10, visibility: C, texture: { viewDimension: '2d-array' } }, { binding: 11, visibility: C, sampler: {} },
    { binding: 12, visibility: C, texture: { sampleType: 'depth', viewDimension: '2d-array' } }, { binding: 13, visibility: C, sampler: { type: 'comparison' } },
  ] });
  const bglArgs = device.createBindGroupLayout({ entries: [st(0, 'storage')] });
  const module = device.createShaderModule({ code: BUILD_WGSL, label: 'dyn.build' });
  const layout0 = device.createPipelineLayout({ bindGroupLayouts: [bgl] });
  const layout1 = device.createPipelineLayout({ bindGroupLayouts: [bgl, bglArgs] });
  const pipes = Object.fromEntries(DYN_PASSES.map((e) =>
    [e, device.createComputePipeline({ label: `dyn.${e}`, layout: e === 'finalize' ? layout1 : layout0, compute: { module, entryPoint: e, constants: dynConstants(NB) } })]));
  const splatAlb = pipes.splat;
  const splatNoAlb = device.createComputePipeline({ label: 'dyn.splat', layout: layout0, compute: { module, entryPoint: 'splat', constants: { ...dynConstants(NB), DYN_ALB: 0 } } });
  pipes.splat = splatNoAlb;
  const sampler = device.createSampler({ minFilter: 'linear', magFilter: 'linear', mipmapFilter: 'linear', addressModeU: 'repeat', addressModeV: 'repeat' });
  const cmp = device.createSampler({ compare: 'less-equal', minFilter: 'linear', magFilter: 'linear' });
  const uni = Array.from({ length: vp.levels }, (_, L) => {
    const b = device.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    device.queue.writeBuffer(b, 0, new Uint32Array([firstDynamicTri, triangleCount, L, 0]));
    return b;
  });
  const bgs = uni.map((u) => device.createBindGroup({ layout: bgl, entries: [
    { binding: 0, resource: { buffer: voxUniform } }, { binding: 1, resource: { buffer } }, { binding: 2, resource: { buffer: frame } },
    { binding: 3, resource: { buffer: u } }, { binding: 5, resource: { buffer: gpu.positions } }, { binding: 6, resource: { buffer: gpu.normals } },
    { binding: 7, resource: { buffer: gpu.uvs } }, { binding: 8, resource: { buffer: tri } }, { binding: 9, resource: { buffer: gpu.materials } },
    { binding: 10, resource: gpu.baseColor.createView({ dimension: '2d-array' }) }, { binding: 11, resource: sampler },
    { binding: 12, resource: shadow.createView({ dimension: '2d-array' }) }, { binding: 13, resource: cmp },
  ] }));
  const bgArgs = device.createBindGroup({ layout: bglArgs, entries: [{ binding: 0, resource: { buffer: args } }] });
  const nDyn = triangleCount - firstDynamicTri;
  const lin = (pass: GPUComputePassEncoder, n: number) => {
    const g = Math.ceil(n / 64), x = Math.min(g, 65535);
    if (g > 0) pass.dispatchWorkgroups(x, Math.ceil(g / x));
  };
  const use = (pass: GPUComputePassEncoder, name: string, L = 0) => { pass.setPipeline(pipes[name]); pass.setBindGroup(0, bgs[L]); };
  const stage = (pass: GPUComputePassEncoder, st: typeof DYN_PASSES[number]) => {
    if (st === 'mark') { use(pass, 'mark'); lin(pass, nDyn); }
    else if (st === 'parents') { use(pass, 'parents'); lin(pass, lay.nw - vp.G ** 3 / 32); }
    else if (st === 'count' || st === 'alloc') { use(pass, st); pass.dispatchWorkgroups(lay.nblk); }
    else if (st === 'finalize') { use(pass, 'finalize'); pass.setBindGroup(1, bgArgs); pass.dispatchWorkgroups(1); }
    else if (st === 'clear') { use(pass, 'clear'); pass.dispatchWorkgroupsIndirect(args, 0); }
    else if (st === 'splat') { use(pass, 'splat'); { const g = Math.ceil(nDyn / SWG), x = Math.min(g, 65535); pass.dispatchWorkgroups(x, Math.ceil(g / x)); } }
    else for (let L = 1; L < vp.levels; L++) { use(pass, 'resolve', L); pass.dispatchWorkgroupsIndirect(args, 12 * (1 + L)); }
  };
  return {
    buffer, args, bytes: buffer.size,
    setAlbedo(on) { pipes.splat = on ? splatAlb : splatNoAlb; },
    encode(pass) {
      if (nDyn <= 0) return;
      for (const st of DYN_PASSES) stage(pass, st);
    },
    encodeStaged(enc, querySet, base) {
      DYN_STAGES.forEach((st, i) => {
        const pass = enc.beginComputePass({ label: `dyn.${st}`,
          timestampWrites: querySet ? { querySet, beginningOfPassWriteIndex: base + 2 * i, endOfPassWriteIndex: base + 2 * i + 1 } : undefined });
        if (nDyn > 0) for (const p of STAGE_PASSES[st]) stage(pass, p);
        pass.end();
      });
    },
    async readCounters() {
      const read = device.createBuffer({ size: HDR * 4, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
      const enc = device.createCommandEncoder();
      enc.copyBufferToBuffer(buffer, 0, read, 0, HDR * 4);
      device.queue.submit([enc.finish()]);
      await read.mapAsync(GPUMapMode.READ);
      const c = new Uint32Array(read.getMappedRange().slice(0));
      read.unmap(); read.destroy();
      return { bricks: c[8], brickOverflow: c[1], outside: c[9] };
    },
    destroy() { buffer.destroy(); args.destroy(); for (const b of uni) b.destroy(); },
  };
}
