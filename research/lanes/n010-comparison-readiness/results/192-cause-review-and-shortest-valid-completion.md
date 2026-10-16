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
that a running GPU job was killed. That initial checkpoint preceded the completed bounded probes below.

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

1. **Use the completed small diagnostics before another variant ladder.**
   193 reconstructs retained moments exactly; 194 identifies reduced observed
   net variance reduction. Fixed-grid 195 does not supply the required strong
   improvement. Existing 188/189/190 remain NOT RUN. Do not dispatch a full
   nested-scramble campaign on compilation or the selected tail pixels alone.
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
in this initial review. Subsequent bounded GPU probes are recorded below.
The preliminary 191 import failure and corrected environment
are disclosed in plan 057; the successful read-only diagnosis took <1 second.

## Follow-up: completed depth/weight and whole-image interpretation

[193](193-selected-bounce-path-diagnosis.json) actually completed. All six
serial compiler/native steps return zero; original and failed-guide selected
mean/moment fields match retained bytes exactly. One-CPU native durations
are 10.324 / 10.400 / 10.271 seconds. No GPU was used.

[194](194-posthoc-depth-weight-and-rqmc-interpretation.json) distinguishes
selected tails from the fixed grid and adds whole-image moment analysis.
The selected-path guide lowers first-indirect variance and raises later
variance, but **whole-image total per-path variance decreases** to
0.968971 / 0.968757 at 8192/16384, while replicate variance increases to
1.132929 / 1.134818. The observed replicate-variance-to-iid-proxy ratio rises
by 1.169209 / 1.171416. Thus attributing the failure solely to higher total
path variance is contradicted by the whole-image data. Reduced observed
RQMC variance-reduction benefit is also part of the measured failure.
These proxies are descriptive, not RQMC uncertainty estimates or a proof
about all randomizations. Tail pixels selected on original errors must not
be used to proclaim a new sampler better (regression to the mean).

The smallest next reference check uses the existing nested binary on a
prospectively fixed grid, rather than another full-image/proof campaign.
Timing's smallest next check targets the cheap C7 HWRT boundary that failed
all seven original gates, rather than the >hour full 186 campaign. Both are
registered in [058](../experiments/058-fixed-grid-and-short-boundary-diagnostics.md)
with strict diagnostic scope, finite resource guards and no acceptance transfer.


## Follow-up: actual bounded outcomes and naturally idle observation

These are completed diagnostic results, not new reference or timing admission.
Plans 058/059 were committed before their respective acquisitions.

| Result | Actual complete outcome | Decision for the shortest route |
| --- | --- | --- |
| [195](195-fixed-grid-scramble-diagnosis.json) | Exact 193 nested binary, prospective 256-pixel C1 grid, 8192 × four seeds; one low-priority CPU, 164.588 seconds | Nested/original max-pairwise p99 0.948183119, replicate-variance sum 1.018947446, per-path variance sum 1.000469321. No strong gain supports a long campaign. Scope is one grid and one level, not formal 190 FAIL. |
| [196](196-deferred-c7-precision-diagnostic.json) | Eight C7 HWRT blocks / all 512 samples complete; all seven original gates FAIL | Deferred PFM output alone has not repaired short-boundary precision. No full 186. |
| [197](197-natural-idle-c7-precision-diagnostic.json) | Same fresh eight blocks / 512 samples during user-declared idle interval; all seven original gates FAIL | Waiting without operating the PC has not established precision. No repeat-until-PASS loop, sample removal or full 186 dispatch. |
| [198](198-bounded-cause-probes-posthoc-replay.json) | CPU replay of original decisions and all schedules; resource receipts rehashed; owned ledgers and CPU spool receipts replayed | Exact decisions retained. Acquisition image/scratch PASS flags checked; this replay does not independently rehash every native payload. |

Exact new result SHA256 identities:

- 195: `fb8241581d78b70cfc2c6db6e73643021392b051f370472d6c10a58618471733`
- 196: `24833b87c6edfd8e748687ab5f5efc8971bfdb998515f687331f1f7aec6c986f`
- 197: `d07cd05eca73c18e0e9bc0f755e6674d73963f8ff0db2aa2b17def783a79fe71`

196/197 each preserve the full 184 C7 Renderer work, original dose 3439,
046 images, all scratch checks, 30 CPU/30 elapsed second native guards,
all-owned Vulkan peak **263317056 bytes**, teardown zero, and bounded CPU
spool release. Summed measured GPU intervals are **0.252901997 / 0.249035210
seconds**. Host setup, settles, readbacks and output are additional.

| Original precision statistic | Limit | 196 | 197 |
| --- | --- | --- | --- |
| Control envelope | <=1.02 | 1.656799 | 1.567719 |
| Control span | <=1.03 | 1.697616 | 1.892328 |
| Control order bias | <=1.02 | 1.940064 | 1.904106 |
| Effect span | <=1.05 | 2.293783 | 1.807090 |
| Effect order bias | <=1.03 | 2.426973 | 4.486912 |
| Minimum effect-positive fraction | >=0.75 | 0.416667 | 0.5 |
| Minimum effect exceeds control envelope | >envelope | 0.838039: FAIL | 1.031253: FAIL |

197's 384 zero-dose samples range **147.961–956.537 us** at the full GPU
boundary and **2.405–13.746 us** for the fixed neutral-work stage. The work
and output checks pass; the execution-time spread is a separate unresolved
measurement problem, not evidence that the GI estimator suddenly changes
its mathematical work. Static inspection finds these Renderer timestamps
inside one submitted GPU command buffer, with fence waiting/query retrieval
outside that buffer; CPU output is not directly counted as GPU time by these
expressions. This inspection is not proof that the entire measurement system
is correct or that preemption, clocks or contention caused the spread.

197's before/after fdinfo interval is about **13.572 seconds**. Surviving
Brave counters increase by graphics **48.116 ms**, compute **0.562 ms**,
encode **310.011 ms**; IDE counters by graphics **136.032 ms**, compute
**0.146 ms**. These per-engine cumulative deltas must not be summed into a
GPU utilization percentage. Eight same-UID processes are inaccessible; the
short-lived benchmark clients are absent from both snapshots. Coarse
interval activity does **not** establish exact overlap with timed queries,
global GPU idleness, causal interference or a clock/power mechanism. No
application, desktop, display, driver, power or clock setting was changed.

### Supported next work

- **Reference branch:** do not spend another full ladder on a marginal
  scrambling change. The evidence supports targeting later-path uncertainty
  while preserving the exact physical integral. A distinct proposal needs
  prospective registration, independent physical/state/prefix proofs and the
  unchanged eight pending ladders. Strong reduction is still unproved.
- **Timing branch:** inspect an isolated batching/cadence repair that retains
  the complete original Renderer work and maintenance costs. Deferred PFM
  output still performs synchronous GPU readbacks between frames. Avoid
  assuming I/O is the proved cause or changing the measured work boundary.
  Preserve every frame's correctness and owned-memory evidence if readbacks
  are deferred. First use a bounded C7 diagnosis before full sixteen-boundary
  proof; all seven existing precision gates remain required.
- **Completion branch:** keep 16/24 qualified references, all losses, unresolved
  error-1.0 pixels, full-corpus quality/memory work and six final gates visible.
  These negative diagnostics save ungrounded long acquisitions; they do not
  complete N010 or justify a completion date. No N011 or Lane M superiority
  claim is introduced.

198's first invocation used system Python and failed at import because NumPy
was unavailable, before any scientific data was read or output created. The
same retained-data replay completed with the existing research venv and its
required library environment. No new samples or numerical retry were involved.
Unit/runtime regression tests are **NOT RUN**. The default build graph and
N001–N009 results are unchanged; no GitHub Actions were added.
