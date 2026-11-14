// S1: radiance cascades for diffuse GI, traced only against the depth buffer.
//
// Three variants share the trace, merge and gather code:
//  - 'world'  : sparse world-grid probes near visible surfaces (Split RC's Sparse RC placement). Each sampled
//               pixel registers the 8 corners of its c0 cell in a hash table; cascade i+1 is registered from
//               the probes of cascade i (exactly the corners its trilinear merge needs). Probe spacing has a
//               distance LOD so that c0 probes are ~P pixels apart. Every (probe, direction) traces its
//               own interval deterministically.
//  - 'screen' : baseline. Probes on a screen tile grid (P * 2^i pixels), placed at the depth of the tile
//               centre. Same directions and intervals.
//  - 'split'  : world probes, but intervals are filled by ray splitting: one random ray per pixel, its hit
//               deposited into the nearest probe of the cascade whose interval contains the hit.
//
// Cascade i: octahedral (4*2^i)^2 directions, spacing 2^i * s0, interval [b_i, b_{i+1}] * s0 with
// b_i = k (4^i - 1) / 3. Rays that leave the screen are unresolved (transmittance 1, no radiance), and rays
// that pass the last interval return the sky radiance. Hit radiance is the direct-lit radiance texture
// (one bounce). No history of any kind.
import { BVH_TRACE_WGSL } from './bvh.ts';
import { FRAME_WGSL } from './frame.ts';
import { STYLE_WGSL } from './style.ts';
import type { DdgiParams } from './ddgi.ts';
import type { GBuffer } from './gbuffer.ts';
import { DYN_READ_WGSL } from './dynlayer.ts';
import { HIT_READ_WGSL } from './hitrad.ts';
import { BRICK_WORDS, VOX_TRACE_WGSL } from './voxel.ts';

export type Method = 'world' | 'screen' | 'split';
/** S2: world-space interval tracer. 'none' keeps S1 (depth buffer only). */
export type WorldTracer = 'none' | 'voxel' | 'tri';
export type Relocate = 'gbuffer' | 'voxel' | 'none';

/** S2: resources of the world-space tracers (bound in group 3). */
export interface WorldResources {
  voxUniform: GPUBuffer; vox: GPUBuffer; dyn: GPUBuffer; bvhNodes: GPUBuffer; bvhTris: GPUBuffer;
  materials: GPUBuffer; baseColor: GPUTexture; shadow: GPUTexture; hasVox: boolean; hasBvh: boolean;
  hr: GPUBuffer; // P1 hit radiance (hitrad.ts), or an empty buffer
}

export interface RcParams {
  method: Method;
  P: number;            // target pixels between c0 probes
  cascades: number;     // number of cascades (<= 8)
  sMin: number;         // smallest c0 spacing (m), world probes
  kInterval: number;    // c0 interval length in units of s0
  regStride: number;    // registration samples every regStride pixels
  rayStride: number;    // split: one ray every rayStride pixels (per axis)
  maxSteps: number;     // max depth-buffer samples per interval
  pxStride: number;     // target screen distance between samples (px)
  thicknessMin: number; // depth-buffer thickness (m)
  lift: number;         // probes are kept at least lift * spacing in front of the surface
  caps: number[];       // max probes per cascade (world / split)
  analytic: boolean;    // placement test: intervals return a smooth world-space field instead of tracing
  // S2
  world: WorldTracer;   // tracer for cascades >= depthCascades, and fallback when a depth trace leaves the screen
  depthCascades: number; // cascades traced against the depth buffer first
  levelMap: number;     // voxel level grows by levelMap per cascade (1: follows the cone footprint, 2: follows the interval length)
  voxScale: number;     // c0 voxel size relative to the c0 probe spacing
  voxOffset: number;    // voxel traces start voxOffset voxels along the probe normal
  voxSkip: number;      // occupied voxels entered within voxSkip voxels of the start are ignored
  resCap: number;       // directions stop growing above this cascade (res = 4 * 2^min(i, resCap))
  stats: number;        // 0: off, 1: DDA steps, 2: steps + voxel / triangle visibility comparison
  // World probes are pushed out of the surface: 'gbuffer' fits a plane to G-buffer samples around the probe (S1,
  // depends on the view), 'voxel' pushes probes away from the occupied voxels around the grid point (same for
  // any view; the gather and the merge then skip probes that voxels hide), 'none' keeps them at their grid
  // points (diagnostic).
  relocate: Relocate;
  // S3 style operators on toon materials (style.ts): emission side, receiving side (ramp on the dominant direction;
  // off: the physical irradiance), half width of the receiving ramp in n.d.
  styleEmit: boolean;
  styleRecv: boolean;
  rampSoft: number;
  // M1: DDGI-style comparator instead of the cascades (ddgi.ts); the cascade fields are then unused.
  ddgi: DdgiParams | null;
}

export const DEFAULT_PARAMS: RcParams = {
  method: 'world', P: 8, cascades: 5, sMin: 0.05, kInterval: 1, regStride: 1, rayStride: 1,
  maxSteps: 16, pxStride: 4, thicknessMin: 0.15, lift: 0.25, caps: [1 << 18, 1 << 16, 1 << 14, 1 << 12, 1 << 11, 1 << 10, 1 << 9, 1 << 8], analytic: false,
  world: 'none', depthCascades: 8, levelMap: 1, voxScale: 0.25, voxOffset: 1, voxSkip: 0.5, resCap: 8, stats: 0, relocate: 'gbuffer',
  styleEmit: true, styleRecv: true, rampSoft: 0, ddgi: null,
};

/** One-bounce hit shading shared by the interval tracers (RC and the DDGI comparator). Needs F, PI, shadowTex,
 * shadowCmp, toonSun (style.ts), the voxel tracer and hr (P1, hitrad.ts). */
export const SHADE_WGSL = /* wgsl */ `
fn sunVis(x: vec3f) -> f32 {
  let c = F.lightViewProj * vec4f(x, 1.0);
  let uv = c.xy * vec2f(0.5, -0.5) + 0.5;
  if (any(uv < vec2f(0.0)) || any(uv > vec2f(1.0))) { return 1.0; }
  return textureSampleCompareLevel(shadowTex, shadowCmp, uv, c.z - 0.0002);
}
// One-bounce hit radiance, as the direct pass computes it (Lambert, sun, shadow map). The normal is turned to
// face the ray; a zero normal (opposite faces averaged in one voxel) faces the ray.
// S3: toon hits (alb.a = 1) inject the emission-side operator instead (style.ts).
fn shadeHit(p: vec3f, n0: vec3f, alb: vec4f, d: vec3f, bias: f32) -> vec3f {
  var n = select(-d, n0, dot(n0, n0) > 0.01);
  if (dot(n, d) > 0.0) { n = -n; }
  let ndl = max(dot(n, F.sunDir.xyz), 0.0);
  if (ndl <= 0.0) { return vec3f(0.0); }
  let vis = sunVis(p + n * bias);
  if (alb.a > 0.5 && F.style.x > 0.5) { return toonSun(alb.rgb, ndl, vis, F.sunE.rgb); }
  return alb.rgb / PI * F.sunE.rgb * ndl * vis;
}
var<private> voxHitEntry: vec3f; // entry point of the last voxel hit (DDGI keeps hit distances)
// P1: static voxel hits read the prefiltered hit radiance at the cone width (coneK, coneO set by the tracer). Without
// the layer (voxels rebuilt every frame) or a level holding the voxel, one point on the ray's side is shaded.
fn voxShade(entry: vec3f, n: vec3f, alb: vec4f, d: vec3f, v: f32, ai: u32, L: u32, pc: vec3f) -> vec3f {
  voxHitEntry = entry;
  if (hrReady()) { let r = hitRadiance(L, pc, d, dot(entry - coneO, d)); if (r.a > 0.0) { return r.rgb; } }
  return shadeHit(entry - d * (0.25 * v), n, alb, d, 0.0);
}
${HIT_READ_WGSL}
`;

const RC_WGSL = /* wgsl */ `
${FRAME_WGSL}
${STYLE_WGSL}
const PI = 3.14159265;
const EMPTY = 0u;
const NONE = 0xffffffffu;
const FIX = 4096.0;

struct CascL { hashOff: u32, hashMask: u32, probeOff: u32, cap: u32, radOff: u32, accOff: u32, res: u32, tileSize: u32,
               tilesX: u32, tilesY: u32, b0: f32, b1: f32 }
struct Layout { hdr: vec4u, c: array<CascL, 8>, wp: vec4f, wu: vec4u, wp2: vec4u }
// wp2: relocation (0 G-buffer, 1 none, 2 voxel), 0, 0, 0
// hdr: cascades, total hash slots, total accum words, 0
// wp: voxScale, voxOffset, levelMap, voxSkip; wu: world tracer (0 none, 1 voxel, 2 tri), depthCascades, stats, has BVH
struct Probe { pos: vec4f, nrm: vec4f, grid: vec4i } // pos.w = s0 (0: invalid), nrm.w = view depth

@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var<uniform> LY: Layout;
@group(0) @binding(2) var depthTex: texture_depth_2d;
@group(0) @binding(3) var normalTex: texture_2d<f32>;
@group(0) @binding(4) var litTex: texture_2d<f32>;
@group(0) @binding(5) var irrOut: texture_storage_2d<rgba16float, write>;
@group(0) @binding(6) var albedoTex: texture_2d<f32>; // a: 1 toon, 0.5 measured photoreal object (S3)
@group(1) @binding(0) var<uniform> CI: vec4u;
@group(2) @binding(0) var<storage, read_write> keys: array<atomic<u32>>;
@group(2) @binding(1) var<storage, read_write> slotProbe: array<u32>;
@group(2) @binding(2) var<storage, read_write> probes: array<Probe>;
@group(2) @binding(3) var<storage, read_write> rad: array<vec2u>;
@group(2) @binding(4) var<storage, read_write> sh: array<vec4u>;
@group(2) @binding(5) var<storage, read_write> counts: array<atomic<u32>>;
// [0,8) probes, [8,16) overflow, [16,24) insert failures, [24,32) world traces, [32,40) DDA steps,
// [40,48) voxel hit / triangle miss, [48,56) voxel miss / triangle hit, [56,64) both hit, [64,72) traces at the step cap
@group(2) @binding(6) var<storage, read_write> accum: array<atomic<u32>>;
@group(2) @binding(7) var<storage, read_write> parents: array<u32>; // world: 8 upper-cascade probes per probe
struct Material { baseColorFactor: vec4f, layers: vec4u, params: vec4f }
@group(3) @binding(0) var<uniform> VX: VoxU;
@group(3) @binding(1) var<storage, read> vox: array<u32>;
@group(3) @binding(2) var<storage, read> bvhNodes: array<BvhNode>;
@group(3) @binding(3) var<storage, read> bvhTris: array<vec4f>;
@group(3) @binding(4) var<storage, read> materials: array<Material>;
@group(3) @binding(5) var baseColorTex: texture_2d_array<f32>;
@group(3) @binding(6) var linSamp: sampler;
@group(3) @binding(7) var shadowTex: texture_depth_2d;
@group(3) @binding(8) var shadowCmp: sampler_comparison;
@group(3) @binding(9) var<storage, read> dyn: array<u32>; // P2 dynamic layer (dynlayer.ts)
@group(3) @binding(10) var<storage, read> hr: array<u32>; // P1 hit radiance (hitrad.ts)

${SHADE_WGSL}
fn triShade(p: vec3f, n: vec3f, alb: vec4f, d: vec3f) -> vec3f { return shadeHit(p, n, alb, d, 0.03); }
${VOX_TRACE_WGSL}
${DYN_READ_WGSL}
${BVH_TRACE_WGSL}

fn voxLevel(s0: f32, c: u32) -> u32 {
  let v = LY.wp.x * s0 * exp2(LY.wp.z * f32(c));
  return u32(clamp(round(log2(v / VX.a.x)), 0.0, VX.a.y - 1.0));
}
// Voxel traces start voxOffset voxels along the probe's surface normal (out of the surface's own voxels) and
// ignore occupied voxels entered within voxSkip voxels.
fn traceWorld(o: vec3f, d: vec3f, t0: f32, t1: f32, s0: f32, c: u32, nrm: vec3f) -> vec4f {
  if (LY.wu.x == 2u) { return traceTri(o, d, t0, t1); }
  let L = voxLevelFor(voxLevel(s0, c), o + d * t1);
  let v = voxSize(L);
  voxSteps = 0u;
  coneK = 3.5449077 / f32(LY.c[c].res); coneO = o;
  var r = traceVox(o + nrm * (LY.wp.y * v), d, t0, t1, LY.wp.w * v, L);
  // P2: the dynamic layer in front of the static hit, read at the width of the direction bin's cone.
  if (dyn[0] != 0u) {
    let tS = select(t1, dot(voxHitEntry - o, d), r.a < 0.5);
    let dl = traceDyn(o, d, t0, min(t1, tS), coneK);
    if (dl.a > 0.0) { r = vec4f(dl.rgb + (1.0 - dl.a) * r.rgb, (1.0 - dl.a) * r.a); }
  }
  if (LY.wu.z > 0u) {
    atomicAdd(&counts[24u + c], 1u);
    atomicAdd(&counts[32u + c], voxSteps);
    if (voxSteps >= 1024u) { atomicAdd(&counts[64u + c], 1u); }
    if (LY.wu.z > 1u && LY.wu.w == 1u) {
      let tr = traceTri(o, d, t0, t1);
      let vh = r.a < 0.5; let th = tr.a < 0.5;
      if (vh && !th) { atomicAdd(&counts[40u + c], 1u); }
      if (!vh && th) { atomicAdd(&counts[48u + c], 1u); }
      if (vh && th) { atomicAdd(&counts[56u + c], 1u); }
    }
  }
  return r;
}

fn lin(wid: vec3u, nwg: vec3u, li: u32) -> u32 { return (wid.y * nwg.x + wid.x) * 64u + li; }
fn hash32(x: u32) -> u32 {
  var h = x; h ^= h >> 16u; h *= 0x7feb352du; h ^= h >> 15u; h *= 0x846ca68bu; h ^= h >> 16u; return h;
}
fn rnd(s: ptr<function, u32>) -> f32 { *s = hash32(*s + 0x9e3779b9u); return f32(*s >> 8u) / 16777216.0; }

fn lodFor(dist: f32) -> i32 { return clamp(i32(floor(log2(max(dist * F.rc.y * F.rc.z / F.rc.x, 1.0)))), 0, 14); }
fn spacing(lod: i32, c: u32) -> f32 { return F.rc.x * exp2(f32(lod) + f32(c)); }
fn originOf(s: f32) -> vec3i { return vec3i(floor(F.eye.xyz / s)) - vec3i(256); }
fn keyFor(g: vec3i, lod: i32, c: u32) -> u32 {
  let rel = g - originOf(spacing(lod, c));
  if (any(rel < vec3i(0)) || any(rel >= vec3i(512))) { return NONE; }
  return 0x80000000u | (u32(lod) << 27u) | (u32(rel.x) << 18u) | (u32(rel.y) << 9u) | u32(rel.z);
}
fn insertKey(c: u32, key: u32) {
  let L = LY.c[c];
  var h = hash32(key) & L.hashMask;
  for (var i = 0u; i < 256u; i++) {
    let cur = atomicLoad(&keys[L.hashOff + h]);
    if (cur == key) { return; }
    if (cur == EMPTY) {
      let r = atomicCompareExchangeWeak(&keys[L.hashOff + h], EMPTY, key);
      if (r.exchanged || r.old_value == key) { return; }
      if (r.old_value == EMPTY) { continue; }
    }
    h = (h + 1u) & L.hashMask;
  }
  atomicAdd(&counts[16u + c], 1u);
}
fn lookup(c: u32, key: u32) -> u32 {
  if (key == NONE) { return NONE; }
  let L = LY.c[c];
  var h = hash32(key) & L.hashMask;
  for (var i = 0u; i < 256u; i++) {
    let cur = atomicLoad(&keys[L.hashOff + h]);
    if (cur == key) { return slotProbe[L.hashOff + h]; }
    if (cur == EMPTY) { return NONE; }
    h = (h + 1u) & L.hashMask;
  }
  return NONE;
}
fn probeCount(c: u32) -> u32 { return min(atomicLoad(&counts[c]), LY.c[c].cap); }
fn corner(k: u32) -> vec3i { return vec3i(i32(k & 1u), i32((k >> 1u) & 1u), i32((k >> 2u) & 1u)); }

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
fn octTexel(d: vec3f, res: u32) -> u32 {
  let t = min(vec2u(octEncode(d) * f32(res)), vec2u(res - 1u));
  return t.y * res + t.x;
}
fn dirOf(di: u32, res: u32) -> vec3f { return octDecode((vec2f(f32(di % res), f32(di / res)) + 0.5) / f32(res)); }
fn packRad(v: vec4f) -> vec2u { return vec2u(pack2x16float(v.xy), pack2x16float(v.zw)); }
fn unpackRad(p: vec2u) -> vec4f { return vec4f(unpack2x16float(p.x), unpack2x16float(p.y)); }
fn viewZ(p: vec3f) -> f32 { return dot(p - F.eye.xyz, F.fwd.xyz); }

// Depth-buffer trace of [t0, t1] along dir. Returns (radiance, T): T = 0 hit, 1 passed, 2 left the screen.
fn traceScreen(o: vec3f, dir: vec3f, t0: f32, t1: f32) -> vec4f {
  var a = o + dir * t0;
  var b = o + dir * t1;
  let zn = F.eye.w * 1.5;
  let za = viewZ(a); let zb = viewZ(b);
  if (za < zn && zb < zn) { return vec4f(0.0, 0.0, 0.0, 2.0); }
  if (za < zn) { a = mix(a, b, (zn - za) / (zb - za)); }
  else if (zb < zn) { b = mix(a, b, (zn - za) / (zb - za)); }
  let ca = F.viewProj * vec4f(a, 1.0);
  let cb = F.viewProj * vec4f(b, 1.0);
  let lenPx = length((cb.xy / cb.w - ca.xy / ca.w) * 0.5 * F.size.xy);
  let steps = u32(clamp(ceil(lenPx / F.rc2.z), 1.0, f32(F.ru.w)));
  let thick = max(F.rc2.y, 2.0 * length(b - a) / f32(steps));
  for (var k = 0u; k < steps; k++) {
    let c = mix(ca, cb, (f32(k) + 0.5) / f32(steps));
    let ndc = c.xy / c.w;
    if (any(abs(ndc) >= vec2f(1.0))) { return vec4f(0.0, 0.0, 0.0, 2.0); }
    let px = clamp(vec2i(floor(vec2f(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5) * F.size.xy)), vec2i(0), vec2i(F.size.xy) - 1);
    let d = textureLoad(depthTex, px, 0);
    if (d <= 0.0) { continue; }
    let sz = F.eye.w / d;
    if (c.w > sz * 1.001 && c.w < sz + thick) { return vec4f(textureLoad(litTex, px, 0).rgb, 0.0); }
  }
  return vec4f(0.0, 0.0, 0.0, 1.0);
}

// Keep a world probe in front of the surface it was registered from: fit a plane (mean normal, mean
// signed distance) to G-buffer samples within 1.5 spacings of the probe and push the probe out along it.
// For planar surfaces the result does not depend on which pixels happen to be sampled.
struct Reloc { p: vec3f, n: vec3f }
fn relocate(p: vec3f, s: f32) -> Reloc {
  let c = F.viewProj * vec4f(p, 1.0);
  if (c.w <= F.eye.w) { return Reloc(p, vec3f(0.0)); }
  let ndc = c.xy / c.w;
  let ctr = vec2f(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5) * F.size.xy;
  let rpx = s / (c.w * F.rc.y);
  var sn = vec3f(0.0); var se = 0.0; var cnt = 0.0;
  for (var j = 0u; j < 16u; j++) {
    let o = (vec2f(f32(j % 4u), f32(j / 4u)) - 1.5) / 1.5 * rpx;
    let q = vec2i(floor(ctr + o));
    if (any(q < vec2i(0)) || any(q >= vec2i(F.size.xy))) { continue; }
    let d = textureLoad(depthTex, q, 0);
    if (d <= 0.0) { continue; }
    let x = worldAt(q, d);
    if (distance(x, p) > 1.5 * s) { continue; }
    let n = textureLoad(normalTex, q, 0).xyz;
    sn += n; se += dot(n, p - x) / s; cnt += 1.0;
  }
  if (cnt < 1.0 || length(sn) < 0.3 * cnt) { return Reloc(p, vec3f(0.0)); }
  let m = normalize(sn);
  let e = se / cnt;
  if (e < F.rc2.x) { return Reloc(p + m * (F.rc2.x - e) * s, m); }
  return Reloc(p, m);
}

// View-independent relocation from the voxel world. The voxel content of a world cell does not depend on the
// camera (only the clipmap window does), so a grid point always gets the same position and normal. Level L is
// the one the probe's own traces use (voxel ~ voxScale * spacing). The normal points away from the occupied
// voxels of the next level in the 4^3 cube around the probe (+-1 spacing), i.e. towards the side of the surface
// the grid point is already on; when that is ambiguous (grid point inside a thin slab) the voxels' stored
// normals decide. The probe is then marched along the normal until its voxel and the voxel lift * spacing
// behind it are empty. Voxels are surfaces only, so a grid point inside a thick object (a pillar) stays there:
// the stored normals are not oriented reliably enough to tell inside from outside (a plane fit to them, as
// relocate() does with G-buffer normals, was darker still). Probes outside a wall therefore stay outside; the
// gather and the merge skip probes that voxels hide (segOccluded).
fn voxCell(L: u32, p: vec3f) -> vec2u { // (brick pointer, bit), pointer VOX_MARK if empty or outside
  let v = voxSize(L);
  let c = vec3i(floor((p - vec3f(VX.origin[L].xyz) * v * 8.0) / v));
  if (any(c < vec3i(0)) || any(c >= vec3i(voxG() * 8))) { return vec2u(VOX_MARK, 0u); }
  let ptr = vox[voxPtrIndex(L, c >> vec3u(3u))];
  if (ptr >= VOX_MARK) { return vec2u(VOX_MARK, 0u); }
  let l = c & vec3i(7);
  let bit = u32(l.x + 8 * l.y + 64 * l.z);
  if ((vox[VX.b.y + ptr * ${BRICK_WORDS}u + (bit >> 5u)] & (1u << (bit & 31u))) == 0u) { return vec2u(VOX_MARK, 0u); }
  return vec2u(ptr, bit);
}
fn voxStoredNormal(cell: vec2u) -> vec3f {
  let nn = unpack2x16snorm(vox[VX.b.z + voxRank(cell.x, cell.y) * 2u + 1u]);
  var n = vec3f(nn.x, nn.y, 1.0 - abs(nn.x) - abs(nn.y));
  let q = max(-n.z, 0.0);
  n.x += select(q, -q, n.x >= 0.0); n.y += select(q, -q, n.y >= 0.0);
  return n;
}
fn voxOcc(L: u32, p: vec3f) -> bool { return voxCell(L, p).x != VOX_MARK; }
fn relocateVox(p: vec3f, s0: f32, c: u32) -> Reloc {
  let L = voxLevelFor(voxLevel(s0, c), p);
  let Lg = voxLevelFor(min(L + 1u, u32(VX.a.y) - 1u), p);
  let vg = voxSize(Lg);
  var grad = vec3f(0.0); var cnt = 0.0;
  for (var k = 0u; k < 64u; k++) {
    let o = (vec3f(f32(k & 3u), f32((k >> 2u) & 3u), f32(k >> 4u)) - 1.5) * vg;
    if (!voxOcc(Lg, p + o)) { continue; }
    grad -= o; cnt += 1.0;
  }
  if (cnt < 1.0) { return Reloc(p, vec3f(0.0)); }
  var n = grad;
  if (length(grad) < 0.1 * cnt * vg) {
    n = vec3f(0.0);
    for (var k = 0u; k < 64u; k++) {
      let cell = voxCell(Lg, p + (vec3f(f32(k & 3u), f32((k >> 2u) & 3u), f32(k >> 4u)) - 1.5) * vg);
      if (cell.x != VOX_MARK) { n += voxStoredNormal(cell); }
    }
  }
  if (length(n) < 1e-4) { return Reloc(p, vec3f(0.0)); }
  n = normalize(n);
  let s = s0 * exp2(f32(c));
  let back = F.rc2.x * s;
  let stp = max(0.5 * voxSize(L), 1.5 * s / 16.0);
  for (var i = 0u; i <= 16u; i++) {
    let q = p + n * (f32(i) * stp);
    if (f32(i) * stp > 1.5 * s) { break; }
    if (!voxOcc(L, q) && !voxOcc(L, q - n * back)) { return Reloc(q, n); }
  }
  return Reloc(p, n);
}

@compute @workgroup_size(64) fn clearKeys(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  if (i < 72u) { atomicStore(&counts[i], 0u); }
  if (i < LY.hdr.y) { atomicStore(&keys[i], EMPTY); }
}
@compute @workgroup_size(64) fn clearAccum(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  if (i < LY.hdr.z) { atomicStore(&accum[i], 0u); }
}

@compute @workgroup_size(64) fn registerPixels(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  let st = F.ru.z;
  let sx = (u32(F.size.x) + st - 1u) / st; let sy = (u32(F.size.y) + st - 1u) / st;
  if (i >= sx * sy) { return; }
  let px = vec2i(vec2u(i % sx, i / sx) * st + vec2u(st / 2u));
  if (px.x >= i32(F.size.x) || px.y >= i32(F.size.y)) { return; }
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { return; }
  let x = worldAt(px, d);
  let lod = lodFor(distance(x, F.eye.xyz));
  let b = vec3i(floor(x / spacing(lod, 0u)));
  for (var k = 0u; k < 8u; k++) {
    let key = keyFor(b + corner(k), lod, 0u);
    if (key != NONE) { insertKey(0u, key); }
  }
}

// Cascade c from the probes of c-1: the c-grid points with non-zero trilinear weight at each c-1 probe.
@compute @workgroup_size(64) fn registerUp(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let c = CI.x;
  let t = lin(wid, nwg, li);
  if (t >= probeCount(c - 1u)) { return; }
  let pr = probes[LY.c[c - 1u].probeOff + t];
  let g = pr.grid.xyz; let lod = pr.grid.w;
  let lo = g >> vec3u(1u);
  let odd = (g & vec3i(1)) != vec3i(0);
  for (var k = 0u; k < 8u; k++) {
    let o = corner(k);
    if (any((o > vec3i(0)) & !odd)) { continue; }
    let key = keyFor(lo + o, lod, c);
    if (key != NONE) { insertKey(c, key); }
  }
}

@compute @workgroup_size(64) fn compact(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let c = CI.x; let L = LY.c[c];
  let h = lin(wid, nwg, li);
  if (h > L.hashMask) { return; }
  let key = atomicLoad(&keys[L.hashOff + h]);
  if (key == EMPTY) { return; }
  let idx = atomicAdd(&counts[c], 1u);
  if (idx >= L.cap) { slotProbe[L.hashOff + h] = NONE; atomicAdd(&counts[8u + c], 1u); return; }
  slotProbe[L.hashOff + h] = idx;
  let lod = i32((key >> 27u) & 15u);
  let rel = vec3i(i32((key >> 18u) & 511u), i32((key >> 9u) & 511u), i32(key & 511u));
  let s = spacing(lod, c);
  let g = rel + originOf(s);
  var r = Reloc(vec3f(g) * s, vec3f(0.0));
  if (LY.wp2.x == 0u) { r = relocate(vec3f(g) * s, s); }
  else if (LY.wp2.x == 2u) { r = relocateVox(vec3f(g) * s, spacing(lod, 0u), c); }
  probes[L.probeOff + idx] = Probe(vec4f(r.p, spacing(lod, 0u)), vec4f(r.n, viewZ(r.p)), vec4i(g, lod));
}

// World probes: find the (up to 8) probes of cascade c+1 that the merge of a cascade-c probe reads, once
// per probe instead of once per (probe, direction).
@compute @workgroup_size(64) fn linkParents(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let c = CI.x; let L = LY.c[c];
  let pi = lin(wid, nwg, li);
  if (pi >= probeCount(c)) { return; }
  let pr = probes[L.probeOff + pi];
  let g = pr.grid.xyz; let lod = pr.grid.w;
  let lo = g >> vec3u(1u);
  let odd = (g & vec3i(1)) != vec3i(0);
  for (var k = 0u; k < 8u; k++) {
    let o = corner(k);
    var q = NONE;
    if (!any((o > vec3i(0)) & !odd)) { q = lookup(c + 1u, keyFor(lo + o, lod, c + 1u)); }
    // Voxel relocation: parents hidden by voxels are not merged (when all are hidden the probe gets nothing from
    // above; keeping them leaked light through the walls of the leak room).
    if (q != NONE && LY.wp2.x == 2u) {
      let Lv = voxLevelFor(voxLevel(pr.pos.w, c), pr.pos.xyz);
      if (segOccluded(pr.pos.xyz, probes[LY.c[c + 1u].probeOff + q].pos.xyz, Lv)) { q = NONE; }
    }
    parents[(L.probeOff + pi) * 8u + k] = q;
  }
}

@compute @workgroup_size(64) fn setupScreen(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let c = CI.x; let L = LY.c[c];
  let t = lin(wid, nwg, li);
  let n = L.tilesX * L.tilesY;
  if (t == 0u) { atomicStore(&counts[c], n); }
  if (t >= n) { return; }
  let tile = vec2u(t % L.tilesX, t / L.tilesX);
  let px = min(vec2i(tile * L.tileSize + L.tileSize / 2u), vec2i(F.size.xy) - 1);
  let d = textureLoad(depthTex, px, 0);
  var pr = Probe(vec4f(0.0), vec4f(0.0), vec4i(vec2i(tile), 0, 0));
  if (d > 0.0) {
    let x = worldAt(px, d);
    let nrm = textureLoad(normalTex, px, 0).xyz;
    let s0 = distance(x, F.eye.xyz) * F.rc.y * F.rc.z;
    pr.pos = vec4f(x + nrm * F.rc2.x * s0 * exp2(f32(c)), s0);
    pr.nrm = vec4f(nrm, viewZ(x));
  }
  probes[L.probeOff + t] = pr;
}

// Placement test: a view-independent, smooth radiance field. Any frame-to-frame change of the gathered
// result then comes from probe placement, LOD, relocation and interpolation, not from the depth buffer.
fn analyticInterval(o: vec3f, dir: vec3f, t0: f32, t1: f32) -> vec4f {
  let p = o + dir * (0.5 * (t0 + t1));
  let f = 1.2 + sin(0.8 * p.x + 0.4) * cos(0.6 * p.z + 0.2) + 0.5 * sin(0.7 * p.y + 1.3);
  return vec4f(vec3f(0.25 * f * (0.7 + 0.3 * dir.y)), 0.5);
}

@compute @workgroup_size(64) fn trace(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let c = CI.x; let L = LY.c[c];
  let t = lin(wid, nwg, li);
  let dirs = L.res * L.res;
  let pi = t / dirs; let di = t % dirs;
  if (pi >= probeCount(c)) { return; }
  let pr = probes[L.probeOff + pi];
  var out = vec4f(0.0, 0.0, 0.0, 1.0);
  if (pr.pos.w > 0.0) {
    let dir = dirOf(di, L.res);
    let t0 = L.b0 * pr.pos.w; let t1 = L.b1 * pr.pos.w;
    if (F.ru2.w == 1u) {
      out = analyticInterval(pr.pos.xyz, dir, t0, t1);
    } else if (c < LY.wu.y || LY.wu.x == 0u) {
      let r = traceScreen(pr.pos.xyz, dir, t0, t1);
      out = vec4f(r.rgb, min(r.a, 1.0));
      if (r.a > 1.5 && LY.wu.x != 0u) { out = traceWorld(pr.pos.xyz, dir, t0, t1, pr.pos.w, c, pr.nrm.xyz); }
    } else {
      out = traceWorld(pr.pos.xyz, dir, t0, t1, pr.pos.w, c, pr.nrm.xyz);
    }
  }
  rad[L.radOff + t] = packRad(out);
}

// Ray splitting: one random ray per sampled pixel over the hemisphere; walks the intervals in order and
// deposits into the nearest probe of each cascade it reaches.
@compute @workgroup_size(64) fn deposit(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  let st = F.ru2.x;
  let sx = (u32(F.size.x) + st - 1u) / st; let sy = (u32(F.size.y) + st - 1u) / st;
  if (i >= sx * sy) { return; }
  let px = vec2i(vec2u(i % sx, i / sx) * st + vec2u(st / 2u));
  if (px.x >= i32(F.size.x) || px.y >= i32(F.size.y)) { return; }
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { return; }
  let x = worldAt(px, d);
  let n = textureLoad(normalTex, px, 0).xyz;
  let lod = lodFor(distance(x, F.eye.xyz));
  let s0 = spacing(lod, 0u);
  var seed = hash32(u32(px.x) * 1973u + u32(px.y) * 9277u + F.ru2.y * 26699u);
  let z = rnd(&seed); let phi = 2.0 * PI * rnd(&seed);
  let r = sqrt(max(0.0, 1.0 - z * z));
  let tb = normalize(select(vec3f(0.0, -n.z, n.y), vec3f(n.z, 0.0, -n.x), abs(n.x) < abs(n.y)) + vec3f(1e-6, 0.0, 0.0));
  let bb = cross(n, tb);
  let dir = normalize(tb * (r * cos(phi)) + bb * (r * sin(phi)) + n * z);
  let o = x + n * (0.05 * s0);
  for (var c = 0u; c < LY.hdr.x; c++) {
    let L = LY.c[c];
    let h = traceScreen(o, dir, L.b0 * s0, L.b1 * s0);
    if (h.a > 1.5) { break; }
    let q = lookup(c, keyFor(vec3i(floor(x / spacing(lod, c) + 0.5)), lod, c));
    if (q != NONE) {
      let a = L.accOff + (q * L.res * L.res + octTexel(dir, L.res)) * 5u;
      atomicAdd(&accum[a], 1u);
      if (h.a < 0.5) {
        let v = vec3u(min(h.rgb * FIX, vec3f(1e6)));
        atomicAdd(&accum[a + 1u], 1u);
        atomicAdd(&accum[a + 2u], v.x); atomicAdd(&accum[a + 3u], v.y); atomicAdd(&accum[a + 4u], v.z);
      }
    }
    if (h.a < 0.5) { break; }
  }
}

@compute @workgroup_size(64) fn resolve(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let c = CI.x; let L = LY.c[c];
  let t = lin(wid, nwg, li);
  if (t / (L.res * L.res) >= probeCount(c)) { return; }
  let a = L.accOff + t * 5u;
  let reach = atomicLoad(&accum[a]);
  var out = vec4f(0.0, 0.0, 0.0, 1.0);
  if (reach > 0u) {
    let hit = f32(atomicLoad(&accum[a + 1u]));
    let s = vec3f(f32(atomicLoad(&accum[a + 2u])), f32(atomicLoad(&accum[a + 3u])), f32(atomicLoad(&accum[a + 4u]))) / FIX;
    out = vec4f(s / f32(reach), 1.0 - hit / f32(reach));
  }
  rad[L.radOff + t] = packRad(out);
}

// Upper-cascade radiance for a direction texel (u, v) of a cascade with res lr: the 2x2 block when the upper
// cascade has twice the directions, the same texel when direction growth is capped.
fn upperAvg(U: CascL, q: u32, u: u32, v: u32, lr: u32) -> vec3f {
  if (U.res == lr) { return unpackRad(rad[U.radOff + q * U.res * U.res + v * U.res + u]).rgb; }
  let base = U.radOff + q * U.res * U.res + v * 2u * U.res + u * 2u;
  return 0.25 * (unpackRad(rad[base]).rgb + unpackRad(rad[base + 1u]).rgb
               + unpackRad(rad[base + U.res]).rgb + unpackRad(rad[base + U.res + 1u]).rgb);
}

@compute @workgroup_size(64) fn mergeWorld(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let c = CI.x; let L = LY.c[c];
  let t = lin(wid, nwg, li);
  let dirs = L.res * L.res;
  let pi = t / dirs; let di = t % dirs;
  if (pi >= probeCount(c)) { return; }
  let v = unpackRad(rad[L.radOff + t]);
  var up = F.sky.rgb;
  if (c + 1u < LY.hdr.x && v.a > 0.0) {
    let U = LY.c[c + 1u];
    let u0 = di % L.res; let v0 = di / L.res;
    var acc = vec3f(0.0); var ws = 0.0;
    for (var k = 0u; k < 8u; k++) {
      let q = parents[(L.probeOff + pi) * 8u + k];
      if (q == NONE) { continue; }
      acc += upperAvg(U, q, u0, v0, L.res); ws += 1.0;
    }
    up = select(vec3f(0.0), acc / max(ws, 1.0), ws > 0.0);
  }
  rad[L.radOff + t] = packRad(vec4f(v.rgb + v.a * up, 1.0));
}

@compute @workgroup_size(64) fn mergeScreen(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let c = CI.x; let L = LY.c[c];
  let t = lin(wid, nwg, li);
  let dirs = L.res * L.res;
  let pi = t / dirs; let di = t % dirs;
  if (pi >= probeCount(c)) { return; }
  let v = unpackRad(rad[L.radOff + t]);
  var up = F.sky.rgb;
  if (c + 1u < LY.hdr.x && v.a > 0.0) {
    up = vec3f(0.0);
    let pr = probes[L.probeOff + pi];
    if (pr.pos.w > 0.0) {
      let U = LY.c[c + 1u];
      let ctr = (vec2f(f32(pi % L.tilesX), f32(pi / L.tilesX)) + 0.5) * f32(L.tileSize);
      let uc = ctr / f32(U.tileSize) - 0.5;
      let b = vec2i(floor(uc)); let f = uc - vec2f(b);
      let u0 = di % L.res; let v0 = di / L.res;
      var acc = vec3f(0.0); var ws = 0.0;
      for (var k = 0u; k < 4u; k++) {
        let o = vec2i(i32(k & 1u), i32(k >> 1u));
        let q = clamp(b + o, vec2i(0), vec2i(i32(U.tilesX) - 1, i32(U.tilesY) - 1));
        let qi = u32(q.y) * U.tilesX + u32(q.x);
        let qp = probes[U.probeOff + qi];
        if (qp.pos.w <= 0.0) { continue; }
        let fw = select(1.0 - f, f, o == vec2i(1));
        let rel = abs(qp.nrm.w - pr.nrm.w) / pr.nrm.w;
        let w = (fw.x * fw.y + 1e-4) * (exp(-20.0 * rel) + 1e-4);
        acc += w * upperAvg(U, qi, u0, v0, L.res); ws += w;
      }
      if (ws > 0.0) { up = acc / ws; }
    }
  }
  rad[L.radOff + t] = packRad(vec4f(v.rgb + v.a * up, 1.0));
}

fn shBasis(n: vec3f) -> array<f32, 9> {
  return array<f32, 9>(0.282095, 0.488603 * n.y, 0.488603 * n.z, 0.488603 * n.x,
    1.092548 * n.x * n.y, 1.092548 * n.y * n.z, 0.315392 * (3.0 * n.z * n.z - 1.0), 1.092548 * n.x * n.z,
    0.546274 * (n.x * n.x - n.y * n.y));
}

// c0 (4x4 directions) -> L2 spherical harmonics of irradiance (cosine-convolved), packed as f16.
@compute @workgroup_size(64) fn projectSH(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let L = LY.c[0];
  let pi = lin(wid, nwg, li);
  if (pi >= probeCount(0u)) { return; }
  var cf: array<vec3f, 9>;
  for (var d = 0u; d < 16u; d++) {
    let r = unpackRad(rad[L.radOff + pi * 16u + d]).rgb * F.omega0[d / 4u][d % 4u];
    let y = shBasis(dirOf(d, 4u));
    for (var k = 0u; k < 9u; k++) { cf[k] += r * y[k]; }
  }
  var v: array<f32, 32>;
  for (var k = 0u; k < 9u; k++) {
    let a = select(select(PI / 4.0, 2.0 * PI / 3.0, k < 4u), PI, k == 0u);
    v[k * 3u] = cf[k].x * a; v[k * 3u + 1u] = cf[k].y * a; v[k * 3u + 2u] = cf[k].z * a;
  }
  for (var q = 0u; q < 4u; q++) {
    let b = q * 8u;
    sh[pi * 4u + q] = vec4u(pack2x16float(vec2f(v[b], v[b + 1u])), pack2x16float(vec2f(v[b + 2u], v[b + 3u])),
                            pack2x16float(vec2f(v[b + 4u], v[b + 5u])), pack2x16float(vec2f(v[b + 6u], v[b + 7u])));
  }
}
fn evalSH(pi: u32, n: vec3f) -> vec3f {
  let y = shBasis(n);
  var v: array<f32, 32>;
  for (var q = 0u; q < 4u; q++) {
    let w = sh[pi * 4u + q];
    for (var j = 0u; j < 4u; j++) { let f = unpack2x16float(w[j]); v[q * 8u + j * 2u] = f.x; v[q * 8u + j * 2u + 1u] = f.y; }
  }
  var e = vec3f(0.0);
  for (var k = 0u; k < 9u; k++) { e += vec3f(v[k * 3u], v[k * 3u + 1u], v[k * 3u + 2u]) * y[k]; }
  return max(e, vec3f(0.0));
}
// L0 and L1 coefficients (irradiance-convolved, basis order 0, y, z, x).
struct ShL1 { c0: vec3f, cy: vec3f, cz: vec3f, cx: vec3f }
fn shL1(pi: u32) -> ShL1 {
  var v: array<f32, 16>;
  for (var q = 0u; q < 2u; q++) {
    let w = sh[pi * 4u + q];
    for (var j = 0u; j < 4u; j++) { let f = unpack2x16float(w[j]); v[q * 8u + j * 2u] = f.x; v[q * 8u + j * 2u + 1u] = f.y; }
  }
  return ShL1(vec3f(v[0], v[1], v[2]), vec3f(v[3], v[4], v[5]), vec3f(v[6], v[7], v[8]), vec3f(v[9], v[10], v[11]));
}
fn shAdd(a: ShL1, b: ShL1, w: f32) -> ShL1 { return ShL1(a.c0 + w * b.c0, a.cy + w * b.cy, a.cz + w * b.cz, a.cx + w * b.cx); }

// Voxel relocation leaves a probe on the side of the surface its grid point is on, so probes behind a wall
// (outside a room) would be interpolated into the room: the gather (pixel -> c0 probe) and the merge (probe ->
// upper probe) sample the segment every voxel of the lower end's trace level and skip it when it is hidden.
fn segOccluded(a: vec3f, b: vec3f, L: u32) -> bool {
  let d = b - a;
  let k = u32(min(ceil(length(d) / voxSize(L)), 16.0));
  for (var i = 0u; i < k; i++) {
    if (voxOcc(L, a + d * ((f32(i) + 0.5) / f32(k)))) { return true; }
  }
  return false;
}
// From the pixel, offset off c0 voxels along its normal.
fn probeOccluded(x: vec3f, n: vec3f, p: vec3f, s0: f32, off: f32) -> bool {
  let L = voxLevelFor(voxLevel(s0, 0u), x);
  return segOccluded(x + n * (off * voxSize(L)), p, L);
}

@compute @workgroup_size(8, 8) fn gatherWorld(@builtin(global_invocation_id) gid: vec3u) {
  if (gid.x >= u32(F.size.x) || gid.y >= u32(F.size.y)) { return; }
  let px = vec2i(gid.xy);
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { textureStore(irrOut, px, vec4f(0.0)); return; }
  let x = worldAt(px, d);
  let n = textureLoad(normalTex, px, 0).xyz;
  let lod = lodFor(distance(x, F.eye.xyz));
  let gp = x / spacing(lod, 0u);
  let b = vec3i(floor(gp)); let f = gp - vec3f(b);
  var e = vec3f(0.0); var ws = 0.0; var hidden = 0u; var ww: array<f32, 8>; var qq: array<u32, 8>;
  // S3: toon pixels also interpolate the L0 / L1 coefficients for the receiving-side operator.
  let tagA = textureLoad(albedoTex, px, 0).a;
  let toon = tagA > 0.75;
  var s1 = ShL1(vec3f(0.0), vec3f(0.0), vec3f(0.0), vec3f(0.0));
  for (var k = 0u; k < 8u; k++) {
    let o = corner(k);
    let q = lookup(0u, keyFor(b + o, lod, 0u));
    if (q == NONE) { continue; }
    let tw = select(1.0 - f, f, o == vec3i(1));
    let pr = probes[LY.c[0].probeOff + q];
    let dv = pr.pos.xyz - x;
    let side = dot(n, dv) / max(length(dv), 1e-5);
    let w = (tw.x * tw.y * tw.z + 1e-4) * ((side + 1.0) * (side + 1.0) * 0.25 + 0.02);
    if (LY.wp2.x == 2u && probeOccluded(x, n, pr.pos.xyz, pr.pos.w, 1.0)) { hidden |= 1u << k; ww[k] = w; qq[k] = q; continue; }
    e += w * evalSH(q, n); ws += w;
    if (toon) { s1 = shAdd(s1, shL1(q), w); }
  }
  // Every probe hidden (the offset start fell into a neighbouring face: concave corners, foliage): retest from two
  // voxels out. Probes still hidden are not used (the pixel stays black rather than leak).
  if (ws <= 0.0 && hidden != 0u) {
    for (var k = 0u; k < 8u; k++) {
      if ((hidden & (1u << k)) == 0u) { continue; }
      let pr = probes[LY.c[0].probeOff + qq[k]];
      if (probeOccluded(x, n, pr.pos.xyz, pr.pos.w, 2.0)) { continue; }
      e += ww[k] * evalSH(qq[k], n); ws += ww[k];
      if (toon) { s1 = shAdd(s1, shL1(qq[k]), ww[k]); }
    }
  }
  var outE = select(vec3f(0.0), e / ws, ws > 0.0);
  // Alpha: 1 photoreal; toon 2 + ramp band (0 / 1) + 2 when the directional part is at least 10% of the ambient;
  // photoreal objects flagged for measurement 2.
  var alpha = 1.0;
  if (toon && ws > 0.0) {
    let iw = 1.0 / ws;
    let r = toonReceive(s1.c0 * iw, s1.cy * iw, s1.cz * iw, s1.cx * iw, n, F.style.z);
    if (F.style.y > 0.5) { outE = r.e; }
    alpha = 2.0 + r.band + select(0.0, 2.0, r.contrast >= 0.1);
  } else if (toon || tagA > 0.25) { alpha = 2.0; }
  textureStore(irrOut, px, vec4f(outE, alpha));
}

@compute @workgroup_size(8, 8) fn gatherScreen(@builtin(global_invocation_id) gid: vec3u) {
  if (gid.x >= u32(F.size.x) || gid.y >= u32(F.size.y)) { return; }
  let px = vec2i(gid.xy);
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { textureStore(irrOut, px, vec4f(0.0)); return; }
  let L = LY.c[0];
  let x = worldAt(px, d);
  let n = textureLoad(normalTex, px, 0).xyz;
  let z = viewZ(x);
  let uc = (vec2f(px) + 0.5) / f32(L.tileSize) - 0.5;
  let b = vec2i(floor(uc)); let f = uc - vec2f(b);
  var e = vec3f(0.0); var ws = 0.0;
  for (var k = 0u; k < 4u; k++) {
    let o = vec2i(i32(k & 1u), i32(k >> 1u));
    let q = clamp(b + o, vec2i(0), vec2i(i32(L.tilesX) - 1, i32(L.tilesY) - 1));
    let qi = u32(q.y) * L.tilesX + u32(q.x);
    let pr = probes[L.probeOff + qi];
    if (pr.pos.w <= 0.0) { continue; }
    let fw = select(1.0 - f, f, o == vec2i(1));
    let rel = abs(pr.nrm.w - z) / z;
    let nd = max(dot(n, pr.nrm.xyz), 0.0);
    let w = (fw.x * fw.y + 1e-4) * (exp(-20.0 * rel) + 1e-4) * (nd * nd * nd * nd + 1e-3);
    e += w * evalSH(qi, n); ws += w;
  }
  textureStore(irrOut, px, vec4f(select(vec3f(0.0), e / ws, ws > 0.0), 1.0));
}
`;

const ARGS_WGSL = /* wgsl */ `
struct CascL { hashOff: u32, hashMask: u32, probeOff: u32, cap: u32, radOff: u32, accOff: u32, res: u32, tileSize: u32,
               tilesX: u32, tilesY: u32, b0: f32, b1: f32 }
struct Layout { hdr: vec4u, c: array<CascL, 8>, wp: vec4f, wu: vec4u }
@group(0) @binding(0) var<uniform> LY: Layout;
@group(0) @binding(1) var<storage, read> counts: array<u32>;
@group(0) @binding(2) var<storage, read_write> args: array<u32>;
@group(1) @binding(0) var<uniform> CI: vec4u;
fn setArgs(o: u32, g: u32) {
  let x = min(g, 65535u);
  args[o] = x; args[o + 1u] = select(0u, (g + x - 1u) / max(x, 1u), x > 0u); args[o + 2u] = 1u;
}
@compute @workgroup_size(1) fn writeArgs() {
  let c = CI.x;
  let n = min(counts[c], LY.c[c].cap);
  let r = LY.c[c].res;
  setArgs(c * 8u, (n + 63u) / 64u);
  setArgs(c * 8u + 3u, (n * r * r + 63u) / 64u);
}
`;

function nextPow2(n: number) { return 1 << Math.ceil(Math.log2(Math.max(n, 1))); }

export interface Rc {
  irr: GPUTexture;
  params: RcParams;
  /** Bytes of GPU resources created for GI (allocated, not a measured peak). */
  bytes: number;
  /** Bytes actually used by the probes of the last frame read with readCounts. */
  usedBytes(counts: Uint32Array): number;
  encode(enc: GPUCommandEncoder, tw: (pass: number) => GPUComputePassTimestampWrites | undefined): void;
  readCounts(): Promise<Uint32Array>;
  /** Tracer statistics for the following frames (0 off, 1 DDA steps, 2 also voxel / triangle visibility). */
  setStats(level: number): void;
  destroy(): void;
}

export const RC_PASSES = ['giBuild', 'giTrace', 'giMerge', 'giGather'] as const;

export function createRc(device: GPUDevice, g: GBuffer, lit: GPUTexture, frame: GPUBuffer, params: RcParams, world: WorldResources): Rc {
  const { width, height } = g;
  const N = params.cascades;
  if (N > 8) throw new Error('at most 8 cascades');
  const screen = params.method === 'screen', split = params.method === 'split';
  const casc: { hashOff: number; hashSize: number; probeOff: number; cap: number; radOff: number; accOff: number; res: number;
    tileSize: number; tilesX: number; tilesY: number; b0: number; b1: number }[] = [];
  let hashTotal = 0, probeTotal = 0, radTotal = 0, accTotal = 0;
  for (let i = 0; i < N; i++) {
    const res = 4 << Math.min(i, params.resCap);
    const tileSize = params.P << i, tilesX = Math.ceil(width / tileSize), tilesY = Math.ceil(height / tileSize);
    const cap = screen ? tilesX * tilesY : params.caps[i];
    const hashSize = screen ? 0 : nextPow2(cap * 2);
    const b = (k: number) => params.kInterval * (4 ** k - 1) / 3;
    casc.push({ hashOff: hashTotal, hashSize, probeOff: probeTotal, cap, radOff: radTotal, accOff: accTotal, res, tileSize, tilesX, tilesY, b0: b(i), b1: b(i + 1) });
    hashTotal += hashSize; probeTotal += cap; radTotal += cap * res * res; accTotal += split ? cap * res * res * 5 : 0;
  }

  if (params.world === 'voxel' && !world.hasVox) throw new Error('voxel tracer without a voxel world');
  if ((params.world === 'tri' || params.stats > 1) && !world.hasBvh) throw new Error('triangle tracer without a BVH');
  const layout = new ArrayBuffer(16 + 8 * 48 + 48);
  const lu = new Uint32Array(layout), lf = new Float32Array(layout);
  lu.set([N, hashTotal, accTotal, 0], 0);
  casc.forEach((c, i) => {
    const o = 4 + i * 12;
    lu.set([c.hashOff, Math.max(c.hashSize - 1, 0), c.probeOff, c.cap, c.radOff, c.accOff, c.res, c.tileSize, c.tilesX, c.tilesY], o);
    lf[o + 10] = c.b0; lf[o + 11] = c.b1;
  });
  lf.set([params.voxScale, params.voxOffset, params.levelMap, params.voxSkip], 4 + 8 * 12);
  if (params.relocate === 'voxel' && !world.hasVox) throw new Error('voxel relocation without a voxel world');
  lu.set([{ gbuffer: 0, none: 1, voxel: 2 }[params.relocate], 0, 0, 0], 12 + 8 * 12);
  lu.set([{ none: 0, voxel: 1, tri: 2 }[params.world], params.world === 'none' ? N : Math.min(params.depthCascades, N), params.stats, world.hasBvh ? 1 : 0], 8 + 8 * 12);
  const layoutBuf = device.createBuffer({ label: 'rc.layout', size: layout.byteLength, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  device.queue.writeBuffer(layoutBuf, 0, layout);
  const ci = casc.map((_, i) => {
    const b = device.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    device.queue.writeBuffer(b, 0, new Uint32Array([i, 0, 0, 0]));
    return b;
  });

  const S = GPUBufferUsage.STORAGE;
  const buf = (label: string, size: number, extra = 0) => device.createBuffer({ label, size: Math.max(16, Math.ceil(size / 16) * 16), usage: S | extra });
  const keys = buf('rc.keys', hashTotal * 4);
  const slotProbe = buf('rc.slotProbe', hashTotal * 4);
  const probes = buf('rc.probes', probeTotal * 48);
  const rad = buf('rc.rad', radTotal * 8);
  const sh = buf('rc.sh', casc[0].cap * 64);
  const counts = buf('rc.counts', 72 * 4, GPUBufferUsage.COPY_SRC);
  const accum = buf('rc.accum', accTotal * 4);
  const parents = buf('rc.parents', screen ? 0 : probeTotal * 8 * 4);
  const args = buf('rc.args', 8 * 8 * 4, GPUBufferUsage.INDIRECT);
  const irr = device.createTexture({ label: 'rc.irr', size: [width, height], format: 'rgba16float',
    usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_SRC });
  const all = [layoutBuf, ...ci, keys, slotProbe, probes, rad, sh, counts, accum, parents, args];
  const bytes = all.reduce((s, b) => s + b.size, 0) + width * height * 8;

  const C = GPUShaderStage.COMPUTE;
  const bgl0 = device.createBindGroupLayout({ entries: [
    { binding: 0, visibility: C, buffer: { type: 'uniform' } },
    { binding: 1, visibility: C, buffer: { type: 'uniform' } },
    { binding: 2, visibility: C, texture: { sampleType: 'depth' } },
    { binding: 3, visibility: C, texture: { sampleType: 'unfilterable-float' } },
    { binding: 4, visibility: C, texture: { sampleType: 'unfilterable-float' } },
    { binding: 5, visibility: C, storageTexture: { access: 'write-only', format: 'rgba16float' } },
    { binding: 6, visibility: C, texture: { sampleType: 'unfilterable-float' } },
  ] });
  const bgl1 = device.createBindGroupLayout({ entries: [{ binding: 0, visibility: C, buffer: { type: 'uniform' } }] });
  const bgl2 = device.createBindGroupLayout({ entries: Array.from({ length: 8 }, (_, i) => ({ binding: i, visibility: C, buffer: { type: 'storage' as const } })) });
  const RO = (binding: number) => ({ binding, visibility: C, buffer: { type: 'read-only-storage' as const } });
  const bgl3 = device.createBindGroupLayout({ entries: [
    { binding: 0, visibility: C, buffer: { type: 'uniform' } }, RO(1), RO(2), RO(3), RO(4),
    { binding: 5, visibility: C, texture: { viewDimension: '2d-array' } }, { binding: 6, visibility: C, sampler: {} },
    { binding: 7, visibility: C, texture: { sampleType: 'depth' } }, { binding: 8, visibility: C, sampler: { type: 'comparison' } }, RO(9), RO(10),
  ] });
  const module = device.createShaderModule({ code: RC_WGSL, label: 'rc' });
  const pl = device.createPipelineLayout({ bindGroupLayouts: [bgl0, bgl1, bgl2, bgl3] });
  const pipe = (entryPoint: string) => device.createComputePipeline({ label: entryPoint, layout: pl, compute: { module, entryPoint } });
  const P = Object.fromEntries(['clearKeys', 'clearAccum', 'registerPixels', 'registerUp', 'compact', 'linkParents', 'setupScreen', 'trace', 'deposit',
    'resolve', 'mergeWorld', 'mergeScreen', 'projectSH', 'gatherWorld', 'gatherScreen'].map((e) => [e, pipe(e)]));
  const argsModule = device.createShaderModule({ code: ARGS_WGSL, label: 'rc.args' });
  const argsPipe = device.createComputePipeline({ label: 'writeArgs', layout: 'auto', compute: { module: argsModule, entryPoint: 'writeArgs' } });

  const bg0 = device.createBindGroup({ layout: bgl0, entries: [
    { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: { buffer: layoutBuf } },
    { binding: 2, resource: g.depth.createView() }, { binding: 3, resource: g.normal.createView() },
    { binding: 4, resource: lit.createView() }, { binding: 5, resource: irr.createView() },
    { binding: 6, resource: g.albedo.createView() },
  ] });
  const bg1 = ci.map((b) => device.createBindGroup({ layout: bgl1, entries: [{ binding: 0, resource: { buffer: b } }] }));
  const bg2 = device.createBindGroup({ layout: bgl2, entries: [keys, slotProbe, probes, rad, sh, counts, accum, parents].map((b, i) => ({ binding: i, resource: { buffer: b } })) });
  const bg3 = device.createBindGroup({ layout: bgl3, entries: [
    { binding: 0, resource: { buffer: world.voxUniform } }, { binding: 1, resource: { buffer: world.vox } },
    { binding: 2, resource: { buffer: world.bvhNodes } }, { binding: 3, resource: { buffer: world.bvhTris } },
    { binding: 4, resource: { buffer: world.materials } }, { binding: 5, resource: world.baseColor.createView({ dimension: '2d-array' }) },
    { binding: 6, resource: device.createSampler({ minFilter: 'linear', magFilter: 'linear', mipmapFilter: 'linear', addressModeU: 'repeat', addressModeV: 'repeat' }) },
    { binding: 7, resource: world.shadow.createView() }, { binding: 8, resource: device.createSampler({ compare: 'less-equal', minFilter: 'linear', magFilter: 'linear' }) },
    { binding: 9, resource: { buffer: world.dyn } }, { binding: 10, resource: { buffer: world.hr } },
  ] });
  const argsBG0 = device.createBindGroup({ layout: argsPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: layoutBuf } }, { binding: 1, resource: { buffer: counts } }, { binding: 2, resource: { buffer: args } },
  ] });
  const argsBG1 = ci.map((b) => device.createBindGroup({ layout: argsPipe.getBindGroupLayout(1), entries: [{ binding: 0, resource: { buffer: b } }] }));

  const linear = (pass: GPUComputePassEncoder, n: number) => {
    const groups = Math.ceil(n / 64), x = Math.min(groups, 65535);
    if (groups > 0) pass.dispatchWorkgroups(x, Math.ceil(groups / x));
  };
  const use = (pass: GPUComputePassEncoder, name: string, c: number) => {
    pass.setPipeline(P[name]); pass.setBindGroup(0, bg0); pass.setBindGroup(1, bg1[c]); pass.setBindGroup(2, bg2); pass.setBindGroup(3, bg3);
  };
  const writeArgs = (pass: GPUComputePassEncoder, c: number) => {
    pass.setPipeline(argsPipe); pass.setBindGroup(0, argsBG0); pass.setBindGroup(1, argsBG1[c]); pass.dispatchWorkgroups(1);
  };
  const probeArgs = (c: number) => c * 32;
  const slotArgs = (c: number) => c * 32 + 12;

  return {
    irr, params, bytes,
    usedBytes(cnt) {
      let b = hashTotal * 8 + 72 * 4 + 8 * 8 * 4;
      casc.forEach((c, i) => {
        const n = Math.min(cnt[i], c.cap);
        b += n * (screen ? 48 : 48 + 32) + n * c.res * c.res * 8 * (split ? 1 + 5 / 2 : 1);
      });
      return b + Math.min(cnt[0], casc[0].cap) * 64 + width * height * 8;
    },
    encode(enc, tw) {
      let pass = enc.beginComputePass({ label: 'giBuild', timestampWrites: tw(0) });
      use(pass, 'clearKeys', 0); linear(pass, Math.max(hashTotal, 72));
      if (screen) {
        for (let i = 0; i < N; i++) {
          use(pass, 'setupScreen', i); linear(pass, casc[i].tilesX * casc[i].tilesY);
          writeArgs(pass, i);
        }
      } else {
        use(pass, 'registerPixels', 0); linear(pass, Math.ceil(width / params.regStride) * Math.ceil(height / params.regStride));
        use(pass, 'compact', 0); linear(pass, casc[0].hashSize);
        writeArgs(pass, 0);
        for (let i = 1; i < N; i++) {
          use(pass, 'registerUp', i); pass.dispatchWorkgroupsIndirect(args, probeArgs(i - 1));
          use(pass, 'compact', i); linear(pass, casc[i].hashSize);
          writeArgs(pass, i);
          use(pass, 'linkParents', i - 1); pass.dispatchWorkgroupsIndirect(args, probeArgs(i - 1));
        }
      }
      pass.end();

      pass = enc.beginComputePass({ label: 'giTrace', timestampWrites: tw(1) });
      if (split) {
        use(pass, 'clearAccum', 0); linear(pass, accTotal);
        use(pass, 'deposit', 0); linear(pass, Math.ceil(width / params.rayStride) * Math.ceil(height / params.rayStride));
        for (let i = 0; i < N; i++) { use(pass, 'resolve', i); pass.dispatchWorkgroupsIndirect(args, slotArgs(i)); }
      } else {
        for (let i = 0; i < N; i++) { use(pass, 'trace', i); pass.dispatchWorkgroupsIndirect(args, slotArgs(i)); }
      }
      pass.end();

      pass = enc.beginComputePass({ label: 'giMerge', timestampWrites: tw(2) });
      for (let i = N - 1; i >= 0; i--) { use(pass, screen ? 'mergeScreen' : 'mergeWorld', i); pass.dispatchWorkgroupsIndirect(args, slotArgs(i)); }
      use(pass, 'projectSH', 0); pass.dispatchWorkgroupsIndirect(args, probeArgs(0));
      pass.end();

      pass = enc.beginComputePass({ label: 'giGather', timestampWrites: tw(3) });
      use(pass, screen ? 'gatherScreen' : 'gatherWorld', 0);
      pass.dispatchWorkgroups(Math.ceil(width / 8), Math.ceil(height / 8));
      pass.end();
    },
    async readCounts() {
      const read = device.createBuffer({ size: 72 * 4, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
      const enc = device.createCommandEncoder();
      enc.copyBufferToBuffer(counts, 0, read, 0, 72 * 4);
      device.queue.submit([enc.finish()]);
      await read.mapAsync(GPUMapMode.READ);
      const r = new Uint32Array(read.getMappedRange().slice(0));
      read.unmap(); read.destroy();
      return r;
    },
    setStats(level) { device.queue.writeBuffer(layoutBuf, (8 + 8 * 12 + 2) * 4, new Uint32Array([level])); },
    destroy() { for (const b of all) b.destroy(); irr.destroy(); },
  };
}
