# N010 full Renderer calibration implementation lock

Prospective implementation detail of 001; no acceptance threshold changes.
This document is frozen before calibration pilots or accepted blocks. Earlier
GPU times remain diagnostic and are not reclassified using a later pass.

An opt-in calibration-only compute stage writes a separate 16,384-word scratch
buffer. Each invocation starts from its index, executes a dose of dependent
32-bit integer multiply/XOR rounds, and writes its result. No image, geometry,
probe or sampler state is changed. Both control arms execute dose zero;
effect A executes zero and effect B executes the fixed sized dose. The stage
and its final barrier are inside the existing image-producing timestamp
interval; geometry/AS maintenance remains included in complete Renderer time.
Scratch allocations join the owned Vulkan ledger. Retain scratch payloads and
HDR images to attest extra work and any unintended image differences.

Freeze coverage: C1 and C7 static incumbent HWRT/software, native pixel PT
(T_B2 1024 spp and T_B8 1024 spp), and dense RC; plus C6/C12 HWRT and native PT
first-target geometry churn. Unsupported software churn stays explicit.
Static samples reuse one runtime in a fresh process block. Churn samples use a
fresh source runtime, execute its source frame, then measure the first target
including geometry transfer/BLAS/TLAS and invalidation. Setup/source time is
separate. No first-target costs are warmed away.

Dose sizing is a diagnostic pilot with doses 0, 256 and 1024, three repetitions
each, and median times. If the two positive-dose increments are nonpositive,
record sizing failure. Otherwise choose integer ceil(0.20 * baseline / slope)
where slope is the median positive incremental microseconds per round. Freeze
that dose in a hashed plan before accepted acquisition. Calibration targets
approximately +20% known work; observed effect is reported, never assumed.

Each boundary has eight fresh-process blocks with one-second settle; each
block retains four warmup pairs and twelve measured pairs for both identical
controls and effects. Within each pair, odd/even pair index and process index
counterbalance AB/BA. Alternate control/effect pair ordering by the same
parity. No sample exclusions or retries. Apply the unchanged 001 paired-log
median, span, order and sign rules; retain failures. Accepted acquisition runs
only after CPU reference generators and other GPU experiments have finished.
Sizing while reference work is active is diagnostic and cannot pass a gate.

This demonstrates capability only for those actual boundaries on the recorded
AMD/RADV host. Lane M must calibrate an added DDGI boundary before its accepted
performance campaign. No Lane K/L precision is transferred.
