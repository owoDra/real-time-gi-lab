# N010 executable cohort pilot freeze

This records implementation conditions before the first new comparator image.
The independent pixel tracer uses native Vulkan ray queries (HWRT), centre
camera sampling, cosine directions, point-light next-event estimation, grey
rho=1, opaque two-sided transport and black background. T_B2/T_B8 count surface
vertices exactly as the independent CPU reference. No denoising, temporal
reuse, Russian roulette, textures, ReSTIR or external production-implementation
claim. Repository RC controls likewise are not external production RC.

PT pilot sample ladder: 1, 4, 16, 64, 256, 1024 samples per pixel; all tested
levels and errors are retained. Additional 16384 samples is a diagnostic
numerical/physical-validation budget only, not a realtime speed baseline.
The 32-bit integer-mixed RNG is separate from the reference's Sobol sampler;
seed and each output identity are recorded. Initial native AS setup is reported
separately; source/target transitions must include rebuild/refit/upload costs
before a dynamic comparative timing claim.

The new common numerical profile starts at four float representable steps
along the outgoing face-forward normal (1e-7 normal displacement where
abs(coordinate)<1/32). Endpoint shortening is relative 2e-7; secondary and
shadow tmin=0. Shadow rays exclude only the originating triangle. Primary
clip near is 0 as in the N009/N010 oracle, far is the recorded camera far;
secondary rays are unbounded in the declared scene scale. These are numerical
implementation differences from the double oracle, require new GPU validation
and are scored over every corpus pixel. The legacy large camera-near offset
remains available and labelled separately. Any further repair is documented
with new source/evidence; no claim that this initial profile is already correct.

Static full pixel Renderer timestamps enclose primary tracing, all requested
bounces/NEE and image composition plus final memory barrier. Setup and
diagnostic readback are separate. Native Vulkan allocation lifetimes include
the AS context, storage/scratch/upload buffers and output buffers, with clean
teardown. These timestamps remain DIAGNOSTIC_UNCALIBRATED until the fixed
N010 complete-boundary calibration passes. No runtime quality claim follows
from compiling a comparator or capturing its first image.
