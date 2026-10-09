# N006 P1j-B — true zero-copy compact work, HWRT/Software 10/10 parity

Issue #42. **Correctness PASS, standalone speed improvement NOT YET ESTABLISHED.** Source: user-uploaded `n006-p1j-b-direct-compact-summary.json` on 2026-10-09, `protocol_version=n006-p1j-b-direct-compact-v1`, clean branch `781ecadc41eaffac87896aa919469c0bd46e6be0`, GPU AMD Radeon 8060S (RADV STRIX_HALO). Flags `status=complete`, `all_cases_byte_identical=true`, `cases_complete=10`, `failures=[]`, `formal=false`; no independent reference rendered.

| Scenario | HWRT canonical-build GPU (µs) | Software canonical-build GPU (µs) | Actually dispatched rays (original→canonical) | Same HDR PFM bytes? |
| --- | ---: | ---: | --- | --- |
| static | 44.084 | 44.485 | 133344→24064 | YES, both backends |
| camera-motion | 48.412 | 48.773 | 135392→25760 | YES, both backends |
| light-motion | 48.011 | **149.644** | 133344→24064 | YES, both backends |
| moving-rigid | 48.853 | 50.897 | 134816→24832 | YES, both backends |
| deforming-control | 49.294 | 50.536 | 133504→24232 | YES, both backends |

All ten actual candidate GPU reports explicitly say `copyback_executed=false` and `direct_compact_work=true`, with the previously validated 32,768 hash slots, ~81–82% fewer actual rays, same unique probe key counts as P1i/P1j-A, zero reported failure gates and exact per-scenario baseline/candidate PFM SHA. Hash aggregate collision steps 443–665 across the frozen ten cases; GPU capacity/hash/owner-weight checks passed. Each reported added N006 scratch **4,489,304 B**, identical to accepted P1j-A, because the separate compact work staging buffer is still present and original owner-local producer still fills the full work array.

## Interpretation

The experimental P1j-B pipeline has eliminated one GPU compact→original work-array **copy dispatch** and its barrier by binding the accepted work-to-rays, radiance, storage, weighted-storage and resolve stages directly to compact work. This is validated end-to-end for all ten scenes/backends in the specific GPU/protocol, with unchanged image and actual GPU ray counts. **It does NOT establish a measured end-to-end or software speedup, nor a further N006 memory saving.** The P1j-B report's cold sequential frame whole-GI current/canonical differences include dynamic state transitions, and the earlier P1j-A report was from different processes and GPU thermal/scheduler conditions: their canonical build timings must not be treated as matched paired differences.

Software/light-motion had one 149.644µs canonical-build anomaly versus nine other observed P1j-B canonical-build values ~44–51µs. A single outlier cannot prove a regression; retain it and test repeated paired workloads rather than censoring it or explaining it without evidence. HWRT-incapable hardware and topology-changing high churn remain untested.

**Next frozen P1k:** `experiments/012-p1k-three-arm-hwrt-software-timing.md`, same-process current vs P1j-A copyback vs P1j-B direct, full order-balanced three-arm triplets on each backend after target-state warmup, with all raw GPU timestamp closures/primary visibility noise and PFM equality. This is necessary before concluding whether zero-copy should replace the simpler accepted copyback path. Original N004/N005 and prior P1a–P1j-A evidence untouched; no GitHub Actions.
