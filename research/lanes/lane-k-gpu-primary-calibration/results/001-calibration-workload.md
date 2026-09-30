# K001 — calibration workload validation

## Formal status

**PASS — K003 target calibration precondition satisfied.**

Target-host validation was executed from:

- Branch: `research-lane-k-gpu-primary-calibration`
- Measurement commit: `e4961e6227b25870331206b4d732e9ffdc8fd7d3`
- GPU: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`
- Driver: `radv` / Mesa 26.1.2
- Timestamp period: 10.019 ns
- Vulkan validation: enabled

## Validation result

Both frozen workload shapes passed deterministic correctness:

| Profile | Elements | Batch dispatches | Variants |
| --- | ---: | ---: | --- |
| accepted-shape | 8192 | 16 | baseline / +5% / +10% / +20% |
| single-dispatch-control | 8192 | 1 | baseline / +5% / +10% / +20% |

For all eight rows:

- GPU checksum matched the CPU reference checksum;
- every checksum was non-zero;
- variant checksums were distinct within each profile;
- the controlled-work ratios were exactly baseline / +5% / +10% / +20%;
- the target-device provenance was consistent across both profiles.

The accepted-shape controlled work was
26,214,400 / 27,525,120 / 28,835,840 / 31,457,280 units.
The single-dispatch control was
1,638,400 / 1,720,320 / 1,802,240 / 1,966,080 units.

The `vulkaninfo` capture also identified the active target as the RADV Strix Halo
device. A separate DZN ICD failed Vulkan instance creation and was skipped by the
loader; it was not the device used by K001.

## Decision

K001 validates the architecture-neutral controlled-work implementation and
target-device provenance required before K003. It contains no timing-resolution
claim and does not modify or reinterpret the K002 methodology freeze.

K003 may proceed under the unchanged `lane-k-k002-v1` protocol.
