# Final full-corpus readiness audit with R1 eligibility (751)

2026-10-21 JST. Plan176 `readiness_audit_r1.py --audit` (unchanged160 state-bound
wrapper over the154 overlay over `readiness_preflight.py`, with the declared
process-local R1 dispatch recorded in `source_composition.r1_dispatch`). Source commit
`d4bd6629`. CPU31, nice15, one numerical thread, 4GiB, CPU1200s; wall17.5min.
Record [751](751-r1-full-readiness-audit.json).

**Classification: `READY_FOR_LANE_M_FIRST_COHORT`** (all six gates PASS).

| Gate | Result |
| --- | --- |
| eligible_locked_physical_references | PASS: 24/24 (16 original screen, 8 R1 via [747](747-full-corpus-r1-reference-view.json)) |
| correctness_validations_and_explicit_remaining_discrepancies | PASS; direct max-relative-error1.0 pixels remain **UNRESOLVED/未解決**, included |
| whole_corpus_dynamic_quality_memory_pilot | PASS: 019/037 + [750](750-controlled-dynamic-cohort-r1.json) (Sponza C2–C6) |
| fixed_ladders_and_quality_selection | PASS: [749](749-c1-complete-pt-quality-ladder-r1.json) (031 + [748](748-c1-b8-pt-quality-ladder.json)) /013/024/025 |
| valid_complete_selected_timing_quality_memory_pilots | PASS: 36/36 (28 PT, 8 non-PT); **TIMING_INCONCLUSIVE**, accepted_timing=false |
| additional_family_source_and_supported_device_boundary | PASS: DDGI source/boundary only; runtime qualification is Lane M work |

Inputs produced in this run sequence (2026-10-21):

- [752](752-r1-reference-acquisition-outcome.md): C3/C4 T_B8 R1 eligible at16384.
- 747: full24-slot view (`full-corpus-r1-view-v1`), every row re-verified.
- 748: C1 T_B8 PT ladder n1…n1024; n1–n256 FAIL, n1024 PASS (R1 scored). 749 merges
  it with031 exactly as `finish_readiness.py` built044.
- 750: dynamic C2–C6, six roles each; all natives returncode0. Pixel PT B2/B8 PASS
  every frame; incumbent HWRT/software, vanilla traversal and dense RC FAIL every
  scored frame (retained as comparison losses). C6 incumbent-software is
  `UNSUPPORTED_IN_CAPTURE_API` by the unchanged pilot (N002 churn entry is HWRT-only).
- Seven remaining selected PT n1024 cases (dynamic C2/C3/C4-B8, C5/C6-B2/B8) via175D:
  all `VALID_SINGLE_CASE_QUALITY_RESULTS_RETAINED`.

Limits unchanged: R1 is a disclosed post-hoc amendment (174); the eight R1 slots
remain original-screen INELIGIBLE and are labelled `eligibility_rule:"R1"` in every
score. The all-split/627 estimator remains unadmitted and is not used. No speed,
equivalence or superiority claim. Tests NOT RUN.
