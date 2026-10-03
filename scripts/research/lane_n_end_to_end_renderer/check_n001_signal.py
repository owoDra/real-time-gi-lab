#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import n001_contract as contract

LUMA = (0.2126, 0.7152, 0.0722)


def signal_stats(image: contract.PFMImage, floor: float) -> dict[str, float | int]:
    luminance: list[float] = []
    for pixel in range(image.width * image.height):
        base = pixel * 3
        value = (
            image.pixels[base + 0] * LUMA[0]
            + image.pixels[base + 1] * LUMA[1]
            + image.pixels[base + 2] * LUMA[2]
        )
        luminance.append(value)
    return {
        "pixel_count": len(luminance),
        "mean_luminance": sum(luminance) / len(luminance),
        "max_luminance": max(luminance),
        "positive_pixel_fraction": sum(v > 0.0 for v in luminance) / len(luminance),
        "above_relative_floor_fraction": sum(v >= floor for v in luminance) / len(luminance),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect N001 HDR signal without rejecting valid black individual frames")
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parents[3]
        / "research/lanes/lane-n-end-to-end-renderer/experiments/001-n001-config.json",
    )
    args = parser.parse_args()

    root = args.artifact.resolve()
    config = contract.load_config(args.config.resolve())
    provenance_path = root / "n001-provenance.json"
    if not provenance_path.is_file():
        raise contract.ContractError("N001 provenance is missing")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    frames = provenance.get("frames")
    if not isinstance(frames, list) or not frames:
        raise contract.ContractError("N001 provenance has no frames")

    floor = float(config["image_metrics"]["relative_luminance_floor"])
    frame_signal: list[dict[str, object]] = []
    renderer_has_signal = False
    reference_has_signal = False

    for frame in frames:
        index = frame.get("frame")
        output = contract.read_pfm(root / str(frame.get("output_hdr")))
        reference = contract.read_pfm(root / str(frame.get("reference_hdr")))
        output_stats = signal_stats(output, floor)
        reference_stats = signal_stats(reference, floor)
        renderer_has_signal |= output_stats["max_luminance"] > 0.0
        reference_has_signal |= reference_stats["max_luminance"] > 0.0
        frame_signal.append(
            {
                "frame": index,
                "output": output_stats,
                "reference": reference_stats,
            }
        )

    summary = {
        "schema_version": 1,
        "status": "pass" if renderer_has_signal and reference_has_signal else "fail",
        "renderer_campaign_has_positive_signal": renderer_has_signal,
        "reference_campaign_has_positive_signal": reference_has_signal,
        "note": "An individual black reference frame is valid; for example, a fully occluded state can expose renderer light leaking. The campaign as a whole must contain positive renderer and reference signal.",
        "frame_signal": frame_signal,
    }
    output_path = root / "n001-signal-summary.json"
    output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["status"] != "pass":
        raise contract.ContractError("N001 campaign does not contain positive renderer and reference HDR signal")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N001 signal error: {error}")
        raise SystemExit(2)
