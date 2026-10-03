# N001 — renderer/reference bring-up

Status: **Complete**

Issue: #26  
Target artifact: `out/research/lane-n-end-to-end-renderer/001-renderer-reference-bringup/20261003T040015Z`

## Decision

N001 is complete as a renderer/reference bring-up. The target artifact passes the frozen correctness/provenance contract and the follow-up HDR signal sanity check.

This result makes **no architecture performance claim**. N002 is the first end-to-end baseline stage and must freeze/calibrate the Lane-N complete-frame interpretation boundary before any formal performance conclusion.

## Target evidence

- target GPU: AMD Radeon 8060S Graphics (RADV_STRIX_HALO);
- target validation summary: `status = pass`;
- deterministic playback digest: `c642a99b4b2b2a825b721c4bd0deecf6a7db73816c0c79022d27ff9344e71ec6`;
- scene bundle digest: `d1590b8a8c58ff81dcab86121d5d6d12ca1532b1f0f5b9d472b1dfcd5c7b3649`;
- all four frozen frame pairs were produced;
- traversal runtime, OOB/validation, storage-failure, and lifetime-accounting gates passed;
- reference convergence passed under the frozen two-seed SPP rule;
- complete-GI/complete-renderer timing-accounting and required memory categories passed validation.

## HDR signal sanity

A post-bring-up sanity check was added after the first target pass to prevent an all-black campaign from being accepted as useful image evidence. The correct campaign-level rule is used: an individual black reference frame is allowed, while the campaign as a whole must contain positive renderer and reference radiance.

Observed signal:

| Frame | Scenario | Renderer positive pixels | Reference positive pixels | Renderer max luminance | Reference max luminance |
| ---: | --- | ---: | ---: | ---: | ---: |
| 0 | static | 0.114635 | 0.002778 | 2.22206e-4 | 1.74709e-4 |
| 1 | camera-motion | 0.143090 | 0.000000 | 1.22072e-4 | 0 |
| 2 | light-motion | 0.174288 | 0.165729 | 1.52531e-3 | 1.52531e-3 |
| 3 | moving-rigid | 0.160538 | 0.000000 | 1.22072e-4 | 0 |

Campaign-level renderer signal: **present**.  
Campaign-level reference signal: **present**.  
Signal sanity status: **pass**.

The black reference frames for camera-motion and moving-rigid are retained as valid observations. They are not removed or converted into exclusions. Any renderer-only radiance in such frames remains useful future weakness evidence (for example, potential leaking), but N001 does not classify or explain that error yet.

## Next

Proceed to N002 / #27: current evidence-backed A–M architecture under the complete Lane-N end-to-end boundary. Preserve N001 workload/provenance contracts where applicable and add the missing stable-topology-deforming and topology-changing/high-churn scenario coverage before N003.
