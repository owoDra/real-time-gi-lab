# N010 tiled PT numerical replay — native policy and evidence intake

2026-10-18 JST; follow-up to122, parent3e4a4087. Commit this policy and
the exact driver before native execution. No new numerical threshold.

Execute `replay_tiled_pixel_pt.py --cell C1` and, only after a valid C1,
separately invoke `--cell C7`. Each invokes exactly one static PT-B8/1024
image, seed305419896, tile64/pause2000us, at the immutable046 state paths.
No automatic second capture, retry, old monolithic capture or GPU campaign.
Plan119 remains the next GPU task after original260 terminates with integrity
PASS. Require119's manual diagnostic steps to be terminal before this route;
a failed119 step is retained and must be reviewed before dispatching here.

## Resource policy

One native process group, CPU31/nice15,120CPU/180elapsed seconds. Keep
RLIMIT_AS unlimited explicitly for the Vulkan driver's virtual reservations;
virtual address space is not owned GPU memory. This does not change any
hardware, power, clock, display, driver or other application's settings.
The immutable state/budget and original allocation behavior remain fixed.
Replay every owned Vulkan allocation/free event, including startup, scratch,
frame and readback lifetimes; true peak must be positive and<=8GiB, with
zero live bytes at teardown. This ledger excludes driver-private and CPU
memory. Record actual limits, affinity, priority, PID/start/boot/PGID,
process CPU/elapsed cost, stdout/stderr, environment and all payload hashes.
No worker overlap. Require2GiB free disk; retain partials on any failure.
Only the invocation's new process group may be killed on elapsed timeout.
Keep122's tile250ms/fence500ms/image180s operational stops; no adaptive retry.

## Exact validation and final391

Pin390's exact source/build inputs and outputs,389 and046. Read the archived
046 frame0 state and three PFM payloads and verify their recorded hashes.
Compare each candidate top-level AND frame0 direct/indirect/total PFM to
the complete archived bytes. Verify frame-state/geometry-state copies match
the immutable original state and046. No scoring exclusions or tolerances.
Require exactly one static frame, original dimensions, family/budget/seed,
zero maintenance/dose/changed geometry, and tile64/pause2000 metadata.
Replay every tile's contiguous pixel range and complete coverage, seed,
image index, actual timestamp bits/period, modular tick duration and image
envelope. Require finite positive durations<=250ms and consistent active
sum/envelope/maximum and complete frame cost; never compare old/new timing.

Write each immutable local part under`tiled-pixel-pt-numerical-v1/C1|C7`.
Refuse an existing part. `--summarize` performs no native work and independently
replays both retained captures, resource receipts and hashes before writing
result391 once. It cannot accept a saved success boolean as numerical proof.
A failed first part prevents the second. A failed second part remains a
negative outcome; do not overwrite it or publish a successful391 summary.

All parts and391 keep`all_pass=false`, `accepted_timing=false` and
`reference_admission=false`; a dedicated`numerical_replay_valid` records only
this exact two-state implementation equivalence. This is no physical oracle,
all-budget/dynamic proof, performance result, memory proof for other roles,
reference qualification or N010 READY. N001–N009 results and unresolved
Sponza direct-relative1.0 pixels remain unchanged. No tests or default build.
