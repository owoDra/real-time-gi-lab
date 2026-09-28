# Integration gate — dynamic end-to-end GI

Issue: #13
Branch: `research-integration-gate`

This directory owns the final research integration gate. It combines only
evidence-backed lane decisions and measures them as one dynamic GI pipeline.

## Frozen lane inputs

- Producer: accepted A001 schema v1 and natural GPU append order.
- Traversal primary: HWRT / TLAS from B002.
- Traversal software fallback: B003 segment DDA/hash + conservative quantized
  Micro BVH8. The older B002 binary-micro fallback is not the Integration
  fallback.
- Storage: C001 per-probe open-addressed sparse hash.
- Renderer reuse: D001 depth reuse only when an equivalent renderer depth
  already exists and its prerequisite cost is reported separately.
- Capacity policy: D005 bounded capacity + safe overflow is an optional
  Integration variant, not an accepted standalone producer.
- No post-generation global sort/reorder.

DDGI / sparse-radiance-cache searches found no representative implementation in
this repository at protocol-freeze time. Integration must not manufacture a
low-quality namesake baseline merely to win. A fair external baseline may be
added only before accepted timing if its complete semantics and cost boundary
can be matched; otherwise the final result records that comparison as
unavailable.

See `experiments/001-dynamic-end-to-end.md` for the fixed protocol.
