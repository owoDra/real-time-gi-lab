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

## Final disposition

Lane K is complete.

- K001 target workload validation: PASS.
- K002: `lane-k-k002-v1` frozen before target timing.
- K003: GPU-primary baseline control passed; +20%, +10%, and +5% known deltas
  were detected contiguously across eight fresh processes.
- K004 outcome: **GPU-primary protocol accepted**.
- Smallest demonstrated safe effect size on the measured target: **5%**.

Canonical result documents:

- `results/003-target-calibration.md`
- `results/004-program-timing-capability.md`

Downstream architecture timing must import the accepted protocol before target
candidate timing and freeze a promotion threshold no smaller than 5%. Historical
diagnostic timing is not promoted retroactively.
