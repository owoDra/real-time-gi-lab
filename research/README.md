# Research evidence guide

Start at [current synthesis](status.md) and [roadmap](roadmap.md). This directory retains **both positive and negative** experimental decisions; a completed study does not imply that its experimental implementation is adopted.

- [Branch inventory](branch-inventory.md): all 25 original Git refs, original commit SHAs, lineage and disposition. Also covers historical M0, `chore/*`, `exp/*`, `issue/*` and the often-overlooked J formal-crossover branch.
- [Decisions](decisions/2026-10-11-program-adoption.md): promoted, conditional and rejected methods.
- [Lanes](lanes/): accepted plans, result documents, indexes, and failure evidence from completed A–M and N-series branches.
- [Integration I001](integration/): end-to-end integration gate history.
- [Protocol](protocol.md): shared rigorous measurement/quality correctness rules.
- [Archived prior synthesis](archive/status-2026-10-02.md): original lengthy A–M historical program summary, retained verbatim for audit.

History is in Git **and** in this research tree. A branch archived in the inventory is not to be force-pushed or deleted. Existing source SHAs and raw artifact digests remain meaningful; original `out/research/` raw artifacts may be machine-local rather than included in this repo.

Historical experimental implementations in `src/research`, `shaders/research` and `scripts/research` are opt-in provenance/reference material. The current Renderer does **not** automatically import or execute every lane directory. The N-series' pinned imported source files must not be silently substituted.

### Result statuses

Accepted = met pre-frozen gate. Rejected/STOP = did not. Conditional/REFINE = restricted regime or further evidence required. Inconclusive/invalidated = not a valid positive/negative promotion gate. Diagnostic-only = useful observations with no architecture promotion. Treat all as persistent scientific results.

### How to evaluate a past claim

Follow the lane's `results/index.json` (when provided), its referenced result Markdown, the source SHA, exact workload/config, complete GPU timestamp/correctness/memory boundary and any retained artifact digest. The live branch tip may have progressed beyond the source SHA for a measurement: do not retroactively promote the later code.
