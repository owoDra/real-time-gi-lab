# N007 P0 result 001 — source audit and synthetic diagnostic validation

**Classification: diagnostic-only / P0 partial.** Parent Issue #4. Branch `research-n007-reference-validity` derived from `main@6a670f1b781e28da15be8e61ad9659382c55bb83`. No new CPU/GPU scene capture.

### Source-evidence findings

See [prospective protocol](../experiments/001-reference-eligibility-protocol.md). The existing CPU tracer fixes primary rays at pixel centers; seeds only affect secondary diffuse bounce sampling. Entirely black/identical images can occur without a seed wiring error. Whole-frame p99 may silently ignore sparse lit pixels. Critically, GPU probe-light shading omits the CPU secondary direct-light shadow visibility test; this is a transport mismatch to isolate, **not** proof of GPU light leaking in specific retained frames.

### Actual execution in ChatGPT's CPU sandbox

- Direct `git clone` attempted: failed (`Could not resolve host: github.com`); source and records inspected through the authenticated GitHub connector.
- Executed `python -m unittest -v test_inspect_hdr.py`: **8 tests PASS** on synthetic PFM files, using CPU/Python only. Coverage: sparse full-frame p99 failure; all-black/identical references; negative and NaN channel flags; four distinct low-noise replicates; dimension mismatch; candidate-only light outside mask; big-endian PFM scale and SHA256; malformed payload.
- `python -m compileall` PASS on the reconstructed diagnostic/test directory. Synthetic data are deliberately **not past physical measurements**.
- `out/` folder not present in GitHub `main`; retained M3b raw PFMs not available in this checkout. Thus actual M3b reference hashes, luminance, and cause remain **NOT MEASURED**. Existing result 043 stays `invalid-retained`.
- C++ source was **read and audited** via GitHub; linked N001 Renderer and Vulkan build, physical shadow evaluation, and new real scene rendering **NOT RUN**.

### Limits / next boundary

The CPU diagnostic can quantify reference sparsity and pairwise discrepancies, but physical correctness and scene-state identity cannot be established without archived real PFMs and an independently checked scene capture. Before any new GPU work, apply read-only diagnostics to the preserved M3b PFMs (if available) and add per-seed fixed-spp export/scene-state fingerprints; run a controlled transport/isolation test under the prospective P1 manifest. Do not reopen N006 P1/P2/P3.
