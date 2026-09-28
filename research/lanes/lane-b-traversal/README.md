# Lane B — geometry traversal

Issue: #11
Branch: `research-lane-b-traversal`

Mission: determine which traversal architecture best serves Split RC gather rays
under realistic dynamic-scene maintenance costs. StrataBrick is a candidate, not
a requirement.

## Status — B002 and B003 complete

Lane B's primary HWRT decision from B002 remains accepted. B003 is now complete and upgrades the software fallback to DDA/hash + conservative quantized Micro BVH8. Integration #13 is not blocked by Lane B.

Lane B B001/B002 established the final primary decision. B001 established the shared Hit contract and candidate
retention. B002 completed the final comparison on Lane A's accepted exact
producer streams and controlled moving geometry.

Accepted B002 target artifact:

- `out/research/lane-b-traversal/002-lane-a-exact-stream-traversal/20260928T164136Z/`;
- measurement commit: `b4baf15c15331411690530a1f9e7388d4e7d6fe8`;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- RADV / Mesa 26.1.2;
- clean tree, return code 0;
- representative correctness mismatches: 0;
- representative runtime errors: 0.

Formal result:

`results/002-lane-a-exact-stream-traversal.md`

## Final Lane B decision

- **Primary: HWRT / TLAS**
  - fastest on all three exact A001 streams;
  - fastest on both controlled moving-geometry maintenance regimes;
  - actual required Vulkan features, BLAS/TLAS creation, and ray-query
    correctness are proven on the intended physical GPU;
  - trade-off: about 64.69 MiB persistent allocation plus 35.06 MiB reusable
    explicit AS scratch in this benchmark.

- **Software fallback: hierarchical StrataBrick-derived traversal**
  - consistently faster than the simple software BVH;
  - localized refit/rebuild behavior works;
  - about 25.72 MiB persistent allocation;
  - retained for portability / HWRT-unavailable or memory-sensitive regimes.

- **Baseline/reference only: software BVH**
  - correct and simplest, but not competitive enough to promote.

- **Rejected: raw sparse-grid DDA**
  - B001 already rejected it as a standalone final architecture.

B002 representative traversal medians:

| workload | software BVH us | hierarchical us | HWRT/TLAS us |
| --- | ---: | ---: | ---: |
| static | 382.767 | 281.415 | 66.066 |
| camera-motion | 376.155 | 276.305 | 63.982 |
| light-motion | 383.469 | 295.281 | 67.128 |

Controlled update + post-update trace:

| regime | software BVH us | hierarchical us | HWRT/TLAS us |
| --- | ---: | ---: | ---: |
| bounds-only | 19,933.237 | 11,081.034 | 3,253.467 |
| topology-change | 17,979.975 | 10,105.977 | 3,247.523 |

## Integration handoff

Integration #13 should use HWRT/TLAS as Lane B's evidence-backed primary
candidate on the measured target.

Carry these caveats into integration:

- HWRT has a substantially larger memory footprint than the software paths;
- keep the hierarchical candidate available as fallback rather than treating the
  simple software BVH as the fallback architecture;
- A001 has no moving geometry, so B002 movement evidence is controlled
  mechanism-isolation evidence;
- final large/vertical/dynamic stress and complete GI frame-time/quality evidence
  remain Integration responsibilities.

Do not interpret Lane B's traversal winner as proof that the combined GI
architecture is superior before Integration #13 passes its end-to-end gate.


## B003 — software fallback optimization

B003 is testing whether a software traversal shaped more like a two-level wide
RT hierarchy can materially reduce the gap to HWRT without losing the memory
advantage.

Stage A replaces only the B002 segment-grid DDA/hash front end with a Macro
BVH8 while keeping the proven binary per-segment BVHs. This is intentionally the
cheapest structural rejection test.

If Stage A cuts same-run representative traversal by at least 20% with at most
15% extra persistent memory, B003 will continue to wide micro-BVH,
quantized/compressed bounds, compact stack, and only then consider triangle
packets / GPU-side maintenance.

Protocol:
`experiments/003-wide-software-traversal.md`.


### B003 candidate selection checkpoint

Stage B3.1 rejected packet retention under the unchanged gate. The current best software-fallback candidate is **DDA/hash + conservative quantized Micro BVH8**. It is materially faster and smaller than the B002 binary-micro hierarchy, but does not meet B003's <=175 us full gap-closing success target. Formal B003 result publication is pending verification of the complete final-run provenance/config/correctness artifact set.


## B003 final fallback update

Formal result:

`results/003-wide-software-traversal.md`

Accepted B003 artifact:

`out/research/lane-b-traversal/003-wide-software-traversal/20260928T175711Z/`

B003 final fallback:

- **DDA/hash + conservative quantized Micro BVH8**;
- representative mean traversal: **231.226 us**;
- persistent allocation: **22,833,584 bytes / 21.78 MiB**;
- zero B001 Hit mismatches/runtime errors.

Relative to the same-run B002-style hierarchical fallback, this is about 18.6%
lower traversal time and 15.3% lower persistent allocation.

B003 did **not** meet its <=175 us full HWRT-gap-closing target. HWRT/TLAS
therefore remains the primary architecture by a large margin. Integration #13
should use the quantized Micro BVH8 candidate as the software fallback rather
than the older binary-micro hierarchy.
