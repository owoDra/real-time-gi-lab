# N010 environment-sensitive criteria and retained C7 quality integration

2026-10-18 JST. Source/recipe128 and shared protocol clarification committed
`2b9797c99b50ac0676d6a8d38d6e780a2757d263` before executing407.

## Decision criteria

The user's concern is valid: incidental desktop load, CPU wall time, GPU
busy, clocks and free VRAM must not decide whether a GI architecture is
correct or whether N010 can hand off to comparison. The shared
[protocol](../../../protocol.md#n010-prospective-handoff-amendment-2026-10-18)
now explicitly maps each observation to its role under existing amendment120.
This clarification adds no gate, relaxes no quality/physical/evidence rule,
and changes no historical threshold or FAIL.

GPU Renderer time remains the primary performance axis. It is conditional
on the declared execution regime and must be measured with matched quality,
complete costs and uncertainty. A valid complete pilot can be
TIMING_INCONCLUSIVE without that outcome alone blocking handoff. Invalid or
missing data cannot be called inconclusive to bypass evidence requirements.
Registered run/dispatch guards protect execution; a stop leaves the run
incomplete, not proof that the algorithm intrinsically loses. No further
generic idle/stability campaign or repeat-until-PASS follows from this review.

The legacy final auditor still needs the full120 implementation. This
documentation change does not make it amended or make N010 READY.

## Actual post-hoc evidence integration

[407](407-retained-continuation-c7-quality.json) is a CPU-only, explicitly
post-hoc analysis of already retained403, using unchanged full-image
`score_hdr.score` and the original001 thresholds. It independently replays
403's native receipt, all960 dispatches, full final sample state, archived046
image equivalence and allocation/free lifetimes. It verifies original
physical proof009, all original full-prefix C7_T_B8 payloads/metadata at
8192/16384spp, four seeds, physical state/scene and recomputed convergence
screens through unchanged `reference_provenance`.

| Metric | Retained C7/PT-B8/1024 | Original target |
| --- | ---: | ---: |
| Total whole-image luma NRMSE |1.4430585%| <=5% |
| Indirect whole-image luma NRMSE |5.5749772%| <=10% |
| Indirect signed-sum bias |−0.0598777%| absolute <=5% |
| Scored pixels per component |57600| all57600 |
| Scoring exclusions |0|0 |

The single row's quality outcome is PASS; result407 deliberately keeps
all_pass/accepted_timing/reference_admission=false. Direct NRMSE is
2.825952e-7. Indirect maximum relative error1.651455 and one
GPU-zero/reference-positive indirect pixel remain included. All three
full signed error maps and reference-zero leakage metrics are retained;
the registered aggregate targets were not replaced by a new per-pixel cut.

The same capture's complete GPU envelope2.272286s, active sum0.240545s,
native2.379170s, separate readback0.012262s, persistent sample state921600
bytes and true owned peak3291760bytes/zero teardown remain descriptive.
The active sum excludes yields; it cannot substitute for end-to-end cost.
No fresh paired measurement, known-work calibration or speed inference.

407 ran CPU31/nice15/one numerical thread,3.047832elapsed/1.489596CPU seconds,
peakRSS479880KiB, within120CPU/180elapsed/2GiB bounds. It records577 raw input
hashes and four new score/map payload hashes. No source capture/reference
was rewritten. No new GPU, compiler or oracle acquisition was launched.

## Remaining work

References remain16/24 and original full physical inventory14/17 including
one diagnostic-only item. C1_T_B8 remains ineligible and is not scored here.
One C7 row is not the required static ladder, dynamic histories, chosen
budget comparison, selected-boundary timing pilot or final provenance intake.
Original261 remains live, unchanged native197130/start1882463/session15102,
CPU31/nice15/one worker; no next seed or GPU/compiler is queued. Original259/
260 are two completed A6a seeds; no four-seed physical admission follows.

N010 remains NOT_READY. Direct relative-error1.0 Sponza pixels remain
**UNRESOLVED / 未解決**, included. No tests/default build/runtime regression
checks were run. No N001–N009 results, Actions, power/clock/display/driver/
other-app settings or branch promotion changed. N010 remains the final
preparation lane before the distinct Lane M GI comparison.

Metadata/provenance validation: all577 input and4 new payload hashes
match407; research harness reports8 indexes/312 declared result links.
These checks are not runtime regression validation.
