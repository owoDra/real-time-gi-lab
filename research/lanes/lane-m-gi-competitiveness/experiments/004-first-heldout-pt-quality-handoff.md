# M001 first heldout PT quality unit — owner GPU handoff

This execution recipe instantiates the unchanged M001 001/002 budgets and quality gates. It is fixed after CPU reference admission and before any new GPU PT image. It is not a timing campaign or a new scientific threshold.

The first named GPU unit is **H01/T_B2, independent pixel PT, 1 spp, seed 305419896, one static 320×180 frame**. Use the original isolated `build/n009/phos-n010-pixel-pt` SHA `b96880ba40c8466b4210d9e5af0dad80855c96416496a6c47ad9dc7670d60ea0` and pixel shader SHA `e8e03c3e7438159f9b0a4a5d4e4e61e841d054c06aab442d80c613face199069`, not the newly compiled default Renderer. Captured geometry/frame bytes and canonical N010 physical input must equal the H01 lock exactly. The already admitted original H01/B2 four-seed reference at 16384 spp is reverified before launch. No pilot C1–C12 or R1 reference is reused.

`first_pt_quality.py prepare` is CPU-only and has run once: `out/m001-h01-b2-pt-n1-plan.json`, SHA `091825218651b649b744cac31f978e3cc32112fbd347b32c53989abd964a8892`. It freezes the actual command and reference/binary/shader/driver-script inputs, and checks the full original source state and physical proof. The `execute` mode is reserved to the owner's explicit invocation under the initial execution contract. The agent has not run it. A later explicit user authorization can transfer execution to the agent; do not infer that authorization from successful preparation.

One command at the repository root, using the available original N010 Python environment:

```bash
LD_LIBRARY_PATH="${NIX_LD_LIBRARY_PATH:-${LD_LIBRARY_PATH:-}}" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 out/research/n010-comparison-readiness/venv/bin/python scripts/research/lane_m_gi_competitiveness/first_pt_quality.py execute
```

Only one native process is launched. Retain all stdout/stderr and partial failures; refuse any existing case or archive. Native CPU limit is 120 seconds, elapsed limit 180 seconds, with termination limited to this runner's own child process group on timeout. No settings, clocks, power, desktop or other processes are changed. No retries, later budgets, other cells or dependent GPU jobs are queued.

The runner checks the exact returned state, one-frame metadata, duplicate root/frame image hashes, complete owned allocation/free ledger, peak ≤8GiB and teardown zero. It scores all 57,600 pixels of total and indirect linear HDR using unchanged N010 `score_hdr.score`: total NRMSE ≤0.05, indirect NRMSE ≤0.10, absolute indirect signed bias ≤0.05. It retains direct, leak, support and per-pixel diagnostics without exclusions. A failed quality target is `QUALITY_FAIL`, not a failed GPU experiment or a reason to change budget gates. An operational or state failure remains incomplete and stops the sequence.

The original executable's timing fields remain **DIAGNOSTIC_UNCALIBRATED**. No selected-boundary precision, performance claim or architecture promotion follows. All timing samples and owned memory stay local; accepted later timing requires the separate preregistered actual-boundary/multiplicity/practical-ratio1.20 procedure. CPU wall is diagnostic; driver-private and CPU memory are excluded from the Vulkan-owned ledger.

Outputs stay under `out/research/lane-m-gi-competitiveness/m001-original-cpu-v2/H01_T_B2/pixel-pt-n1`; compact proof tar is `out/m001-h01-b2-pt-n1-quality.tar`. **Stop after the terminal receipt**, return that tar/JSON, audit it, then separately instantiate the next frozen PT budget. The six-level PT ladder remains 1/4/16/64/256/1024 with first passing budget selected, retaining all failures. DDGI remains unqualified and vanilla/dense/software are not fabricated from the existing HWRT capture.


## Independent intake prepared 2026-10-23

[CPU auditor preparation020](../results/020-independent-pt-auditor-preparation.json) adds a read-only result intake after owner execution. `audit_first_pt_quality.py --output out/m001-h01-b2-pt-n1-independent-audit.json` compares the compact tar with the pinned plan and actual local terminal bytes, verifies every raw payload and root/frame duplicate, replays exact physical reference provenance and allocation/free memory, and recomputes all whole-image component metrics and error maps before classifying the original thresholds. It never executes native/GPU code or writes inside the captured evidence root. Operational failures are kept distinct from quality failures; missing terminal data is not PASS. Its 10 new tests use synthetic negative fixtures; all 24 Lane M CPU tests pass. **Real PT-result audit NOT RUN**. Existing GPU command, binary/shader, 57 input hashes, plan019 and original admission/quality thresholds are unchanged.
