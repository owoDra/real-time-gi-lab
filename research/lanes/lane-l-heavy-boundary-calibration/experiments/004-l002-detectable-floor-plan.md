# L002 — heavy-boundary detectable-effect floor

Status: **PROSPECTIVE — NO L002 TARGET DATA OBSERVED**

## Entry condition

L001 completed with both required environments failing the unchanged J004
1.02 / 1.03 / 1.02 same-variant control-health gate. No reusable heavy-boundary
timing environment was established, so the predeclared L002 entry condition is
satisfied.

L001 and J004 remain immutable evidence. Their thresholds are not relaxed or
reinterpreted here.

## Research question

On fresh measurements of the exact J004/L001 heavy recurring boundary, what
multiplicative GPU-timestamp effect size can be detected consistently despite
the boundary-specific same-variant noise?

L002 does not rank architecture candidates.

## Measurement acquisition

Acquire fresh same-variant measurements using the exact L001 boundary:

- both `dual-context` and `single-context-independent-runtime`;
- all five J002 profiles;
- both incumbent controls;
- eight topology snapshots in exact order;
- 16 complete transitions per sample;
- 4 warmup + 12 measured pairs;
- 8 fresh-process blocks;
- unchanged AB/BA and environment counterbalancing;
- 1 second settle;
- no validation layers during accepted timing;
- no sample exclusion;
- no instability rerun;
- no completed-campaign rerun.

Correctness, output identity, allocation lifetime, workload identity, J002
geometry identity, and device provenance must pass before timing exactly as in
L001.

## Synthetic effect injection

Synthetic effects are **analysis-only**. GPU work and recorded raw measurements
are not modified.

For every measured pair:

```
synthetic_B_gpu_us = measured_B_gpu_us * factor
```

Frozen factors, evaluated in this order:

1. +20% (`1.20`)
2. +10% (`1.10`)
3. +5% (`1.05`)

A-role GPU timestamps remain measured values. CPU wall is never synthetically
modified and remains diagnostic/health/provenance only.

This calibrates a multiplicative detection floor under the real heavy-boundary
noise distribution. It is **not** evidence that a physical +N% work increase has
exactly N% runtime cost.

## Frozen detection gate

For each environment × profile × control family independently, first derive the
unmodified same-variant control metrics from the fresh L002 samples.

The multiplicative control-noise envelope is:

```
max(
  control max absolute process-median ratio,
  control process-median span ratio,
  control max within-process order-bias ratio
)
```

A synthetic effect passes one control only if all of the following hold:

1. its injected factor is strictly greater than that control-noise envelope;
2. all 8 fresh-process synthetic median B/A ratios are > 1;
3. every process has both AB-stratum and BA-stratum median B/A > 1;
4. every process has at least 0.75 positive measured-pair fraction after
   injection;
5. pair structure, finite/positive timing, and provenance remain structurally
   valid.

No profile averaging is allowed.

An effect passes an environment only when all 5 profiles × 2 control families
pass independently.

## Contiguous floor

Evaluate +20%, then +10%, then +5%.

A smaller effect can only be accepted when every larger prerequisite effect
passes. The smallest contiguous passing effect is that environment's
heavy-boundary measurement floor.

If +20% fails any required control, that environment has no accepted floor at or
below 20%.

## Environment decision

- If only one environment establishes a floor, use that environment.
- If both establish different floors, use the environment with the smaller
  accepted floor.
- If both establish the same floor, prefer
  `single-context-independent-runtime` after correctness/allocation validation
  because it uses one Vulkan context while retaining independent runtime
  resources. This tie-break is frozen before L002 target data and is not based
  on speed.
- If neither environment establishes +20%, outcome is
  `target-timing-unsuitable-up-to-20-percent`.

## Downstream meaning

A successful L002 result is a measurement-analysis floor, not architecture
evidence. A later Lane-E or topology candidate run must:

- use the accepted environment;
- predeclare a promotion threshold no smaller than the L002 floor;
- retain run-local same-variant controls;
- retain all correctness/memory/provenance gates;
- never reuse L001/J004 candidate timing as decision evidence.

No candidate backend is present in L002.
