// S3: style operators at the two ends of the transport (H5). The transport itself (voxels, cascades, merge)
// stays linear and shared; a style only changes
//  - the emission side: what a surface injects into the field. A toon surface injects its sun light through a
//    banded ramp with a saturated albedo: L = sat(albedo) / pi * sunE * ramp(n.l * V). The same function shades
//    the visible toon pixels (direct pass) and the toon hits of the interval tracers (voxel and triangle), so the
//    field sees exactly what the camera sees. The reference renders the same function as an emitter.
//  - the receiving side: how a toon pixel maps the field to shading. From the interpolated L1 part of the c0
//    irradiance SH it takes an ambient colour (L0), a dominant direction (the luminance gradient of L1) and a
//    directional colour (L1 along that direction), and puts the direction through a two-band ramp as a virtual
//    key light: E = amb - dir + 2 dir * step(n . d). Photoreal pixels keep the physical SH irradiance.
// Material flag: bit 2 of Material.layers.w (scene_gpu.ts). G-buffer albedo.a and voxel albedo.a carry it.

/** Shared with the Mitsuba reference (written into scene.json by the export). */
export const TOON = { saturation: 1.6, t0: 0.05, t1: 0.3, mid: 0.5 } as const;

export const STYLE_WGSL = /* wgsl */ `
const TOON_SAT = ${TOON.saturation};
fn toonAlbedo(a: vec3f) -> vec3f {
  let l = dot(a, vec3f(0.2126, 0.7152, 0.0722));
  return clamp(vec3f(l) + TOON_SAT * (a - vec3f(l)), vec3f(0.0), vec3f(1.0));
}
// Banded sun term: 0 below t0, mid up to t1, 1 above.
fn toonRamp(x: f32) -> f32 { return select(select(0.0, ${TOON.mid}, x > ${TOON.t0}), 1.0, x > ${TOON.t1}); }
// Emission-side operator of a toon surface lit by the sun with n.l = ndl and visibility vis.
fn toonSun(alb: vec3f, ndl: f32, vis: f32, sunE: vec3f) -> vec3f { return toonAlbedo(alb) / 3.14159265 * sunE * toonRamp(ndl * vis); }

// Receiving-side operator. c0: L0 coefficient (irradiance-convolved), c1: L1 coefficients in basis order (y, z, x).
// soft: half width of the ramp in n.d (0: hard step). Returns (E, band) with band 0 (away from d) or 1.
struct ToonRecv { e: vec3f, band: f32, contrast: f32 }
fn toonReceive(c0: vec3f, c1y: vec3f, c1z: vec3f, c1x: vec3f, n: vec3f, soft: f32) -> ToonRecv {
  let amb = c0 * 0.282095;
  let w = vec3f(0.2126, 0.7152, 0.0722);
  let g = vec3f(dot(c1x, w), dot(c1y, w), dot(c1z, w));
  let gl = length(g);
  if (gl < 1e-6) { return ToonRecv(max(amb, vec3f(0.0)), 0.0, 0.0); }
  let d = g / gl;
  let dir = max(0.488603 * (c1x * d.x + c1y * d.y + c1z * d.z), vec3f(0.0));
  let x = dot(n, d);
  let r = select(select(0.0, 1.0, x > 0.0), smoothstep(-soft, soft, x), soft > 0.0);
  let e = max(amb - dir + 2.0 * dir * r, vec3f(0.0));
  return ToonRecv(e, select(0.0, 1.0, x > 0.0), dot(dir, w) / max(dot(amb, w), 1e-6));
}
`;
