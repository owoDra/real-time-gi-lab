# N006 P1l-B1a — near-first software-primary five-scene correctness preflight PASS

Issue #42. **Preflight correctness only; performance decision deliberately NOT MEASURED**. User-uploaded `n006-p1l-b1a-summary.json`, file SHA-256 `33f2c5e76c63b811c0154cfdc3d6bc7b05323eb27f5fe9c83158d007f5c3f6f9`. Protocol `n006-p1l-b1a-primary-near-first-v1`, `mode=preflight`, `status=complete`, `failures=[]`, `formal=false`, clean source HEAD `9fe4126aebab26cacf6f04b336ca1544befd2de4`, AMD Radeon 8060S RADV, Sponza SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. This test is defined prospectively by `../experiments/016-p1l-b1-primary-near-first-traversal.md`.

**Correctness:** Five supported software scenarios `static`, `camera-motion`, `light-motion`, `moving-rigid`, `deforming-control`: **5/5 fresh processes**, **10/10 measured HDR PFM images byte-identical to accepted Software hashes**, every original/candidate arm `01` correct, `primary_hits` **byte-identical between both arms on every measured target frame**, canonical rays/owners/hash/storage/timing fail-closed gates passed. Each process has 32 source + 8 target-state warmups (all warmup tails maintenance = 0); one CPU N004 full per-ray hit oracle was sampled on the candidate frame index 1 per process. No independently generated reference and no no-HWRT device proof.

## Preflight GPU timestamp changes — descriptive ONE AB pair per scenario

These are uninstrumented GPU timestamps, **candidate minus baseline**; negative means faster. Only **one adjacent 01 pair per scenario**, and fixed arm order makes warm-state/clock/order bias possible; neither this table nor its apparent scene win count constitutes the frozen matched GPU performance decision.

| Scenario | Primary visibility B1−baseline (µs) | Primary delta | Complete GI delta | Complete renderer delta |
| --- | ---: | ---: | ---: | ---: |
| static | −171.806 | **−13.85%** | −182.988 µs (−10.11%) | −197.295 µs (−10.25%) |
| camera-motion | −74.702 | **−5.09%** | −94.379 µs (−4.57%) | −100.711 µs (−4.84%) |
| light-motion | −534.496 | **−34.69%** | −612.844 µs (−28.28%) | −626.550 µs (−25.37%) |
| moving-rigid | **+385.212** | **+42.13% regression** | +372.588 µs (+24.31%) | +363.731 µs (+23.46%) |
| deforming-control | −181.425 | **−20.37%** | −242.340 µs (−16.50%) | −239.535 µs (−15.09%) |

The **moving-rigid single-pair regression is a serious warning**, especially given the B0 2.48M node-visit tail that initially motivated B1. It violates the *candidate adoption* renderer-regression tolerance **if reproduced**. Do not dismiss or remove that scene, tune the gate after seeing it, silently choose only four winning scenes or claim B1a is globally faster. Four apparent single-pair improvements and one regression **do not establish** a robust optimization, because no BA order reversal or independent repeated process medians exist yet.

The frozen next gate is same-process matched GPU A/B, **5 scenes × 3 fresh processes × 24 frames each** with `011001100110011001100110`, **360 measured frames / 180 adjacent pairs**, source and target warmups before each process, exact primary hit and HDR PFM bytes on all frames, one N004 CPU oracle on candidate index 1/process, and complete GPU stage accounting. Compare original primary, complete GI and complete renderer with negative control stages. Prospective acceptance requires **>=5% median primary-stage reduction in >=3/5 scenes**, >=24/36 faster pairs and >=2/3 negative process medians for each winning scene **AND** no scene >+3% median complete-renderer regression, with 100% correctness. No new result or speedup should be stated before this.

## Decision

**Preflight PASS; GO to previously frozen balanced matched experiment without code or rule changes.** The observed moving-rigid regression is not a reason to retroactively exclude it; specifically check whether the full 36 matched pairs in that scene remain slow. The future result may legitimately be REJECT/REFINE despite success on other scenes. The original N003/E003 shaders, N004/N005 and GitHub Actions remain unchanged.

Command on same target NixOS after fetching any docs-only commits:

```sh
git pull --ff-only
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1l_b1_near_first.py
```

The runner has **600-second subprocess timeout per process**, progress output, and checkpoints raw logs/PFM/evidence and the completed/invalid summary separately from preflight. Report `mode=matched`, `status=complete` and 15 accepted process runs, or the first failure; do not combine the preflight's five pairs with the 180 frozen matched pairs.
