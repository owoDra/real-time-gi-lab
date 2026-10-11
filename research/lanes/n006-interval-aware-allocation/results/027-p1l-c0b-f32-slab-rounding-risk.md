# N006 P1l-C0b — float32 slab division versus reciprocal: numerical non-equivalence demonstrated

Issue #42; 2026-10-11. **Offline deterministic CPU float32 roundoff-model result**, not compiled SPIR-V, not AMD GPU timing and not actual scene traversal. Reproduction in `scripts/research/n006_interval_aware_allocation/audit_p1l_c0_division_rounding.py` + `test_audit_p1l_c0_division_rounding.py`.

## Method / observed result

Python stdlib `random.Random(6006)`, **200,000** independent 1D x-entry arithmetic samples:
- `origin=f32(uniform(-3,3))`;
- `minimum=f32(origin+f32(uniform(0.0001,100)))`;
- `direction=f32(uniform(0.0005,10))`;
- `numerator=f32(minimum-origin)`;
- **baseline** `enter_div=f32(numerator/direction)`;
- **candidate** `enter_recip=f32(numerator*f32(1.0/direction))`.

Float32 storage rounding via `struct.pack('<f',...)` / unpack. Valid positive finite nonparallel positive-interval samples; actual result **51,445/200,000 (25.7225%)** had different float32 entry values. This percentage belongs only to the synthetic positive-direction numerical distribution and **cannot be extrapolated to physical E003 rays or GPU performance**.

The first differing synthetic sample (#7) was then used to construct a slab boundary:
- `origin_x = 0.26408806443214417`, `bounds_min_x = 55.509944915771484`,
  `bounds_max_x = 86.91512298583984`, `direction_x = 7.85129451751709`.
- `enter_div = 7.036528587341309`, `enter_recip = 7.03652811050415`.
- `tmax=7.03652811050415`; direct division **rejects**, reciprocal multiplication **accepts** the x slab, assuming y/z rays are parallel and their origin is strictly within the y/z slabs. Both computed x exits are `11.036527633666992 > tmax`. This **constructed boundary is post-hoc**, proving a possible accept/reject flip under this CPU arithmetic model, not the frequency of such flips on any real workload.

## Decision and scope

- The hypothesis **'replace the two per-axis divisions with per-ray reciprocal multiplication while retaining byte-exact accepted E003 hit/image outputs'** has **failed a prerequisite numerical-equivalence demonstration** in a software float32 model; do not implement it as a no-op-equivalent C1 shader without explicit real-GPU bit-exact proof. The existing accepted `ray_aabb_bounds` must remain unchanged.
- This is **not proof of a GPU difference**: GPU driver may already transform division, fuse operations or use other precision/fast-math behavior; actual SPIR-V and backend machine instructions were not available. It does not prove a performance penalty for division or establish that the C0 compiler audit is complete.
- Source/layout result [026](./026-p1l-c0a-e003-source-layout-audit.md) and prospective experiment [019](../experiments/019-p1l-c0-e003-wide-child-cost-audit.md) remain active. Next C0 gate is actual compiled original E003 source rebuild versus runtime-named SPIR-V hash, static opcode histogram and provenance artifact. No GPU C1 intervention is warranted yet; parent N006 P1m0 consumer coverage diagnostic is independently being prepared.

**Decision: REJECT unqualified reciprocal substitution as 'bit exact by algebra'; retain E003 unchanged.**
