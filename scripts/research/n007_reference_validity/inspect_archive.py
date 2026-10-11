#!/usr/bin/env python3
"""Read original N006 M3b PFMs from a private archive; never mutate it."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from inspect_hdr import inspect

EVIDENCE = "n006-candidate-evidence.json"
ORIGINAL_SUMMARY = "n006-p1m3b-moving-rigid-signed-quality-summary.json"
ORIGINAL_SUMMARY_SHA256 = "1c251467f61b9bac777ca860f689c2903c55214cd4bb8ff9e2997b92e6cc98d6"


def find_captures(archive: Path) -> list[Path]:
    archive = archive.resolve()
    if not archive.is_dir():
        raise ValueError(f"Archive directory not found: {archive}")
    if archive.name == "Q8_control_reference":
        return [archive] if (archive / EVIDENCE).is_file() else []
    return sorted(p for p in archive.rglob("Q8_control_reference")
                  if p.is_dir() and "p1m3b-moving-rigid-q8-signed" in p.parts
                  and (p / EVIDENCE).is_file())


def safe_file(capture: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing {label} path in original evidence")
    rel = Path(value)
    path = (capture / rel).resolve()
    if rel.is_absolute() or not path.is_relative_to(capture.resolve()):
        raise ValueError(f"Unsafe path for {label}: {value}")
    if not path.is_file():
        raise ValueError(f"Missing {label} PFM: {path}")
    return path


def inspect_capture(capture: Path) -> dict:
    capture = capture.resolve()
    evidence_path = capture / EVIDENCE
    original = evidence_path.read_bytes()
    evidence = json.loads(original)
    if (evidence.get("scenario") != "moving-rigid"
            or evidence.get("p1m3b_holdout_quality") is not True
            or evidence.get("p1m3_fractional_storage") is not True
            or evidence.get("reference_generation") != "rendered"
            or evidence.get("p1m1_canonical_token") != 0
            or len(evidence.get("frames", [])) != 1):
        raise ValueError("Not an original N006 M3b Q8 control capture")
    frame = evidence["frames"][0]
    a = safe_file(capture, (frame.get("reference") or {}).get("path"), "reference A")
    b = safe_file(capture, (frame.get("reference_independent") or {}).get("path"), "reference B")
    gpu = safe_file(capture, frame.get("image"), "Q8 GPU output")
    summary = capture.parent / ORIGINAL_SUMMARY
    summary_sha = hashlib.sha256(summary.read_bytes()).hexdigest() if summary.is_file() else None
    if summary_sha is not None and summary_sha != ORIGINAL_SUMMARY_SHA256:
        raise ValueError(f"Historical M3b summary differs from archived original: {summary}")
    diagnosis = inspect([a, b], gpu)
    if (diagnosis["reference_paths"][0]["width"], diagnosis["reference_paths"][0]["height"]) != (320, 180):
        raise ValueError("Original M3b capture must be 320x180")
    return {
        "schema_version": 1,
        "classification": "diagnostic-only; original M3b invalid-retained unchanged",
        "capture": str(capture),
        "evidence_sha256": hashlib.sha256(original).hexdigest(),
        "original_summary_sha256": summary_sha,
        "original_summary_verified": summary_sha == ORIGINAL_SUMMARY_SHA256,
        "diagnostic": diagnosis,
        "no_rendering_or_archive_modification": True,
        "physical_correctness_proven": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True,
                        help="Old repository root (e.g. ../gi-lab-old-private)")
    parser.add_argument("--capture", type=Path,
                        help="Specific Q8_control_reference folder if multiple are found")
    parser.add_argument("--output", type=Path, default=Path(
        "out/research/n007-reference-validity/p0-m3b-archive-diagnostic.json"))
    args = parser.parse_args()
    try:
        archive = args.archive.resolve()
        choices = find_captures(archive)
        if args.capture:
            chosen = args.capture.resolve()
            if not chosen.is_relative_to(archive) or chosen not in choices:
                raise ValueError(f"--capture must be a discovered M3b capture under {archive}")
        elif len(choices) == 1:
            chosen = choices[0]
        elif not choices:
            raise ValueError(f"No retained M3b Q8_control_reference capture found under {archive}. "
                             "Original PFMs might not have been retained.")
        else:
            raise ValueError("Multiple retained M3b captures found. Choose one with --capture:\n" +
                             "\n".join(f"  {p}" for p in choices))
        result = inspect_capture(chosen)
        output = args.output.resolve()
        if output.is_relative_to(archive):
            raise ValueError("Refusing to write diagnostic output into private archive")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({"output": str(output), "capture": str(chosen),
                          "reference_status": result["diagnostic"]["problems"],
                          "pairwise_rms": result["diagnostic"]["pairwise"][0]["whole_frame_rgb_rms"],
                          "reference_black": [v["completely_black"] for v in result["diagnostic"]["reference_paths"]]},
                         indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"N007 archived M3b diagnostics: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
