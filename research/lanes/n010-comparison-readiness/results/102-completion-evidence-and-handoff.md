# N010 completion evidence and Lane M handoff conditions

Snapshot: 2026-10-15 01:08 JST / 2026-10-14 16:08 UTC.
Source checkpoint: `3787a33`. Classification: **NOT READY**, not a final decision.

The [preregistration](../experiments/001-comparison-readiness.md) remains the
completion contract. N010 is the last preparation study; no N011 is planned.
This inventory adds no threshold, scene exclusion or reference admission.

## Actual readiness verification

[103](103-interim-full-gate-preflight.json) executes the existing fail-closed
preflight against recovery view 067, dynamic lock 026 and all declared pilot
inputs. Exit code is 2, classification `NOT_READY`, with 153 recorded input
identities. It is an executed check of current evidence, not GPU acquisition
or a substitute for the eventual final preflight 047.

| Completion requirement | Current evidence | Work still required |
| --- | --- | --- |
| Physically validated, eligible references on all 24 locked transports | Original sampler physical proof [009](009-iid-precision-confirmation.json), cache [022](022-cached-oracle-equivalence.json), exact-prefix [050](050-incremental-oracle-equivalence.json), controlled provenance [051](051-controlled-reference-provenance-audit.json), recovered C2 B2 [080](080-recovered-c2-b2-provenance.json). View 067 currently has 15 statistically eligible slots. 103 fails the full reference gate. | Qualify C1 B8, C2 B8, C3 B8 and C4/C5/C6 B2/B8; verify all payloads, physical states and unchanged convergence screens in final preflight. |
| Correctness diagnostics with every pixel retained | Actual GPU-key [002](002-gpu-key-replay.json), BF-P [007](007-c7-probe-replay-validation.json), all-pixel direct accounting [017](017-comparison-pilot-summary.json); 103 correctness gate PASS. | Keep remaining direct disagreements explicit in final decision and all scores. A CPU-supported mechanism does not constitute a verified GPU repair. |
| Executable first RC/path-tracing cohort and complete quality/memory pilots | Static C7 [013](013-c7-pt-cohort-pilot.json), C1 B2 [031](031-c1-b2-pt-quality-ladder.json), C8/C9 [024](024-c8-pt-quality-ladder.json)/[025](025-c9-pt-quality-ladder.json), controlled dynamic [019](019-controlled-dynamic-cohort.json)/[037](037-controlled-dynamic-pt1024.json). | After eligible references: C1 B8 ladder 043, combined C1 ladder 044 and complete Sponza dynamic cohort 048. Those result files are currently absent. |
| Demonstrated timing capability on actual full Renderer boundaries | Loaded diagnostic sizing [035](035-calibration-observable-sizing.json) is retained; it is not accepted calibration. | Quiet sizing 046 followed by accepted calibration 029 on every required boundary. Both are currently absent. Full raw controls/effects, allocation replay and unchanged gates are mandatory. |
| Named additional GI family and device boundary | Pinned RTXGI source [021](021-ddgi-source-provenance.json), Vulkan host [023](023-ddgi-vulkan-host-build.json), official volume controls [057](057-ddgi-volume-runtime-bringup.json); 103 source/device gate PASS. | Lane M must execute scene tracing/gather, finite-depth transport, dynamic history, memory and full-boundary timing qualification before accepting DDGI comparisons. SDK constant-field success alone is insufficient. |
| Runnable handoff and final publication | Existing continuation and preflight commands below; distinct [Lane M](../../lane-m-gi-competitiveness/README.md). | Final 047 must classify `READY_FOR_LANE_M_FIRST_COHORT`; review actual evidence, publish final N010 decision/index/status/roadmap and commit/push. Lane M hypotheses, tuning split and held-out states must be registered before accepted comparisons. |

The 15-slot count is a snapshot of qualification classifications, not a new
whole-corpus provenance PASS. The first failing C1 B8 reference stops the
preflight's reference loop; 103 does not attest the remaining 23 references.
Other preflight gates execute independently and retain their own reasons.

The Sponza direct-light maximum-relative-error-1.0 pixels remain
**UNRESOLVED / 未解決**. The [primary-tie diagnosis](053-residual-primary-contract-diagnosis.md)
is post-hoc CPU evidence. No mask or repair claim is introduced here. Incumbent
quality FAIL and software topology `UNSUPPORTED_IN_CAPTURE_API` remain reported
comparison outcomes, not reasons to omit a scene or delay until the incumbent wins.

## Current execution and separate acceleration candidate

Two existing CPU qualifiers continue C1 B8 at 65536 spp and C2 B8 at 32768 spp.
Their completed levels remain ineligible; partial seeds do not qualify a level.
The fixed 262144 cap has not yet been executed for these cells. The continuation
at `out/research/n010-comparison-readiness/continuation-v3/status.json` is live,
waiting for eligible references, with all 53 frozen input identities unchanged
at this snapshot. Do not restart it or overwrite its reserved results.

The streamed hybrid is a separate reference-acquisition candidate. Full-frame
deep feasibility [096](096-hybrid-full-frame-deep-conformance.json) PASS is
retained. Numerical suite 098 currently has 13/16 cases passing and its next
case running. Physical 099 and all-state/prefix 101 wait on their required
predecessors; they are **NOT RUN**. Prefix [100](100-hybrid-prefix-build.json)
is build evidence only. This candidate is not admitted and does not change
the live CPU reference chain. Original numerical failure 082 stays failed.

## Runnable final verification

The live `finish_readiness.py` driver already schedules 043, 044, 048, 046,
029 and 047 in dependency order. It refuses retries and changed frozen inputs.
After its final evidence exists, an independent review can run the same
preflight into a **fresh** output path (do not overwrite final 047):

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" \
  out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_comparison_readiness/readiness_preflight.py \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --references out/research/n010-comparison-readiness/reference-view-recovery-v1 \
  --reference-view-record research/lanes/n010-comparison-readiness/results/067-recovery-reference-view.json \
  --calibration research/lanes/n010-comparison-readiness/results/029-full-renderer-calibration.json \
  --dynamic-pilots \
    research/lanes/n010-comparison-readiness/results/019-controlled-dynamic-cohort.json \
    research/lanes/n010-comparison-readiness/results/037-controlled-dynamic-pt1024.json \
    research/lanes/n010-comparison-readiness/results/048-sponza-dynamic-cohort.json \
  --static-pilots \
    research/lanes/n010-comparison-readiness/results/044-c1-complete-pt-quality-ladder.json \
    research/lanes/n010-comparison-readiness/results/013-c7-pt-cohort-pilot.json \
    research/lanes/n010-comparison-readiness/results/024-c8-pt-quality-ladder.json \
    research/lanes/n010-comparison-readiness/results/025-c9-pt-quality-ladder.json \
  --output out/research/n010-comparison-readiness/lane-m-preflight-review-v1.json
```

This command is currently expected to exit 2. The recorded 103 invocation used
these inputs with its own fresh result output path. No new Renderer build or
unit tests were run for this evidence inventory. The preflight re-executed
evidence checks; it did not provide runtime regression validation. No power
settings, GitHub Actions, default Renderer behavior or N001–N009 results changed.
