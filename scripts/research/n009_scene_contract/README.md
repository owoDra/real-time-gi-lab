# N009 scripts — scene contract C1, back-face rule BF-P, probe-transport attribution

Protocol: [experiments/001](../../../research/lanes/n009-scene-contract/experiments/001-scene-contract-backface-and-probe-attribution.md).

| Script | Role |
|---|---|
| `generate_overlay.py` | Fail-closed exact-once overlay of the pinned A001/B002 loaders and `a001_runtime.cpp` (node transforms, authored camera, contract light, BF-P). Build-time only. |
| `generate_state_exporter.py` | Verbatim extraction for `n009_state_export` (reuses N008's unchanged `extract`). Build-time only. |
| `select_contract.py` | Preregistered geometry/direct-only selection of the contract light and camera-motion offset. |
| `n009_ladder.py` | Locks the cell states and runs the **unchanged** N008 ladder/classifier on the N009 cells. |
| `n009_gpu_compare.py` | Runs the unchanged N008 GPU diagnostic on N009 captures (C7 via a mechanically verified BF-P equivalence). |
| `probe_attribution.py` | WP-PT: runs `n009_probe_model` on attested captures and scores the R0–R6 counterfactual ladder. |

Build (opt-in; the default build graph is unchanged):

```bash
cmake -S . -B build/n009 -DCMAKE_BUILD_TYPE=Release -DPHOS_BUILD_N007=ON -DPHOS_BUILD_N008=ON -DPHOS_BUILD_N009=ON
cmake --build build/n009 --target n009_state_export n009_probe_model phos-n009-capture
cmake -S src/research/n008_hdr_oracle -B build/n008 && cmake --build build/n008   # oracle
```

The Python analysis uses the N008 crosscheck environment (`scripts/research/n008_hdr_oracle/requirements-crosscheck.txt`; numpy). Raw states, PFMs and captures stay in ignored `out/research/n009-scene-contract/`.
