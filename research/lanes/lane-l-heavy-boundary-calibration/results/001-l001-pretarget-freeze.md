# L001 pre-target execution freeze

Status: **READY FOR TARGET EXECUTION — no target timing observed**
Issue: #24
Branch: `research-lane-l-heavy-boundary-calibration`

## Scope

L001 is measurement-environment calibration only. It does not rank architecture
candidates and does not modify or rerun J004.

Required environments:

- `dual-context`: two Vulkan contexts, two independent FormalRuntime instances;
- `single-context-independent-runtime`: one Vulkan context/device/queue,
  two independent FormalRuntime instances with independent resources.

Only the two incumbent controls are used:

- primary: Lane-E object-local HWRT rebuild;
- software: Lane-E/B003 object-local software rebuild.

The optional single-runtime repeated-baseline diagnostic was excluded before
target execution.

## J004 / Lane K implementation audit

Lane K runs paired A/B work through one `VulkanContext` and one GPU runtime.
J004 instead creates two `B002VulkanContext` objects and two independent
`FormalRuntime` objects per fresh timing process.

L001 preserves the J004 heavy recurring work by directly reusing the frozen v7
`j004_formal_process.cpp` implementation and changes only the pairing
environment around two independent FormalRuntime instances.

Before L001 execution, the runner re-verifies the complete frozen J004 source
and formal-shader trees, including the v7 B001 `best_t + tolerance` pruning
repair.

## Frozen boundary and gate

Unchanged:

- five J002 profiles and eight snapshots in frozen order;
- A001 producer/ray order;
- B001 exact Hit/tie semantics;
- C001 storage;
- 16 complete transitions per sample;
- no future-snapshot prebuild;
- no recurrent work moved into setup;
- GPU timestamp primary axis;
- CPU wall diagnostic/health/provenance only;
- 4 warmup + 12 measured pairs;
- 8 fresh-process blocks;
- AB/BA alternating inside each process;
- 1 second settle;
- no sample exclusion;
- zero instability reruns;
- zero completed-campaign reruns;
- no forced clock/power controls.

J004 control-health limits remain exactly:

- max absolute process-median ratio <= 1.02;
- process-median span ratio <= 1.03;
- max within-process order-bias ratio <= 1.02.

An environment passes only when all 5 profiles × primary/software controls pass
independently. Profile averaging is forbidden.

## Pre-target hardening

The initial L001 harness already implemented both required environments,
paired correctness validation, allocation-lifetime checks, and control-only
analysis. Self review added two measurement-integrity hardenings before target
execution:

1. environment process order is now frozen/counterbalanced 4/4 across the eight
   blocks rather than executing all dual-context work followed by all
   single-context work;
2. L001 now invokes the complete J004 v7 source/shader freeze verification,
   not only a small set of top-level blobs.

Input provenance and source provenance are emitted as explicit artifacts.

## Allocation/lifetime evidence

Allocation/lifetime evidence is collected in the pre-timing validation pass.

For the shared-context environment the required lifetime sequence is:

1. baseline live allocation;
2. runtime A increases live allocation;
3. runtime B independently increases it again;
4. destroying B returns exactly to the post-A level;
5. destroying A returns exactly to baseline.

Timed memory columns are retained only as diagnostics because the shared context
necessarily has a combined allocation counter. No extra GPU bookkeeping is
inserted into the recurring timing boundary.

## Frozen source identity

Execution freeze:
`experiments/003-l001-execution-freeze.json`

Implementation checkpoint:
`55a3f7dca308427206cc16691fc0b6f7c5b63293`

Freeze ref update:
`69641eddce3946b674701ac6cd8e304c4c5b9443`

Key blobs after hardening:

- config: `f3ec006e1e4c0b236463289af73b5405fdc4d5d3`;
- L001 process: `f8803228893cd3cd20a788919758e203563810e2`;
- L001 runner: `f5990abdb4225a469c7c48e807655a3d81647b1e`;
- L001 analysis: `cb17b26073d9c256103064f3edd8236d9c51dbfd`;
- protocol test: `9a8f35e90f5b717244db0a20bf5c44435e3aa77e`;
- runtime-contract test: `1b3a52cca7df954be35800d2f719c961698b5c73`;
- imported J004 source tree: `7b697d2e2b8151e85e0bb451794de0b64e5e842b`;
- imported J004 formal shader tree: `83e6f0f5286e7edb14b15a3e722dca379e126ce5`.

## Tests and target entry

Frozen GPU-independent tests:

- `test_l001_analysis.py`;
- `test_l001_protocol.py`;
- `test_l001_runtime_contract.py`.

The target task runs these tests before building the L001 executable. The
current connector environment cannot clone/build the repository, so no target
or host execution result is claimed here.

Run the target campaign with:

```bash
mise exec -- python scripts/research/run_experiment.py \
  --lane lane-l-heavy-boundary-calibration \
  --experiment 001-heavy-boundary-same-variant-calibration \
  --command "mise run research:l001:formal"
```

Expected decision:

- single PASS / dual FAIL: accept single-context independent-runtime pairing;
- both PASS: choose later from reproducibility, complexity, and
  allocation/lifetime handling, never raw speed;
- both FAIL: record L001 as measurement-limited and only then freeze L002.

Lane E / #22 remains blocked until this target result establishes a usable
environment or L002 establishes a heavy-boundary measurement floor.
