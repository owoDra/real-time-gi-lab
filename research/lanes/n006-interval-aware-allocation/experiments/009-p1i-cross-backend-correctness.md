# N006 P1i — prospective cross-backend canonical correctness matrix

Issue #42. **Protocol frozen before P1i GPU results.** P1h supported a net post-producer GPU-work improvement (18/18 pairs, median −82.577 µs) in the single fixed AMD HWRT/deforming workload, with 36 byte-identical PFM images; complete-GI A/B remains noisy from earlier primary visibility.

## Research question

Does true GPU-native canonical probe×cascade sharing preserve **bitwise image and storage correctness** across the five previously accepted Lane-E-final scenarios on both HWRT and the HWRT-unavailable **software** traversal backend?

## Frozen pilot matrix (10 independent processes)

| Variant | Cases |
| --- | --- |
| `lane-e-final-hwrt` | `static`, `camera-motion`, `light-motion`, `moving-rigid`, `deforming-control` |
| `lane-e-final-software` | `static`, `camera-motion`, `light-motion`, `moving-rigid`, `deforming-control` |

The actual `i001_parse_variant` and `i001_parse_scenario` functions recognize these names, and `lane_e_final_supported_scenario()` supports these five. **High-churn topology changes are NOT in this Lane-E-final supported set**, so don't mislabel them as tested in P1i.

Each of the ten cases:

1. New process, accepted Sponza asset/GPU, 32 source-state warmups, then **two fixed motion=1 target-state frames**: first current baseline, then canonical. No new reference image, no extra rays. Preserve stdout, stderr, both raw HDR PFMs and standard N006 frame evidence independently.
2. Do not hard-code the original deforming pilot counts (4,172 owners, 3,029 keys): read each case's current-mode visible owners, work count, outputs, baseline GPU storage keys. Require base work=owners×4×8, outputs=owners×4. Canonical output count must equal exact GPU-discovered unique keys; canonical rays=unique keys×8; repeated outputs=original outputs−unique keys; restored original owner weight total=original outputs. Zero hash overflow/failures, invalid probe keys, owner-weight/storage/traversal errors.
3. Require original and canonical PFM **byte-for-byte identical**, not only RMS/PSNR. Record both SHA256 digests even on mismatch. Check frame-scoped storage invalidation and no key loss. A failed or overflow case is a negative result (not silently dropped or rerun with tuned capacity).
4. Record canonical GPU build+copy cost, owner restoration nested in storage update, transient scratch bytes and full-GI descriptive times, but DO NOT infer speedup: these are cold sequential targets, not matched paired throughput measurements.
5. Run all ten in fixed row order, retain every failure/raw output, and stop on the first build/renderer/validation failure for diagnosis. Never skip a failing backend or replace it with HWRT without declaring that the matrix is incomplete.

## Gates

- **Correctness PASS in a backend/scenario:** all exact GPU count invariants, valid storage/hits, two PFMs identical. Counts may vary naturally across different scenarios; no brittle P1c cardinality guard beyond semantic invariants.
- **Full P1i PASS:** 10/10 cases valid, including `lane-e-final-software`. This would justify a separately designed **P1j** implementation reducing the temporary 8MiB hash/compaction scratch and avoiding copyback/old owner producer.
- **Partial/REFINE:** any case differs: preserve exact case and source GPU evidence, investigate owner-input equivalence/key limits/storage frame tags before changing general renderer or promising software fallback speedup.
- **Other dynamic classes and devices:** topology changing, sparse/dense/large/vertical stress and non-RADV GPUs require distinct future pre-registered studies. Do not quietly expand this frozen matrix after results.

No changes to accepted N001/N004/N005 renderer logic. No GitHub Actions. P1 original adaptive allocator signal remains unproven and separate.
