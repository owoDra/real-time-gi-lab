#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
N004_SCRIPTS = ROOT / "scripts/research/lane_n_end_to_end_renderer"
sys.path.insert(0, str(N004_SCRIPTS))
sys.path.insert(0, str(HERE))

import n001_contract as image_contract
import n004_contract
import n004_scene_factory
import run_n004_weakness_atlas as n004
import n005_analysis as analysis
import n005_contract as contract

DEFAULT_CONFIG = (
    ROOT
    / "research/lanes/n005-adaptive-tracing/experiments/"
      "001-p0-p1-signal-probes-config.json"
)
CAMPAIGN_ROOT = ROOT / "out/research/n005-adaptive-tracing/001-p0-p1-signal-probes"
CAPTURE_ENV = "PHOS_N005_VISIBILITY_CAPTURE_DIR"


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise contract.ContractError(proc.stderr.strip())
    return proc.stdout.strip()


def require_clean_n005() -> str:
    branch = git("branch", "--show-current")
    if branch != contract.EXPECTED_BRANCH:
        raise contract.ContractError(
            f"N005 P1 requires {contract.EXPECTED_BRANCH}, got {branch!r}"
        )
    if git("status", "--porcelain"):
        raise contract.ContractError("N005 P1 requires a clean worktree")
    commit = git("rev-parse", "HEAD")
    if len(commit) != 40:
        raise contract.ContractError("N005 P1 requires a full Git SHA")
    return commit


def artifact_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    env_root = os.environ.get("PHOS_RESEARCH_ARTIFACT_DIR")
    if env_root:
        return Path(env_root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return (CAMPAIGN_ROOT / stamp).resolve()


@contextmanager
def visibility_capture(root: Path) -> Iterator[None]:
    if root.exists() and any(root.iterdir()):
        raise contract.ContractError(
            f"N005 visibility capture directory must be empty: {root}"
        )
    root.mkdir(parents=True, exist_ok=True)
    previous = os.environ.get(CAPTURE_ENV)
    os.environ[CAPTURE_ENV] = str(root)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(CAPTURE_ENV, None)
        else:
            os.environ[CAPTURE_ENV] = previous


def _named(items: list[dict[str, Any]], name: str, label: str) -> dict[str, Any]:
    for item in items:
        if item.get("name") == name:
            return item
    raise contract.ContractError(f"missing {label}: {name}")


def _capture_paths(root: Path, target_frames: int) -> list[Path]:
    paths = sorted(root.glob("visibility-*.bin"))
    expected = target_frames + 1
    if len(paths) != expected:
        raise contract.ContractError(
            f"N005 expected {expected} visibility captures, got {len(paths)}"
        )
    return paths


def analyze_signal_case(
    case_root: Path,
    evidence: dict[str, Any],
    n004_config: dict[str, Any],
    capture_paths: list[Path],
) -> dict[str, Any]:
    analyzed = n004.analyze_case(case_root, evidence, n004_config)
    captures = [analysis.read_visibility_capture(path) for path in capture_paths]
    quality = n004_config["quality_metrics"]
    floor = float(quality["scale_aware_floor"])
    affected_fraction = float(quality["scale_aware_fraction"])
    selection_fractions = contract.SELECTION_FRACTIONS

    frames: list[dict[str, Any]] = []
    for index, evidence_frame in enumerate(evidence["frames"]):
        output = image_contract.read_pfm(
            n004.safe_file(case_root, evidence_frame["image"])
        )
        reference = image_contract.read_pfm(
            n004.safe_file(case_root, evidence_frame["reference"]["path"])
        )
        absolute, relative, affected = analysis.pixel_error_vectors(
            output.pixels,
            reference.pixels,
            relative_floor=floor,
            affected_fraction=affected_fraction,
        )
        signals = analysis.signal_maps(captures[index], captures[index + 1])
        if set(signals) != set(contract.SIGNALS):
            raise contract.ContractError("N005 signal implementation set drifted")

        signal_metrics = {
            name: analysis.localization_metrics(
                signals[name],
                absolute,
                relative,
                affected,
                selection_fractions,
            )
            for name in contract.SIGNALS
        }
        base = analyzed["frames"][index]
        frames.append({
            "index": base["index"],
            "motion_fraction": base["motion_fraction"],
            "internal_correctness": base["internal_correctness"],
            "n004_frozen_metrics": base["metrics"],
            "n004_frozen_generic_classification": base["generic_classification"],
            "temporal_rgb_rms_from_previous": base["temporal_rgb_rms_from_previous"],
            "timing_us_descriptive_only": base["timing_us"],
            "stats": base["stats"],
            "memory_bytes": base["memory_bytes"],
            "extra_rays": 0,
            "visibility_capture": {
                "previous": str(capture_paths[index].relative_to(case_root)),
                "current": str(capture_paths[index + 1].relative_to(case_root)),
            },
            "signals": signal_metrics,
        })
    return {
        "scenario": analyzed["scenario"],
        "source": analyzed["source"],
        "frames": frames,
    }


def run_signal_case(
    *,
    root: Path,
    binary: Path,
    n004_config: dict[str, Any],
    name: str,
    role: str,
    scene: Path,
    scenario: str,
    source_warmup: int,
    target_frames: int,
    topology: bool = False,
    motion_fractions: list[float] | None = None,
) -> dict[str, Any]:
    case_root = root / "cases" / name
    capture_root = case_root / "n005-visibility"
    with visibility_capture(capture_root):
        evidence = n004.run_case(
            binary,
            case_root,
            scene,
            scenario,
            source_warmup,
            target_frames,
            topology=topology,
            motion_fractions=motion_fractions,
        )
    if evidence["device"]["name"] != n004_config["target_gpu"]:
        raise contract.ContractError(
            "N005 target GPU mismatch: "
            f"{evidence['device']['name']!r}"
        )
    result = analyze_signal_case(
        case_root,
        evidence,
        n004_config,
        _capture_paths(capture_root, target_frames),
    )
    result.update({
        "name": name,
        "role": role,
        "topology": topology,
        "extra_rays": 0,
    })
    return result


def build_case_specs(
    n004_config: dict[str, Any],
    generated: Path,
    manifest: dict[str, Any],
    sponza: Path,
) -> list[dict[str, Any]]:
    families = n004_config["families"]
    camera = families["camera-disocclusion"]
    abrupt = _named(camera["cases"], "abrupt-reveal", "camera case")
    gradual = _named(camera["cases"], "gradual-motion", "camera case")

    dynamic = families["dynamic-geometry"]
    stable = _named(
        dynamic["scenarios"], "stable-topology-deforming", "dynamic case"
    )
    topology = _named(
        dynamic["scenarios"], "topology-changing-high-churn", "dynamic case"
    )

    light = families["changing-illumination"]
    light_step = _named(light["cases"], "step-change", "illumination case")

    world_meta = manifest["scenes"]["world-dense"]
    world_scene = generated / world_meta["path"]
    source_warmup = int(n004_config["baseline"]["source_warmup_frames"])

    return [
        {
            "name": "camera-abrupt-reveal",
            "role": "decision",
            "scene": sponza,
            "scenario": camera["scenario"],
            "source_warmup": source_warmup,
            "target_frames": len(abrupt["motion_fractions"]),
            "motion_fractions": [float(v) for v in abrupt["motion_fractions"]],
        },
        {
            "name": "camera-gradual-motion",
            "role": "decision",
            "scene": sponza,
            "scenario": camera["scenario"],
            "source_warmup": source_warmup,
            "target_frames": len(gradual["motion_fractions"]),
            "motion_fractions": [float(v) for v in gradual["motion_fractions"]],
        },
        {
            "name": "stable-topology-deforming",
            "role": "decision",
            "scene": sponza,
            "scenario": stable["scenario"],
            "source_warmup": source_warmup,
            "target_frames": int(dynamic["target_frames"]),
            "topology": False,
        },
        {
            "name": "topology-changing-high-churn",
            "role": "decision",
            "scene": sponza,
            "scenario": topology["scenario"],
            "source_warmup": source_warmup,
            "target_frames": int(dynamic["target_frames"]),
            "topology": True,
        },
        {
            "name": "static",
            "role": "control",
            "scene": sponza,
            "scenario": "static",
            "source_warmup": source_warmup,
            "target_frames": 1,
        },
        {
            "name": "changing-illumination-step",
            "role": "control",
            "scene": sponza,
            "scenario": light["scenario"],
            "source_warmup": source_warmup,
            "target_frames": len(light_step["motion_fractions"]),
            "motion_fractions": [
                float(v) for v in light_step["motion_fractions"]
            ],
        },
        {
            "name": "world-dense",
            "role": "control",
            "scene": world_scene,
            "scenario": "static",
            "source_warmup": source_warmup,
            "target_frames": int(families["world-shape"]["target_frames"]),
        },
    ]


def run_p1(
    root: Path,
    config: dict[str, Any],
    n004_config: dict[str, Any],
    binary: Path,
) -> int:
    commit = require_clean_n005()
    if not binary.is_file():
        raise contract.ContractError(f"missing N004 atlas binary: {binary}")

    sponza = (ROOT / n004_config["baseline"]["scene"]).resolve()
    if n004.common.sha256_file(sponza) != n004_config["baseline"]["scene_sha256"]:
        raise contract.ContractError("N005 Sponza digest mismatch")

    root.mkdir(parents=True, exist_ok=True)
    generated = root / "generated-scenes"
    manifest = n004_scene_factory.generate_all(generated)
    cases = [
        run_signal_case(
            root=root,
            binary=binary,
            n004_config=n004_config,
            **spec,
        )
        for spec in build_case_specs(n004_config, generated, manifest, sponza)
    ]

    correctness_ok = all(
        bool(case["source"]["internal_correctness"])
        and all(bool(frame["internal_correctness"]) for frame in case["frames"])
        for case in cases
    )
    summary = {
        "schema_version": 1,
        "protocol_version": config["protocol_version"],
        "status": "complete" if correctness_ok else "invalid-correctness",
        "phase": "P1",
        "formal_target_measurement": False,
        "adaptive_tracing_implemented": False,
        "extra_rays": 0,
        "timing_interpretation": config["p1"]["timing_interpretation"],
        "sample_exclusion": "none",
        "aggregate_score": None,
        "git_commit": commit,
        "target_gpu": n004_config["target_gpu"],
        "signals": contract.SIGNALS,
        "cases": cases,
    }
    (root / "n005-p1-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "n005-provenance.json").write_text(
        json.dumps({
            "schema_version": 1,
            "protocol_version": config["protocol_version"],
            "git": {
                "branch": contract.EXPECTED_BRANCH,
                "commit": commit,
                "dirty": False,
            },
            "predecessor": config["predecessor"],
            "visibility_capture_env": CAPTURE_ENV,
            "binary": str(binary.relative_to(ROOT)),
            "gpu_profile_changes": "forbidden-and-not-performed-by-runner",
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / "n005-scenes.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"N005 P1 artifacts: {root}")
    print(
        "N005 P1 signal probes: "
        + ("COMPLETE" if correctness_ok else "INVALID-CORRECTNESS")
    )
    return 0 if correctness_ok else 3


def main() -> int:
    parser = argparse.ArgumentParser(
        description="N005 P0/P1 signal-localization runner"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--phase", choices=("contract", "p1"), required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--binary", type=Path)
    args = parser.parse_args()

    config = contract.load_config(args.config.resolve())
    n004_config_path = (ROOT / config["predecessor"]["config"]).resolve()
    n004_config = n004_contract.load_config(n004_config_path)
    contract.validate_n004_predecessor(n004_config)

    if args.phase == "contract":
        print("N005 P0/P1 prospective contract validation: PASS")
        return 0

    binary = (
        args.binary.resolve()
        if args.binary
        else (ROOT / "build/release/phos-n004-atlas").resolve()
    )
    return run_p1(
        artifact_dir(args.artifact_dir),
        config,
        n004_config,
        binary,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (contract.ContractError, n004_contract.ContractError, ValueError) as error:
        print(f"N005 P0/P1 error: {error}", file=sys.stderr)
        raise SystemExit(2)
