# Lane H — topology-changing object-local rebuild crossover

Issue: #18  
Branch: `research-lane-h-topology-rebuild-crossover`

Final status: **measurement-limited**

Lane H asked whether hardened transient LBVH has class-scoped value as an
object-local rebuild backend for topology-changing/high-churn geometry. Lane E
remains the incumbent ownership/update architecture for static, rigid, and
stable-topology deforming geometry.

## Final disposition

- H001: **INCONCLUSIVE**. The frozen safe repeatability gate failed on valid
  static controls, and review also found that the v1 dynamic harness did not
  actually perform a repeated reversible geometry transition.
- H002: workload identity, boundary contract, correctness checks, and
  allocation-lifetime scaffolding are prepared and retained; no timing winner
  is claimed.
- H003: **not run** because H001 PASS was a hard prerequisite.
- H004: no retained H003 candidate existed to integrate; final outcome is
  **measurement-limited**.

See `results/001-safe-timing-methodology.md` and
`results/004-final-decision.md` for the decision record.

Existing Lane E/G source and evidence remain read-only inputs. Lane H owns its
experiment, script, source, shader, and result paths.
