#!/usr/bin/env bash
set -euo pipefail

resolve_node() {
  if [[ -n "${PHOS_AMDGPU_DPM_NODE:-}" ]]; then
    printf '%s\n' "$PHOS_AMDGPU_DPM_NODE"
    return
  fi

  mapfile -t nodes < <(
    for node in /sys/class/drm/card*/device/power_dpm_force_performance_level; do
      [[ -e "$node" ]] || continue
      vendor="$(dirname "$node")/vendor"
      [[ -r "$vendor" ]] || continue
      [[ "$(tr '[:upper:]' '[:lower:]' < "$vendor")" == "0x1002" ]] || continue
      readlink -f "$node"
    done | sort -u
  )

  if [[ ${#nodes[@]} -ne 1 ]]; then
    echo "expected exactly one AMDGPU DPM node, found ${#nodes[@]}" >&2
    printf '  %s\n' "${nodes[@]:-}" >&2
    echo "set PHOS_AMDGPU_DPM_NODE explicitly if this host has multiple AMD GPUs" >&2
    exit 2
  fi
  printf '%s\n' "${nodes[0]}"
}

node="$(resolve_node)"
action="${1:-status}"

case "$action" in
  status)
    echo "node=$node"
    echo "level=$(cat "$node")"
    ;;
  enable)
    printf '%s\n' profile_peak | sudo tee "$node" >/dev/null
    echo "node=$node"
    echo "level=$(cat "$node")"
    if [[ "$(cat "$node")" != "profile_peak" ]]; then
      echo "driver did not retain profile_peak" >&2
      exit 3
    fi
    ;;
  restore)
    printf '%s\n' auto | sudo tee "$node" >/dev/null
    echo "node=$node"
    echo "level=$(cat "$node")"
    ;;
  *)
    echo "usage: bash $0 [status|enable|restore]" >&2
    exit 2
    ;;
esac
