# Lane G — transient LBVH hardening

Issue: #17

This lane starts from `research@1ab3c09f62fc6778aa598a791c4c1a6f720d75f9`.

Lane G is complete.

G001 identified the F007 sparse-memory failure as static-HWRT lifetime overlap,
not an LBVH-capacity problem. G002 diagnosed program-level timing instability
but closed without a safe decision-valid timing protocol after the power-state
isolation experiment was abandoned for host safety.

G003 retained one attributable hardening candidate: build immutable static HWRT
before shared integration allocations, then release its setup-only vertex,
instance and scratch allocations after the fenced build. G004 passed the frozen
16-case semantic matrix. G005 passed all 60 deterministic correctness/memory
rows.

Final disposition:

- sparse-memory blocker: **resolved**;
- correctness / integration semantics: **pass**;
- decision-valid timing: **inconclusive**;
- Lane E replacement: **not claimed**;
- production promotion: **measurement-limited**;
- hardened transient LBVH: **retained research mechanism**.

GPU power/clock sysfs manipulation is not an accepted Lane-G measurement
requirement and the abandoned G002c experiment must not be rerun.

The copied integration/LBVH/grid sources in
`src/research/lane_g_transient_lbvh_hardening/` are an auditable snapshot of
the Lane-F F007 implementation used as the unchanged G001 baseline. Existing
Lane A/B/C source remains shared and unmodified.

## G001 baseline provenance

The executable baseline is code-equivalent to F007 measurement commit
`041bf0287e2095302b61d31b222de958dd3b6412`. Comparing that commit with the
later Lane-F head used to source the snapshot shows only documentation changes;
runtime/source/shader files are unchanged.

Lane A/B dependencies are copied verbatim under
`src/research/lane_g_transient_lbvh_hardening/baseline/` and
`shaders/research/lane_g_transient_lbvh_hardening/baseline/`. No Lane A/B/F
branch is merged and no source in another lane-owned directory is modified.
