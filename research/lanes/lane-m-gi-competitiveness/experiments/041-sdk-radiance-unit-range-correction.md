# 041 — Diagnose codec range and qualify a fixed global radiance unit

Registered after040's immutable236–239 stop, before041 diagnostic/code/test/
compilation or GPU work.040 H01/B2 andH01/B8 full candidate checks pass; H02/B2
first seed fails the unchanged2% raw-RGB codec gate. Later three conditions are
NOT_RUN. No full040auditor rerun or040retry. The suspected SDK low-end LogLuv
range issue must be verified from frozen actual outputs, not assumed a diagnosis.

## CPU diagnosis and independently fixed numerical correction

ONE supervised CPU1200/wall1800/4GiB numeric worker first diagnoses all four frozen
040 H02/B2 outputs, all57,600pixels each. Recompute only actual packed RGB decode,
unchanged error gates, original grey suffix range and every failed pixel/codec
word; save complete arrays and all failures. Do not call the full040auditor or
relabel any seed fully audited. Pin complete original inventories/processes.

The proposed correction is ONE GLOBAL physical radiance unit C=64, applied to
all conditions/depths/seeds without per-pixel exposure/tuning. The exact pinned
SDK Color.hlsli defines LogLuv's black floor near2^-20 and upper range near2^20.
The existing per-channel2% error budget has absolute floor .02*1e-6=2e-8.
C=2^ceil(log2(2^-20/2e-8))=64 makes even decoded-black original radiance less
than2^-20/64<2e-8. The finite unit-grey suffix bound is(B-1)/pi<=7/pi; times64
is<143, far below2^20. This is an analytical unit/range choice made BEFORE
diagnostic metrics, not a choice fitted to failed values. Source proposals,
original radiance/physical references and all thresholds remain unchanged.

CPU phase must establish every actual codec failure is within the SDK low-end
range and no unexpected normal/weight/position/data corruption is implicated
by those codec words. Decode actual saved words independently. Implement a CPU
reference encoder/decode check on all four saved RGB arrays plus every valid
LogLuv luminance-bin boundary within[0,7/pi] in original units underC64, its two
adjacent float32 values, zero/subnormal,1e-6floor and7/pi endpoints. Save all grid
values/errors/failed masks, not just extrema. Require all original gates under
C64, finite intermediates and no upper saturation. Add eight new CPU contracts
for codec floor/scaled black, black HIT/empty, power-of-two unit roundtrip,
uncompressed physical shading invariance, fixed-grey HDR bin boundary behavior,
upper finite-depth bound, unexpected failure classification and exact reversible
shader/unit-model derivative. No successful old suite/native input test rerun.
First diagnostic/provenance/process/test/range failure stops041 before GPU.

## GPU representation and comparison

Only the SDK boundary changes: Make receives Li*64; packed storage retains SDK
units, and BOTH pre-pack and loaded/decoded shading divide final indirect by64
before adding original primary direct once. SDK weight/PDF/M/age/position/normal
are unchanged; physical MISS M0/black HIT M1/raw trial1 remain. CPU full model
compares decoded packed radiance/64 against original Li with EXACT original
2% floor and all040 uncompressed/local/geometry/packing/final gates. Global
scaling must be identical for every history/candidate; future target PDF/weights
and history units require separately qualified reuse. No resampling/HDR family
quality, checkerboard/history/dynamic or arbitrary unbiasedness admission here.

Reuse exact successful040 host/executable/physical producer/original022 SPIR-V,
bounded objects and six native CPU input receipts. No native/GLSL rebuild or
old successful tests repeated. Build/validate/disassemble only two new HLSL
variants with an exact reversible Li*64/shade/64 overlay. SDK source is unchanged.
New process/full-audit/unit-model/tests committed BEFORE use. Rehash040 compiled
dependencies and every successful/failed artifact including complete040failure.

After CPU diagnosis AND range/tests/compile qualification PASS, execute one new
pipeline per six conditions H01/B2,H01/B8,H02/B2,H02/B8,H03/B2,H03/B8 in order.
Reuse SAME040 seeds XOR0xa040a040, four one-SPP images per condition, as an
explicitly controlled changed-unit comparison; do not label streams independent
or old failed acquisition as new pass. Each process freshly traces original/
observed physical paths, then actual SDK Make/Pack/Load in GPU memory. No CPU
candidate/image replay, reference sampling or hidden native/path reuse.
All cases require full actual native AND supervised numeric PASS before next.
All earlier failures remain; first041 failure stops without retry or later case.

Use unchanged C.guarded for actual HLSL/test children CPU120/wall180/4GiB, actual
native CPU120/wall180/4GiB and numeric CPU1200/wall1800/4GiB, core0/default
unblocked SIGXCPU, BLAS/OMP1. Worker never lowers inherited1200 to parent360.
Parent C.limits; commands before launch/child limits/PID/timeout/reaped/exit
receipts mandatory. Native8GiB/180s/250ms/128pixels/2ms guards unchanged; full
AS/scratch/staging/pipeline ownership/true peak/zero teardown and original timing
boundaries retained. Timings are diagnostics only;022 raw-PT-only speed ban stays.
Exclusive out/m001-restir041-* roots,16GiB free, same quiet qualified GPU; announce
each exact single command. Power/clock/default Renderer/N-history/CI untouched.
Publish all outcomes, complete arrays and preserved evidence/index/link checks,
commit/push/update OPEN Issue7. Full novel-transport/fair-family/HDR/new-heldout/
dynamic/multi-device/deployability/full-cost/memory charter remains incomplete.
