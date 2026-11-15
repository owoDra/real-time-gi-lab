// G-buffer pass and a debug visualisation pass.
// Layout: albedo rgba8unorm-srgb (rgb = base colour, a = 1 toon, 0.5 other measured object, 0 photoreal (S3); metallic is not used),
//         normal rgba16float (xyz = world shading normal, w = roughness),
//         depth32float, reversed Z with an infinite far plane.
// Measurement only (phase 27): GEO_NORMALS leaves the normal map out (the interpolated vertex normal), for the
// flicker and excess metrics on a moving camera or a moving building (docs/spec/10-evaluation.md).
import type { Primitive, SceneData } from './gltf.ts';
import type { Mat4 } from './math.ts';
import type { SceneGpu } from './scene_gpu.ts';
import { MOTION_MARGIN, type World } from './world.ts';

// Phase 32: instanced worlds. A draw's firstInstance carries the material (low 16 bits) and the instance (high bits); the
// vertex shader moves the vertex by the instance's offset (instance 0: none). The static primitives are drawn once per
// instance whose box the camera (or the shadow layer) sees, the dynamic ones once.
export const INSTANCE_WGSL = /* wgsl */ `
fn instOffsetOf(ii: u32) -> vec3f { return instOffset[ii >> 16u].xyz; }
`;
export interface InstancedDraws {
  offsets: GPUBuffer;
  /** Instances whose box is inside the clip volume of m (perspective or orthographic). */
  visible(m: Mat4): number[];
  instancesOf(p: Primitive, visible: number[]): number[];
  firstInstance(p: Primitive, inst: number): number;
}
export function instancedDraws(device: GPUDevice, scene: SceneData, world: World | null): InstancedDraws {
  const inst = world?.instances ?? [[0, 0, 0]];
  const data = new Float32Array(inst.length * 4);
  inst.forEach((o, i) => data.set(o, i * 4));
  const offsets = device.createBuffer({ label: 'instances', size: data.byteLength, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_DST });
  device.queue.writeBuffer(offsets, 0, data);
  const zero = [0];
  const T = world?.staticTriangles ?? scene.triangleCount;
  return {
    offsets,
    visible(m) {
      if (!world) return zero;
      const out: number[] = [];
      const lo = world.staticMin.map((x) => x - MOTION_MARGIN), hi = world.staticMax.map((x) => x + MOTION_MARGIN);
      inst.forEach((o, i) => {
        let ax = 0, bx = 0, ay = 0, by = 0, az = 0, bz = 0, behind = 0;
        for (let k = 0; k < 8; k++) {
          const x = (k & 1 ? hi[0] : lo[0]) + o[0], y = (k & 2 ? hi[1] : lo[1]) + o[1], z = (k & 4 ? hi[2] : lo[2]) + o[2];
          const cx = m[0] * x + m[4] * y + m[8] * z + m[12], cy = m[1] * x + m[5] * y + m[9] * z + m[13];
          const cz = m[2] * x + m[6] * y + m[10] * z + m[14], cw = m[3] * x + m[7] * y + m[11] * z + m[15];
          if (cx > cw) ax++; if (cx < -cw) bx++; if (cy > cw) ay++; if (cy < -cw) by++;
          if (cz > cw) az++; if (cz < 0) bz++; if (cw <= 0) behind++;
        }
        if (ax < 8 && bx < 8 && ay < 8 && by < 8 && az < 8 && bz < 8 && behind < 8) out.push(i);
      });
      return out;
    },
    instancesOf: (p, visible) => world && p.firstIndex / 3 < T ? visible : zero,
    firstInstance: (p, i) => p.material | (i << 16),
  };
}

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
@group(0) @binding(6) var<storage, read> instOffset: array<vec4f>;
${INSTANCE_WGSL}

struct VsIn {
  @location(0) pos: vec3f, @location(1) nrm: vec3f, @location(2) uv: vec2f, @location(3) tan: vec4f,
  @builtin(instance_index) ii: u32, // firstInstance carries the material index and the instance (phase 32)
}
struct VsOut {
  @builtin(position) clip: vec4f,
  @location(0) nrm: vec3f, @location(1) uv: vec2f, @location(2) tan: vec4f,
  @location(3) @interpolate(flat) mat: u32,
}
@vertex fn vs(i: VsIn) -> VsOut {
  return VsOut(cam.viewProj * vec4f(i.pos + instOffsetOf(i.ii), 1), i.nrm, i.uv, i.tan, i.ii & 0xffffu);
}

override GEO_NORMALS: bool = false;
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
  if (tl > 1e-4 && !GEO_NORMALS) {
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
  /** geoNormals: without the normal map (measurement only). */
  encode(enc: GPUCommandEncoder, g: GBuffer, timestampWrites?: GPURenderPassTimestampWrites, geoNormals?: boolean): void;
  /** Phase 32: the instances seen by this view-projection (instanced worlds) for the next encode. */
  cull(viewProj: Mat4): void;
  drawCount: number;
}

export function createGBufferRenderer(device: GPUDevice, scene: SceneData, gpu: SceneGpu, world: World | null = null): GBufferRenderer {
  const inst = instancedDraws(device, scene, world);
  let visible = [0];
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
      { binding: 6, visibility: GPUShaderStage.VERTEX, buffer: { type: 'read-only-storage' } },
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
      { binding: 6, resource: { buffer: inst.offsets } },
    ],
  });
  const layout = device.createPipelineLayout({ bindGroupLayouts: [bgl] });
  const pipelineFor = (doubleSided: boolean, geo = false) => device.createRenderPipeline({
    label: `gbuffer.${doubleSided ? 'two' : 'one'}-sided${geo ? '.geo' : ''}`, layout,
    vertex: {
      module, buffers: [
        { arrayStride: 12, attributes: [{ shaderLocation: 0, offset: 0, format: 'float32x3' }] },
        { arrayStride: 12, attributes: [{ shaderLocation: 1, offset: 0, format: 'float32x3' }] },
        { arrayStride: 8, attributes: [{ shaderLocation: 2, offset: 0, format: 'float32x2' }] },
        { arrayStride: 16, attributes: [{ shaderLocation: 3, offset: 0, format: 'float32x4' }] },
      ],
    },
    fragment: { module, targets: [{ format: ALBEDO_FORMAT }, { format: NORMAL_FORMAT }], constants: { GEO_NORMALS: geo ? 1 : 0 } },
    primitive: { topology: 'triangle-list', cullMode: doubleSided ? 'none' : 'back', frontFace: 'ccw' },
    depthStencil: { format: DEPTH_FORMAT, depthWriteEnabled: true, depthCompare: 'greater' },
  });
  const pipelines = [pipelineFor(false), pipelineFor(true)];
  let geoPipelines: GPURenderPipeline[] | null = null;
  // Opaque single-sided first, then double-sided / alpha-masked.
  const draws = scene.primitives.map((p) => ({ p, ds: scene.materials[p.material].doubleSided, mask: scene.materials[p.material].alphaMask }))
    .sort((a, b) => Number(a.ds) - Number(b.ds) || Number(a.mask) - Number(b.mask));

  return {
    camera, drawCount: draws.length,
    cull(viewProj) { visible = inst.visible(viewProj); },
    encode(enc, g, timestampWrites, geoNormals = false) {
      const pipes = geoNormals ? (geoPipelines ??= [pipelineFor(false, true), pipelineFor(true, true)]) : pipelines;
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
        if (pi !== current) { pass.setPipeline(pipes[pi]); current = pi; }
        for (const i of inst.instancesOf(d.p, visible)) pass.drawIndexed(d.p.indexCount, 1, d.p.firstIndex, d.p.baseVertex, inst.firstInstance(d.p, i));
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
