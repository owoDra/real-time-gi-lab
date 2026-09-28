# phos-gi-lab

Research sandbox for a GPU-locality-first real-time global illumination architecture.

This repository does not assume that page-local caches, surfels, Radiance
Cascades, or any other current idea must survive. Each architectural premise is
isolated, measured, and either promoted or discarded.

## Research source of truth

- [Research charter](docs/research.md) — final research question, constraints,
  and long-term architecture hypotheses.
- [Current status](docs/status.md) — current milestone, accepted/invalidated
  evidence, open questions, and next decision gate.
- [Experiment 000](docs/experiments/000-page-local-cache.md) — current M0
  protocol for page-local cache locality.
- [Documentation policy](docs/README.md) — what belongs in code vs docs.

Implementation behavior remains authoritative in source code and executable
correctness guards; docs record goals, rationale, protocols, and evidence that
cannot be reconstructed from code alone.

## Current experiment

M0 asks one narrow question before building a GI renderer:

> Can page-local contiguous storage and locality-aware scheduling reduce GPU
> cache lookup cost relative to a fair open-addressed hash baseline?

The executable compares:

- `hash` — open-addressed global table sized from actual active cells;
- `paged` — direct page table + contiguous 64-entry pages;
- `paged-sorted` — the same page storage with queries grouped by page.

All variants must return the same semantic payload. A checksum mismatch makes
the benchmark fail instead of producing usable performance evidence.

## Environment

The workflow is managed by mise. The repository pins CMake, Ninja, and Python.
A host C++20 compiler and working Vulkan 1.3 driver/loader are required.

A Vulkan SDK installation is not required:

- Vulkan headers are fetched by `vk-bootstrap`;
- an installed `glslc` / `glslangValidator` is reused when present;
- otherwise pinned glslang is built automatically;
- NixOS benchmark tasks resolve the host Vulkan loader/ICD environment through
  `scripts/run_with_vulkan.sh`.

## Quick start

```bash
mise install
mise run bench
```

A successful single run emits:

```text
variant,queries,pages,bytes,gpu_us_per_dispatch,checksum,expected_checksum,correct
hash,...
paged,...
paged-sorted,...
```

For research evidence, prefer the matrix harness:

```bash
mise run bench:sweep
```

It runs the standard M0 query-count matrix with repeated processes and writes:

```text
out/benchmarks/<timestamp>/
  metadata.json
  results.csv
  summary.csv
  logs/
```

Generated artifacts are intentionally ignored by Git. After review, accepted or
invalidated evidence is summarized in `docs/status.md`.

Useful commands:

```bash
mise run build
mise run bench
mise run bench --queries 8000000 --iterations 200
mise run bench --validation
mise run bench:synthetic
mise run bench:sweep
mise run bench:sweep --query-counts 100000,1000000,4000000 --repeats 5
mise run bench:sweep:synthetic
mise run clean
```

## Scene

The default workload uses the classic Sponza scene fetched from
`KhronosGroup/Vulkan-Samples-Assets`. The asset is not committed to this
repository and retains its upstream license.

```bash
mise run assets
```

## Why C++20

The research target is low-level Vulkan behavior: explicit memory placement,
GPU cache behavior, ray-query integration, vendor profiling, and extension
experiments. C++ keeps the path to Vulkan tooling and reference implementations
short while the hot path remains explicit Vulkan.
