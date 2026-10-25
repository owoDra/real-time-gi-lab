# 044c — Add the 16spp reconstruction comparator, before registered timing

Prospective addition to 044/044a/044b, before the registered preparation,
calibration or any target timing. The disclosed development target samples
place RSR's frame cost between PT4R and PT64R, so an equal-cost comparison
limited to PT1R/PT4R could favour RSR by construction. Add:

- T4: A = PT16R (16spp + the same reconstruction), B = RSR, same pair
  structure and criteria as T2/T3. Its published per-frame quality is the 018
  16spp reconstruction row per target.

Dominance is evaluated in both directions for T2-T4: RSR dominates a
comparator iff RSR is not SIGNIFICANTLY slower and its published warm indirect
NRMSE (043 mean) is lower; the comparator dominates RSR iff it is not
significantly slower than RSR and its published indirect NRMSE is lower;
otherwise the pair is a cost/quality tradeoff. No other rule changes.
