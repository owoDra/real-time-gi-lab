#!/usr/bin/env python3
"""N006 P1m1: frozen M0-derived calibration-only key selection.

No quality labels, reference images, direction tuning or GPU performance data.
Only call AFTER run_p1m0_consumer_coverage.audit_coverage accepted this frame.
"""
from __future__ import annotations

from typing import Any

STRATA = ("zero", "low_positive", "high_positive")


def select_calibration_keys(rows: list[dict[str, int]]) -> dict[str, Any]:
    if not isinstance(rows, list) or not rows:
        raise ValueError("P1m1 calibration selection requires nonempty M0 rows")
    buckets: list[list[dict[str, int]]] = [[] for _ in range(4)]
    previous = -1
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "token", "consumer_pixels", "producer_owner_outputs"
        }:
            raise ValueError("P1m1 unexpected M0 key-row schema")
        token, pixels, owners = (row["token"], row["consumer_pixels"],
                                row["producer_owner_outputs"])
        if (any(type(v) is not int for v in (token, pixels, owners)) or
            token <= previous or token == 0xffffffff or token <= 0 or
            pixels < 0 or owners <= 0):
            raise ValueError("P1m1 malformed/unsorted M0 key rows")
        previous = token
        cascade = (token - 1) >> 30
        if cascade >= 4:
            raise ValueError("P1m1 invalid encoded cascade")
        buckets[cascade].append(row)

    all_selected = []
    unavailable = []
    summaries = []
    for cascade, keys in enumerate(buckets):
        zero = [x for x in keys if x["consumer_pixels"] == 0]
        positive = [x for x in keys if x["consumer_pixels"] > 0]
        low = min(positive, key=lambda x: (x["consumer_pixels"], x["token"])) if positive else None
        high = min(positive, key=lambda x: (-x["consumer_pixels"], x["token"])) if positive else None
        if low is not None and high is not None and (
                low["consumer_pixels"] == high["consumer_pixels"]):
            low = None
            high = None
            unavailable.append({
                "cascade": cascade, "reason": "insufficient_positive_variation",
                "observed_positive_keys": len(positive),
            })
        selections: dict[str, dict[str, int] | None] = {
            "zero": zero[0] if zero else None,
            "low_positive": low,
            "high_positive": high,
        }
        for stratum, chosen in selections.items():
            if chosen is None:
                unavailable.append({
                    "cascade": cascade, "stratum": stratum,
                    "reason": "missing_stratum",
                })
                continue
            all_selected.append({
                "cascade": cascade,
                "stratum": stratum,
                "token": chosen["token"],
                "consumer_pixels": chosen["consumer_pixels"],
                "producer_owner_outputs": chosen["producer_owner_outputs"],
            })
        summaries.append({
            "cascade": cascade,
            "source_keys": len(keys),
            "zero_keys": len(zero),
            "positive_keys": len(positive),
            "selected_strata": {
                stratum: (
                    {"token": chosen["token"],
                     "consumer_pixels": chosen["consumer_pixels"],
                     "producer_owner_outputs": chosen["producer_owner_outputs"]}
                    if chosen is not None else None)
                for stratum, chosen in selections.items()
            },
        })
    status = ("ready_calibration_only" if len(all_selected) == 12 and
              not unavailable else "incomplete_strata_no_intervention")
    return {
        "protocol": "n006-p1m1-frozen-calibration-key-strata-v1",
        "status": status,
        "selection_basis": "M0 canonical key consumer count only",
        "not": ["quality gain", "reference label", "heldout evaluation",
                "P1 GO", "P2 scheduler"],
        "expected_selection_count": 12,
        "actual_selection_count": len(all_selected),
        "per_cascade": summaries,
        "selected": all_selected,
        "unavailable": unavailable,
    }
