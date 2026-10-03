# Lane N N001 scripts

`n001_contract.py` is the implementation truth for HDR exchange, playback identity, radiometric metrics, complete timing/memory schema, and target-artifact validation.

`run_n001.py` supports three phases:

- `--phase contract`: GPU-independent PFM/playback/metric smoke only;
- `--phase target`: requires a clean Lane-N checkout, exact scene SHA, built `phos-n001`, captures validation-layer output, finalizes provenance, and runs the target artifact validator;
- `--phase validate-target`: revalidates an existing target artifact root.

`test_n001_contract.py` covers deterministic playback hashing, PFM orientation, HDR metric behavior, target schema validation, integer memory accounting, path containment, and complete-GI stage accounting.

The target phase must be wrapped by `scripts/research/run_experiment.py` so raw logs and repository metadata are retained under `out/research/`.
