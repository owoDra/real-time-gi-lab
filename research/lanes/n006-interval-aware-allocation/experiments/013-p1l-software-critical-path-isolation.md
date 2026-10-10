# N006 P1l proposal — software traversal and primary-visibility cost isolation

Issue #42 research follow-up, **planning only: NOT yet an executed or accepted GPU experiment**. Source evidence is P1k (`results/018-p1k-three-arm-hwrt-software-gpu-timing.md`). N006 canonical sharing now demonstrates positive post-producer GPU-work effects in both HWRT and software on a fixed deforming workload; further removing compact copyback offered no reliable HWRT net gain.

## Why isolate rather than simply optimize again?

In the P1k direct-compact arm, sample medians (unpaired cross-backend, AMD RADV):

| Stage | HWRT median (µs) | Software median (µs) |
| --- | ---: | ---: |
| Primary visibility | ~611 | ~864 |
| Secondary ray traversal | ~105 | ~313 |
| All affected post-producer GPU work (inclusive canonicalization) | ~203 | ~419 |
| Complete GI GPU | ~928 | ~1454 |

Software ray-traversal still consumes ~3× the sampled HWRT traversal stage. Some time may reflect independent backend acceleration data or query scheduling; the N003 software-primary path is itself distinct from HWRT-primary. **These observations do not isolate the root cause:** process/clock/primary noise is large. Initial question should be *why* software has the remaining gap, not whether to optimize by increasing raw FLOPS or relying on extra GPUs.

## P1l-A — stage attribution, nonintrusive instrumentation (prospective, must freeze code HEAD)

- Keep canonical lean hash and P1j-A copyback **constant** in both backends initially to eliminate zero-copy stage confounding; repeat later with direct only if a stable candidate bottleneck needs it. No new output rays/reference, same Sponza and fixed 5 Lane-E-final scenes.
- Collect 3 independent fresh processes per backend and scene, 32 source + 8 target-state warmup frames, 12 fixed target-state frames/process with GPU timestamps primary (total **30 processes, 360 measured frames**). Preserve raw per-frame images SHA, visible owner/output counts and ray counts, storage/hit/error checks, plus production vs canonical direct-side stage timings as possible. No apparent cold/warm comparison counted.
- Split diagnostics by stage: primary camera ray traversal, direct-light/shadow segment, producer, canonical hash/compact, work-to-rays, software BVH traversal, radiance and storage/resolve. For the first iteration use existing GPU timestamp boundaries; **only add finer-grained boundaries in N006 opt-in** where necessary, without rewriting accepted N001/N004/N005 behavior.
- Report per-backend and scenario median, p10/p90, per-process medians and raw data. Full-GI sums must close. For cross-backend comparisons, label them **separate-process absolute-stage** (not matched A/B unless the implementation truly switches both paths in the same process). Record both one-time geometry update cost and steady-state cost separately; don't drop first-target warmup without logging it.
- Add optional *count-only diagnostic* traversal visits/triangle tests (same output rays) if existing timestamp data indicates a plausible algorithmic reason; run the instrumented shader separately from uninstrumented timing to avoid conflating instrumentation overhead with speed.

## P1l-B — choose at most two focused alternatives, only after A

- Candidate category 1: **software secondary traversal** (BVH hierarchy/coherence/memory access/query grouping). Prior lanes already investigated query ordering/grouping; do not reintroduce global reorder or CPU-side per-frame sort without a new documented rationale and measured crossover.
- Candidate category 2: **software primary/shadow traversal** (N003 software BVH vs HWRT primary), independently of secondary GI rays. Do not credit better primary visibility to canonicalization.
- Choose only if P1l-A identifies a dominant stage and a falsifiable hypothesis. Register independent memory and GPU cost envelopes, bit-identical HDR PFM plus hit/storage equivalence. On failure, retain source and raw GPU data. Backend-specific implementations remain opt-in.
- Measure steady-state GPU gain **including prepasses, BVH maintenance, scratch, and synchronization**, not shader-only “wins”. Track clock/thermal variance and preserve both positive/negative triplets; GPU timestamp is primary, CPU wall diagnostic.
- Ultimate validation still requires actual HWRT-disabled device, topology-changing/high-churn and other scenes/GPU families: software selected on an HWRT-capable GPU is only functional-path evidence, not a capability certification.

## Separate engineering track (not P1l timing result)

A direct unique-probe producer might avoid the original 133,504-owner ray stream and/or the 4MiB compact staging stream. Design separately with owner coverage, integer multiplicity equivalence, frame-scoped hash/storage semantics, capacity fail-closed, **source+canonical image bit-parity across both backends**, and an explicit buffer lifetime/residency accounting. The P1k result alone does not justify shipping a new producer.

**Do not conflate canonical sharing with #42's original predictive marginal-value ray allocator:** P1 / P2 adaptive allocation gates remain independently closed. No GitHub Actions.


## P1l-A1 fixed implementation protocol (frozen before measurements, 2026-10-10)

This first **non-intrusive** diagnostic strictly uses accepted per-stage GPU timestamps; do not imply stage counters can distinguish primary camera work *from shadow traversal* inside a shared shader without further instrumentation.

- Ten fixed HWRT/software × static/camera-motion/light-motion/moving-rigid/deforming-control cases, **3 fresh processes each** = **30 runs**.
- Per process **32 current-mode source warmups**, **8 current-mode target-state warmups**, then **12 consecutive P1j-A lean-hash canonical COPYBACK frames** at `motion_fraction=1`: **360 measured frames**, all equally conditioned and all measured frames have identical canonical ray counts in their case. No newly generated reference; frozen expected image hash/owner count/key cardinality per case is imported from accepted P1j-B `n006-p1j-b-direct-compact-summary.json` and copied as *immutable constants into the P1l-A runner*.
- Important correction from the frozen P1j-B source: **moving-rigid HWRT SHA `b0829e21214de633f80c935ddcfa5ca63204c2c1e353ff5ea1f9fd9b7eb1fe17` differs from Software SHA `d1e43a880cd7a4276b62127b6ae64cf4d1b50ca7922c81589095783fe055a0dd`**. Each P1l-A frame must match its *own* accepted backend-specific SHA. Do not assert cross-backend image equality or silently reconcile these two scenes; investigate in a later cross-backend equivalence audit if important.
- A separate opt-in N006 CLI flag `--p1l-stage-probe` requires `--canonical-lean-hash`, fixed 32 source/8 target warmups and 12 measured frames, `--mode current`, `--skip-reference`, no topology/extra rays, no P1g/P1h/P1i/P1k pattern or zero-copy. All measured frames are true canonical work and use accepted P1j-A copyback, **not** direct P1j-B. Historical runs remain unchanged.
- Per-frame strict evidence: full PFM SHA; visible owners (4167/4231/4167/4213/4172 per scenario); canonical 3008/3220/3008/3104/3029 unique probe/cascade keys; actual rays = unique × 8, outputs=unique, original owner weights = visible ×4, correct cascade key profile, collision count >=0, hash slots=32768, scratch=4489304 B, `copyback_executed=true`, no hash/storage/hit errors, frame tags invalidations valid. Source/target warmup errors or instability are fail-closed, as are any measured dynamic traversal maintenance and >1 µs GPU stage accounting errors.
- Existing `primary_visibility_gpu` measures the complete primary stage, and `composite_gpu` (separate from complete GI time) includes final composite/direct lighting/shadows. `traversal_gpu` is secondary ray traversal. Report each separately plus GPU depth, init, visibility reuse, owner producer, canonical build, ray preparation, radiance, merge, inclusive storage update, nested owner-weight, resolve, invalidation, complete GI, complete renderer, and primary traversal-vs-composite proportions. Distinguish the **measured** stage from an algorithm-specific root cause.
- Report per run and per backend/scenario 36-frame median/p10/p90, all raw frame values, and **3 separate process medians** without dropping outliers. Cross-backend ratios are unpaired descriptive comparisons (processes run separately), no causal claims based on ratios alone. For dynamic cases keep **all eight target warmup maintenance samples**, diagnostic only.
- The runner is fail-fast, keeps all raw stdout/stderr/PFM/evidence and partial results; it performs no active A/B comparison and thus **cannot establish speedup over P1k current** in those other scenarios. Subsequent P1l-A2 candidate choice is frozen only after A1 results, with no retroactive changes to these success gates.
