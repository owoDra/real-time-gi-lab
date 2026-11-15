// Native (Dawn / Vulkan via the `webgpu` package) device and Sponza loading, shared by the runners.
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { create, globals } from 'webgpu';
import jpeg from 'jpeg-js';
import { PNG } from 'pngjs';
import { TEXTURE_SIZE, type ImageUploader } from '../core/scene_gpu.ts';
import { toTextureSize } from '../runner/texture.ts';

Object.assign(globalThis, globals);

export const ROOT = resolve(import.meta.dirname, '../..');
export const IMPLEMENTATION = 'Dawn via webgpu@0.6.2 (node), backend=vulkan';

// The Dawn instance must stay reachable for the life of the process: if it is garbage-collected while a
// device is in use, Dawn aborts (seen as a futex / std::system_error abort during texture upload).
let instance: GPU | null = null;

export async function createNativeDevice(limits: Record<string, number> = {}) {
  // Dawn quantises timestamps by default in some embedders; ask for full resolution.
  const gpu = instance ??= create(['backend=vulkan', 'disable-dawn-features=timestamp_quantization']);
  const adapter = await gpu.requestAdapter({ powerPreference: 'high-performance' });
  if (!adapter) throw new Error('no WebGPU adapter');
  const device = await adapter.requestDevice({
    requiredFeatures: adapter.features.has('timestamp-query') ? ['timestamp-query'] : [],
    requiredLimits: limits,
  });
  device.addEventListener('uncapturederror', (e: any) => { console.error('WebGPU error:', e.error?.message); process.exitCode = 1; });
  const info = adapter.info;
  return { device, adapter, adapterInfo: { vendor: info.vendor, architecture: info.architecture, device: info.device, description: info.description } };
}

function decode(file: string): { width: number; height: number; data: Uint8Array } {
  const buf = readFileSync(file);
  if (file.endsWith('.png')) { const p = PNG.sync.read(buf); return { width: p.width, height: p.height, data: new Uint8Array(p.data) }; }
  const j = jpeg.decode(buf, { useTArray: true, formatAsRGBA: true, maxMemoryUsageInMB: 2048 });
  return { width: j.width, height: j.height, data: j.data };
}

export function loadSponza() {
  const sceneDir = join(ROOT, 'assets/glTF-Sample-Assets/Models/Sponza/glTF');
  const json = JSON.parse(readFileSync(join(sceneDir, 'Sponza.gltf'), 'utf8'));
  const binFile = readFileSync(join(sceneDir, json.buffers[0].uri));
  const bin = binFile.buffer.slice(binFile.byteOffset, binFile.byteOffset + binFile.byteLength);
  const upload: ImageUploader = async (dev, texture, layer, imageIndex) => {
    const data = toTextureSize(decode(join(sceneDir, json.images[imageIndex].uri)));
    dev.queue.writeTexture({ texture, origin: [0, 0, layer] }, data, { bytesPerRow: TEXTURE_SIZE * 4 }, [TEXTURE_SIZE, TEXTURE_SIZE, 1]);
  };
  return { json, bin, upload };
}

export function writePng(width: number, height: number, rgba: Uint8Array) {
  return PNG.sync.write(Object.assign(new PNG({ width, height }), { data: Buffer.from(rgba) }));
}
