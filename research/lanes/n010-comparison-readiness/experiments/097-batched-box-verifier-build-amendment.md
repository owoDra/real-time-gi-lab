# N010 batched-box verifier build amendment

Date:2026-10-17 JST. Parent:6b4fa76. Before any candidate native acquisition.
096/244 compiler exits1: original V3 operator[] returns a value, so the verifier
cannot assign box.lo[a]/hi[a]. No native/query/cost measurement ran. Preserve
244 and sealed096/include bytes. Change ONLY verifier box reconstruction to
whole V3 assignment from the same xyz packet values; production algorithm and
standalone code are unchanged. Include/driver inverse checks remain mandatory.
All096 scenes/counts/seeds/order/interval/query/output/cost/resource/stop rules
remain exact. This is an explicit build amendment, not a scientific gate change
or native retry. A new failure still stops; no automatic full queue.

OneCPU nice15/4GiB,220CPU/300elapsed each child, no GPU/settings changes.
Tests NOT RUN. Physical11/17,refs16/24,N010 NOT_READY.
Work:out/research/n010-comparison-readiness/batched-box-verifier-repaired-v1
Result:results/245-batched-box-verifier-repaired-prototype.json
Driver:scripts/research/n010_reference_sampling/diagnose_batched_box_verifier_repaired.py
Include:scripts/research/n010_reference_sampling/batched_box_verifier_repaired.inc
