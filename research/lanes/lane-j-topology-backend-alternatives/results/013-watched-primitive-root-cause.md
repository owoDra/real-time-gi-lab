# J003 watched-primitive diagnosis — exact arithmetic localized

Status: **ROOT CAUSE LAYER IDENTIFIED — v1.6 strict fp32 correction pending target rerun**

The validation-only watched-primitive replay retained the same step-3 / ray-3252
failure and directly traced the expected lower-ID primitive through the GPU
exact path.

## Watched primitive 262389

Observed shader flags: `15`:

- leaf/test reached: true;
- GPU triangle intersection accepted: true;
- GPU `prefer_hit` accepted: true;
- a prior current Hit already existed: true.

At the moment primitive 262389 was tested:

- GPU candidate t: 1533.32092;
- previous current t: 1534.51123;
- previous current primitive: 58881.

Therefore primitive 262389 was successfully reached, intersected, and promoted
to the current Hit. It was not lost through:

- persistent upload;
- upper-BVH traversal;
- micro-BVH traversal;
- AABB pruning;
- initial tie selection.

The final GPU Hit was later primitive 262932 at approximately t=1533.29016.

## Cross-reference with CPU exact tests

CPU single-triangle values:

- primitive 262389: 1533.32068;
- primitive 262932: 1533.29016;
- CPU delta: 0.0305175781;
- frozen B001 tolerance: 0.0306658018;
- CPU tie-window classification: true.

The significant discrepancy is therefore the GPU t for primitive 262389
(~+0.00024 relative to the CPU reference). That drift is enough for the later
262932 comparison to cross the frozen tie boundary and replace the lower-ID Hit.

## Decision

The active failure is localized to exact triangle floating-point evaluation /
tie-boundary reproducibility, not candidate topology or persistent state.

Lane J v1.6 freezes a correction that retains all B001 Hit semantics and instead
makes the GLSL Moller-Trumbore arithmetic strict source-order fp32 using
explicit scalar dot/cross helpers and `precise` intermediates.

No B001 tolerance, tie rule, workload, topology or ray set is changed.

Validation-only watched-primitive diagnostics remain enabled until the
representative zero-error gate passes.
