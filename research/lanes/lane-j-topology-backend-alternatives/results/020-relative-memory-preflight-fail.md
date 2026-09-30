# J004 relative-memory preflight — clustered candidate rejected

Status: **FAIL — clustered two-level BVH is not timing-eligible**
Issue: #23
Target: AMD Radeon 8060S Graphics (RADV STRIX_HALO)

## Gate

Frozen before target timing:

- candidate persistent bytes <= 1.25x same-run Lane-E object-local HWRT rebuild;
- candidate true-peak resident bytes <= 1.25x same-run Lane-E object-local HWRT rebuild;
- repeated-cycle ownership must remain bounded.

Formal performance timing is not allowed to rescue a candidate that fails this gate.

## Result

The uploaded target artifact `j004-relative-memory-preflight.json` reports:

| profile | max persistent ratio | max true-peak ratio | result |
| --- | ---: | ---: | --- |
| small-global-high | 1.613125 | 0.363624 | FAIL |
| medium-global-representative | 2.129946 | 0.911211 | FAIL |
| medium-local-high | 2.129946 | 0.911211 | FAIL |
| large-global-high | 3.328258 | 1.494583 | FAIL |
| large-local-high | 1.664114 | 0.799896 | FAIL |

Both candidate and comparator remained bounded across the repeated topology cycle,
so this is not an allocation leak/growth failure. It is a relative-residency
failure.

The clustered candidate exceeds the frozen persistent-memory ceiling on **all
five** profiles. The large-global profile additionally exceeds the true-peak
ceiling.

## Decision

The clustered two-level BVH is **rejected before formal performance timing**.

Consequences:

- no J004 timing may be collected for the clustered candidate;
- historical J003 diagnostic timing remains non-decision evidence;
- the failure must not be repaired with a post-hoc memory threshold, selector,
  workload change, favorable profile subset, or rerun;
- J004 may continue only with the other pre-frozen same-run variants/controls;
- J005 may run only if one of those remaining eligible candidates is formally
  retained by J004.

This does not invalidate the J003 correctness result. It rejects the candidate
for the production crossover because it fails the predeclared hard-memory gate.
