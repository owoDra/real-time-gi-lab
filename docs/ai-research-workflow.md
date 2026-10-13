# AI-driven research and human oversight

This repository is a record of a real-time global illumination research program conducted **primarily through semi-autonomous workflows using ChatGPT and OpenAI Codex CLI**, under human direction and oversight. It is not presented as solely human-written code, as an unattended autonomous scientist, or as proof of an AI-discovered breakthrough.

## Who did what

| Responsibility | Main approach |
| --- | --- |
| Research direction | **Human:** established goals, priorities, constraints, and when to stop or change direction |
| Literature and architecture exploration | **AI-assisted:** ChatGPT and Codex CLI helped investigate alternatives, formulate hypotheses, and propose experiment plans |
| Code, shaders, benchmarks, tests, scripts, and documentation | **Primarily AI-produced and iterated:** generated and refined through ChatGPT/Codex CLI workflows, with human feedback |
| Vulkan/GPU execution and environment operation | **Human-operated environment:** experiments used the project's actual Vulkan-capable workstation/GPU; AI handled instructions and result analysis based on observed artifacts |
| Result classification and acceptance | **Human-supervised:** accepted, rejected, neutral, and inconclusive results follow recorded measurements and the [research protocol](../research/protocol.md), not the model's confidence |
| Research history integration | **AI-assisted:** study branches, original result files, decisions, and provenance were inventoried and consolidated with human authorization |

The allocation of work varied between experiments; the table describes the program overall and does not assert that each historical code line or result was authored, verified, or executed by a particular model.

### Later studies with Claude Code

From N008 ([Issue #5](https://github.com/owoDra/real-time-gi-lab/issues/5), 2026-10-13) work was also carried out with **Claude Code (Anthropic)** under the same human direction. N008 Phase A (oracle source, analytic controls, Mitsuba cross-check and records) was implemented and executed by the assistant entirely on CPU in its sandbox; no GPU measurement was performed or claimed by the assistant. GPU steps, when needed, are run by the human operator and recorded as such.

## How the loop worked

1. Define the question, comparable baseline, measurement boundary, quality/correctness constraints, and stopping conditions.
2. Use ChatGPT/Codex CLI to propose and implement an experiment, including code, automated checks, and experiment documentation.
3. Execute builds, tests, and GPU workloads in the actual project environment; capture logs and measured artifacts.
4. Have AI analyze the observed results and propose the next bounded step, with human review of important decisions.
5. Preserve outcomes **including negative, neutral, inconclusive, and abandoned studies** in [lane results](../research/lanes/) and [cross-lane decisions](../research/decisions/).

The cycle could run for many iterations with limited human intervention, but it still depended on human-provided access, execution, evidence, and authorization at key points.

## What the research claims do and do not mean

- **Measurements are the source of truth.** AI-generated explanations do not supersede recorded experiment outputs, comparison boundaries, GPU timestamps, shader/source revisions, or known limitations.
- Most measured studies used **AMD Radeon 8060S Graphics (RADV STRIX_HALO)** and selected workloads. Do not extrapolate their speedups to every GPU, scene, or GI method.
- The current renderer is an experimental artifact, not a validated universal replacement for existing GI solutions. See [current status](../research/status.md).
- The October 2026 branch consolidation imported prior evidence and dormant lane code. Builds, tests, or GPU measurements were **not rerun during that archival consolidation**, and their absence was explicitly disclosed in [consolidation verification](../research/consolidation-validation.md).
- Original commit authorship is Git metadata; it is **not a reliable line-by-line attribution of human versus AI work**. This page is a transparent high-level declaration by the project owner.
- Names of the AI tools are given for transparency, not as product endorsement or independent certification by their provider.

## Reproducing or extending this project

Start with the [README](../README.md), [research charter](research.md), [current status](../research/status.md), and [research protocol](../research/protocol.md). Experiment-specific configurations and evidence are maintained with their study lanes. If an experiment is not reproducible from the committed files alone, report that gap rather than inventing the missing measurements. Third-party assets and dependencies retain their own licenses.
