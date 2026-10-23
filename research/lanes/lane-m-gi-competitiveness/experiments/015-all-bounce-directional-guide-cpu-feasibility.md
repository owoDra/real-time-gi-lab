# All-bounce directional-guide CPU feasibility

2026-10-24, source checkpoint dd739f12, before candidate code, training,
sampling or measurements. Observed-corpus development only. Completed013 and
M001 static results are immutable. No new reference, reference qualification,
architecture promotion, accepted timing or heldout claim follows from this study.

## Question and decision boundary

Can a bounded, independently trained directional proposal reduce the product of
sample variance and complete ray-query count by at least1.20 on **every** original
H01/H02/H03 at B2/B8, including its entire training cost? If not, reject this fixed
candidate before GPU implementation. This is a CPU feasibility screen, not a
substitute for calibrated GPU time, whole-image quality or real-time acceptance.
No follow-up sampling, new seed, grid/ray/rung changes or threshold tuning here.

Path guiding is established prior art, not our novelty claim: [Müller et al.,
2017, corrected authors' version](https://cgl.ethz.ch/publications/papers/paperMue17a.php).
[PBRT4 importance sampling/MIS](https://pbr-book.org/4ed/Monte_Carlo_Integration/Improving_Efficiency)
describes evaluating all proposal densities for a mixture. Our bounded candidate
tests a simple fixed field rather than reproducing an adaptive SD-tree. Existing
N007–N009 already diagnose missing secondary shadows/scalar probe aggregation;
do not rerun those studies or claim them as new findings. N010's rejected or
unadmitted guide/reference routes stay unchanged and are not consumed.

## Fixed candidate and transport

* Original BF-P grey rho=1, opaque two-sided triangles, black background,
  source point light/soft falloff, center-primary rays and B2/B8 finite vertex
  counts. Use the unchanged N008 CPU BVH, oriented normal, source spawn/nudge and
  direct/occlusion functions for this diagnostic. This candidate is **not** an
  independent oracle. A future GPU port must qualify its actual physical/numeric
  behavior separately; CPU double precision is not GPU float validation.
* One8×8×8world-space field over the exact triangle AABB. Each cell has64equal
  solid-angle bins:8uniform z bands×8azimuth intervals. Train exactly2directions
  per bin, at the cell center, with one fixed seed0x475549444531. Independently
  trace each direction and then cosine continuations through at most7vertices.
  Store cumulative incoming-light estimates for each remaining depth1…7. Record
  all65,536training paths and all training closest-hit/shadow queries per scene.
  No render sample or reference radiance trains the guide. The same training
  field serves both B2/B8; charge its **entire** cost to each separate comparison.
* Convert each64weight row to an integer CDF with total2^24, largest-remainder
  allocation and ascending bin-ID ties. Finite/nonnegative weights only;
  all-zero row falls back to uniform sphere. Sample integer categorical draws
  exactly; evaluate the **quantized** bin mass, never its pre-quantized weight.
  Within a selected bin sample uniformly in z/azimuth. No RGB reuse, biased
  radiance replacement, visibility approximation or temporal accumulation.
* At every continuation choose cosine hemisphere with probability1/2 or guide
  sphere with probability1/2, with disjoint RNG draws. Evaluate
  q(w|n)=0.5*max(dot(n,w),0)/pi+0.5*mass(bin(w))/(2^24*bin_area).
  Throughput multiplies by max(dot(n,w),0)/(pi*q). A guide direction below the
  surface terminates with zero; **no retry, rejection renormalization or dropped
  denominator**. Cosine support bounds each continuation multiplier by2. For a
  fixed field, the continuous mixture estimator preserves the finite transport
  integral by conditional expectation. Finite precision, RNG discretization and
  a future GPU implementation remain numerical validation obligations, not
  an assertion of bit-exact or globally unbiased physical GPU behavior.
* Empty spatial extents: expand only zero-width axes to1e-9 times max(1,AABB
  diagonal); field lookup clamps to the registered AABB cells. This changes the
  proposal only. Scene geometry, camera, light and path intersection never change.

## CPU implementation, tests and finite pilot

Standalone new source/header/tests under lane_m only; no default CMake changes,
Renderer integration or N001–N010 edits. Before pilot, compile actual candidate
with C++20, -O2, -fno-fast-math, -ffp-contract=off; test integer-CDF normalization,
categorical boundaries/zero bins, overflow/nonfinite rejection, sphere partition,
mixture PDF and full cosine support, null outcomes, throughput bounds and a
finite two-transition integral with an independently enumerated expectation.
Test the actual kernel used by the candidate, not a prose-only emulator.

Pilot order H01,H02,H03, each one CPU process, both depths. Load the exact original
admitted B8canonical scene bytes (already contain all original physical state).
Read no old indirect image to choose positions. Trace all320×180center primary
rays; choose16hit pixels at sorted-hit indices floor((k+0.5)*Nhit/16), k=0…15.
This geometry-only selection is fixed, explicitly observed-development data and
not representative full-image/heldout scoring. Original admitted B2/B8reference
means may be read **after** selection only for diagnostic errors; no admission
from a16pixel subset. Render cosine control and guided candidate at1024spp for
each selected pixel and original four N007seed IDs. Keep all samples as f64;
retain per-seed/per-pixel means, second moments and complete query counts.
Training and rendering streams are disjoint, and the field freezes before either
render role. No in-path guide update. Coupling between roles/seeds is diagnostic;
no population confidence interval or general variance-reduction guarantee.

Define V_role=sum of all64per-pixel/seed unbiased sample variances, with every
sample including misses/nulls/zeros. Define C_cosine=all cosine rendering
closest+shadow queries, C_guided=all guided rendering queries+all training queries.
For each depth E=(V_cosine*C_cosine)/(V_guided*C_guided). Both variances/costs must
be finite/positive; zero/undefined evidence is INELIGIBLE, never a win. All six
E≥1.20 inclusive is CPU_FEASIBILITY_PASS. Otherwise record every loss and classify
REJECTED_NO_GPU. This proxy ignores arithmetic/cache/divergence costs, so even a
PASS only permits separately registered GPU implementation/qualification. CPU
wall is health only. No calibrated speed or memory win from query count.

No pixel/scene/seed exclusions, extra training or replacement. Keep full integer
CDFs, raw training weights, all64×1024samples per role/depth and full primary hit
selection under repository/out. Hash original scene/header/source and all new
artifacts. Each CPU process: at most300CPU seconds/600wall seconds,4GiB address
space, one thread; fail/timeout preserves partial output and stops study as
INVALID, never retry. Require16GiB disk before pilot. A scientific efficiency
loss does not skip the remaining fixed CPU scenes. No GPU execution in015;
no power/clock/desktop settings, CI/Actions, old-output overwrite or new reference
sampling. Commit/push all outcomes and update Issue7; Lane M remains incomplete.
