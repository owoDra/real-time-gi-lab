# G005 — Final deterministic same-boundary replay

Status: **frozen before execution**

G002 did not establish a safe decision-valid timing protocol. G005 therefore
cannot execute the original timing promotion gates without violating the
research protocol.

This G005 is explicitly a **deterministic correctness+memory final replay**.

## Run-local variants

- unchanged Lane-G transient LBVH;
- hardened transient LBVH;
- vanilla software;
- combined HWRT;
- combined software/B003.

All five use the same Lane-G I001 runtime/campaign.

## Scenarios

The replay covers all twelve representative/stress scenarios:

- static, camera-motion, light-motion;
- moving-rigid;
- sparse/dense/large/vertical stable stress;
- sparse/dense/large/vertical moving stress.

G004 already separately validated rigid-large-few, rigid-small-many32,
stable-topology deforming, and topology-changing/high-churn semantics.

## Correctness gates

Every row must pass the exact G004 quality/storage/overflow gates. Workload
identity fields must match across all five variants for each scenario.

## Memory gates

For every required scenario:

- hardened peak <=3.0x run-local vanilla;
- hardened peak must not regress >10% vs unchanged LBVH.

Sparse-stress and sparse-moving are mandatory independent gates.

True lifetime peak is used for the hardened candidate:
`max(setup_peak_bytes, runtime_resident_bytes)`.

## Lane E comparator disposition

The accepted Lane E final implementation lives in a divergent integration
runtime rather than the Lane-G runtime. Porting it here would itself constitute
new integration implementation work.

Because G002 leaves timing promotion unresolved, such a port could not produce
the required timing-based >=10% primary-axis replacement claim anyway.

Therefore G005 does **not** port Lane E solely for deterministic replay and makes
**no Lane E superiority/replacement claim**. Historical E005 is context only.

## Timing

No timing row is used for PASS/FAIL. No GPU power/clock manipulation is allowed.

## Final outcome rule

If all deterministic gates pass, the hardened LBVH mechanism is retained as a
correct, materially lower-memory mechanism, while production promotion remains
**measurement-limited** by unresolved decision-valid timing.

This result may support future class-scoped work, especially topology-changing
object-local rebuild research, but cannot displace Lane E's accepted
rigid/stable-topology ownership architecture.
