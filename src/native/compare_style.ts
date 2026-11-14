// S3: is the photoreal part still right next to toon objects? Compares, on photoreal pixels, our static irradiance with
// the Mitsuba reference twice: the scene without the objects (base) and the scene with them (style; for toon objects
// the reference is the emission-side proxy). The comparison is reported over all photoreal pixels and over the
// region the objects affect: 8x8-pixel blocks (reference resolution) where the two references differ by more than
// 10% of the base. There it also reports how much of the objects' effect (reference style - base) ours reproduces.
// Usage: node build/native/compare_style.mjs --ref-base A.pfm,B.pfm --ref-style C.pfm,D.pfm --ours-base base.irr.f32
//          --ours-style x.irr.f32[,y...] [--json FILE] [--png DIR]
import { writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import { lum } from '../core/rcrun.ts';
import { writePng } from './env.ts';
import { readDump, readPfmMean } from './pfm.ts';

const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const W = 1920, H = 1080, B = 8;
const refB = readPfmMean(arg('--ref-base', '').split(',')), refS = readPfmMean(arg('--ref-style', '').split(','));
const { w, h } = refB;
const oursB = readDump(arg('--ours-base', ''), W, H, w, h);
const L = (rgb: Float32Array, p: number) => lum(rgb[p * 3], rgb[p * 3 + 1], rgb[p * 3 + 2]);
const r4 = (x: number) => Math.round(x * 1e4) / 1e4;

function errors(ours: Float32Array, ref: Float32Array, pix: number[]) {
  let so = 0, sr = 0, sa = 0;
  for (const p of pix) { const o = L(ours, p), r = L(ref, p); so += o; sr += r; sa += Math.abs(o - r); }
  return { pixels: pix.length, meanRef: r4(sr / pix.length), meanOurs: r4(so / pix.length), bias: r4((so - sr) / sr), meanAbsRel: r4(sa / sr) };
}
// Per-block means (luminance and rgb) over a pixel mask.
function blocks(rgb: Float32Array, mask: Uint8Array) {
  const bw = Math.floor(w / B), bh = Math.floor(h / B), m = new Float32Array(bw * bh * 4);
  for (let by = 0; by < bh; by++) for (let bx = 0; bx < bw; bx++) {
    let n = 0; const s = [0, 0, 0];
    for (let y = by * B; y < by * B + B; y++) for (let x = bx * B; x < bx * B + B; x++) {
      const p = y * w + x; if (!mask[p]) continue; n++; for (let c = 0; c < 3; c++) s[c] += rgb[p * 3 + c];
    }
    const b = by * bw + bx;
    for (let c = 0; c < 3; c++) m[b * 4 + c] = n ? s[c] / n : 0;
    m[b * 4 + 3] = n;
  }
  return { bw, bh, m };
}

const results: Record<string, unknown> = {};
for (const file of arg('--ours-style', '').split(',')) {
  const oursS = readDump(file, W, H, w, h);
  const mask = new Uint8Array(w * h);
  for (let p = 0; p < w * h; p++) mask[p] = oursB.photo[p] && oursS.photo[p] ? 1 : 0;
  const bRB = blocks(refB.rgb, mask), bRS = blocks(refS.rgb, mask), bOB = blocks(oursB.rgb, mask), bOS = blocks(oursS.rgb, mask);
  const { bw, bh } = bRB;
  const affected = new Uint8Array(bw * bh);
  let eRef = 0, eOurs = 0, eAbs = 0, nb = 0;
  const chroma = { ref: [0, 0, 0], ours: [0, 0, 0] };
  for (let b = 0; b < bw * bh; b++) {
    if (bRB.m[b * 4 + 3] < B * B / 2) continue;
    const lb = lum(bRB.m[b * 4], bRB.m[b * 4 + 1], bRB.m[b * 4 + 2]), ls = lum(bRS.m[b * 4], bRS.m[b * 4 + 1], bRS.m[b * 4 + 2]);
    if (Math.abs(ls - lb) <= 0.1 * Math.max(lb, 1e-3)) continue;
    affected[b] = 1; nb++;
    const ob = lum(bOB.m[b * 4], bOB.m[b * 4 + 1], bOB.m[b * 4 + 2]), os = lum(bOS.m[b * 4], bOS.m[b * 4 + 1], bOS.m[b * 4 + 2]);
    eRef += ls - lb; eOurs += os - ob; eAbs += Math.abs((os - ob) - (ls - lb));
    for (let c = 0; c < 3; c++) { chroma.ref[c] += bRS.m[b * 4 + c] - bRB.m[b * 4 + c]; chroma.ours[c] += bOS.m[b * 4 + c] - bOB.m[b * 4 + c]; }
  }
  const all: number[] = [], inA: number[] = [];
  for (let p = 0; p < w * h; p++) {
    if (!mask[p]) continue;
    all.push(p);
    const bx = Math.floor((p % w) / B), by = Math.floor(p / w / B);
    if (bx < bw && by < bh && affected[by * bw + bx]) inA.push(p);
  }
  const res = {
    allPhotoreal: { base: errors(oursB.rgb, refB.rgb, all), style: errors(oursS.rgb, refS.rgb, all) },
    affected: { blocks: nb, base: errors(oursB.rgb, refB.rgb, inA), style: errors(oursS.rgb, refS.rgb, inA),
      // The objects' effect on these blocks (style - base, mean luminance), ours against the reference.
      effect: { ref: r4(eRef / nb), ours: r4(eOurs / nb), captured: r4(eOurs / eRef), meanAbsErrorOverMeanAbsRef: r4(eAbs / nb / (Math.abs(eRef) / nb)) },
      effectRgb: { ref: chroma.ref.map((x) => r4(x / nb)), ours: chroma.ours.map((x) => r4(x / nb)) } },
  };
  results[basename(file)] = res;
  console.log(basename(file), JSON.stringify(res));
  const pngDir = arg('--png', '');
  if (pngDir) {
    // Effect images (style - base), reference | ours, signed: red more light, blue less; affected blocks outlined grey.
    const img = new Uint8Array(w * 2 * h * 4), k = 4;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const p = y * w + x;
      for (const [side, a, b2] of [[0, refS.rgb, refB.rgb], [1, oursS.rgb, oursB.rgb]] as const) {
        const o = (y * w * 2 + side * w + x) * 4;
        const d = mask[p] ? (L(a, p) - L(b2, p)) / Math.max(0.02, L(refB.rgb, p)) : 0;
        const v = Math.min(255, Math.round(Math.abs(d) * k * 255));
        img.set(mask[p] ? (d > 0 ? [v, 0, 0, 255] : [0, 0, v, 255]) : [40, 40, 40, 255], o);
        const bx = Math.floor(x / B), by = Math.floor(y / B);
        if (bx < bw && by < bh && affected[by * bw + bx] && (x % B === 0 || y % B === 0)) img.set([90, 90, 90, 255], o);
      }
    }
    writeFileSync(join(pngDir, basename(file).replace('.static.irr.f32', '.effect.png')), writePng(w * 2, h, img));
  }
}
const jsonOut = arg('--json', '');
if (jsonOut) writeFileSync(jsonOut, JSON.stringify({ kind: 'exploratory (探索値)', refBase: arg('--ref-base', '').split(','), refStyle: arg('--ref-style', '').split(','),
  oursBase: arg('--ours-base', ''), blockPx: B, affectedThreshold: 0.1, results }, null, 2));
