# N010 post-hoc raw timing replay outcome

2026-10-18 JST. [Plan118](../experiments/118-posthoc-ranked-c7-raw-timing-replay.md)
and decoder/driver were committed in757a4ef4 before this replay. Original255
was already observed: this is explicitly a **post-hoc implementation replay**,
not prospective validation of a newly acquired performance result.

## Executed result

[378](378-posthoc-ranked-c7-raw-timing-replay.json): all five exact numerical
comparisons hold. Read/rehashed105 small source, original result, timestamp,
schedule/dose and actual native-receipt files. All24 original processes,
5760 raw GPU frames and1440 four-frame means remain, including warmups and
the original extreme process observations. No image or scratch spool read.

Reconstruction from actual JSONL files reproduces the embedded raw frames,
four-frame arithmetic means, constituent indices and saved103 schedules.
The paired log values/process medians, all six ranked intervals, full-family
noncoverage calculation, control/order-allowance effect interval and all four
calibration checks match255 **exactly**. The unchanged effect interval is
**[1.1386441286318703,1.242058969553914]**, width1.0908227938138153.
This exercises the new decoder and117 core on this retained calibration case.

Immutable378 SHA256:
`8bd30aa3a02eb54b7f41fba00e787a7a965aa1909cb3f491893f213d58732631`.

The analysis itself used0.079903376CPU/0.169679343elapsed seconds on CPU31,
nice15, within20CPU/1GiB limits. This is archived-file processing cost, not a
Renderer performance result. No new native physical/CPU/GPU acquisition or
compiler was launched. Original CPU260 continues on the same low-priority
core and was not restarted, reconfigured or used as a timing denominator.

## Scope and admission

`numerical_replay_pass=true` denotes exact arithmetic reproduction only.
`all_pass=false`, `accepted_timing=false`, `proof_admission=false` remain.
The conditional decision explicitly reports `INVALID_OR_UNVERIFIED_EVIDENCE`
because this replay did not validate the full evidence, quality or nuisance
model. This is intentional; the component cannot convert a successful
arithmetic replay into accepted GPU timing.

Individual original native receipts have PID/start but no boot field;378
uses255's acquisition-wide before/after boot provenance and states that
limitation. No current-boot identity or cross-boot performance pooling is
invented. Unique identities do not establish statistical independence.

Not verified here: image/scratch payloads, original build/binary/shader proof,
owned-memory ledger, actual selected GI quality/budgets/dynamic lifecycle or
nuisance-model validity. This positive added-work case also does not exercise
every candidate win/loss/equivalence classification. No statistical-method
validation or superiority claim follows from implementation consistency.

Actual selected-boundary manifests/acquisition and strict full proof replay
must still be connected to the final six-gate auditor. Old8-process timing
gates remain unchanged;255 stays diagnostic, all earlier FAILs remain. This
component introduces no new physical/reference admission obligation.

References16/24, original full physical artifacts14/17 including one
diagnostic-only item. Original260 remains acquiring; no following seed queued.
All missing physical/bias/state/prefix/feasibility/reference/pilot/memory and
timing-intake obligations remain. Sponza direct-relative1.0 pixels remain
**UNRESOLVED / 未解決** and scored. N010 **NOT_READY**; Lane M accepted
comparisons have not started. No N011 or default Renderer/build changes.

Unit/regression tests and new Renderer/runtime measurements: **NOT RUN**.
The registered archived-data arithmetic replay above executed; Python AST
syntax parsing also completed. These are distinct from release regression
or hardware capability validation. The AI-assisted provenance remains as
disclosed in the repository workflow documentation.

Metadata-only `python scripts/research/verify.py`: OK, eight configured lane
indexes /286 declared result links. `git diff --check`: clean. Neither is a
runtime or admission check.
