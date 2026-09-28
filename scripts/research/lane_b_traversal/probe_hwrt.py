#!/usr/bin/env python3
"""Probe target Vulkan HWRT/ray-query capability without treating support as a win."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

REQUIRED_EXTENSIONS = (
    "VK_KHR_acceleration_structure",
    "VK_KHR_ray_query",
    "VK_KHR_deferred_host_operations",
)


def write_artifact(payload: dict[str, object]) -> None:
    artifact_dir = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if not artifact_dir:
        return
    path = Path(artifact_dir) / "hwrt-probe.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo is None:
        payload = {"status": "unavailable", "reason": "vulkaninfo-not-found"}
        write_artifact(payload)
        print("hwrt_probe=unavailable reason=vulkaninfo-not-found")
        return 0

    proc = subprocess.run(
        [vulkaninfo],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != 0:
        payload = {
            "status": "unavailable",
            "reason": f"vulkaninfo-exit-{proc.returncode}",
        }
        write_artifact(payload)
        print(f"hwrt_probe=unavailable reason=vulkaninfo-exit-{proc.returncode}")
        return 0

    missing = [extension for extension in REQUIRED_EXTENSIONS if extension not in proc.stdout]
    status = "supported" if not missing else "unsupported"
    payload = {
        "status": status,
        "required_extensions": list(REQUIRED_EXTENSIONS),
        "missing_extensions": missing,
        "note": (
            "Extension presence is only a bring-up gate. Feature enablement and "
            "shared Hit semantics still require validation in the Vulkan implementation."
        ),
    }
    write_artifact(payload)
    if missing:
        print("hwrt_probe=unsupported missing=" + ",".join(missing))
    else:
        print("hwrt_probe=supported extensions=" + ",".join(REQUIRED_EXTENSIONS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
