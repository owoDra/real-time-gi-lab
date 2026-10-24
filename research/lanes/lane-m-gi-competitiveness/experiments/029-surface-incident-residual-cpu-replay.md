# Surface incident-radiance residual: finite CPU feasibility replay

2026-10-25. Baseline8d8b12fc, after028 completion, before new029 implementation,
contracts, fitting, residuals or scores. Known M001 development data, not new
heldouts. Preserve all026/028 losses; no further NRD variant or GPU process.

## Question, prior art and architecture hypothesis

Can a geometry/owner-conditioned degree-two incident-direction approximation
reduce empirical full-image variance by at least1.20 including its training
samples, while both signed and clipped64-path images satisfy every original HDR
gate on ALL H01/H02/H03 B2/B8 targets? Failure rejects this fixed representation
before GPU development; there is no in-study grid, ridge, split or sample tuning.

015/016 failed complete-cost guiding;017 had reference-reconstruction bias;
018/022's established quadratic reconstruction passed these static images but
is not novel transport;026/028 fail all six NRD cold/warm conditions. This
motivates testing a physical path residual instead of replacing illumination
with a spatial prediction. It does not prove the cause of any previous loss.

Control variates and regressions are established:
[Neural Control Variates,2020](https://research.nvidia.com/labs/rtr/publication/muller2020ncv/)
learn an integrand and its integral and correct its residual.
[Regression-based Monte Carlo Integration,2022](https://arxiv.org/abs/2211.07422)
relates fitted functions/least squares to control variates. We do NOT inherit its
variance guarantee for our separately trained, regularized, pooled model.
[Neural Two-Level Monte Carlo,2025](https://www.mishok43.com/nirc/)
integrates an incident-radiance cache and corrects it with path-traced residuals.
[ReSTCV,2026](https://hercier.github.io/restcv/)
reuses correlated estimates with reservoir-based pixel-difference estimates.
029 is neither a reproduction of those methods nor a novelty claim.

The prospective architecture is a bounded surface/owner incident-radiance field
with analytic Lambertian integration and physical residual paths. Explicit small
fields could replace a neural/world-volume representation and make allocation,
object updates and fallback costs visible. The proposed system contribution,
competitiveness, object-local transforms, dynamic dependency handling and novelty
are UNPROVEN. This replay tests only whether one required representation has
useful residual correlation on full images. A PASS permits a separately registered
actual transport implementation; it does not promote a cache, Renderer or Lane M.
An eventual architecture must beat fair denoised/transport families, not raw PT
alone, and pass new heldouts/dynamics/devices/deployability/full-cost gates.

## Immutable physical input and fixed model

Use ONLY the six actual026 n1 captures, all64 frames0..63 and their exact seeds
and finite B2/B8 physical state. Published163/165 anchor native/audit receipts;
verify Git identities and consumed payload hashes. Reuse original physical and
input predicates, not old denoised RGB. No new paths, GPU, reference generation,
026 metric rerun, retraining of015, or substitution with028 copies. Actual first
secondary directions and raw PT indirect values at1spp are a direction and one
full finite-depth suffix value. Misses/zeros remain samples. All64 new input
reads are checked against their anchored hashes. Do not infer unavailable deeper
path trajectories or measured hardware query counts.

For each target, frame0 primary hit/normal/material/instance and captured physical
geometry define groups BEFORE radiance is read. For each owner(instance ID),
compute the AABB of ALL its actual geometry triangles. Normalize each hit's actual
secondary origin into that AABB (zero-width axes use extent1), floor8*coordinate,
clamp0..7. Key=(instance,opaque material token,round(1024*n.x/y/z),cell.x/y/z),
where n is the normalized actual oriented primary normal. No reference/radiance
may change these groups. This is a static owner-relative WORLD-axis partition,
not a validated object-local rotation/deformation system. Sky has key-1 and final
zero indirect, yet remains in every full-image denominator. Keep all groups;
no hit/signal threshold or pixel exclusion.

Normalize actual saved first directions to unit length in f64, retaining/checking
the original float32 witnesses and unit/in-lobe predicates. The nine features are
phi(w)=[1,x,y,z,xy,yz,zx,x*x-y*y,3*z*z-1]. Under the continuous cosine density at
unit normal n, mu(n)=[1,2nx/3,2ny/3,2nz/3,nx*ny/4,ny*nz/4,nz*nx/4,
(nx*nx-ny*ny)/4,(3*nz*nz-1)/4]. This follows E[w]=2n/3 and
E[wi*wj]=(delta_ij+ni*nj)/4. Independent quadrature must check the actual kernel.

Train ONLY frames0..7. For each key, form X from all its training directions and
y from their raw indirect suffix values, including zero/miss values. Solve
(X^T X + lambda I)c=X^T y, lambda=1e-3*trace(X^T X)/9, regularizing ALL columns.
No iterative/refit/parameter search or reference fit. Freeze coefficients before
reading/scoring evaluation radiance (frames8..63). Store every Gram/RHS/lambda,
coefficient and key map. No neural network or upstream code/shader changes.

For each pixel, keep the eight raw training contributions, and for EACH of the56
held-apart directions use f_i + mu(n).c - phi(w_i).c. Output their sum divided by64.
The same full64 paths also form the baseline mean. The candidate does not throw
away or discount training path costs; both roles have identical physical samples,
with candidate fit/integration/evaluation arithmetic additionally required. Keep
all signed per-frame corrected values. No residual rejection, positive-only
training, clipping inside the estimator, temporal-mean replacement of026/028
warm gates, or resetting old cohorts. This is a new64-path static batch estimator,
not a claim that an original1spp frame or temporal history passed.

Conditional continuous-sampling expectation of each held-apart correction is
zero for ANY frozen coefficients. Training terms are unchanged, so their use in
the fit does not silently make them corrected in-sample. This reasoning is not
an exact finite-RNG/float32 unbiasedness proof. Record saved-direction moment
drift; discretization/source precision and a future GPU implementation need
separate validation. Cache prediction error/staleness is not permission to drop
the physical residual. Known control-variate algebra alone is not novelty.

## Fixed decisions, validation and stopping

Process order H01/B2,H01/B8,H02/B2,H02/B8,H03/B2,H03/B8, once each, one CPU worker.
Before replay, commit new kernel/runner/independent auditor/tests and run actual
contracts: arbitrary-normal analytic moments against independent quadrature,
constant cancellation, signed residuals, exact polynomial example, singular/zero
ridge fields, invalid/nonfinite/shape/zero direction rejection, geometry keys and
opaque material tokens, split/order/overwrite/no-GPU safeguards. Tests must cover
the executed kernel. Old successful suites/builds are reused by hash, not rerun.

Independent terminal CPU audit rehashes every consumed actual field and original
receipt, recomputes ALL group coefficients with augmented-matrix SVD rather than
production normal equations, and replays all56 corrected full fields and both
signed/clipped images. Coefficient agreement rtol1e-8,atol1e-12*max(max|training y|,
1e-20); image/residual agreement rtol1e-10,atol1e-12*max(max|all raw y|,1e-20).
Independently math.fsum means/second moments/metrics; retain full errors/maps.
Any provenance/nonfinite/input/order/timeout/implementation mismatch stops the
whole029 cohort as INVALID_STOP_NO_RETRY, retaining partials. A parser-only repair
needs a committed correction/new exclusive output, never an overwritten attempt.

Define T=sum over ALL57,600 pixels of training-frame unbiased sample variance
(ddof1 over8); R likewise raw evaluation variance over56; S likewise signed
corrected evaluation variance over56. All zeros/misses are retained. The fixed
empirical ratio E=(8T+56R)/(8T+56S) must be finite/positive and >=1.20 on EACH target.
This includes training-sample noise/cost at the identical64-path physical budget,
but ignores extra arithmetic/cache/transfer/divergence; report operation/storage
counts and diagnostic CPU wall separately. This is NOT a calibrated speed/query-
count gain, confidence interval, universal variance guarantee or cost-matched GPU
claim. The deterministic saved seed set is an observed finite diagnostic.

Score the baseline64-path mean and candidate signed image and its fixed display
clip max(value,0), with unchanged direct mean shared bit-exactly. Preserve every
negative signed pixel/minimum/energy and clipping delta. All pixels/16384spp four-
seed admitted physical references and BT.709 luma stay fixed. BOTH candidate signed
and clipped images must pass total NRMSE<=.05,indirect<=.10,abs indirect signed
energy bias<=.05 and direct NRMSE<=1e-4,maxabs<=1e-5,zero lost-positive support.
No claim of unbiasedness for clipping. Reference radiance is read only AFTER the
fit/evaluation artifacts freeze, for scoring only; it never trains/selects fields.
All six E and both-image HDR conditions are required for CPU_FEASIBILITY_PASS;
otherwise REJECTED_NO_GPU. Report all per-target wins/losses. Scientific losses
alone do not skip remaining targets. Undefined/zero variance evidence is INVALID,
never a win. End after six valid targets or first operational failure; no extra
sample, split, bin, ridge, scene, rung, variant or GPU continuation here.

CPU contracts/replay/audit:240CPU/360wall seconds each,4GiB address space,one worker,
OPENBLAS/OMP threads1,at least16GiB free disk. Actual fit/read/audit peak arrays and
field bytes are CPU storage, not GPU true peak. New outputs exclusive under
repository out/research/lane-m-gi-competitiveness/m001-residual029-*, raw/large
maps excluded from Git. Default build/runtime NOT_RERUN, no Renderer/CMake/N001–
N010 edits, Actions/CI, power/clock/desktop change, main promotion or accepted
speed/memory claim. Commit/push outcomes and update Issue7OPEN. The full Lane M
objective stays open regardless of this finite diagnostic's decision.
