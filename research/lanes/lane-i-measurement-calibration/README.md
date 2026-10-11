# Lane I — measurement calibration

Lane I calibrates safe timing resolution on the target host with architecture-neutral controlled GPU work. It does not compare production GI architectures.

Status: **complete — target timing unsuitable under the frozen I002 protocol**

- I001: deterministic calibration workload and harness correctness — accepted.
- I002: frozen timing protocol before accepted target timing — accepted/frozen.
- I003: target calibration — GPU timestamps resolve 5%, complete CPU wall is non-monotonic/inconclusive.
- I004: program timing capability — **target timing unsuitable** because no tested effect size is supported by both frozen timing axes.

Forced GPU power/clock state manipulation and post-hoc sample filtering are forbidden.

The GPU-timestamp result is useful mechanism evidence for a future methodology redesign, but Lane I does not retroactively make CPU wall diagnostic-only. Any later GPU-primary protocol must be frozen and calibrated in a new accepted campaign before it can support architecture ranking.
