# N006 P1b — instrumented causal-chain diagnosis of image invariance

Issue #42. Status: **prospectively defined diagnostic only, GPU not yet run**.

## Why this narrower step is necessary

The completed P1a *offline image audit* ([result](../results/004-p1a-image-influence-audit.md)) established that 11 of 12 owner × cascade four-ray interventions changed **zero RGB pixels** (identical image SHA), while tile 22890 / cascade 3 changed 468 pixels, all beneficial, none at the selected screen tile. A predictive signal cannot use 11 completely unresponsive end-to-end labels as if they were measured *marginal ray gains*.

The original renderer's causal chain is:
`work_item ray -> hit -> 16-bit integer radiance -> per-output ray mean (round-to-int) -> shared (probe xyz, cascade) slot mean -> composite pixel lookup`.
The exact point where P1a interventions vanish remains unidentified. Do not infer an algorithmic failure merely from the global RMS zeros.

## Prospective fixed micro-probe

Two **preselected** calibration-only cases, contrasting earlier P1a zero and nonzero effects **within the same visible owner**:

| tile | cascade | P1a effect | additional rays |
| --- | --- | --- | --- |
| 22890 | 0 | zero changed pixels | 4 |
| 22890 | 3 | 468 pixels changed | 4 |

No other tile, cascade, threshold or direction is selected in this pilot. This is a *causal-chain debugging pair*, not an independent held-out generalization test.

- Run one fresh `current` render and two targeted renders with 1 source warmup frame, 1 target frame, no fresh independent reference. If the short-warmup current HDR image differs *even by one represented float channel* from the existing 32-warmup P1a current HDR image, **stop before intervention runs**. Never quietly change warmup or select a different baseline.
- Verify and retain the exact earlier P1a repaired reference and all 12 original intervention raw evidence/images using `audit_p1a_images.audit`. The new instrumented images **must be bit-exact** against the two matching prior targeted images; otherwise these readbacks cannot be attributed to the accepted P1a effects, and that case fails.
- Instrument only the *new N006* runtime after a completed GPU frame (no changes to the accepted N004/N005 algorithms). Read back per-work item `contributions`, per-output `accum` and storage slots, assert identities and counts, then emit compact `influence_trace` metadata.
- Record exact selected owner/cascade/output/probe key; base 8 integer radiance sum, four added radiance integers, zero-valued ray counts, before/after **rounded per-owner output mean**, number of same-probe owner outputs, before/after shared-probe sum and fractional mean, and observed GPU storage sum/count. Assert reconstructed post-intervention storage aggregate matches GPU storage. No post-trace trace data is eligible as a real-time pre-trace scheduler signal.
- Correctness and source/target pixels must match the original frozen target; any readback/identity mismatch invalidates the case. Never substitute new images into earlier P1a evidence.
- Readback synchronization/CPU cost and serial P1a selector are **debug only** and excluded from scheduler performance; no elapsed-time superiority claim.

### Interpretations to distinguish

1. Added integer radiance sum = 0 (versus nonzero baseline): extra directions contribute nothing under present low-light/visibility conditions.
2. Per-output `mean16` unchanged: 16-bit sample normalization removed any visible numerical distinction.
3. Per-output mean changed but shared-probe mean unchanged/attenuated: rounding and multiple owners share the same spatial key.
4. Shared probe mean changed but final image unchanged: screen lookup/reachability or floating-point precision remains to be diagnosed; another **prospectively specified** diagnostic would be needed.

A successful pair establishes mechanisms for **these two specific interventions only**. It does not prove that this mechanism dominates the other ten nor authorize signal fitting or P2.

## User GPU step

With the original `20261008T144934Z-cli-repair` campaign left intact:

```bash
git pull --ff-only
mise run build
mise exec -- python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1b_influence.py
```

Expected output: `out/research/n006-interval-aware-allocation/p1b-influence/<timestamp>/n006-p1b-influence-summary.json`. Upload only the JSON summary unless a failed case requests its `stderr.log`. Avoid manual GPU clocks/profiles, sample exclusion or repeat until the result is evaluated. No GitHub Actions.
