# N010 prospective ranked timing decision core

2026-10-18 JST. Parent a7aa6b56. Prepared while original CPU260 is live;
no additional scientific worker, compiler or GPU acquisition. Implements the
remaining decision logic from review249/plans100/103. This is a numerical
analysis component, not accepted calibration, a full proof-intake verifier,
or a new reference gate. Commit before any new data using this component.

## Fixed decision and finite family

Keep GPU Renderer time, matched quality, complete costs and memory/dynamics
as comparison axes. CPU wall, clocks, busy and other-app activity remain
diagnostic. No fixed stability-percentage or idle gate is introduced.

The numerical core consumes exactly24 fresh process repetitions, with three
measured log(B/A) pairs for each of control_a/control_b/effect and AB/BA.
Take each process's median of its three pairs, separately for all six
populations. Same-role controls compare baseline/baseline and
candidate/candidate; calibration compares zero/zero and loaded/loaded.
Calibration effect is loaded/zero; comparison effect is candidate/baseline.
Never use the positive-additional-work check to reject a faster candidate.

Freeze an ordered list of every separately claimed timing boundary BEFORE
acquisition. It must identify actual family, device, selected quality budget,
scene/state, timed full Renderer commands, history/allocation/output lifecycle
and observation unit in the eventual acquisition manifest. A separately
claimed dynamic transition/recovery frame counts separately; four repeated
static frames do not calibrate one history-dependent frame. A trajectory
aggregate cannot replace required individual frame observations. All raw
frames, warmups and absolute GPU intervals remain required upstream.

For M registered boundary identities use the largest integer r in1..12 with

`6*M*2*sum(comb(24,j), j=0..r-1)/2^24 <= 0.05`.

The closed population-median interval is `[x_(r),x_(25-r)]`, using ALL24
values, without interpolation, filtering or bootstrap. Freeze the resulting
design with the manifest before outcomes. No adaptive family reduction,
rank/sample-count change, reclassified old data or repeated-until-PASS
campaign. M=16 yields the unchanged103 rank4; larger families receive their
own simultaneous budget rather than silently borrowing16-boundary coverage.
This deterministic extension addresses actual scope, not observed precision.
Calibration and candidate families are separate; this component grants no
joint confidence claim across both or unlimited subsequent campaigns.

Use100/103's same-role control endpoint allowance, order-specific expanded
intervals and conservative AB/BA hull. Both control-location and order-interval
compatibility remain required. Raw median coverage assumes independent fresh
repetitions/common medians. The expanded interval additionally requires the
registered conditional nuisance model; agreement does not establish it.
Unsupported bias assumptions mean timing inconclusive. Process identities
with boot/PID/start prevent duplicate repetitions and cross-boot pooling but
do not prove statistical independence.

With q=T_candidate/T_baseline and margin1.20:

- Win: the entire conditional interval is strictly below1/1.20.
- Loss: the entire interval is strictly above1.20.
- Practical equivalence: the entire interval is inside[1/1.20,1.20].
- Otherwise timing inconclusive, preserving quality/memory outcomes.

Calibration alone retains positive additional work and interval width<=1.20
as its two additional conditions. A comparison does not need to pass those
calibration-specific checks. Quality FAIL/UNKNOWN prevents a same-quality
speed ranking; unverified evidence prevents a timing conclusion. A numerical
classification never itself authorizes accepted timing or N010 READY.

## Implementation and unfinished integration

`scripts/research/n010_reference_sampling/ranked_timing_decision.py` is a pure
stdlib module. It never acquires, queues, builds, imports Renderer code or
changes the environment. It recalculates ranks, medians, all six intervals,
control allowance, compatibility and the classifier. It retains every paired
value/process identity/ranked summary. It rejects malformed or nonfinite
input, duplicate identities, cross-boot pooling and changed design.

Caller evidence/model booleans are explicitly assertions, not proof replay.
Outputs always retain `accepted_timing=false` and `proof_admission=false`.
The full-boundary verifier must independently check actual raw timestamps,
paired/randomized schedule and warmups, images/scratch, binaries/shaders,
selected quality, resources, owned allocation/free ledgers and provenance.
Only that verifier and the final six-gate adapter can admit a handoff.
Those acquisition-manifest/proof-intake integrations remain required and
unimplemented here. Do not pass255 or a fabricated aggregate through the
old8-process/64-sample auditor. Existing final preflight remains unchanged.

No new acquisition is specified or authorized by this module. Existing103
is terminal; no extension/retry. The next actual timing acquisition still
requires prospective selected boundaries/budgets, raw schedule, resource/
stop conditions, strict proof intake and quiescence. This plan adds no
physical/reference obligations. N010 remains the final preparation lane;
references16/24, direct-relative1.0 pixels UNRESOLVED/未解決 and included.
Past FAILs, GPU372's count failure and N001–N009 results stay unchanged.

Source/syntax/metadata review only; numerical execution, new CPU/GPU
measurement, default build, unit/regression tests: NOT RUN. No claims of
runtime or statistical implementation validation until the registered
analysis is exercised with its required evidence. No Actions or N011.
