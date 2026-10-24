# NRD026 cold/warm HDR: third target checkpoint

**H02_B2_LADDER_EXHAUSTED_QUALITY_FAIL_THREE_TARGETS_PENDING.** H01/B2, H01/B8 and H02/B2 are terminal; three targets remain.026 and Lane M remain active and incomplete. No accepted timing, memory superiority or architecture promotion.

[Registration026](../experiments/026-nrd-cold-and-64-frame-static-hdr-quality.md), [CPU preparation146](146-nrd-cold-warm-hdr-cpu-preparation.json), [previous checkpoint151](151-nrd-cold-warm-second-target-checkpoint.md), [full H02/B2 outcome153](153-nrd-cold-warm-h02-b2-hdr-outcome.json), [verification155](155-nrd-cold-warm-third-target-verification.json).

Registration5753113e, pre-execution stored-history clarification88bb0b19, implementationacb968a1 and CPU readiness4712178d precede these acquisitions. All new plans/native/audits use 9c162baf32646cadbec6010a97dd2ea9db0836fa. Qualified CPU preparation (52 actual Python contracts,24 valid/eight rejected native inputs and six admitted references) is reused without rerun. All025 SDK library/pipeline bytes and other native objects are reused without rebuilding. No source, setting, seed, sampling budget, evidence coverage or threshold changes.

Each process captures64 actual static frames: frame0CLEAR, then63CONTINUE with registered distinct seeds. All sample/primary/guide/pool/constant/RGB fields, full errors and costs remain saved. Original16384spp/four-seed references and inclusive all-pixel HDR gates remain total NRMSE<=5%, indirect NRMSE<=10%, absolute signed indirect bias<=5%. Cold is frame0; warm requires EACH frame48..63 to pass. All64 scores remain; a temporal mean cannot replace failing frames.

| spp/frame | Cold indirect NRMSE | Frame63 indirect NRMSE | Frame63 signed indirect bias | Cold | Warm | Joint |
| ---: | ---: | ---: | ---: | :---: | :---: | :---: |
| 1 | 37.8751% | 32.7737% | -31.1225% | FAIL | FAIL | FAIL |
| 4 | 30.8678% | 25.7800% | -14.7131% | FAIL | FAIL | FAIL |
| 16 | 30.2081% | 25.1610% | -11.3122% | FAIL | FAIL | FAIL |
| 64 | 29.7810% | 25.0410% | -10.1689% | FAIL | FAIL | FAIL |

H02/B2 has 4 new acquisitions/256 frames;026 total 12 acquisitions/768 frames. These results concern the disclosed sky-initialized default RELAX_DIFFUSE role on the known static H02/B2 input, not NRD-family performance generally. Every cold/warm-only or failed result is retained. No additional rung, retry, retuning, new reference sample or pixel exclusion.

All frames pass complete primary presence/primitive/depth/canonical/unit-normal, sample miss/unit/in-lobe/ordered float32 sum/mean, official guide/UNORM/viewZ/static-motion/input-error and RGB composition checks. Winding-normal differences remain visible; no winding-normal equality claim. Stored active history advances1..31 then clamps. ALL active secondary rays of frames0,1,63 have independent double-precision intersections under unchanged024 distance bounds, zero hit-presence/primitive failures. Other61 frames retain/audit every witness/guide/primary record without claiming independent secondary intersections. All frame0 raw PT bytes equal their original same-budget/depth/seed captures. H02/B2 has no025 full-field cold control; none is claimed.

Supplemental CPU bitword verification audits all12 completed cold captures (H01/B2,H01/B8,H02/B2), comparing8,294,400 bytes directly against original little-endian PFM payloads with zero word mismatches. The frozen native auditor uses numeric np.array_equal after f64 PFM decoding; that is weaker than byte equality for signed zero. A signed-zero adversarial control exposes the distinction, and this supplementary uint32 comparison proves the unchanged registered byte gate on actual saved data. No GPU, image/reference sampling, old metric rerun, evidence rewrite or criterion change. Remaining026 target admissions must also supply this direct bitword proof alongside the unchanged native audit. The exact receipt/hash is in153.

Every actual SDK stream agrees with025 CPU exports:651 dispatches/481,632 constant bytes and all15 pipelines. Only selected pipeline9 differs from unmodified023; the other14 remain byte-identical. Full30,540-unit journals, all frame envelopes and37 owned allocation/free pairs (15 images/13 mapped pipeline buffers plus AS/scratch/staging) reconcile with zero teardown. Setup/readback/pauses/history costs are retained; timestamps are uncalibrated diagnostics, not accepted same-quality speed or memory superiority. Driver-private/CPU memory is excluded from owned GPU memory.

Assistant-operated GPU runs are explicitly authorized on Radeon8060S/RADV without power/clock/desktop changes. One announced command and terminal independent audit precede each next selection. Guards remain120CPU/180wall/4GiB process,8GiB aggregate-owned cap,250ms waits,2ms pauses and32GiB free disk. All raw data/full errors/compiler receipts remain in repository out/. Default Renderer build/runtime regression NOT_RERUN; validation layers NOT_RUN. No Actions/CI/main promotion. Prior accepted/failed evidence and N001–N010 remain unchanged.

Next registered case is H02/B8/1spp, followed by H03/B2,H03/B8. Finish the fixed cohort or stop on an operational failure. Novel competitive transport, new heldouts, dynamic/Sponza/multiple GPU classes, deployability and calibrated complete-boundary matched-quality comparisons remain required. Lane M remains incomplete; Issue7OPEN.
