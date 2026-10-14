# Post-hoc deep-transport sampling diagnostic

Result 082 completed C1 T_B8 seed 0 at 8192 spp but failed Amendment 7's
unchanged numerical gates. Result 084 identifies 54 pixels exceeding the
mean gate. This is a diagnosis after observing that failure, not preregistered
reference admission, a new exclusion mask, or a GI performance comparison.

Use the eight largest-difference pixels in the fixed order recorded by 084.
Keep the original scene, seed, sample indices, depth, geometry, BVH, offsets,
and independent CPU transport. Generate separate diagnostic source/binaries;
do not modify the running CPU qualifiers, original GPU port or its evidence.

1. Recompute those pixels with the original CPU sampler and verify every
   component mean/moment against the saved original CPU sidecar.
2. Recompute the selected pixels with the same GPU arithmetic and polynomial
   trigonometry. Check that the saved whole-image failure is reproduced before
   interpreting any intervention.
3. Supply CPU `std::sin(phi)`/`std::cos(phi)` for the identical uniform words
   at every possible bounce, leaving GPU traversal and other arithmetic
   unchanged. Compare selected-pixel means/moments and exact counters.

The CPU trigonometric table is deterministic and does not depend on radiance,
visibility, reference eligibility, or the observed path. This intervention
can establish an influence of the sampling implementation if the original
failure reproduces. It cannot alone establish that this is the only cause.
Any repaired implementation must still pass all Amendment 7 conformance,
physical controls, all-state and nested-prefix gates before admission.

Each diagnostic subprocess has a 4 GiB address-space and 300-second elapsed
guard; build CPU limit is 90 seconds. Preserve failed attempts. Runtime wall
is diagnostic, never an accepted GI GPU timestamp. No power changes.
