# F006 — Geometry-class crossover controls

Plan: `lane-f-plan-v1`  
Measurement commit: `770416b7949b691c682da6018df21d3836e4be1e`  
Target: AMD Radeon 8060S Graphics (RADV STRIX_HALO), RADV / Mesa 26.1.2

## Outcome

**Correctness PASS. Accepted timing INCONCLUSIVE after the one permitted identical full rerun also remained unstable.**

All 12 validation cases passed across transient-LBVH, transient-grid and the
matching extended vanilla software control for rigid-large-few,
rigid-small-many32, deforming and topology-replace25.

The first accepted timing campaign exceeded the frozen
`complete_gpu_us max/min > 1.20` rule in three cases. The one permitted
identical full-campaign rerun still exceeded the rule in one case:
`vanilla-software / rigid-small-many32`.

Under `lane-f-plan-v1`, no additional timing rerun, outlier deletion or
partial-case rerun is allowed. F006 therefore does **not** produce a formal
general-dynamic PASS or FAIL.

## Artifacts

Validation:

`out/research/lane-f-dynamic-geometry-alternatives/006-geometry-class-crossover-controls/20260929T140642Z`

First timing campaign — unstable:

`out/research/lane-f-dynamic-geometry-alternatives/006-geometry-class-crossover-controls/20260929T140821Z`

One permitted identical full rerun — unstable:

`out/research/lane-f-dynamic-geometry-alternatives/006-geometry-class-crossover-controls/20260929T141104Z`

## Correctness and workload identity

All frozen geometry classes matched their required identities for all three
variants:

- Nrep = 796
- rigid-large-few groups = 1
- rigid-small-many32 groups = 32
- deforming primitives = 796
- topology replacements = 199 / 796
- grid overflow = 0
- storage failures = 0
- Vulkan validation errors = 0

## Timing repeatability

Second campaign instability:

| variant | geometry class | min GPU us | median GPU us | max GPU us | max/min |
| --- | --- | ---: | ---: | ---: | ---: |
| vanilla-software | rigid-small-many32 | 2998.938 | 3177.477 | 3990.061 | 1.3305 |

All four transient-LBVH classes and all four transient-grid classes were stable
in the second campaign, but the frozen methodology makes F006 a campaign-level
timing result and the matching control remained unstable after the allowed
rerun.

## Diagnostic medians only

These values are retained as mechanism evidence, not formal promotion evidence.

### transient-LBVH

| geometry class | complete GPU us | ratio vs extended vanilla | peak memory ratio |
| --- | ---: | ---: | ---: |
| rigid-large-few | 1455.285 | 0.4399x | 2.4279x |
| rigid-small-many32 | 1479.571 | 0.4656x | 2.4279x |
| deforming | 1458.251 | 0.4814x | 2.4279x |
| topology-replace25 | 1456.367 | 0.4289x | 2.4279x |

### transient-grid

| geometry class | complete GPU us | ratio vs extended vanilla | peak memory ratio |
| --- | ---: | ---: | ---: |
| rigid-large-few | 17949.184 | 5.4255x | 2.8231x |
| rigid-small-many32 | 17509.188 | 5.5104x | 2.8231x |
| deforming | 28000.682 | 9.2437x | 2.8231x |
| topology-replace25 | 19164.974 | 5.6446x | 2.8231x |

The LBVH mechanism remained close to ~1.46 ms complete GPU across all four
update classes. The grid remained rebuild/sort dominated, with deforming the
worst case.

The second campaign's diagnostic gate calculation marks every LBVH class below
the frozen 1.05x extended-vanilla limit and every grid class above it. Because
the campaign is still unstable, these values cannot grant or deny the formal
general-dynamic claim.

## Decision

- F006 correctness: **PASS**
- F006 timing repeatability: **INCONCLUSIVE**
- F006 formal generalization gate: **NOT EVALUATED**
- additional F006 timing reruns: **not allowed**
- transient-LBVH general-dynamic claim: **not formally established**
- transient-grid general-dynamic claim: **not formally established**
- next experiment: **F007 final integration replay and decision**

F007 remains the final rigid-primary decision campaign. F006 does not override
that decision and cannot rescue a failed representative moving-rigid result.
