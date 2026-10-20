# R1 reference integration and pending PT proof replay

2026-10-20 JST. Follows174 (R1) and746. Registered before any R1-scored capture.
No threshold, physical estimator, capture recipe or score metric changes.

## A. CPU-only proof replay of retained dynamic-C4-B2-n1024 (746)

Its native terminated0; the130 runner's own python RLIMIT_CPU120s killed the proof
stage while hash-verifying the hybrid C4_T_B2 reference. `replay_pending_pt_proof.py
--case dynamic-C4-B2-n1024` re-runs the **unchanged** `references_before_launch` and
`C.verify_capture` (same lock, cell, budget, references, `H.verify_reference`) on the
retained record/capture bytes, writing `continuation-quality-proof-replays/<case>.json`
and a fresh score directory. CPU27, nice15, CPU1800s, 4GiB. No native, no recapture,
no edit of the original record (it stays PROOF_PENDING). A failure is retained.

## B. R1 slot views, verifier and scorer (`r1_reference_provenance.py`)

For each of the eight174 slots, a slot view in `r1-slot-views-v1/<slot>` holds
byte-identical copies of the retained original-oracle payloads, metadata, screens,
scene and prefix import up to the first R1 qualifying level, plus a truncated
qualification whose classification remains the truthful original-screen result
(`INELIGIBLE`). `r1-eligibility.json` stores R1. The verifier first runs the unchanged
full `H.verify_reference(..., require_eligible=False)` chain, then recomputes R1 and
requires an exact match at the final retained level. The scorer runs `score_hdr.score`
unchanged except that R1 replaces its single classification gate, and stamps
`eligibility_rule:"R1"` and the original classification in every score. Slots without
an R1 record use the unchanged original path.

## C. Full24-slot R1 reference view (747)

Once all eight R1 slot views exist: a view like160 with all24 rows; the16 originally
eligible rows keep160's exact targets; the eight R1 rows point to their slot views.
Symlinked work root `full-corpus-r1-view-v1`.

## D. R1 PT adapter (`acquire_r1_pt_quality_case.py`)

Wraps the frozen132/130 runner exactly as132 wraps130: same case set and commands,
with only `VIEW` → 747 and the reference verifier/scorer → B. Used for the remaining
selected PT cases (dynamic C2/C3/C4-B8, C5/C6-B2/B8) and the C1-B8 static ladder
(n1…n256), plus a CPU-only R1 score replay of retained402. One native per call, no
retry. Every result says `eligibility_rule:"R1"` where an R1 slot is used.

N010 NOT_READY until all gates. Tests NOT RUN.
