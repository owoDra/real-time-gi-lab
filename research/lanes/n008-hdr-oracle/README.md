# N008 — independently validated HDR light-transport oracle

Study: [Issue #5](https://github.com/owoDra/real-time-gi-lab/issues/5). Branch: `research-n008-hdr-oracle`.
Prerequisite: [N007 bounded NO GO](../n007-reference-validity/results/012-n007-bounded-no-go-decision.md) (frozen; not reopened).

Goal: a small, auditable CPU HDR reference oracle whose physical correctness is established by analytic controls and an independently maintained integrator (Mitsuba 3) **before** any Renderer comparison.

**Status:** Phase A Exit A = GO ([004](results/004-phase-a-exit-decision.md)); Phase B Exit B = GO bounded ([006](results/006-phase-b-exit-decision.md)); Phase C complete ([008](results/008-phase-c-b4-gpu-diagnostic.md), [010](results/010-phase-c-gpu-diagnostics.json)); **final: oracle GO, cross-class reference set bounded NO GO** ([011](results/011-n008-final-decision.md)).

- Phase A protocol: [experiments/001](experiments/001-phase-a-oracle-spec-and-controls.md)
- Results: [results/index.json](results/index.json)
- Oracle source: `src/research/n008_hdr_oracle/` (opt-in `PHOS_BUILD_N008`, default OFF; also a standalone CMake project)
- Controls and cross-check: `scripts/research/n008_hdr_oracle/`
