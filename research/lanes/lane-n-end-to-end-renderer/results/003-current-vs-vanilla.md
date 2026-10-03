# N003 — current architecture vs vanilla Split RC

Status: **complete**

Issue: #38  
Parent: #26  
Accepted implementation/evidence commit: `52a8d2c7ab2653d40b73afa9f17690712536239e`

## Decision

The accepted A–M support architecture survives end-to-end integration against the historical Integration-13 vanilla global binary software-BVH Split RC baseline under the frozen same-boundary comparison.

Formal complete-GI and complete-renderer timing both favor the current architecture in every timing-eligible scenario. All eight outer blocks agree in direction for every formal timing claim. Moving-rigid remains measurement-limited by the prospectively frozen preflight contract and therefore receives no formal timing win/loss claim even though its descriptive ratio also favors current.

Image quality is numerically identical between current and vanilla for all six scenarios under the frozen primary metrics and converged 512-spp references. No scenario has a material quality direction.

The main cost of the current architecture is higher device-side lifetime memory. This is an explicit speed/device-memory trade-off, not a hidden win.

## Formal timing result

Ratio orientation is `vanilla / current`; values above 1 mean current is faster.

| Scenario | Complete GI median ratio | Complete renderer median ratio | Formal timing result |
| --- | ---: | ---: | --- |
| static | 2.960x | 3.023x | current faster |
| camera-motion | 2.779x | 2.756x | current faster |
| light-motion | 2.810x | 3.108x | current faster |
| moving-rigid | 1.788x | 1.787x | measurement-limited; descriptive only |
| stable-topology-deforming | 2.475x | 2.506x | current faster |
| topology-changing-high-churn | 2.304x | 2.354x | current faster |

All five timing-eligible scenarios had 100% same-direction outer blocks on both complete-GI and complete-renderer axes and exceeded their prospectively frozen material-change thresholds.

No aggregate winner score is reported.

## Quality/reference result

All six scenario references converged at 512 spp and had identical frozen scene state for current and vanilla.

For every scenario, current and vanilla produced exactly equal values for:

- RGB RMS error;
- p99 absolute luminance error;
- scale-aware affected-pixel fraction.

Therefore:

- material quality change: **false** in all six scenarios;
- material quality direction: **none** in all six scenarios.

This means the timing difference is not explained by a quality reduction in the current path under the tested renderer semantics.

## Device memory result

For static, camera-motion, light-motion, moving-rigid and stable-topology-deforming:

- current true lifetime peak: `363,297,488` bytes;
- vanilla true lifetime peak: `287,091,936` bytes;
- current overhead: approximately **+26.5%**.

For topology-changing/high-churn:

- current true lifetime peak: `363,424,016` bytes;
- vanilla true lifetime peak: `293,392,656` bytes;
- current overhead: approximately **+23.9%**.

Current also retains explicit AS scratch and higher persistent device memory. Vanilla's global software-BVH path uses less device lifetime memory in this implementation.

## Non-formal CPU / host-memory diagnostics

These values are explanation/health evidence only and are not formal performance axes.

Renderer-owned host mirror totals favor current:

- static/camera/light: current `44,046,560` B vs vanilla `66,071,660` B;
- moving-rigid: current `30,420,116` B vs vanilla `52,445,216` B;
- stable-topology-deforming: current `44,046,560` B vs vanilla `52,445,216` B;
- topology-changing/high-churn: current `44,046,560` B vs vanilla `66,071,660` B.

Dynamic-update CPU wall diagnostics strongly explain why the global software-BVH baseline is expensive under dynamic geometry:

- moving-rigid: current ~1.56 ms vs vanilla ~105.70 ms;
- stable-topology-deforming: current ~1.92 ms vs vanilla ~109.55 ms;
- topology-changing/high-churn: current ~3.80 ms vs vanilla ~108.14 ms.

The vanilla values are dominated by global software-BVH rebuild CPU work. These diagnostics cannot override the frozen GPU-primary decision; they only explain the same architectural behavior.

## Correctness / provenance

Accepted evidence satisfies:

- all 40 timing micro-pairs retained;
- eight outer blocks completed;
- zero post-hoc sample exclusion;
- clean `research-lane-n-end-to-end-renderer` evidence commit;
- AMD Radeon 8060S Graphics / RADV Mesa 26.1.2 target identity;
- GPU performance/power profile unchanged;
- identical current/vanilla producer workloads where required;
- zero storage failures and internal correctness pass;
- topology mutation schedule identity;
- converged reference and identical final scene state for quality;
- no aggregate timing or quality winner score.

## Interpretation

N003 answers the first Lane-N architecture question positively for this baseline: the component-level architecture choices do not collapse when the recurrent renderer boundary is counted. Their strongest effect is reducing traversal and dynamic global rebuild cost, while consuming more device-side memory.

This result does **not** establish superiority over other modern GI families. It only validates the accepted support architecture against the mandatory fair vanilla Split RC baseline.

The next experiment is N004 weakness atlas. It must now characterize thin-geometry/light leaking, disocclusion, changing illumination, dynamic classes, world-shape/scale stress, and explicit multi-bounce/glossy capability gaps without changing the current transport solution first.
