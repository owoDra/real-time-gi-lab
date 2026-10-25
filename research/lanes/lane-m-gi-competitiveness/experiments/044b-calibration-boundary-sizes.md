# 044b — Calibration boundary sizes matched to the actual role samples

Prospective amendment of 044 (`1f900a16`) and 044a (`712a2907`), written after
three disclosed development processes (two neutral, one H01/B8 target) and
BEFORE the registered preparation, calibration or any target timing. The
development target samples show complete-frame role costs of roughly 0.7-2 ms
(single submit) and about 21 ms for raw PT 1024spp (16 submits of ~1.3 ms);
the registered neutral sizes (~5 ms single, 16 x ~20 ms) do not cover the
sub-millisecond boundary. Per the protocol rule to calibrate the actual
boundary, the calibration uses THREE neutral sizes, all required:

- tiny: one submit, base 600 (~0.7 ms);
- short: one submit, base 4400 (~5 ms);
- multi: 16 submits, base 1100 (~1.25 ms each, ~20 ms total).

Each size keeps control/+5/+10/+20% comparisons; MDE = smallest delta resolved
at ALL three sizes. Every other 044 rule, threshold (1.20 practical ratio,
Lane-K control/candidate criteria), comparison, role, process count and stop
rule is unchanged. No ratio, statistic or decision was computed from the
development samples; they remain inventoried development evidence only.
