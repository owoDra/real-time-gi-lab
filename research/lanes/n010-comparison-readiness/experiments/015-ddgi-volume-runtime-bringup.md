# N010 DDGI Vulkan volume bring-up

Prospective diagnostic before this adapter's first GPU dispatch. Pinned SDK
and CPU shader evidence are 021/023/034/038/056. This does not begin Lane M
accepted comparisons or alter the N010 RC/PT gate.

Build a separate, unlinked executable with app-owned Vulkan images/buffers,
the existing allocation ledger, and the official unmanaged volume API.
Require an AMD physical GPU, supported storage-image features and subgroup
configuration, successful official SDK creation and dispatch, retained raw
readback bytes, and zero owned allocations at clean teardown. Never use a
software fallback or CUDA. Existing GPU binaries and shader directories remain
untouched; refuse concurrent image producers before execution.

Use one 2×2×2 volume, 128 rays/probe, irradiance 6×6 interior/8×8 including
border, distance 14×14/16×16, FP32 resources. Disable relocation,
classification and variability for this first adapter dispatch; provide
genuine modules/pipelines for all unmanaged resources required by the SDK.
Fixed RNG seed 305419896. Gamma=1, hysteresis=0, brightness threshold=1e6.
Those diagnostic values are not a Lane M selected configuration.

Two independent clears/updates: all ray RGB=0 or RGB=1, all ray distances=1.
The official blending normalization predicts stored irradiance RGB=0 or 0.5
and distance moments RG=(0.5,0.5). Require every texel/component finite;
irradiance RGB absolute max error ≤1e-5, distance RG ≤1e-5, including borders.
Retain both controls and any failure; no excluded pixels or adjusted tolerance.
This verifies volume resource/dispatch/normalization wiring. It contains no
scene tracing, finite-depth GI, surface gather or temporal regime and cannot
qualify a DDGI renderer, a physical reference or a performance comparison.
CPU-loaded elapsed/timestamp data, if any, remain diagnostic only.
