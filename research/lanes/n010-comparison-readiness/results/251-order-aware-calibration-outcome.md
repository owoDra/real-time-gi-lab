# N010 order-aware calibration outcome and post-hoc diagnosis

2026-10-17 JST. [Plan100](../experiments/100-order-aware-timing-uncertainty.md)
and both drivers were committed in `c966abe` before acquisition. Native
[250](250-uncertainty-c7-calibration-diagnostic.json) completed twelve fresh
processes with all returncodes0. No native retry. This is the first acquisition
under the replacement decision method, not a reanalysis of247/248.

## Prospective decision: timing capability INCONCLUSIVE

The measured control-allowance effect interval is **[0.889520,1.639825]**,
multiplicative width1.843495. It includes no change and fails the registered
width<=1.20. The two control-location compatibility checks and effect-order
compatibility check pass. Two of four registered checks pass; overall
`all_pass=false`. This is **inconclusive timing capability**, not a GI
architecture rejection, an accepted calibration or proof of equivalence.

The effect's raw process-median point ratios are approximately1.19749 AB and
1.20165 BA. Those points alone do not override the uncertainty/bias decision.
All2880 original frame intervals,720 four-frame means, all warmups and complete
labelled pre-native schedules are retained. No sample/process is removed.
This boundary measures repeated static C7 HWRT frames in one submission per
process, not individual-frame precision, dynamic history or all16 boundaries.

Integrity results: every image matches046 exactly; both neutral-work payloads
validate; every owned ledger replays and returns to zero. Owned Vulkan peak
**500,371,904bytes**. All12 native receipts show CPU31,nice15,30CPU/30elapsed
limits and successful exit. Retained work6,161,865,608bytes, below8GiB. Sum of
measured raw GPU intervals0.451951874seconds is not total batch or campaign
elapsed. No settings, clocks, display, drivers or applications were changed.

250 JSON SHA-256:
`240da6964b2f5f3d0d2cff8f8aa0983c174c26595795fec458c53a43c98bf9a9`.

## Post-hoc diagnosis: where the wide allowance comes from

This section examines already completed250; it changes no decision or rule.
Unloaded and loaded controls have overlapping median intervals within each
order. However the loaded BA control's process11 median ratio is0.761215,
giving the BA log allowance0.272839, versus AB0.032020. Its three measured
BA pairs are:

| Pair | B mean us | A mean us | B neutral-work mean us | A neutral-work mean us |
| --- | ---: | ---: | ---: | ---: |
| 4 | 164.171929 | 228.373913 | 29.566176 | 36.579502 |
| 6 | 162.959625 | 170.734397 | 29.566176 | 29.616271 |
| 8 | 167.458173 | 219.987980 | 29.656347 | 34.665866 |

Both arms execute dose1301 and identical image-producing work. In two of
these pairs A is substantially longer. Thus the new inconclusive outcome is
not just the old2% order gate under another label. The observed control
location spread can obscure the intended approximately20% effect under this
conservative interval design. Its min/max construction reserves simultaneous
coverage for96 medians and is sensitive to an extreme process summary; that
is a predeclared precision/power tradeoff, not proof of contamination.

The neutral-work interval is also longer for those A means, but contributes
only part of their full Renderer difference. This does not isolate a pass,
prove clock/load/preemption as the cause, or justify discarding process11.
No arbitrary median independence or nuisance-bias guarantee is claimed beyond
the explicit assumptions of100. Increasing repetitions or changing the
estimator after seeing these outcomes would need a distinct prospective
plan; none is automatically queued.

## Next work and remaining scope

Stop this acquisition method here. Keep existing GPU calibrations and pilot
times diagnostic. No accepted Lane M campaign or revised preflight PASS.
Proceed with the independent missing original CPU physical controls, starting
with the sealed-room artifacts whose unchanged full-count cost236 projects
roughly11–13minutes each on one low-priority CPU. These are cost projections,
not an N010 ETA; the three multibounce sphere cases still project about12CPU
hours each and require a separate bounded execution decision.

References remain16/24; full original physical artifacts remain11/17 at this
checkpoint. A6b IID/bias/all-state/prefix/feasibility, remaining references,
quality ladders/dynamic pilots/truepeak and DDGI scene GI are not supplied by
this timing study. Direct maximum-relative-error1.0 pixels remain
**UNRESOLVED / 未解決**, included in scoring. No N011 or scope reduction.

Build/unit/regression tests: **NOT RUN**. Scientific runtime integrity checks
above were executed. Renderer/shader/default build graph unchanged. No
historical result was rewritten.
