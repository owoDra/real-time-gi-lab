# R1 reference acquisition, first invocation (745)

2026-10-20/21 JST, plan174 route, `qualify_incremental_references.py --stop-rule R1`,
original incremental oracle (009/022/050 proofs re-verified), lock016, 4 threads on
CPUs28–31, nice15. Work `r1-reference-ladders-v2`. Record
[745](745-r1-reference-acquisition.json) (`complete=false`).

| Slot | Original screen | R1 | Level |
| --- | --- | --- | --- |
| C5_T_B2 | INELIGIBLE | **R1_STATISTICALLY_ELIGIBLE** | 16384 |
| C5_T_B8 | INELIGIBLE | **R1_STATISTICALLY_ELIGIBLE** | 16384 |
| C6_T_B2 | INELIGIBLE | **R1_STATISTICALLY_ELIGIBLE** | 16384 |
| C6_T_B8 | INELIGIBLE | **R1_STATISTICALLY_ELIGIBLE** | 16384 |

The invocation then stopped (exit1) before any C3_T_B8 native: the import plan
`evidence/745-r1-import-plan.json` used a repository-relative path that the script
resolved against its own working directory (`FileNotFoundError`). Operator error, no
scientific data affected; the empty `C3_T_B8` directory is retained. C3_T_B8 and
C4_T_B8 remain to acquire in a fresh root with an absolute import path.

R1 status: C1/C2/C5/C6 eligible slots now total 6/8 R1 (with744); references
22/24 (16 original + 6 R1). Remaining: C3_T_B8, C4_T_B8. Tests NOT RUN.
