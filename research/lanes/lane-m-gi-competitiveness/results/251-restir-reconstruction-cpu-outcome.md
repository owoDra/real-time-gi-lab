# 043: ReSTIR reuse frames through the fixed quadratic reconstruction — per-frame 0/6

**RECONSTRUCTED_RESTIR_PER_FRAME_0_6_STATIC_ACCUMULATED_V1_4_6.** CPU only, no
new rendering, sample or GPU. Registration
[043](../experiments/043-restir-reuse-quadratic-reconstruction-cpu-screen.md)
`50186de8` and [control-bound addendum043a](../experiments/043a-reconstruction-control-bound.md)
`3149970f` precede implementation; [summary250](250-restir-reconstruction-cpu-screen.json).

The unchanged 018/022 geometry-only quadratic reconstruction (archived 022 GPU
coefficients) was applied to the published 042 per-frame V1 (explicit null
trial) and raw 1spp PT indirect images. Preconditions pass: all 72 record-frame
primary hit buffers are bit-identical to 022, and the reused CPU filter
reproduces every archived 022 GPU stage within 2.5% of the 022 stage bound.
Five new contracts and one supervised CPU1200/wall1800 worker ran once.

| Target | R1 V1+recon warm indirect NRMSE (4 streams) | R1 PT+recon warm | R2 64-frame V1+recon passing | R2 PT64+recon passing | Reference bias |
|---|---|---|---:|---:|---|
|H01/B2|12.5–15.1%|33.1–33.7%|4/4|4/4|PASS 0.92%|
|H01/B8|15.0–15.6%|38.9–41.0%|4/4|4/4|PASS 1.26%|
|H02/B2|14.1–16.0%|42.7–43.8%|4/4|4/4|PASS 1.87%|
|H02/B8|15.4–17.6%|47.3–49.1%|4/4|4/4|PASS 2.49%|
|H03/B2|21.6–25.1%|59.6–64.5%|0/4|3/4|PASS 0.60%|
|H03/B8|23.4–26.4%|71.4–75.1%|0/4|1/4|PASS 1.47%|

- **R1 0/6 (and 0 of 384 warm V1 frames)**: reconstruction lowers mean warm V1
  indirect error by 3.2–3.9× (H01/H02) and 2.3× (H03) but not to 10%.
  Cold frames stay at 29–92%. Mean warm total NRMSE is 2.3–4.0% on H01/H02 and
  4.7–6.5% on H03; the indirect gate decides.
- At the same 1 path/pixel/frame, V1+recon is 2.4–3.0× lower in mean warm
  indirect NRMSE than PT+recon, and below the published NRD026 frame-63
  indirect errors at 1spp (32–39%) and even at 64spp (25–34%). These are unequal-gate,
  uncalibrated-cost observations, not an accepted equal-cost win.
- **R2**: reconstruction of the 64-frame V1 mean passes on 4/6 targets (all
  streams); PT64+recon passes the same four and 3/4 and 1/4 streams on H03. After
  accumulation the reconstruction favors PT (H01/B2 4.2–4.4% vs 6.4–7.2%):
  ReSTIR's spatially correlated reuse leaves structure the geometry filter
  cannot average.

Prediction (R1 fails most, R2 passes most) held. The per-frame route stops here;
static accumulation is a convergence diagnostic, not a real-time result. A
same-cost comparison of 1-path real-time families needs a separately registered,
calibrated timing study with integrated GPU reconstruction costs. No timing,
memory, novelty, architecture promotion or Lane M completion.
