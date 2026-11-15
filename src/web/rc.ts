// Browser radiance-cascade runs: the same src/core/ code as src/native/rc.ts, run by the page web/rc.html in a browser's
// WebGPU. Served and driven by src/native/browser.ts, which stores what this page posts (log lines, PNGs, summaries,
// irradiance dumps) under its output directory.
// URL parameters mirror the native flags: scene, configs, frames, warmup, exposure, nosky, static (--static-only),
// seedfixed, pose (--pose-frame), vox (JSON), params (JSON), dumpirr, bvh, dynstages, response (FROM,TO), seq (EVERY,COUNT), voxbench.
import jpeg from 'jpeg-js';
import type { Vec3 } from '../core/math.ts';
import type { RcParams } from '../core/rc.ts';
import { benchVoxels, createRunContext, runConfig, SKY, type RunOptions } from '../core/rcrun.ts';
import { TEXTURE_SIZE, uploadScene, type ImageUploader } from '../core/scene_gpu.ts';
import { parseConfig } from '../runner/configs.ts';
import { packIrradiance, reportConfig } from '../runner/report.ts';
import { loadScene } from '../runner/scene.ts';
import { toTextureSize } from '../runner/texture.ts';
import { decodePng } from './png.ts';

const SPONZA = '/assets/glTF-Sample-Assets/Models/Sponza/glTF/';
const logEl = document.getElementById('log')!;
// Posts go one after another, so the driver prints the log lines in order.
let chain: Promise<unknown> = Promise.resolve();
const post = (path: string, body: BodyInit) => { chain = chain.then(() => fetch(path, { method: 'POST', body })); };
const log = (s: string) => { logEl.textContent += s + '\n'; post('/log', s); };

async function loadSponza() {
  const json = await (await fetch(SPONZA + 'Sponza.gltf')).json();
  const bin = await (await fetch(SPONZA + json.buffers[0].uri)).arrayBuffer();
  // Decoded in script (jpeg-js as natively, PNG by png.ts) so that the texels equal the native runner's.
  const upload: ImageUploader = async (dev, texture, layer, imageIndex) => {
    const uri: string = json.images[imageIndex].uri;
    const buf = await (await fetch(SPONZA + uri)).arrayBuffer();
    const img = uri.endsWith('.png') ? await decodePng(buf)
      : jpeg.decode(new Uint8Array(buf), { useTArray: true, formatAsRGBA: true, maxMemoryUsageInMB: 2048 });
    dev.queue.writeTexture({ texture, origin: [0, 0, layer] }, toTextureSize(img) as Uint8Array<ArrayBuffer>, { bytesPerRow: TEXTURE_SIZE * 4 }, [TEXTURE_SIZE, TEXTURE_SIZE, 1]);
  };
  return { json, bin, upload };
}

async function main() {
  const q = new URLSearchParams(location.search);
  const has = (k: string) => q.has(k);
  const sceneArg = q.get('scene') ?? 'sponza';
  const configs = (q.get('configs') ?? 'world-48-voxel-rc2-vrel').split(',');
  const opts: RunOptions = { warmup: Number(q.get('warmup') ?? 60), frames: Number(q.get('frames') ?? 240), inFlight: 2,
    exposure: Number(q.get('exposure') ?? 1), seedFixed: has('seedfixed'), staticOnly: has('static'),
    sky: (has('nosky') ? [0, 0, 0] : SKY) as Vec3, poseFrame: has('pose') ? Number(q.get('pose')) : undefined, dynStages: has('dynstages'),
    response: has('response') ? (([a, b]) => ({ from: a, to: b }))(q.get('response')!.split(',').map(Number)) : undefined,
    seq: has('seq') ? (([every, count]) => ({ every, count, sink: (k: number, im: Record<string, Uint8Array>) => {
      for (const [img, rgba] of Object.entries(im)) post(`/out/seq.${String(k).padStart(3, '0')}.${img}.png?w=1920&h=1080`, new Blob([rgba as Uint8Array<ArrayBuffer>])); } }))(q.get('seq')!.split(',').map(Number)) : undefined };
  const overrides = JSON.parse(q.get('params') ?? '{}') as Partial<RcParams>;
  const parsed = configs.map((c) => [c, parseConfig(c, overrides)] as const);

  if (!navigator.gpu) throw new Error('navigator.gpu is not available');
  const adapter = await navigator.gpu.requestAdapter({ powerPreference: 'high-performance' });
  if (!adapter) throw new Error('no WebGPU adapter');
  const info = adapter.info;
  const adapterInfo = { vendor: info.vendor, architecture: info.architecture, device: info.device, description: info.description,
    isFallbackAdapter: (info as GPUAdapterInfo & { isFallbackAdapter?: boolean }).isFallbackAdapter ?? null };
  log(`adapter ${JSON.stringify(adapterInfo)}; user agent ${navigator.userAgent}`);
  if (adapterInfo.isFallbackAdapter || /swiftshader/i.test(`${info.architecture} ${info.description}`)) log('WARNING: software adapter (SwiftShader); the times are not GPU times');
  if (!adapter.features.has('timestamp-query')) throw new Error('no timestamp-query on this adapter');
  // WebGPU's default limits: nothing in requiredLimits.
  const device = await adapter.requestDevice({ requiredFeatures: ['timestamp-query'] });
  device.addEventListener('uncapturederror', (e) => log('WebGPU error: ' + (e as GPUUncapturedErrorEvent).error.message));
  log(`limits: maxStorageBufferBindingSize ${device.limits.maxStorageBufferBindingSize}, maxBufferSize ${device.limits.maxBufferSize}, maxStorageBuffersPerShaderStage ${device.limits.maxStorageBuffersPerShaderStage}`);

  const t0 = performance.now();
  const { spec, upload } = await loadScene(sceneArg, loadSponza);
  const gpu = await uploadScene(device, spec.scene, upload);
  const needVox = has('voxbench') || parsed.some(([, p]) => p.world === 'voxel' || p.relocate === 'voxel');
  const needBvh = has('bvh') || parsed.some(([, p]) => p.world === 'tri');
  const ctx = createRunContext(device, spec, gpu, { voxel: needVox, bvh: needBvh, vox: JSON.parse(q.get('vox') ?? '{}') });
  log(`scene ${spec.name}: ${spec.scene.triangleCount} triangles, loaded in ${Math.round(performance.now() - t0)} ms`
    + (ctx.bvh ? `; BVH ${ctx.bvh.nodes} nodes, ${(ctx.bvh.bytes / 2 ** 20).toFixed(1)} MiB, built in ${ctx.bvh.buildMs} ms (CPU)` : ''));
  const implementation = `browser WebGPU (${navigator.userAgent})`;
  if (has('voxbench')) {
    const r = await benchVoxels(ctx, 60);
    log(JSON.stringify(r));
    post(`/out/vox-bench.json`, JSON.stringify({ kind: 'exploratory (探索値)', date: new Date().toISOString(), implementation, adapter: adapterInfo,
      scene: { name: spec.name, triangles: spec.scene.triangleCount }, voxParams: ctx.voxWorld!.params, ...r }, null, 2));
    device.destroy();
    return;
  }
  for (const [name, params] of parsed) {
    log(`${name}`);
    const r0 = await runConfig(ctx, params, opts, log);
    if (r0.response) {
      const rr = r0.response;
      log(`  response: 90% after ${rr.frames90} frames, 50% after ${rr.frames50}; end value ${JSON.stringify(rr.end)}; curve ${rr.curve.slice(0, 12).join(', ')} ... last ${rr.curve[rr.curve.length - 1]}`);
      post(`/out/${name}.response.json`, JSON.stringify({ kind: 'exploratory (探索値)', date: new Date().toISOString(), platform: 'browser', scene: spec.name, config: name, params: r0.params, ...rr }, null, 2));
      await chain;
      continue;
    }
    const r = r0 as Required<typeof r0>;
    for (const [mode, res] of [['static', r.static], ['moving', r.moving], ['static-geo', r.staticGeo], ['moving-geo', r.movingGeo]] as const)
      if (res) for (const [img, rgba] of Object.entries(res.images)) post(`/out/${name}.${mode}.${img}.png?w=${ctx.width}&h=${ctx.height}`, new Blob([rgba as Uint8Array<ArrayBuffer>]));
    if (has('dumpirr') && r.static.irr) post(`/out/${name}.static.irr.f32`, new Blob([packIrradiance(r.static.irr)]));
    const summary = reportConfig(name, r, ctx, opts, { platform: 'browser', implementation, adapter: adapterInfo }, log);
    post(`/out/${name}.summary.json`, JSON.stringify(summary, null, 2));
    await chain;
  }
  device.destroy();
}

main().then(async () => { await chain; await fetch('/done', { method: 'POST', body: 'ok' }); },
  async (e) => { log('ERROR: ' + (e?.stack ?? e)); await chain.catch(() => undefined); await fetch('/done', { method: 'POST', body: 'error' }); });
