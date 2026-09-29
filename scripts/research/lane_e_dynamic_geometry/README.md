# Lane E research scripts

Lane E reuses the accepted Integration I001 executable as the baseline runtime.
Lane-owned scripts orchestrate validation, repeated timing, provenance capture and
fixed-gate evaluation without introducing a duplicate rendering/traversal stack.

Entrypoints:

- E001: `run_e001.py` — current dynamic-ownership decomposition.
- E002: `run_e002.py` — current HWRT control versus immutable rigid-object
  BLAS + TLAS UPDATE/BUILD policies.
- E003: `run_e003.py` — current software control versus immutable object-local
  binary/quantized StrataBrick instance ownership.

Formal runs require the exact Lane E branch, a clean tree, and the target
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`. Each experiment runs its
validation matrix before accepted timing; validation-only mode is available for
the pre-timing checkpoint.
