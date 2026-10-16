# N010: bounded cause diagnosis before further full acquisitions

Date: 2026-10-17 JST. Parent checkpoint: `e6dbc33`.
User direction: resume, identify causes broadly and take the shortest valid
route to N010 completion; retain the request to limit interactive load.

## Current facts and boundary

180 actually terminated: both levels FAIL the original <=0.75 feasibility
criterion (ratios 1.0703554221788882 / 1.0599135470235277). This is not a
262144-spp cap failure. 185 actually terminated with all sixteen sizing
boundaries PASS; 186 has not run. No stopped acquisition is restarted.

Post-hoc CPU analysis 191 uses retained, hash-checked original C1 B2/B8
sidecars at 8192/16384/32768. The B8-minus-B2 component accounts for about
97.47/98.28/98.69% of full indirect replicate-centered squared energy;
covariance is separately retained, so these are not additive variance shares.
The first-indirect component is small. This establishes the location of the
observed replicate disagreement, not the causal success of another sampler.
rho=1 in the locked scene prevents reflectance attenuation of later bounces.
The original four-level absolute-p99 decay exponent is about 0.5184.
Extrapolation predicts 1.71e-5 at 131072 and 1.20e-5 at 262144: this is a
planning warning only, not a measured cap outcome or a new threshold.

## One small selected-pixel CPU diagnosis, result 193

Before any more full-image acquisition, instrument separately generated
headers from builds 151 and 187. Keep the returned transport components and
all their accumulation expressions unchanged; only record the actual
per-bounce reflected contribution and first-direction importance correction.
Reversing the instrumentation must reconstruct the entire input header.
The original-cosine header is recovered by exactly reversing 187's declared
scrambling edit. No active/default source, old binary or evidence is modified.

Select exactly sixteen C1 pixels from the original 8192-spp sidecars only:
eight largest per-pixel centered replicate energies (descending energy,
ascending linear index for ties), plus eight fixed grid positions at
(x,y) = (40,30), (120,30), (200,30), (280,30), (40,150), (120,150),
(200,150), (280,150). If a grid position duplicates a tail position, retain
it once and take the next unused largest-energy pixel until sixteen remain.
Selection is explicitly post-hoc, C1-only and unsuitable for acceptance.

Run original cosine, failed primary-direction guide and already-built nested
scramble in that order, one time each, at the original four seeds and exact
sample interval [0,8192). Keep every selected pixel and every bounce, including
zeros. Record per-component float64 means/moments, per-bounce luminance means,
second moments and cross moments, and importance-weight moments. Require
bit-exact reconstruction of all selected original and 180 mean/moment fields
before interpreting instrumentation. No independence or confidence claim
uses per-path RQMC moments. A nested-scramble selected-pixel result is only a
diagnostic; it cannot satisfy 188/189/190 or admit any reference.

Use one CPU with nice 15, 4 GiB address space, 120 aggregate CPU seconds and
180 elapsed seconds per native/serial compilation invocation. No GPU work,
parallel native jobs or queue. Refuse existing work/output, preserve every
invocation, generated source, compiler log, partial and actual return code.
An operational failure stops without an automatic retry. The preliminary
191 launch failed before imports/data processing because LD_LIBRARY_PATH was
missing; the corrected environment completed in <1 second. No radiance job
or scientific attempt was restarted in that correction.

Questions: Is later-bounce contribution spread across many bounces? Does
the direct-only guide reduce first-bounce variance while increasing weighted
later contribution variance? Does nested scrambling show a useful change on
these fixed diagnostic paths? Answers retain covariance and selected-pixel
scope; no population or reference qualification inference follows.

## Critical path and stop rules

1. Finish terminal-record publication (180/185), 191 diagnosis and the small
   diagnostic above. Keep correctness records 053/054, GPU-port signed-zero
   diagnosis 091 and all actual quality losses separate from reference noise.
2. Choose further sampling work only after the diagnosis. Do not blindly run
   a new full-image guide or start 188/189/190 because a binary exists. A new
   candidate still needs prospective definition, physical/all-state/prefix
   proof, feasibility, the fixed full corpus and original provenance intake.
3. Timing is independent: 185 admits the already registered 186, but sizing
   is not accepted calibration. Do not launch the long GPU campaign merely
   to fill idle time. Examine retained precision/output evidence first; any
   new targeted GPU diagnosis needs its own prospective scope and load bound.
4. Run the final corpus pilots and original six-gate auditor only with actual
   complete prerequisites. No subset, threshold relaxation, seed selection,
   increased cap, dropped scene, repaired-variant substitution or hidden mask.

All 24 eligible references, complete quality/memory pilots, actual full
timing capability and the original six READY gates remain mandatory. No
claim that these actions guarantee success or provide a completion date.
No N011, CUDA, Actions, power/clock/display/window changes, default build
promotion or N001–N009 result changes. Direct error-1.0 pixels remain
**UNRESOLVED / 未解決**, included. This diagnostic is scientific analysis;
unit/runtime regression tests are not run.
