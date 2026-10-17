# N010 prospective array-RQMC transport diagnosis

Date: 2026-10-17 JST. Parent: `9f0cbd5`. Register before building/acquiring.
Prior fixed conditional-correction prototype 202 completes but fails its
promising rule; stop it. This is a distinct sampling construction, not tuning
that correction or restarting an old acquisition. Timing 201 also remains FAIL.

## Basis and fixed construction

Later contributions dominate observed C1 disagreement (191). Both perturbing
the sample map (180/195) and a coarse next-hit predictor (202) have failed to
establish a strong repair. Investigate preserving stratification through each
diffuse Markov transition, rather than one fourteen-dimensional path map.

Primary research: L'Ecuyer et al.,
[On Array-RQMC for Markov Chains: Mapping Alternatives and Convergence Rates](https://www.gerad.ca/en/papers/G-2009-03),
and [Sorting methods and convergence rates for Array-RQMC](https://www.gerad.ca/en/papers/G-2016-61).
These describe sorting parallel chains and assigning independently randomized
point sets at each step. They do not establish performance or implementation
validity for this repository's geometry. Author PDF URLs returned access-denied
pages in the browser; the institutional abstracts and indexed author-paper
algorithm excerpts were available. No full-paper-reading claim.

Prototype one array of exactly 8192 paths per pixel/replicate. Keep original
first continuation coordinates bit-for-bit. After shading each later vertex
j=1..6, sort all paths by normal octant, then an 18-bit-per-axis Morton code
of the spawned origin normalized to original scene bounds. Dead paths sort
last; sample index breaks ties. No radiance, GI image or quality score defines
the key. Assign a fresh three-dimensional digitally shifted Sobol point set,
sorted by its first coordinate, to the sorted paths. Remaining two coordinates
are the unchanged cosine sampler inputs. Shift words:
`uint32(mix(seed ^ mix(pixel) ^ mix(0x415252415900 + 3*j + dim)))`, dim=0..2.
The same original net file and four N007 seeds remain. Preserve every path,
including absorbing dead paths; no resampling, weights, rejection or clamping.

Each transition's randomization must be separate from earlier transitions;
under that randomized construction each assigned continuation is marginally
uniform, and the physical cosine integral is unchanged. Hash-based finite-seed
implementation, sorting and recorded outputs still require independent proof;
a mathematical argument is not reference admission.

Use the original Oracle sample body, with optional diagnostic stop/vertex
exports only. Replay each assigned path prefix to expose its current state,
then finish the path with assigned coordinates. This costs repeated tracing
and is explicitly diagnostic, not a claimed efficient oracle. Original hit,
normal, offsets/inset, direct, material, finite depth and accumulation remain
in that body. A separate unchanged-original mode must reproduce all retained
193 means/second moments exactly. First-indirect luma means must also match
193 bit-for-bit for every candidate record. No new shading implementation.

## One bounded diagnostic 203

Fresh `array-rqmc-transport-diagnosis-v1`, result
`203-array-rqmc-transport-diagnosis.json`. Exactly the eight fixed non-tail
pixels from 202, 8192 samples, original four seeds. One compile and one native
process, one CPU at nice 15, 4 GiB address space, 220 aggregate CPU / 300 elapsed
seconds per invocation. Record actual PID/start/limits, generated source,
binary, all data and immutable input hashes. Failure stops without retry.
No concurrent scientific worker, GPU work, default build change or new seeds.

Report original/array means/moments, all records, first-indirect coupling,
paired-replicate p99, replicate variance and descriptive per-path variance.
Promising triage requires exact controls, nonnegative finite means/moments,
p99 ratio <=0.75 and replicate-variance ratio <=0.75^2. This is only a
prospective small diagnostic, not whole-frame feasibility or eligibility.
Negative stops this fixed construction; positive needs independent physical,
all-state/prefix and full-frame two-level proofs before any corpus acquisition.

Sorting a growing whole array would violate existing prefix requirements.
This prototype does not claim a larger-level prefix. A future reference method
would need fixed 8192-path blocks with independent per-block randomizations
and exact accumulation-order/prefix proofs, registered before those samples.
No substitution of an inexact whole-array prefix is authorized.

All original 24 slots, four seeds, six levels/262144 cap, support/absolute/
relative/two-consecutive-level gates, quality, timing and memory requirements
remain. All prior failures remain; no N010 READY, Lane M superiority claim,
N011, CUDA, Actions or N001–N009 changes. Error-1.0 direct pixels remain
UNRESOLVED / 未解決 and included. Unit/runtime regression tests NOT RUN.
