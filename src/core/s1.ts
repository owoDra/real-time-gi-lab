// S1 runner: G-buffer + sun + radiance cascades, a static and a moving camera, GPU timestamps per pass,
// the band-boundary flicker counters and captures.
import { s0Camera } from './bench.ts';
import { cameraMatrices, octSolidAngles, packFrame, type Camera, type FrameParams } from './frame.ts';
import { createGBuffer, createGBufferRenderer, type GBuffer } from './gbuffer.ts';
import type { SceneData } from './gltf.ts';
import { createLighting, type Lighting } from './lighting.ts';
import { add3, cross, normalize, scale3, type Vec3 } from './math.ts';
import { createPost, FLICKER_FIELDS } from './post.ts';
import { createRc, DEFAULT_PARAMS, RC_PASSES, type RcParams } from './rc.ts';
import type { SceneGpu } from './scene_gpu.ts';

export const PASSES = ['gbuffer', 'shadow', 'direct', ...RC_PASSES] as const;
const Q = 16; // timestamp slots per frame

export const SUN_DIR: Vec3 = [-0.15, 1, 0.1];
const SUN_E: Vec3 = [9, 8.5, 7.8];
export const SKY: Vec3 = [0.45, 0.6, 0.9];

export interface S1Context {
  device: GPUDevice; scene: SceneData; gpu: SceneGpu; g: GBuffer; frame: GPUBuffer; lighting: Lighting;
  gbuffer: ReturnType<typeof createGBufferRenderer>; omega0: Float32Array; width: number; height: number;
}

export function createS1Context(device: GPUDevice, scene: SceneData, gpu: SceneGpu, width = 1920, height = 1080): S1Context {
  const g = createGBuffer(device, width, height);
  const frame = device.createBuffer({ label: 'frame', size: 136 * 4, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  const lighting = createLighting(device, scene, gpu, g, frame, SUN_DIR);
  return { device, scene, gpu, g, frame, lighting, gbuffer: createGBufferRenderer(device, scene, gpu), omega0: octSolidAngles(4), width, height };
}

/** Moving camera: walks 2.5 cm per frame along the S0 view direction, swaying sideways and yawing. */
export function cameraPath(scene: SceneData) {
  const c0 = s0Camera(scene);
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
  return { median: r(percentile(s, 0.5)), p05: r(percentile(s, 0.05)), p95: r(percentile(s, 0.95)), max: r(s[s.length - 1]) };
}

export interface RunOptions { warmup: number; frames: number; inFlight: number; exposure: number; sky: Vec3; seedFixed?: boolean; }

export async function runConfig(ctx: S1Context, params: RcParams, opts: RunOptions, log: (s: string) => void) {
  const { device, g, frame, lighting, gbuffer, scene, width, height } = ctx;
  if (opts.frames * Q > 4096) throw new Error('too many frames for one query set');
  const path = cameraPath(scene);
  const static0 = s0Camera(scene);

  const frameParams = (cam: Camera, prevCam: Camera, slot: number, prevValid: boolean, seed: number, p: RcParams): FrameParams => ({
    cam, prevCam, lightViewProj: lighting.lightViewProj, width, height, sunDir: SUN_DIR, sunE: SUN_E, sky: opts.sky,
    sMin: p.sMin, P: p.P, lift: p.lift, thicknessMin: p.thicknessMin, pxStride: p.pxStride, exposure: opts.exposure,
    cascades: p.cascades, slot, regStride: p.regStride, maxSteps: p.maxSteps, rayStride: p.rayStride, seed, prevValid, analytic: p.analytic, omega0: ctx.omega0,
  });
  const setCamera = (cam: Camera) => {
    const m = cameraMatrices(cam, width, height);
    const camData = new Float32Array(36);
    camData.set(m.viewProj, 0); camData.set(m.view, 16); camData.set([...cam.eye, cam.near], 32);
    device.queue.writeBuffer(gbuffer.camera, 0, camData);
  };

  // Sizing: run the world-probe build along the path with generous caps and keep the largest counts.
  let caps = params.caps;
  if (params.method !== 'screen') {
    const sizing = createRc(device, g, lighting.lit, frame, { ...params, method: 'world', caps: DEFAULT_PARAMS.caps });
    const maxCount = new Array(params.cascades).fill(0);
    let overflow = 0;
    for (let k = -1; k < 240; k += 12) {
      const cam = k < 0 ? static0 : path(k);
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
  const rc = createRc(device, g, lighting.lit, frame, p);
  const post = createPost(device, g, frame, lighting.lit, rc.irr, 256);
  const querySet = device.createQuerySet({ type: 'timestamp', count: opts.frames * Q });

  async function run(mode: 'static' | 'moving') {
    post.clearCounters();
    const pending: Promise<undefined>[] = [];
    let prev = mode === 'static' ? static0 : path(0);
    for (let f = 0; f < opts.warmup + opts.frames; f++) {
      const k = f - opts.warmup;
      const cam = mode === 'static' ? static0 : path(Math.max(k, 0));
      const seed = opts.seedFixed ? 1 : f + 1;
      device.queue.writeBuffer(frame, 0, packFrame(frameParams(cam, prev, Math.max(k, 0), k >= 1, seed, p)));
      setCamera(cam);
      prev = cam;
      const tw = <T>(pass: number): T | undefined => k >= 0
        ? { querySet, beginningOfPassWriteIndex: k * Q + 2 * pass, endOfPassWriteIndex: k * Q + 2 * pass + 1 } as T : undefined;
      const enc = device.createCommandEncoder();
      gbuffer.encode(enc, g, tw(0));
      lighting.encodeShadow(enc, tw(1));
      lighting.encodeDirect(enc, tw(2));
      rc.encode(enc, (i) => tw(3 + i));
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
    const passMs: Record<string, number[]> = Object.fromEntries([...PASSES, 'giSum', 'giSpan'].map((n) => [n, []]));
    for (let k = 0; k < opts.frames; k++) {
      let gi = 0;
      PASSES.forEach((name, i) => {
        const ms = Number(ts[k * Q + 2 * i + 1] - ts[k * Q + 2 * i]) / 1e6;
        passMs[name].push(ms);
        if (i >= 3) gi += ms;
      });
      passMs.giSum.push(gi);
      passMs.giSpan.push(Number(ts[k * Q + 2 * (PASSES.length - 1) + 1] - ts[k * Q + 6]) / 1e6);
    }
    const timing = Object.fromEntries(Object.entries(passMs).map(([n, v]) => [n, stats(v)]));

    const cnt = await post.readCounters(opts.frames);
    const tot = new Array(8).fill(0);
    let worstFine = 0;
    for (let k = 1; k < opts.frames; k++) {
      for (let j = 0; j < 8; j++) tot[j] += cnt[k * 8 + j];
      if (cnt[k * 8] > 0) worstFine = Math.max(worstFine, cnt[k * 8 + 1] / cnt[k * 8]);
    }
    const rate = (j: number) => Math.round(tot[j] / tot[0] * 1e5) / 1e3; // percent, 3 decimals
    const flicker = {
      validPixelsPerFrame: Math.round(tot[0] / (opts.frames - 1)),
      giFinePct: rate(1), giCoarsePct: rate(2), controlFinePct: rate(3), controlCoarsePct: rate(4),
      giMeanAbsDlog2: Math.round(tot[5] / tot[0]) / 1000, controlMeanAbsDlog2: Math.round(tot[6] / tot[0]) / 1000,
      giFineWorstFramePct: Math.round(worstFine * 1e5) / 1e3,
      fields: FLICKER_FIELDS.slice(0, 7),
    };
    const counts = await rc.readCounts();
    const images: Record<string, Uint8Array> = {};
    for (const [name, mode] of [['final', 0], ['indirect', 1], ['direct', 2], ['flicker', 3]] as const) images[name] = await post.capture(mode);
    return { timing, flicker, counts: Array.from(counts.slice(0, p.cascades)), overflow: Array.from(counts.slice(8, 8 + p.cascades)),
      insertFailures: Array.from(counts.slice(16, 16 + p.cascades)), usedBytes: rc.usedBytes(counts), images };
  }

  log(`  static`);
  const st = await run('static');
  log(`  moving`);
  const mv = await run('moving');
  rc.destroy(); querySet.destroy();
  return { params: p, allocatedBytes: rc.bytes, static: st, moving: mv };
}
