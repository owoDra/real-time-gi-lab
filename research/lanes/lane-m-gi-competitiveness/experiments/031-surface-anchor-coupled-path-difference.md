# Surface-anchor coupled path difference: fixed CPU feasibility

2026-10-25. Baseline3b2980e8. Registered BEFORE031 implementation, tests,
geometry/anchor selection, new candidate paths or scores.029 remains stopped;
030 remains six quality rejections, no extra samples/tuning/GPU continuation.
This is a different physical path-difference estimator, not a rescue of030.

## Hypothesis and prior art

A geometry-only representative receiver can supply an absolute irradiance
estimate, while complete physical paths from that receiver and a neighboring
receiver share random numbers at every bounce. Can their difference plus the
representative's independent absolute estimate pass every original full-image
HDR gate and achieve>=1.20 complete CPU ray-query variance efficiency on EVERY
H01/H02/H03 B2/B8 target? This tests coupling across physical paths, not a wider
incident-direction fit, more030 samples or reference reconstruction.

Control variates, correlated differences and reuse are prior art. In particular
[ReSTCV2026](https://hercier.github.io/restcv/) reuses correlated estimates and
pixel differences with reservoirs; [ReSTIR GI2021](https://research.nvidia.com/publication/2021-06_restir-gi-path-resampling-real-time-path-tracing)
shares indirect paths across pixels/time. [Primary-space control variates2021](https://mcrespo.me/publications/primary-space-cv/)
also address high-dimensional residuals.031 is NOT a reproduction of these
methods, a qualified ReSTIR-family comparison, or a novelty claim. Proposed
bounded owner-anchored storage/dependencies and eventual dynamic architecture
remain unproven. It does not satisfy the charter's fair representative families,
new heldouts, dynamics/devices/full-system cost/novelty gates by itself.

## Fixed physical model and estimator

Use the SIX immutable original admitted16384spp/four-seed scene.n008 inputs
and original026 geometry/owner/material metadata, with exact full provenance
through published163/165. No new reference, camera precision change, environment,
albedo, sidedness, light, finite bounce boundary or far/offset convention.
Candidate paths are NEW CPU candidate data, not independent reference samples.
Use pinned N008 Oracle::sample with center primary, unit-grey two-sided opaque
nonemissive surfaces, point lights only, original soft falloff and finite B2/B8.
Its offset/edge inset remain original CPU-oracle semantics, not GPU-float32 proof.

For observability, create a PRIVATE out/ header copy with reversible changes
ONLY: namespace rename, add closest_queries counter to RenderCounters, increment
it before the single Oracle::sample bvh.closest call. Shadow counts already
exist. Preserve tracked N008 source and all historical code. Commit overlay,
new kernel/native/tests/runner before compilation/tests. Verify inverse bytes,
compiler/dependency identities and counted-vs-original radiance/primary/shadow
contracts. Never link this study into the Renderer/default build.

Compute all center-primary records and physical offset origins/normals in CPU,
BEFORE new radiance. Require exact original admitted primary hit records.
Map triangle order to immutable original owner/material metadata and verify
all scene triangle vertices. Build the unchanged geometry-only owner-relative
world-axis8^3 partition/key rule from029 (with actual CPU origins/normals,
round1024 normal, sky group-1). Different float precision may change a boundary
key; record actual complete mapping. For EACH group choose its median increasing
linear pixel ID as representative. No radiance-dependent selection or merging.
Freeze full primary/group/representative artifacts before candidate path calls.

For each of the four original independent N007 seed words, render1024 absolute
indirect samples at each representative, in a domain-separated random stream.
For EACH active pixel p render16 pairs of full physical paths: F(p,U_j) and
F(a(p),U_j), initializing/cloning the SAME RNG state (seed,pixel,sample) for
both complete Oracle calls. Same cosine random coordinates until either path
terminates; no reconnection, Jacobian, retrained field, reservoir, rejected
visibility event, truncated residual or tail substitution. Save all values.
The signed candidate is mean_1024 F(a,V) + mean_16[F(p,U)-F(a,U)].
Display clip=max(signed,0) is scored separately. Representative bank streams
are independent of pair streams by fixed XOR domain0xa031a031a031a031;
pair streams use original seed, target pixel ID, sample0..15. Full finite-depth
physical paths/direct/visibility remain unchanged, including misses/zeros.
The equality E[F(a,V)]+E[F(p,U)-F(a,U)]=E[F(p)] is a continuous/marginal argument,
not exact finite-RNG unbiasedness proof; clipping is not unbiased.

Baseline32 full local paths uses the same16 local pair paths plus16 NEW local
paths at sample indices16..31. No extra baseline rendering or path-budget
substitution. Candidate direct is actual first local path direct, shared
bit-exactly with baseline; point lights make it deterministic. Sky remains zero
and in ALL57,600 denominators. All four seed images are distinct trials;
DO NOT average them into an easier quality decision.

## Costs, gates, independent verification and stops

Count actual closest+shadow queries separately for each complete role. Candidate
charges ALL1024 representative paths for EVERY group/seed plus both sides of
ALL16 pairs, each including repeated primary/direct work of Oracle::sample,
and full primary geometry scan. Baseline charges ALL32 local paths and the
same full scan. No free bank, amortization over unmeasured future frames or
hidden physical samples. Preserve per-pixel/representative counts and all
raw values. This is CPU query-count efficiency, not GPU timestamp speed,
calibrated Renderer costs, device memory, or accepted quality-matched ranking.

Let Vb,Vc be sums over all pixels of unbiased sample variance across the FOUR
separate baseline32 and signed candidate seed images, ddof1. E=Vb*Qb/(Vc*Qc)
with complete-role total queries, finite positive, must>=1.20 on EACH target.
This four-seed empirical proxy has no declared confidence interval or universal
variance guarantee. Baseline images are descriptive, not a gate exception.
On EACH seed separately BOTH signed/clipped candidate totalNRMSE<=.05,
indirectNRMSE<=.10,absolute signed indirect energy bias<=.05; directNRMSE<=1e-4,
maxabsolute<=1e-5 and zero nonpositive lost-positive support. Use original full
fourseed16384spp mean/BT709 luma, no signal masks or exclusions. Require ALL24
seed-target decisions AND all6 E gates for CPU_FEASIBILITY_PASS; otherwise
preserve every finite loss and reject before GPU. No sample/grid/anchor/split
or threshold changes or in-study tuning.

References may be decoded ONLY after all candidate raw paths/images freeze.
New independent Python audit rehashes complete inputs/native payloads, checks
all primary/group/anchor data, ALL sample coverage/nonnegativity, exact local
control reuse, complete path/query accounting, independently fsum absolute/
difference/control means, signed/clip/direct images and full HDR errors,
variance and final decisions. Image agreement rtol1e-10,atol1e-12 times maximum
absolute physical sample (floor1e-20); metric/variance rtol1e-8,atol1e-12 times
that scale. Save full audit arrays. Sampled original-vs-counted Oracle contracts
and exact reversible-source proof qualify transport semantics; audit does not
pretend to independently trace every new path. No successful old suite rerun.

Actual pre-experiment CPU contracts must cover original/count radiance/primary/
shadow agreement, actual closest counts/termination, identical receiver pair
cancellation, signed differences/no clip inside estimator, physical marginal
RNG-clone equivalence, zero/miss paths, constants, finite-depth boundaries,
nonnegative direct/physical values, opaque ownership and geometry-only median
anchor mapping, malformed/overwrite/no-GPU commands and durable phase inputs.
Commit all code before execution. Exclusive canonical out/m001-anchor031-* data;
all logs, sources, compiler dependencies, raw values and failed partials remain.

One worker/no GPU; limits per native production process1200CPU/1800wall seconds,
4GiB address space; preparation/independent Python360CPU/600wall/4GiB, BLAS/OMP1,
16GiB free disk. Native writes seed progress; observe SAME live handle/PID,
never restart a timeout/missing/truncated observation. Geometry and path commands
run once per target in order H01/B2,H01/B8,H02/B2,H02/B8,H03/B2,H03/B8; valid
scientific loss continues, ANY input/provenance/operational/numeric/timeout failure
stops031 with all partials and no retry/later target. Durable input manifests
precede geometry, path and reference phases and remain on failures. No GPU
continuation is selected even on CPU success; that needs a new registration.
No Actions/CI, N-history/default-build/main changes or power/clock/desktop changes.
Publish actual checks/limits, commit/push and update OPEN Issue7. Lane M remains
incomplete until the full charter, not this component, is verified.
