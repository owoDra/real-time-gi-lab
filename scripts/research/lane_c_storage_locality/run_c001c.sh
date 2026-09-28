#!/usr/bin/env bash
set -euo pipefail
build_dir="${PHOS_GI_BUILD_DIR:-build/release}"
program="$build_dir/src/research/lane_c_storage_locality/phos-c001-storage"
if [[ ! -x "$program" ]]; then
  echo "C001c executable not found: $program" >&2
  echo "Run: mise run build" >&2
  exit 2
fi
exec bash ./scripts/run_with_vulkan.sh "$program" "$@"
