# Material-token repair020: six native float32 CPU targets pass

2026-10-24. **REPAIRED_HOST_CPU_COHORT_PASS,6/6**; actual GPU execution NOT_RUN.
[Preregistration020](../experiments/020-surface-quadratic-material-abi-repair.md)
was committed/pushed at70ebae2e before code/build/new CPU attempts. Exact actual
code428bd6b4 precedes the first repaired build and all six attempts.
[Preparation121](121-surface-quadratic-material-abi-cpu-preparation.json) and
[full raw replay122](122-surface-quadratic-material-abi-six-cpu-targets-raw-replay.json)
pin the new host, original shader and every old/new source/input/output identity.

The private loader overlay changes exactly one predicate: material word5accepts
all32-bit tokens; primitive/instance words4/6must still be valid. Byte-exact
inverse reconstruction recovers019scalar source. Host/header/shared shader
bytes remain exact. Original canonical metadata equality is checked in intake;
material mismatches are rejected. No material remap, sampler, radiance input,
numeric/image threshold or reconstruction algorithm change.019remains stopped;
its failed first input attempt and synthetic-fixture coverage gap remain in119.

New host compiles under ordered float math/UBSan.19actual native CLI contracts
and16canonical/overlay/frozen-derivation contracts pass with an unusable ICD.
Material0,UINT32_MAX,and0x80000001give byte-exact single-hit math; invalid
primitive/instance, flags/normal/depth/miss/source/camera and existing outputs
are rejected before Vulkan, including GPU CLI negative paths. Obsolete019
material-sentinel rejection is not carried forward as new host qualification.
Unchanged shared-kernel/SVD/shader evidence is rehashed, not identically rerun.
The numerical auditor is exactly019with study labels/import binding changed;
eight protected runner functions retain their original AST after label change.

Six one-time native CPU rehearsals in H01/B2,H01/B8,H02/B2,H02/B8,H03/B2,H03/B8
order complete without timeout. Each independent full-field terminal audit
passes and is pinned in every later native plan before selection. Six separate
CPU captured-geometry replays independently evaluate actual shared float32 math;
all masks/model/rank integer fields match exactly and full coefficients pass
the prospectively fixed health bounds. No GPU/primary/PT/reference path ran.

|Target|Fixed selected noisy spp|Selected indirect NRMSE|Reference-reconstruction indirect NRMSE|Target|
|---|---:|---:|---:|---|
|H01/B2|16|8.459498%|0.922537%|PASS|
|H01/B8|64|5.429742%|1.264419%|PASS|
|H02/B2|64|5.923170%|1.872155%|PASS|
|H02/B8|64|6.710647%|2.491904%|PASS|
|H03/B2|64|6.807888%|0.603104%|PASS|
|H03/B8|64|8.010577%|1.473296%|PASS|

All original inclusive total<=5%, indirect<=10%, absolute indirect bias<=5%
full57,600pixel/no-exclusion gates apply. Both selected noisy and separate
reference-bias rows must pass. All24noisy rows remain:7PASS,17losses; all6bias
rows pass. The original admitted references remain unchanged/unfiltered.
All geometry positions/oriented normals match independent ordered NumPyf32
reconstruction exactly; unit-normal bounds pass. No model/rank/tap changes
from018are observed. These are observed-development one-seed CPU image
feasibility results; they do not establish robustness on unseen data.

All84native and114terminal-audit payloads rehash, including
270complete preclip/clipped/error arrays and every geometry/coefficient/integer
map. Independent double/SVD checks cover1272
hit coefficient vectors and1032analytic miss
vectors;23040preclip/clipped pixel
comparisons and independent fsum all-image RMS/bias checks pass. Maximum SVD
coefficient absolute error3.0513355838701628e-06;
maximum SVD stage error normalized by preceding-stage maximum
6.9250291303730928e-07. Signed coefficients and all negative
preclip counts/minima/energies remain recorded; no field correction or exclusion.

This qualifies the repaired actual host/input/float32 CPU boundary only.020ends
here and authorizes zero GPU processes. A separately frozen one-process GPU
plan/intake/ordering/failure test gate is needed; reuse these successful receipts
without repeating the cohort. Actual device fitting/filter correctness and
<=8GiB owned peak/zero teardown remain unmeasured for this component. Archived
013exports and original PT images exclude integrated new tracing/dynamics/full
costs. No accepted GPU time/speed/memory, architecture or Lane M completion.
Audited GPU total stays120; no power/clock/desktop change, CI/Actions or default
Renderer integration. Default build/runtime regression NOT_RERUN; validation
layers NOT_RUN. [Verification124](124-surface-quadratic-material-abi-cpu-verification.json)
records preservation and link scope. Broader fair denoised families, independent
heldouts/dynamic/Sponza/multiple-device and novel architecture gates remain open.
