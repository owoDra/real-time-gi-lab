# N006 P0 source-level feasibility checkpoint

Issue: #42. Status: **source-audit GO for owner × cascade intervention; baseline GPU smoke PASS. Novel per-cascade intervention PENDING.**  
No renderer, shader, N004/N005 raw result, or frozen contract changed in this checkpoint.

## What we checked (actual accepted source)

- `imported/lane_a_split_rc/producer.comp.glsl`: each visible owner reserves `counts.w` distinct output IDs (one per cascade), and emits `limits.x` rays per cascade. The output ID is computed independently from the ray index.
- `imported/lane_a_split_rc/stream_schema.hpp`: `SplitRcWorkItemV1` stores probe xyz, cascade, ray index, output, interval min/max and direction. There is **no independent angular-interval storage identity**, only a ray/work-item direction within the cascade's distance interval.
- `n005_extra_producer.comp.glsl`: extra work is appended after the frozen producer; it already clones one representative `ray_index == 0` item per owner/cascade and assigns deterministic extra direction/ray-index values. Currently this is **owner-selected, every cascade**, not independent cascade selection.
- `imported/lane_a_split_rc/merge.comp.glsl`: the accum-buffer value and *actual sample count* are atomically accumulated by `output_id`; the merged result is not divided by a single global rays-per-cascade constant.
- `imported/integration/i001_storage_update.comp.glsl`: only `ray_index == 0` items reserve/commit one **mean-per-output** sample into the spatial `(probe_x,y,z,cascade)` slot; extra rays with new nonzero indices do not add duplicate storage updates.
- `imported/integration/i001_storage_resolve.comp.glsl` and `n001_composite.comp.glsl`: stored values are normalized by their actual accumulator count and the composite looks up four cascade-specific probe values. There is no fixed *equal extra-ray count in all cascades* assumption in these shown equations.

## Narrow conclusion

An **owner × cascade count-varying extra suffix** looks implementable without a new persistent confidence structure or representation rewrite. It would keep the frozen base output IDs and ray-index-zero storage reservation intact. *This is source-level feasibility only.* It does not validate execution under novel ray placement or prove unbiased angular quadrature: the extra directions use a hashed spherical scheme while base uses eight octants, so differing per-cascade counts can alter finite-sample noise/error. Verify observed causal marginal gain, image correctness and sample-count identity on GPU before relying on the new scheduling unit.

The smallest **demonstrably represented** update identity is `(probe xyz, cascade)` with `interval_min/max` carried in its work items. Scheduling finer *angular intervals* as independently persistent entities remains **unproven and out of scope for the initial intervention**.


## P0 baseline GPU smoke — accepted device/correctness check

User-run evidence received 2026-10-08 (separate, non-formal device verification; no independent quality reference generated).

- Protocol: `n005-p2-candidate-evidence-v1`, `mode=current`, `scenario=static`; source warmup = 1, target frames = 1, zero extra-ray budget.
- Clean working branch `research-n006-interval-aware-allocation` at commit `7e4d3abe6f9b17e169c164391bbc19092c507287`; N005 accepted predecessor `3a098584ec76bcaa06e5166793b2946cd1f7eb25`.
- GPU: AMD Radeon 8060S Graphics (RADV STRIX_HALO), Mesa 26.1.2, RADV.
- `source_correct=true`, `frame_correct=true`; strict/tie/substantive traversal mismatches all 0.
- Visible owners = 4,167; base work items = 133,344; outputs = 16,668; zero extra ray, overflow, and storage failures.
- One-frame descriptive GPU time = **818.354884 us complete GI**, **846.448262 us renderer**; do not treat a one-shot smoke as timing evidence.
- No independent path-traced reference was generated (`reference_generation=skipped`), so **no quality advantage or P1 ranking signal is established**.

Decision: local baseline GPU environment and N005 correctness checks **PASS**. The executable owner × cascade experimental intervention still requires dedicated implementation and GPU correctness checks. The next user GPU action should be on **new N006 pilot code**, not a repetition of this smoke.

## GPU data needed next

1. Environment smoke: run the accepted N005 `current` renderer **unchanged** under the N006 branch. This confirms local binary/assets, current target GPU, zero extra work, traversal/storage integrity and confirms one clean evidence path. **Not a measurement of N006 improvement.**
2. After smoke and a prospectively frozen P1 contract: generate a new N006-only, bounded per-cascade intervention and compare final image to shared canonical reference. The user should only have to execute the supplied runner and share the resulting compact summary/artifacts; analysis is the assistant's responsibility.

### Local next commands

```sh
git fetch origin research-n006-interval-aware-allocation
git switch research-n006-interval-aware-allocation
git pull --ff-only
mise run build
mise exec -- python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p0_smoke.py
```

If the smoke reports missing Sponza, execute `mise run assets` then rerun just the final command. Failed attempts remain on disk; do not delete or cherry-pick them. The compact result is `out/research/n006-interval-aware-allocation/p0-smoke/<timestamp>/n006-p0-smoke-summary.json`; include its contents and any error log in the next handoff.

## Gate decision

**P0 source granularity: GO (owner × cascade) conditional on hardware verification.**  
**P1 experimental contract/counterfactual code: NOT yet implemented or authorized by this smoke.**  
Do not claim ray-allocation superiority based on this smoke. No GitHub Actions.
