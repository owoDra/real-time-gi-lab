# phos-gi-lab

**Evidence-driven research toward a competitive real-time global illumination architecture.**

The objective is to establish a new light-transport architecture that can outperform representative existing real-time GI techniques **in a defensible combination of image quality, end-to-end GPU cost, GPU memory, and dynamic-scene coverage**. This is not merely a Split Radiance Cascades optimization project. Producer, traversal, storage and reuse components are replaceable hypotheses, not permanent commitments.

## Current position (2026-10-11)

The laboratory has a functioning GPU image-producing Renderer and substantial measured performance results, **but has not established a generally superior GI solution**.

- **Current measured design:** visibility-driven Split RC producer with natural append order; HWRT/TLAS on the measured Radeon 8060S; segment-DDA/hash plus conservative quantized Micro BVH8 as software fallback; per-probe sparse hash storage; and object-local geometry ownership/updates.
- **Dynamic updates:** accepted Lane E heavy-boundary revalidation, including substantial GPU-time improvements on moving-rigid and stable-topology-deforming workloads. Lane M retained the Lane E incumbent for topology-changing/high-churn regimes.
- **N003 renderer comparison:** approximately **2.35–3.11x** faster than the tested vanilla Split RC in reported cases; **approximately 24–27% more GPU memory**. These are bounded cases, not cross-GPU or universal claims.
- **Known weaknesses:** N004 reports quality issues under camera and dynamic-geometry motion. N005 adaptive tracing is REFINE/conditional, not one universally accepted rule. N006 demonstrated reproducible Q8 image influence, **not** detectable signed quality lift from the tested extra four rays; its P1/P2/P3 progression stopped.
- **Next independent issue:** [N007 #43](https://github.com/owoDra/phos-gi-lab/issues/43) must establish adequate HDR reference signal and convergence eligibility before future quality claims. No new GI algorithm research is authorized by this consolidation.

**Read [research/status.md](research/status.md) first.** It is the single current architecture/status synthesis. [research/roadmap.md](research/roadmap.md) defines the next major gates; [research/branch-inventory.md](research/branch-inventory.md) locates all 25 original refs and preserves abandoned/negative experiments.

## Repository navigation

| Path | Purpose |
| --- | --- |
| [docs/research.md](docs/research.md) | Stable objective, fairness rules, end-state criteria |
| [research/status.md](research/status.md) | Current decision-grade synthesis and limitations |
| [research/roadmap.md](research/roadmap.md) | Three-phase forward plan; N007 remains a separate issue |
| [research/protocol.md](research/protocol.md) | Frozen measurement, correctness, provenance rules |
| [research/decisions/](research/decisions/) | Cross-lane adoption decisions |
| [research/lanes/](research/lanes/) | Frozen plans, results, and per-lane evidence |
| [research/integration/](research/integration/) | Historical I001 evidence |
| [src/](src/), [shaders/](shaders/) | Renderer and isolated historical research implementations |
| [scripts/](scripts/) | Experimental runners, evidence checks, reproducibility scripts |

Earlier branches remain immutable historical provenance. Imported historical lane sources are **not automatically activated in the production Renderer**. N001–N006 research variants may have separate targets; being present is not equivalent to being adopted.

## Building and validating

Requires a host C++20 compiler, Vulkan 1.3 loader/driver, and dependencies resolved by CMake/mise. The measured GPU for the historical results was AMD Radeon 8060S Graphics (RADV STRIX_HALO).

```bash
mise install
mise run build
mise run research:check
```

To launch a particular renderer or historical experiment, follow its lane-specific README and scripts, and confirm prerequisites and expected output before claiming a pass. Existing M0 controls are available as `mise run bench` and `mise run bench:sweep` (the Sponza scene may need downloading via `mise run assets`).

Raw runs under `out/research/` are local/ignored; retained results include experiment IDs, source SHAs, decision labels and artifact provenance. **Do not mistake an absent historical raw artifact for a newly reproduced result.**

## Workflow

Run studies on dedicated lane branches; integrate validated findings and their records into `research`; advance `main` only at a verified program checkpoint. No PR requirement and **no GitHub Actions/CI**. Follow [AGENTS.md](AGENTS.md) for evidence immutability and promotion gates.
