# N010 Amendment 2: prospective iid crosscheck precision

The original 002 validation completed with all independent physical controls
passing, but A7's RQMC/iid image difference was 1.011794883962283%, above the
fixed 1% limit. Result 003 remains a failed completed acquisition. This
amendment does not change its classification or relax any error threshold.

Before additional images, freeze a separate precision confirmation: unchanged
N008 iid binary, identical authored A7 and A6b scenes, the same four fixed
seeds, **16384 samples per seed for both controls**. Compare the new iid means
to the existing 8192-sample RQMC means. Keep mean difference <=0.2% per channel
and whole-image indirect NRMSE <=1%. Require both controls; no scene selection,
seed deletion, additional adaptive sample increase or threshold change.

Save the iid 8192 checkpoint for each seed and require byte equality with the
original acquisition's f64 and component PFM payloads. Record all new payload
hashes, exact binary/input hashes, commands and source commit. The unchanged
RQMC binary/table and passing physical controls are carried forward by result
003's hash. Qualification under this amendment requires all carried physical
controls, checkpoint equality and both new fixed precision gates. A failed
confirmation remains ineligible and requires investigation in N010.

The motivation is post-hoc: RQMC A7 agrees with independent quadrature to
0.0344588% region NRMSE, suggesting iid noise dominates the failed comparison.
That inference is separately diagnosed against quadrature; it is not a PASS.
This prospective sampling-budget change is explicitly an amendment beyond
002's original 8192-sample crosscheck, and must be disclosed in final readiness.
