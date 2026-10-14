# N010 preregistration — final preparation for Lane M GI comparisons

Date: 2026-10-14 JST. Parent: `6e7e96246cf7e9e38394bdce89519bf09320c6b1`.
Branch: `research-n010-comparison-readiness`. User direction: N010 ends the
preparation series; proceed to Lane M comparative demonstration afterwards.

## Question and completion boundary

Can the current image-producing GI architecture and credible existing GI
families be executed on identical states, scored against eligible references,
and measured at a common complete Renderer boundary, with true peak memory?

Readiness means an actual retained end-to-end pilot through each step. A plan,
an unexecuted command, a parser-only test or a passing isolated kernel is
insufficient. Failure of the incumbent quality target is a measurable loss;
it must not prevent comparison or trigger another preparation study. N010
does not require the incumbent to win. Preparation defects are repaired here.
An inability to construct a valid comparison is recorded explicitly and
remains unfinished work in N010; it is not relabelled READY.

## Known prior evidence and diagnostic phase

N009 SC NO GO, BF PASS (C7 scope), PT INCOMPLETE and Amendment 1 remain frozen.
C7 V1 mismatch at 21 pixels and old B4 V3 failure are known before this study.
The prior sensitivity mask is not used for acceptance. Sponza direct max
relative error 1.0 is unresolved in N009. CPU investigation of those captures
is **post-hoc diagnosis of N009**, even when run during N010.

Diagnose all C1/C2/C4/C5 direct-zero pixels on both backends, plus C7's
GPU-positive/reference-zero pixel. Retain coordinates, primary primitive,
shadow blocker, ray origin/direction/interval and offset variants. Separate
double geometry diagnosis from prediction of float GPU intersection; a
hypothesis is not a verified GPU repair. Capture actual composite lookup keys
in a new diagnostic path: reconstructed CPU float keys alone do not attest
GPU keys. Validate all pixels, without removing boundary mismatches. Require
R0 max absolute error <=1e-6 and zero positivity disagreements; requantisation
>=99.9% within one LSB; consistent BF-P secondary retrace >=99%. Old B4 remains
historically INCOMPLETE; new two-sided captures do not retroactively fix it.

New executable work is isolated and opt-in. Scene contract C1 and BF-P apply
identically to candidate, controls and oracle. Direct correctness fixes are
shared prerequisites. Missing probe coverage, finite range and secondary
shadow omission remain scored estimator weaknesses unless a separately
identified repaired variant is included; do not silently replace the
incumbent with an improved algorithm.

## Reference qualification

Keep the independent N008 physical transport, intersection, falloff, offsets,
Lambert reflectance, camera and finite bounce definitions. T_B2 (one indirect
bounce) and T_B8 (seven indirect bounces) are distinct strata; no truncated
reference is presented as infinite-bounce truth. BF-P uses opaque two-sided
grey Lambert surfaces, rho=1, black background, N001 soft point-light falloff.
Textures, alpha and glossy materials are outside this declared comparison.

To reduce acquisition cost, N010 may change **only sampling** to randomized
Sobol digital nets with independent per-replicate/per-pixel digital shifts,
fixed dimensions per bounce and nested power-of-two prefixes. Source and
direction-number identities must be recorded. Validate this new sampler on
the applicable N008 analytic/independent controls and compare against the
unchanged iid oracle. RQMC per-sample second moments are **not** an iid
standard error; uncertainty uses independent replicate means. No physically
invalid reference becomes eligible by passing a statistical screen alone.

Freeze four replicate seeds to the four N007 seeds. Levels:
8192, 16384, 32768, 65536, 131072, 262144 samples per replicate. The unchanged
N007 support-aware screen is required: active p99 absolute <=1e-5 and
relative <=5%, with stable support and two consecutive qualifying levels.
All required replicate pairs are retained. Stop at the first qualifying pair
for each cell/transport. Maximum is 262144; a cap failure remains INELIGIBLE.
No sparse whole-frame p99 shortcut, seed substitution or relaxed threshold.
Sampling changes/cap are prospective N010 methodology, never a revision of
N009's 8192-SPP negative result. If qualification fails, retain evidence and
repair methodology prospectively within N010 before another acquisition.

Required comparison corpus: Sponza plus non-Sponza controlled leak/occlusion
geometry, static and actual source/target transitions for camera, light,
moving rigid, stable deformation and topology churn. Reuse attested states
where possible. Declare new light-motion positions by geometry/direct-only
selection and lock them before indirect images; N009 C3 stays
NOT_CONSTRUCTIBLE. Required states, assets and hashes are locked before
reference acquisition. No scene is dropped because of candidate losses.

## Comparison families and quality conditions

Incumbent: visibility-guided Split RC with accepted Lane E ownership, software
and HWRT paths. Controls: executable vanilla/Split RC without candidate's
visibility/storage optimisations, and an independent pixel cosine path
tracer with next-event point-light estimation (path-tracing GI family).
Path tracing is not labelled ReSTIR, and repository RC controls are not
labelled an external production RC implementation. DDGI/RTXGI is a required
named additional Lane M comparator; its integration and supported devices
must be specified before Lane M's accepted comparison campaign, with actual
SDK/source provenance. N010 must make the first RC/path-tracing cohort
executable; the wider Lane M family set is not satisfied by these two alone.
Sources: [Radiance Cascades](https://radiance-cascades.com/),
[PBRT sampling](https://pbr-book.org/4ed/Sampling_and_Reconstruction/Sampling_and_Integration),
[DDGI integration](https://developer.nvidia.com/blog/an-engineers-guide-to-integrating-ddgi/).

Compare common resolution, geometry, camera, sidedness, lighting, transport,
hardware and dynamic source/target sequence. No CPU oracle time serves as a
real-time GPU baseline. Freeze per-family quality-budget ladders and their
tuning split before Lane M accepted timing. N010 pilot validates both
fixed-cost scoring and same-quality selection; it makes no superiority claim.

Score linear HDR direct, indirect and total separately, including reference
zero pixels. Report whole-image RMSE, normalised RMSE, signed sum bias,
active p99 absolute/relative error, leak energy and visibility mismatches;
retain images and full error maps. No whole-image total score may hide an
indirect deficit. Pilot quality targets: total NRMSE <=5%, indirect NRMSE
<=10%, absolute indirect sum bias <=5%; error normalisation is reference
whole-image RMS, with zero reference handled as absolute error/leak.
Same-quality ranking requires **all** targets; nonqualifying families get
quality FAIL and no speed-win claim. Dynamic scoring additionally retains
first changed frame and following recovery frames, with no discarded warmup
after the state transition. Candidate tuning uses distinct held-out states;
neither tuning nor evidence may omit an inconvenient test regime.

## GPU timestamp, memory and bounded measurement

Primary performance axis: GPU timestamps over all image-producing passes,
geometry/instance upload, BLAS/TLAS or software rebuild/refit, invalidation,
allocation-related GPU work, tracing, resolve/composite and synchronisation.
Report CPU geometry/allocation/submit/wait wall costs separately as complete
CPU health/provenance; do not call an omitted CPU cost a GPU win. Initial
setup is separate; recurring dynamic costs stay inside the recurring sample.

Calibrate the **actual full Renderer boundary** with identical controls and
architecture-neutral additional known work (+20% target); Lane K's 5% and
Lane L's 20% are not automatically transferred. Freeze 4 warmup pairs,
12 measured pairs, 8 fresh-process blocks, AB/BA position counterbalancing,
1-second process settle, all raw samples, no exclusions or reruns. Primary
statistic: process median of paired log ratios; control max absolute ratio
<=1.02, span <=1.03 and order bias <=1.02; effect process span <=1.05, order
bias <=1.03 and positive-pair fraction >=0.75 in every process; minimum
effect must exceed control envelope. If calibration is inconclusive, retain
timings descriptively and repair/calibrate before Lane M promotion timing.
No effect claim tighter than demonstrated capability. N010 pilot timings
are diagnostic unless the frozen calibration has passed.

Memory: instrument Vulkan allocation/free lifetimes, including device/local
and host-visible/staging memory, AS storage and scratch, old/new allocations
coexisting during replacement and uploads. Record allocation sizes, current
live sum and high-water mark at every event. Split steady persistent,
transient/scratch, startup peak and recurring true peak; no sum of named
buffers or driver heap budget is accepted as measured true peak. Include
all separate contexts required by a role, prevent double counting shared
allocations, and prove the ledger returns to zero on clean teardown. Freeze
memory constraints before target campaign: no allocation failure/overflow;
total owned Vulkan allocation peak <=8 GiB per role for this first cohort.

## Exit and handoff

READY requires: physically validated eligible references on the locked
corpus; resolved or explicitly measured remaining correctness discrepancies
with no hidden scoring exclusions; executable RC/path-tracing cohort;
retained complete quality/time/memory pilot artifacts; demonstrated timing
capability; runnable commands and fail-closed preflight for Lane M. Replay
keys and direct errors need verified diagnostic conclusions/repairs, not
untested explanations. Estimator quality failures are legitimate outcomes.

Publish N010 results/index, current status/roadmap, evidence hashes/source
commits, tests/build/runtime checks actually run and a Lane M handoff. Create
a distinct `lane-m-gi-competitiveness` identity; preserve all historical Lane M
topology records. No N011 preparation lane, no power/clock changes, no CI
workflows, no changes to N001–N009 results, no default architecture promotion.
