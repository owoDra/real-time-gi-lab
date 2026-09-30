# Shared research protocol

## Evidence classes

Program-level interpretation uses these terms consistently:

- **accepted**: decision-valid evidence passed the frozen gate;
- **rejected**: decision-valid evidence failed the frozen gate;
- **inconclusive**: the frozen gate could not be evaluated reliably;
- **invalidated**: evidence is superseded because correctness, workload identity,
  provenance, or methodology was later shown to be invalid;
- **diagnostic-only**: a measurement/mechanism observation that may motivate a
  later experiment but may not be used as a formal promotion PASS/FAIL.

A result document may be complete without promoting an architecture.

## Accepted performance evidence

A performance result is accepted only when:

- the semantic/correctness gate for the experiment passes;
- the workload and hardware are identified;
- required architectural costs are inside the measured boundary;
- repeated measurements are used where timing variance can affect the decision;
- the exact Git commit and retained artifact provenance are recorded;
- limitations are stated explicitly;
- the decision thresholds and instability handling were frozen before accepted
  target timing.

Vulkan validation layers are optional diagnostics. They are not the semantic
correctness gate and should normally be disabled for accepted performance runs.

If an older accepted record lacks a normal
`out/research/<lane>/<experiment>/<timestamp>/` path, do not invent one. Record
the exact supplied artifact identity and the provenance limitation in that
result. New experiments should use the shared artifact recorder.

## End-to-end accounting

A candidate must count every cost it requires that its baseline does not:

- query/work production;
- allocation and residency management;
- sorting/grouping/scheduling;
- build/refit/rebuild;
- dynamic input preparation and transfer;
- invalidation and update propagation;
- lookup/traversal;
- cross-structure merge where required;
- merge/resolve;
- synchronization;
- scratch, transient, persistent, and peak resident memory.

An isolated kernel win may justify another experiment, but it does not promote
an architecture.

One-time setup may be reported separately when the protocol explicitly defines
it as setup. Recurrent allocation, transfer, rebuild, update, scratch clearing,
or synchronization must remain inside the recurring boundary.

## Workload rules

- Real producer streams are preferred.
- Synthetic streams are permitted for bring-up, correctness, stress limits, or
  controlled mechanism isolation only.
- Synthetic ordering must not be used as final evidence that producer-side
  locality is practical.
- Traversal/storage final decisions must be replayed against the representative
  Lane A stream unless a later frozen protocol explicitly studies another
  workload.
- Do not change candidate workload identity after seeing timing results.

## Dynamic scenarios

Decision gates should distinguish the regimes relevant to the claim, including:

- static camera / static geometry;
- camera motion and disocclusion;
- changing direct lighting;
- moving rigid geometry;
- stable-topology deforming/skinned-like geometry where relevant;
- topology-changing/high-churn geometry where relevant;
- sparse geometry;
- dense geometry;
- vertical/large-world stress where relevant.

Do not collapse regimes into one average if the winning architecture differs by
regime.

## Comparison rules

Use semantic parity and equivalent quality targets. A candidate that silently
does less work or produces a materially different result is not a fair speed
comparison.

Before attributing an ordering result to cache behavior, gather representative
GPU profiling evidence. Timestamp changes alone establish performance, not the
microarchitectural cause.

Historical results may provide context, but a historical number does not become
a formal run-local comparator when:

- the measured boundary differs;
- the workload differs materially;
- the timing methodology differs;
- required rows are unstable.

Cross-lane numerical comparisons with different boundaries must be labeled
context/diagnostic rather than a promotion gate.

## Timing repeatability

Repeatability is a shared methodology concern, not an architecture-specific
failure by default.

Before accepted timing, each experiment must freeze:

- repeat/warmup counts;
- the decision statistic;
- the instability criterion;
- the allowed rerun budget;
- whether instability is row-level or campaign-level;
- whether process/scenario ordering is fixed.

If the frozen instability criterion is exceeded:

1. retain all raw samples;
2. do not delete outliers or substitute the fastest subset;
3. use only the predeclared rerun policy;
4. if the permitted rerun remains unstable, mark the affected timing gate
   **inconclusive**;
5. do not convert an unstable median into PASS/FAIL.

If candidates and controls both exhibit repeated instability, treat the issue as
a measurement-methodology problem until evidence isolates an
architecture-specific cause.

A later methodology change is allowed only when diagnostics justify it. Freeze
the new protocol before the next accepted campaign and do not silently mix old
and new timing evidence.

### Post-Lane-H calibration requirement

After Lane G/H, a new timing methodology intended to support architecture
promotion must first be calibrated against controlled workloads with known,
predeclared work deltas. Candidate architectures are not the calibration source.

The calibration plan must freeze before target execution:

- controlled workload definition and exact work deltas;
- same-process/fresh-process structure;
- batching or aggregation boundary;
- candidate/control ordering;
- GPU timestamp and CPU wall accounting;
- decision statistic and uncertainty/repeatability criterion;
- minimum effect size the protocol claims it can resolve;
- rerun budget.

A protocol may claim only the effect-size resolution demonstrated by that
calibration. If it can distinguish 20% but not 10%, later architecture gates
must not use it to make a 10% superiority claim.

Before timing a dynamic architecture, the harness must also prove that every
measured sample actually exercises the intended update/rebuild transition.
Alternating a logical target flag is not sufficient evidence by itself.

### Post-Lane-I calibration disposition

Lane I tested a pre-frozen dual-axis calibration protocol on architecture-neutral
known work deltas. Under that exact protocol:

- the accepted GPU timestamp control passed and +20%, +10%, and +5% deltas were
  all detected across fresh-process replication;
- complete CPU wall produced a non-monotonic result: +20% failed the frozen
  maximum order-bias gate while +10% and +5% passed;
- therefore no common 5%, 10%, or 20% dual-axis resolution was accepted;
- I004 classifies the tested target timing protocol as **target timing
  unsuitable**.

The demonstrated Lane-I 5% GPU-timestamp resolution remains mechanism evidence
for that historical dual-axis campaign. It must not be retroactively reclassified
by changing CPU-wall semantics after observing the result.

### Post-Lane-K accepted GPU-primary protocol

Lane K prospectively froze the new role split before new target timing and
completed a fresh architecture-neutral calibration. K004 accepts
`lane-k-k002-v1` on AMD Radeon 8060S Graphics (RADV STRIX_HALO) with a
demonstrated **5% minimum effect size**.

The reusable protocol contract is:

- GPU timestamp is the sole primary performance decision axis;
- complete CPU wall is diagnostic / health / provenance only;
- 8192 calibration elements and 16 accepted batch dispatches;
- 4 warmup pairs and 12 measured pairs per process;
- 8 fresh-process blocks;
- paired AB/BA sampling with position-counterbalanced comparison order;
- 1 second settle before each process;
- primary statistic: fresh-process median of paired `log(B/A)`;
- control max absolute process-median ratio <= 1.02;
- control process-median span <= 1.03;
- control max within-process order-bias ratio <= 1.02;
- candidate process-effect span <= 1.05;
- candidate max within-process order-bias ratio <= 1.03;
- candidate minimum positive-pair fraction >= 0.75;
- candidate minimum process effect must exceed the accepted control noise
  envelope;
- all raw samples retained;
- sample exclusion forbidden;
- instability rerun budget = 0;
- completed-campaign rerun budget = 0;
- consistent device/driver/API/timestamp provenance required.

CPU-wall repeatability annotations do not veto the primary GPU decision.
CPU wall invalidates a campaign only for the structural failures frozen in K002:
non-positive/non-finite timings, incomplete pair structure, complete wall smaller
than GPU timestamp, inconsistent device provenance, or process failure.

A downstream architecture campaign may reuse Lane K only if it imports this
protocol **before** its first accepted candidate timing and freezes a promotion
threshold no smaller than 5%. Historical architecture timing remains diagnostic;
new same-run comparator evidence is required.

If a different GPU, driver/environment, workload boundary, smaller effect size,
or materially changed timing method is needed, calibrate that new method
architecture-neutrally before promotion.

### GPU safety constraint

The G002c forced-performance-state experiment caused host instability. Active
research must not require or request:

- `power_dpm_force_performance_level` writes;
- `profile_peak` or equivalent forced GPU performance states;
- privileged GPU clock/power sysfs writes;
- equivalent power/clock isolation experiments.

No conclusion about DVFS as a unique root cause is established by the crash.

## Decision-gate discipline

Freeze correctness, performance, memory, workload, and repeatability gates
before accepted timing.

After accepted timing starts:

- do not weaken thresholds;
- do not change structural parameters and keep only the better run;
- do not add candidate-specific favorable scenarios;
- do not move required costs outside the measured boundary.

A failed hard gate remains a failure even if another timing gate is
inconclusive. An inconclusive gate must not be treated as either pass or fail.

## Raw artifact contract

`scripts/research/run_experiment.py` creates:

```text
out/research/<lane>/<experiment>/<UTC timestamp>/
  metadata.json
  stdout.log
  stderr.log
```

The child command receives:

```text
PHOS_RESEARCH_ARTIFACT_DIR=<absolute artifact directory>
PHOS_RESEARCH_LANE=<lane slug>
PHOS_RESEARCH_EXPERIMENT=<experiment id>
```

Lane tools should write structured measurements into that directory rather than
inventing a second artifact tree.

## Committed result contract

Each concluded lane experiment gets:

`research/lanes/<lane>/results/NNN-name.md`

with:

- formal status/evidence class;
- question and compared variants;
- artifact path(s) or explicit provenance limitation;
- Git commit;
- hardware and workload;
- correctness outcome;
- key decision-relevant measurements;
- repeatability outcome;
- interpretation;
- limitations;
- decision and next question.

The same experiment is listed once in that lane's `results/index.json`.

Detailed experiment evidence remains in lane result documents. Cross-lane
synthesis belongs in `research/status.md`; do not duplicate large result tables
there.
