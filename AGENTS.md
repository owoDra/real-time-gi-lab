# Research repository operation

## Purpose and sources of truth

- `docs/research.md`: stable mission, evaluation criteria.
- `research/status.md`: **the single current** architecture, status and limitations.
- `research/roadmap.md`: open, large research questions and exit gates.
- `research/protocol.md`: reusable correctness, GPU timestamp, memory and evidence rules.
- `research/decisions/`: cross-lane decisions, with reasons.
- `research/lanes/<lane>/results/`: detailed outcome records; historical branches and source SHAs remain provenance, not competing current summaries.
- Source, shader, tests: executable behavior. Do not replace source truth with prose.

## AI research transparency

This project was largely developed through AI-assisted, near-autonomous iterations using ChatGPT and OpenAI Codex CLI, with human oversight. Keep that provenance visible in the [research workflow disclosure](docs/ai-research-workflow.md) and README. Treat human-operated GPU measurements and archived evidence as authoritative; do not imply AI independently performed unavailable hardware verification or that every line has a known AI author.

## Branch roles

- `main`: verified, published research-result checkpoint; **not** an active experimental branch.
- `research`: integrated, reviewed research assets and cross-lane decisions.
- A dedicated `research-lane-*` (or explicit `research-n*`) branch per experiment. Experiment commits normally go directly to that branch.
- **New or changed executable Renderer behavior** requires build, applicable tests, and runtime/correctness checks before architecture promotion. A **historical evidence-only consolidation** may publish with explicit user authorization, immutable source/evidence identities, verified Git ancestry, result-index/link checks, and a provably unchanged active build graph; record that tests were **not rerun** and do not claim runtime regression validation. Promote to `main` only after the appropriate checkpoint gates.
- Preserve historical Git refs, non-promotion results, failed runs, and the exact accepted evidence bytes. No force push or ref deletion during consolidation.
- Never use `git merge -s ours`, synthetic empty merges or misleading commit ancestry to present missing files as integrated. Preserve actual records and explain any branch kept as a historical ref.
- No pull-request requirement for routine studies. Do not add GitHub Actions, CI workflows or secret-bearing logs.

## Current-vs-historical separation

- Historical standalone study files may be in `src/research/`, `shaders/research/`, and `scripts/research/`, but that does **not** authorize linking them into the current Renderer or default CMake build.
- The N-series Renderer contains pinned imported source/shader copies. Do not casually deduplicate them against historical Lane A/B/I001 trees: compare exact semantics, shader names, provenance and tests first.
- Do not enable old A/B targets wholesale: they register overlapping shader output names with the N-series CMake definition. Keep the historical code accessible without changing the default build graph.
- Before deleting or rewriting historical experiments, verify that their adopted/rejected results, hashes, configs and references remain reachable. Prefer retaining the original branch to destructive archival operations.

## Measurement and quality

1. Pre-register a falsifiable question, exact comparison boundary, quality/semantic parity, evidence classifier, memory constraints, minimal detectable effect and stop conditions.
2. GPU timestamp is the primary performance decision axis; CPU wall is health/provenance/diagnostic. Confirm the precision of the actual workload boundary (Lane K 5% is **not** transferable to Lane L's heavy boundary, which demonstrated 20%).
3. Include end-to-end costs, persistent and true-peak memory, correctness and movement/dynamic regimes. Preserve all samples; no post-hoc threshold changes or cherry-picked scenes.
4. Treat black/low-signal CPU HDR references as **ineligible until validated**; zero whole-frame p99 under sparse illumination is not proof of convergence. N007 remains separate; do not rewrite N006's negative result.
5. No general superiority claims from only a single GPU/Sponza or a non-equivalent quality budget.
6. Never request privileged GPU clock/power forcing (prior Lane G safety incident).
7. Compare representative existing GI families fairly; report both wins and losses.

## Basic commands

```bash
mise install
mise run build
mise run research:check
```

Perform explicit GPU/runtime smoke tests only on an environment that can execute them. Report unexecuted checks as **not run**, never PASS. Keep independent research outcomes distinct from release-level acceptance.
