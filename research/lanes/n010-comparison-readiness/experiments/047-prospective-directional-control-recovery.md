# Prospective recovery of user-interrupted directional controls

Date: 2026-10-15 JST. Parent checkpoint: `bf87f77`.
Registered after the operational stop 161, before any recovery acquisition.
GPU calibration 158 is running; no CPU acquisition may overlap it.

## Retained evidence and fixed boundary

Plan-043 physical 152 was user-interrupted, not a completed scientific failure.
It contains seven complete passing scene exports and an unfinished A6a row.
Its immutable SHA256 is
`a891a103476d2f8ac1e8840275f55b11303d79fec0042ac3d57e173ad67cc0c8`.
Stop 161 is
`08fb9b7821efebe5075afbb27d41e51e7977a6bd562819eea6747b517c4d22ff`.
Both old work directories, 152 and its stale controller status stay unchanged.
No old controller, native invocation or original output path is restarted.

Retain precisely A10, A2, A2b, A4a, A4b, A4c and A4d: every complete scene
before interruption, without selection by radiance or a new score. Verify all
152 inputs, their complete four-seed exports, original native commands and
all 161 preserved file identities. Copy those seven scenes byte-for-byte into
a fresh recovery directory, record original commands and explicit import
origin, and rerun all original numerical/header/direct/primary/counter checks
on the copies. Imported rows are not new native executions.

Acquire the other ten fixed scenes once in that fresh directory, beginning
with A6a, using the same binary, scene bytes, four seeds, spp and resource limits.
Do not import A6a partial samples or moments. The complete numerical and eight
physical checks plus both retained iid comparisons must cover all seventeen
scenes. No change to the estimator, proposal, thresholds, exclusions or seeds.

## Separate ordered artifacts

1. Recovery physical 163 uses `primary-direction-physical-recovery-v1`.
   Its seventeen rows distinguish the seven imported native commands from
   ten new invocations. A completed FAIL stops the candidate without retry.
2. Only complete 163 PASS permits fresh state/prefix 164 in
   `primary-direction-prefix-proof-recovery-v1`: all 24 low-dose states, both
   actual C7 transports, all 78 native invocations and the exact original gates.
3. Only complete 151/163/164 PASS permits fresh bounded feasibility 165 in
   `primary-direction-feasibility-recovery-v1`: four-seed C1 B8 at 8192/16384,
   own exact prefix, original-cosine baseline and <=0.75 ratios at both levels.
   All plan-043 uncertainty/support, resource, deterministic and stop rules apply.

Use guarded source adapters; retain frozen 151, 152 and all original programs.
Record this plan, each adapter/helper, original sources and proof inputs.
The old 153/154 paths remain unexecuted rather than being populated by a
different attempt. No automatic waiting/restart worker is installed.
Each new entry point refuses existing output/work and other research workers.
Execute only after actual termination of 158 and other research computation.

Plan-046's sixteen retained eligible references, fixed eight pending targets
and full 24-slot map stay unchanged. A future explicit intake adapter must
validate the new 163/164/165 proof chain and actual native/import provenance;
the old API still refuses incomplete 152. Neither recovery construction nor
complete controls alone admit a new reference. All six readiness gates remain.
Direct max-relative-error-1.0 pixels remain UNRESOLVED / 未解決 and included.
No N011, CUDA, Actions, power/clock change, active Renderer promotion or
N001–N009 result modification.
