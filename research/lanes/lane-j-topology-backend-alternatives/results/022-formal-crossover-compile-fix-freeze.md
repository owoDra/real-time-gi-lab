# J004 formal execution preparation v3 — compile-only correction

Status: **READY FOR TARGET EXECUTION — no accepted timing observed**
Issue: #23
Supersedes execution freeze v2 only for harness identity.

The first target build exposed a compile error in
`j004_formal_process.cpp`: unqualified `detail::make_vk_info` was used from
the global anonymous namespace even though the helper lives in
`phos::gi::detail`.

## Correction

Commit `7577efb961c1ac8b9fa52c864e956205dc217ce2` adds only:

```cpp
namespace detail = phos::gi::detail;
```

No workload, candidate implementation, measurement boundary, timing order,
threshold, selector, memory gate, or rerun policy changed.

No accepted architecture timing was observed before this correction; the
failure occurred during C++ compilation.

## Refrozen identities

- Lane-J source tree:
  `cd7dae0c155ffdb7fc21405c8e84cac647e978d6`
- `j004_formal_process.cpp` blob:
  `fa26d3df0ed3b60a3442d329eb047f1d289b9202`
- runner blob:
  `38db6d5f87dd25ddf27ac36effa89bfda025fbc4`
- shader tree remains:
  `021faf5c71fc2bfed323887602148df0f7809dc9`
- formal config blob remains:
  `22951382f8a510bf176c7a427a12d7a2ae24e5d9`

Machine-readable freeze:
`experiments/007-formal-execution-freeze-v3.json`.

## Next target command

```bash
mise exec -- python scripts/research/run_experiment.py \
  --lane lane-j-topology-backend-alternatives \
  --experiment 004-formal-crossover \
  --command "mise run research:j004:formal"
```

J005 remains blocked until a valid J004 summary reports
`j005_eligible=true`.
