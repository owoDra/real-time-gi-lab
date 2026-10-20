# R1 Sponza pilots and final full-corpus readiness audit

2026-10-20 JST. Follows174/175. Registered before any R1 pilot or audit run.
Original gates, metrics, budgets, binaries and commands are unchanged; only reference
eligibility dispatch (R1 for the eight174 slots) differs, and every use is recorded.

## Pilots (after747 exists; one invocation per step, inspect before the next)

`run_r1_pilot.py <pilot> args…` executes the committed pilot source with exactly one
line replaced — its `classification=='STATISTICALLY_ELIGIBLE'` gate becomes a full
`r1_reference_provenance.verify_reference` of the same slots through the747 view —
and routes `score_hdr.score` through the175B R1 scorer. Inverse is proved per run
and recorded in `<output>.r1-adapter.json`.

1. C1 T_B8 static ladder (Amendment1 of049, unchanged `acquire_pt_pilot.py`):
   `--cell C1 --vertices 8 --state <026 C1> --references <747 work> --work
   final-comparison-pilots-r1-v1/C1-B8-ladder --output 748-c1-b8-pt-quality-ladder.json`.
   749 = 031 rows + 748 rows, exactly as `finish_readiness.py` merges 044.
2. Sponza dynamic cohorts, unchanged `acquire_dynamic_pilot.py`, one cell per call in
   order C2…C6, lock026, default budgets (B2 256 / B8 1024, as019), work
   `final-comparison-pilots-r1-v1/<cell>-dynamic`. 750 = merged rows, as048.
   A failed native stops the sequence (retained); no retry.
3. Remaining selected PT n1024 via175D (dynamic C2/C3/C4-B8, C5/C6-B2/B8), written to
   the original `continuation-quality-cases` paths that the417/503 inventory reads.

## Final audit (751)

`readiness_audit_r1.py --audit` wraps the unchanged160 state-bound wrapper over the154
overlay over `readiness_preflight.py`. Before execution it sets
`hybrid_reference_provenance.verify_reference` and `score_hdr.score` (module
attributes, process-local) to the175B R1 verifier/scorer, which bind the original
functions at import and use them unchanged for the16 original slots. This patch is
not visible to file-hash checks and is therefore declared here and in751's
`r1_dispatch` field. Output `751-r1-full-readiness-audit.json`, work
`r1-full-readiness-v1` (not619/618: their registered composition is unchanged and
remains NOT RUN). Arguments: lock026, references = 747 work,
`--reference-view-record 747`, timing scope503, dynamic pilots019/037/750, static
pilots749/013/024/025.

READY in751 means all six original gates pass with R1 eligibility for the eight
slots. Timing remains TIMING_INCONCLUSIVE (120/147); no speed or superiority claim.
The direct relative error1.0 pixels remain UNRESOLVED/未解決 and included, which the
unchanged correctness gate checks. Tests NOT RUN.
