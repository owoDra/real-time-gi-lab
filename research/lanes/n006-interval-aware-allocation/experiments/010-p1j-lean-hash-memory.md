# N006 P1j-A — lean hash/multiplicity scratch preflight

Issue #42. **Frozen before P1j-A GPU evidence.** P1i (source HEAD `85d0b295e5fed0575e984f8e7e9b3993ba347a6e`) passed byte-identical current vs actual canonical images in all 5 HWRT plus 5 software Lane-E-final scenarios. P1i's complete-GI times compare sequential cold-state frames and do **not** prove software performance improvement.

## Hypothesis, scope and intended engineering impact

The accepted canonical-probe pipeline already reduced actual GPU rays ~81–82%. Its extra scratch per run is **8,421,464 B (~8.03 MiB)**. Two GPU arrays (`hash_keys` and `canonical_multiplicity`) are each allocated for **524,288 slots** (~2 MiB each), even though each observed scenario has only 3,008–3,220 unique spatial keys. The prototype has a hard unique-key capacity of 8,192, so a separately opt-in **32,768-slot power-of-two hash table** has a worst-case allowed load <= 25%. Keeping fixed 128-probe linear probing with explicit insertion failures gives a bounded, falsifiable memory tradeoff; no global sort.

- Hash slots: 524,288 -> **32,768**.
- Each 4-byte key and multiplicity table: 2,097,152 -> **131,072 B**.
- **Theoretical total scratch: 8,421,464 -> 4,489,304 B**, **3,932,160 B saved (~46.7% of N006 scratch)** before accounting for Vulkan allocation alignment/extra residency. This is **not** a demonstrated 46.7% overall GI memory saving, and does not reduce the 4 MiB separate compact work copy yet.
- Keep the existing P1d hash and P1g/P1h/P1i canonical implementation intact by opt-in constructor/CLI switch `--canonical-lean-hash`. No CPU readback/sort/build of compact keys. Hash and owner multiplicity are GPU-only.

## Frozen correctness matrix

First run the **same 10-case P1i fixed matrix**, one fresh process per case, 32 source warmups and 2 sequential fixed motion=1 target frames: first original current, next P1j-A lean-hash canonical. Variants: `lane-e-final-hwrt`, `lane-e-final-software`; scenes: static, camera-motion, light-motion, moving-rigid, deforming-control. No independent reference, extra rays or changing baseline/candidate renderer output.

For every case require:
1. **Bit-for-bit equal current/canonical HDR PFM** with full source correctness, hit/storage failure=0, matching baseline and candidate visible owners, and case-specific original owner-output cardinalities.
2. Canonical actual GPU rays = exact discovered unique probe/cascade keys × eight, valid per-cascade cardinalities, all original owner counts reweighted, no insertion failure / key invalidation / overflow, and canonical hash collision steps recorded (must not censor expensive cases).
3. Report original/lean hash table slots, actual total scratch allocation including both hash tables and compact work, GPU canonical build time (diagnostic only), and all 10 individual exact image SHA digests and raw renderer evidence.
4. Fail closed on the first invalid case and preserve all accumulated results and retained stdout/stderr/PFM; do not overwrite accepted P1i. Never infer time speedup from these sequential cold target frames.

**GO P1j-B** to eliminating the redundant compact-to-original work-list copy (GPU zero-copy bindings) if 10/10 exact images and all bounded hash probes remain valid. **REFINE/STOP** on a failed insertion, high collision cost, bitwise divergence or unexpected allocation count. After P1j-B, a separately frozen warm state **matched HWRT+software timing** study must quantify end-to-end GI, post-producer stages and production peak memory. No claim of hardware without ray-query extension support until tested on such a GPU.

No N001/N004/N005 accepted renderer semantic changes, no GitHub Actions; P1a's predictive allocator question remains separate.
