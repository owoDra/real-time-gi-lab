# N006 P1j-B — direct compact-work consumption (zero copyback)

Issue #42. **Freeze before P1j-B GPU measurements.** The P1j-A completed user GPU campaign passed all ten Lane-E-final HWRT/software cases with byte-identical PFM and reduced added N006 scratch 8,421,464 → **4,489,304 B** (46.69%). See accepted `results/016-p1j-a-lean-hash-cross-backend-pass.md`.

## Objective and boundaries

Remove the GPU pass which copies `state_->canonical_work` back to `impl.work` after compaction, **without touching accepted N001/N004/N005 shader semantics or old N006 current / P1g / P1h / P1i paths**.

- New opt-in flag `--canonical-zero-copy` requires both `--canonical-matrix-case` and `--canonical-lean-hash`. The original main work buffer remains the input to the accepted owner-local producer and hash-indexer. One temporary compact work stream is still generated in GPU scratch.
- After the unique key hash and `canonical_compact`, **do NOT dispatch `canonical_copy`**. The canonical apply/finalize still updates actual GPU ray/output/indirect counts and downstream buffers.
- Instantiate N006-only alternative compute stages with descriptors **pointing directly at `canonical_work`** for: work→ray conversion, integer radiance, storage update (reserve+accumulate), owner multiplicity restoration, storage resolve. Merge (which consumes contribution/accum and no work descriptor) and HWRT/software traversal remain shared. Renderer current frames continue to bind and process `impl.work`, unchanged.
- Host-side N006 per-frame compact-work correctness validation must read from `canonical_work` when zero-copy active; never check an obsolete `impl.work` prefix. N004 traversal diagnostics consume actual generated rays/hits and remain enabled.
- Add explicit `copyback_executed=false` to candidate GPU evidence; default P1g/P1i legacy candidate `copyback_executed=true`. Retain full ray/owner/hash/overflow/storage/bitwise-image correctness checks; no inferred gain from “zero copy” if images mismatch.

## Frozen first pilot

Exactly the same **10 P1i/P1j-A independent processes**, five scenarios (`static`, `camera-motion`, `light-motion`, `moving-rigid`, `deforming-control`) and two `LaneEFinalHwrt/Software` backends. Each runs 32 source warmups, then current original + direct-compact canonical motion=1 target, with original/canonical HDR PFM SHA equality **required**. No ray-traced reference, no extra rays, no silent fallback; all 10 original and candidate raw GPU frame evidence/logs retained. Require proper case-specific owner/probe count, same number of compact ray work items, original owner-weight reconstruction, zero hash/weight/storage/hit failures. Fail fast on first incorrect case and preserve logs.

Measure descriptive P1j-B canonical-build stage (hash/compaction/apply/finalize, **copyback absent**), scratch allocation 4,489,304 B, collision counters, per-case complete-GI timing, but **do not claim speedup**: sequential target-state frames differ in cold dynamic maintenance. The compact staging scratch remains necessary because the accepted old producer still constructs the full work list before compaction. Therefore P1j-B aims to remove a GPU copy *dispatch and barrier*, **not another ~4 MiB memory allocation**.

## Subsequent gates

- 10/10 parity PASS → separately freeze matched-state 3-process alternating current/compact timing on **both HWRT and software**, checking disjoint timestamp closure and end-to-end GI vs affected downstream GPU work.
- Actual further scratch reduction requires a later distinct direct canonical probe producer: avoid the original full owner-output work list entirely, rather than falsely calling this zero-copy experiment zero-allocation.
- Remaining portability gaps: hardware truly without HWRT extensions, high topology churn, multi-GPU, worst-case 128 hash probes, memory peak; no production adoption yet. Predictive ray allocator P1/P2 remains gated.

No GitHub Actions, no old source behavior edits.
