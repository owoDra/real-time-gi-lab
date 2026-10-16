# N010 cause review and shortest valid completion path

Date: 2026-10-17 JST. This is a **post-hoc synthesis**, not preregistration,
reference admission, accepted timing or a final N010 decision.
N010 remains **NOT_READY**. User requested cause diagnosis and completion,
while limiting interactive load. No stopped job was resumed.

## Actual terminal checkpoint

| Evidence | Actual outcome | Consequence |
| --- | --- | --- |
| [180](180-primary-direction-second-stop-bounded-feasibility.json) | COMPLETE / FAIL, both original feasibility levels; ratios 1.0703554221788882 and 1.0599135470235277 | Direct-only primary guide is rejected. 166 is NOT RUN and cannot consume this chain. |
| [185](185-deferred-image-calibration-sizing.json) | COMPLETE / PASS, all sixteen boundaries, image/scratch/owned-memory/spool checks | Doses are frozen. Full 186 is NOT RUN; accepted timing remains absent. |
| [187](187-nested-scramble-oracle-build.json) | COMPLETE / build PASS only | 188/189/190 have NOT RUN. A built candidate is not a reason to start another long ladder. |
| [191](191-posthoc-readiness-bottleneck-diagnosis.json) | COMPLETE, CPU-only retained-data analysis | Identifies the dominant depth component of C1 replicate disagreement; no new transport samples. |
| [160](160-primary-direction-reference-view.json) | Sixteen eligible references; eight pending | All 24 slots remain required. The pending map does not authorize the rejected guide. |

Immutable result SHA256 identities:

- 180: `f52002b46754152f02ef6111863f7776b5404d2b4673d201b20d4fb253d808ef`
- 185: `58dba169986246adc16898e89f351d6ca1643d6e16a9f247e6934183f3838b32`
- 191: `448a0bd9f36e94dd3b487d7e805073a5efa2286ea281452a76a8b067bfb28f5c`

180's reference screen is INCOMPLETE/ineligible at two levels. Its bounded
feasibility campaign is COMPLETE/FAIL. Neither statement is a measured
262144-spp cap failure. Both native processes returned zero; this is a
scientific failure, not an operational crash. Producer attempts took
2999.5225 and 3099.9844 wall seconds, diagnostic only, at sixteen threads.
185 finished naturally before the subsequent research-worker scan; no claim
that a running GPU job was killed. Current work is small CPU analysis.

## 1. Reference noise: depth mismatch in the improvement target

191 verifies the original C1 B2/B8 scene texts differ only in finite depth,
and hashes each consumed sidecar against its retained qualification. The
original sampler starts a fresh per-sample RNG with the same dimension prefix,
so paired B8 minus B2 means isolate the contribution after the first indirect
bounce, subject to the retained float64 rounding.

| spp | First-indirect centered energy / full | Later-indirect centered energy / full | Later-component pairwise p99 |
| ---: | ---: | ---: | ---: |
| 8192 | 0.0171150 | 0.974696 | 7.10323e-5 |
| 16384 | 0.0128329 | 0.982808 | 4.98612e-5 |
| 32768 | 0.0100156 | 0.986884 | 3.51548e-5 |

These are energies of four replicate-centered mean images, not iid path
variances or population confidence bounds. The full energy is first + later
+ twice covariance; the ratios are not additive variance shares. All covariance
terms and near-machine-precision decomposition residuals are retained in 191.
These sidecar values are not substituted for the original PFM eligibility
screens (which also have float32 rounding).

**Established:** later-bounce contributions dominate the observed C1 replicate
disagreement. The locked material has rho=1, so later throughput has no
reflectance attenuation; this is the intended physical contract, not a reason
to change it. The failed guide scores direct lighting at the first secondary
hit and only changes the first continuation. Its reciprocal density correction
then multiplies every later contribution as well. The guide's target omits
most of the contribution whose disagreement is actually limiting eligibility.

**Not established:** that a particular bounce, rare light path, Sobol
projection, visibility discontinuity or weight distribution is the ultimate
cause; that all eight pending states behave like C1; or that nested scrambling
will improve them. First-direction sampling can affect every later bounce,
so the depth decomposition alone does not prove any first-direction method
must fail. [Plan 057](../experiments/057-bounded-cause-diagnosis-and-critical-path.md)
registers a sixteen-pixel, one-CPU diagnosis to distinguish these mechanisms
before another full-image run. It is explicitly post-hoc and cannot admit a
reference or satisfy the existing nested-scramble proof chain.

### Why simply running longer is a poor next action

Original C1 B8 absolute p99 at 8192/16384/32768/65536 is
7.22177e-5 / 5.03748e-5 / 3.54031e-5 / 2.45194e-5. Its descriptive log-log
decay exponent is 0.518411, close to inverse-square-root decay. Extrapolating
that trend predicts 1.71180e-5 at 131072 and 1.19508e-5 at 262144. The final
two levels must both meet the unchanged 1e-5 absolute gate. A planning model
therefore suggests approximately 0.584 times the original uncertainty at
131072 would be needed. This **is not a new acceptance threshold**, measured
cap failure or guarantee that the extrapolation is accurate. The old <=0.75
feasibility rule remains unchanged and, even if passed, never guaranteed
reference admission. Do not spend days on a ladder solely because that early
screen passes.

## 2. Timing precision: short boundary and acquisition cadence

[169](169-bulk-pfm-calibration-full-renderer.json) completed all 128 blocks /
8192 samples: only the two heavy C1/C6 PT B8 boundaries pass; fourteen fail.
[178](178-hidden-ide-bulk-pfm-calibration-full-renderer.json) retains three
completed failures and one partial boundary plus environment/restoration
failures. [175](175-bulk-pfm-calibration-decision-and-replay.json),
[179](179-hidden-ide-calibration-decision-and-replay.json) and
[183](183-bulk-calibration-precision-posthoc-diagnosis.json) preserve their
original decisions. No subset or historical timing is accepted.

**Established:** failures include control/order bias and effect span, not just
an added-work signal too small to detect. For example, 169 C7 HWRT has control
order bias 1.789 and effect order bias 2.250 versus original 1.02/1.03 limits.
Full workloads at the shortest boundaries are sub-millisecond. Retained
file-output intervals are much longer than timed GPU work. Heavy PT B8 can
pass the precision gates in this same cohort. These observations prioritize
measurement cadence and short-boundary variability over speculative GI
algorithm repairs as the next timing investigation.

**Not established:** causation by output I/O, GPU power/clock transitions,
desktop competition or driver behavior. File timestamps do not measure GPU
idle duration. The reversible IDE accounting result 174 was a local diagnostic
and did not establish global quiescence or repair precision. No settings are
changed now. Deferred serialization build 184 and actual sizing 185 preserve
original images, work and all-owned memory checks, but only actual full 186
can establish its unchanged original precision gates.

185's zero-dose medians imply approximately 4405 seconds of summed GPU work
for a 512-sample-per-boundary full campaign even before effect work, setup,
source preparation, readbacks and CPU output. This is a scale estimate, **not
a completion ETA**. A >hour GPU campaign is not an appropriate automatic next
step while the interactive-load constraint and cause review are in effect.

## 3. Correctness failures are distinct

- Direct zero/reference-positive pixels: CPU [053](053-residual-primary-contract-diagnosis.md)
  and [054](054-primary-tie-cpu-diagnostic.json) support a legacy closest-hit
  tie mechanism selecting a farther surface, changing shadowing or cosine.
  Actual GPU repair is unverified; max-relative-error-1.0 pixels remain
  **UNRESOLVED / 未解決**, included. These few pixels do not explain the large
  measured indirect quality losses.
- The original attempted GPU reference port failed numerical conformance.
  [091](091-deep-path-signed-zero-diagnosis.md) reproduces a signed-zero
  tangent-basis mechanism on the selected traced paths. The separately
  validated hybrid preserves an exact CPU fallback and qualified C4 B2.
  Replacing the independent oracle with an unproved fast GPU port is not a
  valid shortcut; neither diagnosis proves population bias or fixes Renderer.
- Incumbent indirect quality failures (C1/C3/C7 deficits and C9 excess energy)
  remain measured losses. N010 does not require a winning incumbent. Do not
  spend preparation time improving the GI estimator to avoid publishing losses.

## 4. Shortest valid route and decision points

1. **Diagnose cheaply before another variant ladder.** Run only plan 057's
   bounded selected-path comparison. Check reconstruction against actual
   original/180 moments, retain each bounce and correction moment, and separate
   what it establishes from hypotheses. Existing 188/189/190 remain NOT RUN.
2. **Repair the dominant reference mechanism once supported.** Keep all sixteen
   eligible references. A proposed sampler still needs prospective registration,
   original physical/all-state/prefix checks and the unchanged full eight-slot
   ladders. Do not force failed 180 through 166 or reuse stopped sample paths.
3. **Treat timing as its own branch.** Use retained evidence to choose a bounded
   prospective diagnosis before committing to the long full GPU campaign.
   No timing-gate relaxation, subtraction, favorable subset, power/clock change
   or hidden alteration of the full Renderer work boundary is authorized here.
4. **Spend full-image/full-corpus work only after those decisions.** Complete
   all 24 references, quality ladders and dynamic/memory pilots, then actual
   full timing proof and the original six-gate final auditor. Preserve the
   named DDGI source/device boundary and Lane M's separate identity.

The preparation process previously moved from failed sampler to another
candidate without first locating the dominant disagreement. That was an
execution-planning weakness. Existing proof chains remain useful, but more
build/provenance records alone will not resolve the numerical bottleneck.
This review changes work ordering, not the preregistered success criteria.
Completion and a date are not yet guaranteed. No new unit/regression tests,
GPU run, architecture promotion, Actions or N001–N009 result changes occur
in this review. The preliminary 191 import failure and corrected environment
are disclosed in plan 057; the successful read-only diagnosis took <1 second.
