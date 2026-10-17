# N010 prospective depth-split hybrid numerical diagnostic

2026-10-18 JST; after terminal360 build, before any new native acquisition.
Freeze this plan/driver in Git before data. Not a performance comparison.

## Fixed scope and independent reference

Does112's new tile/depth execution reproduce original254's CPU all-split
data while retaining original full-sample CPU fallback? Require360 build
PASS and immutable generated/input identities, terminal353 independent CPU
probe and terminal358 all32 original selected-C1 conformance. Do not rerun
the original CPU probe: reuse its353-pinned cpu-probe.json, primary/cache/
scored counters and original hits. Original254 paired-data supplies exactly
32 mixture_mean/mixture_second records and original proposal audits, in the
original eight-pixel/four-seed order. Old sampler mean/second are not used.

All new natives use360 binary/full.spv, original320x180 C1_T_B8 scene/net,
diagnostic8 mode/tile8/BEGIN0/PREFIX '-' and one CPU fallback worker. This
remains eight computed pixels only; all outside-selection zeros are
uncomputed and ineligible. No full-frame/reference/bias/density admission.

## Explicit steps and fixed resources

Driver: scripts/research/n010_reference_sampling/acquire_depth_split_hybrid.py
Work: out/research/n010-comparison-readiness/depth-split-hybrid-diagnostic-v1

1. One explicit --probe creates361-depth-split-hybrid-probe.json. Only one
   new GPU native at seed305419896/1spp/batch1/tile8;60CPU/90elapsed seconds.
   Compare directly to the retained independent353 CPU probe, not just352's
   GPU values. No new CPU native or geometry/reference generation.
2. Only after361 PASS, one explicit --seed-index0..3 creates362..365,
   in original seed order305419896,2596069104,81985529216486895,
   18364758544493064720. Each8192spp/batch16/tile8,360CPU/600elapsed.
   Require all preceding parts PASS; one manually invoked part at a time.
3. A separate --summarize creates366-depth-split-hybrid-numerical.json
   only after probe and all four parts PASS; all32 original rows required.

CPU31/nice15/4GiB for driver and each native, one scientific worker/compiler
at a time. No automatic queue, retries, output overwrite or favorable-data
extension. Preserve failure/partials on250ms per-depth submit/wait guard,
resource timeout, device fault or any invalid evidence. Observation-tool
timeout is not native completion and does not permit restarting a live PID.
Fixed2ms between depth submissions as112. No power/clock/display/driver/app
changes or idle-percentage requirement. Retained work cap1GiB for all five
parts; preflight must require2GiB free. These are operational guards, not GI
losses, accepted GPU timestamps or environmental stability acceptance cuts.

## Frozen validation before accepting a part

Use honest new112 schemas, without schema substitution into the111 validator.
Record source/backend/scene/net/geometry/shape/seed/SPP/layout identities,
native PID/start/resources/terminal receipts, stdout/stderr, every input and
payload SHA. Recheck inputs after acquisition. No accepted part on a missing
pair, invalid/nonfinite corrected value, device fault or provenance mismatch.

Retain all raw160-byte paths, corrected160-byte paths,4-byte route masks and
seven128-byte depth parts per path. Check every stream length and sample/
tile/depth interval. Reassemble raw paths from all depth parts in the exact
host depth-addition order and original primary RGB/counts; require bit-exact
raw reconstruction. Require every unflagged raw/corrected path byte-identical.
Reconstruct corrected per-pixel sums, second moments and scored counters in
original sample order; require exact full-layout gpu.stats and o.f64 bits.
Require all uncomputed pixels zero and selected per-pixel sample counts SPP.
All batch/global route-bit counts and CPU-fallback counts must match streams.
Report all six overlapping route reasons; never infer causality from a
missing reason category or delete a flag because raw output is close.

For each original row, require exact emission/direct means AND moments,
primary hit/cache192-byte records and all four scored integer counters.
Max absolute error over all12 mean/second-moment channels<=1e-10 and indirect
RGB NRMSE across all eight rows<=1e-8. Zero CPU energy requires exact equality.
No relaxed thresholds after viewing data.8192 expected endpoint counts come
from254 plus independent353 primary-cache counts*8192.

Check64-byte audit.bin against metadata exactly. Attempts=8*SPP*7 and
nulls+ownchecks=attempts; audit maxima finite/nonnegative, own-log-error
bound<=1e-6, conditioned error fraction<=1 and weight<=8. Preserve unconditioned
maxima without inventing a passing threshold. For each8192 native require
proposal query/attempt/null/own counts equal sums of original254 audits.
The1spp353 CPU probe has no corresponding full proposal-audit record; do not
claim an independent count match for that step. GPU own-log metadata is the
conservative ratio-derived bound, not the exact CPU logarithmic error.

Replay owned allocation events, true peak<=8GiB and teardown zero. This is
standalone-backend Vulkan memory only, excluding CPU/driver-private memory;
it cannot qualify Renderer true peak. Every depth submit/wait must satisfy
the unchanged operational250ms guard; wall values remain diagnostic. No
comparison against254's different-work CPU cost as a GI speedup denominator.

All PASS means only numerical conformance on the selected32 C1 pairs for
the new execution layout. Full-frame execution feasibility, original full
physical/IID/bias proof, all24 states/exact prefixes, reference qualification,
quality/dynamic/true-peak pilots, selected GPU-time calibration and final
proof intake remain required. No change to106/108/109 or old FAILs.
References16/24, original full inventory14/17 including one diagnostic-only
item, direct relative1.0 pixels UNRESOLVED/未解決 and scored; N010 NOT_READY.
No N011, CUDA, Actions, default Renderer graph or N001--N009 result changes.
Unit/regression tests NOT RUN; these are registered scientific acquisitions.
