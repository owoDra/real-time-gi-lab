// Exports a scene from our SceneData (the same parse the renderer uses) for the Mitsuba 3 reference:
// one binary PLY per material (positions, normals, uv), opacity images for alpha-masked materials, and
// scene.json (materials, camera, sun, sky, toon ramp). See scripts/reference_irradiance.py.
// Toon materials (S3) are flagged per vertex (toon = 1): the reference shades them as emitters of the emission-side
// operator (the emission-side proxy).
// Usage: node build/native/mitsuba_export.mjs [--scene sponza|sponza-toon|sponza-objects|leak-<t>] [--out DIR]
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { PNG } from 'pngjs';
import { parseGltf } from '../core/gltf.ts';
import { SUN_E } from '../core/rcrun.ts';
import { leakRoom, sponzaSpec, toonSponza, type SceneSpec } from '../core/scenes.ts';
import { TOON } from '../core/style.ts';
import { ROOT } from './env.ts';

const args = process.argv.slice(2);
const arg = (name: string, dflt: string) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const sceneName = arg('--scene', 'sponza');
const outDir = resolve(arg('--out', join(ROOT, 'out/mitsuba', sceneName)));
mkdirSync(join(outDir, 'meshes'), { recursive: true });
mkdirSync(join(outDir, 'textures'), { recursive: true });

let spec: SceneSpec, imageDir = '';
let images: string[] = [];
if (sceneName.startsWith('leak-')) spec = leakRoom(Number(sceneName.slice(5)));
else {
  imageDir = join(ROOT, 'assets/glTF-Sample-Assets/Models/Sponza/glTF');
  const json = JSON.parse(readFileSync(join(imageDir, 'Sponza.gltf'), 'utf8'));
  const binFile = readFileSync(join(imageDir, json.buffers[0].uri));
  const base = parseGltf(json, binFile.buffer.slice(binFile.byteOffset, binFile.byteOffset + binFile.byteLength));
  spec = sceneName === 'sponza' ? sponzaSpec(base) : sceneName === 'sponza-toon' ? toonSponza(base)
    : sceneName === 'sponza-objects' ? toonSponza(base, true) : (() => { throw new Error(`unknown scene ${sceneName}`); })();
  images = json.images.map((i: any) => i.uri as string);
}
const s = spec.scene;

// Triangles per material, re-indexed.
const perMat = new Map<number, number[]>();
for (const p of s.primitives) {
  const list = perMat.get(p.material) ?? [];
  for (let i = p.firstIndex; i < p.firstIndex + p.indexCount; i++) list.push(s.indices[i] + p.baseVertex);
  perMat.set(p.material, list);
}
const materials: any[] = [];
for (const [m, idx] of perMat) {
  const remap = new Map<number, number>(), verts: number[] = [];
  const faces = idx.map((v) => { let r = remap.get(v); if (r === undefined) { r = verts.length; remap.set(v, r); verts.push(v); } return r; });
  const header = `ply\nformat binary_little_endian 1.0\nelement vertex ${verts.length}\nproperty float x\nproperty float y\nproperty float z\n`
    + `property float nx\nproperty float ny\nproperty float nz\nproperty float u\nproperty float v\nproperty float ds_x\nproperty float toon_x\nproperty float tex_x\nelement face ${faces.length / 3}\n`
    + `property list uchar int vertex_indices\nend_header\n`;
  const md = s.materials[m];
  // ds: 1 for double-sided materials. The G-buffer culls back faces of single-sided ones (primary rays only).
  const vb = Buffer.alloc(verts.length * 44), fb = Buffer.alloc(faces.length / 3 * 13);
  verts.forEach((v, i) => {
    for (let a = 0; a < 3; a++) vb.writeFloatLE(s.positions[v * 3 + a], i * 44 + a * 4);
    for (let a = 0; a < 3; a++) vb.writeFloatLE(s.normals[v * 3 + a], i * 44 + 12 + a * 4);
    // glTF puts v = 0 at the top of the image; Mitsuba at the bottom.
    vb.writeFloatLE(s.uvs[v * 2], i * 44 + 24); vb.writeFloatLE(1 - s.uvs[v * 2 + 1], i * 44 + 28);
    vb.writeFloatLE(md.doubleSided ? 1 : 0, i * 44 + 32);
    vb.writeFloatLE(md.style === 1 ? 1 : 0, i * 44 + 36);
    vb.writeFloatLE(md.baseColorImage >= 0 ? 1 : 0, i * 44 + 40); // the reference applies the shared texture factor only here
  });
  for (let f = 0; f < faces.length / 3; f++) {
    fb.writeUInt8(3, f * 13);
    for (let a = 0; a < 3; a++) fb.writeInt32LE(faces[f * 3 + a], f * 13 + 1 + a * 4);
  }
  const mesh = `meshes/m${m}.ply`;
  writeFileSync(join(outDir, mesh), Buffer.concat([Buffer.from(header, 'ascii'), vb, fb]));
  let texture: string | null = null, opacity: string | null = null;
  if (md.baseColorImage >= 0) {
    const src = images[md.baseColorImage];
    texture = `textures/${src}`;
    copyFileSync(join(imageDir, src), join(outDir, texture));
    if (md.alphaMask) {
      const png = PNG.sync.read(readFileSync(join(imageDir, src)));
      const out = new PNG({ width: png.width, height: png.height });
      for (let i = 0; i < png.width * png.height; i++) { const a = png.data[i * 4 + 3]; out.data.set([a, a, a, 255], i * 4); }
      opacity = `textures/alpha-${src.replace(/\.[a-z]+$/, '')}.png`;
      writeFileSync(join(outDir, opacity), PNG.sync.write(out));
    }
  }
  materials.push({ mesh, triangles: faces.length / 3, texture, factor: md.baseColorFactor.slice(0, 3), opacity, cutoff: md.alphaCutoff, doubleSided: md.doubleSided, toon: md.style === 1 });
}
writeFileSync(join(outDir, 'scene.json'), JSON.stringify({
  scene: spec.name, materials, camera: spec.camera, sunDir: spec.sunDir, sunE: SUN_E, toon: TOON,
}, null, 2));
console.log(`exported ${spec.name}: ${materials.length} materials, ${s.triangleCount} triangles -> ${outDir}`);
