# Lane K — GPU-primary timing calibration

Issue: #21  
Branch: `research-lane-k-gpu-primary-calibration`  
Exact base: `research@81f8cbd0673a1035e8b586a9ce21aa33fa18ab8d`

Lane K is a new architecture-neutral calibration lane. It does not reinterpret
Lane I I003 and does not alter Lane I I004.

Only architecture-neutral mechanism is selectively ported from Lane I:
deterministic known work, identical resource/layout/dispatch shape, checksum
validation, batched GPU timestamps, paired ordering, fresh-process replication,
and complete raw-sample retention.

Lane K owns a new role split frozen before target timing:

- GPU timestamp: primary performance decision axis;
- complete CPU wall: diagnostic / health / provenance only.

Forced GPU power/clock state, outlier deletion, fastest-subset selection,
favorable reruns, and post-hoc threshold changes are forbidden.
