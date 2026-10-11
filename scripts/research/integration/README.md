# Integration runner

`run_i001.py` executes the complete frozen I001 target matrix.

Formal command:

```bash
mise run research:record --lane integration-gate \
  --experiment 001-dynamic-end-to-end \
  --command "python scripts/research/integration/run_i001.py --build-dir build/release --repeats 3"
```

Before the formal command, run `mise run research:check`, `mise run assets`
and `mise run build` from a clean `research-integration-gate` checkout.

The runner:

- requires a clean integration branch and at least three process repeats;
- can run the complete 33-case diagnostic preflight alone with
  `--validation-only`;
- runs every Vulkan-validation case before reporting failures, writes
  `i001-validation-summary.json`, and treats validation-layer error markers
  as hard failures;
- runs Vulkan-validation diagnostics before accepted timing;
- covers vanilla software, HWRT primary, B003 quantized fallback,
  renderer-depth reuse, and bounded-capacity HWRT;
- covers Sponza static, camera motion, changing light, and topology-changing
  moving rigid geometry;
- covers sparse, dense, large-world, and vertical-world stresses;
- forces 512-owner bounded overflow and records an explicit full-capacity retry,
  including setup-wall and GPU retry cost;
- rejects bounded normal-case promotion if any representative bounded row
  overflowed;
- writes raw aggregate CSVs plus validation and result JSON summaries;
- applies the fixed protocol thresholds mechanically;
- aborts on quality, producer-semantic, traversal, storage, or provenance
  failures.

Target GPU evidence has not been produced merely by landing this code. I001 is
complete only after the recorded artifact is inspected and the accepted/rejected
result is committed.


For a one-shot correctness preflight before the repeated timing matrix:

```bash
python scripts/research/integration/run_i001.py \
  --build-dir build/release \
  --validation-only
```

The bounded variant does not reuse D005's rejected staged owner-slot path. It
uses one natural GPU owner append index to derive both output and work ranges
and writes directly into the bounded stream, so overflow cannot create holes
between independently reserved counters.
