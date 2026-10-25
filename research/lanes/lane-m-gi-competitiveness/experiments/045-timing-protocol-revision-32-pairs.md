# 045 — Final timing-protocol revision: 32 measured pairs per process

Registered after 044 publication `a8d5f412`, before any 045 code, build or GPU
execution. 044 calibration v2 resolved every neutral delta (+5/+10/+20% within
~1%, all process effects above the control envelope) but its control failed the
frozen per-process order-bias limit (2.4% short, 4.2% multi; limit 2%), while
the pooled position effect was only 0.0-0.6%. The failing statistic is
|median(AB) - median(BA)| from 6+6 pairs per process, maximized over 8
processes, i.e. dominated by small-sample noise.

## Single change

Measured pairs per comparison per process: 12 -> 32 (16 AB + 16 BA under the
044d rule AB iff pair+process even); 4 warmup pairs. Everything else is the
044/044b/044c/044d design unchanged: host roles and SPIR-V, three neutral sizes
(tiny 600, short 4400, multi 16x1100), 8 fresh processes, Lane-K control and
candidate criteria (control |process medians|<=log1.02, span<=log1.03, order
bias<=log1.02; candidate span<=log1.05, order bias<=log1.03, same-sign pair
fraction>=0.75), MDE at all three sizes, T1 threshold max(log1.20,log(1+MDE)),
T2-T4 dominance rules, published quality inputs, six targets in fixed order,
fence/wall guards, no exclusions.

## Execution and stop

New roots `m001-timing045-*`: preparation (host with a `--measured` option, the
44 contract suite plus a 32-pair schedule contract), calibration once, then the
six target campaigns. The host's analysis requires exactly 16 AB + 16 BA
measured pairs. This is the LAST protocol revision for these boundaries in Lane
M: if the control fails again, the timings remain TIMING_INCONCLUSIVE and no
further revision, rerun or threshold change is made. A passing control does not
retroactively validate 044. No power/clock change; one GPU; static targets.
