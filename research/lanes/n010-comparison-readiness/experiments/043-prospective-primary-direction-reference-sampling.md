# Prospective primary-position directional reference proposal

Date: 2026-10-15 JST. Parent checkpoint: `0249537`.
Registered before this candidate is built or measured. The user-stopped 029
calibration remains partial; completed HWRT/software rows fail their unchanged
gates. No old computation is restarted. Plan 040 remains a stopped failure.

## Question and comparison boundary

Can a direction distribution conditioned on the actual primary surface reduce
offline reference uncertainty while preserving the independent physical
integral? Global triangle and light-surface proposals produced poor precision.
This distinct candidate uses visible directions from the shading point rather
than a global surface distribution. It changes sampling only, not a GI Renderer.

At the fixed center primary hit, partition the cosine sampler's uniform
`(u,v)` square into 16 by 16 bins. Evaluate four fixed subcell midpoints per
bin. Each pilot direction uses the original BVH, primary-ignore rule, secondary
far bound, sidedness, inset/offset and deterministic point-light direct evaluator
at its first hit. Its weight is the maximum RGB reflected direct radiance;
misses/backfaces/zero reflectance have zero weight. No pilot contribution enters
radiance sums or moments, and no candidate GI output trains the distribution.

The 256 bin probabilities are proportional to these four-score sums. Cache
the deterministic CDF per primary pixel, shared across the four sequential
replicates in one process, rebuilt identically in a fresh prefix process.
This costs 1024 pilot rays per reached primary pixel and approximately 2056
bytes per image pixel. Pilot construction is part of offline CPU cost. It uses
no transport random dimensions, no stochastic adaptation and no sample import.

For the **first continuation only**, use 50% original cosine / 50% histogram.
Later continuations remain original cosine. The two original uniform dimensions
select/remap the mixture and bin and then position within that bin. For a bin
of probability `p`, the density relative to the original cosine distribution is
`0.5 + 0.5 * 256 * p`. Multiply continuation throughput by its reciprocal.
Positive cosine support is retained everywhere, with correction at most 2.
An entirely zero CDF uses original cosine and correction 1. Jittered primary
and emissive scenes remain outside the existing RQMC executable's scope.
There is no sampled surface target and no target-mismatch rejection.

Keep the original radiance evaluator, finite vertices, primary/direct/emission,
geometry, light falloff, all pixels, four N007 seeds, Sobol table and moments.
Uncertainty is computed from replicate means, not iid per-path moments.

## Ordered evidence and stop conditions

1. Build 151 generates the pinned cached cosine sources and a separately named
   standalone/prefix pair. An inverse overlay must reproduce the entire cached
   header exactly; prefix construction retains the existing byte-equality guard
   outside render continuation. Freeze generated sources and binaries.
2. Physical 152 applies all seventeen original scenes/four seeds, eight physical
   checks and two retained independent 16384-spp iid comparisons. Retain original
   exact primary/direct/emission/headers, finite/nonnegative moments and bounded
   counters; iid mean-channel relative difference <=0.2%, NRMSE <=1%.
3. Only after complete physical PASS, state/prefix 153 checks all 24 locked
   states at 16 spp with own 8-to-16 prefixes and both C7 transports with actual
   8192-to-16384 prefixes. All 78 invocations, payload bytes and counters must
   satisfy the existing exact gates. Failure stops without tuning or retry.
4. Only after complete 151/152/153 PASS, bounded feasibility 154 acquires fresh
   C1 B8 four-seed 8192/16384 levels. Compare **both** active absolute p99 values
   against the original cosine levels in the immutable recovery qualification
   SHA256 `9da5eece00c7e1e490a35aefceb0a54f7ea42b0a90b4ad655d6713c482a9fa8f`.
   Require <=0.75 uncertainty ratio at both levels, stable full signal support,
   and exact deterministic components/primary records. This is a practical
   feasibility screen, not a powered statistical superiority claim. Failure
   stops the candidate. Do not substitute the worse global-guide baseline.

Build/control/state work is CPU only. Control/state invocations retain four
threads, 4 GiB, 21600 aggregate CPU seconds and 3600 elapsed seconds. Full-image
feasibility retains sixteen threads, 4 GiB, 691200 aggregate CPU seconds and
43200 elapsed seconds per invocation. Runtime/provenance failure preserves
partials and stops without automatic retry. No GPU acquisition overlaps it.

Feasibility is not reference admission. A later separately registered corpus
transition must retain all already eligible targets and every one of the 24
required slots. Original six levels 8192 through 262144, first consecutive
qualifying pair, active p99 <=1e-5 / <=5%, support and cap rules are unchanged.
All final quality, correctness, timing, peak-memory and provenance gates remain.
Sponza direct max-relative-error-1.0 pixels remain **UNRESOLVED / 未解決** and
included. No N011, power/clock change, CUDA, Actions, active/default Renderer
promotion or N001–N009 result modification.
