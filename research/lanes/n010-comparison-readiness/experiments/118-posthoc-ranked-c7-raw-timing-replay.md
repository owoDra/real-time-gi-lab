# N010 post-hoc raw timing arithmetic replay

2026-10-18 JST; parent5a4a1efb. Prepare/commit this source before replay.
This is a post-hoc implementation cross-check on already observed255, not
preregistration of that acquisition or a new performance experiment.

## Exact scope

The117 numerical decision core is written but unexecuted. Implement a pure
raw-observation decoder and replay all24 original C7 processes from immutable
255 (`e71e9f9c17852fc3399660c79dce370850f7b4e0a90ea3ecab37f921b1cd864d`).
Rehash/read actual JSONL timestamps, actual resource receipts, saved103
schedules and dose files, including every warmup, and compare embedded data.
Reconstruct all5760 raw frames/1440 four-frame means without filtering.
Verify exact raw indices/doses, contiguous constituent frames, adjacent paired
arms, round identities, and balanced warmup/measured orders. Recalculate the
three log pairs per population/order and every process median. Feed the
original reserved16-boundary family from immutable046 into117; require its
rank4, all six intervals, all four calibration conditions and effect interval
to reproduce255 exactly. No family/rank/threshold/sample-count tuning.

The decoder's expected records must come from the caller's pinned prospective
schedule. Structural checking does not prove randomization, scene/history,
quality, or full native semantics. The dedicated replay additionally compares
against the original103 schedule generator and actual saved schedule files.
Original255's acquisition-wide boot identity accompanies PID/start receipts;
individual receipts do not contain boot IDs. Do not invent per-native boot
evidence or pool with this continuation's current boot.

This is only small archived-file parsing/arithmetic. No CPU/GPU physical
acquisition, compiler, native launch or new Renderer measurement. It may run
while260 calculates, on the SAME CPU31/nice15, with20CPU seconds/1GiB limits.
This is not a second measurement worker. Do not read/re-hash12GiB of images
or claim their validation. No accepted GPU timing or final preflight dispatch.

## Classification and artifacts

One explicit invocation; refuse existing output. All exact comparisons must
hold for `numerical_replay_pass=true`; otherwise retain the mismatch. Output
always has `all_pass=false`, `accepted_timing=false`, `proof_admission=false`.
Call117 with `evidence_verified=false`, `quality_status=UNKNOWN` and
`nuisance_model_justified=false`: the result must remain unverified. Reproducing
an old interval checks this implementation's arithmetic on this dataset; it
does not independently validate the method, independence/nuisance assumptions,
image/scene/quality/memory correctness, another boundary or the full classifier.
No old FAIL or255 outcome is changed.

Decoder: `scripts/research/n010_reference_sampling/ranked_timing_observations.py`.
Driver: `scripts/research/n010_reference_sampling/replay_ranked_c7_timing.py`.
Result: `378-posthoc-ranked-c7-raw-timing-replay.json` (absent until execution).
No automatic queue, settings/Actions/N011/default graph/N001–N009 changes.
N010 NOT_READY; missing references/physical/bias/state/prefix/pilots/memory/
selected-boundary acquisition and final proof intake remain. Direct-relative
1.0 pixels remain UNRESOLVED/未解決 and included. Unit/regression tests NOT RUN.
