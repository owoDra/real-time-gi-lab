# J004 formal crossover gate v1

Status: **FROZEN BEFORE ACCEPTED CANDIDATE TIMING**
Issue: #23
Predecessor: Lane J / #20, J001-J003 complete
Measurement dependency: Lane K / #21

This record is the decision gate for the J004-equivalent topology-backend
crossover. It is frozen before any accepted architecture timing on this branch.
Historical Lane E/G/J timing and J003 diagnostic traversal timestamps are not
decision evidence.

## Imported Lane-K methodology

The Lane-K branch is **not merged wholesale**. This gate imports only the
accepted measurement contract.

Canonical references:

- program source-of-truth after Lane K:
  `research@ff375b43f34db8b49371ab1a73299999f9677778`;
- K002 freeze commit:
  `c886d0f33f63de131da9db3757f2c0b05c7c2634`;
- K002 frozen config blob:
  `08657f3e176128a73c6f7f4d1769bab3f1eff7ad`;
- K003 accepted measurement commit:
  `0cab088ed2316ba38497b1aa92a8a507638471f5`;
- K004 final Lane-K result commit:
  `eff91667ba5d8dd33e1730216cfa26b21c994f27`;
- K004 result document:
  `research/lanes/lane-k-gpu-primary-calibration/results/004-program-timing-capability.md`;
- accepted protocol name: `lane-k-k002-v1`;
- measured target:
  `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- smallest demonstrated safe effect size: **5%**.

## Measurement axes

### Primary decision axis

**GPU timestamp over the complete recurring J004 GPU boundary.**

No CPU-wall statistic can promote or reject a backend for speed when the GPU
primary gates pass.

### CPU-wall semantics

Complete CPU wall is diagnostic / health / provenance only.

CPU wall invalidates a campaign only for a structural failure inherited from
Lane K:

- non-positive or non-finite timing;
- incomplete pair/sample structure;
- complete CPU wall smaller than the covered GPU timestamp;
- inconsistent device/driver/API/timestamp provenance;
- process failure.

CPU-wall repeatability warnings are retained and reported but do not veto a
valid GPU-primary decision.

## Frozen workload and equality constraints

J004 reuses J002 exactly. No profile, geometry, primitive ID, producer ordering,
ray stream, Hit semantics, storage path, or static-world state may be changed
after this freeze.

Every formal variant consumes the same:

- five J002 topology profiles;
- complete eight-snapshot cyclic topology sequence;
- exact geometry bytes and primitive IDs/count;
- A001 natural append producer stream/order;
- query/ray stream;
- exact B001-compatible Hit/nearest-hit/tie semantics;
- C001 storage state/path;
- immutable static world and unrelated owners;
- recurrent update boundary;
- allocation lifetime accounting.

A timed sample may aggregate multiple complete transitions, but it may not
prebuild, pre-upload, or preprocess future topology outside that sample's
recurring boundary.

## Formal same-run variants

Frozen variant set:

1. `lane-e-object-local-hwrt-rebuild`;
2. `lane-e-object-local-software-b003-rebuild` where practical;
3. `hardened-transient-lbvh`;
4. `clustered-two-level-bvh`, only after the relative-memory preflight passes;
5. `transient-lbvh-unchanged` where attribution requires it;
6. `vanilla-accounting-control`.

No target result may add or remove a promotion candidate. A variant found
impossible to implement under semantic parity is retained as an explicit
not-practical/not-applicable result rather than silently omitted.

## Hard pre-timing relative-memory eligibility

The J003 clustered candidate has **not** passed this gate yet.

Before any clustered-candidate formal timing, collect a same-run memory replay
against `lane-e-object-local-hwrt-rebuild` using the same J002 snapshots,
allocation-lifetime census, and transition boundary.

For every required J002 profile:

- candidate `persistent_bytes <= 1.25 * comparator persistent_bytes`;
- candidate `true_peak_resident_bytes <= 1.25 * comparator true_peak_resident_bytes`;
- no unbounded monotonic allocation growth;
- after a complete repeated cycle, live ownership returns to the declared
  persistent baseline.

Failure is a hard rejection for the clustered candidate in J004. Timing cannot
rescue it. Candidate-only J003 memory numbers are insufficient.

## Frozen timing shape

Lane K's accepted timing structure is reused without target-result-driven
changes.

For each formal **profile + control/candidate comparison**:

- batch length: **16 complete recurring topology transitions per timed sample**;
- the J002 eight-snapshot sequence is traversed cyclically in its frozen order;
- every batched transition remains inside the recurrent boundary;
- warmup: **4 paired samples per fresh process**;
- measured: **12 paired samples per fresh process**;
- fresh-process blocks: **8**;
- pairing: A/B and B/A;
- block/order schedule: position-counterbalanced before execution;
- settle: **1 second before each fresh process**;
- all raw warmup and measured rows retained;
- sample exclusion: **forbidden**;
- instability rerun budget: **0**;
- completed-campaign rerun budget: **0**.

A process may not continue from a partially completed measured pair. An
interrupted campaign is incomplete evidence; retained partial rows remain
diagnostic and the accepted campaign must start from a new complete frozen
campaign identity, not from favorable-row selection.

## Primary statistic and repeatability

For each fresh process, compute the median paired
`log(candidate_gpu / control_gpu)` over the 12 measured pairs.

Campaign effect is the median of the eight fresh-process medians.

Before candidate promotion, the matching control/control health comparison for
that track/profile must pass:

- max absolute process-median ratio <= **1.02**;
- process-median span ratio <= **1.03**;
- max within-process order-bias ratio <= **1.02**.

Candidate comparison repeatability must pass:

- process-effect span ratio <= **1.05**;
- max within-process order-bias ratio <= **1.03**;
- at least **75%** of measured pairs show improvement in the declared direction;
- every fresh-process median improvement must exceed the accepted control noise
  envelope used by the imported Lane-K rule.

If a repeatability gate fails, that profile/track is **inconclusive**. No sample
is removed and no rerun is permitted.

## Promotion threshold

The J004 promotion threshold is frozen at **5% complete-GPU improvement**.

A candidate passes the performance threshold only when:

`exp(campaign_median_log_ratio) <= 0.95`

in addition to all control and candidate repeatability gates.

Effects between 0% and 5% are not promotion evidence. A candidate may still be
reported as numerically faster/slower diagnostic context, but J004 treats it as
no demonstrated crossover.

Non-regression for a candidate retained in one class but exercised in the other
class is also frozen at the Lane-K resolution boundary:

`exp(campaign_median_log_ratio) <= 1.05`

with the same repeatability requirements. A >5% regression is a hard
class-retention failure.

## Primary and software-fallback tracks

Two tracks are evaluated without mixing comparators:

### Primary topology track

Incumbent control:
`lane-e-object-local-hwrt-rebuild`.

Eligible alternatives:
- `clustered-two-level-bvh` if memory-eligible;
- `hardened-transient-lbvh`;
- unchanged LBVH only for attribution, not as a preferred production promotion
  unless it independently passes all gates.

### Software fallback track

Incumbent control:
`lane-e-object-local-software-b003-rebuild`.

Eligible alternatives:
- `clustered-two-level-bvh` if semantic parity and memory eligibility hold;
- `hardened-transient-lbvh`.

A software-fallback win does not replace the primary HWRT topology path.

## Frozen class-conditional selector rule

Selector classes use only the J002-frozen **locality** field. No timing-derived
size or dirty-fraction threshold may be introduced.

- `global-topology-churn`:
  `small-global-high`, `medium-global-representative`,
  `large-global-high`;
- `local-topology-churn`:
  `medium-local-high`, `large-local-high`.

A backend is retained for one class only if it:

1. passes correctness, ownership, workload identity, accounting, and memory
   gates for every profile in that class;
2. passes the 5% promotion threshold and repeatability gate for **every** profile
   in that class against the appropriate incumbent track;
3. does not regress the other locality class by more than 5% on any required
   profile where the backend is exercised;
4. does not require a post-hoc object-size, triangle-count, dirty-fraction, or
   candidate-internal selector.

If these conditions do not hold, the incumbent Lane-E rebuild remains selected
for that class. A one-profile win cannot create a new selector threshold.

## Correctness/accounting hard gates

Every accepted formal row requires:

- visibility mismatch = 0;
- producer semantic error = 0;
- Hit mismatch = 0;
- nearest-hit/tie mismatch = 0;
- traversal runtime error = 0;
- storage failure = 0;
- immutable-owner mutation = 0;
- exact workload digest match;
- memory/lifetime census complete;
- recurrent work kept inside the complete update boundary.

Correctness, ownership, workload, or hard-memory failure rejects the affected
candidate before timing interpretation.

## Forbidden

Permanently forbidden in this campaign:

- historical E/G/J timing as formal evidence;
- J003 diagnostic timing for ranking;
- workload/profile edits after this freeze;
- outlier deletion;
- fastest-subset selection;
- favorable reruns;
- post-hoc thresholds or selector rules;
- recurrent allocation/upload/build/sort/sync hidden in setup;
- `profile_peak`, `power_dpm_force_performance_level`, forced clocks/power,
  privileged GPU power/clock sysfs writes.

## J005 entry condition

J005 may start only if J004 formally retains at least one candidate in at least
one frozen locality class/track.

J005 must preserve Lane E geometry-class ownership:

- static path unchanged;
- rigid transform/instance-only path unchanged;
- stable-topology deforming UPDATE path unchanged;
- new backend only for the J004-retained topology-changing class;
- fallback to Lane E rebuild outside the retained class.

If no candidate is retained, J005 does not run and the final result records the
appropriate incumbent/rejection/inconclusive disposition.
