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


## Completed implementation probes: packed readback and later-bounce correction

[Plan 060](../experiments/060-packed-readback-cadence-diagnosis.md) produces
actual build [199](199-packed-readback-fixture-build.json), C7 sizing
[200](200-packed-readback-c7-sizing.json), and eight-block precision
[201](201-packed-readback-c7-precision-diagnostic.json). Four separate
synchronous diagnostic downloads are replaced with four copies after the
original stamp(15) in the same command buffer, followed by the original
fence wait. CPU scratch and RGBA spools preserve all original output bytes.
The default Renderer and PT/dense-RC fixture are unchanged. This is a narrow
timing repair prototype, not a complete cohort fixture or accepted timing.

199's whole-source inverse guards pass; the original timed GPU recording and
time expressions are byte-identical. The three serial compile/link steps
return zero in 6.461 / 2.646 / 0.057 seconds on one CPU at nice 15. Actual
200 sizing PASS freezes dose 3500 by the original three-dose/+20% rule.
201 completes all eight blocks and 512 samples, but all seven original
precision gates FAIL: control envelope 1.733625, span 1.773053, order bias
1.691504; effect span 1.419234, order bias 1.451815, minimum positive fraction
0.666667, minimum effect 1.210181 below control envelope. No thresholds change.

Every image equals 046, scratch checks pass, owned Vulkan peak is 263382656
bytes and teardown zero, bounded CPU RGBA/scratch spools release all records.
Summed timed GPU work is 0.303380 seconds. Zero-dose full times range
156.177–987.717 us and neutral stage 1.202–79.271 us. Coalescing readbacks
alone is insufficient; the candidate stops. These uncontrolled campaigns do
not establish how much of the variation is caused by downloads. The remaining
per-frame submit/fence/query cycle is not removed and may still matter.
A complete contiguous-frame implementation would need per-frame parameter,
query and captured-buffer identities, every frame's correctness and all
owned memory, with unchanged original workload and precision gates.

[Plan 061](../experiments/061-later-bounce-control-variate-diagnosis.md) and
[202](202-later-bounce-cv-path-diagnosis.json) target later transport directly:
a fixed 4x4 cosine-square midpoint predictor adds a conditionally zero-mean
correction after later vertices, preserving the original cosine sample mapping
and every original path contribution. The prototype separately retains both
original and corrected estimates. All 32 original mean/second-moment records
are bit-exact to 193. Compiler/native return zero, 1.916 / 67.572 seconds,
one CPU at nice 15, 4 GiB address-space / 220 CPU / 300 elapsed bounds.

On the eight prospectively fixed C1 pixels, corrected/original p99 ratio is
0.837924133, replicate variance 1.054490032 and descriptive per-path variance
1.032952174. No corrected indirect mean is negative. The preregistered
promising rule requires p99 <=0.75 and replicate variance <=0.75^2; it FAILS.
The fixed prototype stops without parameter tuning, full controls or a ladder.
This eight-pixel diagnostic does not rank whole-frame/corpus performance or
reject all control variates. It does show this coarse direct-light predictor
does not provide the required reduction in the measured later-path uncertainty.

New exact result SHA256:

- 199: `7780bec0e9e2ec7f6da930a9b81fad01384e3620c5e39091f9a838e2c68dc108`
- 200: `174f9f5439853b7c0339a6e82a17edd6c3ac80e00bc21733ae1e24f714eacb76`
- 201: `d11d11e81ff8b2aad1cbef9e084036e2badd3c2fc989d1b3514b967691995796`
- 202: `58f75c7606a5553c4e409c3c5375cc9b8c9d2ec3a2639a5b4817cc8390af9fea`

The 202 tool session handle expired after sampling, but the retained native
PID/start identity is absent and the authoritative result records complete
native termination (return code zero) with all 32 outputs. No calculation was
restarted because observation failed. No research worker remains after the
recorded termination. Unit/runtime regression tests remain NOT RUN. N010 is
still NOT_READY with all original reference, timing and final requirements.


## Array-RQMC follow-up: preserve the negative result

[062](../experiments/062-array-rqmc-transport-diagnosis.md) registers a
geometry-only normal-octant/Morton sorting and per-transition randomized
3D Sobol assignment. [203](203-array-rqmc-transport-diagnosis.json) completes
one compiler and one native invocation in 2.164 / 24.206 seconds, one CPU at
nice 15, 4 GiB / 220 CPU / 300 elapsed guards. Its exact SHA256 is
`9cb28aa598201b593a53c0e0d58e08f0a352f44008a4615c82a52881bd31515a`.

The prototype replays assigned prefixes through the original physical body,
with optional stop/vertex exports. All 32 original means/second moments are
bit-exact to 193; all first-indirect luma means and deterministic components
also match exactly. It uses no weights, correction, extra scored camera
samples, radiance-defined sorting or clamping. Prefix replays are real extra
CPU cost and are explicitly retained. This is not an efficient production
reference implementation.

On the same eight fixed C1 pixels, array/original paired-p99 ratio is
**1.049287102**, replicate variance **0.885353909**, descriptive per-path
variance **0.994756569**. Thus smaller replicate variance does not imply the
required tail-error reduction. The original prospective promising rule FAILS;
this fixed sort/assignment stops. Do not tune its key or dispatch another
level/full corpus from this result. No larger-level prefix was proved.

The institutional [2009](https://www.gerad.ca/en/papers/G-2009-03) and
[2016](https://www.gerad.ca/en/papers/G-2016-61) Array-RQMC abstracts motivate
per-step sorting/randomization; they do not establish success on this geometry.
The author PDF requests returned access-denied pages, so no full-paper-reading
claim is made. This negative prototype does not reject all array-RQMC methods
or prove a population variance bound.

Post-hoc CPU verification replays 201's exact original analysis, all 512
schedule tags, eight owned-memory ledgers and eight native resource receipts.
It rehashes all generated 202/203 payloads and confirms their recorded native
PID/start identities are no longer present. No GPU work or regression tests
were dispatched by that verification. This is not an independent rehash of
all 201 native payload files, which were checked during acquisition.

### Remaining prerequisite boundary, without adding unnecessary repairs

The original correctness gate explicitly permits **measured and included**
remaining direct discrepancies (readiness_preflight.py, correctness gate).
Actual key/BF-P validation is distinct from proving a new GPU primary repair.
Do not make an unrequested winning-incumbent or complete direct-pixel repair
another prerequisite for comparison: retain the measured max-relative-error
1.0 pixels as UNRESOLVED / 未解決 and include them in scoring. All required
key/BF-P validations and explicit discrepancy records still have to verify.

The main unfinished prerequisites remain (a) eight pending eligible references
under the unchanged screen and (b) all sixteen complete Renderer boundaries
under the unchanged precision gates. Whole-corpus quality/true-peak pilots,
fixed quality selection, additional-family provenance and the final original
six-gate auditor are still required afterwards. 199–203 improve executable
cause diagnosis and reject unsupported dispatches, not readiness. No long
acquisition, default promotion, N011 or threshold change is substituted for
those requirements.


## Contiguous C7 submission: completed evidence, not precision admission

Plans 063–065 and results 204–208 implement one original frame stream with
per-frame parameters, query ranges and output copies, in one submit/fence
wait per block. The original commands through stamp15 and timing expressions
are byte-identical. Uniform descriptors alone become dynamic descriptors,
with actual device alignment4, stride4096, range128; all frame IDs are verified.
The inter-frame full memory dependency and diagnostic copies are outside the
scored timestamps. No extra warmup/scientific frames, averaging or power change.
This is static C7 only, not a full-corpus or dynamic implementation.

204's compiler caught an omitted target_state helper argument; 205 retains
that repair and catches a generated relative include resolving historical
standalone Lane B instead of the pinned imported header. Both terminate with
no GPU work and remain immutable. 206 explicitly selects the original pinned
header and completes runtime/capture/compute/link in 5.965 / 2.525 / 0.524 /
0.057 seconds, each one CPU nice15, original 8GiB/120CPU/300elapsed guards.
Original headers, default build and N001–N009 remain byte-unchanged.

207 sizing completes 9 scheduled frames and freezes dose1342, original rule.
208 completes all 8x64 scheduled frames, 8 single frame-batch submits and waits,
all frame/query/uniform identities, original 046 image hashes, neutral-scratch
verification, CPU spool receipts and owned-memory replay. Each native process
has an actual receipt for CPU30/elapsed30, one CPU nice15. All ledgers return
zero at teardown. Summed measured full GPU intervals are 0.082507846 seconds;
zero-dose min/median/max 131.249375 / 141.108107 / 419.156402 us. Batch CPU
wall includes recording/submission; cached per-frame calls are not independent
frame execution costs. Initial resource uploads and diagnostic copies remain
additional work, not hidden inside a single-submit-lifetime claim.

| Original precision gate | Observed | Decision |
| --- | ---: | --- |
| Control absolute envelope <=1.02 | 1.030658426 | FAIL |
| Control span <=1.03 | 1.046921226 | FAIL |
| Control AB/BA bias <=1.02 | 1.078221697 | FAIL |
| Effect span <=1.05 | 1.027634048 | PASS |
| Effect AB/BA bias <=1.03 | 1.033715157 | FAIL |
| Minimum positive fraction >=0.75 | 0.916666667 | PASS |
| Minimum effect > control envelope | 1.193435139 > 1.030658426 | PASS |

Overall **COMPLETE / FAIL**. The candidate stops. Three passing component
gates do not override the four failures or authorize accepted timing. Earlier
201 has 0/7 passing gates, but differing dose/cadence/natural environment do
not establish a causal effect size or identify clock/app interference. No
full campaign is started. References remain16/24, no readiness claim.

Post-hoc CPU verification recomputes the exact original C.analysis, every
512 schedule tag, all eight owned ledgers and actual native receipts, and
**every retained native payload hash** for 208. Recorded native PID/start
identities are absent. No GPU dispatch or unit/regression tests in replay.
All plans and failed records remain; no settings/apps were changed.

Exact terminal result SHA256:

- 204: `d6af20614355724f086a193f291636a8cd5209c9a2a7da8f9c29989f41f59d90`
- 205: `b969168cfca2dabe6b58df97d7fbc065ae45373fbe106af111b5689559a2e17d`
- 206: `01ecd757d296e97e2d724b01547603d1cb5a9eabbddcd7b0e7437b3ad132f5a1`
- 207: `ce208b43b004cdd90be55d37764fedf84991e8819f038058a3d8cee2c5f41a8c`
- 208: `6341ee46e8e744495dd48bdb6b115fbfb51d0f0178dc904253a6fb6498cde318`


## Frozen full-suffix predictor: no qualifying reduction

Plan066/result209 address a distinct limitation of 202: predicting the entire
remaining finite suffix instead of the next direct contribution. A separate
fixed pilot (seed0x50494c4f5431, 65536 paths on the same eight fixed pixels)
trains an 8^3 world-grid / normal-octant / remaining-depth table with sixteen
cosine-square bins and fixed pseudocount32. Its exactly integrated table mean
minus the selected-bin value is added as a separate correction. Original
path contributions and sample map remain untouched; the auxiliary training
cost is explicit, not counted as scored reference samples.

209 completes compile/native in 1.767 / 6.389 seconds, actual one CPU nice15,
4GiB/220CPU/300elapsed guards. All32 original mean/second-moment records are
bit-exact to193, as are deterministic components. No negative corrected means.
Frozen model dumps are byte-identical before/after scoring. Pilot contains
358120 reached continuations,6902 visited state keys,69509 nonempty directional
cells. No scored values fit the model. This is not reference admission or an
independent proof of conditional RQMC/finite-hash behavior.

Corrected/original paired-p99 ratio **0.947268365**, replicate-variance ratio
**1.033001634**, descriptive per-path variance ratio **0.975723868**. The
original prospective promising rule FAILS. This fixed model/grid/prior/pilot
stops without tuning or a larger-level dispatch. Small path-variance reduction
again does not establish reduced four-replicate disagreement. This does not
reject all full-suffix predictors or establish corpus/cap behavior.

Post-hoc CPU replay rehashes every209 immutable input/generated payload,
verifies actual native termination and the identical frozen dumps, and
reconciles every table visit with its global count. The largest stored-table
floating residual in the sixteen-cell conditional correction mean is
1.0842021724855044e-19. This finite table check is not an all-state/physical or
cross-replicate independence validation. Unit/regression tests remain NOT RUN.
Exact209 SHA256: `0ad479ef2dd2ffe7ba38dcd291cc93a29fe963416f878796cee2dd78b37a1bc2`.

### Current scope of the remaining work

The bounded diagnoses reject these fixed repairs; they do not prove that a
full original reference ladder has failed at its cap. Nor do they establish a
method that will complete all eight pending slots. Do not extend a failed
local predictor into expensive whole-frame runs. A future reference candidate
must target whole-path transport with a derived matching density or a stronger
integrable surrogate, then pass the same independent physical/state/prefix
and full-frame feasibility gates. That is remaining research, not a completed
implementation or a promised completion date. Timing208 remains an independent
FAIL; other full-boundary implementations/precision and original final gates
are still required. No worker or delayed dispatch remains.


## Whole-path mixture: numerical support must be repaired before feasibility

Plan067 derives a raw-hit-area path integral for the fixed rho1 point-lit
C1 prototype. Family E generates forward cosine paths; family L starts at the
light and reverses prefixes. The same original point-direct target is used,
including N001 soft falloff and original canonical shading spawns. Forward
and reverse generative densities are evaluated separately; no reciprocity,
reciprocal-square radiance substitution or repeated per-bounce correction is
assumed. The original physical sample body is unchanged; whole-source inverses
and all inputs are retained. This is a restricted prototype, not full PBRT BDPT.

210 compiles in1.973s, then native aborts in3.378s at the raw-target geometric
reconstruction guard. It remains INCOMPLETE. Partial rows are not a completed
32-record diagnostic, a variance FAIL, reference eligibility or cap evidence.
Plan068/211 reproduces the identical guard without changing it, compile/native
2.037/3.352s, and records the precise original geometry before the same abort.
Decimal80 arithmetic on recorded binary64 coordinates gives:

- abs(normal dot unit direction)0.00028386281198589516;
- condition number3522.828485365984;
- stored target signed plane residual5.726400733464768e-14;
- ideal line-plane to target distance2.693020242080077e-10;
- actual to target distance2.977577705144710e-10;
- original unconditioned bound2.082746319999676e-10;
- actual to ideal line-plane distance2.845574881781110e-11.

Thus the first numerical guard can reject even the high-precision geometric
intersection; this does not prove a transport-density bias. Plan069 explicitly
**changes that diagnostic guard**, prospectively, to geometric backward error:
retain original scale B; require target/actual plane residuals<=B and
|actual-target|*abs(N dot direction)<=B. It preserves and separately reports
unconditioned error/B. No projection, sample removal, changed physical body,
scientific threshold or old-record rewrite. The inclusion inverse proves only
the declared numeric audit/reporting differs. Own log-density<=1e-6 remains.
This audit is not a proof of unbiased finite-arithmetic transport.

212 compile/native1.928/18.716s ends at a **different unchanged guard**:
generated own-family path has zero reconstructed density. It remains
INCOMPLETE, with no promising-rule conclusion. Plan070/213 reproduces the
same abort. The first failure is light-family C1 pixel(200,150),prefix5;
steps0–3 retain their IDs, step4 expects59258 and returns59011. Both triangles
lie exactly on x=-1086.4200439453125; their overlapping interiors contain
recorded point(-1086.4200439453125,937.5586958317924,-117.97109649398705).
Independent Decimal80 barycentric minima are0.07295981164 and0.07482003880:
this witness is inside both triangles, not a shared-edge-only ambiguity.

Plan071/214 loads the original full scene and byte-identical193 original
header. It calls the original nudge_inside, offset and cosine_sample, without
new sampled paths. Both primitives have material0, two-sided rho1/emission0.
Nudge and spawn bit patterns match exactly at this point. Spawn is behind
their common plane in the incoming direction and is4.637058736989275e-9
on the outgoing hemisphere side; original offset4.636979505308799e-9.
But face-forward normal.x is-0.9999999999999999 vs-1, and one fixed mapped
cosine direction differs by1 ULP. Numeric normal equality is **false**. Thus
neither exact operator identity nor primitive-tag interchangeability has been
proved. Do not hide this by renaming IDs, merging geometry or dropping paths.
The geometric plane is behind ideal positive-cosine outgoing rays; that
observation is not an exhaustive finite-arithmetic BVH self-ignore proof.

The concrete next issue is path-density matching for coincident geometric
surfaces while preserving canonical numeric operators and self-ignore behavior.
Any repair must be prospectively specified, preserve all points/failed runs,
and receive independent physical/normalization/state/prefix validation before
full-frame feasibility. It may fail the original promising rule afterwards;
current partials cannot answer that question. No statistical threshold, seed,
cap, corpus or N008 physical definition is changed. No GPU direct repair or
N010 readiness is established by these CPU witnesses.

All work is one CPU nice15 with4GiB and finite per-process time bounds. CPU
replay rehashes every immutable input/generated payload for211/213/214 and
confirms their actual PID/start identities terminated. The211 input manifest
preserves every210 generated/partial file;213 likewise preserves all212 bytes.
No GPU, unit/regression tests, settings change or retained scientific worker.
Exact terminal result SHA256:

- 210: `abcf6336a4310d36e6894467fab1b12484383e09aa8adc4d5b562fe588dae64e`
- 211: `d33b15c3d481f2685b171a7aa2bb7f33761513ef1c81f4e5648c934aeec9ee95`
- 212: `11713aca61ef3fd15d312a562e0d60a2e1cb04c73f4311ba97ffcf38790341ad`
- 213: `e277ae8a4893d0d8f39dbe5b44d9e78227c87f0d354490c1de1a47a735d17be7`
- 214: `df8828a3eadd1f9cb69272509d9e58d207d73aacc1ae158180be21672535279c`


## All-split path sampler: first bounded promising result and derived furnace control

The latest current findings and remaining admission obligations are recorded
above the historical checkpoint in status/roadmap/README. This section retains
the detailed new215–221 evidence; no prior terminal record is rewritten.

Plans072/074 explicitly amend prototype numerical support matching, not the
scientific thresholds. 215 is INCOMPLETE at own-support, native24.838s; its
large opposite-family unmatched log is retained, not converted into a variance
verdict. 216 reuses original operators at the last logged pair59259/59010 on
x=-1086.4200439453125. Projected barycentrics are strictly interior on both;
normal numeric/spawn/nudge/material equal, but signed-zero normal.z branches
and mapped tangent directions differ. It locates a rejected candidate pair,
not the complete failing own-prefix. For exact unit axis normals the two
Duff frames differ by(t,s)->(-t,-s), an azimuth pi rotation. Uniform azimuth
and thus cosine density are unchanged. 074 removes only that basis-sign
predicate; no original mapped sample is replaced. All other restricted
plane/interior/material/nudge/spawn/offset/normal, alternative-self and own
log-density guards remain. This numerical approximation still needs physical
bias assessment; it is not exact finite-arithmetic transport equivalence.

217 completes: p99 ratio0.8458802216130148, replicate variance0.8194006481790704,
path variance1.3902094299824768. Original promising rule FAIL; fixed half-eye/
half-light stops. 218 is a structurally different all-split construction.
For each k, s uniform0..k, e=k-s eye vertices and s light vertices; join the
raw eye prefix with reversed raw light prefix. q_j=E(prefix k-j)*L(reverse
suffix j), q_mix=sum_j(q_j)/(k+1). The target F=q_0*R_k uses original forward
point-direct physics. Thus weight=(k+1)*q_0/sum(q_j)<=k+1. Ordered canonical
spawns/normal/visibility/range are evaluated separately; no reciprocity.
One uniform coordinate selects and remaps the strategy, the original first2k
of14 net dimensions generate its vertices; reuse across depths does not
change the integral sum. Up to28 vertices/scored index is explicit extra cost.

218 completes all32 records on the eight original fixed C1 pixels,8192/four
original seeds. Original193 means/second moments and deterministic components
are bit-exact. Strategy selection counts have exact floor/ceil stratification;
all generated non-null own products reconstruct within1e-6 log error.
Ratios: p99 **0.7017963067378328**, replicate variance **0.5074178675470417**,
path variance **0.8308178798828323**. Original two-gate promising rule PASS.
This is selected one-level reference-sampler evidence, not corpus admission,
measured cap feasibility, equal-cost performance, or an incumbent GI win.

219 preserves an original Xoshiro constructor compile error, native NOT RUN.
077 changes only the driver to actual(seed,pixel,index), including per-index
iid stream boundaries; no data-driven threshold change. 220 reuses218's exact
header, all original A6a geometry/camera/falloff/bounces/light, changing only
rho0.5 to rho1 for a derived control. Eight other prospectively fixed pixels,
original four seeds,8192 net and16384 original iid samples. Unit sphere target
is1/pi for B2 and7/pi for B8. Finite mesh allowance is independently derived
from minimum facet distance and maximum vertex radius, including original
offset plus1024epsilon margin; original A6 .002 target allowance is retained.
All four analytic checks and both iid comparator checks pass. Global mean
relative differences B2/B8 **6.044807454363976e-6 / 4.138105199613662e-6**;
NRMSE **4.575118814680136e-5 / 1.2831637533379166e-5**. All zero-intensity
controls exactly zero. This derived eight-pixel result is not a PASS of all
seventeen original applicable physical controls or general materials/sidedness.

221 is post-hoc, no native sampling. On one low-priority CPU it independently
rehashes98 immutable input/generated payloads, checks11 actual compiler/native
PID/start identities are terminal, inverts the physical headers, checks exact
original moments/deterministic bits and recomputes217/218 and220 decisions.
All replay exactly. 218 audit coverage: five coincident matches, zero following
alternative-self ray checks, one alternative-self direct check. Maximum normal
difference1.1102230246251565e-16, own-log error1.1189378312792542e-9, conditioned
backward-error fraction0.6358539612193481. Critically, maximum UNCONDITIONED
reconstruction-error/B is **14108638923.233318** (217:616576777.438203).
Near-parallel amplification is not bounded spatially by the conditioned
plane check. Do not describe all reconstructed points as spatially identical,
claim exhaustive self-ignore coverage, or infer a Sponza physical bias bound
from the sphere result. Those are remaining numerical/physical obligations.

Next concrete work: integrate physically correct general material/sidedness/
finite-depth target factors (the current rho1 eight-bounce prototype is not
yet a full original-control adapter), validate the full original physical
suite and density/numerical approximation, then all-state/prefix and whole-frame
two-level feasibility. Positive small triage does not authorize qualification.
All24 slots/four seeds/six levels/cap/consecutive support1e-5/5% gates remain.
References16/24;208 timingFAIL and remaining quality/true-peak/full-boundary
pilots remain separate work. Direct max-relative-error1.0 pixels UNRESOLVED/
未解決 and included. No GPU/settings/display/default-build/Actions/historical
result changes; no scientific worker or automatic acquisition queue remains.
Unit/regression tests NOT RUN; no claim of N010 READY or Lane M superiority.

Exact terminal record SHA256:

- 215: `f0a9b3797f0c51be30cd082cea410b5974d3b98b4053dce07c90d788c5846152`
- 216: `c7d5395462c10ee06bb597fecae2a96585dda3d14ac42b50ea2b04488a36cd03`
- 217: `8f00fa4a820a1f4dc12cbcad696894a539ac3a237540f1daae3a949f746f50d4`
- 218: `5ca6c3a278ac1b79673e5b6622d7a6d7fb0832473faeae0a0a990c4d6261ddb3`
- 219: `06edcbb4144a89c81676f19f37ee3ff13bacdb3e91da592d12fa84b8ae9acfe7`
- 220: `e1ea2c33e62e562395b60ac893d90e2cf83a1822bfe927f739952c7a5cc8b996`
- 221: `7d175550bb5bd554e044fed0b1611b99793e6835e46103f03d6da3e522f548af`


## General target adapter, ten original full controls, and the live A6c run

078 derives the actual RGB material product and one-sided absorption target,
with per-order cumulative density reuse and original physical methods intact.
222 preserves a misplaced closing-brace compile failure; scope-only079/223
completes all262144 legacy/new C1 RGB/depth bit comparisons. Accumulated218
means/second/depth fields are exact. The paired native82.398s includes legacy
and new work; it is not an independent new-sampler speed estimate. 224 builds
the original-format single-thread exporter, preserving original writer and
physical source via inverses, explicit auxiliary primary-cache primes and
unchanged scored RNG. Default Renderer/CMake/shaders are untouched.

225/226 complete nine original full128x96/64spp/four-seed controls. Every
f64/PFM/hit payload equals original bytes, no mask. Shadow-work count
comparisons are scoped:225's direct/absorbed controls match all integer counts;
226 primary-hit/absorption counts match while extra sampled endpoint shadows
remain descriptive. No variance or convergence inference from zero indirect.

227 retains a COST-pilot guard failure comparing64- and8192-sample rounded
deterministic accumulations. 228 NOT RUN. Prospectively083 adds original
same-count64 baseline, without changing accuracy/cost gates. 229 passes;
the distinct230 full8192 original A7 acquisition completes but its analysis
metadata omitted geometry_hash_match and raises KeyError. 230 is sealed as
terminal analysis failure with raw outputs complete and exact unsealed crash
snapshot. Its process elapsed/childCPU were NOT RETAINED before the exception;
no invented timings/exit receipt and no native rerun. 084/231 replays that same
full data, adding the hash predicate through independent original authored
scene identity. All original analytic and full iid16384 gates PASS. Indirect
analytic per-channel region relative error1.0425099784e-5,NRMSE0.000444196791;
iid relative difference9.3568489428e-5,NRMSE0.007144046945. All original
same-count deterministic mean/second fields and primary hits are byte-exact.
This is full original RGB B2 A7 validation, not the entire physical suite.

233 independently rehashes718 immutable payloads, confirms18 old compiler/
native PID/start identities terminal, compares all original/retained fields,
and inventories10of17 original full controls. Its first inventory incorrectly
included022's three corpus checkpoints along with17 control scenes; it stopped
without a result, then selects the exact original17 control metadata assets.
This is an explicit post-hoc catalog correction, not a scientific gate change.
Pending: A6a,A6b,A6b_level5_diag,A6c,A10,sealed-dark,sealed-lit. Numerical bias,
A6b independent iid, full all-state/prefix and whole-frame two-level feasibility
still precede qualification. No reference admission or full-suite PASS.

085/232 costs original full-frame A6c at8spp/fourseeds:1.898731CPU and
1.910170elapsed sec;8192 conservative scaling1944.300544CPU/1956.014465elapsed
(~32.6min), not an ETA or physical result. Same-count inter-seed deterministic
bits, original primary geometry, finite/proposal audits pass, no quality score.
086 prospectively registers ONE original full A6c8192/fourseed/whole-frame
acquisition234, same224 binary and original scientific gates, oneCPU nice15,
4GiB/3600CPU/5400elapsed. No retry or automatic subsequent-control queue.

**234 is currently RUNNING, not a result.** Native PID69782/start473962 was
verified live at2026-10-17T04:40:30UTC; tool session78104. Source601db86.
Resume by polling that exact handle/identity and inspecting terminal234; a
poll timeout never justifies a new acquisition. The complete native receipt
must be saved before analytic parsing. No GPU or settings/app/display/clock/
power changes. Reference eligibility16/24,timing208FAIL,error1.0UNRESOLVED/
未解決 included; all original final requirements remain. Unit/regression tests
NOT RUN. N010 NOT_READY; no Lane M comparative superiority is claimed.

Exact terminal record SHA256 (234 is mutable acquisition state, excluded):

- 222: `62449c632f305b6740a04d0fff97c5cebd155b255c11d992719dd9553655ea89`
- 223: `2f5c516468153b1aea04021530c10eaca0b1c89dfc50045a40f688ddb6def1c7`
- 224: `56bb79b683fffe5c8b30d12626939aa6b86d8d3cf85dfe724d7afc2937a5b0b6`
- 225: `f4de1c124fa6cba6412d4a1471be4f488144fd1d3c26de20ef4330b6c236f777`
- 226: `3868f2d80d1860074c6c7f84ee8576b7d7a88b2f52900a44fea9054183e5d8c8`
- 227: `f3edaef1a4f293064083bc64c497f4eb78e04d0d2661c38c715e53fdcbfc86b6`
- 228: `d67fbb2696eb09667f6f537aad8f20c8f6e5f7fa293df90379d6ee2c9caa710b`
- 229: `61b7aa722fc3f2256be78cbaa376b3993f8b1be4f5519a21557d3e26d4fde996`
- 230: `42b656a47a490e7df85d145d9aed3930a29ac0f138485ed5c38a9c128f26812b`
- 231: `4ca006c299fda61accc6e78eee7b3a5dba543f4f505ecf2f2ed5dcc3fb26051e`
- 232: `e493feffc868477258d284efc0b081fe2af065b6112bca392b17c89ab13e4e7d`
- 233: `842de54fc3af69ad403545cee00fd4ccb70bfc92eeac3a8ecc295ef0eed34615`


## User-declared idle read-only observation while A6c continues

235 is explicitly post-hoc, read-only and separate from original natural-idle
197. The latest “now” answer was honored with seven DRM-accounting snapshots
over30.156964s; no concurrent scientific acquisition or GPU load was started
under086. Brave surviving-client increments: gfx98,479,386ns,compute937,102ns,
enc631,024,838ns. IDE: gfx36,104,708ns,compute530,143ns. Eight same-UID
processes are inaccessible in every snapshot. Counter increments establish
activity over this coarse interval, not per-query interference, global
quiescence, clock behavior or causality. Full paired precision remains NOT RUN
for this observation. No samples or apps were removed; settings/display/clock/
power unchanged. A6c PID69782/start473962 remains the same live acquisition.

Raw observation SHA256: `71ec68bd9e5b370d6fa4e4a3ea56cc294adf66c5d9cbb3c598e00c32e3d368ba`.

Exact terminal235 SHA256: `f7d572d66a56a97147b5994404b6f8f6a44e5a02e12be1468f9b906761579aad`.


## Preparation of the next cost decision (NOT RUN)

087 and size_all_split_remaining_controls.py prepare a six-scene,8spp,
whole128x96,four-original-seed cost inventory on unchanged224. It refuses
live/failed234 and any concurrent research worker before creating output.
One native at a time,oneCPU nice15,4GiB;90CPU/120elapsed per native within
180CPU/240elapsed total native budgets. Record native terminal evidence before
analysis, including timeout resource deltas. Original physical counts remain
8192/8192/256/8192/1024/1024; no quality claim, changed threshold, independent
IID substitute or automatic full queue.236 does not exist until acquisition.
The controller is prepared but NOT RUN; no unit/regression tests were run.
This avoids committing an unmeasured multi-bounce full workload while A6c
still runs. A6b_level5_diag is diagnostic only in the original control law;
its presence in the17-scene artifact inventory does not create a new gate.


## Terminal A6c native, analysis-only metadata failure

234 native returned0:1331.127171410elapsed/1325.210989000CPU sec, all25
payload identities retained BEFORE analysis. Its Python summary then raises
KeyError run_counters. Both original native and controlling process are
terminal. Preserve234 exactly.088 registers an explicitly post-hoc analysis
replay237 with only that metadata field supplied from actual integer counters;
original analytic/identity/proposal checks stay identical. No native rerun.
Original087/236 remains NOT RUN and refuses failed234; a separate dispatch
amendment is needed after successful237. No current physical verdict.

Terminal234 SHA256: `3d9ac259909cd1ec796623233d54c6a7dba821e10bf80dc85a1980ecb7878a9b`.


## Same A6c analytic replay PASS and prospective cost dispatch

237 rehashes234 inputs/all25 outputs, confirms native terminal identity and
resource receipts, then replays the exact original analysis with only actual
run_counters inserted; inverse exact. No native rerun or input rewrite. Direct
facet allowance violations0; indirect max region-relative8.1611197802e-5,
NRMSE0.00138358751045, original gates PASS. Full inventory11/17; remaining
A6a,A6b,A6b_level5_diag,A10,sealed-dark/lit and required A6b IID unchanged.
089 changes only087 controller prerequisite filename234 ->237, preserving
the original driver hash and original cost/native/stop/scientific guards.
No full queue.236 has not yet been acquired at this checkpoint.

Terminal237 SHA256: `ff30d739737318fd534742e4b7c56adf01f820bcfa5430e0a89d6fe3be58aabf`.


## All six original-scene cost probes complete; execution scalability

236 completed six original128x96/four-seed/eight-sample probes serially with
175.253736CPU/176.120783171elapsed sec. All source/primary/finite/deterministic
inter-seed/proposal guards pass; all six native PID/start identities terminal.
Inputs211,payloads144 retained. These are NOT the original full controls.

| Original scene | Actual pilot CPU sec | Linear original-count CPU hours |
| --- | ---: | ---: |
| A6a | 42.641725 | 12.129202 |
| A6b | 42.653570 | 12.132571 |
| A6b_level5_diag | 36.899459 | 0.327995 |
| A10 | 42.220372 | 12.009350 |
| sealed-dark | 4.939181 | 0.175615 |
| sealed-lit | 5.899429 | 0.209757 |

Total projected remaining full controls36.984491CPU hours on the current
one-core execution. Scaling includes setup/output; planning only, not an ETA.
The current all-split method is expensive despite its eight-pixel statistical
improvement. This is a measured execution-scalability issue, not a physical
FAIL or measured statistical-cap failure. No full run is automatically queued.
Optimize the exact execution path before spending these long controls; retain
all original scene/count/seed/accuracy requirements. Physical inventory11/17,
references16/24,timing208FAIL,direct1.0UNRESOLVED/未解決 included. N010 NOT_READY.

Terminal236 SHA256: `f805f49d6d89b99be968510c856c1b994a8f260b99908d1783b8ea66c58140cf`.


## Near-first execution prototype: identity PASS, cost stop

090/238 preserves the exact old Bvh copy and pairs every executed query.
51,047,139closest queries have identical triangle/t bits;2,368,308occlusion
queries identical bool. The whole223 C1 data.json is byte-identical, including
all original/mixture/depth/audit data. Its paired native115.444280CPU/116.000005
elapsed sec includes BOTH query implementations and is not a standalone cost.
The separately compiled optimized exporter A6a8/fourseed/128x96 native has
all21 f64/PFM/hit payloads byte-identical to236, matching native integer and
proposal audits. Measured41.859831CPU versus retained42.641725CPU yields
0.9816636405, failing prospectively registered<=0.75 execution-promising rule.
Both complete=true and all_pass=false are intentional: identity passes, cost
condition fails. Do not start full controls with this traversal candidate.
Single-run retained sizing is not a controlled speedup estimate or GI win.

The ordering argument did not establish a useful cost reduction. Next inspect
actual CPU time concentration, including profile coverage/overhead, rather than
assuming traversal ordering explains cost. No new sampling/physical/quality/
GPU-time threshold was used. Original physical inventory11/17,references16/24,
timing208FAIL,direct1.0UNRESOLVED/未解決 included. Full objective incomplete.

Terminal238 SHA256: `5ea7ca9e64934a19479339b17e6f909fc0461d439ad37b2ee6d498c7bb6e7b90`.


## Original CPU profiles and post-hoc inline attribution

239 preserves a bootstrap linker failure before any profile/native execution.
092's environment-only strict-inverse dispatch240 removes LD_LIBRARY_PATH only
from perf/its children, retaining original224 binary/counts/seeds. No system or
app changes. Both own-user-IP-only profiles completed: A6a8spp/four seeds/full
128x96, C1 one spp/four seeds/full320x180. A6a all21 payloads and integer/proposal
audits exactly match236. Profile-root+descendant CPU includes overhead:
A6a42.901428CPU/43.251436elapsed, C1 33.702783CPU/33.945753elapsed seconds.
C1 low count supplies no physical, convergence or cap verdict.

093/241 compiles exact224 source/flags with only -g/output path changed, NEVER
executes it, and verifies identical .text address/bytes and every text symbol
address/name before offline addr2line mapping. This interpretation is POST-HOC.

| Original case | All IP samples | Slab | Remaining traversal | Triangle intersection | Unannotated |
| --- | ---: | ---: | ---: | ---: | ---: |
| A6a | 4256 | 1949 (45.7942%) | 1171 (27.5141%) | 776 (18.2331%) | 77 |
| C1 | 3342 | 1570 (46.9779%) | 886 (26.5111%) | 615 (18.4022%) | 75 |

Zero reported lost samples; all original samples remain denominators. Inline
frames, all address/count/category rows, executable and shared-library reports
and raw IP samples retained. Sampling/skid/line-table coverage/user-only scope
limit attribution. This locates dominant reference CPU cost in BVH box/loop
work. It neither explains GPU precision nor proves a complete cause or speedup.
The near-first238 candidate remains stopped. Next optimize the box predicate
with original node/query/output identity checks. No full physical queue;
11/17 physical,16/24references,N010 NOT_READY; tests NOT RUN.

Terminal239 SHA256: `180f22a88c10c6fd9d6eb18eab39790b00c4912521173bf1876ea776628d08ca`.

Terminal240 SHA256: `571c3bef164911e1662956008237236ea09c94a6b6653403fbb9469494c8f1ff`.

Terminal241 SHA256: `d6dea5b8ae136d52f00c303cda0e96458cf837e24ecd212a5dfe33c714b6c3f2`.
