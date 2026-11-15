// Decoded images -> the texture arrays' size (TEXTURE_SIZE). Shared by the native and the browser loaders so that both
// upload the same texels.
import { TEXTURE_SIZE } from '../core/scene_gpu.ts';

/** Nearest-neighbour resize to TEXTURE_SIZE; only used for the odd 4x4 placeholder image. */
export function toTextureSize(img: { width: number; height: number; data: Uint8Array }) {
  if (img.width === TEXTURE_SIZE && img.height === TEXTURE_SIZE) return img.data;
  const out = new Uint8Array(TEXTURE_SIZE * TEXTURE_SIZE * 4);
  for (let y = 0; y < TEXTURE_SIZE; y++)
    for (let x = 0; x < TEXTURE_SIZE; x++) {
      const sx = Math.floor(x * img.width / TEXTURE_SIZE), sy = Math.floor(y * img.height / TEXTURE_SIZE);
      out.set(img.data.subarray((sy * img.width + sx) * 4, (sy * img.width + sx) * 4 + 4), (y * TEXTURE_SIZE + x) * 4);
    }
  return out;
}
