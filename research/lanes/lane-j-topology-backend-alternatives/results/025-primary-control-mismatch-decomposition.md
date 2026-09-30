# J004 primary-control mismatch decomposition v6

Status: **DIAGNOSTIC TARGET RERUN REQUIRED — formal timing not started**
Issue: #23

The retained v4 validation artifact established that
`large-global-high/primary/control` fails only the exact Hit/tie contract:

- hit mismatch: 445
- nearest-hit/tie mismatch: 445
- traversal runtime errors: 0
- storage failures: 0
- immutable-owner mutations: 0

CPU/GPU static-vs-dynamic merge rules were reviewed and are semantically
identical, while descriptor rebinding is explicit and valid. The remaining
ambiguity is whether the mismatches originate in the static HWRT traversal, the
dynamic HWRT rebuild traversal, or only the final static/dynamic merge.

Commit `9dd9f7f84de6d2cb642c24f81217c48995cc79ee` adds validation-only readback
and counters for those three components. Formal timing code, workload,
thresholds, selector, rerun policy, and pass criteria are unchanged.

The diagnostic rerun must remain fail-closed; it is not evidence for ranking.
