#!/usr/bin/env python3
"""Deprecated H02-only N008 camera-source exporter (archived in Git history).

The original function derived camera target through float32 origin+forward,
unlike N010's pre-existing float64 precision correction. Original study hashes
remain in reports as diagnostics, NOT reference acquisition inputs. Never
generate a new physical radiance reference using this obsolete entry point.
Use prepare_m001_n010_physical_inputs.py and lock result 010 instead.
"""
raise SystemExit(
    "DEPRECATED N008 camera source: use "
    "scripts/research/lane_m_gi_competitiveness/prepare_m001_n010_physical_inputs.py"
)
