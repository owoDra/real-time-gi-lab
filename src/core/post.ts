// Display (tonemapped captures) and the band-boundary flicker metric.
//
// Flicker: for each pixel, find the same surface point in the previous frame (reprojection with the
// previous camera, nearest pixel, accepted when the world positions are within two pixel footprints and the
// normals agree). Count pixels whose quantised log-luminance band of the indirect irradiance changed.
// Fine bands are 1/4 stop, coarse bands 1 stop. A world-fixed smooth analytic field goes through the same
// reprojection as a control (it also depends on the shading normal, as irradiance does), so its rate is the
// floor that the measurement itself produces.
import { FRAME_WGSL } from './frame.ts';
import type { GBuffer } from './gbuffer.ts';

const DISPLAY_WGSL = /* wgsl */ `
${FRAME_WGSL}
const PI = 3.14159265;
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var albedoTex: texture_2d<f32>;
@group(0) @binding(2) var depthTex: texture_depth_2d;
@group(0) @binding(3) var litTex: texture_2d<f32>;
@group(0) @binding(4) var irrTex: texture_2d<f32>;
@group(0) @binding(5) var outTex: texture_storage_2d<rgba8unorm, write>;
@group(0) @binding(6) var<uniform> mode: vec4u;
fn aces(x: vec3f) -> vec3f { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), vec3f(0.0), vec3f(1.0)); }
fn toSrgb(c: vec3f) -> vec3f { return select(1.055 * pow(c, vec3f(1.0 / 2.4)) - 0.055, c * 12.92, c <= vec3f(0.0031308)); }
@compute @workgroup_size(8, 8) fn display(@builtin(global_invocation_id) gid: vec3u) {
  if (gid.x >= u32(F.size.x) || gid.y >= u32(F.size.y)) { return; }
  let px = vec2i(gid.xy);
  let d = textureLoad(depthTex, px, 0);
  let a = textureLoad(albedoTex, px, 0).rgb;
  let e = textureLoad(irrTex, px, 0).rgb;
  let lit = textureLoad(litTex, px, 0).rgb;
  var c = vec3f(0.0);
  if (d <= 0.0) { c = F.sky.rgb; }
  else if (mode.x == 0u) { c = lit + a / PI * e; }
  else if (mode.x == 1u) { c = 0.8 / PI * e; }
  else { c = lit; }
  textureStore(outTex, px, vec4f(toSrgb(aces(c * F.rc2.w)), 1.0));
}
`;

const FLICKER_WGSL = /* wgsl */ `
${FRAME_WGSL}
@group(0) @binding(0) var<uniform> F: Frame;
@group(0) @binding(1) var depthTex: texture_depth_2d;
@group(0) @binding(2) var normalTex: texture_2d<f32>;
@group(0) @binding(3) var irrTex: texture_2d<f32>;
@group(0) @binding(4) var depthPrev: texture_depth_2d;
@group(0) @binding(5) var normalPrev: texture_2d<f32>;
@group(0) @binding(6) var irrPrev: texture_2d<f32>;
@group(0) @binding(7) var<storage, read_write> counters: array<atomic<u32>>;
@group(0) @binding(8) var heat: texture_storage_2d<rgba8unorm, write>;
var<workgroup> wc: array<atomic<u32>, 8>;

// World-fixed smooth field with a cosine-like normal dependence, like irradiance.
fn control(x: vec3f, n: vec3f) -> f32 {
  return exp2(1.5 * sin(0.9 * x.x + 0.3) * sin(0.7 * x.y + 1.1) + sin(0.8 * x.z + 0.5)) * (0.7 + 0.2 * n.y + 0.1 * n.x);
}
fn lb(v: f32) -> f32 { return log2(max(v, 1e-3)); }

@compute @workgroup_size(8, 8) fn flicker(@builtin(global_invocation_id) gid: vec3u, @builtin(local_invocation_index) li: u32) {
  if (li < 8u) { atomicStore(&wc[li], 0u); }
  workgroupBarrier();
  var ok = gid.x < u32(F.size.x) && gid.y < u32(F.size.y) && F.ru2.z == 1u;
  let px = vec2i(gid.xy);
  var d = 0.0;
  if (ok) { d = textureLoad(depthTex, px, 0); ok = d > 0.0; }
  var x = vec3f(0.0); var q = vec2i(0);
  var hv = vec4f(0.0, 0.0, 0.0, 1.0);
  if (ok) {
    x = worldAt(px, d);
    let c = F.prevViewProj * vec4f(x, 1.0);
    ok = c.w > F.eye.w;
    if (ok) {
      let ndc = c.xy / c.w;
      ok = all(abs(ndc) < vec2f(1.0));
      q = vec2i(floor(vec2f(ndc.x * 0.5 + 0.5, 0.5 - ndc.y * 0.5) * F.size.xy));
      q = clamp(q, vec2i(0), vec2i(F.size.xy) - 1);
    }
  }
  if (ok) {
    let dq = textureLoad(depthPrev, q, 0);
    ok = dq > 0.0;
    if (ok) {
      let xq = prevWorldAt(q, dq);
      let tol = 2.0 * distance(x, F.eye.xyz) * F.rc.y + 0.005;
      let n = textureLoad(normalTex, px, 0).xyz;
      let nq = textureLoad(normalPrev, q, 0).xyz;
      ok = distance(x, xq) < tol && dot(n, nq) > 0.9;
      if (ok) {
        let e = lb(luminance(textureLoad(irrTex, px, 0).rgb));
        let eq = lb(luminance(textureLoad(irrPrev, q, 0).rgb));
        let c0 = lb(control(x, n)); let c1 = lb(control(xq, nq));
        atomicAdd(&wc[0], 1u);
        hv = vec4f(0.25, 0.25, 0.25, 1.0);
        if (floor(e * 4.0) != floor(eq * 4.0)) { atomicAdd(&wc[1], 1u); hv = vec4f(1.0, 0.2, 0.1, 1.0); }
        if (floor(e) != floor(eq)) { atomicAdd(&wc[2], 1u); }
        if (floor(c0 * 4.0) != floor(c1 * 4.0)) { atomicAdd(&wc[3], 1u); }
        if (floor(c0) != floor(c1)) { atomicAdd(&wc[4], 1u); }
        atomicAdd(&wc[5], u32(min(abs(e - eq), 10.0) * 1000.0));
        atomicAdd(&wc[6], u32(min(abs(c0 - c1), 10.0) * 1000.0));
      }
    }
  }
  if (gid.x < u32(F.size.x) && gid.y < u32(F.size.y)) { textureStore(heat, px, hv); }
  workgroupBarrier();
  if (li < 8u) {
    let v = atomicLoad(&wc[li]);
    if (v > 0u) { atomicAdd(&counters[F.ru.y * 8u + li], v); }
  }
}
`;

export const FLICKER_FIELDS = ['valid', 'giFine', 'giCoarse', 'ctrlFine', 'ctrlCoarse', 'giAbsDlog2Milli', 'ctrlAbsDlog2Milli', 'unused'] as const;

export function createPost(device: GPUDevice, g: GBuffer, frame: GPUBuffer, lit: GPUTexture, irr: GPUTexture, maxSlots: number) {
  const { width, height } = g;
  const out = device.createTexture({ label: 'display', size: [width, height], format: 'rgba8unorm',
    usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.COPY_SRC });
  const dm = device.createShaderModule({ code: DISPLAY_WGSL, label: 'display' });
  const displayPipe = device.createComputePipeline({ layout: 'auto', compute: { module: dm, entryPoint: 'display' } });
  const displayBG = [0, 1, 2].map((m) => {
    const b = device.createBuffer({ size: 16, usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST });
    device.queue.writeBuffer(b, 0, new Uint32Array([m, 0, 0, 0]));
    return device.createBindGroup({ layout: displayPipe.getBindGroupLayout(0), entries: [
      { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: g.albedo.createView() },
      { binding: 2, resource: g.depth.createView() }, { binding: 3, resource: lit.createView() },
      { binding: 4, resource: irr.createView() }, { binding: 5, resource: out.createView() }, { binding: 6, resource: { buffer: b } },
    ] });
  });

  const usage = GPUTextureUsage.TEXTURE_BINDING | GPUTextureUsage.COPY_DST;
  const depthPrev = device.createTexture({ size: [width, height], format: 'depth32float', usage });
  const normalPrev = device.createTexture({ size: [width, height], format: g.normal.format, usage });
  const irrPrev = device.createTexture({ size: [width, height], format: irr.format, usage });
  const heat = device.createTexture({ label: 'flicker.heat', size: [width, height], format: 'rgba8unorm',
    usage: GPUTextureUsage.STORAGE_BINDING | GPUTextureUsage.COPY_SRC });
  const counters = device.createBuffer({ size: maxSlots * 32, usage: GPUBufferUsage.STORAGE | GPUBufferUsage.COPY_SRC | GPUBufferUsage.COPY_DST });
  const fm = device.createShaderModule({ code: FLICKER_WGSL, label: 'flicker' });
  const flickerPipe = device.createComputePipeline({ layout: 'auto', compute: { module: fm, entryPoint: 'flicker' } });
  const flickerBG = device.createBindGroup({ layout: flickerPipe.getBindGroupLayout(0), entries: [
    { binding: 0, resource: { buffer: frame } }, { binding: 1, resource: g.depth.createView() },
    { binding: 2, resource: g.normal.createView() }, { binding: 3, resource: irr.createView() },
    { binding: 4, resource: depthPrev.createView() }, { binding: 5, resource: normalPrev.createView() },
    { binding: 6, resource: irrPrev.createView() }, { binding: 7, resource: { buffer: counters } },
    { binding: 8, resource: heat.createView() },
  ] });

  return {
    counters,
    /** Measures against the previous frame (if the frame uniform says it is valid), then keeps this frame. */
    encodeFlicker(enc: GPUCommandEncoder) {
      const pass = enc.beginComputePass({ label: 'flicker' });
      pass.setPipeline(flickerPipe); pass.setBindGroup(0, flickerBG);
      pass.dispatchWorkgroups(Math.ceil(width / 8), Math.ceil(height / 8));
      pass.end();
      enc.copyTextureToTexture({ texture: g.depth }, { texture: depthPrev }, [width, height]);
      enc.copyTextureToTexture({ texture: g.normal }, { texture: normalPrev }, [width, height]);
      enc.copyTextureToTexture({ texture: irr }, { texture: irrPrev }, [width, height]);
    },
    async readCounters(slots: number): Promise<Uint32Array> {
      const read = device.createBuffer({ size: slots * 32, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
      const enc = device.createCommandEncoder();
      enc.copyBufferToBuffer(counters, 0, read, 0, slots * 32);
      device.queue.submit([enc.finish()]);
      await read.mapAsync(GPUMapMode.READ);
      const r = new Uint32Array(read.getMappedRange().slice(0));
      read.unmap(); read.destroy();
      return r;
    },
    clearCounters() { device.queue.writeBuffer(counters, 0, new Uint8Array(maxSlots * 32)); },
    /** Mode 0: final (direct + indirect), 1: indirect irradiance on a 0.8 albedo, 2: direct only,
     * 3: flicker heatmap of the last measured frame (red: fine band changed, grey: valid). Tightly packed RGBA8. */
    async capture(mode: number): Promise<Uint8Array> {
      const enc = device.createCommandEncoder();
      if (mode < 3) {
        const pass = enc.beginComputePass();
        pass.setPipeline(displayPipe); pass.setBindGroup(0, displayBG[mode]);
        pass.dispatchWorkgroups(Math.ceil(width / 8), Math.ceil(height / 8));
        pass.end();
      }
      const bytesPerRow = Math.ceil(width * 4 / 256) * 256;
      const readback = device.createBuffer({ size: bytesPerRow * height, usage: GPUBufferUsage.COPY_DST | GPUBufferUsage.MAP_READ });
      enc.copyTextureToBuffer({ texture: mode < 3 ? out : heat }, { buffer: readback, bytesPerRow }, [width, height]);
      device.queue.submit([enc.finish()]);
      await readback.mapAsync(GPUMapMode.READ);
      const src = new Uint8Array(readback.getMappedRange());
      const img = new Uint8Array(width * height * 4);
      for (let y = 0; y < height; y++) img.set(src.subarray(y * bytesPerRow, y * bytesPerRow + width * 4), y * width * 4);
      readback.unmap(); readback.destroy();
      return img;
    },
  };
}
