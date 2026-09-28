#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <program> [args...]" >&2
  exit 2
fi

is_nixos=false
if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  [[ "${ID:-}" == "nixos" ]] && is_nixos=true
fi

if [[ "$is_nixos" == "true" ]]; then
  loader_root=""

  # Prefer a loader already exposed by the running system.
  if [[ -e /run/current-system/sw/lib/libvulkan.so.1 ]]; then
    loader_root="/run/current-system/sw"
  elif command -v nix >/dev/null 2>&1; then
    # Modern Nix path. This only realizes vulkan-loader and is cached by Nix.
    loader_root="$(nix build --no-link --print-out-paths nixpkgs#vulkan-loader 2>/dev/null || true)"
  fi

  if [[ -z "$loader_root" ]] && command -v nix-build >/dev/null 2>&1; then
    # Fallback for systems without nix-command/flakes enabled.
    loader_root="$(nix-build '<nixpkgs>' -A vulkan-loader --no-out-link 2>/dev/null || true)"
  fi

  if [[ -z "$loader_root" || ! -e "$loader_root/lib/libvulkan.so.1" ]]; then
    cat >&2 <<'EOF'
phos-gi-lab: Vulkan loader could not be resolved on NixOS.

The GPU driver may be installed, but libvulkan.so.1 is not visible to this
development shell. Verify the host graphics setup with:

  nix shell nixpkgs#vulkan-tools -c vulkaninfo --summary

EOF
    exit 1
  fi

  # libvulkan.so.1 comes from vulkan-loader. Vendor ICD libraries live under
  # /run/opengl-driver on NixOS and must remain the host/system versions.
  export LD_LIBRARY_PATH="$loader_root/lib:/run/opengl-driver/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export XDG_DATA_DIRS="/run/opengl-driver/share${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
fi

exec "$@"
