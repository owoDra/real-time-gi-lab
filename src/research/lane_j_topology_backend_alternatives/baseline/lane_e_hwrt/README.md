# Selective Lane-E HWRT comparator snapshot

Issue: #23

This directory contains only the B002 HWRT/Vulkan pieces needed to instantiate
the accepted Lane-E object-local **topology rebuild** comparator on the frozen
J002 geometry snapshots.

Source is pinned to the accepted E005 measurement commit:

`2911790d8fd1716615a59dc86034e4fea783c9ec`

Imported source blobs:

- `b002_vulkan.hpp`: `7df5275cb40ddabbceb3d8a09040fb4c63244e6a`
- `b002_vulkan.cpp`: `5cff8c2f7f1a739e9643fc303e15ce49d0504d3e`
- `b002_hwrt.hpp`: `a00fbfbfd5b9b2fd3c36cd2ceed49c14d2c9f71c`
- `b002_hwrt.cpp`: `91456326f9d946aedec46ff479f5d68600ed14a2`

J-local changes are deliberately limited to:

1. allocation-lifetime counters in `B002VulkanContext` so old/new rebuild
   overlap, staging and scratch contribute to true peak;
2. a local `median_us` helper so the unrelated B002 compute traversal
   implementation does not need to be imported;
3. a minimal GPU ABI header containing only the HWRT types used by
   `B002HwrtTraversal`.

No Lane-E timing result is imported. The comparator is rebuilt and measured
against J002 snapshots in the J004 same-run preflight.
