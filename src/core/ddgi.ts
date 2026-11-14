// M1: DDGI-style comparator (C1 decision). A uniform world-space grid of probes, each tracing R rays per update
// against the same voxel StrataBrick as the radiance cascades, with temporal accumulation (hysteresis) of an
// octahedral irradiance map and an octahedral map of distance moments for Chebyshev visibility. The update rule,
// the encoding and the sampling follow RTXGI's DDGI (Majercik et al. 2019; RTXGI 1.x defaults where they apply):
//  - rays: spherical Fibonacci directions with one random rotation per frame shared by all probes;
//  - irradiance 6x6 + 1 texel border, stored gamma-encoded (gamma 5); distance moments 14x14 + border, distance
//    clamped to 1.5 x the probe spacing, cos^50 weighting;
//  - hysteresis 0.97; when an irradiance texel darkens by more than 0.2 (encoded) the hysteresis drops by 0.75,
//    and a brightening of more than 0.1 (encoded, vector length) is limited to a quarter (RTXGI's thresholds);
//  - sampling: trilinear x wrap-shading backface term x Chebyshev visibility (cubed, crushed below 0.2), surface
//    bias (0.2 n + 0.8 v) x 0.75 x spacing x 0.3.
// What differs from RTXGI, to keep the comparison on the field and not on the tracer:
//  - rays trace the voxels exactly as the cascades' intervals do: the ray is split into segments whose voxel level
//    grows one per segment while the segment length grows 4x (the cascades' cone-footprint level map), so a DDGI ray
//    is the concatenation of the intervals c0..c4 of a probe with s0 = 4 v0;
//  - transport: the same sun light at the hit (shadeHit, including the S3 emission-side operator), sky on escape;
//  - probe relocation and classification come from the voxel occupancy (view independent, recomputed every frame,
//    so they follow moving geometry): a probe whose voxel (~ spacing / 4) is occupied moves to the first free
//    candidate among 26 directions at 0.15 / 0.3 / 0.45 spacing; a probe is active when a voxel brick of size
//    ~ spacing / 2..spacing overlaps the box of +-1 spacing around it. Inactive probes are not traced; a probe
//    that becomes active starts without history.
//  - the volume is fixed in the world and covers the scene bounds (no scrolling).
// Trace and blend are two passes (phase 23); the rays of one update go through a texture.
// Phase 23 (multi-bounce, on by default): the hit radiance adds albedo / pi times the probes' own irradiance, sampled as the
// gather does from the state the previous update left (RTXGI's usual multi-bounce).
import { FRAME_WGSL } from './frame.ts';
import type { GBuffer } from './gbuffer.ts';
import { SHADE_WGSL, type WorldResources } from './rc.ts';
import { STYLE_WGSL } from './style.ts';
import type { Vec3 } from './math.ts';
import { DYN_READ_WGSL, dynConstants } from './dynlayer.ts';
import { VOX_TRACE_WGSL } from './voxel.ts';

export interface DdgiParams {
  spacing: number;      // probe spacing (m)
  rays: number;         // rays per probe update (multiple of 64, <= 256)
  hysteresis: number;   // 0.97 in RTXGI
  adaptive: boolean;    // RTXGI's irradiance / brightness thresholds
  updateDiv: number;    // each active probe is updated every updateDiv frames (round robin)
  segBase: number;      // length of the first ray segment (m); the voxel of segment k is v0 * 2^k
  relocate: 0 | 1 | 2;  // 0 off, 1 first free of 26 fixed directions, 2 away from the occupancy (fallback: upward first)
  classify: boolean;
  gamma: number;        // irradiance encoding for the temporal blend (RTXGI 5; 1: linear)
  viewBias: number;     // surface bias = (n (1 - viewBias) + v viewBias) x 0.75 x spacing x 0.3 (RTXGI 0.8)
  bounce: boolean;      // phase 23: multi-bounce from the probes' own irradiance
}
export const DEFAULT_DDGI: DdgiParams = { spacing: 1, rays: 128, hysteresis: 0.97, adaptive: true, updateDiv: 1, segBase: 0.4, relocate: 1, classify: true,
  gamma: 5, viewBias: 0.8, bounce: true };

const IRR = 8;   // 6 + border
const DEP = 16;  // 14 + border

const DDGI_WGSL = /* wgsl */ `
${FRAME_WGSL}
${STYLE_WGSL}
const PI = 3.14159265;
struct DU {
  origin: vec4f,   // xyz, spacing
  dims: vec4u,     // nx, ny, nz, rays
  rot0: vec4f, rot1: vec4f, rot2: vec4f,
  p: vec4f,        // hysteresis, segBase, max depth (1.5 spacing), adaptive (1/0)
  u: vec4u,        // frame, updateDiv, relocate, classify
  q: vec4f,        // gamma, viewBias, multi-bounce (1/0), 0
}
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var<uniform> D: DU;
@group(0) @binding(2) var depthTex: texture_depth_2d;
@group(0) @binding(3) var normalTex: texture_2d<f32>;
@group(0) @binding(4) var irrOut: texture_storage_2d<rgba16float, write>;
@group(0) @binding(5) var albedoTex: texture_2d<f32>;
@group(1) @binding(0) var<storage, read_write> state: array<vec4f>;   // offset xyz, flags (1 active, 2 has data)
@group(1) @binding(1) var<storage, read_write> irr: array<vec2u>;     // 8x8 per probe, rgba16f (encoded)
@group(1) @binding(2) var<storage, read_write> dep: array<u32>;       // 16x16 per probe, rg16f (mean, mean^2)
@group(1) @binding(3) var<storage, read_write> counts: array<atomic<u32>>; // 0 listed, 1 active, 2 relocated, 3 stuck
@group(1) @binding(4) var<storage, read_write> list: array<u32>;
@group(2) @binding(0) var<uniform> VX: VoxU;
@group(2) @binding(1) var<storage, read> vox: array<u32>;
@group(2) @binding(2) var shadowTex: texture_depth_2d;
@group(2) @binding(3) var shadowCmp: sampler_comparison;
@group(2) @binding(4) var<storage, read> dyn: array<u32>; // P2 dynamic layer (dynlayer.ts)
@group(2) @binding(5) var<storage, read> hr: array<u32>; // P1 hit radiance (hitrad.ts)
// Phase 23 (multi-bounce): hits add albedo / pi times the irradiance of the probes as the previous update left them
// (the trace pass only reads irr and dep; the blend pass writes them), sampled as the gather does (bounceE).
fn bounceE(p: vec3f, n: vec3f, v: vec3f) -> vec3f {
  if (D.q.z < 0.5) { return vec3f(0.0); }
  let s = D.origin.w;
  let bp = p + (n * (1.0 - D.q.y) + v * D.q.y) * (0.75 * s * 0.3);
  let g = (bp - D.origin.xyz) / s;
  let b = vec3i(floor(g)); let a = g - vec3f(b);
  var e = vec3f(0.0); var ws = 0.0;
  for (var k = 0u; k < 8u; k++) {
    let o = vec3i(i32(k & 1u), i32((k >> 1u) & 1u), i32((k >> 2u) & 1u));
    let c = b + o;
    if (any(c < vec3i(0)) || any(c >= vec3i(D.dims.xyz))) { continue; }
    let pi = u32(c.x) + D.dims.x * (u32(c.y) + D.dims.y * u32(c.z));
    let st = state[pi];
    if ((u32(st.w) & 3u) != 3u) { continue; }
    let pp = D.origin.xyz + vec3f(c) * s + st.xyz;
    let tri = select(1.0 - a, a, o == vec3i(1));
    let toP = normalize(pp - p);
    let wrap = (dot(toP, n) + 1.0) * 0.5;
    var w = wrap * wrap + 0.2;
    let bv = bp - pp;
    let dist = length(bv);
    let m = sampleDep(pi, bv / max(dist, 1e-6));
    let variance = abs(m.x * m.x - m.y);
    var cheb = 1.0;
    if (dist > m.x) { let t = dist - m.x; cheb = variance / (variance + t * t); cheb = max(cheb * cheb * cheb, 0.0); }
    w *= max(0.05, cheb);
    w = max(w, 1e-6);
    if (w < 0.2) { w *= w * w / (0.2 * 0.2); }
    w *= tri.x * tri.y * tri.z;
    e += w * pow(max(sampleIrr(pi, n), vec3f(0.0)), vec3f(0.5 * D.q.x)); ws += w;
  }
  let eh = e / max(ws, 1e-9);
  return select(vec3f(0.0), PI * eh * eh, ws > 0.0);
}
fn voxBounce(p: vec3f, n0: vec3f, d: vec3f, ai: u32) -> vec3f {
  var n = select(-d, n0, dot(n0, n0) > 0.01);
  if (dot(n, d) > 0.0) { n = -n; }
  return bounceE(p, n, -d);
}
${SHADE_WGSL}
${VOX_TRACE_WGSL}
${DYN_READ_WGSL}

fn probeCount() -> u32 { return D.dims.x * D.dims.y * D.dims.z; }
fn probeGrid(i: u32) -> vec3u { return vec3u(i % D.dims.x, (i / D.dims.x) % D.dims.y, i / (D.dims.x * D.dims.y)); }
fn probeBase(i: u32) -> vec3f { return D.origin.xyz + vec3f(probeGrid(i)) * D.origin.w; }

fn octDecode(uv: vec2f) -> vec3f {
  let f = uv * 2.0 - 1.0;
  var n = vec3f(f.x, f.y, 1.0 - abs(f.x) - abs(f.y));
  let t = max(-n.z, 0.0);
  n.x += select(t, -t, n.x >= 0.0);
  n.y += select(t, -t, n.y >= 0.0);
  return normalize(n);
}
fn octEncode(n: vec3f) -> vec2f {
  var p = n.xy / (abs(n.x) + abs(n.y) + abs(n.z));
  if (n.z < 0.0) { p = (1.0 - abs(p.yx)) * select(vec2f(-1.0), vec2f(1.0), p >= vec2f(0.0)); }
  return p * 0.5 + 0.5;
}
// Interior texel whose value a texel of an (n + 2)^2 bordered octahedral tile holds (borders copy the texel
// across the fold).
fn borderSrc(t: vec2u, n: u32) -> vec2u {
  let e = n + 1u;
  var s = t;
  let bx = t.x == 0u || t.x == e; let by = t.y == 0u || t.y == e;
  if (bx && by) { s = vec2u(select(1u, n, t.x == 0u), select(1u, n, t.y == 0u)); }
  else if (by) { s = vec2u(e - t.x, select(n, 1u, t.y == 0u)); }
  else if (bx) { s = vec2u(select(n, 1u, t.x == 0u), e - t.y); }
  return s;
}
fn texelDir(s: vec2u, n: u32) -> vec3f { return octDecode((vec2f(s - vec2u(1u)) + 0.5) / f32(n)); }

// ---- classification and relocation (view independent, from the voxel occupancy) ----
fn occ(L0: u32, p: vec3f) -> bool {
  let L = voxLevelFor(L0, p);
  let v = voxSize(L);
  let c = vec3i(floor((p - vec3f(VX.origin[L].xyz) * v * 8.0) / v));
  if (any(c < vec3i(0)) || any(c >= vec3i(voxG() * 8))) { return false; }
  let ptr = vox[voxPtrIndex(L, c >> vec3u(3u))];
  if (ptr >= VOX_MARK) { return false; }
  let l = c & vec3i(7);
  let bit = u32(l.x + 8 * l.y + 64 * l.z);
  return (vox[VX.b.y + ptr * BRICK_W + (bit >> 5u)] & (1u << (bit & 31u))) != 0u;
}
const BRICK_W = 18u;
fn levelFor(size: f32) -> u32 { return u32(clamp(floor(log2(max(size, 1e-4) / VX.a.x)), 0.0, VX.a.y - 1.0)); }
// Any occupied voxel (level with voxels of about spacing / 2) in the box of +-1 spacing around the probe.
fn anyBrick(p: vec3f, r: f32) -> bool {
  let L = levelFor(0.5 * D.origin.w);
  let v = voxSize(L);
  let n = i32(ceil(r / v));
  for (var z = -n; z <= n; z++) { for (var y = -n; y <= n; y++) { for (var x = -n; x <= n; x++) {
    if (occ(L, p + vec3f(f32(x), f32(y), f32(z)) * (r / f32(n)))) { return true; }
  } } }
  return false;
}

@compute @workgroup_size(1) fn clearCounts() { for (var i = 0u; i < 8u; i++) { atomicStore(&counts[i], 0u); } }

@compute @workgroup_size(64) fn classify(@builtin(global_invocation_id) gid: vec3u, @builtin(num_workgroups) nwg: vec3u) {
  let i = gid.x + gid.y * nwg.x * 64u;
  if (i >= probeCount()) { return; }
  let s = D.origin.w;
  let p = probeBase(i);
  let prev = state[i];
  var flags = u32(prev.w);
  var isActive = true;
  if (D.u.w == 1u) { isActive = anyBrick(p, s); }
  var off = vec3f(0.0);
  if (isActive && D.u.z >= 1u) {
    let L = levelFor(0.25 * s);
    if (occ(L, p)) {
      var found = false;
      // Mode 2: march away from the occupied voxels around the probe (their centroid in the 4^3 cube of +-1.5 voxels
      // of about spacing / 2, as the cascades' vrel does). Mode 1, and mode 2 when that direction is ambiguous:
      // the first free candidate among 26 directions (upward ones first in mode 2) at 0.15 / 0.3 / 0.45 spacing.
      if (D.u.z == 2u) {
        let Lg = levelFor(0.5 * s);
        let vg = voxSize(Lg);
        var grad = vec3f(0.0); var cnt = 0.0;
        for (var k = 0u; k < 64u; k++) {
          let o = (vec3f(f32(k & 3u), f32((k >> 2u) & 3u), f32(k >> 4u)) - 1.5) * vg;
          if (occ(Lg, p + o)) { grad -= o; cnt += 1.0; }
        }
        if (cnt > 0.0 && length(grad) >= 0.1 * cnt * vg) {
          let d = normalize(grad);
          for (var k = 1u; k <= 3u; k++) {
            let q = p + d * (0.15 * f32(k) * s);
            if (!occ(L, q)) { off = q - p; found = true; break; }
          }
        }
      }
      for (var k = 1u; k <= 3u && !found; k++) {
        for (var j = 0u; j < 27u; j++) {
          if (j == 13u) { continue; }
          var jj = j;
          if (D.u.z == 2u) { jj = (j + 18u) % 27u; } // dy = +1 first
          if (jj == 13u) { continue; }
          var d = normalize(vec3f(f32(jj % 3u), f32((jj / 3u) % 3u), f32(jj / 9u)) - 1.0);
          if (D.u.z == 2u) { d = normalize(vec3f(f32(jj % 3u), f32(jj / 9u), f32((jj / 3u) % 3u)) - 1.0); }
          let q = p + d * (0.15 * f32(k) * s);
          if (!occ(L, q)) { off = q - p; found = true; break; }
        }
      }
      atomicAdd(&counts[select(3u, 2u, found)], 1u);
    }
  }
  // A probe whose position moved by more than a voxel keeps its history (as RTXGI); one that was inactive does not.
  if (!isActive) { flags = 0u; } else { flags = flags | 1u; atomicAdd(&counts[1], 1u); }
  state[i] = vec4f(off, f32(flags));
  if (isActive && ((i + D.u.x) % D.u.y) == 0u) {
    let k = atomicAdd(&counts[0], 1u);
    list[k] = i;
  }
}

@compute @workgroup_size(1) fn writeArgs() {
  let n = atomicLoad(&counts[0]);
  let x = min(n, 65535u);
  atomicStore(&counts[4], x);
  atomicStore(&counts[5], select(0u, (n + x - 1u) / max(x, 1u), x > 0u));
  atomicStore(&counts[6], 1u);
}

// ---- trace + blend: one workgroup per listed probe ----
var<workgroup> rayRad: array<vec3f, 256>;
var<workgroup> rayDir: array<vec3f, 256>;
var<workgroup> rayDist: array<f32, 256>;

fn sfDir(i: u32, n: u32) -> vec3f {
  let z = 1.0 - (2.0 * f32(i) + 1.0) / f32(n);
  let r = sqrt(max(0.0, 1.0 - z * z));
  let phi = 2.0 * PI * fract(f32(i) * 0.618033988749);
  let d = vec3f(r * cos(phi), r * sin(phi), z);
  return normalize(D.rot0.xyz * d.x + D.rot1.xyz * d.y + D.rot2.xyz * d.z);
}
// One ray as consecutive segments [b_k, b_k+1] * segBase, b_k = (4^k - 1) / 3, with voxels of segBase / 4 * 2^k
// (level k when v0 = segBase / 4; with v0 = 0.2 m, phase 21, the first two segments read level 0, so that a coarser
// level 0 does not coarsen every segment of the comparator: that alone took its reference error from 0.36 to 0.47). Returns
// (radiance, distance); distance < 0 on a miss. P2: the dynamic layer is read in front of each segment's static
// hit with the cone of one ray (4 pi / rays); the distance is the static hit's (dynamic objects do not enter the
// depth moments). P1: static hits read the prefiltered hit radiance with the same cone.
fn traceRay(o: vec3f, d: vec3f) -> vec4f {
  let nl = u32(VX.a.y);
  let kc = sqrt(4.0 * PI / f32(D.dims.w));
  coneK = kc; coneO = o;
  var b0 = 0.0;
  var acc = vec3f(0.0); var tr = 1.0;
  let shift = u32(max(round(log2(VX.a.x * 4.0 / D.p.y)), 0.0));
  for (var k = 0u; k < nl; k++) {
    let b1 = b0 * 4.0 + 1.0;
    let t0 = b0 * D.p.y; let t1 = b1 * D.p.y;
    let L = voxLevelFor(k - min(k, shift), o + d * t1);
    let r = traceVox(o, d, t0, t1, 0.0, L);
    if (dyn[0] != 0u) {
      let dl = traceDyn(o, d, t0, select(t1, min(t1, dot(voxHitEntry - o, d)), r.a < 0.5), kc);
      acc += tr * dl.rgb; tr *= 1.0 - dl.a;
    }
    if (r.a < 0.5) { return vec4f(acc + tr * r.rgb, distance(voxHitEntry, o)); }
    b0 = b1;
  }
  return vec4f(acc + tr * F.sky.rgb, -1.0);
}

fn enc(v: vec3f) -> vec3f { return pow(max(v, vec3f(0.0)), vec3f(1.0 / D.q.x)); }
fn maxc(v: vec3f) -> f32 { return max(v.x, max(v.y, v.z)); }

// Trace and blend are separate passes (phase 23: the trace reads the probes for the multi-bounce while the blend writes
// them). The rays of listed probe slot k go to texels k * rays + r of rayOut (2048 wide).
@group(3) @binding(0) var rayOut: texture_storage_2d<rgba32float, write>;
@group(3) @binding(1) var rayIn: texture_2d<f32>;
fn rayTexel(i: u32) -> vec2i { return vec2i(i32(i % 2048u), i32(i / 2048u)); }
var<workgroup> wgProbe: u32;
@compute @workgroup_size(64) fn traceRays(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let slot = wid.x + wid.y * nwg.x;
  if (li == 0u) { wgProbe = select(0xffffffffu, list[slot], slot < atomicLoad(&counts[0])); }
  let pi = workgroupUniformLoad(&wgProbe);
  if (pi == 0xffffffffu) { return; }
  let o = probeBase(pi) + state[pi].xyz;
  let R = D.dims.w;
  for (var r = li; r < R; r += 64u) { textureStore(rayOut, rayTexel(slot * R + r), traceRay(o, sfDir(r, R))); }
}
@compute @workgroup_size(64) fn update(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let slot = wid.x + wid.y * nwg.x;
  if (li == 0u) { wgProbe = select(0xffffffffu, list[slot], slot < atomicLoad(&counts[0])); }
  let pi = workgroupUniformLoad(&wgProbe);
  if (pi == 0xffffffffu) { return; }
  let st = state[pi];
  let R = D.dims.w;
  for (var r = li; r < R; r += 64u) {
    let h = textureLoad(rayIn, rayTexel(slot * R + r), 0);
    rayDir[r] = sfDir(r, R); rayRad[r] = h.rgb; rayDist[r] = select(1e9, h.a, h.a >= 0.0);
  }
  workgroupBarrier();
  let hasData = (u32(st.w) & 2u) != 0u;
  let h0 = select(0.0, D.p.x, hasData);
  // Irradiance: one texel per thread (8x8).
  {
    let t = vec2u(li % ${IRR}u, li / ${IRR}u);
    let n = texelDir(borderSrc(t, ${IRR - 2}u), ${IRR - 2}u);
    var acc = vec3f(0.0); var ws = 0.0;
    for (var r = 0u; r < R; r++) {
      let w = max(dot(n, rayDir[r]), 0.0);
      acc += w * rayRad[r]; ws += w;
    }
    let cur = enc(acc / max(ws, 1e-6));
    let ai = pi * ${IRR * IRR}u + li;
    let pv = irr[ai];
    let prev = vec3f(unpack2x16float(pv.x), unpack2x16float(pv.y).x);
    var h = h0;
    var res = cur;
    if (hasData && D.p.w > 0.5) {
      if (maxc(prev - cur) > 0.2) { h = max(0.0, h - 0.75); }
      let delta = cur - prev;
      if (length(delta) > 0.1) { res = prev + delta * 0.25; }
    }
    let v = mix(res, prev, h);
    irr[ai] = vec2u(pack2x16float(v.xy), pack2x16float(vec2f(v.z, 1.0)));
  }
  // Distance moments: four texels per thread (16x16).
  let maxD = D.p.z;
  for (var q = 0u; q < 4u; q++) {
    let ti = li + q * 64u;
    let t = vec2u(ti % ${DEP}u, ti / ${DEP}u);
    let n = texelDir(borderSrc(t, ${DEP - 2}u), ${DEP - 2}u);
    var acc = vec2f(0.0); var ws = 0.0;
    for (var r = 0u; r < R; r++) {
      let c = dot(n, rayDir[r]);
      if (c < 0.83) { continue; } // cos^50 < 1e-4
      let w = pow(c, 50.0);
      let dd = min(rayDist[r], maxD);
      acc += w * vec2f(dd, dd * dd); ws += w;
    }
    let ai = pi * ${DEP * DEP}u + ti;
    let prev = unpack2x16float(dep[ai]);
    var cur = prev;
    if (ws > 1e-6) { cur = acc / ws; }
    dep[ai] = pack2x16float(mix(cur, prev, h0));
  }
  if (li == 0u) { state[pi] = vec4f(st.xyz, f32(u32(st.w) | 2u)); }
}

// ---- gather ----
fn sampleIrr(pi: u32, n: vec3f) -> vec3f {
  let uv = octEncode(n) * f32(${IRR - 2}) + 0.5;  // texel space incl. border, centres at +0.5
  let b = vec2i(floor(uv)); let f = uv - vec2f(b);
  var s = vec3f(0.0);
  for (var k = 0u; k < 4u; k++) {
    let o = vec2i(i32(k & 1u), i32(k >> 1u));
    let t = clamp(b + o, vec2i(0), vec2i(${IRR - 1}));
    let w = select(1.0 - f.x, f.x, o.x == 1) * select(1.0 - f.y, f.y, o.y == 1);
    let v = irr[pi * ${IRR * IRR}u + u32(t.y) * ${IRR}u + u32(t.x)];
    s += w * vec3f(unpack2x16float(v.x), unpack2x16float(v.y).x);
  }
  return s;
}
fn sampleDep(pi: u32, d: vec3f) -> vec2f {
  let uv = octEncode(d) * f32(${DEP - 2}) + 0.5;
  let b = vec2i(floor(uv)); let f = uv - vec2f(b);
  var s = vec2f(0.0);
  for (var k = 0u; k < 4u; k++) {
    let o = vec2i(i32(k & 1u), i32(k >> 1u));
    let t = clamp(b + o, vec2i(0), vec2i(${DEP - 1}));
    let w = select(1.0 - f.x, f.x, o.x == 1) * select(1.0 - f.y, f.y, o.y == 1);
    s += w * unpack2x16float(dep[pi * ${DEP * DEP}u + u32(t.y) * ${DEP}u + u32(t.x)]);
  }
  return s;
}

@compute @workgroup_size(8, 8) fn gather(@builtin(global_invocation_id) gid: vec3u) {
  if (gid.x >= u32(F.size.x) || gid.y >= u32(F.size.y)) { return; }
  let px = vec2i(gid.xy);
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { textureStore(irrOut, px, vec4f(0.0)); return; }
  let x = worldAt(px, d);
  let n = textureLoad(normalTex, px, 0).xyz;
  let v = normalize(F.eye.xyz - x);
  let s = D.origin.w;
  let bp = x + (n * (1.0 - D.q.y) + v * D.q.y) * (0.75 * s * 0.3);
  let g = (bp - D.origin.xyz) / s;
  let b = vec3i(floor(g)); let a = g - vec3f(b);
  var e = vec3f(0.0); var ws = 0.0;
  // S3 receiving-side operator on toon pixels: L0 / L1 of the interpolated irradiance from its values along the six
  // axes (the L2 terms cancel in these sums), then the same toonReceive as the cascades' gather.
  let tagA = textureLoad(albedoTex, px, 0).a;
  let toon = tagA > 0.75;
  var ax: array<vec3f, 6>;
  for (var k = 0u; k < 8u; k++) {
    let o = vec3i(i32(k & 1u), i32((k >> 1u) & 1u), i32((k >> 2u) & 1u));
    let c = b + o;
    if (any(c < vec3i(0)) || any(c >= vec3i(D.dims.xyz))) { continue; }
    let pi = u32(c.x) + D.dims.x * (u32(c.y) + D.dims.y * u32(c.z));
    let st = state[pi];
    if ((u32(st.w) & 3u) != 3u) { continue; }
    let pp = D.origin.xyz + vec3f(c) * s + st.xyz;
    let tri = select(1.0 - a, a, o == vec3i(1));
    var w = 1.0;
    let toP = normalize(pp - x);
    let wrap = (dot(toP, n) + 1.0) * 0.5;
    w *= wrap * wrap + 0.2;
    let bv = bp - pp;
    let dist = length(bv);
    let m = sampleDep(pi, bv / max(dist, 1e-6));
    let variance = abs(m.x * m.x - m.y);
    var cheb = 1.0;
    if (dist > m.x) {
      let t = dist - m.x;
      cheb = variance / (variance + t * t);
      cheb = max(cheb * cheb * cheb, 0.0);
    }
    w *= max(0.05, cheb);
    w = max(w, 1e-6);
    if (w < 0.2) { w *= w * w / (0.2 * 0.2); }
    w *= tri.x * tri.y * tri.z;
    // RTXGI: probes are blended in pow(x, gamma / 2) space and the sum is squared back to linear.
    let ie = sampleIrr(pi, n);
    e += w * pow(max(ie, vec3f(0.0)), vec3f(0.5 * D.q.x)); ws += w;
    if (toon) {
      for (var a = 0u; a < 6u; a++) {
        var dir = vec3f(0.0); dir[a / 2u] = select(1.0, -1.0, (a & 1u) == 1u);
        ax[a] += w * pow(max(sampleIrr(pi, dir), vec3f(0.0)), vec3f(D.q.x));
      }
    }
  }
  let eh = e / max(ws, 1e-9);
  var outE = select(vec3f(0.0), PI * eh * eh, ws > 0.0);
  var alpha = select(1.0, 2.0, tagA > 0.25);
  if (toon && ws > 0.0) {
    let iw = PI / ws;
    let c0 = (ax[0] + ax[1] + ax[2] + ax[3] + ax[4] + ax[5]) * iw / (6.0 * 0.282095);
    let k1 = iw / (2.0 * 0.488603);
    let r = toonReceive(c0, (ax[2] - ax[3]) * k1, (ax[4] - ax[5]) * k1, (ax[0] - ax[1]) * k1, n, F.style.z);
    if (F.style.y > 0.5) { outE = r.e; }
    alpha = 2.0 + r.band + select(0.0, 2.0, r.contrast >= 0.1);
  }
  textureStore(irrOut, px, vec4f(outE, alpha));
}
`;

export interface Ddgi {
  irr: GPUTexture;
  params: DdgiParams;
  dims: [number, number, number];
  bytes: number;
  usedBytes(counts: Uint32Array): number;
  encode(enc: GPUCommandEncoder, tw: (pass: number) => GPUComputePassTimestampWrites | undefined): void;
  readCounts(): Promise<Uint32Array>;
  setStats(level: number): void;
  destroy(): void;
}

function rotation(seed: number): number[] {
  // Deterministic random rotation (uniform quaternion from a hashed seed).
  let s = (seed * 2654435761) >>> 0;
  const rnd = () => { s = (s ^ (s >>> 15)) >>> 0; s = Math.imul(s, 0x2c1b3c6d) >>> 0; s = (s ^ (s >>> 12)) >>> 0; s = Math.imul(s, 0x297a2d39) >>> 0; s = (s ^ (s >>> 15)) >>> 0; return s / 4294967296; };
  const u1 = rnd(), u2 = rnd(), u3 = rnd();
  const a = Math.sqrt(1 - u1), b = Math.sqrt(u1);
  const [x, y, z, w] = [a * Math.sin(2 * Math.PI * u2), a * Math.cos(2 * Math.PI * u2), b * Math.sin(2 * Math.PI * u3), b * Math.cos(2 * Math.PI * u3)];
  return [1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w), 0,
    2 * (x * y - z * w), 1 - 2 * (x * x + z * z), 2 * (y * z + x * w), 0,
    2 * (x * z + y * w), 2 * (y * z - x * w), 1 - 2 * (x * x + y * y), 0];
}

export function createDdgi(device: GPUDevice, g: GBuffer, frame: GPUBuffer, params: DdgiParams, world: WorldResources,
  bounds: [Vec3, Vec3]): Ddgi {
  if (!world.hasVox) throw new Error('DDGI needs the voxel world');
  if (params.rays % 64 !== 0 || params.rays > 256) throw new Error('rays must be a multiple of 64, <= 256');
  const { width, height } = g;
  const s = params.spacing;
  const origin = bounds[0].map((v) => Math.floor(v / s) * s) as Vec3;
  const dims = [0, 1, 2].map((a) => Math.ceil((bounds[1][a] - origin[a]) / s) + 1) as [number, number, number];
  const N = dims[0] * dims[1] * dims[2];
  const S = GPUBufferUsage.STORAGE;
  const buf = (label: string, size: number, extra = 0) => device.createBuffer({ label, size: Math.max(16, Math.ceil(size / 16) * 16), usage: S | extra });
  const state = buf('ddgi.state', N * 16);
  const irrBuf = buf('ddgi.irr', N * IRR * IRR * 8);
  const depBuf = buf('ddgi.dep', N * DEP * DEP * 4);
  const counts = buf('ddgi.counts', 8 * 4, GPUBufferUsage.COPY_SRC | GPUBufferUsage.INDIRECT);
  const list = buf('ddgi.list', N * 4);
  const uni = device.createBuffer({ label: 'ddgi.u', size: 16 * 8, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  const irr = device.createTexture({ label: 'ddgi.irrOut', size: [width, height], format: 'rgba16float',
    usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_SRC });
  // At most ceil(N / updateDiv) probes are listed per frame (classify: index + frame divisible by updateDiv).
  const rayRows = Math.ceil(Math.ceil(N / params.updateDiv) * params.rays / 2048);
  const rayTex = device.createTexture({ label: 'ddgi.rays', size: [2048, rayRows], format: 'rgba32float', usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.TEXTURE_BINDING });
  const all = [state, irrBuf, depBuf, counts, list, uni];
  const bytes = all.reduce((t, b) => t + b.size, 0) + width * height * 8 + 2048 * rayRows * 16;

  const module = device.createShaderModule({ code: DDGI_WGSL, label: 'ddgi' });
  const C = GPUShaderStage.COMPUTE;
  const bgl0 = device.createBindGroupLayout({ entries: [
    { binding: 0, visibility: C, buffer: { type: 'uniform' } }, { binding: 1, visibility: C, buffer: { type: 'uniform' } },
    { binding: 2, visibility: C, texture: { sampleType: 'depth' } }, { binding: 3, visibility: C, texture: { sampleType: 'unfilterable-float' } },
    { binding: 4, visibility: C, storageTexture: { access: 'write-only', format: 'rgba16float' } },
    { binding: 5, visibility: C, texture: { sampleType: 'unfilterable-float' } },
  ] });
  const bgl1 = device.createBindGroupLayout({ entries: Array.from({ length: 5 }, (_, i) => ({ binding: i, visibility: C, buffer: { type: 'storage' as const } })) });
  const bgl2 = device.createBindGroupLayout({ entries: [
    { binding: 0, visibility: C, buffer: { type: 'uniform' } }, { binding: 1, visibility: C, buffer: { type: 'read-only-storage' } },
    { binding: 2, visibility: C, texture: { sampleType: 'depth' } }, { binding: 3, visibility: C, sampler: { type: 'comparison' } },
    { binding: 4, visibility: C, buffer: { type: 'read-only-storage' } }, { binding: 5, visibility: C, buffer: { type: 'read-only-storage' } },
  ] });
  const pl = device.createPipelineLayout({ bindGroupLayouts: [bgl0, bgl1, bgl2] });
  const bgl3w = device.createBindGroupLayout({ entries: [{ binding: 0, visibility: C, storageTexture: { access: 'write-only', format: 'rgba32float' } }] });
  const bgl3r = device.createBindGroupLayout({ entries: [{ binding: 1, visibility: C, texture: { sampleType: 'unfilterable-float' } }] });
  const layoutOf: Record<string, GPUPipelineLayout> = {
    traceRays: device.createPipelineLayout({ bindGroupLayouts: [bgl0, bgl1, bgl2, bgl3w] }),
    update: device.createPipelineLayout({ bindGroupLayouts: [bgl0, bgl1, bgl2, bgl3r] }),
  };
  const bg3: Record<string, GPUBindGroup> = {
    traceRays: device.createBindGroup({ layout: bgl3w, entries: [{ binding: 0, resource: rayTex.createView() }] }),
    update: device.createBindGroup({ layout: bgl3r, entries: [{ binding: 1, resource: rayTex.createView() }] }),
  };
  const P = Object.fromEntries(['clearCounts', 'classify', 'writeArgs', 'traceRays', 'update', 'gather'].map((e) =>
    [e, device.createComputePipeline({ label: `ddgi.${e}`, layout: layoutOf[e] ?? pl, compute: { module, entryPoint: e, constants: dynConstants(world.dynBricks) } })]));
  const bg0 = device.createBindGroup({ layout: bgl0, entries: [
    { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: { buffer: uni } },
    { binding: 2, resource: g.depth.createView() }, { binding: 3, resource: g.normal.createView() },
    { binding: 4, resource: irr.createView() }, { binding: 5, resource: g.albedo.createView() },
  ] });
  // The indirect args live in counts[4..7); the update reads counts too, so it gets a copy as indirect buffer.
  const args = buf('ddgi.args', 16, GPUBufferUsage.INDIRECT | GPUBufferUsage.COPY_DST);
  const bg1 = device.createBindGroup({ layout: bgl1, entries: [state, irrBuf, depBuf, counts, list].map((b, i) => ({ binding: i, resource: { buffer: b } })) });
  const bg2 = device.createBindGroup({ layout: bgl2, entries: [
    { binding: 0, resource: { buffer: world.voxUniform } }, { binding: 1, resource: { buffer: world.vox } },
    { binding: 2, resource: world.shadow.createView() }, { binding: 3, resource: device.createSampler({ compare: 'less-equal', minFilter: 'linear', magFilter: 'linear' }) },
    { binding: 4, resource: { buffer: world.dyn } }, { binding: 5, resource: { buffer: world.hr } },
  ] });
  const use = (pass: GPUComputePassEncoder, name: string) => {
    pass.setPipeline(P[name]); pass.setBindGroup(0, bg0); pass.setBindGroup(1, bg1); pass.setBindGroup(2, bg2);
    if (bg3[name]) pass.setBindGroup(3, bg3[name]);
  };
  let frameNo = 0;

  return {
    irr, params, dims, bytes: bytes + args.size,
    usedBytes(cnt) { return state.size + irrBuf.size + depBuf.size + cnt[0] * 4 + width * height * 8; },
    encode(enc, tw) {
      const u = new ArrayBuffer(16 * 8), f = new Float32Array(u), w = new Uint32Array(u);
      f.set([...origin, s], 0); w.set([...dims, params.rays], 4); f.set(rotation(frameNo + 1), 8);
      f.set([params.hysteresis, params.segBase, 1.5 * Math.sqrt(3) * s, params.adaptive ? 1 : 0], 20); // RTXGI: 1.5 |spacing|
      w.set([frameNo, params.updateDiv, params.relocate, params.classify ? 1 : 0], 24);
      f.set([params.gamma, params.viewBias, params.bounce ? 1 : 0, 0], 28);
      device.queue.writeBuffer(uni, 0, u);
      frameNo++;
      let pass = enc.beginComputePass({ label: 'giBuild', timestampWrites: tw(0) });
      use(pass, 'clearCounts'); pass.dispatchWorkgroups(1);
      use(pass, 'classify');
      const gN = Math.ceil(N / 64), gx = Math.min(gN, 65535);
      pass.dispatchWorkgroups(gx, Math.ceil(gN / gx));
      use(pass, 'writeArgs'); pass.dispatchWorkgroups(1);
      pass.end();
      enc.copyBufferToBuffer(counts, 16, args, 0, 16);
      pass = enc.beginComputePass({ label: 'giTrace', timestampWrites: tw(1) });
      use(pass, 'traceRays'); pass.dispatchWorkgroupsIndirect(args, 0);
      use(pass, 'update'); pass.dispatchWorkgroupsIndirect(args, 0);
      pass.end();
      pass = enc.beginComputePass({ label: 'giMerge', timestampWrites: tw(2) });
      pass.end();
      pass = enc.beginComputePass({ label: 'giGather', timestampWrites: tw(3) });
      use(pass, 'gather'); pass.dispatchWorkgroups(Math.ceil(width / 8), Math.ceil(height / 8));
      pass.end();
    },
    async readCounts() {
      const read = device.createBuffer({ size: 32, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
      const enc = device.createCommandEncoder();
      enc.copyBufferToBuffer(counts, 0, read, 0, 32);
      device.queue.submit([enc.finish()]);
      await read.mapAsync(GPUMapMode.READ);
      const r = new Uint32Array(read.getMappedRange().slice(0));
      read.unmap(); read.destroy();
      const out = new Uint32Array(72);
      out[0] = r[1]; out[1] = r[0]; out[2] = r[2]; out[3] = r[3];
      return out;
    },
    setStats() {},
    destroy() { for (const b of [...all, args]) b.destroy(); irr.destroy(); rayTex.destroy(); },
  };
}
