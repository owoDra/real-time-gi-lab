# Consolidation verification and publication gate — 2026-10-11

## Audited staging state

- Base: N006 `fffe594a4731f9cb8a939c4eab3f68b3948b2d69`, a descendant of the old `research` and `main`.
- Audit: 25 original remote heads in [branch inventory](branch-inventory.md) plus exact Git merge-base and ahead/behind data in [branch-lineage.json](branch-lineage.json). **16 divergent / 8 ancestor / 1 same**, and no branch ref deleted or force-pushed.
- Consolidated Git tree checked with GitHub: **1,166 tree entries** versus **512** in the N006 baseline; original paths all present; only intended README/AGENTS/charter/status/result-index blobs replaced, with earlier summaries archived byte-for-byte. Original experiment result Markdown/SHAs unchanged.
- Evidence: **17 lane/N-series result indexes** were checked against the consolidated tree; **all referenced result paths present**, including N006's new 45-item archive index. Read-only result material is carried over from the original object IDs.
- Documentation: **9 newly authored/rewritten top-level and program documents**, all **114** relative/external Markdown links scanned; **no missing local link targets** in the consolidated tree.
- Build graph: root CMake, mise configuration, research protocol, verifier and A/B/C/N active CMake files retain **exact N006 blob SHAs**. No GitHub Actions workflow files introduced.
- Algorithm policy: no new GI algorithm research, no N007 changes, no old experimental shader targets registered, no rewriting historical accepted evidence.

## Execution gate — NOT YET VERIFIED

This connector-only consolidation environment **cannot clone the private repo** because its terminal cannot resolve github.com; it also does not provide the study GPU. Consequently **no successful local C++, GLSL, Python-suite build or Vulkan Renderer run is claimed**. The program is **not approved** for moving `research` or `main` until those tests pass. This is a deliberately retained quality gate, not an accepted waiver.

Execute on a developer machine with access to the private repository and a Vulkan-capable GPU:

```bash
git fetch origin --prune
git switch --track origin/integration/2026-10-research-consolidation
# If that local branch already exists: git switch integration/2026-10-research-consolidation
git pull --ff-only
mise install
mise run build
mise run research:check

python -m unittest discover -s scripts/research/lane_n_end_to_end_renderer -p 'test_*.py' -v
python -m unittest discover -s scripts/research/n005_adaptive_tracing -p 'test_*.py' -v
python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py' -v
python scripts/research/lane_n_end_to_end_renderer/run_n001.py --phase contract
```

Check the applicable retained Lane E/M test suites if the copied source is to be built separately. Confirm an N001/N003/N004 **actual Renderer target** can start, dispatch and produce HDR PFM on the test GPU under the saved scene/config, without replaying huge historical formal campaigns. Use lane-specific `run_n001.py --phase target` through `run_experiment.py` only after confirming exact Sponza asset/digest and required target options. The GPU-independent N001 contract is **not** a replacement for runtime smoke.

Before promoting:
- Verify no changed reference SHA, source/import dependency, build cache or required asset mismatch.
- Check all cloned branch object IDs against the recorded audit; check `git diff --check` and uncommitted state.
- Ensure new inactive source trees do **not** alter the default build/renderer dispatch behavior.
- Confirm errors, missing raw artifacts or historical invalid reference comparisons are not misrepresented as accepted.
- Advance `research` by verified fast-forward from the N006-derived checkpoint if the remote ref still has the audited ancestry; only then fast-forward `main` if it remains an ancestor and the gate passed. Never force-push.
- On any failure: keep `main`/`research` unchanged; correct on the temporary integration branch and rerun the affected test, without modifying accepted experimental evidence.

N007 [#43](https://github.com/owoDra/phos-gi-lab/issues/43) is the separate next research task, **not** a prerequisite to reviewing this archive's existing evidence, and is not to be started in the consolidation session.
