# Geometry-barrier reconstruction: full-image CPU feasibility

2026-10-24, checkpoint f646271f, before implementation/reconstruction/new scores.
Observed M001 development only; no new heldout, novelty or architecture claim.
Completed static screen,013,015and016evidence remain immutable.

## Question and prior art

Can one fixed geometry-constrained spatial reconstruction satisfy the unchanged
all-image quality gates on all six finite-depth targets with <=64original PT
samples/pixel, and keep its deterministic reference reconstruction bias inside
the same gates? This tests spatial reuse of physically correct finite transport,
not another directional proposal. A failure rejects this fixed reconstruction.

[Edge-avoiding a-trous filtering, Dammertz et al.2010](https://doi.org/10.2312/EGGH/HPG10/067-075)
is established prior art. Our fixed screen-space segment barrier and geometry-only
weights are an implementation choice, not a novelty claim or exact reproduction
of that paper. Biased reconstruction can smear lighting discontinuities even
with geometric barriers; measure every pixel and preserve losses.

## Exact fixed reconstruction

Use only the original source seed305419896 at spp=[1,4,16,64], all four rungs for
each H01/B2,H01/B8,H02/B2,H02/B8,H03/B2,H03/B8, in that order. These24existing PT
captures are already terminal/admitted in022. No PT or reference sampling, new
seed, resubmission, denoiser tuning, quality-mask exclusion or old-output write.
Raw PT selected budgets256(B2)/1024(B8) remain independent published controls.

Use actual013HWRT primary hits.bin and its identical original physical state,
not reference radiance or oracle hit positions, to build geometry weights. Rehash
and require its published096correctness/primary pass and zero M001 primitive/
presence/depth-bound mismatches. Reconstruct positions from exported t and the
specified float32 center-camera ray expression, as in013diagnostics; these are
CPU reconstructions, not exact exported GPU positions or a qualified future GPU
G-buffer. Normalize exported normals and flip toward the camera. Require actual
hit flags/primitive/material identities consistent with the captured geometry.

Apply three successive a-trous passes at fixed strides1,2,4. Each uses the25
integer offsets(dx,dy) in [-2,2]^2 and separable kernel[1,4,6,4,1]. For center i
and tap j, accept only if every pixel on their discrete segment, including the
endpoint, is in bounds, is a primary hit, has the same material, normal dot>=.999,
and abs(dot(n_i,pos_k-pos_i))<=1e-5*max(1,scene triangle AABB diagonal). The segment
has m=max(abs(dx*stride),abs(dy*stride)) steps; k=1…m uses nearest integer offsets
floor(k*delta/m+.5) independently in x/y. The center tap is always valid for hits.
No radiance-dependent weight, range clamp, energy rescale or adaptive radius.
Normalize surviving nonnegative weights per center each pass; primary misses
output exactly zero. All weights depend only on frozen geometry/camera, never
candidate/reference intensity. Filter only indirect luma (the source is exactly
grey RGB), preserve original PT direct and form total=direct+filtered indirect.
No history, temporal accumulation, new geometry rays or cached lighting.

Freeze geometry weights before reference radiance is read. Save complete masks,
positions/unit normals/hit/material arrays, all three output stages for every
rung, final per-component error arrays and full metrics. Hash all input and new
output bytes under repository/out. Original PT plan/result/full raw inventory,
022published identities,013geometry evidence and complete original qualification/
physical/source chains must validate before reconstruction.

## Decision, CPU qualification and stopping

For every row use all57,600pixels/linear reference-RMS normalization with total
NRMSE<=.05, indirect NRMSE<=.10, absolute indirect energy bias<=.05; defined finite
nonnegative image values and finite/defined metrics required. Record support,
reference-zero leakage, active-p99/max and zero samples without exclusions.
Apply the SAME fixed filter to original four-seed16384spp indirect mean only as
a deterministic reconstruction-bias diagnostic. Preserve reference direct and
score against the unfiltered admitted mean. This is never replacement reference
or new convergence/admission. Its own total/indirect/bias gates must also PASS,
so accidental noisy-error cancellation cannot admit a filter with excessive bias.

Select the smallest passing rung independently per target, retaining all four
scores even after PASS. All six targets need a passing rung<=64 AND passing
reference-bias gate for CPU_RECONSTRUCTION_FEASIBILITY_PASS; otherwise reject as
REJECTED_NO_GPU after all six valid outcomes. Missing/nonfinite/inconsistent
input or process failure means INVALID_STOP_NO_RETRY, preserve partial outputs
and stop. Do not skip later targets after scientific quality failures. No added
rungs, stages, thresholds, samples or retries. Original raw-PT sample reduction
would be >=4atB2/>=16atB8, but is NOT a speed claim: a future product must include
primary export, buffers, barriers, filtering, synchronization, allocation and
end-to-end GPU calibration. Standard denoised external baselines remain needed;
raw PT versus filtered PT is not general family superiority or final novelty.

Before reconstruction, test the actual vectorized kernel against a separately
written scalar loop on small fixtures: exact stencil/stride/normalization,
constant and zero preservation, positive convex bounds, material/normal/plane
barriers, miss/viewport/segment barriers including a thin intervening obstacle,
sequential-pass order, and malformed/nonfinite inputs. Test inclusive full-image
quality predicates and reference-bias conjunction. Commit code/test receipt
before pilot. Do not identically rerun earlier test suites or old Renderer builds.
New source is standalone under lane_m; default build graph and N001–N010 unchanged.

One named CPU target process at a time, max300CPU/600wall seconds,4GiB address
space/one thread,16GiB free disk; no output overwrite. Independently rehash and
recompute all saved stages/error arrays/metrics and verify against scalar sampled
pixels before next selection. Publish all outcomes, commit/push branch and update
Issue7. No GPU in017. Any PASS permits only separately registered GPU correctness
implementation; no accepted GPU time, memory, heldout/device/dynamic support,
architecture promotion or Lane M completion follows. No power/clock/desktop
changes, CI/Actions or historical evidence edits.
