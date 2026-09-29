# G005 — Final deterministic same-boundary replay

Status: **implementation complete; target-GPU evidence pending**

Evidence class: deterministic correctness+memory only.

## Scope

Run-local variants:

- unchanged transient LBVH;
- hardened transient LBVH;
- vanilla software;
- combined HWRT;
- combined software/B003.

All five execute through the same Lane-G I001 runtime and the same 12-scenario
campaign.

## Required deterministic gates

Every row must pass exact correctness/storage/overflow validation.

For each scenario, workload identity must match across all five variants for
work/output counts, requested work/output counts, visible owners, moved
primitives, and segment-membership changes.

Memory gates:

- hardened true lifetime peak <= 3.0x run-local vanilla in every scenario;
- sparse-stress and sparse-moving independently pass that ceiling;
- hardened peak does not regress >10% vs unchanged LBVH in any required case.

## Timing / Lane E limitations

G002 closed without a safe decision-valid timing protocol. Timing is therefore
not used for G005 PASS/FAIL.

The accepted Lane E final candidates live in a divergent integration runtime.
They are not ported solely for this deterministic replay because doing so would
create a new integration implementation while still not enabling a formal
timing-based replacement claim.

Historical E005 remains context only. No Lane E replacement/superiority claim is
permitted. No GPU power/clock manipulation is allowed.

## Final decision rule

If the deterministic gates pass, Lane G retains the hardened LBVH mechanism as a
correct lower-memory mechanism. Production promotion remains
**measurement-limited** because timing superiority cannot be established under
an accepted safe protocol.

Pending target-GPU artifacts.
