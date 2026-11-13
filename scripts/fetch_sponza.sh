#!/usr/bin/env bash
# Fetch the Khronos glTF Sponza (PNG/JPG textures) into assets/ (not tracked by git).
# The Vulkan-Samples-Assets Sponza used before 2026-11-13 ships ASTC textures,
# which the development GPU (RADV) and desktop WebGPU cannot sample.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="$ROOT/assets/glTF-Sample-Assets"

if [[ -d "$DST/.git" ]]; then
  echo "glTF-Sample-Assets already exists: $DST"
  exit 0
fi

mkdir -p "$ROOT/assets"
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/KhronosGroup/glTF-Sample-Assets.git "$DST"

git -C "$DST" sparse-checkout set Models/Sponza/glTF

echo "Fetched Sponza to: $DST/Models/Sponza/glTF"
echo "Asset licensing: see $DST/Models/Sponza/LICENSE.md (if present) and the repository README."
