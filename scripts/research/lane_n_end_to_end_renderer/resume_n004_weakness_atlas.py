#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import n004_contract as contract
import run_n004_weakness_atlas as runner

EXPECTED_EVIDENCE_PROTOCOL = "n004-atlas-evidence-v3"


def _safe_case_file(case_root: Path, relative: str, label: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise contract.ContractError(f"N004 resume {label} escaped case root")
    resolved = case_root / path
    if not resolved.is_file():
        raise contract.ContractError(f"N004 resume missing {label}: {resolved}")
    return resolved


def _load_complete_case(
    case_root: Path,
    *,
    scenario: str,
    source_warmup: int,
    target_frames: int,
    topology: bool,
    one_bounce: bool,
    motion_fractions: list[float] | None,
    target_gpu: str,
) -> dict[str, Any] | None:
    evidence_path = case_root / "n004-evidence.json"
    if not evidence_path.is_file():
        return None
    try:
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise contract.ContractError(
            f"N004 resume unreadable evidence in {case_root}: {error}"
        ) from error

    if payload.get("schema_version") != 1:
        raise contract.ContractError(f"N004 resume schema mismatch: {case_root}")
    if payload.get("protocol_version") != EXPECTED_EVIDENCE_PROTOCOL:
        raise contract.ContractError(f"N004 resume evidence protocol mismatch: {case_root}")
    if payload.get("scenario") != scenario:
        raise contract.ContractError(f"N004 resume scenario mismatch: {case_root}")
    if int(payload.get("source_warmup_frames", -1)) != source_warmup:
        raise contract.ContractError(f"N004 resume source warm-up mismatch: {case_root}")
    if bool(payload.get("topology")) != topology:
        raise contract.ContractError(f"N004 resume topology mismatch: {case_root}")
    device = payload.get("device")
    if not isinstance(device, dict) or device.get("name") != target_gpu:
        raise contract.ContractError(f"N004 resume target GPU mismatch: {case_root}")

    frames = payload.get("frames")
    if not isinstance(frames, list) or len(frames) != target_frames:
        return None

    if motion_fractions is not None:
        observed = [float(frame.get("motion_fraction", -1.0)) for frame in frames]
        expected = [float(value) for value in motion_fractions]
        if observed != expected:
            raise contract.ContractError(f"N004 resume motion path mismatch: {case_root}")

    for index, frame in enumerate(frames):
        if int(frame.get("index", -1)) != index:
            raise contract.ContractError(f"N004 resume frame index mismatch: {case_root}")
        image = frame.get("image")
        reference = frame.get("reference")
        if not isinstance(image, str) or not isinstance(reference, dict) or not isinstance(reference.get("path"), str):
            raise contract.ContractError(f"N004 resume incomplete frame metadata: {case_root}")
        _safe_case_file(case_root, image, "image")
        _safe_case_file(case_root, reference["path"], "reference")

    if one_bounce:
        reference_one = payload.get("reference_one_bounce")
        if not isinstance(reference_one, dict) or not isinstance(reference_one.get("path"), str):
            raise contract.ContractError(f"N004 resume one-bounce reference missing: {case_root}")
        _safe_case_file(case_root, reference_one["path"], "one-bounce reference")

    return payload


def _retain_incomplete(campaign_root: Path, case_root: Path) -> Path | None:
    if not case_root.exists() or not any(case_root.iterdir()):
        return None
    cases_root = campaign_root / "cases"
    try:
        relative = case_root.relative_to(cases_root)
    except ValueError as error:
        raise contract.ContractError(
            f"N004 resume case escaped campaign cases root: {case_root}"
        ) from error
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = campaign_root / "retained-incomplete" / relative.parent / f"{relative.name}-{stamp}"
    suffix = 1
    while destination.exists():
        destination = campaign_root / "retained-incomplete" / relative.parent / f"{relative.name}-{stamp}-{suffix}"
        suffix += 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(case_root), str(destination))
    return destination


def _validate_campaign_root(root: Path, config: dict[str, Any]) -> None:
    if not root.is_dir():
        raise contract.ContractError(f"N004 resume artifact root does not exist: {root}")
    summary_path = root / "n004-summary.json"
    if summary_path.is_file():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise contract.ContractError(f"N004 resume unreadable summary: {error}") from error
        if summary.get("status") == "complete":
            raise contract.ContractError("N004 resume refused: campaign is already complete")

    scenes_path = root / "generated-scenes" / "n004-scenes.json"
    if not scenes_path.is_file():
        raise contract.ContractError("N004 resume generated scene manifest missing")
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    expected_generator = config.get("revision", {}).get("synthetic_scene_generator")
    if scenes.get("generator") != expected_generator:
        raise contract.ContractError(
            "N004 resume synthetic scene generator differs from frozen v2 contract"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resume an interrupted Lane N N004 campaign at whole-case boundaries"
    )
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=runner.DEFAULT_CONFIG)
    parser.add_argument("--binary", type=Path, default=runner.ROOT / "build/release/phos-n004-atlas")
    parser.add_argument(
        "--origin-commit",
        default="d7ff7ea7d25b1883f17148dbdadde1b83e6619e2",
        help="commit used by the interrupted campaign whose completed cases are reused",
    )
    args = parser.parse_args()

    root = args.artifact_dir.resolve()
    config = contract.load_config(args.config.resolve())
    _validate_campaign_root(root, config)

    current_commit = runner.git("rev-parse", "HEAD")
    origin_commit = args.origin_commit.strip()
    if len(origin_commit) != 40:
        raise contract.ContractError("N004 resume requires a full origin commit SHA")

    original_run_case = runner.run_case
    reused_cases: list[str] = []
    rerun_cases: list[str] = []
    retained_incomplete: list[str] = []

    def resume_run_case(
        binary: Path,
        case_root: Path,
        scene: Path,
        scenario: str,
        source_warmup: int,
        target_frames: int,
        *,
        topology: bool = False,
        one_bounce: bool = False,
        motion_fractions: list[float] | None = None,
    ) -> dict[str, Any]:
        complete = _load_complete_case(
            case_root,
            scenario=scenario,
            source_warmup=source_warmup,
            target_frames=target_frames,
            topology=topology,
            one_bounce=one_bounce,
            motion_fractions=motion_fractions,
            target_gpu=config["target_gpu"],
        )
        relative = str(case_root.relative_to(root))
        if complete is not None:
            reused_cases.append(relative)
            print(f"N004 resume: reusing complete case {relative}")
            return complete

        retained = _retain_incomplete(root, case_root)
        if retained is not None:
            retained_incomplete.append(str(retained.relative_to(root)))
            print(
                "N004 resume: retained incomplete case "
                f"{relative} -> {retained.relative_to(root)}"
            )
        rerun_cases.append(relative)
        print(f"N004 resume: running case {relative}")
        return original_run_case(
            binary,
            case_root,
            scene,
            scenario,
            source_warmup,
            target_frames,
            topology=topology,
            one_bounce=one_bounce,
            motion_fractions=motion_fractions,
        )

    runner.run_case = resume_run_case
    try:
        return_code = runner.run_target(root, config, args.binary.resolve())
    finally:
        runner.run_case = original_run_case

    resume_info = {
        "schema_version": 1,
        "policy": "whole-case-checkpoint-resume",
        "sample_exclusion": "none",
        "partial_case_policy": "retain-partial-artifact-and-rerun-entire-case",
        "origin_commit": origin_commit,
        "resume_harness_commit": current_commit,
        "reused_complete_cases": reused_cases,
        "rerun_cases": rerun_cases,
        "retained_incomplete_cases": retained_incomplete,
    }
    (root / "n004-resume.json").write_text(
        json.dumps(resume_info, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    for filename in ("n004-summary.json", "n004-provenance.json"):
        path = root / filename
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["resume"] = resume_info
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        "N004 resume complete: "
        f"reused={len(reused_cases)} rerun={len(rerun_cases)} "
        f"retained_incomplete={len(retained_incomplete)}"
    )
    return return_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except contract.ContractError as error:
        print(f"N004 resume contract error: {error}")
        raise SystemExit(2)
