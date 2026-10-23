# M001 closest-primary development validation

2026-10-24. Registered after the bounded static screen083, before producing a
closest-primary shader, compiling its isolated executable or running its GPU
variant. This is correctness development on observed data, not a new heldout
cohort, a reference replacement, an indirect-GI repair or a timing campaign.

## Question and immutable boundary

Can strict closest-float primary selection remove the two C1 wrong-surface
zero-direct observations diagnosed in N010053/054, while preserving all-pixel
primary/direct correctness on C1 and the original three M001 static scenes?
N010 already performed the CPU geometry diagnosis. Reuse its immutable evidence;
do not rerun that diagnosis or reinterpret it as a verified GPU repair.

The only shader change is primary selection in private copies of
`n001_primary.comp.glsl` and `n003_primary_software.comp.glsl`: remove the wide
`max(2e-4,abs(best_t)*2e-5)` tie interval; select smaller finite candidate t,
using smaller primitive ID only for exactly equal float t. Candidate triangle
acceptance rejects t>best_t, without a tie allowance. Keep software AABB pruning
at best_t; keep ray minimum, triangle intersection arithmetic, sidedness, camera,
geometry, normal computation, stack, descriptor ABI, direct ulp4 profile and all
RC transport/representation/sample settings unchanged. This is strict ordering
of the existing float candidates, not a watertight-double GPU implementation.

Use a new standalone output tree under repository/out. Recompile all13original
capture translation units with the original compile options and includes,
changing only the three shader-directory macro values to a private shader tree.
Copy every original SPIR-V byte exactly except the two newly compiled primary
shaders. Pin all source/generated inputs, compiler commands, actual dependency
files, linked static libraries, old/new shader identities and executable bytes.
Original sources, generated files, build/n009 outputs, evidence and default CMake
graph stay unchanged. No old A/B targets or default Renderer integration.

## CPU gates before GPU work

1. Verify original primary source hashes against N010054 and original fixed RC
   executable/shader identities against the frozen controls. Prove exact inverse
   of each private source overlay and unchanged unrelated shader bytes.
2. Test the actual extracted shader selection functions as C++ float functions:
   closer surface wins regardless of ID/visitation order, one-ULP differences
   remain ordered, exactly equal t chooses the smaller ID, and permutations of
   multiple candidates produce the lexicographic (t,ID) minimum. Include the
   old-rule counterexample; this is a selection contract, not repeated geometry
   diagnosis or an emulator of GPU candidate enumeration.
3. Compile both shaders for Vulkan1.3 and validate SPIR-V; compile/link all13host
   translation units privately. Preserve any failure in a new immutable attempt.
   A justified implementation repair requires a new output version, never an
   overwrite. Rehash all original inputs after build. Run CPU CLI rejection with
   an unusable ICD and explicitly label it CPU-only, not runtime admission.
4. Implement/test one-named-process preparation and independent intake before
   acquisition: exact source/reference/plan identities, ordered stop/failure,
   missing/partial data and overwrite refusal. No automatic GPU queue.

## Fixed corpus, process order and finite stop

At most eight new native processes, each individually CPU-planned, announced,
executed and independently audited before the next selection:

1. C1/hwrt; 2.C1/software; 3.H01/hwrt; 4.H01/software;
5. H02/hwrt; 6.H02/software; 7.H03/hwrt; 8.H03/software.

C1 exactly reuses the static Sponza scene, contract and source+target two-frame
CLI of N010011, direct-profile ulp4, with final captured state identical to that
record and its C1_T_B2 physical reference. The other six use the original M001
static scene/contract, one source frame and metadata spp512, matching their
retained fixed RC capture state. This is one fixed RC image per process; its
B2/B8 diagnostic scoring does not establish PT-equivalent finite transport.

Reuse original admitted M00116384spp four-seed means and the original N010 C1
qualified reference bytes/32768spp means. Rehash complete qualification and raw
reference inventories and prove physical state/canonical scene identity. No
reference sampling, new seed, extra scene/rung or quality tuning. Before each
execution freeze the full native command and all actual build/dependency/CPU/
reference inputs in a unique plan, require16GiB free disk and validate again at
execution. Use explicit180s native wall/120s CPU process guards, complete owned
allocation ledgers≤8GiB true peak and zero teardown. No power/clock/desktop change.
Existing timestamps are diagnostics; no accepted statistical or lifetime timing.

Any missing/partial/invalid provenance, physical-state mismatch, operational,
finite/coverage/memory failure or valid correctness FAIL preserves evidence and
**stops this registered sequence**. No retry, automatic next-backend diagnostic,
threshold relaxation or continuation after failure. A later identified repair
requires a separately registered change and new outputs. First failure is a
reportable outcome. Eight independent PASS outcomes end the sequence; no further
013process, generality or architecture promotion follows automatically.

## Independent all-pixel admission and outcome

Rehash the complete plan, acquisition inventory and archive, actual new binary
and shader tree, source/build/CPU receipts and all reference bytes. Validate
metadata, geometry/frame and canonical physical-scene identities, capture/PFM
shapes, all native outputs, zero work overflow and complete allocation ledger.
Store complete primary-comparison arrays and f64 direct/indirect/total error maps
under repository/out; Git receives compact identities and outcomes only.

Every57,600pixel is included. Primary hit/miss presence must match the oracle;
every GPU hit must have valid metadata, finite t within the original ray bounds
and finite unit normal. For each reference hit require
`abs(t_gpu-t_ref) <= max(1e-4,1e-5*abs(t_ref))`, inclusive. This is a new prospective
float-depth correctness bound, not a changed M001 image-quality threshold.
Report all primitive/normal/position/depth mismatches and their maxima; do not
mask edges, coplanar IDs, low-signal regions or either named pixel. Exact primitive
identity across the entire image is a reported diagnostic, not an assumed
consequence of closest-float selection. Camera float/double and intersection
arithmetic can still differ.

For direct light require unchanged M001 physical checks: whole-image linear
luminance NRMSE≤1e-4 and max absolute error≤1e-5, both inclusive, finite and defined.
Additionally require no reference-positive/GPU-nonpositive direct pixels in the
entire image. On C1, both named pixels (107,109)/(261,161) must select reference
primitives51389/172941, have positive direct output and relative direct error<1.
Report full-image maximum relative error over every reference-positive pixel and
all reference-zero leakage separately; undefined relative values must not be
silently converted to zero. These reports do not exclude pixels from any metric.

A valid correctness PASS requires every above predicate. Independently report
all-pixel indirect/total metrics and unchanged original quality decisions
(total NRMSE≤5%, indirect NRMSE≤10%, absolute indirect signed bias≤5%). They do
not gate this narrow primary/direct question or erase old RC losses; no speed
comparison follows without actual same-quality admission and a separately
registered complete calibrated timing family. Undefined/nonfinite quality
metrics are invalid evidence, never a scientific loss or an escalation permit.

Even eight PASS outcomes would establish only this private variant's correctness
on the declared observed corpus. The historical original executable/results stay
unresolved and unchanged; other Sponza scenarios, dynamics, temporal reuse,
representative devices, direct relative-error behavior outside this corpus,
structural indirect error and timing uncertainty remain open. A C1 two-pixel
repair cannot explain the historical88.8399% indirect NRMSE loss. Broader Lane M
remains incomplete; new independent heldouts are required for new architecture
claims. Default Renderer build/runtime regression and validation layers are
NOT_RUN unless separately actually executed.

## Pre-acquisition numerical clarification

2026-10-24, after CPU build088and before implementing the full-image auditor or
any variant GPU acquisition: finite unit normal means
`abs(length(normal)-1) <= 1e-4`, inclusive, for each actual hit. Miss records must
retain the original invalid-ID/clear convention. This fixes the previously
unspecified float normalization tolerance before any candidate observations;
none of the image, depth or named-pixel gates changes. Position differences are
diagnostics reconstructed from captured camera/hit distance and the canonical
reference ray, not exported GPU positions or proof of exact GPU arithmetic.
