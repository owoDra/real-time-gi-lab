# Prospective light-surface proposal for offline reference sampling

Date: 2026-10-15 JST. Parent checkpoint: `8c8e05a`.
Registered before building or acquiring this candidate. This is a bounded N010
sampling repair candidate, not a new GI Renderer, Lane M campaign or N011.

## Motivation and falsifiable boundary

Post-hoc motivation is 136/137: the global triangle proposal has about 80.63%
null-ending paths, with worse first-level precision than original cosine.
Its complete C1 B8 levels 8192/16384 remain INELIGIBLE. No statistical cap
failure has been observed. Existing acquisitions and plan-039 boundary work
continue unchanged and retain their outcomes.

Test whether sampling light-visible surface points can improve this reference
estimator while preserving the exact independent physical integral. The current
triangle proposal samples uniformly within each triangle, missing small bright
regions inside large faces. Geometry and direct-light information alone define
the new proposal; no candidate indirect image or GI quality score trains it.

## Exact proposal and density

Keep 75% cosine / 25% guidance. Select a point light with probability proportional
to its maximum nonnegative intensity channel; zero total weight means pure
cosine. Use the same two random dimensions: remap the first through the light
CDF, then sample a uniform sphere direction. Trace from that light using the
unchanged BVH and first hit beyond the existing offset. The hit point is the
proposed continuation target. Misses, negative shading hemispheres and targets
hidden from the shading origin are explicit null samples, retaining earlier
radiance contributions.

At a target y, the proposal's surface density is the sum over all point lights:
`q_A(y) = sum_l P(l) * first_hit_l(y) * abs(n_y dot w_l) / (4*pi*r_l^2)`.
Convert to a direction density at the shading origin x with
`q_omega = q_A(y) * distance(x,y)^2 / abs(n_y dot w_xy)`.
Evaluate the same first-hit support when computing density for a cosine sample.
Weight continuation throughput by `cosine_pdf / (0.75*cosine_pdf+0.25*q_omega)`.
The positive cosine component preserves all hemispherical support; the maximum
single continuation correction remains 4/3. Empty guidance uses cosine density
and correction 1. Guide rays do not consume transport random dimensions or
alter any radiance, geometry, sidedness, clipping, offset or finite-depth rule.
In particular, the density Jacobian does **not** replace N001 soft-light falloff
in the unchanged radiance evaluator. No light-path radiance is added.

The solid-angle/surface-area Jacobian follows the probability-density conversion
in [PBRT, Bidirectional Path Tracing](https://www.pbr-book.org/3ed-2018/Light_Transport_III_Bidirectional_Methods/Bidirectional_Path_Tracing).
This proposal is an offline sampling mixture, not a claimed implementation of
the complete PBRT bidirectional integrator. Mathematical construction alone
does not establish implementation validity or lower variance.

## Ordered proofs, classifier and stop rules

1. Build 144 copies the pinned original point-guided standalone sources, changing
   only the proposal and its density evaluation. Construct a prefix executable
   with the exact existing loader overlay; prove source bytes outside render
   continuation match. Preserve all generated sources, commands and binaries.
2. Physical 145 reruns all seventeen original scenes/four seeds, eight physical
   checks and two independent retained 16384-spp iid comparisons. Keep every
   original threshold: exact primary/direct/emission records, finite/nonnegative
   means/moments, bounded counters, iid per-channel mean difference <=0.2% and
   NRMSE <=1%. Prospectively include the metadata fields omitted in historical
   113, derived exactly as in replay 125. Old 113/125 remain unchanged.
3. Only after complete physical PASS, validate all 24 locked low-dose states
   and both actual-level C7 own-prefix transports with all four seeds and the
   existing exact payload/counter continuation gates (78 native invocations).
4. Only after complete physical/state/prefix proof, acquire fresh C1 B8 four-seed
   8192 and 16384 levels. Import no cosine/global-guide samples or moments.
   Preserve all pixels, components, means/moments, counters and screen inputs.
   Compare each level's active absolute p99 uncertainty with the corresponding
   immutable global-guide levels archived by 137. The minimum practical
   feasibility effect is >=25% lower uncertainty at **both** levels, with stable
   full signal support. This is a bounded feasibility classifier, not a powered
   variance-superiority claim or reference eligibility. A failed feasibility
   candidate stops; no parameter search, scene deletion or silent rerun.

Physical/state controls retain four threads, 4 GiB, 21600 aggregate CPU seconds
and 3600 elapsed seconds per invocation. The two full-image feasibility levels
use sixteen threads, 4 GiB, 691200 aggregate CPU seconds and 43200 elapsed
seconds per invocation. All operations are CPU only and offline. Runtime or
provenance failure stops without automatic retry; preserve partials and failures.

Any reference acquisition/admission transition after feasibility needs a separate
prospective record covering all nine unfinished slots within the same 24-slot
corpus. Every reference still needs the original four seeds, six-level ladder,
262144 cap, active p99 <=1e-5 / <=5%, stable support and first consecutive
qualifying pair. Do not select a new view based on GI wins/losses or admit this
prototype from build/control success. Current view 127, source/binaries, timing
gates and independent operational transition remain frozen. No GPU acquisition,
power/clock change, CUDA, default build change or N001–N009 result modification.
