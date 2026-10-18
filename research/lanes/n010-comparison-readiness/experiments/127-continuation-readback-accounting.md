# N010 continuation PT readback accounting before build401

2026-10-18 JST; parent60114b2e. Follow-up implementation detail of126,
committed before preparation405.400's source/payloads remain immutable.

400 downloads and validates all final continuation states but does not emit
the separate readback duration required by126.405 adds ONLY a host steady-
clock interval starting at diagnostic-readback phase and ending after all
image/state downloads, validation, state copies and PFM/state file writes.
Emit one `readback-timings.jsonl` row per frame, index/wall_us. Keep the shader
byte-identical to400 and prove a whole host inverse to400. No change to frame
GPU/CPU timing boundary, physical work, RNG/sum, samples, guards or numerical
criterion. Native total elapsed remains end-to-end; readback is not free.

Driver `prepare_continuation_readback.py` creates private
`continuation-pixel-pt-accounted-source-v1`, result405. Source-only, refuse
existing output, no compiler/GPU or queue. Build401 then compiles this exact
host and400's exact shader with126's original native limits and private
paths. Its driver must pin405 and400's source/inverse chain before use.
402/403/404 preserve126 unchanged, additionally require one finite positive
readback row for each captured frame. No tests/default build or runtime
acceptance from source preparation. N010 NOT_READY, references16/24;
N001–N009 unchanged, Sponza direct-relative1.0 pixels UNRESOLVED/未解決.
