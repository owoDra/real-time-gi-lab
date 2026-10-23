# M001 corrected DDGI H01/B2: three valid quality losses, ladder exhausted

2026-10-23. [Unblinded continuation012](../experiments/012-ddgi-corrected-quality-continuation.md)
began only after the complete20control replay067/outcome068 were committed in
`2073959176e8be08128107fe06cbb736e9561d2b`. Three separately CPU-planned,
explicitly announced native processes acquired H01/B2/q0,q1,q2 in fixed order.
Each terminal capture passed independent runtime/copy/reference/physical/memory
checks before whole-image scoring. [Complete replay070](070-ddgi-corrected-h01-b2-quality-raw-replay.json)
rehashes/recomputes every acquisition, metric and full error map. All three are
valid **QUALITY_FAIL**, not operational or border-corruption failures.

|Rung / grid / rays|Total NRMSE %|Indirect NRMSE %|Indirect signed bias %|Outcome|
|---|---:|---:|---:|---|
|q0 / 8³ / 128|3.732623|19.132680|−13.495426|QUALITY_FAIL|
|q1 / 16³ / 256|5.836618|29.917344|−9.509769|QUALITY_FAIL|
|q2 / 24³ / 512|3.180520|16.302717|−3.906366|QUALITY_FAIL|

The unchanged inclusive gates are total NRMSE≤5%,indirect NRMSE≤10%,absolute
indirect signed bias≤5%, with no excluded pixels. q2passes total/bias but misses
the indirect gate. More budget is not monotonically better in these observations;
no cause, parameter tuning or additional rung is inferred. **H01/B2stops at
exhausted q2.** No q3, replacement seed, mask, relaxed threshold or retry.

All original16384spp reference four-seed bytes and8192/16384consecutive admission,
complete physical/camera state and provenance replay unchanged. Primary/direct
NRMSE3.170989533437041e−7 and whole-image maxabs5.664375897853919e−10 pass their
independent physical tolerances for every case. Source/shader/settings/seed are
the corrected011implementation frozen by012; no changes after observing scores.

The three native captures retain75payload hashes,2,045completed GPU units,
six full-copy atlas checks,14,155,776complete copied components and4,276,224border
components. Every pre/post copy is bit-exact, all interiors unchanged and initial
history exactly+0; no corrupt/undefined evidence can authorize escalation. Nine
complete f64 error maps, all support/leak/p99 diagnostics and every lower-rung
loss remain under repository/out. Full independent saved scores:

- `out/research/lane-m-gi-competitiveness/m001-ddgi-border-quality-scores-v1/h01-b2-q0/result.json`
- `out/research/lane-m-gi-competitiveness/m001-ddgi-border-quality-scores-v1/h01-b2-q1/result.json`
- `out/research/lane-m-gi-competitiveness/m001-ddgi-border-quality-scores-v1/h01-b2-q2/result.json`

Complete owned ledgers pass≤8GiB/zero teardown; peaks8,084,368/78,289,808/
431,872,912bytes. Persistent SDK image pairs, full ray coverage/layout/constants,
raw/PFM/composite identities and250msunit/180sprocess guards pass. Native timing
is diagnostic/uncalibrated, not an accepted end-to-end boundary. **No H01/B2
matched-quality speed branch exists for this corrected DDGI ladder.** Its
quality failure cannot become a performance or memory win.

This is one target of the original explicitly unblinded static cohort, using
the registered finite-stage fresh/reset implementation. It is not a general
DDGI-family negative. Five corrected targets remain unresolved; the fixed next
unit is **H01/B8/q0**, after its own CPU plan and independent terminal audit.
All 18 original 010 score/evidence records remain scientifically superseded and do not select the
new order; the corrected three results are separate records and do not replace
them. The20control runtime requalification stays intact.

Total new assistant-operated GPU acquisitions97:94through011+3corrected012quality
captures. Original human-operated evidence keeps attribution. No power/clock/
desktop changes, automatic queue, retry, overwrite, CI or default Renderer
integration. Existing source/old results unchanged. Prior CPU tests/builds not
rerun; recorded new GPU captures and CPU full replay actually executed. Default
Renderer build/runtime and validation layers NOT_RUN. Verification072 records
the applicable index/provenance checks. No accepted timing, architecture
promotion, general superiority or Lane M completion; broader dynamic/Sponza/
representative-device strata, temporal limits and historical direct/timing
issues remain open.
