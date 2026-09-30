# J004 formal crossover — final target campaign

Status: **COMPLETE — measurement-limited; J005 ineligible**
Issue: #23
Target artifact:
`out/research/lane-j-topology-backend-alternatives/004-formal-crossover/20260930T121921Z/`

## Provenance

- branch: `research-lane-j-formal-crossover`;
- commit: `e1b3c9f0a23f96fa7f54518a2af1a15138f424b3`;
- dirty: false;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- driver: RADV / Mesa 26.1.2;
- experiment return code: 0;
- wall duration: 802.288086 s;
- device/driver/API/timestamp provenance: consistent;
- all samples retained;
- sample exclusion: none;
- instability rerun budget: 0;
- completed-campaign rerun budget: 0.

## Correctness

The v7 B001 tie-pruning repair resolved the retained pre-timing failure.

All 25 hard validation rows pass across five profiles and both decision tracks:

- visibility mismatches: 0;
- producer semantic errors: 0;
- Hit mismatches: 0;
- nearest-hit/tie mismatches: 0;
- traversal runtime errors: 0;
- storage failures: 0;
- immutable-owner mutations: 0;
- workload identity matches: true.

The campaign therefore entered formal timing legitimately.

## Campaign completeness

The formal campaign completed all frozen fresh-process work:

- primary track: 5 profiles x 2 comparisons x 8 blocks = 80 processes;
- software track: 5 profiles x 3 comparisons x 8 blocks = 120 processes;
- total: **200 processes**;
- every process contributes 4 warmup + 12 measured pairs;
- total raw rows: 6,400;
- measured rows: 4,800;
- warmup rows: 1,600;
- measured order rows are exactly balanced: 2,400 AB / 2,400 BA.

No row was dropped or rerun.

## Frozen GPU-primary result

The frozen control-health gate requires:

- max absolute process-median ratio <= 1.02;
- process-median span ratio <= 1.03;
- max within-process order-bias ratio <= 1.02.

Every primary and software profile failed control health. Therefore no candidate
comparison is formal promotion/rejection evidence, regardless of raw effect
magnitude.

| track | profile | control max abs | control span | control order bias | candidate campaign B/A |
| --- | --- | ---: | ---: | ---: | ---: |
| primary | small-global-high | 1.0831 | 1.0955 | 1.1021 | 1.0665 |
| primary | medium-global-representative | 1.0687 | 1.0870 | 1.0893 | 1.2080 |
| primary | medium-local-high | 1.0498 | 1.0557 | 1.0950 | 1.2152 |
| primary | large-global-high | 1.1053 | 1.0924 | 1.1344 | 2.8958 |
| primary | large-local-high | 1.0537 | 1.0922 | 1.1478 | 2.8564 |
| software | small-global-high | 1.0399 | 1.0615 | 1.0911 | 1.3398 |
| software | medium-global-representative | 1.0906 | 1.1560 | 1.1289 | 1.2905 |
| software | medium-local-high | 1.0987 | 1.1727 | 1.1307 | 1.2037 |
| software | large-global-high | 1.0310 | 1.0579 | 1.0543 | 1.5155 |
| software | large-local-high | 1.0324 | 1.0429 | 1.0355 | 1.3547 |

Thus all four frozen locality/track class decisions are `retained=false`.

## Diagnostic direction only

The hardened transient LBVH campaign median ratio is >1.0 in every one of the
ten profile/track comparisons. Nine of ten comparisons also have every one of
their eight fresh-process medians >1.0; only
`primary/small-global-high` has one process median slightly below 1.0.

This is strong diagnostic evidence that the measured LBVH path is not showing
the intended speed crossover, especially for large primary profiles. It is not
promoted to a formal rejection because the pre-frozen control-health condition
failed.

The vanilla software accounting control is also slower than the B003 software
control on every profile, with process-median GPU ratios roughly 1.06x–1.84x.
It remains diagnostic/attribution-only as frozen.

## Why this remains measurement-limited

Lane K calibrated its paired GPU timing inside one Vulkan context/runtime
environment. J004 instead gives role A and role B independent Vulkan contexts
and independent FormalRuntime instances, while alternating AB/BA execution.

That difference was introduced to keep A/B memory/lifetime accounting
independent, but it was not itself calibrated by Lane K. The across-the-board
same-variant control failures show that the J004 comparison environment exceeds
the imported 2%/3% control-noise envelope.

This result does **not** retroactively change the J004 gate, relax thresholds, or
permit a favorable rerun. The completed campaign is retained exactly as
measurement-limited evidence.

## Decision

Formal J004 outcome:

- clustered two-level BVH: already rejected before timing by the frozen relative
  memory gate;
- hardened transient LBVH: **not retained** in any frozen locality/track class,
  because formal control health was not satisfied;
- no post-hoc selector is introduced;
- `outcome = measurement-limited`;
- `j005_eligible = false`;
- **J005 must not run**.

Lane E object-local topology rebuild remains the research-program incumbent by
lack of accepted replacement evidence, not by a new J004 performance-win claim.

## Follow-up boundary

Any further topology-backend ranking requires a new prospective experiment that
first proves same-variant control stability for the actual heavy J002 recurring
boundary. It must not reinterpret or rerun this zero-rerun J004 campaign.

The first hypothesis to isolate is the methodological difference between
Lane-K's one-context pairing and J004's two-independent-context pairing.
