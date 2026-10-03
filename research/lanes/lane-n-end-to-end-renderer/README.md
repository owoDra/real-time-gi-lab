# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 complete; N003 preflight v1/v2 timing-unsuitable; same-process prewarmed v3 next (#31)**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance claim.

## N001

N001 renderer/reference bring-up is complete. See:

- `experiments/001-n001-config.json`;
- `experiments/001-n001-source-provenance.json`;
- `results/001-renderer-reference-bringup.md`.

The target AMD Radeon 8060S / RADV run passed correctness/provenance and campaign-level renderer/reference HDR signal sanity. Individual black reference frames remain valid observations. N001 makes no performance claim.

## N002

N002 current-architecture baseline is complete. See:

- `experiments/002-n002-config.json` — core five-scenario checkpoint;
- `experiments/002-n002-full-config.json` — final six-scenario playback;
- `n002_main.cpp` / `phos-n002` — static, camera, light, moving-rigid, stable-topology deformation;
- `n002_runtime.cpp`, `n002_hwrt_rebuild.cpp`, `n002_topology_main.cpp` / `phos-n002-topology` — topology-changing/high-churn object-local rebuild;
- `n002_full_contract.py` / `run_n002_full.py` — final completion artifact and validation;
- `results/002-current-architecture-baseline.md` — accepted target result.

Final evidence commit: `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`.

The six-scenario artifact passed correctness, provenance, reference convergence, HDR campaign-signal, timing-accounting, and memory gates. Topology/high-churn replaced 398/796 dynamic-owner primitive identities, executed exactly one object-local backend rebuild, recorded 252,928 bytes of old/new overlap, and retained static ownership outside the rebuild path.

## N003 preflight/calibration

Issue #31 is part of Lane N and is the preflight for N003 proper, not a separate lane.

v1 at commit `422945ea32164e487e8562214dc7568f6e2ad9a6` used absolute fresh-process timing and failed: 48.297% worst noise, 145% derived threshold.

v2 at commit `aa46afd1594cf66cae440b30223cfc1350475a67` used eight fresh-process A/A pairs and also failed: 110% derived threshold and roughly 97% worst p95 pair effect. The short static/camera scenarios showed near-2x timing modes. Quality, however, was deterministic across all 16 A/B observations and the scale-aware quality metric had signal.

Current v3 keeps the same timing boundary and statistical thresholds but uses a dedicated `phos-n003-preflight` timing probe:

- A and B run in the same process;
- each role receives 32 unmeasured source-state warm-up frames immediately before its measured target transition;
- dynamic update/rebuild remains inside the one measured target frame;
- eight fresh process pair blocks with alternating AB/BA order;
- complete-GI, complete-renderer and per-stage GPU timings are retained.

See:

- `experiments/003-n003-preflight-calibration-v3-config.json`;
- `experiments/003-n003-preflight-calibration.md`;
- `n003_preflight_v3_contract.py` / `run_n003_preflight_v3.py` / `test_n003_preflight_v3_contract.py`;
- `n003_preflight_main.cpp` / `phos-n003-preflight`.

The timing decision rule remains median paired `log(B/A)` plus robust MAD null bound, >=75% same-direction support, <=20% derived threshold, <=20% worst p95 A/A pair effect, and zero A/A formal-claim triggers. Failed v1/v2 artifacts remain retained; no sample deletion or post-hoc threshold relaxation is allowed.

Quality interpretation remains unchanged from v2: legacy fixed-absolute affected fraction is diagnostic-only; RGB RMS, p99 absolute luminance error, and scale-aware affected fraction are the primary scenario-by-scenario metrics with no aggregate winner score.

N003 proper must not start until v3 passes and its derived timing threshold is recorded in result truth.

Raw target artifacts remain under `out/research/`. Continue in parent Issue #26.
