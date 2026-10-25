# 044d — Pair-order counterbalance correction after the first calibration stop

The registered calibration `m001-timing044-calibration-v1` (implementation
`0e07137d`) completed all 8 native processes (12 comparisons x 16 pairs each,
zero teardown) and then stopped in analysis with INVALID_STOP_NO_RETRY:
"complete measured AB/BA pairs". Cause, verified on the saved pair journals:
the host chose AB iff (pair + position + process) is even, where position =
(comparison - pair) mod L. With an even number of comparisons L (12 for
calibration, 4 for targets) the parity reduces to (comparison + process), so
every comparison ran in ONE order for all pairs of a process (AB in even
processes for even comparisons, BA otherwise). Within-process order bias is then
undefined. The CPU contract had tested a different parity rule, so it missed
the defect. No statistic or decision was computed from v1; its raw data and
failure receipt are preserved unchanged and are not used for any decision.

Correction, before any new GPU execution: AB iff (pair + process) is even, so
each comparison alternates AB/BA across pairs inside every process (6 AB + 6 BA
measured pairs) and the starting order alternates across processes; the
comparison-position rotation is unchanged. The analysis requires exactly 6 AB
and 6 BA measured pairs per comparison per process, and a new contract checks
the host schedule rule itself. A corrected preparation, calibration and target
campaigns use new `-v2` roots. Every other 044/044a/044b/044c rule, threshold,
size, role, comparison and process count is unchanged. v1 is not rerun in place.
