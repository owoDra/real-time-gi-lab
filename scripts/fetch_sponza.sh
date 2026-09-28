#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST="$ROOT/assets/Vulkan-Samples-Assets"

if [[ -d "$DST/.git" ]]; then
  echo "Sponza asset repository already exists: $DST"
  exit 0
fi

mkdir -p "$ROOT/assets"
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/KhronosGroup/Vulkan-Samples-Assets.git "$DST"

git -C "$DST" sparse-checkout set scenes/sponza textures

echo "Fetched Sponza to: $DST/scenes/sponza"
echo "Asset licensing remains governed by KhronosGroup/Vulkan-Samples-Assets."
