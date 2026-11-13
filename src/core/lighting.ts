// Direct sun light: a shadow map and a full-screen pass that writes outgoing (Lambert) radiance per pixel.
// The radiance texture is what the GI passes read at a hit point (one bounce).
import type { SceneData } from './gltf.ts';
import type { SceneGpu } from './scene_gpu.ts';
import type { GBuffer } from './gbuffer.ts';
import { FRAME_WGSL } from './frame.ts';
import { add3, lookAt, mul, orthoZO, scale3, sub, type Mat4, type Vec3 } from './math.ts';

const SHADOW_WGSL = /* wgsl */ `
struct Material { baseColorFactor: vec4f, layers: vec4u, params: vec4f }
@group(0) @binding(0) var<uniform> lightVP: mat4x4f;
@group(0) @binding(1) var<storage, read> materials: array<Material>;
@group(0) @binding(2) var samp: sampler;
@group(0) @binding(3) var baseColorTex: texture_2d_array<f32>;
struct VsOut { @builtin(position) clip: vec4f, @location(0) uv: vec2f, @location(1) @interpolate(flat) mat: u32 }
@vertex fn vs(@location(0) pos: vec3f, @location(1) uv: vec2f, @builtin(instance_index) mat: u32) -> VsOut {
  return VsOut(lightVP * vec4f(pos, 1.0), uv, mat);
}
@fragment fn fs(i: VsOut) {
  let m = materials[i.mat];
  if ((m.layers.w & 1u) != 0u) {
    let a = textureSampleLevel(baseColorTex, samp, i.uv, m.layers.x, 0.0).a * m.baseColorFactor.a;
    if (a < m.params.z) { discard; }
  }
}
`;

const DIRECT_WGSL = /* wgsl */ `
${FRAME_WGSL}
const PI = 3.14159265;
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var albedoTex: texture_2d<f32>;
@group(0) @binding(2) var normalTex: texture_2d<f32>;
@group(0) @binding(3) var depthTex: texture_depth_2d;
@group(0) @binding(4) var shadowTex: texture_depth_2d;
@group(0) @binding(5) var shadowSamp: sampler_comparison;
@group(0) @binding(6) var litOut: texture_storage_2d<rgba16float, write>;

fn sunVisibility(x: vec3f) -> f32 {
  let c = F.lightViewProj * vec4f(x, 1.0);
  let uv = c.xy * vec2f(0.5, -0.5) + 0.5;
  if (any(uv < vec2f(0.0)) || any(uv > vec2f(1.0))) { return 1.0; }
  let texel = 1.0 / vec2f(textureDimensions(shadowTex));
  var v = 0.0;
  for (var j = -1; j <= 1; j++) {
    for (var i = -1; i <= 1; i++) {
      v += textureSampleCompareLevel(shadowTex, shadowSamp, uv + vec2f(f32(i), f32(j)) * texel, c.z - 0.0002);
    }
  }
  return v / 9.0;
}

@compute @workgroup_size(8, 8) fn direct(@builtin(global_invocation_id) gid: vec3u) {
  if (gid.x >= u32(F.size.x) || gid.y >= u32(F.size.y)) { return; }
  let px = vec2i(gid.xy);
  let d = textureLoad(depthTex, px, 0);
  if (d <= 0.0) { textureStore(litOut, px, vec4f(0.0)); return; }
  let x = worldAt(px, d);
  let n = textureLoad(normalTex, px, 0).xyz;
  let a = textureLoad(albedoTex, px, 0).rgb;
  let ndl = max(dot(n, F.sunDir.xyz), 0.0);
  var vis = 0.0;
  if (ndl > 0.0) { vis = sunVisibility(x + n * 0.03); }
  textureStore(litOut, px, vec4f(a / PI * F.sunE.rgb * ndl * vis, ndl * vis));
}
`;

export interface Lighting {
  lit: GPUTexture;
  shadow: GPUTexture;
  lightViewProj: Mat4;
  encodeShadow(enc: GPUCommandEncoder, tw?: GPURenderPassTimestampWrites): void;
  encodeDirect(enc: GPUCommandEncoder, tw?: GPUComputePassTimestampWrites): void;
  bytes: number;
}

export function createLighting(device: GPUDevice, scene: SceneData, gpu: SceneGpu, g: GBuffer, frame: GPUBuffer,
  sunDir: Vec3, shadowSize = 4096): Lighting {
  const center = scale3(add3(scene.boundsMin, scene.boundsMax), 0.5);
  const radius = Math.hypot(...sub(scene.boundsMax, scene.boundsMin)) / 2;
  const len = Math.hypot(...sunDir), dir = scale3(sunDir, 1 / len);
  const up: Vec3 = Math.abs(dir[1]) > 0.99 ? [0, 0, 1] : [0, 1, 0];
  const lightViewProj = mul(orthoZO(radius, radius, 0, 2 * radius), lookAt(add3(center, scale3(dir, radius)), center, up));

  const shadow = device.createTexture({ label: 'shadow', size: [shadowSize, shadowSize], format: 'depth32float',
    usage: GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.TEXTURE_BINDING });
  const lightBuf = device.createBuffer({ size: 64, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
  device.queue.writeBuffer(lightBuf, 0, lightViewProj);
  const sm = device.createShaderModule({ code: SHADOW_WGSL, label: 'shadow' });
  const shadowPipe = device.createRenderPipeline({
    label: 'shadow', layout: 'auto',
    vertex: { module: sm, buffers: [
      { arrayStride: 12, attributes: [{ shaderLocation: 0, offset: 0, format: 'float32x3' }] },
      { arrayStride: 8, attributes: [{ shaderLocation: 1, offset: 0, format: 'float32x2' }] },
    ] },
    fragment: { module: sm, targets: [] },
    primitive: { topology: 'triangle-list', cullMode: 'none' },
    depthStencil: { format: 'depth32float', depthWriteEnabled: true, depthCompare: 'less', depthBias: 2, depthBiasSlopeScale: 2 },
  });
  const sampler = device.createSampler({ minFilter: 'linear', magFilter: 'linear', addressModeU: 'repeat', addressModeV: 'repeat' });
  const shadowBG = device.createBindGroup({ layout: shadowPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: lightBuf } }, { binding: 1, resource: { buffer: gpu.materials } },
    { binding: 2, resource: sampler }, { binding: 3, resource: gpu.baseColor.createView({ dimension: '2d-array' }) },
  ] });

  const lit = device.createTexture({ label: 'lit', size: [g.width, g.height], format: 'rgba16float',
    usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_SRC });
  const dm = device.createShaderModule({ code: DIRECT_WGSL, label: 'direct' });
  const directPipe = device.createComputePipeline({ label: 'direct', layout: 'auto', compute: { module: dm, entryPoint: 'direct' } });
  const cmp = device.createSampler({ compare: 'less-equal', minFilter: 'linear', magFilter: 'linear' });
  const directBG = device.createBindGroup({ layout: directPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: g.albedo.createView() },
    { binding: 2, resource: g.normal.createView() }, { binding: 3, resource: g.depth.createView() },
    { binding: 4, resource: shadow.createView() }, { binding: 5, resource: cmp }, { binding: 6, resource: lit.createView() },
  ] });

  return {
    lit, shadow, lightViewProj, bytes: shadowSize * shadowSize * 4 + g.width * g.height * 8,
    encodeShadow(enc, tw) {
      const pass = enc.beginRenderPass({ label: 'shadow', colorAttachments: [],
        depthStencilAttachment: { view: shadow.createView(), depthLoadOp: 'clear', depthStoreOp: 'store', depthClearValue: 1 },
        timestampWrites: tw });
      pass.setPipeline(shadowPipe); pass.setBindGroup(0, shadowBG);
      pass.setVertexBuffer(0, gpu.positions); pass.setVertexBuffer(1, gpu.uvs);
      pass.setIndexBuffer(gpu.indices, 'uint32');
      for (const p of scene.primitives) pass.drawIndexed(p.indexCount, 1, p.firstIndex, p.baseVertex, p.material);
      pass.end();
    },
    encodeDirect(enc, tw) {
      const pass = enc.beginComputePass({ label: 'direct', timestampWrites: tw });
      pass.setPipeline(directPipe); pass.setBindGroup(0, directBG);
      pass.dispatchWorkgroups(Math.ceil(g.width / 8), Math.ceil(g.height / 8));
      pass.end();
    },
  };
}
