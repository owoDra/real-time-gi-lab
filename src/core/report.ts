import type { BenchResult } from './bench.ts';

export interface RunContext {
  platform: 'native' | 'web';
  implementation: string;
  userAgent: string;
  adapter: { vendor?: string; architecture?: string; device?: string; description?: string };
}

/** Small, committable summary of one run (no per-frame data, no images). */
export function summarize(r: BenchResult, ctx: RunContext) {
  const round = (x: number) => Math.round(x * 1000) / 1000;
  return {
    kind: 'exploratory (探索値)',
    date: new Date().toISOString(),
    ...ctx,
    resolution: `${r.options.width}x${r.options.height}`,
    frames: { warmup: r.options.warmup, measured: r.options.frames, inFlight: r.options.inFlight },
    scene: r.scene,
    camera: r.camera,
    timestampsAvailable: r.timestampsAvailable,
    timestampGranularityNs: r.timestampGranularityNs,
    gbufferPass: r.stats && Object.fromEntries(Object.entries(r.stats).map(([k, v]) => [k, round(v)])),
    allocatedBytes: { ...r.memoryBytes, note: 'sum of created resources, not a measured peak' },
    loadMs: Math.round(r.loadMs),
  };
}
