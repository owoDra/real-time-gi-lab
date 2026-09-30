# J002/J003 GPU-independent preparation checkpoint

Status: **GPU-independent implementation complete; canonical local artifact replay pending**

This checkpoint distinguishes implementation readiness from evidence that
requires files intentionally kept outside Git.

## Completed on the Lane J branch

J002 now has Lane-J-owned code for:

- frozen five-profile primitive-count-changing topology sequences;
- frozen profile seeds and topology digests;
- accepted A001 natural-append stream parser and workload-id validation;
- accepted A001 source pinned to:
  - case: `static`;
  - commit: `8b647ef8dcf1150f86a9d25c039ca48bd7f30b8f`;
  - accepted campaign: `20260928T143212Z`;
- B002-compatible glTF triangle extraction semantics;
- representative 796-triangle object selection;
- deterministic small/medium/large profile derivation;
- complete exact binary snapshot serialization;
- count-change and snapshot-digest transition hard gates;
- retained-population-only topology replacement;
- immutable-owner mutation validation;
- common boundary field validation;
- allocation-lifetime true peak calculation;
- B001 exact Hit / nearest-hit / primitive-id tie reference semantics.

J003 now has a CPU reference model for the retained clustered candidate:

- target occupancy 48;
- hard maximum 64 triangles;
- merge-below 24;
- minimum-AABB-expansion insertion;
- deterministic local Morton split;
- deterministic merge;
- stable cluster IDs for unaffected clusters;
- split reachability and unaffected-cluster invariants.

## Pre-evidence corrections

Two issues were found in self review before candidate timing/evidence:

1. `plan-v1.md` selected only non-full clusters for insertion while also
   describing overflow-driven splits. That made the split path effectively
   unreachable. `plan-v1.1-amendment.md` fixes assignment to ignore capacity
   until the deterministic post-assignment split phase.
2. The first geometry materializer could select newly inserted primitives for
   same-transition topology replacement. That violated the frozen definition of
   replacement as a fraction of the **retained** population. The generator now
   limits replacement sources to retained IDs and has a regression test.

No target timing was observed before either correction.

## Frozen profile topology digests

- `small-global-high`:
  `45819e4759e2cbe2ff90b617043a8baa5ed3242c5b648e447b43ef21853309c5`
- `medium-global-representative`:
  `3c7de01e9628d46d0b516dc0e3b7edd5a66f7e47c23e7cec8a89b4ca9a3cc358`
- `medium-local-high`:
  `b0e58dc496f5c8d5efb1e5ab549bd310e51f26fd5e5d65a4bd5cecdb712407bb`
- `large-global-high`:
  `8d1473fb238de7f6281710eb4a493d6e558ec68339a090dc7b1fa15f1c782c87`
- `large-local-high`:
  `042896ddfc2ff2b928bf7ed9792c851f28803c24cb760a826e3495e0ebdfa69e`

These digests were recomputed independently during self review and match the
frozen config.

## What cannot be executed through the GitHub connector

The canonical J002 materialization consumes files outside Git:

- accepted A001 `stream-v1.bin` from the frozen A001 campaign;
- local Vulkan-Samples Sponza asset and external buffers.

The GitHub connector cannot inspect the user's local `out/` tree or asset
checkout. Therefore this session does **not** claim that the canonical Sponza
materialization has been executed.

The runner auto-discovers exactly the frozen A001 artifact and fails closed if
zero or multiple matching streams exist.

## CPU-only local preflight

On the target checkout, but without requiring a GPU:

```bash
git switch research-lane-j-topology-backend-alternatives

mise exec -- python -m unittest discover \
  -s scripts/research/lane_j_topology_backend_alternatives \
  -p 'test_*.py'

mise exec -- python \
  scripts/research/lane_j_topology_backend_alternatives/run_j002_materialize.py \
  --artifact-dir \
  out/research/lane-j-topology-backend-alternatives/002-deterministic-topology-contract/materialized

mise exec -- python \
  scripts/research/lane_j_topology_backend_alternatives/run_j003_cpu_gates.py \
  --j002-artifact-dir \
  out/research/lane-j-topology-backend-alternatives/002-deterministic-topology-contract/materialized
```

Expected outputs:

- `j002-materialized-manifest.json`;
- 5 profile directories;
- 8 exact binary snapshots per profile;
- `j003-cpu-structural.json`.

If the accepted A001 artifact or Sponza asset is absent, restore/fetch that
existing input rather than changing the frozen workload.

## Next research boundary

After the local CPU preflight passes, the next new research work is **J003
target-GPU prototype implementation and exact end-to-end validation**.

That work requires iterative Vulkan/shader validation on the target GPU. It
must implement only the retained clustered candidate and required controls.
Formal performance ranking remains prohibited.

Lane I is concurrently at I003 target calibration; Issue #19 has not yet
published I004. Therefore J004 formal crossover remains blocked independently
of J003.
