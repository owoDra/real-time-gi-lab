# N010 bounded history timing preparation and terminal CPU failure

2026-10-18 JST. Recipe135 and sources committed as `6244794a` before
428–430 execution. No new compiler or GPU run. N010 remains **NOT_READY**.

## Environment-sensitive criteria

The user's request to review environment-sensitive decision criteria is
covered prospectively by [amendment120](../experiments/120-reportable-comparison-readiness-amendment.md)
and the [shared protocol](../../../protocol.md). There is no further
threshold change in this record. CPU wall, GPU busy/clocks, other-app load
and global free VRAM are diagnostics. They cannot decide architecture
acceptance. Full Renderer GPU time remains a performance measurement,
conditional on its declared device/workload and registered uncertainty.
A complete valid timing pilot may be INCONCLUSIVE without that outcome
alone blocking handoff; missing or invalid evidence remains incomplete.
Correctness, reference eligibility, quality and owned-memory requirements
remain. A candidate quality loss is a reportable comparison outcome.

Do not pursue idle/stability percentages or repeat until PASS. Retain every
registered sample and use the finite registered stop. Time/dispatch guards
protect operation; a stop leaves an acquisition incomplete, not a measured
intrinsic architecture loss. Actual-boundary calibration and matched-quality
uncertainty rules still apply before accepted speed claims. Current426
implements an intermediate evidence/precision distinction, but the final
selected-history intake and all-split admission adapter are unfinished.

## Actual source preparation and archived CPU replay

[428](428-history-known-work-source-prepare.json) prepares the private
full-history fixture. The whole original host inverse, PT shader bytes,
history/update/seed flow and integer recurrence body are exact. Known work
uses16384 lanes, chunks of at most65536 iterations and131072 additional
persistent owned bytes. Its complete GPU envelope includes the cooperative
gaps. Preparation is not compilation, runtime qualification or timing
admission. Actual CPU/elapsed times were0.044086/0.052519 seconds.

[429](429-retained-neutral-work-full-cpu-replay.json) is post-hoc analysis
of185's archived144 scratch images across16 boundaries. All16384 uint32
words per image match an independent CPU recurrence at doses0,65536 and
262144. Every boundary and sample is retained. CPU/elapsed times were
1.408477/1.518693 seconds, CPU31/nice15/one numerical thread, within
120CPU/180elapsed/2GiB limits. This does not validate the new uncompiled
shader or transfer185's dose response to the current boot/history fixture.

[430](430-history-known-work-build-description.json) records three private
build stages only: known-work shader, host, link. Zero compiler processes
were launched. Original401 flags/libraries and its byte-exact compiled PT
shader are retained in the recipe. Actual431 build and all new known-work
GPU qualification are **NOT RUN**. In particular135's requirement for a
terminal integrity-PASS261 is now unmet; do not launch431 or bypass that
guard. Any future operational amendment must be separately recorded before
execution and cannot waive the physical-control failure.

## Original physical seed ended in a genuine numerical failure

The same original process handle ended with native returncode−6/SIGABRT.
[261](261-wide8-original-a6a-seed2.json) is the exact terminal failure
record; `complete:false` denotes an incomplete scientific seed, not a live
process. Its stdout/stderr/resource partials are retained and hashed.
[433](433-original-a6a-seed2-terminal-failure.json) records the post-hoc
terminal diagnosis; its `complete:true` applies only to that diagnosis.

At A6a pixel(96,77), four-vertex split3, the original check compares sampled
log density16.299489357790691 with reconstructed16.299490368089238.
Absolute difference1.0102985470439307e-6 exceeds the unchanged1e-6 bound.
The uncaught `own-family area-density mismatch` exception directly explains
termination. CPU4369.726179/elapsed4552.480710 seconds remained within the
registered7200CPU/10800elapsed limits. This is not an idle/stability
criterion or a timeout. Do not relabel it TIMING_INCONCLUSIVE.

One raw segment is about1.06856e-8 long. Its numerical conditioning is a
hypothesis, not an established root cause. The original log did not capture
the sample index; no focused reproduction, repair or retry has run. Do not
relax the density threshold, discard the seed or queue the next seed.
The next physical task is a separately registered, bounded CPU diagnostic
of this pixel using the pinned original source and exact seed, before a
repair or further full-seed acquisition. No new diagnostic is executed here.

## Remaining work and scope

The verified inventories remain16/24 eligible references and14/17 physical
artifacts including one diagnostic-only item. A6a has two of four original
seeds complete; seed2 failed and seed3 is not acquired. No new reference is
admitted. Full physical/reference proof, missing Sponza/static/dynamic
evidence, selected-history timing qualification/intake and final audit remain.
Reuse415/423's retained quality evidence rather than duplicating it.
Sponza direct maximum relative-error1.0 pixels remain **UNRESOLVED / 未解決**,
included. Finish N010 before distinct Lane M; no N011 or superiority claim.

Build, unit/regression/default-build and new runtime smoke checks: **NOT RUN**.
Source inverse checks and the archived CPU scientific replay are distinct
from those checks. No default build graph, N001–N009 result, Actions, CUDA,
power/clock/display/driver or other-app setting was changed. No next seed,
compiler or GPU task was automatically queued.

Publication metadata checks:8 configured lane indexes/337 declared result
links resolve. All1619 declared input/payload hash entries across261,
428–430 and433 match1140 unique files. `git diff --check` is clean.
These checks are not runtime regression validation.
