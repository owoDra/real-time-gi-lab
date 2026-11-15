// Log lines and the committable summary of one config's run, shared by the native and the browser runners.
import { lum, type RunContext, type RunOptions, type runConfig } from '../core/rcrun.ts';

export type RunResult = Required<Awaited<ReturnType<typeof runConfig>>>;
export interface Platform { platform: 'native' | 'browser'; implementation: string; adapter: Record<string, unknown> }

export function reportConfig(name: string, r: RunResult, ctx: RunContext, opts: RunOptions, meta: Platform, log: (s: string) => void) {
  const spec = ctx.spec;
  const strip = <T extends { images: unknown }>(x: T | null) => { if (!x) return null; const { images: _, irr: __, ...rest } = x as T & { irr?: unknown }; return rest; };
  let leak = null;
  if (spec.enclosed && r.static.irr) {
    const { rgb, valid } = r.static.irr;
    let s = 0, n = 0, mx = 0;
    const all: number[] = [];
    for (let p = 0; p < valid.length; p++) if (valid[p]) { const l = lum(rgb[p * 3], rgb[p * 3 + 1], rgb[p * 3 + 2]); s += l; n++; mx = Math.max(mx, l); if (p % 5 === 0) all.push(l); }
    all.sort((a, b) => a - b);
    // Reference scale: the sun's irradiance on the floor outside.
    const sd = spec.sunDir, sunOnFloor = lum(9, 8.5, 7.8) * sd[1] / Math.hypot(...sd);
    leak = { meanIrradiance: s / n, p99Irradiance: all[Math.floor(all.length * 0.99)], maxIrradiance: mx, sunOnFloor,
      meanFractionOfSun: s / n / sunOnFloor, pixels: n };
  }
  const summary: Record<string, unknown> = {
    kind: 'exploratory (探索値)', date: new Date().toISOString(), ...meta,
    scene: { name: spec.name, triangles: spec.scene.triangleCount, sunDir: spec.sunDir }, resolution: `${ctx.width}x${ctx.height}`,
    frames: { warmup: opts.warmup, measured: opts.frames, inFlight: opts.inFlight, seedFixed: opts.seedFixed }, sky: opts.sky,
    config: name, params: r.params, ddgiDims: r.ddgiDims, allocatedBytes: r.allocatedBytes, voxAllocatedBytes: r.voxAllocatedBytes, dynAllocatedBytes: r.dynAllocatedBytes, bvh: ctx.bvh,
    voxParams: ctx.voxWorld?.params ?? null, buildingMotion: r.buildingMotion, static: strip(r.static), moving: strip(r.moving), staticGeo: strip(r.staticGeo), movingGeo: strip(r.movingGeo), tracer: r.tracer, leak,
  };
  const t = r.static.timing, m = r.moving?.timing;
  if (r.ddgiDims) log(`  ddgi grid ${r.ddgiDims.join('x')}; active, updated, relocated, stuck: ${r.static.counts.join(', ')}`);
  log(`  GI static ${t.giTotal.median} ms (vox ${t.vox?.median ?? '-'}, build ${t.giBuild.median}, trace ${t.giTrace.median}, merge ${t.giMerge.median}, gather ${t.giGather.median})` + (m ? `; moving ${m.giTotal.median} ms` : ''));
  log(`  probes ${r.static.counts.join(', ')}; used ${(r.static.usedBytes / 2 ** 20).toFixed(1)} MiB, allocated ${(r.allocatedBytes / 2 ** 20).toFixed(1)} MiB`);
  const M = (b: number) => (b / 2 ** 20).toFixed(1);
  log(`  GI allocated ${M(r.allocatedBytes + r.voxAllocatedBytes + r.dynAllocatedBytes)} MiB (field ${M(r.allocatedBytes)}, vox ${M(r.voxAllocatedBytes)} incl. build temporaries, dyn ${M(r.dynAllocatedBytes)})`);
  if (r.static.vox) log(`  vox ${JSON.stringify(r.static.vox)}`);
  if (opts.dynStages) log(`  stages (median ms) ${Object.entries(t).filter(([k]) => k.startsWith('dyn.') || k.startsWith('vox.')).map(([k, v]) => `${k} ${v.median}`).join(', ')}`);
  if (r.static.buildingChange) log(`  building change (first vs last measured frame, static camera) ${JSON.stringify(r.static.buildingChange)}`);
  if (r.static.dynWork) log(`  dyn work ${JSON.stringify(r.static.dynWork)}; last frame ${JSON.stringify(r.static.dynWorkLast)}`);
  if (r.tracer) log(`  tracer ${JSON.stringify(r.tracer)}`);
  if (leak) log(`  leak ${JSON.stringify(leak)}`);
  if (r.static.blackPct !== null) log(`  black pixels ${r.static.blackPct} % of the photoreal pixels (every c0 probe hidden, last frame)`);
  log(`  flicker static ${JSON.stringify(r.static.flicker)}`);
  log(`  excess static ${JSON.stringify(r.static.excess)}`);
  log(`  chain excess static ${JSON.stringify(r.static.chainExcess)}`);
  if (r.moving) log(`  flicker moving ${JSON.stringify(r.moving.flicker)}`);
  if (r.moving) log(`  chain excess moving ${JSON.stringify(r.moving.chainExcess)}`);
  // Without normal maps (the main values on a moving camera and a moving building).
  if (r.staticGeo) log(`  geo static: flicker fine ${r.staticGeo.flicker.staticFinePct} % (control ${r.staticGeo.flicker.controlFinePct}), excess k16 ${r.staticGeo.excess?.k16.excessPerFrame} (linear ${r.staticGeo.excess?.k16linear.excessRelPerFrame})`);
  if (r.movingGeo) log(`  geo moving: flicker fine ${r.movingGeo.flicker.staticFinePct} % (control ${r.movingGeo.flicker.controlFinePct}), chain excess ${r.movingGeo.chainExcess.excessPerFrame} (linear ${r.movingGeo.chainExcess.excessRelPerFrame}, control ${r.movingGeo.chainExcess.controlExcessPerFrame})`);
  return summary;
}

/** rgb + tag (0 invalid, 1 photoreal, >= 2 toon) as float32, rows top to bottom (--dump-irr, the Mitsuba comparison). */
export function packIrradiance(irr: { rgb: Float32Array; tag: Uint8Array }) {
  const { rgb, tag } = irr, f = new Float32Array(tag.length * 4);
  for (let p = 0; p < tag.length; p++) { f.set(rgb.subarray(p * 3, p * 3 + 3), p * 4); f[p * 4 + 3] = tag[p]; }
  return f;
}
