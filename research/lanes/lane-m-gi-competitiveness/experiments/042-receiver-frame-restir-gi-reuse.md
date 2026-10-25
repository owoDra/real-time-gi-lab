# 042 — Receiver-frame SDK ReSTIR GI reuse with explicit null trials

Registered at `6d8b4438` after the user resumed Lane M on 2026-10-25, BEFORE any
042 code, test, compilation, CPU replay, GPU process or metric. 041 admits only
candidate construction/storage/recovery (6/6 conditions, 24/24 seeds). Earlier
stops/withdrawals (035, 037, 038, 040) and all M001 losses remain unchanged.

## Questions

1. Can the unmodified official RTXDI 3.1.0 GI temporal and spatial resampling
   functions run on actual M001 static targets when every stored position is
   receiver-local (041 `D=float32(t*wi)` from the owner's spawn origin `O`) and
   is converted to the current receiver frame only at the SDK load boundary?
2. Does an explicit null-trial normalization (secondary MISS = one counted
   zero-contribution trial) remove the upward energy bias predicted for the 041
   SDK-style MISS policy (MISS = empty reservoir, M=0)?
3. What all-pixel HDR quality does the configured family reach per frame (cold
   and 64-frame warm, unchanged 026 gates) and after static 64-frame
   accumulation, against the same 1spp paths accumulated by PT?

## Frozen transport, frame and normalization contract

- Producer: the EXACT 041 compiled `physical_producer.spv`
  (`m001-restir041-cpu-build-v1`, identical to 040), 1 path/pixel/frame, finite
  B2/B8 depth, grey rho=1 two-sided Lambertian, point-light NEE, black
  background. No producer source/SPIR-V change; only push-constant seeds differ.
- Frame: each reservoir slot has a parallel owner record holding the owner's
  world spawn origin `O_owner`. A DXC HLSL-2021 accessor object replaces
  `RTXDI_GI_RESERVOIR_BUFFER`; on every SDK load it returns
  `position=(O_owner-O_receiver)+D` (`precise`, origin difference first). The
  receiver is the frame origin: `RAB_GetSurfaceWorldPos(s)=O_s-O_receiver`.
  Self loads are therefore bit-identical to stored `D`. Resampled outputs are
  stored by application code in the receiver frame with owner `O_receiver`.
  SDK headers/functions are not edited; SDK stores are disabled in resampling
  shaders. Temporal history uses the previous frame's owner records and
  previous surfaces (static targets: zero motion, surfaces copied each frame).
- Units: 041 fixed SDK radiance unit 64 for Make inputs; shading divides by 64.
- Variant V1 (primary): secondary HIT = `RTXDI_MakeGIReservoir(D,n2,64*Li,pdf)`
  (black HIT kept, M=1); secondary MISS = null trial with M=1, weightSum=0,
  radiance 0, placeholder local position `n1` and normal `-n1`; no primary hit
  = empty M=0 (not a domain). Variant V0 (control): identical except secondary
  MISS = empty M=0 (041 policy). Both variants share every candidate, RNG seed,
  neighbor choice rule and parameter; only the MISS policy differs.
- Zero-contribution rule (both variants): `RAB_ValidateGISampleWithJacobian`
  accepts with jacobian 1 when the most recently loaded reservoir has zero
  weightSum or zero radiance, so its M is counted without a fabricated
  geometric Jacobian; otherwise the RTXDI FullSample rule is used unchanged
  (reject outside [0.1,10], clamp [1/3,3]).
- Target function: `luminance(radiance)*max(0,cos)/pi` at the receiver, zero if
  the sample normal faces away (`dot(n2, receiver-sample)<=0`); no visibility in
  the target. Visibility (bias correction and final shading): real HWRT ray from
  the viewing surface's world `O` toward the sample, ignoring that surface's own
  primitive, `tmax=dist*(1-1e-3)-eps`, `eps=1e-5*max(1,scene diagonal)` (022
  camera epsilon); `tmax<=0` counts visible. Final shading:
  `direct + [hemisphere AND visible] radiance/64*cos/pi*W`.
- Parameters: RTXDI library defaults (temporal depth .1, normal .6, history 8,
  age 30, fallback on, permutation off; spatial 2 samples, radius 32, depth .1,
  normal .6) except bias correction RAY_TRACED for temporal and spatial (the
  SDK's unbiased-capable mode; BASIC not run). 8192 neighbor offsets are the
  qualified 033 `neighbor-offsets.u8` bytes decoded as SNORM. Boiling filter,
  sample-app final MIS and checkerboard are NOT_RUN limitations.

## Execution

Six targets in fixed order H01/B2, H01/B8, H02/B2, H02/B8, H03/B2, H03/B8 using
the admitted 022 state captures. One GPU process per target runs 4 independent
streams x 64 frames, both variants. Stream s/frame f producer seed
`((0x0a420000+64s+f)*0x9e3779b1 mod 2^32) xor 0xa042a042`; SDK frameIndex
`4096s+f`; history reset at each stream start. Per frame: producer (450
128-pixel dispatches, as 041), initial, temporal V1/V0, spatial V1/V0, shade
V1/V0, previous-surface copy, one fence (250 ms guard), timestamps per pass.
Every frame reads back direct, PT 1spp indirect, V1 and V0 indirect. Full-record
frames {0,1,63} of every stream additionally save candidates, local endpoints,
primary hits, surfaces, history-in, initial/temporal/spatial reservoirs and
owners for both variants, and shading records. Native 8 GiB owned cap,
180 s wall guard, true-peak/zero-teardown ledger as 041.

## Audits and stop rules

CPU preparation (before any GPU): new native compile/link, HLSL compile/
validate/disassemble for each stage, new Python contracts (transform exactness,
null-trial counting, zero-contribution rule, CPU replay of the SDK temporal and
spatial functions on synthetic fields, RNG/offset/address replay, visibility
model), six actual unusable-ICD native input checks. Any failure stops before GPU.

Per target, the numeric worker (CPU1200/wall1800/4GiB) checks all frames
(finite/nonnegative images, bit-identical primary direct across all frames and
streams) and fully replays every full-record frame on CPU: initial reservoirs,
temporal and spatial resampling and final shading for both variants, with
independent brute-force float64 ray/triangle visibility for every visibility
query. Transformed positions must be bit-exact to the float32 replay of the
registered expression. A replay divergence is admitted only when classified
near-boundary (relative decision margin <=1e-5, or a visibility verdict that
flips under tmax x(1+-1e-4)); unexplained divergences must be 0 and explained
ones <=0.1% of valid pixels per frame/variant. First implementation, native or
audit failure stops 042: later targets NOT_RUN, no retry. Quality losses never
stop the cohort.

## Prespecified quality and bias decisions

References: the six admitted 16384spp four-seed means (luminance), unchanged
full-image gates: total NRMSE<=5%, indirect NRMSE<=10%, |indirect signed bias|
<=5%, no exclusions.

- Q1 (026-compatible, V1): a stream passes if frame 0 (cold) AND each of frames
  48-63 (warm) pass; a target passes only if all 4 streams pass.
- Q2 (static accumulation): per stream, the mean of frames 0-63 for V1, V0 and
  PT (64spp, same paths) scored with the same gates; NRMSE ratios reported.
- B1 (null trial): pooled indirect signed bias over all 256 frames per variant;
  H_null holds on a target iff bias(V0)-bias(V1) > 3 x its standard error across
  the 4 stream means. Prediction: holds on 6/6.
- B2: |pooled V1 indirect bias| <= 5% per target, reported beside PT's pooled bias.

All timings are diagnostics; no accepted speed, memory advantage, novelty or
architecture claim. A quality-matched pair, if any, only permits a separately
registered calibrated timing study. Power/clock settings, default Renderer,
N-series history and CI are untouched. All outputs stay under
`out/research/lane-m-gi-competitiveness/m001-restir042-*`; results, failures and
limitations are published and Issue #7 updated. Full Lane M remains incomplete.
