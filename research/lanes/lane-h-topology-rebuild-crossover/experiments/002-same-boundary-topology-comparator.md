# H002 — same-boundary object-local topology comparator

Status: **GPU-independent contract/harness complete; GPU backend implementation pending**

H002 does not choose a winner. It creates the minimum Lane-H-owned comparator
contract required for a later H003 same-boundary timing campaign.

The machine-readable source of truth is
`002-same-boundary-topology-comparator-config.json`. `h002_contract.py` owns deterministic workload and lifetime-accounting rules; `run_h002_prepare.py` emits the canonical manifest and validates future candidate evidence before timing can be considered.

## Frozen workload identity

The changed object starts from 796 primitives and follows one deterministic
primitive-count-changing cycle generated from the frozen factors. Each
transition also replaces 25% of the retained primitive population using the
frozen topology seed. This makes primitive-count change and topology churn
explicit instead of treating Lane G's same-count `topology-replace25` case as a
count-changing workload.

All variants must receive the same generated sequence and canonical workload
digest. A candidate-specific topology stream invalidates the comparison.

## Ownership contract

Only `topology-object-0` is mutable. Static world and unrelated object-owned
resources are immutable for every transition. The comparator may read those
resources but must not rebuild, resize, upload, or rewrite them.

## Measurement/accounting contract

Every variant reports the same stage fields. A stage that is not applicable is
reported as zero rather than omitted. Allocation/reallocation, geometry upload,
build/rebuild/maintenance, instance/TLAS update, traversal, synchronization,
merge, and complete wall/GPU boundaries therefore remain auditable.

Memory accounting uses allocation lifetimes. `true_peak_resident_bytes` is the
maximum simultaneous live allocation sum, including old/new allocation overlap
during resize/reallocation. A post-reallocation steady resident number is not a
substitute for the true peak.

## Candidate scope

The planned set is Lane E object-local HWRT rebuild, Lane E object-local
software/B003 rebuild where practical, hardened transient LBVH object-local
rebuild, unchanged transient LBVH control, and a run-local vanilla control.

Lane E/G source-of-truth is input evidence only. Comparator implementation must
remain Lane-H-owned.

## H003 dependency

No H003 formal timing may start from this contract alone. H001 must first pass
its frozen safe repeatability gate. H003 primary axis and promotion evaluation
remain separate decisions to freeze before accepted H003 target timing.
