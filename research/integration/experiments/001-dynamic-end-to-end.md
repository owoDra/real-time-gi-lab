# I001 — dynamic end-to-end GI integration gate

Status: protocol frozen; implementation target-run-ready; target evidence pending

## Question

Do the evidence-backed lane choices remain a better quality/performance/memory
trade-off when executed as one complete dynamic GI pipeline rather than as
isolated kernels?

## Fixed architecture variants

1. **vanilla-split-rc**
   - A001 standalone visibility + producer semantics;
   - natural append order;
   - B002 software-BVH reference traversal;
   - C001 per-probe sparse hash;
   - full-capacity stream;
   - no renderer reuse.

2. **combined-hwrt**
   - same producer/storage/order;
   - HWRT / TLAS primary traversal;
   - all BLAS/TLAS setup/update costs required by the scenario included.

3. **combined-software**
   - same producer/storage/order;
   - B003 segment DDA/hash + conservative quantized Micro BVH8;
   - required membership/build/refit/rebuild/upload costs included.

4. **depth-reuse-hwrt**
   - combined-hwrt with D001 depth reuse;
   - report both renderer-integrated incremental GI time and a full standalone
     boundary that includes the equivalent renderer depth prerequisite.

5. **bounded-hwrt**
   - optional only if bounded capacity can be integrated without the rejected
     D005 owner-slot staging path;
   - safe clamp/overflow detection and explicit full-capacity retry are
     mandatory.

The B002 binary-micro hierarchy remains a diagnostic control only. D002-D004
and D005's standalone owner-slot implementation are not candidates.

## Scenarios

Accepted architectural evidence must cover:

- Sponza static camera/static geometry;
- Sponza camera motion/disocclusion;
- Sponza changing direct light;
- Sponza controlled moving rigid geometry;
- sparse stress;
- dense stress;
- large-world stress;
- vertical-world stress.

Sponza cases are the representative evidence. Synthetic/stress cases isolate
mechanisms and limits; they cannot by themselves select the final architecture.

Moving geometry timing includes producer interaction, traversal maintenance,
storage invalidation/update, temporal resolve and:
- HWRT: BLAS update/rebuild + TLAS update + trace;
- software: membership/update + refit/rebuild + upload + traversal.

## Timing boundaries

GPU timestamps must report at least:

- renderer visibility prerequisite (when present);
- GI visibility/reuse;
- producer emit/finalize;
- traversal maintenance;
- traversal;
- radiance lookup/update;
- allocation/residency;
- invalidation;
- merge/resolve;
- complete GI frame.

CPU work required by an architecture is recorded separately and is never hidden
from the end-to-end result. Setup, steady state and dynamic update are reported
separately.

Accepted timing uses validation disabled and process-level repeats. A diagnostic
validation run precedes accepted timing.

## Memory and churn

Record persistent, transient, scratch, resident/peak bytes plus:

- rays/queries/updates;
- allocation/eviction/invalidation churn;
- overflow count and requested/capacity items;
- fallback/retry occurrence;
- update latency.

Resident fallback resources count when they remain allocated.

## Quality/reference

Performance rows are accepted only after quality parity.

The independent reference path uses the software-BVH Hit contract from the same
A001 rays. Those independently generated hits are then evaluated by the same
canonical deterministic radiance shader used by candidates before merge/storage.

The I001 radiance value is intentionally a synthetic contract payload rather
than a production shading model. A hit's primitive/material/instance identity,
cascade/ray identity, and the current direct-light state are hashed into a
16-bit contribution. Hit distance and normal are not re-used for this payload
because they are already checked by the independent Hit gate with an explicit
floating tolerance. This separation makes equivalent HWRT/software hits produce
bit-identical radiance while light-motion still changes the payload, so the
fixed final radiance thresholds remain meaningful for merge/storage/temporal
integration rather than becoming a second, inconsistent traversal tolerance.

Integrated variants compare their resolved probe/tile field against that
reference.

Record:
- RMS and max absolute radiance error;
- temporal RMS/max error across transitions;
- disocclusion stale-output count;
- moving-geometry stale/ghost count;
- changing-light convergence error after each measured frame;
- invalid/missing/leaked probe count.

Hard quality gate:
- Hit-contract mismatches/runtime errors/OOB/validation errors: zero;
- stale outputs after a required invalidation/update frame: zero;
- max absolute deterministic radiance error <= 1e-4;
- RMS deterministic radiance error <= 1e-5.

If later production shading introduces stochastic sampling, that requires a new
protocol rather than silently relaxing I001.

## Correctness hard gate

Before timing:
- A001 visibility/producer semantics and counts pass;
- schema/workload identity is preserved;
- traversal Hit contract passes;
- sparse-hash insert/lookup/update/invalidation passes;
- moving geometry update is visible in the same frame contract;
- overflow clamp/retry is safe where applicable;
- no OOB or Vulkan validation errors in the diagnostic run;
- deterministic contract fields match; natural append-order nondeterminism is
  compared semantically, not byte-for-byte.

A failed correctness row cannot contribute accepted timing.

## Fixed decision gates

### Target-GPU primary
`combined-hwrt` is promotable for the measured target only if:
- quality/correctness gates pass in every required scenario;
- median complete GI GPU time is <= 0.90x vanilla in each representative
  Sponza static/camera/light/moving scenario;
- no required stress scenario regresses complete GI GPU time by >5%;
- peak resident memory is reported and remains <=3.0x vanilla.

A memory ratio above 1.5x prevents an unqualified universal-win claim even when
the target-GPU primary passes; the result must be target/performance-conditional.

### No-HWRT fallback
`combined-software` is promoted over vanilla software traversal only if:
- quality/correctness passes;
- representative complete GI median is <=0.90x vanilla;
- peak resident memory is <=1.15x vanilla;
- moving-geometry complete maintenance does not regress by >5%.

### Renderer depth reuse
Retain as an integration optimization only if incremental GI GPU time improves
by >=10% versus the otherwise identical combined-hwrt boundary. The standalone
full boundary must still expose the renderer depth prerequisite.

### Bounded capacity
Retain only if:
- producer resident/peak stream memory is <=0.60x full-capacity combined-hwrt;
- normal-case complete GI GPU time is <=1.05x full-capacity;
- forced-overflow clamp and full retry both pass correctness;
- retry latency/memory is reported, not discarded.

If regimes disagree, publish conditional decisions rather than changing these
thresholds or averaging away the split.

## Repeats and provenance

Accepted artifact must record:
- clean Git commit/branch;
- exact command and artifact root;
- scene/scenario/variant;
- target GPU, driver and API;
- validation state;
- warmup/iteration/process-repeat counts;
- raw rows and summary;
- commit hash in CSV/JSON, not only metadata.

Formal target runs use `mise run research:record --lane integration-gate
--experiment 001-dynamic-end-to-end --command "..."`.

## Result contract

I001 concludes only after implementation, validation, repeated target timing,
quality/reference evidence and a committed result/index entry. No PR or merge
is part of this experiment.


## Target-ready implementation checkpoint

The implementation is complete enough for the first formal target run. No
performance conclusion has been drawn from implementation-only evidence.

The composed runtime uses one Vulkan device/queue and records the measured frame
as a connected GPU pipeline:

1. A001 visibility/depth or the D001 depth-reuse boundary;
2. A001 natural owner/producer emission with no global reorder;
3. GPU work-item to ray conversion;
4. selected traversal path;
5. deterministic hit-derived radiance;
6. merge;
7. per-probe open-addressed sparse-hash update;
8. stale-entry invalidation;
9. resolved probe output.

The moving-rigid Sponza case deliberately selects a real mesh instance and a
translation that changes StrataBrick segment membership. HWRT measures the
accepted BLAS/TLAS update path. The vanilla software control rebuilds its BVH.
The B003 fallback performs membership update, affected hierarchy rebuild,
quantized Micro BVH8 regeneration/upload, and traversal. Moving primitive count
and segment-membership-change count are written into every target row.

Stress definitions were fixed before target timing:

- sparse: Sponza at 64 x 36 visibility tiles;
- dense: Sponza at 256 x 144 visibility tiles;
- large-world: identical Sponza geometry translated by +1e6 X / -1e6 Z;
- vertical-world: identical Sponza geometry scaled 16x on Y.

These are mechanism/stability stresses only; they do not replace the
representative Sponza static/camera/light/moving evidence.

The bounded variant uses the integrated clamp/overflow path rather than D005's
rejected staged owner-slot implementation. A single natural owner append index
derives both output and work ranges and writes directly into the bounded stream;
requested counters are tracked separately and clamped only after emission. This
prevents overflow from leaving holes in the dispatchable prefix. The formal
matrix also forces a 512-owner overflow and then runs an explicit full-capacity
HWRT retry. Failed-attempt setup wall time, retry setup wall time, GPU retry
time, and peak memory are retained as evidence.

Quality validation now covers:

- A001 visibility and producer semantic parity;
- bounded partial-block owner/order/range safety under forced overflow;
- shared Hit-contract parity against the software-BVH reference;
- sparse-hash reserve/reset and accumulate phases;
- token/key consistency and duplicate current-frame sparse slots;
- insert/update/invalidate/resolve behavior;
- missing/leaked/stale probes;
- final resolved-output parity;
- frame-to-frame temporal RMS/max parity.

The diagnostic validation matrix runs before validation-disabled accepted
timing. All 33 validation cases are attempted before failures are reported, and
the runner persists `i001-validation-summary.json`. Validation-layer error
markers are a hard failure even when the child process exits successfully. A
`--validation-only` preflight is available to exercise the complete
correctness matrix without starting repeated timing.

Each accepted process records one warmup frame, one measured static/transition
frame, setup wall time, exact device/driver/API, memory, churn, quality, and Git
provenance. Storage capacity is reserved for the maximum of the warmup and
target transition endpoints. Moving-frame `complete_gpu_us` includes timed
surface/traversal-buffer transfers plus HWRT/software traversal maintenance.
Process-level repeats are aggregated by the formal runner.

Formal target sequence:

```bash
git checkout research-integration-gate
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane integration-gate \
  --experiment 001-dynamic-end-to-end \
  --command "python scripts/research/integration/run_i001.py --build-dir build/release --repeats 3"
```

Expected top-level I001 artifacts include:

- `i001-validation-summary.json`;
- `i001-representative.csv`;
- `i001-stress.csv`;
- `i001-overflow-retry.csv`;
- `i001-representative-summary.json`;
- normal `metadata.json`, stdout and stderr from `research:record`.

The summary evaluates the already-frozen decision gates mechanically. It does
not alter a threshold after observing timing.

No DDGI or representative sparse-radiance-cache implementation existed in this
repository when the protocol was frozen. I001 therefore does not manufacture a
weaker namesake baseline. That comparison remains unavailable unless a
semantically comparable implementation is introduced before accepted timing.
