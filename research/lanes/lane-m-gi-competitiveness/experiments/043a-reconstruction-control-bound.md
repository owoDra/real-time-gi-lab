# 043a — Reconstruction control bound, before implementation

Prospective correction of 043 (`50186de8`) BEFORE any 043 code, test,
reconstruction or metric. 043 asked for "exact equality with the 022 final
image" when the reused CPU filter is applied to the archived 022 source. The
archived 022 stages are GPU float32 while the reused 018 filter evaluates in
float64, so bitwise equality is not a valid expectation. The control instead
uses 022's own registered stage bound: for every stage, unclipped and clipped
CPU outputs agree with the archived 022 GPU stage within rtol 2e-5 and
atol 2e-7 x max|previous stage input|, over all 57,600 pixels. Every other 043
input, operator, evaluation, gate, prediction and stop rule is unchanged.
