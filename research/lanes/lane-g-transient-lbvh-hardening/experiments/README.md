# Lane G experiments

Execution order is frozen by Issue #17:

1. G001 memory ownership and lifetime census;
2. G002 timing-repeatability diagnosis;
3. G003 memory candidates justified by G001 only;
4. G004 integration hardening;
5. G005 final same-boundary replay.

G001 must finish before G002 begins. Memory optimization is forbidden until
G001 explains the F007 sparse-memory failures.
