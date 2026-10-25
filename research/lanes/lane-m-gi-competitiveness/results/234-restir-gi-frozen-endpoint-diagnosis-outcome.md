# 039: one short-segment float32 endpoint discrepancy, no re-admission

**FROZEN_ENDPOINT_DIAGNOSIS_EXECUTED_NO_ADMISSION.** One actual externally
supervised CPU1200/wall1800/4GiB worker diagnoses all230,400 frozen H01/B2pixels
across four038seeds. No GPU acquisition, path regeneration, original full-auditor
rerun, shader/native compilation, old-test rerun, HDR reference decode or quality
score. [Full diagnosis233](233-restir-gi-frozen-endpoint-diagnosis.json) binds four
complete NPZs, every failed pixel/component and actual process/PID/limits/terminal
receipts. All old038inputs and raw outputs are unchanged.

| Frozen seed index | Secondary hits | Direction-failed pixels | Recovery-failed pixels |
|---|---:|---:|---:|
|0|1338|0|0|
|1|1353|0|0|
|2|1349|1|0|
|3|1360|0|0|

There is exactly one failing pixel: seed2, index32498, x178/y101, all3direction
components. Its physical intersection t is0.00123737915419m and stored endpoint
distance0.00123781977458m. The saved barycentric endpoint differs from O+t*wi by
(4.31e-13,1.02e-11,-6.658420588e-7)m. Local z float32 spacing is2.384185791e-7m,
so the z discrepancy is about2.793 local representable steps on a1.24mm segment.
Maximum direction component error is0.0003023717702515, failing the original
componentwise rtol3e-4/atol3e-6 rule. No threshold is relaxed. The primary and
secondary primitive indices are301 and1194; geometric normals are perpendicular.
The reported primary-plane gap0 is a vertex-plane diagnostic, not a statement
that these perpendicular triangles are coplanar.

Source cosine0.292614936829 versus endpoint cosine0.292510784392 gives recovered
indirect error-5.339450604e-9 per channel(original1.500152484e-5). The unchanged
radiance-recovery tolerance passes, while the direction tolerance still fails.
These observations support amplification of float32 barycentric endpoint error
on a short segment; they do not prove a globally correct replacement endpoint,
PDF, spawn or coordinate representation. The exact failed packet/position/t/
normal/primitive/source/SDK values are retained. No fake MISS, source-PDF change,
new endpoint or hidden rejection is introduced as a rescue.

All four saved original/observed PT, primary and source arrays are bit-identical.
All targeted radiance-recovery predicates and saved unpacked/packed actual SDK
visibility/hemisphere flags pass. This is a newly targeted diagnosis, not a rerun
or completion of the full037audit: seed3 remains full-audit NOT_RUN and038 H01/B2
remains unadmitted. Other physical/packing/history/dynamic predicates are not
newly admitted by these targeted checks. Five later GPU conditions remain NOT_RUN.

Raw diagnostic receipts inherit an extra `study=038` metadata field from the
unchanged038 finish helper. Their explicit schema/actual command/source identify
039;233 records the authoritative diagnostic ID039 and this non-authoritative
inherited tag separately. Preserve original bytes; do not silently rewrite them.
[Verification235](235-restir-gi-frozen-endpoint-diagnosis-verification.json) checks
actual PID/CPU/wall/AS/default unblocked SIGXCPU/exit0/reaped receipts, complete
arrays/payloads, original source/result preservation and all current index/links.
No native/GPU/reference retry. Default Renderer build/runtime NOT_RERUN; validation
layers NOT_RUN. No accepted performance, physical resampling/HDR quality, novelty,
architecture or Lane M closure. GPU acquisitions remain187. A future precision/
coordinate correction needs prospective physical contracts and fresh qualified
CPU/GPU evidence;037/038 failures and original thresholds remain immutable.
