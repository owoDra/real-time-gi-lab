# D001 — renderer visibility reuse boundary

Status: active

## Question

How much of accepted A001 producer cost can be removed when renderer visibility
already exists, and which visibility information must the renderer expose for
that saving to be real?

This experiment deliberately keeps A001's surface-scan emission. Eliminating
that rescan belongs to D002 so the two effects can be measured independently.

## Baseline delta

Accepted A001 performs, in order:

1. clear depth, owner, counters, and accumulation buffers;
2. scan every source surface for nearest tile depth;
3. scan every source surface again for deterministic nearest owner;
4. scan every source surface a third time and let visible owners emit work;
5. finalize indirect dispatch arguments.

A001's recorded `visibility_depth` timestamp includes the initial transfer
clears/barrier, so D001 adds explicit stage boundaries rather than interpreting
that number as depth-kernel-only time.

D001 compares three regimes while leaving schema-v1 work semantics unchanged:

- **full**: GI pays visibility reset + depth + owner selection;
- **depth-reuse**: renderer depth is already available; GI pays owner
  reset/selection because surface identity is unavailable;
- **owner-reuse**: renderer nearest surface ID/owner is already available; GI
  skips both visibility scans.

For reuse modes, renderer visibility is prepared with the same A001 semantic
reference before timing. The incremental number excludes that external work.
The same run also reports a standalone full-cost boundary by adding the measured
visibility prerequisite back.

## Hypothesis

Owner/surface-ID reuse will materially reduce incremental producer and
end-to-end cost because A001 otherwise performs two full source-surface
visibility scans. Depth-only reuse may save less because deterministic owner
selection still rescans all source surfaces.

If owner reuse is still dominated by the unchanged all-surface producer emit,
that is evidence for D002 rather than evidence to hide emit cost.

## Correctness gate

Every static, camera-motion, and light-motion case must satisfy all of:

- A001 CPU visibility reference for the visibility input used by the candidate;
- identical visible-owner set to the A001 semantic reference;
- identical work-item and output counts;
- every emitted block passes existing A001 schema-v1 semantic checks;
- no output holes, duplicate visible tiles, overflow, or fallback activation;
- downstream gather/merge/resolve passes the A001 reference tolerance;
- stream order/locality is measured from natural GPU append order with no CPU
  sort or post-generation reorder.

Exact byte-for-byte inter-owner stream order is not required because A001's GPU
append order is intentionally nondeterministic. Semantic block contents and
counts are required to match.

## Measured boundary

D001 records separately:

- visibility reset/clear;
- depth visibility;
- owner reset/clear;
- owner selection;
- GI producer reset/clear;
- producer emit;
- finalize/synchronization;
- producer total;
- renderer prerequisite cost;
- incremental GI producer cost for each reuse regime;
- standalone full producer cost;
- gather, merge, resolve, and downstream end-to-end;
- work-item/output/visible-owner counts;
- natural stream locality statistics;
- GI-owned persistent/transient/scratch/peak stream bytes;
- reused renderer visibility bytes;
- overflow/fallback counters.

The unchanged A001 worst-case stream allocation remains charged in D001.
Capacity reduction belongs to D005.

## Target workload

- real Sponza;
- static;
- camera-motion;
- light-motion;
- AMD Radeon 8060S Graphics (RADV STRIX_HALO);
- validation enabled for diagnostic bring-up, then disabled for accepted timing;
- at least 3 process-level repeats, 50 timed iterations per case unless variance
  requires more.

## Retain / reject criteria

Correctness failure rejects the affected mechanism.

A reuse mechanism is retained for composition only when, relative to the
same-run full baseline:

- median incremental producer total improves by at least 10%; and
- median incremental downstream end-to-end improves by at least 5%; and
- adding its measured visibility prerequisite back does not regress standalone
  end-to-end by more than 5%; and
- no hidden CPU work, global reorder, or unaccounted GI-only visibility
  attachment is required.

A result below 5% producer-total improvement is rejected as immaterial for this
lane. Results between the reject and retain thresholds are inconclusive and do
not promote a mechanism without a follow-up explaining the uncertainty.

D001 does not decide the final Lane D producer. It decides which renderer
visibility contract, if any, is worth carrying into D002+.
