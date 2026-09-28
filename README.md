# phos-gi-lab

Measurement-driven research sandbox for a GPU-locality-aware real-time global
illumination architecture.

## Current program

The standalone M0 cache/scheduler investigation is concluded. It established
that coherent access can materially improve hash lookup, but the tested
post-generation global reorder is too expensive and only becomes conditionally
competitive when a large query population is naturally reused roughly five to
six or more times.

Research now moves to a representative **Split Radiance Cascades** workload and
runs three parallel lanes:

- **Lane A — Split RC producer/transport**: generate the real GPU query/update
  stream and implement the minimum gather/merge/resolve semantics.
- **Lane B — traversal**: compare StrataBrick, hardware RT/TLAS where practical,
  and simpler software traversal under dynamic GI-like rays.
- **Lane C — radiance storage/locality**: compare sparse hash, hashed brick
  pools, virtual/clipmap storage, and justified StrataBrick-inspired layouts on
  the real producer stream.

See [research/README.md](research/README.md) for branch topology, issues,
dependencies, and the experiment lifecycle.

## Source of truth

- [Research program](research/README.md)
- [Research protocol](research/protocol.md)
- [Historical charter](docs/research.md)
- [M0 status/evidence](docs/status.md)
- [Codex instructions](AGENTS.md)

Implementation behavior remains authoritative in source code, doc comments, and
executable correctness guards. Research documents preserve hypotheses,
protocols, evidence, limitations, and architectural decisions.

## Environment

The workflow is managed by mise. A host C++20 compiler and Vulkan 1.3
driver/loader are required.

```bash
mise install
mise run build
mise run research:check
```

Run a lane experiment through the artifact recorder when practical:

```bash
mise run research:record \
  --lane lane-a-split-rc \
  --experiment 001-producer-stream \
  --command "build/release/<lane-executable> ..."
```

The command receives `PHOS_RESEARCH_ARTIFACT_DIR` and may write structured
CSV/JSON data there. The harness always records command/stdout/stderr, Git
commit/branch/dirty state, host metadata, and timestamps.

Raw artifacts are intentionally ignored by Git:

```text
out/research/<lane>/<experiment>/<timestamp>/
  metadata.json
  stdout.log
  stderr.log
  ... lane-specific CSV/JSON
```

Accepted/rejected/invalidated conclusions are committed in the corresponding
`research/lanes/<lane>/results/` directory and indexed by that lane's
`results/index.json`.

The existing M0 commands remain available for historical controls:

```bash
mise run bench
mise run bench:sweep
```
