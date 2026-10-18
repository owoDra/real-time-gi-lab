# N010 prospective amendment — readiness to compare and timing claims

2026-10-18 JST. Parent checkpoint: `8c7a941692fbdf777b506fd1c957425ffb04e057`.
User direction: review environment-sensitive decision criteria and finish
N010 before Lane M. Commit this amendment before any acquisition using it.
This is a change to future completion policy, not a new measurement or a
retroactive interpretation of earlier data.

## Change and scope

For future N010 handoff, replace experiment001's requirement that every
timing boundary demonstrate a decisive precision PASS with a requirement
for a complete, valid, independently replayable timing pilot on the frozen
actual boundaries. Preserve the original six areas of evidence. A valid
pilot can end **TIMING_INCONCLUSIVE**; that outcome alone does not prevent
handoff. It never grants an accepted performance claim.

This supersedes only the timing-precision prerequisite for future handoff.
Reference eligibility, all locked states, no scoring exclusions, correctness,
complete static/dynamic quality pilots, family/budget selection, full costs,
owned-memory constraints, source/device provenance and runnable commands
remain required. An incumbent quality loss remains a legitimate comparison
outcome. N010 is still unfinished and NOT_READY.

## Evidence validity and precision are separate

| State | N010 handoff treatment | Performance treatment |
| --- | --- | --- |
| Missing/partial/malformed evidence, changed binary/state/budget, invalid timestamps, missing pairs, unverified full boundary or memory ledger | Timing pilot incomplete; NOT_READY | No timing conclusion |
| Complete valid pilot, but unresolved uncertainty, order effects, unsupported nuisance model or unsuccessful known-work precision check | Retain every row and classify timing INCONCLUSIVE; does not by itself block handoff | Descriptive GPU times and assumptions only; no win/loss/equivalence claim |
| Complete valid pilot and demonstrated precision on actual selected boundaries | Timing part of handoff complete | Later prospective Lane M claims additionally require matched quality and their registered uncertainty/multiplicity rules |

An integrity failure is not measurement uncertainty. In particular GPU372's
missing shadow/proposal counts remain FAIL. Sponza direct-relative-error1.0
pixels remain **UNRESOLVED / 未解決**, included and explicitly measured;
this timing amendment does not resolve either problem.

The pilot must retain raw GPU timestamps, frozen command/schedule/warmups,
native identities/resources, binaries/shaders, physical states, selected
budgets, images/known-work witnesses and owned allocation/free events.
Recompute the pilot's results from actual retained payloads. Caller booleans,
saved summaries, a timing parser or a numerical classifier alone cannot
establish evidence validity. Unsupported nuisance assumptions permit no
speed conclusion even when the sampling interval is narrow.

## Fixed measurement and stopping policy

GPU timestamps over the complete Renderer remain the primary performance
axis. Preserve absolute times and paired relative effects, actual device/
driver/environment identity, persistent/startup/recurring peak ownership,
transition and recovery frames. CPU wall, global free VRAM, clocks, busy and
other-app activity are diagnostic or execution-resource observations; do
not introduce an idle threshold or tune display/power settings.

Freeze the complete selected boundary family, quality budgets, observation
unit, process/sample counts, schedule, analysis, time/resource limits and
terminal outcome rules before fresh data. Keep all samples and all declared
rows. A bounded campaign ends at its registered stop, including inconclusive
or invalid outcomes; no repeat-until-PASS, post-hoc family reduction or
outcome-driven extension. A precision failure alone does not justify another
generic stability campaign.

Plan117's prospective1.20 practical margin and its conditional numerical
classifications are unchanged. Calibration before accepted performance
claims still applies to the actual selected workload/quality/frame boundary;
C7 diagnostic255 cannot qualify other boundaries. Neither a valid pilot nor
handoff is architecture promotion or proof of GI superiority.

## Implementation status and next action

The numerical component117 and archived replay118 exist. The original
preflight and its pinned adapters still require the old eight-process
calibration PASS. They have **not** implemented this amendment and must not
be described as the new auditor. Implement a separately versioned full
evidence intake and final adapter that records evidence validity separately
from precision and preserves the other five gate bodies/provenance dispatch.
Do not bypass the old gate by editing a boolean or refeeding old diagnostics.

No new acquisition is specified by this amendment. Actual selected-boundary
registration, a valid executed pilot and the amended auditor remain work to
complete in N010. There is no N011 or automatic scientific queue.
Past FAILs, historical numerical thresholds and N001–N009 results are unchanged.
