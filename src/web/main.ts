// Browser S0 run. Served by tools/serve.ts, which stores the posted results under out/s0/web/.
import { runGBufferBench, DEFAULT_OPTIONS } from '../core/bench.ts';
import { TEXTURE_SIZE, type ImageUploader } from '../core/scene_gpu.ts';
import { summarize } from '../core/report.ts';

const SCENE = '/assets/glTF-Sample-Assets/Models/Sponza/glTF/';
const logEl = document.getElementById('log')!;
const log = (s: string) => { logEl.textContent += s + '\n'; };

async function main() {
  const q = new URLSearchParams(location.search);
  const options = { ...DEFAULT_OPTIONS, frames: Number(q.get('frames') ?? DEFAULT_OPTIONS.frames), warmup: Number(q.get('warmup') ?? DEFAULT_OPTIONS.warmup) };
  if (!navigator.gpu) throw new Error('navigator.gpu is not available');
  const adapter = await navigator.gpu.requestAdapter({ powerPreference: 'high-performance' });
  if (!adapter) throw new Error('no WebGPU adapter');
  const info = adapter.info;
  log(`adapter: ${info.vendor} / ${info.architecture} / ${info.description}`);
  if (info.architecture === 'swiftshader' || /swiftshader/i.test(info.description)) log('WARNING: software adapter (SwiftShader); numbers are not GPU numbers');
  const device = await adapter.requestDevice({ requiredFeatures: adapter.features.has('timestamp-query') ? ['timestamp-query'] : [] });
  device.addEventListener('uncapturederror', (e) => log('WebGPU error: ' + (e as GPUUncapturedErrorEvent).error.message));

  const json = await (await fetch(SCENE + 'Sponza.gltf')).json();
  const bin = await (await fetch(SCENE + json.buffers[0].uri)).arrayBuffer();
  const upload: ImageUploader = async (dev, texture, layer, imageIndex) => {
    const blob = await (await fetch(SCENE + json.images[imageIndex].uri)).blob();
    const bmp = await createImageBitmap(blob, {
      colorSpaceConversion: 'none', premultiplyAlpha: 'none', resizeWidth: TEXTURE_SIZE, resizeHeight: TEXTURE_SIZE, resizeQuality: 'pixelated',
    });
    dev.queue.copyExternalImageToTexture({ source: bmp }, { texture, origin: [0, 0, layer] }, [TEXTURE_SIZE, TEXTURE_SIZE]);
    bmp.close();
  };

  const result = await runGBufferBench(device, json, bin, upload, options, log);
  const summary = summarize(result, {
    platform: 'web', implementation: 'browser WebGPU', userAgent: navigator.userAgent,
    adapter: { vendor: info.vendor, architecture: info.architecture, device: info.device, description: info.description },
  });
  log(JSON.stringify(summary.gbufferPass, null, 2));
  log(`timestamp granularity: ${summary.timestampGranularityNs} ns`);

  // Show the albedo image on the page.
  const canvas = document.getElementById('view') as HTMLCanvasElement;
  canvas.width = options.width; canvas.height = options.height;
  canvas.getContext('2d')!.putImageData(new ImageData(new Uint8ClampedArray(result.images.albedo), options.width, options.height), 0, 0);

  await fetch('/result/summary.json', { method: 'POST', body: JSON.stringify(summary, null, 2) });
  await fetch('/result/pass_ns.json', { method: 'POST', body: JSON.stringify(result.passNs) });
  for (const [name, rgba] of Object.entries(result.images))
    await fetch(`/image/${name}?w=${options.width}&h=${options.height}`, { method: 'POST', body: new Blob([rgba as Uint8Array<ArrayBuffer>]) });
  log('results posted');
  document.title = 'S0 done';
}

main().catch((e) => { log('ERROR: ' + (e?.message ?? e)); fetch('/result/error.txt', { method: 'POST', body: String(e?.stack ?? e) }); });
