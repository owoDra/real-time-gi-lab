// Native S1 run: radiance cascades over the depth buffer (world probes, screen probes, ray splitting).
// Usage: node build/native/s1.mjs [--configs world-8,screen-8,...] [--frames N] [--warmup N] [--out DIR] [--images]
import { mkdirSync, writeFileSync, writeSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { parseGltf } from '../core/gltf.ts';
import { uploadScene } from '../core/scene_gpu.ts';
import { createS1Context, runConfig, SKY } from '../core/s1.ts';
import type { Vec3 } from '../core/math.ts';
import { DEFAULT_PARAMS, type Method, type RcParams } from '../core/rc.ts';
import { createNativeDevice, loadSponza, writePng, IMPLEMENTATION, ROOT } from './env.ts';

// Synchronous logging: a native abort would otherwise drop buffered output.
const log = (s: string) => { writeSync(1, s + '\n'); };
const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const outDir = resolve(arg('--out', join(ROOT, 'out/s1/native')));
const configs = arg('--configs', 'world-8,screen-8,split-8').split(',');
const opts = { warmup: Number(arg('--warmup', '60')), frames: Number(arg('--frames', '240')), inFlight: 2,
  exposure: Number(arg('--exposure', '1.0')), seedFixed: args.includes('--seed-fixed'),
  sky: (args.includes('--no-sky') ? [0, 0, 0] : SKY) as Vec3 };
const overrides = JSON.parse(arg('--params', '{}')) as Partial<RcParams>;

// Exploration only: the sizing pass allocates more than WebGPU's default 128 MiB binding limit.
const { device, adapterInfo } = await createNativeDevice({ maxStorageBufferBindingSize: 1 << 30, maxBufferSize: 1 << 30 });
const { json, bin, upload } = loadSponza();
const t0 = performance.now();
const scene = parseGltf(json, bin);
const gpu = await uploadScene(device, scene, upload);
log(`scene loaded in ${Math.round(performance.now() - t0)} ms; bounds ${scene.boundsMin.map((v) => v.toFixed(2))} .. ${scene.boundsMax.map((v) => v.toFixed(2))}`);
const ctx = createS1Context(device, scene, gpu);
mkdirSync(outDir, { recursive: true });

for (const name of configs) {
  // <method>-<P>[-analytic]
  const [method, P, variant] = name.split('-');
  const params: RcParams = { ...DEFAULT_PARAMS, ...overrides, method: method as Method, P: Number(P), analytic: variant === 'analytic' };
  log(`${name}`);
  const r = await runConfig(ctx, params, opts, (s) => log(s));
  for (const [mode, res] of [['static', r.static], ['moving', r.moving]] as const)
    for (const [img, rgba] of Object.entries(res.images)) writeFileSync(join(outDir, `${name}.${mode}.${img}.png`), writePng(ctx.width, ctx.height, rgba));
  const strip = (x: typeof r.static) => { const { images: _, ...rest } = x; return rest; };
  const summary = {
    kind: 'exploratory (探索値)', date: new Date().toISOString(), platform: 'native', implementation: IMPLEMENTATION, adapter: adapterInfo,
    resolution: `${ctx.width}x${ctx.height}`, frames: { warmup: opts.warmup, measured: opts.frames, inFlight: opts.inFlight, seedFixed: opts.seedFixed }, sky: opts.sky,
    config: name, params: r.params, allocatedBytes: r.allocatedBytes, static: strip(r.static), moving: strip(r.moving),
  };
  writeFileSync(join(outDir, `${name}.summary.json`), JSON.stringify(summary, null, 2));
  const t = r.static.timing, m = r.moving.timing;
  log(`  GI static ${t.giSum.median} ms (build ${t.giBuild.median}, trace ${t.giTrace.median}, merge ${t.giMerge.median}, gather ${t.giGather.median}); moving ${m.giSum.median} ms`);
  log(`  probes ${r.static.counts.join(', ')}; used ${(r.static.usedBytes / 2 ** 20).toFixed(1)} MiB, allocated ${(r.allocatedBytes / 2 ** 20).toFixed(1)} MiB`);
  log(`  flicker static ${JSON.stringify(r.static.flicker)}`);
  log(`  flicker moving ${JSON.stringify(r.moving.flicker)}`);
}
device.destroy();
process.exit(process.exitCode ?? 0);
