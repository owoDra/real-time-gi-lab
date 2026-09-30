# J003 pruning hypotheses rejected; shader-path diagnosis promoted

Status: **DIAGNOSTIC GATE — v1.4/v1.5 rejected and reverted**

The representative persistent-Vulkan replay was rerun after both proposed
broad-phase conservativeness corrections.

Observed retained failure remained exactly:

- step: 3;
- ray: 3252;
- required lower-ID primitive: 262389;
- competing primitive: 262932;
- CPU single-triangle delta: 0.0305175781;
- frozen B001 tie tolerance: 0.0306658018;
- reference tie-window classification: true;
- runtime errors: 0.

Neither correction changed the retained mismatch. The aggregate step-3
traversal counters also remained unchanged:

- upper-node visits: 123,458;
- micro-node visits: 922,738;
- exact triangle tests: 34,920;
- watched ray: 41 upper visits / 377 micro visits / 10 triangle tests.

## Decision

Reject the v1.4 caller-limit and v1.5 per-axis slab-roundoff hypotheses as
unsupported by the rerun evidence. Their shader changes are reverted so they do
not remain as unexplained performance-affecting behavior.

No Hit tolerance, tie rule, workload, ray sequence, topology sequence or
candidate structure is changed.

## Next diagnostic boundary

The traversal shader now supports a validation-only watched primitive path.
After a normal mismatch, the runner automatically replays that snapshot with:

- watched ray index = mismatching ray;
- watched primitive ID = expected lower-ID primitive.

The shader reports whether the watched primitive:

1. reached the exact triangle-test leaf;
2. passed GPU triangle intersection;
3. passed the B001 prefer/tie comparator;
4. already had a current Hit when tested;
5. candidate t, current t and current primitive ID at that point.

This diagnostic payload belongs only to the validation Hit buffer and is not
candidate persistent memory.
