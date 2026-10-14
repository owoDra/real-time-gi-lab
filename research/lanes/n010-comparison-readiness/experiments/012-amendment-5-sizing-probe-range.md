# N010 Amendment 5 — adequate known-work sizing probes

Prospective after 027/028 diagnostic failures, before any accepted process
blocks. Keep both failed sizing datasets. Inner timestamps in Amendment 4
remain, and all full Renderer acceptance gates are unchanged.

At small 256/1024 doses, two inner increments in 028 were nonpositive; two
heavy PT boundaries required a sized dose above the implementation's ten
million-round ceiling. These are execution/sizing failures, not evidence of
measurement capability. Use the fixed nine-sample diagnostic schedule
[0,65536,262144] repeated three times to obtain increments above timer/dispatch
variation. The same positive-slope requirement and +20% sizing formula apply.
Raise only the calibration round-count safety ceiling to 100,000,000; do not
change image transport, sample budgets, reference or timing decision thresholds.
Never accept a negative slope or silently clamp the dose. Record a cap failure.

Memoize independent CPU uint32 expected values for known-work witness indices,
since repeated equal doses must have equal scratch bytes. Use a compiled CPU
verifier for large doses; it implements the shader's exact unsigned operations.
These diagnostic checks are outside the timed boundary. Shader hashes, as well
as host binary hashes, must match the frozen sizing plan in every accepted
block and the current handoff, with all captured HDR components byte-identical.

A later quiet sizing acquisition is identified separately; diagnostic CPU-loaded
sizing is not reclassified into an accepted timing campaign.
