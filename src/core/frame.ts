// Per-frame uniform shared by the lighting, radiance-cascade and post passes.
import { invert, lookAt, mul, normalize, perspectiveReversedInfinite, sub, type Mat4, type Vec3 } from './math.ts';

export const FRAME_WGSL = /* wgsl */ `
struct Frame {
  viewProj: mat4x4f, invViewProj: mat4x4f, prevViewProj: mat4x4f, prevInvViewProj: mat4x4f, lightViewProj: mat4x4f,
  eye: vec4f,     // xyz, near
  fwd: vec4f,     // camera forward
  sunDir: vec4f,  // towards the sun
  sunE: vec4f,    // sun irradiance (rgb)
  sky: vec4f,     // sky radiance (rgb), returned by rays that leave the last interval
  size: vec4f,    // w, h, 1/w, 1/h
  rc: vec4f,      // sMin (m), pixel angle (rad), P (pixels per c0 probe), unused
  rc2: vec4f,     // probe lift (x spacing), min thickness (m), screen march stride (px), exposure
  ru: vec4u,      // cascades, frame slot, registration stride, max steps per interval
  ru2: vec4u,     // ray stride (split), random seed, previous frame valid, analytic trace (placement test)
  omega0: array<vec4f, 4>, // solid angle of each c0 octahedral texel (4x4)
}
fn worldAt(px: vec2i, d: f32) -> vec3f {
  let ndc = vec2f((f32(px.x) + 0.5) * F.size.z * 2.0 - 1.0, 1.0 - (f32(px.y) + 0.5) * F.size.w * 2.0);
  let h = F.invViewProj * vec4f(ndc, d, 1.0);
  return h.xyz / h.w;
}
fn prevWorldAt(px: vec2i, d: f32) -> vec3f {
  let ndc = vec2f((f32(px.x) + 0.5) * F.size.z * 2.0 - 1.0, 1.0 - (f32(px.y) + 0.5) * F.size.w * 2.0);
  let h = F.prevInvViewProj * vec4f(ndc, d, 1.0);
  return h.xyz / h.w;
}
fn luminance(c: vec3f) -> f32 { return dot(c, vec3f(0.2126, 0.7152, 0.0722)); }
`;
export const FRAME_BYTES = 136 * 4;

export interface Camera { eye: Vec3; target: Vec3; fovYDeg: number; near: number; }

export function cameraMatrices(c: Camera, width: number, height: number) {
  const view = lookAt(c.eye, c.target, [0, 1, 0]);
  const proj = perspectiveReversedInfinite(c.fovYDeg * Math.PI / 180, width / height, c.near);
  const viewProj = mul(proj, view);
  return { view, viewProj, invViewProj: invert(viewProj), fwd: normalize(sub(c.target, c.eye)) };
}

export interface FrameParams {
  cam: Camera; prevCam: Camera; lightViewProj: Mat4; width: number; height: number;
  sunDir: Vec3; sunE: Vec3; sky: Vec3;
  sMin: number; P: number; lift: number; thicknessMin: number; pxStride: number; exposure: number;
  cascades: number; slot: number; regStride: number; maxSteps: number; rayStride: number; seed: number; prevValid: boolean; analytic: boolean;
  omega0: Float32Array;
}

export function packFrame(p: FrameParams): ArrayBuffer {
  const buf = new ArrayBuffer(FRAME_BYTES);
  const f = new Float32Array(buf), u = new Uint32Array(buf);
  const cur = cameraMatrices(p.cam, p.width, p.height), prev = cameraMatrices(p.prevCam, p.width, p.height);
  f.set(cur.viewProj, 0); f.set(cur.invViewProj, 16); f.set(prev.viewProj, 32); f.set(prev.invViewProj, 48); f.set(p.lightViewProj, 64);
  f.set([...p.cam.eye, p.cam.near], 80); f.set([...cur.fwd, 0], 84);
  f.set([...normalize(p.sunDir), 0], 88); f.set([...p.sunE, 0], 92); f.set([...p.sky, 0], 96);
  f.set([p.width, p.height, 1 / p.width, 1 / p.height], 100);
  const pixAng = 2 * Math.tan(p.cam.fovYDeg * Math.PI / 360) / p.height;
  f.set([p.sMin, pixAng, p.P, 0], 104);
  f.set([p.lift, p.thicknessMin, p.pxStride, p.exposure], 108);
  u.set([p.cascades, p.slot, p.regStride, p.maxSteps], 112);
  u.set([p.rayStride, p.seed, p.prevValid ? 1 : 0, p.analytic ? 1 : 0], 116);
  f.set(p.omega0, 120);
  return buf;
}

/** Octahedral encode, identical to the WGSL version. */
export function octEncode(n: Vec3): [number, number] {
  const s = Math.abs(n[0]) + Math.abs(n[1]) + Math.abs(n[2]);
  let x = n[0] / s, y = n[1] / s;
  if (n[2] < 0) { const ox = x, oy = y; x = (1 - Math.abs(oy)) * (ox >= 0 ? 1 : -1); y = (1 - Math.abs(ox)) * (oy >= 0 ? 1 : -1); }
  return [x * 0.5 + 0.5, y * 0.5 + 0.5];
}

/** Solid angle of each texel of a res x res octahedral map (Fibonacci-sphere count). */
export function octSolidAngles(res: number, samples = 1 << 20): Float32Array {
  const counts = new Float64Array(res * res);
  const golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < samples; i++) {
    const z = 1 - (2 * i + 1) / samples, r = Math.sqrt(1 - z * z), phi = golden * i;
    const [u, v] = octEncode([r * Math.cos(phi), r * Math.sin(phi), z]);
    counts[Math.min(res - 1, Math.floor(v * res)) * res + Math.min(res - 1, Math.floor(u * res))]++;
  }
  return new Float32Array(Array.from(counts, (c) => c / samples * 4 * Math.PI));
}
