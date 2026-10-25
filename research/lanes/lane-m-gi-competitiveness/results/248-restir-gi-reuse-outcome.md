# 042: receiver-frame SDK ReSTIR GI reuse — implementation 6/6, null-trial bias confirmed 6/6, quality 0/6

**RECEIVER_FRAME_REUSE_IMPLEMENTATION_PASS_6_6_NULL_TRIAL_BIAS_CONFIRMED_6_6_QUALITY_0_6.**
Unmodified RTXDI 3.1.0 GI temporal and spatial resampling now runs on actual
M001 static targets with 041 receiver-local positions converted owner→receiver
only at the SDK load boundary. Every full-record reservoir replays exactly on
CPU, the explicit null-trial normalization removes the large MISS-as-empty
bias, but no configuration meets the unchanged image gates. No accepted timing,
memory advantage, architecture promotion or Lane M completion.

Registration [042](../experiments/042-receiver-frame-restir-gi-reuse.md)
`d576bc75`, [042a replay boundaries](../experiments/042a-replay-boundary-addendum.md)
`7e9dbef3` and [042b development disclosure](../experiments/042b-development-smoke-disclosure.md)
`7c41269a` precede implementation `450bfebf`. Evidence:
[preparation246](246-restir-gi-reuse-cpu-preparation.json),
[six targets247](247-restir-gi-reuse-six-targets.json),
[verification249](249-restir-gi-reuse-verification.json).

## Implementation and audit

- CPU preparation: new host and independent float64 brute-force visibility tool
  (UBSan, `-Werror`), five HLSL stages compiled/validated/disassembled, 12 new
  contracts (transform exactness, RNG vs qualified 034 sampler, address maps vs
  033, offsets, zero-contribution rule, null-trial temporal normalization,
  spatial counting, visibility classes, agreement detector, seeds, normals) and
  six unusable-ICD native input checks. Exact 041 producer SPIR-V and 033
  neighbor-offset bytes reused; no old successful test rerun.
- Six ordered GPU processes (H01/B2 … H03/B8), each 4 streams × 64 frames × both
  variants, 117,248 dispatches; per-frame image readback, full records at
  frames 0/1/63. Owned true peak 50,317,088–77,974,240 bytes, zero teardown,
  no shader error flag in any of 1,536 frames.
- Supervised numeric workers replay 72 full-record frames: initial reservoirs,
  temporal and spatial SDK resampling and final shading for both variants
  (2,091,264 replayed output reservoirs) with 930,810 independent visibility
  queries. Transformed positions, M, age and selection agree exactly; W within
  1e-4. **Unexplained divergences 0, explained (near-boundary) divergences 0,
  unstable final visibility 0.** Primary direct is bit-identical in all frames.
- Development (042b): two disclosed H01/B2 smoke processes at stream base 16, no
  quality computed. Smoke 1 exposed a host defect: bias-correction enum 2
  (PAIRWISE, unsupported in GI, i.e. BASIC) instead of RAY_TRACED 3, caught by
  the replay as a W mismatch with stable occluded visibility. Fixed before the
  registered preparation; smoke 2 replayed with zero divergences.

## Quality and bias (unchanged gates, 16384spp references)

| Target | V1 pooled indirect bias | V0 (MISS M0) bias | PT bias | Q2 64-frame indirect NRMSE V1 / PT | Warm per-frame indirect NRMSE V1 / PT 1spp | Q1 | Q2 |
|---|---:|---:|---:|---|---|---|---|
|H01/B2|+0.55%|+363%|−0.07%|18.2–21.5% / 19.6–19.8%|54.5% / 156.9%|0/4|0/4|
|H01/B8|+0.86%|+377%|−0.12%|20.5–20.8% / 22.1–22.7%|56.4% / 177.3%|0/4|0/4|
|H02/B2|−0.26%|+258%|+0.20%|18.8–21.3% / 18.5–19.3%|47.2% / 150.8%|0/4|0/4|
|H02/B8|+0.43%|+356%|+0.52%|20.6–23.2% / 22.3–22.9%|53.2% / 182.1%|0/4|0/4|
|H03/B2|−0.73%|+258%|−0.32%|21.4–24.2% / 18.8–20.3%|53.5% / 154.8%|0/4|0/4|
|H03/B8|−0.09%|+296%|+0.12%|22.9–25.5% / 22.5–23.4%|56.5% / 177.9%|0/4|0/4|

- **H_null holds 6/6**: V0−V1 bias difference 2.58–3.77 versus standard errors
  0.03–0.08. Treating a secondary MISS as an empty reservoir (041 policy)
  over-weights the hits that remain and multiplies indirect energy ~3.6–4.8×.
  Counting each MISS as one zero-contribution trial keeps the pooled bias
  within ±0.9% on all targets (B2 6/6), comparable to PT's.
- **Q1 0/6**: no stream passes cold or warm. Warm V1 per-frame indirect error is
  ~3× below 1spp PT (≈9–12 spp equivalent) but still 47–57%.
- **Q2 0/6**: after 64 static frames V1 is NOT better than PT built from the
  same paths (PT/V1 NRMSE ratio 0.83–1.10; worse on H03). Temporal/spatial
  correlation consumes the per-frame gain under accumulation.
- Diagnostic GPU time per frame 0.84–1.39 ms including the 1spp producer
  (0.30 ms at B2); uncalibrated, not accepted timing.

## Scope and limits

Static H01–H03 only, one AMD Radeon 8060S/RADV. Boiling filter, sample-app
final MIS and checkerboard were NOT_RUN. RAY_TRACED correction still excludes
neighbors by realized Jacobian (SDK behavior). Only primary-visible pixels
(6,748–7,670 per target) carry surfaces. Earlier stops (035/037/038/040) and all
M001 losses are unchanged. ReSTIR GI is now a qualified, explicitly normalized
family baseline with measured per-frame variance reduction, not a competitive
architecture. A separately registered denoised/reconstructed pipeline and
matched-quality calibrated timing remain required; full Lane M is incomplete.
