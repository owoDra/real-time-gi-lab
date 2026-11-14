// Native radiance-cascade runs.
// Usage: node build/native/rc.mjs [--scene sponza|sponza-wide10|sponza-dense9|sponza-toon|sponza-objects|sponza-dyn*|leak-<t>] [--configs a,b,...]
//   [--frames N] [--warmup N] [--out DIR] [--no-sky] [--params JSON] [--vox JSON] [--bvh] [--static-only]
//   [--vox-bench [--tag T]]  (voxel rebuild alone, per stage)  [--dump-irr]  (static irradiance as float32)
// Config names: <method>-<P>[-<token>...], method world | screen | split. Tokens:
//   analytic (placement test), depth (S1: depth buffer only, the default), voxel (all intervals in voxels),
//   hybrid (c0 depth buffer, voxels when it leaves the screen and above), tri / trihybrid (same with the
//   triangle BVH), l2 (voxel level grows 2 per cascade), rc<N> (directions stop growing above cascade N),
//   vs<x> (c0 voxel size / c0 spacing), vo<x> (voxel trace start offset along the probe normal, voxels),
//   vk<x> (occupied voxels entered within this many voxels are ignored), norel (diagnostic: no probe relocation),
//   vrel (probes relocated from the voxel occupancy instead of the G-buffer: view independent),
//   S3 (toon materials, scene sponza-toon): noemit (toon surfaces inject plain Lambert), norecv (toon pixels receive
//   the physical irradiance), soft<x> (receiving ramp half width in n.d).
import { mkdirSync, writeFileSync, writeSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { parseGltf } from '../core/gltf.ts';
import type { Vec3 } from '../core/math.ts';
import { DEFAULT_DDGI, type DdgiParams } from '../core/ddgi.ts';
import { DEFAULT_PARAMS, type Method, type RcParams } from '../core/rc.ts';
import { benchVoxels, compareIrradiance, createRunContext, lum, readIrradiance, runConfig, SKY } from '../core/rcrun.ts';
import { uploadScene } from '../core/scene_gpu.ts';
import { densify, dynamicSponza, leakRoom, sponzaSpec, toonSponza, widen, type SceneSpec } from '../core/scenes.ts';
import { createNativeDevice, IMPLEMENTATION, loadSponza, ROOT, writePng } from './env.ts';

// Synchronous logging: a native abort would otherwise drop buffered output.
const log = (s: string) => { writeSync(1, s + '\n'); };
const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const sceneName = arg('--scene', 'sponza');
const outDir = resolve(arg('--out', join(ROOT, 'box/out/rc/native', sceneName)));
const configs = arg('--configs', 'world-32').split(',');
const opts = { warmup: Number(arg('--warmup', '60')), frames: Number(arg('--frames', '240')), inFlight: 2,
  exposure: Number(arg('--exposure', '1.0')), seedFixed: args.includes('--seed-fixed'), staticOnly: args.includes('--static-only'),
  sky: (args.includes('--no-sky') ? [0, 0, 0] : SKY) as Vec3,
  poseFrame: args.includes('--pose-frame') ? Number(arg('--pose-frame', '0')) : undefined,
  // R1: --response FROM,TO (use with a sponza-dyn-switch<FROM> scene)
  response: args.includes('--response') ? (([a, b]) => ({ from: a, to: b }))(arg('--response', '').split(',').map(Number)) : undefined };
const overrides = JSON.parse(arg('--params', '{}')) as Partial<RcParams>;

// DDGI comparator: ddgi-<spacing cm>-<rays>[-h<hysteresis>][-noadapt][-u<div>][-norel|-rg][-nocls][-sb<segBase m>][-g<gamma>][-vb<view bias>]
function parseDdgi(name: string): RcParams {
  const [, sp, rays, ...tokens] = name.split('-');
  const d: DdgiParams = { ...DEFAULT_DDGI, spacing: Number(sp) / 100, rays: Number(rays) };
  for (const t of tokens) {
    if (/^h[\d.]+$/.test(t)) d.hysteresis = Number(t.slice(1));
    else if (t === 'noadapt') d.adaptive = false;
    else if (/^u\d+$/.test(t)) d.updateDiv = Number(t.slice(1));
    else if (t === 'norel') d.relocate = 0;
    else if (t === 'rg') d.relocate = 2;
    else if (t === 'nocls') d.classify = false;
    else if (/^sb[\d.]+$/.test(t)) d.segBase = Number(t.slice(2));
    else if (/^g[\d.]+$/.test(t)) d.gamma = Number(t.slice(1));
    else if (/^vb[\d.]+$/.test(t)) d.viewBias = Number(t.slice(2));
    else throw new Error(`unknown ddgi token ${t} in ${name}`);
  }
  return { ...DEFAULT_PARAMS, ...overrides, world: 'voxel', depthCascades: 0, ddgi: d };
}

function parseConfig(name: string): RcParams {
  if (name.startsWith('ddgi-')) return parseDdgi(name);
  const [method, P, ...tokens] = name.split('-');
  const p: RcParams = { ...DEFAULT_PARAMS, ...overrides, method: method as Method, P: Number(P) };
  for (const t of tokens) {
    if (t === 'analytic') p.analytic = true;
    else if (t === 'depth') p.world = 'none';
    else if (t === 'voxel') { p.world = 'voxel'; p.depthCascades = 0; }
    else if (t === 'hybrid') { p.world = 'voxel'; p.depthCascades = 1; }
    else if (t === 'tri') { p.world = 'tri'; p.depthCascades = 0; }
    else if (t === 'trihybrid') { p.world = 'tri'; p.depthCascades = 1; }
    else if (t === 'l2') p.levelMap = 2;
    else if (t === 'norel') p.relocate = 'none';
    else if (t === 'vrel') p.relocate = 'voxel';
    else if (t === 'noemit') p.styleEmit = false;
    else if (t === 'norecv') p.styleRecv = false;
    else if (/^soft[\d.]+$/.test(t)) p.rampSoft = Number(t.slice(4));
    else if (/^rc\d$/.test(t)) p.resCap = Number(t.slice(2));
    else if (/^vs[\d.]+$/.test(t)) p.voxScale = Number(t.slice(2));
    else if (/^vo[\d.]+$/.test(t)) p.voxOffset = Number(t.slice(2));
    else if (/^vk[\d.]+$/.test(t)) p.voxSkip = Number(t.slice(2));
    else throw new Error(`unknown config token ${t} in ${name}`);
  }
  return p;
}
const parsed = configs.map((c) => [c, parseConfig(c)] as const);

// Exploration only: beyond WebGPU's default limits (128 MiB bindings, 8 storage buffers per stage).
const { device, adapterInfo } = await createNativeDevice({ maxStorageBufferBindingSize: 1 << 30, maxBufferSize: 1 << 30, maxStorageBuffersPerShaderStage: 16 });
const t0 = performance.now();
let spec: SceneSpec;
let upload: Parameters<typeof uploadScene>[2] = async () => undefined;
if (sceneName.startsWith('leak-')) spec = leakRoom(Number(sceneName.slice(5)));
else {
  const s = loadSponza();
  upload = s.upload;
  const base = parseGltf(s.json, s.bin);
  spec = sceneName === 'sponza' ? sponzaSpec(base) : sceneName === 'sponza-wide10' ? widen(base, 10)
    : sceneName === 'sponza-dense9' ? densify(base) : sceneName === 'sponza-toon' ? toonSponza(base)
    : sceneName === 'sponza-objects' ? toonSponza(base, true)
    : sceneName === 'sponza-dyn' ? dynamicSponza(base) : sceneName === 'sponza-dynobj' ? dynamicSponza(base, true)
    : sceneName === 'sponza-dyn-sunonly' ? dynamicSponza(base, false, -1, 'sun') : sceneName === 'sponza-dyn-objectsonly' ? dynamicSponza(base, false, -1, 'objects')
    : sceneName === 'sponza-dynobj-sunonly' ? dynamicSponza(base, true, -1, 'sun') : sceneName === 'sponza-dynobj-objectsonly' ? dynamicSponza(base, true, -1, 'objects')
    : sceneName === 'sponza-dynobj-sphereonly' ? dynamicSponza(base, true, -1, 'sphere')
    : sceneName.startsWith('sponza-dyn-switch') ? dynamicSponza(base, false, Number(sceneName.slice('sponza-dyn-switch'.length)))
    : (() => { throw new Error(`unknown scene ${sceneName}`); })();
}
const gpu = await uploadScene(device, spec.scene, upload);
const needBvh = args.includes('--bvh') || parsed.some(([, p]) => p.world === 'tri');
const voxBench = args.includes('--vox-bench');
const needVox = voxBench || parsed.some(([, p]) => p.world === 'voxel' || p.relocate === 'voxel');
const ctx = createRunContext(device, spec, gpu, { voxel: needVox, bvh: needBvh, vox: JSON.parse(arg('--vox', '{}')) });
let staticBuildMs: number | null = null;
if (ctx.voxWorld?.params.local) {
  ctx.voxWorld.update(spec.camera.eye);
  staticBuildMs = await ctx.voxWorld.buildStatic();
  log(`voxels: static triangles built once in ${staticBuildMs.toFixed(2)} ms; dynamic triangles (from ${spec.dynamic?.firstTriangle}) in the dynamic layer`);
}
log(`scene ${spec.name}: ${spec.scene.triangleCount} triangles, loaded in ${Math.round(performance.now() - t0)} ms; bounds ${spec.scene.boundsMin.map((v) => v.toFixed(2))} .. ${spec.scene.boundsMax.map((v) => v.toFixed(2))}`
  + (ctx.bvh ? `; BVH ${ctx.bvh.nodes} nodes, ${(ctx.bvh.bytes / 2 ** 20).toFixed(1)} MiB, built in ${ctx.bvh.buildMs} ms (CPU)` : ''));
mkdirSync(outDir, { recursive: true });
if (voxBench) {
  const r = await benchVoxels(ctx, 60);
  log(JSON.stringify(r));
  writeFileSync(join(outDir, `vox-bench.${arg('--tag', 'default')}.json`), JSON.stringify({ kind: 'exploratory (探索値)', date: new Date().toISOString(),
    implementation: IMPLEMENTATION, adapter: adapterInfo, scene: { name: spec.name, triangles: spec.scene.triangleCount }, voxParams: ctx.voxWorld!.params, ...r }, null, 2));
  device.destroy();
  process.exit(process.exitCode ?? 0);
}

const irr: Record<string, Awaited<ReturnType<typeof readIrradiance>> | null> = {};
const summaries: Record<string, any> = {};
for (const [name, params] of parsed) {
  log(`${name}`);
  const r0 = await runConfig(ctx, params, opts, (s) => log(s));
  if (r0.response) {
    const rr = r0.response;
    log(`  response: 90% after ${rr.frames90} frames, 50% after ${rr.frames50}; curve ${rr.curve.slice(0, 12).join(', ')} ...`);
    writeFileSync(join(outDir, `${name}.response.json`), JSON.stringify({ kind: 'exploratory (探索値)', date: new Date().toISOString(), scene: spec.name,
      config: name, params: r0.params, ...rr }, null, 2));
    continue;
  }
  const r = r0 as Required<typeof r0>;
  for (const [mode, res] of [['static', r.static], ['moving', r.moving]] as const)
    if (res) for (const [img, rgba] of Object.entries(res.images)) writeFileSync(join(outDir, `${name}.${mode}.${img}.png`), writePng(ctx.width, ctx.height, rgba));
  irr[name] = r.static.irr;
  if (args.includes('--dump-irr') && r.static.irr) {
    // rgb + tag (0 invalid, 1 photoreal, >= 2 toon) as float32, rows top to bottom (for the Mitsuba comparison).
    const { rgb, tag } = r.static.irr, f = new Float32Array(tag.length * 4);
    for (let p = 0; p < tag.length; p++) { f.set(rgb.subarray(p * 3, p * 3 + 3), p * 4); f[p * 4 + 3] = tag[p]; }
    writeFileSync(join(outDir, `${name}.static.irr.f32`), Buffer.from(f.buffer));
  }
  const strip = (x: typeof r.static | null) => { if (!x) return null; const { images: _, irr: __, ...rest } = x; return rest; };
  let leak = null;
  if (spec.enclosed && r.static.irr) {
    const { rgb, valid } = r.static.irr;
    let s = 0, n = 0, mx = 0;
    const all: number[] = [];
    for (let p = 0; p < valid.length; p++) if (valid[p]) { const l = lum(rgb[p * 3], rgb[p * 3 + 1], rgb[p * 3 + 2]); s += l; n++; mx = Math.max(mx, l); if (p % 5 === 0) all.push(l); }
    all.sort((a, b) => a - b);
    // Reference scale: the sun's irradiance on the floor outside.
    const sd = spec.sunDir, sunOnFloor = lum(9, 8.5, 7.8) * sd[1] / Math.hypot(...sd);
    leak = { meanIrradiance: s / n, p99Irradiance: all[Math.floor(all.length * 0.99)], maxIrradiance: mx, sunOnFloor,
      meanFractionOfSun: s / n / sunOnFloor, pixels: n };
  }
  summaries[name] = {
    kind: 'exploratory (探索値)', date: new Date().toISOString(), platform: 'native', implementation: IMPLEMENTATION, adapter: adapterInfo,
    scene: { name: spec.name, triangles: spec.scene.triangleCount, sunDir: spec.sunDir }, resolution: `${ctx.width}x${ctx.height}`,
    frames: { warmup: opts.warmup, measured: opts.frames, inFlight: opts.inFlight, seedFixed: opts.seedFixed }, sky: opts.sky,
    config: name, params: r.params, ddgiDims: r.ddgiDims, voxStaticBuildMs: staticBuildMs, allocatedBytes: r.allocatedBytes, voxAllocatedBytes: r.voxAllocatedBytes, bvh: ctx.bvh,
    voxParams: ctx.voxWorld?.params ?? null, static: strip(r.static), moving: strip(r.moving), tracer: r.tracer, leak,
  };
  const t = r.static.timing, m = r.moving?.timing;
  if (r.ddgiDims) log(`  ddgi grid ${r.ddgiDims.join('x')}; active, updated, relocated, stuck: ${r.static.counts.join(', ')}`);
  log(`  GI static ${t.giTotal.median} ms (vox ${t.vox?.median ?? '-'}, build ${t.giBuild.median}, trace ${t.giTrace.median}, merge ${t.giMerge.median}, gather ${t.giGather.median})` + (m ? `; moving ${m.giTotal.median} ms` : ''));
  log(`  probes ${r.static.counts.join(', ')}; used ${(r.static.usedBytes / 2 ** 20).toFixed(1)} MiB, allocated ${(r.allocatedBytes / 2 ** 20).toFixed(1)} MiB`);
  if (r.static.vox) log(`  vox ${JSON.stringify(r.static.vox)}`);
  if (r.tracer) log(`  tracer ${JSON.stringify(r.tracer)}`);
  if (leak) log(`  leak ${JSON.stringify(leak)}`);
  log(`  flicker static ${JSON.stringify(r.static.flicker)}`);
  log(`  excess static ${JSON.stringify(r.static.excess)}`);
  if (r.moving) log(`  flicker moving ${JSON.stringify(r.moving.flicker)}`);
}
// Irradiance against the triangle tracer (same probes, same intervals), static camera.
// The reference uses the same probe relocation when the run has one (same probe positions).
const tris = parsed.filter(([, p]) => p.world === 'tri' && p.depthCascades === 0);
for (const [name, params] of parsed) {
  const ref = (tris.find(([, p]) => p.relocate === params.relocate) ?? tris[0])?.[0];
  if (!ref || name === ref || !irr[name] || !irr[ref]) continue;
  summaries[name].vsTriangle = { reference: ref, ...compareIrradiance(irr[name]!, irr[ref]!) };
  log(`${name} vs ${ref}: ${JSON.stringify(summaries[name].vsTriangle)}`);
}
for (const [name] of parsed) if (summaries[name]) writeFileSync(join(outDir, `${name}.summary.json`), JSON.stringify(summaries[name], null, 2));
device.destroy();
process.exit(process.exitCode ?? 0);
