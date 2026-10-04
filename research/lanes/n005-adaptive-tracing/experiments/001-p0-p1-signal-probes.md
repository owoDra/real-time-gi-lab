# N005 P0/P1 — reuse, accounting, and signal probes

Issue: #40  
Protocol: `n005-p0-p1-signal-probes-v1`

## Research boundary

P0/P1 does **not** implement adaptive tracing and does not produce formal current-vs-uniform-vs-adaptive evidence. The renderer remains the frozen N004 `LaneEFinalHwrt` path and traces zero extra rays.

N004's classification thresholds and completed result are immutable inputs. P1 reports absolute luminance error, relative luminance error, and the frozen scale-aware affected-pixel label separately; it does not reinterpret N004 blocker labels.

## P0 decisions

### Reuse boundary

Reuse the N004 executable path rather than copying the renderer/reference/playback stack:

- `n004_atlas_main.cpp` remains the playback/reference entry point;
- `n004_runtime.cpp` remains the frozen renderer path;
- N004's aligned multi-bounce reference generation and PFM evidence are reused;
- `n004_scene_factory.py`, `run_n004_weakness_atlas.run_case`, image loading, and N004 config validation are reused by the P1 runner.

N005 uses the same `phos-n004-atlas` playback. An opt-in observation hook inside the existing N004 diagnostic boundary reads already-produced visibility depth/owner buffers only when `PHOS_N005_VISIBILITY_CAPTURE_DIR` is set. Normal N004 runs leave the environment unset, so their diagnostic behavior remains unchanged apart from the dormant environment check.

P1 stores the exact depth/owner snapshots as raw sidecars and derives signal maps offline. This keeps signal math out of the renderer and makes every P1 signal reproducible from retained raw observation data.

### Minimum-invasive signal data

Do not add signal state to traversal, radiance, merge, storage, or resolve. The smallest faithful observation point is the existing visibility result:

- exact tile depth bits;
- exact tile owner IDs.

The N005-only runtime readback occurs after a frame has completed. It cannot change rays, work items, storage updates, or the rendered image. Because the extra host readback can perturb inter-frame host/GPU sequencing, P1 timing is descriptive only and cannot become formal timing evidence.

### Future extra-ray accounting

P2 must preserve the frozen base producer. Extra work is a logically separate append range inserted after the frozen base producer and before ray preparation (`work -> rays`). The base work-item count is snapshotted before the append so base and extra work remain separately accountable.

Per frame, future evidence must distinguish:

- `base_traced_rays`;
- `extra_rays_requested`;
- `extra_rays_traced`;
- `extra_work_items`;
- eligible and selected probe counts/fraction.

Each extra ray must retain `{probe_x, probe_y, probe_z, cascade, source_tile_id, signal_id}` attribution. Uniform and adaptive candidates must compare on equal **actual extra rays traced per frame and case**. Requested budget alone is insufficient if eligibility, overflow, or capacity prevents spending it.

P0 only freezes this accounting contract; it does not add extra-ray buffers or execution.

## P1 signals

Measure these independently:

1. `newly-visible` — current tile becomes owned after being unowned in the previous observed state.
2. `ownership-changed` — a visible tile changes owning surface ID.
3. `temporal-depth-change` — normalized depth change where both previous/current tiles are visible.
4. `visibility-discontinuity` — a **visible current tile** borders an unowned 4-neighbor. Unowned current tiles are not candidates because P2 must be able to map every selected region back to base probe work.
5. `depth-discontinuity` — maximum normalized depth difference to visible 4-neighbors.

The first three are state-change signals. The last two are persistent local confidence signals. Do not combine them in P1.

Storage churn, dynamic-owner AABB proximity, probe age/newly-created state, and sample variance remain deferred. Add one only if this first signal group fails to localize the error regimes or leaves a specific blind spot.

## P1 matrix

Decision regimes reuse N004's exact motion/dynamic schedules:

- camera abrupt reveal;
- camera gradual motion;
- stable-topology deforming;
- topology-changing/high-churn.

Controls:

- static Sponza;
- N004 changing-illumination step case;
- N004 `world-dense` synthetic world-shape case.

`moving-rigid` is excluded from P1 decisions and no new prospective timing calibration is introduced.

## Localization evidence

For every frame and every signal, preserve the three N004 error views separately:

- absolute luminance error;
- relative luminance error using N004's frozen floor;
- N004 scale-aware affected-pixel mask.

Report signal support, affected recall/precision on non-zero support, absolute/relative error mass captured on support, affected-vs-unaffected mean signal, Pearson correlation to absolute/relative error, and descriptive ranked capture at fixed 1/5/10/20% pixel fractions.

The ranked capture grid is descriptive signal triage, not a P2 threshold or ray budget. Binary-signal tie ordering is deterministic by pixel index and must not be interpreted as a formal optimum.

## P1 exit

After local P1 evidence exists:

- reject signals with poor localization or control specificity;
- retain one signal, or a minimal small set only if one signal has a clearly evidenced blind spot;
- then prospectively freeze P2 candidate rule, threshold, equal incremental ray budget, formal/descriptive regimes, timing interpretation, and quality success criteria.

Do not proceed to P2 before that freeze.
