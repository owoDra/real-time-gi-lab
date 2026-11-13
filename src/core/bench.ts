// S0 benchmark: render the Sponza G-buffer repeatedly and read back per-pass GPU timestamps.
import { lookAt, mul, perspectiveReversedInfinite, type Vec3 } from './math.ts';
import { parseGltf, type SceneData } from './gltf.ts';
import { uploadScene, type ImageUploader } from './scene_gpu.ts';
import { createGBuffer, createGBufferRenderer, createVisualizer, gbufferBytes, VIZ_MODES } from './gbuffer.ts';

export interface BenchOptions { width: number; height: number; warmup: number; frames: number; inFlight: number; }
export const DEFAULT_OPTIONS: BenchOptions = { width: 1920, height: 1080, warmup: 120, frames: 600, inFlight: 2 };

export interface BenchResult {
  options: BenchOptions;
  scene: { triangles: number; vertices: number; draws: number; materials: number; textures: number };
  camera: { eye: Vec3; target: Vec3; fovYDeg: number; near: number };
  timestampsAvailable: boolean;
  /** Per-frame G-buffer pass GPU time in nanoseconds (empty if timestamps are unavailable). */
  passNs: number[];
  /** Smallest non-zero difference between distinct raw timestamps (hints at quantisation). */
  timestampGranularityNs: number | null;
  stats: { medianMs: number; p05Ms: number; p95Ms: number; minMs: number; maxMs: number; meanMs: number } | null;
  memoryBytes: { scene: number; gbuffer: number };
  loadMs: number;
  images: Record<string, Uint8Array>;
}

/** Fixed S0 camera: inside the atrium, looking down its long (X) axis. */
export function s0Camera(scene: SceneData) {
  const [x0, y0, z0] = scene.boundsMin, [x1, y1, z1] = scene.boundsMax;
  const eye: Vec3 = [x1 - 0.12 * (x1 - x0), y0 + 0.12 * (y1 - y0), (z0 + z1) / 2];
  const target: Vec3 = [x0, y0 + 0.30 * (y1 - y0), (z0 + z1) / 2];
  return { eye, target, fovYDeg: 60, near: 0.05 };
}

function percentile(sorted: number[], q: number) {
  const i = (sorted.length - 1) * q, lo = Math.floor(i), hi = Math.ceil(i);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
}

export async function runGBufferBench(
  device: GPUDevice, gltfJson: any, bin: ArrayBuffer, upload: ImageUploader, options: BenchOptions,
  log: (s: string) => void = () => {},
): Promise<BenchResult> {
  const t0 = performance.now();
  const scene = parseGltf(gltfJson, bin);
  log(`parsed: ${scene.triangleCount} triangles, ${scene.primitives.length} primitives`);
  const gpu = await uploadScene(device, scene, upload);
  const loadMs = performance.now() - t0;
  log(`uploaded in ${loadMs.toFixed(0)} ms`);

  const { width, height, warmup, frames, inFlight } = options;
  const g = createGBuffer(device, width, height);
  const renderer = createGBufferRenderer(device, scene, gpu);
  const cam = s0Camera(scene);
  const view = lookAt(cam.eye, cam.target, [0, 1, 0]);
  const proj = perspectiveReversedInfinite(cam.fovYDeg * Math.PI / 180, width / height, cam.near);
  const camData = new Float32Array(36);
  camData.set(mul(proj, view), 0); camData.set(view, 16); camData.set([...cam.eye, cam.near], 32);
  device.queue.writeBuffer(renderer.camera, 0, camData);

  const timestampsAvailable = device.features.has('timestamp-query');
  const querySet = timestampsAvailable ? device.createQuerySet({ type: 'timestamp', count: frames * 2 }) : null;

  const pending: Promise<undefined>[] = [];
  for (let f = 0; f < warmup + frames; f++) {
    const enc = device.createCommandEncoder();
    const k = f - warmup;
    renderer.encode(enc, g, querySet && k >= 0 ? { querySet, beginningOfPassWriteIndex: 2 * k, endOfPassWriteIndex: 2 * k + 1 } : undefined);
    device.queue.submit([enc.finish()]);
    pending.push(device.queue.onSubmittedWorkDone());
    if (pending.length >= inFlight) await pending.shift();
  }
  await Promise.all(pending);

  let passNs: number[] = [], granularity: number | null = null;
  if (querySet) {
    const size = frames * 2 * 8;
    const resolve = device.createBuffer({ size, usage: GPUBufferUsage.QUERY_RESOLVE | GPUBufferUsage.COPY_SRC });
    const read = device.createBuffer({ size, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
    const enc = device.createCommandEncoder();
    enc.resolveQuerySet(querySet, 0, frames * 2, resolve, 0);
    enc.copyBufferToBuffer(resolve, 0, read, 0, size);
    device.queue.submit([enc.finish()]);
    await read.mapAsync(GPUMapMode.READ);
    const ts = new BigUint64Array(read.getMappedRange().slice(0));
    read.unmap();
    passNs = Array.from({ length: frames }, (_, k) => Number(ts[2 * k + 1] - ts[2 * k]));
    const sortedRaw = Array.from(ts, Number).sort((a, b) => a - b);
    for (let i = 1; i < sortedRaw.length; i++) {
      const d = sortedRaw[i] - sortedRaw[i - 1];
      if (d > 0 && (granularity === null || d < granularity)) granularity = d;
    }
  }
  const sorted = [...passNs].sort((a, b) => a - b).map((ns) => ns / 1e6);
  const stats = sorted.length ? {
    medianMs: percentile(sorted, 0.5), p05Ms: percentile(sorted, 0.05), p95Ms: percentile(sorted, 0.95),
    minMs: sorted[0], maxMs: sorted[sorted.length - 1], meanMs: sorted.reduce((a, b) => a + b, 0) / sorted.length,
  } : null;

  const viz = createVisualizer(device, g, cam.near);
  const images: Record<string, Uint8Array> = {};
  for (let m = 0; m < VIZ_MODES.length; m++) images[VIZ_MODES[m]] = await viz.capture(m);

  return {
    options,
    scene: { triangles: scene.triangleCount, vertices: scene.positions.length / 3, draws: renderer.drawCount,
      materials: scene.materials.length, textures: scene.imageUris.length },
    camera: cam, timestampsAvailable, passNs, timestampGranularityNs: granularity, stats,
    memoryBytes: { scene: gpu.bytes, gbuffer: gbufferBytes(g) }, loadMs, images,
  };
}
