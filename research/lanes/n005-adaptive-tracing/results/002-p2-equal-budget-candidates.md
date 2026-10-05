# N005 P2 equal-budget candidate result

Status: P2 campaign complete; implementation follow-up required before P3.

Evidence commit: `73843d77b4126965860ff49e4e0c37be7ad40b7e`

## Contract gates

- `current`, `uniform-extra-rays`, and `adaptive-extra-rays` completed for all decision and control cases.
- Uniform and adaptive used the frozen actual incremental budget: 9,216 extra rays on every active frame.
- Base prefix validation, extra-work validation, traversal diagnostics, overflow, and storage-failure gates passed.
- No sample exclusion, post-hoc threshold change, or GPU profile change was used.
- P2 remains non-formal.

## Quality observation

Across the 11 frozen active decision frames, using the per-frame percentage change from `current` and then taking an unweighted mean:

| Metric | Uniform extra rays | Adaptive extra rays |
| --- | ---: | ---: |
| RGB RMS error reduction vs current | 3.28% | 4.20% |
| p99 absolute luminance error reduction vs current | 2.67% | 3.63% |
| scale-aware affected-pixel fraction reduction vs current | -0.21% | 0.00% |

Adaptive beat uniform on RGB RMS in 9/11 active frames. The mean adaptive-vs-uniform RGB RMS advantage was about 0.93%. The p99 advantage was smaller and mixed by frame. Neither candidate materially reduced the affected-pixel fraction under the frozen N004 classification threshold.

Representative dynamic frames retained the same qualitative pattern:

- stable-topology-deforming: RGB RMS improvement was about 5.06% for uniform and 6.11% for adaptive.
- topology-changing-high-churn: RGB RMS improvement was about 2.45% for uniform and 5.57% for adaptive.

Therefore the P1-selected state-gated depth-discontinuity signal has evidence of useful targeting beyond uniform ray placement at equal ray count, but the advantage is modest rather than decisive.

## Cost observation

The current P2 implementation is not an acceptable efficiency result.

Across the same 11 active frames:

- uniform complete-GI GPU time was about 3.78x current on average;
- adaptive complete-GI GPU time was about 6.48x current on average;
- uniform extra-producer time averaged about 3.37 ms;
- adaptive extra-producer time averaged about 6.53 ms.

The ordinary downstream ray stages changed by only tens of microseconds on average. The cost is overwhelmingly the N005 selection producer, not the 9,216 extra rays themselves.

Root cause in the P2 implementation: `n005_extra_producer.comp.glsl` uses one GPU invocation and serially scans all base owners twice. Adaptive additionally evaluates the depth-discontinuity neighborhood during both scans.

## Decision

Do **not** freeze or run P3 yet.

Preserve the frozen P2 candidate semantics exactly:

- depth-discontinuity threshold `0.01`;
- state-change gate;
- 576 selected owners per active frame;
- 4 cascades;
- 4 extra rays per selected probe;
- 9,216 actual extra rays;
- deterministic even selection over the same eligible-owner order;
- same extra-ray direction rule.

Next, replace only the serial implementation of owner eligibility/ranking/selection with a parallel GPU implementation. The selected owner set/order and appended work must remain semantically identical. Re-run the same frozen P2 campaign after that implementation change.

Only after the optimized P2 run demonstrates acceptable implementation cost while retaining the quality/correctness result should N005 freeze a separate P3 formal measurement contract.
