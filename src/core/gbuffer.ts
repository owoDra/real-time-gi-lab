// G-buffer pass and a debug visualisation pass.
// Layout: albedo rgba8unorm-srgb (rgb = base colour, a = 1 toon, 0.5 other measured object, 0 photoreal (S3); metallic is not used),
//         normal rgba16float (xyz = world shading normal, w = roughness),
//         depth32float, reversed Z with an infinite far plane.
import type { SceneData } from './gltf.ts';
import type { SceneGpu } from './scene_gpu.ts';

export const ALBEDO_FORMAT: GPUTextureFormat = 'rgba8unorm-srgb';
export const NORMAL_FORMAT: GPUTextureFormat = 'rgba16float';
export const DEPTH_FORMAT: GPUTextureFormat = 'depth32float';

const GBUFFER_WGSL = /* wgsl */ `
struct Camera { viewProj: mat4x4f, view: mat4x4f, eyeNear: vec4f }
struct Material { baseColorFactor: vec4f, layers: vec4u, params: vec4f }
@group(0) @binding(0) var<uniform> cam: Camera;
@group(0) @binding(1) var<storage, read> materials: array<Material>;
@group(0) @binding(2) var samp: sampler;
@group(0) @binding(3) var baseColorTex: texture_2d_array<f32>;
@group(0) @binding(4) var normalTex: texture_2d_array<f32>;
@group(0) @binding(5) var mrTex: texture_2d_array<f32>;

struct VsIn {
  @location(0) pos: vec3f, @location(1) nrm: vec3f, @location(2) uv: vec2f, @location(3) tan: vec4f,
  @builtin(instance_index) mat: u32, // firstInstance carries the material index
}
struct VsOut {
  @builtin(position) clip: vec4f,
  @location(0) nrm: vec3f, @location(1) uv: vec2f, @location(2) tan: vec4f,
  @location(3) @interpolate(flat) mat: u32,
}
@vertex fn vs(i: VsIn) -> VsOut {
  return VsOut(cam.viewProj * vec4f(i.pos, 1), i.nrm, i.uv, i.tan, i.mat);
}

struct FsOut { @location(0) albedo: vec4f, @location(1) normal: vec4f }
@fragment fn fs(i: VsOut, @builtin(front_facing) front: bool) -> FsOut {
  let m = materials[i.mat];
  let base = textureSample(baseColorTex, samp, i.uv, m.layers.x) * m.baseColorFactor;
  let tn = textureSample(normalTex, samp, i.uv, m.layers.y).xyz * 2.0 - 1.0;
  let mr = textureSample(mrTex, samp, i.uv, m.layers.z);
  if ((m.layers.w & 1u) != 0u && base.a < m.params.z) { discard; }
  let flip = select(-1.0, 1.0, front);
  var n = normalize(i.nrm) * flip;
  let tl = length(i.tan.xyz);
  if (tl > 1e-4) {
    let t = normalize(i.tan.xyz - n * dot(n, i.tan.xyz));
    let b = cross(n, t) * i.tan.w * flip;
    n = normalize(t * tn.x + b * tn.y + n * tn.z);
  }
  return FsOut(vec4f(base.rgb, select(select(0.0, 0.5, (m.layers.w & 8u) != 0u), 1.0, (m.layers.w & 4u) != 0u)), vec4f(n, mr.g * m.params.y));
}
`;

const VIZ_WGSL = /* wgsl */ `
struct Viz { mode: u32, near: f32, pad0: u32, pad1: u32 }
@group(0) @binding(0) var albedo: texture_2d<f32>;
@group(0) @binding(1) var normal: texture_2d<f32>;
@group(0) @binding(2) var depth: texture_depth_2d;
@group(0) @binding(3) var<uniform> viz: Viz;
@vertex fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4f {
  let uv = vec2f(f32((i << 1u) & 2u), f32(i & 2u));
  return vec4f(uv * vec2f(2, -2) + vec2f(-1, 1), 0, 1);
}
fn toSrgb(c: vec3f) -> vec3f {
  return select(1.055 * pow(c, vec3f(1.0 / 2.4)) - 0.055, c * 12.92, c <= vec3f(0.0031308));
}
@fragment fn fs(@builtin(position) p: vec4f) -> @location(0) vec4f {
  let px = vec2i(p.xy);
  let d = textureLoad(depth, px, 0);
  if (viz.mode == 0u) { return vec4f(toSrgb(textureLoad(albedo, px, 0).rgb), 1); }
  if (viz.mode == 1u) {
    if (d == 0.0) { return vec4f(0, 0, 0, 1); }
    return vec4f(textureLoad(normal, px, 0).xyz * 0.5 + 0.5, 1);
  }
  if (d == 0.0) { return vec4f(0.2, 0.3, 0.5, 1); }
  let z = viz.near / d; // view-space distance along -Z
  let t = clamp(log2(z / viz.near) / 10.0, 0.0, 1.0);
  return vec4f(vec3f(1.0 - t), 1);
}
`;

export interface GBuffer { albedo: GPUTexture; normal: GPUTexture; depth: GPUTexture; width: number; height: number; }

export function createGBuffer(device: GPUDevice, width: number, height: number): GBuffer {
  const usage = GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_SRC;
  return {
    albedo: device.createTexture({ label: 'gb.albedo', size: [width, height], format: ALBEDO_FORMAT, usage }),
    normal: device.createTexture({ label: 'gb.normal', size: [width, height], format: NORMAL_FORMAT, usage }),
    depth: device.createTexture({ label: 'gb.depth', size: [width, height], format: DEPTH_FORMAT, usage }),
    width, height,
  };
}

export function gbufferBytes(g: GBuffer) { return g.width * g.height * (4 + 8 + 4); }

export interface GBufferRenderer {
  camera: GPUBuffer;
  encode(enc: GPUCommandEncoder, g: GBuffer, timestampWrites?: GPURenderPassTimestampWrites): void;
  drawCount: number;
}

export function createGBufferRenderer(device: GPUDevice, scene: SceneData, gpu: SceneGpu): GBufferRenderer {
  const module = device.createShaderModule({ code: GBUFFER_WGSL, label: 'gbuffer' });
  const camera = device.createBuffer({ label: 'camera', size: 144, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  const bgl = device.createBindGroupLayout({
    entries: [
      { binding: 0, visibility: GPUShaderStage.VERTEX | GPUShaderStage.FRAGMENT, buffer: { type: 'uniform' } },
      { binding: 1, visibility: GPUShaderStage.FRAGMENT, buffer: { type: 'read-only-storage' } },
      { binding: 2, visibility: GPUShaderStage.FRAGMENT, sampler: {} },
      { binding: 3, visibility: GPUShaderStage.FRAGMENT, texture: { viewDimension: '2d-array' } },
      { binding: 4, visibility: GPUShaderStage.FRAGMENT, texture: { viewDimension: '2d-array' } },
      { binding: 5, visibility: GPUShaderStage.FRAGMENT, texture: { viewDimension: '2d-array' } },
    ],
  });
  const sampler = device.createSampler({
    minFilter: 'linear', magFilter: 'linear', mipmapFilter: 'linear', addressModeU: 'repeat', addressModeV: 'repeat', maxAnisotropy: 8,
  });
  const bindGroup = device.createBindGroup({
    layout: bgl,
    entries: [
      { binding: 0, resource: { buffer: camera } },
      { binding: 1, resource: { buffer: gpu.materials } },
      { binding: 2, resource: sampler },
      { binding: 3, resource: gpu.baseColor.createView({ dimension: '2d-array' }) },
      { binding: 4, resource: gpu.normal.createView({ dimension: '2d-array' }) },
      { binding: 5, resource: gpu.metallicRoughness.createView({ dimension: '2d-array' }) },
    ],
  });
  const layout = device.createPipelineLayout({ bindGroupLayouts: [bgl] });
  const pipelineFor = (doubleSided: boolean) => device.createRenderPipeline({
    label: `gbuffer.${doubleSided ? 'two' : 'one'}-sided`, layout,
    vertex: {
      module, buffers: [
        { arrayStride: 12, attributes: [{ shaderLocation: 0, offset: 0, format: 'float32x3' }] },
        { arrayStride: 12, attributes: [{ shaderLocation: 1, offset: 0, format: 'float32x3' }] },
        { arrayStride: 8, attributes: [{ shaderLocation: 2, offset: 0, format: 'float32x2' }] },
        { arrayStride: 16, attributes: [{ shaderLocation: 3, offset: 0, format: 'float32x4' }] },
      ],
    },
    fragment: { module, targets: [{ format: ALBEDO_FORMAT }, { format: NORMAL_FORMAT }] },
    primitive: { topology: 'triangle-list', cullMode: doubleSided ? 'none' : 'back', frontFace: 'ccw' },
    depthStencil: { format: DEPTH_FORMAT, depthWriteEnabled: true, depthCompare: 'greater' },
  });
  const pipelines = [pipelineFor(false), pipelineFor(true)];
  // Opaque single-sided first, then double-sided / alpha-masked.
  const draws = scene.primitives.map((p) => ({ p, ds: scene.materials[p.material].doubleSided, mask: scene.materials[p.material].alphaMask }))
    .sort((a, b) => Number(a.ds) - Number(b.ds) || Number(a.mask) - Number(b.mask));

  return {
    camera, drawCount: draws.length,
    encode(enc, g, timestampWrites) {
      const pass = enc.beginRenderPass({
        label: 'gbuffer',
        colorAttachments: [
          { view: g.albedo.createView(), loadOp: 'clear', storeOp: 'store', clearValue: [0, 0, 0, 0] },
          { view: g.normal.createView(), loadOp: 'clear', storeOp: 'store', clearValue: [0, 0, 0, 0] },
        ],
        depthStencilAttachment: { view: g.depth.createView(), depthLoadOp: 'clear', depthStoreOp: 'store', depthClearValue: 0 },
        timestampWrites,
      });
      pass.setBindGroup(0, bindGroup);
      pass.setVertexBuffer(0, gpu.positions); pass.setVertexBuffer(1, gpu.normals);
      pass.setVertexBuffer(2, gpu.uvs); pass.setVertexBuffer(3, gpu.tangents);
      pass.setIndexBuffer(gpu.indices, 'uint32');
      let current = -1;
      for (const d of draws) {
        const pi = d.ds ? 1 : 0;
        if (pi !== current) { pass.setPipeline(pipelines[pi]); current = pi; }
        pass.drawIndexed(d.p.indexCount, 1, d.p.firstIndex, d.p.baseVertex, d.p.material);
      }
      pass.end();
    },
  };
}

export const VIZ_MODES = ['albedo', 'normal', 'depth'] as const;

/** Renders a visualisation of the G-buffer into an rgba8unorm texture (sRGB-encoded values). */
export function createVisualizer(device: GPUDevice, g: GBuffer, near: number) {
  const module = device.createShaderModule({ code: VIZ_WGSL, label: 'viz' });
  const pipeline = device.createRenderPipeline({ layout: 'auto', vertex: { module }, fragment: { module, targets: [{ format: 'rgba8unorm' }] } });
  const target = device.createTexture({ label: 'viz', size: [g.width, g.height], format: 'rgba8unorm',
    usage: GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.COPY_SRC });
  const uniforms = VIZ_MODES.map((_, mode) => {
    const b = device.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    const data = new ArrayBuffer(16); new Uint32Array(data)[0] = mode; new Float32Array(data)[1] = near;
    device.queue.writeBuffer(b, 0, data);
    return device.createBindGroup({ layout: pipeline.getBindGroupLayout(0), entries: [
      { binding: 0, resource: g.albedo.createView() }, { binding: 1, resource: g.normal.createView() },
      { binding: 2, resource: g.depth.createView() }, { binding: 3, resource: { buffer: b } },
    ] });
  });
  /** Returns tightly packed RGBA8 rows. */
  async function capture(mode: number): Promise<Uint8Array> {
    const bytesPerRow = Math.ceil(g.width * 4 / 256) * 256;
    const readback = device.createBuffer({ size: bytesPerRow * g.height, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
    const enc = device.createCommandEncoder();
    const pass = enc.beginRenderPass({ colorAttachments: [{ view: target.createView(), loadOp: 'clear', storeOp: 'store', clearValue: [0, 0, 0, 1] }] });
    pass.setPipeline(pipeline); pass.setBindGroup(0, uniforms[mode]); pass.draw(3); pass.end();
    enc.copyTextureToBuffer({ texture: target }, { buffer: readback, bytesPerRow }, [g.width, g.height]);
    device.queue.submit([enc.finish()]);
    await readback.mapAsync(GPUMapMode.READ);
    const src = new Uint8Array(readback.getMappedRange());
    const out = new Uint8Array(g.width * g.height * 4);
    for (let y = 0; y < g.height; y++) out.set(src.subarray(y * bytesPerRow, y * bytesPerRow + g.width * 4), y * g.width * 4);
    readback.unmap(); readback.destroy();
    return out;
  }
  return { capture, target };
}
