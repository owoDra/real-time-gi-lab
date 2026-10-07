# N005 P2 equal-budget candidate result

Status: **complete; optimized implementation accepted for P3 freeze.**

Initial evidence commit: `73843d77b4126965860ff49e4e0c37be7ad40b7e`  
Optimized evidence commit: `c9c2d80e898fe3b01e3c40e8ee449865ae65e581`

## Contract gates

Both retained P2 campaigns completed the frozen current / uniform / adaptive matrix.

The optimized rerun retained all prospective semantics:

- `depth-discontinuity >= 0.01`;
- camera/dynamic state-change gate;
- 576 selected visible owner regions on active frames;
- 4 cascades;
- 4 extra rays per selected probe;
- 9,216 actual extra rays per active frame;
- deterministic even selection over the same eligible-owner order;
- the same deterministic extra-ray direction rule.

The optimized rerun passed:

- equal actual-ray budget on every active frame;
- base-prefix and appended-work validation;
- traversal diagnostics;
- zero overflow and storage failures;
- zero extra work on all controls/inactive frames;
- no sample exclusion, threshold change, or GPU profile change.

P2 remains non-formal.

## Optimized quality observation

Across the 11 frozen active decision frames, using per-frame percentage change from `current` followed by an unweighted mean:

| Metric | Uniform extra rays | Adaptive extra rays |
| --- | ---: | ---: |
| RGB RMS error reduction vs current | 2.54% | 4.23% |
| p99 absolute luminance error reduction vs current | 2.25% | 4.14% |
| p99 relative luminance error reduction vs current | 2.25% | 4.14% |
| scale-aware affected-pixel fraction reduction vs current | -0.11% | 0.00% |

Adaptive had lower RGB RMS than uniform on 8/11 active frames. The exact per-run percentages moved slightly relative to the first P2 campaign, which is why P3 uses independent repetitions and median interpretation rather than treating one P2 timing/quality sample as formal evidence.

The conclusion is unchanged: state-gated depth-discontinuity provides useful targeting beyond uniform placement at the same traced-ray count, but the advantage is modest and must be judged together with formal GPU cost.

## Optimized implementation cost

The serial implementation problem is resolved.

Across the 11 active frames:

- uniform extra-producer GPU time: **144.1 us mean**;
- adaptive extra-producer GPU time: **214.7 us mean**.

The first retained P2 implementation measured about 3.37 ms / 6.53 ms respectively. The parallel implementation therefore removed the pathological serial scan cost while preserving the frozen candidate semantics and correctness gates.

Complete-GI timings in P2 remain descriptive only. They show enough run-to-run variation that P3 must use fresh-process repetitions and median GPU timestamps.

## Decision

**Proceed to P3 formal comparison.**

P3 must not re-tune the candidate. It freezes the optimized P2 implementation lineage and the exact P2 signal/budget/schedule. Formal evidence will use a shared canonical reference per case, independent fresh-process repetitions, rotated mode order, GPU timestamp medians, and retained raw samples.

The formal result must report quality, timing, memory, correctness, ray-normalized efficiency and GPU-cost efficiency separately. No aggregate score is permitted.
