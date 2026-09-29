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
- F003: implementation frozen for first target validation; no accepted F003
  timing artifact exists yet.

F003 preserves the fixed dynamic classification: the F001/I001 selected
moving-rigid primitive set is excluded from persistent static HWRT before the
warmup frame and remains frame-local dynamic data through the measured frame.
