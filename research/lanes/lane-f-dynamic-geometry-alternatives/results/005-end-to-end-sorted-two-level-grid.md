# F005 — End-to-end sorted two-level grid control

Plan: `lane-f-plan-v1`  
Measurement commit: `f704a0cbc690774d2c3fb68eeab87ea9e525bb7c`  
Target: AMD Radeon 8060S Graphics (RADV STRIX_HALO), RADV / Mesa 26.1.2

## Outcome

**Correctness PASS. Accepted timing INCONCLUSIVE after the one permitted identical full rerun also remained unstable.**

The sorted two-level grid completed the full 32-case validation matrix with
zero quality failures, grid overflows, storage failures or Vulkan validation
errors. The first accepted timing campaign exceeded the frozen
`complete_gpu_us max/min > 1.20` instability threshold. The one permitted
identical full-campaign rerun also exceeded it.

Under `lane-f-plan-v1`, no additional timing rerun, outlier deletion,
partial-case rerun or threshold reinterpretation is allowed. F005 therefore
does **not** produce a formal performance PASS or FAIL.

## Artifacts

Validation:

`out/research/lane-f-dynamic-geometry-alternatives/005-end-to-end-sorted-two-level-grid/20260929T132648Z`

First timing campaign — unstable:

`out/research/lane-f-dynamic-geometry-alternatives/005-end-to-end-sorted-two-level-grid/20260929T132842Z`

One permitted identical full rerun — unstable:

`out/research/lane-f-dynamic-geometry-alternatives/005-end-to-end-sorted-two-level-grid/20260929T133229Z`

## Correctness

All 32 frozen combinations passed:

- transient-grid
- vanilla-software
- combined-hwrt
- combined-software

across static, camera-motion, light-motion, moving-rigid, sparse-stress,
dense-stress, large-world-stress and vertical-world-stress.

Every validation row reported:

- `quality_passed = true`
- `grid_overflow = 0`
- `storage_failures = 0`
- `validation_errors = 0`

## Timing repeatability

The second and final allowed campaign still contained **14 unstable
variant/scenario pairs**. The transient-grid moving-rigid row itself was also
unstable:

- complete GPU min: 17,634.065 us
- complete GPU median: 18,600.421 us
- complete GPU max: 21,880.413 us
- max/min: 1.2408

The rerun budget is exhausted. No further F005 timing is decision-valid under
the frozen plan.

## Grid mechanism evidence

Although timing gates are inconclusive, the candidate-specific structural
metrics are deterministic and were reproduced across campaigns.

For the frozen moving-rigid subset:

- dynamic triangles: 796
- emitted cell references: 155,033
- references / dynamic triangle: 194.765
- maximum references for one triangle: 6,100
- pair-stream bytes: 6,835,168
- sort scratch bytes: 7,055,296
- visited macro cells: 35,604
- visited local cells: 95,651
- empty-cell steps: 86,196
- tested primitive references: 55,951
- peak resident bytes: 196,140,496

Second-campaign moving-rigid phase medians:

- builder reset: 16.752 us
- current-frame input: 3.727 us
- overlap: 53.862 us
- prefix: 2,298.327 us
- pair emit: 6.693 us
- radix sort: **15,035.888 us**
- range build: 1.723 us
- complete dynamic builder: **17,182.727 us**
- dynamic traversal: 49.895 us
- cross-structure merge: 8.376 us

The dominant cost is therefore not DDA traversal. It is the amplified
cell-reference stream and its sort, with prefix work a secondary cost.

## Diagnostic gate values only

The second unstable campaign's ratio calculations are retained only as
diagnostic leads; they are **not formal gate decisions**.

- moving-rigid GPU ratio vs run-local vanilla: 6.163x
- moving-rigid wall ratio vs run-local vanilla: 0.173x
- sparse-stress peak memory ratio vs run-local vanilla: 3.0836x
- stable static/camera/light and the other stable stress median GPU ratios were
  close to the full-scene combined-HWRT control.

The contradictory-looking wall/GPU moving ratios are another reason not to
reinterpret this unstable campaign as formal promotion evidence.

## Decision

- F005 correctness: **PASS**
- F005 timing repeatability: **INCONCLUSIVE**
- F005 formal performance gate: **NOT EVALUATED**
- additional F005 timing reruns: **not allowed**
- architecture promotion from F005: **none**
- grid diagnostic: pair-reference amplification makes the frozen two-level
  grid builder strongly sort-dominated on the representative dynamic subset

F005 remains eligible as a correctness-valid end-to-end transient architecture
for F006 controlled geometry-class mechanism tests unless a separate hard-memory
eligibility decision is made from plan-valid evidence.

No grid structural parameter is changed after accepted timing.
