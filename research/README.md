# Research program

Umbrella issue: #9

The goal is to determine whether a complete real-time GI architecture can exploit
naturally produced GPU locality while remaining correct, dynamic,
memory-efficient, and cheaper end-to-end than representative alternatives.

## Branch topology

Git cannot store both a `research` ref and refs below `research/...`, so
research branches use a hyphenated prefix.

```text
research
├── research-lane-a-split-rc                 # Issue #10
├── research-lane-b-traversal                # Issue #11
├── research-lane-c-storage-locality         # Issue #12
├── research-lane-d-producer-optimization    # Issue #14
└── research-integration-gate                # Issue #13
```

Routine lane iterations are committed directly to the owning lane branch.
Issue #13 integration selectively carries the accepted implementations/contracts
onto `research-integration-gate`; it does not merge entire lane histories.

## Evidence-backed inputs to Integration #13

- A001 producer/schema v1 and natural append order.
- B002 HWRT/TLAS primary.
- B003 software fallback: segment DDA/hash + conservative quantized Micro BVH8.
- C001 per-probe open-addressed sparse hash.
- D001 renderer depth reuse only as a renderer-integrated incremental contract.
- D005 bounded-capacity/safe-overflow only as a separately measured policy
  candidate.
- D002/D003/D004 are rejected and are not Integration candidates.

These are inputs, not proof that the combined architecture wins.

## Evidence flow

```text
question + frozen decision gate
        ↓
implementation
        ↓
raw run → out/research/<lane>/<experiment>/<timestamp>/
        ↓
correctness + quality review
        ↓
accepted / rejected / invalidated result
        ↓
results index + architectural decision
```

Raw artifacts remain outside Git. Committed results must contain enough
provenance, numeric evidence, limitations and rationale to audit the decision.

See [protocol.md](protocol.md) for shared rules and
[integration/experiments/001-dynamic-end-to-end.md](integration/experiments/001-dynamic-end-to-end.md)
for the frozen Issue #13 gate.
