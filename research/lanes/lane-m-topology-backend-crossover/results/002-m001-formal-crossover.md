# M001 — formal topology-backend crossover

Status: **accepted; Lane E incumbent retained for all frozen topology-changing/high-churn regimes**

Issue: #25

## Decision

M001 completes the previously unresolved same-boundary topology-backend
crossover.

Under the prospectively frozen Lane-L heavy-boundary protocol, neither hardened
transient LBVH nor the clustered two-level object-local BVH qualifies for
promotion over the Lane-E incumbent in any required topology-changing/high-churn
scenario on either the primary or software track.

The retained decisions are therefore:

- topology-changing-object-local / primary: **Lane E incumbent retained**;
- topology-changing-object-local / software: **Lane E incumbent retained**;
- high-churn-global / primary: **Lane E incumbent retained**;
- high-churn-global / software: **Lane E incumbent retained**;
- high-churn-local / primary: **Lane E incumbent retained**;
- high-churn-local / software: **Lane E incumbent retained**.

No candidate pair reached the dual-promotion trigger, so the conditional direct
LBVH-vs-clustered stage did not run.

## Frozen measurement contract

Measured source commit:

`b07b6bf5f5020b59742d17b85de240e35a2b39df`

Plan:

`lane-m-m001-v1`

Imported heavy-boundary capability:

- dual independent Vulkan contexts;
- GPU timestamp primary;
- complete CPU wall diagnostic/health/provenance only;
- 20% demonstrated minimum detectable effect;
- 4 warmup + 12 measured pairs per process;
- 8 fresh-process blocks;
- 16 complete recurring-boundary transitions per timed role sample;
- frozen AB/BA counterbalancing;
- 1 second settle before each fresh process;
- no sample exclusion;
- instability rerun budget = 0;
- completed-campaign rerun budget = 0.

Promotion required candidate/control <= 0.80 plus fresh-control-noise,
fresh-process, AB/BA, directional-pair, correctness and memory gates.
candidate/control >= 1.20 under the same direction/noise gates is a detected
>=20% regression. Anything else remains <20% difference /
measurement-limited.

## Target and retained campaign

Target:

- GPU: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- driver: RADV / Mesa 26.1.2;
- Vulkan timestamp period: 10.019 ns;
- scene: `Sponza01.gltf`;
- scene SHA-256:
  `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`.

Formal campaign:

- fresh timing processes: **192/192**;
- retained raw timing rows: **6,144**;
- conditional direct processes: **0**;
- all samples retained;
- wall duration: **15,299.57 s** (~4.25 h);
- return code: 0;
- device/driver/API/timestamp provenance consistent.

The formal artifact root was:

`out/research/lane-m-topology-backend-crossover/001-topology-backend-crossover/20261001T134649Z`

Target validation passed before timing with exact source/input identity and no
accepted source/input drift between validation and formal execution.

## Formal performance

All ratios are candidate/control on complete GPU time. Lower is better.

| Scenario | Track | LBVH ratio | LBVH classification | Clustered ratio | Clustered classification |
| --- | --- | ---: | --- | ---: | --- |
| topology-changing-object-local | primary | 1.218883x | detected >=20% regression | 3.323954x | detected >=20% regression |
| topology-changing-object-local | software | 1.272652x | detected >=20% regression | 2.690152x | detected >=20% regression |
| high-churn-global | primary | 2.358234x | detected >=20% regression | 8.109075x | detected >=20% regression |
| high-churn-global | software | 2.181794x | detected >=20% regression | 6.477188x | detected >=20% regression |
| high-churn-local | primary | 2.608696x | detected >=20% regression | 11.551081x | detected >=20% regression |
| high-churn-local | software | 1.889332x | detected >=20% regression | 8.255209x | detected >=20% regression |

Every required mutating candidate is slower than the run-local Lane-E incumbent
by a decision-valid >=20% margin under the frozen gates.

The result is especially strong for the high-churn classes. The clustered
candidate is several times slower than the incumbent; hardened LBVH is also
materially slower despite having already resolved its earlier deterministic
memory blocker.

## Stable/no-change guard

The no-change guard checks whether a candidate imposes a hidden regression when
no topology rebuild is required.

| Track | Candidate | Candidate/control | Classification |
| --- | --- | ---: | --- |
| primary | LBVH | 1.507931x | detected >=20% regression |
| primary | clustered | 3.609810x | detected >=20% regression |
| software | LBVH | 1.040619x | <20% difference / measurement-limited |
| software | clustered | 1.895644x | detected >=20% regression |

The stable LBVH setup-prime fix is outside the recurrent boundary. Stable timed
samples still report zero topology mutations and zero backend rebuilds.

## Memory

The frozen memory hard guard requires:

- persistent candidate/control max <= 1.25x;
- true-peak candidate/control max <= 1.25x;
- complete allocation-lifetime accounting.

All candidate memory gates pass in the formal campaign. Representative maxima
across required mutating scenarios are:

- LBVH persistent max: **0.997158x** primary / **0.983403x** software for the
  representative topology-changing class, and below 1.0x in the high-churn
  classes;
- clustered persistent max remains <= **1.079030x** across the required
  high-churn/global software case;
- true-peak ratios remain <= **1.023996x** across the required mutating cases.

Therefore candidate rejection is driven by complete-GPU performance, not by the
1.25x memory guard.

## Architecture interpretation

Lane M resolves the topology-changing/high-churn backend question for the frozen
target, workloads and complete recurring boundary:

- retain Lane E object-local rebuild/update semantics as the incumbent;
- do not promote hardened transient LBVH for the tested topology-changing or
  high-churn regimes;
- do not promote clustered two-level object-local BVH for the tested regimes;
- do not infer a universal cross-GPU ranking;
- do not reinterpret sub-20% differences as rankings.

Lane G and Lane J remain useful mechanism/structural evidence, but their
candidates do not replace Lane E in the decision-valid Lane-M crossover.

## Limits

This result is specific to:

- AMD Radeon 8060S / RADV Mesa 26.1.2;
- the frozen Sponza/A001/J002 workload identity;
- the three frozen topology-changing/high-churn regimes;
- the complete M001 recurring boundary;
- the Lane-L 20% heavy-boundary effect floor.

It does not establish:

- cross-GPU generality;
- a sub-20% ranking;
- behavior for materially different topology workloads or future backend
  implementations;
- final renderer/game integration performance.

## Final disposition

**Accept M001 and retain the Lane E incumbent.**

The program-level topology-changing/high-churn backend selection is no longer an
open blocker for the measured target and frozen regimes. Future work should only
reopen this axis with materially new workload evidence, a materially different
backend, or a different target requiring fresh calibration.
