# N006 P1i — partial: HWRT 5/5 byte-exact, software static renderer exception

Issue #42. **P1i status INVALID-RETAINED / incomplete**, not a ten-case PASS. Evidence uploaded 2026-10-09: `n006-p1i-cross-backend-summary.json`, protocol `n006-p1i-cross-backend-correctness-v1`, clean HEAD `07f1bae87efc351a953880a415ddc25bdc819bb1`, GPU AMD Radeon 8060S (RADV STRIX_HALO), `reference_generated=false`.

## Observed fixed matrix results

| Case | Backend | Scenario | Owners | Original rays | Canonical rays | Actual ray reduction | PFM SHA |
|---:|---|---|---:|---:|---:|---:|---|
| 0 | HWRT | static | 4,167 | 133,344 | 24,064 | 81.9534% | byte-identical |
| 1 | HWRT | camera-motion | 4,231 | 135,392 | 25,760 | 80.9738% | byte-identical |
| 2 | HWRT | light-motion | 4,167 | 133,344 | 24,064 | 81.9534% | byte-identical |
| 3 | HWRT | moving-rigid | 4,213 | 134,816 | 24,832 | 81.5808% | byte-identical |
| 4 | HWRT | deforming-control | 4,172 | 133,504 | 24,232 | 81.8492% | byte-identical |
| 5 | software | static | unknown | — | — | — | **renderer exit 1; stderr not attached** |
| 6–9 | software | camera/light/moving-rigid/deforming | — | — | — | — | not run due prospective fail-fast |

For all five HWRT cases, `status=pass`, distinct per-scenario owner counts and GPU unique key counts validated, no GPU hash/weight/storage failure and each baseline/canonical PFM SHA bit-identical. Canonical scratch allocation reported as 8,421,464 B for each. These are **two sequential cold target frames** per case, so **no matched throughput claim** from complete-GI timings.

The user-supplied summary has `failures[0]={case_index:5,variant:"lane-e-final-software",scenario:"static",error:"renderer exit 1; see …/stderr.log"}`. It does **not include stderr text or a stack trace**. Therefore the precise exception, whether it happened at software runtime initialization, baseline source warmup, canonical dispatch, or storage/hit validation, is unknown. No evidence establishes a software correctness failure or successful software fallback. Preserve the P1i status `invalid-retained`, do not label backend parity PASS.

## Minimal diagnostic step — no GPU rerun

Inspect original retained `out/research/n006-interval-aware-allocation/p1i-cross-backend/20261009T080747Z/case-05-lane-e-final-software-static/stderr.log` (and `stdout.log` if stderr is uninformative). User can send the contents or upload the log; do not guess the exception from `renderer exit 1`. Once grounded, patch only the actual failure, write a regression test, then prospectively rerun a frozen, properly documented test preserving previous failures. Do not waive bit-exact PFM, hash/storage validation or silently skip software variants.

No N001/N004/N005 edits, no GitHub Actions.
