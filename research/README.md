# Research program

Umbrella issue: #9

The goal is not to prove a predetermined representation. The goal is to find
whether a complete real-time GI architecture can exploit naturally produced GPU
locality while remaining correct, dynamic, memory-efficient, and cheaper
end-to-end than representative alternatives.

## Branch topology

```text
research
├── research/lane-a-split-rc          # Issue #10
├── research/lane-b-traversal         # Issue #11
└── research/lane-c-storage-locality  # Issue #12
```

Normal iterations are committed and pushed directly to the active lane branch.
No routine PRs are created. The lanes are integrated into `research` only at
explicit evidence-backed checkpoints. Final convergence is tracked by Issue #13.

## Why the lanes are separate

Lane A establishes the representative Split RC producer stream.

Lane B can independently bring up traversal candidates using clearly labeled
GI-like controls, then must repeat final comparisons against Lane A's real
stream.

Lane C can independently implement storage candidates and correctness tests,
then must repeat final locality/performance comparisons against Lane A's real
stream.

The branch/file ownership rules in the root `AGENTS.md` keep each lane's
source, shaders, scripts, experiment protocols, and results in disjoint paths so
later integration does not create avoidable merge conflicts.

## Evidence flow

```text
question + decision gate
        ↓
lane experiment implementation
        ↓
raw run → out/research/<lane>/<experiment>/<timestamp>/
        ↓
correctness review
        ↓
accepted / rejected / invalidated result
        ↓
research/lanes/<lane>/results/*.md + results/index.json
        ↓
lane decision
        ↓
explicit integration checkpoint
```

Raw artifacts are not committed because they can be large and machine-specific.
The committed result must contain enough numeric evidence, artifact path,
hardware/workload identity, limitations, and decision rationale to audit the
conclusion.

## Program dependencies

1. Lane A must eventually publish a stable representative producer stream or
   replay schema.
2. Lane B and C may progress in parallel before that, but their final
   architectural decisions must use the Lane A stream.
3. Producer-side locality is evaluated only after the producer exists; do not
   replace it with a producer invented solely to emit favorable ordering.
4. Integration (#13) starts only after each lane has a documented decision gate
   result.

See [protocol.md](protocol.md) for the rules shared by all lanes.
