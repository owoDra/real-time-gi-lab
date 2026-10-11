# N007 P0-005 — archived reference cohort: first 200/338 pairs

**Classification:** diagnostic-only, **partial archive sample**, no physical correctness or renderer quality verdict. The attached JSON was produced in the user's local workspace by the N007 v1 read-only archive scanner; it was parsed in the assistant's CPU sandbox. Original private PFM bytes are not available in the assistant sandbox.

## Source fingerprint

- Supplied parsed JSON SHA-256: `6b687338e22389bfcde0e8915f6afc23365385167f89d75e9081431725e79606` (189,080 bytes).
- `archive_root_not_exported=true`, `no_gpu_or_cpu_rendering=true`, `schema_version=1`.
- `total_discovered_pairs=338`, `inspected_pairs=200`, `failed_pairs=0`, `errors=[]`, `truncated=true`.
- `reference_all_black_pairs=69`; **all 69** also have positive candidate (GPU) luminance.
- Historical private archive: `../gi-lab-old-private`; neither source artifacts nor images were copied into GitHub.

## Deduplicated image facts

**Only 6 distinct (reference SHA, candidate SHA) combinations** were present in the first 200 pairs. Five distinct reference SHA values and six candidate SHA values. The **69 black observations correspond to only two unique image pairs**, not 69 independent failures. All those 69 black-reference images share the same SHA-256 `7595a554e8cce3af07b1aa6a89521c803c12e8f70f2ed725ed74bba20220ea47` (the same zero image as the authentic M3b CPU references). The GPU candidates for the two black-reference signatures have **8,242** and **9,247** positive pixels respectively.

| Representative relative file name | Duplicate count | Reference positive pixels | GPU positive pixels | RMS(GPU,reference) |
| --- | ---: | ---: | ---: | ---: |
| reference-000 / output-000 | 35 | 160 | 6,603 | 1.613140227722273e-05 |
| reference-001 / output-001 | 35 | **0** | 8,242 | 1.789222438521992e-05 |
| reference-002 / output-002 | 35 | 9,546 | 10,039 | 4.790857187949352e-06 |
| reference-003 / output-003 | 34 | **0** | 9,247 | 1.6159391012142084e-05 |
| reference-004 / output-004 | 31 | 161 | 6,605 | 3.019924015741972e-05 |
| reference-005 / output-005 | 30 | 169 | 6,577 | 1.7417424990100606e-05 |

Notice the positive GPU signal is not systematically absent when the CPU reference is black; conversely, `reference-002` is a high-signal positive-reference counterexample. The observations show that black references occur in some frozen frame states but not every state. They **do not establish whether candidate energy is physically real, physically biased, or light leakage.**

### Archive-folder coverage problem

The initial scanner had a default `max_pairs=200` and sorted paths lexically, so the **first 200** covered only:

| Archived cohort | Pairs | Fully black refs | Unique SHA pairs within cohort |
| --- | ---: | ---: | ---: |
| `001-renderer-reference-bringup` | 8 | 4 | 4 |
| `002-current-architecture-baseline` | 6 | 2 | 6 |
| `002-current-architecture-baseline-core` | 5 | 2 | 5 |
| `003-n003-preflight-calibration` | 181 | 61 | 6 |
| **Total** | **200** | **69** | **6 across cohorts** |

**No N004 or N006 pair** was included in this broad v1 scan, despite the separate real-M3b audit of one N006 capture in N007 P0-004. Therefore this result is **not** a comprehensive N001/N004/N006 survey. 138 matched pairs remain uninspected by this invocation; those may contain different references and scenario behavior.

## Remediation and next evidence

N007 survey v2 (research branch) removes the default cap (`--max-pairs 0`), includes `cohort_summary`, `signature_groups`, `unique_pair_signatures` and `unique_black_reference_signatures`, and retains explicit opt-in partial truncation. **7/7 unit tests PASS in the assistant CPU sandbox**; on-GitHub script + test Git blob hashes matched the local tested bytes. This is a **tool correction**, not a change to the original N001–N006 histories.

Run v2 from the new repo:

```bash
git pull --ff-only origin research-n007-reference-validity
python3 scripts/research/n007_reference_validity/survey_archive.py --archive ../gi-lab-old-private
```

Once complete, compare **unique signatures** and cohort summaries across **all 338 pairs**, especially N004 and N006 (and any failures). Until then do not call the 69/200 fraction a rate of failure of independent GI experiments. Do not initiate a GPU rerun nor reopen N006 acceptance based on this partial survey.
