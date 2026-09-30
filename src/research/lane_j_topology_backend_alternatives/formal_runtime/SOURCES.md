# Formal comparator provenance

J004 primary control uses the accepted Lane E E005 object-local HWRT rebuild
source from commit `2911790d8fd1716615a59dc86034e4fea783c9ec`.

J004 software control uses the accepted B003-compatible quantized hierarchy
source snapshotted by Lane G final.

The hardened transient LBVH keeps the Lane G builder and traversal shaders
unchanged. A J004-only host adapter reserves the maximum primitive capacity
already frozen by J002, then updates only active geometry/count per transition.
This prevents recurrent pipeline/layout creation from being omitted from the
measurement boundary.

The formal driver checks the frozen source blob identities before timing and
aborts on drift. Historical E/G timing is never imported as decision evidence.
