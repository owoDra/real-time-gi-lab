# N010 → Lane M handoff (753)

2026-10-21 JST. Issued on the strength of [751](751-r1-full-readiness-outcome.md)
`READY_FOR_LANE_M_FIRST_COHORT` (six gates PASS). Target lane:
[lane-m-gi-competitiveness](../../lane-m-gi-competitiveness/README.md) (distinct from
the historical topology-backend Lane M). No N011. This handoff makes the comparison
executable; it does not start the accepted campaign or establish any speed result.

## 1. References

- Corpus: lock026, 24 slots = 12 cells × {T_B2, T_B8}, original four seeds.
- View: [747](747-full-corpus-r1-reference-view.json), work root
  `out/research/n010-comparison-readiness/full-corpus-r1-view-v1` (symlinks).
- 16 slots pass the original001 screen. 8 Sponza slots (C1–C4 T_B8, C5/C6 T_B2/T_B8)
  are **R1_STATISTICALLY_ELIGIBLE** at16384 under plan174 (pooled-reference noise ≤
  one tenth of each scored target) and remain original-screen INELIGIBLE. Score them
  only through `r1_reference_provenance.verify_reference` / `.score`; every score
  carries `eligibility_rule`. Report R1 use beside any result that depends on it.
- Estimator: original digital-shift RQMC oracle family only (009/022/050 proofs).

## 2. Unresolved correctness (carried, not masked)

- N009 direct max-relative-error1.0 pixels on Sponza: **UNRESOLVED/未解決**, included
  in every score; no mask, exclusion or seed substitution.
- All-split/compensated627 estimator: unadmitted (735/742); not a reference route.
- R1 does not prove physical correctness or global bias bounds beyond the original
  oracle's controls.

## 3. Comparators (first cohort)

Frozen incumbent RC (HWRT; software where the capture API supports it), vanilla
traversal control, dense repository RC estimator control (1 spp) and independent GPU
pixel PT (B2/B8). DDGI (RTXGI `f33e496c…`, Vulkan/AMD, no CUDA) is the required
additional family; its adapter, finite-depth transport, ledger, dynamic history and
full-boundary calibration must be qualified in Lane M before DDGI comparisons.

## 4. Quality conditions

`score_hdr.py` on linear HDR, whole image, all pixels: total NRMSE ≤5%, indirect
NRMSE ≤10%, |indirect signed sum bias| ≤5%, normalised by reference luma RMS. Fixed
PT budget ladder 1/4/16/64/256/1024 spp; selected budget = lowest passing level with
the original thresholds (all 28 selected PT boundaries are n1024, every frame PASS).
Incumbent/traversal/dense-RC FAILs at their fixed budgets are comparison outcomes
(750: all scored frames FAIL); report them as quality losses, never as a
same-quality speed ranking.

## 5. GPU time

Axis: GPU Renderer time from Vulkan timestamp queries (`renderer_gpu_us` /
`full_renderer_envelope_gpu_us`), per frame including transition/recovery frames;
CPU wall and readback are diagnostics. The 36-boundary selected scope (503) is
complete and valid but **TIMING_INCONCLUSIVE** (120/147). Before any speed claim:
prospectively register hypotheses, held-out states (locked before viewing indirect
output), family budget ladders and tuning split; calibrate the actual selected
boundary with the order-aware ranked method (100/103, 255/256, 377) including
multiplicity; pin binaries, shaders, budgets, resolution, readback/output mode and
frame lifecycle. N010 pilot timing is tuning/pilot evidence only. Descriptive
medians (751): PT n1024 non-Sponza ≈2.1–2.3s/frame; Sponza B2 ≈4.2–6.9s, B8
≈12.4–17.6s.

## 6. Peak memory

Owned-Vulkan allocation ledger (`n010-allocation-lifetimes/1`): replay all
allocation/free events, record persistent, transient, startup and recurring peaks
and true peak (including simultaneous old/new AS/upload), require zero live bytes
at teardown and the 8GiB owned cap. Driver-private and CPU memory are excluded and
must be stated. 751: PT true peak 3.29MB (non-Sponza) to 107.4MB (Sponza), all
teardown-zero; 750 incumbent HWRT up to 416.9MB.

## 7. Execution environment

Radeon 8060S (RADV), `scripts/run_with_vulkan.sh`. Python
`out/research/n010-comparison-readiness/venv` (3.13.13, NumPy2.5.4) with
`LD_LIBRARY_PATH=$NIX_LD_LIBRARY_PATH`, `OPENBLAS_NUM_THREADS=OMP_NUM_THREADS=1`.
One native GPU capture at a time; `quiet()` refuses captures while any `n010_`
worker runs. Raw corpus (~233GiB) is local and not fully backed up (741).

No single-GPU generality, scene omission or quality-unmatched superiority claims.
