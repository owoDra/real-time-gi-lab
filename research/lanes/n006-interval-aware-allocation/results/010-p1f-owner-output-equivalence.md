# N006 P1f accepted — duplicate owner output values and GPU slots equivalent

Issue #42. User-supplied `n006-p1f-owner-equivalence-summary.json`, `n006-probe-equivalence.json`, `n006-candidate-evidence.json` on AMD Radeon 8060S (RADV STRIX_HALO), clean `research-n006-interval-aware-allocation` @ `88c40d31776dadcd2175b401510f606080edefaf`.

## Accepted facts

- Status `complete`, non-formal, `results.fully_equivalent=true`; source and target frame correctness true, zero substantive hit mismatches, zero overflow, zero storage failures. One source warmup + one target deforming-control frame; **no extra rays or new independent reference**.
- 4,172 visible owners; 16,688 owner×cascade outputs; eight rays per output, **133,504 base rays**.
- **3,029 unique (probe_xyz,cascade) keys** = 1,853/815/284/77 across cascades, or **24,232 unique ray inputs**, leaving **109,272 exact repeated inputs (81.84923298%)**.
- **All 16,688 owner outputs** were checked. For all keys, integer merged radiance sums and sample counts matched among owners sharing a probe, including rounding to per-owner 16-bit mean; **0 divergent merged keys, 0 divergent owner outputs, 0 divergent rounded means**.
- Spatial GPU storage slots reconstructed exactly from sums of owner rounded means and counts; all cascade storage mismatch counts zero, no zero-count owner output.
- Shared keys per cascade: 1,044/594/256/74.

## Scope and critical interpretation

This is a **strong correctness GO for an isolated prototype** that traces **one fixed eight-ray set per unique probe×cascade** and stores one rounded mean per key in the same frozen workload. It is not a measured faster renderer, not proof of bit-exact behavior for every dynamic/visibility class or other GPU, and not P1 predictive allocator validation.

The pre-existing owner-local output sequence and spatial storage produce the same per-owner quantized mean for every owner of a shared key. The storage composite divides summed owner mean by owner count; storing that common per-probe mean once should be algebraically equivalent for those keys. But a new GPU implementation must actually demonstrate bit-exact PFM output, correct dynamic invalidation/frame tags, no probe loss and zero hash/compaction overflow before any performance claim. The 81.85% number is a **ray-count** theoretical opportunity, not an elapsed-time reduction.

## Next prospective gate

Freeze P1g canonical-probe compact-work **N006-only** experimental path before its first target GPU run. Use GPU hash/representative list, direct 8-ray-per-key compact work, output identity remapped to compact key index, then run existing HWRT + integer radiance + merge + spatial storage/resolve/composite. No CPU readback or global sort for construction, and no mutation of accepted N001/N004/N005/N006 original current path. For this frozen 3,029-key workload, a bounded capacity ≥4,096 keys with explicit overflow hard failure is permissible as a prototype; never silently clip keys. Required checks: generated canonical key count 3,029, compact ray count 24,232, GPU hash zero failures, exact output image SHA versus same-scene existing current-mode frame, correct storage count and ray outputs. Report GPU cost of *all* hash/compact/copy passes and whole-GI timing as descriptive; don't claim performance speedup from one cold A/B pair. N004/N005 historical work unchanged; no GitHub Actions.
