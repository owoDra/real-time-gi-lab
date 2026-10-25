# 037: first HLSL compile stops before GPU

**STOP_UNDECLARED_SDK_PI_NO_RETRY.** After registration2d427d0b and implementation
c9c50cab, the new native host compiles/links and the observed physical producer
compiles/validates/disassembles. SDK Make dependency emission succeeds; its actual
HLSL compile returns5 because RTXDI_PI is undeclared. The adapter omitted
Rtxdi/Utils/Math.hlsli, which declares this constant. This is an adapter compile
failure, not a physical, SDK-family, quality or GPU result.

[Full failure226](226-restir-gi-physical-gpu-preparation-failure.json) preserves
seven actual child command/limits/PID/terminal receipts, six successful steps,
the failed compile stderr,54 original raw payloads and874 consumed input hashes.
All seven processes have CPU120/wall180/4GiB/default unblocked SIGXCPU and reaped
terminal receipts, with no timeout. The original preparation remains incomplete
and invalid. The actual new host dependency file is independently inventoried;
its original preparation result has an empty dependency map because failure
preceded that final collection. This limitation is retained, not rewritten.

The new eight Python contracts, six native CPU input checks, GPU conditions and
full numeric audits are NOT_RUN. No path samples, GPU acquisition or reference
sampling; cumulative assistant GPU acquisitions remain186. No repeat of037,
code/threshold rescue, HDR quality scoring, timing/novelty/architecture admission
or default Renderer build/runtime validation. [Verification228](228-restir-gi-physical-gpu-failure-verification.json)
checks source/evidence preservation, all actual process envelopes, index/links
and unchanged active build graph. A separately registered correction may add the
missing official header, reuse successful native/GLSL bytes without recompiling,
and execute only previously unexecuted preparation and physical bridge work.
035 remains withdrawn;036 CPU extraction remains admitted. Full Lane M remains
active and incomplete. No N-history, CI/Actions, power/clock or desktop change.
