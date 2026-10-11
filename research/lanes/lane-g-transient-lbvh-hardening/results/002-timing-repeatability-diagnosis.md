# G002 — Timing-repeatability diagnosis

Status: **closed diagnostic / timing protocol unresolved**

## Phase A — target-GPU diagnosis

Measurement commit: `5377cf5b85194eff82e34e3a846eb25af6e2155e`.

The F007-style one-warmup / one-measured fresh-process protocol is rejected.
Fourteen of sixteen anchor groups exceeded the historical `max/min > 1.20`
warning, including every control family. Warmup 0 / 1 / 4 / 16 never stabilized
all anchors, and canonical/reverse full-matrix order produced more than 10%
median shifts in sixteen variant/scenario groups.

The evidence rejects both a purely LBVH-specific instability explanation and
"just warm up longer" as a sufficient fix.

## Phase B — paired/counterbalanced G002b

Measurement commit: `7b14d6ec82252d0a169c3530ce0c3fcaeb5dc18a`.  
Plan: `lane-g-g002b-v1`.

All 160 planned measurements were retained.

Only **1 of 8** frozen candidate/control comparisons met all three repeatability
criteria. Therefore the paired protocol under automatic DPM is rejected and
cannot be frozen for decision-valid G003/G005 timing.

The LBVH moving paths themselves were comparatively repeatable:

- moving-rigid LBVH: 1.431–1.488 ms, max/min **1.039**;
- sparse-moving LBVH: 1.383–1.430 ms, max/min **1.034**.

The matching vanilla comparators were not:

- moving-rigid vanilla: max/min **1.487**;
- sparse-moving vanilla: max/min **1.571**.

The comparator traversal-maintenance timing repeatedly occupied distinct timing
bands, while other unrelated GPU stages could also move together. This rejects
an intrinsic transient-LBVH builder instability explanation but does not
establish a unique external cause.

## Phase C — G002c safety stop

Plan `lane-g-g002c-v1` proposed repeating the paired experiment while the AMDGPU
performance level was externally set to `profile_peak`.

The host crashed after attempting this power-state experiment. The user
explicitly declined any further execution of this experiment.

**G002c is therefore abandoned for host-safety reasons and must not be requested
again.**

No G002c result is accepted and no conclusion about `profile_peak`, DVFS, or
clock/power isolation is drawn from the crash.

The repository may retain the runner/config as historical diagnostic material,
but they are not an active execution requirement.

## Final G002 disposition

Accepted findings:

- F007 one-shot fresh-process timing is not decision-valid on this host.
- longer warmup alone does not fix repeatability;
- automatic-DPM paired timing is still insufficient;
- the instability is not specific to the transient-LBVH moving builder;
- timing excursions also affect control implementations.

Rejected / not established:

- no stable decision-valid timing protocol was established;
- DVFS is not established as the unique root cause;
- `profile_peak` is not an accepted measurement requirement;
- G002c must not be rerun.

Therefore **G002 closes as diagnostic/inconclusive for formal timing**.

This does not invalidate deterministic G001 memory evidence. It does mean that
future Lane-G work must not use current timing runs as formal promotion evidence
unless a later, safe measurement protocol is separately planned and accepted.

No forced GPU performance-state manipulation is permitted as a prerequisite for
continuing Lane G.
