# Prospective light-surface reference acquisition and full-corpus admission

Date: 2026-10-15 JST. Parent checkpoint: `26cb98e`.
The local draft was created at 01:48 UTC while physical 145 was acquiring;
this record is first committed after 145/146/147 completed. No corpus
acquisition was dispatched. It prepares a conditional N010 admission path,
not N011 or Lane M, and does not revise plan 040 or its frozen threshold.

**INACTIVE:** 147 fails plan 040's two-level feasibility rule: its 8192 ratio
is 0.7575396423, above 0.75, even though 16384 passes at 0.7462398911.
The candidate stops. The prepared code must refuse corpus acquisition on this
result; it is retained as unexecuted admission machinery, not a qualified path.
Any later distinct candidate requires new prospective registration.

## Dispatch barrier and fixed targets

Require complete PASS 144/145/146/147, actual artifact/input hashes and exact
scope: seventeen physical scenes/four seeds, eight physical gates, two iid
comparisons, all 24 low-dose states, both actual C7 prefix cases and 78 native
state/prefix invocations. Feasibility must preserve full support and reduce
active absolute p99 uncertainty by at least 25% at both 8192/16384 levels under
plan 040. That is a practical feasibility condition, not statistical eligibility.
No acquisition on a missing, failed or partial prerequisite, and no retry.

Prospectively select all nine unfinished targets in order: C1 B8, C2 B8,
C3 B8, C4 B2/B8, C5 B2/B8, C6 B2/B8. Retain the exact fifteen eligible original
targets from scheduling map 067. A fresh map selects these nine light-surface
targets and the same fifteen original targets within the complete 24-slot
corpus. This selection precedes feasibility outcomes and new GI scores; no
selection based on quality wins/losses, no scene deletion or view-127 mutation.
The already qualified independent hybrid C4 B2 remains separate evidence.

Use a new `light-surface-reference-ladders-v1` root and computational variant
`validated-light-surface-mixture`, with the exact standalone/prefix binaries
from 144. Import only the complete C1 B8 own-proposal 8192/16384 outputs from
147; never import cosine, global-guide or hybrid samples/moments. Preserve
every original 147 byte. Copy payloads byte-exactly into the new root and retain
the actual original command, raw metadata, resource receipt, stdout/stderr and
source-result identity. Enriched import metadata must explicitly distinguish
the copy from a new native invocation. Verify both imported levels through the
same canonical scene/header/mean/moment/component/primary/counter and unchanged
screen checks before continuing their own prefix. Never synthesize a native
command claiming the copy was rendered in the destination directory.

## Sampling, resource and stop rules

Use the original four N007 seeds, levels 8192/16384/32768/65536/131072/262144,
all pixels and all five saved counters. Other eight slots start with fresh
8192 samples. Continue only complete prefixes produced by this exact binary
and proposal, with exact predecessor metadata/payload hashes. No tuning of
the mixture or transport evaluator. Keep every mean, second moment, primary,
component PFM, command, stdout/stderr, interval and source/proof identity.

Sixteen threads, 4 GiB address space, 691200 aggregate CPU seconds and 43200
elapsed seconds per native invocation match the prospectively registered
plan-040 feasibility bounds. Preserve actual fresh-child resource receipts.
These are offline costs, never Renderer performance evidence. Runtime,
provenance or identity failure stops with partials retained and no automatic
retry. A complete statistical cap failure remains INELIGIBLE and does not
remove that slot or prevent acquiring the other fixed targets.

Replay the original support-aware screen: active absolute p99 <=1e-5,
relative p99 <=5%, stable support, two consecutive qualifying levels, stop at
the first qualifying pair. Imported levels count toward this same ladder and
are not re-rendered. Four independent replicate means supply uncertainty;
do not treat RQMC samples as iid. No post-hoc threshold or cap changes.

## Full comparison barrier and handoff

The separate provenance API delegates unchanged original references to the
existing CPU/hybrid API. For the new variant it replays all original numerical
and provenance gates, plus explicit feasibility-import and resource checks.
It must check actual prerequisites and payloads, canonical states/scenes,
headers, finite/nonnegative means/moments, every PFM against binary64 rounding,
primary records, actual commands/stdout, counters, prefix chains and exact
screen inputs/classification/first qualifying stop. A scheduling map with
pending targets is never an admission result.

Before a new pilot, require all 24 exact map targets eligible, full provenance
PASS and actual CPU/GPU acquisition termination/quiescence. Freeze every read
identity and save a full admission record. Keep the original cohort commands,
16 complete timing boundaries, quiet sizing, eight-process accepted calibration,
memory/quality conditions, single-attempt outputs 043/044/048/046/029/047 and
all six final readiness gates. The new adapter changes reference dispatch and
its explicit provenance only. No automatic publication of READY from reference
or feasibility success. Sponza direct max-relative-error-1.0 pixels remain
included and **UNRESOLVED / 未解決**. Quality failures remain losses.

Final N010 decision and actual READY are still required before the distinct
Lane M campaign. No power/clock changes, CUDA, Actions, default build promotion
or changes to N001–N009 outcomes. The stopped old roots/workflows remain
historical; this plan does not restart or overwrite them.
