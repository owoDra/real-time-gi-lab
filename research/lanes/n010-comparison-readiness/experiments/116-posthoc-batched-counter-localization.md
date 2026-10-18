# N010 post-hoc CPU-only batched-counter localization

2026-10-18 JST; after terminal371/372, before this diagnostic build/native.
This is explicitly post-hoc diagnosis, not preregistered performance evidence,
accepted qualification or a repair of372. Parent fc044642.

## Known failure and finite question

372 native exits0 and its full16spp means/moments pass the frozen numerical
cuts, but CPU/GPU shadow_tests differ by one (2722260 versus2722259).
Blocked/primary/backface counts match. Proposal queries also differ by two
(53595139 versus53595137). Original115 is **FAIL**, irrespective of its
44.752s GPU versus53.512s CPU native elapsed. Do not create successful373
summary or continue GPU scaling/restore/campaign on this failed variant.

Localize the shadow-count mismatch using existing GPU per-pixel aggregate
stats and a CPU-only replay. No new GPU acquisition, routing/threshold
relaxation, scene/sample omission or changed reference. Ray-level numerical
cause is unknown; a matching energy result alone does not resolve it.

## Source, complete scan and retained evidence

Driver: scripts/research/n010_reference_sampling/diagnose_batched_counter_mismatch.py
Source: scripts/research/n010_reference_sampling/batched_counter_scan.cpp
Work: out/research/n010-comparison-readiness/posthoc-batched-counter-localization-v1

--step build creates375-posthoc-batched-counter-build.json: one isolated
compiler, exact254 CPU header copied byte for byte, original exporter strict
O3/AVX512F/-fno-fast-math/-ffp-contract=off flags, no BVH verification macro.
No physical/RNG/sampler/CPU header edits; no default build linkage.

Only after375 terminal compiler PASS, --step scan creates376-posthoc-batched-counter-scan.json:
one CPU native computing all57,600 original C1 pixels,16spp, seed305419896.
Use original371 scene/net,372 gpu.stats and371 independent CPU sidecar.
For EVERY pixel reconstruct CPU mean/moment and require all24 sidecar double
bits exactly371. Compare all four per-pixel scored counters to existing GPU
stats, sum the full-frame counts and require exact371/372 global identities.
Require all full-scan CPU proposal counts exactly371. No scan stops on first
mismatch; retain every differing pixel, both pixel counters, all16 CPU sample
components/counters and query/null/own counts for each differing pixel.
No per-path GPU evidence exists in372 full mode; do not invent a differing
sample/depth or ray cause from CPU detail alone. Two missing global proposal
queries cannot automatically be attributed to the shadow-mismatching pixel.

The scan's diagnostic_valid=true means original CPU/global/input identities
replayed and differences localized. Its all_pass remains false, preserving
GPU qualification failure; a valid diagnosis does not admit that backend.
Save all source/input/generated/binary hashes, command, actual PID/start/
resources, terminal exit, stdout/stderr and JSON including on failure.

## Bounds and next action

One explicit step at a time; no native queue. CPU31/nice15/4GiB,
120CPU/180elapsed per compiler/native. No retry/overwrite or GPU acquisition;
observation timeout is not completion. Do not run alongside any scientific
worker. Completed original106 CPU qualification remains the continuation
path; this finite diagnosis does not authorize new GPU tuning iterations.
No power/clock/display/driver/app changes, CUDA, Actions, default Renderer
graph or N001--N009 changes. Unit/regression tests NOT RUN; scientific
post-hoc CPU diagnosis only. Original full artifacts14/17 (one diagnostic-only),
references16/24, direct relative1.0 pixels UNRESOLVED/未解決 and scored,
N010 NOT_READY/no N011. All original quality/physical/state/prefix/intake
requirements remain; no successful Lane M admission follows.
