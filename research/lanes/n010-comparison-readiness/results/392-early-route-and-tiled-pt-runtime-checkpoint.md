# N010 runtime checkpoint: localized counter repair and stopped tiled PT

2026-10-18 JST; source0325435b. N010 NOT_READY, references16/24.
No unit/regression tests; default build and N001–N009 results unchanged.

## Original CPU260 terminal

[260](260-wide8-original-a6a-seed1.json) completes original A6a seed1,
2596069104,128x96/8192spp, exit0,5204.821257CPU/5228.693009elapsed seconds.
Actual CPU31/nice15/4GiB,7200CPU/10800elapsed limits; original deterministic
and primary bytes exact,704643072 own checks, own-log maximum1.00798e-8.
This is seed integrity only: A6a has two of four original seeds, not an
admitted physical artifact or reference. Inventory remains14/17 including
one diagnostic-only item. PID10159 is terminal; no next seed was queued.

## Post-hoc119 diagnosis: same pixel restores all registered counts

[381 build](381-early-density-route-build.json), [382 old](382-early-density-route-old.json),
and [383 guarded](383-early-density-route-guarded.json) complete the frozen
119 manual sequence. Original360 SPIR-V reproduces pixel43665's corrected
aggregate[16,52,4,0] versus CPU[16,53,4,0]; proposal queries942 versus944.
The separately built candidate restores every one of16 independent CPU
sample scored counters and aggregate proposal queries944, attempts112,
nulls20 and own checks92. Component maximum error3.2959746043559335e-17.
Old/new raw GPU path records are bit-identical: the observed repair comes
from delegating the flagged original sample to unchanged CPU logic.

Sample9 changes corrected shadow count1 to2 with routing flag8. At depth2
its telemetry reports early-site mask1 (prefix PDF) and one nonpositive
branch. This is observed coverage of an early PDF branch before the old
small-density routing check. The exact floating ray/cosine/PDF operands are
not retained, and no individual ray's geometric cause is proved. This pixel
reproduces the same one-shadow/two-query deficit seen globally; possible
compensating query differences elsewhere have not been excluded.

Both probes own peak89,941,232bytes, zero teardown. Old native0.925707s,
guarded1.138462s; diagnostic single runs only, no performance conclusion.
Candidate audit retains unconditioned error fraction221087782.5472765;
119/115 register no cut for that diagnostic value. Conditioned fraction
0.00717425, own-log bound2.84217e-14 and max weight6 meet unchanged cuts.
Do not hide the large unconditioned value or infer globally negligible bias.

All119 records deliberately keep all_pass/accepted_timing/reference_admission
false; step_valid refers only to their diagnostic integrity. Original372
remains FAIL and373 is absent. Candidate full-frame/all-state/physical/
prefix/full-count proof remains required; no larger GPU task was queued.

## Private PT390 builds; first C1 capture fails and stops123

[390](390-tiled-pixel-pt-build.json) compiles/links the three private stages,
using original inputs and explicit isolated shader path, no default graph.
Source389 inverses remain exact; compilation is not numerical acceptance.

[395](395-tiled-pt-first-capture-failure.json) preserves the exact local C1
part record from123. Native53587 exits1 after0.671375s/0.102508CPU seconds;
stderr is `Vulkan operation failed`. No tile timestamp completed, frames.json
is partial, no full image or byte comparison exists. Actual native limits
are120CPU/180elapsed, CPU31/nice15 and explicit unlimited Vulkan virtual
address space. Ledger peak105,517,152bytes; teardown is NOT zero,921,728bytes
remain in the exception path. This is a failed capture, not accepted memory.

The generic error does not identify a Vulkan call or VkResult; attributing
it to the500ms fence guard, device loss or driver behavior is unproven.
Read-only kernel journal query for recent amdgpu/reset/timeouts returned no
entries; absence of a log is not proof of device health. C7 was NOT RUN,
no retry or monolithic recapture, and successful391 is absent. Preserve all
partials; diagnose the call/result before another PT capture or policy change.

Sponza original direct max-relative-error1.0 pixels remain **UNRESOLVED /
未解決**, included and distinct from this repaired single-pixel counter case.
Timing amendment120 remains prospective: valid uncertainty may be
INCONCLUSIVE, missing/invalid evidence still blocks handoff. Final auditor,
full references, quality/dynamics/memory and selected-boundary pilots remain.
