// Minimal PNG decoder for the browser runner (8-bit RGB / RGBA, not interlaced: the formats Sponza uses). Decoding in
// script, not with createImageBitmap or a canvas, keeps the texels exactly those of the native loader (pngjs): no colour
// management and no premultiplied alpha.
export async function decodePng(buf: ArrayBuffer): Promise<{ width: number; height: number; data: Uint8Array }> {
  const b = new Uint8Array(buf), dv = new DataView(buf);
  let off = 8, width = 0, height = 0, channels = 0;
  const idat: Uint8Array[] = [];
  while (off < b.length) {
    const len = dv.getUint32(off), type = String.fromCharCode(...b.subarray(off + 4, off + 8));
    const data = b.subarray(off + 8, off + 8 + len);
    if (type === 'IHDR') {
      width = dv.getUint32(off + 8); height = dv.getUint32(off + 12);
      const depth = data[8], ctype = data[9], interlace = data[12];
      if (depth !== 8 || interlace !== 0 || (ctype !== 2 && ctype !== 6)) throw new Error(`unsupported PNG (depth ${depth}, type ${ctype}, interlace ${interlace})`);
      channels = ctype === 6 ? 4 : 3;
    } else if (type === 'IDAT') idat.push(data);
    else if (type === 'IEND') break;
    off += 12 + len;
  }
  const raw = new Uint8Array(await new Response(new Blob(idat as BlobPart[]).stream().pipeThrough(new DecompressionStream('deflate'))).arrayBuffer());
  const stride = width * channels, px = new Uint8Array(stride * height), out = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y++) {
    const f = raw[y * (stride + 1)], src = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1)), row = y * stride;
    for (let x = 0; x < stride; x++) {
      const a = x >= channels ? px[row + x - channels] : 0, up = y > 0 ? px[row - stride + x] : 0, c = x >= channels && y > 0 ? px[row - stride + x - channels] : 0;
      let v = src[x];
      if (f === 1) v += a;
      else if (f === 2) v += up;
      else if (f === 3) v += (a + up) >> 1;
      else if (f === 4) { const p = a + up - c, pa = Math.abs(p - a), pb = Math.abs(p - up), pc = Math.abs(p - c); v += pa <= pb && pa <= pc ? a : pb <= pc ? up : c; }
      else if (f !== 0) throw new Error(`bad PNG filter ${f}`);
      px[row + x] = v & 255;
    }
  }
  for (let p = 0; p < width * height; p++) {
    out[p * 4] = px[p * channels]; out[p * 4 + 1] = px[p * channels + 1]; out[p * 4 + 2] = px[p * channels + 2];
    out[p * 4 + 3] = channels === 4 ? px[p * channels + 3] : 255;
  }
  return { width, height, data: out };
}
