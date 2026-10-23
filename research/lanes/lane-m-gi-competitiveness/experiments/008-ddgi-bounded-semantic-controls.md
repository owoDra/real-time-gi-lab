# M001 DDGI bounded semantic controls

2026-10-23. Extension of007 after the standalone host builds and its native CPU input, symbolic finite-transport and exhaustive ray-ownership tests pass. Original001/002 scientific criteria, references and selected PT/fixed-RC evidence remain unchanged. This is a semantic qualification sequence, not a DDGI quality-budget ladder, timing experiment or architecture promotion.

## Frozen implementation and resources

Host/contract/private CPU builder are committed at `eeee5822`; build root `out/research/lane-m-gi-competitiveness/m001-ddgi-host-build-v1`, build result031. Native test evidence032 retains v1, v2 (two mocked-process fixture path errors) and current v3 after test harness fixes. The host binary is unchanged. Adapter entries are exact029 binaries, SDK pin and official SPIR-V are unchanged021/038/056/057. The private B002 context differs from its existing ledger-enabled source only by requiring/enabling storage-image read/write-without-format and extended formats; the builder proves inverse byte equality. No historical source/default build edits.

Two independent SDK volumes have identical packed descriptors, index0 in separate128-byte buffers, seed305419896, one SDK `Update()` each, fixed identical rotation throughout all finite stages. Grid side4, rays128,64probes,8192rays/stage in disjoint4096ray tiles (64threads/workgroup). Origin is frozen geometry AABB midpoint; per-axis spacing is `(extent+2*extent/(side−1))/(side−1)` computed in double then float. It adds one nominal AABB cell at each side, without looking at radiance/errors. Gather320×180,8×8groups. Bias normal=view=.01×minimum grid spacing; gamma1, hysteresis0, distance exponent50, brightness/irradiance thresholds1e6, ray extent equals original frame far. Classification/relocation/variability off, all six destination images cleared before every stage. This prevents SDK old-target history from affecting a finite stage. The finite physical field and radiance8control are below the explicit1e6impulse threshold; no arbitrary-HDR-range claim is made.

Each atlas owns ray/irradiance/probe-data F32x4, distance F32x2, variability F32 and variability-average F32x2, including unused required SDK resources. Every image is 2D-array, storage/sampled/transfer source+destination; sampled filtering is linear, clamp-to-edge, no mip/anisotropy. SDK set bindings0constants,1..6storage images; independent adapter set0,1,7AS,8triangle,9frame,10pixels,11..13previous sampled irradiance/distance/data,14sampler. SDK push range is its official descriptor; adapter push16bytes. Frame128bytes and triangle64bytes match030. Trace sets read the other atlas; gather sets read the final atlas. Both volumes and every staging/current/previous allocation coexist and are ledger-accounted, together with original AS ownership. Driver-private/CPU memory remains excluded. New adapter allocations cap7GiB conservatively; independent entire-process ledger cap8GiB, zero teardown required.

Only the named controls below may execute, one explicit process/terminal CPU audit at a time. Mode/depth/CLI, native binary, both adapter SPIR-Vs, official SDK SPIR-Vs, CPU receipts, original complete H01 state/reference provenance, wrapper and committed runner/auditor/protocol are hashed into each plan. No automatic loop or retry. Outputs stay in `out/research/lane-m-gi-competitiveness/m001-ddgi-controls-v1/<name>`, compact proof tars in repository/out. An existing partial/result/tar refuses another acquisition.

## Sequence and prospective pass criteria

All use the original H01 physical state and eligible16384spp reference. Direct/constant/finite-stage captures are explicitly diagnostic qualification images, never DDGI heldout quality-budget entries; no indirect HDR quality score is computed here and no future budget is chosen from their images/errors.

| Named control | Native mode/depth | Required independent CPU predicates |
| --- | --- | --- |
| direct | direct/B1;0probe stages | Original four-seed CPU oracle direct mean vs new GPU direct: whole-image max absolute≤1e−5 and NRMSE≤1e−4; indirect exactly0. |
| black | constant0/B2;1stage | Ray RGB0, distance1; all irradiance RGB0, distance moments.5within1e−5; output indirect exactly0; direct bytes unchanged. |
| unit | constant1/B2;1stage | Ray RGB1; blended irradiance RGB.5 and distance moments.5within1e−5; direct bytes unchanged. |
| hdr | constant8/B2;1stage | Ray RGB8; blended irradiance RGB4 and distance moments.5within1e−5; indirect gather equals8×unit (rtol1e−5,atol2e−6) with nonzero unit signal. |
| scene-one | scene/B2;1stage | Actual scene probe ray production/blending/gather; complete finite arrays; all previous irradiance/distance/data bytes remain initial0; direct bytes unchanged. |
| scene-seven | scene/B8;7stages | First-stage four raw arrays byte-identical to scene-one. At every stage, previous three atlas arrays byte-identical to the preceding stage's current output (or0at stage0). CPU symbolic stage plan plus frozen shader read bindings proves finite composition without in-place feedback; this does not prove estimator accuracy. |

All controls additionally require exact state copies, pixel/PFM correspondence, alpha1, total=D+I, finite complete pixels and captured current ray/irradiance/distance/data plus previous irradiance/distance/data at every stage, identical packed rotation/grid descriptors, all expected begin/complete GPU journal units in order, and cap-compliant/zero-teardown memory. SDK blend's internal barrier covers layer0; the host adds a full compute memory barrier for all array layers. Each new dispatch waits at most250ms on its fence, records raw timestamps as diagnostic only, stops at measured250ms or180s host wall guard, and yields2ms between units. Initial inherited B002 AS construction uses its existing synchronous implementation; the external whole-process180s guard also covers that setup. Timeout/nonzero/partial is OPERATIONAL_FAILURE, never semantic PASS; kill process group, retain bytes/proof and stop. The uncompleted native fence path records live ledger/partial journal and exits without a false teardown claim.

Failure of a required predicate stops the sequence and blocks DDGI quality acquisition. Preserve failed bytes. A source repair requires a newly identified build/control registration; no silent overwrite, retry or threshold relaxation. Static initialization and separate finite stages do not establish temporal, dynamic/light/geometry transition, Sponza, other-device or performance support. Those remain unqualified; no calibrated speed result from these controls.

## Single-unit operation

CPU prepare first, then print/review its exact command and execute only that named unit. For the first control:

```bash
python scripts/research/lane_m_gi_competitiveness/ddgi_control_step.py prepare --name direct
python scripts/research/lane_m_gi_competitiveness/ddgi_control_step.py execute --name direct
python scripts/research/lane_m_gi_competitiveness/ddgi_control_step.py audit --name direct
```

Use the established NumPy environment for all three invocations. These are three separate actions, with the middle invocation launching exactly one GPU process. Each subsequent named control requires the immediately preceding independent semantic PASS; a terminal failure stops. Assistant GPU execution is already user-authorized without power/clock changes; do not change any power, clock or desktop setting. No CI/Actions.
