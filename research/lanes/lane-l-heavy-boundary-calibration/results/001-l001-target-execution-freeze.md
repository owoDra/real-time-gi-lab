# L001 target execution freeze

Status: **READY FOR TARGET EXECUTION — no target timing observed**
Issue: #24
Branch: `research-lane-l-heavy-boundary-calibration`

## What is frozen

L001 is a measurement-environment calibration only. No architecture candidate is
present and no backend ranking can be produced.

Required environments:

- `dual-context`;
- `single-context-independent-runtime`.

Required controls:

- primary: `lane-e-object-local-hwrt-rebuild`;
- software: `lane-e-object-local-software-b003-rebuild`.

Required workload:

- all five frozen J002 profiles;
- all eight snapshots in the frozen order;
- accepted A001 producer/rays;
- B001 exact Hit/tie semantics, including the v7 `best_t + tolerance` pruning
  repair;
- C001 storage;
- 16 complete transitions per timed sample;
- no future prebuild and no recurrent work moved into setup.

## Timing shape

- 4 warmup pairs;
- 12 measured pairs;
- 8 fresh-process blocks;
- alternating AB/BA inside each process;
- frozen start order: `AB, BA, AB, BA, BA, AB, BA, AB`;
- dual/single process position counterbalanced 4/4;
- 1 second settle;
- no sample exclusion;
- no instability rerun;
- no completed-campaign rerun;
- no forced GPU clock/power state.

Expected accepted timing work:

- 2 environments × 5 profiles × 2 control families × 8 blocks
  = **160 fresh timing processes**;
- 32 sample rows per timing process;
- **5,120 raw timing rows** total;
- **3,840 measured rows** and **1,280 warmup rows**.

Before those processes, all 20
environment × profile × control-family paired validations must pass.

## Acceptance gate

Every profile/control pair independently requires:

- max absolute process-median ratio <= 1.02;
- process-median span ratio <= 1.03;
- max within-process order-bias ratio <= 1.02.

An environment is usable only if all ten controls pass. No averaging is allowed.

## Evidence separation

GPU timestamp is primary decision evidence.

CPU wall is diagnostic/health/provenance only.

Timed memory columns are diagnostic-only. Allocation/lifetime independence is
checked in the validation pass so no extra bookkeeping GPU work is inserted
into the timed recurring boundary.

## Source identity

Machine-readable source/config identity is frozen in
`experiments/003-l001-execution-freeze.json`.

The runner also re-executes J004 v7 source/shader-tree verification before target
timing and records:

- `l001-input-provenance.json`;
- `l001-source-provenance.json`;
- device/driver/API/timestamp provenance;
- complete validation, raw, process-summary, and host-observation artifacts.

## Target command

```bash
mise exec -- python scripts/research/run_experiment.py \
  --lane lane-l-heavy-boundary-calibration \
  --experiment 001-heavy-boundary-same-variant-calibration \
  --command "mise run research:l001:formal"
```

The task runs GPU-independent protocol/analysis/runtime-contract tests, builds the
L001 executable, runs all required validation, and only then enters the zero-rerun
timing campaign.

## Result branches

- single PASS / dual FAIL: retain single-context independent-runtime timing;
- dual PASS / single FAIL: retain dual-context timing;
- both PASS: both are measurement-valid; select later from reproducibility,
  complexity, and allocation-evidence handling, never raw speed;
- both FAIL: record L001 as `measurement-limited` and enter L002 prospectively.

Lane E / #22 remains blocked until Lane L establishes a usable environment or an
accepted L002 measurement floor.
