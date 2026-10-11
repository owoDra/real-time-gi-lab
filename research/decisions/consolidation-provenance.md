# Consolidation provenance — 2026-10-11

N006 is a verified Git descendant of `main`, `research`, Lane K, Lane N and N005. Other branches are often divergent; this consolidation **copies their unique evidence and optional lane-local code** instead of fabricating merge ancestry. [Complete ref inventory](../branch-inventory.md).

- Lane A/B/C: final result indexes and missing files copied at Git-blob identity; placeholder `src/research/lane_{a,b,c}_*/CMakeLists.txt` retained. Full historical standalone targets must not register duplicate N-series shader output names.
- Lane D, E, F, G, H, I, J, L, M: owned `research/lanes/` subtrees and companion source, shader and script trees copied using original Git tree objects. The original Lane E results and later E revalidation are separate. The later `research-lane-j-formal-crossover` owns the canonical J folder; the original J variant and Lane M's altered J adapter remain accessible by old ref.
- I001: original `research/integration` evidence, plus later E integration source paths, retained without enabling independent targets.
- N-series: current N006 Renderer owns pinned imported dependency copies; these must not silently be replaced with differently versioned Lane A/B/I001 code.
- The extensive old status and old charter are archived byte-for-byte. Original accepted `results/*.md` and fixed results are never rewritten.
- Old branches are still Git refs, not parents of a newly manufactured empty merge. This is **selected-artifact integration with retained ref provenance**.

**Publication gate:** check full `mise run build`, `mise run research:check`, applicable Python tests, image-producing Renderer smoke run, non-activation of rejected targets and Markdown/results references before moving `research` or `main`. If runtime is unavailable, report **unverified** and retain the temporary integration branch. New N007 work is out of scope.
