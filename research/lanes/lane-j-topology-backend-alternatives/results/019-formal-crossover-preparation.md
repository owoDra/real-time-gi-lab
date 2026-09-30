# J004 formal crossover preparation

Status: **pre-timing freeze complete; target relative-memory preflight required**
Issue: #23
Branch: `research-lane-j-formal-crossover`

## Completed before target architecture timing

- Lane K K004 was verified as **GPU-primary protocol accepted** with a 5%
  demonstrated floor.
- Old Lane J / #20 remains closed and unchanged as `measurement-limited`.
- J001-J003 implementation/history is preserved as the base of this follow-up.
- The versioned J004 gate was frozen in
  `experiments/004-formal-crossover-gate-v1.md` before any accepted candidate
  timing.
- No Lane-K branch was merged; only its accepted methodology/gates were
  imported into the frozen J004 record.
- The accepted E005 HWRT rebuild implementation was selectively snapshotted from
  `2911790d8fd1716615a59dc86034e4fea783c9ec`.
- A same-run relative-memory preflight now replays the exact five J002 profiles
  through both the retained clustered candidate and the Lane-E object-local
  HWRT rebuild comparator.
- The preflight retains initial memory plus two complete topology cycles, counts
  actual Vulkan allocation requirements, old/new rebuild overlap, scratch and
  staging, and requires the repeated-cycle persistent baseline to be bounded.

## Hard gate

For every corresponding snapshot/transition:

- clustered persistent bytes <= 1.25x Lane-E HWRT comparator;
- clustered true peak resident bytes <= 1.25x Lane-E HWRT comparator.

A failure rejects the clustered candidate before timing. Formal J004 timing and
J005 remain forbidden until this gate is run and accepted.

## Target command

From a clean checkout of this branch:

```bash
mise exec -- python scripts/research/run_experiment.py \
  --lane lane-j-topology-backend-alternatives \
  --experiment 004-formal-crossover-memory-preflight \
  --command "mise run research:j004:memory-preflight"
```

Expected primary artifact inside the recorded run directory:

- `j004-relative-memory-preflight.json`

Exit code:

- `0`: every required profile passes the relative-memory gate;
- `2`: at least one profile fails; reject clustered candidate, do not time it;
- `1`: invalid/incomplete run; fix the harness/runtime issue without using
  candidate timing evidence.

No formal architecture timing has been run at this checkpoint.
