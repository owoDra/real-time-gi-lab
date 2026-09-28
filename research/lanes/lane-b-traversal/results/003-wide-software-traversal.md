# B003 result — wide software traversal toward the HWRT gap

Status: accepted evidence; fallback improved; full B003 target not met

## Provenance

Formal target artifact:

`out/research/lane-b-traversal/003-wide-software-traversal/20260928T175711Z/`

Measurement checkout:

- branch: `research-lane-b-traversal`;
- commit: `c3dffb80b4640abfc6fcf1d22608c883de537378`;
- dirty: false;
- return code: 0.

Accepted A001 source:

- artifact: `out/research/lane-a-split-rc/001-representative-producer/20260928T143212Z/`;
- measurement commit: `8b647ef8dcf1150f86a9d25c039ca48bd7f30b8f`.

Target device:

- `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- RADV / Mesa 26.1.2;
- exact device match: true.

Formal run used 30 traversal iterations and 3 build repeats with validation
disabled, matching the B002 performance methodology.

## Correctness

All six candidates over all three exact A001 streams passed the B001 shared Hit
contract.

- total candidate rows: 18;
- total mismatches: 0;
- total runtime / stack errors: 0;
- brute-force reference parity: checked;
- static rays: 31,392;
- camera-motion rays: 31,296;
- light-motion rays: 31,392.

Primitive, material, instance, geometric-normal, finite-tMax, tie-breaking, and
glTF double-sided semantics therefore remain intact across the interpreted
performance rows.

## Final representative measurements

Final-run means across the exact A001 static, camera-motion, and light-motion
streams:

| candidate | mean trace us | persistent bytes | persistent MiB | disposition |
| --- | ---: | ---: | ---: | --- |
| hierarchical StrataBrick / binary micro BVH | 284.013 | 26,971,056 | 25.72 | B002 fallback baseline |
| Macro BVH8 + binary micro BVH | 615.409 | 26,998,832 | 25.75 | rejected |
| DDA/hash + float Micro BVH8 | 251.959 | 28,534,032 | 27.21 | positive mechanism evidence |
| **DDA/hash + conservative quantized Micro BVH8** | **231.226** | **22,833,584** | **21.78** | **selected B003 fallback** |
| quantized BVH8 + packet4 | 216.658 | 28,872,096 | 27.53 | rejected by fixed packet memory gate |
| quantized BVH8 + compact-metadata packet4 | 221.060 | 25,874,208 | 24.68 | rejected by fixed packet speed gate |

Per-case selected quantized traversal:

| workload | trace us |
| --- | ---: |
| static | 226.330 |
| camera-motion | 235.187 |
| light-motion | 232.161 |

## Mechanism conclusions

### Keep the segment DDA/hash top level

Replacing the disjoint segment-grid walk with a balanced Macro BVH8 is strongly
negative on this workload. The corrected Macro candidate is roughly 2.17x
slower than the same-run hierarchical baseline.

The B002 top-level spatial partition is therefore not the part to replace.

### Wide per-segment traversal is useful

Changing only the per-segment binary BVHs to float BVH8 reduces representative
mean traversal from 284.013 us to 251.959 us, about 11.3%, while preserving all
Hit semantics.

This establishes wide micro traversal as a useful mechanism.

### Quantized BVH8 is the best balanced result

Conservative parent-relative 16-bit child-bound quantization reduces the
selected candidate to 231.226 us and 22,833,584 persistent bytes.

Relative to the same-run B002-style hierarchical fallback this is:

- about 18.6% lower traversal time;
- about 1.23x speedup;
- about 15.3% lower persistent allocation.

The 27,406-node wide hierarchy uses 176-byte quantized nodes instead of
384-byte float nodes. Conservative outward rounding preserved zero-mismatch
correctness.

### Triangle packets are not retained

The original 256-byte packet layout is the fastest software row in the final
run at 216.658 us, but its persistent-memory ratio versus the quantized
non-packet candidate is above the fixed 1.25x B3 retention gate.

Compact metadata reduces packet persistent memory to 25,874,208 bytes but the
mean traversal becomes 221.060 us. Its 0.956034 trace ratio versus quantized
non-packet does not reach the fixed <=0.95 speed gate.

The thresholds were not relaxed after seeing the results. Packet variants remain
useful evidence but are not part of the selected B003 fallback.

## B003 success target

B003 predefined a full-success region of roughly <=175 us representative mean,
which corresponds to closing at least half of the accepted B002
hierarchy-to-HWRT traversal gap.

The selected quantized fallback measures 231.226 us. Using B002's accepted
65.725 us HWRT mean, it remains about 3.52x slower than HWRT and closes only
about 24% of the historical hierarchy-to-HWRT traversal gap.

Therefore:

- **software-fallback optimization succeeded materially**;
- **the full B003 HWRT-gap-closing target was not met**.

The protocol says to stop adding complexity when traversal does not reach that
region. GPU-side maintenance optimization is therefore not promoted as a B003
follow-up requirement: the traversal gate already rejects full-success status.

## Final B003 decision

For HWRT-unavailable operation, promote:

**segment DDA/hash + conservative quantized Micro BVH8**

as the evidence-backed software fallback.

Keep B002's primary decision unchanged:

**HWRT / TLAS remains the preferred traversal path when available.**

B003 changes the software fallback from the B002 binary-micro hierarchy to the
quantized Micro BVH8 variant. This should be carried into Integration #13 as the
fallback candidate, while the accepted B002 HWRT result remains primary.

## Limits

- representative final GPU evidence remains Sponza / exact A001 streams on one
  AMD Radeon 8060S / RADV target;
- B003 optimizes representative traversal, not complete GI frame time;
- B003 does not establish the selected fallback's moving-geometry maintenance
  cost;
- B002's controlled maintenance evidence remains the current dynamic-scene
  reference until Integration measures the combined architecture;
- packet behavior may differ on workloads with less segment membership
  duplication or different material/instance ranges.
