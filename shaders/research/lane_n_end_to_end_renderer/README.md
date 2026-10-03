# Lane N renderer shaders

N001 shader ownership is intentionally narrow:

- accepted Lane A/B/E shaders are exact snapshots under `imported/`;
- `n001_physical_radiance.comp.glsl` replaces only Integration #13's synthetic hash radiance with one-bounce Lambertian probe-hit radiance;
- `n001_primary.comp.glsl` produces full-resolution primary visibility for HDR alignment;
- `n001_composite.comp.glsl` resolves direct lighting plus sparse stored probe radiance into linear HDR pixels.

N001 does not add temporal reuse, leak mitigation, denoising, glossy/specular transport, or realtime multi-bounce transport.
