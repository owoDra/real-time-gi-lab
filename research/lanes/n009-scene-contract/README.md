# N009 — scene contract C1, back-face rule BF-P, probe-transport attribution

Branch: `research-n009-scene-contract` (from `research-n008-hdr-oracle` @ `12f4846`).
Origin: the three follow-ups of [N008 result 011](../n008-hdr-oracle/results/011-n008-final-decision.md). N006–N008 are frozen and not reopened.

Work packages:
- **WP-BF:** one physical back-face rule (BF-P: every triangle is two-sided for every ray type) shared by the Renderer overlay and the references.
- **WP-SC:** Sponza under scene contract C1 (glTF node transforms, authored camera, preregistered interior light), with the unchanged N008 oracle and ladder, for every dynamic class.
- **WP-PT:** stage-wise attribution of the Renderer's probe-indirect errors (leak and deficit) with a CPU counterfactual ladder.

- Protocol: [experiments/001](experiments/001-scene-contract-backface-and-probe-attribution.md)
- Results: [results/index.json](results/index.json)
- Sources: `src/research/n009_scene_contract/` (opt-in `PHOS_BUILD_N009`, default OFF)
- Scripts: `scripts/research/n009_scene_contract/`
