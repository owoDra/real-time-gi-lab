# N009 interim status (2026-10-14, NOT a final decision)

**Done:**
- preregistration `f215bc7`;
- contract selection, Amendment 1 and state lock `bc2419c`;
- 10 GPU captures (RADV 8060S, software + hwrt, C1/C2/C4/C5/C7), all byte-attested against the lock or exporter;
- T_B2 ladder for C1, C2, C4, C5 and C6.

## Interim findings (preregistered gates)

### WP-SC
- Under C1, every Sponza cell is lit: total support covers 57,600/57,600 px, and direct support covers 63–68% of pixels.
- **T_B2 classification:** every cell is DIRECT_DETERMINISTIC_PROVED. The total fails the N007 screen at the 8192 spp cap: at C1 8192 spp, active p99 rel is 5.5% against the 5% threshold and abs is 3.0e-5 against 1e-5.
- The screen metrics fall as 1/√spp, so the failure is non-convergence within the cap. It is not a lack of support.
- C3 (light motion) is NOT_CONSTRUCTIBLE (Amendment 1).
- Provisional Exit SC: total NO GO within the cap. The direct reference is proved for static, camera, moving-rigid, deforming and churn.
- T_B8 is still pending: C1 is done; C2, C4, C5 and C6 were running.

### WP-BF
On C7 software, the BF-P gates pass:

| Gate | Result |
|---|---|
| BF1 | all triangles have sided = 1 |
| BF2 | primary mismatch 0 px (N008: 4,978 px) |
| BF3 | direct max rel 1.1e-5 on all 6,943 px |

Not yet run: the C7 hwrt check and the full `n009_gpu_compare.py` run.

### WP-PT, C7 software
Ladder results (relative bias of sum vs the T_B2 indirect reference):

| Stage | Relative bias of sum |
|---|---|
| R0 | −91.4% |
| R1 | −92.1% |
| R2 | −96.3% |
| R3 | −27.4% |
| R4 | +22.2% |
| R5 | −3.4% |
| R6 | +0.03% |

- **Closure:** V4 passes.
- **Dominant factor:** probe coverage (R3, +69 pt), followed by range truncation (R4, +50 pt). Quantisation and secondary shadowing are minor.
- **V1 fails at 21 cell-boundary pixels** (GPU float key assignment is not reproducible on CPU), so this capture is **INCOMPLETE** under preregistration. A post-hoc sensitivity analysis that excludes those pixels was added to `probe_attribution.py`; it is not a gate.

### WP-PT, N008 B4 capture (R0–R2)
- Secondary shadowing removes 100% of the leak energy (0.2405 → 0).
- V3 fails (86.9% re-trace match) because the capture predates BF-P (single-sided traversal), so the capture is formally INCOMPLETE. R0–R2 do not use the re-trace.

## Resume
- Python: the N008 venv with numpy.
- Env: `LD_LIBRARY_PATH=/nix/store/d6vnmfmcz5b299180issiaad4m96wh8k-vulkan-loader-1.4.341.0/lib` (GPU runs only).

```bash
# 1. finish the T_B8 ladder (skips nothing already rendered only if rerun per cell)
python scripts/research/n009_scene_contract/n009_ladder.py render --lock research/lanes/n009-scene-contract/results/002-state-lock.json --transports T_B8 --cells C2 C4 C5 C6 --out out/research/n009-scene-contract/ladder-bc2419c
python scripts/research/n009_scene_contract/n009_ladder.py analyze --lock research/lanes/n009-scene-contract/results/002-state-lock.json --out out/research/n009-scene-contract/ladder-bc2419c --commit bc2419c08797f24eaecb8d3d7b368eb26d967054 --summary research/lanes/n009-scene-contract/results/003-ladder.json
# 2. GPU diagnostic + BF gates
python scripts/research/n009_scene_contract/n009_gpu_compare.py --captures out/research/n009-scene-contract/gpu-bc2419c --n009-summary research/lanes/n009-scene-contract/results/003-ladder.json --n009-ladder out/research/n009-scene-contract/ladder-bc2419c --n008-summary research/lanes/n008-hdr-oracle/results/005-phase-b-reference-ladder.json --n008-phase-b out/research/n008-hdr-oracle/phase-b-9aab73b --output research/lanes/n009-scene-contract/results/007-gpu-compare.json
# 3. WP-PT final (C7 sw+hwrt; B4 R0-R2)
python scripts/research/n009_scene_contract/probe_attribution.py --job out/research/n009-scene-contract/gpu-bc2419c/C7-leak-medium-software:out/research/n008-hdr-oracle/phase-b-9aab73b/B7_T_B2:STATISTICALLY_ELIGIBLE --job out/research/n009-scene-contract/gpu-bc2419c/C7-leak-medium-hwrt:out/research/n008-hdr-oracle/phase-b-9aab73b/B7_T_B2:STATISTICALLY_ELIGIBLE --job out/research/n007-reference-validity/p1a/probe-shadow-dabe590b0c6e:out/research/n008-hdr-oracle/phase-b-9aab73b/B4_T_B2:NO_SUPPORT:3 --output research/lanes/n009-scene-contract/results/008-probe-attribution.json
```

Then write the final decision record and update status.md, roadmap.md, the lane README and the Issue.
