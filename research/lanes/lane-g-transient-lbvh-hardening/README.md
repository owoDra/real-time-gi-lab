# Lane G — transient LBVH hardening

Issue: #17

This lane starts from `research@1ab3c09f62fc6778aa598a791c4c1a6f720d75f9`.

G001 completed the memory ownership/lifetime census. G002 then diagnosed
program-level timing instability but closed without a safe decision-valid timing
protocol after the power-isolation experiment was abandoned for host safety.

G003 is now active. Memory candidates must be directly attributable to G001,
must retain the unchanged `transient-lbvh` run-local control, and must not use
GPU power/clock sysfs manipulation. Timing remains non-decision-valid until a
separately accepted safe protocol exists.

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
