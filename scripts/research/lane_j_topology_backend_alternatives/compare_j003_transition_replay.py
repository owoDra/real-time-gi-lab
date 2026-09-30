#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

FIELDS = (
    "cluster_count",
    "dirty_cluster_count",
    "rebuilt_triangle_count",
    "split_count",
    "merge_count",
    "retired_empty_cluster_count",
    "unaffected_cluster_rebuild_count",
    "occupancy_min",
    "occupancy_max",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare C++ J003 transition replay with canonical Python CPU gate"
    )
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--cpp", type=Path, required=True)
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()

    canonical = json.loads(args.canonical.read_text())
    cpp = json.loads(args.cpp.read_text())

    profiles = {
        profile["name"]: profile["rows"]
        for profile in canonical["profiles"]
    }
    if args.profile not in profiles:
        raise RuntimeError(f"profile not found in canonical gate: {args.profile}")

    expected = profiles[args.profile]
    actual = cpp["rows"]
    if len(expected) != len(actual):
        raise RuntimeError(
            f"row count mismatch: canonical={len(expected)} cpp={len(actual)}"
        )

    mismatches: list[str] = []
    for expected_row, actual_row in zip(expected, actual, strict=True):
        if expected_row["index"] != actual_row["index"]:
            mismatches.append(
                f"index mismatch canonical={expected_row['index']} "
                f"cpp={actual_row['index']}"
            )
            continue
        index = expected_row["index"]
        for field in FIELDS:
            if expected_row[field] != actual_row[field]:
                mismatches.append(
                    f"step {index} {field}: "
                    f"canonical={expected_row[field]} cpp={actual_row[field]}"
                )

    if mismatches:
        raise RuntimeError(
            "J003 C++ transition semantics diverged from canonical Python gate:\n"
            + "\n".join(mismatches)
        )

    print(
        f"J003 transition parity PASS: {args.profile} "
        f"({len(actual)} snapshots, {len(FIELDS)} fields/row)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
