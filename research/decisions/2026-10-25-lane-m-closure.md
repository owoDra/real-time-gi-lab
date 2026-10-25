# 2026-10-25 — Lane M closure

Decision: close Lane M (GI competitiveness) with verdict
**LANE_M_COMPLETE_CHARTER_NOT_MET**, per the criteria registered in
[047](../lanes/lane-m-gi-competitiveness/experiments/047-lane-m-closure-criteria.md)
before the final M002 results.

Reasons:

- All registered Lane M studies are terminal and published, including stops.
- A fair cross-family comparison exists for this device and cohort
  ([closure outcome](../lanes/lane-m-gi-competitiveness/results/263-lane-m-closure-outcome.md)):
  only path-traced families meet the fixed HDR gates; PT plus the fixed
  quadratic reconstruction is the only accepted matched-quality speedup over raw
  PT, at higher memory, and it fails to generalize on M002 box-field and
  light-change states.
- The charter's success state (novel architecture, superiority over fair
  families across scenes, dynamics and multiple GPU classes) is not met;
  multiple GPU classes and Sponza-scale scenes are blocked in this environment.

Consequences:

- The incumbent architecture is unchanged; nothing is promoted to `main`.
- Remaining requirements are handed to a proposed follow-up lane
  (generalization and devices), not started. Lane M results remain historical
  evidence and may not be relabelled.
