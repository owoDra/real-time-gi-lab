# All-bounce directional guide015: CPU feasibility rejected; no GPU continuation

2026-10-24. [Preregistration015](../experiments/015-all-bounce-directional-guide-cpu-feasibility.md)
was committed at d5618a58before candidate implementation or sampling. Actual CPU
kernel/build/25contract checks099and source b9aa0e08precede all three acquisitions.
H01,H02,H03each completed once, in order, both depths/all four original render
seeds. All six registered efficiency conditions FAIL: REJECTED_NO_GPU. No GPU
implementation or acquisition is selected for this fixed candidate. Lane M
remains active and incomplete.

The candidate uses the unchanged N008 double CPU BVH/spawn/direct-shadow kernel
and BF-P physical scene. A fixed8³world grid stores64equal-solid-angle direction
bins per remaining depth1…7, trained with2paths/bin. An integer2^24CDF records the
actual quantized sampling probabilities. Every continuation uses the full1/2
cosine+1/2guide PDF and cosine/(pi*q) throughput. Below-surface guide draws are
zero-valued samples, never retried or removed. Conditional continuous-estimator
reasoning is not a claim of exact finite-precision/GPU unbiasedness. This is
prior-art-based development, not a novelty or independent-reference claim.

[Replay100](100-all-bounce-guide-cpu-feasibility-raw-replay.json) rehashes all75
payloads (including24score arrays), recomputes786,432retained f64 render samples and
independently checks sample variances using math.fsum. All original scene,
reference, CPU source and build identities remain exact. All172,800primary
records (three full images) match original oracle hit bytes exactly. Geometry-only
selection fixes16hit pixels per scene before reading reference radiance. CDF
normalization/monotonicity, finite weights, quantized masses, full sample coverage,
nonnegative finite values and exact saved-array replay pass. No statistical or
whole-image quality admission follows from a16pixel diagnostic subset.

Each table row includes all64pixel/seed groups at1024spp. E is
(V_cosine*C_cosine)/(V_guided*C_guided), requiring≥1.20inclusive on all six rows.
V sums unbiased per-group sample variances, including all zeros/misses/nulls.
C counts all role rendering closest-hit+shadow queries; guided additionally pays
its entire training cost, separately at each depth. The field is shared between
B2/B8but no training cost is discounted. The cost column is a query-count proxy,
not CPU wall/GPU time or a full-frame speed result.

|Target|E, required≥1.20|V_cosine/V_guided|Cosine queries|Guided+training queries|Guided null samples|Decision|
|---|---:|---:|---:|---:|---:|---|
|H01/B2|0.318714802|0.731970059|77187|177270|27161|FAIL|
|H01/B8|0.342718525|0.658244846|100589|193197|32564|FAIL|
|H02/B2|0.487905134|1.130832915|74733|173211|28564|FAIL|
|H02/B8|0.267757459|0.516483404|98864|190701|31919|FAIL|
|H03/B2|0.219756667|0.709164108|75030|242125|24957|FAIL|
|H03/B8|0.209372903|0.554664896|96050|254453|28862|FAIL|

All196,608training paths are included in the source-fixed loop counts, with
450,494actual training closest/shadow queries. Retained training
artifacts are complete pre-quantized per-cell/depth/bin weight tensors and CDFs;
individual training trajectories are not exported. Full raw render samples and
all per-group moments are retained. No rendering/reference samples train the
field. The small16pixel diagnostic charges the full field; amortization over a
full image or temporal reuse was not measured and is not inferred. Variance
alone also worsens in most conditions, so training cost is not the sole issue.
These measurements do not establish a causal diagnosis or reject path guiding
as a family. No in-study grid, sample, seed, mixture or threshold tuning.

099preserves the first failed preflight: a nonexistent Python Git-helper method
raised before compilation/native execution. The identified local Git helper
repair uses a new v2build output; v1is untouched. UBSan actual-kernel tests pass,
including all16,777,216categorical draws, PDF/bin/support/null/weight predicates
and262,144two-transition samples against an analytic expectation (6SE health
check, not a research confidence interval). No test suite or native acquisition
was repeated merely to improve a result. All three CPU natives return0 without
timeout and stay within300sCPU/600swall/4GiB guards. CPU wall is diagnostic only.

No new reference sampling or old output/source/evidence overwrite. Original
N001–N010and013/static-screen outcomes stay unchanged. All new code is standalone;
default Renderer/CMake integration, build and runtime regression NOT_RUN;
validation layers NOT_RUN. This study executed no GPU or power/clock/desktop
change, added no CI/Actions and made no accepted speed/memory/architecture claim.
Raw samples/fields/maps stay repository/out. Broader Lane M's quality-matched
competitiveness, new heldout/dynamic/representative-device and timing gates
remain unmet. [Verification102](102-all-bounce-guide-cpu-feasibility-verification.json)
records source/history/default-build/index preservation.
