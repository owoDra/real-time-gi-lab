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


def vulkan_values(output: str, key: str) -> list[str]:
    values = re.findall(
        rf"^\s*{re.escape(key)}\s*=\s*(.+?)\s*$",
        output,
        re.MULTILINE,
    )
    return list(dict.fromkeys(value.strip() for value in values))


def cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        text = cpuinfo.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^model name\s*:\s*(.+?)\s*$", text, re.MULTILINE)
        if match:
            return match.group(1)
    return platform.processor() or "unknown"


def emit_host_lines(payload: dict[str, object]) -> None:
    device_names = payload.get("device_names")
    if isinstance(device_names, list) and device_names:
        print("GPU: " + " | ".join(str(name) for name in device_names))
    print(f"CPU: {payload.get('cpu_model', 'unknown')}")


def main() -> int:
    host_cpu = cpu_model()
    vulkaninfo = shutil.which("vulkaninfo")
    if vulkaninfo is None:
        payload: dict[str, object] = {
            "status": "unavailable",
            "reason": "vulkaninfo-not-found",
            "device_names": [],
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
            "device_names": [],
            "cpu_model": host_cpu,
        }
        write_artifact(payload)
        emit_host_lines(payload)
        print(f"hwrt_probe=unavailable reason=vulkaninfo-exit-{proc.returncode}")
        return 0

    device_names = vulkan_values(proc.stdout, "deviceName")
    driver_names = vulkan_values(proc.stdout, "driverName")
    driver_infos = vulkan_values(proc.stdout, "driverInfo")
    api_versions = vulkan_values(proc.stdout, "apiVersion")
    missing = [
        extension
        for extension in REQUIRED_EXTENSIONS
        if extension not in proc.stdout
    ]

    if missing:
        status = "unsupported"
        reason = "missing-required-extensions"
    elif len(device_names) != 1:
        status = "ambiguous"
        reason = (
            "multiple-vulkan-devices"
            if len(device_names) > 1
            else "vulkan-device-not-identified"
        )
    else:
        status = "supported"
        reason = None

    payload = {
        "status": status,
        "reason": reason,
        "required_extensions": list(REQUIRED_EXTENSIONS),
        "missing_extensions": missing,
        "device_name": device_names[0] if len(device_names) == 1 else "unknown",
        "device_names": device_names,
        "driver_name": driver_names[0] if len(driver_names) == 1 else "unknown",
        "driver_names": driver_names,
        "driver_info": driver_infos[0] if len(driver_infos) == 1 else "unknown",
        "driver_infos": driver_infos,
        "api_version": api_versions[0] if len(api_versions) == 1 else "unknown",
        "api_versions": api_versions,
        "cpu_model": host_cpu,
        "note": (
            "Extension presence is only a bring-up gate. Feature enablement and "
            "shared Hit semantics still require validation in the Vulkan implementation. "
            "When vulkaninfo reports zero or multiple physical devices, extension text "
            "cannot be safely attributed to one target device here, so support remains "
            "ambiguous rather than being reported as supported."
        ),
    }
    write_artifact(payload)
    emit_host_lines(payload)

    if missing:
        print("hwrt_probe=unsupported missing=" + ",".join(missing))
    elif status == "ambiguous":
        print(f"hwrt_probe=ambiguous reason={reason}")
    else:
        print("hwrt_probe=supported extensions=" + ",".join(REQUIRED_EXTENSIONS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
