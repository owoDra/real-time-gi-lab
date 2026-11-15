// Phase 32 (D7): the moving-camera irradiance of two runs of the same path (--dump-moving), compared on 8 x 8 pixel blocks.
// Usage: node build/native/compare_blocks.mjs --a DIR (reference: a pool large enough) --b DIR [--block 8]
// For every frame dumped in both (mov.<k>.irr.f32) and every block whose pixels are all valid photoreal pixels in both
// runs, the ratio of the block's mean luminance b / a. Blocks darker than 1e-3 in both count as equal. Prints the share of
// blocks with a ratio in [0.8, 1.25], per frame and over all frames.
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const args = process.argv.slice(2);
const arg = (name: string, d?: string) => { const i = args.indexOf(name); if (i < 0) { if (d !== undefined) return d; throw new Error(`missing ${name}`); } return args[i + 1]; };
const [a, b, B] = [arg('--a'), arg('--b'), Number(arg('--block', '8'))];
const W = 1920, H = 1080;
const load = (f: string) => { const buf = readFileSync(f); return new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4); };
const lum = (v: Float32Array, p: number) => 0.2126 * v[p * 4] + 0.7152 * v[p * 4 + 1] + 0.0722 * v[p * 4 + 2];
let inside = 0, total = 0;
const frames: { k: string; blocks: number; inRangePct: number; p05: number; p95: number }[] = [];
for (const f of readdirSync(a).filter((n) => /^mov\.\d+\.irr\.f32$/.test(n)).sort()) {
  if (!existsSync(join(b, f))) continue;
  const A = load(join(a, f)), Bv = load(join(b, f));
  const ratios: number[] = [];
  for (let by = 0; by + B <= H; by += B)
    for (let bx = 0; bx + B <= W; bx += B) {
      let sa = 0, sb = 0, ok = true;
      for (let y = by; y < by + B && ok; y++)
        for (let x = bx; x < bx + B; x++) {
          const p = y * W + x;
          if (A[p * 4 + 3] !== 1 || Bv[p * 4 + 3] !== 1) { ok = false; break; }
          sa += lum(A, p); sb += lum(Bv, p);
        }
      if (!ok) continue;
      const n = B * B;
      ratios.push(sa / n < 1e-3 && sb / n < 1e-3 ? 1 : sb / Math.max(sa, 1e-9));
    }
  const k = ratios.filter((r) => r >= 0.8 && r <= 1.25).length;
  inside += k; total += ratios.length;
  ratios.sort((x, y) => x - y);
  const q = (t: number) => ratios.length ? Math.round(ratios[Math.floor((ratios.length - 1) * t)] * 1e3) / 1e3 : NaN;
  frames.push({ k: f.slice(4, 7), blocks: ratios.length, inRangePct: ratios.length ? Math.round(k / ratios.length * 1e4) / 100 : 100, p05: q(0.05), p95: q(0.95) });
}
console.log(JSON.stringify({ a, b, block: B, frames, blocks: total, inRangePct: total ? Math.round(inside / total * 1e4) / 100 : null,
  worstFramePct: Math.min(...frames.map((x) => x.inRangePct)) }));
