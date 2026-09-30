# Lane J — topology-changing object-local backend alternatives

Issue: #20  
Branch: `research-lane-j-topology-backend-alternatives`  
Base: `research@76f65f8944aba8405dce5d386161df2540957349`

## Current status

**COMPLETE — J003 correctness/memory PASS; J004/J005 measurement-limited.**

J001 retained one new structurally different candidate:

- object-local clustered two-level BVH with dirty-cluster rebuild,
  upper-level refit/rebuild, and exact triangle refinement.

J003 now validates that candidate across all five frozen topology profiles on the
target RADV GPU with zero exact-Hit mismatches and zero traversal runtime errors.
The large-global profile also validates the frozen 256 -> 512 persistent-slot
resize path and true-peak lifetime accounting.

Lane I / Issue #19 concluded `target timing unsuitable` for its frozen
dual-axis protocol. Therefore J004 formal performance ranking is not permitted,
and J005 cannot run because it requires a J004-retained candidate.

Final disposition:

- Lane E ownership/update semantics remain incumbent;
- clustered two-level BVH is correctness- and absolute/lifetime-memory-qualified for a future topology-changing crossover;
- the frozen J003 same-run <=1.25x Lane-E HWRT relative-memory gate remains pending and must be completed before formal J004 timing;
- hardened transient LBVH remains a qualified control;
- no performance winner is declared;
- Lane J closes **measurement-limited**.

## Source of truth

- J001 research and candidate disposition:
  `results/001-deep-architecture-survey.md`
- Frozen J002-J005 plan:
  `experiments/plan-v1.md`
- Pre-evidence J003 corrections:
  `experiments/plan-v1.1-amendment.md`
  `experiments/plan-v1.2-amendment.md`
- Persistent GPU layout policy:
  `experiments/plan-v1.3-amendment.md`
- Rejected pruning hypotheses:
  `experiments/plan-v1.4-amendment.md`
  `experiments/plan-v1.5-amendment.md`
- Retained exact-intersection correction:
  `experiments/plan-v1.6-amendment.md`

No production candidate implementation belongs in this first session.

- GPU-independent checkpoint:
  `results/002-gpu-independent-preparation.md`
- Canonical J003 CPU structural result:
  `results/003-cpu-structural-gate.md`
- First GPU-required gate:
  `experiments/003-gpu-prototype-gate.md`


## Final evidence

- All-profile persistent Vulkan PASS:
  `results/017-all-profile-persistent-vulkan-pass.md`
- Lane final decision:
  `results/018-final-decision.md`

The v1.4/v1.5 AABB-pruning hypotheses are retained only as rejected research
history; their shader changes were reverted. v1.6 is the retained
exact-intersection correction.


## Post-closure formal crossover follow-up

Issue: #23  
Branch: `research-lane-j-formal-crossover`

Lane K / #21 subsequently accepted the reusable GPU-primary protocol with a
5% demonstrated measurement floor. The historical #20 conclusion above is
retained unchanged; #23 is a prospective follow-up rather than a rewrite.

Current follow-up status:

- J004 gate v1 is frozen before accepted candidate timing:
  `experiments/004-formal-crossover-gate-v1.md`;
- the same-run <=1.25x Lane-E HWRT relative-memory preflight has now **FAILED**;
- clustered two-level BVH is rejected before formal timing:
  `results/020-relative-memory-preflight-fail.md`;
- J004 may continue only with the remaining pre-frozen variants/controls;
- pre-timing self review produced a v2 executable-method amendment without
  changing workload/threshold/selector:
  `experiments/004-formal-crossover-gate-v2-amendment.md`;
- v2 exposed a compile-only namespace error before any timing;
- v3 then exposed a link-only missing-source dependency before any timing;
- the link-only correction is refrozen as v4 and is ready for target execution:
  `results/023-formal-crossover-link-fix-freeze.md`;
- J005 remains forbidden unless the formal target campaign retains another
  candidate.
Preparation checkpoint:
`results/019-formal-crossover-preparation.md`.

- v4 built/linked but hard validation stopped at `large-global-high/primary/control` before timing; diagnostic visibility record:
  `results/024-formal-validation-diagnostic-visibility.md`.

- component-level root-cause diagnostic for the retained large-global primary-control failure:
  `results/025-primary-control-mismatch-decomposition.md`.
