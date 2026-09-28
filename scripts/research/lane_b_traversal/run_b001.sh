#!/usr/bin/env bash
set -euo pipefail

binary="${1:-build/release/phos-lane-b-b001}"
rays="${B001_RAYS:-65536}"
repeats="${B001_REPEATS:-5}"

python3 scripts/research/lane_b_traversal/probe_hwrt.py
exec "$binary" --rays "$rays" --repeats "$repeats"
