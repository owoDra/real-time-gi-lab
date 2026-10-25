# 046 / M002 — Prospective new-heldout and dynamic-state validation

Registered after 045 publication `ba353ec4`, BEFORE any M002 scene, state,
reference, image, metric or timing exists. M001 (H01-H03) is now observed
development data. 045 accepted, on 3/6 M001 targets, that PT + the fixed
geometry-only quadratic reconstruction (PTR) is faster than raw PT at matched
quality; every other tested family failed quality. M002 asks whether that
matched-quality result generalizes to unseen static scenes and to changed
camera/light states, with fresh references, unchanged gates and the 045 timing
protocol. Known components only; no novelty claim.

## Frozen targets (16 = 8 states x B2/B8)

Geometry from the unchanged N004 factory; states from the CPU exporter
`build/n009/.../n009_state_export` with the M001 contract, `--frame-id 1`
(precondition: it reproduces the M001 H01 state bytes exactly; checked once
before any new export, already observed in development to match).

- S1 `leak_scene("thin", 0.071)`, static
- S2 `leak_scene("one-sided")`, static
- S3 `world_scene("sparse")`, static
- S4 `world_scene("large-horizontal")`, static
- S1 `--regime camera-motion`, S1 `--regime light-motion`
- S3 `--regime camera-motion`, S3 `--regime light-motion`

Each at T_B2 and T_B8. Dynamic states are single changed states scored on their
own references; both roles are stateless, so this covers per-state camera/light
change, not temporal history, rigid/deforming/topology motion, AS update cost
or Sponza (>2048 triangles; NOT_RUN, stated limitation).

## References

Unchanged N010 RQMC oracle/net/seeds and the M001 admission rule (N007 screen,
levels 8192, 16384, ... in order, stop at the first statistically eligible
level with geometry-hash match); the admitted level's four-seed luminance mean
is the reference. Ineligible targets are reported REFERENCE_INELIGIBLE, never
scored.

## Quality (one fixed-seed GPU image per rung, first-pass selection)

Roles in the 044/045 harness, new capture mode writing direct and indirect:
PT ladder [16, 64, 256, 1024] spp; PTR ladder [4, 16, 64] spp (unchanged 022
operator and SPIR-V). Gates unchanged: total NRMSE<=5%, indirect NRMSE<=10%,
|indirect signed bias|<=5%, all pixels. Per target record every rung and the
first passing rung per role (or FAIL).

## Timing and memory

Fresh 045-protocol calibration (8 processes, 32 pairs, three sizes) on the new
build; then, for every target where BOTH roles pass, a T1 campaign (A = PT at
its first-pass rung, B = PTR at its first-pass rung), 8 processes x 32 pairs,
045 decision rules (threshold max(log1.20, log(1+MDE))). Owned role buffers and
true peak recorded.

## Decisions

- M002 quality generalization holds iff PTR passes at <=64spp on every
  reference-eligible target.
- M002 matched-quality speed generalization holds iff T1 is ACCEPTED_FASTER on
  a majority of matched targets and ACCEPTED_SLOWER on none.
Prediction: PTR passes on most targets; T1 faster wherever PT needs >=256spp.
First implementation/provenance failure stops M002; quality losses never stop
it. No reruns, tuning, ladder or gate changes. One GPU; CI/default
Renderer/power untouched.
