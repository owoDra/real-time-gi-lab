# J004 validation diagnostic visibility v5

Status: **HARD VALIDATION FAILURE RETAINED — timing not started**
Issue: #23

The v4 target run built and linked successfully, then stopped on the frozen hard
validation gate for `large-global-high/primary/control`.

The runner previously raised only the profile/track/variant and hid the retained
`j004-validation.json` counters. Commit
`787f437c3e96b8572d3436a264c30d84d6866c12` changes only error reporting so
future failures include that JSON payload.

No correctness rule or decision semantics changed. In particular, the failed
control is not accepted, ignored, rerun selectively, or timed.

The original failed run artifact is retained at timestamp
`20260930T115408Z`; its validation JSON is sufficient for root-cause diagnosis
without another validation run.

Machine-readable record:
`experiments/009-formal-validation-diagnostic-v5.json`.
