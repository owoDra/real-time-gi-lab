# 043 — ReSTIR GI reuse frames through the fixed quadratic reconstruction (CPU screen)

Registered after 042 publication `7e68617b`, BEFORE any 043 code, test,
reconstruction or metric. 042 per-frame and accumulated scores are known; no
043 reconstruction output has been computed or viewed.

## Question

042 shows ReSTIR GI V1 (explicit null trials) lowers warm per-frame indirect
error about 3x versus 1spp PT, yet fails every gate. 018/022 show the fixed
geometry-only quadratic reconstruction passes all six targets from 16-64spp PT.
Does the UNCHANGED reconstruction applied to 1-path-per-pixel ReSTIR frames
meet the unchanged gates per frame (cold and warm), and how does it compare with
the same reconstruction applied to the same frames' raw 1spp PT and to their
64-frame static means? Known regression prior art; no novelty claim.

## Frozen inputs and operator

- Images: the published 042 per-frame readbacks (`m001-restir042-*-v1/capture/
  stream-s/frames.f32`): direct, PT 1spp indirect, V1 indirect; V0 is not used.
  Rehash all 042 receipts/payloads first. No new rendering, path, seed or GPU.
- Operator: the archived 022 GPU-fitted coefficients (`m001-integrated022-gpu-
  <target>-v1/capture/coefficients.f32`, 3x25x180x320, rehashed against the 022
  receipt) applied by the unchanged 018 `surface_quadratic_filter.reconstruct`
  (strides 1/2/4, 25 taps, signed coefficients, negative clipping between
  passes, no upper clamp, no history). Precondition: 042 primary hits of every
  stream's record frames are bit-identical to the 022 capture `hits.u32`;
  otherwise the coefficients do not apply and 043 stops INVALID.
- total = unchanged direct + reconstructed indirect. All 57,600 pixels, unchanged
  references (16384spp four-seed luminance means) and gates: total NRMSE<=5%,
  indirect NRMSE<=10%, |indirect signed bias|<=5%.

## Prespecified evaluations (per target, all 4 streams)

- R1 (primary, 026-compatible): reconstructed V1 frame 0 (cold) and each of
  frames 48-63 (warm). A stream passes iff cold and all warm frames pass; a
  target passes iff all 4 streams pass.
- R1-PT (comparator): the same for reconstructed raw 1spp PT frames.
- R2 (static accumulation): reconstruction of the 64-frame mean of V1 and of PT
  per stream (PT mean = 64spp, the 018 rung that passed); pass counts.
- RB: the same coefficients applied to the reference indirect (reference-bias
  diagnostic, as 018/022).
Prediction stated before execution: R1 fails on most targets (V1 is roughly
9-12spp-equivalent noise and spatially correlated; 018 needed 16-64spp); R2
passes for both V1 and PT on most targets.

## Process, decisions and stop

CPU only: new contracts (coefficient/hit ABI, constant-preservation and clipping
of the reused filter on synthetic fields, exact equality with the 022 final
image when applied to the archived 022 source) run under C.guarded CPU120/
wall180; one supervised numeric worker CPU1200/wall1800/4GiB evaluates all six
targets in fixed order and saves every score and complete per-target error
summaries. First precondition/implementation failure stops 043 without retry.
No parameter, coefficient, rung, frame window or gate tuning.

If any target passes R1, a separately registered GPU-integrated pipeline with
full costs and calibrated matched-quality timing may follow; R1 failures stop
this per-frame route. Static accumulation results are convergence diagnostics,
not real-time claims. No timing, memory, novelty or Lane M completion claims.
