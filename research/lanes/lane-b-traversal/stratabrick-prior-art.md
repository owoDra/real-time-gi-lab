# StrataBrick prior-art notes for Lane B

These notes are **hypothesis input only**. They do not establish that StrataBrick
wins B001 or the final Lane B comparison.

Sources inspected in `owo-x-project/phos`:

- branch `test/stratabrick`:
  - `docs/tech/13_ray_query_api.md`
  - `docs/tech/14_stratabrick_spec_lock.md`
  - `docs/reports/stratabrick_eval_2026-02-23_fix.md`
  - `docs/reports/stratabrick_rayvalidatevis_2026-02-23_fix2.md`
  - `docs/validation/stratabrick_validation.md`
  - `src/renderer/mod.rs`
  - `shaders/ray_query_debug.wgsl`
- branch `test/stratabrick-3dsrc`:
  - `docs/tech/14_stratabrick_spec_lock.md`
  - `docs/tech/16_gi_radiance_cascades_world_probes.md`
  - `src/renderer/mod.rs`
  - `shaders/ray_query_debug.wgsl`
  - `shaders/gi/gi_rc_gather.wgsl`

## Reusable hypotheses

1. Historical StrataBrick was not merely a lookup structure. It included world
   membership/key generation, sorted segment ranges, per-segment instance BVHs,
   a static mesh BVH, occupancy metadata, dirty classification, rebuild/refit,
   and ray traversal. Lane B must count every required part.
2. Topology changes caused rebuilds while AABB-only changes on dynamic segments
   caused refits. Recorded dynamic controls could reduce rebuilds to zero while
   many active segments still required refit, so dynamic maintenance is not free.
3. Grid DDA behaved reasonably at practical finite GI ranges in the prior PoC,
   while `t_max = Infinity` produced thousands of empty-cell steps per ray and
   very large query time. B001 therefore uses 50 m and 200 m controls.
4. Occupancy removed binary-search calls but did not create a decisive 200 m win
   in the old PoC. Occupancy is therefore not assumed to be the winning mechanism.
5. RayValidate work exposed sensitivity to origin bias, face policy and reference
   semantics. B001 fixes one explicit shared Hit contract before timing.
6. `test/stratabrick-3dsrc` called `traceRay` directly from RC gather, which
   supports GI-like control rays for bring-up but is not representative evidence
   for this repository until Lane A publishes its producer stream.

## B001 implication

The raw sparse-grid/DDA control is intentionally simpler than historical
StrataBrick. It tests whether finite-range spatial stepping is promising at all.
Poor raw-grid regimes do **not** directly reject the historical hierarchical
candidate because segment/BVH pruning is a distinct mechanism; they do reject
promoting raw DDA alone as the candidate.
