# M001 H01 native-capture checkpoint — owner reported, not independently attested

2026-10-21 JST. The owner returned the one-shot M001 H01 command output:

```json
{
  "classification": "RAW_H01_GPU_CAPTURE_RETAINED_UNQUALIFIED",
  "returncode": 0,
  "work": "out/research/lane-m-gi-competitiveness/m001-first-heldout-v1",
  "receipt": "out/research/lane-m-gi-competitiveness/m001-first-heldout-v1/result.json",
  "payload_count": 13,
  "next": "STOP: no other H02/H03 capture, reference admission or speed claim"
}
```

**Classification: `OWNER_REPORTED_GPU_CAPTURE_SUCCESS_UNVERIFIED_INPUTS`.** Exact user-returned terminal JSON, not a copied/reverified local result.json, byte hash audit, physically qualified reference, or speed measurement. No inference about HDR quality or device-memory correctness. H02/H03 remain NOT RUN. The actual local `out/` directory is not accessible from the assistant sandbox. Do not push the raw capture to the public repository.

The pure CPU `scripts/research/lane_m_gi_competitiveness/audit_h01_evidence.py` implements a fail-closed binary+metadata identity check using the **existing** N007 frame layout and N010 Vulkan owned-allocation event replay. Its `--metadata-only` mode explicitly marks unprovided GPU payloads unverified; neither mode admits a reference or samples GPU timing.

Minimal optional owner-supplied private attachment to permit assistant-side CPU verification: an archive containing `result.json`, `assets/manifest.json`, `assets/M001-H01.gltf`, `assets/M001-H01.bin`, and `capture/M001-H01-hwrt/{geometry-state.bin,frame-state.bin,capture.json,allocation-ledger.json}`. All paths relative to `out/research/lane-m-gi-competitiveness/m001-first-heldout-v1`. The source 13 GPU payloads and original local work root must stay intact. No new GPU capture or CPU computation by the owner is scientifically necessary to produce the archive; the owner only provides files inaccessible in the assistant environment.

**Next:** independently inspect those exact bytes against the frozen preregistration. If they fail, stop/retain failures rather than rerun H01 or select a different scene. If they pass, register an immutable exact H01 source/frame-state scene hash and then independently qualify new B2/B8 physical references before any HDR scoring. Do not start PT, H02/H03, DDGI or speed calibration from the receipt alone.

Audit status: code written; actual H01 raw data unavailable, H01 audit NOT RUN. No legacy evidence, Renderer, Actions, host clocks/power or default build changes.
