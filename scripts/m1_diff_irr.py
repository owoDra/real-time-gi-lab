#!/usr/bin/env python3
"""Compares two irradiance dumps (--dump-irr: float32 rgb + tag per pixel) of the same view: largest and mean
absolute difference and the share of pixels that differ. Used to check that the local voxel update gives the same
result as a full rebuild.
Usage: python scripts/m1_diff_irr.py a.static.irr.f32 b.static.irr.f32
"""
import array
import sys

a, b = (array.array("f") for _ in range(2))
with open(sys.argv[1], "rb") as f:
    a.frombytes(f.read())
with open(sys.argv[2], "rb") as f:
    b.frombytes(f.read())
assert len(a) == len(b)
n = len(a) // 4
mx = s = ref = 0.0
diff = 0
for p in range(n):
    if a[p * 4 + 3] != b[p * 4 + 3]:
        diff += 1
        continue
    d = sum(abs(a[p * 4 + c] - b[p * 4 + c]) for c in range(3))
    s += d
    ref += sum(abs(a[p * 4 + c]) for c in range(3))
    mx = max(mx, d)
    if d > 1e-6:
        diff += 1
print(f"pixels {n}, differing {diff} ({diff / n * 100:.4f}%), max |d| {mx:.6g}, sum |d| / sum |a| {s / max(ref, 1e-12):.3e}")
