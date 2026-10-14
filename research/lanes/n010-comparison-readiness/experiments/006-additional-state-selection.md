# N010 prospective additional state selection

Before new indirect reference images, freeze these additions to initial lock
004. N009 light-motion NOT_CONSTRUCTIBLE remains unchanged. N010 uses an
explicitly prospective local displacement search.

Sponza base light and camera remain N009 C1. Candidate target positions are
base light plus world-axis displacements. Search ordered fractions 0.01,
0.02, 0.04, 0.08 of the world vertex-bounds diagonal; within each fraction:
+X, -X, +Y, -Y, +Z, -Z. Require minimum triangle distance >=2 times the recorded
light interval scale. Direct-only gates: >=64 pixels, >=1% of the image, peak
linear luma >=1e-4. Choose the first passing candidate; record every attempt
and payload hash. No total/indirect image guides selection. This differs from
N009's 0.1 diagonal global candidate requirement and is not its retrospective fix.

Controlled non-Sponza corpus is the unchanged leak-medium glTF used for C7.
Construct static/source, camera-motion, light-motion, moving-rigid,
deforming-control and topology-churn target states using the same frozen
Renderer scenario/mutation rules as Sponza. Attest camera/light support and
changed geometry identities without selecting on indirect quality. Retain
regimes with quality failures. Topology churn uses N002/N003's 50% delete/insert
primitive identity mutation with fixed triangle count; verify HWRT incumbent
and vanilla software state parity. Repair nonconstructible transitions within
N010 before declaring the corpus complete. Preserve historical Lane M results.

Physical reference reuse for source/recovery frames requires byte identity of
the **complete derived N010 oracle scene** (all triangles/materials, camera,
resolution, light/falloff and finite vertex count), not a tolerance or pixel
subset. Record each raw frame/geometry hash separately. Frame counter and
probe configuration alone do not change physical transport. Exact derived
scene equality is the permitted equivalence for such bookkeeping differences;
BF-P sidedness is independently required. Distinct light/geometry/camera
states still require distinct qualified references. This changes no quality
or reference threshold and does not revise historical outcome records.
