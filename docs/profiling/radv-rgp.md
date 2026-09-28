# RADV / Radeon GPU Profiler capture procedure

This procedure is evidence support for Experiment 000. It is not part of the
timed benchmark harness: profiling changes execution and must not be mixed with
the timestamp results in `results.csv`.

The authoritative environment-variable reference is Mesa's current
[Environment Variables documentation](https://docs.mesa3d.org/envvars.html).
RGP itself is documented by
[AMD GPUOpen](https://gpuopen.com/rgp/).

## Why integrated RADV capture

The target exploratory system uses RADV. Current AMD Linux driver releases use
RADV by default and Radeon Developer Panel cannot capture Vulkan workloads
through RADV. Use RADV's integrated RGP trace path instead.

## Minimal reproducible capture

Build normally, then capture a single benchmark submit:

```bash
mise run build

MESA_VK_TRACE=rgp \
MESA_VK_TRACE_PER_SUBMIT=1 \
RADV_THREAD_TRACE_CACHE_COUNTERS=1 \
RADV_THREAD_TRACE_INSTRUCTION_TIMING=1 \
bash ./scripts/run_with_vulkan.sh \
  build/release/phos-gi-lab \
  --scene assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf \
  --queries 4000000 \
  --iterations 1
```

Mesa writes RGP traces to `/tmp`. `MESA_VK_TRACE_PER_SUBMIT=1` is intended
for compute-only workloads. This program performs setup/upload submits as well
as benchmark submits, so identify the trace containing the expected compute
dispatch sequence rather than assuming the first generated file is the lookup
measurement.

Use one timed iteration for profiling to keep traces tractable. The normal
`mise run bench:sweep` settings remain the source of timing evidence.

## Cases to inspect

Capture representative 4M-query cases only after normal timestamp results are
stable. At minimum compare:

- hash / source;
- hash / page-grouped;
- paged / source;
- paged / page-grouped;
- GPU page grouping itself;
- GPU grouping + hash lookup;
- GPU grouping + paged lookup.

The CPU page-grouped cases provide the clean layout-vs-ordering comparison.
GPU-grouped cases answer whether the scheduling mechanism changes the same
memory behavior and whether its own cost is acceptable.

## Evidence to record

Prefer counters and panes that answer the causal question rather than collecting
every available metric:

- cache request/hit/miss behavior, especially the last-level cache;
- device-memory request volume and bandwidth;
- cache/memory stalls or latency-bound behavior;
- wavefront occupancy and active-wave behavior;
- instruction timing around hash probing, page-table lookup, histogram atomics,
  prefix construction, and scatter.

RGP/RADV exposes some cache counters directly on GFX10+.
`RADV_THREAD_TRACE_CACHE_COUNTERS` and
`RADV_THREAD_TRACE_INSTRUCTION_TIMING` are currently enabled by default, but
set them explicitly in research captures so the procedure is self-describing.

When additional sampled counters are required, Mesa supports
`RADV_SPM_COUNTERS_CONFIG=/path/to/config` on GFX10+. Counter block/event IDs
are ASIC-specific. Do not copy example event IDs into the experiment protocol
without first verifying that they are valid for the target GPU.

For each accepted profile, record alongside the observation:

- repository commit;
- GPU name;
- Mesa/RADV version;
- kernel version;
- query count and workload;
- representation and ordering;
- all trace-related environment variables;
- RGP version;
- whether the capture changed clocks or profiling p-state.

## Interpretation

A lower timestamp alone does not establish better locality.

- If page grouping lowers lookup time and cache misses/transactions for both
  hash and paged storage, scheduling is the likely common cause.
- If paged remains better than hash under the same grouping and also shows
  lower memory pressure/stalls, contiguous page-local storage has independent
  evidence.
- If GPU grouping consumes enough time or bandwidth to erase the lookup gain,
  the CPU-preordered result is only an upper bound and should not justify
  promotion of the scheduling strategy.
- If timing improves without a corresponding memory-behavior explanation,
  retain the observation but do not claim a locality mechanism until additional
  evidence resolves it.
