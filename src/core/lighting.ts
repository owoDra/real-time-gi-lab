// Direct sun light: a shadow map and a full-screen pass that writes outgoing (Lambert) radiance per pixel.
// The radiance texture is what the GI passes read at a hit point (one bounce).
import type { SceneData } from './gltf.ts';
import type { SceneGpu } from './scene_gpu.ts';
import type { GBuffer } from './gbuffer.ts';
import { FRAME_WGSL } from './frame.ts';
import { STYLE_WGSL } from './style.ts';
import { add3, cross, dot, lookAt, mul, normalize, orthoZO, scale3, sub, type Mat4, type Vec3 } from './math.ts';
import type { World } from './world.ts';
import { instancedDraws, INSTANCE_WGSL, type InstancedDraws } from './gbuffer.ts';

const SHADOW_WGSL = /* wgsl */ `
struct Material { baseColorFactor: vec4f, layers: vec4u, params: vec4f }
@group(0) @binding(0) var<uniform> lightVP: mat4x4f;
@group(0) @binding(1) var<storage, read> materials: array<Material>;
@group(0) @binding(2) var samp: sampler;
@group(0) @binding(3) var baseColorTex: texture_2d_array<f32>;
@group(0) @binding(4) var<storage, read> instOffset: array<vec4f>;
${INSTANCE_WGSL}
struct VsOut { @builtin(position) clip: vec4f, @location(0) uv: vec2f, @location(1) @interpolate(flat) mat: u32 }
@vertex fn vs(@location(0) pos: vec3f, @location(1) uv: vec2f, @builtin(instance_index) ii: u32) -> VsOut {
  return VsOut(lightVP * vec4f(pos + instOffsetOf(ii), 1.0), uv, ii & 0xffffu);
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
${STYLE_WGSL}
const PI = 3.14159265;
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var albedoTex: texture_2d<f32>;
@group(0) @binding(2) var normalTex: texture_2d<f32>;
@group(0) @binding(3) var depthTex: texture_depth_2d;
@group(0) @binding(4) var shadowTex: texture_depth_2d_array;
@group(0) @binding(5) var shadowSamp: sampler_comparison;
@group(0) @binding(6) var litOut: texture_storage_2d<rgba16float, write>;

fn sunVisibility(x: vec3f) -> f32 {
  let s = shadowCoord(x);
  if (s.w < 0.0) { return 1.0; }
  let texel = 1.0 / vec2f(textureDimensions(shadowTex));
  var v = 0.0;
  for (var j = -1; j <= 1; j++) {
    for (var i = -1; i <= 1; i++) {
      v += textureSampleCompareLevel(shadowTex, shadowSamp, s.xy + vec2f(f32(i), f32(j)) * texel, i32(s.w), s.z);
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
  let ab = textureLoad(albedoTex, px, 0);
  let a = ab.rgb;
  let ndl = max(dot(n, F.sunDir.xyz), 0.0);
  var vis = 0.0;
  if (ndl > 0.0) { vis = sunVisibility(x + n * 0.03); }
  var l = a / PI * F.sunE.rgb * ndl * vis;
  if (ab.a > 0.75 && F.style.x > 0.5) { l = toonSun(a, ndl, vis, F.sunE.rgb); } // S3 emission-side operator
  textureStore(litOut, px, vec4f(l, ndl * vis));
}
`;

export interface Lighting {
  lit: GPUTexture;
  /** Depth, one layer (the whole scene) or, for an instanced world (phase 32), two layers around the camera. */
  shadow: GPUTexture;
  lightViewProj: Mat4;
  /** Phase 32: the second layer's matrix (null with one layer) and the depth bias of each layer. */
  shadowFar: Mat4 | null;
  shadowBias: [number, number];
  /** M1: moves the sun (shadow map projection); lightViewProj is updated in place. */
  setSun(sunDir: Vec3): void;
  /** Phase 32: an instanced world's shadow layers follow the camera (no effect otherwise). Call before packing the frame. */
  setCamera(eye: Vec3): void;
  encodeShadow(enc: GPUCommandEncoder, tw?: GPURenderPassTimestampWrites): void;
  encodeDirect(enc: GPUCommandEncoder, tw?: GPUComputePassTimestampWrites): void;
  bytes: number;
}

// Phase 32 (instanced worlds): two layers centred on the camera, snapped to their texels in the light's plane: layer 0 of
// NEAR_R m (half width; 1.6 cm texels, close to Sponza's whole-scene map) and layer 1 of FAR_R m (the coarsest voxel window
// of the default clipmap). Depth covers DEPTH_R m on either side of the camera along the sun. Biases in metres.
const NEAR_R = 32, FAR_R = 410, DEPTH_R = 300, NEAR_BIAS = 0.012, FAR_BIAS = 0.15;

export function createLighting(device: GPUDevice, scene: SceneData, gpu: SceneGpu, g: GBuffer, frame: GPUBuffer,
  sunDir: Vec3, world: World | null = null, shadowSize = 4096): Lighting {
  const center = scale3(add3(scene.boundsMin, scene.boundsMax), 0.5);
  const radius = Math.hypot(...sub(scene.boundsMax, scene.boundsMin)) / 2;
  let sun = scale3(sunDir, 1 / Math.hypot(...sunDir));
  let eye: Vec3 = center;
  const upOf = (dir: Vec3): Vec3 => Math.abs(dir[1]) > 0.99 ? [0, 0, 1] : [0, 1, 0];
  const sunMatrix = (sd: Vec3) => {
    const dir = scale3(sd, 1 / Math.hypot(...sd));
    return mul(orthoZO(radius, radius, 0, 2 * radius), lookAt(add3(center, scale3(dir, radius)), center, upOf(dir)));
  };
  // A layer of half width r around the camera, its centre snapped to the layer's texels across the sun.
  const cameraMatrix = (dir: Vec3, r: number) => {
    const up0 = upOf(dir), right = normalize(cross(up0, dir)), up = cross(dir, right);
    const texel = 2 * r / shadowSize;
    const snap = (x: number) => Math.round(x / texel) * texel;
    const c = add3(add3(scale3(right, snap(dot(eye, right))), scale3(up, snap(dot(eye, up)))), scale3(dir, dot(eye, dir)));
    return mul(orthoZO(r, r, 0, 2 * DEPTH_R), lookAt(add3(c, scale3(dir, DEPTH_R)), c, up0));
  };
  const layers = world ? 2 : 1;
  const lightViewProj = world ? cameraMatrix(sun, NEAR_R) : sunMatrix(sunDir);
  const shadowFar = world ? cameraMatrix(sun, FAR_R) : null;
  const shadowBias: [number, number] = world ? [NEAR_BIAS / (2 * DEPTH_R), FAR_BIAS / (2 * DEPTH_R)] : [0.0002, 0];

  const shadow = device.createTexture({ label: 'shadow', size: [shadowSize, shadowSize, layers], format: 'depth32float',
    usage: GPUTextureUsage.RENDER_ATTACHMENT | GPUTextureUsage.TEXTURE_BINDING });
  const lightBufs = Array.from({ length: layers }, () => device.createBuffer({ size: 64, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST }));
  const writeLight = () => { device.queue.writeBuffer(lightBufs[0], 0, lightViewProj); if (shadowFar) device.queue.writeBuffer(lightBufs[1], 0, shadowFar); };
  writeLight();
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
  const draws: InstancedDraws = instancedDraws(device, scene, world);
  const shadowBGs = lightBufs.map((b) => device.createBindGroup({ layout: shadowPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: b } }, { binding: 1, resource: { buffer: gpu.materials } },
    { binding: 2, resource: sampler }, { binding: 3, resource: gpu.baseColor.createView({ dimension: '2d-array' }) },
    { binding: 4, resource: { buffer: draws.offsets } },
  ] }));
  const layerViews = Array.from({ length: layers }, (_, l) => shadow.createView({ dimension: '2d', baseArrayLayer: l, arrayLayerCount: 1 }));

  const lit = device.createTexture({ label: 'lit', size: [g.width, g.height], format: 'rgba16float',
    usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_SRC });
  const dm = device.createShaderModule({ code: DIRECT_WGSL, label: 'direct' });
  const directPipe = device.createComputePipeline({ label: 'direct', layout: 'auto', compute: { module: dm, entryPoint: 'direct' } });
  const cmp = device.createSampler({ compare: 'less-equal', minFilter: 'linear', magFilter: 'linear' });
  const directBG = device.createBindGroup({ layout: directPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: g.albedo.createView() },
    { binding: 2, resource: g.normal.createView() }, { binding: 3, resource: g.depth.createView() },
    { binding: 4, resource: shadow.createView({ dimension: '2d-array' }) }, { binding: 5, resource: cmp }, { binding: 6, resource: lit.createView() },
  ] });

  const update = () => {
    if (world) { lightViewProj.set(cameraMatrix(sun, NEAR_R)); shadowFar!.set(cameraMatrix(sun, FAR_R)); }
    else lightViewProj.set(sunMatrix(sun));
    writeLight();
  };
  return {
    setSun(sd) { sun = scale3(sd, 1 / Math.hypot(...sd)); update(); },
    setCamera(e) { if (!world) return; eye = e; update(); },
    lit, shadow, lightViewProj, shadowFar, shadowBias, bytes: shadowSize * shadowSize * 4 * layers + g.width * g.height * 8,
    encodeShadow(enc, tw) {
      // One pass per layer; the timestamps (if any) span the first layer's begin and the last layer's end.
      for (let l = 0; l < layers; l++) {
        const m = l === 0 ? lightViewProj : shadowFar!;
        const pass = enc.beginRenderPass({ label: `shadow${l}`, colorAttachments: [],
          depthStencilAttachment: { view: layerViews[l], depthLoadOp: 'clear', depthStoreOp: 'store', depthClearValue: 1 },
          timestampWrites: tw ? { querySet: tw.querySet, beginningOfPassWriteIndex: l === 0 ? tw.beginningOfPassWriteIndex : undefined,
            endOfPassWriteIndex: l === layers - 1 ? tw.endOfPassWriteIndex : undefined } : undefined });
        pass.setPipeline(shadowPipe); pass.setBindGroup(0, shadowBGs[l]);
        pass.setVertexBuffer(0, gpu.positions); pass.setVertexBuffer(1, gpu.uvs);
        pass.setIndexBuffer(gpu.indices, 'uint32');
        const vis = draws.visible(m);
        for (const p of scene.primitives) for (const i of draws.instancesOf(p, vis)) pass.drawIndexed(p.indexCount, 1, p.firstIndex, p.baseVertex, draws.firstInstance(p, i));
        pass.end();
      }
    },
    encodeDirect(enc, tw) {
      const pass = enc.beginComputePass({ label: 'direct', timestampWrites: tw });
      pass.setPipeline(directPipe); pass.setBindGroup(0, directBG);
      pass.dispatchWorkgroups(Math.ceil(g.width / 8), Math.ceil(g.height / 8));
      pass.end();
    },
  };
}
