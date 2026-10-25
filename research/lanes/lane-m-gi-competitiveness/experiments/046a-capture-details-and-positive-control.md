# 046a — Capture details and positive control, before any M002 GPU run

Prospective addendum to 046 (`f4e9434e`), after the CPU states/lock were
written and while references are being qualified, BEFORE any M002 GPU capture,
build, calibration or metric.

- Capture mode: one role sample in a fresh process, seed jenkins(0x0a440000)
  (the first sample seed of the harness); PT uses min(64, spp)-spp chunks
  averaged by the accumulation pass; PTR is the unchanged 022 sequence; the
  image file holds direct and indirect float32 per pixel (total = direct +
  indirect in float64 at scoring).
- Positive control (must pass before any M002 target capture): on M001 H01/B2
  with its admitted 16384spp reference, capture PT 256spp and PTR 16spp; both
  must meet all three gates, as M001/022 established for those rungs. A failure
  stops M002 as an implementation failure (no retry). This control uses
  observed M001 data and is not M002 evidence.
- Timing campaigns allow PT rungs 16/64/256/1024 and PTR rungs 4/16/64 so the
  first-pass rungs of new targets can be timed; decision rules are unchanged.
