# N006 P1f: whole-frame owner-output equivalence (pre-canonicalization correctness gate)

Issue #42. **Prospectively frozen, before running P1f GPU diagnostics.** P1a–P1e remain preserved.

## Causal question

P1c proved repeated **ray INPUTS** are bit-identical for each shared `(probe_x,probe_y,probe_z,cascade,ray_index)`. P1e confirmed GPU unique-key hashing at 20–27 µs but whole-GI time comparisons were confounded by primary visibility/cold geometry transitions. For a single canonical probe/cascade sample to replace all owner outputs with no image change, we must separately prove that all duplicate owners share the **same final merged integer radiance sum and sample count** (not merely same directions).

## Frozen GPU diagnostic

- Device AMD Radeon 8060S RADV, workload `deforming-control`, `LaneEFinalHwrt`, current mode, one source warmup, one target frame, no extra rays, no reference generation.
- N006-only readback after a normal completed frame of the existing `work`, `accum` and spatial `storage_slots`. There is NO additional shader pass and NO changed renderer work.
- Group all 16,688 owner×cascade output IDs by the exact 4-component probe key. For each key compare **integer merged radiance sums, sample counts and shader-equivalent rounded per-owner sample mean** across all owners. Record divergent keys/owners, zero-count outputs and storage aggregation mismatches per cascade.
- For every key, reconstruct `storage_slot.data.y` as sum of per-owner rounded means, `storage_slot.data.z` as the number of valid owners, and compare GPU slot token/key/frame tag. Reject missing or duplicate slots, stale frame tags, invalid identities, count/sum overflow.
- Expected baseline cardinalities fixed from P1c: visible 4,172; outputs 16,688; work 133,504; unique keys **[1853,815,284,77]**; duplicate outputs **[2319,3357,3888,4095]**. No case cherry-picking.
- Save a separate `n006-p1f-owner-equivalence.json`, append compact `n006-owner-equivalence.json` diagnostic raw file and existing standard candidate evidence/PFM, never overwriting accepted artifacts.

## Gate

- **GO to designing a distinct canonical-probe producer:** zero divergent merged sum/count and rounded means over ALL shared keys, zero storage mismatches, complete rendering correctness and P1c cardinalities. This verifies one frozen source/target workload only, not all scene/motion classes.
- **REFINE:** merged outputs differ despite identical input rays; quantify divergence, inspect traversal/device nondeterminism and shared storage semantics before proposing dedup.
- **INVALID:** any wrong source count, stale/missing slots, GPU storage mismatch, runtime error or scenario/branch/device deviation.
- Even with GO, dedup is **unimplemented**. Later P1g must build a true compact canonical ray producer with exactly 24,232 ray inputs on this workload and bit-exact rendered output, and measure whole GI **plus ray-dependent subtotal**, making cold target frames distinct from steady-state. Avoid per-frame global sort.

No GitHub Actions, no N004/N005 edits, no retroactive modification to P1a–P1e.
