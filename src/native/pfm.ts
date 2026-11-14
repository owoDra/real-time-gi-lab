// PFM reading (Mitsuba references) and our --dump-irr files reduced to the reference resolution.
import { readFileSync } from 'node:fs';

export function readPfm(file: string) {
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

/** Mean of several PFMs (independent seeds). */
export function readPfmMean(files: string[]) {
  const all = files.map(readPfm), r = all[0];
  return { w: r.w, h: r.h, rgb: r.rgb.map((_, i) => all.reduce((s, x) => s + x.rgb[i], 0) / all.length) };
}

/** A --dump-irr file box-filtered to w x h. photo: every source pixel photoreal (tag 1). */
export function readDump(file: string, W: number, H: number, w: number, h: number) {
  const raw = readFileSync(file), f = new Float32Array(raw.buffer, raw.byteOffset, raw.byteLength / 4);
  const fx = W / w, fy = H / h;
  if (!Number.isInteger(fx) || fx !== fy) throw new Error('resolution must be an integer multiple of the reference');
  const rgb = new Float32Array(w * h * 3), photo = new Uint8Array(w * h);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    let n = 0; const s = [0, 0, 0];
    for (let j = 0; j < fy; j++) for (let i = 0; i < fx; i++) {
      const p = (y * fy + j) * W + x * fx + i;
      if (f[p * 4 + 3] > 0.5 && f[p * 4 + 3] < 1.5) { n++; for (let c = 0; c < 3; c++) s[c] += f[p * 4 + c]; }
    }
    if (n === fx * fy) { photo[y * w + x] = 1; for (let c = 0; c < 3; c++) rgb[(y * w + x) * 3 + c] = s[c] / n; }
  }
  return { rgb, photo };
}
