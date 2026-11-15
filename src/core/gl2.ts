// Phase 33: the WebGL2 tier, measured natively. Only what WebGL2 has: render passes with fragment shaders that read
// textures and write colour targets (no compute, no storage buffers, no atomics, no voxels). The same shaders in GLSL
// run in a browser's WebGL2 (src/web/gl2.ts); this WGSL version plugs into the WebGPU runner (config gl2-..., rcrun.ts)
// so that it is measured with the same scenes, images and metrics as the WebGPU tier. Its inputs are the G-buffer and the
// direct light (lit), which WebGL2 rasterises as well, and a small G-buffer seen from the sun (the reflective shadow map,
// RSM) that this tier renders itself. Raster passes read the scene's material table (WebGL2: uniforms per draw).
//
// What it keeps and what it drops:
//  - Screen probes: one probe per T x T pixel tile, at the tile's centre pixel (world position and normal from the
//    G-buffer). Each probe traces D x D fixed directions over its normal's hemisphere (uniform in solid angle; the set is
//    turned per tile by a fixed hash, so it never changes from frame to frame) against a half-resolution depth buffer.
//    A hit returns the outgoing radiance seen there: the direct pass's radiance (which already holds the toon emission
//    operator); one bounce only (no light from the previous frame's indirect).
//  - Rays that leave the screen, go behind the camera or end without a hit (the light from off screen) return the sun's
//    first bounce from the RSM: every surface the sun sees, as patches of the RSM's mip chain gathered per probe on fixed
//    rings around the probe's position in the sun's view, into an L0 + L1 radiance SH that the missed directions read.
//    The RSM has no visibility between a patch and the probe (light through walls is only cut by the screen rays that
//    hit something), only the sun's first bounce, and the sky as the screen's sky fraction.
//  - Probe radiance -> L0 + L1 irradiance SH (cosine-convolved, the basis order of rc.ts), filtered over neighbouring
//    probes on the same plane; every pixel interpolates the 4 nearest probes with depth-plane and normal weights. Toon
//    pixels put the L0 / L1 part through the receiving-side operator (style.ts), as the WebGPU tier does.
//  - No random numbers; a short history on the filtered probe SH (weight 0.5 for the new frame, the WebGPU tier's c0
//    rule), reprojected to the previous frame's probes on the same plane, so a still scene converges to one image.
import { FRAME_WGSL } from './frame.ts';
import { createGBuffer, createGBufferRenderer, type GBuffer } from './gbuffer.ts';
import type { SceneData } from './gltf.ts';
import type { Lighting } from './lighting.ts';
import { invert, type Mat4 } from './math.ts';
import type { SceneGpu } from './scene_gpu.ts';
import { STYLE_WGSL } from './style.ts';
import { wgslUses } from './rc.ts';

export interface Gl2Params {
  /** Pixels per probe tile (both axes). */
  tile: number;
  /** Directions per probe: dirs x dirs over the hemisphere. */
  dirs: number;
  /** Depth-buffer samples per ray. */
  steps: number;
  /** Ray length (m). */
  length: number;
  /** Depth thickness: a sample behind the depth buffer by less than max(thick, thickRel x depth) is a hit (m). */
  thick: number;
  thickRel: number;
  /** Probe filter radius (probes): each probe's SH is the plane- and normal-weighted mean of its (2 r + 1)^2 neighbours. */
  filter: number;
  /** RSM resolution (texels per side, power of two; 0: no RSM, missed rays return 0 and the sky fraction). */
  rsm: number;
  /** RSM samples per ring (rings double in radius from 2 texels to half the map). */
  rsmRing: number;
  /** Short history on the filtered probe SH: weight of the new frame (0: none). The WebGPU tier's c0 uses 0.5. */
  history: number;
}
export const DEFAULT_GL2: Gl2Params = { tile: 8, dirs: 8, steps: 16, length: 8, thick: 0.3, thickRel: 0.05, filter: 2, rsm: 512, rsmRing: 24, history: 0.5 };

const ENV_FORMAT: GPUTextureFormat = 'rgba32float';

export function gl2Wgsl(p: Gl2Params) {
  const rsmLevels = p.rsm ? Math.log2(p.rsm) + 1 : 1; // RSM B (positions) is rgba16float: filterable everywhere
  const rings = p.rsm ? Math.log2(p.rsm) - 1 : 0; // radius 2 texels .. half the map
  return /* wgsl */ `
${FRAME_WGSL}
${STYLE_WGSL}
const PI = 3.14159265;
const T = ${p.tile}u;
const D = ${p.dirs}u;
const STEPS = ${p.steps}u;
const RAY_LEN = ${p.length.toFixed(4)};
const THICK = ${p.thick.toFixed(4)};
const THICK_REL = ${p.thickRel.toFixed(4)};
const FILTER = ${p.filter};
const HIST = ${p.history > 0};
const HIST_W = ${p.history > 0 ? p.history.toFixed(4) : '1.0'};
const RSM_ON = ${p.rsm > 0};
const RSM_RES = ${Math.max(p.rsm, 1)};
const RSM_LEVELS = ${rsmLevels};
const RINGS = ${rings};
const RING_N = ${p.rsmRing};
struct Rsm { lightVP: mat4x4f, invLightVP: mat4x4f, extent: vec4f } // extent.x: width of the sun's view (m)
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var depthTex: texture_depth_2d;
@group(0) @binding(2) var normalTex: texture_2d<f32>;
@group(0) @binding(3) var albedoTex: texture_2d<f32>;
@group(0) @binding(4) var litTex: texture_2d<f32>;
@group(0) @binding(5) var<uniform> R: Rsm;
@group(0) @binding(6) var linS: sampler;
@group(1) @binding(1) var halfZ: texture_2d<f32>;
@group(1) @binding(2) var envTex: texture_2d<f32>;
@group(1) @binding(3) var atlas: texture_2d<f32>;
@group(1) @binding(4) var shR: texture_2d<f32>;
@group(1) @binding(5) var shG: texture_2d<f32>;
@group(1) @binding(6) var shB: texture_2d<f32>;
@group(1) @binding(7) var fR: texture_2d<f32>;
@group(1) @binding(8) var fG: texture_2d<f32>;
@group(1) @binding(9) var fB: texture_2d<f32>;
@group(1) @binding(10) var rsR: texture_2d<f32>;
@group(1) @binding(11) var rsG: texture_2d<f32>;
@group(1) @binding(12) var rsB: texture_2d<f32>;
@group(1) @binding(13) var src: texture_2d<f32>;
@group(1) @binding(14) var hR: texture_2d<f32>;
@group(1) @binding(15) var hG: texture_2d<f32>;
@group(1) @binding(16) var hB: texture_2d<f32>;
@group(1) @binding(17) var hGeo: texture_2d<f32>;
@group(2) @binding(0) var rAlb: texture_2d<f32>;
@group(2) @binding(1) var rNrm: texture_2d<f32>;
@group(2) @binding(2) var rDepth: texture_depth_2d;
@group(2) @binding(3) var rA: texture_2d<f32>;
@group(2) @binding(4) var rB: texture_2d<f32>;
@group(2) @binding(5) var rC: texture_2d<f32>;
@group(2) @binding(6) var mA: texture_2d<f32>;
@group(2) @binding(7) var mB: texture_2d<f32>;
@group(2) @binding(8) var mC: texture_2d<f32>;

@vertex fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4f {
  let uv = vec2f(f32((i << 1u) & 2u), f32(i & 2u));
  return vec4f(uv * vec2f(2.0, -2.0) + vec2f(-1.0, 1.0), 0.0, 1.0);
}
fn hash32(x0: u32) -> u32 {
  var x = x0;
  x ^= x >> 16u; x *= 0x7feb352du; x ^= x >> 15u; x *= 0x846ca68bu; x ^= x >> 16u;
  return x;
}
fn screenSize() -> vec2i { return vec2i(F.size.xy); }
fn tiles() -> vec2u { return (vec2u(F.size.xy) + T - 1u) / T; }
fn probePixel(t: vec2u) -> vec2i { return min(vec2i(t * T + T / 2u), screenSize() - 1); }
// --- giBuild 1: half-resolution depth (nearest of 2 x 2, as the view distance) and the screen's sky fraction.
@fragment fn halfDepth(@builtin(position) p: vec4f) -> @location(0) vec4f {
  let q = vec2i(p.xy) * 2;
  var z = 1e30;
  for (var k = 0; k < 4; k++) {
    let d = textureLoad(depthTex, min(q + vec2i(k & 1, k >> 1), screenSize() - 1), 0);
    if (d > 0.0) { z = min(z, F.eye.w / d); }
  }
  return vec4f(z, 0.0, 0.0, 0.0);
}
// First reduction: 4 x 4 full-resolution pixels -> (sky pixels, 0, 0, pixels).
@fragment fn envFirst(@builtin(position) p: vec4f) -> @location(0) vec4f {
  let q = vec2i(p.xy) * 4;
  var s = vec4f(0.0);
  for (var k = 0; k < 16; k++) {
    let px = q + vec2i(k & 3, k >> 2);
    if (any(px >= screenSize())) { continue; }
    s += vec4f(select(0.0, 1.0, textureLoad(depthTex, px, 0) <= 0.0), 0.0, 0.0, 1.0);
  }
  return s;
}
// Further reductions: 4 x 4 texels of src -> one (sums).
@fragment fn envReduce(@builtin(position) p: vec4f) -> @location(0) vec4f {
  let q = vec2i(p.xy) * 4;
  let n = vec2i(textureDimensions(src));
  var s = vec4f(0.0);
  for (var k = 0; k < 16; k++) {
    let t = q + vec2i(k & 3, k >> 2);
    if (all(t < n)) { s += textureLoad(src, t, 0); }
  }
  return s;
}

// --- giBuild 2: the RSM. Shade the sun's G-buffer: A = (radiance per unit area across the sun, 1), B = (position, 1),
// C = (normal, 1); coverage-premultiplied so that the mip chain averages patches.
struct RsmOut { @location(0) a: vec4f, @location(1) b: vec4f, @location(2) c: vec4f }
@fragment fn rsmShade(@builtin(position) p: vec4f) -> RsmOut {
  let px = vec2i(p.xy);
  let d = textureLoad(rDepth, px, 0);
  if (d <= 0.0) { return RsmOut(vec4f(0.0), vec4f(0.0), vec4f(0.0)); }
  let ndc = vec2f((f32(px.x) + 0.5) / f32(RSM_RES) * 2.0 - 1.0, 1.0 - (f32(px.y) + 0.5) / f32(RSM_RES) * 2.0);
  let h = R.invLightVP * vec4f(ndc, d, 1.0);
  let n = textureLoad(rNrm, px, 0).xyz;
  let ab = textureLoad(rAlb, px, 0);
  let ndl = max(dot(n, F.sunDir.xyz), 0.0);
  // Seen from the sun, every texel is sunlit. Radiance / n.l: the patch's area is its texel's area / n.l.
  var l = ab.rgb / PI * F.sunE.rgb * ndl;
  if (ab.a > 0.75 && F.style.x > 0.5) { l = toonSun(ab.rgb, ndl, 1.0, F.sunE.rgb); }
  return RsmOut(vec4f(l / max(ndl, 0.1), 1.0), vec4f(h.xyz / h.w, 1.0), vec4f(n, 1.0));
}
// Mip level of A / B / C from the level above (mA / mB / mC): the mean of 2 x 2.
@fragment fn rsmMip(@builtin(position) p: vec4f) -> RsmOut {
  let q = vec2i(p.xy) * 2;
  var o = RsmOut(vec4f(0.0), vec4f(0.0), vec4f(0.0));
  for (var k = 0; k < 4; k++) {
    let t = q + vec2i(k & 1, k >> 1);
    o.a += 0.25 * textureLoad(mA, t, 0); o.b += 0.25 * textureLoad(mB, t, 0); o.c += 0.25 * textureLoad(mC, t, 0);
  }
  return o;
}
// Per probe: L0 + L1 radiance SH (not convolved) of the RSM's patches on rings around the probe in the sun's view.
// Ring k: radius 2^(k+1) texels (sample at 1.5 x), RING_N samples, read at the mip level whose texel covers a sample's area.
struct ShOut { @location(0) r: vec4f, @location(1) g: vec4f, @location(2) b: vec4f }
fn rsmPatch(xp: vec3f, np: vec3f, uv: vec2f, level: i32, areaUv: f32, s: ptr<function, array<vec3f, 4>>) {
  if (any(uv < vec2f(0.0)) || any(uv >= vec2f(1.0))) { return; }
  // Bilinear within the level: as the sun turns, the RSM's texels slide over the scene and a nearest read would jump.
  let lv = f32(level);
  let a = textureSampleLevel(rA, linS, uv, lv);
  if (a.a < 1e-3) { return; }
  let xv = textureSampleLevel(rB, linS, uv, lv).xyz / a.a;
  let nv = normalize(textureSampleLevel(rC, linS, uv, lv).xyz);
  let area = areaUv * R.extent.x * R.extent.x * a.a;
  let v = xv - xp;
  let r2 = dot(v, v);
  if (r2 < 1e-8) { return; }
  let w = v * inverseSqrt(r2);
  let cv = -dot(nv, w); let cp = dot(np, w);
  if (cv <= 0.0 || cp <= 0.0) { return; }
  let rad = a.rgb / a.a * min(area * cv / max(r2, area), 2.0 * PI);
  (*s)[0] += rad * 0.282095; (*s)[1] += rad * (0.488603 * w.y); (*s)[2] += rad * (0.488603 * w.z); (*s)[3] += rad * (0.488603 * w.x);
}
@fragment fn rsmGather(@builtin(position) p: vec4f) -> ShOut {
  let t = vec2u(p.xy);
  let px = probePixel(t);
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { return ShOut(vec4f(0.0), vec4f(0.0), vec4f(0.0)); }
  let xp = worldAt(px, d);
  let np = textureLoad(normalTex, px, 0).xyz;
  let lc = R.lightVP * vec4f(xp, 1.0);
  let uv0 = vec2f(lc.x * 0.5 + 0.5, 0.5 - lc.y * 0.5);
  var s: array<vec3f, 4>;
  let rho0 = 2.0 / f32(RSM_RES);
  rsmPatch(xp, np, uv0, 1, PI * rho0 * rho0, &s);
  for (var k = 0; k < RINGS; k++) {
    let rho = rho0 * exp2(f32(k));
    let areaUv = 3.0 * PI * rho * rho / f32(RING_N);
    let level = clamp(i32(round(0.5 * log2(areaUv * f32(RSM_RES * RSM_RES)))), 0, RSM_LEVELS - 1);
    for (var j = 0; j < RING_N; j++) {
      let ang = 2.0 * PI * (f32(j) + 0.5 * f32(k & 1)) / f32(RING_N);
      rsmPatch(xp, np, uv0 + 1.5 * rho * vec2f(cos(ang), sin(ang)), level, areaUv, &s);
    }
  }
  return ShOut(vec4f(s[0].r, s[1].r, s[2].r, s[3].r), vec4f(s[0].g, s[1].g, s[2].g, s[3].g), vec4f(s[0].b, s[1].b, s[2].b, s[3].b));
}

// --- giTrace: one fragment per (probe, direction) of the atlas.
fn basis(n: vec3f) -> mat3x3f {
  let s = select(-1.0, 1.0, n.z >= 0.0);
  let a = -1.0 / (s + n.z);
  let b = n.x * n.y * a;
  return mat3x3f(vec3f(1.0 + s * n.x * n.x * a, s * b, -s * n.x), vec3f(b, s + n.y * n.y * a, -n.y), n);
}
// Direction c of tile t's set around n: uniform in cos(theta) (equal solid angle 2 pi / D^2), turned by the tile's hash.
fn probeDir(t: vec2u, c: vec2u, n: vec3f) -> vec3f {
  let h = hash32((t.x * 0x9e3779b9u) ^ ((t.y + 0x632be5abu) * 0x85ebca6bu));
  let ct = (f32(c.x) + 0.5) / f32(D);
  let st = sqrt(max(1.0 - ct * ct, 0.0));
  let ph = 2.0 * PI * (f32(c.y) + f32(h & 0xffffu) / 65536.0) / f32(D);
  return normalize(basis(n) * vec3f(st * cos(ph), st * sin(ph), ct));
}
// Radiance of a missed ray: the RSM radiance SH of the probe along dir, and the sky by the screen's sky fraction.
fn missed(t: vec2u, dir: vec3f) -> vec3f {
  let e = textureLoad(envTex, vec2i(0), 0);
  var l = F.sky.rgb * (e.x / max(e.w, 1.0));
  if (RSM_ON) {
    let q = vec2i(t);
    let r = textureLoad(rsR, q, 0); let g = textureLoad(rsG, q, 0); let b = textureLoad(rsB, q, 0);
    let y = vec4f(0.282095, 0.488603 * dir.y, 0.488603 * dir.z, 0.488603 * dir.x);
    l += max(vec3f(dot(r, y), dot(g, y), dot(b, y)), vec3f(0.0));
  }
  return l;
}
fn march(t: vec2u, c: vec2u, x: vec3f, n: vec3f, dir: vec3f) -> vec3f {
  let dist = distance(x, F.eye.xyz);
  let o = x + n * (0.02 + 0.002 * dist);
  let hs = vec2i(textureDimensions(halfZ));
  let jit = f32(hash32((t.x * 1973u + t.y * 9277u + c.x * 26699u + c.y * 70607u) | 1u) & 0xffffu) / 65536.0;
  let c0 = F.viewProj * vec4f(x, 1.0);
  let h0 = vec2i(vec2f(c0.x / c0.w * 0.5 + 0.5, 0.5 - c0.y / c0.w * 0.5) * vec2f(hs));
  // A hit is a step from in front of the depth buffer to behind it (by less than the thickness), at least two
  // half-resolution pixels from the probe (its own surface, seen through the 2 x 2 nearest depth, is not a hit).
  var front = true;
  for (var k = 0u; k < STEPS; k++) {
    let q = (f32(k) + jit) / f32(STEPS);
    let pw = o + dir * (0.05 + (RAY_LEN - 0.05) * q * q);
    let cl = F.viewProj * vec4f(pw, 1.0);
    if (cl.w <= F.eye.w) { break; }
    let ndc = cl.xy / cl.w;
    if (any(abs(ndc) >= vec2f(1.0))) { break; }
    let uv = vec2f(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5);
    let hp = min(vec2i(uv * vec2f(hs)), hs - 1);
    if (max(abs(hp.x - h0.x), abs(hp.y - h0.y)) < 2) { continue; }
    let zs = textureLoad(halfZ, hp, 0).r;
    let dz = cl.w - zs;
    let wasFront = front;
    front = dz <= 0.01 * zs;
    if (wasFront && !front && dz < max(THICK, THICK_REL * zs)) {
      let px = min(vec2i(uv * F.size.xy), screenSize() - 1);
      let d = textureLoad(depthTex, px, 0);
      if (d > 0.0) { return textureLoad(litTex, px, 0).rgb; }
    }
  }
  return missed(t, dir);
}
@fragment fn trace(@builtin(position) p: vec4f) -> @location(0) vec4f {
  let a = vec2u(p.xy);
  let t = a / D; let c = a % D;
  let px = probePixel(t);
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { return vec4f(0.0); }
  let x = worldAt(px, d);
  let n = textureLoad(normalTex, px, 0).xyz;
  return vec4f(march(t, c, x, n, probeDir(t, c, n)), 1.0);
}

// --- giMerge: probe -> L0 + L1 irradiance SH, one target per colour channel (c0, cy, cz, cx).
@fragment fn projectSH(@builtin(position) p: vec4f) -> ShOut {
  let t = vec2u(p.xy);
  let px = probePixel(t);
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { return ShOut(vec4f(0.0), vec4f(0.0), vec4f(0.0)); }
  let n = textureLoad(normalTex, px, 0).xyz;
  var c0 = vec3f(0.0); var cy = vec3f(0.0); var cz = vec3f(0.0); var cx = vec3f(0.0);
  for (var j = 0u; j < D; j++) {
    for (var i = 0u; i < D; i++) {
      let l = textureLoad(atlas, vec2i(t * D + vec2u(i, j)), 0).rgb;
      let dir = probeDir(t, vec2u(i, j), n);
      c0 += l; cy += l * dir.y; cz += l * dir.z; cx += l * dir.x;
    }
  }
  // Solid angle per direction 2 pi / D^2; Y00 = 0.282095, Y1 = 0.488603 (y, z, x); cosine convolution pi, 2 pi / 3.
  let w = 2.0 * PI / f32(D * D);
  c0 *= w * 0.282095 * PI;
  let w1 = w * 0.488603 * 2.0 * PI / 3.0;
  cy *= w1; cz *= w1; cx *= w1;
  return ShOut(vec4f(c0.r, cy.r, cz.r, cx.r), vec4f(c0.g, cy.g, cz.g, cx.g), vec4f(c0.b, cy.b, cz.b, cx.b));
}
// Probe filter: the plane- and normal-weighted mean of the raw SH over (2 FILTER + 1)^2 probes.
struct FiltOut { @location(0) r: vec4f, @location(1) g: vec4f, @location(2) b: vec4f, @location(3) geo: vec4f }
@fragment fn filterSH(@builtin(position) p: vec4f) -> FiltOut {
  let t = vec2i(p.xy);
  let px = probePixel(vec2u(t));
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { return FiltOut(vec4f(0.0), vec4f(0.0), vec4f(0.0), vec4f(0.0)); }
  let x = worldAt(px, d);
  let n = textureLoad(normalTex, px, 0).xyz;
  let z = F.eye.w / d;
  let tn = vec2i(tiles());
  var r = vec4f(0.0); var g = vec4f(0.0); var b = vec4f(0.0); var ws = 0.0;
  for (var j = -FILTER; j <= FILTER; j++) {
    for (var i = -FILTER; i <= FILTER; i++) {
      let q = t + vec2i(i, j);
      if (any(q < vec2i(0)) || any(q >= tn)) { continue; }
      let pp = probePixel(vec2u(q));
      let dq = textureLoad(depthTex, pp, 0);
      if (dq <= 0.0) { continue; }
      let nq = textureLoad(normalTex, pp, 0).xyz;
      let xq = worldAt(pp, dq);
      let nd = max(dot(n, nq), 0.0);
      let w = exp(-40.0 * abs(dot(n, xq - x)) / z) * nd * nd * nd * nd;
      if (w < 1e-4) { continue; }
      r += w * textureLoad(shR, q, 0); g += w * textureLoad(shG, q, 0); b += w * textureLoad(shB, q, 0); ws += w;
    }
  }
  r /= ws; g /= ws; b /= ws;
  // Short history (the WebGPU tier's c0 rule, rc.ts): mix with the previous frame's SH at this probe's point (weight
  // HIST_W on the new frame), read from the previous probes around its reprojection that lie on the same plane. A probe
  // without such a previous probe (first frame, disocclusion) keeps the frame's own value.
  if (HIST && F.ru2.z == 1u) {
    let c = F.prevViewProj * vec4f(x, 1.0);
    if (c.w > 0.0) {
      // Probe tile coordinates of the reprojected point (a probe sits at the centre of pixel t T + T / 2: a still camera
      // reads its own probe with weight 1, so a still scene settles on the frame's value).
      let pu = (vec2f(c.x / c.w * 0.5 + 0.5, 0.5 - c.y / c.w * 0.5) * F.size.xy - 0.5 - f32(T / 2u)) / f32(T);
      // Snapped when within 1e-3 of a probe: the reprojection's rounding would otherwise mix a little of the neighbours
      // every frame, and the 16-bit history would never settle (static flicker).
      let pr = round(pu);
      let ps = select(pu, pr, abs(pu - pr) < vec2f(1e-3));
      let pb = vec2i(floor(ps)); let pf = ps - vec2f(pb);
      var hr = vec4f(0.0); var hg = vec4f(0.0); var hb = vec4f(0.0); var hw = 0.0;
      for (var k = 0; k < 4; k++) {
        let o = vec2i(k & 1, k >> 1);
        let q = pb + o;
        if (any(q < vec2i(0)) || any(q >= tn)) { continue; }
        let gq = textureLoad(hGeo, q, 0);
        if (gq.w <= 0.0) { continue; }
        let bw = select(1.0 - pf, pf, o == vec2i(1));
        let w = bw.x * bw.y * select(0.0, 1.0, abs(dot(n, gq.xyz - x)) < 0.02 * z);
        if (w <= 0.0) { continue; }
        hr += w * textureLoad(hR, q, 0); hg += w * textureLoad(hG, q, 0); hb += w * textureLoad(hB, q, 0); hw += w;
      }
      if (hw > 0.05) { r = mix(hr / hw, r, HIST_W); g = mix(hg / hw, g, HIST_W); b = mix(hb / hw, b, HIST_W); }
    }
  }
  return FiltOut(r, g, b, vec4f(x, 1.0));
}

// --- giGather: every pixel interpolates the 4 nearest probes (fR / fG / fB: filtered SH).
@fragment fn gather(@builtin(position) p: vec4f) -> @location(0) vec4f {
  let px = vec2i(p.xy);
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { return vec4f(0.0); }
  let x = worldAt(px, d);
  let n = textureLoad(normalTex, px, 0).xyz;
  let z = F.eye.w / d;
  let tn = vec2i(tiles());
  let uc = (vec2f(px) + 0.5) / f32(T) - 0.5;
  let b = vec2i(floor(uc)); let f = uc - vec2f(b);
  var s0 = vec3f(0.0); var sy = vec3f(0.0); var sz = vec3f(0.0); var sx = vec3f(0.0); var ws = 0.0;
  var best = -1.0; var bq = vec2i(-1);
  for (var k = 0; k < 4; k++) {
    let o = vec2i(k & 1, k >> 1);
    let q = clamp(b + o, vec2i(0), tn - 1);
    let pp = probePixel(vec2u(q));
    let dq = textureLoad(depthTex, pp, 0);
    if (dq <= 0.0) { continue; }
    let nq = textureLoad(normalTex, pp, 0).xyz;
    let xq = worldAt(pp, dq);
    let bw = select(1.0 - f, f, o == vec2i(1));
    let plane = abs(dot(nq, x - xq)) / z;
    let nd = max(dot(n, nq), 0.0);
    let geo = exp(-40.0 * plane) * nd * nd * nd * nd;
    if (geo > best) { best = geo; bq = q; }
    let w = (bw.x * bw.y + 1e-3) * geo;
    if (w < 1e-6) { continue; }
    let r = textureLoad(fR, q, 0); let g = textureLoad(fG, q, 0); let bl = textureLoad(fB, q, 0);
    s0 += w * vec3f(r.x, g.x, bl.x); sy += w * vec3f(r.y, g.y, bl.y); sz += w * vec3f(r.z, g.z, bl.z); sx += w * vec3f(r.w, g.w, bl.w);
    ws += w;
  }
  // No probe on this pixel's surface (thin objects, edges): the most similar of the four.
  if (ws <= 0.0 && bq.x >= 0) {
    let r = textureLoad(fR, bq, 0); let g = textureLoad(fG, bq, 0); let bl = textureLoad(fB, bq, 0);
    s0 = vec3f(r.x, g.x, bl.x); sy = vec3f(r.y, g.y, bl.y); sz = vec3f(r.z, g.z, bl.z); sx = vec3f(r.w, g.w, bl.w);
    ws = 1.0;
  }
  if (ws <= 0.0) { return vec4f(0.0, 0.0, 0.0, 1.0); }
  let iw = 1.0 / ws;
  s0 *= iw; sy *= iw; sz *= iw; sx *= iw;
  var e = max(0.282095 * s0 + 0.488603 * (sx * n.x + sy * n.y + sz * n.z), vec3f(0.0));
  // Alpha as rc.ts writes it: 1 photoreal; toon 2 + ramp band + 2 when the directional part is >= 10 % of the ambient;
  // photoreal objects flagged for measurement 2.
  let tagA = textureLoad(albedoTex, px, 0).a;
  var alpha = 1.0;
  if (tagA > 0.75) {
    let r = toonReceive(s0, sy, sz, sx, n, F.style.z);
    if (F.style.y > 0.5) { e = r.e; }
    alpha = 2.0 + r.band + select(0.0, 2.0, r.contrast >= 0.1);
  } else if (tagA > 0.25) { alpha = 2.0; }
  return vec4f(e, alpha);
}
`;
}

export interface Gl2 {
  irr: GPUTexture; bytes: number;
  usedBytes(counts: Uint32Array): number;
  encode(enc: GPUCommandEncoder, tw: (pass: number) => GPUComputePassTimestampWrites | undefined): void;
  readCounts(): Promise<Uint32Array>;
  setStats(level: number): void;
  destroy(): void;
}

/** The sun's view with reversed depth (the G-buffer pass clears to 0 and keeps the greater depth). */
export function reversedOrtho(m: Mat4): Mat4 {
  const o = new Float32Array(m);
  for (let c = 0; c < 4; c++) o[c * 4 + 2] = m[c * 4 + 3] - m[c * 4 + 2];
  return o;
}

const GROUPS: Record<string, [number, number]> = {
  F: [0, 0], depthTex: [0, 1], normalTex: [0, 2], albedoTex: [0, 3], litTex: [0, 4], R: [0, 5], linS: [0, 6],
  halfZ: [1, 1], envTex: [1, 2], atlas: [1, 3], shR: [1, 4], shG: [1, 5], shB: [1, 6], fR: [1, 7], fG: [1, 8], fB: [1, 9],
  rsR: [1, 10], rsG: [1, 11], rsB: [1, 12], src: [1, 13], hR: [1, 14], hG: [1, 15], hB: [1, 16], hGeo: [1, 17],
  rAlb: [2, 0], rNrm: [2, 1], rDepth: [2, 2], rA: [2, 3], rB: [2, 4], rC: [2, 5], mA: [2, 6], mB: [2, 7], mC: [2, 8],
};

export function createGl2(device: GPUDevice, g: GBuffer, lighting: Lighting, frame: GPUBuffer, scene: SceneData, gpu: SceneGpu, p: Gl2Params): Gl2 {
  const { width, height } = g;
  const tx = Math.ceil(width / p.tile), ty = Math.ceil(height / p.tile);
  const hw = Math.ceil(width / 2), hh = Math.ceil(height / 2);
  const RT = GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.TEXTURE_BINDING;
  const made: GPUTexture[] = [];
  let bytes = 0;
  const tex = (label: string, w: number, h: number, format: GPUTextureFormat, bpp: number, extra = 0, mips = 1) => {
    const t = device.createTexture({ label: `gl2.${label}`, size: [w, h], format, usage: RT | extra, mipLevelCount: mips });
    made.push(t);
    for (let m = 0; m < mips; m++) bytes += Math.max(w >> m, 1) * Math.max(h >> m, 1) * bpp;
    return t;
  };
  const irr = tex('irr', width, height, 'rgba16float', 8, GPUTextureUsage.COPY_SRC);
  const half = tex('halfZ', hw, hh, 'r32float', 4);
  const atlas = tex('atlas', tx * p.dirs, ty * p.dirs, 'rgba16float', 8);
  const sh = [0, 1, 2].map((c) => tex(`sh${c}`, tx, ty, 'rgba16float', 8));
  if (p.filter <= 0) throw new Error('gl2: the probe filter pass (filter > 0) is required (it also holds the history)');
  // Filtered SH and probe positions, two sets: this frame's and the previous frame's (history).
  const shF = [0, 1].map((k) => [0, 1, 2].map((c) => tex(`shF${k}.${c}`, tx, ty, 'rgba16float', 8)));
  const geo = [0, 1].map((k) => tex(`geo${k}`, tx, ty, 'rgba16float', 8)); // 4 targets of 8 bytes: WebGPU's default 32 bytes per sample
  const env: GPUTexture[] = [];
  for (let w = Math.ceil(width / 4), h = Math.ceil(height / 4); ; w = Math.ceil(w / 4), h = Math.ceil(h / 4)) {
    env.push(tex(`env${env.length}`, w, h, ENV_FORMAT, 16));
    if (w === 1 && h === 1) break;
  }
  // The RSM: a G-buffer seen from the sun (the scene's raster pass with the sun's matrix), its shading and mip chain,
  // and the per-probe radiance SH.
  const levels = p.rsm ? Math.log2(p.rsm) + 1 : 1;
  const rsmG = p.rsm ? createGBuffer(device, p.rsm, p.rsm) : null;
  if (rsmG) bytes += p.rsm * p.rsm * 16;
  const rsmRaster = p.rsm ? createGBufferRenderer(device, scene, gpu, null) : null;
  const rA = p.rsm ? tex('rsmA', p.rsm, p.rsm, 'rgba16float', 8, 0, levels) : half;
  const rB = p.rsm ? tex('rsmB', p.rsm, p.rsm, 'rgba16float', 8, 0, levels) : half;
  const rC = p.rsm ? tex('rsmC', p.rsm, p.rsm, 'rgba16float', 8, 0, levels) : half;
  const rs = p.rsm ? [0, 1, 2].map((c) => tex(`rsmSh${c}`, tx, ty, 'rgba16float', 8)) : [half, half, half];
  const rsmU = device.createBuffer({ label: 'gl2.rsm', size: 144, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });

  const code = gl2Wgsl(p);
  const module = device.createShaderModule({ label: 'gl2', code });
  const names = Object.keys(GROUPS);
  const view = (t: GPUTexture, level?: number) => t.createView(level === undefined ? {} : { baseMipLevel: level, mipLevelCount: 1 });
  // Pipelines with layouts made from the shader: each entry point binds only what it uses.
  const pipes = new Map<string, { pl: GPURenderPipeline; uses: Set<string> }>();
  const pipe = (entry: string, formats: GPUTextureFormat[]) => {
    let e = pipes.get(entry);
    if (!e) {
      const pl = device.createRenderPipeline({ label: `gl2.${entry}`, layout: 'auto', vertex: { module, entryPoint: 'vs' },
        fragment: { module, entryPoint: entry, targets: formats.map((format) => ({ format })) }, primitive: { topology: 'triangle-list' } });
      e = { pl, uses: wgslUses(code, [entry], names)[entry] };
      pipes.set(entry, e);
    }
    return e;
  };
  const common: Record<string, GPUBindingResource> = { F: { buffer: frame }, depthTex: view(g.depth), normalTex: view(g.normal), albedoTex: view(g.albedo),
    litTex: view(lighting.lit), R: { buffer: rsmU }, linS: device.createSampler({ minFilter: 'linear', magFilter: 'linear' }), halfZ: view(half), envTex: view(env[env.length - 1]), atlas: view(atlas),
    shR: view(sh[0]), shG: view(sh[1]), shB: view(sh[2]),
    rsR: view(rs[0]), rsG: view(rs[1]), rsB: view(rs[2]), rA: view(rA), rB: view(rB), rC: view(rC),
    ...(rsmG ? { rAlb: view(rsmG.albedo), rNrm: view(rsmG.normal), rDepth: view(rsmG.depth) } : {}) };
  interface Draw { pl: GPURenderPipeline; groups: GPUBindGroup[]; targets: GPUTextureView[] }
  const draw = (entry: string, targets: [GPUTexture, number?][], extra: Record<string, GPUBindingResource> = {}): Draw => {
    const { pl, uses } = pipe(entry, targets.map(([t]) => t.format));
    const res = { ...common, ...extra };
    const top = Math.max(...[...uses].map((n) => GROUPS[n][0]));
    const groups = Array.from({ length: top + 1 }, (_, gi) => device.createBindGroup({ layout: pl.getBindGroupLayout(gi),
      entries: [...uses].filter((n) => GROUPS[n][0] === gi).map((n) => ({ binding: GROUPS[n][1], resource: res[n] })) }));
    return { pl, groups, targets: targets.map(([t, l]) => view(t, l)) };
  };
  const D_half = draw('halfDepth', [[half]]);
  const D_env = env.map((e, i) => i === 0 ? draw('envFirst', [[e]]) : draw('envReduce', [[e]], { src: view(env[i - 1]) }));
  const D_rsm = p.rsm ? [draw('rsmShade', [[rA, 0], [rB, 0], [rC, 0]]),
    ...Array.from({ length: levels - 1 }, (_, m) => draw('rsmMip', [[rA, m + 1], [rB, m + 1], [rC, m + 1]], { mA: view(rA, m), mB: view(rB, m), mC: view(rC, m) })),
    draw('rsmGather', [[rs[0]], [rs[1]], [rs[2]]])] : [];
  const D_trace = draw('trace', [[atlas]]);
  const D_sh = draw('projectSH', sh.map((t) => [t] as [GPUTexture]));
  // Parity k writes set k and reads set 1 - k as the history.
  const D_filter = [0, 1].map((k) => draw('filterSH', [...shF[k].map((t) => [t] as [GPUTexture]), [geo[k]]],
    { hR: view(shF[1 - k][0]), hG: view(shF[1 - k][1]), hB: view(shF[1 - k][2]), hGeo: view(geo[1 - k]) }));
  const D_gather = [0, 1].map((k) => draw('gather', [[irr]], { fR: view(shF[k][0]), fG: view(shF[k][1]), fB: view(shF[k][2]) }));
  let par = 0;

  const run = (enc: GPUCommandEncoder, d: Draw, tws?: GPURenderPassTimestampWrites) => {
    const pass = enc.beginRenderPass({ label: `gl2.${d.pl.label}`, timestampWrites: tws,
      colorAttachments: d.targets.map((v) => ({ view: v, loadOp: 'clear' as const, storeOp: 'store' as const, clearValue: [0, 0, 0, 0] })) });
    pass.setPipeline(d.pl);
    d.groups.forEach((bg, i) => pass.setBindGroup(i, bg));
    pass.draw(3); pass.end();
  };
  // A slot's timestamps span its first pass's begin and its last pass's end.
  const span = (t: GPUComputePassTimestampWrites | undefined, first: boolean, last: boolean): GPURenderPassTimestampWrites | undefined => {
    const b = first ? t?.beginningOfPassWriteIndex : undefined, e = last ? t?.endOfPassWriteIndex : undefined;
    return t && (b !== undefined || e !== undefined) ? { querySet: t.querySet, beginningOfPassWriteIndex: b, endOfPassWriteIndex: e } : undefined;
  };
  const seq = (enc: GPUCommandEncoder, t: GPUComputePassTimestampWrites | undefined, ds: Draw[]) => ds.forEach((d, i) => run(enc, d, span(t, i === 0, i === ds.length - 1)));
  const zeros = new Uint32Array(80);

  return {
    irr, bytes,
    usedBytes: () => bytes,
    encode(enc, tw) {
      const t0 = tw(0);
      if (rsmG) {
        // The RSM's raster pass opens the first slot (it is part of this tier's cost).
        const lvp = reversedOrtho(lighting.lightViewProj);
        const u = new Float32Array(36);
        u.set(lvp, 0); u.set(invert(lvp), 16);
        u[32] = 2 / Math.hypot(lighting.lightViewProj[0], lighting.lightViewProj[4], lighting.lightViewProj[8]);
        device.queue.writeBuffer(rsmU, 0, u);
        const cam = new Float32Array(36);
        cam.set(lvp, 0);
        device.queue.writeBuffer(rsmRaster!.camera, 0, cam);
        rsmRaster!.encode(enc, rsmG, span(t0, true, false));
        seq(enc, t0 && { ...t0, beginningOfPassWriteIndex: undefined }, [D_half, ...D_env, ...D_rsm]);
      } else seq(enc, t0, [D_half, ...D_env]);
      seq(enc, tw(1), [D_trace]);
      par = 1 - par;
      seq(enc, tw(2), [D_sh, D_filter[par]]);
      seq(enc, tw(3), [D_gather[par]]);
    },
    readCounts: async () => zeros,
    setStats() { /* no tracer statistics */ },
    destroy() { for (const t of made) t.destroy(); rsmU.destroy(); if (rsmG) { rsmG.albedo.destroy(); rsmG.normal.destroy(); rsmG.depth.destroy(); } },
  };
}
