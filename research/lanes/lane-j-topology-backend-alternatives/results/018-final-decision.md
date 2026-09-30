# Lane J final decision

Status: **COMPLETE — measurement-limited**

Lane J completes J001-J003 and stops before J004/J005 because the mandatory
timing dependency did not produce an accepted architecture-ranking protocol.

## J003 retained result

The sole new structural candidate is the object-local clustered two-level BVH:

- stable logical cluster ownership;
- reusable fixed-capacity physical GPU slots;
- dirty-cluster micro-BVH rebuilds;
- upper refit when membership is stable;
- upper rebuild on split/merge/retire;
- exact triangle refinement under the shared B001 Hit/tie contract;
- explicit persistent/staging/resize lifetime accounting.

One unchanged v1.6 build passed the complete five-profile target-GPU campaign
on AMD Radeon 8060S Graphics (RADV STRIX_HALO):

| Profile | Hit mismatches | Runtime errors | Max candidate true peak resident bytes |
| --- | ---: | ---: | ---: |
| small-global-high | 0 | 0 | 65,680 |
| medium-global-representative | 0 | 0 | 483,104 |
| medium-local-high | 0 | 0 | 470,912 |
| large-global-high | 0 | 0 | 11,059,104 |
| large-local-high | 0 | 0 | 3,932,224 |

The large-global profile exercised the frozen 256 -> 512 physical-slot growth:

- old persistent candidate allocation: 2,645,968 bytes;
- new persistent candidate allocation: 5,291,984 bytes;
- simultaneous old/new candidate overlap: 7,937,952 bytes;
- maximum migration staging allocation: 3,121,152 bytes;
- candidate true peak resident bytes: 11,059,104 bytes.

All 40 frozen snapshots used 4096 exact validation rays each and completed with
zero retained Hit mismatches and zero traversal runtime errors.

## Exact-Hit correction retained

The initial representative persistent-GPU replay exposed one B001 tie-boundary
mismatch. Diagnostic work established that the expected lower-ID primitive was
reached, intersected and selected on the GPU, but later lost because GLSL
triangle-intersection arithmetic drifted across the frozen tie boundary.

Two AABB-pruning hypotheses (v1.4/v1.5) were tested, produced unchanged
behavior, and were reverted.

v1.6 retained the B001 tolerance and primitive-ID tie rule and instead made the
Moller-Trumbore arithmetic strict source-order fp32 with explicit scalar
dot/cross helpers and GLSL `precise` intermediates. The unchanged
representative and all-profile gates then passed.

The watched-primitive payload remains validation-only. It is not candidate
persistent memory and must not be included in any future formal timing build
without an explicitly frozen timing protocol.

## Why J004 is not run

Lane I / Issue #19 is complete with I004 outcome:

**target timing unsuitable** for the frozen dual-axis `lane-i-i002-v1`
protocol.

Lane I demonstrated useful GPU-timestamp mechanism evidence down to the tested
5% known-work delta, but complete CPU wall failed the frozen dual-axis
acceptance rule. The program therefore has no accepted timing protocol or
measurement floor that Lane J may import for formal architecture ranking.

Issue #20 explicitly forbids J004 until such a protocol exists. Historical
Lane E/G timings and J003 diagnostic timestamps cannot substitute for run-local
decision-valid comparator evidence.

## J005 disposition

J005 requires a candidate retained by J004. Since J004 is not legally run,
J005 is also not run.

The J003 clustered candidate is therefore **correctness- and absolute/lifetime-memory-qualified for future crossover**, not integrated or promoted into the Lane E production architecture.

One frozen J003 eligibility item remains to be completed before formal J004 timing: plan-v1 requires candidate `persistent_bytes` and `true_peak_resident_bytes` to be <=1.25x a **same-run Lane-E HWRT rebuild comparator**. The all-profile J003 campaign established the candidate's own absolute/lifetime memory and resize overlap, but did not include that same-run comparator. A future J004 preflight must complete this relative memory gate; timing may not rescue a failure.

## Final architecture disposition

- **Lane E object-local ownership/update semantics remain incumbent.**
- **Clustered two-level BVH becomes a correctness- and absolute/lifetime-memory-qualified future topology-changing backend candidate; its frozen same-run <=1.25x Lane-E HWRT relative-memory eligibility remains pending.**
- **Hardened transient LBVH remains a correctness/memory-qualified control.**
- **No topology-changing backend performance winner is declared.**
- **Lane J final outcome: measurement-limited.**

A future crossover may reopen J004 only after a new architecture-neutral
measurement campaign pre-freezes and accepts a reusable timing protocol
(for example, a GPU-primary protocol with CPU wall diagnostic-only). That
future methodology must be calibrated before any competing backend timing is
used for promotion.

Diagnostic traversal timestamps produced during J003 are not formal ranking
evidence.
