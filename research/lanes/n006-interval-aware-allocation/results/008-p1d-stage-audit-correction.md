# N006 P1d — offline stage audit review and corrected timing overlap

Issue #42. **Completed diagnostic; historical raw evidence preserved.** User attached `n006-p1d-stage-audit.json`, protocol `n006-p1d-offline-stage-audit-v1`, sourced from P1d `2b862de49b8627e7d8bdbd4d91c312400c161019`, all six raw run evidence and PFM files validated, status `complete`.

## Observations

- 3 pairs (current→hash / hash→current / current→hash), final images byte-identical; GPU clear/hash cost **24.5266 / 20.9197 / 30.5781 µs**; complete-GI delay **20.9598 / 421.6010 / 635.5676 µs**. Source P1d never changed ray count.
- Raw exported GPU stage changes were small by comparison. `ray_prepare_gpu` deltas **+29.496 / +20.198 / +21.841 µs**; `traversal_gpu` **−9.378 / +7.775 / +5.330 µs**; `producer_gpu` **−13.586 / +20.198 / +0.040 µs**.
- CPU `dynamic_update_wall` changed +1,229 / +602 / +755 µs across pairs. This is CPU wall diagnostic **not** a GPU stage; correlation is suggestive but does not establish the cause of GPU complete GI delay.

## Source-level accounting defect found AFTER upload

The historical P1d N006 runtime places the hash command after producer timestamp **4** and before ray-preparation timestamp **5**. The exported historical `ray_prepare_gpu = timestamp(4,5)` **already includes** the complete auxiliary hash stage measured separately as `timestamp(18,19)`.

The first offline audit v1 **double-subtracted** hash in its arithmetic residual, giving −12.103 / +354.914 / +584.911 µs. The corrected residual without overlapping subtraction is:

| Pair | Whole GI delta | Exported (inclusive) pipeline-stage delta | Corrected non-overlapping unattributed GI delta |
| --- | ---: | ---: | ---: |
| 0 | +20.960 µs | +8.536 µs | **+12.424 µs** |
| 1 | +421.601 µs | +45.767 µs | **+375.834 µs** |
| 2 | +635.568 µs | +20.078 µs | **+615.489 µs** |

No raw outcome is discarded: the original v1 audit remains an historical *diagnostic with an identified accounting bug*; future `audit_p1d_stages.py` produces `n006-p1d-offline-stage-audit-v2` with exclusive hash/ray-prepare values and no double subtraction. The source-level correction is certain; the unattributed portion is **not** a directly timestamped hardware interval.

Hash-free ray preparation differences, subtracting measured hash from historical inclusive `ray_prepare_gpu`, are +4.969 / −0.721 / −8.737 µs. No broad ray-prepare regression is demonstrated.

## What remains uncertain

A sizeable GI delta after all recorded stages remains. The earlier per-stage JSON did not export primary visibility, renderer depth, frame initialization, visibility reuse, invalidation or dynamic-maintenance GPU total. Thus these cannot be identified from P1d's six raw output files. We must not blame GPU hash itself from a 24.5 µs timestamp, nor assert a dedup speedup.

## Next prospectively frozen test

See [P1e same-process timing-boundary calibration](../experiments/005-p1e-timing-boundary-calibration.md). Its N006-only instrumentation uses **nonoverlapping** GPU segments (`hash: timestamp(4,19)`, `ray_prepare: timestamp(19,5)`), exports previously hidden GPU stage times, and verifies the sum reconstructs complete-GI GPU. It runs 12 frames in one process alternating current/hash across 6 paired windows on identical geometry with reference generation disabled, strict image/frame checks, and raw evidence retained.

**Decision: P1d hash correctness PASS; whole-GI timing interpretation REFINE.** Do not implement a dedup ray backend or fit an adaptive allocation signal before causal cost and full-GI quality/correctness are resolved. N004/N005 unaffected. No GitHub Actions.
