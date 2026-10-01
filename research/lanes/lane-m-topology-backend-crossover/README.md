# Lane M — topology backend crossover

Issue: #25

Status: **GPU-independent preparation frozen; accepted target timing not started**

Candidates are the Lane E incumbent object-local rebuild, Lane G hardened
transient LBVH, and Lane J clustered two-level object-local BVH.

M001 uses one qualified J004-derived complete recurring boundary for all three
backends. J002 topology workloads, Lane L dual-context capability, the 20%
decision floor, 1.25x memory hard guard, exact correctness/identity gates, and
zero-rerun policy are frozen prospectively.

Implementation behavior belongs in source/doc comments/tests. Research docs
retain only protocol, provenance, evidence limits, and decisions.

Next boundary: target validation. Accepted formal timing remains forbidden until
validation passes unchanged.
