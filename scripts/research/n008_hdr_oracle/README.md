# N008 HDR oracle harness (CPU only)

Protocol: [`research/lanes/n008-hdr-oracle/experiments/001`](../../../research/lanes/n008-hdr-oracle/experiments/001-phase-a-oracle-spec-and-controls.md).

```bash
cmake -S src/research/n008_hdr_oracle -B build/n008 -G Ninja && cmake --build build/n008
build/n008/test_n008_oracle                      # C++ unit tests
python -m venv .venv-n008 && .venv-n008/bin/pip install -r scripts/research/n008_hdr_oracle/requirements-crosscheck.txt
.venv-n008/bin/python scripts/research/n008_hdr_oracle/test_n008lib.py
.venv-n008/bin/python scripts/research/n008_hdr_oracle/phase_a_controls.py --summary out/research/n008-hdr-oracle/phase-a-controls.json
.venv-n008/bin/python scripts/research/n008_hdr_oracle/mitsuba_crosscheck.py --summary out/research/n008-hdr-oracle/phase-a-crosscheck.json
.venv-n008/bin/python scripts/research/n008_hdr_oracle/sensitivity_diagnostics.py --summary out/research/n008-hdr-oracle/phase-a-sensitivity.json
```

- `n008lib.py` — scene authoring/text format, canonical geometry SHA-256 (same bytes as the oracle), sidecar/PFM readers, analytic primitives, closed-form rectangle form factor, Gauss–Legendre quadrature, icosphere.
- `phase_a_controls.py` — A1–A10 physically known controls with frozen gates.
- `mitsuba_crosscheck.py` — X1–X6 against Mitsuba 3.6.4 `scalar_rgb` on identical meshes (independent `.n008` parser).
- `sensitivity_diagnostics.py` — post-hoc defect injection showing the gates fail on known transport errors (not a gate).

Raw PFM/sidecars stay in ignored `out/`; only compact JSON is committed under `research/lanes/n008-hdr-oracle/results/`. No GPU is used.
