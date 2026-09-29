# Lane G shaders

Issue #17 owns this directory.

G001 keeps an instrumented but algorithmically unchanged snapshot of the F007
integration and transient-LBVH shaders. The `baseline/` subtree contains the
exact Lane A/B shader dependencies used by the F007 runtime. Shader filenames
remain unchanged where the runtime ABI expects historical names; ownership is
nevertheless Lane G on this branch.

No shader optimization is permitted before G001 concludes.
