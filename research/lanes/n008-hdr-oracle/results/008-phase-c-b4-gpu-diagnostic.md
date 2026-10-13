# N008 Phase C (partial) — B4 moving-rigid: frozen GPU output vs locked oracle reference

**Date:** 2026-10-13 JST.

**GPU input:** the existing private N007 software-backend capture `out/research/n007-reference-validity/p1a/probe-shadow-dabe590b0c6e`, acquired by the human operator on 2026-10-12 at source `dabe590`. **No new GPU run.**

**Comparison:** CPU-only, using [`phase_c_gpu_diagnostic.py`](../../../../scripts/research/n008_hdr_oracle/phase_c_gpu_diagnostic.py). Evidence: [007-phase-c-b4-gpu-diagnostic.json](007-phase-c-b4-gpu-diagnostic.json).

| Check | Result |
|---|---|
| Capture frame/geometry state bytes vs locked B4 reference state | **identical** (`77e1d952…`, `d70e8344…`) |
| Primary visibility (oracle hit sidecar vs GPU `hits.bin`) | 15,173 / 15,173 hit pixels; mask mismatch **0**; primitive mismatch **0**; max relative t difference 9.9e-7 (float32) |
| Direct component | GPU 0 px positive, oracle 0 px positive: **agree** |
| Indirect / total | GPU **9,247** positive pixels, sum 0.26734. Oracle (D=2 **and** D=8): **0** positive. **100% of GPU light is GPU-only** (no physical support under T_B) |
| Score | **Not produced**: the reference is NO_SUPPORT by preregistration |

**Inference:**
- **What this comparison shows:** for this attested frame, the Renderer's whole indirect output is energy that a physically validated estimator of the same declared scene does not produce, even with eight bounces. That is a GPU-only light leak at the image level.
- **Consistency with N007:** this matches N007's model-specific mechanism (unshadowed secondary probe hits), but **does not re-run, revise or extend N007's causal claim**.
- **What it does not show:** a quality ranking, or anything about other frames, states or GPUs.
