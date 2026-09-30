# Lane M — topology backend crossover

Issue: #25

Lane M resolves the remaining topology-changing / high-churn object-local
backend question after Lane E timing revalidation.

Candidate families:

- Lane E incumbent object-local rebuild boundary;
- Lane G hardened transient LBVH;
- Lane J clustered two-level object-local BVH.

Accepted target timing is forbidden until Lane M prospectively freezes its exact
workload, candidate set, Lane-L heavy-boundary import, >=20% decision floor,
memory rule, sample shape, and zero-rerun policy.

Source code, comments, and tests are the implementation source of truth.
Lane docs retain only experiment protocol, provenance, decisions, and evidence
that cannot be represented cleanly in code/tests.
