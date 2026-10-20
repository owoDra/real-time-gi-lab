# Sponza T_B8 cannot qualify under the frozen screen with either retained sampler (743)

2026-10-20 JST. POST-HOC analysis of already-retained bytes; no native, no GPU.
Not a reference result, not an amendment. Frozen001 screen: pairwise active
luma p99 absolute ≤1e-5 and relative ≤5%, two consecutive qualifying levels,
cap262144.

## Evidence

Retained original digital-shift RQMC ladder `references-recovery-sponza-v1/C1_T_B8`
(the sampler that qualified the existing16 slots):

| spp | max pairwise active abs p99 | source |
| --- | --- | --- |
| 8192 |7.222e-5 | retained screen, 4 seeds |
| 16384 |5.037e-5 | retained screen |
| 32768 |3.540e-5 | retained screen |
| 65536 |2.452e-5 | retained screen |
| 131072 |**1.694e-5** (s0–s1 only; max over all pairs is ≥ this) | retained partial `o.n131072.s0/s1.f64` |
| 262144 | ≈1.20e-5 (1/√N extrapolation) | projection |

Each doubling scales by0.70 ≈1/√2 (no RQMC rate gain at this depth). Because
131072 already fails on one actual pair, two consecutive qualifying levels within
the cap are impossible: **C1 T_B8 is certain INELIGIBLE under the frozen rule**,
independent of the unacquired262144 level. Passing both131072 and262144 would
need ≈2.9× lower per-sample variance.

Compensated all-split627 (737 seed0, 8192spp, retained bytes): per-pixel luma
SE implies MC-predicted pairwise p99 8.51e-5 versus8.99e-5 for the old sampler's
seed0 (ratio0.945; calibrated by the old sampler's observed/predicted0.803 →
6.83e-5). Per-sample cost is ~61µs versus ~34µs (old 16-thread incremental
levels). Thus627 does not change feasibility and is ~1.7× less efficient.
Its means agree with the old sampler to −2.6e-5 relative (whole-frame luma).

Noise is spatially broad: at65536 the median per-pixel replicate SD is5.5e-6,
p99 1.3e-5, relative SD median0.27%; exceeding pixels are spread over all
rows/columns (no hotspot). Local fixes cannot close the gap.

## Consequence

The remaining N010 reference gate for Sponza T_B8 (C1–C4, C5/C6) is not a
compute or numerical-guard problem: the frozen per-replicate screen is
unreachable at the frozen cap with the retained estimators. Continuing737/738
or the172 ladder for C1 T_B8 would spend ≈140–250h of four-core CPU to reach a
known INELIGIBLE. Not launched. Viable routes all need an explicit decision:
(1) a prospective, disclosed eligibility amendment; (2) declared exclusion of
Sponza T_B8 from scored scope; (3) ≥3× variance-reduction research.
For reference, at65536 the old sampler's per-replicate noise RMS(9.1e-6) is
0.41% of mean luma (pooled 4-seed ≈0.2%), against quality targets of total
NRMSE≤5% / indirect≤10%. N010 NOT_READY; Tests NOT RUN.
