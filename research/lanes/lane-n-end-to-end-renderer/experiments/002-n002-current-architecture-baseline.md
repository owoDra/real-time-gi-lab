# N002 — current architecture end-to-end baseline

Status: **in progress — core five-scenario renderer slice frozen first**

Issue: #27  
Parent: #26  
N001 result: `results/001-renderer-reference-bringup.md`

## Objective

Run the accepted A–M architecture through the Lane-N image-producing boundary before any same-boundary vanilla comparison.

N002 completion still requires all six scenario classes from #27:

1. static;
2. camera motion / disocclusion;
3. changing illumination;
4. moving rigid geometry;
5. stable-topology deformation;
6. topology-changing / high-churn.

## Staged implementation rule

The first target checkpoint intentionally exercises the five scenario classes already supported by the accepted Lane-E-final integrated runtime. This is a correctness/quality/provenance vertical slice, not a reduced N002 completion criterion.

Topology-changing/high-churn remains mandatory. It is added only after the core slice is target-valid because its accepted Lane-M implementation requires a materially different ownership boundary: immutable static world backend plus a separately rebuilt dynamic-object backend with old/new lifetime overlap. Rebuilding the whole world would violate the accepted Lane-M/Lane-E semantics and is therefore not an acceptable shortcut.

## Core playback

The frozen core checkpoint uses the N001 Sponza/render/reference contract and adds stable-topology deformation:

- static;
- camera-motion;
- light-motion;
- moving-rigid;
- stable-topology-deforming (`I001Scenario::DeformingControl`).

Each scenario is instantiated in a fresh runtime, warmed in the source state, then measured/rendered in its target state. This preserves N001's deterministic reference and avoids cross-scenario state leakage.

## Interpretation

N002 core timing is **descriptive only**. No architecture performance winner or regression classification is allowed until the Lane-N complete-frame boundary has its own prospectively frozen calibration. Lane K's 5% and Lane L's 20% floors are not imported as N002 thresholds.

Image metrics remain raw radiometric diagnostics. N002 does not turn them into a single score or winner.

An individual black reference frame is valid. The campaign must contain positive renderer and reference HDR signal overall; black frames remain evidence rather than exclusions.

## Topology/high-churn adapter requirement

The follow-up adapter must preserve the M001 retained incumbent:

- static world ownership remains immutable;
- only the selected dynamic object is rebuilt;
- old and new dynamic backends may coexist during handover and that overlap must be counted;
- true lifetime peak must include the rebuild overlap;
- unrelated static ownership must not be rebuilt or mutated;
- renderer primary visibility, GI traversal, and direct-light visibility must all see both static and dynamic backends;
- no fallback to whole-scene rebuild is permitted.

N002 is not complete until that adapter produces aligned HDR/reference evidence and passes correctness/provenance gates.

## No-claim rule

Until N002 completion and Lane-N calibration:

- no performance ranking;
- no sub-threshold interpretation;
- no N003 vanilla comparison claim;
- no sample deletion;
- no post-hoc threshold relaxation.
