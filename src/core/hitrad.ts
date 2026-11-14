// P1: prefiltered hit radiance of the static voxels. Static hits no longer shade one point (the sun's visibility of
// one point flips a whole direction bin when a shadow edge passes it); they read the direct light of the voxels,
// injected every frame and averaged from fine to coarse levels, at the level that matches the width of the direction
// bin's cone. Geometry (the binary bricks, built once) and radiance (every frame) are updated separately.
//
// Each occupied static voxel of levels 1.. has two radiances: the side its representative normal n points to
// ("front") and the opposite side ("back"), so the lit face of a thin wall does not pass to the other side.
// Level 0 holds none: injecting its 0.73 M voxels (Sponza) with an area-averaged visibility cost about 0.5 ms, which
// does not fit in the GI budget next to the rest; hits on level 0 read level 1 (0.2 m).
// Build (every frame, after the shadow map; needs the static bricks built once, anchor 'scene' and local):
//  inject     level 1: Lambert on the lit side (toon: the emission-side operator) with the sun's visibility averaged
//             over 4 x 4 points spread over the voxel's face on that side (plane through centre + ns v / 2, normal
//             to n, v x v). Each point is a bilinear shadow-map comparison, so the value moves continuously with the
//             sun. 16 threads per voxel (their comparisons fall close together in the shadow map).
//  aggregate  levels 2.., fine to coarse: the mean of the occupied children (the 8 voxels of the level below),
//             each weighted by |n_child . n| and with its sides swapped when its normal points away from the
//             parent's (faces normal to the parent's do not count: a corner's wall does not light a floor's side).
//             With every child normal to the voxel, the plain mean; with no child, a negative mark (reads skip it).
// Read (hitRadiance): the hit voxel's centre is looked up at the level nearest to v = w (w = cone width at the hit,
// never finer than the traced level or level 1); the side is the one facing the ray (by the read voxel's own normal).
// A level whose voxel at the centre is empty or marked falls back to the next finer one; with none (level-0 voxels
// without an occupied parent), the hit is shaded at one point as before P1.
// The radiances of levels 1.. are stored per brick slot (512 per brick, 4 words: two rgb half triples and the voxel's
// normal), so a read is the brick pointer, the brick's base and one slot. The lists of voxels, the child table, the
// bricks' bases and the normals are written once after the static bricks.
import { FRAME_WGSL } from './frame.ts';
import { STYLE_WGSL } from './style.ts';
import { BRICK_WORDS, VOX_STRUCT_WGSL, type VoxWorld } from './voxel.ts';

// hr: [0] 1 when built, [1] finest level held, [2] first slot word, [3] 0, then one word per brick (its first slot,
// 0xffffffff for bricks of finer levels), then 4 words per slot (empty and marked slots: negative radiance).
const HR_HDR = 4;
const FIRST = 1; // finest level held
const VOX_HDR = 64;

/** Read side, shared by the RC and DDGI voxel tracers. Needs VX, vox, voxSize, voxG, voxPtrIndex and hr. */
export const HIT_READ_WGSL = /* wgsl */ `
var<private> coneK: f32;    // cone width per unit distance of the current ray (set by the tracer)
var<private> coneO: vec3f;  // where the cone starts
fn hrReady() -> bool { return hr[0] != 0u; }
// Radiance of the voxel of level L at p toward a ray along d (the side facing it): (rgb, 1), or 0 if the voxel is
// empty or marked.
fn hrAt(L: u32, p: vec3f, d: vec3f) -> vec4f {
  let v = voxSize(L);
  let c = vec3i(floor((p - vec3f(VX.origin[L].xyz) * v * 8.0) / v));
  if (any(c < vec3i(0)) || any(c >= vec3i(voxG() * 8))) { return vec4f(0.0); }
  let ptr = vox[voxPtrIndex(L, c >> vec3u(3u))];
  if (ptr >= VOX_MARK) { return vec4f(0.0); }
  let l = c & vec3i(7);
  let b = hr[2] + (hr[${HR_HDR}u + ptr] + u32(l.x + 8 * l.y + 64 * l.z)) * 4u;
  let w0 = unpack2x16float(hr[b]);
  if (w0.x < 0.0) { return vec4f(0.0); }
  let w1 = unpack2x16float(hr[b + 1u]); let w2 = unpack2x16float(hr[b + 2u]);
  let nn = unpack2x16snorm(hr[b + 3u]);
  var n = vec3f(nn.x, nn.y, 1.0 - abs(nn.x) - abs(nn.y));
  let q = max(-n.z, 0.0);
  n.x += select(q, -q, n.x >= 0.0); n.y += select(q, -q, n.y >= 0.0);
  return vec4f(select(vec3f(w1.y, w2.x, w2.y), vec3f(w0.x, w0.y, w1.x), dot(n, d) <= 0.0), 1.0);
}
// P1 radiance of a static hit on a voxel of level Lh with centre pc, ray along d, hit at distance t from coneO:
// (rgb, 1), or 0 when no level holds it.
fn hitRadiance(Lh: u32, pc: vec3f, d: vec3f, t: f32) -> vec4f {
  let lo = max(Lh, hr[1]);
  var l = u32(round(clamp(log2(max(coneK * t, 1e-6) / VX.a.x), f32(lo), VX.a.y - 1.0)));
  loop {
    let r = hrAt(l, pc, d);
    if (r.a > 0.0 || l <= lo) { return r; }
    l--;
  }
}
`;

const BUILD_WGSL = /* wgsl */ `
${FRAME_WGSL}
${STYLE_WGSL}
${VOX_STRUCT_WGSL}
const PI = 3.14159265;
@group(0) @binding(0) var<uniform> VX: VoxU;
@group(0) @binding(1) var<storage, read> vox: array<u32>;
@group(0) @binding(2) var<storage, read_write> hr: array<u32>;
@group(0) @binding(3) var<uniform> F: Frame;
@group(0) @binding(4) var<storage, read> lists: array<vec4u>; // per level: brick << 9 | bit, attribute index, slot
@group(0) @binding(5) var<uniform> HU: vec4u;                // level, first list entry, entries, first child-table entry
@group(0) @binding(6) var shadowTex: texture_depth_2d;
@group(0) @binding(7) var shadowCmp: sampler_comparison;
@group(0) @binding(8) var<storage, read_write> kids: array<u32>; // 8 per voxel of levels 2..: slot | weight << 24

fn lin(wid: vec3u, nwg: vec3u, li: u32) -> u32 { return (wid.y * nwg.x + wid.x) * 64u + li; }
fn normalOf(ai: u32) -> vec3f {
  let nn = unpack2x16snorm(vox[VX.b.z + ai * 2u + 1u]);
  var n = vec3f(nn.x, nn.y, 1.0 - abs(nn.x) - abs(nn.y));
  let q = max(-n.z, 0.0);
  n.x += select(q, -q, n.x >= 0.0); n.y += select(q, -q, n.y >= 0.0);
  return normalize(n);
}
fn tap(c: vec3f) -> f32 {
  let uv = c.xy * vec2f(0.5, -0.5) + 0.5;
  if (any(uv < vec2f(0.0)) || any(uv > vec2f(1.0))) { return 1.0; }
  return textureSampleCompareLevel(shadowTex, shadowCmp, uv, c.z - 0.0002);
}
fn store(idx: u32, front: vec3f, back: vec3f) {
  let b = hr[2] + idx * 4u;
  hr[b] = pack2x16float(front.xy); hr[b + 1u] = pack2x16float(vec2f(front.z, back.x)); hr[b + 2u] = pack2x16float(back.yz);
}
fn loadSides(idx: u32) -> array<vec3f, 2> {
  let b = hr[2] + idx * 4u;
  let w0 = unpack2x16float(hr[b]); let w1 = unpack2x16float(hr[b + 1u]); let w2 = unpack2x16float(hr[b + 2u]);
  return array<vec3f, 2>(vec3f(w0.x, w0.y, w1.x), vec3f(w1.y, w2.x, w2.y));
}
struct Entry { ai: u32, idx: u32, L: u32, c: vec3i, p: vec3f }
fn entry(i: u32) -> Entry {
  let le = lists[HU.y + i];
  let ptr = le.x >> 9u; let bit = le.x & 511u;
  let code = vox[VX.b.y + ptr * ${BRICK_WORDS}u + 17u];
  let L = code >> 27u;
  let b = vec3i(i32((code >> 18u) & 511u), i32((code >> 9u) & 511u), i32(code & 511u));
  let c = b * 8 + vec3i(i32(bit & 7u), i32((bit >> 3u) & 7u), i32(bit >> 6u));
  let v = voxSize(L);
  return Entry(le.y, le.z, L, c, vec3f(VX.origin[L].xyz) * v * 8.0 + (vec3f(c) + 0.5) * v);
}

// Level 1: 4 voxels per workgroup, 16 threads each. One thread per voxel prepares it (the light-space position is
// affine in the point: centre and two axes) and sums the 16 results.
struct Prep { c0: vec3f, ndl: f32, c1: vec3f, c2: vec3f }
var<workgroup> wp: array<Prep, 4>;
var<workgroup> wv: array<f32, 64>;
@compute @workgroup_size(64) fn inject(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let first = (wid.y * nwg.x + wid.x) * 4u;
  if (li < 4u) {
    var pr = Prep(vec3f(0.0), 0.0, vec3f(0.0), vec3f(0.0));
    if (first + li < HU.z) {
      let e = entry(first + li);
      let n = normalOf(e.ai);
      let sd = dot(n, F.sunDir.xyz);
      if (sd != 0.0) {
        let ns = select(-n, n, sd > 0.0);
        let v = voxSize(e.L);
        let t1 = normalize(cross(ns, select(vec3f(0.0, 0.0, 1.0), vec3f(1.0, 0.0, 0.0), abs(ns.z) > 0.9)));
        let t2 = cross(ns, t1);
        pr = Prep((F.lightViewProj * vec4f(e.p + ns * (0.5 * v), 1.0)).xyz, abs(sd),
          (F.lightViewProj * vec4f(t1 * v, 0.0)).xyz, (F.lightViewProj * vec4f(t2 * v, 0.0)).xyz);
      }
    }
    wp[li] = pr;
  }
  workgroupBarrier();
  let pr = wp[li >> 4u];
  let k = li & 15u;
  var vis = 0.0;
  if (pr.ndl > 0.0) { vis = tap(pr.c0 + pr.c1 * ((f32(k & 3u) + 0.5) * 0.25 - 0.5) + pr.c2 * ((f32(k >> 2u) + 0.5) * 0.25 - 0.5)); }
  wv[li] = vis;
  workgroupBarrier();
  if (li >= 4u || first + li >= HU.z) { return; }
  let e = entry(first + li);
  let alb = unpack4x8unorm(vox[VX.b.z + e.ai * 2u]);
  let ndl = wp[li].ndl;
  var r = vec3f(0.0);
  if (ndl > 0.0) {
    let base = li * 16u;
    if (alb.a > 0.5 && F.style.x > 0.5) {
      for (var j = 0u; j < 16u; j++) { r += toonSun(alb.rgb, ndl, wv[base + j], F.sunE.rgb); }
      r /= 16.0;
    } else {
      var s = 0.0;
      for (var j = 0u; j < 16u; j++) { s += wv[base + j]; }
      r = alb.rgb / PI * F.sunE.rgb * ndl * s / 16.0;
    }
  }
  let lit = dot(normalOf(e.ai), F.sunDir.xyz) > 0.0;
  store(e.idx, select(vec3f(0.0), r, lit), select(r, vec3f(0.0), lit));
}

// Once (static bricks): the 8 children of every voxel of levels 2.. with their weights n_child . n (8 bits).
@compute @workgroup_size(64) fn children(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  if (i >= HU.z) { return; }
  let e = entry(i);
  let n = normalOf(e.ai);
  let gc = (VX.origin[e.L].xyz * 8 + e.c) * 2 - VX.origin[e.L - 1u].xyz * 8;
  for (var q = 0u; q < 8u; q++) {
    let c = gc + vec3i(i32(q & 1u), i32((q >> 1u) & 1u), i32(q >> 2u));
    var x = 0xffffffffu;
    if (all(c >= vec3i(0)) && all(c < vec3i(voxG() * 8))) {
      let ptr = vox[voxPtrIndex(e.L - 1u, c >> vec3u(3u))];
      let l = c & vec3i(7);
      let bit = u32(l.x + 8 * l.y + 64 * l.z);
      let base = VX.b.y + ptr * ${BRICK_WORDS}u;
      if (ptr < VOX_MARK && (vox[base + (bit >> 5u)] & (1u << (bit & 31u))) != 0u) {
        var r = countOneBits(vox[base + (bit >> 5u)] & ((1u << (bit & 31u)) - 1u));
        for (var j = 0u; j < (bit >> 5u); j++) { r += countOneBits(vox[base + j]); }
        let w = u32(round(clamp(dot(normalOf(vox[base + 16u] + r), n), -1.0, 1.0) * 127.0) + 127.0);
        x = (hr[${HR_HDR}u + ptr] + bit) | (w << 24u);
      }
    }
    kids[(HU.w + i) * 8u + q] = x;
  }
}
// Once: the normal of every voxel of levels 1.. into its slot.
@compute @workgroup_size(64) fn normals(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  if (i >= HU.z) { return; }
  let le = lists[HU.y + i];
  hr[hr[2] + le.z * 4u + 3u] = vox[VX.b.z + le.y * 2u + 1u];
}
// Levels 2.., fine to coarse.
@compute @workgroup_size(64) fn aggregate(@builtin(workgroup_id) wid: vec3u, @builtin(num_workgroups) nwg: vec3u, @builtin(local_invocation_index) li: u32) {
  let i = lin(wid, nwg, li);
  if (i >= HU.z) { return; }
  var front = vec3f(0.0); var back = vec3f(0.0); var wsum = 0.0;
  var pf = vec3f(0.0); var pb = vec3f(0.0); var cnt = 0.0;
  for (var q = 0u; q < 8u; q++) {
    let x = kids[(HU.w + i) * 8u + q];
    if (x == 0xffffffffu) { continue; }
    let k = f32(x >> 24u) / 127.0 - 1.0;
    let s = loadSides(x & 0xffffffu);
    if (s[0].x < 0.0) { continue; }
    let f = select(s[1], s[0], k >= 0.0); let b = select(s[0], s[1], k >= 0.0);
    front += abs(k) * f; back += abs(k) * b; wsum += abs(k);
    pf += f; pb += b; cnt += 1.0;
  }
  let idx = lists[HU.y + i].z;
  if (cnt == 0.0) { store(idx, vec3f(-1.0), vec3f(-1.0)); return; }
  if (wsum < 1e-3) { store(idx, pf / cnt, pb / cnt); return; }
  store(idx, front / wsum, back / wsum);
}
`;

export interface HitRad {
  buffer: GPUBuffer;
  /** Slots, voxel lists and child table (allocated = used: sized to the static bricks). */
  bytes: number;
  voxelsPerLevel: number[];
  /** This frame's injection and aggregation (after the shadow map, inside the caller's compute pass). */
  encode(pass: GPUComputePassEncoder): void;
  destroy(): void;
}

/** Empty layer: hits keep the one-point shading (voxel worlds rebuilt every frame). */
export function emptyHitRad(device: GPUDevice): GPUBuffer {
  return device.createBuffer({ label: 'hitrad.empty', size: 16, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
}

/** Builds the layer for static bricks built once (call after VoxWorld.buildStatic). */
export async function createHitRad(device: GPUDevice, vw: VoxWorld, frame: GPUBuffer, shadow: GPUTexture): Promise<HitRad> {
  const { levels: NL, G } = vw.params;
  if (!vw.params.local) throw new Error('P1 hit radiance needs static bricks built once (local)');
  const c = await vw.readCounters();
  if (c.brickOverflow || c.voxelOverflow) throw new Error('voxel pool overflow');
  // The bricks (occupancy, first attribute, level and coordinates) of the static build.
  const brickOff = VOX_HDR + NL * G ** 3, nWords = c.bricks * BRICK_WORDS;
  const read = device.createBuffer({ size: Math.max(16, nWords * 4), usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
  const enc = device.createCommandEncoder();
  enc.copyBufferToBuffer(vw.vox, brickOff * 4, read, 0, nWords * 4);
  device.queue.submit([enc.finish()]);
  await read.mapAsync(GPUMapMode.READ);
  const bw = new Uint32Array(read.getMappedRange().slice(0));
  read.unmap(); read.destroy();
  // Per brick of levels >= FIRST: its first slot; per level: (brick << 9 | bit, attribute, slot).
  const hrBase = new Uint32Array(c.bricks).fill(0xffffffff);
  const perLevel: number[][] = Array.from({ length: NL }, () => []);
  const counts = new Array(NL).fill(0);
  let slots = 0;
  for (let b = 0; b < c.bricks; b++) {
    const o = b * BRICK_WORDS, L = bw[o + 17] >>> 27;
    let ai = bw[o + 16];
    if (L >= FIRST) { hrBase[b] = slots; slots += 512; }
    for (let w = 0; w < 16; w++) for (let bit = 0; bit < 32; bit++) {
      if (!(bw[o + w] & (1 << bit))) continue;
      counts[L]++;
      if (L >= FIRST) perLevel[L].push((b << 9) | (w * 32 + bit), ai, hrBase[b] + w * 32 + bit, 0);
      ai++;
    }
  }
  if (counts.reduce((a, b) => a + b, 0) !== c.voxels) throw new Error('voxel count mismatch');
  const n = perLevel.map((l) => l.length / 4);
  const held = n.reduce((a, b) => a + b, 0);
  const firsts = n.map((_, L) => n.slice(0, L).reduce((a, b) => a + b, 0));
  const lists = device.createBuffer({ label: 'hitrad.lists', size: Math.max(16, held * 16), usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
  device.queue.writeBuffer(lists, 0, Uint32Array.from(perLevel.flat()));
  const dataOff = Math.ceil((HR_HDR + c.bricks) / 4) * 4;
  const buffer = device.createBuffer({ label: 'hitrad', size: (dataOff + slots * 4) * 4, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
  const init = new Uint32Array(dataOff + slots * 4);
  init.set([1, FIRST, dataOff, 0]); init.set(hrBase, HR_HDR);
  for (let k = 0; k < slots; k++) init[dataOff + k * 4] = 0xbc00bc00; // half (-1, -1): empty
  device.queue.writeBuffer(buffer, 0, init);
  const kidFirst = (L: number) => firsts[L] - n[FIRST];
  const kids = device.createBuffer({ label: 'hitrad.kids', size: Math.max(16, (held - n[FIRST]) * 8 * 4), usage: GPUBufferUsage.STORAGE });
  const uni = n.map((cnt, L) => {
    const u = device.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    device.queue.writeBuffer(u, 0, new Uint32Array([L, firsts[L], cnt, Math.max(kidFirst(L), 0)]));
    return u;
  });
  const module = device.createShaderModule({ code: BUILD_WGSL, label: 'hitrad.build' });
  const C = GPUShaderStage.COMPUTE;
  const st = (binding: number, type: GPUBufferBindingType) => ({ binding, visibility: C, buffer: { type } });
  const bgl = device.createBindGroupLayout({ entries: [st(0, 'uniform'), st(1, 'read-only-storage'), st(2, 'storage'), st(3, 'uniform'),
    st(4, 'read-only-storage'), st(5, 'uniform'), { binding: 6, visibility: C, texture: { sampleType: 'depth' } },
    { binding: 7, visibility: C, sampler: { type: 'comparison' } }, st(8, 'storage')] });
  const layout = device.createPipelineLayout({ bindGroupLayouts: [bgl] });
  const pipes = Object.fromEntries(['inject', 'normals', 'children', 'aggregate'].map((e) =>
    [e, device.createComputePipeline({ label: `hitrad.${e}`, layout, compute: { module, entryPoint: e } })]));
  const cmp = device.createSampler({ compare: 'less-equal', minFilter: 'linear', magFilter: 'linear' });
  const bgs = uni.map((u) => device.createBindGroup({ layout: bgl, entries: [
    { binding: 0, resource: { buffer: vw.uniform } }, { binding: 1, resource: { buffer: vw.vox } }, { binding: 2, resource: { buffer } },
    { binding: 3, resource: { buffer: frame } }, { binding: 4, resource: { buffer: lists } }, { binding: 5, resource: { buffer: u } },
    { binding: 6, resource: shadow.createView() }, { binding: 7, resource: cmp }, { binding: 8, resource: { buffer: kids } },
  ] }));
  const groups = (pass: GPUComputePassEncoder, g: number) => {
    const x = Math.min(g, 65535);
    if (g > 0) pass.dispatchWorkgroups(x, Math.ceil(g / x));
  };
  {
    const e = device.createCommandEncoder();
    const pass = e.beginComputePass();
    for (let L = FIRST; L < NL; L++) { pass.setPipeline(pipes.normals); pass.setBindGroup(0, bgs[L]); groups(pass, Math.ceil(n[L] / 64)); }
    for (let L = FIRST + 1; L < NL; L++) { pass.setPipeline(pipes.children); pass.setBindGroup(0, bgs[L]); groups(pass, Math.ceil(n[L] / 64)); }
    pass.end();
    device.queue.submit([e.finish()]);
  }
  return {
    buffer, bytes: buffer.size + lists.size + kids.size, voxelsPerLevel: counts,
    encode(pass) {
      pass.setPipeline(pipes.inject); pass.setBindGroup(0, bgs[FIRST]); groups(pass, Math.ceil(n[FIRST] / 4));
      for (let L = FIRST + 1; L < NL; L++) { pass.setPipeline(pipes.aggregate); pass.setBindGroup(0, bgs[L]); groups(pass, Math.ceil(n[L] / 64)); }
    },
    destroy() { buffer.destroy(); lists.destroy(); kids.destroy(); for (const u of uni) u.destroy(); },
  };
}
