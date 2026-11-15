// Same run on two platforms (native and browser): the images of one config compared pixel by pixel.
// Usage: node build/native/compare_runs.mjs --a DIR --b DIR --config NAME [--png DIR]
//   8-bit images (<config>.static.{indirect,final,direct}.png): mean absolute difference in 8-bit levels over all pixels
//   and channels (phase 30: "match" is a mean of 0.5 level or less on the indirect image), max, share of pixels off by
//   more than 2 levels. Irradiance dumps (--dump-irr) if both have them: compareIrradiance over the photoreal pixels.
//   --png: difference images (absolute difference x 16).
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { PNG } from 'pngjs';
import { compareIrradiance } from '../core/rcrun.ts';

const args = process.argv.slice(2);
const arg = (name: string) => { const i = args.indexOf(name); if (i < 0) throw new Error(`missing ${name}`); return args[i + 1]; };
const [a, b, config] = [arg('--a'), arg('--b'), arg('--config')];
const pngDir = args.includes('--png') ? arg('--png') : null;
if (pngDir) mkdirSync(pngDir, { recursive: true });
const result: Record<string, unknown> = { a, b, config };
for (const img of ['indirect', 'final', 'direct']) {
  const fa = join(a, `${config}.static.${img}.png`), fb = join(b, `${config}.static.${img}.png`);
  if (!existsSync(fa) || !existsSync(fb)) continue;
  const A = PNG.sync.read(readFileSync(fa)), B = PNG.sync.read(readFileSync(fb));
  if (A.width !== B.width || A.height !== B.height) throw new Error(`${img}: sizes differ`);
  const n = A.width * A.height, diff = new PNG({ width: A.width, height: A.height });
  let sum = 0, max = 0, over2 = 0;
  for (let p = 0; p < n; p++) {
    let pm = 0;
    for (let c = 0; c < 3; c++) { const d = Math.abs(A.data[p * 4 + c] - B.data[p * 4 + c]); sum += d; pm = Math.max(pm, d); diff.data[p * 4 + c] = Math.min(255, d * 16); }
    diff.data[p * 4 + 3] = 255;
    max = Math.max(max, pm); if (pm > 2) over2++;
  }
  result[img] = { meanAbsLevels: Math.round(sum / (n * 3) * 1e4) / 1e4, maxLevels: max, pixelsOver2LevelsPct: Math.round(over2 / n * 1e5) / 1e3,
    identical: createHash('sha256').update(A.data).digest('hex') === createHash('sha256').update(B.data).digest('hex') };
  if (pngDir) writeFileSync(join(pngDir, `${config}.${img}.diff.png`), PNG.sync.write(diff));
}
const ia = join(a, `${config}.static.irr.f32`), ib = join(b, `${config}.static.irr.f32`);
if (existsSync(ia) && existsSync(ib)) {
  const unpack = (f: string) => {
    const buf = readFileSync(f), v = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4), n = v.length / 4;
    const rgb = new Float32Array(n * 3), valid = new Uint8Array(n), tag = new Uint8Array(n);
    for (let p = 0; p < n; p++) { rgb.set(v.subarray(p * 4, p * 4 + 3), p * 3); tag[p] = v[p * 4 + 3]; valid[p] = tag[p] > 0 ? 1 : 0; }
    return { rgb, valid, tag };
  };
  // b against a (a is the reference: the native run).
  result.irradiance = compareIrradiance(unpack(ib), unpack(ia));
}
console.log(JSON.stringify(result));
