# N010 retained dynamic cohort: all histories replayed, quality losses retained

2026-10-18 JST. Explicitly **post-hoc CPU-only evidence replay**, not fresh
GPU acquisition or an accepted performance comparison. Recipe133 and its
driver were committed at `ef2f1ae1` before any cell replay.

## Actual completed scope

[418](418-retained-dynamic-c8-proof.json), [419](419-retained-dynamic-c9-proof.json),
[420](420-retained-dynamic-c10-proof.json), [421](421-retained-dynamic-c11-proof.json)
and [422](422-retained-dynamic-c12-proof.json) independently replay every
retained019/037 row for C8 through C12. Each terminal part was reviewed
before manually starting the next cell. [423](423-retained-controlled-dynamic-cohort-proof.json)
then rechecks all part inputs/outputs and exports one canonical dynamic cohort.

There are35 retained rows:34 actual native histories,170 frames,265 full-image
transport scores and the original C12 software UNSUPPORTED_IN_CAPTURE_API
placeholder. All original B2/256 losses remain beside the later B2/1024
histories. No role, cell, transition or recovery frame was selected away.
C8 is camera motion, C9 light motion, C10 moving rigid, C11 stable-topology
deformation and C12 topology churn of the controlled scene.

All265 recomputed component metric dictionaries, quality classifications,
image hashes and795 complete signed error-map bytes match the originals.
Every component scores all57600 pixels with zero exclusions. Original001
total NRMSE<=5%, indirect NRMSE<=10%, absolute indirect signed-sum bias<=5%
are unchanged. All reference-zero leaks and per-pixel extremes remain.

| Retained role and budget | Quality PASS scores | Quality FAIL scores |
| --- | ---: | ---: |
| Incumbent HWRT, both transports |0|50|
| Incumbent software, both transports; C12 unsupported |0|40|
| Vanilla traversal, both transports |0|50|
| Dense RC, both transports |0|50|
| Pixel PT B2/256 |17|8|
| Pixel PT B2/1024 |25|0|
| Pixel PT B8/1024 |25|0|
| Total |67|198|

The B2/256 failures are the four changed/recovery frames in each C8/C9.
The other three cells pass that retained budget. No observation is retuned.
Both1024spp PT histories meet the registered aggregate quality targets on
all five frames in every retained cell. The supported incumbent captures
do not meet those targets. This identifies a quality limitation in this
controlled retained scope; unequal-quality timings cannot establish a fair
speed ranking, and this is no general GI superiority or Lane M result.

## What was independently checked

- Original019 lock016 and037 lock026 digests, every actual capture payload,
  role/command/budget/seed/source identity and all five raw/saved frame costs.
- Complete canonical geometry bytes. PT/dense frame bytes are exact; RC
  frame bytes differ only by the original final frame-ID word, whose value
  must equal frame index+1. All other bytes match026, and the unchanged
  scorer requires COMPLETE derived physical-scene bytes at both transports.
  This is not a physical-scene tolerance or a scoring mask.
- Twelve original eligible reference chains (C7 source and C8–C12 targets,
  both transports),009 physical proof, full-prefix metadata/payloads/seeds,
  original convergence screens and unchanged qualification digests.
- Actual allocation/free lifetimes and true peak, all device contexts and
  zero teardown for every native. Owned peaks range2370160–266937920 bytes;
  all are within the original8GiB cap. Global free VRAM is not substituted.
- Published pinned N-series source/shader subtrees at the actual capture
  commits and HEAD. Historical host/wrapper/source and binary identities
  remain provenance; old overwritten binary bytes were not recovered.
  Unchanged core trees do not establish identical host/timing wrappers.

The five cell processes together used82.301715 elapsed /39.071794 CPU
seconds; aggregate used8.180729 /4.066828. Each process ran CPU31/nice15,
one numerical thread, peakRSS479880KiB, within120CPU/180elapsed/2GiB.
They shared the existing original261 CPU; no GPU/compiler/oracle acquisition
was added. All1065 per-cell outputs (795 maps,265 scores,five pilots), the
combined canonical pilot and4380 aggregate input identities are retained
and hash-checked. Original evidence bytes are unchanged.

## Effect on the completion path

Canonical input for the final dynamic gate is
`out/research/n010-comparison-readiness/retained-dynamic-proof-v1/aggregate/canonical-cohort.json`.
It preserves the original preflight row schema and all35 rows; its
`full_required_corpus=false` is deliberate. C2–C6 are absent and must still
block the full-corpus gate. Neither this export nor source assembly is a
completed final audit. all_pass/accepted_timing/reference_admission stay false.

This removes the need to reacquire the same C8–C12 quality images merely to
populate pilot inputs.132's selected1024spp rule used C7/C8/C9 tuning only;
this replay of historical C10–C12 is post-hoc held-out observation, not a
new blinded acquisition, independent geometry or prospective validation.
The new401 continuation implementation still needs actual five-frame
execution/conformance and its own selected-boundary timing proof. Historical
timings here are descriptive and do not qualify that implementation.

Under120, a complete valid selected-boundary timing pilot may terminate
TIMING_INCONCLUSIVE without that alone preventing handoff. Missing/invalid
evidence still blocks; performance claims still require actual-boundary
calibration, matched quality and registered uncertainty. CPU wall, GPU
busy/clocks, other-app load and free VRAM remain diagnostics. No generic
stability/idle threshold campaign follows from these results.

Full obligations remain: all24 eligible references (currently16), original
physical proof14/17 including one diagnostic-only item, all-split
physical/state/prefix/full-count admission, C1 B8 reference/six-row ladder,
C2–C6/all-family dynamic coverage, selected execution/timing evidence and
the final120 auditor. N010 is **NOT_READY**, followed by the distinct Lane M;
no N011 or reduced corpus. Sponza direct relative-error1.0 pixels remain
**UNRESOLVED / 未解決**, included in scoring.

Original261 was observed live as PID197130/start1882463/session15102,
CPU31/nice15,51:14 CPU at52:45 elapsed. It was not restarted; no next seed,
GPU or compiler is queued. No N001–N009 results, Actions, default build,
power/clock/display/driver/other-app settings or architecture promotion changed.

Build, unit/regression tests and new runtime smoke checks: **NOT RUN**.
This is scientific archived-data/provenance replay. The separate metadata
index/link check reports8 indexes/328 declared result links, and
`git diff --check` is clean. These checks do not establish runtime regression
validation.
