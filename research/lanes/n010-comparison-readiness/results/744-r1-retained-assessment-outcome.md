# R1 assessment of retained ladders (744)

2026-10-20 JST, plan [174](../experiments/174-scoring-aligned-reference-eligibility-amendment.md)
(registered `cbedeb0`, before any R1 statistic). CPU analysis of retained bytes only.

- [744 C1/C2 T_B8](744-r1-retained-c1-c2-b8.json): original digital-shift oracle ladders
  `references-recovery-sponza-v1/C1_T_B8` and `references-recovery-dynamic-v1/C2_T_B8`.
  Both **R1_STATISTICALLY_ELIGIBLE at16384** (8192 and16384 both pass, support stable).
  C1 total/indirect reference-noise NRMSE 0.00384/0.00495 at8192, 0.00268/0.00345 at16384;
  C2 0.00385/0.00498, 0.00269/0.00349 (limits0.005/0.010). Original classification
  remains **INELIGIBLE** (pairwise p99 screen, 743) and is stored verbatim beside R1.
- [744 consistency](744-r1-consistency-original-16.json): all16 originally eligible slots
  also satisfy R1 (first pair at16384 for every slot). Non-gating; their original
  eligibility levels are unchanged and remain the levels used for scoring.

C1/C2 T_B8 use the16384 level per R1's first-qualifying-pair rule; the retained
32768/65536 levels are not used. Physical admission rests on the unchanged original
oracle controls (003/009/022/050). Remaining missing: C3/C4 T_B8, C5/C6 T_B2/T_B8,
acquired under174 (745). Tests NOT RUN.
