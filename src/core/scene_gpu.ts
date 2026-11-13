// Uploads SceneData to the GPU. Textures go into one 2D array per role so that later GI passes
// can sample any material from a single bind group (WebGPU core has no bindless textures).
import type { SceneData } from './gltf.ts';

export const TEXTURE_SIZE = 1024;

/** Platform hook: decode image `imageIndex` and write it into `texture` at array `layer`, level 0,
 * resized to TEXTURE_SIZE x TEXTURE_SIZE. */
export type ImageUploader = (device: GPUDevice, texture: GPUTexture, layer: number, imageIndex: number) => Promise<void>;

export interface SceneGpu {
  positions: GPUBuffer; normals: GPUBuffer; uvs: GPUBuffer; tangents: GPUBuffer; indices: GPUBuffer;
  materials: GPUBuffer;
  baseColor: GPUTexture; normal: GPUTexture; metallicRoughness: GPUTexture;
  /** Bytes of GPU resources created here (buffers + textures incl. mips). */
  bytes: number;
}

const MIP_WGSL = /* wgsl */ `
@group(0) @binding(0) var src: texture_2d<f32>;
@group(0) @binding(1) var samp: sampler;
struct V { @builtin(position) p: vec4f, @location(0) uv: vec2f }
@vertex fn vs(@builtin(vertex_index) i: u32) -> V {
  let uv = vec2f(f32((i << 1u) & 2u), f32(i & 2u));
  return V(vec4f(uv * vec2f(2, -2) + vec2f(-1, 1), 0, 1), uv);
}
@fragment fn fs(v: V) -> @location(0) vec4f { return textureSampleLevel(src, samp, v.uv, 0); }
`;

function mipCount(size: number) { return Math.floor(Math.log2(size)) + 1; }

function buffer(device: GPUDevice, data: ArrayBufferView, usage: GPUBufferUsageFlags, label: string) {
  const b = device.createBuffer({ label, size: Math.ceil(data.byteLength / 4) * 4, usage: usage | GPUBufferUsage.COPY_DST });
  device.queue.writeBuffer(b, 0, data.buffer, data.byteOffset, data.byteLength);
  return b;
}

function generateMips(device: GPUDevice, tex: GPUTexture) {
  const module = device.createShaderModule({ code: MIP_WGSL, label: 'mip' });
  const pipeline = device.createRenderPipeline({
    layout: 'auto', vertex: { module }, fragment: { module, targets: [{ format: tex.format }] },
  });
  const sampler = device.createSampler({ minFilter: 'linear', magFilter: 'linear' });
  const enc = device.createCommandEncoder({ label: 'mips' });
  for (let layer = 0; layer < tex.depthOrArrayLayers; layer++)
    for (let level = 1; level < tex.mipLevelCount; level++) {
      const src = tex.createView({ dimension: '2d', baseArrayLayer: layer, arrayLayerCount: 1, baseMipLevel: level - 1, mipLevelCount: 1 });
      const dst = tex.createView({ dimension: '2d', baseArrayLayer: layer, arrayLayerCount: 1, baseMipLevel: level, mipLevelCount: 1 });
      const bg = device.createBindGroup({ layout: pipeline.getBindGroupLayout(0), entries: [{ binding: 0, resource: src }, { binding: 1, resource: sampler }] });
      const pass = enc.beginRenderPass({ colorAttachments: [{ view: dst, loadOp: 'clear', storeOp: 'store', clearValue: [0, 0, 0, 0] }] });
      pass.setPipeline(pipeline); pass.setBindGroup(0, bg); pass.draw(3); pass.end();
    }
  device.queue.submit([enc.finish()]);
}

export async function uploadScene(device: GPUDevice, scene: SceneData, upload: ImageUploader): Promise<SceneGpu> {
  const V = GPUBufferUsage.VERTEX | GPUBufferUsage.STORAGE;
  const positions = buffer(device, scene.positions, V, 'positions');
  const normals = buffer(device, scene.normals, V, 'normals');
  const uvs = buffer(device, scene.uvs, V, 'uvs');
  const tangents = buffer(device, scene.tangents, V, 'tangents');
  const indices = buffer(device, scene.indices, GPUBufferUsage.INDEX | GPUBufferUsage.STORAGE, 'indices');

  // Layer 0 of every array is a 1x1-filled default; image layers follow.
  const roles = [
    { key: 'baseColorImage', format: 'rgba8unorm-srgb', fill: [255, 255, 255, 255] },
    { key: 'normalImage', format: 'rgba8unorm', fill: [128, 128, 255, 255] },
    { key: 'metallicRoughnessImage', format: 'rgba8unorm', fill: [255, 255, 255, 255] },
  ] as const;
  const layerOf = roles.map(() => new Map<number, number>());
  roles.forEach((r, ri) => {
    for (const m of scene.materials) {
      const img = m[r.key];
      if (img >= 0 && !layerOf[ri].has(img)) layerOf[ri].set(img, layerOf[ri].size + 1);
    }
  });
  const levels = mipCount(TEXTURE_SIZE);
  let bytes = 0;
  const textures = roles.map((r, ri) => {
    const layers = layerOf[ri].size + 1;
    const tex = device.createTexture({
      label: r.key, format: r.format, size: [TEXTURE_SIZE, TEXTURE_SIZE, layers], mipLevelCount: levels,
      usage: GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST | GPUTextureUsage.RENDER_ATTACHMENT,
    });
    bytes += Math.round(TEXTURE_SIZE * TEXTURE_SIZE * 4 * layers * 4 / 3);
    const fill = new Uint8Array(TEXTURE_SIZE * TEXTURE_SIZE * 4);
    for (let i = 0; i < fill.length; i += 4) fill.set(r.fill, i);
    device.queue.writeTexture({ texture: tex, origin: [0, 0, 0] }, fill, { bytesPerRow: TEXTURE_SIZE * 4 }, [TEXTURE_SIZE, TEXTURE_SIZE, 1]);
    return tex;
  });
  for (let ri = 0; ri < roles.length; ri++)
    for (const [img, layer] of layerOf[ri]) await upload(device, textures[ri], layer, img);
  textures.forEach((t) => generateMips(device, t));

  // struct Material { baseColorFactor: vec4f, layers: vec4u (bc, n, mr, flags), params: vec4f (metal, rough, cutoff, 0) }
  const mat = new ArrayBuffer(scene.materials.length * 48);
  scene.materials.forEach((m, i) => {
    const f = new Float32Array(mat, i * 48, 12), u = new Uint32Array(mat, i * 48, 12);
    f.set(m.baseColorFactor, 0);
    u[4] = layerOf[0].get(m.baseColorImage) ?? 0;
    u[5] = layerOf[1].get(m.normalImage) ?? 0;
    u[6] = layerOf[2].get(m.metallicRoughnessImage) ?? 0;
    u[7] = (m.alphaMask ? 1 : 0) | (m.doubleSided ? 2 : 0);
    f[8] = m.metallicFactor; f[9] = m.roughnessFactor; f[10] = m.alphaCutoff;
  });
  const materials = buffer(device, new Uint8Array(mat), GPUBufferUsage.STORAGE, 'materials');
  for (const b of [positions, normals, uvs, tangents, indices, materials]) bytes += b.size;
  await device.queue.onSubmittedWorkDone();
  return { positions, normals, uvs, tangents, indices, materials, baseColor: textures[0], normal: textures[1], metallicRoughness: textures[2], bytes };
}
