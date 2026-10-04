# N005 P1 result — signal localization

Issue: #40  
Protocol: `n005-p0-p1-signal-probes-v1`  
Evidence commit: `f110ee3044b00f4dba5c7ae5787aa3df094bd0e1`

## Status

**Complete — proceed to a frozen P2 candidate.**

The P1 run remained observation-only: zero extra rays, no adaptive tracing, no formal target claim. Internal correctness passed across the retained cases.

## Signal decision

Retain **`depth-discontinuity`** as the single first P2 local confidence signal.

Why:

- camera abrupt/gradual: it consistently concentrated N004 error in a small spatial support;
- stable-topology deformation and topology-changing/high-churn: temporal owner/depth-change signals were almost blind, while depth discontinuity still localized a material fraction of the error;
- the signal is simple, renderer-observable, and maps directly back to visible owner/probe work.

Representative P1 observations:

- abrupt camera: ~7.1% non-zero support captured ~38.7% of absolute error mass and ~47.0% of affected pixels;
- stable deforming: ~7.0% support captured ~38.3% absolute error mass and ~49.1% affected pixels;
- topology churn: ~7.0% support captured ~39.8% absolute error mass and ~49.2% affected pixels;
- at the fixed 1% ranked probe (576 pixels), the two dynamic blockers captured about 6% of absolute error mass and about 7.8% of affected pixels.

The affected-region mean depth-discontinuity score in the camera/dynamic blockers was roughly `0.041–0.047`, while unaffected regions were roughly `0.00017–0.00090`. This supports a simple prospective `0.01` normalized-depth threshold without fitting a per-case threshold.

## Rejected/deferred signals for the first P2 candidate

- `newly-visible`: useful only in narrow transition regions and too sparse for the dynamic blockers.
- `ownership-changed`: strong camera-state specificity, but nearly blind to stable/topology-changing dynamic error.
- `temporal-depth-change`: same dynamic blind spot.
- `visibility-discontinuity`: weaker localization than depth discontinuity.
- storage churn, dynamic-owner proximity, probe age, and sample variance remain deferred. P1 no longer justifies adding them before testing the simpler candidate.

## Important control finding

`depth-discontinuity` also lights up ordinary static/world geometry. It is therefore **not** a state-change detector by itself.

P2 must gate the signal with an explicit renderer state-change event:

- camera abrupt: first changed target frame only;
- camera gradual: every changed motion frame;
- stable deformation: first target mutation frame only;
- topology churn: first topology-mutation frame only;
- static, illumination-only, and world-shape controls: no adaptive extra tracing.

This keeps the local signal responsible only for *where* to spend work; the renderer state transition decides *when* extra work is allowed.

## P2 handoff

Freeze one candidate before implementation:

- signal: `depth-discontinuity`;
- threshold: normalized depth delta `>= 0.01`;
- selected owner budget on active frames: `576` (1% of the 320x180 grid);
- 4 cascades per owner;
- 4 additional deterministic directions per selected probe;
- requested incremental work: `576 * 4 * 4 = 9,216` extra rays per active frame;
- uniform and adaptive must trace the same actual incremental ray count per frame/case;
- controls keep zero extra rays;
- P2 remains validation/calibration only. P3 requires a separately frozen formal contract.

No N004 threshold or completed result is changed.
