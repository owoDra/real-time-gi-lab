# I001 — dynamic end-to-end GI integration result

Status: complete; no integrated candidate promoted under all frozen gates

## Measurement identity

- Branch: `research-integration-gate`
- Measurement commit: `3a1aa9c25ffcec583459409aca4c526b17b53e3c`
- Artifact:
  `out/research/integration-gate/001-dynamic-end-to-end/20260929T060025Z`
- GPU: AMD Radeon 8060S Graphics (RADV STRIX_HALO)
- Process repeats: 3
- Representative timing rows: 60
- Stress timing rows: 36
- Complete diagnostic validation cases: 33
- Validation failures: 0
- Formal runner exit code: 0

The frozen thresholds were not changed after measurement.

## Correctness and quality

All 33 diagnostic validation cases passed.

Across the accepted representative and stress timing rows:

- visibility mismatches: 0;
- producer semantic errors: 0;
- Hit-contract mismatches: 0;
- traversal runtime errors: 0;
- missing/leaked/stale probes: 0;
- resolved-output mismatches: 0;
- deterministic radiance RMS/max error: 0;
- temporal RMS/max error: 0;
- storage failures: 0;
- Vulkan validation errors recorded by the runner: 0.

The integrated pipeline is therefore functionally valid for the measured
variants/scenarios. The remaining decisions are performance/memory gate
decisions, not correctness failures.

## Representative end-to-end result

Median complete GPU time in microseconds:

| scenario | vanilla software | combined HWRT | HWRT vs vanilla | combined software | software vs vanilla |
| --- | ---: | ---: | ---: | ---: | ---: |
| static | 593.969 | 202.465 | -65.91% | 391.544 | -34.08% |
| camera motion | 604.268 | 213.886 | -64.60% | 396.714 | -34.35% |
| light motion | 603.186 | 206.512 | -65.76% | 378.279 | -37.29% |
| moving rigid | 3302.675 | 4100.230 | +24.15% | 3566.897 | +8.00% |

This is the central I001 result.

HWRT is dramatically faster for static, camera-motion and light-motion frames,
but its measured moving-rigid BLAS/TLAS maintenance reverses the result.
The software B003 fallback shows the same qualitative split at a smaller
magnitude: it wins the three non-geometry-changing cases but loses the
moving-rigid case.

The result must therefore remain regime-conditional. Averaging the moving case
away would violate the frozen per-regime primary gate.

## Target-GPU primary gate

The `combined-hwrt` primary candidate is **not promoted**.

Reasons:

- static, camera and light representative timing pass comfortably;
- moving-rigid complete GPU time is 1.2415x vanilla, a 24.15% regression,
  failing the required <=0.90x representative gate;
- every required stress scenario passes the <=1.05x no-regression gate;
- peak resident memory ratio is 2.1581x vanilla, below the hard 3.0x ceiling
  but above the 1.5x level required for an unqualified universal-win claim.

The evidence supports HWRT/TLAS as a strong target-GPU path for non-moving
geometry, but I001 does not support promoting it as the universal primary
architecture for the complete dynamic workload.

## Stress result

Median `combined-hwrt` complete GPU time versus vanilla software:

| stress | HWRT vs vanilla |
| --- | ---: |
| sparse | -54.19% |
| dense | -66.60% |
| large world | -63.60% |
| vertical world | -60.54% |

No required stress regime regressed. The primary failure is specifically the
moving-geometry maintenance regime, not scale, density or world-shape
robustness.

## Software fallback gate

The B003 DDA/hash + conservative quantized Micro BVH8 fallback is
**not promoted** over vanilla software traversal under the frozen gate.

- representative aggregate timing ratio: 0.9274x, missing the <=0.90x gate;
- peak resident memory ratio: 0.9814x, passing the <=1.15x memory gate;
- moving-update wall-time gate passes;
- moving-rigid complete GPU time is still +8.00% versus vanilla.

It remains useful research evidence and is substantially faster in static,
camera, light and all stress cases, but it does not satisfy the fixed complete
fallback promotion rule.

## Renderer depth-reuse gate

`depth-reuse-hwrt` is **not promoted as an unconditional integration
optimization** because the fixed >=10% incremental-GI improvement must hold
through the representative regimes.

Incremental GI improvement versus otherwise identical `combined-hwrt`:

| scenario | improvement |
| --- | ---: |
| static | 18.21% |
| camera motion | 11.65% |
| light motion | 21.70% |
| moving rigid | 3.72% |

Depth reuse remains clearly beneficial when traversal maintenance does not
dominate, but the moving-rigid regime misses the fixed gate.

## Bounded-capacity gate

The integrated bounded-capacity policy is **not promoted**, despite a strong
memory result.

- stream-capacity ratio: 0.1389x full capacity, an 86.11% reduction;
- normal representative rows overflowed 0 times;
- forced 512-owner overflow was safely clamped;
- explicit full-capacity retries all passed quality;
- normal timing gate fails.

Median bounded-HWRT complete GPU time versus full-capacity combined-HWRT:

| scenario | bounded vs full |
| --- | ---: |
| static | +10.79% |
| camera motion | +4.67% |
| light motion | +14.13% |
| moving rigid | -1.60% |

Static and light-motion exceed the allowed +5% cost.

For the forced 512-owner overflow, requested work was 31,392 items and the
bounded attempt clamped to 16,384. The median explicit failed-attempt + retry
GPU time was 423.404 us. Median total setup-wall cost across the two harness
processes was 162.161 ms, and the maximum retry-path resident footprint was
149,939,904 bytes.

The D005 policy result therefore remains valid as a memory technique, but the
current integrated implementation still does not meet the promotion timing
gate.

## Final integration decision

I001 does **not** select one universal composed GI architecture.

The measured decision is conditional:

- keep accepted A001 semantics, schema and natural append ordering as the stable
  producer contract;
- keep C001 per-probe sparse hash as the validated storage contract;
- HWRT/TLAS is the strong target-GPU traversal choice when geometry is stable,
  but moving-rigid maintenance requires additional research before universal
  promotion;
- B003 quantized software traversal remains a useful fallback candidate but
  needs moving-frame improvement to pass the frozen fallback gate;
- renderer depth reuse is useful in non-maintenance-dominated regimes but is not
  promoted unconditionally by I001;
- bounded capacity remains strong memory-policy evidence with correct safe
  overflow/retry, but its normal-case static/light overhead prevents promotion.

The next architecture work should focus on moving-geometry maintenance rather
than further static traversal tuning: that regime is the common blocker for the
otherwise strong HWRT/software candidates.

## I001 completion

The experiment question is answered and Issue #13 can close:

- implementation complete;
- correctness/quality matrix complete;
- repeated target timing complete;
- fixed gates evaluated without threshold changes;
- overflow retry cost retained;
- conditional result recorded.

No PR or merge is part of this research closeout.
