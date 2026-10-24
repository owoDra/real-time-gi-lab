# Surface-quadratic reconstruction: fixed full-image CPU screen

2026-10-24, checkpoint 7afa141c, before new implementation, coefficients or scores.
Observed M001 development only. The completed 017 operator/results are immutable;
this is a different local model, not an extra rung or retry of 017.

## Falsifiable question and comparison

Can geometry-constrained local quadratic regression retain lighting variation
that the 017 constant model blurred, while meeting the original full-image gates
on every H01/H02/H03 B2/B8 target at <=64 original PT spp? Require the same separate
reference-reconstruction bias gate; a good noisy image cannot cancel an excessive
fixed-operator discrepancy into admission. All six targets must pass. CPU success
would permit separately registered GPU correctness work, not architecture acceptance.

Local regression for Monte Carlo reconstruction is established prior art:
[Bitterli et al.2016 NFOR](https://jannovak.info/publications/NFOR/index.html).
NFOR also discusses limitations of auxiliary-buffer weights for regression. This
fixed geometric quadratic model is not an NFOR reproduction or a novelty claim.
The goal remains a competitive GI transport architecture; a CPU image component
and sample reduction alone cannot establish it. Fair denoised external baselines,
new heldouts/dynamics/devices and full-cost GPU measurements remain necessary.

## Immutable inputs and full boundary

Reuse exactly the 017 geometry/masks frozen from actual 013 HWRT primary exports,
and the 24 original seed305419896 PT images at spp=[1,4,16,64], not new rendering.
Order: H01/B2,H01/B8,H02/B2,H02/B8,H03/B2,H03/B8. Evaluate all four rungs per target.
Rehash published 108/017 receipts and payload inventories, source plans, original
022 PT identities and 096 primary evidence, plus original complete physical and
reference qualification chains. Use no oracle positions/radiance for weights.
All 017 barriers, 25 tap positions, separable [1,4,6,4,1] base weights, strides
1/2/4 and geometry normalization are identical, not retuned. Frozen masks are
read, never modified. No old source/output overwrite, new seed or reference path.

For every center, build coefficients from geometry alone before reading reference
intensity. Let n be the oriented unit normal. Use helper z if abs(n.z)<.999,
else helper y; t=normalize(cross(helper,n)), b=cross(n,t). For accepted tap j,
delta=position_j-position_i and s=max accepted length(delta); use s=1 if all zero.
Set u=dot(t,delta)/s, v=dot(b,delta)/s; rejected taps have delta/u/v zero. Basis
columns, in this fixed order, are [1,u,v,u*u,u*v,v*v]. The evaluation basis at
center is [1,0,0,0,0,0]. Original raw kernel weights a_j are zero for rejected taps.

Use weighted modified Gram-Schmidt, with TWO ordered reorthogonalization sweeps
per column over previously retained columns. Carry each column's evaluation at
the center through the same subtractions. Retain a column iff its squared weighted
residual norm is strictly >1e-6*sum(a); otherwise set the column and center value
to zero. Normalize retained columns by sqrt(weighted norm). The constant column
is always retained for hits. This fixed ordered rank reduction handles one-
dimensional support without a radiance-selected model or ridge regularization.

After columns0…2, store affine coefficients c_j=a_j*sum_k q_k(center)*q_k(j).
After all six columns, store quadratic coefficients with the same formula.
Choose full quadratic if sum(abs(c_j))<=4; else affine if its L1<=4; else original
constant a_j/sum(a). The L1 bound limits signed coefficient amplification, not
image-quality error. Require finite coefficients, rejected weights exactly zero,
and abs(sum(c_j)-1)<=1e-8 for hits; failures are INVALID, not repaired by rescaling.
Miss coefficients/output are exactly zero. Record retained-column bitmasks and
selected model (quadratic/affine/constant/miss) per pixel/stage, including rank
reductions and L1 fallbacks; selection uses no radiance.

Each pass evaluates the signed coefficient sum of previous indirect values, saves
that FULL preclip image, and clips only negative results to zero before the next
pass. Save negative count/minimum/absolute energy per stage. Clipping introduces
possible bias and is included in every score, never hidden as discarded pixels.
No upper clamp, energy rescale, radiance-dependent weights or temporal history.
Preserve original PT direct and form total=direct+filtered indirect.

This CPU double prototype computes/stores 3*25*57600 coefficients (34,560,000bytes
as f64;17,280,000bytes if f32), in addition to masks/geometry/images and fitting
work. These are not a GPU owned-memory measurement. A future implementation must
produce/qualify actual primary data and coefficients on GPU, charge fitting,
all buffer lifetimes, synchronization and filtering each frame, and validate
float32 rank/fallback decisions. Uploading free CPU-fitted coefficients is not
an end-to-end architecture speed demonstration. No performance inference from
CPU wall, source sample count, isolated filtering or ignored fitting costs.

## Fixed quality classifier, CPU tests and stop

Every new output and bias diagnostic uses all57,600pixels, unchanged linear-luma
reference-RMS normalization: totalNRMSE<=.05, indirectNRMSE<=.10, absolute indirect
signed-energy bias<=.05; finite/nonnegative final images and defined metrics.
Apply the SAME fitted coefficients/clipping to the original four-seed16384spp
mean for a labelled reference-reconstruction bias diagnostic. Preserve reference
direct; compare with the unchanged unfiltered admitted mean. This is not a new
reference, convergence test or exact physical-bias proof. Record complete support,
reference-zero leakage, active-p99/max and all error arrays without exclusions.

Per target select smallest passing noisy rung; retain all four rows. Admission
requires that rung<=64 AND reference-bias PASS. All six admitted targets imply
CPU_RECONSTRUCTION_FEASIBILITY_PASS; otherwise REJECTED_NO_GPU after all valid
outcomes. No extra samples/rungs/models/thresholds/stages or in-study tuning.
Scientific loss does not skip later targets. Inconsistent/missing/nonfinite input
or process failure is INVALID_STOP_NO_RETRY: preserve all partial data and stop.

Before any coefficients/images from M001: test the actual vectorized kernel,
including independent weighted least-squares/scalar checks, constants/zeros,
positive affine/quadratic reproduction, one-dimensional/rank-deficient support,
L1 fallback/invalid normalization, signed weights/preclip negatives, geometry
barriers, miss/viewport behavior and malformed inputs. Reuse 017 test evidence
without identical rerun; test the new model itself. Commit source and test record
before pilot. Independently replay full saved coefficients/selector maps, all
preclip/clipped stages/error arrays and metrics; compare coefficients and every
stage at fixed64uniform full-image+64geometry-hit percentile pixels per target
with a separately written scalar/SVD solve (numeric health, not quality tolerance).
Independently recompute full-image RMS/energy bias with fsum before next target.

One named CPU process at a time:300CPU/600wall seconds,4GiB address space, one
thread,16GiB free disk; new directories under repository/out only. Persist all
coefficient fields, maps, preclip/clipped stages, metrics, hashes and all failures.
Standalone new lane_m files only; no default Renderer/CMake or N001–N010 changes,
old-output write, CI/Actions, GPU or power/clock/desktop setting change in018.
Publish compact outcomes, commit/push research branch and update Issue7.
No accepted timing/memory/architecture/novelty claim or Lane M completion follows.
