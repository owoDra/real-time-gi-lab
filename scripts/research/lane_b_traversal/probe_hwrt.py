#!/usr/bin/env python3
"""Probe target Vulkan HWRT/ray-query capability without treating support as a win."""
from __future__ import annotations

import json
import os
import platform
import re
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


def first_vulkan_value(output: str, key: str) -> str | None:
    match = re.search(
        rf"^\s*{re.escape(key)}\s*=\s*(.+?)\s*$",
        output,
        re.MULTILINE,
    )
    return match.group(1) if match else None


def cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        text = cpuinfo.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^model name\s*:\s*(.+?)\s*$", text, re.MULTILINE)
        if match:
            return match.group(1)
    return platform.processor() or "unknown"


def emit_host_lines(payload: dict[str, object]) -> None:
    device_name = payload.get("device_name")
    if isinstance(device_name, str) and device_name:
        print(f"GPU: {device_name}")
    print(f"CPU: {payload.get('cpu_model', 'unknown')}")


def main() -> int:
    host_cpu = cpu_model()
    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo is None:
        payload: dict[str, object] = {
            "status": "unavailable",
            "reason": "vulkaninfo-not-found",
            "cpu_model": host_cpu,
        }
        write_artifact(payload)
        emit_host_lines(payload)
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
            "cpu_model": host_cpu,
        }
        write_artifact(payload)
        emit_host_lines(payload)
        print(f"hwrt_probe=unavailable reason=vulkaninfo-exit-{proc.returncode}")
        return 0

    missing = [
        extension
        for extension in REQUIRED_EXTENSIONS
        if extension not in proc.stdout
    ]
    status = "supported" if not missing else "unsupported"
    payload = {
        "status": status,
        "required_extensions": list(REQUIRED_EXTENSIONS),
        "missing_extensions": missing,
        "device_name": first_vulkan_value(proc.stdout, "deviceName") or "unknown",
        "driver_name": first_vulkan_value(proc.stdout, "driverName") or "unknown",
        "driver_info": first_vulkan_value(proc.stdout, "driverInfo") or "unknown",
        "api_version": first_vulkan_value(proc.stdout, "apiVersion") or "unknown",
        "cpu_model": host_cpu,
        "note": (
            "Extension presence is only a bring-up gate. Feature enablement and "
            "shared Hit semantics still require validation in the Vulkan implementation."
        ),
    }
    write_artifact(payload)
    emit_host_lines(payload)

    if missing:
        print("hwrt_probe=unsupported missing=" + ",".join(missing))
    else:
        print("hwrt_probe=supported extensions=" + ",".join(REQUIRED_EXTENSIONS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
