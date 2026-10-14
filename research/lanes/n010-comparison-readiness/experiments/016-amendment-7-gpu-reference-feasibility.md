# N010 Amendment 7 — GPU execution feasibility for reference acquisition

Prospective diagnostic before any GPU-oracle dispatch. Existing CPU reference
acquisitions, Amendment 6, all acceptance thresholds and historical evidence
remain intact. This investigates execution cost; it does not accept a new
reference method by a successful shader build or a plausible speed estimate.

## Scope and numerical contract

Use the independent N008 oracle's scene parser, canonical binary64 geometry,
own SAH BVH/order and host-computed centre primary/direct terms. An exported
read-only snapshot may add accessors to the separately generated cached header;
it must not rewrite the original header or executable. Use no N001/Lane B
intersection or radiance implementation and no hardware float32 ray query.

The experimental compute shader uses binary64 software watertight intersection,
the same conservative slabs/traversal order/tie rule, offsets/edge inset,
opaque two-sided Lambert transport, N001-soft point-light falloff, finite
T_B2/T_B8, black background and identical sample-indexed shifted Sobol inputs.
Reject box camera sampling and emissive/area-light scenes. Those unsupported
oracle capabilities are not claimed validated by this adapter. Retain seeds,
moments, counters, all component images and failure flags. Require actual AMD
Float64/Int64 support; no CUDA or software-device fallback. All resources are
app owned and ledgered. Keep the target and SPIR-V outside the frozen build.

GLSL double trigonometry is unavailable in the standard function family and
double-operation precision is not a CPU-libm identity guarantee. A documented
binary64 range-reduced polynomial may implement sin/cos, with `precise`
arithmetic and explicit scalar expression ordering. This is a numerical port,
not Amendment 6's proved byte-identical CPU continuation. Source:
[Khronos GLSL 4.60 specification, sections 4.7 and 8.1](https://registry.khronos.org/OpenGL/specs/gl/GLSLangSpec.4.60.html).

## Diagnostic and eligibility conditions

First build and dispatch small explicit sample intervals; retain every attempt
without replacing failed artifacts. Compare the frozen four seeds on C1 T_B2,
C7 T_B2 and C7 T_B8 against complete original 8192-SPP CPU outputs. Also compare
C1 T_B8 against its original 8192 outputs before any deep-transport use. Require
all components/moments finite, zero scoring exclusions, identical primary
records/direct/emission mean terms, exact integer counters, mean/moment max
absolute discrepancy ≤1e-10 and indirect NRMSE ≤1e-8. Thresholds are fixed
before this adapter's first output. Any failure leaves it ineligible.

Even full numerical conformance is insufficient alone. Require applicable
physical controls (lit/blocked point light, back faces, sealed no-leak and
positive indirect support), all-24-state low-sample CPU/GPU conformance, and
deterministic nested-prefix continuation validation before reference use.
The same 8192→262144/four-seed/support-aware/two-consecutive screen remains
mandatory for any eventual reference. Do not qualify black images from sparse
whole-frame noise or silently replace a pending CPU acquisition. Any scheduling
transition needs a separate executed provenance record at a completed boundary.

GPU acquisition elapsed/timestamps are reference-generation diagnostics,
never an existing GI baseline or evidence of Renderer superiority. Runtime
measurement may coexist with CPU reference work and is marked loaded. A
non-performing or numerically inconclusive port is retained and rejected.
