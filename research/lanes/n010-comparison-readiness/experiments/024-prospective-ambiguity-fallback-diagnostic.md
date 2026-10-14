# Ambiguous-intersection CPU fallback candidate

This implementation candidate follows post-hoc diagnosis 089/092. It does not
relax Amendment 7 admission thresholds or exclude samples. Existing CPU
qualifiers, old GPU failure records and frozen continuation inputs persist.

For the same eight pixels, seed and 8192 sample indices as 087, mark an entire
path when closest-hit candidates have distinct primitive IDs and distances
within `64 * binary64 epsilon * max(abs(best_t), scene_diagonal)`. Use the
existing oracle scene diagonal reconstructed from its offset. Expand the
closest-query slab upper bound by that guard to observe nearby candidates;
keep the actual closest/tie choice unchanged. Also mark a shadow intersection
within that guard of its strict endpoint. Freeze this guard before outputs.

Save every sample's GPU components/counters and path flag. Independently
recompute every flagged complete path using the original CPU sampler, the
same scene and seed/sample indices. Accumulate samples in their original
order on CPU, using GPU values for unflagged paths and CPU values for flagged
paths. No stored reference radiance or prescribed hit/sign is used for this
fallback. It replaces computation of a path rather than removing the path.

Require finite corrected mean/moments, identical direct/emission means, exact
integer counters, mean/moment differences <=1e-10 and indirect NRMSE <=1e-8.
Record flag counts and every failed check. A selected-pixel success is only
a feasibility diagnostic. A production candidate still requires every full
numerical, independent physical, all-state and deterministic nested-prefix
gate before any reference acquisition transition. The guard may fail to
cover other disagreements; those failures remain visible.

Use separate sources/binaries and the diagnostic 4 GiB / 90 CPU-second /
300 elapsed-second subprocess guards. No GPU timing competitiveness claim,
power changes, default Renderer changes or historical result revisions.
