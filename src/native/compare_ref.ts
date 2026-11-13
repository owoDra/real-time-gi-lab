// Compares the renderer's static indirect irradiance (--dump-irr) with the Mitsuba reference
// (scripts/reference_irradiance.py). Ours is box-filtered down to the reference resolution.
// Usage: node build/native/compare_ref.mjs --ref E.pfm[,E2.pfm...] --ours a.static.irr.f32[,b...] [--width 1920 --height 1080]
//   [--png DIR]  (side-by-side images: reference | ours, same exposure) [--json FILE]
import { readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { lum } from '../core/rcrun.ts';
import { writePng } from './env.ts';

const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const W = Number(arg('--width', '1920')), H = Number(arg('--height', '1080'));

function readPfm(file: string) {
  const buf = readFileSync(file);
  let off = 0;
  const line = () => { const e = buf.indexOf(10, off); const s = buf.toString('ascii', off, e).trim(); off = e + 1; return s; };
  const kind = line(); if (kind !== 'PF') throw new Error(`not an RGB PFM: ${kind}`);
  const [w, h] = line().split(/\s+/).map(Number); const scale = Number(line());
  const le = scale < 0, rgb = new Float32Array(w * h * 3);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let c = 0; c < 3; c++) {
    const o = off + ((h - 1 - y) * w + x) * 12 + c * 4; // PFM rows go bottom to top
    rgb[(y * w + x) * 3 + c] = le ? buf.readFloatLE(o) : buf.readFloatBE(o);
  }
  return { w, h, rgb };
}

// Several reference files (independent seeds) are averaged; the difference between the first two shows the
// reference's own noise (the average's error is about half of it).
const refs = arg('--ref', '').split(',').map(readPfm);
const ref = refs[0];
let refNoise: number | null = null;
if (refs.length > 1) {
  let sd = 0, ss = 0;
  for (let p = 0; p < ref.w * ref.h; p++) {
    const a = lum(refs[0].rgb[p * 3], refs[0].rgb[p * 3 + 1], refs[0].rgb[p * 3 + 2]), b = lum(refs[1].rgb[p * 3], refs[1].rgb[p * 3 + 1], refs[1].rgb[p * 3 + 2]);
    sd += Math.abs(a - b); ss += (a + b) / 2;
  }
  refNoise = Math.round(sd / ss * 1e4) / 1e4;
  ref.rgb = ref.rgb.map((_, i) => refs.reduce((s, r) => s + r.rgb[i], 0) / refs.length);
  console.log(`reference: ${refs.length} renders averaged; mean |half A - half B| / mean = ${refNoise}`);
}
const fx = W / ref.w, fy = H / ref.h;
if (!Number.isInteger(fx) || fx !== fy) throw new Error('resolution must be an integer multiple of the reference');
const tonemap = (v: number) => Math.round(255 * Math.min(1, Math.pow(Math.max(v, 0) / (1 + Math.max(v, 0)), 1 / 2.2)));
const results: Record<string, unknown> = {};
for (const file of arg('--ours', '').split(',')) {
  const raw = readFileSync(file), f = new Float32Array(raw.buffer, raw.byteOffset, raw.byteLength / 4);
  const ours = new Float32Array(ref.w * ref.h * 3), ok = new Uint8Array(ref.w * ref.h);
  for (let y = 0; y < ref.h; y++) for (let x = 0; x < ref.w; x++) {
    let n = 0; const s = [0, 0, 0];
    for (let j = 0; j < fy; j++) for (let i = 0; i < fx; i++) {
      const p = (y * fy + j) * W + x * fx + i;
      if (f[p * 4 + 3] > 0.5) { n++; for (let c = 0; c < 3; c++) s[c] += f[p * 4 + c]; }
    }
    if (n === fx * fy) { ok[y * ref.w + x] = 1; for (let c = 0; c < 3; c++) ours[(y * ref.w + x) * 3 + c] = s[c] / n; }
  }
  let sr = 0, so = 0, sabs = 0, cnt = 0;
  const rel: number[] = [];
  for (let p = 0; p < ok.length; p++) {
    if (!ok[p]) continue;
    const lr = lum(ref.rgb[p * 3], ref.rgb[p * 3 + 1], ref.rgb[p * 3 + 2]), lo = lum(ours[p * 3], ours[p * 3 + 1], ours[p * 3 + 2]);
    sr += lr; so += lo; sabs += Math.abs(lo - lr); cnt++;
    rel.push(Math.abs(lo - lr) / Math.max(lr, 0.01));
  }
  rel.sort((a, b) => a - b);
  const r4 = (x: number) => Math.round(x * 1e4) / 1e4;
  const res = { pixels: cnt, meanRef: r4(sr / cnt), meanOurs: r4(so / cnt), bias: r4((so - sr) / sr), meanAbsRel: r4(sabs / sr),
    medianRel: r4(rel[Math.floor(rel.length * 0.5)]), p90Rel: r4(rel[Math.floor(rel.length * 0.9)]) };
  results[basename(file)] = res;
  console.log(basename(file), JSON.stringify(res));
  const pngDir = arg('--png', '');
  if (pngDir) {
    const img = new Uint8Array(ref.w * 2 * ref.h * 4);
    const k = Number(arg('--exposure', '1')) * 0.8 / Math.PI;
    for (let y = 0; y < ref.h; y++) for (let x = 0; x < ref.w; x++) {
      const p = y * ref.w + x;
      for (let c = 0; c < 3; c++) {
        img[(y * ref.w * 2 + x) * 4 + c] = tonemap(ref.rgb[p * 3 + c] * k);
        img[(y * ref.w * 2 + ref.w + x) * 4 + c] = ok[p] ? tonemap(ours[p * 3 + c] * k) : 255 * (c === 0 ? 1 : 0);
      }
      img[(y * ref.w * 2 + x) * 4 + 3] = 255; img[(y * ref.w * 2 + ref.w + x) * 4 + 3] = 255;
    }
    writeFileSync(join(pngDir, basename(file).replace('.static.irr.f32', '.vs-ref.png')), writePng(ref.w * 2, ref.h, img));
  }
}
const jsonOut = arg('--json', '');
if (jsonOut) writeFileSync(jsonOut, JSON.stringify({ kind: 'exploratory (探索値)', reference: arg('--ref', '').split(','), referenceHalvesMeanAbsRel: refNoise, results }, null, 2));
