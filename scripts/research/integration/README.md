# Integration runner

`run_i001.py` executes the repeatable representative Sponza matrix for I001.

Formal representative command:

```bash
mise run research:record --lane integration-gate \
  --experiment 001-dynamic-end-to-end \
  --command "python scripts/research/integration/run_i001.py --build-dir build/release --repeats 3"
```

The runner:
- requires a clean `research-integration-gate` checkout;
- runs a validation diagnostic before accepted timing unless explicitly skipped;
- measures vanilla software, HWRT primary, B003 quantized software fallback,
  and renderer-depth-reuse boundaries;
- executes static, camera-motion, and light-motion as process-level repeats;
- writes `i001-representative.csv` and
  `i001-representative-summary.json` into `PHOS_RESEARCH_ARTIFACT_DIR`;
- fails immediately on correctness/quality or storage failures.

This representative matrix is not the final I001 closeout. Moving rigid geometry,
sparse/dense stress, large/vertical stress, and bounded-capacity forced-overflow
retry remain separate required gates.
