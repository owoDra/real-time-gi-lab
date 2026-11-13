// Native S0 run: Dawn (Vulkan) through the `webgpu` npm package.
// Usage: node build/native/main.mjs [--frames N] [--warmup N] [--out DIR]
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { create, globals } from 'webgpu';
import jpeg from 'jpeg-js';
import { PNG } from 'pngjs';
import { runGBufferBench, DEFAULT_OPTIONS } from '../core/bench.ts';
import { TEXTURE_SIZE, type ImageUploader } from '../core/scene_gpu.ts';
import { summarize } from '../core/report.ts';

Object.assign(globalThis, globals);

const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const root = resolve(import.meta.dirname, '../..');
const sceneDir = join(root, 'assets/glTF-Sample-Assets/Models/Sponza/glTF');
const outDir = resolve(arg('--out', join(root, 'out/s0/native')));
const options = { ...DEFAULT_OPTIONS, frames: Number(arg('--frames', String(DEFAULT_OPTIONS.frames))), warmup: Number(arg('--warmup', String(DEFAULT_OPTIONS.warmup))) };

// Dawn quantises timestamps by default in some embedders; ask for full resolution.
const gpu = create(['backend=vulkan', 'disable-dawn-features=timestamp_quantization']);
const adapter = await gpu.requestAdapter({ powerPreference: 'high-performance' });
if (!adapter) throw new Error('no WebGPU adapter');
const device = await adapter.requestDevice({
  requiredFeatures: adapter.features.has('timestamp-query') ? ['timestamp-query'] : [],
});
device.addEventListener('uncapturederror', (e: any) => { console.error('WebGPU error:', e.error?.message); process.exitCode = 1; });

function decode(file: string): { width: number; height: number; data: Uint8Array } {
  const buf = readFileSync(file);
  if (file.endsWith('.png')) { const p = PNG.sync.read(buf); return { width: p.width, height: p.height, data: new Uint8Array(p.data) }; }
  const j = jpeg.decode(buf, { useTArray: true, formatAsRGBA: true, maxMemoryUsageInMB: 2048 });
  return { width: j.width, height: j.height, data: j.data };
}

/** Nearest-neighbour resize to TEXTURE_SIZE; only used for the odd 4x4 placeholder image. */
function toTextureSize(img: { width: number; height: number; data: Uint8Array }) {
  if (img.width === TEXTURE_SIZE && img.height === TEXTURE_SIZE) return img.data;
  const out = new Uint8Array(TEXTURE_SIZE * TEXTURE_SIZE * 4);
  for (let y = 0; y < TEXTURE_SIZE; y++)
    for (let x = 0; x < TEXTURE_SIZE; x++) {
      const sx = Math.floor(x * img.width / TEXTURE_SIZE), sy = Math.floor(y * img.height / TEXTURE_SIZE);
      out.set(img.data.subarray((sy * img.width + sx) * 4, (sy * img.width + sx) * 4 + 4), (y * TEXTURE_SIZE + x) * 4);
    }
  return out;
}

const json = JSON.parse(readFileSync(join(sceneDir, 'Sponza.gltf'), 'utf8'));
const binFile = readFileSync(join(sceneDir, json.buffers[0].uri));
const bin = binFile.buffer.slice(binFile.byteOffset, binFile.byteOffset + binFile.byteLength);
const upload: ImageUploader = async (dev, texture, layer, imageIndex) => {
  const data = toTextureSize(decode(join(sceneDir, json.images[imageIndex].uri)));
  dev.queue.writeTexture({ texture, origin: [0, 0, layer] }, data, { bytesPerRow: TEXTURE_SIZE * 4 }, [TEXTURE_SIZE, TEXTURE_SIZE, 1]);
};

const result = await runGBufferBench(device, json, bin, upload, options, (s) => console.log(s));
mkdirSync(outDir, { recursive: true });
for (const [name, rgba] of Object.entries(result.images))
  writeFileSync(join(outDir, `${name}.png`), PNG.sync.write(Object.assign(new PNG({ width: options.width, height: options.height }), { data: Buffer.from(rgba) })));
const info = adapter.info;
const summary = summarize(result, {
  platform: 'native', implementation: 'Dawn via webgpu@0.6.2 (node), backend=vulkan', userAgent: `node ${process.version}`,
  adapter: { vendor: info.vendor, architecture: info.architecture, device: info.device, description: info.description },
});
writeFileSync(join(outDir, 'summary.json'), JSON.stringify(summary, null, 2));
writeFileSync(join(outDir, 'pass_ns.json'), JSON.stringify(result.passNs));
console.log(JSON.stringify(summary.gbufferPass, null, 2));
device.destroy();
process.exit(process.exitCode ?? 0);
