// Native S0 run: Dawn (Vulkan) through the `webgpu` npm package.
// Usage: node build/native/main.mjs [--frames N] [--warmup N] [--out DIR]
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { runGBufferBench, DEFAULT_OPTIONS } from '../core/bench.ts';
import { summarize } from '../core/report.ts';
import { createNativeDevice, loadSponza, writePng, IMPLEMENTATION, ROOT } from './env.ts';

const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const outDir = resolve(arg('--out', join(ROOT, 'out/s0/native')));
const options = { ...DEFAULT_OPTIONS, frames: Number(arg('--frames', String(DEFAULT_OPTIONS.frames))), warmup: Number(arg('--warmup', String(DEFAULT_OPTIONS.warmup))) };

const { device, adapterInfo } = await createNativeDevice();
const { json, bin, upload } = loadSponza();

const result = await runGBufferBench(device, json, bin, upload, options, (s) => console.log(s));
mkdirSync(outDir, { recursive: true });
for (const [name, rgba] of Object.entries(result.images))
  writeFileSync(join(outDir, `${name}.png`), writePng(options.width, options.height, rgba));
const summary = summarize(result, { platform: 'native', implementation: IMPLEMENTATION, userAgent: `node ${process.version}`, adapter: adapterInfo });
writeFileSync(join(outDir, 'summary.json'), JSON.stringify(summary, null, 2));
writeFileSync(join(outDir, 'pass_ns.json'), JSON.stringify(result.passNs));
console.log(JSON.stringify(summary.gbufferPass, null, 2));
device.destroy();
process.exit(process.exitCode ?? 0);
