#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
N004_SCRIPTS = ROOT / "scripts/research/lane_n_end_to_end_renderer"
sys.path.insert(0, str(N004_SCRIPTS))
sys.path.insert(0, str(HERE))

import n001_contract as image_contract
import n004_contract
import n004_scene_factory
import run_n004_weakness_atlas as n004
import run_n005_p1 as p1
import n005_p2_contract as contract

DEFAULT_CONFIG = (
    ROOT
    / "research/lanes/n005-adaptive-tracing/experiments/"
      "002-p2-equal-budget-candidates-config.json"
)
N004_CONFIG = (
    ROOT
    / "research/lanes/lane-n-end-to-end-renderer/experiments/"
      "004-n004-weakness-atlas-v2-config.json"
)
CAMPAIGN_ROOT = ROOT / "out/research/n005-adaptive-tracing/002-p2-equal-budget-candidates"
VULKAN_WRAPPER = ROOT / "scripts/run_with_vulkan.sh"
CAPTURE_ENV = "PHOS_N005_VISIBILITY_CAPTURE_DIR"
EVIDENCE_PROTOCOL = "n005-p2-candidate-evidence-v1"


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise contract.ContractError(proc.stderr.strip())
    return proc.stdout.strip()


def require_clean_branch() -> str:
    branch = git("branch", "--show-current")
    if branch != contract.EXPECTED_BRANCH:
        raise contract.ContractError(
            f"N005 P2 requires {contract.EXPECTED_BRANCH}, got {branch!r}"
        )
    if git("status", "--porcelain"):
        raise contract.ContractError("N005 P2 requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    if len(commit) != 40:
        raise contract.ContractError("N005 P2 requires a full Git SHA")
    return commit


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if env_root:
        return Path(env_root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (CAMPAIGN_ROOT / stamp).resolve()


def safe_file(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise contract.ContractError("N005 evidence path escaped case root")
    full = root / path
    if not full.is_file():
        raise contract.ContractError(f"N005 evidence file missing: {full}")
    return full


def run_case(
    *,
    binary: Path,
    root: Path,
    scene: Path,
    scenario: str,
    mode: str,
    source_warmup: int,
    target_frames: int,
    owner_budgets: list[int],
    depth_threshold: float,
    extra_rays_per_probe: int,
    topology: bool = False,
    motion_fractions: list[float] | None = None,
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    command = [
        str(binary),
        "--artifact-dir", str(root),
        "--scene", str(scene),
        "--scenario", scenario,
        "--mode", mode,
        "--source-warmup-frames", str(source_warmup),
        "--target-frames", str(target_frames),
        "--owner-budgets", ",".join(str(value) for value in owner_budgets),
        "--depth-threshold", str(depth_threshold),
        "--extra-rays-per-probe", str(extra_rays_per_probe),
    ]
    if motion_fractions is not None:
        command += [
            "--motion-fractions",
            ",".join(str(value) for value in motion_fractions),
        ]
    if topology:
        command.append("--topology")
    if n004.common.is_nixos():
        command = ["bash", str(VULKAN_WRAPPER), *command]

    env = os.environ.copy()
    env.pop(CAPTURE_ENV, None)
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    (root / "stdout.log").write_text(proc.stdout, encoding="utf-8")
    (root / "stderr.log").write_text(proc.stderr, encoding="utf-8")
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise contract.ContractError(
            f"N005 P2 case failed: {root.parent.name}/{root.name}; artifact retained"
        )

    path = root / "n005-candidate-evidence.json"
    if not path.is_file():
        raise contract.ContractError(f"N005 P2 evidence missing: {root}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("protocol_version") != EVIDENCE_PROTOCOL:
        raise contract.ContractError("N005 P2 evidence protocol changed")
    if payload.get("mode") != mode:
        raise contract.ContractError("N005 P2 evidence mode mismatch")
    if len(payload.get("frames", [])) != target_frames:
        raise contract.ContractError("N005 P2 evidence frame count mismatch")
    if payload.get("depth_threshold") != depth_threshold:
        raise contract.ContractError("N005 P2 evidence threshold mismatch")
    if payload.get("extra_rays_per_probe") != extra_rays_per_probe:
        raise contract.ContractError("N005 P2 extra-ray multiplicity mismatch")
    return payload


def analyze_case(
    case_root: Path,
    evidence: dict[str, Any],
    n004_config: dict[str, Any],
) -> dict[str, Any]:
    frames: list[dict[str, Any]] = []
    images: list[image_contract.PFMImage] = []
    for frame in evidence["frames"]:
        image = image_contract.read_pfm(safe_file(case_root, frame["image"]))
        reference = image_contract.read_pfm(
            safe_file(case_root, frame["reference"]["path"])
        )
        metrics = n004.metrics(image, reference, n004_config)
        images.append(image)
        frames.append({
            "index": int(frame["index"]),
            "motion_fraction": float(frame["motion_fraction"]),
            "owner_budget": int(frame["owner_budget"]),
            "internal_correctness": bool(frame["internal_correctness"]),
            "metrics": metrics,
            "generic_classification": n004.generic_classification(
                metrics, n004_config
            ),
            "reference": frame["reference"],
            "timing_us": frame["timing_us"],
            "stats": frame["stats"],
            "memory_bytes": frame["memory_bytes"],
            "extra": frame["extra"],
            "hit_diagnostics": frame["hit_diagnostics"],
        })
    for index, frame in enumerate(frames):
        frame["temporal_rgb_rms_from_previous"] = (
            None
            if index == 0
            else n004.temporal_rgb_rms(images[index], images[index - 1])
        )
    return {
        "mode": evidence["mode"],
        "scenario": evidence["scenario"],
        "source": evidence["source"],
        "frames": frames,
    }


def validate_mode_case(
    case_name: str,
    mode: str,
    budgets: list[int],
    analyzed: dict[str, Any],
    config: dict[str, Any],
) -> None:
    if not bool(analyzed["source"]["internal_correctness"]):
        raise contract.ContractError(
            f"N005 P2 source correctness failed: {case_name}/{mode}"
        )
    if len(analyzed["frames"]) != len(budgets):
        raise contract.ContractError("N005 P2 analyzed schedule length mismatch")

    rays_per_active = int(
        config["candidate"]["requested_extra_rays_per_active_frame"]
    )
    owner_budget = int(config["candidate"]["owner_budget_per_active_frame"])
    for index, (budget, frame) in enumerate(zip(budgets, analyzed["frames"], strict=True)):
        label = f"{case_name}/{mode}/frame-{index}"
        if not bool(frame["internal_correctness"]):
            raise contract.ContractError(f"N005 P2 correctness failed: {label}")
        extra = frame["extra"]
        if not bool(extra["base_prefix_correct"]) or not bool(extra["extra_work_correct"]):
            raise contract.ContractError(f"N005 P2 work contract failed: {label}")
        if int(frame["stats"]["overflow"]) != 0 or int(frame["stats"]["storage_failures"]) != 0:
            raise contract.ContractError(f"N005 P2 overflow/storage failure: {label}")

        expected = 0 if mode == "current" or budget == 0 else rays_per_active
        if int(extra["extra_rays_traced"]) != expected:
            raise contract.ContractError(
                f"N005 P2 actual extra-ray mismatch: {label}; "
                f"expected {expected}, got {extra['extra_rays_traced']}"
            )
        if int(extra["extra_work_items"]) != expected:
            raise contract.ContractError(f"N005 P2 extra work mismatch: {label}")
        if expected == 0:
            if int(extra["selected_owner_count"]) != 0:
                raise contract.ContractError(f"N005 P2 inactive frame selected owners: {label}")
        else:
            if int(extra["selected_owner_count"]) != owner_budget:
                raise contract.ContractError(f"N005 P2 selected-owner mismatch: {label}")
            if int(extra["extra_rays_requested"]) != rays_per_active:
                raise contract.ContractError(f"N005 P2 requested-ray mismatch: {label}")
            if mode == "adaptive-extra-rays" and int(extra["eligible_owner_count"]) < owner_budget:
                raise contract.ContractError(f"N005 P2 adaptive eligibility shortfall: {label}")


def validate_equal_budget(
    case_name: str,
    uniform: dict[str, Any],
    adaptive: dict[str, Any],
) -> None:
    if len(uniform["frames"]) != len(adaptive["frames"]):
        raise contract.ContractError("N005 P2 uniform/adaptive frame mismatch")
    for index, (u, a) in enumerate(
        zip(uniform["frames"], adaptive["frames"], strict=True)
    ):
        u_rays = int(u["extra"]["extra_rays_traced"])
        a_rays = int(a["extra"]["extra_rays_traced"])
        if u_rays != a_rays:
            raise contract.ContractError(
                f"N005 P2 equal-budget gate failed: {case_name}/frame-{index}; "
                f"uniform={u_rays} adaptive={a_rays}"
            )


def run_p2(
    root: Path,
    config: dict[str, Any],
    n004_config: dict[str, Any],
    binary: Path,
) -> int:
    commit = require_clean_branch()
    if not binary.is_file():
        raise contract.ContractError(f"missing N005 P2 binary: {binary}")
    if root.exists() and any(root.iterdir()):
        raise contract.ContractError(f"N005 P2 artifact directory must be empty: {root}")

    sponza = (ROOT / n004_config["baseline"]["scene"]).resolve()
    if n004.common.sha256_file(sponza) != n004_config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N005 P2 Sponza digest mismatch")

    root.mkdir(parents=True, exist_ok=True)
    generated = root / "generated-scenes"
    manifest = n004_scene_factory.generate_all(generated)
    specs = p1.build_case_specs(n004_config, generated, manifest, sponza)

    cases: list[dict[str, Any]] = []
    for spec in specs:
        name = spec["name"]
        frozen_schedule = [int(v) for v in config["state_change_schedule"][name]]
        if len(frozen_schedule) != int(spec["target_frames"]):
            raise contract.ContractError(f"N005 P2 frozen schedule length drifted: {name}")

        modes: dict[str, Any] = {}
        for mode in config["required_modes"]:
            budgets = [0] * len(frozen_schedule) if mode == "current" else frozen_schedule
            mode_root = root / "cases" / name / mode
            evidence = run_case(
                binary=binary,
                root=mode_root,
                scene=spec["scene"],
                scenario=spec["scenario"],
                mode=mode,
                source_warmup=int(spec["source_warmup"]),
                target_frames=int(spec["target_frames"]),
                owner_budgets=budgets,
                depth_threshold=float(config["candidate"]["normalized_depth_threshold"]),
                extra_rays_per_probe=int(config["candidate"]["extra_rays_per_probe"]),
                topology=bool(spec.get("topology", False)),
                motion_fractions=spec.get("motion_fractions"),
            )
            if evidence["device"]["name"] != n004_config["target_gpu"]:
                raise contract.ContractError("N005 P2 target GPU mismatch")
            analyzed = analyze_case(mode_root, evidence, n004_config)
            validate_mode_case(name, mode, budgets, analyzed, config)
            modes[mode] = analyzed

        validate_equal_budget(
            name,
            modes["uniform-extra-rays"],
            modes["adaptive-extra-rays"],
        )
        cases.append({
            "name": name,
            "role": spec["role"],
            "owner_budget_schedule": frozen_schedule,
            "modes": modes,
        })

    summary = {
        "schema_version": 1,
        "protocol_version": config["protocol_version"],
        "status": "complete",
        "phase": "P2",
        "formal_target_measurement": False,
        "aggregate_score": None,
        "sample_exclusion": "none",
        "post_hoc_threshold_change": "none",
        "git_commit": commit,
        "target_gpu": n004_config["target_gpu"],
        "candidate": config["candidate"],
        "equal_budget_gate": "passed",
        "cases": cases,
    }
    (root / "n005-p2-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "n005-p2-provenance.json").write_text(
        json.dumps({
            "schema_version": 1,
            "protocol_version": config["protocol_version"],
            "git": {
                "branch": contract.EXPECTED_BRANCH,
                "commit": commit,
                "dirty": False,
            },
            "binary": str(binary.relative_to(ROOT)),
            "n004_config": str(N004_CONFIG.relative_to(ROOT)),
            "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
            "visibility_capture": "disabled-for-p2-timing",
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "n005-scenes.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"N005 P2 artifacts: {root}")
    print("N005 P2 equal-budget validation: COMPLETE")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="N005 P2 equal-budget candidate runner")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "p2"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())
    n004_config = n004_contract.load_config(N004_CONFIG.resolve())
    if n004_config.get("protocol_version") != "n004-weakness-atlas-v2":
        raise contract.ContractError("N005 P2 requires accepted N004 v2")

    if args.phase == "contract":
        print("N005 P2 prospective contract validation: PASS")
        return 0

    binary = (
        args.binary.resolve()
        if args.binary
        else (ROOT / "build/release/phos-n005-candidate").resolve()
    )
    return run_p2(
        artifact_dir(args.artifact_dir),
        config,
        n004_config,
        binary,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (contract.ContractError, n004_contract.ContractError, ValueError) as error:
        print(f"N005 P2 error: {error}", file=sys.stderr)
        raise SystemExit(2)
