# phos-gi-lab

Measurement-driven research sandbox for a GPU-locality-aware real-time global
illumination architecture.

## Current program

The original M0 cache/scheduler study and research Lanes A-F are concluded.
Integration #13 is also complete.

The current evidence-backed Split Radiance Cascades architecture is:

- A001 GPU visibility-driven producer with its natural append order;
- HWRT/TLAS as primary traversal on the measured AMD Radeon 8060S target;
- segment DDA/hash + conservative quantized Micro BVH8 as the software fallback;
- per-probe open-addressed sparse hash radiance storage;
- Lane E object-local dynamic-geometry ownership:
  - immutable static acceleration data;
  - transform-only rigid instances;
  - object-local UPDATE for stable-topology deformation;
  - object-local rebuild boundaries for topology changes.

Lane D did not replace A001. Renderer depth reuse remains a conditional
integration optimization and bounded-capacity/safe-overflow remains
non-promoted memory-policy evidence.

Lane F did not promote a transient architecture. The sorted two-level grid is
not retained as the next direction. Transient LBVH remains promising, but its
sparse-memory gate failed and required timing remained inconclusive after the
permitted rerun.

The next proposed work is Issue #17 / Lane G, after its plan is amended to
diagnose memory ownership and timing repeatability first and to compare against
the accepted Lane E incumbent under a common boundary.

See:

- [research/status.md](research/status.md) — canonical A-F synthesis, current
  architecture, unresolved questions and roadmap;
- [research/README.md](research/README.md) — branch/program topology and
  evidence flow;
- [research/protocol.md](research/protocol.md) — shared methodology.

## Source of truth

- [Current research status](research/status.md)
- [Research program](research/README.md)
- [Research protocol](research/protocol.md)
- [Historical charter](docs/research.md)
- [M0 status/evidence](docs/status.md)
- [Codex instructions](AGENTS.md)

Implementation behavior remains authoritative in source code, doc comments, and
executable correctness guards. Lane result documents preserve detailed
hypotheses, protocols, evidence, limitations, and architectural decisions.
`research/status.md` preserves only cross-lane synthesis rather than copying
experiment details.

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
  --lane <lane> \
  --experiment <experiment> \
  --command "<lane runner>"
```

The command receives `PHOS_RESEARCH_ARTIFACT_DIR` and may write structured
CSV/JSON data there. The harness records command/stdout/stderr, Git
commit/branch/dirty state, host metadata, and timestamps.

Raw artifacts are intentionally ignored by Git:

```text
out/research/<lane>/<experiment>/<timestamp>/
  metadata.json
  stdout.log
  stderr.log
  ... lane-specific CSV/JSON
```

Detailed accepted/rejected/inconclusive conclusions remain in the corresponding
lane branch's `research/lanes/<lane>/results/` directory and
`results/index.json`.

The existing M0 commands remain available for historical controls:

```bash
mise run bench
mise run bench:sweep
```
