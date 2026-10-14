# Deep GPU oracle: selected-path signed-zero diagnosis

## Classification

**Post-hoc diagnosis, not reference admission or a GI comparison verdict.**
The original candidate remains rejected by complete conformance 082. Fixed
Amendment 7 thresholds, all pixels, all seeds and sample indices remain intact.
This diagnosis concerns the independent binary64 oracle execution port, not
the N-series Renderer or N009's unresolved direct-zero pixels.

## Reproduction and intervention

- 087 reproduces the eight largest-difference original CPU/GPU selected-pixel
  payloads byte exactly at C1 T_B8, seed 305419896, 8192 spp.
- CPU sin/cos substitution removes mean/moment/counter discrepancies in two
  pixels, but six remain. It is insufficient as a complete repair.
- 089 records all seven possible secondary bounces of all 8192 samples in
  each selected pixel, in both trigonometric modes. All 16 selected-pixel
  aggregates reproduce 087 exactly. The manual CPU trace aggregate and
  integer counters reproduce the original independent sampler exactly.
- 092 independently evaluates the next sampling direction on CPU with the
  identical shifted-Sobol words. Replace only the sign of zero `normal.z` in
  the captured GPU normal with the captured CPU sign. In **8/8** original
  divergent paths the resulting direction is numerically identical to
  the captured CPU direction (reported max absolute error **0.0**). The
  unmodified GPU normal predicts the captured GPU direction within
  **2.220446049250313e-16**. Actual CPU/GPU next-direction differences range
  from **0.21700106455284557 to 1.1836907189507428**.

## Mechanism and scope

In these eight paths, the first semantic divergence is a different closest
primitive among **85946, 85947 and 85951**, at bounce 2–5. Their vertices lie
on the same plane, `x = 1307.27001953125`. The selected normals describe the
same physical direction `(-1, 0, 0)`, but their z components have opposite
zero signs (binary64 `0x0000000000000000` versus `0x8000000000000000`).

The source's Duff basis uses `copysign(1.0, normal.z)` on CPU and the explicit
sign bit on GPU. Changing that zero sign changes the tangential basis. With
the same uniform words, the following reflection direction can therefore
change substantially, then change subsequent intersections, light visibility,
path contribution and exact counters. The recorded trace and CPU direction
counterfactual establish this deterministic amplification mechanism in the
eight selected paths. Tiny preceding numeric differences and closest-choice
differences are recorded; the exact arithmetic operation responsible for
every initial closest-choice difference has not been isolated.

This does not establish physical bias of the independently validated CPU
oracle: both signed-zero bases can represent valid cosine hemispheres. It
does establish failure to reproduce the frozen CPU sample paths under the
port's admission contract. Do not canonicalize the CPU normal, force a known
hit, copy reference values, relax the numerical gates, or exclude these paths
to turn 082 into a pass. The other **46** above-gate pixels from 084 have not
been individually traced here.

## Next implementation candidate

Plan 024 tests a general near-hit ambiguity guard with independent whole-path
CPU recomputation for flagged paths. It uses no stored reference radiance or
prescribed primitive/sign. Every sample remains in the image. A selected-pixel
success would only justify a separately retained full conformance candidate;
physical controls, all-state checks and nested-prefix validation remain
mandatory before any reference acquisition transition.

The original CPU qualifiers continue independently with their frozen inputs.
N010 remains NOT READY pending all 24 eligible references, remaining pilots
and accepted quiet full-boundary calibration. N001–N009 outcomes remain
unchanged; Sponza direct max-relative-error-1.0 pixels remain **未解決**.

## Evidence

- [082 full numerical failure](082-gpu-reference-deep-conformance-resource-followup.json)
- [084 whole-image post-hoc map](084-gpu-deep-numerical-failure-map.json)
- [087 trigonometric intervention](087-deep-sampling-intervention.json)
- [089 retained path traces and replay](089-deep-path-diagnostic.json)
- [092 CPU signed-zero counterfactual](092-signed-zero-basis-counterfactual.json)

089 hashes all four 117,440,512-byte trace payloads and accompanying means,
counters and ledgers. Local artifacts are under
`out/research/n010-comparison-readiness/deep-path-diagnostic-v2/`.
092 records the source/header/net/trace hashes and its independent C++
build/runtime command. Runtime wall is diagnostic; no accepted GI GPU-time
measurement or release-level regression validation follows.
