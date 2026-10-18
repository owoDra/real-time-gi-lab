# N010 post-hoc early-density route diagnostic

2026-10-18 JST; parent b39465c1. Commit before source generation/build/GPU.
Original115's full-frame372 FAIL stays authoritative and stopped. This is a
new, bounded cause diagnostic and conservative routing candidate, not a retry
of that campaign, a mask, reference admission, or a new acceptance threshold.

## Source finding and falsifiable hypothesis

Original360 `whole_density_prefixes_gpu` returns for nonpositive PDF before
the existing1e-12 small-density route check. It similarly returns at zero
target cosine before its route check. `direct_term` also skips a nonpositive
endpoint cosine without a near-zero CPU route. These are source-confirmed
gaps in routing coverage, not confirmation that any caused372's discrepancy.
CPU scan376 localizes the shadow count to pixel43665/(145,136), but has no
per-path GPU record. Its sample9 has indirect RGB2.794246640492007e-27; this
suggests inspecting grazing cases, not selecting it as the known failing
sample. Do not attribute the two global proposal queries to this pixel yet.

Question: does the original shader reproduce the retained pixel count
[16,52,4,0], and does routing near-zero cases BEFORE those early branches
restore all16 original CPU sample counters/proposal audit while preserving
the old raw GPU path outputs? If not, stop this diagnostic without tuning.
Actual sample/depth/ray cause remains UNRESOLVED until evidence identifies it.

## Exact candidate and scope

Copy original360 shader/host/CPU headers with pinned identities. Add early
route8 at abs(unclamped source cosine)/pi<1e-12, target cosine<1e-12 and
abs(direct endpoint cosine)<1e-12, before their zero returns. Preserve PDF,
geometry, weights, target contributions, all old guards and CPU fallback.
Negative source cosines far from zero remain ordinary proposal zeros. This
only delegates complete original samples to unchanged CPU logic; no pixel or
contribution is excluded or thresholded from scoring. Record telemetry in
the two reserved GPart proposal words: early-site bit mask(1 PDF,2 target
cosine,4 direct cosine) and number of nonpositive early branches. CPU audit
query/own fields and physical work stay unchanged.

Add a separate `counter-pixel` host mode selecting43665 and retaining all
raw/corrected16 samples, seven depth parts, flags, statistics, images, ledger
and full scene identities. Existing full/diagnostic8 modes keep their scope.
Recompute backend identity; prove complete shader/host inverse to360 and
byte-identical CPU headers. Old GPU probe uses the exact original360 SPIR-V;
guarded probe uses only the separately compiled candidate. Same new host,
scene/net/seed305419896,16spp/batch16/tile1, no prefix and one CPU worker.

## Explicit manual steps and finite stop

Driver: `scripts/research/n010_reference_sampling/diagnose_early_density_routes.py`.
Work: `early-density-route-diagnostic-v1`. No waiting/automatic next step.

1. `--step prepare` ->380 source/inverse evidence only. May execute while260
   runs: small file/source processing, no native compilation or acquisition.
2. `--step build` ->381 two isolated compiler invocations only, each120CPU/
   180elapsed seconds. Requires260 terminal seed integrity PASS and actual
   quiescence. Keep strict original compiler flags and NoContraction.
3. `--step old` ->382 ONE focused diagnostic with original SPIR-V. Requires
   381 terminal valid. No new CPU oracle acquisition: use all16 exact retained
   independent CPU sample records from376. If old corrected aggregate does
   not reproduce[16,52,4,0], stop; no guarded probe or favorable-data repetition.
4. `--step guarded` ->383 ONE focused candidate diagnostic, only after382
   valid/reproducing. Require all16 CPU scored counts and aggregate original
   query/attempt/null/own counts exactly, finite nonnegative sample components
   with max absolute error<=1e-10, and preserve all raw/route/depth evidence.
   Compare old/new raw path bytes; if different, no guard-only causal claim.

Each GPU native60CPU/120elapsed seconds, CPU31/nice15/4GiB, fixed original2ms
depth pauses and250ms submit/wait operational guard. One compiler/native at
a time, no overlap with260 or any acquisition. Require2GiB free before work;
retained diagnostic work<=1GiB; owned Vulkan replay<=8GiB/zero teardown and
original own-log<=1e-6/conditioned<=1/weight<=8 numerical guards. Keep all failures, stdout/
stderr, actual PID/start/limits, hashes and terminal status; no overwrite or
retry. Re-poll live handles after observation expiry. Default Renderer and
all completed results remain untouched. No display/power/clock/driver/app
settings, CUDA, Actions or N011.

All four outputs retain `all_pass=false`, `accepted_timing=false` and
`reference_admission=false`; use `step_valid` for this bounded diagnostic's
integrity only. Even a restored pixel does not repair372, prove full-frame
conformance, qualify the candidate for references or justify scaling. Any
later full-frame candidate check needs separate prospective scope/stop
conditions. No such acquisition is queued by this plan. Continue original
CPU qualification; this preparation does not interrupt or restart260.
N010 NOT_READY, references16/24, direct-relative1.0 pixels UNRESOLVED/未解決
and included. Unit/regression tests NOT RUN; source/scientific diagnosis only.
