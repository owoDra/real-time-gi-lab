# Lane M runtime adapters

Lane M reuses the qualified Lane J formal runtime as the common recurring
boundary. This directory contains only the topology-crossover-specific adapter,
workload identity contract, and clustered traversal ABI bridge.

The clustered backend's topology state machine and persistent layout remain
owned by Lane J. The adapter only maps those existing structures onto the
B002VulkanContext used by the common formal runtime so Lane E, Lane G, and Lane
J candidates share one allocation/timestamp/merge/storage boundary.
