# Post-hoc507 intake: exact native binary32 timer conversion, no GPU retry

2026-10-19 JST.150/507 native returns0 and full original image/state bytes
match, but intake FAILS raw/native image time equality. Preserve507 exactly.
The retained image query ticks differ9300 at period10.019036293029785ns:
raw binary64 replay93.177037525177us; native reports93.1770390625us.
Source184/504 dense lambda computes (uint64_delta * float_period) /1000.,
so C++ first rounds the integer/product to binary32, then divides in
binary64. Original150 compared against a binary64 multiplication. This
is a source-defined conversion mismatch, not evidence of GPU instability.

Commit before CPU replay. Require exact507 terminal return0/intake-failure
identity and all its source/payload hashes; no new native, overwrite or
partial repair. Require quiescence. Replay all original150 physical/image/
native/resource/raw-context/query/fence/phase/ledger requirements, retaining
every original row and pixel. Keep source150 trace() unchanged. Decode the
native timer independently with Python struct binary32 nearest rounding:
f32(f32(uint64_delta) * f32(period))/1000, where f32 is pack/unpack float.
This exact saved-field check uses unchanged R.close tolerances; do not
increase tolerance or replace the raw64-bit words by a rounded summary.

Keep raw binary64 complete GPU time separate from the source-defined
native display/aggregate. Record their difference, empty optional-work
timestamp overhead, actual maintenance receipts and all source expressions.
Recompute B2/B8 full-image quality/maps from eligible C7 chains with original
targets. A quality FAIL remains a reportable loss. No native image, original
JSON or GPU output is rewritten. No speed claim or precision PASS.

replay_raw_query_dense_c7.py creates509 and separate CPU score outputs at
raw-query-c7-dense-replay-v1.508 records the combined actual outcome.
CPU31/nice15/BLAS1/120CPU/180elapsed/2GiB. This is POST-HOC analysis of
the same single native, not a prospective second pilot or retry. Refuse
existing replay outputs. If replay fails retain it; no automatic following
task. Source/header/compiler paths and all science thresholds unchanged.
N010 NOT_READY, full36 and reference/physical/final-intake obligations remain.
No default graph/N001–N009/Actions/CUDA/settings change. Tests NOT RUN.
