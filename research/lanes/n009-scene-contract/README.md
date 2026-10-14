# N009 — scene contract C1, back-face rule BF-P, probe-transport attribution

Branch: `research-n009-scene-contract` (from `research-n008-hdr-oracle` @ `12f4846`).
Origin: the three follow-ups of [N008 result 011](../n008-hdr-oracle/results/011-n008-final-decision.md). N006–N008 are frozen and not reopened.

**Final (2026-10-14): [result 009](results/009-n009-final-decision.md) — Exit SC = NO GO; BF1–BF3 = PASS; Exit PT = INCOMPLETE.** All preregistered computation is complete.

- C1/C2/C4/C5/C6 are DIRECT_DETERMINISTIC_PROVED under T_B2 and T_B8; their broadly lit total references fail the unchanged screen at the four-seed 8192-SPP cap. C3 light motion is NOT_CONSTRUCTIBLE under Amendment 1.
- All 10 GPU captures are byte-attested. C7 passes BF gates on software and hwrt; this does not establish Sponza per-pixel agreement. Sponza direct max-relative-error-1.0 pixels remain **unresolved (未解決)**.
- C7 fails V1; the old B4 capture fails V3. Probe coverage/range and shadow-removal observations remain diagnostic; excluding the 21 C7 mismatch pixels is explicitly post-hoc sensitivity, not a gate pass.

C1/BF-P remain an opt-in overlay (`PHOS_BUILD_N009`, default OFF). The final write-up uses archived evidence; build, executable tests and GPU/runtime checks were not rerun. No total-quality ranking or architecture promotion follows.

Work packages:
- **WP-BF:** one physical back-face rule (BF-P: every triangle is two-sided for every ray type) shared by the Renderer overlay and the references.
- **WP-SC:** Sponza under scene contract C1 (glTF node transforms, authored camera, preregistered interior light), with the unchanged N008 oracle and ladder, for every dynamic class.
- **WP-PT:** stage-wise attribution of the Renderer's probe-indirect errors (leak and deficit) with a CPU counterfactual ladder.

- Protocol: [experiments/001](experiments/001-scene-contract-backface-and-probe-attribution.md)
- Results: [results/index.json](results/index.json)
- Sources: `src/research/n009_scene_contract/` (opt-in `PHOS_BUILD_N009`, default OFF)
- Scripts: `scripts/research/n009_scene_contract/`
