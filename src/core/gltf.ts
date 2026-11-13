// Minimal glTF 2.0 reader: triangles, one buffer, PBR metallic-roughness materials.
// Mesh instances are flattened into world space so later GI passes can use one vertex set.
import { identity, mul, nodeMatrix, normalMatrix, type Mat4, type Vec3 } from './math.ts';

export interface MaterialDesc {
  name: string;
  baseColorFactor: [number, number, number, number];
  baseColorImage: number; // image index, -1 if none
  normalImage: number;
  metallicRoughnessImage: number;
  metallicFactor: number;
  roughnessFactor: number;
  alphaMask: boolean;
  alphaCutoff: number;
  doubleSided: boolean;
}

export interface Primitive { firstIndex: number; indexCount: number; baseVertex: number; material: number; }

export interface SceneData {
  positions: Float32Array; // xyz
  normals: Float32Array;   // xyz
  uvs: Float32Array;       // uv
  tangents: Float32Array;  // xyzw, zero when the source has no tangents
  indices: Uint32Array;
  primitives: Primitive[];
  materials: MaterialDesc[];
  imageUris: string[];
  boundsMin: Vec3;
  boundsMax: Vec3;
  triangleCount: number;
}

const COMPONENTS: Record<string, number> = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };

function readAccessor(json: any, bin: ArrayBuffer, index: number): { data: Float32Array | Uint32Array; size: number; count: number } {
  const acc = json.accessors[index];
  const view = json.bufferViews[acc.bufferView];
  if (acc.sparse) throw new Error('sparse accessors are not supported');
  const size = COMPONENTS[acc.type];
  const count = acc.count;
  const base = (view.byteOffset ?? 0) + (acc.byteOffset ?? 0);
  const dv = new DataView(bin);
  const ct = acc.componentType;
  const compBytes = ct === 5126 || ct === 5125 ? 4 : ct === 5123 || ct === 5122 ? 2 : 1;
  const stride = view.byteStride ?? size * compBytes;
  const out = ct === 5126 ? new Float32Array(count * size) : new Uint32Array(count * size);
  for (let i = 0; i < count; i++)
    for (let c = 0; c < size; c++) {
      const o = base + i * stride + c * compBytes;
      let v: number;
      switch (ct) {
        case 5126: v = dv.getFloat32(o, true); break;
        case 5125: v = dv.getUint32(o, true); break;
        case 5123: v = dv.getUint16(o, true); break;
        case 5121: v = dv.getUint8(o); break;
        default: throw new Error(`componentType ${ct} not supported`);
      }
      if (acc.normalized && ct !== 5126) throw new Error('normalized integer attributes not supported');
      out[i * size + c] = v;
    }
  return { data: out, size, count };
}

export function parseGltf(json: any, bin: ArrayBuffer): SceneData {
  const texImage = (t?: { index: number; texCoord?: number }) => {
    if (!t) return -1;
    if ((t.texCoord ?? 0) !== 0) throw new Error('only TEXCOORD_0 is supported');
    return json.textures[t.index].source as number;
  };
  const materials: MaterialDesc[] = (json.materials ?? []).map((m: any) => {
    const pbr = m.pbrMetallicRoughness ?? {};
    return {
      name: m.name ?? '',
      baseColorFactor: pbr.baseColorFactor ?? [1, 1, 1, 1],
      baseColorImage: texImage(pbr.baseColorTexture),
      normalImage: texImage(m.normalTexture),
      metallicRoughnessImage: texImage(pbr.metallicRoughnessTexture),
      metallicFactor: pbr.metallicFactor ?? 1,
      roughnessFactor: pbr.roughnessFactor ?? 1,
      alphaMask: m.alphaMode === 'MASK',
      alphaCutoff: m.alphaCutoff ?? 0.5,
      doubleSided: !!m.doubleSided,
    } satisfies MaterialDesc;
  });
  if (materials.length === 0 || json.meshes.some((me: any) => me.primitives.some((p: any) => p.material === undefined)))
    materials.push({ name: 'default', baseColorFactor: [1, 1, 1, 1], baseColorImage: -1, normalImage: -1, metallicRoughnessImage: -1,
      metallicFactor: 0, roughnessFactor: 1, alphaMask: false, alphaCutoff: 0.5, doubleSided: false });
  const defaultMaterial = materials.length - 1;

  const pos: number[] = [], nrm: number[] = [], uv: number[] = [], tan: number[] = [], idx: number[] = [];
  const primitives: Primitive[] = [];
  const bmin: Vec3 = [Infinity, Infinity, Infinity], bmax: Vec3 = [-Infinity, -Infinity, -Infinity];

  const visit = (nodeIndex: number, parent: Mat4) => {
    const node = json.nodes[nodeIndex];
    const world = mul(parent, nodeMatrix(node));
    if (node.mesh !== undefined) {
      const nm = normalMatrix(world);
      for (const p of json.meshes[node.mesh].primitives) {
        if ((p.mode ?? 4) !== 4) throw new Error('only triangle lists are supported');
        const P = readAccessor(json, bin, p.attributes.POSITION);
        const N = p.attributes.NORMAL !== undefined ? readAccessor(json, bin, p.attributes.NORMAL) : null;
        const T = p.attributes.TEXCOORD_0 !== undefined ? readAccessor(json, bin, p.attributes.TEXCOORD_0) : null;
        const G = p.attributes.TANGENT !== undefined ? readAccessor(json, bin, p.attributes.TANGENT) : null;
        if (!N) throw new Error('primitives without normals are not supported');
        const baseVertex = pos.length / 3;
        for (let i = 0; i < P.count; i++) {
          const x = P.data[i * 3], y = P.data[i * 3 + 1], z = P.data[i * 3 + 2];
          const wx = world[0] * x + world[4] * y + world[8] * z + world[12];
          const wy = world[1] * x + world[5] * y + world[9] * z + world[13];
          const wz = world[2] * x + world[6] * y + world[10] * z + world[14];
          pos.push(wx, wy, wz);
          bmin[0] = Math.min(bmin[0], wx); bmin[1] = Math.min(bmin[1], wy); bmin[2] = Math.min(bmin[2], wz);
          bmax[0] = Math.max(bmax[0], wx); bmax[1] = Math.max(bmax[1], wy); bmax[2] = Math.max(bmax[2], wz);
          const a = N.data[i * 3], b = N.data[i * 3 + 1], c = N.data[i * 3 + 2];
          const n0 = nm[0] * a + nm[3] * b + nm[6] * c, n1 = nm[1] * a + nm[4] * b + nm[7] * c, n2 = nm[2] * a + nm[5] * b + nm[8] * c;
          const nl = Math.hypot(n0, n1, n2) || 1;
          nrm.push(n0 / nl, n1 / nl, n2 / nl);
          uv.push(T ? T.data[i * 2] : 0, T ? T.data[i * 2 + 1] : 0);
          if (G) {
            const tx = G.data[i * 4], ty = G.data[i * 4 + 1], tz = G.data[i * 4 + 2];
            const t0 = world[0] * tx + world[4] * ty + world[8] * tz;
            const t1 = world[1] * tx + world[5] * ty + world[9] * tz;
            const t2 = world[2] * tx + world[6] * ty + world[10] * tz;
            const tl = Math.hypot(t0, t1, t2) || 1;
            tan.push(t0 / tl, t1 / tl, t2 / tl, G.data[i * 4 + 3]);
          } else tan.push(0, 0, 0, 0);
        }
        const firstIndex = idx.length;
        if (p.indices !== undefined) { const I = readAccessor(json, bin, p.indices); for (const v of I.data) idx.push(v); }
        else for (let i = 0; i < P.count; i++) idx.push(i);
        primitives.push({ firstIndex, indexCount: idx.length - firstIndex, baseVertex, material: p.material ?? defaultMaterial });
      }
    }
    for (const c of node.children ?? []) visit(c, world);
  };
  for (const n of json.scenes[json.scene ?? 0].nodes) visit(n, identity());

  return {
    positions: new Float32Array(pos), normals: new Float32Array(nrm), uvs: new Float32Array(uv), tangents: new Float32Array(tan),
    indices: new Uint32Array(idx), primitives, materials, imageUris: json.images.map((i: any) => i.uri as string),
    boundsMin: bmin, boundsMax: bmax, triangleCount: idx.length / 3,
  };
}
