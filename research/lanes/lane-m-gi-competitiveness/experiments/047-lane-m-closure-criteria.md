# 047 — Lane M closure criteria (registered before M002 results)

Registered while M002 references are still being qualified, before any M002
image, metric or timing exists. The user asked to complete Lane M, including a
fair quality, speed and memory comparison with existing GI. Closing a lane is
not the same as meeting the research charter; this file fixes, in advance, what
"Lane M complete" means and how the outcome is labelled.

## Lane M is COMPLETE when all hold

1. Every registered Lane M study (001-046 and addenda) is terminal: completed,
   stopped or superseded, with no running, pending or unpublished process.
2. A cross-family comparison matrix is published covering every tested family
   (raw PT, fixed RC roles, corrected DDGI, NRD RELAX, ReSTIR GI, PT+quadratic
   reconstruction, ReSTIR+reconstruction) on M001 and, where run, M002:
   quality decision per target, calibrated GPU-time decisions only where both
   sides meet the gates (or equal-cost rules where registered), owned memory,
   with every loss, stop and inconclusive result kept.
3. Each charter requirement is classified MET, NOT_MET or BLOCKED with
   evidence: novel architecture; same-quality speed/memory or same-cost quality
   superiority over fair families; new heldouts; dynamic camera/light/rigid/
   deforming/topology/churn; Sponza/broader scenes; multiple GPU classes and
   software fallback; deployability; true-peak memory accounting.
4. status.md, roadmap.md, the lane README, index.json and a decision record
   state the final verdict and hand every NOT_MET/BLOCKED requirement to an
   explicitly named follow-up lane proposal (not started).

## Verdict labels (chosen by the evidence, not by preference)

- `LANE_M_COMPLETE_CHARTER_MET` only if every charter requirement is MET.
- `LANE_M_COMPLETE_CHARTER_NOT_MET` otherwise, listing the MET subset
  (e.g. a bounded matched-quality speed result) and every NOT_MET/BLOCKED item.

No earlier result is reclassified; no gate is relaxed to reach a label. A
single available GPU makes "multiple GPU classes" BLOCKED unless other hardware
becomes available; that is recorded, not waived.
