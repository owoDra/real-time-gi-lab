# R1 reference acquisition, C3/C4 T_B8 (752)

2026-10-21 JST. Continues745 under plan174 with the identical route:
`qualify_incremental_references.py --stop-rule R1 --transports C3_T_B8 C4_T_B8`,
original incremental oracle (009/022/050 proofs re-verified), lock016, 4 threads on
CPUs28–31, nice15, 4GiB. Fresh work root `r1-reference-ladders-v3`; import plan
[evidence/752-r1-import-plan.json](evidence/752-r1-import-plan.json) differs from745's
only by holding the absolute path of `references-v1/C3_T_B8` (the745 operator error).
Record [752](752-r1-reference-acquisition.json) (`complete=true`).

A first launch with a Python lacking NumPy exited at import before creating the work
root or output (no native, no bytes); relaunched with the project venv
(Python3.13.13, NumPy2.5.4, as recorded in earlier results).

| Slot | Route | Original screen | R1 | Level | Indirect noise NRMSE at8192 |
| --- | --- | --- | --- | --- | --- |
| C3_T_B8 | 8192 imported (Amendment8) +16384 | INELIGIBLE | **R1_STATISTICALLY_ELIGIBLE** | 16384 | 0.00503 |
| C4_T_B8 | fresh 8192 →16384 | INELIGIBLE | **R1_STATISTICALLY_ELIGIBLE** | 16384 | 0.00491 |

Native wall (diagnostic): C3 16384 3.6h; C4 8192 4.3h, 16384 3.0h.

R1 status: all eight174 slots are R1 eligible at16384; references 24/24
(16 original + 8 R1). R1 slot views for C3–C6 built in `r1-slot-views-v1` with the
unchanged175B `build_slot_view` (each reproduced its source R1 result).

Harness fix before747: `build_r1_full_view.py` read `proof['eligibility_rule']`, which
the175B verifier adds only for R1 slots (it returns the unchanged original proof for
the16 original slots), so the first747 attempt raised `KeyError` after ~5s before
writing any file. The comparison now treats a missing key as `original`; no
verification, threshold or row content changed. Tests NOT RUN.
