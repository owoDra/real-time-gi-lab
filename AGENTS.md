# Codex research instructions

This repository is a measurement-driven GI research lab.

## Branch discipline

- `research` is the long-lived integration and research source-of-truth branch.
- Routine experiment work happens directly on exactly one lane branch:
  - `research-lane-a-split-rc`
  - `research-lane-b-traversal`
  - `research-lane-c-storage-locality`
  - `research-lane-d-producer-optimization`
- Push experiment commits directly to the active lane branch.
- Do not create pull requests for normal research iterations.
- Do not merge another lane or `research` without an explicit user request.
- If a common harness change is required from a lane, prefer recording the need
  in that lane's result/issue instead of editing shared files. This keeps later
  integration conflict-free.

## Lane ownership

Lane A owns:
- `src/research/lane_a_split_rc/**`
- `shaders/research/lane_a_split_rc/**`
- `scripts/research/lane_a_split_rc/**`
- `research/lanes/lane-a-split-rc/**`

Lane B owns:
- `src/research/lane_b_traversal/**`
- `shaders/research/lane_b_traversal/**`
- `scripts/research/lane_b_traversal/**`
- `research/lanes/lane-b-traversal/**`

Lane C owns:
- `src/research/lane_c_storage_locality/**`
- `shaders/research/lane_c_storage_locality/**`
- `scripts/research/lane_c_storage_locality/**`
- `research/lanes/lane-c-storage-locality/**`

Lane D owns:
- `src/research/lane_d_producer_optimization/**`
- `shaders/research/lane_d_producer_optimization/**`
- `scripts/research/lane_d_producer_optimization/**`
- `research/lanes/lane-d-producer-optimization/**`

Shared roots such as `CMakeLists.txt`, `mise.toml`, `src/*.cpp`,
`shaders/*.glsl`, and `research/protocol.md` are read-mostly from lane
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

1. State a falsifiable question and decision gate before optimizing.
2. Preserve semantic parity before comparing performance.
3. Include all costs required by the candidate architecture. Lookup-only wins
   do not promote an architecture if producer, allocation, update,
   invalidation, scheduling, or maintenance costs erase the win.
4. Do not manufacture favorable ordering in synthetic producers. Synthetic
   distributions are allowed only for bring-up or isolated controls and must be
   labeled as such.
5. Prefer the simplest experiment that can reject a hypothesis.
6. Do not infer a cache/memory mechanism from timestamps alone. Use profiling
   evidence before making microarchitectural claims.
7. Results on one GPU are exploratory evidence, not a universal claim.

## Result lifecycle

For every experiment:

1. Create/update `research/lanes/<lane>/experiments/NNN-name.md` with question,
   hypothesis, protocol, correctness gate, and decision gate.
2. Run through `mise run research:record` when practical. Raw artifacts go to
   `out/research/<lane>/<experiment>/<timestamp>/` and stay out of Git.
3. Record accepted, rejected, or invalidated evidence in
   `research/lanes/<lane>/results/NNN-name.md`.
4. Add one entry to that lane's `results/index.json`.
5. Update the lane README only when the lane-level conclusion/next decision gate
   changes.

Implementation behavior belongs in source/doc comments/tests. Research docs
record rationale, protocols, evidence, limitations, and decisions that cannot
be reconstructed from code alone.
