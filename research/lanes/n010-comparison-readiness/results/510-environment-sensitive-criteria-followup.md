# Environment-sensitive criteria: decision roles and unfinished integration

2026-10-19 JST. User asks whether frequently environment-dependent quantities
should decide acceptance. This is a methodology/status review, not a new
numerical amendment, accepted timing result or readiness decision. No new
measurement is authorized by this record. N010 remains NOT_READY.

## Decision

Use environment-dependent telemetry to diagnose execution. Do not require a
desktop idle percentage, a CPU/GPU wall ratio, constant clocks or global
free VRAM for architecture acceptance. Retain complete Renderer GPU time
as a conditional performance observation: removing time altogether would
leave the real-time performance question unanswered. An unresolved timing
effect permits no speed ordering, even if correctness/quality evidence is
valid. Same-session relative comparisons do not guarantee cancellation of
contention, order bias or workload-dependent clock effects.

This direction is already registered in [120](../experiments/120-reportable-comparison-readiness-amendment.md)
and [147](../experiments/147-selected-pilot-validity-without-speed-claims.md),
following [249](249-comparison-criteria-review.md). The remaining problem
is implementation and missing evidence, not a need for another threshold.

| Observation | Decision role |
| --- | --- |
| Scene/transport identity, qualified reference, full-image error and dynamic quality | Required scientific validity. Preserve quality losses and every registered case. |
| Allocation/free ledger and persistent/startup/recurring true owned peak | Required budget evidence; global free VRAM cannot replace it. |
| Complete Renderer GPU timestamps and all required costs | Performance axis conditional on declared hardware/driver/regime; retain absolute times and uncertainty. |
| CPU wall, GPU busy/clocks, other-app activity and global free VRAM | Diagnostic only; no generic stability or idle gate. |
| Timeouts and bounded dispatch/fence guards | Execution protection. A stop gives incomplete evidence, not an intrinsic architecture loss. |

N010 needs complete valid descriptive selected pilots. Under120/147,
TIMING_INCONCLUSIVE alone does not block handoff. Missing/invalid evidence
does. Lane M accepted performance claims still require the actual-boundary
calibration and prospectively fixed matched-quality design, observation
units, order, sample count, effect margin, uncertainty/bias/multiplicity and
finite stopping rules. Preserve117's registered1.20 practical margin and
all historical outcomes; no retroactive gate or threshold change here.

## Concrete current work

Final120 intake/adapter integration is unfinished. Complete that route and
the missing physical/reference/quality evidence; do not repeat a generic
stability campaign. Optional146 known-work building is not a prerequisite
for N010's descriptive handoff. No family, heavy scene or quality loss is
removed to obtain completion. N010 remains the final preparation lane;
distinct Lane M follows, no N011.

[508](508-raw-query-pilot-and-posthoc-replay-outcome.md) also shows why failures
must be classified by cause: the most recent time-intake FAIL came from
binary32 versus binary64 arithmetic. Source-exact CPU replay validates
that one native without relaxing tolerance or rerunning the GPU. This is
not proof of general timing stability. Its dense quality losses remain.

Current evidence: compensated physical candidate13/17; eligible references
16/24; selected PT2/28 and one post-hoc non-PT pilot, union3/36. These are
coverage counts, not readiness. Sponza direct-relative1.0 pixels remain
**UNRESOLVED / 未解決**, included. Tests NOT RUN; documentation review only.

Publication metadata checks:7125 declared input/payload SHA256 entries across
487/504/505/506/507/509 match1743 unique retained files. The metadata harness
resolves8 configured lane indexes/379 declared links. Diff whitespace check
is clean; default CMake/config/workflows and N001–N009 trees remain unchanged
relative toadf81960. These checks are not runtime regression validation.
