# Codex research instructions

This repository is a measurement-driven GI research lab.

## Program source of truth

- `research` is the long-lived program integration/source-of-truth branch.
- `research/status.md` is the canonical cross-lane architecture/status/roadmap.
- Detailed experiment evidence remains canonical on each lane branch under
  `research/lanes/<lane>/results/`.
- `research/protocol.md` is the shared evidence and measurement methodology.
- Do not copy complete lane result documents into `research`.

## Branch discipline

Routine experiment work happens directly on exactly one lane branch using the
`research-lane-*` naming convention.

Completed branches currently include:

- `research-lane-a-split-rc`
- `research-lane-b-traversal`
- `research-lane-c-storage-locality`
- `research-lane-d-producer-optimization`
- `research-lane-e-dynamic-geometry`
- `research-lane-f-dynamic-geometry-alternatives`
- `research-integration-gate`

Issue #17 proposes
`research-lane-g-transient-lbvh-hardening`, but implementation must not begin
until the post-A-F synthesis amendments described by `research/status.md` are
reflected in the lane plan.

- Push normal experiment commits directly to the active lane branch.
- Do not create pull requests for normal research iterations.
- Do not merge lane implementation branches wholesale into `research`.
- Do not merge another active lane into the current lane unless explicitly
  requested.
- A new lane must fork from the explicit program checkpoint named by its plan.
- If a common harness/methodology change is discovered inside a lane, record the
  evidence first; promote only genuinely shared rules back to `research` at an
  explicit synthesis checkpoint.

## Lane ownership

Each lane owns disjoint paths based on its lane slug:

- `src/research/<lane_snake_case>/**`
- `shaders/research/<lane_snake_case>/**`
- `scripts/research/<lane_snake_case>/**`
- `research/lanes/<lane-kebab-case>/**`

Integration work uses its dedicated integration paths.

Shared roots such as `CMakeLists.txt`, `mise.toml`, common `src/` or
`shaders/` files, and `research/protocol.md` are read-mostly from lane
branches. Change them only when unavoidable and document why.

## Environment

Use mise. Do not introduce a second environment/bootstrap path.

Normal commands:

- `mise install`
- `mise run build`
- `mise run research:check`
- `mise run research:record --lane ... --experiment ... --command "..."`

Vulkan validation layers are diagnostics, not a prerequisite for accepted
performance timing. Semantic/correctness guards are always required.

## Research method

1. State a falsifiable question and freeze decision gates before optimizing.
2. Preserve semantic parity before comparing performance.
3. Include all costs required by the candidate architecture. Isolated kernel
   wins do not promote an architecture if producer, allocation, update,
   invalidation, scheduling, build, transfer, merge, or synchronization costs
   erase the win.
4. Do not manufacture favorable ordering in synthetic producers. Synthetic
   distributions are allowed only for bring-up or isolated controls and must be
   labeled as such.
5. Prefer the simplest experiment that can reject a hypothesis.
6. Do not infer a cache/memory mechanism from timestamps alone.
7. Results on one GPU are not universal claims.
8. Keep accepted/rejected/inconclusive/diagnostic-only distinctions exact.
9. Never turn unstable timing into PASS/FAIL by deleting outliers or relaxing a
   threshold after measurement.
10. Historical numbers with different boundaries are context, not formal
    run-local gates.

## Result lifecycle

For every experiment:

1. Create/update `research/lanes/<lane>/experiments/NNN-name.md` with question,
   hypothesis, protocol, correctness gate, timing/repeatability rules, and
   decision gate.
2. Run through `mise run research:record` when practical. Raw artifacts go to
   `out/research/<lane>/<experiment>/<timestamp>/` and stay out of Git.
3. Record the concluded evidence class and decision in
   `research/lanes/<lane>/results/NNN-name.md`.
4. Add one entry to that lane's `results/index.json`.
5. Update the lane README only when the lane-level conclusion/next decision gate
   changes.
6. Update `research/status.md` only at an explicit cross-lane synthesis or
   program checkpoint.

Implementation behavior belongs in source/doc comments/tests. Research docs
record rationale, protocols, evidence, limitations, and decisions that cannot
be reconstructed from code alone.
