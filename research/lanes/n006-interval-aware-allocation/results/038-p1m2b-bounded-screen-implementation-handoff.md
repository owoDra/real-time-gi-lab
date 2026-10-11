# N006 P1m2b — bounded independent-state observable-image screen implemented; GPU UNMEASURED

2026-10-11, Issue #42. Implements the previously frozen [experiment 027](../experiments/027-p1m2b-independent-state-observable-image-gate.md) **after** accepting P1m2a hit-recovery-but-exact-image-null [result 037](./037-p1m2a-fixed-tetra-octant-null-image.md).

## Source and contracts

- Production opt-in CLI `--p1m2b-independent-state` is **valid only** with scenario **camera-motion/light-motion**, `lane-e-final-software`, canonical lean-copyback, **32 original-source + 8 target-state warmups**, one target, `--p1m0-consumer-coverage`, skipped reference, current mode and no competing capture. Without the new flag, the original **M1a/M2a static/C3 three-token whitelist is unchanged**. Uses original N006 M1a and M2a stages, **no new GPU shaders**, no accepted N001/N003/E003 source changes.
- Script `scripts/research/n006_interval_aware_allocation/run_p1m2b_independent_state.py` and one-batch shell `run_n006_p1m2b_independent_state.sh`:
  - For **each scenario** two separately warmed **control** processes, required exact accepted scenario HDR PFM SHA, byte-equal control PFMs, identical per-key M0 coverage rows/sha, full original N004 sampled oracle and original canonical stage correctness.
  - Only then select among M0 rows: for each cascade 0..3, smallest token at **maximum consumer_pixels**, then smallest token among **consumer_pixels=0**. Missing/no-zero stratum explicitly retained, equal tokens deduplicated. **≤8 keys/scenario**. Selected rows are written to intermediate retained summary **before** any extra rays.
  - Two isolated intervention arms for every selected key: immutable P1a-original deterministic uniform sphere, immutable fixed tetra-octant/jitter `[0,3,5,6]`. +4 rays (8+4 canonical merge) for **one** key, same GPU stage timing/oracle/base-prefix and owner-weight checks, full SHA and float32 PFM RGB difference versus scenario-matched control.
  - **≤32 treatment cells total** across two scenarios and two arms (not counting mandatory control pairs); only candidates with any nonzero RGB channel have an additional separately warmed confirmation run. It must reproduce the entire PFM bytes and exact changed-pixel/channel metrics. Every zero/positive/failed attempt is retained to disk after each process; GPU subprocess stderr/stdout available in per-case folders.
  - Complete without any reproducible PFM change ⇒ `bounded-observable-null-stop`: STOP this specific +4-ray/current-quantization family, do not cherry-pick further directions/keys. ≥1 replicated PFM change ⇒ `observable-influence-screen-complete` but **NO QUALITY CLAIM**, independent converged reference, paired signed RMS, matched noise and independent sealed geometry+trajectory still mandatory. Abort invalid unexpected gate/unstable control ⇒ `invalid-retained`.
- Unit tests `test_p1m2b_independent_state.py` cover selection tie-breaks, zero-only duplicates, empty strata, unsorted/invalid tokens, source/CLI separation and fixed experiment bounds.

**Validation status**: source committed via GitHub connector; not built or unit-tested on user's NixOS environment and **not** executed on their Radeon 8060S GPU. Build/test command is included in single script. No PR, no CI/GitHub Actions. Historical C0/B1a/B1c rejected data unaffected.

## Next GPU operator command

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m2b_independent_state.sh
```

Upload `out/research/n006-interval-aware-allocation/p1m2b-independent-state/<UTC>/n006-p1m2b-independent-state-summary.json`. If the shell stops before GPU, supply the first compile or unittest error; do not claim or assume that the experiment ran. The recorded selection table and every process's raw evidence/PFM should be retained locally. Only after valid bounded screening should the next research decision be made.
