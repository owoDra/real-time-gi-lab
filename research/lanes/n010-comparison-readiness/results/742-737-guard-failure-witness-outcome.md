# 737 guard failure: witness and root cause (742)

2026-10-20 JST. Explicit user resumption after740. Plan
[173](../experiments/173-737-guard-failure-witness.md), registered in `4e08e5e`
before the instrumented build/native. **Diagnostic only: no reference,
feasibility or admission.** 737 and its partials are unchanged.

## Outcome

**Reproduced. Classification `ROUNDOFF_TAIL` under173; the specific mechanism
is an internal inconsistency of the069 audit's third term.**

- [742 witness record](742-737-guard-failure-witness.json): instrumented exact627
  (header inverse exact; only stderr witnesses added), seed index1 `2596069104`,
  C1 T_B8, 8192spp, 4 threads CPUs28–31. Returncode-6 with the identical
  `conditioned raw-target/plane reconstruction error` after915s wall /3640s CPU.
  One `fail` and one `near` (>0.9B) witness.
- [742 exact analysis](742-737-guard-failure-witness-analysis.json): exact-rational
  re-evaluation of the witness operands against the scene's binary64 vertices.

Failing check: pixel(277,20), sample658, eye-first reconstruction index2,
source triangle86176 → target triangle59183. `hit.tri==target.triangle`, not
coincident, target barycentrics(0.581,0.245,0.174) interior, shape condition604,
|cos|0.581, distance5.01, B=7.26e-11.

| Term (fraction of B) | binary64 | exact rational |
| --- | --- | --- |
| target plane residual |0.5869 |0.5869 |
| actual plane residual |0.4226 |0.4227 |
| conditioned `|a−t|·|N·w|` |**1.0095** |— |
| exact line∩plane to target, conditioned | — |0.5868 |

The target and the returned hit lie on **opposite sides** of the triangle plane,
each within the069 per-point allowance B. Because the reconstruction ray is
aimed at the target, `a−t` is parallel to `w` up to roundoff, so
`|a−t|·|N·w| ≈ |N·(a−t)| ≤ |N·(a−v0)|+|N·(t−v0)| ≤ 2B`.
Here0.5869+0.4226=1.0095. Thus069 admits each point up toB from the plane
yet requires their separation along the normal to be ≤B: valid roundoff that
satisfies both plane terms can fail the third. It is not a wrong triangle,
target, coincident surface, mis-computed normal or estimator/physics defect.

Supporting post-hoc checks (scratch, no native, frozen inputs): all262241
triangle vertex plane residuals ≤8.9e-5 of their minimum B; synthetic emulation
(2e8 pairs/mode) reaches 0.47 (area-weighted) and 0.81 (cond≥1e3) without
exceedance, consistent with a rare tail; 737 seed0 retained 0.880.

## What this does and does not establish

- Root cause of737's immediate guard failure: identified (audit design).
- It does **not** pass737, admit any reference, bound global finite-arithmetic
  bias, or show feasibility. The own-family log-density check (seed0 max
  6.6e-12 vs1e-6) is unchanged and unaffected.
- Nice was19, not15 (parent `nice -n 15` plus the script's relative
  `os.nice(15)`): scheduling only; recorded, not hidden.

## Next step (requires its own registration; not authorized here)

A repair must amend only the diagnostic audit, prospectively, e.g. replace the
third term's allowance by the implied `2B` (or by `target_plane+actual_plane+B`),
with the same inverse/source-composition proofs used by069. Because627 is
the qualified exporter, an audit-only change still needs an explicit
assessment of whether all78 state/prefix and physical evidence transfers
(output bytes are unchanged where no guard fires) before re-running737's
level under a new attempt identity. 738/739 remain NOT RUN. N010 NOT_READY;
references16/24. Direct error1.0 remains UNRESOLVED/未解決. Tests NOT RUN.
