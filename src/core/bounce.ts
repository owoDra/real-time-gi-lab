// Phase 23: multi-bounce for the radiance cascades. A coarse grid of irradiance probes centred on the camera (the
// bounce volume) is rebuilt every frame from the voxels: each probe near a surface traces a fixed set of rays (the
// same directions every frame: no noise, no history of its own) and stores the irradiance along the six axes (an
// ambient cube). A ray's hit radiance is the direct term plus albedo / pi times the irradiance read from the volume of
// the previous frame, so the volume holds all bounces with one frame of lag per bounce beyond the second. The
// cascades' hits (shadeHit in rc.ts) read the volume of the current frame: the second bounce has no lag, the third
// one frame, and so on.
// Reads are trilinear over the 8 probes around the point, skipping inactive probes (no surface near, or the probe inside
// a level-0 voxel), probes on the other side of the surface and probes whose way to the point is blocked (bnRead).
// The texture holds the six axes stacked along z (axis a at z = a * DZ + z), alpha: the reach along the axis (0 inactive),
// and the volume's origin (probe coordinates of probe 0) in the texel (0, 0, 6 DZ).
// Not included: dynamic objects neither receive the bounce (their radiance comes from the dynamic layer, dynlayer.ts)
// nor block the volume's rays.
import { FRAME_WGSL } from './frame.ts';
import { STYLE_WGSL } from './style.ts';
import { BRICK_WORDS, VOX_STRUCT_WGSL, VOX_TRACE_WGSL } from './voxel.ts';
import type { WorldResources } from './rc.ts';

export interface BounceParams {
  cell: number;                    // probe spacing (m)
  dims: [number, number, number];  // probes per axis (camera-centred window)
  rays: number;                    // rays per probe (<= 58)
  div: number;                     // a probe is traced every div frames (by its world position), kept in between
}
// Phase 23 (AI decision, 64 objects + building wave): 1.2 m, 16 rays, every 2 frames cost +0.30 ms of GI. Measured
// alternatives: 0.8 m / 32 rays every frame +0.96 ms update alone; 1.0 m / 24 rays / 2 frames +0.38 ms (jumps 0.0133,
// over the gate); 0.8 m / 24 rays / 4 frames +0.41 ms.
export const DEFAULT_BOUNCE: BounceParams = { cell: 1.2, dims: [32, 16, 32], rays: 16, div: 2 };

export function bounceConstants(b: BounceParams): Record<string, number> {
  return { BN_CELL: b.cell, BN_DX: b.dims[0], BN_DY: b.dims[1], BN_DZ: b.dims[2] };
}

/** Read side: bounceE(p, n, v) -> irradiance at p for normal n. Needs `bnTex: texture_3d<f32>`, the voxel uniform VX and
 * the overrides. */
export const BOUNCE_READ_WGSL = /* wgsl */ `
override BN_CELL: f32 = 0.8;
override BN_DX: i32 = 48;
override BN_DY: i32 = 24;
override BN_DZ: i32 = 48;
fn bnOrigin() -> vec3i { return vec3i(textureLoad(bnTex, vec3i(0, 0, 6 * BN_DZ), 0).xyz); }
fn bnAxis(c: vec3i, a: i32) -> vec4f { return textureLoad(bnTex, vec3i(c.x, c.y, a * BN_DZ + c.z), 0); }
// Irradiance on the side n of a surface at p, read at q (q = p, or moved towards that side): trilinear over the 8 probes
// around q. A probe counts when it is active, lies on that side of p, and q is within the reach it sees along its axes
// towards q (plus half a level-0 voxel: its axis rays stop at the surface's voxel), so that probes behind a wall, beside
// or under the surface do not light it. (Reading half a cell in front of the surface instead moved the read point
// through floors at wall junctions and lit the closed room from outside: phase 24.)
fn bnRead(q: vec3f, p: vec3f, n: vec3f) -> vec3f {
  let org = bnOrigin();
  let g = q / BN_CELL - vec3f(org);
  let bb = vec3i(floor(g)); let fr = g - vec3f(bb);
  let n2 = n * n;
  let tol = 0.5 * VX.a.x;
  var e = vec3f(0.0); var ws = 0.0;
  for (var k = 0u; k < 8u; k++) {
    let off = vec3i(i32(k & 1u), i32((k >> 1u) & 1u), i32((k >> 2u) & 1u));
    let cc = bb + off;
    if (any(cc < vec3i(0)) || any(cc >= vec3i(BN_DX, BN_DY, BN_DZ))) { continue; }
    let pp = vec3f(org + cc) * BN_CELL;
    let u = q - pp;
    if (bnAxis(cc, 0).a <= 0.0) { continue; }
    if (abs(u.x) > bnAxis(cc, select(1, 0, u.x >= 0.0)).a + tol || abs(u.y) > bnAxis(cc, select(3, 2, u.y >= 0.0)).a + tol
        || abs(u.z) > bnAxis(cc, select(5, 4, u.z >= 0.0)).a + tol) { continue; }
    let t3 = select(1.0 - fr, fr, off == vec3i(1));
    let w = t3.x * t3.y * t3.z * smoothstep(-0.05, 0.25, dot(pp - p, n) / BN_CELL);
    if (w <= 0.0) { continue; }
    e += w * (n2.x * bnAxis(cc, select(1, 0, n.x >= 0.0)).rgb + n2.y * bnAxis(cc, select(3, 2, n.y >= 0.0)).rgb + n2.z * bnAxis(cc, select(5, 4, n.z >= 0.0)).rgb);
    ws += w;
  }
  return select(vec3f(0.0), e / ws, ws > 1e-6);
}
fn bounceE(p: vec3f, n: vec3f, v: vec3f) -> vec3f { return bnRead(p, p, n); }
`;

const BOUNCE_WGSL = /* wgsl */ `
${FRAME_WGSL}
${STYLE_WGSL}
const PI = 3.14159265;
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var<uniform> VX: VoxU;
@group(0) @binding(2) var<storage, read> vox: array<u32>;
@group(0) @binding(3) var<storage, read> hr: array<u32>;
@group(0) @binding(4) var shadowTex: texture_depth_2d;
@group(0) @binding(5) var shadowCmp: sampler_comparison;
@group(0) @binding(6) var<storage, read_write> list: array<atomic<u32>>; // 0 count, 1 frame counter, 4.. probes
@group(0) @binding(7) var<storage, read_write> args: array<u32>;         // indirect arguments of bnUpdate
@group(1) @binding(0) var bnTex: texture_3d<f32>;                       // previous frame (read)
@group(1) @binding(1) var bnOut: texture_storage_3d<rgba16float, write>; // this frame
override BN_RAYS: u32 = 32u;
${VOX_TRACE_WGSL}
${BOUNCE_READ_WGSL}
fn voxBounce(p: vec3f, n0: vec3f, d: vec3f, ai: u32, pc: vec3f, v: f32) -> vec3f {
  if (dot(n0, n0) <= 0.01) { return bounceE(p, -d, -d); }
  return bounceE(p, n0 * voxSide(p, n0, d, pc, v), -d);
}
SHADE_PLACEHOLDER

fn bnOriginNow() -> vec3i { return vec3i(floor(F.eye.xyz / BN_CELL)) - vec3i(BN_DX, BN_DY, BN_DZ) / 2; }
fn occAt(L: u32, p: vec3f) -> bool {
  let v = voxSize(L);
  let c = vec3i(floor((p - vec3f(VX.origin[L].xyz) * v * 8.0) / v));
  if (any(c < vec3i(0)) || any(c >= vec3i(voxG() * 8))) { return false; }
  let ptr = vox[voxPtrIndex(L, c >> vec3u(3u))];
  if (ptr >= VOX_MARK) { return false; }
  let l = c & vec3i(7);
  let bit = u32(l.x + 8 * l.y + 64 * l.z);
  return (vox[VX.b.y + ptr * 18u + (bit >> 5u)] & (1u << (bit & 31u))) != 0u;
}
fn levelOf(size: f32) -> u32 { return u32(clamp(round(log2(max(size, 1e-4) / VX.a.x)), 0.0, VX.a.y - 1.0)); }

@compute @workgroup_size(1) fn bnClear() { atomicStore(&list[0], 0u); atomicAdd(&list[1], 1u); }
override BN_DIV: u32 = 1u;

// One thread per probe: inactive probes are cleared, active ones listed (a surface within one cell, the probe itself
// outside the level-0 voxels).
@compute @workgroup_size(64) fn bnClassify(@builtin(global_invocation_id) gid: vec3u, @builtin(num_workgroups) nwg: vec3u) {
  let i = gid.x + gid.y * nwg.x * 64u;
  let n = u32(BN_DX * BN_DY * BN_DZ);
  let o = bnOriginNow();
  if (i == n) { textureStore(bnOut, vec3i(0, 0, 6 * BN_DZ), vec4f(vec3f(o), 0.0)); }
  if (i >= n) { return; }
  let c = vec3i(i32(i % u32(BN_DX)), i32((i / u32(BN_DX)) % u32(BN_DY)), i32(i / u32(BN_DX * BN_DY)));
  let p = vec3f(o + c) * BN_CELL;
  var near = false;
  let L = levelOf(BN_CELL);
  for (var k = 0u; k < 8u && !near; k++) {
    near = occAt(L, p + (vec3f(f32(k & 1u), f32((k >> 1u) & 1u), f32(k >> 2u)) - 0.5) * BN_CELL);
  }
  if (near && !occAt(0u, p)) {
    // With BN_DIV > 1 a probe is traced every BN_DIV frames (by its world position); in between it keeps the previous
    // frame's values when the previous volume holds it.
    let w = o + c;
    if (BN_DIV > 1u && (u32(w.x + w.y + w.z + 1048576) + atomicLoad(&list[1])) % BN_DIV != 0u) {
      let pc = w - bnOrigin();
      if (all(pc >= vec3i(0)) && all(pc < vec3i(BN_DX, BN_DY, BN_DZ)) && bnAxis(pc, 0).a > 0.0) {
        for (var a = 0; a < 6; a++) { textureStore(bnOut, vec3i(c.x, c.y, a * BN_DZ + c.z), bnAxis(pc, a)); }
        return;
      }
    }
    let s = atomicAdd(&list[0], 1u);
    atomicStore(&list[4u + s], i);
  } else {
    for (var a = 0; a < 6; a++) { textureStore(bnOut, vec3i(c.x, c.y, a * BN_DZ + c.z), vec4f(0.0)); }
  }
}
@compute @workgroup_size(1) fn bnArgs() {
  let n = atomicLoad(&list[0]);
  args[0] = min(n, 65535u); args[1] = (n + 65534u) / 65535u; args[2] = 1u;
}

fn sfDir(i: u32, n: u32) -> vec3f {
  let z = 1.0 - (2.0 * f32(i) + 1.0) / f32(n);
  let r = sqrt(max(0.0, 1.0 - z * z));
  let phi = 2.0 * PI * fract(f32(i) * 0.618033988749);
  return vec3f(r * cos(phi), r * sin(phi), z);
}
// A ray as segments [b_k, b_k+1] * cell (b_k = (4^k - 1) / 3) on voxel level k. The probe is outside the level-0 voxels
// (bnClassify), so nothing is skipped: skipping the probe's own coarser voxel let probes next to a thin wall see
// through it (the closed room's leak rose from 0.39 to 1.75 %).
fn bnTrace(o: vec3f, d: vec3f, tMax: f32) -> vec4f {
  let nl = u32(VX.a.y);
  var b0 = 0.0;
  for (var k = 0u; k < nl && b0 * BN_CELL < tMax; k++) {
    let b1 = b0 * 4.0 + 1.0;
    let L = voxLevelFor(k, o + d * b1 * BN_CELL);
    let r = traceVox(o, d, b0 * BN_CELL, min(b1 * BN_CELL, tMax), 0.0, L);
    if (r.a < 0.5) { return vec4f(r.rgb, dot(voxHitEntry - o, d)); }
    b0 = b1;
  }
  return vec4f(F.sky.rgb, 1e9);
}

var<workgroup> wgRad: array<vec3f, 64>;
var<workgroup> wgReach: array<f32, 6>;
var<workgroup> wgProbe: u32;
// One workgroup per active probe: lanes [0, rays) trace the irradiance rays, lanes [rays, rays + 6) the six axis rays
// (reach: up to the first occupied voxel, at most 1.5 cells; alpha of the axes), then six lanes sum the ambient cube.
@compute @workgroup_size(64) fn bnUpdate(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let slot = wid.x + wid.y * nwg.x;
  if (li == 0u) { wgProbe = select(0xffffffffu, atomicLoad(&list[4u + slot]), slot < atomicLoad(&list[0])); }
  let i = workgroupUniformLoad(&wgProbe);
  if (i == 0xffffffffu) { return; }
  let c = vec3i(i32(i % u32(BN_DX)), i32((i / u32(BN_DX)) % u32(BN_DY)), i32(i / u32(BN_DX * BN_DY)));
  let p = vec3f(bnOriginNow() + c) * BN_CELL;
  if (li < BN_RAYS) { wgRad[li] = bnTrace(p, sfDir(li, BN_RAYS), 1e9).rgb; }
  else if (li < BN_RAYS + 6u) {
    let a = li - BN_RAYS;
    var axis = vec3f(0.0); axis[a / 2u] = select(1.0, -1.0, (a & 1u) == 1u);
    wgReach[a] = max(min(bnTrace(p, axis, 1.5 * BN_CELL).a, 1.5 * BN_CELL), 1e-3);
  }
  workgroupBarrier();
  if (li < 6u) {
    var axis = vec3f(0.0); axis[li / 2u] = select(1.0, -1.0, (li & 1u) == 1u);
    var e = vec3f(0.0); var ws = 0.0;
    for (var r = 0u; r < BN_RAYS; r++) {
      let w = max(dot(axis, sfDir(r, BN_RAYS)), 0.0);
      e += w * wgRad[r]; ws += w;
    }
    textureStore(bnOut, vec3i(c.x, c.y, i32(li) * BN_DZ + c.z), vec4f(PI * e / max(ws, 1e-6), wgReach[li]));
  }
}
`;

// After the volume update: one thread per (brick, voxel slot), as voxel.ts resolveAttr. Every occupied voxel stores the
// irradiance of this frame's volume on its two sides (along and against its normal), so that a cascade hit reads two
// words instead of eight probes (the per-hit read cost 0.6 ms on the 64-object building-wave scene).
const INJECT_WGSL = /* wgsl */ `
${VOX_STRUCT_WGSL}
@group(0) @binding(0) var<uniform> VX: VoxU;
@group(0) @binding(1) var<storage, read_write> vox: array<u32>;
@group(0) @binding(2) var bnTex: texture_3d<f32>;
${BOUNCE_READ_WGSL}
// One side (normal n) of a voxel centred at p: level 0 is read at the centre, coarser levels half a voxel towards that
// side (a coarse voxel's centre may lie metres from the surface).
fn bnSide(p: vec3f, n: vec3f, v: f32, L: u32) -> vec3f { return bnRead(p + n * select(0.5 * v, 0.0, L == 0u), p, n); }
@compute @workgroup_size(64) fn bnInject(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
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
  let p = vec3f(VX.origin[L].xyz) * v * 8.0 + (vec3f(c) + 0.5) * v;
  let nn = unpack2x16snorm(vox[VX.b.z + ai * 2u + 1u]);
  var n = vec3f(nn.x, nn.y, 1.0 - abs(nn.x) - abs(nn.y));
  let q = max(-n.z, 0.0);
  n.x += select(q, -q, n.x >= 0.0); n.y += select(q, -q, n.y >= 0.0);
  let nf = select(vec3f(0.0, 1.0, 0.0), normalize(n), dot(n, n) > 0.01);
  let ef = bnSide(p, nf, v, L);
  let eb = bnSide(p, -nf, v, L);
  let o = VX.c.z + ai * 4u;
  vox[o] = pack2x16float(ef.rg); vox[o + 1u] = pack2x16float(vec2f(ef.b, 0.0));
  vox[o + 2u] = pack2x16float(eb.rg); vox[o + 3u] = pack2x16float(vec2f(eb.b, 0.0));
}
`;

export interface Bounce {
  bytes: number;
  /** The volume the cascades read this frame (written by the last encode). */
  current(): GPUTextureView;
  views: [GPUTextureView, GPUTextureView];
  parity(): number;
  encode(pass: GPUComputePassEncoder): void;
  destroy(): void;
}

export function createBounce(device: GPUDevice, frame: GPUBuffer, world: WorldResources, b: BounceParams, shadeWgsl: string): Bounce {
  const [DX, DY, DZ] = b.dims, n = DX * DY * DZ;
  const tex = [0, 1].map((i) => device.createTexture({ label: `bounce.${i}`, size: [DX, DY, 6 * DZ + 1], dimension: '3d', format: 'rgba16float',
    usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.TEXTURE_BINDING }));
  const views = tex.map((t) => t.createView()) as [GPUTextureView, GPUTextureView];
  const list = device.createBuffer({ label: 'bounce.list', size: (4 + n) * 4, usage: GPUBufferUsage.STORAGE });
  const args = device.createBuffer({ label: 'bounce.args', size: 16, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.INDIRECT });
  const code = BOUNCE_WGSL.replace('SHADE_PLACEHOLDER', shadeWgsl);
  const module = device.createShaderModule({ code, label: 'bounce' });
  const C = GPUShaderStage.COMPUTE;
  const bgl0 = device.createBindGroupLayout({ entries: [
    { binding: 0, visibility: C, buffer: { type: 'uniform' } }, { binding: 1, visibility: C, buffer: { type: 'uniform' } },
    { binding: 2, visibility: C, buffer: { type: 'read-only-storage' } }, { binding: 3, visibility: C, buffer: { type: 'read-only-storage' } },
    { binding: 4, visibility: C, texture: { sampleType: 'depth' } }, { binding: 5, visibility: C, sampler: { type: 'comparison' } },
    { binding: 6, visibility: C, buffer: { type: 'storage' } },
  ] });
  const bgl1 = device.createBindGroupLayout({ entries: [
    { binding: 0, visibility: C, texture: { sampleType: 'unfilterable-float', viewDimension: '3d' } },
    { binding: 1, visibility: C, storageTexture: { access: 'write-only', format: 'rgba16float', viewDimension: '3d' } },
  ] });
  const layout = device.createPipelineLayout({ bindGroupLayouts: [bgl0, bgl1] });
  const constants = { ...bounceConstants(b), BN_RAYS: b.rays, BN_DIV: b.div };
  const P = Object.fromEntries(['bnClear', 'bnClassify', 'bnUpdate'].map((e) => [e,
    device.createComputePipeline({ label: e, layout, compute: { module, entryPoint: e, constants } })]));
  // bnArgs alone binds the indirect arguments as storage (a dispatch may not use them both ways).
  const argsPipe = device.createComputePipeline({ label: 'bnArgs', layout: 'auto', compute: { module, entryPoint: 'bnArgs', constants } });
  const argsBG = device.createBindGroup({ layout: argsPipe.getBindGroupLayout(0), entries: [
    { binding: 6, resource: { buffer: list } }, { binding: 7, resource: { buffer: args } }] });
  const bg0 = device.createBindGroup({ layout: bgl0, entries: [
    { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: { buffer: world.voxUniform } },
    { binding: 2, resource: { buffer: world.vox } }, { binding: 3, resource: { buffer: world.hr } },
    { binding: 4, resource: world.shadow.createView() }, { binding: 5, resource: device.createSampler({ compare: 'less-equal', minFilter: 'linear', magFilter: 'linear' }) },
    { binding: 6, resource: { buffer: list } },
  ] });
  // Parity p writes texture p and reads texture 1 - p.
  const bg1 = [0, 1].map((p) => device.createBindGroup({ layout: bgl1, entries: [{ binding: 0, resource: views[1 - p] }, { binding: 1, resource: views[p] }] }));
  const injModule = device.createShaderModule({ code: INJECT_WGSL, label: 'bounce.inject' });
  const injPipe = device.createComputePipeline({ label: 'bnInject', layout: 'auto', compute: { module: injModule, entryPoint: 'bnInject', constants: bounceConstants(b) } });
  const injBG = views.map((v) => device.createBindGroup({ layout: injPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: world.voxUniform } }, { binding: 1, resource: { buffer: world.vox } }, { binding: 2, resource: v }] }));
  const maxSlots = world.maxBricks * 512;
  let par = 1;
  const use = (pass: GPUComputePassEncoder, e: string) => { pass.setPipeline(P[e]); pass.setBindGroup(0, bg0); pass.setBindGroup(1, bg1[par]); };
  return {
    bytes: 2 * DX * DY * (6 * DZ + 1) * 8 + list.size + args.size,
    views,
    current: () => views[par],
    parity: () => par,
    encode(pass) {
      par = 1 - par;
      use(pass, 'bnClear'); pass.dispatchWorkgroups(1);
      const groups = Math.ceil((n + 1) / 64), x = Math.min(groups, 65535);
      use(pass, 'bnClassify'); pass.dispatchWorkgroups(x, Math.ceil(groups / x));
      pass.setPipeline(argsPipe); pass.setBindGroup(0, argsBG); pass.dispatchWorkgroups(1);
      use(pass, 'bnUpdate'); pass.dispatchWorkgroupsIndirect(args, 0);
      const g = Math.ceil(maxSlots / 64), gx = Math.min(g, 65535);
      pass.setPipeline(injPipe); pass.setBindGroup(0, injBG[par]); pass.dispatchWorkgroups(gx, Math.ceil(g / gx));
    },
    destroy() { for (const t of tex) t.destroy(); list.destroy(); args.destroy(); },
  };
}
