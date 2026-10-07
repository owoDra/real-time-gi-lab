#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
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
import run_n005_p2 as p2
import n005_p3_contract as contract

DEFAULT_CONFIG = (
    ROOT / "research/lanes/n005-adaptive-tracing/experiments/"
    "003-p3-formal-comparison-config.json"
)
N004_CONFIG = (
    ROOT / "research/lanes/lane-n-end-to-end-renderer/experiments/"
    "004-n004-weakness-atlas-v2-config.json"
)
CAMPAIGN_ROOT = ROOT / "out/research/n005-adaptive-tracing/003-p3-formal-comparison"
VULKAN_WRAPPER = ROOT / "scripts/run_with_vulkan.sh"
CAPTURE_ENV = "PHOS_N005_VISIBILITY_CAPTURE_DIR"
EVIDENCE_PROTOCOL = "n005-p2-candidate-evidence-v1"

METRIC_KEYS = (
    "rgb_rms_error",
    "mean_abs_luminance_error",
    "signed_mean_luminance_error",
    "p99_abs_luminance_error",
    "max_abs_luminance_error",
    "p99_relative_luminance_error",
    "scale_aware_affected_pixel_fraction",
)
TIMING_KEYS = (
    "complete_gi_gpu",
    "complete_renderer_gpu",
    "extra_producer_gpu",
    "producer_gpu",
    "ray_prepare_gpu",
    "traversal_gpu",
    "radiance_gpu",
    "merge_gpu",
    "storage_update_gpu",
    "resolve_gpu",
    "dynamic_update_wall",
    "geometry_transfer_gpu",
    "instance_transfer_gpu",
    "blas_update_gpu",
    "tlas_update_gpu",
)
MEMORY_KEYS = (
    "persistent",
    "transient",
    "scratch",
    "old_new_overlap",
    "true_lifetime_peak",
    "radiance_storage_persistent",
    "producer_stream_capacity",
    "image_transient",
)
EXTRA_KEYS = (
    "base_traced_rays",
    "extra_rays_requested",
    "extra_rays_traced",
    "extra_work_items",
    "eligible_owner_count",
    "selected_owner_count",
    "eligible_probe_count",
    "extra_probe_count",
    "extra_probe_fraction",
    "extra_producer_gpu_us",
)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if check and proc.returncode != 0:
        raise contract.ContractError(proc.stderr.strip() or "git command failed")
    return proc


def require_clean_branch() -> str:
    branch = git("branch", "--show-current").stdout.strip()
    if branch != contract.EXPECTED_BRANCH:
        raise contract.ContractError(
            f"N005 P3 requires {contract.EXPECTED_BRANCH}, got {branch!r}"
        )
    if git("status", "--porcelain").stdout.strip():
        raise contract.ContractError("N005 P3 requires a clean worktree")
    commit = git("rev-parse", "HEAD").stdout.strip()
    if len(commit) != 40:
        raise contract.ContractError("N005 P3 requires a full Git SHA")
    ancestor = git(
        "merge-base", "--is-ancestor", contract.EXPECTED_P2_COMMIT, commit, check=False
    )
    if ancestor.returncode != 0:
        raise contract.ContractError(
            "N005 P3 HEAD does not contain the accepted optimized P2 commit"
        )
    return commit


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if env_root:
        return Path(env_root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (CAMPAIGN_ROOT / stamp).resolve()


def completed_campaigns(current_root: Path) -> list[Path]:
    if not CAMPAIGN_ROOT.exists():
        return []
    found = []
    for path in CAMPAIGN_ROOT.glob("*/n005-p3-summary.json"):
        if path.parent.resolve() == current_root.resolve():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            payload.get("status") == "complete"
            and payload.get("protocol_version") == contract.PROTOCOL_VERSION
        ):
            found.append(path)
    return sorted(found)


def safe_file(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise contract.ContractError("N005 P3 evidence path escaped case root")
    result = root / path
    if not result.is_file():
        raise contract.ContractError(f"N005 P3 evidence file missing: {result}")
    return result


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
    skip_reference: bool,
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
        "--owner-budgets", ",".join(str(v) for v in owner_budgets),
        "--depth-threshold", str(depth_threshold),
        "--extra-rays-per-probe", str(extra_rays_per_probe),
    ]
    if motion_fractions is not None:
        command += [
            "--motion-fractions",
            ",".join(str(v) for v in motion_fractions),
        ]
    if topology:
        command.append("--topology")
    if skip_reference:
        command.append("--skip-reference")
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
            f"N005 P3 case failed: {root}; artifact retained"
        )

    path = root / "n005-candidate-evidence.json"
    if not path.is_file():
        raise contract.ContractError(f"N005 P3 evidence missing: {root}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("protocol_version") != EVIDENCE_PROTOCOL:
        raise contract.ContractError("N005 P3 candidate evidence protocol changed")
    if payload.get("mode") != mode:
        raise contract.ContractError("N005 P3 evidence mode mismatch")
    if len(payload.get("frames", [])) != target_frames:
        raise contract.ContractError("N005 P3 evidence frame count mismatch")
    p2.validate_evidence_threshold(payload.get("depth_threshold"), depth_threshold)
    if payload.get("extra_rays_per_probe") != extra_rays_per_probe:
        raise contract.ContractError("N005 P3 extra-ray multiplicity mismatch")
    expected_ref = "skipped" if skip_reference else "rendered"
    if payload.get("reference_generation") != expected_ref:
        raise contract.ContractError("N005 P3 reference-generation mode mismatch")
    for frame in payload["frames"]:
        if skip_reference and frame.get("reference") is not None:
            raise contract.ContractError("N005 P3 skip-reference run emitted reference")
        if not skip_reference and not isinstance(frame.get("reference"), dict):
            raise contract.ContractError("N005 P3 reference seed missing reference")
    return payload


def analyze_against_seed(
    case_root: Path,
    evidence: dict[str, Any],
    seed_root: Path,
    seed_evidence: dict[str, Any],
    n004_config: dict[str, Any],
) -> dict[str, Any]:
    if len(evidence["frames"]) != len(seed_evidence["frames"]):
        raise contract.ContractError("N005 P3 seed/formal frame count mismatch")

    frames = []
    images = []
    for frame, seed in zip(evidence["frames"], seed_evidence["frames"], strict=True):
        image = image_contract.read_pfm(safe_file(case_root, frame["image"]))
        reference_meta = seed.get("reference")
        if not isinstance(reference_meta, dict):
            raise contract.ContractError("N005 P3 canonical reference metadata missing")
        reference = image_contract.read_pfm(
            safe_file(seed_root, reference_meta["path"])
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
            "canonical_reference": reference_meta,
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
        "device": evidence["device"],
        "frames": frames,
    }


def median_dict(samples: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, float]:
    return {
        key: float(statistics.median(float(sample[key]) for sample in samples))
        for key in keys
    }


def median_mode(
    mode: str,
    repetitions: list[dict[str, Any]],
    n004_config: dict[str, Any],
) -> dict[str, Any]:
    runs = [rep["modes"][mode] for rep in repetitions]
    frame_count = len(runs[0]["frames"])
    if any(len(run["frames"]) != frame_count for run in runs):
        raise contract.ContractError("N005 P3 repetition frame count mismatch")

    frames = []
    for index in range(frame_count):
        raw = [run["frames"][index] for run in runs]
        metrics = median_dict([f["metrics"] for f in raw], METRIC_KEYS)
        temporal = [
            float(f["temporal_rgb_rms_from_previous"])
            for f in raw
            if f["temporal_rgb_rms_from_previous"] is not None
        ]
        frames.append({
            "index": index,
            "metrics": metrics,
            "generic_classification": n004.generic_classification(
                metrics, n004_config
            ),
            "timing_us": median_dict([f["timing_us"] for f in raw], TIMING_KEYS),
            "memory_bytes": median_dict(
                [f["memory_bytes"] for f in raw], MEMORY_KEYS
            ),
            "extra": median_dict([f["extra"] for f in raw], EXTRA_KEYS),
            "temporal_rgb_rms_from_previous": (
                None if not temporal else float(statistics.median(temporal))
            ),
            "all_internal_correctness": all(
                bool(f["internal_correctness"]) for f in raw
            ),
            "all_base_prefix_correct": all(
                bool(f["extra"]["base_prefix_correct"]) for f in raw
            ),
            "all_extra_work_correct": all(
                bool(f["extra"]["extra_work_correct"]) for f in raw
            ),
            "all_zero_substantive_mismatches": all(
                int(f["hit_diagnostics"]["substantive_mismatches"]) == 0
                for f in raw
            ),
        })
    return {"mode": mode, "frames": frames}


def efficiency_view(
    role: str,
    schedule: list[int],
    medians: dict[str, Any],
) -> dict[str, Any] | None:
    if role != "decision":
        return None
    active = [i for i, budget in enumerate(schedule) if budget > 0]
    current = medians["current"]["frames"]
    result: dict[str, Any] = {"active_frames": active, "modes": {}}

    for mode in ("uniform-extra-rays", "adaptive-extra-rays"):
        candidate = medians[mode]["frames"]
        improvements = []
        incremental = []
        for index in active:
            c = float(current[index]["metrics"]["rgb_rms_error"])
            m = float(candidate[index]["metrics"]["rgb_rms_error"])
            improvements.append(0.0 if c == 0.0 else (c - m) / c)
            incremental.append(
                float(candidate[index]["timing_us"]["complete_gi_gpu"])
                - float(current[index]["timing_us"]["complete_gi_gpu"])
            )
        median_improvement = float(statistics.median(improvements))
        median_incremental = float(statistics.median(incremental))
        rays = float(
            medians[mode]["frames"][active[0]]["extra"]["extra_rays_traced"]
        )
        result["modes"][mode] = {
            "median_rgb_rms_improvement_fraction": median_improvement,
            "quality_improvement_per_1000_extra_rays": (
                None if rays <= 0.0 else median_improvement / (rays / 1000.0)
            ),
            "median_incremental_complete_gi_gpu_us": median_incremental,
            "quality_improvement_per_incremental_complete_gi_gpu_us": (
                None
                if median_incremental <= 0.0
                else median_improvement / median_incremental
            ),
            "gpu_cost_efficiency_status": (
                "measurement-limited"
                if median_incremental <= 0.0
                else "measured"
            ),
            "per_active_frame_rgb_rms_improvement_fraction": improvements,
            "per_active_frame_incremental_complete_gi_gpu_us": incremental,
        }

    adaptive_delta = []
    cost_delta = []
    for index in active:
        uniform = medians["uniform-extra-rays"]["frames"][index]
        adaptive = medians["adaptive-extra-rays"]["frames"][index]
        adaptive_delta.append(
            float(adaptive["metrics"]["rgb_rms_error"])
            - float(uniform["metrics"]["rgb_rms_error"])
        )
        cost_delta.append(
            float(adaptive["timing_us"]["complete_gi_gpu"])
            - float(uniform["timing_us"]["complete_gi_gpu"])
        )
    result["adaptive_vs_uniform"] = {
        "median_rgb_rms_error_delta": float(statistics.median(adaptive_delta)),
        "median_complete_gi_gpu_us_delta": float(statistics.median(cost_delta)),
    }
    return result


def run_p3(
    root: Path,
    config: dict[str, Any],
    n004_config: dict[str, Any],
    binary: Path,
) -> int:
    commit = require_clean_branch()
    if not binary.is_file():
        raise contract.ContractError(f"missing N005 P3 binary: {binary}")
    if root.exists() and any(root.iterdir()):
        raise contract.ContractError(
            f"N005 P3 artifact directory must be empty: {root}"
        )
    existing = completed_campaigns(root)
    if existing:
        joined = ", ".join(str(p.parent.relative_to(ROOT)) for p in existing)
        raise contract.ContractError(
            "N005 P3 completed campaign rerun budget is zero; existing campaign: "
            + joined
        )

    sponza = (ROOT / n004_config["baseline"]["scene"]).resolve()
    if n004.common.sha256_file(sponza) != n004_config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N005 P3 Sponza digest mismatch")

    root.mkdir(parents=True, exist_ok=True)
    generated = root / "generated-scenes"
    manifest = n004_scene_factory.generate_all(generated)
    specs = p1.build_case_specs(n004_config, generated, manifest, sponza)
    expected = (
        config["formal_regimes"]["decision"]
        + config["formal_regimes"]["controls"]
    )
    if [spec["name"] for spec in specs] != expected:
        raise contract.ContractError("N005 P3 formal case set/order drifted")

    cases = []
    repeat_count = int(config["repetition"]["count"])
    rotation = config["repetition"]["mode_order_rotation"]

    for spec in specs:
        name = spec["name"]
        schedule = [int(v) for v in config["state_change_schedule"][name]]
        if len(schedule) != int(spec["target_frames"]):
            raise contract.ContractError(
                f"N005 P3 frozen schedule length drifted: {name}"
            )

        seed_root = root / "references" / name
        seed = run_case(
            binary=binary,
            root=seed_root,
            scene=spec["scene"],
            scenario=spec["scenario"],
            mode="current",
            source_warmup=int(spec["source_warmup"]),
            target_frames=int(spec["target_frames"]),
            owner_budgets=[0] * len(schedule),
            depth_threshold=float(config["candidate"]["normalized_depth_threshold"]),
            extra_rays_per_probe=int(config["candidate"]["extra_rays_per_probe"]),
            skip_reference=False,
            topology=bool(spec.get("topology", False)),
            motion_fractions=spec.get("motion_fractions"),
        )
        if seed["device"]["name"] != n004_config["target_gpu"]:
            raise contract.ContractError("N005 P3 target GPU mismatch in reference seed")

        repetitions = []
        for repetition in range(repeat_count):
            order = rotation[repetition % len(rotation)]
            modes = {}
            for mode in order:
                budgets = [0] * len(schedule) if mode == "current" else schedule
                mode_root = (
                    root / "cases" / name
                    / f"repetition-{repetition:02d}" / mode
                )
                evidence = run_case(
                    binary=binary,
                    root=mode_root,
                    scene=spec["scene"],
                    scenario=spec["scenario"],
                    mode=mode,
                    source_warmup=int(spec["source_warmup"]),
                    target_frames=int(spec["target_frames"]),
                    owner_budgets=budgets,
                    depth_threshold=float(
                        config["candidate"]["normalized_depth_threshold"]
                    ),
                    extra_rays_per_probe=int(
                        config["candidate"]["extra_rays_per_probe"]
                    ),
                    skip_reference=True,
                    topology=bool(spec.get("topology", False)),
                    motion_fractions=spec.get("motion_fractions"),
                )
                if evidence["device"]["name"] != n004_config["target_gpu"]:
                    raise contract.ContractError("N005 P3 target GPU mismatch")
                analyzed = analyze_against_seed(
                    mode_root, evidence, seed_root, seed, n004_config
                )
                p2.validate_mode_case(name, mode, budgets, analyzed, config)
                modes[mode] = analyzed
            p2.validate_equal_budget(
                name,
                modes["uniform-extra-rays"],
                modes["adaptive-extra-rays"],
            )
            repetitions.append({
                "index": repetition,
                "mode_order": order,
                "modes": modes,
            })

        medians = {
            mode: median_mode(mode, repetitions, n004_config)
            for mode in config["required_modes"]
        }
        cases.append({
            "name": name,
            "role": spec["role"],
            "owner_budget_schedule": schedule,
            "canonical_reference_seed": {
                "path": str(seed_root.relative_to(root)),
                "mode": "current",
                "formal_repetition": False,
                "frames": [frame["reference"] for frame in seed["frames"]],
            },
            "repetitions": repetitions,
            "medians": medians,
            "efficiency": efficiency_view(spec["role"], schedule, medians),
        })

    summary = {
        "schema_version": 1,
        "protocol_version": config["protocol_version"],
        "status": "complete",
        "phase": "P3",
        "formal_target_measurement": True,
        "aggregate_score": None,
        "sample_exclusion": "none",
        "post_hoc_threshold_or_budget_change": "none",
        "git_commit": commit,
        "target_gpu": n004_config["target_gpu"],
        "candidate": config["candidate"],
        "repetition": config["repetition"],
        "reference_policy": config["reference"],
        "equal_budget_gate": "passed",
        "decision": "pending-result-analysis",
        "cases": cases,
    }
    (root / "n005-p3-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "n005-p3-provenance.json").write_text(
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
            "optimized_p2_evidence_commit": contract.EXPECTED_P2_COMMIT,
            "completed_campaign_rerun_budget": 0,
            "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
            "visibility_capture": "disabled-for-p3-formal-timing",
            "reference_policy": config["reference"],
            "repetition": config["repetition"],
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "n005-scenes.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"N005 P3 artifacts: {root}")
    print("N005 P3 formal comparison: COMPLETE")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run N005 P3 formal comparison")
    parser.add_argument(
        "--phase", choices=["contract", "formal"], default="contract"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument(
        "--binary",
        type=Path,
        default=ROOT / "build/release/phos-n005-candidate",
    )
    args = parser.parse_args()

    try:
        config = contract.load_config(args.config)
        n004_config = json.loads(N004_CONFIG.read_text(encoding="utf-8"))
        n004_contract.validate_config(n004_config)
        contract.validate_n004_predecessor(n004_config)
        if args.phase == "contract":
            print("N005 P3 formal contract: PASS")
            print(json.dumps({
                "protocol_version": config["protocol_version"],
                "repetitions": config["repetition"]["count"],
                "summary_statistic": config["repetition"]["summary_statistic"],
                "reference_policy": config["reference"]["policy"],
                "signal": config["candidate"]["signal"],
                "threshold": config["candidate"]["normalized_depth_threshold"],
                "active_extra_rays": config["equal_budget_gate"][
                    "active_actual_extra_rays"
                ],
                "completed_campaign_rerun_budget": config[
                    "completed_campaign_rerun_budget"
                ],
            }, indent=2, sort_keys=True))
            return 0
        return run_p3(
            artifact_dir(args.artifact_dir),
            config,
            n004_config,
            args.binary.resolve(),
        )
    except (
        contract.ContractError,
        n004_contract.ContractError,
        p2.contract.ContractError,
    ) as error:
        print(f"N005 P3 error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
