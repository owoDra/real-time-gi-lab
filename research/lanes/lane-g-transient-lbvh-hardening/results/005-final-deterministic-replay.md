# G005 — Final deterministic same-boundary replay

Status: **complete — deterministic correctness/memory PASS; production promotion measurement-limited**

Measurement commit: `81ca547fa7c1541db15cef3ad3ac83609a34d716`.

Evidence class: deterministic correctness+memory only.

## Provenance

- artifact: `out/research/lane-g-transient-lbvh-hardening/005-final-deterministic-replay/20260929T174627Z`;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- plan: `lane-g-g005-deterministic-v1`;
- validation: enabled;
- rows: **60 / 60** retained;
- variants: 5;
- scenarios: 12;
- power/clock manipulation: none.

Run-local variants:

- unchanged transient LBVH;
- hardened transient LBVH;
- vanilla software;
- combined HWRT;
- combined software/B003.

All five execute through the same Lane-G I001 runtime and campaign.

## Correctness and workload identity

All required rows passed:

- quality PASS;
- visibility mismatches = 0;
- producer semantic errors = 0;
- hit mismatches = 0;
- traversal runtime errors = 0;
- missing/leaked probes = 0;
- stale storage slots = 0;
- resolved-output mismatches = 0;
- storage failures = 0;
- overflow = 0.

For every scenario, the frozen workload identity fields matched across all five
variants.

**Correctness/workload gate: PASS.**

## Memory

Every required scenario satisfies:

- hardened true lifetime peak <= 3.0x run-local vanilla;
- hardened peak regression vs unchanged LBVH <=10%.

In practice the hardened candidate reduced peak memory vs unchanged LBVH in
**every** required scenario.

The previously blocking sparse rows are:

| scenario | unchanged LBVH | hardened LBVH | vanilla | hardened / vanilla | peak change vs unchanged |
| --- | ---: | ---: | ---: | ---: | ---: |
| sparse-stress | 119,078,592 B | **104,595,424 B** | 38,616,288 B | **2.708583x** | **-12.16%** |
| sparse-moving | 123,668,160 B | **104,233,440 B** | 38,616,288 B | **2.699209x** | **-15.72%** |

Across the full replay, the worst hardened/vanilla ratio is the sparse-stress
**2.708583x**, below the frozen 3.0x ceiling. The smallest peak reduction vs
unchanged LBVH is also sparse-stress at **12.16%**.

**Memory gate: PASS.**

This closes the deterministic F007 sparse-memory blocker.

## G004 class-scoped semantic evidence

G004 already passed all 16 frozen semantic cases, including separate rigid,
stable-topology deforming, and topology-changing/high-churn workloads.

That establishes that the G003 lifetime change did not break those semantics.
It does **not** establish a class-scoped performance crossover because G002 did
not produce a decision-valid timing protocol.

## Timing

G002 closed without a safe decision-valid timing protocol. The proposed
power-state isolation experiment was abandoned after a host crash and must not
be rerun.

Therefore G005 timing fields are not used for PASS/FAIL.

**Timing gate: INCONCLUSIVE / UNEVALUATED.**

## Lane E comparator and replacement claim

The accepted Lane E final candidates live in a divergent integration runtime.
They were not ported solely for this deterministic replay because the resulting
campaign still could not support the frozen timing-based replacement gate.

Historical E005 remains context only.

Consequently:

- no Lane E superiority claim is made;
- no Lane E replacement claim is made;
- Lane E remains the incumbent ownership/update architecture.

## Final Lane G disposition

Lane G resolves one of Lane F's two formal blockers and leaves the other
unresolved:

1. **Sparse peak memory: resolved.**
   Hardened immutable-static-HWRT lifetime scheduling/release brings every
   required row under the 3.0x vanilla ceiling and reduces peak memory vs the
   unchanged transient LBVH.
2. **Decision-valid timing repeatability: unresolved.**
   No safe accepted timing protocol was established.

Final outcome:

**mechanism retained; deterministic memory/correctness hardening accepted;
production promotion measurement-limited.**

The hardened transient LBVH remains useful research evidence and a plausible
future object-local rebuild mechanism, especially at topology-changing/high-
churn boundaries, but it is **not promoted into or above Lane E** without new
safe same-boundary timing evidence.

No further Lane G experiment is required under Issue #17's frozen plan.
