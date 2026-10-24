# Actual-normal product guide016: six CPU efficiency losses

2026-10-24. **REJECTED_NO_GPU:0/6conditions meet the fixed E>=1.20 gate.**
[Preregistration016](../experiments/016-normal-product-guide-cpu-feasibility.md)
was committed/pushed at4a9f02f6 before new implementation/sampling.
[Preparation103](103-normal-product-guide-cpu-preparation.json) and actual source
29e7ddc6 precede all acquisitions. H01,H02,H03 each ran once, in order, both
original depths/four seeds/1024spp. No additional016process or GPU implementation
is selected. Broader Lane M remains active and incomplete.

This standalone CPU proposal multiplies each frozen015 incoming-light direction
weight by max(dot(actual_oriented_normal,bin_center),0), quantizes the64products
with the unchanged2^24largest-remainder CDF, and uses the original half-cosine,
half-guide sampler and complete mixed PDF. Tangent-crossing bins still produce
below-surface directions: zero/null samples remain in the denominator, without
retry. All-zero products fall back to uniform sphere. Actual original N008
physical intersection/spawn/direct-shadow transport is unchanged. This is
established product-guiding prior art, not a novelty or independent-oracle claim.

[Full replay104](104-normal-product-guide-six-conditions-raw-replay.json) retains
all3new native receipts and their independent terminal audits. All45new payloads,
12full mean/variance arrays and393,216new candidate f64 render samples rehash and
replay. Independent math.fsum means/variances match, numerical tolerance5e-12
relative/1e-30absolute. No sample, seed, pixel or scene is excluded. New172,800
primary records and selected IDs exactly match015 and original admitted oracle
bytes; all primary direct arrays match original015cosine bytes exactly.

No training or cosine render path was rerun. The exact015 field/control bytes,
393,216cosine samples and original196,608training-path loop counts are **reused**;
training-path trajectories were not exported in015. The original450,494measured
training ray queries are charged again at each depth in the model. This is a
cost charge, not new training execution. Old pilot inventories/plans/build and
original physical/reference qualification chains are rehashed before sampling
and at independent terminal replay. All old records and outputs remain exact.

Each row uses64groups (four seeds×16geometry-selected pixels),1024samples each.
V sums their unbiased sample variances, including zeros. C counts role closest
and shadow queries, with the entire original field training additionally charged
to product at each depth. E=(V_cos*C_cos)/(V_product*C_product), requiring>=1.20
on every row. Query count ignores actual64products/quantization per continuation,
arithmetic/cache/divergence; it is not calibrated GPU timing. The diagnostic
charges the whole field to16pixels; full-image/temporal amortization was not
measured and is not inferred.

|Target|E, required>=1.20|V_cos/V_product|Cosine queries|Product+training queries|Product null paths|Decision|
|---|---:|---:|---:|---:|---:|---|
|H01/B2|0.509556289|1.468977364|77187|222519|1019|FAIL|
|H01/B8|0.459074949|1.561276526|100589|342095|1081|FAIL|
|H02/B2|0.660366248|1.942766698|74733|219861|1114|FAIL|
|H02/B8|0.393240432|1.283934148|98864|322792|324|FAIL|
|H03/B2|0.202419108|0.711704290|75030|263805|10220|FAIL|
|H03/B8|0.192980390|0.642243963|96050|319657|10601|FAIL|

Compared with015's24,957–32,564null paths, all six rows have fewer below-surface
nulls. Variance improves against cosine in H01/H02 but worsens in H03 at both
depths. Product query costs also increase relative to cosine in five conditions.
Thus fewer nulls alone do not establish feasibility; no causal or general
path-guiding family conclusion follows. No post-hoc mixture/grid/seed/threshold
change, extra samples, new reference, full-image quality admission or GPU trial.

26new actual kernel/UBSan checks PASS, including independent product masses,
actual field lookup/remaining depth, arbitrary-normal continuous quadrature,
complete PDF/support, retained nulls, weight<=2 and262,144actual two-transition
samples against an analytic expectation under a fixed6SE health guard. The
observed mean0.7125718236300083 agrees with0.7129634300859559 atSE0.001149900164115455;
this is numerical health, not a population confidence interval or quality gate.
Prior01525kernel checks are rehashed/reused, not identically rerun. Each new native
returns0 without timeout inside300CPU/600wall seconds/4GiB guards. CPU wall is
health only; no hardware/GPU equivalence is claimed.

No GPU, power/clock/desktop setting, CI/Actions or default CMake/Renderer change.
Total audited assistant GPU acquisitions remains120; human-operated historical
reference attribution stays unchanged. Default Renderer build/runtime regression
NOT_RERUN and validation layers NOT_RUN. Original N001–N010, static screen083,
013controls/quality losses and015negative result remain exact. New raw data and
proof receipts stay repository/out. [Verification106](106-normal-product-guide-cpu-verification.json)
records source/history/default-build/index preservation. Competitive architecture,
full-image quality-matched calibrated end-to-end GPU timing, dynamics, new heldouts
and representative devices remain open; no Lane M completion claim.
