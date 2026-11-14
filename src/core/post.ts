// Display (tonemapped captures) and the band-boundary flicker metric.
//
// Flicker: for each pixel, find the same surface point in the previous frame (reprojection with the
// previous camera, nearest pixel, accepted when the world positions are within two pixel footprints and the
// normals agree). Count pixels whose quantised log-luminance band of the indirect irradiance changed.
// Fine bands are 1/4 stop, coarse bands 1 stop. A world-fixed smooth analytic field goes through the same
// reprojection as a control (it also depends on the shading normal, as irradiance does), so its rate is the
// floor that the measurement itself produces.
// S3: toon pixels (irradiance alpha >= 2, written by the gather; photoreal objects flagged for measurement too) are also counted on their own, with the change of
// their receiving ramp band (only where the directional part is visible in both frames) and, as a control, the
// change of a ramp band against a fixed world direction (what reprojection and normal maps produce alone).
// Dynamic stability: the fine band rate is also counted over static pixels only (not a dynamic object in either
// frame: irradiance alpha < 1.5 in both, which also drops the occluded / exposed pixels), and, on the static camera,
// the excess variation: per pixel and window of K frames (K = 8, 16, 32, aligned on the frame slot), with
// l = log2 of the indirect irradiance luminance (same clamp as the bands),
//   excess = sum_t |l_t - l_(t-1)| - |l_end - l_start|  (K - 1 differences, >= 0).
// A smooth one-way change gives 0; only back-and-forth jumps remain. A window is dropped for a pixel that is a
// dynamic object or invalid in any of its frames. Reported per frame (divided by K - 1), in stops. For K = 16 the same
// is also summed on the linear luminance E and divided by the sum of the window means of E (relative excess), as a
// check that dark pixels do not dominate the log2 value.
import { FRAME_WGSL } from './frame.ts';
import type { GBuffer } from './gbuffer.ts';

const DISPLAY_WGSL = /* wgsl */ `
${FRAME_WGSL}
const PI = 3.14159265;
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var albedoTex: texture_2d<f32>;
@group(0) @binding(2) var depthTex: texture_depth_2d;
@group(0) @binding(3) var litTex: texture_2d<f32>;
@group(0) @binding(4) var irrTex: texture_2d<f32>;
@group(0) @binding(5) var outTex: texture_storage_2d<rgba8unorm, write>;
@group(0) @binding(6) var<uniform> mode: vec4u;
fn aces(x: vec3f) -> vec3f { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), vec3f(0.0), vec3f(1.0)); }
fn toSrgb(c: vec3f) -> vec3f { return select(1.055 * pow(c, vec3f(1.0 / 2.4)) - 0.055, c * 12.92, c <= vec3f(0.0031308)); }
@compute @workgroup_size(8, 8) fn display(@builtin(global_invocation_id) gid: vec3u) {
  if (gid.x >= u32(F.size.x) || gid.y >= u32(F.size.y)) { return; }
  let px = vec2i(gid.xy);
  let d = textureLoad(depthTex, px, 0);
  let a = textureLoad(albedoTex, px, 0).rgb;
  let e = textureLoad(irrTex, px, 0).rgb;
  let lit = textureLoad(litTex, px, 0).rgb;
  var c = vec3f(0.0);
  if (d <= 0.0) { c = F.sky.rgb; }
  else if (mode.x == 0u) { c = lit + a / PI * e; }
  else if (mode.x == 1u) { c = 0.8 / PI * e; }
  else { c = lit; }
  textureStore(outTex, px, vec4f(toSrgb(aces(c * F.rc2.w)), 1.0));
}
`;

const FLICKER_WGSL = /* wgsl */ `
${FRAME_WGSL}
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var depthTex: texture_depth_2d;
@group(0) @binding(2) var normalTex: texture_2d<f32>;
@group(0) @binding(3) var irrTex: texture_2d<f32>;
@group(0) @binding(4) var depthPrev: texture_depth_2d;
@group(0) @binding(5) var normalPrev: texture_2d<f32>;
@group(0) @binding(6) var irrPrev: texture_2d<f32>;
@group(0) @binding(7) var<storage, read_write> counters: array<atomic<u32>>;
@group(0) @binding(8) var heat: texture_storage_2d<rgba8unorm, write>;
var<workgroup> wc: array<atomic<u32>, 16>;

// World-fixed smooth field with a cosine-like normal dependence, like irradiance.
fn control(x: vec3f, n: vec3f) -> f32 {
  return exp2(1.5 * sin(0.9 * x.x + 0.3) * sin(0.7 * x.y + 1.1) + sin(0.8 * x.z + 0.5)) * (0.7 + 0.2 * n.y + 0.1 * n.x);
}
fn lb(v: f32) -> f32 { return log2(max(v, 1e-3)); }

@compute @workgroup_size(8, 8) fn flicker(@builtin(global_invocation_id) gid: vec3u, @builtin(local_invocation_index) li: u32) {
  if (li < 16u) { atomicStore(&wc[li], 0u); }
  workgroupBarrier();
  var ok = gid.x < u32(F.size.x) && gid.y < u32(F.size.y) && F.ru2.z == 1u;
  let px = vec2i(gid.xy);
  var d = 0.0;
  if (ok) { d = textureLoad(depthTex, px, 0); ok = d > 0.0; }
  var x = vec3f(0.0); var q = vec2i(0);
  var hv = vec4f(0.0, 0.0, 0.0, 1.0);
  if (ok) {
    x = worldAt(px, d);
    let c = F.prevViewProj * vec4f(x, 1.0);
    ok = c.w > F.eye.w;
    if (ok) {
      let ndc = c.xy / c.w;
      ok = all(abs(ndc) < vec2f(1.0));
      q = vec2i(floor(vec2f(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5) * F.size.xy));
      q = clamp(q, vec2i(0), vec2i(F.size.xy) - 1);
    }
  }
  if (ok) {
    let dq = textureLoad(depthPrev, q, 0);
    ok = dq > 0.0;
    if (ok) {
      let xq = prevWorldAt(q, dq);
      let tol = 2.0 * distance(x, F.eye.xyz) * F.rc.y + 0.005;
      let n = textureLoad(normalTex, px, 0).xyz;
      let nq = textureLoad(normalPrev, q, 0).xyz;
      ok = distance(x, xq) < tol && dot(n, nq) > 0.9;
      if (ok) {
        let ir = textureLoad(irrTex, px, 0); let iq = textureLoad(irrPrev, q, 0);
        let e = lb(luminance(ir.rgb));
        let eq = lb(luminance(iq.rgb));
        let c0 = lb(control(x, n)); let c1 = lb(control(xq, nq));
        atomicAdd(&wc[0], 1u);
        hv = vec4f(0.25, 0.25, 0.25, 1.0);
        if (floor(e * 4.0) != floor(eq * 4.0)) { atomicAdd(&wc[1], 1u); hv = vec4f(1.0, 0.2, 0.1, 1.0); }
        if (floor(e) != floor(eq)) { atomicAdd(&wc[2], 1u); }
        if (floor(c0 * 4.0) != floor(c1 * 4.0)) { atomicAdd(&wc[3], 1u); }
        if (floor(c0) != floor(c1)) { atomicAdd(&wc[4], 1u); }
        atomicAdd(&wc[5], u32(min(abs(e - eq), 10.0) * 1000.0));
        atomicAdd(&wc[6], u32(min(abs(c0 - c1), 10.0) * 1000.0));
        if (ir.a > 1.5 && iq.a > 1.5) {
          atomicAdd(&wc[7], 1u);
          if (floor(e * 4.0) != floor(eq * 4.0)) { atomicAdd(&wc[8], 1u); hv = vec4f(1.0, 0.9, 0.1, 1.0); }
          if (floor(e) != floor(eq)) { atomicAdd(&wc[9], 1u); }
          if (ir.a > 3.5 && iq.a > 3.5) {
            atomicAdd(&wc[12], 1u);
            if (ir.a != iq.a) { atomicAdd(&wc[10], 1u); }
          }
          let k = normalize(vec3f(0.3, 0.8, 0.5));
          if ((dot(n, k) > 0.0) != (dot(nq, k) > 0.0)) { atomicAdd(&wc[11], 1u); }
          atomicAdd(&wc[13], u32(min(abs(e - eq), 10.0) * 1000.0));
        }
        if (ir.a < 1.5 && iq.a < 1.5) {
          atomicAdd(&wc[14], 1u);
          if (floor(e * 4.0) != floor(eq * 4.0)) { atomicAdd(&wc[15], 1u); }
        }
      }
    }
  }
  if (gid.x < u32(F.size.x) && gid.y < u32(F.size.y)) { textureStore(heat, px, hv); }
  workgroupBarrier();
  if (li < 16u) {
    let v = atomicLoad(&wc[li]);
    if (v > 0u) { atomicAdd(&counters[F.ru.y * 16u + li], v); }
  }
}
`;

// Excess variation, static camera only. State per pixel (EX_WORDS u32): l_prev, l_start[3], tv[3] (f32 bits),
// mask bits (window i masked: bit i; ever masked: bit 3), sum of the K = 16 window excesses (f32 bits),
// linear K = 16: E_prev, E_start, tv, sum of E.
export const EXCESS_K = [8, 16, 32] as const;
const EX_WORDS = 13;
// Counter words per frame: per K, [pixel windows, sum tv, sum excess] (EXCESS_SCALE units per stop), then linear
// K = 16 [sum excess, sum tv, sum of window means] (EXCESS_LIN_SCALE units per irradiance unit).
export const EXCESS_SLOT = 12;
export const EXCESS_SCALE = 64;
export const EXCESS_LIN_SCALE = 16;
const EXCESS_WGSL = /* wgsl */ `
${FRAME_WGSL}
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var depthTex: texture_depth_2d;
@group(0) @binding(2) var irrTex: texture_2d<f32>;
@group(0) @binding(3) var<storage, read_write> st: array<u32>;
@group(0) @binding(4) var<storage, read_write> counters: array<atomic<u32>>;
var<workgroup> wtv: array<vec3f, 64>;
var<workgroup> wex: array<vec3f, 64>;
var<workgroup> wn: array<atomic<u32>, 3>;
var<workgroup> wlin: array<vec3f, 64>;
const SCALE = ${EXCESS_SCALE}.0; // counter units per stop (overflows above ~33 stops per pixel and window at 1080p)
fn lb(v: f32) -> f32 { return log2(max(v, 1e-3)); }

@compute @workgroup_size(8, 8) fn excess(@builtin(global_invocation_id) gid: vec3u, @builtin(local_invocation_index) li: u32) {
  if (li < 3u) { atomicStore(&wn[li], 0u); }
  workgroupBarrier();
  let k = F.ru.y;
  var tv3 = vec3f(0.0); var ex3 = vec3f(0.0); var lin3 = vec3f(0.0);
  if (gid.x < u32(F.size.x) && gid.y < u32(F.size.y)) {
    let px = vec2i(gid.xy);
    let o = (gid.y * u32(F.size.x) + gid.x) * ${EX_WORDS}u;
    let ir = textureLoad(irrTex, px, 0);
    let bad = textureLoad(depthTex, px, 0) <= 0.0 || ir.a < 0.5 || ir.a > 1.5;
    let E = luminance(ir.rgb);
    let l = lb(E);
    let lPrev = bitcast<f32>(st[o]);
    let ePrev = bitcast<f32>(st[o + 9u]);
    var eStart = bitcast<f32>(st[o + 10u]); var eTv = bitcast<f32>(st[o + 11u]); var eSum = bitcast<f32>(st[o + 12u]);
    if (k % 16u == 0u) { eStart = E; eTv = 0.0; eSum = E; } else { eTv += abs(E - ePrev); eSum += E; }
    var mask = st[o + 7u];
    if (bad) { mask |= 8u; }
    var acc = bitcast<f32>(st[o + 8u]);
    for (var i = 0u; i < 3u; i++) {
      let K = 8u << i;
      var start = bitcast<f32>(st[o + 1u + i]);
      var tv = bitcast<f32>(st[o + 4u + i]);
      if (k % K == 0u) {
        start = l; tv = 0.0;
        mask = (mask & ~(1u << i)) | select(0u, 1u << i, bad);
      } else {
        tv += abs(l - lPrev);
        if (bad) { mask |= 1u << i; }
      }
      if (k % K == K - 1u && (mask & (1u << i)) == 0u) {
        let ex = max(tv - abs(l - start), 0.0);
        tv3[i] = tv; ex3[i] = ex;
        atomicAdd(&wn[i], 1u);
        if (i == 1u) { acc += ex; lin3 = vec3f(max(eTv - abs(E - eStart), 0.0), eTv, eSum / 16.0); }
      }
      st[o + 1u + i] = bitcast<u32>(start);
      st[o + 4u + i] = bitcast<u32>(tv);
    }
    st[o] = bitcast<u32>(l);
    st[o + 7u] = mask;
    st[o + 8u] = bitcast<u32>(acc);
    st[o + 9u] = bitcast<u32>(E); st[o + 10u] = bitcast<u32>(eStart); st[o + 11u] = bitcast<u32>(eTv); st[o + 12u] = bitcast<u32>(eSum);
  }
  wtv[li] = tv3; wex[li] = ex3; wlin[li] = lin3;
  workgroupBarrier();
  for (var s = 32u; s > 0u; s >>= 1u) {
    if (li < s) { wtv[li] += wtv[li + s]; wex[li] += wex[li + s]; wlin[li] += wlin[li + s]; }
    workgroupBarrier();
  }
  if (li < 3u) {
    let n = atomicLoad(&wn[li]);
    if (n > 0u) {
      let b = k * ${EXCESS_SLOT}u + li * 3u;
      atomicAdd(&counters[b], n);
      atomicAdd(&counters[b + 1u], u32(round(wtv[0][li] * SCALE)));
      atomicAdd(&counters[b + 2u], u32(round(wex[0][li] * SCALE)));
      if (li == 1u) {
        let c = k * ${EXCESS_SLOT}u + 9u;
        atomicAdd(&counters[c], u32(round(wlin[0].x * ${EXCESS_LIN_SCALE}.0)));
        atomicAdd(&counters[c + 1u], u32(round(wlin[0].y * ${EXCESS_LIN_SCALE}.0)));
        atomicAdd(&counters[c + 2u], u32(round(wlin[0].z * ${EXCESS_LIN_SCALE}.0)));
      }
    }
  }
}

`;

// Excess variation along reprojected chains (moving camera; also run on the static camera, where it equals the K = 16
// excess above). Each pixel pulls its window state from the previous frame's state at its reprojected pixel (the
// flicker test: nearest pixel, world positions within two pixel footprints, normals agree); a window (K = 16, aligned
// on the frame slot) restarts the state. A window is dropped for a chain that failed the reprojection, was invalid or
// a dynamic object in any of its frames. The world-fixed control field goes through the same chains (its excess is the
// floor from chains drifting by up to half a pixel per frame and from normal maps). State (MX_WORDS u32 per pixel,
// ping-pong): l_prev, l_start, tv, c_prev, c_start, c_tv, E_prev, E_start, E_tv, E_sum, bad (f32 bits but the last).
// Counter words per frame (MEXCESS_SLOT): pixel windows, sum tv, sum excess, control tv, control excess (EXCESS_SCALE
// units per stop), linear excess, linear tv, sum of window means (EXCESS_LIN_SCALE units).
const MX_WORDS = 11;
export const MEXCESS_SLOT = 8;
const MEXCESS_WGSL = /* wgsl */ `
${FRAME_WGSL}
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var depthTex: texture_depth_2d;
@group(0) @binding(2) var normalTex: texture_2d<f32>;
@group(0) @binding(3) var irrTex: texture_2d<f32>;
@group(0) @binding(4) var depthPrev: texture_depth_2d;
@group(0) @binding(5) var normalPrev: texture_2d<f32>;
@group(0) @binding(6) var<storage, read> stPrev: array<u32>;
@group(0) @binding(7) var<storage, read_write> st: array<u32>;
@group(0) @binding(8) var<storage, read_write> counters: array<atomic<u32>>;
@group(0) @binding(9) var heat: texture_storage_2d<rgba8unorm, write>;
var<workgroup> wa: array<vec4f, 64>;
var<workgroup> wb: array<vec4f, 64>;
var<workgroup> wn: atomic<u32>;
const SCALE = ${EXCESS_SCALE}.0;
fn control(x: vec3f, n: vec3f) -> f32 {
  return exp2(1.5 * sin(0.9 * x.x + 0.3) * sin(0.7 * x.y + 1.1) + sin(0.8 * x.z + 0.5)) * (0.7 + 0.2 * n.y + 0.1 * n.x);
}
fn lb(v: f32) -> f32 { return log2(max(v, 1e-3)); }
fn heatColor(t: f32) -> vec3f {
  let red = vec3f(1.0, 0.1, 0.05); let yellow = vec3f(1.0, 0.9, 0.1);
  return select(select(mix(yellow, vec3f(1.0), 3.0 * t - 2.0), mix(red, yellow, 3.0 * t - 1.0), t < 2.0 / 3.0),
    mix(vec3f(0.25), red, 3.0 * t), t < 1.0 / 3.0);
}

@compute @workgroup_size(8, 8) fn mexcess(@builtin(global_invocation_id) gid: vec3u, @builtin(local_invocation_index) li: u32) {
  if (li == 0u) { atomicStore(&wn, 0u); }
  workgroupBarrier();
  let k = F.ru.y;
  let start = k % 16u == 0u;
  let last = k % 16u == 15u;
  var a = vec4f(0.0); var b = vec4f(0.0);
  let inside = gid.x < u32(F.size.x) && gid.y < u32(F.size.y);
  if (inside) {
    let px = vec2i(gid.xy);
    let o = (gid.y * u32(F.size.x) + gid.x) * ${MX_WORDS}u;
    let d = textureLoad(depthTex, px, 0);
    let ir = textureLoad(irrTex, px, 0);
    var bad = d <= 0.0 || ir.a < 0.5 || ir.a > 1.5;
    var x = vec3f(0.0); var n = vec3f(0.0, 1.0, 0.0);
    if (d > 0.0) { x = worldAt(px, d); n = textureLoad(normalTex, px, 0).xyz; }
    let l = lb(luminance(ir.rgb)); let E = luminance(ir.rgb); let c = lb(control(x, n));
    var s: array<f32, 10>;
    var sbad = 0u;
    if (start) {
      s = array<f32, 10>(l, l, 0.0, c, c, 0.0, E, E, 0.0, E);
    } else {
      // Pull the chain from the previous frame.
      var q = vec2i(0); var ok = !bad && F.ru2.z == 1u;
      if (ok) {
        let cp = F.prevViewProj * vec4f(x, 1.0);
        ok = cp.w > F.eye.w;
        if (ok) {
          let ndc = cp.xy / cp.w;
          ok = all(abs(ndc) < vec2f(1.0));
          q = clamp(vec2i(floor(vec2f(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5) * F.size.xy)), vec2i(0), vec2i(F.size.xy) - 1);
        }
      }
      if (ok) {
        let dq = textureLoad(depthPrev, q, 0);
        ok = dq > 0.0;
        if (ok) {
          let xq = prevWorldAt(q, dq);
          let tol = 2.0 * distance(x, F.eye.xyz) * F.rc.y + 0.005;
          ok = distance(x, xq) < tol && dot(n, textureLoad(normalPrev, q, 0).xyz) > 0.9;
        }
      }
      let oq = (u32(q.y) * u32(F.size.x) + u32(q.x)) * ${MX_WORDS}u;
      if (ok) {
        for (var i = 0u; i < 10u; i++) { s[i] = bitcast<f32>(stPrev[oq + i]); }
        sbad = stPrev[oq + 10u];
      } else { sbad = 1u; }
      s[2] += abs(l - s[0]); s[0] = l;
      s[5] += abs(c - s[3]); s[3] = c;
      s[8] += abs(E - s[6]); s[6] = E; s[9] += E;
    }
    if (bad) { sbad = 1u; }
    for (var i = 0u; i < 10u; i++) { st[o + i] = bitcast<u32>(s[i]); }
    st[o + 10u] = sbad;
    if (last) {
      var hc = vec3f(0.0);
      if (sbad == 0u) {
        let ex = max(s[2] - abs(l - s[1]), 0.0);
        a = vec4f(s[2], ex, s[5], max(s[5] - abs(c - s[4]), 0.0));
        b = vec4f(max(s[8] - abs(E - s[7]), 0.0), s[8], s[9] / 16.0, 0.0);
        atomicAdd(&wn, 1u);
        hc = heatColor(clamp(ex / 15.0 / 0.1, 0.0, 1.0));
      }
      textureStore(heat, px, vec4f(hc, 1.0));
    }
  }
  wa[li] = a; wb[li] = b;
  workgroupBarrier();
  for (var s2 = 32u; s2 > 0u; s2 >>= 1u) {
    if (li < s2) { wa[li] += wa[li + s2]; wb[li] += wb[li + s2]; }
    workgroupBarrier();
  }
  if (li == 0u) {
    let nw = atomicLoad(&wn);
    if (nw > 0u) {
      let c0 = k * ${MEXCESS_SLOT}u;
      atomicAdd(&counters[c0], nw);
      for (var i = 0u; i < 4u; i++) { atomicAdd(&counters[c0 + 1u + i], u32(round(wa[0][i] * SCALE))); }
      for (var i = 0u; i < 3u; i++) { atomicAdd(&counters[c0 + 5u + i], u32(round(wb[0][i] * ${EXCESS_LIN_SCALE}.0))); }
    }
  }
}
`;

// Map of the mean K = 16 excess per frame: 0 grey, 0.1 stop per frame and above white through red and yellow
// (black: a dynamic object or invalid at some point of the run).
const EXCESS_MAP_WGSL = /* wgsl */ `
@group(0) @binding(0) var<storage, read> st: array<u32>;
@group(0) @binding(1) var heat: texture_storage_2d<rgba8unorm, write>;
@group(0) @binding(2) var<uniform> m: vec4f; // width, 1 / (windows * 15), 0, 0
@compute @workgroup_size(8, 8) fn exmap(@builtin(global_invocation_id) gid: vec3u) {
  let size = textureDimensions(heat);
  if (gid.x >= size.x || gid.y >= size.y) { return; }
  let o = (gid.y * size.x + gid.x) * ${EX_WORDS}u;
  var c = vec3f(0.0);
  if ((st[o + 7u] & 8u) == 0u) {
    let t = clamp(bitcast<f32>(st[o + 8u]) * m.y / 0.1, 0.0, 1.0);
    let red = vec3f(1.0, 0.1, 0.05); let yellow = vec3f(1.0, 0.9, 0.1);
    c = select(select(mix(yellow, vec3f(1.0), 3.0 * t - 2.0), mix(red, yellow, 3.0 * t - 1.0), t < 2.0 / 3.0),
      mix(vec3f(0.25), red, 3.0 * t), t < 1.0 / 3.0);
  }
  textureStore(heat, gid.xy, vec4f(c, 1.0));
}
`;

export const FLICKER_FIELDS = ['valid', 'giFine', 'giCoarse', 'ctrlFine', 'ctrlCoarse', 'giAbsDlog2Milli', 'ctrlAbsDlog2Milli',
  'toonValid', 'toonFine', 'toonCoarse', 'toonRampChange', 'ctrlRampChange', 'toonSignificant', 'toonAbsDlog2Milli', 'staticValid', 'staticFine'] as const;
export const FLICKER_SLOT = 16; // counter words per frame

export function createPost(device: GPUDevice, g: GBuffer, frame: GPUBuffer, lit: GPUTexture, irr: GPUTexture, maxSlots: number) {
  const { width, height } = g;
  const out = device.createTexture({ label: 'display', size: [width, height], format: 'rgba8unorm',
    usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.COPY_SRC });
  const dm = device.createShaderModule({ code: DISPLAY_WGSL, label: 'display' });
  const displayPipe = device.createComputePipeline({ layout: 'auto', compute: { module: dm, entryPoint: 'display' } });
  const displayBG = [0, 1, 2].map((m) => {
    const b = device.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    device.queue.writeBuffer(b, 0, new Uint32Array([m, 0, 0, 0]));
    return device.createBindGroup({ layout: displayPipe.getBindGroupLayout(0), entries: [
      { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: g.albedo.createView() },
      { binding: 2, resource: g.depth.createView() }, { binding: 3, resource: lit.createView() },
      { binding: 4, resource: irr.createView() }, { binding: 5, resource: out.createView() }, { binding: 6, resource: { buffer: b } },
    ] });
  });

  const usage = GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST;
  const depthPrev = device.createTexture({ size: [width, height], format: 'depth32float', usage });
  const normalPrev = device.createTexture({ size: [width, height], format: g.normal.format, usage });
  const irrPrev = device.createTexture({ size: [width, height], format: irr.format, usage });
  const heat = device.createTexture({ label: 'flicker.heat', size: [width, height], format: 'rgba8unorm',
    usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.COPY_SRC });
  const counters = device.createBuffer({ size: maxSlots * FLICKER_SLOT * 4, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST });
  const fm = device.createShaderModule({ code: FLICKER_WGSL, label: 'flicker' });
  const flickerPipe = device.createComputePipeline({ layout: 'auto', compute: { module: fm, entryPoint: 'flicker' } });
  const flickerBG = device.createBindGroup({ layout: flickerPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: g.depth.createView() },
    { binding: 2, resource: g.normal.createView() }, { binding: 3, resource: irr.createView() },
    { binding: 4, resource: depthPrev.createView() }, { binding: 5, resource: normalPrev.createView() },
    { binding: 6, resource: irrPrev.createView() }, { binding: 7, resource: { buffer: counters } },
    { binding: 8, resource: heat.createView() },
  ] });

  const exState = device.createBuffer({ label: 'excess.state', size: width * height * EX_WORDS * 4, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
  const exCounters = device.createBuffer({ label: 'excess.counters', size: maxSlots * EXCESS_SLOT * 4,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST });
  const em = device.createShaderModule({ code: EXCESS_WGSL, label: 'excess' });
  const excessPipe = device.createComputePipeline({ layout: 'auto', compute: { module: em, entryPoint: 'excess' } });
  const excessBG = device.createBindGroup({ layout: excessPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: g.depth.createView() },
    { binding: 2, resource: irr.createView() }, { binding: 3, resource: { buffer: exState } }, { binding: 4, resource: { buffer: exCounters } },
  ] });
  const xm = device.createShaderModule({ code: EXCESS_MAP_WGSL, label: 'excess.map' });
  const mapPipe = device.createComputePipeline({ layout: 'auto', compute: { module: xm, entryPoint: 'exmap' } });
  const mapUniform = device.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  const mapBG = device.createBindGroup({ layout: mapPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: exState } }, { binding: 1, resource: heat.createView() }, { binding: 2, resource: { buffer: mapUniform } },
  ] });

  const mxState = [0, 1].map((i) => device.createBuffer({ label: `mexcess.state${i}`, size: width * height * MX_WORDS * 4, usage: GPUBufferUsage.STORAGE }));
  const mxCounters = device.createBuffer({ label: 'mexcess.counters', size: maxSlots * MEXCESS_SLOT * 4,
    usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST });
  const mxHeat = device.createTexture({ label: 'mexcess.heat', size: [width, height], format: 'rgba8unorm',
    usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.COPY_SRC });
  const mxm = device.createShaderModule({ code: MEXCESS_WGSL, label: 'mexcess' });
  const mxPipe = device.createComputePipeline({ layout: 'auto', compute: { module: mxm, entryPoint: 'mexcess' } });
  const mxBG = [0, 1].map((i) => device.createBindGroup({ layout: mxPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: g.depth.createView() },
    { binding: 2, resource: g.normal.createView() }, { binding: 3, resource: irr.createView() },
    { binding: 4, resource: depthPrev.createView() }, { binding: 5, resource: normalPrev.createView() },
    { binding: 6, resource: { buffer: mxState[1 - i] } }, { binding: 7, resource: { buffer: mxState[i] } },
    { binding: 8, resource: { buffer: mxCounters } }, { binding: 9, resource: mxHeat.createView() },
  ] }));
  let mxParity = 0;

  const readU32 = async (src: GPUBuffer, bytes: number) => {
    const read = device.createBuffer({ size: bytes, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
    const enc = device.createCommandEncoder();
    enc.copyBufferToBuffer(src, 0, read, 0, bytes);
    device.queue.submit([enc.finish()]);
    await read.mapAsync(GPUMapMode.READ);
    const r = new Uint32Array(read.getMappedRange().slice(0));
    read.unmap(); read.destroy();
    return r;
  };

  return {
    counters,
    /** Excess variation of this frame (static camera only; the frame slot sets the windows). */
    encodeExcess(enc: GPUCommandEncoder) {
      const pass = enc.beginComputePass({ label: 'excess' });
      pass.setPipeline(excessPipe); pass.setBindGroup(0, excessBG);
      pass.dispatchWorkgroups(Math.ceil(width / 8), Math.ceil(height / 8));
      pass.end();
    },
    readExcess: (slots: number) => readU32(exCounters, slots * EXCESS_SLOT * 4),
    /** Excess variation along reprojected chains (before encodeFlicker, which replaces the previous frame). */
    encodeChainExcess(enc: GPUCommandEncoder) {
      const pass = enc.beginComputePass({ label: 'mexcess' });
      pass.setPipeline(mxPipe); pass.setBindGroup(0, mxBG[mxParity]);
      pass.dispatchWorkgroups(Math.ceil(width / 8), Math.ceil(height / 8));
      pass.end();
      mxParity = 1 - mxParity;
    },
    readChainExcess: (slots: number) => readU32(mxCounters, slots * MEXCESS_SLOT * 4),
    /** Writes the excess map (mean K = 16 excess per frame over `windows` windows) into the heatmap texture. */
    encodeExcessMap(windows: number) {
      device.queue.writeBuffer(mapUniform, 0, new Float32Array([width, 1 / Math.max(windows * 15, 1), 0, 0]));
      const enc = device.createCommandEncoder();
      const pass = enc.beginComputePass({ label: 'excess.map' });
      pass.setPipeline(mapPipe); pass.setBindGroup(0, mapBG);
      pass.dispatchWorkgroups(Math.ceil(width / 8), Math.ceil(height / 8));
      pass.end();
      device.queue.submit([enc.finish()]);
    },
    /** Measures against the previous frame (if the frame uniform says it is valid), then keeps this frame. */
    encodeFlicker(enc: GPUCommandEncoder) {
      const pass = enc.beginComputePass({ label: 'flicker' });
      pass.setPipeline(flickerPipe); pass.setBindGroup(0, flickerBG);
      pass.dispatchWorkgroups(Math.ceil(width / 8), Math.ceil(height / 8));
      pass.end();
      enc.copyTextureToTexture({ texture: g.depth }, { texture: depthPrev }, [width, height]);
      enc.copyTextureToTexture({ texture: g.normal }, { texture: normalPrev }, [width, height]);
      enc.copyTextureToTexture({ texture: irr }, { texture: irrPrev }, [width, height]);
    },
    readCounters: (slots: number) => readU32(counters, slots * FLICKER_SLOT * 4),
    clearCounters() {
      device.queue.writeBuffer(counters, 0, new Uint8Array(maxSlots * FLICKER_SLOT * 4));
      device.queue.writeBuffer(exCounters, 0, new Uint8Array(maxSlots * EXCESS_SLOT * 4));
      device.queue.writeBuffer(mxCounters, 0, new Uint8Array(maxSlots * MEXCESS_SLOT * 4));
      const enc = device.createCommandEncoder();
      enc.clearBuffer(exState);
      device.queue.submit([enc.finish()]);
    },
    destroy() { for (const b of [counters, exState, exCounters, mapUniform, ...mxState, mxCounters]) b.destroy(); for (const t of [out, depthPrev, normalPrev, irrPrev, heat, mxHeat]) t.destroy(); },
    /** Mode 0: final (direct + indirect), 1: indirect irradiance on a 0.8 albedo, 2: direct only,
     * 3: flicker heatmap of the last measured frame (red: fine band changed, yellow: on a toon pixel, grey: valid),
     * or the excess map after encodeExcessMap; 4: the chain excess map of the last K = 16 window. Tightly packed RGBA8. */
    async capture(mode: number): Promise<Uint8Array> {
      const enc = device.createCommandEncoder();
      if (mode < 3) {
        const pass = enc.beginComputePass();
        pass.setPipeline(displayPipe); pass.setBindGroup(0, displayBG[mode]);
        pass.dispatchWorkgroups(Math.ceil(width / 8), Math.ceil(height / 8));
        pass.end();
      }
      const bytesPerRow = Math.ceil(width * 4 / 256) * 256;
      const readback = device.createBuffer({ size: bytesPerRow * height, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
      enc.copyTextureToBuffer({ texture: mode < 3 ? out : mode === 3 ? heat : mxHeat }, { buffer: readback, bytesPerRow }, [width, height]);
      device.queue.submit([enc.finish()]);
      await readback.mapAsync(GPUMapMode.READ);
      const src = new Uint8Array(readback.getMappedRange());
      const img = new Uint8Array(width * height * 4);
      for (let y = 0; y < height; y++) img.set(src.subarray(y * bytesPerRow, y * bytesPerRow + width * 4), y * width * 4);
      readback.unmap(); readback.destroy();
      return img;
    },
  };
}
