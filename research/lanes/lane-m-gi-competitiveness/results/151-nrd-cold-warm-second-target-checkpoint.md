# NRD026 cold/warm HDR: second target checkpoint

**H01_B8_LADDER_EXHAUSTED_QUALITY_FAIL_FOUR_TARGETS_PENDING.** H01/B2 and H01/B8 are terminal; four targets remain.026 and Lane M remain active and incomplete. No accepted timing, memory superiority or architecture promotion.

[Registration026](../experiments/026-nrd-cold-and-64-frame-static-hdr-quality.md), [CPU preparation146](146-nrd-cold-warm-hdr-cpu-preparation.json), [first target148](148-nrd-cold-warm-first-target-checkpoint.md), [full H01/B8 outcome150](150-nrd-cold-warm-h01-b8-hdr-outcome.json), [verification152](152-nrd-cold-warm-second-target-verification.json).

Original registration5753113e, pre-execution stored-history clarification88bb0b19, implementationacb968a1 and CPU readiness4712178d precede these acquisitions. All new plans/native/audits use5bb5691bd2ed4cebb1e9828663ae6c835e4d9b73. The52 actual Python contracts,24 valid/eight rejected native inputs and six admitted references remain the qualified CPU preparation; they are reused without rerun. No source, SDK setting, seed, sampling budget, evidence coverage or threshold changes. The same025 library/pipelines and all other objects are reused without rebuilding.

Each process records64 actual frames, frame0CLEAR and63CONTINUE with the registered distinct seed schedule. All per-frame fields, actual guides, pools, constants, costs and errors are retained without masking or pixel exclusions. The admitted16384spp/four-seed physical reference and all-pixel gates remain total NRMSE<=5%, indirect NRMSE<=10%, absolute indirect signed bias<=5%. Cold is frame0; warm requires every frame48..63 PASS; all64 image scores are retained. No temporal mean substitutes for a failing frame.

| spp/frame | Cold indirect NRMSE | Frame63 indirect NRMSE | Frame63 signed indirect bias | Cold | Warm | Joint |
| ---: | ---: | ---: | ---: | :---: | :---: | :---: |
| 1 | 39.5173% | 36.0798% | -25.4824% | FAIL | FAIL | FAIL |
| 4 | 37.0506% | 32.6017% | -12.7384% | FAIL | FAIL | FAIL |
| 16 | 36.8231% | 32.0693% | -9.5239% | FAIL | FAIL | FAIL |
| 64 | 36.6481% | 32.0503% | -8.8871% | FAIL | FAIL | FAIL |

There are4 new acquisitions/256 frames for H01/B8;026 total8 acquisitions/512 frames. Decisions concern only the disclosed sky-initialized default RELAX_DIFFUSE configuration on known static H01 data, not NRD-family performance generally. Every loss is retained. No additional H01 rung, retuning, retry, new reference sample or post-hoc exclusion.

Every frame passes full primary presence/primitive/depth/canonical/unit-normal, all sample miss/unit/in-lobe/ordered float32 sum/mean, official guide/UNORM/viewZ/static-motion/input-error and RGB composition checks. Original winding-normal diagnostics remain visible; no winding-normal equality claim. Stored history advances1..31 then clamps. All active secondary rays of frames0,1,63 have independent double-precision intersections under unchanged024 distance bounds and zero presence/primitive mismatches. Other61 frames retain/audit every witness, guide and primary record, without claiming independent secondary intersections there. Frame0 raw PT equals the original same-budget/depth/seed capture. H01/B8 has no025 full-field cold control, and none is claimed.

Each actual SDK stream matches025 CPU exports:651 dispatches/481,632 constant bytes and all15 pipeline bytes. Complete30,540-unit journals, frame envelopes and37 owned allocation/free pairs (15 images/13 mapped pipeline buffers plus AS/scratch/staging) reconcile to zero teardown. Full startup/readback/history/pauses are retained; these uncalibrated timestamps and ownership measurements do not establish accepted speed/memory superiority. Driver-private and CPU memory are excluded from owned GPU memory.

Assistant-operated runs use explicit user authorization on Radeon8060S/RADV, with no power/clock/desktop changes. One announced command and independent terminal audit precede every next rung.120CPU/180wall/4GiB process,8GiB aggregate-owned cap,250ms waits,2ms pauses and32GiB free-disk guards apply. Raw data/full errors/compiler receipts remain in repository out/. Default Renderer build/runtime regression NOT_RERUN; validation layers NOT_RUN. No Actions/CI/main promotion. Prior experiments/N001–N010 and accepted bytes remain unchanged.

Next registered target is H02/B2/1spp, followed by H02/B8,H03/B2,H03/B8. Complete the fixed cohort or stop on an operational failure. New heldouts, dynamic/Sponza/multiple GPU classes, complete-boundary calibrated matched-quality comparisons, deployability and novel competitive transport remain required. Lane M remains incomplete; Issue7OPEN.
