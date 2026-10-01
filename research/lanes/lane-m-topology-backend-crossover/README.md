# Lane M — topology backend crossover

Issue: #25

Status: **complete / accepted — Lane E incumbent retained**

Candidates were the Lane E incumbent object-local rebuild, Lane G hardened
transient LBVH, and Lane J clustered two-level object-local BVH.

M001 used one qualified J004-derived complete recurring boundary for all three
backends. J002 topology workloads, Lane L dual-context capability, the 20%
decision floor, 1.25x memory hard guard, exact correctness/identity gates, and
zero-rerun policy were frozen prospectively.

Target validation passed unchanged, then the formal campaign completed all 192
fresh timing processes and retained all 6,144 timing rows.

Neither LBVH nor clustered qualified for promotion in any required mutating
scenario on either track. All candidate memory hard guards passed; the rejection
is performance-driven. The conditional direct LBVH-vs-clustered stage did not
run because no scenario/track had two promoted candidates.

Canonical detailed results:

- `results/001-gpu-independent-preparation.md`
- `results/002-m001-formal-crossover.md`

Implementation behavior belongs in source/doc comments/tests. Research docs
retain protocol, provenance, evidence limits, and decisions.
