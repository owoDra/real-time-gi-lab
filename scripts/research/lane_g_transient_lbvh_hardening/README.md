# Lane G research scripts

G001 writes retained artifacts under:

`out/research/lane-g-transient-lbvh-hardening/001-memory-ownership-lifetime-census/<timestamp>/`

GPU-independent checks:

```bash
mise exec -- python -m unittest scripts/research/lane_g_transient_lbvh_hardening/test_run_g001.py
mise run research:check
mise run build
```

Accepted G001 target run:

```bash
mise run assets
mise run build
mise exec -- python scripts/research/lane_g_transient_lbvh_hardening/run_g001.py --validation
```

The runner requires a clean `research-lane-g-transient-lbvh-hardening`
worktree and exact device
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`. It aborts if the individual
allocation census differs from the F007 peak accounting by one byte, if a
required ownership role is missing, or if a Vulkan allocation lacks logical
payload size.
