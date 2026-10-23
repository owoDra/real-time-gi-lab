# Actual-normal product guide: fixed CPU feasibility screen

2026-10-24, checkpoint c8b77521, before new implementation or sampling.
Observed-corpus development only. Study015 and all earlier evidence remain
immutable. This is a separate fixed proposal, not an extension or retry of015.

## Question and prior art

Can conditioning the frozen015 incoming-light field on the actual continuation
normal achieve variance times complete query-cost efficiency E>=1.20 in every
original H01/H02/H03 B2/B8 condition, including the entire old training cost?
015 observed 24,957–32,564 below-surface null paths per65,536 samples and worse
variance in five conditions. This motivates a prospective alternative, not proof
that nulls caused the losses or that eliminating them fixes the representation.

Product sampling of incoming light and BSDF is established prior art:
[Diolatzis et al.2020](https://rgl.epfl.ch/publications/Diolatzis2020Practical).
This simple discrete Lambertian approximation is neither their LTC algorithm
nor a novelty claim. Existing scalar-cache deficiencies remain unresolved.

## Fixed candidate and reused evidence

All015 transport, grid, directional bins, depth, four render seeds,1024spp,
geometry-only16pixel selection and finite BF-P semantics remain fixed. Read the
exact015 training-weights.f64 for each scene; do not retrain or read reference
radiance to form the proposal. At each continuation, with actual oriented unit
normal n, original weights a_b and bin center w_b=bin_direction(b,0.5,0.5), form
p_b=a_b*max(dot(n,w_b),0). Use the unchanged015 largest-remainder quantizer, total
2^24 and ascending-bin ties. An all-zero product falls back to uniform sphere.
The lookup uses the original cell and exact remaining vertex count,1…7.

Keep the unchanged half-cosine/half-guide draw and evaluate its full mixture PDF
using the actual quantized mass. Within-bin directions remain uniform z/phi.
Bins can cross the tangent plane; all below-surface draws remain zero/null,
without retry or rejection renormalization. Cosine support remains complete and
per-step throughput<=2. Conditional proposal changes do not change transport.
Continuous importance identities are not bit-exact GPU/unbiased RNG claims.
Compute64 products and quantization at every vertex in this CPU prototype;
query counts exclude that overhead. No GPU performance inference from this proxy.

Reuse exact015 cosine sample/direct arrays, query counts, primary scan/selected
pixel evidence and frozen training payloads. Rehash the entire source pilot
receipt/inventory and old plans; verify old reference qualification/source/build
input chains before acquisition. Do not rerun the cosine control or training.
Charge the original FULL measured training closest+shadow cost to each depth
again in the cost model, despite byte reuse now. Record executed and reused
paths separately. This cost model does not describe new training execution.

Only the new candidate is sampled: H01,H02,H03, each one CPU process, both depths
and all original four seeds,1024spp per16pixels (393,216 new render paths total).
Scan/retrace primaries in the new binary and verify exact bytes and selected IDs
against both original reference and015. Save every f64 new indirect sample and
primary direct value; compare primary direct to015 exactly. No exclusions,
reference resampling, additional seed, training, tuning or replacement.

## Preparation, decision and stopping

New standalone header/native/test/runner only; preserve all015 files, old results,
N001–N010 and default CMake graph. Compile C++20/O2/no-fast-math/no-contract with
UBSan. Before sampling, test the actual new normal product/lookup and its use of
the original sampler: front/back normal response, zero fallback, finite inputs,
quantized mass/empty-bin handling, complete mixed PDF/support and throughput
bound, and retained tangent-crossing nulls. Test a deterministic independent
continuous integral for multiple arbitrary normals and an actual two-transition
analytic estimator with a fixed seed,262,144 samples and6-standard-error health
bound. The health tolerance is not a quality threshold. Reuse old25kernel test
PASS records; do not identically rerun them. Commit implementation before pilot.

V is the sum of64 unbiased1024-sample variances, including zeros, per role/depth.
C_cos is the unchanged015 total cosine closest+shadow count. C_product is all new
candidate closest+shadow counts plus ALL original training queries for that scene.
E=(V_cos*C_cos)/(V_product*C_product), finite positive variances/costs required.
All six E>=1.20 inclusive: CPU_FEASIBILITY_PASS; otherwise REJECTED_NO_GPU after
all six valid decisions. Invalid/missing/nonfinite evidence or acquisition
failure: INVALID_STOP_NO_RETRY, preserve partial output and stop. A scientific
loss does not skip later scenes. No population interval/general efficiency claim,
full-frame amortization, whole-image quality admission, accepted GPU timing,
new heldout, architecture promotion or Lane M completion follows from this screen.
Even a PASS only permits a separately registered GPU implementation/qualification.

Each native process max300CPU/600wall seconds,4GiB address space, one thread,
16GiB free disk before execution; new output directories only under repository/out.
Persist source/compiler/dependencies, exact old receipts/inputs/field/control
identities, command, all samples, moments and cost classifications. Independent
terminal replay must rehash inputs, recompute variances (including independent
fsum), compare all saved arrays and preserve all losses. Publish compact records,
commit/push research branch and update Issue7. No GPU in016, settings change,
CI/Actions, destructive history operation or old-output overwrite.
