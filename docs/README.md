# Research documentation

This directory records research decisions that cannot be recovered from source
code alone.

## Source-of-truth boundaries

- **Source code, shaders, comments, and executable correctness guards** are the
  source of truth for implemented behavior.
- **`research.md`** is the source of truth for the long-term research question,
  constraints, and architecture hypotheses. It should change slowly.
- **`status.md`** is the source of truth for the current milestone, accepted
  evidence, invalidated evidence, open questions, and next decision gate.
- **`experiments/*.md`** define reproducible experiment protocols and their
  pass/fail criteria.
- **`out/benchmarks/`** contains generated raw benchmark artifacts and is not
  committed. Results become project evidence only after they are reviewed and
  summarized in `status.md`.

README files should link to these documents rather than duplicate their
contents. Implementation details that are obvious from code must not be copied
into docs.

## Branch policy

- `exp/*` branches are the workspace for hypotheses, measurements, and
  implementations that have not passed their decision gate.
- `main` is for the consolidated research baseline after an experimental
  direction is considered stable enough to keep.
- Failed or invalidated experiments are not erased; their conclusion is kept in
  the evidence ledger so the same path is not accidentally rediscovered as an
  untested idea.

The active page-local cache work therefore remains based on
`exp/page-local-radiance-cache` until its M0/M1 gates are resolved.
