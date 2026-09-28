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
