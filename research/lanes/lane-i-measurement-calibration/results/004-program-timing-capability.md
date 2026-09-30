# I004 — program timing capability

## Primary outcome

# **Target timing unsuitable**

Under the exact frozen `lane-i-i002-v1` protocol, no tested effect size is simultaneously demonstrated by both required timing axes.

This is the sole primary Lane I outcome.

## Basis

The accepted I003 campaign is complete, provenance-consistent, and retains all samples.

GPU timestamps are strong:

- baseline control passes;
- +20%, +10%, and +5% all pass the frozen candidate gates;
- the smallest tested demonstrated GPU-timestamp effect size is 5%.

Complete CPU wall is not decision-valid at a matching resolution:

- baseline control passes;
- +20% fails the frozen maximum order-bias gate at 1.051029 versus the 1.05 limit;
- +10% and +5% pass individually;
- the resulting pattern is non-monotonic, which I002 explicitly classifies as inconclusive.

The separate one-dispatch diagnostic also shows unstable complete CPU wall, but it is diagnostic-only.

## Why this is not “calibrated protocol accepted”

I002 froze GPU timestamp and complete CPU wall as decision axes before target timing. Retroactively treating wall time as diagnostic-only after seeing I003 would be a post-hoc methodology change.

Therefore the demonstrated 5% GPU-timestamp resolution cannot be promoted into a reusable dual-axis architecture-ranking protocol in Lane I.

## Why this is not “measurement floor established”

A measurement floor requires a contiguous effect size that later lanes may safely claim under the accepted protocol, for example +20% passes while +10% fails.

Here the complete CPU-wall axis is non-monotonic: +20% fails while smaller deltas pass. There is no frozen common 5%, 10%, or 20% floor to carry forward.

## Reuse rule

Later architecture lanes must **not** use `lane-i-i002-v1` to make a formal architecture-ranking timing claim.

The I003 GPU-timestamp evidence may motivate a new architecture-neutral measurement-methodology experiment in which GPU timestamp is explicitly primary and complete CPU wall is explicitly diagnostic. Such a change must be designed and frozen **before** new accepted target calibration; I003 cannot be reinterpreted post hoc as that calibration.

No forced GPU performance state, outlier deletion, favorable rerun, or threshold adjustment is permitted.

## Shared methodology

The shared timing protocol is not updated with a newly accepted promotion method because Lane I did not accept one.

## Next question

Can a new safely pre-frozen calibration protocol make GPU timestamps the primary performance boundary, while retaining complete CPU wall only as a health/provenance diagnostic, and still demonstrate robust known-delta resolution before any architecture comparison?
