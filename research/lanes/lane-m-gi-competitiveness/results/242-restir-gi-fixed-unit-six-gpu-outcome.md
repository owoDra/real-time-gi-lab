# 041: all six actual local physical SDK candidate constructions pass

**RAY_PARAMETRIC_FIXED_UNIT_GPU_CONSTRUCTION_PASS:6/6conditions,24/24seed images.**
Actual GPU-produced original finite-path suffixes pass through unmodified pinned
RTXDI Make/Pack and a separate GPU Load/Unpack/shading dispatch. Receiver-local
D=float32(t*wi) preserves original sampling/PDF; one GLOBAL64 radiance unit
keeps low positive suffixes within SDK LogLuv range. Final images and CPU/HDR
references stay in original physical units. This is candidate construction,
not ReSTIR spatial/temporal reuse, HDR quality, competitive transport or speed.

| Condition | Fully audited seeds | Secondary HITs | Old absolute-direction failures retained | Owned peak bytes |
|---|---:|---:|---:|---:|
|H01/B2|4/4|5479|2|31403632|
|H01/B8|4/4|5479|2|59051632|
|H02/B2|4/4|4475|1|31403632|
|H02/B8|4/4|4475|1|59051632|
|H03/B2|4/4|5725|9|31412784|
|H03/B8|4/4|5725|9|59060784|

Registration041/7eb7af4f and exact-black-bin addendum041a/6f379d55 precede all
implementation1eab5504/data/tests.041a resolves the BEFORE-execution analytical
imprecision in the original black-bin bound: actual Y0=2^(-20+1/409.6), not
2^-20. C=64 is unchanged; Y0/64<1.50e-8<the original2e-8 floor, and64*(7/pi)<143
is far below the codec upper range. No measured threshold/seed-based selection.

[Preparation240](240-restir-gi-fixed-unit-cpu-preparation.json) retains ONE actual
CPU1200/wall1800 diagnostic/range worker, eight new CPU contracts and two new
HLSL compile/validation/disassembly sequences. All63 frozen040H02/B2 codec
failures are explained by positive radiance encoded as black; no unexplained
normal/position/weight/M corruption. All230,400saved source pixels and33,374
neutral-grey luminance-bin boundaries/adjacent float32 values pass the unchanged
codec budget underC64; maximum critical-grid budget ratio0.438109282.
Full arrays/every old failure retained. This targeted diagnosis does not rerun
or re-admit040. Exact040 native executable/GLSL/022objects and six successful
CPU input receipts are reused without recompilation/repetition; only SDK input
Li*64 and BOTH shaded indirect outputs /64 differ. Source references and original
PT arithmetic, BRDF, PDF, finite depth, MISS M0/black HIT M1/raw trial1 stay exact.

[Six GPU results241](241-restir-gi-fixed-unit-six-gpu-conditions.json) bind six
fresh ordered native processes using the SAME040streams for a controlled unit
comparison, not independent new streams or relabeled old acquisitions. Each
previous complete native/numeric PASS gates the next. All2,764,800new camera/path
trials across both roles,6,912,000allocated observed vertex slots,1,579,382
actual observed queries,31,358secondary HITs,142,586secondary MISSes
and5,654black HITs are accounted for. All43,200 bounded units complete.

All original/observed PT/primary/source arrays are bit-exact. Full original
vertex/triangle/RNG/normal/front/spawn/direct/suffix, local t*wi and represented
world same-triangle geometry, source PDF, status/M/raw trials, real-BVH generated
segment visibility, oriented hemisphere, packed position/normal/weight/age/zero
padding and before/after-packing image recovery checks pass unchanged tolerances.
The old world H-O diagnostic still fails at24pixels; these exact
full fields remain saved. The actual SDK local direction passes the SAME3e-4/
3e-6 component gate. Maximum uncompressed recovery error1.1641532182693481e-10; maximum
packed error6.521295290440321e-06. No candidate drop, fake finite MISS, direction/PDF
substitution, extra1/r²/BRDF/bounce or primary-direct double counting.

All22 actual041 child envelopes are independently verified: one range worker,
nine test/HLSL steps, six native CPU120/wall180 and six numeric CPU1200/wall1800;
4GiB/core0/default unblocked SIGXCPU, actual PID/reaped exit0/no timeout. Full
owned AS/scratch/staging/pipeline lifetimes cover21allocation/free pairs per
native, max59,060,784bytes true peak and zero teardown.
Driver-private and CPU memory excluded. Startup/upload/AS/pipelines, all unit
timestamps, full fence/pause envelopes and readback remain saved diagnostics.
No matched timing or memory advantage. No CPU candidate/image/primary upload or
intermediate readback; only physical scene/camera/constants are uploaded.

[Verification243](243-restir-gi-fixed-unit-verification.json) checks old source/
results/protocols, raw inputs/payloads, actual process guards, current index/links
and unchanged active build graph.037/038/040remain stopped;035remains withdrawn;
036admits CPU double extraction only. Default Renderer build/runtime NOT_RERUN;
validation layers NOT_RUN. Six new GPU acquisitions bring total196. No power/
clock/default Renderer/N-history/CI changes.

Per-receiver local positions CANNOT be mixed directly for spatial/temporal
resampling. Next qualify explicit source-to-destination frame transforms,
actual current/previous surfaces/motion/reset/checkerboard/visibility, global
history radiance units and full persistent/peak ownership in a real image
pipeline. SDK physical MISS M0 versus raw-trial denominator must stay explicit;
this construction does not establish arbitrary reuse unbiasedness. Then fair
cold/warm all-seed HDR family quality and complete calibrated costs are still
required;022 prohibits accepted raw-PT-only speed rankings. Novel competitive
actual Renderer transport, independently NEW heldouts, camera/light/rigid/
deforming/topology/churn, broad scenes/Sponza, multiple GPU classes/software
fallback/deployability and full memory gates remain open. Lane M is NOT complete.
