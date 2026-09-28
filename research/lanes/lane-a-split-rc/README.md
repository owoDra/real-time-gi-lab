# Lane A — Split RC producer and transport

Issue: #10
Branch: `research/lane-a-split-rc`

Mission: create the minimum representative Split Radiance Cascades producer and
transport pipeline needed to expose the real GPU query/update stream.

Initial order:
1. lock minimal diffuse Split RC semantics and a correctness reference;
2. generate probe/ray/cascade work on GPU from actual scene/visibility inputs;
3. record natural ordering/locality without sorting it;
4. add minimum gather, merge, and resolve for a meaningful workload;
5. version a replay/export schema Lane B/C can consume after an integration checkpoint;
6. measure producer and per-stage costs separately and end-to-end.

Do not select traversal or radiance-storage winners in this lane.
