"""Run one N006 current frame and validate exact-probe base-ray repetition counts."""
import json
import subprocess
from datetime import datetime, timezone

import run_p1_pilot as p

def validate(stats, evidence):
    if stats.get("protocol_version") != "n006-probe-multiplicity-v1":
        raise ValueError("wrong protocol")
    frame = p.check_evidence(evidence, "current", 0, evidence["device"]["name"])
    n = stats["visible_owners"]
    if frame["stats"]["work_items"] != n * 32 or stats["base_work_items"] != n * 32 or stats["cascade_count"] != 4 or stats["rays_per_probe"] != 8:
        raise ValueError("inconsistent base work")
    if len(stats["cascades"]) != 4:
        raise ValueError("expected four cascades")
    rows = sorted(stats["cascades"], key=lambda x: x["cascade"])
    repeated = 0
    for cascade, row in enumerate(rows):
        unique = row["unique_probe_keys"]
        if (row["cascade"] != cascade or row["owner_outputs"] != n or not 1 <= unique <= n or
            row["duplicated_ray_inputs"] != 8 * (n - unique) or
            not row["same_probe_ray_inputs_identical"]):
            raise ValueError(f"incorrect repeated-ray contract in cascade {cascade}")
        repeated += row["duplicated_ray_inputs"]
    return {"base_work_items": n * 32,
            "repeat_base_ray_inputs": repeated,
            "repeat_fraction": repeated / (n * 32),
            "per_cascade": rows,
            "claim": "exact repeated base ray INPUTS, not measured attainable speedup"}

def main():
    head = p.require_clean_branch()
    if not p.BINARY.is_file():
        raise RuntimeError("run mise run build")
    config = json.loads(p.CONFIG_PATH.read_text())
    scene = p.ROOT / config["baseline"]["scene"]
    if not scene.is_file() or p.sha256(scene) != config["baseline"]["scene_sha256"]:
        raise RuntimeError("wrong/missing scene")
    out = p.ROOT / "out/research/n006-interval-aware-allocation/p1c-probe-multiplicity" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=False)
    args = ["bash", str(p.ROOT / "scripts/run_with_vulkan.sh"),
            str(p.BINARY), "--scene", str(scene), "--artifact-dir", str(out),
            "--scenario", "deforming-control", "--mode", "current",
            "--source-warmup-frames", "1", "--target-frames", "1",
            "--owner-budgets", "0", "--skip-reference", "--capture-probe-multiplicity"]
    proc = subprocess.run(args, cwd=p.ROOT, capture_output=True, text=True, check=False)
    (out / "stdout.log").write_text(proc.stdout)
    (out / "stderr.log").write_text(proc.stderr)
    if proc.returncode:
        raise RuntimeError(f"GPU capture exit {proc.returncode}: {out / 'stderr.log'}")
    evidence = json.loads((out / "n006-candidate-evidence.json").read_text())
    if evidence["device"]["name"] != config["target_gpu"]:
        raise RuntimeError("incorrect device")
    raw = json.loads((out / "n006-probe-multiplicity.json").read_text())
    result = validate(raw, evidence)
    result.update({"protocol_version": "n006-p1c-multiplicity-v1",
                   "formal": False, "reference_generated": False,
                   "git": {"branch": p.EXPECTED_BRANCH, "head": head, "dirty": False},
                   "device": evidence["device"]["name"], "status": "complete"})
    path = out / "n006-p1c-multiplicity-summary.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "repeat_fraction": result["repeat_fraction"], "summary": str(path)}, indent=2))

if __name__ == "__main__":
    main()
