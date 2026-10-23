# M001 DDGI prospective static quality budget ladder

2026-10-23, after009 dynamic reset controls PASS and before any DDGI quality score or candidate acquisition. Original001/002 remain unchanged. All six original references at16384spp are admitted; original PT/fixed-RC results remain fixed. Static008 and within-context dynamic reset009 qualify the stated finite-depth/reset implementation, not its HDR accuracy. Control indirect images were used only for semantic/byte identities; no indirect quality scores/error maps were computed and no budget is selected from them.

## Fixed estimator, source and history

Use the private dynamic host binary from036, its unchanged retained static entry (no target-state argument), exact029 TraceProbes/GatherPixels, unchanged pinned RTXGI official kernels/SDK archive, BF-P physical inputs and original seed305419896. One fresh process and one static image per named scene/depth/budget. Full atlas initialization, no reused history; B2 one finite stage, B8 seven. Gamma1,hysteresis0,normal=view bias.01×minimum grid spacing,distance exponent50,brightness/irradiance thresholds1e6; classification/relocation/variability off. Same full F32 resource formats, bilinear clamp-to-edge sampler, full previous/current capture, tile4096, geometry-only AABB origin/spacing rule as008/009. No new scene recipe, mask, albedo/HDR clamp, sample seed or estimator setting selected from candidate outcomes.

The supported changed-state policy is within-context `reset-all`: frame upload, actual geometry/BLAS/TLAS update where changed, both atlases cleared, finite stages, gather. This is actual qualified reset behavior, not temporal accumulation or scrolling. The static quality cohort remains distinct from later dynamic heldout quality and calibrated update costs.

## Frozen budgets and order

Budget ladder is the same for every scene and depth, chosen from bounded grid/ray capacity and acquisition cost, without observed DDGI quality scores:

| Rung | Cubic grid | Rays/probe | Total rays/stage |4096ray tiles/stage|
| --- | ---: | ---: | ---: | ---: |
| q0 |8³|128|65,536|16|
| q1 |16³|256|1,048,576|256|
| q2 |24³|512|7,077,888|1,728|

These are DDGI estimator budgets, not PT spp equivalents. Official128/256/512 blending kernels must match the rung exactly. Grid origin is AABB midpoint; spacing on each axis is `(extent+2*(extent/(side−1)))/(side−1)`, evaluated in double then float as the qualified host. Ray rotation remains fixed throughout finite stages, independently initialized with the same registered seed on each fresh image.

Target order: H01/T_B2, H01/T_B8, H02/T_B2, H02/T_B8, H03/T_B2, H03/T_B8. For each target run q0, then only following an independently audited valid QUALITY_FAIL advance to q1/q2. Stop at the first PASS. Exhausted q2 losses are final QUALITY_FAIL for this registered ladder. Do not skip, resample, retune settings, run past a PASS, overwrite an existing work root or silently substitute the grid4 semantic controls. At most18new named quality processes; no automatic GPU queue. Prepare/review one exact CPU/provenance plan, execute that single named GPU process, audit terminal bytes before choosing the next allowed unit.

## Required CPU admission and GPU evidence

Before any GPU quality unit, implement/test a dedicated runner/auditor and CPU rung-selection/stop/failure/refusal tests; freeze them in a commit. Verify original full physical state, all eligible reference payloads/provenance, original physical sampler proof, all pins/private build/dependencies, and all required008/009 controls. Validate each named native grid/ray/depth through its actual CPU-only CLI. Require at least16GiB free disk. The native original8GiB owned cap and independently balanced allocation ledger still apply, including all atlas pairs, AS, staging, output and buffers. Estimated bytes never replace actual allocation requirements/true peak.

GPU lifecycle/guards remain those qualified by008/009: every probe ray covered once by complete disjoint tiles,250ms bounded fence/unit guard,2ms cooperative gap,180s external whole-process guard covering inherited synchronous setup. All native captures/partials and proof tars remain under repository/out, never Git. Native build/compile/driver identities and exact source/reference state must match the prepared plan. Operational/incomplete/state/reference mismatch stops the series for investigation; it is not a valid QUALITY_FAIL permitting budget escalation. No automatic retries or threshold/guard relaxation. Preserve failed bytes and prospectively identify any necessary repair.

Independent CPU audit must rehash complete raw inventory/archive/state/reference identities, prove every expected native GPU unit completed in order and within guards, compare all captured previous arrays to preceding current arrays/initial0, require complete finite images/atlases, check PFM/raw/composite identities and replay every allocation. Use256/512official SPIR-V identities where selected; do not transfer only the128rays control's runtime assertion without checking the actual new case. Larger-budget execution is experimental until its own terminal audit.

Score every pixel/component against the original admitted16384spp four-seed f64 mean for the exact scene/finite transport, retaining full error maps, source/reference fingerprints and all diagnostics. Unchanged gates: total NRMSE≤.05,indirect NRMSE≤.10,absolute indirect signed energy bias≤.05. No exclusions, threshold changes or replacement references. Report direct/support/leak/active-p99 diagnostics even if failing; no low-signal zero-p99 convergence inference. Classify PASS or QUALITY_FAIL only after all physical/reference/native/finite/memory checks. Retain all lower-rung failures and exact selected first PASS/exhausted loss.

## Timing and broader acceptance

All native timestamps, setup/update, CPU wall, cooperative gaps and proof readbacks here are diagnostic/uncalibrated. There is no accepted DDGI speed result from this screen. Only a quality-matched pair can advance to a separately committed complete timing family with actual-boundary multiplicity/order/process counts, precision calibration, practical ratio1.20 and full recurring/startup/update/memory costs. Proof readbacks and actual product-boundary costs must be explicitly separated in that future registration; do not silently time a different lifecycle or omit setup/update costs.

Regardless of static results, broader new dynamic/Sponza/representative-device strata, explicit temporal limitations, fair family wins/losses and original unresolved historical Sponza direct error remain Lane M gates. Completing this ladder does not itself complete Lane M or promote an architecture.
