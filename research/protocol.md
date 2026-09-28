# Shared research protocol

## Accepted evidence

A performance result is accepted only when:

- the semantic/correctness gate for the experiment passes;
- the workload and hardware are identified;
- required architectural costs are inside the measured boundary;
- repeated measurements are used where timing variance can affect the decision;
- the raw artifact path and Git commit are recorded;
- limitations are stated explicitly.

Vulkan validation layers are optional diagnostics. They are not the semantic
correctness gate and should normally be disabled for accepted performance runs.

## End-to-end accounting

A candidate must count every cost it requires that its baseline does not:

- query/work production;
- allocation and residency management;
- sorting/grouping/scheduling;
- build/refit/rebuild;
- invalidation and update propagation;
- lookup/traversal;
- merge/resolve;
- scratch and persistent memory.

An isolated kernel win may justify another experiment, but it does not promote
an architecture.

## Workload rules

- Real producer streams are preferred.
- Synthetic streams are permitted for bring-up, correctness, stress limits, or
  controlled mechanism isolation only.
- Synthetic ordering must not be used as final evidence that producer-side
  locality is practical.
- Lane B/C final decisions must be replayed against the representative Lane A
  stream.

## Dynamic scenarios

At minimum later decision gates should distinguish:

- static camera / static geometry;
- camera motion and disocclusion;
- moving rigid geometry;
- changing direct lighting;
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

Lane tools should write any structured measurements into that directory rather
than inventing a second artifact tree.

## Committed result contract

Each concluded experiment gets:

`research/lanes/<lane>/results/NNN-name.md`

with:

- status: accepted / rejected / invalidated;
- question and compared variants;
- artifact path(s);
- Git commit;
- hardware and workload;
- correctness outcome;
- key measurements;
- interpretation;
- limitations;
- decision and next question.

The same experiment is listed once in that lane's `results/index.json`.
