# Amendment R1: scoring-aligned reference eligibility

2026-10-20 JST. Explicit user decision after743 ("適格基準を前向きに修正").
Registered before any R1 statistic is computed on any slot. This is an
**amendment to001's statistical eligibility screen**, motivated post-hoc by743;
it is not a claim that any slot passed the original screen. All original screen
results, INELIGIBLE classifications and bytes remain unchanged and are reported
beside every R1 result.

## Disclosure of data seen before registration

743 inspected C1 T_B8 old-sampler pairwise p99 values (retained screens and the
partial131072 pair), the retained `noise_rms_range` (per-replicate RGB RMS of
replicate-minus-mean), and per-pixel luma SD percentiles at65536. No R1 statistic
(pooled-reference SE relative to reference RMS, per component) was computed for
any slot. The R1 thresholds below are fixed fractions of001's frozen pilot
quality targets and are not tuned to any slot's data.

## Why the original screen is replaced for scoring purposes

001's pairwise screen bounds the disagreement of two **single** replicates at the
99th pixel percentile (absolute1e-5). The scorer (`score_hdr.py`) instead uses the
**pooled mean of the four frozen replicates** and whole-image metrics: total
NRMSE≤5%, indirect NRMSE≤10%, |indirect signed sum bias|≤5%, normalised by
whole-image reference luma RMS. The requirement that matters for a valid score is
that reference noise cannot materially move those decisions. 743 shows the
original screen is unreachable at the cap for Sponza T_B8 although the pooled
reference noise is far below the scored tolerances.

## R1 rule (all conditions, per slot, per level N)

Inputs: the four frozen replicates at level N (seeds unchanged), luma of the
direct, indirect and total components exactly as `score_hdr.py` computes them.
Let `m_p` be the pooled mean of pixel p, `s²_p` the unbiased (ddof=1) replicate
variance, `SE²_p=s²_p/4`, `R=sqrt(mean_p m_p²)` the reference RMS.

1. Finite, nonnegative inputs; identical to001's finiteness/sign checks.
2. Reference-noise NRMSE `e=sqrt(mean_p SE²_p)/R`: total ≤0.005, indirect ≤0.010
   (one tenth of each frozen target). At a target boundary this moves the
   expected observed NRMSE by at most0.5% of the target.
3. Reference-noise sum bias `b=sqrt(sum_p SE²_p)/sum_p m_p` for indirect ≤0.005
   (one tenth of the5% bias target).
4. 001's unchanged support condition: active fraction (union of positive total
   luma over replicates) changes by ≤10% relative to the previous level.
5. Two consecutive levels satisfy 1–3 and4 holds between them; the reference is
   the **first** such pair's higher level. Levels8192…262144 and cap unchanged; a
   cap failure is R1-INELIGIBLE. No seed substitution, pixel mask or exclusion.

Classification string: `R1_STATISTICALLY_ELIGIBLE`. It is never written as the
original `STATISTICALLY_ELIGIBLE`. Every R1 record also stores the original
screen rows and classification verbatim. Direct-only deterministic components
contribute zero noise and are reported, not used to pass.

Physical validity is unchanged: only estimators with retained physical/IID
admission may be screened under R1 (route section below). R1 does not establish
physical correctness, global bias bounds or admission for the all-split/
compensated627 estimator, which remains unadmitted (735/742).

## Scope and consistency check

R1 applies prospectively to the eight missing slots. As a non-gating consistency
check it is also evaluated on the16 originally eligible slots; any of those
failing R1 is reported and retains its original eligibility (no retroactive
revocation or upgrade). Scoring code accepts `R1_STATISTICALLY_ELIGIBLE` only
with an explicit `eligibility_rule:"R1"` recorded in every score.

## Route (admitted estimator only)

Only the original digital-shift RQMC oracle family that produced the existing
eligible slots: `build/n010-cpu/n010_rqmc_oracle` (cbe1186c…) and its byte-equal
incremental/cached forms (`n010_incremental_oracle` 83da95f6…, 022/050), with
physical controls003 + Amendment2/009. It was never declared invalid; 2xx/4xx
density aborts concern the separate all-split estimator. The hybrid GPU port,
point-guided, light-surface, primary-direction and all-split/627 variants are
**not** used under R1, and their moments are never imported.

- C1 T_B8 and C2 T_B8: R1 is evaluated on the complete retained four-seed levels
  `references-recovery-sponza-v1/C1_T_B8` and `references-recovery-dynamic-v1/C2_T_B8`
  (8192…65536), with payload hashes checked against their qualification records.
  The partial C1 131072 level (two seeds) is not used. If R1 is not met by65536,
  continuation uses the same incremental oracle and `--resume-prefix` chain.
- C3 T_B8: complete8192 from `references-v1` imported (Amendment8 rule, partial
  16384 not imported); continue with `qualify_incremental_references.py`.
- C4 T_B8, C5 T_B2/T_B8, C6 T_B2/T_B8: fresh ladders from8192 with
  `qualify_incremental_references.py` on lock016 (the lock used by the recovery
  runs), fresh work roots, one slot per invocation, original order.
- This supersedes, for these eight slots only, 046/158's "no original fallback"
  and the ordering rule; the reason is743's certain original-screen failure of
  every retained estimator. Execution profile: 4 threads, CPUs28–31, nice15,
  4GiB per native, as in169/170. Thread count does not change output bytes for
  this oracle (per-pixel RNG; 022/050 exactness); not re-proven here.

Evaluator: `scripts/research/n010_comparison_readiness/assess_r1_reference_eligibility.py`,
results `744-r1-*`.

N010 remains NOT_READY until all handoff gates. Direct error1.0 remains
UNRESOLVED/未解決 and included. Tests NOT RUN.
