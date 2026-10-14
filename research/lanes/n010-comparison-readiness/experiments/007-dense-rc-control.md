# N010 independent dense RC control

Source inspection found the historical N003 `VanillaSoftware` switches the
traversal backend but retains visibility-guided production and sparse hash
storage. Its new captures are therefore **traversal controls**, not an
independent unoptimised GI-family baseline. Preserve their names/provenance
and report this limitation explicitly; do not satisfy 001's GI-control gate
with that label alone.

Before its first image, freeze a separate dense, cache-free implementation
of the repository RC estimator. Every camera-visible pixel directly evaluates
its four cascade probe centres and eight octant-diagonal directions per
cascade, with the incumbent spacing/intervals, two-sided hit semantics,
unshadowed secondary Lambert and 16-bit radiance quantisation. Average eight
contributions per cascade, sum cascades; shared direct lighting and native
primary visibility use the new numerical profile. No centroid-visibility
selection, sparse hash, lookup reuse, temporal cache or CPU oracle computation
produces this image. Duplicate per-pixel probe work is intentional and
reported as the cache-free control's full cost.

This is a **repository dense RC estimator control**, not a canonical external
production RC implementation. It does not repair the estimator's finite
range, angular reconstruction or secondary-shadow omissions. Those errors
are scored. Native closest-hit differences are recorded, not hidden behind
historical deterministic tie tolerances. Fixed budget is four cascades by
eight directions; no adaptive tuning. Compare to both T_B2/T_B8 targets as an
approximate estimator, without implying it traces seven indirect bounces.
External DDGI/RTXGI and broader Lane M families remain required for any claim
against representative existing GI.
