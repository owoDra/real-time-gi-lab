# Lane J — topology-changing object-local backend alternatives

Issue: #20  
Branch: `research-lane-j-topology-backend-alternatives`  
Base: `research@76f65f8944aba8405dce5d386161df2540957349`

## Current status

**J001 complete / J002-J005 plan frozen / candidate implementation not started.**

J001 retains one new structurally different candidate:

- object-local clustered two-level BVH with dirty-cluster rebuild,
  upper-level refit/rebuild, and exact triangle refinement.

Controls remain:

- Lane E object-local HWRT rebuild;
- Lane E/B003 software rebuild where practical;
- hardened transient LBVH;
- unchanged LBVH/accounting controls as required.

Formal timing is blocked on Issue #19 / Lane I.

## Source of truth

- J001 research and candidate disposition:
  `results/001-deep-architecture-survey.md`
- Frozen J002-J005 plan:
  `experiments/plan-v1.md`
- Pre-evidence J003 correction:
  `experiments/plan-v1.1-amendment.md`

No production candidate implementation belongs in this first session.
