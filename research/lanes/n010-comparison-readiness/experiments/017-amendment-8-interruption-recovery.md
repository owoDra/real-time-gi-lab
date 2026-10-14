# N010 Amendment 8 — recover externally terminated reference acquisition

Prospective recovery after the terminal exits recorded in 065. The cause is
unestablished; complete and partial output hashes are retained. A stale WAITING
file is not a live process. No accepted GPU calibration was acquired.

Recovery uses the already proved exact CPU prefix implementation (009/022/050)
and changes no physical calculation, sample point, dimension, seed, level,
cap, convergence screen or stop condition. It adds recovery of complete
previous levels from a terminated acquisition, rather than requiring a fresh
8192 level. This supersedes Amendment 6's fresh-first-level scheduling rule
only for this recovery. The original in-progress jobs are confirmed terminal;
they were not voluntarily stopped before their declared transport boundary.

Copy every complete contiguous prefix through its last hashed metadata into
a fresh directory, including scene, all f64/component/hit payloads, metadata
and screen manifests. Verify canonical locked state/geometry, original or
proved incremental binary/net, fixed replicate headers, all hashes, unchanged
convergence results and previous-prefix/proof chains. Preserve imported bytes
and source identities. Record the source directory/inventory and the fact that
old later partial seeds remain there, ineligible. Never fill an old partial
directory or choose between samples according to their values.

Continue the next full level with the original four seeds from the last
complete prefix. The unchanged incremental executable restores exact dyadic
sums/moments and integer counters. The new level retains sample interval,
previous metadata/payload hashes and the proof dependency chain. Earlier
ineligible screens remain; stop at the first qualifying consecutive pair or
262144. Imported original levels retain original binary provenance, while
later levels identify the incremental binary. Preflight must verify both.

Required recovery slots: C1 T_B8 from original 16384; C3 T_B8 from original
8192; C2 T_B2 from complete incremental 8192. Remaining C2 T_B8/C4/C5/C6
start fresh with the proved variant. All other eligible original slots remain
selected. A new full-24-slot view and driver must retain predecessors 059/061
and both terminated driver statuses. No quality-based selection, exclusions,
relaxed threshold, cap failure claim for an unexecuted cap, or silent retry of
accepted timing is allowed.

Compiler trials for the GPU feasibility port must have explicit memory/CPU/
elapsed limits before another compilation. Any alternative `NoContraction`
SPIR-V implementation of precise arithmetic is frozen before its first GPU
output; it still needs every Amendment 7 conformance/physical eligibility gate.
