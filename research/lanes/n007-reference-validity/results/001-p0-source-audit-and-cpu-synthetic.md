# N007 P0 result 001 — source audit and synthetic diagnostic validation

**Classification: diagnostic-only / P0 partial.** Parent Issue #4. Branch `research-n007-reference-validity` derived from `main@6a670f1b781e28da15be8e61ad9659382c55bb83`. No new CPU/GPU scene capture.

### Source-evidence findings

See [prospective protocol](../experiments/001-reference-eligibility-protocol.md). The existing CPU tracer fixes primary rays at pixel centers; seeds only affect secondary diffuse bounce sampling. Entirely black/identical images can occur without a seed wiring error. Whole-frame p99 may silently ignore sparse lit pixels. Critically, GPU probe-light shading omits the CPU secondary direct-light shadow visibility test; this is a transport mismatch to isolate, **not** proof of GPU light leaking in specific retained frames.

### Actual execution in ChatGPT's CPU sandbox

- Direct `git clone` attempted: failed (`Could not resolve host: github.com`); source and records inspected through the authenticated GitHub connector.
- Executed `python -m unittest -v test_inspect_hdr.py`: **17 tests PASS** on synthetic PFM files, using CPU/Python only. Coverage: sparse full-frame p99 failure; all-black/identical references; negative and NaN channel flags; four distinct low-noise replicates; dimension mismatch; candidate-only light outside mask; big-endian PFM scale and SHA256; malformed payload.
- Executed `python -m unittest discover -q`: **17/17 PASS**, including 6 fixed-four-seed manifest/SPP/SHA/stop tests and a synthetic 320×180 N006-support test. With at most 161+169=330 different positive pixels in 57,600 pixels, the full-frame 99th-percentile difference must be zero, even when the nonzero pixels disagree. This is a mathematical bound on the documented support size, not an analysis of missing real PFMs.
- `python -m compileall` PASS on the reconstructed diagnostic/test directory. Synthetic data are deliberately **not past physical measurements**.
- `out/` folder not present in GitHub `main`; retained M3b raw PFMs not available in this checkout. Thus actual M3b reference hashes, luminance, and cause remain **NOT MEASURED**. Existing result 043 stays `invalid-retained`.
- C++ source was **read and audited** via GitHub; linked N001 Renderer and Vulkan build, physical shadow evaluation, and new real scene rendering **NOT RUN**.

### Limits / next boundary

The CPU diagnostic can quantify reference sparsity and pairwise discrepancies, but physical correctness and scene-state identity cannot be established without archived real PFMs and an independently checked scene capture. Before any new GPU work, apply read-only diagnostics to the preserved M3b PFMs (if available) and add per-seed fixed-spp export/scene-state fingerprints; run a controlled transport/isolation test under the prospective P1 manifest. Do not reopen N006 P1/P2/P3.

### Authentic historical JSON reanalysis (additional read-only work)

- Located and materialized original N006 M3b/M3c summary JSONs from the file library; their byte SHA256 values matched historical result 043 and 045 respectively. CPU analyzer `audit_historical_summaries.py` completed against **actual historic summary JSON, not PFM files**. Its [derived JSON report](./002-historical-summary-audit.json) is retained separately with original source SHA256 values.
- The M3c summaries report 161/169 positive RGB pixels; finite/nonnegative and at most 330/57,600 union-positive pixels, forcing pairwise full-frame p99 zero regardless of the active-pixel differences. Reported per-channel mean A/B around 6.55e-8/6.53e-8; inter-reference RGB RMS 6.328440285901378e-8. **Real PFM file bytes and hash claims are not independently available/verified**. M3b summary provides only "identical" without brightness; no conclusion whether fully black.
- Original rewritten SHA provenance: N003 `52a8d2c7ab2653d40b73afa9f17690712536239e` -> `1cf8046ea9884141bf82cb7b68dc950159526cb5`; M3b `60451d3fe2c836b94f750771da72c87684bc9851` -> `b908f4f7ae6b6cb128ad9efb361a21e569dc1d07`; M3c `b6fa95820bb81a035a88370da691c1c236b07648` -> `4d85da3da0f89949f2d9fc989291ff3739523cd6` as recorded in `research/provenance/commit-map.tsv`. Historic source records are untouched.
