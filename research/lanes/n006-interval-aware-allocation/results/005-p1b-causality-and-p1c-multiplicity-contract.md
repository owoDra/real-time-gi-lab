# N006 P1b — causality confirmed, work-unit change recommended

Issue #42. Status: **P1b complete**. This is a frozen two-case causal-chain diagnostic, not a formal predictive-ranking result.

## User GPU evidence

Uploaded `n006-p1b-influence-summary.json`: clean `research-n006-interval-aware-allocation` HEAD `25df5716c297b2bf5a8d7f47e9e9b2777ce9d271` on AMD Radeon 8060S (RADV STRIX_HALO); `status=complete`, `failures=[]`, no new reference generation, one-frame warmup baseline image RMS 0 versus previous P1a, and both instrumented intervention images exactly equal their previous P1a outputs (`new_image_vs_p1a_rgb_rms=0`).

| Frozen tile/cascade | Base 8-ray integer sum | Extra 4-ray integer sum | Owner output rounded mean16 | Shared (probe xyz, cascade) output count | Spatial storage sum16 | Previous final image effect |
| --- | ---: | ---: | --- | ---: | --- | --- |
| 22890 / cascade 0 | 12 | 3 | 2 -> 1 | 8 | 16 -> 15 | 0 pixels changed |
| 22890 / cascade 3 | 4 | 1 | 1 -> 0 | 151 | 151 -> 150 | 468 pixels changed, all beneficial |

- Both interventions had actual nonzero integer radiance contributions and a lower rounded per-owner output. Both led to an observed one-unit decrease in a **real GPU spatial storage slot**, with sum/count matching CPU reconstruction.
- Both include some extra rays with zero radiance (cascade 0: 1/4; cascade 3: 3/4).
- This **rules out** “all added rays are zero” and “all interventions were rounded away before reaching storage” for these two cases.
- The unchanged final image in cascade 0 **does not prove** zero screen consumers yet. The most likely mechanism is an unreferenced spatial probe key; however pixel-level lookup reachability was *not read back*. Render-space numerical masking is another possibility to measure before treating it as established.
- The 151-output shared cascade-3 probe is heavily diluted: its storage fractional mean goes `1 -> 0.99337748` integer-domain units, which yields only a tiny final-image change. It is a good example of how `tile_id` fails to identify final pixel influence: the selected tile pixel is unchanged.

## Critical new source-audit observation

The original N001/A001 **base producer** emits eight *fixed octant direction rays for each visible owner × cascade*, but both the origin (probe cell center), interval and ray direction depend only on `(probe_xyz, cascade, ray_index)`. This has been checked against:
- `shaders/research/lane_n_end_to_end_renderer/imported/lane_a_split_rc/producer.comp.glsl`;
- `.../imported/integration/i001_work_to_rays.comp.glsl`;
- `.../imported/integration/i001_hwrt.comp.glsl`;
- `.../n001_physical_radiance.comp.glsl`;
- `.../imported/integration/i001_storage_update.comp.glsl` and `.../n001_composite.comp.glsl`.

Neither HWRT traversal nor light response consults `tile_id` or `surface_id`; both consume constructed rays/hits. Therefore every visible owner belonging to the **same probe/cascade** nominally triggers the same eight base rays with the same geometric/radiometric inputs, under a fixed frame geometry. P1b empirically found **8** owner outputs for the cascade-0 key and **151** for cascade-3, at the same tile: potentially 64 and 1,208 repeated base ray invocations for those two specific keys respectively. These are per-key counts, **not** whole-scene counts.

This is a stronger optimization hypothesis than immediately trying a pre-trace predictor to add four more rays at arbitrary `owner × cascade` sites:

1. The natural **storage unit is probe × cascade**, not screen owner × cascade. Output replication and spatial lookup obscure causal attribution.
2. Duplicate ray inputs may be **pure repeated work**, removable without spending additional ray budget or changing the final single-frame RC representation, provided exact same-key/ray-input and roundoff semantics are validated.
3. Claiming speedup from deduplicating these ray inputs would be **premature**: building/scanning unique GPU keys, writing one output per key, restoring merge/storage identity, dispatch overhead and memory locality may outweigh saved traversal; earlier grouping/scheduling research warned about GPU ordering overhead. No change to accepted N001/N005 yet.

## Next prospective gate — one-frame multiplicity survey, not a scheduler

A new **N006-only** `probe_multiplicity_audit` readback enumerates unique `(probe xyz, cascade)` keys across existing base work per cascade; checks source ray origin, interval and octant direction inputs are exactly identical for all owners in a key; reports unique keys, shared keys, maximum multiplicity and `(owners - unique keys) * 8` exact repeated base ray *inputs*. It does not modify GPU work.

Frozen case: stable-topology deformation, **one source frame plus one target current frame**, zero extra rays, no reference generation; required target AMD Radeon 8060S. Collect all four cascades and raw current evidence without excluding low- or high-multiplicity keys. No post-hoc case selection. Gate:
- If same-key input identity check fails, **STOP** canonicalized-work hypothesis and investigate aliases/pipeline semantics.
- If identity holds but repeated work is small, preserve negative counts and return to other P1 mechanisms.
- If identity holds and repetition is substantial, next design a **costed canonical-probe tracing vs. current** microexperiment (do not promise GI improvement). A shader rewrite and correct reference/storage validation would require a separately frozen P1d, not a retroactive reinterpretation of P1a.

## User GPU command

```bash
git pull --ff-only
mise run build
mise exec -- python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1c_multiplicity.py
```

Upload newly produced `n006-p1c-multiplicity-summary.json`. Unlike P1a, this needs no 512-spp reference and only a single target current frame. No GPU profile tweaks, no GitHub Actions. P1 predictive-ranking / P2 scheduler decision is **still not GO**.
