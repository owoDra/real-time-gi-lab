# M001 DDGI H02: both quality ladders exhausted

2026-10-23. [Prospective010](../experiments/010-ddgi-static-quality-budget-ladder.md), [CPU preparation042](042-ddgi-quality-cpu-preparation.json), [cumulative raw replay046](046-ddgi-h01-h02-quality-raw-replay.json). The earlier [H01 outcome044](044-ddgi-h01-quality-outcome.md) remains unchanged.

H02/T_B2 and H02/T_B8 both exhaust their3fixed budgets with **QUALITY_FAIL**. All6first-attempt acquisitions are complete and physically/reference eligible; each terminal independent CPU audit preceded the next preparation. No operational failure, retry, output overwrite, excluded pixel, skipped budget, seed/estimator change or relaxed gate. Total NRMSE≤5%, indirect NRMSE≤10%, absolute indirect signed bias≤5% all remain required.

|Target|Grid/rays|Total NRMSE|Indirect NRMSE|Indirect signed bias|Decision|
|---|---|---:|---:|---:|---|
|H02/T_B2|8³/128|4.258719%|25.697658%|-10.339301%|QUALITY_FAIL|
|H02/T_B2|16³/256|5.709265%|34.450448%|-14.576081%|QUALITY_FAIL|
|H02/T_B2|24³/512|7.320067%|44.170228%|-22.058980%|QUALITY_FAIL|
|H02/T_B8|8³/128|5.428911%|26.842886%|+0.336008%|QUALITY_FAIL|
|H02/T_B8|16³/256|4.865760%|24.058428%|+7.245904%|QUALITY_FAIL|
|H02/T_B8|24³/512|4.034632%|19.948973%|+3.948592%|QUALITY_FAIL|

At maximum24³/512 the indirect NRMSE is44.170228%/B2 and19.948973%/B8. The B2 ladder worsens at each higher budget; no favorable rung is substituted for its registered exhausted loss. B8 improves in NRMSE but still fails. Direct NRMSE is3.713625724005728e−7 at every budget/depth. All direct/support/leak/active-p99 diagnostics and18new full error maps are retained; neither matching total energy nor small direct error replaces indirect spatial accuracy. These observations do not isolate a cause or authorize tuning on completed heldouts.

Cumulative H01/H02 replay046 actually rehashes528native payloads and32,456completed GPU units across12acquisitions, with36full error maps. Every case verifies exact physical and original four-seed16384spp reference/provenance, official128/256/512SDK shader identities, packed grid/ray/rotation/format/feature constants, SDK extents, disjoint ray tile completion, finite entire arrays, initial-zero/immutable previous atlas, pixel/PFM/composite correspondence and every owned allocation. Each H02 ledger has56events, true peaks8,084,368/78,289,808/431,872,912owned bytes for q0/q1/q2, zero teardown; CPU/driver-private excluded. Larger-budget runtime qualification remains scoped to actually audited states. Validation layers NOT_RUN.

All6new H02 captures were assistant-operated under explicit workstation authorization, without power/clock/desktop changes or automatic GPU queue. Total new acquisitions in this continuation are68 (prior62 plus these6); original human-operated captures keep their attribution. Large raw arrays/error maps/proof tars remain in repository/out. Native source/binary036 unchanged; CPU preparation042 and prior038 are preserved rather than falsely claiming new test/build reruns. Default Renderer build/runtime regression NOT_RERUN; historical source/evidence and all CMake unchanged.

**Both H02 DDGI/PT timing branches stop as quality-ineligible**, as both H01 branches already did. No timestamp sum or memory observation is admitted as a speed/architecture win. Fresh-static finite-depth/reset qualification does not qualify temporal accumulation, scrolling, steady-state temporal DDGI, unseen dynamic quality or representative-device generalization. Native per-unit timestamps/setup metadata are diagnostic/uncalibrated; no accepted complete end-to-end or whole-process lifetime boundary.

Four DDGI target ladders are now exhausted losses (12cases,0PASS). **H03/T_B2 and H03/T_B8 are NOT_RUN** and have no inferred result. Next permitted acquisition is H03/T_B2/q0 (8³/128), following its own CPU plan, single named GPU process and terminal audit. Original references, PT selections,24fixed-RC losses and N001–N010 evidence remain unchanged. Broader Lane M dynamic/Sponza/device/temporal and matched-quality performance gates remain open; M001/Lane M are incomplete.
