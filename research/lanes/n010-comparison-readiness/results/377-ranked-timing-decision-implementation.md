# N010 ranked timing decision implementation checkpoint

2026-10-18 JST; parent a7aa6b56. Classification: **IMPLEMENTATION_PREPARED,
NOT_EXECUTED, NO_ADMISSION**. No new measurement or change to past outcomes.

[Plan117](../experiments/117-ranked-timing-decision-core.md) and its
[pure numerical core](../../../../scripts/research/n010_reference_sampling/ranked_timing_decision.py)
implement the comparison classification remaining after249/100/103/256.
The existing final preflight still expects the old eight-process method;
it is not changed or bypassed by this component. N010 is **NOT_READY**.

## Concrete changes

- Separate calibration from GI comparison. Positive additional work and the
  calibration interval-width condition apply only to calibration; a faster
  candidate must not fail because its effect is negative.
- At matched quality use candidate/baseline GPU-time ratio and the existing
  1.20 practical margin: interval wholly below1/1.20 wins, wholly above1.20
  loses, wholly inside the equivalence band is practically equivalent,
  otherwise timing is inconclusive. Control/order incompatibility or an
  unjustified nuisance model also gives timing inconclusive.
- Preserve quality FAIL/UNKNOWN explicitly instead of ranking an unmatched
  candidate's speed. Unverified evidence cannot yield a timing conclusion.
- Keep all24 process summaries and their six populations, each containing
  three measured pairs. Duplicate native identities and cross-boot pooling
  are refused. Recalculate every median, rank, interval and allowance.
- Explicitly budget the full preregistered family, including each separately
  claimed dynamic frame. Deterministically choose the largest median-interval
  rank satisfying the fixed5% family bound at24 repetitions. With16 boundaries
  this reproduces103's rank4; no observed-data rank selection or sample removal.

All output classifications are conditional numerical results with
`accepted_timing=false` and `proof_admission=false`. Evidence/model booleans
are caller assertions, not independently validated facts. Independence/common
medians and100/103's conditional nuisance model remain assumptions; identical
controls or distinct PIDs do not establish them. No claim of a universal
environment-independent performance measure is made.

## Actual remaining integration

Pin actual selected workloads, quality budgets and frame lifecycle before
new timing data. Their acquisition manifest/schedule and strict raw-payload,
image/scratch, native/binary/shader/resource and memory-ledger replay must be
implemented and connected to the final six-gate auditor. This core is only
the numerical part of that work. No255 diagnostic result or historical FAIL
is retroactively admitted, and no new acquisition/automatic queue starts.

During this work original260 is still live: PID10159/start59862 confirmed in
`/proc`, same838d3e50 native and one low-priority CPU. The mutable result stays
uncommitted/unindexed until terminal. No other scientific work is overlapped.
References remain16/24 and physical artifacts14/17 including one diagnostic;
all missing physical/bias/state/prefix/reference and pilot/memory gates
remain. Sponza direct relative-error1.0 pixels are **UNRESOLVED / 未解決**,
included. GPU372's separate shadow/proposal count failure remains FAIL.

## Source identities and checks

- Core SHA256: `ae1b5e4510bb70afe6a9414ce597efc026c0bacfdd1ac9543aad7c9cdc6bf572`.
- Plan117 SHA256: `50777da01eb9aea564a010b0576df6e3e241a2ca086fdf2624b1a0e731c1c444`.
- Python AST syntax parsing: completed. This does not execute or validate
  the numerical algorithm or its evidence intake.
- Metadata-only `python scripts/research/verify.py`: OK, eight configured
  lane indexes /284 declared result links. `git diff --check`: clean. Neither
  is runtime validation or proof admission.
- Numerical execution, new CPU/GPU acquisition, default build and unit/
  regression tests: **NOT RUN**. No executable Renderer/shader/default build
  graph or N001–N009 result changes. No Actions or N011.

The implementation and this review are AI-assisted work under the repository's
[workflow disclosure](../../../../docs/ai-research-workflow.md); this record
does not imply an external independent statistical review.
