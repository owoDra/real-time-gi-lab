// Radiance-cascade runner (S1, S2): G-buffer + sun + voxel rebuild + radiance cascades, a static and a moving
// camera, GPU timestamps per pass, the band-boundary flicker counters, tracer statistics and captures.
import { createBuilding, type Building } from './building.ts';
import { buildBvh, bvhGpuLayout, refitBvh, type Bvh } from './bvh.ts';
import { cameraMatrices, FRAME_BYTES, octSolidAngles, packFrame, type Camera, type FrameParams } from './frame.ts';
import { createGBuffer, createGBufferRenderer, type GBuffer } from './gbuffer.ts';
import { createLighting, type Lighting } from './lighting.ts';
import { add3, cross, normalize, scale3, type Vec3 } from './math.ts';
import { createPost, EXCESS_K, EXCESS_LIN_SCALE, EXCESS_SCALE, EXCESS_SLOT, FLICKER_FIELDS, FLICKER_SLOT, MEXCESS_SLOT } from './post.ts';
import { createDdgi } from './ddgi.ts';
import { createGl2 } from './gl2.ts';
import { createRc, DEFAULT_PARAMS, RC_PASSES, type RcParams, type WorldResources } from './rc.ts';
import type { SceneGpu } from './scene_gpu.ts';
import { posedVertices, type SceneSpec } from './scenes.ts';
import { createDynLayer, DYN_MAX_BRICKS, DYN_STAGES, dynWork, mortonSortDynamic, type DynLayer } from './dynlayer.ts';
import { createVoxWorld, triangleTable, VOX_STAGES, VOX_UNIFORM_BYTES, voxParams, type VoxWorld } from './voxel.ts';

export const PASSES = ['gbuffer', 'shadow', 'direct', 'vox', ...RC_PASSES] as const;
const Q = 16; // timestamp slots per frame
const RC0 = 4; // first RC pass

// Response metric: frames per window of the held pose, frames between reads, tolerance on the change of the window's
// mean irradiance, most windows, frames after the switch read one by one.
const RESP_WINDOW = 1008, RESP_EVERY = 9, RESP_TOL = 0.01, RESP_MAX = 8, RESP_DENSE = 64;

export const SUN_E: Vec3 = [9, 8.5, 7.8];
export const SKY: Vec3 = [0.45, 0.6, 0.9];

export interface RunContext {
  device: GPUDevice; spec: SceneSpec; gpu: SceneGpu; g: GBuffer; frame: GPUBuffer; lighting: Lighting;
  gbuffer: ReturnType<typeof createGBufferRenderer>; omega0: Float32Array; width: number; height: number;
  world: WorldResources; voxWorld: VoxWorld | null; dynLayer: DynLayer | null; bvh: { buildMs: number; bytes: number; nodes: number } | null;
  /** Dynamic scenes with a BVH: refits it to the posed vertices (CPU, outside the GPU timing). */
  refitBvh: ((first: number, pos: Float32Array) => void) | null;
  /** Posed dynamic vertices by pose frame, computed on the CPU before the frames that use them are timed, so
   * that posing (and deforming, about 20 ms per frame at 64 objects) never leaves the GPU waiting between frames.
   * Shared by the configs of a run. */
  posed: Map<number, ReturnType<typeof posedVertices>>;
  /** Full-dynamic lane: the building changes every frame (scenes with -bwave / -bcut). */
  building: Building | null;
}

export function createRunContext(device: GPUDevice, spec: SceneSpec, gpu: SceneGpu,
  opts: { voxel: boolean; bvh: boolean; vox?: Record<string, unknown> }, width = 1920, height = 1080): RunContext {
  const g = createGBuffer(device, width, height);
  const frame = device.createBuffer({ label: 'frame', size: FRAME_BYTES, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  // Phase 32: every static scene is a world (chunks, clustered copies for the voxel build); only a world of several instances
  // (wide) has the camera-following shadow layers, instanced draws and the scrolling DDGI volume.
  const wide = spec.world && spec.world.instances.length > 1 ? spec.world : null;
  const lighting = createLighting(device, spec.scene, gpu, g, frame, spec.sunDir, wide);
  const S = GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST;
  const dummy = () => device.createBuffer({ size: 64, usage: S });
  const raster = triangleTable(spec.scene);
  if (spec.dynamic) mortonSortDynamic(raster, spec.dynamic.firstTriangle, spec.scene.positions);
  // Phase 32: the rows of the clustered copies of a world follow the scene's rows (not drawn).
  const table = spec.world ? new Uint32Array(raster.length + spec.world.lodTable.length) : raster;
  if (spec.world) { table.set(raster); table.set(spec.world.lodTable, raster.length); }
  const tri = device.createBuffer({ label: 'tri', size: table.byteLength, usage: S });
  device.queue.writeBuffer(tri, 0, table);
  if (spec.building && opts.bvh) throw new Error('a changing building needs no BVH (the BVH is built once)');
  if (wide && opts.bvh) throw new Error('no BVH for instanced worlds');
  const voxWorld = opts.voxel ? createVoxWorld(device, spec.scene, gpu, tri, table.length / 4, voxParams(opts.vox ?? {}), { frame, shadow: lighting.shadow },
    spec.dynamic?.firstTriangle, spec.world ?? null) : null;
  // P2: dynamic triangles are in the dynamic layer, read by the voxel tracers at the cone width.
  const dynLayer = voxWorld ? createDynLayer(device, gpu, tri, voxWorld.uniform, frame, lighting.shadow, voxWorld.params,
    spec.dynamic?.firstTriangle ?? spec.scene.triangleCount, spec.scene.triangleCount) : null;
  let bvh: RunContext['bvh'] = null, refit: RunContext['refitBvh'] = null;
  let bvhBuf = dummy();
  if (opts.bvh) {
    const b = buildBvh(spec.scene, raster);
    const L = bvhGpuLayout(b);
    bvhBuf = device.createBuffer({ label: 'bvh', size: L.bytes, usage: S });
    device.queue.writeBuffer(bvhBuf, 0, L.header); device.queue.writeBuffer(bvhBuf, L.nodesOff, b.nodes); device.queue.writeBuffer(bvhBuf, L.trisOff, b.tris);
    bvh = { buildMs: Math.round(b.buildMs), bytes: L.bytes, nodes: b.nodeCount };
    if (spec.dynamic) {
      const P = spec.scene.positions.slice(), firstTri = spec.dynamic.firstTriangle, buf = bvhBuf, bb: Bvh = b;
      refit = (first, pos) => {
        P.set(pos, first * 3);
        refitBvh(bb, P, raster, firstTri);
        device.queue.writeBuffer(buf, L.nodesOff, bb.nodes);
        device.queue.writeBuffer(buf, L.trisOff, bb.tris);
      };
    }
  }
  const voxUniform = voxWorld?.uniform ?? device.createBuffer({ size: VOX_UNIFORM_BYTES, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  const world: WorldResources = { voxUniform, vox: voxWorld?.vox ?? dummy(), dyn: dynLayer?.buffer ?? dummy(), dynArgs: dynLayer?.args ?? null, bvh: bvhBuf, materials: gpu.materials,
    baseColor: gpu.baseColor, shadow: lighting.shadow, hasVox: !!voxWorld, hasBvh: !!bvh, dynBricks: voxWorld?.params.dynBricks ?? DYN_MAX_BRICKS, maxBricks: voxWorld?.params.maxBricks ?? 0 };
  return { device, spec, gpu, g, frame, lighting, gbuffer: createGBufferRenderer(device, spec.scene, gpu, wide), omega0: octSolidAngles(4),
    width, height, world, voxWorld, dynLayer, bvh, refitBvh: refit, posed: new Map(),
    building: spec.building ? createBuilding(device, spec.scene, gpu, tri, table, spec.building, spec.world ?? null) : null };
}

/** Moving camera: walks 2.5 cm per frame along the view direction, swaying sideways and yawing. Phase 32 (D4, fly > 0): flies
 * along +x at `fly` m per frame, looking along +x and a little down, without sway. */
export function cameraPath(c0: Camera, fly = 0) {
  if (fly > 0) return (k: number): Camera => {
    const eye: Vec3 = [c0.eye[0] + fly * k, c0.eye[1], c0.eye[2]];
    return { eye, target: add3(eye, [1, -0.12, 0]), fovYDeg: c0.fovYDeg, near: c0.near };
  };
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
  return { median: r(percentile(s, 0.5)), mean: r(s.reduce((a, b) => a + b, 0) / s.length), p05: r(percentile(s, 0.05)), p95: r(percentile(s, 0.95)), p99: r(percentile(s, 0.99)), max: r(s[s.length - 1]) };
}

function halfToFloat(h: number) {
  const s = h & 0x8000 ? -1 : 1, e = (h >> 10) & 0x1f, m = h & 0x3ff;
  if (e === 0) return s * m * 2 ** -24;
  if (e === 31) return m ? NaN : s * Infinity;
  return s * (1 + m / 1024) * 2 ** (e - 15);
}

let halfLut: Float32Array | null = null;
const half = (h: number) => (halfLut ??= Float32Array.from({ length: 65536 }, (_, i) => halfToFloat(i)))[h];

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
      for (let c = 0; c < 3; c++) rgb[p * 3 + c] = half(src[o + c]);
      const a = half(src[o + 3]);
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
  /** Dynamic layer build timed per stage (one compute pass per stage, DYN_STAGES; the vox time is their sum) and its
   * work counted on the CPU (dynWork) every 24 measured frames of the static camera. The static bricks' stages (VOX_STAGES)
   * are timed too, before the dynamic layer's. */
  dynStages?: boolean;
  /** Dynamic scenes: hold the objects and the sun at this frame's pose. */
  poseFrame?: number;
  /** Static camera (moving camera with `moving`): capture the final and indirect images every `every` measured frames, `count` times. */
  seq?: { every: number; count: number; moving?: boolean; sink: (k: number, images: Record<string, Uint8Array>) => void };
  /** Phase 32 (D7): moving camera, the irradiance of every `every`-th measured frame (timings are disturbed). */
  dumpMoving?: { every: number; sink: (k: number, irr: Awaited<ReturnType<typeof readIrradiance>>, vox: unknown) => void };
  /** R1: static camera only; read the irradiance of every frame from `from` to `to` (inclusive, warm-up counted as
   * frame 0..) and return the response curve to a light switch at `from` (the scene's switch frame), against the
   * irradiance converged on the pose of frame `to`. Frames to 50% / 90% beyond 64 are multiples of 8. */
  response?: { from: number; to: number }; }

export async function runConfig(ctx: RunContext, params: RcParams, opts: RunOptions, log: (s: string) => void) {
  const { device, g, frame, lighting, gbuffer, spec, width, height, voxWorld } = ctx;
  if (opts.frames * Q > 4096) throw new Error('too many frames for one query set');
  const path = cameraPath(spec.camera, spec.fly);
  const static0 = spec.camera;
  const useVox = params.world === 'voxel' || params.relocate === 'voxel' || !!params.ddgi;

  // M1: fully dynamic scenes pose their objects and the sun per frame (t counts every frame of a run, warm-up included).
  let sunDir = spec.sunDir;
  let lastPosed: ReturnType<typeof posedVertices> | null = null;
  const posedAt = (f: number) => {
    let v = ctx.posed.get(f);
    if (!v) { v = posedVertices(spec.scene, spec.dynamic!, spec.dynamic!.at(f)); ctx.posed.set(f, v); }
    return v;
  };
  if (spec.dynamic && !opts.response) {
    const c0 = performance.now(), n = ctx.posed.size;
    for (let f = 0; f < opts.warmup + opts.frames; f++) posedAt(opts.poseFrame ?? f);
    if (ctx.posed.size > n) log(`  posed ${ctx.posed.size - n} frames on the CPU before timing in ${Math.round(performance.now() - c0)} ms`);
  }
  if (ctx.building) for (let f = 0; f < opts.warmup + opts.frames; f++) ctx.building.present(opts.poseFrame ?? f);
  const pose = (t: number) => {
    ctx.building?.apply(opts.poseFrame ?? t);
    const d = spec.dynamic;
    if (!d) return;
    const ps = d.at(opts.poseFrame ?? t);
    const v = posedAt(opts.poseFrame ?? t);
    lastPosed = v;
    device.queue.writeBuffer(ctx.gpu.positions, v.first * 12, v.pos);
    device.queue.writeBuffer(ctx.gpu.normals, v.first * 12, v.nrm);
    ctx.refitBvh?.(v.first, v.pos);
    sunDir = ps.sunDir;
    lighting.setSun(sunDir);
  };
  // Phase 32: an instanced world's shadow layers follow the camera, so they are placed before the frame is packed.
  const frameParams = (cam: Camera, prevCam: Camera, slot: number, prevValid: boolean, seed: number, p: RcParams): FrameParams => (lighting.setCamera(cam.eye), {
    cam, prevCam, lightViewProj: lighting.lightViewProj, shadow: { far: lighting.shadowFar, bias: lighting.shadowBias }, width, height, sunDir, sunE: SUN_E, sky: opts.sky,
    sMin: p.sMin, P: p.P, lift: p.lift, thicknessMin: p.thicknessMin, pxStride: p.pxStride, exposure: opts.exposure,
    cascades: p.cascades, slot, regStride: p.regStride, maxSteps: p.maxSteps, rayStride: p.rayStride, seed, prevValid, analytic: p.analytic, omega0: ctx.omega0,
    style: [p.styleEmit ? 1 : 0, p.styleRecv ? 1 : 0, p.rampSoft],
  });
  // Phase 32: a scrolling DDGI volume follows the camera (set once the field exists).
  let follow: ((eye: Vec3, fwd: Vec3) => void) | null = null;
  const setCamera = (cam: Camera) => {
    const m = cameraMatrices(cam, width, height);
    const camData = new Float32Array(36);
    camData.set(m.viewProj, 0); camData.set(m.view, 16); camData.set([...cam.eye, cam.near], 32);
    device.queue.writeBuffer(gbuffer.camera, 0, camData);
    gbuffer.cull(m.viewProj);
    follow?.(cam.eye, m.fwd);
    if (useVox) voxWorld!.update(cam.eye);
  };

  // Phase 21: with voxels (level 0 of 0.2 m), c0 probes are never spaced finer than a level-0 voxel. Finer probes near
  // the camera cannot be placed from the occupancy (they stay inside a surface's voxels, every probe of a pixel is
  // hidden and the pixel goes black: the near curtains on Sponza's moving camera).
  if (useVox && !params.ddgi) params = { ...params, sMin: Math.max(params.sMin, voxWorld!.params.v0) };
  // Sizing: run the world-probe build along the path with generous caps and keep the largest counts.
  let caps = params.caps;
  if (params.method !== 'screen' && !params.ddgi) {
    const sizing = createRc(device, g, lighting.lit, frame, { ...params, method: 'world', world: 'none', analytic: true, bounce: false, caps: DEFAULT_PARAMS.caps }, ctx.world);
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
  // Phase 31: only configs with the token obj let the dynamic objects receive and block the bounce (dynArgs), and only they
  // pay for the albedo of the dynamic layer.
  const world = { ...ctx.world, dynArgs: p.objects ? ctx.world.dynArgs : null };
  ctx.dynLayer?.setAlbedo(p.objects);
  const createField = () => p.gl2 ? createGl2(device, g, lighting, frame, spec.scene, ctx.gpu, p.gl2) : p.ddgi ? createDdgi(device, g, frame, p.ddgi, world, [spec.scene.boundsMin, spec.scene.boundsMax], !!spec.world && spec.world.instances.length > 1)
    : createRc(device, g, lighting.lit, frame, p, world);
  let rc = createField();
  follow = 'setCamera' in rc ? (e, f) => (rc as ReturnType<typeof createDdgi>).setCamera(e, f) : null;
  let post = createPost(device, g, frame, lighting.lit, rc.irr, 256);
  const querySet = device.createQuerySet({ type: 'timestamp', count: opts.frames * Q });
  const staged = !!opts.dynStages && useVox;
  const NV = staged ? VOX_STAGES.length * 2 : 0;
  const NS = NV + DYN_STAGES.length * 2;
  if (opts.frames * NS > 4096) throw new Error(`--dyn-stages: ${opts.frames} frames x ${NS} timestamps exceed one query set (4096); use fewer frames`);
  const stageSet = staged ? device.createQuerySet({ type: 'timestamp', count: opts.frames * NS }) : null;

  // Measurement only: the G-buffer without normal maps (the runs that give the flicker and excess floors).
  let geoNormals = false;
  const encodeFrame = (enc: GPUCommandEncoder, tw: <T>(pass: number) => T | undefined, k = -1) => {
    gbuffer.encode(enc, g, tw(0), geoNormals);
    lighting.encodeShadow(enc, tw(1));
    lighting.encodeDirect(enc, tw(2));
    if (staged) {
      voxWorld!.encodeStaged(enc, k >= 0 ? stageSet : null, k * NS);
      ctx.dynLayer!.encodeStaged(enc, k >= 0 ? stageSet : null, k * NS + NV);
    }
    else if (useVox) {
      const pass = enc.beginComputePass({ label: 'vox', timestampWrites: tw(3) });
      voxWorld!.encode(pass);
      ctx.dynLayer!.encode(pass);
      pass.end();
    }
    rc.encode(enc, (i) => tw(RC0 + i));
  };

  // Work of the dynamic layer build at the current pose (CPU, mirrors the shaders).
  const triTable = staged && spec.dynamic ? triangleTable(spec.scene) : null;
  const countWork = (v: ReturnType<typeof posedVertices>) => {
    const vp = voxWorld!.params, P = spec.scene.positions.slice();
    P.set(v.pos, v.first * 3);
    const eye = spec.camera.eye;
    const origin = Array.from({ length: vp.levels }, (_, L) => [0, 1, 2].map((a) => Math.floor(eye[a] / (vp.v0 * 2 ** L * 8)) - vp.G / 2));
    return dynWork(triTable!, spec.dynamic!.firstTriangle, spec.scene.triangleCount, P, vp, origin);
  };

  async function run(mode: 'static' | 'moving', geo = false) {
    geoNormals = geo;
    post.clearCounters();
    let firstFinal: Uint8Array | null = null;
    const work: ReturnType<typeof dynWork>[] = [];
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
      encodeFrame(enc, tw, k);
      if (triTable && mode === 'static' && k >= 0 && k % 24 === 0 && lastPosed) work.push(countWork(lastPosed));
      post.encodeChainExcess(enc);
      post.encodeFlicker(enc);
      if (mode === 'static') post.encodeExcess(enc);
      device.queue.submit([enc.finish()]);
      pending.push(device.queue.onSubmittedWorkDone());
      if (pending.length >= opts.inFlight) await pending.shift();
      // A changing building must change the image (checked against the last frame after the run).
      if (ctx.building && mode === 'static' && !geo && k === 0 && opts.poseFrame === undefined) { await Promise.all(pending.splice(0)); firstFinal = await post.capture(0); }
      if (mode === (opts.seq?.moving ? 'moving' : 'static') && !geo && opts.seq && k >= 0 && k % opts.seq.every === 0 && k / opts.seq.every < opts.seq.count) {
        await Promise.all(pending.splice(0));
        opts.seq.sink(k, { final: await post.capture(0), indirect: await post.capture(1) });
      }
      if (mode === 'moving' && !geo && opts.dumpMoving && k >= 0 && k % opts.dumpMoving.every === 0) {
        await Promise.all(pending.splice(0));
        opts.dumpMoving.sink(k, await readIrradiance(device, rc.irr, width, height), useVox ? await voxWorld!.readCounters() : null);
      }
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
    if (staged) {
      // vox = the sum of the stage passes.
      const sres = device.createBuffer({ size: opts.frames * NS * 8, usage: GPUBufferUsage.QUERY_RESOLVE | GPUBufferUsage.COPY_SRC });
      const sread = device.createBuffer({ size: opts.frames * NS * 8, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
      const e2 = device.createCommandEncoder();
      e2.resolveQuerySet(stageSet!, 0, opts.frames * NS, sres, 0);
      e2.copyBufferToBuffer(sres, 0, sread, 0, opts.frames * NS * 8);
      device.queue.submit([e2.finish()]);
      await sread.mapAsync(GPUMapMode.READ);
      const sts = new BigUint64Array(sread.getMappedRange().slice(0));
      sread.unmap(); sread.destroy(); sres.destroy();
      const stageNames = [...VOX_STAGES.map((st) => `vox.${st}`), ...DYN_STAGES.map((st) => `dyn.${st}`)];
      for (const st of stageNames) passMs[st] = [];
      passMs.vox = [];
      for (let k = 0; k < opts.frames; k++) {
        let sum = 0;
        stageNames.forEach((st, i) => { const ms = Number(sts[k * NS + 2 * i + 1] - sts[k * NS + 2 * i]) / 1e6; passMs[st].push(ms); sum += ms; });
        passMs.vox.push(sum);
        passMs.giTotal[k] = passMs.giSum[k] + sum;
      }
    }
    const timing = Object.fromEntries(Object.entries(passMs).map(([n, v]) => [n, stats(v)]));
    const dynWorkStats = work.length ? Object.fromEntries(Object.keys(work[0]).filter((key) => key !== 'bricksPerLevel').map((key) => {
      const v = work.map((w) => (w as any)[key] as number);
      return [key, { min: Math.min(...v), mean: Math.round(v.reduce((a, b) => a + b, 0) / v.length), max: Math.max(...v) }];
    })) : null;

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
      staticFinePct: pct(15, 14), staticPixelsPerFrame: Math.round(tot[14] / (opts.frames - 1)),
      fields: FLICKER_FIELDS,
    };
    // Excess variation (static camera): per K, mean over pixel windows of excess / (K - 1) and tv / (K - 1), in stops per frame.
    let excess: Record<string, Record<string, number | null>> | null = null;
    if (mode === 'static') {
      const ex = await post.readExcess(opts.frames);
      const r5 = (x: number) => Math.round(x * 1e5) / 1e5;
      excess = Object.fromEntries(EXCESS_K.map((K, i) => {
        let n = 0, tv = 0, e = 0;
        for (let k = 0; k < opts.frames; k++) { const b = k * EXCESS_SLOT + i * 3; n += ex[b]; tv += ex[b + 1]; e += ex[b + 2]; }
        const per = (s: number) => n ? r5(s / EXCESS_SCALE / n / (K - 1)) : null;
        return [`k${K}`, { windows: Math.floor(opts.frames / K), pixelWindows: n, excessPerFrame: per(e), tvPerFrame: per(tv), excessShare: tv ? r5(e / tv) : null }];
      }));
      let le = 0, lt = 0, lm = 0;
      for (let k = 0; k < opts.frames; k++) { const b = k * EXCESS_SLOT + 9; le += ex[b]; lt += ex[b + 1]; lm += ex[b + 2]; }
      // Relative to the mean irradiance (per frame): sum excess / sum window mean / 15.
      excess.k16linear = { excessRelPerFrame: lm ? r5(le / lm / 15) : null, tvRelPerFrame: lm ? r5(lt / lm / 15) : null, meanIrradiance: excess.k16.pixelWindows ? r5(lm / EXCESS_LIN_SCALE / excess.k16.pixelWindows) : null };
    }
    // Excess along reprojected chains (K = 16; on the static camera it equals excess.k16).
    const mx = await post.readChainExcess(opts.frames);
    const ms = new Array(MEXCESS_SLOT).fill(0);
    for (let k = 0; k < opts.frames; k++) for (let j = 0; j < MEXCESS_SLOT; j++) ms[j] += mx[k * MEXCESS_SLOT + j];
    const r5c = (x: number) => Math.round(x * 1e5) / 1e5;
    const perC = (s: number) => ms[0] ? r5c(s / EXCESS_SCALE / ms[0] / 15) : null;
    const chainExcess = { windows: Math.floor(opts.frames / 16), pixelWindows: ms[0], pixelWindowsPerWindow: Math.round(ms[0] / Math.max(Math.floor(opts.frames / 16), 1)),
      excessPerFrame: perC(ms[2]), tvPerFrame: perC(ms[1]), controlExcessPerFrame: perC(ms[4]), controlTvPerFrame: perC(ms[3]),
      excessRelPerFrame: ms[7] ? r5c(ms[5] / ms[7] / 15) : null, tvRelPerFrame: ms[7] ? r5c(ms[6] / ms[7] / 15) : null };
    const counts = await rc.readCounts();
    const vox = useVox ? { ...await voxWorld!.readCounters(), dyn: await ctx.dynLayer!.readCounters() } : null;
    const images: Record<string, Uint8Array> = {};
    for (const [name, m] of [['final', 0], ['indirect', 1], ['direct', 2], ['flicker', 3]] as const) images[name] = await post.capture(m);
    if (mode === 'static') { post.encodeExcessMap(Math.floor(opts.frames / 16)); images.excess = await post.capture(3); }
    else images.excess = await post.capture(4);
    const irr = mode === 'static' && !geo ? await readIrradiance(device, rc.irr, width, height) : null;
    geoNormals = false;
    // Share of pixels whose final colour changed by more than 2 levels between the first and the last measured frame.
    let buildingChange: { changedPct: number; presentFirst: number; presentLast: number } | null = null;
    if (firstFinal) {
      const a = firstFinal, b = images.final;
      let changed = 0;
      for (let q = 0; q < a.length; q += 4) if (Math.abs(a[q] - b[q]) > 2 || Math.abs(a[q + 1] - b[q + 1]) > 2 || Math.abs(a[q + 2] - b[q + 2]) > 2) changed++;
      const r4 = (x: number) => Math.round(x * 1e4) / 1e4;
      buildingChange = { changedPct: r4(changed / (a.length / 4) * 100), presentFirst: r4(ctx.building!.present(opts.warmup)), presentLast: r4(ctx.building!.present(opts.warmup + opts.frames - 1)) };
      if (buildingChange.changedPct < 0.5) throw new Error(`the building changes but the image did not: ${JSON.stringify(buildingChange)}`);
    }
    // Black photoreal pixels of the last frame (RC: every c0 probe found hidden), percent of the photoreal pixels.
    let blackPct: number | null = null;
    if (irr && !p.ddgi && !p.gl2) {
      let ph = 0;
      for (let q = 0; q < irr.tag.length; q++) if (irr.tag[q] === 1) ph++;
      let nb = 0;
      for (let j = 72; j < 80; j++) nb += counts[j];
      blackPct = ph ? Math.round(nb / ph * 1e5) / 1e3 : null;
    }
    return { timing, flicker, excess, chainExcess, blackPct, counts: Array.from(counts.slice(0, p.ddgi ? 4 : p.cascades)), overflow: Array.from(counts.slice(8, 8 + p.cascades)),
      insertFailures: Array.from(counts.slice(16, 16 + p.cascades)), usedBytes: rc.usedBytes(counts),
      vox: vox ? { ...vox, ...voxWorld!.usedBytes(vox) } : null, buildingChange, dynWork: dynWorkStats, dynWorkLast: work.length && lastPosed ? countWork(lastPosed) : null, images, irr };
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

  // R1: response to a light switch (static camera). E_t is read every frame for RESP_DENSE frames after the switch and
  // every 8th frame after that (a long run does not fit in memory otherwise); the curve is
  // sum |E_t - E_end| / sum |E_(from-1) - E_end| over photoreal pixels (luminance).
  // E_end is the converged irradiance of the pose after the switch (phase 27): the pose of frame `to` is held and the
  // run goes on in windows of RESP_WINDOW frames, read every RESP_EVERY frames. E_end is the mean of the first window
  // whose mean irradiance (summed over the pixels) differs from the previous window's by less than RESP_TOL, or of the
  // last window at RESP_MAX windows (end.converged false). A field that does not change at all over the first reads
  // (no history, no noise) is taken as it is. The last frame of the run is not the converged value of a method with
  // a long history: it made the curve reach 0 at `to` whatever the method. The test is on the summed irradiance of a
  // long window because a stochastic field never stops changing pixel by pixel (the mean of 7 frames still differs
  // from the next 7 by 1 % for the linear DDGI comparator and by 7-9 % for its fast settings, converged or not).
  if (opts.response) {
    const { from, to } = opts.response;
    const lums: Float32Array[] = [];
    let prev = static0;
    const step = async (f: number, poseAt: number, read: boolean) => {
      pose(poseAt);
      device.queue.writeBuffer(frame, 0, packFrame(frameParams(static0, prev, 0, f > 0, f + 1, p)));
      setCamera(static0);
      const enc = device.createCommandEncoder();
      encodeFrame(enc, () => undefined);
      device.queue.submit([enc.finish()]);
      if (!read) { if (f % 8 === 7) await device.queue.onSubmittedWorkDone(); return null; }
      const ir = await readIrradiance(device, rc.irr, width, height);
      const l = new Float32Array(ir.valid.length);
      for (let q = 0; q < l.length; q++) l[q] = ir.valid[q] && ir.tag[q] < 2 ? lum(ir.rgb[q * 3], ir.rgb[q * 3 + 1], ir.rgb[q * 3 + 2]) : NaN;
      return l;
    };
    const at: number[] = []; // frames after the switch of lums[1..]
    for (let f = 0; f <= to; f++) {
      const l = await step(f, f, f >= from - 1 && (f - from < RESP_DENSE || (f - from) % 8 === 7 || f === to));
      if (l) { lums.push(l); if (f >= from) at.push(f - from + 1); }
    }
    const before = lums[0];
    let end = new Float32Array(before.length), endChange: number | null = null, windows = 0, f = to + 1, lastSum = 0, still = true;
    const sums: number[] = [];
    while (windows < RESP_MAX && !(endChange !== null && Math.abs(endChange) < RESP_TOL)) {
      const mean = new Float32Array(before.length), reads = RESP_WINDOW / RESP_EVERY;
      let first: Float32Array | null = null;
      for (let i = 0; i < RESP_WINDOW; i++, f++) {
        const l = await step(f, to, i % RESP_EVERY === RESP_EVERY - 1);
        if (!l) continue;
        for (let q = 0; q < l.length; q++) mean[q] += l[q] / reads;
        if (windows === 0 && still) {
          if (!first) first = l;
          else for (let q = 0; q < l.length && still; q++) if (l[q] !== first[q] && !(Number.isNaN(l[q]) && Number.isNaN(first[q]))) still = false;
          if (still && i >= 7 * RESP_EVERY) { end = l; break; }
        }
      }
      if (windows === 0 && still) { endChange = 0; windows = 1; f++; break; }
      let sum = 0;
      for (let q = 0; q < mean.length; q++) if (!Number.isNaN(mean[q])) sum += mean[q];
      if (windows > 0) endChange = (sum - lastSum) / lastSum;
      sums.push(sum); lastSum = sum; end = mean; windows++;
    }
    let d0 = 0;
    for (let q = 0; q < end.length; q++) if (!Number.isNaN(end[q]) && !Number.isNaN(before[q])) d0 += Math.abs(before[q] - end[q]);
    const curve = lums.slice(1).map((l) => {
      let d = 0;
      for (let q = 0; q < end.length; q++) if (!Number.isNaN(end[q]) && !Number.isNaN(l[q])) d += Math.abs(l[q] - end[q]);
      return Math.round(d / d0 * 1e4) / 1e4;
    });
    // First frame from which the curve stays at or below x (null: not within the frames read).
    const firstBelow = (x: number) => { const i = curve.findIndex((c, k) => c <= x && curve.slice(k).every((v) => v <= x)); return i < 0 ? null : at[i]; };
    rc.destroy(); post.destroy(); querySet.destroy();
    const r5 = (x: number) => Math.round(x * 1e5) / 1e5;
    return { params: p, response: { from, to, curve, curveFrames: at, frames90: firstBelow(0.1), frames50: firstBelow(0.5),
      end: { poseFrame: to, framesHeld: f - to - 1, still, windows, lastWindowChange: endChange === null ? null : r5(endChange),
        converged: endChange !== null && Math.abs(endChange) < RESP_TOL, windowMeans: sums.map((x) => r5(x / sums[sums.length - 1])) } } };
  }

  // Full-dynamic lane: every frame really changes the whole building. Wave: share of the building's vertices that move
  // between two consecutive measured frames (read back from the GPU). There is no path that skips unchanged geometry:
  // every frame voxelises all static triangles (voxWorld.staticTriangles).
  async function buildingMotion() {
    const b = ctx.building;
    if (!b || b.spec.kind !== 'wave' || opts.poseFrame !== undefined) return null;
    const n = b.spec.vertexCount;
    const read = async (t: number) => {
      b.apply(t);
      const buf = device.createBuffer({ size: n * 12, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
      const enc = device.createCommandEncoder();
      enc.copyBufferToBuffer(ctx.gpu.positions, 0, buf, 0, n * 12);
      device.queue.submit([enc.finish()]);
      await buf.mapAsync(GPUMapMode.READ);
      const a = new Float32Array(buf.getMappedRange().slice(0));
      buf.unmap(); buf.destroy();
      return a;
    };
    const t = opts.warmup + Math.floor(opts.frames / 2);
    const a = await read(t), c = await read(t + 1);
    let moved = 0;
    for (let v = 0; v < n; v++) if (Math.hypot(a[v * 3] - c[v * 3], a[v * 3 + 1] - c[v * 3 + 1], a[v * 3 + 2] - c[v * 3 + 2]) > 1e-5) moved++;
    return { frames: [t, t + 1], buildingVertices: n, movedShare: Math.round(moved / n * 1e4) / 1e4, staticTrianglesVoxelisedPerFrame: voxWorld?.staticTriangles() ?? null };
  }

  log(`  static`);
  const st = await run('static');
  const motion = await buildingMotion();
  if (motion) log(`  building motion ${JSON.stringify(motion)}`);
  const tracer = await traceStats();
  let mv = null;
  if (spec.moving && !opts.staticOnly) { log(`  moving`); mv = await run('moving'); }
  // The same runs without normal maps (phase 27): on a moving camera or a moving building a reprojected pixel lands on
  // another texel of the normal map, which the flicker and excess metrics count as a change of the irradiance. These
  // runs give the metrics without that; their timings are not used.
  const metrics = (r: Awaited<ReturnType<typeof run>>) => ({ flicker: r.flicker, excess: r.excess, chainExcess: r.chainExcess, overflow: r.overflow, insertFailures: r.insertFailures,
    images: { indirect: r.images.indirect, flicker: r.images.flicker, excess: r.images.excess } });
  let stGeo = null, mvGeo = null;
  const ddgiDims = 'dims' in rc ? (rc as ReturnType<typeof createDdgi>).dims : null, allocatedBytes = rc.bytes;
  if (!opts.dynStages && !opts.seq) {
    // A new field: a method with a history starts these runs from the same state as the runs above.
    rc.destroy(); post.destroy();
    rc = createField(); post = createPost(device, g, frame, lighting.lit, rc.irr, 256);
    log(`  static, geometric normals`);
    stGeo = metrics(await run('static', true));
    if (mv) { log(`  moving, geometric normals`); mvGeo = metrics(await run('moving', true)); }
  }
  rc.destroy(); post.destroy(); querySet.destroy(); stageSet?.destroy();
  return { params: p, buildingMotion: motion, ddgiDims, allocatedBytes, voxAllocatedBytes: useVox ? voxWorld!.bytes : 0, dynAllocatedBytes: useVox ? ctx.dynLayer!.bytes : 0, static: st, moving: mv, staticGeo: stGeo, movingGeo: mvGeo, tracer };
}

/** Voxel rebuild alone, one pass per stage, static camera. */
export async function benchVoxels(ctx: RunContext, frames: number) {
  const { device, voxWorld, spec } = ctx;
  if (!voxWorld) throw new Error('no voxel world');
  const names = VOX_STAGES;
  const n = names.length * 2;
  const querySet = device.createQuerySet({ type: 'timestamp', count: frames * n });
  voxWorld.update(spec.camera.eye);
  for (let f = 0; f < 10 + frames; f++) {
    const enc = device.createCommandEncoder();
    if (f >= 10) voxWorld.encodeStaged(enc, querySet, (f - 10) * n);
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
