# Lane B — geometry traversal

Issue: #11
Branch: `research/lane-b-traversal`

Mission: determine which traversal architecture best serves Split RC gather rays
under realistic dynamic-scene maintenance costs. StrataBrick is a candidate, not
a requirement.

Initial order:
1. define one semantic `traceRay(origin, direction, tMax)` contract/reference;
2. bring up a simple software baseline;
3. bring up StrataBrick/derived traversal using prior phos findings as hypotheses;
4. add hardware RT/TLAS where available and comparable;
5. measure build/refit/rebuild + trace + memory across static/dynamic regimes;
6. repeat the decision experiment on Lane A's real producer stream.

Prefer a regime-specific conclusion over forcing one universal winner.
