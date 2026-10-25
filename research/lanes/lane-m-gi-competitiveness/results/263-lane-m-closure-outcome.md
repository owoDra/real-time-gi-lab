# Lane M closure — LANE_M_COMPLETE_CHARTER_NOT_MET

Lane M is closed under the criteria registered in
[047](../experiments/047-lane-m-closure-criteria.md) (`b7375747`, fixed before
any M002 result). Closing the lane records a final, honest verdict; it is not a
claim that the research charter was met. Full matrix:
[262](262-lane-m-closure-matrix.json); verification [264](264-lane-m-closure-verification.json);
decision record [2026-10-25 Lane M closure](../../../decisions/2026-10-25-lane-m-closure.md).

## Closure criteria

1. All registered Lane M studies 001-046 (with addenda) are terminal; no process
   is running or pending. Stops and withdrawals (019, 024, 029, 031, 035, 037,
   038, 040, 044 v1/v2) remain preserved as stops.
2. The cross-family matrix below is published with every loss kept.
3. Every charter requirement is classified (table below).
4. status, roadmap, lane README, index and a decision record carry the verdict.

## Fair comparison on this device (M001 static heldouts; M002 unseen states)

| Family | M001 quality | M002 quality | Owned memory | Calibrated time |
|---|---|---|---|---|
|Raw PT|6/6 (256/1024spp)|10/12|2.4-3.9 MB|matched-quality comparator|
|PT + fixed quadratic reconstruction|6/6 (16/64spp)|6/12|25.8-26.3 MB|faster than raw PT at matched quality: accepted on 5 targets (1.48-10×), 7 inconclusive in the same direction, 0 slower|
|Fixed Split RC (HWRT/software/vanilla/dense)|0/6 each|not run|~267 MB (dense 2.4 MB)|ineligible|
|Corrected DDGI|0/6|not run|432 MB|ineligible|
|NRD RELAX (1-64spp, two configs)|0/6 each|not run|32-87 MB|ineligible|
|ReSTIR GI (null trials)|0/6|not run|50-78 MB|ineligible|
|ReSTIR GI + reconstruction|0/6 per frame|not scored|73-100 MB|dominated at equal cost by PT16+reconstruction (6/6)|

Within the fixed gates (total NRMSE<=5%, indirect<=10%, |bias|<=5%, all
pixels), only path-traced families reach quality on this cohort. The
reconstruction is the only accepted same-quality speedup, it trades memory for
time, and it does not generalize to box-field and light-change states (M002).

## Charter requirements

| Requirement | Status |
|---|---|
|Novel GI transport architecture|NOT_MET|
|Same-quality GPU-time superiority over fair families|NOT_MET (bounded partial vs raw PT)|
|Same-quality memory superiority|NOT_MET|
|Same-cost quality superiority|NOT_MET (bounded partial: PT16+recon over ReSTIR+recon)|
|New heldouts|MET as tested; generalization negative|
|Dynamic camera/light|PARTIAL (single changed states, stateless roles)|
|Dynamic rigid/deforming/topology/churn|NOT_MET|
|Sponza / broader scenes|BLOCKED (harness ≤2048 triangles)|
|Multiple GPU classes|BLOCKED (one AMD Radeon 8060S)|
|Software fallback|PARTIAL (RC software role only)|
|Deployability|NOT_MET|
|True-peak owned-memory accounting|MET|

**Verdict: LANE_M_COMPLETE_CHARTER_NOT_MET.** Every NOT_MET/BLOCKED item is
handed to a proposed, not started, follow-up lane (generalization and devices).
465 assistant-executed GPU acquisitions in total; no power/clock changes, no
CI, no default Renderer change, no main promotion.
