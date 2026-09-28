# D003 — one-pass visibility owner selection

Status: rejected for promotion

## Question

Can A001's two source scans for depth and deterministic owner selection be
replaced by one exact 64-bit packed `atomicMin` scan without changing owner
semantics or adding a conversion pass?

## Evidence source / provenance

The decision below is based on the uploaded `d003.csv` containing three
process-level repeats for each of static, camera-motion, and light-motion.

The CSV itself does not embed the git commit or artifact directory. The expected
measurement-ready branch head was
`6fee5a8c920da7e00ff7b29a61effe5a56dfedf1`, but this result record does not
treat that hash as independently verified measurement identity. This provenance
limitation does not change the performance rejection: the packed candidate loses
the fixed gate by large margins.

## Correctness

Every CSV row reports:

- correctness = true;
- overflow flag = 0;
- the same representative visible-owner/work counts as A001.

Representative counts:

| case | visible probes | work items |
| --- | ---: | ---: |
| static | 981 | 31,392 |
| camera-motion | 978 | 31,296 |
| light-motion | 981 | 31,392 |

The candidate therefore preserved the exact owner/work semantics exercised by
the A001 analyzer.

## Timing result

Three-repeat medians in microseconds:

| case | accepted A001 producer | two-pass staged producer | packed one-pass producer | packed vs staged |
| --- | ---: | ---: | ---: | ---: |
| static | 49.367 | 53.953 | 60.466 | +12.07% |
| camera-motion | 49.555 | 54.609 | 54.692 | +0.15% |
| light-motion | 51.475 | 54.068 | 57.163 | +5.72% |

End-to-end:

| case | accepted A001 E2E | two-pass staged E2E | packed one-pass E2E | packed vs staged |
| --- | ---: | ---: | ---: | ---: |
| static | 58.010 | 62.582 | 70.282 | +12.30% |
| camera-motion | 58.839 | 63.445 | 63.333 | -0.18% |
| light-motion | 60.648 | 62.793 | 65.804 | +4.80% |

Directly against accepted A001, packed one-pass producer total regressed:

- static: +22.48%;
- camera-motion: +10.37%;
- light-motion: +11.05%.

Direct accepted-A001 E2E also regressed in all three cases:

- static: +21.16%;
- camera-motion: +7.64%;
- light-motion: +8.50%.

The fixed D003 gate required a >=10% producer improvement and >=5% E2E
improvement versus staged two-pass, plus >=5% producer improvement and no E2E
regression versus accepted A001. The packed candidate fails decisively.

## Stage evidence

Median packed visibility selection itself was slower than the combined staged
32-bit depth+owner selection:

| case | staged visibility select | packed visibility select |
| --- | ---: | ---: |
| static | 31.358 | 37.243 |
| camera-motion | 31.236 | 33.448 |
| light-motion | 31.344 | 36.011 |

Packed reset is slightly cheaper than the two separate staged resets, but that
saving is overwhelmed by the 64-bit atomic selection cost.

Producer emit itself did not improve consistently enough to compensate:

| case | A001 emit | packed emit |
| --- | ---: | ---: |
| static | 14.791 | 15.495 |
| camera-motion | 15.207 | 14.379 |
| light-motion | 15.561 | 14.337 |

## Memory

The candidate used the intended 8 bytes/tile packed visibility storage, equal
in logical visibility bytes to A001's 4-byte depth plus 4-byte owner buffers.

Persistent/transient allocation and stream capacity were otherwise unchanged.
There is therefore no memory benefit that could justify the performance loss.

## Interpretation

The experiment rejects the specific exact packed-64 mechanism on the target
GPU. It does **not** show that all one-pass owner algorithms are impossible.

The useful finding is narrower:

- eliminating one source scan is insufficient when it replaces two 32-bit
  atomics with a contended 64-bit atomic;
- the packed path's exact semantics and zero-conversion design are not enough
  to overcome that atomic throughput cost on AMD Radeon 8060S / RADV;
- quantized or approximate 32-bit packing is outside D003 because it would
  change the accepted visibility semantics.

## Decision

- do not retain packed one-pass visibility selection;
- keep accepted A001 two-pass visibility semantics;
- keep D001 depth reuse as the only retained Lane D integration mechanism so
  far;
- continue to D004 and isolate producer work-allocation contention using the
  accepted surface-source producer semantics.

D003 changes no Lane B traversal or Lane C storage decision.
