# N006 P1l-B1c — compiler-cost audit and packed split-direction proxy (FROZEN BEFORE GPU)

Issue #42. Date: 2026-10-11. **Prospective hypothesis only, not an accepted optimization.** This protocol was committed before B1c shader implementation or any B1c GPU result. Accepted baseline remains N003 original software-primary; rejected B1a must never be used as the comparison baseline.

## Existing evidence and falsifiable question

- B1a had 0/5 primary stage wins and 4/5 full-renderer regressions in the frozen 15-process/180-pair study (result 023). Do not rerun its failed candidate.
- B1b showed 5/5 fewer primary node pops (2.23–5.91%) and fewer triangle tests (6.52–31.42%), but no candidate GPU timing (result 024). The exact slowdown mechanism is **unknown**.
- Baseline CPU `GpuSoftwareBvhData::build_node` partitions triangles on the largest centroid extent into left/right children. GPU `GpuBvhNode` is exactly 48 bytes, internal nodes use `data.x/y` for children and leave `data.z/w` zero. B1a's child-center ordering reads *both child BvhNode records at each internal traversal step*.
- Test whether a **single precomputed child-center separation axis and orientation**, stored in an existing unused 32-bit internal-node field, can approximate useful front-to-back ordering without any runtime child-node SSBO reads or persistent buffer growth. The proxy ignores ray origin and components of separation off the chosen axis: it is not exact AABB entry or B1a's ray-projected full-vector order, and pruning might disappear.

## Offline audit gate (before interpreting speed)

- Compare byte lengths, SHA-256, SPIR-V instruction-word counts and opcode-family frequencies of built original N003, rejected B1a and new B1c shaders; record compiler path/version and CMake build flags from the **real configured build**. Plain `OpLoad` counts include private/local memory and cannot be interpreted as physical GPU SSBO transactions.
- Record N003/B1a source-level child-buffer access difference; distinguish static instructions from executed instructions, divergence, VGPR/SGPR, occupancy and memory latency (all **unmeasured** without hardware counters).
- Audit output must carry source hashes and GPU shader binary hashes, flag build/compiler differences, and never treat generated SPIR-V lengths as GPU performance.

## Candidate constraints

- **N006-only**: untouched historical N003/E003 shader source, original CPU BVH algorithm, N004/N005, CI. New shader opt-in via separate B1c flag and own shader artifact. No PR.
- For internal node only: compute child bounds-center delta at BVH GPU-node packing time; choose coordinate of largest absolute delta (ties X > Y > Z), and store axis plus center-order direction in existing `data.z`. For leaves retain original `data.z` primitive-begin index. The packed field must be refreshed after **each** source/target BVH rebuild, including rigid translation and deforming; no new GPU buffer or second tree copy. No global per-ray sorting.
- Candidate shader tests sign of ray direction along packed axis, compares near/far child by precomputed orientation, and pushes far then near on the same 128-entry stack. Keep AABB/triangle hit, tie-breaking and overflow math **byte identical** to accepted original. A missing/invalid metadata encoding is a hard correctness error in offline tests, not an alternate algorithm.
- Record per-refresh CPU metadata packing elapsed time, number of packed internal nodes, and unchanged persistent node capacity; precompute CPU work is **not free** even though the GPU node footprint stays 48B. GPU-only paired timestamps do not include CPU packing; report CPU packing separately and disallow calling GPU-only gains a net CPU+GPU speedup.

## GPU preflight → matched comparison (gates fixed before measurement)

- Same five frozen Lane-E-final SOFTWARE Sponza scenarios and backend-specific accepted PFM SHA, same target GPU, same scene SHA, 32 source+8 stable target warmups, same `--canonical-lean-hash`, zero extra rays, fixed 320×180.
- Preflight: **5 independent processes × 2 frames** `01` (original N003, B1c packed-proxy); strict all-frames accepted exact PFM hash, every GPU primary-hit byte identical to original first measured frame, N004 CPU per-ray oracle on candidate frame 1, owner/producer/secondary/storage and stage closure, no overflow or unexpected maintenance. Mandatory light-motion **and moving-rigid** included. Time no candidate acceptance in preflight.
- Only if 5/5 preflight pass: 5 scenes ×3 independent processes ×24 frames of `011001100110011001100110` each, balanced 18 AB/18 BA adjacent pairs per scene; same exact-output checks on every frame; one CPU hit oracle per process. Hard 600s/process with preserved fail-closed artifacts. Source/target metadata packing refreshed at every actual geometry rebuild; verify raw frames derive from a clean branch HEAD.
- Performance primary gate: paired median primary GPU gain **≥5%**, ≥24/36 paired wins and ≥2/3 negative per-process median differences in at least **3 of 5 scenes**. Complete-renderer paired median regression **≤+3% in each scene**. Include all independent negative control stages and separately reported CPU packing / incremental update cost. **Only exploratory acceptance on this GPU**, never claim HWRT parity / hardware independence.
- If any correctness gate fails or no primary performance win: REJECT B1c; do **not** add more primary heuristic variants without a new measured causal justification. Shift to independent E003 quantized secondary child AABB work (B0 ~25.5–26.3 per ray), keeping N006 predictive allocator P1/P2 separately gated.

## Evidence status at protocol freeze

**B1c GPU run NOT PERFORMED, SPIR-V audit NOT YET MEASURED**. Result 024 is last accepted GPU evidence. After implementation, a single verified local command should build, run unit checks, write SPIR-V audit, run full preflight and **only on preflight success** perform the frozen balanced experiment. Never override a failed correctness check to proceed.
