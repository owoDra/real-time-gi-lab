# N002 — current architecture end-to-end baseline

Status: **in progress — core five-scenario target PASS; topology/high-churn target ready**

Issue: #27  
Parent: #26  
N001 result: `results/001-renderer-reference-bringup.md`

## Objective

Run the accepted A–M architecture through the Lane-N image-producing boundary before any same-boundary vanilla comparison.

N002 completion requires all six scenario classes from #27:

1. static;
2. camera motion / disocclusion;
3. changing illumination;
4. moving rigid geometry;
5. stable-topology deformation;
6. topology-changing / high-churn.

## Core target checkpoint

The five scenario classes already supported by the accepted Lane-E-final integrated runtime have passed the target checkpoint on AMD Radeon 8060S / RADV Mesa 26.1.2.

Artifact root:

`out/research/lane-n-end-to-end-renderer/002-current-architecture-baseline-core/20261003T044631Z`

Measured source commit:

`041171dbbd12ffaccd3d7c0f8105de77e4dbc672`

Observed gates:

- process return code: 0;
- target validation: PASS;
- validation-layer error lines: 0;
- traversal/runtime, storage, OOB, lifetime and alignment gates: PASS for all five frames;
- reference convergence: PASS for all five frames at 512 spp;
- campaign-level renderer HDR signal: present;
- campaign-level reference HDR signal: present;
- no samples excluded.

The timing rows are retained only as descriptive diagnostics. No performance ranking is inferred from this checkpoint.

## Topology/high-churn integration

The final N002 adapter preserves the M001 retained Lane-E incumbent rather than using a whole-scene rebuild:

- one deterministic dynamic object partition is selected;
- static world geometry and the static BLAS remain immutable;
- exactly 50% of the selected object's primitive identities are replaced, exercising delete+insert topology churn while renderer slot capacity remains stable;
- only the dynamic object BLAS is rebuilt;
- the replacement dynamic BLAS is built while the old one remains alive;
- TLAS switches to the replacement before the old dynamic BLAS is retired;
- old/new overlap is recorded explicitly;
- the lifetime peak includes the retired old dynamic BLAS during handover;
- renderer/GI execution after handover reuses the unchanged complete Lane-N frame boundary.

The final target is split into `phos-n002` for the five accepted core paths and `phos-n002-topology` for the object-local topology transition, then combined into one six-frame provenance artifact by `run_n002_full.py`. Both phases must report identical device/driver/timestamp provenance.

## Full completion contract

The full frozen contract is `002-n002-full-config.json`. The final validator requires:

- all six scenario frames;
- deterministic scene/playback provenance;
- reference convergence;
- zero required correctness counters;
- complete GI / complete renderer GPU accounting;
- all required memory categories;
- frame 5 executes exactly one topology mutation and one object-local backend rebuild;
- frame 5 records nonzero old/new overlap;
- campaign-level renderer/reference HDR signal remains present;
- no sample deletion or post-hoc threshold change.

N002 remains incomplete until the six-frame target artifact passes this contract.

## Interpretation

N002 timing is **descriptive only**. No architecture performance winner or regression classification is allowed until the Lane-N complete-frame boundary has its own prospectively frozen calibration. Lane K's 5% and Lane L's 20% floors are not imported as N002 thresholds.

An individual black reference frame remains valid. Campaign-level signal, not every individual frame, is the sanity gate.

## No-claim rule

Until N002 completion and Lane-N calibration:

- no performance ranking;
- no sub-threshold interpretation;
- no N003 vanilla comparison claim;
- no sample deletion;
- no post-hoc threshold relaxation.
