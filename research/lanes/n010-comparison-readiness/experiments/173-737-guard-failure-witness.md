# Diagnose the737 conditioned raw-target/plane guard failure

2026-10-20 JST. Explicit user resumption after the740 pause. Parent `7946266`.
Registered before any instrumented build or native. Diagnostic only: no reference,
no feasibility, no admission, no threshold change, and737 is never rewritten.

## Question

Which operands made737's `certified_error>bound` guard throw, and is the failure
explained by finite-precision roundoff of the unchanged watertight intersection
(the069 audit's constant `B=256*eps*(1+|o|+|t|+d)` being an empirical scale,
not a rigorous error bound), rather than by a wrong triangle, a wrong target,
a coincident-surface case or a physics/estimator defect?

## Post-hoc evidence already in hand (no native, seconds of CPU)

These were run in a scratch directory against the frozen archive bytes only
(627 header/main, C1 T_B8 `scene.n008`) and are reported in742, not used as
admission evidence:

- Static audit of all262241 triangles with the header's own
  `normalize(cross(v1-v0,v2-v0))`: the largest vertex plane residual is
  8.9e-5 of the smallest possible `B` for that triangle. A mis-computed normal
  does not explain the failure. 47 triangles have shape condition
  `|e1||e2|/|e1 x e2| >= 1e3` (39 at >=1e4).
- Synthetic emulation using copied header bodies (watertight intersection,
  precise hit/delta, nudge, guard arithmetic; visibility ignored), 2e8 forward
  plus reconstruction pairs per mode: no exceedance, but the maximum fraction
  grows with sample count and with triangle condition: 0.47 for area-weighted
  targets, 0.81 for cond>=1e3 targets, dominated by the conditioned term.
  737's seed0 retained `max_conditioned_error_fraction=0.880`. This suggests an
  unbounded roundoff tail; it does not identify the737 operands.

## One bounded diagnostic native (742)

Script `scripts/research/n010_reference_sampling/diagnose_737_guard_witness.py`.
Work root `out/research/n010-comparison-readiness/737-guard-witness-v1/`
(refuse existing). Inputs are hash-checked against the740 archive manifest.

Generated source = exact627 header/main plus only these diagnostic edits,
each applied exactly once and proven inverse to the original bytes:

1. namespace-scope `thread_local` pixel/sample/near-counter variables and one
   stderr witness macro (all doubles printed as exact `%a`, also `%.17g`);
2. set those variables right after `N010NetRng rng(seed, pixel, s);`;
3. at both guard sites, print a `near` witness when `certified>0.9B` (first64
   per thread) and a `fail` witness immediately before the unchanged throw.

No sampling, BVH, arithmetic, guard or output change. Compile with627's exact
flags (`-mavx512f -std=c++20 -O3 -fno-fast-math -ffp-contract=off -pthread`).
Run once: seed index1 of737 only (`2596069104`), C1 T_B8, 8192spp, 4 threads,
CPUs28–31, nice15, 4GiB address space, CPU57600s, elapsed14400s. Dynamic row
scheduling may make the first failing row differ from737; that is reported,
not hidden. No retry, no second seed, no GPU, no concurrent scientific worker.

## Classifier (diagnostic, not admission)

- `ROUNDOFF_TAIL`: the failing witness has `hit.tri==target.triangle` (or an
  accepted coincident pair), the excess is in the registered terms, and
  extended-precision (long double and exact-rational reference via Python
  `fractions`) re-evaluation of the same operands shows the exact line/plane
  point is within `B` of the target while binary64 is not.
- `GEOMETRY_OR_LOGIC`: wrong triangle, wrong target, inconsistent direction or
  an exact-arithmetic violation of `B`.
- `NOT_REPRODUCED`: seed completes, or a different guard/resource stop occurs.

Any outcome only informs a separately registered repair. Candidate repairs
(e.g. a rigorous per-intersection forward error bound, or extended-precision
reconstruction) would change the audit or arithmetic and therefore require
their own registration, inverse proofs and requalification of affected
prefix/physical evidence. This plan authorizes none of them. 738/739 remain
NOT RUN. N010 NOT_READY; references16/24. Direct error1.0 remains UNRESOLVED/
未解決. Tests NOT RUN.
