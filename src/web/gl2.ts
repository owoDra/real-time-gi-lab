// Phase 33: the WebGL2 tier in a browser's WebGL2 (page web/gl2.html, driven by src/native/browser.ts --page gl2). The
// whole frame is WebGL2: the G-buffer, the shadow map, the direct light and the GI passes of src/core/gl2.ts translated
// to GLSL ES 3.00 pass for pass (same constants, same pixel indexing, same formats). Raster passes flip clip y (and the
// winding) and map clip z from [0, 1] to GL's [-1, 1], so every texture has WebGPU's row order and depth values.
// Measures the GI passes with EXT_disjoint_timer_query_webgl2 (one query per slot, as the native runner's four slots)
// and posts the final and indirect images and the irradiance (as --dump-irr) of the last frame of a static camera.
// URL parameters: scene, config (gl2-...), frames, warmup, exposure, nosky.
import jpeg from 'jpeg-js';
import type { SceneData } from '../core/gltf.ts';
import { DEFAULT_GL2, reversedOrtho, type Gl2Params } from '../core/gl2.ts';
import { sceneSunViewProj } from '../core/lighting.ts';
import { invert, type Mat4, type Vec3 } from '../core/math.ts';
import { cameraMatrices } from '../core/frame.ts';
import { posedVertices } from '../core/scenes.ts';
import { TEXTURE_SIZE } from '../core/scene_gpu.ts';
import { TOON } from '../core/style.ts';
import { SKY, SUN_E } from '../core/rcrun.ts';
import { parseConfig } from '../runner/configs.ts';
import { loadScene } from '../runner/scene.ts';
import { toTextureSize } from '../runner/texture.ts';
import { decodePng } from './png.ts';

const SPONZA = '/assets/glTF-Sample-Assets/Models/Sponza/glTF/';
const logEl = document.getElementById('log')!;
let chain: Promise<unknown> = Promise.resolve();
const post = (path: string, body: BodyInit) => { chain = chain.then(() => fetch(path, { method: 'POST', body })); };
const log = (s: string) => { logEl.textContent += s + '\n'; post('/log', s); };

// ---------------------------------------------------------------------------------------------------------------- GLSL
const HEAD = `#version 300 es
precision highp float; precision highp int; precision highp sampler2D; precision highp sampler2DArray; precision highp sampler2DShadow;
`;
const FRAME = `
uniform mat4 uVP, uInvVP, uPrevVP, uLightVP;
uniform vec4 uEye, uSunDir, uSunE, uSky, uSize, uStyle, uShadow, uExposure;
uniform int uPrevValid;
vec3 worldAt(ivec2 px, float d) {
  vec2 ndc = vec2((float(px.x) + 0.5) * uSize.z * 2.0 - 1.0, 1.0 - (float(px.y) + 0.5) * uSize.w * 2.0);
  vec4 h = uInvVP * vec4(ndc, d, 1.0);
  return h.xyz / h.w;
}
const float PI = 3.14159265;
vec3 toonAlbedo(vec3 a) { float l = dot(a, vec3(0.2126, 0.7152, 0.0722)); return clamp(vec3(l) + ${TOON.saturation.toFixed(4)} * (a - vec3(l)), vec3(0.0), vec3(1.0)); }
float toonRamp(float x) { return x > ${TOON.t1.toFixed(4)} ? 1.0 : (x > ${TOON.t0.toFixed(4)} ? ${TOON.mid.toFixed(4)} : 0.0); }
vec3 toonSun(vec3 alb, float ndl, float vis, vec3 sunE) { return toonAlbedo(alb) / PI * sunE * toonRamp(ndl * vis); }
`;
const FULL_VS = `${HEAD}void main() {
  vec2 uv = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  gl_Position = vec4(uv * vec2(2.0, -2.0) + vec2(-1.0, 1.0), 0.0, 1.0);
}`;
// G-buffer (also the RSM's raster pass): as src/core/gbuffer.ts, material from uniforms.
const GB_VS = `${HEAD}
uniform mat4 uVP;
layout(location = 0) in vec3 aPos; layout(location = 1) in vec3 aNrm; layout(location = 2) in vec2 aUv; layout(location = 3) in vec4 aTan;
out vec3 vNrm; out vec2 vUv; out vec4 vTan;
void main() {
  vec4 c = uVP * vec4(aPos, 1.0);
  gl_Position = vec4(c.x, -c.y, 2.0 * c.z - c.w, c.w);
  vNrm = aNrm; vUv = aUv; vTan = aTan;
}`;
const GB_FS = `${HEAD}
uniform sampler2DArray baseTex, normalTex, mrTex;
uniform vec4 uBaseFactor, uParams; uniform ivec4 uLayers;
uniform bool uGeoNormals;
in vec3 vNrm; in vec2 vUv; in vec4 vTan;
layout(location = 0) out vec4 oAlbedo; layout(location = 1) out vec4 oNormal;
void main() {
  vec4 base = texture(baseTex, vec3(vUv, float(uLayers.x))) * uBaseFactor;
  vec3 tn = texture(normalTex, vec3(vUv, float(uLayers.y))).xyz * 2.0 - 1.0;
  vec4 mr = texture(mrTex, vec3(vUv, float(uLayers.z)));
  if ((uLayers.w & 1) != 0 && base.a < uParams.z) discard;
  float flip = gl_FrontFacing ? 1.0 : -1.0;
  vec3 n = normalize(vNrm) * flip;
  float tl = length(vTan.xyz);
  if (tl > 1e-4 && !uGeoNormals) {
    vec3 t = normalize(vTan.xyz - n * dot(n, vTan.xyz));
    vec3 b = cross(n, t) * vTan.w * flip;
    n = normalize(t * tn.x + b * tn.y + n * tn.z);
  }
  oAlbedo = vec4(base.rgb, (uLayers.w & 4) != 0 ? 1.0 : ((uLayers.w & 8) != 0 ? 0.5 : 0.0));
  oNormal = vec4(n, mr.g * uParams.y);
}`;
const SHADOW_VS = `${HEAD}
uniform mat4 uVP;
layout(location = 0) in vec3 aPos; layout(location = 2) in vec2 aUv;
out vec2 vUv;
void main() { vec4 c = uVP * vec4(aPos, 1.0); gl_Position = vec4(c.x, -c.y, 2.0 * c.z - c.w, c.w); vUv = aUv; }`;
const SHADOW_FS = `${HEAD}
uniform sampler2DArray baseTex; uniform vec4 uBaseFactor, uParams; uniform ivec4 uLayers;
in vec2 vUv; out vec4 o;
void main() {
  if ((uLayers.w & 1) != 0 && textureLod(baseTex, vec3(vUv, float(uLayers.x)), 0.0).a * uBaseFactor.a < uParams.z) discard;
  o = vec4(0.0);
}`;
const DIRECT_FS = `${HEAD}${FRAME}
uniform sampler2D albedoTex, normalTex, depthTex; uniform sampler2DShadow shadowTex;
out vec4 o;
float sunVisibility(vec3 x) {
  vec4 c = uLightVP * vec4(x, 1.0);
  vec2 uv = c.xy * vec2(0.5, -0.5) + 0.5;
  if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) return 1.0;
  vec2 texel = 1.0 / vec2(textureSize(shadowTex, 0));
  float v = 0.0;
  for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) v += texture(shadowTex, vec3(uv + vec2(float(i), float(j)) * texel, c.z - uShadow.y));
  return v / 9.0;
}
void main() {
  ivec2 px = ivec2(gl_FragCoord.xy);
  float d = texelFetch(depthTex, px, 0).r;
  if (d <= 0.0) { o = vec4(0.0); return; }
  vec3 x = worldAt(px, d);
  vec3 n = texelFetch(normalTex, px, 0).xyz;
  vec4 ab = texelFetch(albedoTex, px, 0);
  float ndl = max(dot(n, uSunDir.xyz), 0.0);
  float vis = ndl > 0.0 ? sunVisibility(x + n * 0.03) : 0.0;
  vec3 l = ab.rgb / PI * uSunE.rgb * ndl * vis;
  if (ab.a > 0.75 && uStyle.x > 0.5) l = toonSun(ab.rgb, ndl, vis, uSunE.rgb);
  o = vec4(l, ndl * vis);
}`;
const DISPLAY_FS = `${HEAD}${FRAME}
uniform sampler2D albedoTex, depthTex, litTex, irrTex; uniform int uMode;
out vec4 o;
vec3 aces(vec3 x) { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), vec3(0.0), vec3(1.0)); }
vec3 toSrgb(vec3 c) { return mix(1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, c * 12.92, vec3(lessThanEqual(c, vec3(0.0031308)))); }
void main() {
  ivec2 px = ivec2(gl_FragCoord.xy);
  float d = texelFetch(depthTex, px, 0).r;
  vec3 a = texelFetch(albedoTex, px, 0).rgb, e = texelFetch(irrTex, px, 0).rgb, lit = texelFetch(litTex, px, 0).rgb;
  vec3 c = d <= 0.0 ? uSky.rgb : (uMode == 0 ? lit + a / PI * e : 0.8 / PI * e);
  o = vec4(toSrgb(aces(c * uExposure.x)), 1.0);
}`;

// The GI passes (src/core/gl2.ts gl2Wgsl), one fragment shader per entry point.
function giShaders(p: Gl2Params) {
  const levels = Math.log2(p.rsm) + 1, rings = Math.log2(p.rsm) - 1;
  const C = `${HEAD}${FRAME}
#define T ${p.tile}u
#define D ${p.dirs}u
#define STEPS ${p.steps}u
#define RAY_LEN ${p.length.toFixed(4)}
#define THICK ${p.thick.toFixed(4)}
#define THICK_REL ${p.thickRel.toFixed(4)}
#define FILTER ${p.filter}
#define HIST ${p.history > 0}
#define HIST_W ${p.history > 0 ? p.history.toFixed(4) : '1.0'}
#define RSM_RES ${p.rsm}
#define RSM_LEVELS ${levels}
#define RINGS ${rings}
#define RING_N ${p.rsmRing}
uniform mat4 uLvp, uInvLvp; uniform vec4 uExtent;
uint hash32(uint x) { x ^= x >> 16u; x *= 0x7feb352du; x ^= x >> 15u; x *= 0x846ca68bu; x ^= x >> 16u; return x; }
ivec2 screenSize() { return ivec2(uSize.xy); }
uvec2 tiles() { return (uvec2(uSize.xy) + T - 1u) / T; }
ivec2 probePixel(uvec2 t) { return min(ivec2(t * T + T / 2u), screenSize() - 1); }
mat3 basis(vec3 n) {
  float s = n.z >= 0.0 ? 1.0 : -1.0;
  float a = -1.0 / (s + n.z);
  float b = n.x * n.y * a;
  return mat3(vec3(1.0 + s * n.x * n.x * a, s * b, -s * n.x), vec3(b, s + n.y * n.y * a, -n.y), n);
}
vec3 probeDir(uvec2 t, uvec2 c, vec3 n) {
  uint h = hash32((t.x * 0x9e3779b9u) ^ ((t.y + 0x632be5abu) * 0x85ebca6bu));
  float ct = (float(c.x) + 0.5) / float(D);
  float st = sqrt(max(1.0 - ct * ct, 0.0));
  float ph = 2.0 * PI * (float(c.y) + float(h & 0xffffu) / 65536.0) / float(D);
  return normalize(basis(n) * vec3(st * cos(ph), st * sin(ph), ct));
}
`;
  return {
    halfDepth: `${C}uniform sampler2D depthTex; out vec4 o;
void main() {
  ivec2 q = ivec2(gl_FragCoord.xy) * 2; float z = 1e30;
  for (int k = 0; k < 4; k++) { float d = texelFetch(depthTex, min(q + ivec2(k & 1, k >> 1), screenSize() - 1), 0).r; if (d > 0.0) z = min(z, uEye.w / d); }
  o = vec4(z, 0.0, 0.0, 0.0);
}`,
    envFirst: `${C}uniform sampler2D depthTex; out vec4 o;
void main() {
  ivec2 q = ivec2(gl_FragCoord.xy) * 4; vec4 s = vec4(0.0);
  for (int k = 0; k < 16; k++) { ivec2 px = q + ivec2(k & 3, k >> 2); if (any(greaterThanEqual(px, screenSize()))) continue;
    s += vec4(texelFetch(depthTex, px, 0).r <= 0.0 ? 1.0 : 0.0, 0.0, 0.0, 1.0); }
  o = s;
}`,
    envReduce: `${C}uniform sampler2D src; out vec4 o;
void main() {
  ivec2 q = ivec2(gl_FragCoord.xy) * 4; ivec2 n = textureSize(src, 0); vec4 s = vec4(0.0);
  for (int k = 0; k < 16; k++) { ivec2 t = q + ivec2(k & 3, k >> 2); if (all(lessThan(t, n))) s += texelFetch(src, t, 0); }
  o = s;
}`,
    rsmShade: `${C}uniform sampler2D rAlb, rNrm, rDepth;
layout(location = 0) out vec4 oA; layout(location = 1) out vec4 oB; layout(location = 2) out vec4 oC;
void main() {
  ivec2 px = ivec2(gl_FragCoord.xy);
  float d = texelFetch(rDepth, px, 0).r;
  if (d <= 0.0) { oA = vec4(0.0); oB = vec4(0.0); oC = vec4(0.0); return; }
  vec2 ndc = vec2((float(px.x) + 0.5) / float(RSM_RES) * 2.0 - 1.0, 1.0 - (float(px.y) + 0.5) / float(RSM_RES) * 2.0);
  vec4 h = uInvLvp * vec4(ndc, d, 1.0);
  vec3 n = texelFetch(rNrm, px, 0).xyz; vec4 ab = texelFetch(rAlb, px, 0);
  float ndl = max(dot(n, uSunDir.xyz), 0.0);
  vec3 l = ab.rgb / PI * uSunE.rgb * ndl;
  if (ab.a > 0.75 && uStyle.x > 0.5) l = toonSun(ab.rgb, ndl, 1.0, uSunE.rgb);
  oA = vec4(l / max(ndl, 0.1), 1.0); oB = vec4(h.xyz / h.w, 1.0); oC = vec4(n, 1.0);
}`,
    rsmMip: `${C}uniform sampler2D mA, mB, mC;
layout(location = 0) out vec4 oA; layout(location = 1) out vec4 oB; layout(location = 2) out vec4 oC;
void main() {
  ivec2 q = ivec2(gl_FragCoord.xy) * 2; oA = vec4(0.0); oB = vec4(0.0); oC = vec4(0.0);
  for (int k = 0; k < 4; k++) { ivec2 t = q + ivec2(k & 1, k >> 1);
    oA += 0.25 * texelFetch(mA, t, 0); oB += 0.25 * texelFetch(mB, t, 0); oC += 0.25 * texelFetch(mC, t, 0); }
}`,
    rsmGather: `${C}uniform sampler2D depthTex, normalTex, rA, rB, rC;
layout(location = 0) out vec4 oR; layout(location = 1) out vec4 oG; layout(location = 2) out vec4 oB;
vec3 s[4];
void rsmPatch(vec3 xp, vec3 np, vec2 uv, int level, float areaUv) {
  if (any(lessThan(uv, vec2(0.0))) || any(greaterThanEqual(uv, vec2(1.0)))) return;
  float lv = float(level);
  vec4 a = textureLod(rA, uv, lv);
  if (a.a < 1e-3) return;
  vec3 xv = textureLod(rB, uv, lv).xyz / a.a;
  vec3 nv = normalize(textureLod(rC, uv, lv).xyz);
  float area = areaUv * uExtent.x * uExtent.x * a.a;
  vec3 v = xv - xp; float r2 = dot(v, v);
  if (r2 < 1e-8) return;
  vec3 w = v * inversesqrt(r2);
  float cv = -dot(nv, w), cp = dot(np, w);
  if (cv <= 0.0 || cp <= 0.0) return;
  vec3 rad = a.rgb / a.a * min(area * cv / max(r2, area), 2.0 * PI);
  s[0] += rad * 0.282095; s[1] += rad * (0.488603 * w.y); s[2] += rad * (0.488603 * w.z); s[3] += rad * (0.488603 * w.x);
}
void main() {
  uvec2 t = uvec2(gl_FragCoord.xy);
  ivec2 px = probePixel(t);
  float d = texelFetch(depthTex, px, 0).r;
  if (d <= 0.0) { oR = vec4(0.0); oG = vec4(0.0); oB = vec4(0.0); return; }
  vec3 xp = worldAt(px, d), np = texelFetch(normalTex, px, 0).xyz;
  vec4 lc = uLvp * vec4(xp, 1.0);
  vec2 uv0 = vec2(lc.x * 0.5 + 0.5, 0.5 - lc.y * 0.5);
  for (int i = 0; i < 4; i++) s[i] = vec3(0.0);
  float rho0 = 2.0 / float(RSM_RES);
  rsmPatch(xp, np, uv0, 1, PI * rho0 * rho0);
  for (int k = 0; k < RINGS; k++) {
    float rho = rho0 * exp2(float(k));
    float areaUv = 3.0 * PI * rho * rho / float(RING_N);
    int level = clamp(int(round(0.5 * log2(areaUv * float(RSM_RES * RSM_RES)))), 0, RSM_LEVELS - 1);
    for (int j = 0; j < RING_N; j++) {
      float ang = 2.0 * PI * (float(j) + 0.5 * float(k & 1)) / float(RING_N);
      rsmPatch(xp, np, uv0 + 1.5 * rho * vec2(cos(ang), sin(ang)), level, areaUv);
    }
  }
  oR = vec4(s[0].r, s[1].r, s[2].r, s[3].r); oG = vec4(s[0].g, s[1].g, s[2].g, s[3].g); oB = vec4(s[0].b, s[1].b, s[2].b, s[3].b);
}`,
    trace: `${C}uniform sampler2D depthTex, normalTex, litTex, halfZ, envTex, rsR, rsG, rsB; out vec4 o;
vec3 missed(uvec2 t, vec3 dir) {
  vec4 e = texelFetch(envTex, ivec2(0), 0);
  vec3 l = uSky.rgb * (e.x / max(e.w, 1.0));
  ivec2 q = ivec2(t);
  vec4 r = texelFetch(rsR, q, 0), g = texelFetch(rsG, q, 0), b = texelFetch(rsB, q, 0);
  vec4 y = vec4(0.282095, 0.488603 * dir.y, 0.488603 * dir.z, 0.488603 * dir.x);
  return l + max(vec3(dot(r, y), dot(g, y), dot(b, y)), vec3(0.0));
}
vec3 march(uvec2 t, uvec2 c, vec3 x, vec3 n, vec3 dir) {
  float dist = distance(x, uEye.xyz);
  vec3 o = x + n * (0.02 + 0.002 * dist);
  ivec2 hs = textureSize(halfZ, 0);
  float jit = float(hash32((t.x * 1973u + t.y * 9277u + c.x * 26699u + c.y * 70607u) | 1u) & 0xffffu) / 65536.0;
  vec4 c0 = uVP * vec4(x, 1.0);
  ivec2 h0 = ivec2(vec2(c0.x / c0.w * 0.5 + 0.5, 0.5 - c0.y / c0.w * 0.5) * vec2(hs));
  bool front = true;
  for (uint k = 0u; k < STEPS; k++) {
    float q = (float(k) + jit) / float(STEPS);
    vec3 pw = o + dir * (0.05 + (RAY_LEN - 0.05) * q * q);
    vec4 cl = uVP * vec4(pw, 1.0);
    if (cl.w <= uEye.w) break;
    vec2 ndc = cl.xy / cl.w;
    if (any(greaterThanEqual(abs(ndc), vec2(1.0)))) break;
    vec2 uv = vec2(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5);
    ivec2 hp = min(ivec2(uv * vec2(hs)), hs - 1);
    if (max(abs(hp.x - h0.x), abs(hp.y - h0.y)) < 2) continue;
    float zs = texelFetch(halfZ, hp, 0).r;
    float dz = cl.w - zs;
    bool wasFront = front;
    front = dz <= 0.01 * zs;
    if (wasFront && !front && dz < max(THICK, THICK_REL * zs)) {
      ivec2 px = min(ivec2(uv * uSize.xy), screenSize() - 1);
      float d = texelFetch(depthTex, px, 0).r;
      if (d > 0.0) return texelFetch(litTex, px, 0).rgb;
    }
  }
  return missed(t, dir);
}
void main() {
  uvec2 a = uvec2(gl_FragCoord.xy);
  uvec2 t = a / D, c = a % D;
  ivec2 px = probePixel(t);
  float d = texelFetch(depthTex, px, 0).r;
  if (d <= 0.0) { o = vec4(0.0); return; }
  vec3 x = worldAt(px, d), n = texelFetch(normalTex, px, 0).xyz;
  o = vec4(march(t, c, x, n, probeDir(t, c, n)), 1.0);
}`,
    projectSH: `${C}uniform sampler2D depthTex, normalTex, atlas;
layout(location = 0) out vec4 oR; layout(location = 1) out vec4 oG; layout(location = 2) out vec4 oB;
void main() {
  uvec2 t = uvec2(gl_FragCoord.xy);
  ivec2 px = probePixel(t);
  float d = texelFetch(depthTex, px, 0).r;
  if (d <= 0.0) { oR = vec4(0.0); oG = vec4(0.0); oB = vec4(0.0); return; }
  vec3 n = texelFetch(normalTex, px, 0).xyz;
  vec3 c0 = vec3(0.0), cy = vec3(0.0), cz = vec3(0.0), cx = vec3(0.0);
  for (uint j = 0u; j < D; j++) for (uint i = 0u; i < D; i++) {
    vec3 l = texelFetch(atlas, ivec2(t * D + uvec2(i, j)), 0).rgb;
    vec3 dir = probeDir(t, uvec2(i, j), n);
    c0 += l; cy += l * dir.y; cz += l * dir.z; cx += l * dir.x;
  }
  float w = 2.0 * PI / float(D * D);
  c0 *= w * 0.282095 * PI;
  float w1 = w * 0.488603 * 2.0 * PI / 3.0;
  cy *= w1; cz *= w1; cx *= w1;
  oR = vec4(c0.r, cy.r, cz.r, cx.r); oG = vec4(c0.g, cy.g, cz.g, cx.g); oB = vec4(c0.b, cy.b, cz.b, cx.b);
}`,
    filterSH: `${C}uniform sampler2D depthTex, normalTex, shR, shG, shB, hR, hG, hB, hGeo;
layout(location = 0) out vec4 oR; layout(location = 1) out vec4 oG; layout(location = 2) out vec4 oB; layout(location = 3) out vec4 oGeo;
void main() {
  ivec2 t = ivec2(gl_FragCoord.xy);
  ivec2 px = probePixel(uvec2(t));
  float d = texelFetch(depthTex, px, 0).r;
  if (d <= 0.0) { oR = vec4(0.0); oG = vec4(0.0); oB = vec4(0.0); oGeo = vec4(0.0); return; }
  vec3 x = worldAt(px, d), n = texelFetch(normalTex, px, 0).xyz;
  float z = uEye.w / d;
  ivec2 tn = ivec2(tiles());
  vec4 r = vec4(0.0), g = vec4(0.0), b = vec4(0.0); float ws = 0.0;
  for (int j = -FILTER; j <= FILTER; j++) for (int i = -FILTER; i <= FILTER; i++) {
    ivec2 q = t + ivec2(i, j);
    if (any(lessThan(q, ivec2(0))) || any(greaterThanEqual(q, tn))) continue;
    ivec2 pp = probePixel(uvec2(q));
    float dq = texelFetch(depthTex, pp, 0).r;
    if (dq <= 0.0) continue;
    vec3 nq = texelFetch(normalTex, pp, 0).xyz, xq = worldAt(pp, dq);
    float nd = max(dot(n, nq), 0.0);
    float w = exp(-40.0 * abs(dot(n, xq - x)) / z) * nd * nd * nd * nd;
    if (w < 1e-4) continue;
    r += w * texelFetch(shR, q, 0); g += w * texelFetch(shG, q, 0); b += w * texelFetch(shB, q, 0); ws += w;
  }
  r /= ws; g /= ws; b /= ws;
  if (HIST && uPrevValid == 1) {
    vec4 c = uPrevVP * vec4(x, 1.0);
    if (c.w > 0.0) {
      vec2 pu = (vec2(c.x / c.w * 0.5 + 0.5, 0.5 - c.y / c.w * 0.5) * uSize.xy - 0.5 - float(T / 2u)) / float(T);
      vec2 pr = round(pu);
      vec2 ps = mix(pu, pr, vec2(lessThan(abs(pu - pr), vec2(1e-3))));
      ivec2 pb = ivec2(floor(ps)); vec2 pf = ps - vec2(pb);
      vec4 hr = vec4(0.0), hg = vec4(0.0), hb = vec4(0.0); float hw = 0.0;
      for (int k = 0; k < 4; k++) {
        ivec2 o2 = ivec2(k & 1, k >> 1);
        ivec2 q = pb + o2;
        if (any(lessThan(q, ivec2(0))) || any(greaterThanEqual(q, tn))) continue;
        vec4 gq = texelFetch(hGeo, q, 0);
        if (gq.w <= 0.0) continue;
        vec2 bw = mix(1.0 - pf, pf, vec2(equal(o2, ivec2(1))));
        float w = bw.x * bw.y * (abs(dot(n, gq.xyz - x)) < 0.02 * z ? 1.0 : 0.0);
        if (w <= 0.0) continue;
        hr += w * texelFetch(hR, q, 0); hg += w * texelFetch(hG, q, 0); hb += w * texelFetch(hB, q, 0); hw += w;
      }
      if (hw > 0.05) { r = mix(hr / hw, r, HIST_W); g = mix(hg / hw, g, HIST_W); b = mix(hb / hw, b, HIST_W); }
    }
  }
  oR = r; oG = g; oB = b; oGeo = vec4(x, 1.0);
}`,
    gather: `${C}uniform sampler2D depthTex, normalTex, albedoTex, fR, fG, fB; out vec4 o;
struct ToonRecv { vec3 e; float band; float contrast; };
ToonRecv toonReceive(vec3 c0, vec3 c1y, vec3 c1z, vec3 c1x, vec3 n, float soft) {
  vec3 amb = c0 * 0.282095; vec3 w = vec3(0.2126, 0.7152, 0.0722);
  vec3 g = vec3(dot(c1x, w), dot(c1y, w), dot(c1z, w)); float gl = length(g);
  if (gl < 1e-6) return ToonRecv(max(amb, vec3(0.0)), 0.0, 0.0);
  vec3 d = g / gl;
  vec3 dir = max(0.488603 * (c1x * d.x + c1y * d.y + c1z * d.z), vec3(0.0));
  float x = dot(n, d);
  float r = soft > 0.0 ? smoothstep(-soft, soft, x) : (x > 0.0 ? 1.0 : 0.0);
  vec3 e = max(amb - dir + 2.0 * dir * r, vec3(0.0));
  return ToonRecv(e, x > 0.0 ? 1.0 : 0.0, dot(dir, w) / max(dot(amb, w), 1e-6));
}
void main() {
  ivec2 px = ivec2(gl_FragCoord.xy);
  float d = texelFetch(depthTex, px, 0).r;
  if (d <= 0.0) { o = vec4(0.0); return; }
  vec3 x = worldAt(px, d), n = texelFetch(normalTex, px, 0).xyz;
  float z = uEye.w / d;
  ivec2 tn = ivec2(tiles());
  vec2 uc = (vec2(px) + 0.5) / float(T) - 0.5;
  ivec2 b = ivec2(floor(uc)); vec2 f = uc - vec2(b);
  vec3 s0 = vec3(0.0), sy = vec3(0.0), sz = vec3(0.0), sx = vec3(0.0); float ws = 0.0;
  float best = -1.0; ivec2 bq = ivec2(-1);
  for (int k = 0; k < 4; k++) {
    ivec2 o2 = ivec2(k & 1, k >> 1);
    ivec2 q = clamp(b + o2, ivec2(0), tn - 1);
    ivec2 pp = probePixel(uvec2(q));
    float dq = texelFetch(depthTex, pp, 0).r;
    if (dq <= 0.0) continue;
    vec3 nq = texelFetch(normalTex, pp, 0).xyz, xq = worldAt(pp, dq);
    vec2 bw = mix(1.0 - f, f, vec2(equal(o2, ivec2(1))));
    float plane = abs(dot(nq, x - xq)) / z;
    float nd = max(dot(n, nq), 0.0);
    float geo = exp(-40.0 * plane) * nd * nd * nd * nd;
    if (geo > best) { best = geo; bq = q; }
    float w = (bw.x * bw.y + 1e-3) * geo;
    if (w < 1e-6) continue;
    vec4 r = texelFetch(fR, q, 0), g = texelFetch(fG, q, 0), bl = texelFetch(fB, q, 0);
    s0 += w * vec3(r.x, g.x, bl.x); sy += w * vec3(r.y, g.y, bl.y); sz += w * vec3(r.z, g.z, bl.z); sx += w * vec3(r.w, g.w, bl.w);
    ws += w;
  }
  if (ws <= 0.0 && bq.x >= 0) {
    vec4 r = texelFetch(fR, bq, 0), g = texelFetch(fG, bq, 0), bl = texelFetch(fB, bq, 0);
    s0 = vec3(r.x, g.x, bl.x); sy = vec3(r.y, g.y, bl.y); sz = vec3(r.z, g.z, bl.z); sx = vec3(r.w, g.w, bl.w); ws = 1.0;
  }
  if (ws <= 0.0) { o = vec4(0.0, 0.0, 0.0, 1.0); return; }
  float iw = 1.0 / ws; s0 *= iw; sy *= iw; sz *= iw; sx *= iw;
  vec3 e = max(0.282095 * s0 + 0.488603 * (sx * n.x + sy * n.y + sz * n.z), vec3(0.0));
  float tagA = texelFetch(albedoTex, px, 0).a;
  float alpha = 1.0;
  if (tagA > 0.75) {
    ToonRecv r = toonReceive(s0, sy, sz, sx, n, uStyle.z);
    if (uStyle.y > 0.5) e = r.e;
    alpha = 2.0 + r.band + (r.contrast >= 0.1 ? 2.0 : 0.0);
  } else if (tagA > 0.25) alpha = 2.0;
  o = vec4(e, alpha);
}`,
  };
}

// ------------------------------------------------------------------------------------------------------------- WebGL2
type GL = WebGL2RenderingContext;
interface Prog { p: WebGLProgram; u: Map<string, WebGLUniformLocation | null>; samplers: { name: string; array: boolean }[] }
function program(gl: GL, vs: string, fs: string, label: string): Prog {
  const sh = (type: number, src: string) => {
    const s = gl.createShader(type)!;
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(`${label}: ${gl.getShaderInfoLog(s)}`);
    return s;
  };
  const p = gl.createProgram()!;
  gl.attachShader(p, sh(gl.VERTEX_SHADER, vs)); gl.attachShader(p, sh(gl.FRAGMENT_SHADER, fs));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(`${label}: ${gl.getProgramInfoLog(p)}`);
  const samplers: Prog['samplers'] = [];
  const n = gl.getProgramParameter(p, gl.ACTIVE_UNIFORMS) as number;
  for (let i = 0; i < n; i++) {
    const a = gl.getActiveUniform(p, i)!;
    if (([gl.SAMPLER_2D, gl.SAMPLER_2D_ARRAY, gl.SAMPLER_2D_SHADOW] as number[]).includes(a.type)) samplers.push({ name: a.name, array: a.type === gl.SAMPLER_2D_ARRAY });
  }
  return { p, u: new Map(), samplers };
}
function loc(gl: GL, pr: Prog, name: string) {
  if (!pr.u.has(name)) pr.u.set(name, gl.getUniformLocation(pr.p, name));
  return pr.u.get(name)!;
}

function texture2D(gl: GL, w: number, h: number, internal: number, levels = 1) {
  const t = gl.createTexture()!;
  gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texStorage2D(gl.TEXTURE_2D, levels, internal, w, h);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  return { t, w, h, internal, levels };
}
type Tex = ReturnType<typeof texture2D>;
function fbo(gl: GL, colors: [Tex, number?][], depth?: Tex) {
  const f = gl.createFramebuffer()!;
  gl.bindFramebuffer(gl.FRAMEBUFFER, f);
  colors.forEach(([t, l], i) => gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0 + i, gl.TEXTURE_2D, t.t, l ?? 0));
  if (depth) gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.TEXTURE_2D, depth.t, 0);
  gl.drawBuffers(colors.length ? colors.map((_, i) => gl.COLOR_ATTACHMENT0 + i) : [gl.NONE]);
  const st = gl.checkFramebufferStatus(gl.FRAMEBUFFER);
  if (st !== gl.FRAMEBUFFER_COMPLETE) throw new Error(`framebuffer incomplete 0x${st.toString(16)}`);
  const t0 = colors[0]?.[0] ?? depth!;
  const lv = colors[0]?.[1] ?? 0;
  return { f, w: Math.max(t0.w >> lv, 1), h: Math.max(t0.h >> lv, 1), n: colors.length };
}
type Fbo = ReturnType<typeof fbo>;

async function loadSponza() {
  const json = await (await fetch(SPONZA + 'Sponza.gltf')).json();
  const bin = await (await fetch(SPONZA + json.buffers[0].uri)).arrayBuffer();
  return { json, bin, upload: async () => undefined };
}
async function decodeImage(uri: string) {
  const buf = await (await fetch(SPONZA + uri)).arrayBuffer();
  const img = uri.endsWith('.png') ? await decodePng(buf) : jpeg.decode(new Uint8Array(buf), { useTArray: true, formatAsRGBA: true, maxMemoryUsageInMB: 2048 });
  return toTextureSize(img);
}

async function main() {
  const q = new URLSearchParams(location.search);
  const sceneArg = q.get('scene') ?? 'sponza';
  const config = q.get('configs') ?? 'gl2-8-8';
  const warmup = Number(q.get('warmup') ?? 60), frames = Number(q.get('frames') ?? 240), exposure = Number(q.get('exposure') ?? 1);
  const sky: Vec3 = q.has('nosky') ? [0, 0, 0] : SKY;
  const params = parseConfig(config);
  const p: Gl2Params = params.gl2 ?? DEFAULT_GL2;
  const W = 1920, H = 1080;
  const canvas = document.createElement('canvas');
  canvas.width = 64; canvas.height = 64;
  const gl = canvas.getContext('webgl2', { antialias: false, depth: false, powerPreference: 'high-performance' }) as GL | null;
  if (!gl) throw new Error('no WebGL2 context');
  const dbg = gl.getExtension('WEBGL_debug_renderer_info');
  const renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
  log(`WebGL2 ${gl.getParameter(gl.VERSION)}; renderer ${renderer}; user agent ${navigator.userAgent}`);
  if (/swiftshader|llvmpipe/i.test(String(renderer))) log('WARNING: software renderer; the times are not GPU times');
  if (!gl.getExtension('EXT_color_buffer_float')) throw new Error('no EXT_color_buffer_float (float render targets)');
  const timer = gl.getExtension('EXT_disjoint_timer_query_webgl2');
  log(`EXT_disjoint_timer_query_webgl2: ${timer ? 'yes' : 'no (CPU times with gl.finish are logged instead)'}`);
  const aniso = gl.getExtension('EXT_texture_filter_anisotropic');
  log(`limits: MAX_TEXTURE_SIZE ${gl.getParameter(gl.MAX_TEXTURE_SIZE)}, MAX_ARRAY_TEXTURE_LAYERS ${gl.getParameter(gl.MAX_ARRAY_TEXTURE_LAYERS)}, MAX_DRAW_BUFFERS ${gl.getParameter(gl.MAX_DRAW_BUFFERS)}, MAX_TEXTURE_IMAGE_UNITS ${gl.getParameter(gl.MAX_TEXTURE_IMAGE_UNITS)}`);

  // Scene.
  const t0 = performance.now();
  const { spec } = await loadScene(sceneArg, loadSponza);
  if (spec.building || (spec.world && spec.world.instances.length > 1)) throw new Error('the WebGL2 runner has no building motion and no instanced worlds');
  const scene: SceneData = spec.scene;
  const vbo = (data: Float32Array, dynamic = false) => { const b = gl.createBuffer()!; gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, data, dynamic ? gl.DYNAMIC_DRAW : gl.STATIC_DRAW); return b; };
  const vao = gl.createVertexArray()!;
  gl.bindVertexArray(vao);
  const posBuf = vbo(scene.positions, !!spec.dynamic), nrmBuf = vbo(scene.normals, !!spec.dynamic);
  for (const [i, b, n] of [[0, posBuf, 3], [1, nrmBuf, 3], [2, vbo(scene.uvs), 2], [3, vbo(scene.tangents), 4]] as const) {
    gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.enableVertexAttribArray(i); gl.vertexAttribPointer(i, n, gl.FLOAT, false, 0, 0);
  }
  // WebGL2 has no base vertex: indices are offset on the CPU.
  const idx = new Uint32Array(scene.indices.length);
  for (const pr of scene.primitives) for (let i = 0; i < pr.indexCount; i++) idx[pr.firstIndex + i] = scene.indices[pr.firstIndex + i] + pr.baseVertex;
  const ibo = gl.createBuffer()!;
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
  const fullVao = gl.createVertexArray()!;
  // Texture arrays (layer 0 a 1 x 1-filled default), as scene_gpu.ts.
  const roles = [['baseColorImage', gl.SRGB8_ALPHA8, [255, 255, 255, 255]], ['normalImage', gl.RGBA8, [128, 128, 255, 255]], ['metallicRoughnessImage', gl.RGBA8, [255, 255, 255, 255]]] as const;
  const levels = Math.floor(Math.log2(TEXTURE_SIZE)) + 1;
  let sceneBytes = 0;
  const layerOf = roles.map(() => new Map<number, number>());
  const arrays = [] as WebGLTexture[];
  for (const [ri, [key, internal, fill]] of roles.entries()) {
    for (const m of scene.materials) { const img = m[key]; if (img >= 0 && !layerOf[ri].has(img)) layerOf[ri].set(img, layerOf[ri].size + 1); }
    const layers = layerOf[ri].size + 1;
    const t = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D_ARRAY, t);
    gl.texStorage3D(gl.TEXTURE_2D_ARRAY, levels, internal, TEXTURE_SIZE, TEXTURE_SIZE, layers);
    const f = new Uint8Array(TEXTURE_SIZE * TEXTURE_SIZE * 4);
    for (let i = 0; i < f.length; i += 4) f.set(fill, i);
    gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, 0, TEXTURE_SIZE, TEXTURE_SIZE, 1, gl.RGBA, gl.UNSIGNED_BYTE, f);
    for (const [img, layer] of layerOf[ri]) {
      const data = await decodeImage(scene.imageUris[img]);
      gl.bindTexture(gl.TEXTURE_2D_ARRAY, t);
      gl.texSubImage3D(gl.TEXTURE_2D_ARRAY, 0, 0, 0, layer, TEXTURE_SIZE, TEXTURE_SIZE, 1, gl.RGBA, gl.UNSIGNED_BYTE, data);
    }
    gl.generateMipmap(gl.TEXTURE_2D_ARRAY);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR); gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_S, gl.REPEAT); gl.texParameteri(gl.TEXTURE_2D_ARRAY, gl.TEXTURE_WRAP_T, gl.REPEAT);
    if (aniso) gl.texParameterf(gl.TEXTURE_2D_ARRAY, aniso.TEXTURE_MAX_ANISOTROPY_EXT, 8);
    sceneBytes += Math.round(TEXTURE_SIZE * TEXTURE_SIZE * 4 * layers * 4 / 3);
    arrays.push(t);
  }
  log(`scene ${spec.name}: ${scene.triangleCount} triangles, loaded in ${Math.round(performance.now() - t0)} ms, textures ${(sceneBytes / 2 ** 20).toFixed(0)} MiB`);

  // Targets.
  const RT16 = gl.RGBA16F, RT32 = gl.RGBA32F;
  const gAlb = texture2D(gl, W, H, gl.SRGB8_ALPHA8), gNrm = texture2D(gl, W, H, RT16), gDep = texture2D(gl, W, H, gl.DEPTH_COMPONENT32F);
  const gFbo = fbo(gl, [[gAlb], [gNrm]], gDep);
  const SHADOW = 4096;
  const shadow = texture2D(gl, SHADOW, SHADOW, gl.DEPTH_COMPONENT32F);
  gl.bindTexture(gl.TEXTURE_2D, shadow.t);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_COMPARE_MODE, gl.COMPARE_REF_TO_TEXTURE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_COMPARE_FUNC, gl.LEQUAL);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  const sFbo = fbo(gl, [], shadow);
  const lit = texture2D(gl, W, H, RT16), litFbo = fbo(gl, [[lit]]);
  const irr = texture2D(gl, W, H, RT16), irrFbo = fbo(gl, [[irr]]);
  const tx = Math.ceil(W / p.tile), ty = Math.ceil(H / p.tile);
  const half = texture2D(gl, Math.ceil(W / 2), Math.ceil(H / 2), gl.R32F), halfFbo = fbo(gl, [[half]]);
  const atlas = texture2D(gl, tx * p.dirs, ty * p.dirs, RT16), atlasFbo = fbo(gl, [[atlas]]);
  const sh = [0, 1, 2].map(() => texture2D(gl, tx, ty, RT16)), rs = [0, 1, 2].map(() => texture2D(gl, tx, ty, RT16));
  // Filtered SH and probe positions, two sets (this frame's and the history), as src/core/gl2.ts.
  const shF = [0, 1].map(() => [0, 1, 2].map(() => texture2D(gl, tx, ty, RT16))), geo = [0, 1].map(() => texture2D(gl, tx, ty, RT16));
  const shFbo = fbo(gl, sh.map((t) => [t] as [Tex])), rsFbo = fbo(gl, rs.map((t) => [t] as [Tex]));
  const shFFbo = [0, 1].map((k) => fbo(gl, [...shF[k].map((t) => [t] as [Tex]), [geo[k]]]));
  const env: Tex[] = [];
  for (let w = Math.ceil(W / 4), h = Math.ceil(H / 4); ; w = Math.ceil(w / 4), h = Math.ceil(h / 4)) { env.push(texture2D(gl, w, h, RT32)); if (w === 1 && h === 1) break; }
  const envFbo = env.map((t) => fbo(gl, [[t]]));
  const RL = Math.log2(p.rsm) + 1;
  const rAlb = texture2D(gl, p.rsm, p.rsm, gl.SRGB8_ALPHA8), rNrm = texture2D(gl, p.rsm, p.rsm, RT16), rDep = texture2D(gl, p.rsm, p.rsm, gl.DEPTH_COMPONENT32F);
  const rFbo = fbo(gl, [[rAlb], [rNrm]], rDep);
  const rA = texture2D(gl, p.rsm, p.rsm, RT16, RL), rB = texture2D(gl, p.rsm, p.rsm, RT16, RL), rC = texture2D(gl, p.rsm, p.rsm, RT16, RL);
  const rMip = Array.from({ length: RL }, (_, m) => fbo(gl, [[rA, m], [rB, m], [rC, m]]));
  const disp = texture2D(gl, W, H, gl.RGBA8), dispFbo = fbo(gl, [[disp]]);
  // Same bytes as createGl2 counts (src/core/gl2.ts).
  for (const t of [rA, rB, rC]) {
    // Bilinear within a level for the gather's textureLod (texelFetch ignores the filter).
    gl.bindTexture(gl.TEXTURE_2D, t.t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
  }
  let giBytes = W * H * 8 + Math.ceil(W / 2) * Math.ceil(H / 2) * 4 + tx * p.dirs * ty * p.dirs * 8 + 14 * tx * ty * 8 + env.reduce((s, t) => s + t.w * t.h * 16, 0) + p.rsm * p.rsm * 16;
  for (let m = 0; m < RL; m++) giBytes += (p.rsm >> m) ** 2 * 24;

  // Programs.
  const gbProg = program(gl, GB_VS, GB_FS, 'gbuffer'), shProg = program(gl, SHADOW_VS, SHADOW_FS, 'shadow');
  const directProg = program(gl, FULL_VS, DIRECT_FS, 'direct'), dispProg = program(gl, FULL_VS, DISPLAY_FS, 'display');
  const gi = Object.fromEntries(Object.entries(giShaders(p)).map(([k, fs]) => [k, program(gl, FULL_VS, fs, k)])) as Record<keyof ReturnType<typeof giShaders>, Prog>;

  // Frame state.
  const static0 = spec.camera;
  const cam = cameraMatrices(static0, W, H);
  let sunDir = spec.sunDir;
  // As the native runner: the previous frame counts (history) from the second measured frame on.
  let prevValid = false, par = 0;
  let lightVP = sceneSunViewProj(scene.boundsMin, scene.boundsMax, sunDir);
  const frameU = () => ({
    uVP: cam.viewProj, uInvVP: cam.invViewProj, uPrevVP: cam.viewProj, uLightVP: lightVP,
    uEye: [...static0.eye, static0.near], uSunDir: [...sunDir.map((x) => x / Math.hypot(...sunDir)), 0], uSunE: [...SUN_E, 0], uSky: [...sky, 0],
    uSize: [W, H, 1 / W, 1 / H], uStyle: [params.styleEmit ? 1 : 0, params.styleRecv ? 1 : 0, params.rampSoft, 0], uShadow: [1, 0.0002, 0, 0], uExposure: [exposure, 0, 0, 0],
    uPrevValid: prevValid ? 1 : 0,
  });
  let lvp: Mat4 = reversedOrtho(lightVP), invLvp = invert(lvp);
  const extent = () => 2 / Math.hypot(lightVP[0], lightVP[4], lightVP[8]);
  const setU = (pr: Prog, u: Record<string, unknown>) => {
    for (const [k, v] of Object.entries(u)) {
      const l = loc(gl, pr, k);
      if (!l) continue;
      if (k === 'uPrevValid' || k === 'uMode') gl.uniform1i(l, v as number);
      else if ((v as ArrayLike<number>).length === 16) gl.uniformMatrix4fv(l, false, v as Float32Array);
      else gl.uniform4fv(l, v as number[]);
    }
  };
  const bindTex = (pr: Prog, tex: Record<string, WebGLTexture>) => {
    pr.samplers.forEach(({ name, array }, unit) => {
      const t = tex[name];
      if (!t) throw new Error(`no texture for ${name}`);
      gl.activeTexture(gl.TEXTURE0 + unit);
      gl.bindTexture(array ? gl.TEXTURE_2D_ARRAY : gl.TEXTURE_2D, t);
      gl.uniform1i(loc(gl, pr, name), unit);
    });
  };
  const full = (pr: Prog, target: Fbo, tex: Record<string, WebGLTexture>, extra: Record<string, unknown> = {}) => {
    gl.bindFramebuffer(gl.FRAMEBUFFER, target.f);
    gl.viewport(0, 0, target.w, target.h);
    gl.useProgram(pr.p);
    setU(pr, { ...frameU(), uLvp: lvp, uInvLvp: invLvp, uExtent: [extent(), 0, 0, 0], ...extra });
    bindTex(pr, tex);
    gl.bindVertexArray(fullVao);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  };
  // Raster: opaque single-sided first, then double-sided (as gbuffer.ts).
  const draws = scene.primitives.map((pr) => ({ pr, m: scene.materials[pr.material] })).sort((a, b) => Number(a.m.doubleSided) - Number(b.m.doubleSided) || Number(a.m.alphaMask) - Number(b.m.alphaMask));
  const matU = (m: SceneData['materials'][number]) => ({
    uBaseFactor: m.baseColorFactor, uParams: [m.metallicFactor, m.roughnessFactor, m.alphaCutoff, 0],
    uLayers: [layerOf[0].get(m.baseColorImage) ?? 0, layerOf[1].get(m.normalImage) ?? 0, layerOf[2].get(m.metallicRoughnessImage) ?? 0,
      (m.alphaMask ? 1 : 0) | (m.doubleSided ? 2 : 0) | (m.style === 1 ? 4 : 0) | (m.object ? 8 : 0)] });
  const raster = (pr: Prog, target: Fbo, vp: Mat4, cull: boolean, clearDepth: number) => {
    gl.bindFramebuffer(gl.FRAMEBUFFER, target.f);
    gl.viewport(0, 0, target.w, target.h);
    for (let i = 0; i < target.n; i++) gl.clearBufferfv(gl.COLOR, i, [0, 0, 0, 0]);
    gl.clearBufferfi(gl.DEPTH_STENCIL, 0, clearDepth, 0);
    gl.enable(gl.DEPTH_TEST); gl.depthMask(true);
    gl.depthFunc(clearDepth === 0 ? gl.GREATER : gl.LESS);
    gl.frontFace(gl.CW); // clip y is flipped
    gl.useProgram(pr.p);
    gl.uniformMatrix4fv(loc(gl, pr, 'uVP'), false, vp);
    gl.uniform1i(loc(gl, pr, 'uGeoNormals'), 0);
    bindTex(pr, { baseTex: arrays[0], normalTex: arrays[1], mrTex: arrays[2] });
    gl.bindVertexArray(vao);
    for (const d of draws) {
      const u = matU(d.m);
      gl.uniform4fv(loc(gl, pr, 'uBaseFactor'), u.uBaseFactor); gl.uniform4fv(loc(gl, pr, 'uParams'), u.uParams); gl.uniform4iv(loc(gl, pr, 'uLayers'), u.uLayers);
      if (cull && !d.m.doubleSided) gl.enable(gl.CULL_FACE); else gl.disable(gl.CULL_FACE);
      gl.drawElements(gl.TRIANGLES, d.pr.indexCount, gl.UNSIGNED_INT, d.pr.firstIndex * 4);
    }
    gl.disable(gl.CULL_FACE); gl.disable(gl.DEPTH_TEST);
  };
  const pose = (f: number) => {
    const d = spec.dynamic;
    if (!d) return;
    const ps = d.at(f);
    const v = posedVertices(scene, d, ps);
    gl.bindBuffer(gl.ARRAY_BUFFER, posBuf); gl.bufferSubData(gl.ARRAY_BUFFER, v.first * 12, v.pos);
    gl.bindBuffer(gl.ARRAY_BUFFER, nrmBuf); gl.bufferSubData(gl.ARRAY_BUFFER, v.first * 12, v.nrm);
    sunDir = ps.sunDir;
    lightVP = sceneSunViewProj(scene.boundsMin, scene.boundsMax, sunDir);
    lvp = reversedOrtho(lightVP); invLvp = invert(lvp);
  };
  const setLevels = (t: Tex, base: number, max: number) => {
    gl.bindTexture(gl.TEXTURE_2D, t.t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_BASE_LEVEL, base); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAX_LEVEL, max);
  };

  // GI slots (as the native runner): build, trace, merge, gather.
  const SLOTS = ['giBuild', 'giTrace', 'giMerge', 'giGather'] as const;
  const giPasses: (() => void)[][] = [
    [
      () => raster(gbProg, rFbo, lvp, true, 0),
      () => full(gi.halfDepth, halfFbo, { depthTex: gDep.t }),
      ...env.map((_, i) => () => i === 0 ? full(gi.envFirst, envFbo[0], { depthTex: gDep.t }) : full(gi.envReduce, envFbo[i], { src: env[i - 1].t })),
      () => { for (const t of [rA, rB, rC]) setLevels(t, 0, RL - 1); full(gi.rsmShade, rMip[0], { rAlb: rAlb.t, rNrm: rNrm.t, rDepth: rDep.t }); },
      ...Array.from({ length: RL - 1 }, (_, m) => () => {
        // The source level only, so that sampling it while rendering the next level is no feedback loop.
        for (const t of [rA, rB, rC]) setLevels(t, m, m);
        full(gi.rsmMip, rMip[m + 1], { mA: rA.t, mB: rB.t, mC: rC.t });
      }),
      () => { for (const t of [rA, rB, rC]) setLevels(t, 0, RL - 1); full(gi.rsmGather, rsFbo, { depthTex: gDep.t, normalTex: gNrm.t, rA: rA.t, rB: rB.t, rC: rC.t }); },
    ],
    [() => full(gi.trace, atlasFbo, { depthTex: gDep.t, normalTex: gNrm.t, litTex: lit.t, halfZ: half.t, envTex: env[env.length - 1].t, rsR: rs[0].t, rsG: rs[1].t, rsB: rs[2].t })],
    [() => full(gi.projectSH, shFbo, { depthTex: gDep.t, normalTex: gNrm.t, atlas: atlas.t }),
      () => full(gi.filterSH, shFFbo[par], { depthTex: gDep.t, normalTex: gNrm.t, shR: sh[0].t, shG: sh[1].t, shB: sh[2].t,
        hR: shF[1 - par][0].t, hG: shF[1 - par][1].t, hB: shF[1 - par][2].t, hGeo: geo[1 - par].t })],
    [() => full(gi.gather, irrFbo, { depthTex: gDep.t, normalTex: gNrm.t, albedoTex: gAlb.t, fR: shF[par][0].t, fG: shF[par][1].t, fB: shF[par][2].t })],
  ];
  const queries: { q: WebGLQuery; frame: number; slot: number }[] = [];
  const ms: number[][] = SLOTS.map(() => []);
  // Query results only become available after the page returns to the event loop.
  const poll = async (all: boolean) => {
    while (queries.length) {
      const e = queries[0];
      const avail = gl.getQueryParameter(e.q, gl.QUERY_RESULT_AVAILABLE);
      if (!avail) { if (!all) return; await new Promise((r) => setTimeout(r, 4)); continue; }
      const disjoint = gl.getParameter(timer!.GPU_DISJOINT_EXT);
      const ns = gl.getQueryParameter(e.q, gl.QUERY_RESULT) as number;
      if (!disjoint) ms[e.slot].push(ns / 1e6);
      gl.deleteQuery(e.q); queries.shift();
    }
  };
  const cpuMs: number[] = [];
  for (let f = 0; f < warmup + frames; f++) {
    const k = f - warmup;
    prevValid = k >= 1; par = 1 - par;
    pose(f);
    raster(gbProg, gFbo, cam.viewProj, true, 0);
    gl.enable(gl.POLYGON_OFFSET_FILL); gl.polygonOffset(2, 2);
    raster(shProg, sFbo, lightVP, false, 1);
    gl.disable(gl.POLYGON_OFFSET_FILL);
    full(directProg, litFbo, { albedoTex: gAlb.t, normalTex: gNrm.t, depthTex: gDep.t, shadowTex: shadow.t });
    if (!timer && k >= 0) gl.finish();
    const c0 = performance.now();
    giPasses.forEach((passes, slot) => {
      const qq = timer && k >= 0 ? gl.createQuery()! : null;
      if (qq) gl.beginQuery(timer!.TIME_ELAPSED_EXT, qq);
      for (const run of passes) run();
      if (qq) { gl.endQuery(timer!.TIME_ELAPSED_EXT); queries.push({ q: qq, frame: k, slot }); }
    });
    if (!timer && k >= 0) { gl.finish(); cpuMs.push(performance.now() - c0); }
    if (timer) await poll(false);
    if (f % 8 === 7) await new Promise((r) => setTimeout(r, 0));
  }
  if (timer) await poll(true);
  const r3 = (x: number) => Math.round(x * 1000) / 1000;
  const stats = (v: number[]) => { const s = [...v].sort((a, b) => a - b); return s.length ? { n: s.length, median: r3(s[Math.floor(s.length / 2)]), p05: r3(s[Math.floor(s.length * 0.05)]), p95: r3(s[Math.floor(s.length * 0.95)]), max: r3(s[s.length - 1]) } : null; };
  const total = timer ? ms[0].map((_, i) => ms.reduce((s, m) => s + (m[i] ?? 0), 0)) : cpuMs;
  const timing: Record<string, ReturnType<typeof stats>> & { source?: string } = { ...Object.fromEntries(SLOTS.map((s, i) => [s, stats(ms[i])])), giTotal: stats(total) };
  const source = timer ? 'EXT_disjoint_timer_query_webgl2' : 'CPU with gl.finish';
  log(`  GI static ${timing.giTotal?.median} ms (build ${timing.giBuild?.median}, trace ${timing.giTrace?.median}, merge ${timing.giMerge?.median}, gather ${timing.giGather?.median}); ${source}`);
  log(`  GI allocated ${(giBytes / 2 ** 20).toFixed(1)} MiB (same textures as the native gl2)`);

  // Images and irradiance of the last frame.
  const read = (fb: Fbo, type: number) => {
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb.f);
    const out = type === gl.FLOAT ? new Float32Array(W * H * 4) : new Uint8Array(W * H * 4);
    gl.readPixels(0, 0, W, H, gl.RGBA, type, out);
    return out;
  };
  for (const [name, mode] of [['final', 0], ['indirect', 1]] as const) {
    full(dispProg, dispFbo, { albedoTex: gAlb.t, depthTex: gDep.t, litTex: lit.t, irrTex: irr.t }, { uMode: mode });
    post(`/out/${config}.static.${name}.png?w=${W}&h=${H}`, new Blob([read(dispFbo, gl.UNSIGNED_BYTE) as Uint8Array<ArrayBuffer>]));
  }
  // As packIrradiance: rgb + tag (round of alpha; 0 when alpha <= 0.5).
  const f = read(irrFbo, gl.FLOAT) as Float32Array;
  for (let i = 0; i < W * H; i++) { const a = f[i * 4 + 3]; f[i * 4 + 3] = a > 0.5 ? Math.round(a) : 0; }
  post(`/out/${config}.static.irr.f32`, new Blob([f as Float32Array<ArrayBuffer>]));
  post(`/out/${config}.summary.json`, JSON.stringify({ kind: 'exploratory (探索値)', date: new Date().toISOString(), platform: 'browser WebGL2', renderer, userAgent: navigator.userAgent,
    scene: spec.name, config, params: p, frames: { warmup, measured: frames }, sky, timing, timingSource: source, giAllocatedBytes: giBytes, glError: gl.getError() }, null, 2));
  log(`  gl error ${gl.getError()}`);
}

main().then(async () => { await chain; await fetch('/done', { method: 'POST', body: 'ok' }); },
  async (e) => { log('ERROR: ' + (e?.stack ?? e)); await chain.catch(() => undefined); await fetch('/done', { method: 'POST', body: 'error' }); });
