// Compares the renderer's static indirect irradiance (--dump-irr) with the Mitsuba reference
// (scripts/reference_irradiance.py). Ours is box-filtered down to the reference resolution. Only photoreal pixels are
// compared (a reference pixel is used when every one of our pixels in it is photoreal: tag 1).
// Usage: node build/native/compare_ref.mjs --ref E.pfm[,E2.pfm...] --ours a.static.irr.f32[,b...] [--width 1920 --height 1080]
//   [--png DIR]  (side-by-side images: reference | ours, same exposure) [--json FILE]
//   [--objects]  (scenes with flagged photoreal objects: also their pixels on their own)
// Block errors (W3, phase 25): the same mean |ours - ref| / mean ref over means of B x B reference pixels (B = 8, 16;
// a block counts when at least 3/4 of its pixels are compared). Averaging B^2 pixels divides the reference's own
// noise by about B, so two independent references agree within a few percent where single pixels differ by 20-30%.
import { readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { lum } from '../core/rcrun.ts';
import { writePng } from './env.ts';
import { readPfm } from './pfm.ts';

const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const W = Number(arg('--width', '1920')), H = Number(arg('--height', '1080'));


// Several reference files (independent seeds) are averaged; the difference between the first two shows the
// reference's own noise (the average's error is about half of it).
const refs = arg('--ref', '').split(',').map(readPfm);
const ref = refs[0];
const halfA = refs[0].rgb.slice(), halfB = refs.length > 1 ? refs[1].rgb : null;
const BLOCKS = [8, 16];
/** Mean |a - b| / mean b over B x B block means of luminance (pixels where ok is set). */
function blockErr(a: Float32Array, b: Float32Array, ok: Uint8Array | null, w: number, h: number, B: number) {
  let sd = 0, sb = 0, sa = 0;
  for (let by = 0; by + B <= h; by += B) for (let bx = 0; bx + B <= w; bx += B) {
    let n = 0, la = 0, lb = 0;
    for (let y = by; y < by + B; y++) for (let x = bx; x < bx + B; x++) {
      const p = y * w + x;
      if (ok && !ok[p]) continue;
      n++; la += lum(a[p * 3], a[p * 3 + 1], a[p * 3 + 2]); lb += lum(b[p * 3], b[p * 3 + 1], b[p * 3 + 2]);
    }
    if (n * 4 < B * B * 3) continue;
    sd += Math.abs(la - lb) / n; sb += lb / n; sa += la / n;
  }
  return { meanAbsRel: Math.round(sd / sb * 1e4) / 1e4, bias: Math.round((sa - sb) / sb * 1e4) / 1e4 };
}
let refNoiseBlocks: Record<string, number> | null = null;
let refNoise: number | null = null;
if (refs.length > 1) {
  let sd = 0, ss = 0;
  for (let p = 0; p < ref.w * ref.h; p++) {
    const a = lum(refs[0].rgb[p * 3], refs[0].rgb[p * 3 + 1], refs[0].rgb[p * 3 + 2]), b = lum(refs[1].rgb[p * 3], refs[1].rgb[p * 3 + 1], refs[1].rgb[p * 3 + 2]);
    sd += Math.abs(a - b); ss += (a + b) / 2;
  }
  refNoise = Math.round(sd / ss * 1e4) / 1e4;
  refNoiseBlocks = Object.fromEntries(BLOCKS.map((B) => [`b${B}`, blockErr(refs[0].rgb, refs[1].rgb, null, ref.w, ref.h, B).meanAbsRel]));
  console.log(`reference halves, block means: ${JSON.stringify(refNoiseBlocks)}`);
  ref.rgb = ref.rgb.map((_, i) => refs.reduce((s, r) => s + r.rgb[i], 0) / refs.length);
  console.log(`reference: ${refs.length} renders averaged; mean |half A - half B| / mean = ${refNoise}`);
}
/** The reference's own noise over a mask: mean |half A - half B| / mean, per pixel and on 8 x 8 block means. */
function halves(mask: Uint8Array) {
  let sd = 0, ss = 0;
  for (let p = 0; p < mask.length; p++) {
    if (!mask[p]) continue;
    const a = lum(halfA[p * 3], halfA[p * 3 + 1], halfA[p * 3 + 2]), b = lum(halfB![p * 3], halfB![p * 3 + 1], halfB![p * 3 + 2]);
    sd += Math.abs(a - b); ss += (a + b) / 2;
  }
  return { pixel: Math.round(sd / ss * 1e4) / 1e4, b8: blockErr(halfA, halfB!, mask, ref.w, ref.h, 8).meanAbsRel };
}
const fx = W / ref.w, fy = H / ref.h;
if (!Number.isInteger(fx) || fx !== fy) throw new Error('resolution must be an integer multiple of the reference');
const tonemap = (v: number) => Math.round(255 * Math.min(1, Math.pow(Math.max(v, 0) / (1 + Math.max(v, 0)), 1 / 2.2)));
const results: Record<string, unknown> = {};
for (const file of arg('--ours', '').split(',')) {
  const raw = readFileSync(file), f = new Float32Array(raw.buffer, raw.byteOffset, raw.byteLength / 4);
  // ok: every pixel photoreal (compared); obj: every pixel a flagged photoreal object (tag 2; compared with --objects);
  // shown: every pixel valid (toon pixels are drawn but not compared).
  const ours = new Float32Array(ref.w * ref.h * 3), ok = new Uint8Array(ref.w * ref.h), obj = new Uint8Array(ref.w * ref.h), shown = new Uint8Array(ref.w * ref.h);
  for (let y = 0; y < ref.h; y++) for (let x = 0; x < ref.w; x++) {
    let n = 0, photo = 0, object = 0; const s = [0, 0, 0];
    for (let j = 0; j < fy; j++) for (let i = 0; i < fx; i++) {
      const p = (y * fy + j) * W + x * fx + i, t = f[p * 4 + 3];
      if (t > 0.5) { n++; if (t < 1.5) photo++; else if (t < 2.5) object++; for (let c = 0; c < 3; c++) s[c] += f[p * 4 + c]; }
    }
    if (n === fx * fy) { const q = y * ref.w + x; shown[q] = 1; ok[q] = photo === n ? 1 : 0; obj[q] = object === n ? 1 : 0; for (let c = 0; c < 3; c++) ours[q * 3 + c] = s[c] / n; }
  }
  const r4 = (x: number) => Math.round(x * 1e4) / 1e4;
  const compare = (mask: Uint8Array) => {
    let sr = 0, so = 0, sabs = 0, cnt = 0;
    const rel: number[] = [];
    for (let p = 0; p < mask.length; p++) {
      if (!mask[p]) continue;
      const lr = lum(ref.rgb[p * 3], ref.rgb[p * 3 + 1], ref.rgb[p * 3 + 2]), lo = lum(ours[p * 3], ours[p * 3 + 1], ours[p * 3 + 2]);
      sr += lr; so += lo; sabs += Math.abs(lo - lr); cnt++;
      rel.push(Math.abs(lo - lr) / Math.max(lr, 0.01));
    }
    rel.sort((a, b) => a - b);
    return { pixels: cnt, meanRef: r4(sr / cnt), meanOurs: r4(so / cnt), bias: r4((so - sr) / sr), meanAbsRel: r4(sabs / sr),
      medianRel: r4(rel[Math.floor(rel.length * 0.5)]), p90Rel: r4(rel[Math.floor(rel.length * 0.9)]),
      blocks: Object.fromEntries(BLOCKS.map((B) => [`b${B}`, blockErr(ours, ref.rgb, mask, ref.w, ref.h, B)])) };
  };
  // --objects (phase 27): the pixels of the flagged photoreal objects (the moving objects of the -dynobj scenes), which
  // the main comparison leaves out, compared on their own. Not for toon scenes (a toon pixel's irradiance went through
  // the receiving-side operator and its tag can be 2 as well).
  const res = { ...compare(ok), ...(args.includes('--objects') ? { objects: { ...compare(obj),
    refHalvesMeanAbsRel: refs.length > 1 ? halves(obj) : null } } : {}) };
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
        img[(y * ref.w * 2 + ref.w + x) * 4 + c] = shown[p] ? tonemap(ours[p * 3 + c] * k) : 255 * (c === 0 ? 1 : 0);
      }
      img[(y * ref.w * 2 + x) * 4 + 3] = 255; img[(y * ref.w * 2 + ref.w + x) * 4 + 3] = 255;
    }
    writeFileSync(join(pngDir, basename(file).replace('.static.irr.f32', '.vs-ref.png')), writePng(ref.w * 2, ref.h, img));
  }
}
const jsonOut = arg('--json', '');
if (jsonOut) writeFileSync(jsonOut, JSON.stringify({ kind: 'exploratory (探索値)', reference: arg('--ref', '').split(','), referenceHalvesMeanAbsRel: refNoise, referenceHalvesBlocks: refNoiseBlocks, results }, null, 2));
