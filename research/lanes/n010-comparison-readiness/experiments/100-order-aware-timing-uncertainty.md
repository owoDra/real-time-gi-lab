# N010 prospective timing Amendment — order-aware effect uncertainty

Date: 2026-10-17 JST. Parent: `28fc64b`. Register and commit this document and
its analysis/acquisition code **before new acquisition**. Implements the
direction in result249. This is a new method, not a reinterpretation of
001/009/098/099 or results169/208/247/248. All earlier FAILs remain. No old
samples enter its decision. No existing accepted preflight is bypassed.

## Question and scope

Can the actual static C7 HWRT Renderer boundary distinguish the sized
approximately +20% neutral additional work when process variability and
order-dependent nuisance shifts are included in the effect interval?

Use the byte-identical206 isolated contiguous fixture, shaders and original
timed commands/expressions. Reuse246's frozen dose1301 only with its exact
boot/device/driver and binary/shader identities. No sizing or tuning repeat.
The target is not an assumed exact GPU-time increment. Images, scratch,
allocation ledger, CPU spool and resource receipts remain required.

This first bounded acquisition is diagnostic, not the sixteen-boundary
campaign. A PASS demonstrates this registered repeated-frame boundary only;
it does not qualify individual-frame timing, other selected budgets, dynamic
lifecycle, other families or GPUs, the complete N010 gate or GI superiority.
Any extension must calibrate the actual selected boundaries. The statistical
family budget below reserves sixteen calibration boundaries, not an unlimited
number of Lane M architecture comparisons.

## Observation, randomization and finite acquisition

- Observation: arithmetic mean of four separately timestamped consecutive
  actual frames at the same dose. Preserve all four original GPU intervals,
  frame identities, images, scratch and explicit constituent indices. No
  interleaved arm interpretation from099. Batch CPU wall is diagnostic only.
- Twelve fresh-process blocks. Four warmup +six measured paired rounds per
  kind per process; both arms in a pair are executed consecutively as four
  frames each. Every round includes `control_a` (0/0), `control_b` (1301/1301)
  and `effect` (A=0/B=1301). All three have pseudo-arms A/B.
- Within each kind, independently shuffle four warmup orders (2 AB/2 BA) and
  six measured orders (3 AB/3 BA). Shuffle the three kinds within each round.
  Freeze the generator in timing_uncertainty.py: Python Random seeded from
  SHA-256 of `N010-plan100-order-aware-process-median-v1:<block-index>`.
  The complete labelled schedule is saved before each native invocation.
  This is randomization fixed before observing new outcomes, not adaptive
  order selection. Preserve Python/version and generated schedules.
- Per process: 60 mean observations /240 actual frames. Twelve processes:
  720 observations /2880 original frames, of which all warmup data remain.
  No adaptive additions, sample exclusions, trimming or retries.
- One-second settle between processes; no concurrent research worker.
  One low-priority CPU (31 on the current32-CPU allowed affinity), nice15;
  each native <=30CPU/30elapsed seconds. Do not start a further process once
  campaign acquisition wall exceeds180seconds. Retain all partial evidence
  on any failure. Full completion or failure ends this method's acquisition.
- Before each process require >=12GiB free disk; new retained work <=8GiB.
  Existing CPU RGBA256MiB, scratch16MiB, Vulkan staging256MiB, total owned8GiB
  and teardown-to-zero checks remain. No display/power/clock/app changes.

The extra role-matched control is a response to workload-dependent nuisance:
zero-dose control alone cannot establish loaded-role order behavior. It is
not an external GPU-idle or clock-stability requirement.

## Estimand and interval

For each process, kind and order, take the median of its three measured
`log(t_B/t_A)` paired means. The six process-summary populations (three kinds
times two orders) are kept separate; correlated frames/pairs are not promoted
to independent repetitions. The estimands are their process-summary medians,
conditional on this host and registered lifecycle. Also report absolute GPU
times; a process-median ratio is not a mean frame-rate ratio.

For twelve process summaries x, use the closed order-statistic median
interval `[min(x),max(x)]`, and the median as its point estimate. No bootstrap,
normal approximation or interpolated quantile. Under independent repetitions
with a common median, noncoverage is at most `2/2^12 = 0.00048828125` per
interval. Ties stay in the data. Across6 intervals x16 boundaries, the union
bound is `96*2/4096 = 0.046875`, hence at least95.3125% simultaneous coverage
for those raw population medians under the assumptions. Twelve is the
smallest integer meeting <=5% for this six-by-sixteen family budget.
Dependence between the six intervals does not invalidate the union bound;
dependence across fresh-process repetitions can invalidate the individual
interval coverage. A new boot/driver/device is not silently pooled.

For each order o, let E_o be the effect median interval and C0_o/C1_o the two
same-role control median intervals. Define the nonnegative log allowance
`b_o=max(abs(endpoint) for endpoint in C0_o and C1_o)`.
Use `J_o=[E_o.lower-b_o,E_o.upper+b_o]`, then the conservative order hull
`J=[min(J_AB.lower,J_BA.lower),max(J_AB.upper,J_BA.upper)]`.
Report `exp(J)` as the control-allowance sensitivity interval. Do not subtract
a favorable point control estimate or pool opposing order results away.

This allowance is **conditional**, not a universal statistical guarantee
against systematic error: the unmodelled log-location shift in an effect arm
must be no larger in magnitude than the matched same-role control shifts.
Its motivation is identical scene/frame/command lifecycle and adjacent,
randomized, both-load controls. Identical images and exact neutral-work
witnesses attest workload semantics, not clock stability. Require overlapping
C0/C1 intervals within each order and overlapping J_AB/J_BA. Disagreement
contradicts the proposed common-nuisance approximation and makes the method
inconclusive. Agreement alone does not prove it; report this assumption and
the raw intervals even on PASS. Independent workload-specific carryover or
cross-process drift outside this model remains a limitation. Do not make a
causal explanation for external load, clocks or apps from this experiment.

The order-statistic construction follows the binomial/order-statistic basis
described by [NIST median confidence limits](https://itl.nist.gov/div898/software/dataplot/refman1/auxillar/mediancl.htm).
Blocking/randomization follows the design principle in
[NIST randomized block designs](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm).
Our control allowance and GPU model are an explicitly specified research
choice, not a claim that either source validates this fixture or its bias.

## Frozen classifier and decision resolution

Integrity/resource/workload failure: preserve evidence, operational failure,
no accepted timing. For a complete acquisition require all four checks:

1. The two same-role control median intervals overlap within each order.
2. The two order-specific effect intervals J_o overlap after allowance.
3. `J.lower > 0`: positive additional-work effect survives the allowance.
4. `J.upper-J.lower <= log(1.20)`: multiplicative interval width <=1.20.

If all pass, report bounded C7 calibration PASS with its measured effect and
conditional model. Otherwise report **inconclusive timing capability**; retain
which numerical checks failed. Do not label this an architecture rejection
or repeat until PASS. The width is tied to the original approximately20%
calibration question, rather than a new arbitrary2% stability cut.

For subsequent registered same-quality comparisons, reserve a practical
ratio margin of1.20, no tighter than this method's stated resolution. With
q=T_candidate/T_baseline, win requires the entire justified interval below
1/1.20; loss requires it above1.20; practical equivalence requires it entirely
inside[1/1.20,1.20]; otherwise inconclusive. A1.20 speed ratio means16.67%
less GPU time, not20% less. Detecting the approximately+20% calibration effect
against zero is distinct from proving an architecture exceeds this margin.
The comparator/state count, tuning/held-out split and simultaneous intervals
must be registered in Lane M before candidate timing. This calibration's96
interval budget does not authorize a selected-scene or overall winner.

## Artifacts and unchanged obligations

Driver: scripts/research/n010_reference_sampling/diagnose_uncertainty_c7.py
Analysis: scripts/research/n010_reference_sampling/timing_uncertainty.py
Work: out/research/n010-comparison-readiness/uncertainty-c7-diagnostic-v1
Result: results/250-uncertainty-c7-calibration-diagnostic.json

N010 remains NOT_READY until the complete readiness obligations are proved.
All24 reference slots, all remaining physical proofs, full-corpus quality and
dynamic pilots, frozen budgets, true peak and DDGI scene-GI remain. Direct
max-relative-error1.0 pixels remain UNRESOLVED/未解決 and included. No N011,
CI/Actions, default Renderer/build changes or N001–N009 result edits.
Unit/regression tests NOT RUN; authorized bounded scientific acquisition and
its image/scratch/ledger/identity checks are not release regression tests.
