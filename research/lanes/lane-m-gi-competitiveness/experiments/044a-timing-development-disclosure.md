# 044a — Disclosed timing-harness development runs

Prospective addendum to 044 (`1f900a16`), written after the 044 host and new
GLSL compiled in a scratch build and BEFORE any 044 GPU execution or registered
preparation. Nothing in 044 changes.

- At most 6 development GPU processes, outputs only under
  `out/research/lane-m-gi-competitiveness/m001-timing044-dev-*`, all kept and
  inventoried. Allowed: the neutral calibration workload and the H01/B2 and
  H01/B8 target roles, with fewer pairs if needed.
- Purpose: verify that every role submits, completes inside the 250 ms fence
  guard and journals correctly, and choose the neutral iteration counts so the
  short boundary is about 5 ms and each long-boundary submit about 20 ms (the
  base counts are multiples of 100 so +5/+10/+20% deltas are exact).
- Development timings are never evidence: no ratio, statistic or decision is
  computed from them beyond per-sample duration magnitudes needed for the
  iteration counts and guard check. Registered calibration and target processes
  are fresh and use only committed sources rebuilt by the registered preparation.
