# M001 H02 owner terminal receipt — stop at input review

Date: 2026-10-22 JST. Branch: `research-lane-m-gi-competitiveness`.

The owner reports that preregistered one-shot `capture_h02.py` returned:

```json
{
  "classification": "H02_RAW_STATE_CAPTURE_RETAINED_UNQUALIFIED",
  "returncode": 0,
  "payload_count": 13,
  "result": "out/research/lane-m-gi-competitiveness/m001-first-heldout-v1/result-h02.json",
  "next": "STOP: no H03, scoring, reference admission or timing claim"
}
```

**Result classification: `H02_OWNER_REPORTED_NATIVE_SUCCESS_INPUTS_NOT_INDEPENDENTLY_VERIFIED`.** The terminal report is consistent with the runner's success path but the locally held H02 payloads are not available to the assistant. The returned count does not prove byte-level identity, BF-P scene match, reference eligibility, numeric HDR correctness or owned-memory teardown. No H03 capture, PT budget sweep, DDGI scene integration, reference acquisition or GPU timing is authorized by this receipt.

The CPU-only [H02 verifier](../../../scripts/research/lane_m_gi_competitiveness/audit_h02_evidence.py) is committed. It refuses changed frozen H01 receipt hashes, N004 preregistration, H02 glTF/BIN identity, native scenario/backend/return code, captured N007 binary frame layout, mismatching *ordered* H02 1,224 triangles, and invalid Vulkan owned-allocation replay/teardown/8GiB bound. For partial private state input it records every omitted GPU payload hash as **UNVERIFIED** rather than accepting a full raw proof. The glTF decoding method was locally exercised against the earlier owner's H01 archive (1,224/1,224 exact triangle order and 74 valid allocation events); H02 raw attestation is **NOT RUN**.

For assistant-side CPU verification, provide one compact private tar, preserving the paths relative to the existing retained M001 work root:

```bash
tar -cf /tmp/m001-h02-state.tar \
  -C out/research/lane-m-gi-competitiveness/m001-first-heldout-v1 \
  result.json result-h02.json \
  assets/manifest.json assets/M001-H02.gltf assets/M001-H02.bin \
  capture/M001-H02-hwrt/geometry-state.bin \
  capture/M001-H02-hwrt/frame-state.bin \
  capture/M001-H02-hwrt/capture.json \
  capture/M001-H02-hwrt/allocation-ledger.json
```

Nine small files, no native HDR PFMs or 233GiB past corpus upload needed. Archive stays private to conversation; do not push raw `out/research` files to this public repo. H01 retained in the original user-uploaded archive and H02's source H01 receipt has a pinned SHA-256 `27e612439447bd1afd73f9346a679682c46eb0babe053883f17e9a53455a6cc0`.

**Next decision:** only after H02 CPU metadata/geometry/resource integrity passes may a separately frozen and guarded H03 *state-only* capture be considered. Before any quality-scored comparison, H01–H03 require exact transport states, full physical-scene hashes and independently eligible finite-depth HDR oracle references; statistical and support/convergence criteria must not be changed after observing candidate output. Retain H01 4/13 verified and 9/13 unverified GPU payload caveat, and all existing N010 correctness/timing failures. All existing run outputs must remain untouched.
