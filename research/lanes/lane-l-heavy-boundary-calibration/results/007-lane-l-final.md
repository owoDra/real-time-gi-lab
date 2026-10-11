# Lane L — final decision

## Outcome

Lane L is **complete**.

The heavy recurring boundary does not support the 5% timing capability
demonstrated by Lane K's calibration workload.

Final reusable measurement contract on the measured target:

- environment: `dual-context`;
- primary axis: GPU timestamp;
- CPU wall: diagnostic/health/provenance only;
- heavy-boundary minimum demonstrated effect: **20%**;
- 4 warmup pairs;
- 12 measured pairs;
- 8 fresh-process blocks;
- 16 complete topology transitions per sample;
- frozen AB/BA and environment-order counterbalancing;
- no sample exclusion;
- no instability rerun;
- no completed-campaign rerun;
- all five J002 profiles and both incumbent controls retained as run-local
  health evidence.

## Interpretation

L001 showed that simply sharing one Vulkan context did not restore the original
2%/3% control-health envelope.

L002 then established that the complete heavy recurring boundary can reliably
detect a 20% multiplicative GPU-time effect in the dual-context environment
across all required controls. A 10% effect is not generally separable from the
observed run-local noise, and the single-context environment fails even the
+20% all-control requirement.

Therefore downstream candidate timing must not claim effects smaller than 20%
under this boundary.

This result does not rank topology backends and does not reinterpret J004.

## Downstream

Lane E / Issue #22 is unblocked for a new prospective revalidation campaign,
provided its pre-target gate imports this Lane-L result and sets promotion /
non-regression decision thresholds consistent with the 20% floor.

J005 remains forbidden. Any future Lane-J backend comparison requires a new
experiment identity and must import this measurement contract prospectively.
