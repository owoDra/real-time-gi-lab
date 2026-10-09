# N006 P1g: actual compact canonical probe tracing — frozen pilot

Issue #42. **Prospectively frozen before any P1g GPU result.** Target: AMD Radeon 8060S Graphics (RADV STRIX_HALO), `deforming-control`, `LaneEFinalHwrt`, 32 source warmups, 2 target frames in the **same process**, fixed motion fraction 1.0; initial target current baseline, subsequent target canonical. No independent path-traced reference, no extra rays. Full evidence retained. First target may have dynamic geometry maintenance; **do not compare whole-GI speed as matched timing**. Purpose is correctness and actual ray-work reduction.

## Experimental variant

N006-only `--canonical-probe-pilot` mode, leaving all accepted production/historical N001/N004/N005 and original N006 current path unaffected.

After regular visible owner work is produced:
1. Fresh 524,288-slot GPU token hash scans each eight-ray owner/cascade output block and records **the representative work-block index** for each distinct `(probe xyz,cascade)`. Duplicated keys do not append another representative. Keys are packed exactly as in accepted spatial storage. No GPU global sort, no CPU readback to build the work stream.
2. GPU indirect-count setup; one compact output per unique representative with **eight copied ray-input records**, remapping only `output_id` to the new canonical ID. Preserve probe key, origin, ray direction, interval, ray_index. Keep visible owner count separate.
3. Copy compact work from GPU scratch into the existing renderer work buffer by GPU indirect dispatch; update active `work_items` and `outputs` and rebuild indirect dispatch counts. Existing ray preparation, HWRT traversal, integer radiance, merge and spatial storage/resolve/composite then run on exactly the **compact stream**. Each key updates storage once.
4. All GPU work-list counters, collision/failure/overflow flags and every phase's hardware timestamps are part of P1g evidence. Explicitly count the original owner-local 133,504 base rays, compact 24,232 actual dispatched ray work items, 16,688 original outputs and 3,029 unique keys; zero invalid probes, hash overflow or mapping gaps. Small fixed prototype scratch capacity **8192 canonical outputs** with fail-fast overflow; **not a reusable shipping system**.

## Correctness vs reference current target

- Current and canonical target images must be byte-for-byte identical PFM, same SHA-256.
- Current target expected 4,172 visible owners, 16,688 owner outputs, 133,504 rays; canonical target expected **same 4,172 visible owners**, 3,029 outputs, **24,232 actual rays** and **3,029 GPU storage updates**, with matching image, zero invalid slots/hit mismatch, correct reused spatial probe key count.
- Current and canonical target must see the **same fixed scene/material/light/camera state**. No silent reference regeneration. Any source work identity, GPU error, output image mismatch, hash overflow or invalid cascade invalidates the pilot. Do not accept merely equal RMS as bit-exactness.
- Report separate canonical GPU hash, compaction, copy and counter-update timings and inclusive complete GI, along with memory overhead. **Do not infer speedup from one cold baseline pair**.
- If validation passes, next **P1h** must compare warmed target-state alternating A/B frames across multiple fresh processes, include dynamic movement/topology changes and memory/time budgets; eliminate the temporary copy stage if its overhead dominates.

P1a original predictive-ray-allocation question and N004/N005 benchmarks remain unchanged. No GitHub Actions.
