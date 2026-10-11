# H001 — Safe timing methodology result

Status: **closed / INCONCLUSIVE**  
Measurement commit: `5664abba21875fbe273474fe14034b31156d74b1`  
Plan: `lane-h-h001-safe-timing-v1`

## Accepted provenance

The target run completed on `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`
with Mesa 26.1.2 / RADV, Vulkan validation disabled, a clean worktree, and the
frozen H001 configuration. The run retained all 3,072 frame rows and all 96
fresh-process summaries.

The frozen campaign rule was all-or-nothing: every case/variant row had to pass
all GPU and CPU-wall repeatability criteria. The instability rerun budget was
zero.

## Static-control repeatability failure

The static control does not depend on the dynamic-transition semantics described
below. All four implementations fail at least one frozen repeatability gate:

| Variant | GPU failures | Wall failures |
| --- | --- | --- |
| hardened transient LBVH | p90/p10 1.267, first/last 1.233, fresh max/min 1.115 | p90/p10 9.492, first/last 3.648, fresh max/min 1.313, MAD/median 0.064 |
| transient LBVH | p90/p10 1.151, fresh max/min 1.124 | p90/p10 1.378 |
| combined HWRT | p90/p10 1.125 | p90/p10 1.484, first/last 1.218 |
| vanilla software | p90/p10 1.108 | p90/p10 1.172 |

The frozen limits were 1.10 for GPU p90/p10, first/last, fresh max/min and slot
ratio, 0.04 for GPU MAD/median; and 1.15 / 0.06 for the corresponding wall
criteria. Therefore H001 cannot pass even if the dynamic-case harness defect
were ignored.

Host-load observations remained modest (1-minute load average 0.958–1.358 and
available memory about 126.8–127.5 GB), but H001 intentionally defined host
state as observational rather than a post-hoc exclusion gate. No sample is
removed on that basis.

## Dynamic-case semantic defect discovered in review

The frozen v1 plan stated that alternating `target_state=false/true` would make
every measured dynamic frame cross the update boundary. The reused Lane G
`I001Runtime` is one-way for this transition:

- `update_dynamic_geometry()` returns without updating when
  `target_state == false`;
- after the first target update it sets `geometry_is_target = true`;
- later `target_state == true` calls also return without another geometry
  update.

The target artifacts confirm the mismatch. For each dynamic case and each
variant, exactly one non-zero dynamic update occurred per fresh process during
warmup (8 total over the 8 processes), while **zero measured frames** contained
a non-zero dynamic update.

Accordingly the moving-rigid and topology-replace25 rows are not accepted as
repeated-transition timing evidence. This is a harness/workload semantic defect,
not evidence about the relative topology-rebuild candidates.

A separate provenance bug was also found in the H001 executable: the GPU banner
used a multi-character newline literal, which emitted `23662` instead of a
newline. This corrupted the shared recorder's parsed GPU string. The per-process
device JSON and raw-frame device columns remain correct and show the exact
target GPU.

## Decision

H001 is **INCONCLUSIVE** and `repeatability_passed=false`.

No instability rerun is permitted. A corrected dynamic harness is not rerun as
a replacement result because the valid static controls already failed the
pre-frozen repeatability gate; rerunning after observing that failure would
create another opportunity to pass by chance.

Therefore:

- H003 formal timing remains forbidden;
- no topology backend can be promoted from Lane H timing;
- H002 contract/correctness scaffolding remains useful preparation but cannot
  produce a timing winner in this lane;
- Lane H closes as **measurement-limited** unless a future, separately planned
  research lane establishes a new decision-valid safe timing protocol before
  observing its target results.
