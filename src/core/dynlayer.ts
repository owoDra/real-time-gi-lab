// P2: the dynamic layer. Dynamic triangles (the tail of the triangle table) are not in the binary voxel bricks;
// every frame they are written into this separate layer of coverage and mean radiance, prefiltered from fine to
// coarse levels, and the interval tracers read it at the level that matches the width of the direction bin's cone.
//
// Build (every frame, after the shadow map):
//  reset    pointers of last frame's bricks back to empty
//  begin    counters and bounds
//  mark     per dynamic triangle: its splat level (the finest level whose clipmap holds it) and every brick its box,
//           grown by one voxel, touches at that level and all coarser levels
//  clear    the claimed bricks' accumulators
//  splat    per dynamic triangle: m^2 equal sub-triangles (m from the edge length, about half a voxel of the splat
//           level), each a sample at its centroid with its area, shaded there like a voxel hit (albedo, outward
//           normal, sun, shadow map, toon operator). Each sample adds, with trilinear weights over the 8 nearest
//           voxel centres (fixed point), its area projected on the 6 axis directions (front and back separately),
//           its area and its area x radiance. Trilinear splats of samples that move with the object make every
//           voxel value continuous in the object's pose: no voxel switches on or off.
//  resolve  level by level from fine to coarse: a voxel's value (float, in units of its own voxel face v^2) is its
//           own splats plus the sum of its 8 children.
// Read (traceDyn): the segment is marched with steps of half the cone width w = t * sqrt(4 pi / res^2); at each
// step the layer is read at the two levels around v = w (nearest voxel) and interpolated between them. A voxel's
// coverage for direction d is front / v^2 with front = sum_a |d_a| P(faces against d), so a closed object inside
// one voxel covers its projected area and a surface crossing a fine voxel covers it whole; it is scaled by the step
// length / v. Faces along d (seen from inside a closed object) do not cover: probes that end up inside a dynamic
// object (the relocation sees only the static voxels) look out through it instead of at its inner shell. Coverage is accumulated additively front to back and clamped at 1
// (a wall split between two voxels then still covers the ray fully); the covered part carries the voxels' mean
// radiance (area-weighted mean of the samples).
import { FRAME_WGSL } from './frame.ts';
import type { SceneGpu } from './scene_gpu.ts';
import { STYLE_WGSL } from './style.ts';
import { VOX_STRUCT_WGSL, type VoxParams } from './voxel.ts';

export const DYN_MAX_BRICKS = 256;
const HDR = 64;
const WORDS = 10; // per voxel: P+x P-x P+y P-y P+z P-z, area, area x radiance (rgb)
const FIX = 65536;

/** Read side, shared by the RC and DDGI tracers. Needs VX (VoxU), voxSize, voxG, voxLevelFor, dyn (array<u32>). */
export const DYN_READ_WGSL = /* wgsl */ `
const DYN_MAX_BRICKS = ${DYN_MAX_BRICKS}u;
fn dynPtrOff() -> u32 { return ${HDR}u; }
fn dynDataOff() -> u32 { let G = u32(VX.a.z); return ${HDR}u + u32(VX.a.y) * G * G * G + DYN_MAX_BRICKS; }
// Data base of the voxel of level L at p, or 0xffffffff.
fn dynVoxel(L: u32, p: vec3f) -> u32 {
  let v = voxSize(L);
  let G = voxG();
  let c = vec3i(floor((p - vec3f(VX.origin[L].xyz) * v * 8.0) / v));
  if (any(c < vec3i(0)) || any(c >= vec3i(G * 8))) { return 0xffffffffu; }
  let b = vec3u(c >> vec3u(3u));
  let ug = u32(G);
  let ptr = dyn[dynPtrOff() + L * ug * ug * ug + (b.z * ug + b.y) * ug + b.x];
  if (ptr >= 0xfffffffeu) { return 0xffffffffu; }
  let l = c & vec3i(7);
  return dynDataOff() + (ptr * 512u + u32(l.x + 8 * l.y + 64 * l.z)) * ${WORDS}u;
}
// (mean radiance, coverage per voxel length) of the voxel at base for direction d.
fn dynRead(base: u32, d: vec3f) -> vec4f {
  if (base == 0xffffffffu) { return vec4f(0.0); }
  var P: array<f32, 6>;
  for (var k = 0u; k < 6u; k++) { P[k] = bitcast<f32>(dyn[base + k]); }
  let ad = abs(d);
  let sx = select(0u, 1u, d.x > 0.0); let sy = select(0u, 1u, d.y > 0.0); let sz = select(0u, 1u, d.z > 0.0);
  let front = ad.x * P[sx] + ad.y * P[2u + sy] + ad.z * P[4u + sz];
  let a = bitcast<f32>(dyn[base + 6u]);
  if (a <= 0.0) { return vec4f(0.0); }
  let r = vec3f(bitcast<f32>(dyn[base + 7u]), bitcast<f32>(dyn[base + 8u]), bitcast<f32>(dyn[base + 9u])) / a;
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
      let sa = dynRead(dynVoxel(L0, p), d);
      var aa = sa.a * len / voxSize(L0);
      var ra = sa.rgb * aa;
      if (f > 0.0 && L0 + 1u < nl) {
        let sb = dynRead(dynVoxel(L0 + 1u, p), d);
        let ab = sb.a * len / voxSize(L0 + 1u);
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
@group(0) @binding(12) var shadowTex: texture_depth_2d;
@group(0) @binding(13) var shadowCmp: sampler_comparison;

const MAXB = ${DYN_MAX_BRICKS}u;
const W = ${WORDS}u;
const FIX = ${FIX}.0;
fn ptrCount() -> u32 { let G = u32(VX.a.z); return u32(VX.a.y) * G * G * G; }
fn metaOff() -> u32 { return ${HDR}u + ptrCount(); }
fn dataOff() -> u32 { return metaOff() + MAXB; }
fn lin(wid: vec3u, nwg: vec3u, li: u32) -> u32 { return (wid.y * nwg.x + wid.x) * 64u + li; }
fn P(i: u32) -> vec3f { return vec3f(positions[i * 3u], positions[i * 3u + 1u], positions[i * 3u + 2u]); }
fn N(i: u32) -> vec3f { return vec3f(normals[i * 3u], normals[i * 3u + 1u], normals[i * 3u + 2u]); }
fn UV(i: u32) -> vec2f { return vec2f(uvs[i * 2u], uvs[i * 2u + 1u]); }
fn regionLo(L: u32) -> vec3f { return vec3f(VX.origin[L].xyz) * voxSize(L) * 8.0; }
fn ptrIndex(L: u32, b: vec3i) -> u32 { let G = u32(VX.a.z); return L * G * G * G + (u32(b.z) * G + u32(b.y)) * G + u32(b.x); }
// Splat level of a triangle: the finest level whose clipmap holds its box grown by two voxels.
fn splatLevel(mn: vec3f, mx: vec3f) -> u32 {
  let n = u32(VX.a.y);
  for (var L = 0u; L < n; L++) {
    let v = voxSize(L); let lo = regionLo(L); let hi = lo + f32(voxG()) * v * 8.0;
    if (all(mn - 2.0 * v > lo) && all(mx + 2.0 * v < hi)) { return L; }
  }
  return 0xffffffffu;
}
fn sunVis(x: vec3f) -> f32 {
  let c = F.lightViewProj * vec4f(x, 1.0);
  let uv = c.xy * vec2f(0.5, -0.5) + 0.5;
  if (any(uv < vec2f(0.0)) || any(uv > vec2f(1.0))) { return 1.0; }
  return textureSampleCompareLevel(shadowTex, shadowCmp, uv, c.z - 0.0002);
}

@compute @workgroup_size(64) fn reset(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  if (i >= min(atomicLoad(&dyn[8]), MAXB)) { return; }
  atomicStore(&dyn[${HDR}u + atomicLoad(&dyn[metaOff() + i])], 0xffffffffu);
}
@compute @workgroup_size(1) fn begin() {
  atomicStore(&dyn[0], 0u); atomicStore(&dyn[1], 0u); atomicStore(&dyn[9], 0u);
  for (var k = 2u; k < 5u; k++) { atomicStore(&dyn[k], 0xffffffffu); atomicStore(&dyn[k + 3u], 0u); }
}
@compute @workgroup_size(1) fn end() { atomicStore(&dyn[8], min(atomicLoad(&dyn[0]), MAXB)); }

fn claim(L: u32, b: vec3i) {
  let pi = ptrIndex(L, b);
  if (atomicLoad(&dyn[${HDR}u + pi]) != 0xffffffffu) { return; }
  loop {
    let q = atomicCompareExchangeWeak(&dyn[${HDR}u + pi], 0xffffffffu, 0xfffffffeu);
    if (q.exchanged) { break; }
    if (q.old_value != 0xffffffffu) { return; }
  }
  let idx = atomicAdd(&dyn[0], 1u);
  if (idx >= MAXB) { atomicAdd(&dyn[1], 1u); atomicStore(&dyn[${HDR}u + pi], 0xffffffffu); return; }
  atomicStore(&dyn[metaOff() + idx], pi);
  atomicStore(&dyn[${HDR}u + pi], idx);
}
@compute @workgroup_size(64) fn mark(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let t = lin(wid, nwg, li) + DL.x;
  if (t >= DL.y) { return; }
  let i = tri[t];
  let a = P(i.x); let b = P(i.y); let c = P(i.z);
  let mn = min(min(a, b), c); let mx = max(max(a, b), c);
  let Ls = splatLevel(mn, mx);
  if (Ls == 0xffffffffu) { atomicAdd(&dyn[9], 1u); return; }
  let n = u32(VX.a.y);
  for (var L = Ls; L < n; L++) {
    let bs = voxSize(L) * 8.0; let lo = regionLo(L);
    let g0 = vec3i(floor((mn - voxSize(L) - lo) / bs)); let g1 = vec3i(floor((mx + voxSize(L) - lo) / bs));
    for (var z = g0.z; z <= g1.z; z++) { for (var y = g0.y; y <= g1.y; y++) { for (var x = g0.x; x <= g1.x; x++) {
      claim(L, vec3i(x, y, z));
    } } }
  }
  // Bounds of everything a read can see: the box grown by the coarsest voxel (cm, offset by 2^30).
  let gv = voxSize(n - 1u);
  let lo = vec3u(vec3i(floor((mn - gv) * 100.0)) + 1073741824); let hi = vec3u(vec3i(ceil((mx + gv) * 100.0)) + 1073741824);
  atomicMin(&dyn[2], lo.x); atomicMin(&dyn[3], lo.y); atomicMin(&dyn[4], lo.z);
  atomicMax(&dyn[5], hi.x); atomicMax(&dyn[6], hi.y); atomicMax(&dyn[7], hi.z);
}
@compute @workgroup_size(64) fn clear(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  if (i / 512u >= min(atomicLoad(&dyn[0]), MAXB)) { return; }
  for (var k = 0u; k < W; k++) { atomicStore(&dyn[dataOff() + i * W + k], 0u); }
}

fn addFix(base: u32, k: u32, x: f32) { let q = u32(round(x * FIX)); if (q > 0u) { atomicAdd(&dyn[base + k], q); } }
fn splatSample(L: u32, p: vec3f, n: vec3f, area: f32, rad: vec3f) {
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
    let ptr = atomicLoad(&dyn[${HDR}u + ptrIndex(L, c >> vec3u(3u))]);
    if (ptr >= MAXB) { continue; }
    let l = c & vec3i(7);
    let base = dataOff() + (ptr * 512u + u32(l.x + 8 * l.y + 64 * l.z)) * W;
    addFix(base, 0u, w * pn.x); addFix(base, 1u, w * nn.x);
    addFix(base, 2u, w * pn.y); addFix(base, 3u, w * nn.y);
    addFix(base, 4u, w * pn.z); addFix(base, 5u, w * nn.z);
    addFix(base, 6u, w);
    addFix(base, 7u, w * rad.x); addFix(base, 8u, w * rad.y); addFix(base, 9u, w * rad.z);
  }
}
fn shadeSample(m: Material, p: vec3f, n: vec3f, uv: vec2f, L: u32) -> vec4f {
  let tex = textureSampleLevel(baseColorTex, samp, uv, m.layers.x, f32(3u + L)) * m.baseColorFactor;
  if ((m.layers.w & 1u) != 0u && tex.a < m.params.z) { return vec4f(0.0, 0.0, 0.0, -1.0); }
  let ndl = max(dot(n, F.sunDir.xyz), 0.0);
  if (ndl <= 0.0) { return vec4f(0.0); }
  let vis = sunVis(p + n * 0.03);
  if ((m.layers.w & 4u) != 0u && F.style.x > 0.5) { return vec4f(toonSun(tex.rgb, ndl, vis, F.sunE.rgb), 0.0); }
  return vec4f(tex.rgb / PI * F.sunE.rgb * ndl * vis, 0.0);
}
@compute @workgroup_size(64) fn splat(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let t = lin(wid, nwg, li) + DL.x;
  if (t >= DL.y) { return; }
  let i = tri[t];
  let a = P(i.x); let b = P(i.y); let c = P(i.z);
  let L = splatLevel(min(min(a, b), c), max(max(a, b), c));
  if (L == 0xffffffffu) { return; }
  let area = 0.5 * length(cross(b - a, c - a));
  if (area <= 0.0) { return; }
  let e = max(max(length(b - a), length(c - b)), length(a - c));
  let m = u32(clamp(ceil(e / (0.5 * voxSize(L))), 1.0, 16.0));
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
        splatSample(L, p, n, sa, s.rgb);
      }
    }
  }
}
// Level DL.z, fine to coarse: own splats (fixed point) + the 8 children (already floats), in units of v^2.
@compute @workgroup_size(64) fn resolve(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  let bi = i / 512u;
  if (bi >= min(atomicLoad(&dyn[0]), MAXB)) { return; }
  let L = DL.z;
  let G = u32(VX.a.z);
  let pi = atomicLoad(&dyn[metaOff() + bi]);
  if (pi / (G * G * G) != L) { return; }
  let r = pi % (G * G * G);
  let bit = i % 512u;
  let c = vec3i(i32(r % G), i32((r / G) % G), i32(r / (G * G))) * 8 + vec3i(i32(bit & 7u), i32((bit >> 3u) & 7u), i32(bit >> 6u));
  var acc: array<f32, ${WORDS}>;
  let base = dataOff() + i * W;
  for (var k = 0u; k < W; k++) { acc[k] = f32(atomicLoad(&dyn[base + k])) / FIX; }
  if (L > 0u) {
    let gc = (VX.origin[L].xyz * 8 + c) * 2 - VX.origin[L - 1u].xyz * 8;
    for (var q = 0u; q < 8u; q++) {
      let cc = gc + vec3i(i32(q & 1u), i32((q >> 1u) & 1u), i32(q >> 2u));
      if (any(cc < vec3i(0)) || any(cc >= vec3i(i32(G) * 8))) { continue; }
      let ptr = atomicLoad(&dyn[${HDR}u + ptrIndex(L - 1u, cc >> vec3u(3u))]);
      if (ptr >= MAXB) { continue; }
      let l = cc & vec3i(7);
      let cb = dataOff() + (ptr * 512u + u32(l.x + 8 * l.y + 64 * l.z)) * W;
      for (var k = 0u; k < W; k++) { acc[k] += 0.25 * bitcast<f32>(atomicLoad(&dyn[cb + k])); }
    }
  }
  for (var k = 0u; k < W; k++) { atomicStore(&dyn[base + k], bitcast<u32>(acc[k])); }
}
`;

export interface DynLayer {
  buffer: GPUBuffer;
  bytes: number;
  /** Builds this frame's layer (after the shadow map, inside the caller's compute pass). */
  encode(pass: GPUComputePassEncoder): void;
  /** Claimed bricks, brick overflow and triangles outside every clipmap (last frame). */
  readCounters(): Promise<{ bricks: number; brickOverflow: number; outside: number }>;
  destroy(): void;
}

export function createDynLayer(device: GPUDevice, gpu: SceneGpu, tri: GPUBuffer, voxUniform: GPUBuffer, frame: GPUBuffer, shadow: GPUTexture,
  vp: VoxParams, firstDynamicTri: number, triangleCount: number): DynLayer {
  const ptrCount = vp.levels * vp.G ** 3;
  const words = HDR + ptrCount + DYN_MAX_BRICKS + DYN_MAX_BRICKS * 512 * WORDS;
  const buffer = device.createBuffer({ label: 'dyn', size: words * 4, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST | GPUBufferUsage.COPY_SRC });
  const init = new Uint32Array(HDR + ptrCount);
  init.fill(0xffffffff, HDR);
  device.queue.writeBuffer(buffer, 0, init);
  const C = GPUShaderStage.COMPUTE;
  const st = (binding: number, type: GPUBufferBindingType) => ({ binding, visibility: C, buffer: { type } });
  const bgl = device.createBindGroupLayout({ entries: [
    st(0, 'uniform'), st(1, 'storage'), st(2, 'uniform'), st(3, 'uniform'),
    st(5, 'read-only-storage'), st(6, 'read-only-storage'), st(7, 'read-only-storage'), st(8, 'read-only-storage'), st(9, 'read-only-storage'),
    { binding: 10, visibility: C, texture: { viewDimension: '2d-array' } }, { binding: 11, visibility: C, sampler: {} },
    { binding: 12, visibility: C, texture: { sampleType: 'depth' } }, { binding: 13, visibility: C, sampler: { type: 'comparison' } },
  ] });
  const module = device.createShaderModule({ code: BUILD_WGSL, label: 'dyn.build' });
  const layout = device.createPipelineLayout({ bindGroupLayouts: [bgl] });
  const pipes = Object.fromEntries(['reset', 'begin', 'mark', 'clear', 'splat', 'resolve', 'end'].map((e) =>
    [e, device.createComputePipeline({ label: `dyn.${e}`, layout, compute: { module, entryPoint: e } })]));
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
    { binding: 12, resource: shadow.createView() }, { binding: 13, resource: cmp },
  ] }));
  const nDyn = triangleCount - firstDynamicTri;
  const lin = (pass: GPUComputePassEncoder, n: number) => {
    const g = Math.ceil(n / 64), x = Math.min(g, 65535);
    if (g > 0) pass.dispatchWorkgroups(x, Math.ceil(g / x));
  };
  const use = (pass: GPUComputePassEncoder, name: string, L = 0) => { pass.setPipeline(pipes[name]); pass.setBindGroup(0, bgs[L]); };
  return {
    buffer, bytes: buffer.size,
    encode(pass) {
      if (nDyn <= 0) return;
      use(pass, 'reset'); lin(pass, DYN_MAX_BRICKS);
      use(pass, 'begin'); pass.dispatchWorkgroups(1);
      use(pass, 'mark'); lin(pass, nDyn);
      use(pass, 'clear'); lin(pass, DYN_MAX_BRICKS * 512);
      use(pass, 'splat'); lin(pass, nDyn);
      for (let L = 0; L < vp.levels; L++) { use(pass, 'resolve', L); lin(pass, DYN_MAX_BRICKS * 512); }
      use(pass, 'end'); pass.dispatchWorkgroups(1);
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
    destroy() { buffer.destroy(); for (const b of uni) b.destroy(); },
  };
}
