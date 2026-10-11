# J004 formal execution preparation v4 — link-only correction

Status: **READY FOR TARGET EXECUTION — no accepted timing observed**
Issue: #23
Supersedes v3 only for harness identity.

The second target build reached link and failed because `j003_reference.cpp`
calls `triangle_bounds` and `merge_bounds`, whose existing definitions live
in `j003_clustered_bvh.cpp`, but that source was missing from the formal
executable target.

## Correction

Commit `eecb51f730e14916a6a7982aa3165a08273830c8` adds only the existing source
to the formal target:

```cmake
../j003_clustered_bvh.cpp
```

No clustered candidate timing or production selection is re-enabled. The file
is linked only to satisfy the already-used J003 reference helper definitions.

No workload, candidate behavior, measurement boundary, timing order, threshold,
selector, memory gate, or rerun policy changed. No accepted architecture timing
was observed; the run stopped during linking.

## Refrozen identities

- Lane-J source tree:
  `40c42f30acfe99599d220352c392a95235d1159b`
- formal CMake blob:
  `7b883480dfc3338c36417df1f1252be3fedcd9c5`
- `j003_clustered_bvh.cpp`:
  `27bfbf764898a83aa9829282dbd453bf65a4be17`
- `j003_clustered_bvh.hpp`:
  `e535972264dc3b8046fe9d2b253597516dfc4b94`
- runner blob:
  `9e2be93cd37dce9e093fefa7e19ce4eb1b319ac2`
- formal config remains:
  `22951382f8a510bf176c7a427a12d7a2ae24e5d9`

Machine-readable freeze:
`experiments/008-formal-execution-freeze-v4.json`.

## Next target command

```bash
mise exec -- python scripts/research/run_experiment.py \
  --lane lane-j-topology-backend-alternatives \
  --experiment 004-formal-crossover \
  --command "mise run research:j004:formal"
```

J005 remains blocked until a valid J004 summary reports
`j005_eligible=true`.
