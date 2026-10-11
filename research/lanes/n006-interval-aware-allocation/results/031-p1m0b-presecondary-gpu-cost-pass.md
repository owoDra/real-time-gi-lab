# N006 P1m0b — same-frame presecondary consumer coverage, 5/5 PASS

Issue #42; reported by user upload `n006-p1m0-consumer-coverage-summary(2).json`, raw SHA256 **`d7774a3e4fee8c9a103a7529979d7303ad865d05878143e4522232b8ef14affd`**, independent of previous P1m0 postframe record [030](./030-p1m0-five-scene-coverage-pass.md). Clean user-executed HEAD `359e6b87fe38919349b994136005251187137b4b`, GPU AMD Radeon 8060S Graphics RADV STRIX_HALO; same Sponza source SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. `protocol_version=n006-p1m0b-pretrace-cost-five-scenes-v1`, `status=complete`, `failures=[]`, `pretrace_cost_gate_status=within_predeclared_limit_5_of_5`, `diagnostic_work_inside_accepted_timing=true`, 32 source + 8 target warmups, one target per scenario. All 60 prospective M1 calibration-only sample keys remain available and identical to M0.

| Scene | Pre-secondary scratch clear+dispatch+barriers C (µs) | Instrumented complete GI G (µs) | C/G | Secondary traversal T (µs) | Pre-registered bound min(.1G,.5T) (µs) |
|---|---:|---:|---:|---:|---:|
| static | 21.280 | 1622.723 | 1.31% | 367.178 | 162.272 |
| camera-motion | 14.387 | 1744.835 | 0.82% | 331.550 | 165.775 |
| light-motion | 14.868 | 1556.517 | 0.96% | 340.928 | 155.652 |
| moving-rigid | 22.683 | 2096.063 | 1.08% | 317.684 | 158.842 |
| deforming-control | 20.439 | 1491.835 | 1.37% | 344.374 | 149.183 |

**All five**: per-slot 32768 uint32 consumer counts BYTE-EQUAL to separately executed postframe M0, all eight stats BYTE-EQUAL, original [030] per-case sorted-key SHA and successful lookup count equal, no invalid hash/launch, expected accepted final renderer PFM SHA/N004 hit checks intact. **131,104 bytes** disjoint scratch (hash counter 131,072 and eight counters 32). The pre-secondary pass is in the correct position *after primary hits and canonical hash/compaction, before secondary ray creation*.

**Decision P1m0b ACCEPT**: prospectively bounded GPU cost and pretrace diagnostic availability proved for the frozen five scenes on the sampled Radeon 8060S (not broader hardware). Pass only proves lookup counting is technically usable as a selection feature. It is NOT proof any matched key can improve signed HDR quality, P1 ranking predicts marginal benefit, P2 ROI, or that keys unused in this frame are useless in a different frame/trajectory. All complete-GI timestamps from this run INCLUDE diagnostic and cannot be construed as original accepted baseline performance. GPU timestamp C excludes CPU overhead/pipeline creation & warmup and is not full allocator overhead.

**Next gate**: P1m1 initial canonical-key +4-ray intervention, strictly one key/cascade at a time from immutable calibration-only strata; check base 8 directions unchanged, four deterministic new ray indices, exact key and owner-weight preservation with per-output integer average; paired no-extra control must be byte-identical to [030] accepted image, and interventions need independent HDR reference for **signed** gain. All negative/zero outcomes retained. Only after pilot may test P1 predictor and sealed holdout. No PR, no Actions, no accepted historical shaders modified.
