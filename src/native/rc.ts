// Native radiance-cascade runs.
// Usage: node build/native/rc.mjs [--scene sponza|sponza-wide10|sponza-dense9|sponza-toon|sponza-objects|sponza-dyn*|leak-<t>|town*][-bwave|-bcut] [--configs a,b,...]
//   [--frames N] [--warmup N] [--out DIR] [--no-sky] [--params JSON] [--vox JSON] [--bvh] [--static-only]
//   [--pose-frame F] [--seq EVERY,COUNT]  (static camera: final and indirect images every EVERY frames, timings disturbed)
//   [--vox-bench [--tag T]]  (voxel rebuild alone, per stage)  [--dump-irr]  (static irradiance as float32)
//   [--dyn-stages]  (the static voxel build and the dynamic layer build timed per stage in separate passes, and the dynamic
//                    layer's work counted; at most 4096 / timestamps-per-frame frames)
//   --vox JSON overrides voxel.ts DEFAULT_VOX (v0, levels, G, maxBricks, maxVoxels, dynBricks).
//   Scene suffix -bwave / -bcut: the building itself changes every frame (src/core/building.ts).
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
import type { Vec3 } from '../core/math.ts';
import type { RcParams } from '../core/rc.ts';
import { benchVoxels, compareIrradiance, createRunContext, readIrradiance, runConfig, SKY } from '../core/rcrun.ts';
import { uploadScene } from '../core/scene_gpu.ts';
import { parseConfig } from '../runner/configs.ts';
import { packIrradiance, reportConfig } from '../runner/report.ts';
import { loadScene } from '../runner/scene.ts';
import { createNativeDevice, IMPLEMENTATION, loadSponza, ROOT, writePng } from './env.ts';

// Synchronous logging: a native abort would otherwise drop buffered output.
const log = (s: string) => { writeSync(1, s + '\n'); };
const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const sceneArg = arg('--scene', 'sponza');
const outDir = resolve(arg('--out', join(ROOT, 'box/out/rc/native', sceneArg)));
const configs = arg('--configs', 'world-32').split(',');
const opts = { warmup: Number(arg('--warmup', '60')), frames: Number(arg('--frames', '240')), inFlight: 2,
  exposure: Number(arg('--exposure', '1.0')), seedFixed: args.includes('--seed-fixed'), staticOnly: args.includes('--static-only'),
  dynStages: args.includes('--dyn-stages'),
  sky: (args.includes('--no-sky') ? [0, 0, 0] : SKY) as Vec3,
  poseFrame: args.includes('--pose-frame') ? Number(arg('--pose-frame', '0')) : undefined,
  // --seq EVERY,COUNT: static camera, final and indirect images every EVERY measured frames (timings are disturbed).
  seq: args.includes('--seq') ? (([every, count]) => ({ every, count, sink: (k: number, im: Record<string, Uint8Array>) => {
    for (const [img, rgba] of Object.entries(im)) writeFileSync(join(outDir, `seq.${String(k).padStart(3, '0')}.${img}.png`), writePng(ctx.width, ctx.height, rgba)); } }))(arg('--seq', '').split(',').map(Number)) : undefined,
  // R1: --response FROM,TO (use with a sponza-dyn-switch<FROM> scene)
  response: args.includes('--response') ? (([a, b]) => ({ from: a, to: b }))(arg('--response', '').split(',').map(Number)) : undefined };
const overrides = JSON.parse(arg('--params', '{}')) as Partial<RcParams>;

const parsed = configs.map((c) => [c, parseConfig(c, overrides)] as const);

// WebGPU's default limits (128 MiB per binding, 256 MiB per buffer, 8 storage buffers per stage).
const { device, adapterInfo } = await createNativeDevice();
log(`limits: maxStorageBufferBindingSize ${device.limits.maxStorageBufferBindingSize}, maxBufferSize ${device.limits.maxBufferSize}, maxStorageBuffersPerShaderStage ${device.limits.maxStorageBuffersPerShaderStage}`);
const t0 = performance.now();
const { spec, upload } = await loadScene(sceneArg, async () => loadSponza());
const gpu = await uploadScene(device, spec.scene, upload);
const needBvh = args.includes('--bvh') || parsed.some(([, p]) => p.world === 'tri');
const voxBench = args.includes('--vox-bench');
const needVox = voxBench || parsed.some(([, p]) => p.world === 'voxel' || p.relocate === 'voxel');
const ctx = createRunContext(device, spec, gpu, { voxel: needVox, bvh: needBvh, vox: JSON.parse(arg('--vox', '{}')) });
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
    log(`  response: 90% after ${rr.frames90} frames, 50% after ${rr.frames50}; end value ${JSON.stringify(rr.end)}; curve ${rr.curve.slice(0, 12).join(', ')} ... last ${rr.curve[rr.curve.length - 1]}`);
    writeFileSync(join(outDir, `${name}.response.json`), JSON.stringify({ kind: 'exploratory (探索値)', date: new Date().toISOString(), scene: spec.name,
      config: name, params: r0.params, ...rr }, null, 2));
    continue;
  }
  const r = r0 as Required<typeof r0>;
  for (const [mode, res] of [['static', r.static], ['moving', r.moving], ['static-geo', r.staticGeo], ['moving-geo', r.movingGeo]] as const)
    if (res) for (const [img, rgba] of Object.entries(res.images)) writeFileSync(join(outDir, `${name}.${mode}.${img}.png`), writePng(ctx.width, ctx.height, rgba));
  irr[name] = r.static.irr;
  if (args.includes('--dump-irr') && r.static.irr) {
    writeFileSync(join(outDir, `${name}.static.irr.f32`), Buffer.from(packIrradiance(r.static.irr).buffer));
  }
  summaries[name] = reportConfig(name, r, ctx, opts, { platform: 'native', implementation: IMPLEMENTATION, adapter: adapterInfo }, log);
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
