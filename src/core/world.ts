// Phase 32: worlds. The static part of a scene (the building: triangles [0, staticTriangles), vertices [0, staticVertices))
// is placed at one or several offsets (instances; instance 0 at the origin holds the camera and the dynamic objects).
// Every scene whose building does not cut is a world (runner/scene.ts); a wide world (several instances) also gets the
// instanced draws, the camera-following shadow layers and the scrolling DDGI volume. Nothing is duplicated on the GPU:
// the rasterisers draw the visible instances, and the voxel build (voxel.ts) reads a per-frame list of work items
// (instance, chunk, level), so that its cost follows what lies inside the camera's clipmap windows, not the size of the
// world.
//
// Chunks: the static triangles grouped by centroid into CHUNK m cells (CPU, once). Items are culled per chunk against
// the windows.
// Voxelised geometry (LOD): a chunk whose finest window is level s is voxelised from a vertex-clustered copy of its
// triangles (cells aligned with the voxel grid: lod0Cell at level 0, v0 * 2^(s-1) = half a voxel at level s >= 1):
// every vertex moves to the mean of its cell's vertices (same material), duplicate triangles are dropped, triangles that
// collapse to a segment or a point are kept (they are still voxelised conservatively, so thin parts do not vanish). A
// triangle inside one cell is inside one voxel, so it marks the same voxel as before; the voxel build's cost then
// follows the surface inside the windows rather than the triangle count (sponza-dense10). The clustered vertices are
// appended to the scene's vertex arrays (not drawn) and moved by the building motion like the others (building.ts).
import type { SceneData } from './gltf.ts';
import type { Vec3 } from './math.ts';

export const CHUNK = 8;
/** Clustering cell of the level-0 copy (m), half a 0.2 m voxel; 0 = the full triangles. Tried (phase 32): 0.05 (dense
 * scenes keep 0.3 ms of the triangle cost) and a whole voxel for the coarse levels (no gain). */
export const DEFAULT_LOD0_CELL = 0.1;
/** A chunk uses the level-0 copy only when it keeps at most this share of the chunk's triangles (triangles much finer
 * than the voxels). Sponza's chunks keep 67-100 % (never clustered, images unchanged); sponza-dense10's large chunks keep
 * 18-47 %. Clustering every chunk changed the toon objects' ramp band changes 1.157 -> 1.22 % (phase 32). */
export const LOD0_KEEP = 0.5;
/** Building motion (building.ts, wave) moves vertices by at most 0.12 m; chunk boxes are grown by this. */
export const MOTION_MARGIN = 0.15;

export interface WorldChunk {
  lo: Vec3; hi: Vec3;
  /** Triangle table rows of the chunk, ascending (the full geometry). */
  full: Uint32Array;
  /** lod[s]: rows voxelised when the chunk's finest window is level s (0 .. levels - 1), ascending; lod[0] is full when
   * lod0Cell is 0. */
  lod: Uint32Array[];
}

export interface World {
  instances: Vec3[];
  staticTriangles: number;
  staticVertices: number;
  v0: number; levels: number;
  chunks: WorldChunk[];
  /** Clustered vertices appended to the scene's arrays: [lodFirstVertex, lodFirstVertex + lodVertexCount). */
  lodFirstVertex: number; lodVertexCount: number;
  /** Table rows of the clustered triangles (absolute vertex indices + material), appended after the scene's rows. */
  lodTable: Uint32Array;
  /** Bounds of the whole world (all instances, static part). */
  boundsMin: Vec3; boundsMax: Vec3;
  /** Bounds of the static part of instance 0. */
  staticMin: Vec3; staticMax: Vec3;
}

/** 0..5: the dominant axis of a normal and its sign. */
function dirKey(x: number, y: number, z: number): number {
  const ax = Math.abs(x), ay = Math.abs(y), az = Math.abs(z);
  return ax >= ay && ax >= az ? (x >= 0 ? 0 : 1) : ay >= az ? (y >= 0 ? 2 : 3) : (z >= 0 ? 4 : 5);
}

/** Builds the chunks and the clustered copies (v0, levels of the voxel world) and appends the clustered vertices. */
export function withWorld(scene: SceneData, table: Uint32Array, staticTriangles: number, staticVertices: number, instances: Vec3[],
  v0: number, levels: number, lod0Cell = 0): { scene: SceneData; world: World } {
  if (instances.length === 0 || instances[0].some((x) => x !== 0)) throw new Error('instance 0 must be at the origin');
  const P = scene.positions, N = scene.normals, UV = scene.uvs;
  const T = staticTriangles;
  // Chunks by centroid.
  const key = (c: number[]) => c.map((x) => Math.floor(x / CHUNK)).join(',');
  const byChunk = new Map<string, number[]>();
  const sMin: Vec3 = [Infinity, Infinity, Infinity], sMax: Vec3 = [-Infinity, -Infinity, -Infinity];
  for (let t = 0; t < T; t++) {
    const c = [0, 0, 0];
    for (let q = 0; q < 3; q++) {
      const v = table[t * 4 + q];
      for (let a = 0; a < 3; a++) { c[a] += P[v * 3 + a] / 3; sMin[a] = Math.min(sMin[a], P[v * 3 + a]); sMax[a] = Math.max(sMax[a], P[v * 3 + a]); }
    }
    const k = key(c);
    let l = byChunk.get(k);
    if (!l) byChunk.set(k, l = []);
    l.push(t);
  }
  const keys = [...byChunk.keys()].sort();
  // Clustered copies, per chunk and start level.
  const lodPos: number[] = [], lodNrm: number[] = [], lodUv: number[] = [], lodRows: number[] = [];
  const firstRow = table.length / 4, V0 = P.length / 3;
  // Rows of the clustered triangles, per start level, numbered after the chunks are clustered: in the order of their source
  // triangle, collapsed ones (a segment or a point) first. A voxel's representative is the overlapping triangle with the
  // largest row, so the choice is the same as with the full triangles (the two faces of a 2 cm wall share voxels: chunk
  // order put the outer face last and the leak room leaked 2 x), and a real triangle wins over a collapsed one.
  const pending: { chunk: number; t: number; collapsed: boolean; v: number[]; m: number }[][] = Array.from({ length: levels }, () => []);
  const chunks: WorldChunk[] = keys.map((k, ci) => {
    const tris = byChunk.get(k)!;
    const lo: Vec3 = [Infinity, Infinity, Infinity], hi: Vec3 = [-Infinity, -Infinity, -Infinity];
    for (const t of tris) for (let q = 0; q < 3; q++) for (let a = 0; a < 3; a++) {
      const x = P[table[t * 4 + q] * 3 + a];
      lo[a] = Math.min(lo[a], x); hi[a] = Math.max(hi[a], x);
    }
    const lod: Uint32Array[] = [];
    const full = Uint32Array.from(tris);
    for (let s = 0; s < levels; s++) {
      const cell = s === 0 ? lod0Cell : v0 * 2 ** (s - 1);
      if (cell === 0) { lod.push(full); continue; }
      const clusters = new Map<string, { id: number; sum: number[]; n: number; nrm: number[]; verts: number[] }>();
      const triCl: number[][] = [];
      for (const t of tris) {
        const m = table[t * 4 + 3];
        triCl.push([0, 1, 2].map((q) => {
          const v = table[t * 4 + q];
          // Level 0: the vertex normal's dominant axis and sign are part of the key, so that the two faces of a wall
          // thinner than the cell do not merge (leak rooms: 0.68 / 0.40 % of the sun leaked with it, 4.2 / 1.5 % without).
          const d = s === 0 ? dirKey(N[v * 3], N[v * 3 + 1], N[v * 3 + 2]) : 0;
          const ck = `${m}|${d}|${Math.floor(P[v * 3] / cell)},${Math.floor(P[v * 3 + 1] / cell)},${Math.floor(P[v * 3 + 2] / cell)}`;
          let c = clusters.get(ck);
          if (!c) clusters.set(ck, c = { id: clusters.size, sum: [0, 0, 0], n: 0, nrm: [0, 0, 0], verts: [] });
          if (!c.verts.includes(v)) {
            c.verts.push(v); c.n++;
            for (let a = 0; a < 3; a++) { c.sum[a] += P[v * 3 + a]; c.nrm[a] += N[v * 3 + a]; }
          }
          return c.id;
        }));
      }
      // Cluster vertices: mean position, summed normal, the uv of the vertex nearest the mean.
      const vbase = V0 + lodPos.length / 3;
      const ordered = [...clusters.values()].sort((a, b) => a.id - b.id);
      for (const c of ordered) {
        const p = c.sum.map((x) => x / c.n);
        const l = Math.hypot(c.nrm[0], c.nrm[1], c.nrm[2]);
        let best = c.verts[0], bd = Infinity;
        for (const v of c.verts) {
          const d = (P[v * 3] - p[0]) ** 2 + (P[v * 3 + 1] - p[1]) ** 2 + (P[v * 3 + 2] - p[2]) ** 2;
          if (d < bd) { bd = d; best = v; }
        }
        lodPos.push(...p);
        lodNrm.push(...(l > 1e-12 ? c.nrm.map((x) => x / l) : [N[best * 3], N[best * 3 + 1], N[best * 3 + 2]]));
        lodUv.push(UV[best * 2], UV[best * 2 + 1]);
      }
      const seen = new Set<string>();
      const mine: typeof pending[number] = [];
      tris.forEach((t, i) => {
        const m = table[t * 4 + 3];
        const ids = triCl[i];
        const k2 = `${m}|${[...ids].sort((a, b) => a - b).join(',')}`;
        if (seen.has(k2)) return;
        seen.add(k2);
        const collapsed = ids[0] === ids[1] || ids[1] === ids[2] || ids[0] === ids[2];
        mine.push({ chunk: ci, t, collapsed, v: [vbase + ids[0], vbase + ids[1], vbase + ids[2]], m });
      });
      // Level 0 keeps the full triangles unless clustering removes most of them (triangles much finer than the voxels).
      if (s === 0 && mine.length > LOD0_KEEP * tris.length) { lod.push(full); continue; }
      pending[s].push(...mine);
      lod.push(new Uint32Array(0)); // filled below, once the rows are numbered
    }
    return { lo: lo.map((x) => x - MOTION_MARGIN) as Vec3, hi: hi.map((x) => x + MOTION_MARGIN) as Vec3, full, lod };
  });
  pending.forEach((list, s) => {
    if (list.length === 0) return;
    list.sort((a, b) => (Number(b.collapsed) - Number(a.collapsed)) || a.t - b.t);
    const perChunk = new Map<number, number[]>();
    for (const e of list) {
      let l = perChunk.get(e.chunk);
      if (!l) perChunk.set(e.chunk, l = []);
      l.push(firstRow + lodRows.length / 4);
      lodRows.push(e.v[0], e.v[1], e.v[2], e.m);
    }
    for (const [c, l] of perChunk) chunks[c].lod[s] = Uint32Array.from(l);
  });
  const grow = (a: Float32Array, add: number[]) => { const b = new Float32Array(a.length + add.length); b.set(a); b.set(add, a.length); return b; };
  const nv = lodPos.length / 3;
  const out: SceneData = { ...scene, positions: grow(P, lodPos), normals: grow(N, lodNrm), uvs: grow(UV, lodUv),
    tangents: grow(scene.tangents, new Array(nv * 4).fill(0)) };
  const bMin: Vec3 = [Infinity, Infinity, Infinity], bMax: Vec3 = [-Infinity, -Infinity, -Infinity];
  for (const o of instances) for (let a = 0; a < 3; a++) { bMin[a] = Math.min(bMin[a], sMin[a] + o[a]); bMax[a] = Math.max(bMax[a], sMax[a] + o[a]); }
  return { scene: out, world: { instances, staticTriangles: T, staticVertices, v0, levels, chunks, lodFirstVertex: V0, lodVertexCount: nv,
    lodTable: Uint32Array.from(lodRows), boundsMin: bMin, boundsMax: bMax, staticMin: sMin, staticMax: sMax } };
}

/** One work item of the voxel build: the chunk's rows (list) or a contiguous range of rows (list < 0), placed at an instance,
 * voxelised from level `start` on. */
export interface WorkItem { inst: number; start: number; list: number; first: number; count: number; }

/** The windows (per level, [lo, hi) in metres) -> this frame's items, in a fixed order (instance, chunk). */
export function selectItems(world: World, listOffset: (c: number, s: number) => number, windows: { lo: Vec3; hi: Vec3 }[]): WorkItem[] {
  const items: WorkItem[] = [];
  world.instances.forEach((o, inst) => {
    world.chunks.forEach((ch, c) => {
      let s = -1;
      for (let L = 0; L < windows.length && s < 0; L++) {
        const w = windows[L];
        if ([0, 1, 2].every((a) => ch.lo[a] + o[a] < w.hi[a] && ch.hi[a] + o[a] > w.lo[a])) s = L;
      }
      if (s < 0) return;
      const n = ch.lod[s].length;
      if (n > 0) items.push({ inst, start: s, list: listOffset(c, s), first: 0, count: n });
    });
  });
  return items;
}
