from __future__ import annotations

import array
import math
import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

LUMA = (0.2126, 0.7152, 0.0722)
VISIBILITY_MAGIC = b"N005VIS1"
VISIBILITY_VERSION = 1
INVALID_OWNER = 0xFFFFFFFF
_HEADER = struct.Struct("<8sIIII")


@dataclass(frozen=True)
class VisibilityCapture:
    width: int
    height: int
    depth: Sequence[float]
    owner: Sequence[int]


def luminance(rgb: Sequence[float]) -> float:
    return sum(float(rgb[index]) * LUMA[index] for index in range(3))


def pixel_error_vectors(
    output_pixels: Sequence[float],
    reference_pixels: Sequence[float],
    *,
    relative_floor: float,
    affected_fraction: float,
) -> tuple[list[float], list[float], list[bool]]:
    if len(output_pixels) != len(reference_pixels) or len(output_pixels) % 3:
        raise ValueError("RGB payload sizes must match and be divisible by three")
    if relative_floor <= 0.0 or affected_fraction <= 0.0:
        raise ValueError("error floors/fractions must be positive")

    absolute: list[float] = []
    relative: list[float] = []
    affected: list[bool] = []
    for base in range(0, len(output_pixels), 3):
        out_y = luminance(output_pixels[base:base + 3])
        ref_y = luminance(reference_pixels[base:base + 3])
        delta = abs(out_y - ref_y)
        scale = max(abs(ref_y), relative_floor)
        absolute.append(delta)
        relative.append(delta / scale)
        affected.append(delta >= affected_fraction * scale)
    return absolute, relative, affected


def read_visibility_capture(path: Path) -> VisibilityCapture:
    payload = path.read_bytes()
    if len(payload) < _HEADER.size:
        raise ValueError(f"visibility capture header is truncated: {path}")
    magic, version, width, height, count = _HEADER.unpack_from(payload)
    if magic != VISIBILITY_MAGIC or version != VISIBILITY_VERSION:
        raise ValueError(f"visibility capture protocol mismatch: {path}")
    if count != width * height:
        raise ValueError(f"visibility capture dimensions/count mismatch: {path}")
    expected = _HEADER.size + count * 8
    if len(payload) != expected:
        raise ValueError(f"visibility capture payload size mismatch: {path}")

    depth_bytes = payload[_HEADER.size:_HEADER.size + count * 4]
    owner_bytes = payload[_HEADER.size + count * 4:]
    depth = array.array("f")
    depth.frombytes(depth_bytes)
    owner = array.array("I")
    owner.frombytes(owner_bytes)
    if depth.itemsize != 4 or owner.itemsize != 4:
        raise ValueError("N005 visibility capture requires 32-bit float/uint arrays")
    if sys.byteorder != "little":
        depth.byteswap()
        owner.byteswap()
    return VisibilityCapture(width, height, depth, owner)


def _visible(capture: VisibilityCapture, index: int) -> bool:
    return (
        capture.owner[index] != INVALID_OWNER
        and math.isfinite(float(capture.depth[index]))
        and float(capture.depth[index]) > 0.0
    )


def _relative_depth_delta(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), 1.0e-6)


def signal_maps(
    previous: VisibilityCapture,
    current: VisibilityCapture,
) -> dict[str, list[float]]:
    if (previous.width, previous.height) != (current.width, current.height):
        raise ValueError("visibility capture dimensions changed")
    count = current.width * current.height
    if not (
        len(previous.depth) == len(previous.owner) ==
        len(current.depth) == len(current.owner) == count
    ):
        raise ValueError("visibility capture vector length mismatch")

    newly_visible = [0.0] * count
    ownership_changed = [0.0] * count
    temporal_depth_change = [0.0] * count
    visibility_discontinuity = [0.0] * count
    depth_discontinuity = [0.0] * count

    previous_valid = [_visible(previous, index) for index in range(count)]
    current_valid = [_visible(current, index) for index in range(count)]

    for index in range(count):
        if current_valid[index] and not previous_valid[index]:
            newly_visible[index] = 1.0
        if current_valid[index] and previous_valid[index]:
            if current.owner[index] != previous.owner[index]:
                ownership_changed[index] = 1.0
            temporal_depth_change[index] = _relative_depth_delta(
                float(current.depth[index]),
                float(previous.depth[index]),
            )

    width = current.width
    height = current.height
    for y in range(height):
        for x in range(width):
            index = y * width + x
            neighbors: list[int] = []
            if x > 0:
                neighbors.append(index - 1)
            if x + 1 < width:
                neighbors.append(index + 1)
            if y > 0:
                neighbors.append(index - width)
            if y + 1 < height:
                neighbors.append(index + width)

            for neighbor in neighbors:
                if current_valid[index] and not current_valid[neighbor]:
                    visibility_discontinuity[index] = 1.0
                elif current_valid[index] and current_valid[neighbor]:
                    depth_discontinuity[index] = max(
                        depth_discontinuity[index],
                        _relative_depth_delta(
                            float(current.depth[index]),
                            float(current.depth[neighbor]),
                        ),
                    )

    return {
        "newly-visible": newly_visible,
        "ownership-changed": ownership_changed,
        "temporal-depth-change": temporal_depth_change,
        "visibility-discontinuity": visibility_discontinuity,
        "depth-discontinuity": depth_discontinuity,
    }


def pearson(values: Sequence[float], errors: Sequence[float]) -> float | None:
    if len(values) != len(errors):
        raise ValueError("correlation vectors must have equal length")
    if not values:
        return None
    mean_x = sum(values) / len(values)
    mean_y = sum(errors) / len(errors)
    dx = [value - mean_x for value in values]
    dy = [value - mean_y for value in errors]
    xx = sum(value * value for value in dx)
    yy = sum(value * value for value in dy)
    if xx <= 0.0 or yy <= 0.0:
        return None
    return sum(x * y for x, y in zip(dx, dy, strict=True)) / math.sqrt(xx * yy)


def _mass_capture(indices: Sequence[int], values: Sequence[float]) -> float:
    total = sum(values)
    if total <= 0.0:
        return 0.0
    return sum(values[index] for index in indices) / total


def localization_metrics(
    signal: Sequence[float],
    absolute_error: Sequence[float],
    relative_error: Sequence[float],
    affected: Sequence[bool],
    selection_fractions: Sequence[float],
) -> dict[str, Any]:
    count = len(signal)
    if not (
        count == len(absolute_error) == len(relative_error) == len(affected)
    ):
        raise ValueError("signal/error vectors must have equal length")
    if count == 0:
        raise ValueError("signal vector must not be empty")
    if any(not math.isfinite(value) or value < 0.0 for value in signal):
        raise ValueError("signal scores must be finite and non-negative")

    support = [index for index, value in enumerate(signal) if value > 0.0]
    affected_indices = [index for index, value in enumerate(affected) if value]
    affected_total = len(affected_indices)
    affected_on_support = sum(1 for index in support if affected[index])

    mean_affected = (
        sum(signal[index] for index in affected_indices) / affected_total
        if affected_total else 0.0
    )
    unaffected = [index for index, value in enumerate(affected) if not value]
    mean_unaffected = (
        sum(signal[index] for index in unaffected) / len(unaffected)
        if unaffected else 0.0
    )

    ranking = sorted(range(count), key=lambda index: (-signal[index], index))
    selections: list[dict[str, float | int]] = []
    for fraction in selection_fractions:
        if not 0.0 < fraction <= 1.0:
            raise ValueError("selection fractions must be within (0,1]")
        selected_count = max(1, min(count, math.ceil(count * fraction)))
        selected = ranking[:selected_count]
        selected_affected = sum(1 for index in selected if affected[index])
        selections.append({
            "requested_fraction": float(fraction),
            "selected_pixels": selected_count,
            "selected_fraction": selected_count / count,
            "affected_recall": (
                selected_affected / affected_total if affected_total else 0.0
            ),
            "absolute_error_mass_capture": _mass_capture(selected, absolute_error),
            "relative_error_mass_capture": _mass_capture(selected, relative_error),
        })

    return {
        "pixel_count": count,
        "signal_nonzero_fraction": len(support) / count,
        "signal_mean": sum(signal) / count,
        "affected_pixel_fraction": affected_total / count,
        "support_affected_recall": (
            affected_on_support / affected_total if affected_total else 0.0
        ),
        "support_affected_precision": (
            affected_on_support / len(support) if support else 0.0
        ),
        "support_absolute_error_mass_capture": _mass_capture(
            support, absolute_error
        ),
        "support_relative_error_mass_capture": _mass_capture(
            support, relative_error
        ),
        "mean_score_affected": mean_affected,
        "mean_score_unaffected": mean_unaffected,
        "pearson_absolute_error": pearson(signal, absolute_error),
        "pearson_relative_error": pearson(signal, relative_error),
        "ranked_selection": selections,
    }
