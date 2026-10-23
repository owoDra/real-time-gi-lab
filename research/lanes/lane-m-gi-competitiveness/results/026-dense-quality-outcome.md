# M001 dense fixed estimator control — six quality losses

Three separately prepared/executed/audited native images, one per H01/H02/H03 scene, produce **QUALITY_FAIL on all six separately admitted B2/B8 reference targets**. No speed comparison or architecture promotion is eligible. [Evidence025](025-dense-fixed-control-replay.json) retains all three full independent native intakes,54 raw hash replays, six full-image scores and error-array hashes. [Prospective006](../experiments/006-fixed-controls-execution.md) and [CPU source replay024](024-dense-source-cpu-replay.json) precede acquisition.

| Target | Total NRMSE | Indirect NRMSE | Indirect signed bias |
| --- | ---: | ---: | ---: |
| H01 / T_B2 | 19.698% | 100.968% | -17.188% |
| H01 / T_B8 | 23.008% | 89.070% | -42.550% |
| H02 / T_B2 | 28.842% | 174.039% | -7.733% |
| H02 / T_B8 | 29.173% | 144.242% | -42.468% |
| H03 / T_B2 | 29.200% | 135.394% | +5.158% |
| H03 / T_B8 | 29.502% | 120.401% | -24.565% |

Every score retains all57,600pixels and unchanged total≤5%, indirect≤10%, absolute indirect bias≤5%. Original physical scene bytes, admitted references and component/error-array replay pass. Dense source preserves eight fixed directions/cascade, fixed-point reduction and unshadowed secondary Lambert lighting. Its indirect loop ignores spp/vertices; each single scene image is reused for two diagnostic reference targets. These rows are not six independent acquisitions or finite-depth PT-equivalent results. No duplicate B8 image was acquired.

Cache-free evaluation alone does not restore quality on these heldouts. This does not isolate a unique error cause or justify retuning the incumbent on observed heldouts. Both dense and retained sparse-incumbent losses remain visible beside the6PT passes in023. Vanilla/software and actual-scene DDGI remain unfinished; broader Lane M remains active.

All native ledgers have26events, peak2,370,160bytes(H01/H02) or2,379,312(H03), cap≤8GiB and zero teardown. CPU/driver-private memory excluded. Native timestamps remain diagnostic/uncalibrated; no selected-boundary calibration, full per-process driver provenance or equal-quality RC/PT ranking. Acquisitions are assistant-executed on the explicitly authorized workstation, no settings changes. Source a427ffde; isolated historical binary/shaders unchanged. Native files/tars/error arrays stay inout. No N001–N010 or active Renderer/CMake/source/shader edits; existing35scoped CPU tests PASS, no new default build/runtime regression test.
