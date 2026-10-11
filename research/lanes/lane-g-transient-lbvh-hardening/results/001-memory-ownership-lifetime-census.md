# G001 — Memory ownership and lifetime census

Status: **accepted diagnostic evidence — G001 complete**  
Plan: `lane-g-g001-v1`

## Question

Can the F007 transient-LBVH sparse-memory failures be explained byte-accurately
without changing the architecture, and are they actually caused by the transient
LBVH itself?

F007 anchors:

- sparse-stress: **3.0836x** run-local vanilla;
- sparse-moving: **3.2025x** run-local vanilla.

## Provenance

- branch: `research-lane-g-transient-lbvh-hardening`;
- target measurement commit:
  `0fcd6bce9576be5fdc708e434991b811e88cc74c`;
- target GPU: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- validation: enabled;
- cases: 20;
- supplied retained artifacts:
  - `g001-raw-frames.csv`;
  - `g001-raw-allocations.csv`;
  - `g001-byte-ownership.csv`;
  - `g001-summary.json`;
  - `g001-validation.json`.

The target run passed all quality/storage/device checks. The sum of individually
counted Vulkan allocations equals the historical F007-derived
`peak_resident_bytes` exactly for every case, and no duplicate Vulkan
allocation census names were found.

The F007 sparse anchors were reproduced:

| scenario | F007 anchor | G001 observed | absolute delta |
| --- | ---: | ---: | ---: |
| sparse-stress | 3.0836x | 3.083636x | 0.0000364 |
| sparse-moving | 3.2025x | 3.202487x | 0.0000130 |

## Byte-accurate root cause

### Sparse-stress

| ownership | transient-LBVH variant |
| --- | ---: |
| shared integration | 14,483,168 B |
| static HWRT | 104,595,424 B |
| transient LBVH | **0 B** |
| total peak | **119,078,592 B** |
| vanilla total peak | **38,616,288 B** |

The transient-LBVH variant and run-local `combined-hwrt` control have the
**same 119,078,592 B peak** in this scenario.

The +80,462,304 B excess over vanilla is exactly explained by replacing the
24,133,120 B vanilla software-control ownership with 104,595,424 B of static
HWRT ownership. No transient-LBVH allocation exists in this stable scenario.

Therefore the F007 sparse-stress memory failure is **not an LBVH-size failure**.
It is an integration ownership/lifetime failure dominated by static HWRT memory.

### Sparse-moving

| ownership | transient-LBVH variant |
| --- | ---: |
| shared integration | 19,201,760 B |
| static HWRT | 104,233,440 B |
| transient LBVH | **232,960 B** |
| total peak | **123,668,160 B** |
| vanilla total peak | **38,616,288 B** |

The transient-LBVH allocation is only **232,960 B / 0.222 MiB**, about **0.19%**
of candidate peak memory.

Its byte ownership is:

| LBVH allocation class | bytes |
| --- | ---: |
| immutable dynamic template | 50,944 |
| current-frame geometry | 50,944 |
| radix/sort scratch | 26,048 |
| node/topology/bounds scratch | 105,024 |
| total | **232,960** |

The radix key double buffer is explicit: `keys-a` and `keys-b` are
12,736 B each. No dense-only capacity retained in a sparse workload was found.

Compared with run-local `combined-hwrt` in the same sparse-moving scenario,
the transient candidate adds 4,589,568 B net:

- +4,718,592 B from the separate static-hit + dynamic-hit streams;
- +232,960 B from the complete transient-LBVH allocation set;
- -361,984 B because the candidate static HWRT excludes the moved 796
  primitives.

This explains the increase from the 3.083636x HWRT baseline to 3.202487x.

## Lifetime overlap

For the immutable/static HWRT path, the following allocations remain allocated
for the full runtime although their measured use is setup-only:

- vertex build input;
- TLAS instance build input;
- acceleration-structure scratch.

Retained setup-only bytes:

| scenario | retained setup-only bytes |
| --- | ---: |
| sparse-stress | **46,202,400 B / 44.06 MiB** |
| sparse-moving | **46,017,696 B / 43.89 MiB** |

This is the largest directly identified non-overlapping lifetime opportunity.

**Diagnostic-only what-if:** subtracting these already-proven setup-only
allocations, without claiming an implemented optimization, would reduce the
reported candidate/vanilla peak ratio to approximately:

- sparse-stress: 1.887x;
- sparse-moving: 2.011x.

This is not G003 evidence and does not authorize an architectural conclusion;
it only identifies the first memory-lifetime hypothesis to test later.

## Other accounting findings

### Vulkan allocation size vs logical payload

Vulkan allocation padding is negligible:

- sparse-stress candidate: 33 B total padding;
- sparse-moving candidate: 37 B total padding.

Allocation granularity is therefore rejected as an explanation for the F007
memory failure.

### Host mirrors

Host mirrors are measured independently but are not included in the historical
F007 device peak:

- sparse-stress: 44,040,192 B;
- sparse-moving: 44,043,376 B.

They are real process memory, but they do not explain the 3.0836x / 3.2025x
device-memory gate failure.

### Double counting

Rejected as a cause.

- every case exactly reconstructs the F007 peak from individual allocations;
- duplicate Vulkan allocation names: none;
- F007 sparse anchors reproduce within the frozen tolerance.

## G001 disposition

### Accepted

- F007 sparse-memory failure is reproduced byte-accurately.
- Static HWRT ownership is the dominant cause.
- Static HWRT setup-only allocations have a measurable runtime-lifetime overlap.
- Sparse-moving split hit streams add 4.5 MiB.
- The transient LBVH itself is small for the frozen 796-primitive moving set.

### Rejected

- "the transient LBVH itself causes the 3.08x / 3.20x sparse memory blow-up";
- Vulkan allocation padding as a material cause;
- accounting double counting as a cause;
- dense-only LBVH capacity retention as a cause in the measured sparse cases.

### Conditional

The setup-only HWRT buffers and split-hit-stream ownership are valid future G003
memory-hardening candidates **only after G002 establishes decision-valid timing
repeatability**. No memory optimization was made in G001.

### Inconclusive / not claimed

- no Lane E superiority/replacement conclusion;
- no timing conclusion;
- no rigid/stable-deforming/topology-changing promotion conclusion.

## Decision

**G001 is complete. Proceed to G002 timing-repeatability diagnosis without
changing the architecture.**
