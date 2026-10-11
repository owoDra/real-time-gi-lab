# Research archive consolidation — verification and publication decision (2026-10-11)

## Acceptance scope

The repository owner explicitly authorized publishing **existing completed research results without rerunning the GPU experiments, builds, or test suites**. The scientific evidence consists of **previously accepted results at their recorded source commits, test configurations, process counts, original measurement methods, and artifact digests**, not a new performance or quality claim.

This is **evidence-and-history consolidation**, not certification that the newly combined historical standalone test programs all compile. The currently active N006 Renderer/GLSL/CMake/mise pipeline is not intentionally changed by this consolidation. The newly restored standalone A–M research sources and shaders are dormant, **not** made default build targets.

## Provenance and static verification

- Audited **25 original remote branches**, recorded HEAD, Git merge base and ahead/behind for each in [branch-lineage.json](branch-lineage.json); 16 diverged, 8 are ancestors of N006 and N006 itself is identical to the selected base. No original branch was deleted, force-pushed or spuriously merged.
- N006 base: `fffe594a4731f9cb8a939c4eab3f68b3948b2d69`. It already descends from original `main` and `research`, so a non-forced fast-forward can publish it after verifying the refs have not changed.
- Consolidation preserves every original N006 path; all original experiment result markdown objects and accepted measurement records are unchanged. Only intended program-level documentation and A/B/C seed result indexes were replaced, while old program text is byte-preserved under archive paths.
- A–M/I001 missing lane evidence and lane-owned historical scripts, shaders and C++ trees were carried over from their Git object IDs. Selected differing branch variants remain reachable via the original named Git refs; see [inventory](branch-inventory.md) and [provenance](decisions/consolidation-provenance.md). **This is not a full merge of all divergent commit histories**.
- 17 lane/N-series results indexes and their referenced result documents: **all paths present** in the consolidated Git tree.
- The newly written main navigation/status/decision documents were link-checked without missing local targets before publication.
- CMake root, `mise.toml`, common `research/protocol.md`, shared verifier and active A/B/C/N CMake files: **blob-identical to N006**. No GitHub Actions or CI files introduced; no discarded/experimental old shaders registered with the default build.

## Execution verification — not rerun, by explicit scope decision

| Check | This consolidation |
| --- | --- |
| Immutable historical results and source commit provenance | Preserved by Git object identity, with references recorded |
| Git branch/ref ancestry and inventory | Checked with GitHub API |
| Research result index/reference existence | Checked |
| Active build graph identity vs N006 | Checked |
| New C++ compile and GLSL compile | **Not run** |
| New Python tests / `research:check` | **Not run** |
| New Vulkan Renderer GPU smoke tests | **Not run** |
| New performance/quality/memory benchmarks | **Not run** (not needed for retrospective reporting) |

**Publication decision:** acceptable as an evidence-only research checkpoint by owner direction. Do **not** describe the imported old programs as newly build-validated, or any historical performance claim as newly reproduced. Any subsequent executable behavior change must be validated normally.

For optional local regression checking, a developer may run:

```bash
mise install
mise run build
mise run research:check
python -m unittest discover -s scripts/research/lane_n_end_to_end_renderer -p 'test_*.py' -v
python -m unittest discover -s scripts/research/n005_adaptive_tracing -p 'test_*.py' -v
python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py' -v
python scripts/research/lane_n_end_to_end_renderer/run_n001.py --phase contract
```

[Issue #43 / N007](https://github.com/owoDra/phos-gi-lab/issues/43) is an independent, unfinished reference-validity study. It was neither started nor silently treated as solved in this consolidation.
