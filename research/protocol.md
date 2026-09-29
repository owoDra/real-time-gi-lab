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
