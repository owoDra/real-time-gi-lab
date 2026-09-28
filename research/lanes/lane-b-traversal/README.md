# Lane B — geometry traversal

Issue: #11
Branch: `research-lane-b-traversal`

Mission: determine which traversal architecture best serves Split RC gather rays
under realistic dynamic-scene maintenance costs. StrataBrick is a candidate, not
a requirement.

## Status — B002 complete; B003 fallback optimization active

Lane B's primary decision from B002 remains complete and accepted. B003 is an optional software-fallback optimization follow-up and does not block Integration #13.

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
