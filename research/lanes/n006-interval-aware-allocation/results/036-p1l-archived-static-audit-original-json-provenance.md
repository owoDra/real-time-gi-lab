# N006 — late-arriving original P1l-B1c/C0 static audit JSON: matched, NO new GPU evidence

2026-10-11 user attached three full historic audit JSON files **after** P1m1c had completed and P1m2a experimental code had been pushed. Original P1l-C0 audit reports dated **2026-10-11T04:23:35 UTC** and source git checkout **`8a5cb251384ba14deb6c158057583fcd8214e335`**; do **not** attribute these to today's newer P1m2a head. The files were read directly and their original-byte hashes independently calculated in the assistant container; claimed nested SPIR-V hashes still originate from the uploader's historical local audit, because no .spv raw files were attached.

| Received original file | Original file SHA256 | Protocol / type |
|---|---|---|
| `b1c-spv-audit.json` | `409cf6f82878c765ebc087cfed0dbd3339dca665c066bd7651f3d3b7271ae294` | `n006-p1l-b1c-spirv-static-audit-v1` |
| `p1l-c0-e003-static-audit.json` | `830f26eeb0677aad4cf679f2f18d2c5107e70fd62e6eb0bf96bff8292f58bf23` | `n006-p1l-c0-e003-spirv-static-audit-v1` |
| `p1l-c0-floating-divide-risk.json` | `f43cd00f8b80d2105c0e242f7db94f9e008afd7ca76bfc90c273f339908a2179` | `n006-p1l-c0-f32-division-risk-v1` |

## Direct audit checks from full JSON

- **B1c static compiler artifacts**: accepted original 14,984 SPV bytes, 918 static instructions, 157 OpLoad, 24 OpBranchConditional. Candidate B1c 16,084 bytes (+1100), 992 instructions (+74), 173 OpLoad (+16), 27 conditional branches (+3). Rejected B1a comparator 16,120 bytes (+1136), 979 instructions (+61), 175 OpLoad (+18), 25 conditional branches (+1). These are **static SPIR-V opcodes**, not physical register/cache/occupancy, dynamic instruction counts or actual Vulkan execution. Confirmed JSON deltas reproduce exact earlier result [028](./028-p1l-c0-static-spv-provenance-pass.md), and **do not overturn B1c GPU REJECT** in [025](./025-p1l-b1c-packed-axis-performance-reject.md). The earlier result's statement that the original JSON *had not been provided at that time* is now superseded **only as file availability**, not a retroactive GPU performance result.
- **C0 E003 binary identity audit**: historical source rebuild and active runtime-named `e003_instance_quantized.spv` both report SHA256 `5f3ee73417b17b0b08329a93c0f065beddb578e64150f5f2f787b831ebba7e69`, 36,072 bytes and **7 static OpFDiv**. B0 count-only variant 38,404 bytes (+2332), 7 OpFDiv, 2390 vs 2246 static instructions (+144). `provenance_status=MATCHED`, `status=ready_static_only`. Equality of the **reported hashes** is established by the file, not independently recompiling/downloaded SPV; GPU compiler lowering, per-ray cost, SSA hoisting and registers remain unmeasured.
- **Float32 risk**: frozen seed=6006, samples=200,000, `different_float32_enters=51,445` (25.7225%). Synthetic boundary index 7 has direct-division `enter=7.036528587341309` > `tmax=7.03652811050415`, reject; reciprocal-multiply `enter=7.03652811050415` <= same tmax, accept. This is **constructed synthetic CPU float32 arithmetic**, not an actual E003 GPU hit divergence. Consistent with earlier [027](./027-p1l-c0b-f32-slab-rounding-risk.md).

## Unchanged gate

**P1l-B1c remains rejected by prior matched GPU data; C0 remains a static-provenance PASS with no E003 C1 hypothesis accepted; reciprocal substitution remains unsafe to call byte-exact; P1m2a remains the separate next unmeasured GPU study.** Do not rerun historical B1a/B1c/C0 campaigns, invent GPU speedups or claim M2a passed based on these files. Next N006 action is the already prepared `bash scripts/research/n006_interval_aware_allocation/run_n006_p1m2a_tetra_octant.sh`, requiring user-local AMD GPU execution and `n006-p1m2a-tetra-octant-summary.json` outcome.
