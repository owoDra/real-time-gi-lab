// Radiance-cascade runner (S1, S2): G-buffer + sun + voxel rebuild + radiance cascades, a static and a moving
// camera, GPU timestamps per pass, the band-boundary flicker counters, tracer statistics and captures.
import { buildBvh } from './bvh.ts';
import { cameraMatrices, FRAME_BYTES, octSolidAngles, packFrame, type Camera, type FrameParams } from './frame.ts';
import { createGBuffer, createGBufferRenderer, type GBuffer } from './gbuffer.ts';
import { createLighting, type Lighting } from './lighting.ts';
import { add3, cross, normalize, scale3, type Vec3 } from './math.ts';
import { createPost, FLICKER_FIELDS, FLICKER_SLOT } from './post.ts';
import { createDdgi } from './ddgi.ts';
import { createRc, DEFAULT_PARAMS, RC_PASSES, type RcParams, type WorldResources } from './rc.ts';
import type { SceneGpu } from './scene_gpu.ts';
import { posedVertices, type SceneSpec } from './scenes.ts';
import { createVoxWorld, DEFAULT_VOX, triangleTable, VOX_LOCAL_STAGES, VOX_STAGES, type VoxParams, type VoxWorld } from './voxel.ts';

export const PASSES = ['gbuffer', 'shadow', 'direct', 'vox', ...RC_PASSES] as const;
const Q = 16; // timestamp slots per frame
const RC0 = 4; // first RC pass

export const SUN_E: Vec3 = [9, 8.5, 7.8];
export const SKY: Vec3 = [0.45, 0.6, 0.9];

export interface RunContext {
  device: GPUDevice; spec: SceneSpec; gpu: SceneGpu; g: GBuffer; frame: GPUBuffer; lighting: Lighting;
  gbuffer: ReturnType<typeof createGBufferRenderer>; omega0: Float32Array; width: number; height: number;
  world: WorldResources; voxWorld: VoxWorld | null; bvh: { buildMs: number; bytes: number; nodes: number } | null;
}

export function createRunContext(device: GPUDevice, spec: SceneSpec, gpu: SceneGpu,
  opts: { voxel: boolean; bvh: boolean; vox?: Partial<VoxParams> }, width = 1920, height = 1080): RunContext {
  const g = createGBuffer(device, width, height);
  const frame = device.createBuffer({ label: 'frame', size: FRAME_BYTES, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  const lighting = createLighting(device, spec.scene, gpu, g, frame, spec.sunDir);
  const S = GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST;
  const dummy = () => device.createBuffer({ size: 64, usage: S });
  const table = triangleTable(spec.scene);
  const tri = device.createBuffer({ label: 'tri', size: table.byteLength, usage: S });
  device.queue.writeBuffer(tri, 0, table);
  const dv = spec.dynamic ? { first: spec.dynamic.objects[0].firstVertex,
    count: spec.dynamic.objects.reduce((n, o) => n + o.vertexCount, 0) } : undefined;
  const voxWorld = opts.voxel ? createVoxWorld(device, spec.scene, gpu, tri, { ...DEFAULT_VOX, ...opts.vox }, spec.dynamic?.firstTriangle, dv) : null;
  let bvh: RunContext['bvh'] = null;
  let bvhNodes = dummy(), bvhTris = dummy();
  if (opts.bvh) {
    const b = buildBvh(spec.scene, table);
    bvhNodes = device.createBuffer({ label: 'bvh.nodes', size: b.nodes.byteLength, usage: S });
    bvhTris = device.createBuffer({ label: 'bvh.tris', size: b.tris.byteLength, usage: S });
    device.queue.writeBuffer(bvhNodes, 0, b.nodes); device.queue.writeBuffer(bvhTris, 0, b.tris);
    bvh = { buildMs: Math.round(b.buildMs), bytes: b.nodes.byteLength + b.tris.byteLength, nodes: b.nodeCount };
  }
  const voxUniform = voxWorld?.uniform ?? device.createBuffer({ size: 48 + 8 * 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  const world: WorldResources = { voxUniform, vox: voxWorld?.vox ?? dummy(), bvhNodes, bvhTris, materials: gpu.materials,
    baseColor: gpu.baseColor, shadow: lighting.shadow, hasVox: !!voxWorld, hasBvh: !!bvh };
  return { device, spec, gpu, g, frame, lighting, gbuffer: createGBufferRenderer(device, spec.scene, gpu), omega0: octSolidAngles(4),
    width, height, world, voxWorld, bvh };
}

/** Moving camera: walks 2.5 cm per frame along the view direction, swaying sideways and yawing. */
export function cameraPath(c0: Camera) {
  const f = normalize([c0.target[0] - c0.eye[0], 0, c0.target[2] - c0.eye[2]]);
  const side = normalize(cross(f, [0, 1, 0]));
  return (k: number): Camera => {
    const eye = add3(add3(c0.eye, scale3(f, 0.025 * k)), scale3(side, 0.4 * Math.sin(2 * Math.PI * k / 240)));
    const yaw = (12 * Math.PI / 180) * Math.sin(2 * Math.PI * k / 160);
    const dir: Vec3 = [f[0] * Math.cos(yaw) - f[2] * Math.sin(yaw), (c0.target[1] - c0.eye[1]) / Math.hypot(c0.target[0] - c0.eye[0], c0.target[2] - c0.eye[2]), f[0] * Math.sin(yaw) + f[2] * Math.cos(yaw)];
    return { eye, target: add3(eye, dir), fovYDeg: c0.fovYDeg, near: c0.near };
  };
}

function percentile(sorted: number[], q: number) {
  const i = (sorted.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
}
function stats(ms: number[]) {
  const s = [...ms].sort((a, b) => a - b);
  const r = (x: number) => Math.round(x * 1000) / 1000;
  return { median: r(percentile(s, 0.5)), mean: r(s.reduce((a, b) => a + b, 0) / s.length), p05: r(percentile(s, 0.05)), p95: r(percentile(s, 0.95)), max: r(s[s.length - 1]) };
}

function halfToFloat(h: number) {
  const s = h & 0x8000 ? -1 : 1, e = (h >> 10) & 0x1f, m = h & 0x3ff;
  if (e === 0) return s * m * 2 ** -24;
  if (e === 31) return m ? NaN : s * Infinity;
  return s * (1 + m / 1024) * 2 ** (e - 15);
}

/** Indirect irradiance (rgb), validity and the gather's tag (1 photoreal, >= 2 toon) of every pixel. */
export async function readIrradiance(device: GPUDevice, tex: GPUTexture, width: number, height: number) {
  const bytesPerRow = Math.ceil(width * 8 / 256) * 256;
  const buf = device.createBuffer({ size: bytesPerRow * height, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
  const enc = device.createCommandEncoder();
  enc.copyTextureToBuffer({ texture: tex }, { buffer: buf, bytesPerRow }, [width, height]);
  device.queue.submit([enc.finish()]);
  await buf.mapAsync(GPUMapMode.READ);
  const src = new Uint16Array(buf.getMappedRange().slice(0));
  buf.unmap(); buf.destroy();
  const rgb = new Float32Array(width * height * 3), valid = new Uint8Array(width * height), tag = new Uint8Array(width * height);
  for (let y = 0; y < height; y++)
    for (let x = 0; x < width; x++) {
      const o = y * bytesPerRow / 2 + x * 4, p = y * width + x;
      for (let c = 0; c < 3; c++) rgb[p * 3 + c] = halfToFloat(src[o + c]);
      const a = halfToFloat(src[o + 3]);
      valid[p] = a > 0.5 ? 1 : 0; tag[p] = Math.round(a);
    }
  return { rgb, valid, tag };
}

export const lum = (r: number, g: number, b: number) => 0.2126 * r + 0.7152 * g + 0.0722 * b;

/** Error of an irradiance image against a reference, over photoreal pixels valid in both. */
export function compareIrradiance(a: { rgb: Float32Array; valid: Uint8Array; tag: Uint8Array }, ref: { rgb: Float32Array; valid: Uint8Array; tag: Uint8Array }) {
  let sa = 0, sr = 0, sabs = 0, n = 0;
  const rel: number[] = [];
  for (let p = 0; p < ref.valid.length; p++) {
    if (!a.valid[p] || !ref.valid[p] || a.tag[p] >= 2 || ref.tag[p] >= 2) continue;
    const la = lum(a.rgb[p * 3], a.rgb[p * 3 + 1], a.rgb[p * 3 + 2]), lr = lum(ref.rgb[p * 3], ref.rgb[p * 3 + 1], ref.rgb[p * 3 + 2]);
    sa += la; sr += lr; sabs += Math.abs(la - lr); n++;
    if (p % 7 === 0) rel.push(Math.abs(la - lr) / Math.max(lr, 1e-3));
  }
  rel.sort((x, y) => x - y);
  const r = (x: number) => Math.round(x * 1e4) / 1e4;
  return { pixels: n, meanRef: r(sr / n), meanThis: r(sa / n), bias: r((sa - sr) / sr), meanAbsRel: r(sabs / sr),
    medianRel: r(percentile(rel, 0.5)), p90Rel: r(percentile(rel, 0.9)) };
}

export interface RunOptions { warmup: number; frames: number; inFlight: number; exposure: number; sky: Vec3; seedFixed?: boolean; staticOnly?: boolean;
  /** Dynamic scenes: hold the objects and the sun at this frame's pose. */
  poseFrame?: number;
  /** R1: static camera only; read the irradiance of every frame from `from` to `to` (inclusive, warm-up counted as
   * frame 0..) and return the response curve to a light switch at `from` (the scene's switch frame). */
  response?: { from: number; to: number }; }

export async function runConfig(ctx: RunContext, params: RcParams, opts: RunOptions, log: (s: string) => void) {
  const { device, g, frame, lighting, gbuffer, spec, width, height, voxWorld } = ctx;
  if (opts.frames * Q > 4096) throw new Error('too many frames for one query set');
  const path = cameraPath(spec.camera);
  const static0 = spec.camera;
  const useVox = params.world === 'voxel' || params.relocate === 'voxel' || !!params.ddgi;

  // M1: fully dynamic scenes pose their objects and the sun per frame (t counts every frame of a run, warm-up included).
  let sunDir = spec.sunDir;
  const pose = (t: number) => {
    const d = spec.dynamic;
    if (!d) return;
    const ps = d.at(opts.poseFrame ?? t);
    const v = posedVertices(spec.scene, d, ps);
    device.queue.writeBuffer(ctx.gpu.positions, v.first * 12, v.pos);
    device.queue.writeBuffer(ctx.gpu.normals, v.first * 12, v.nrm);
    ctx.voxWorld?.h4Frame(opts.poseFrame ?? t, v.first, v.pos);
    sunDir = ps.sunDir;
    lighting.setSun(sunDir);
  };
  const frameParams = (cam: Camera, prevCam: Camera, slot: number, prevValid: boolean, seed: number, p: RcParams): FrameParams => ({
    cam, prevCam, lightViewProj: lighting.lightViewProj, width, height, sunDir, sunE: SUN_E, sky: opts.sky,
    sMin: p.sMin, P: p.P, lift: p.lift, thicknessMin: p.thicknessMin, pxStride: p.pxStride, exposure: opts.exposure,
    cascades: p.cascades, slot, regStride: p.regStride, maxSteps: p.maxSteps, rayStride: p.rayStride, seed, prevValid, analytic: p.analytic, omega0: ctx.omega0,
    style: [p.styleEmit ? 1 : 0, p.styleRecv ? 1 : 0, p.rampSoft],
  });
  const setCamera = (cam: Camera) => {
    const m = cameraMatrices(cam, width, height);
    const camData = new Float32Array(36);
    camData.set(m.viewProj, 0); camData.set(m.view, 16); camData.set([...cam.eye, cam.near], 32);
    device.queue.writeBuffer(gbuffer.camera, 0, camData);
    if (useVox) voxWorld!.update(cam.eye);
  };

  // Sizing: run the world-probe build along the path with generous caps and keep the largest counts.
  let caps = params.caps;
  if (params.method !== 'screen' && !params.ddgi) {
    const sizing = createRc(device, g, lighting.lit, frame, { ...params, method: 'world', world: 'none', analytic: true, caps: DEFAULT_PARAMS.caps }, ctx.world);
    const maxCount = new Array(params.cascades).fill(0);
    let overflow = 0;
    for (let k = -1; k < (spec.moving ? 240 : 0); k += 12) {
      const cam = k < 0 ? static0 : path(k);
      pose(Math.max(k, 0));
      device.queue.writeBuffer(frame, 0, packFrame(frameParams(cam, cam, 0, false, 0, params)));
      setCamera(cam);
      const enc = device.createCommandEncoder();
      gbuffer.encode(enc, g); lighting.encodeShadow(enc); lighting.encodeDirect(enc); sizing.encode(enc, () => undefined);
      device.queue.submit([enc.finish()]);
      const c = await sizing.readCounts();
      for (let i = 0; i < params.cascades; i++) { maxCount[i] = Math.max(maxCount[i], c[i]); overflow += c[8 + i] + c[16 + i]; }
    }
    sizing.destroy();
    if (overflow > 0) throw new Error(`sizing caps overflowed: ${overflow}`);
    caps = maxCount.map((n) => Math.max(256, Math.ceil(n * 1.25 / 256) * 256));
    log(`  sizing: max probes per cascade ${maxCount.join(', ')} -> caps ${caps.join(', ')}`);
  }
  const p = { ...params, caps };
  const rc = p.ddgi ? createDdgi(device, g, frame, p.ddgi, ctx.world, [spec.scene.boundsMin, spec.scene.boundsMax])
    : createRc(device, g, lighting.lit, frame, p, ctx.world);
  const post = createPost(device, g, frame, lighting.lit, rc.irr, 256);
  const querySet = device.createQuerySet({ type: 'timestamp', count: opts.frames * Q });

  const encodeFrame = (enc: GPUCommandEncoder, tw: <T>(pass: number) => T | undefined) => {
    gbuffer.encode(enc, g, tw(0));
    lighting.encodeShadow(enc, tw(1));
    lighting.encodeDirect(enc, tw(2));
    if (useVox) voxWorld!.encode(enc, tw(3));
    rc.encode(enc, (i) => tw(RC0 + i));
  };

  async function run(mode: 'static' | 'moving') {
    post.clearCounters();
    const pending: Promise<undefined>[] = [];
    let prev = mode === 'static' ? static0 : path(0);
    for (let f = 0; f < opts.warmup + opts.frames; f++) {
      const k = f - opts.warmup;
      const cam = mode === 'static' ? static0 : path(Math.max(k, 0));
      const seed = opts.seedFixed ? 1 : f + 1;
      pose(f);
      device.queue.writeBuffer(frame, 0, packFrame(frameParams(cam, prev, Math.max(k, 0), k >= 1, seed, p)));
      setCamera(cam);
      prev = cam;
      const tw = <T>(pass: number): T | undefined => k >= 0
        ? { querySet, beginningOfPassWriteIndex: k * Q + 2 * pass, endOfPassWriteIndex: k * Q + 2 * pass + 1 } as T : undefined;
      const enc = device.createCommandEncoder();
      encodeFrame(enc, tw);
      post.encodeFlicker(enc);
      device.queue.submit([enc.finish()]);
      pending.push(device.queue.onSubmittedWorkDone());
      if (pending.length >= opts.inFlight) await pending.shift();
    }
    await Promise.all(pending);

    const size = opts.frames * Q * 8;
    const resolveBuf = device.createBuffer({ size, usage: GPUBufferUsage.QUERY_RESOLVE | GPUBufferUsage.COPY_SRC });
    const read = device.createBuffer({ size, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
    const enc = device.createCommandEncoder();
    enc.resolveQuerySet(querySet, 0, opts.frames * Q, resolveBuf, 0);
    enc.copyBufferToBuffer(resolveBuf, 0, read, 0, size);
    device.queue.submit([enc.finish()]);
    await read.mapAsync(GPUMapMode.READ);
    const ts = new BigUint64Array(read.getMappedRange().slice(0));
    read.unmap(); read.destroy(); resolveBuf.destroy();
    const names = PASSES.filter((n) => n !== 'vox' || useVox);
    const passMs: Record<string, number[]> = Object.fromEntries([...names, 'giSum', 'giTotal'].map((n) => [n, []]));
    for (let k = 0; k < opts.frames; k++) {
      let rcMs = 0, voxMs = 0;
      PASSES.forEach((name, i) => {
        if (!(name in passMs)) return;
        const ms = Number(ts[k * Q + 2 * i + 1] - ts[k * Q + 2 * i]) / 1e6;
        passMs[name].push(ms);
        if (i >= RC0) rcMs += ms;
        if (name === 'vox') voxMs = ms;
      });
      passMs.giSum.push(rcMs);
      passMs.giTotal.push(rcMs + voxMs);
    }
    const timing = Object.fromEntries(Object.entries(passMs).map(([n, v]) => [n, stats(v)]));

    const cnt = await post.readCounters(opts.frames);
    const tot = new Array(FLICKER_SLOT).fill(0);
    let worstFine = 0;
    for (let k = 1; k < opts.frames; k++) {
      for (let j = 0; j < FLICKER_SLOT; j++) tot[j] += cnt[k * FLICKER_SLOT + j];
      if (cnt[k * FLICKER_SLOT] > 0) worstFine = Math.max(worstFine, cnt[k * FLICKER_SLOT + 1] / cnt[k * FLICKER_SLOT]);
    }
    const pct = (j: number, d: number) => tot[d] ? Math.round(tot[j] / tot[d] * 1e5) / 1e3 : null; // percent, 3 decimals
    const rate = (j: number) => pct(j, 0);
    // Photoreal pixels: all valid pixels minus the toon ones.
    const photo = tot[0] - tot[7];
    const flicker = {
      validPixelsPerFrame: Math.round(tot[0] / (opts.frames - 1)),
      giFinePct: rate(1), giCoarsePct: rate(2), controlFinePct: rate(3), controlCoarsePct: rate(4),
      giMeanAbsDlog2: Math.round(tot[5] / tot[0]) / 1000, controlMeanAbsDlog2: Math.round(tot[6] / tot[0]) / 1000,
      giFineWorstFramePct: Math.round(worstFine * 1e5) / 1e3,
      photoFinePct: photo ? Math.round((tot[1] - tot[8]) / photo * 1e5) / 1e3 : null,
      photoCoarsePct: photo ? Math.round((tot[2] - tot[9]) / photo * 1e5) / 1e3 : null,
      toonPixelsPerFrame: Math.round(tot[7] / (opts.frames - 1)),
      toonFinePct: pct(8, 7), toonCoarsePct: pct(9, 7), toonMeanAbsDlog2: tot[7] ? Math.round(tot[13] / tot[7]) / 1000 : null,
      toonSignificantPct: pct(12, 7), toonRampChangePct: pct(10, 12), controlRampChangePct: pct(11, 7),
      fields: FLICKER_FIELDS.slice(0, 14),
    };
    const counts = await rc.readCounts();
    const vox = useVox ? await voxWorld!.readCounters() : null;
    const images: Record<string, Uint8Array> = {};
    for (const [name, m] of [['final', 0], ['indirect', 1], ['direct', 2], ['flicker', 3]] as const) images[name] = await post.capture(m);
    const irr = mode === 'static' ? await readIrradiance(device, rc.irr, width, height) : null;
    return { timing, flicker, counts: Array.from(counts.slice(0, p.ddgi ? 4 : p.cascades)), overflow: Array.from(counts.slice(8, 8 + p.cascades)),
      insertFailures: Array.from(counts.slice(16, 16 + p.cascades)), usedBytes: rc.usedBytes(counts),
      vox: vox ? { ...vox, ...voxWorld!.usedBytes(vox) } : null, images, irr };
  }

  // Tracer statistics on the static camera: DDA steps per interval and, with a BVH, voxel / triangle visibility.
  async function traceStats() {
    if (p.world !== 'voxel' || p.ddgi) return null;
    rc.setStats(ctx.bvh ? 2 : 1);
    pose(0);
    device.queue.writeBuffer(frame, 0, packFrame(frameParams(static0, static0, 0, false, 1, p)));
    setCamera(static0);
    const enc = device.createCommandEncoder();
    encodeFrame(enc, () => undefined);
    device.queue.submit([enc.finish()]);
    const c = await rc.readCounts();
    rc.setStats(0);
    return Array.from({ length: p.cascades }, (_, i) => {
      const n = c[24 + i];
      const r = (x: number) => Math.round(x * 1e4) / 1e4;
      return { intervals: n, meanSteps: n ? r(c[32 + i] / n) : 0, atStepCap: c[64 + i],
        ...(ctx.bvh ? { voxHitTriMiss: r(c[40 + i] / Math.max(n, 1)), voxMissTriHit: r(c[48 + i] / Math.max(n, 1)), bothHit: r(c[56 + i] / Math.max(n, 1)) } : {}) };
    });
  }

  // R1: response to a light switch (static camera). E_t is read every frame; the curve is
  // sum |E_t - E_end| / sum |E_(from-1) - E_end| over photoreal pixels (luminance), E_end the last frame.
  if (opts.response) {
    const { from, to } = opts.response;
    const lums: Float32Array[] = [];
    let prev = static0;
    for (let f = 0; f <= to; f++) {
      pose(f);
      device.queue.writeBuffer(frame, 0, packFrame(frameParams(static0, prev, 0, f > 0, f + 1, p)));
      setCamera(static0);
      const enc = device.createCommandEncoder();
      encodeFrame(enc, () => undefined);
      device.queue.submit([enc.finish()]);
      if (f >= from - 1) {
        const ir = await readIrradiance(device, rc.irr, width, height);
        const l = new Float32Array(ir.valid.length);
        for (let q = 0; q < l.length; q++) l[q] = ir.valid[q] && ir.tag[q] < 2 ? lum(ir.rgb[q * 3], ir.rgb[q * 3 + 1], ir.rgb[q * 3 + 2]) : NaN;
        lums.push(l);
      } else if (f % 8 === 7) await device.queue.onSubmittedWorkDone();
    }
    const end = lums[lums.length - 1], before = lums[0];
    let d0 = 0;
    for (let q = 0; q < end.length; q++) if (!Number.isNaN(end[q]) && !Number.isNaN(before[q])) d0 += Math.abs(before[q] - end[q]);
    const curve = lums.slice(1).map((l) => {
      let d = 0;
      for (let q = 0; q < end.length; q++) if (!Number.isNaN(end[q]) && !Number.isNaN(l[q])) d += Math.abs(l[q] - end[q]);
      return Math.round(d / d0 * 1e4) / 1e4;
    });
    const firstBelow = (x: number) => { const i = curve.findIndex((c, k) => c <= x && curve.slice(k).every((v) => v <= x)); return i < 0 ? null : i + 1; };
    rc.destroy(); querySet.destroy();
    return { params: p, response: { from, to, curve, frames90: firstBelow(0.1), frames50: firstBelow(0.5) } };
  }

  log(`  static`);
  const st = await run('static');
  const tracer = await traceStats();
  let mv = null;
  if (spec.moving && !opts.staticOnly) { log(`  moving`); mv = await run('moving'); }
  rc.destroy(); querySet.destroy();
  return { params: p, ddgiDims: 'dims' in rc ? rc.dims : null, allocatedBytes: rc.bytes, voxAllocatedBytes: useVox ? voxWorld!.bytes : 0, static: st, moving: mv, tracer };
}

/** Voxel rebuild alone, one pass per stage, static camera. */
export async function benchVoxels(ctx: RunContext, frames: number) {
  const { device, voxWorld, spec } = ctx;
  if (!voxWorld) throw new Error('no voxel world');
  const names = voxWorld.params.local ? VOX_LOCAL_STAGES : VOX_STAGES;
  const n = names.length * 2;
  const querySet = device.createQuerySet({ type: 'timestamp', count: frames * n });
  voxWorld.update(spec.camera.eye);
  for (let f = 0; f < 10 + frames; f++) {
    const enc = device.createCommandEncoder();
    if (f >= 10) voxWorld.encodeStaged(enc, querySet, (f - 10) * n); else voxWorld.encode(enc);
    device.queue.submit([enc.finish()]);
    if (f % 4 === 3) await device.queue.onSubmittedWorkDone();
  }
  await device.queue.onSubmittedWorkDone();
  const size = frames * n * 8;
  const resolveBuf = device.createBuffer({ size, usage: GPUBufferUsage.QUERY_RESOLVE | GPUBufferUsage.COPY_SRC });
  const read = device.createBuffer({ size, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
  const enc = device.createCommandEncoder();
  enc.resolveQuerySet(querySet, 0, frames * n, resolveBuf, 0);
  enc.copyBufferToBuffer(resolveBuf, 0, read, 0, size);
  device.queue.submit([enc.finish()]);
  await read.mapAsync(GPUMapMode.READ);
  const ts = new BigUint64Array(read.getMappedRange().slice(0));
  read.unmap(); read.destroy(); resolveBuf.destroy(); querySet.destroy();
  const per: Record<string, number[]> = Object.fromEntries([...names, 'total'].map((s) => [s, []]));
  for (let f = 0; f < frames; f++) {
    let tot = 0;
    names.forEach((s, i) => { const ms = Number(ts[f * n + 2 * i + 1] - ts[f * n + 2 * i]) / 1e6; per[s].push(ms); tot += ms; });
    per.total.push(tot);
  }
  const counters = await voxWorld.readCounters();
  return { stages: Object.fromEntries(Object.entries(per).map(([k, v]) => [k, stats(v)])), counters, bytes: voxWorld.usedBytes(counters), allocated: voxWorld.bytes };
}
