# Lane F — alternative dynamic geometry architectures

Issue: #16
Branch: `research-lane-f-dynamic-geometry-alternatives`
Plan: `lane-f-plan-v1`

Issue #16 is the canonical frozen research protocol. This lane owns only the
implementation, raw-artifact adapters, and concluded result records needed to
execute that protocol. Do not duplicate or relax thresholds here.

Current checkpoint:

- F001: correctness PASS; moving-rigid baseline repeatability INCONCLUSIVE.
- F002: structural correctness/repeatability PASS; formal feasibility gate
  remains pending because its required F001 run-local comparator is inconclusive.
- F003: correctness PASS; accepted timing INCONCLUSIVE after the one permitted
  identical full rerun also remained unstable.
- F004: not activated because the frozen F002 formal-PASS prerequisite is not
  available; F003 moving dynamic traversal was also below builder time.
- F005: correctness PASS; accepted timing INCONCLUSIVE after the one permitted
  identical full rerun also remained unstable. Grid mechanism evidence shows
  strong cell-reference amplification and radix-sort-dominated rebuild cost.
- F006: geometry-class crossover implementation/config/runner are frozen
  before first accepted timing; target validation is the next checkpoint.

F003 and F005 preserve the same fixed dynamic classification: the F001/I001
selected moving-rigid primitive set is excluded from persistent static HWRT
before warmup and remains frame-local dynamic data through warmup + measured
target frame. F005 changes only the transient dynamic representation/traversal:
AABB cell overlap -> prefix -> sorted macro/local cell pairs -> RLE ranges ->
two-level DDA + exact triangle tests.
